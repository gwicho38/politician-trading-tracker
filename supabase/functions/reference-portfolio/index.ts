import { createClient } from 'supabase'
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

// Structured logging utility
const log = {
  info: (message: string, metadata?: any) => {
    console.log(JSON.stringify({
      level: 'INFO',
      timestamp: new Date().toISOString(),
      service: 'reference-portfolio',
      message,
      ...metadata
    }))
  },
  error: (message: string, error?: any, metadata?: any) => {
    console.error(JSON.stringify({
      level: 'ERROR',
      timestamp: new Date().toISOString(),
      service: 'reference-portfolio',
      message,
      error: error?.message || error,
      stack: error?.stack,
      ...metadata
    }))
  },
  warn: (message: string, metadata?: any) => {
    console.warn(JSON.stringify({
      level: 'WARN',
      timestamp: new Date().toISOString(),
      service: 'reference-portfolio',
      message,
      ...metadata
    }))
  }
}

// Types
interface ReferencePortfolioConfig {
  id: string
  name: string
  initial_capital: number
  min_confidence_threshold: number
  max_position_size_pct: number
  max_portfolio_positions: number
  max_single_trade_pct: number
  max_daily_trades: number
  default_stop_loss_pct: number
  default_take_profit_pct: number
  base_position_size_pct: number
  confidence_multiplier: number
  is_active: boolean
}

interface ReferencePortfolioState {
  id: string
  config_id: string
  cash: number
  portfolio_value: number
  positions_value: number
  buying_power: number
  total_return: number
  total_return_pct: number
  open_positions: number
  trades_today: number
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  sharpe_ratio: number | null
  max_drawdown: number
  peak_portfolio_value: number
  last_trade_at: string | null
  last_sync_at: string | null
}

interface TradingSignal {
  id: string
  ticker: string
  asset_name: string
  signal_type: string
  confidence_score: number
  target_price: number | null
  stop_loss: number | null
  take_profit: number | null
}

// Get Alpaca credentials from environment (reference portfolio uses app-level credentials)
function getAlpacaCredentials(): { apiKey: string; secretKey: string; baseUrl: string } | null {
  const apiKey = Deno.env.get('ALPACA_API_KEY')
  const secretKey = Deno.env.get('ALPACA_SECRET_KEY')
  const paper = Deno.env.get('ALPACA_PAPER') === 'true'
  const baseUrl = Deno.env.get('ALPACA_BASE_URL') || (paper ? 'https://paper-api.alpaca.markets' : 'https://api.alpaca.markets')

  if (!apiKey || !secretKey) {
    return null
  }

  return { apiKey, secretKey, baseUrl }
}

// Calculate position size based on confidence (confidence-weighted)
function calculatePositionSize(
  portfolioValue: number,
  confidence: number,
  currentPrice: number,
  config: ReferencePortfolioConfig
): { shares: number; positionValue: number; multiplier: number } {
  // Base position size
  const baseSize = portfolioValue * (config.base_position_size_pct / 100)

  // Calculate confidence multiplier (1x to max based on confidence)
  const confidenceRange = 1.0 - config.min_confidence_threshold
  const normalizedConfidence = Math.max(0, Math.min(1, (confidence - config.min_confidence_threshold) / confidenceRange))
  const multiplier = 1 + (normalizedConfidence * (config.confidence_multiplier - 1))

  // Apply multiplier
  let positionValue = baseSize * multiplier

  // Cap at max position size
  const maxPosition = portfolioValue * (config.max_position_size_pct / 100)
  positionValue = Math.min(positionValue, maxPosition)

  // Cap at max single trade size
  const maxTrade = portfolioValue * (config.max_single_trade_pct / 100)
  positionValue = Math.min(positionValue, maxTrade)

  // Calculate shares
  const shares = Math.floor(positionValue / currentPrice)

  return { shares, positionValue: shares * currentPrice, multiplier }
}

// Check if market is currently open (US Eastern Time)
function isMarketOpen(): boolean {
  const now = new Date()
  const etOffset = -5 // EST (simplified - should handle DST)
  const utcHour = now.getUTCHours()
  const etHour = (utcHour + etOffset + 24) % 24
  const dayOfWeek = now.getUTCDay()

  // Market hours: 9:30 AM - 4:00 PM ET, Monday-Friday
  const isWeekday = dayOfWeek >= 1 && dayOfWeek <= 5
  const isMarketHours = (etHour >= 9 && etHour < 16) || (etHour === 9 && now.getUTCMinutes() >= 30)

  return isWeekday && isMarketHours
}

serve(async (req) => {
  const startTime = Date.now()
  const requestId = crypto.randomUUID().substring(0, 8)

  log.info('Request received', { requestId, method: req.method, url: req.url })

  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // Initialize Supabase client with service role key
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const url = new URL(req.url)
    let action = url.pathname.split('/').pop()

    // Support action in request body
    let bodyParams: any = {}
    if (req.method === 'POST') {
      try {
        bodyParams = await req.clone().json()
        if (bodyParams.action) {
          action = bodyParams.action
        }
      } catch {
        // Body parsing failed
      }
    }

    log.info('Processing action', { requestId, action })

    let response: Response

    switch (action) {
      case 'get-state':
        response = await handleGetState(supabaseClient, requestId)
        break
      case 'get-positions':
        response = await handleGetPositions(supabaseClient, requestId, bodyParams)
        break
      case 'get-trades':
        response = await handleGetTrades(supabaseClient, requestId, bodyParams)
        break
      case 'get-performance':
        response = await handleGetPerformance(supabaseClient, requestId, bodyParams)
        break
      case 'execute-signals':
        response = await handleExecuteSignals(supabaseClient, requestId, bodyParams)
        break
      case 'update-positions':
        response = await handleUpdatePositions(supabaseClient, requestId)
        break
      case 'take-snapshot':
        response = await handleTakeSnapshot(supabaseClient, requestId)
        break
      case 'reset-daily-trades':
        response = await handleResetDailyTrades(supabaseClient, requestId)
        break
      default:
        // Default to get-state for general requests
        response = await handleGetState(supabaseClient, requestId)
    }

    log.info('Request completed', { requestId, duration: Date.now() - startTime })
    return response

  } catch (error) {
    log.error('Edge function error', error, { requestId })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

// =============================================================================
// GET STATE - Public endpoint to get current portfolio state
// =============================================================================
async function handleGetState(supabaseClient: any, requestId: string) {
  try {
    // Get config and state together
    const { data: state, error: stateError } = await supabaseClient
      .from('reference_portfolio_state')
      .select(`
        *,
        config:reference_portfolio_config(*)
      `)
      .single()

    if (stateError) {
      log.error('Failed to fetch portfolio state', stateError, { requestId })
      return new Response(
        JSON.stringify({ error: 'Failed to fetch portfolio state' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    return new Response(
      JSON.stringify({
        success: true,
        state: {
          ...state,
          is_market_open: isMarketOpen()
        }
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    log.error('Error in handleGetState', error, { requestId })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}

// =============================================================================
// GET POSITIONS - Public endpoint to get current open positions
// =============================================================================
async function handleGetPositions(supabaseClient: any, requestId: string, bodyParams: any) {
  try {
    const includesClosed = bodyParams.include_closed === true
    const limit = bodyParams.limit || 100

    let query = supabaseClient
      .from('reference_portfolio_positions')
      .select('*')
      .order('entry_date', { ascending: false })
      .limit(limit)

    if (!includesClosed) {
      query = query.eq('is_open', true)
    }

    const { data: positions, error } = await query

    if (error) {
      log.error('Failed to fetch positions', error, { requestId })
      return new Response(
        JSON.stringify({ error: 'Failed to fetch positions' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    return new Response(
      JSON.stringify({
        success: true,
        positions: positions || [],
        count: positions?.length || 0
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    log.error('Error in handleGetPositions', error, { requestId })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}

// =============================================================================
// GET TRADES - Public endpoint to get trade history
// =============================================================================
async function handleGetTrades(supabaseClient: any, requestId: string, bodyParams: any) {
  try {
    const limit = bodyParams.limit || 50
    const offset = bodyParams.offset || 0

    const { data: trades, error, count } = await supabaseClient
      .from('reference_portfolio_transactions')
      .select('*', { count: 'exact' })
      .order('executed_at', { ascending: false })
      .range(offset, offset + limit - 1)

    if (error) {
      log.error('Failed to fetch trades', error, { requestId })
      return new Response(
        JSON.stringify({ error: 'Failed to fetch trades' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    return new Response(
      JSON.stringify({
        success: true,
        trades: trades || [],
        total: count || 0,
        limit,
        offset
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    log.error('Error in handleGetTrades', error, { requestId })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}

// =============================================================================
// GET PERFORMANCE - Public endpoint to get performance snapshots
// =============================================================================
async function handleGetPerformance(supabaseClient: any, requestId: string, bodyParams: any) {
  try {
    const timeframe = bodyParams.timeframe || '1m' // 1d, 1w, 1m, 3m, ytd, 1y
    const now = new Date()
    let startDate: Date

    switch (timeframe) {
      case '1d':
        startDate = new Date(now.getTime() - 24 * 60 * 60 * 1000)
        break
      case '1w':
        startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
        break
      case '1m':
        startDate = new Date(now.setMonth(now.getMonth() - 1))
        break
      case '3m':
        startDate = new Date(now.setMonth(now.getMonth() - 3))
        break
      case 'ytd':
        startDate = new Date(now.getFullYear(), 0, 1)
        break
      case '1y':
        startDate = new Date(now.setFullYear(now.getFullYear() - 1))
        break
      default:
        startDate = new Date(now.setMonth(now.getMonth() - 1))
    }

    const { data: snapshots, error } = await supabaseClient
      .from('reference_portfolio_snapshots')
      .select('*')
      .gte('snapshot_date', startDate.toISOString().split('T')[0])
      .order('snapshot_date', { ascending: true })

    if (error) {
      log.error('Failed to fetch performance data', error, { requestId })
      return new Response(
        JSON.stringify({ error: 'Failed to fetch performance data' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    return new Response(
      JSON.stringify({
        success: true,
        timeframe,
        snapshots: snapshots || [],
        count: snapshots?.length || 0
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    log.error('Error in handleGetPerformance', error, { requestId })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}

// =============================================================================
// EXECUTE SIGNALS - Process pending signals and execute trades
// =============================================================================
async function handleExecuteSignals(supabaseClient: any, requestId: string, bodyParams: any) {
  try {
    log.info('Starting signal execution', { requestId })

    // Get config and state
    const { data: config, error: configError } = await supabaseClient
      .from('reference_portfolio_config')
      .select('*')
      .single()

    if (configError || !config) {
      log.error('Failed to fetch config', configError, { requestId })
      return new Response(
        JSON.stringify({ error: 'Portfolio configuration not found' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    if (!config.is_active) {
      log.info('Portfolio trading is disabled', { requestId })
      return new Response(
        JSON.stringify({ success: true, message: 'Trading is disabled', executed: 0 }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const { data: state, error: stateError } = await supabaseClient
      .from('reference_portfolio_state')
      .select('*')
      .single()

    if (stateError || !state) {
      log.error('Failed to fetch state', stateError, { requestId })
      return new Response(
        JSON.stringify({ error: 'Portfolio state not found' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Check trading constraints
    if (state.trades_today >= config.max_daily_trades) {
      log.info('Daily trade limit reached', { requestId, tradesToday: state.trades_today, limit: config.max_daily_trades })
      return new Response(
        JSON.stringify({ success: true, message: 'Daily trade limit reached', executed: 0 }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    if (state.open_positions >= config.max_portfolio_positions) {
      log.info('Max positions reached', { requestId, openPositions: state.open_positions, limit: config.max_portfolio_positions })
      return new Response(
        JSON.stringify({ success: true, message: 'Maximum positions reached', executed: 0 }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get pending signals from queue
    const { data: queuedSignals, error: queueError } = await supabaseClient
      .from('reference_portfolio_signal_queue')
      .select(`
        *,
        signal:trading_signals(*)
      `)
      .eq('status', 'pending')
      .order('created_at', { ascending: true })
      .limit(config.max_daily_trades - state.trades_today)

    if (queueError) {
      log.error('Failed to fetch signal queue', queueError, { requestId })
      return new Response(
        JSON.stringify({ error: 'Failed to fetch signal queue' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    if (!queuedSignals || queuedSignals.length === 0) {
      log.info('No pending signals to process', { requestId })
      return new Response(
        JSON.stringify({ success: true, message: 'No pending signals', executed: 0 }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    log.info('Processing signals', { requestId, count: queuedSignals.length })

    // Get Alpaca credentials
    const credentials = getAlpacaCredentials()
    if (!credentials) {
      log.error('No Alpaca credentials configured', null, { requestId })
      return new Response(
        JSON.stringify({ error: 'Alpaca credentials not configured' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get existing positions to avoid duplicates
    const { data: existingPositions } = await supabaseClient
      .from('reference_portfolio_positions')
      .select('ticker')
      .eq('is_open', true)

    const existingTickers = new Set((existingPositions || []).map((p: any) => p.ticker.toUpperCase()))

    let executed = 0
    let skipped = 0
    let failed = 0
    const results: any[] = []

    for (const queued of queuedSignals) {
      const signal = queued.signal as TradingSignal

      if (!signal) {
        await updateQueueStatus(supabaseClient, queued.id, 'skipped', 'Signal not found')
        skipped++
        continue
      }

      // Skip if we already have a position in this ticker
      if (existingTickers.has(signal.ticker.toUpperCase())) {
        await updateQueueStatus(supabaseClient, queued.id, 'skipped', 'Already have position')
        skipped++
        continue
      }

      // Check confidence threshold
      if (signal.confidence_score < config.min_confidence_threshold) {
        await updateQueueStatus(supabaseClient, queued.id, 'skipped', 'Below confidence threshold')
        skipped++
        continue
      }

      // Only process buy signals for new positions (we handle sells separately)
      const isBuySignal = ['buy', 'strong_buy'].includes(signal.signal_type)
      if (!isBuySignal) {
        await updateQueueStatus(supabaseClient, queued.id, 'skipped', 'Not a buy signal')
        skipped++
        continue
      }

      try {
        // Get current price from Alpaca
        const quoteUrl = `${credentials.baseUrl}/v2/stocks/${signal.ticker}/quotes/latest`
        const quoteResponse = await fetch(quoteUrl, {
          headers: {
            'APCA-API-KEY-ID': credentials.apiKey,
            'APCA-API-SECRET-KEY': credentials.secretKey
          }
        })

        if (!quoteResponse.ok) {
          await updateQueueStatus(supabaseClient, queued.id, 'failed', 'Failed to get quote')
          failed++
          continue
        }

        const quote = await quoteResponse.json()
        const currentPrice = quote.quote?.ap || quote.quote?.bp || 0

        if (currentPrice <= 0) {
          await updateQueueStatus(supabaseClient, queued.id, 'failed', 'Invalid price')
          failed++
          continue
        }

        // Calculate position size
        const { shares, positionValue, multiplier } = calculatePositionSize(
          state.portfolio_value,
          signal.confidence_score,
          currentPrice,
          config
        )

        if (shares <= 0) {
          await updateQueueStatus(supabaseClient, queued.id, 'skipped', 'Position too small')
          skipped++
          continue
        }

        // Check buying power
        if (positionValue > state.buying_power) {
          await updateQueueStatus(supabaseClient, queued.id, 'skipped', 'Insufficient buying power')
          skipped++
          continue
        }

        // Place order with Alpaca
        const orderUrl = `${credentials.baseUrl}/v2/orders`
        const orderRequest = {
          symbol: signal.ticker.toUpperCase(),
          qty: shares,
          side: 'buy',
          type: 'market',
          time_in_force: 'day'
        }

        log.info('Placing order', { requestId, ticker: signal.ticker, shares, positionValue })

        const orderResponse = await fetch(orderUrl, {
          method: 'POST',
          headers: {
            'APCA-API-KEY-ID': credentials.apiKey,
            'APCA-API-SECRET-KEY': credentials.secretKey,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(orderRequest)
        })

        const orderResult = await orderResponse.json()

        if (!orderResponse.ok) {
          log.error('Order failed', { error: orderResult }, { requestId, ticker: signal.ticker })
          await updateQueueStatus(supabaseClient, queued.id, 'failed', orderResult.message || 'Order rejected')
          failed++
          continue
        }

        log.info('Order placed successfully', { requestId, orderId: orderResult.id, ticker: signal.ticker })

        // Calculate stop loss and take profit prices
        const stopLossPrice = currentPrice * (1 - config.default_stop_loss_pct / 100)
        const takeProfitPrice = currentPrice * (1 + config.default_take_profit_pct / 100)

        // Record the position
        const { data: position, error: positionError } = await supabaseClient
          .from('reference_portfolio_positions')
          .insert({
            ticker: signal.ticker.toUpperCase(),
            asset_name: signal.asset_name,
            quantity: shares,
            side: 'long',
            entry_price: currentPrice,
            entry_date: new Date().toISOString(),
            entry_signal_id: signal.id,
            entry_confidence: signal.confidence_score,
            entry_order_id: orderResult.id,
            current_price: currentPrice,
            market_value: positionValue,
            stop_loss_price: stopLossPrice,
            take_profit_price: takeProfitPrice,
            position_size_pct: (positionValue / state.portfolio_value) * 100,
            confidence_weight: multiplier,
            is_open: true
          })
          .select()
          .single()

        if (positionError) {
          log.error('Failed to record position', positionError, { requestId })
        }

        // Record the transaction
        await supabaseClient
          .from('reference_portfolio_transactions')
          .insert({
            position_id: position?.id,
            ticker: signal.ticker.toUpperCase(),
            transaction_type: 'buy',
            quantity: shares,
            price: currentPrice,
            total_value: positionValue,
            signal_id: signal.id,
            signal_confidence: signal.confidence_score,
            signal_type: signal.signal_type,
            executed_at: new Date().toISOString(),
            alpaca_order_id: orderResult.id,
            alpaca_client_order_id: orderResult.client_order_id,
            position_size_pct: (positionValue / state.portfolio_value) * 100,
            confidence_weight: multiplier,
            portfolio_value_at_trade: state.portfolio_value,
            status: 'executed'
          })

        // Update portfolio state
        await supabaseClient
          .from('reference_portfolio_state')
          .update({
            cash: state.cash - positionValue,
            buying_power: state.buying_power - positionValue,
            positions_value: state.positions_value + positionValue,
            open_positions: state.open_positions + 1,
            trades_today: state.trades_today + 1,
            total_trades: state.total_trades + 1,
            last_trade_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          })
          .eq('id', state.id)

        // Update queue status
        await updateQueueStatus(supabaseClient, queued.id, 'executed', null, position?.id)

        // Add to existing tickers to prevent duplicate buys in same batch
        existingTickers.add(signal.ticker.toUpperCase())

        executed++
        results.push({
          ticker: signal.ticker,
          shares,
          price: currentPrice,
          value: positionValue,
          orderId: orderResult.id
        })

        // Small delay between orders
        await new Promise(resolve => setTimeout(resolve, 200))

      } catch (error) {
        log.error('Error processing signal', error, { requestId, ticker: signal.ticker })
        await updateQueueStatus(supabaseClient, queued.id, 'failed', error.message)
        failed++
      }
    }

    log.info('Signal execution completed', { requestId, executed, skipped, failed })

    return new Response(
      JSON.stringify({
        success: true,
        message: `Executed ${executed} trades, skipped ${skipped}, failed ${failed}`,
        summary: { executed, skipped, failed },
        results
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    log.error('Error in handleExecuteSignals', error, { requestId })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}

// Helper to update queue status
async function updateQueueStatus(
  supabaseClient: any,
  queueId: string,
  status: string,
  reason: string | null,
  transactionId?: string
) {
  await supabaseClient
    .from('reference_portfolio_signal_queue')
    .update({
      status,
      skip_reason: reason,
      transaction_id: transactionId || null,
      processed_at: new Date().toISOString()
    })
    .eq('id', queueId)
}

// =============================================================================
// UPDATE POSITIONS - Sync prices and P&L from Alpaca
// =============================================================================
async function handleUpdatePositions(supabaseClient: any, requestId: string) {
  try {
    log.info('Updating positions', { requestId })

    const credentials = getAlpacaCredentials()
    if (!credentials) {
      return new Response(
        JSON.stringify({ error: 'Alpaca credentials not configured' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get open positions from database
    const { data: positions, error: positionsError } = await supabaseClient
      .from('reference_portfolio_positions')
      .select('*')
      .eq('is_open', true)

    if (positionsError) {
      log.error('Failed to fetch positions', positionsError, { requestId })
      return new Response(
        JSON.stringify({ error: 'Failed to fetch positions' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    if (!positions || positions.length === 0) {
      log.info('No positions to update', { requestId })
      return new Response(
        JSON.stringify({ success: true, message: 'No positions to update', updated: 0 }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Fetch positions from Alpaca
    const alpacaPositionsUrl = `${credentials.baseUrl}/v2/positions`
    const alpacaResponse = await fetch(alpacaPositionsUrl, {
      headers: {
        'APCA-API-KEY-ID': credentials.apiKey,
        'APCA-API-SECRET-KEY': credentials.secretKey
      }
    })

    if (!alpacaResponse.ok) {
      log.error('Failed to fetch Alpaca positions', { status: alpacaResponse.status }, { requestId })
      return new Response(
        JSON.stringify({ error: 'Failed to fetch positions from Alpaca' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const alpacaPositions = await alpacaResponse.json()
    const alpacaPositionMap = new Map(alpacaPositions.map((p: any) => [p.symbol, p]))

    let updated = 0
    let totalPositionsValue = 0
    let totalUnrealizedPL = 0

    for (const position of positions) {
      const alpacaPosition = alpacaPositionMap.get(position.ticker.toUpperCase())

      if (alpacaPosition) {
        const currentPrice = parseFloat(alpacaPosition.current_price)
        const marketValue = parseFloat(alpacaPosition.market_value)
        const unrealizedPL = parseFloat(alpacaPosition.unrealized_pl)
        const unrealizedPLPct = parseFloat(alpacaPosition.unrealized_plpc) * 100

        await supabaseClient
          .from('reference_portfolio_positions')
          .update({
            current_price: currentPrice,
            market_value: marketValue,
            unrealized_pl: unrealizedPL,
            unrealized_pl_pct: unrealizedPLPct,
            updated_at: new Date().toISOString()
          })
          .eq('id', position.id)

        totalPositionsValue += marketValue
        totalUnrealizedPL += unrealizedPL
        updated++
      } else {
        // Position not found in Alpaca - might have been closed
        log.warn('Position not found in Alpaca', { requestId, ticker: position.ticker })
      }
    }

    // Update portfolio state
    const { data: state } = await supabaseClient
      .from('reference_portfolio_state')
      .select('*')
      .single()

    if (state) {
      const portfolioValue = state.cash + totalPositionsValue
      const totalReturn = portfolioValue - 100000 // Assuming $100k initial
      const totalReturnPct = (totalReturn / 100000) * 100

      // Check for new peak (for drawdown calculation)
      const peakValue = Math.max(state.peak_portfolio_value || 100000, portfolioValue)
      const currentDrawdown = ((peakValue - portfolioValue) / peakValue) * 100
      const maxDrawdown = Math.max(state.max_drawdown || 0, currentDrawdown)

      await supabaseClient
        .from('reference_portfolio_state')
        .update({
          positions_value: totalPositionsValue,
          portfolio_value: portfolioValue,
          total_return: totalReturn,
          total_return_pct: totalReturnPct,
          peak_portfolio_value: peakValue,
          current_drawdown: currentDrawdown,
          max_drawdown: maxDrawdown,
          last_sync_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        })
        .eq('id', state.id)
    }

    log.info('Positions updated', { requestId, updated, totalPositionsValue, totalUnrealizedPL })

    return new Response(
      JSON.stringify({
        success: true,
        message: `Updated ${updated} positions`,
        summary: { updated, totalPositionsValue, totalUnrealizedPL }
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    log.error('Error in handleUpdatePositions', error, { requestId })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}

// =============================================================================
// TAKE SNAPSHOT - Record daily performance snapshot
// =============================================================================
async function handleTakeSnapshot(supabaseClient: any, requestId: string) {
  try {
    log.info('Taking performance snapshot', { requestId })

    // Get current state
    const { data: state, error: stateError } = await supabaseClient
      .from('reference_portfolio_state')
      .select('*')
      .single()

    if (stateError || !state) {
      return new Response(
        JSON.stringify({ error: 'Portfolio state not found' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get previous snapshot for day return calculation
    const today = new Date().toISOString().split('T')[0]
    const { data: lastSnapshot } = await supabaseClient
      .from('reference_portfolio_snapshots')
      .select('*')
      .lt('snapshot_date', today)
      .order('snapshot_date', { ascending: false })
      .limit(1)
      .single()

    const previousValue = lastSnapshot?.portfolio_value || 100000
    const dayReturn = state.portfolio_value - previousValue
    const dayReturnPct = (dayReturn / previousValue) * 100

    const cumulativeReturn = state.portfolio_value - 100000
    const cumulativeReturnPct = (cumulativeReturn / 100000) * 100

    // Fetch S&P 500 benchmark (SPY) for comparison
    let benchmarkValue = null
    let benchmarkReturn = null
    let benchmarkReturnPct = null
    let alpha = null

    const credentials = getAlpacaCredentials()
    if (credentials) {
      try {
        const spyUrl = `${credentials.baseUrl}/v2/stocks/SPY/quotes/latest`
        const spyResponse = await fetch(spyUrl, {
          headers: {
            'APCA-API-KEY-ID': credentials.apiKey,
            'APCA-API-SECRET-KEY': credentials.secretKey
          }
        })

        if (spyResponse.ok) {
          const spyQuote = await spyResponse.json()
          const spyPrice = spyQuote.quote?.ap || spyQuote.quote?.bp
          if (spyPrice) {
            // Simple benchmark tracking (would need historical data for accurate returns)
            benchmarkValue = spyPrice
            // TODO: Calculate actual benchmark returns from historical data
          }
        }
      } catch (e) {
        log.warn('Failed to fetch benchmark data', { error: e.message })
      }
    }

    // Calculate win rate
    const totalClosedTrades = state.winning_trades + state.losing_trades
    const winRate = totalClosedTrades > 0 ? (state.winning_trades / totalClosedTrades) * 100 : 0

    // Insert snapshot
    const { data: snapshot, error: snapshotError } = await supabaseClient
      .from('reference_portfolio_snapshots')
      .upsert({
        snapshot_date: today,
        snapshot_time: new Date().toISOString(),
        portfolio_value: state.portfolio_value,
        cash: state.cash,
        positions_value: state.positions_value,
        day_return: dayReturn,
        day_return_pct: dayReturnPct,
        cumulative_return: cumulativeReturn,
        cumulative_return_pct: cumulativeReturnPct,
        open_positions: state.open_positions,
        total_trades: state.total_trades,
        sharpe_ratio: state.sharpe_ratio,
        max_drawdown: state.max_drawdown,
        current_drawdown: state.current_drawdown,
        win_rate: winRate,
        benchmark_value: benchmarkValue,
        benchmark_return: benchmarkReturn,
        benchmark_return_pct: benchmarkReturnPct,
        alpha: alpha
      }, { onConflict: 'snapshot_date' })
      .select()
      .single()

    if (snapshotError) {
      log.error('Failed to save snapshot', snapshotError, { requestId })
      return new Response(
        JSON.stringify({ error: 'Failed to save snapshot' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    log.info('Snapshot saved', { requestId, date: today, portfolioValue: state.portfolio_value })

    return new Response(
      JSON.stringify({
        success: true,
        snapshot: {
          date: today,
          portfolio_value: state.portfolio_value,
          day_return: dayReturn,
          day_return_pct: dayReturnPct,
          cumulative_return_pct: cumulativeReturnPct
        }
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    log.error('Error in handleTakeSnapshot', error, { requestId })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}

// =============================================================================
// RESET DAILY TRADES - Called at market open
// =============================================================================
async function handleResetDailyTrades(supabaseClient: any, requestId: string) {
  try {
    await supabaseClient
      .from('reference_portfolio_state')
      .update({
        trades_today: 0,
        day_return: 0,
        day_return_pct: 0,
        updated_at: new Date().toISOString()
      })

    log.info('Daily trades reset', { requestId })

    return new Response(
      JSON.stringify({ success: true, message: 'Daily trades reset' }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    log.error('Error in handleResetDailyTrades', error, { requestId })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}
