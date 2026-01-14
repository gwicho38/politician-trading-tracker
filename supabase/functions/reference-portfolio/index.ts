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
function getAlpacaCredentials(): { apiKey: string; secretKey: string; baseUrl: string; dataUrl: string } | null {
  const apiKey = Deno.env.get('ALPACA_API_KEY')
  const secretKey = Deno.env.get('ALPACA_SECRET_KEY')
  const paper = Deno.env.get('ALPACA_PAPER') === 'true'
  const baseUrl = Deno.env.get('ALPACA_BASE_URL') || (paper ? 'https://paper-api.alpaca.markets' : 'https://api.alpaca.markets')
  // Market data API is separate from trading API
  const dataUrl = 'https://data.alpaca.markets'

  if (!apiKey || !secretKey) {
    return null
  }

  return { apiKey, secretKey, baseUrl, dataUrl }
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
      case 'check-exits':
        response = await handleCheckExits(supabaseClient, requestId)
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
// GET PERFORMANCE - Fetch portfolio history directly from Alpaca API
// =============================================================================
async function handleGetPerformance(supabaseClient: any, requestId: string, bodyParams: any) {
  try {
    const timeframe = bodyParams.timeframe || '1m' // 1d, 1w, 1m, 3m, ytd, 1y

    // Map our timeframe to Alpaca's period format
    let alpacaPeriod: string
    let alpacaTimeframe: string

    switch (timeframe) {
      case '1d':
        alpacaPeriod = '1D'
        alpacaTimeframe = '15Min'
        break
      case '1w':
        alpacaPeriod = '1W'
        alpacaTimeframe = '1H'
        break
      case '1m':
        alpacaPeriod = '1M'
        alpacaTimeframe = '1D'
        break
      case '3m':
        alpacaPeriod = '3M'
        alpacaTimeframe = '1D'
        break
      case 'ytd':
        // Calculate days since Jan 1
        const now = new Date()
        const startOfYear = new Date(now.getFullYear(), 0, 1)
        const daysSinceYearStart = Math.ceil((now.getTime() - startOfYear.getTime()) / (1000 * 60 * 60 * 24))
        alpacaPeriod = `${daysSinceYearStart}D`
        alpacaTimeframe = '1D'
        break
      case '1y':
        alpacaPeriod = '1A'
        alpacaTimeframe = '1D'
        break
      default:
        alpacaPeriod = '1M'
        alpacaTimeframe = '1D'
    }

    const credentials = getAlpacaCredentials()
    if (!credentials) {
      log.error('Alpaca credentials not configured', null, { requestId })
      return new Response(
        JSON.stringify({ error: 'Alpaca credentials not configured' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Fetch portfolio history from Alpaca
    const historyUrl = `${credentials.baseUrl}/v2/account/portfolio/history?period=${alpacaPeriod}&timeframe=${alpacaTimeframe}&extended_hours=true`
    log.info('Fetching Alpaca portfolio history', { requestId, url: historyUrl, period: alpacaPeriod, timeframe: alpacaTimeframe })

    const response = await fetch(historyUrl, {
      headers: {
        'APCA-API-KEY-ID': credentials.apiKey,
        'APCA-API-SECRET-KEY': credentials.secretKey
      }
    })

    if (!response.ok) {
      const errorText = await response.text()
      log.error('Alpaca portfolio history failed', { status: response.status, error: errorText }, { requestId })
      return new Response(
        JSON.stringify({ error: `Alpaca API error: ${response.status}` }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const alpacaHistory = await response.json()

    // Get config for initial capital
    const { data: config } = await supabaseClient
      .from('reference_portfolio_config')
      .select('initial_capital')
      .single()
    const initialCapital = config?.initial_capital || 100000

    // Transform Alpaca response to our snapshot format
    const snapshots = []
    const timestamps = alpacaHistory.timestamp || []
    const equities = alpacaHistory.equity || []
    const profitLoss = alpacaHistory.profit_loss || []
    const profitLossPct = alpacaHistory.profit_loss_pct || []
    const baseValue = alpacaHistory.base_value || initialCapital

    for (let i = 0; i < timestamps.length; i++) {
      const timestamp = timestamps[i]
      const equity = equities[i]
      const pl = profitLoss[i]
      const plPct = profitLossPct[i]

      // Skip null or zero values (market closed periods or before account was funded)
      if (equity === null || equity === 0) continue

      const date = new Date(timestamp * 1000) // Alpaca returns epoch seconds
      const snapshotDate = date.toISOString().split('T')[0]

      // Calculate day return (difference from previous point)
      const prevEquity = i > 0 ? equities[i - 1] : baseValue
      const dayReturn = prevEquity !== null ? equity - prevEquity : 0
      const dayReturnPct = prevEquity !== null && prevEquity > 0 ? (dayReturn / prevEquity) * 100 : 0

      // Calculate cumulative return from initial capital
      const cumulativeReturn = equity - initialCapital
      const cumulativeReturnPct = (cumulativeReturn / initialCapital) * 100

      snapshots.push({
        id: `alpaca-${timestamp}`,
        snapshot_date: snapshotDate,
        snapshot_time: date.toISOString(),
        portfolio_value: equity,
        cash: null, // Not provided by Alpaca history
        positions_value: null, // Not provided by Alpaca history
        day_return: dayReturn,
        day_return_pct: dayReturnPct,
        cumulative_return: cumulativeReturn,
        cumulative_return_pct: cumulativeReturnPct,
        // Alpaca's P&L is relative to base_value (account value at start of period)
        alpaca_pl: pl,
        alpaca_pl_pct: plPct !== null ? plPct * 100 : null, // Convert to percentage
        open_positions: null,
        total_trades: null,
        sharpe_ratio: null,
        max_drawdown: null,
        current_drawdown: null,
        win_rate: null,
        benchmark_value: null,
        benchmark_return: null,
        benchmark_return_pct: null,
        alpha: null
      })
    }

    log.info('Alpaca portfolio history fetched', {
      requestId,
      dataPoints: snapshots.length,
      baseValue,
      latestEquity: equities[equities.length - 1]
    })

    return new Response(
      JSON.stringify({
        success: true,
        timeframe,
        source: 'alpaca',
        base_value: baseValue,
        initial_capital: initialCapital,
        snapshots,
        count: snapshots.length
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
        // Get current price from Alpaca (market data uses separate API)
        const quoteUrl = `${credentials.dataUrl}/v2/stocks/${signal.ticker}/quotes/latest`
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

    // Get config for initial_capital
    const { data: config } = await supabaseClient
      .from('reference_portfolio_config')
      .select('initial_capital')
      .single()

    const initialCapital = config?.initial_capital || 100000

    // Get open positions from database FIRST (this is our source of truth for position count)
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

    // Always count open positions from database (fix for position count mismatch)
    const openPositionsCount = positions?.length || 0

    if (!positions || positions.length === 0) {
      // No positions - update state to reflect this
      await supabaseClient
        .from('reference_portfolio_state')
        .update({
          open_positions: 0,
          positions_value: 0,
          last_sync_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        })

      log.info('No positions to update', { requestId })
      return new Response(
        JSON.stringify({ success: true, message: 'No positions to update', updated: 0 }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Calculate positions value from database as fallback
    let totalPositionsValue = 0
    let totalUnrealizedPL = 0
    let updated = 0

    // First, calculate from database positions (as fallback)
    for (const position of positions) {
      const marketValue = position.market_value || (position.quantity * (position.current_price || position.entry_price))
      totalPositionsValue += marketValue
      totalUnrealizedPL += position.unrealized_pl || 0
    }

    const dbPositionsValue = totalPositionsValue // Save for fallback

    // Try to update from Alpaca if credentials available
    const credentials = getAlpacaCredentials()
    let alpacaSyncSuccess = false

    if (credentials) {
      try {
        const alpacaPositionsUrl = `${credentials.baseUrl}/v2/positions`
        const alpacaResponse = await fetch(alpacaPositionsUrl, {
          headers: {
            'APCA-API-KEY-ID': credentials.apiKey,
            'APCA-API-SECRET-KEY': credentials.secretKey
          }
        })

        if (alpacaResponse.ok) {
          const alpacaPositions = await alpacaResponse.json()
          const alpacaPositionMap = new Map(alpacaPositions.map((p: any) => [p.symbol, p]))

          // Reset totals for Alpaca data
          totalPositionsValue = 0
          totalUnrealizedPL = 0

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
              alpacaSyncSuccess = true
            } else {
              // Position not in Alpaca - use database value
              const dbMarketValue = position.market_value || (position.quantity * (position.current_price || position.entry_price))
              totalPositionsValue += dbMarketValue
              totalUnrealizedPL += position.unrealized_pl || 0
              log.warn('Position not found in Alpaca, using DB value', { requestId, ticker: position.ticker, value: dbMarketValue })
            }
          }
        } else {
          log.warn('Alpaca API failed, using database values', { requestId, status: alpacaResponse.status })
          totalPositionsValue = dbPositionsValue
        }
      } catch (alpacaError) {
        log.warn('Alpaca sync failed, using database values', { requestId, error: alpacaError.message })
        totalPositionsValue = dbPositionsValue
      }
    } else {
      log.info('No Alpaca credentials, using database values', { requestId })
    }

    // Update portfolio state with correct position count and value
    const { data: state } = await supabaseClient
      .from('reference_portfolio_state')
      .select('*')
      .single()

    if (state) {
      const portfolioValue = state.cash + totalPositionsValue
      const totalReturn = portfolioValue - initialCapital
      const totalReturnPct = (totalReturn / initialCapital) * 100

      // Check for new peak (for drawdown calculation)
      const peakValue = Math.max(state.peak_portfolio_value || initialCapital, portfolioValue)
      const currentDrawdown = ((peakValue - portfolioValue) / peakValue) * 100
      const maxDrawdown = Math.max(state.max_drawdown || 0, currentDrawdown)

      // Calculate day return from previous day's snapshot
      const today = new Date().toISOString().split('T')[0]
      const { data: lastSnapshot } = await supabaseClient
        .from('reference_portfolio_snapshots')
        .select('portfolio_value')
        .lt('snapshot_date', today)
        .order('snapshot_date', { ascending: false })
        .limit(1)
        .single()

      // Use previous snapshot value or initial capital as baseline
      const previousValue = lastSnapshot?.portfolio_value || initialCapital
      const dayReturn = portfolioValue - previousValue
      const dayReturnPct = (dayReturn / previousValue) * 100

      await supabaseClient
        .from('reference_portfolio_state')
        .update({
          positions_value: totalPositionsValue,
          portfolio_value: portfolioValue,
          total_return: totalReturn,
          total_return_pct: totalReturnPct,
          day_return: Math.round(dayReturn * 100) / 100,
          day_return_pct: Math.round(dayReturnPct * 10000) / 10000,
          peak_portfolio_value: peakValue,
          current_drawdown: currentDrawdown,
          max_drawdown: maxDrawdown,
          open_positions: openPositionsCount, // FIX: Always update from actual position count
          last_sync_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        })
        .eq('id', state.id)
    }

    log.info('Positions updated', {
      requestId,
      updated,
      openPositionsCount,
      totalPositionsValue,
      totalUnrealizedPL,
      alpacaSyncSuccess
    })

    return new Response(
      JSON.stringify({
        success: true,
        message: `Updated ${updated} positions`,
        summary: {
          updated,
          openPositionsCount,
          totalPositionsValue,
          totalUnrealizedPL,
          alpacaSyncSuccess
        }
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
// SYNC POSITIONS WITH ALPACA - Helper function for position value updates
// =============================================================================
async function syncPositionsWithAlpaca(supabaseClient: any, requestId: string, initialCapital: number) {
  try {
    // Get open positions from database
    const { data: positions, error: positionsError } = await supabaseClient
      .from('reference_portfolio_positions')
      .select('*')
      .eq('is_open', true)

    if (positionsError) {
      log.error('Failed to fetch positions for sync', positionsError, { requestId })
      return
    }

    const openPositionsCount = positions?.length || 0

    if (!positions || positions.length === 0) {
      // No positions - update state to reflect this
      await supabaseClient
        .from('reference_portfolio_state')
        .update({
          open_positions: 0,
          positions_value: 0,
          last_sync_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        })
      log.info('No positions to sync', { requestId })
      return
    }

    // Calculate positions value from database as fallback
    let totalPositionsValue = 0
    let totalUnrealizedPL = 0

    for (const position of positions) {
      const marketValue = position.market_value || (position.quantity * (position.current_price || position.entry_price))
      totalPositionsValue += marketValue
      totalUnrealizedPL += position.unrealized_pl || 0
    }

    const dbPositionsValue = totalPositionsValue

    // Try to update from Alpaca if credentials available
    const credentials = getAlpacaCredentials()

    if (credentials) {
      try {
        const alpacaPositionsUrl = `${credentials.baseUrl}/v2/positions`
        const alpacaResponse = await fetch(alpacaPositionsUrl, {
          headers: {
            'APCA-API-KEY-ID': credentials.apiKey,
            'APCA-API-SECRET-KEY': credentials.secretKey
          }
        })

        if (alpacaResponse.ok) {
          const alpacaPositions = await alpacaResponse.json()
          const alpacaPositionMap = new Map(alpacaPositions.map((p: any) => [p.symbol, p]))

          // Reset totals for Alpaca data
          totalPositionsValue = 0
          totalUnrealizedPL = 0

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
            } else {
              // Position not in Alpaca - use database value
              const dbMarketValue = position.market_value || (position.quantity * (position.current_price || position.entry_price))
              totalPositionsValue += dbMarketValue
              totalUnrealizedPL += position.unrealized_pl || 0
            }
          }
        } else {
          log.warn('Alpaca API failed during sync, using database values', { requestId, status: alpacaResponse.status })
          totalPositionsValue = dbPositionsValue
        }
      } catch (alpacaError) {
        log.warn('Alpaca sync failed, using database values', { requestId, error: alpacaError.message })
        totalPositionsValue = dbPositionsValue
      }
    } else {
      log.info('No Alpaca credentials, using database values', { requestId })
    }

    // Update portfolio state with correct position count and value
    const { data: state } = await supabaseClient
      .from('reference_portfolio_state')
      .select('*')
      .single()

    if (state) {
      const portfolioValue = state.cash + totalPositionsValue
      const totalReturn = portfolioValue - initialCapital
      const totalReturnPct = (totalReturn / initialCapital) * 100

      // Check for new peak (for drawdown calculation)
      const peakValue = Math.max(state.peak_portfolio_value || initialCapital, portfolioValue)
      const currentDrawdown = ((peakValue - portfolioValue) / peakValue) * 100
      const maxDrawdown = Math.max(state.max_drawdown || 0, currentDrawdown)

      // Calculate day return from previous day's snapshot
      const today = new Date().toISOString().split('T')[0]
      const { data: lastSnapshot } = await supabaseClient
        .from('reference_portfolio_snapshots')
        .select('portfolio_value')
        .lt('snapshot_date', today)
        .order('snapshot_date', { ascending: false })
        .limit(1)
        .single()

      const previousValue = lastSnapshot?.portfolio_value || initialCapital
      const dayReturn = portfolioValue - previousValue
      const dayReturnPct = (dayReturn / previousValue) * 100

      await supabaseClient
        .from('reference_portfolio_state')
        .update({
          positions_value: totalPositionsValue,
          portfolio_value: portfolioValue,
          total_return: totalReturn,
          total_return_pct: totalReturnPct,
          day_return: Math.round(dayReturn * 100) / 100,
          day_return_pct: Math.round(dayReturnPct * 10000) / 10000,
          peak_portfolio_value: peakValue,
          current_drawdown: currentDrawdown,
          max_drawdown: maxDrawdown,
          open_positions: openPositionsCount,
          last_sync_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        })
        .eq('id', state.id)

      log.info('Positions synced for snapshot', {
        requestId,
        openPositionsCount,
        totalPositionsValue,
        portfolioValue,
        totalReturn,
        totalReturnPct,
        dayReturn,
        dayReturnPct
      })
    }
  } catch (error) {
    log.error('Error syncing positions', error, { requestId })
  }
}

// =============================================================================
// TAKE SNAPSHOT - Record daily performance snapshot
// =============================================================================
async function handleTakeSnapshot(supabaseClient: any, requestId: string) {
  try {
    log.info('Taking performance snapshot', { requestId })

    // First, get the config to know initial_capital
    const { data: config, error: configError } = await supabaseClient
      .from('reference_portfolio_config')
      .select('*')
      .single()

    if (configError || !config) {
      return new Response(
        JSON.stringify({ error: 'Portfolio config not found' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const initialCapital = config.initial_capital || 100000

    // Sync positions with Alpaca BEFORE taking snapshot
    log.info('Syncing positions before snapshot', { requestId })
    await syncPositionsWithAlpaca(supabaseClient, requestId, initialCapital)

    // Get current state (now freshly updated)
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

    const previousValue = lastSnapshot?.portfolio_value || initialCapital
    const dayReturn = state.portfolio_value - previousValue
    const dayReturnPct = (dayReturn / previousValue) * 100

    const cumulativeReturn = state.portfolio_value - initialCapital
    const cumulativeReturnPct = (cumulativeReturn / initialCapital) * 100

    // Fetch S&P 500 benchmark (SPY) for comparison
    let benchmarkValue = null
    let benchmarkReturn = null
    let benchmarkReturnPct = null
    let alpha = null

    const credentials = getAlpacaCredentials()
    if (credentials) {
      try {
        const spyUrl = `${credentials.dataUrl}/v2/stocks/SPY/quotes/latest`
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

    // Calculate Sharpe ratio from recent daily returns (last 30 days)
    let sharpeRatio = state.sharpe_ratio
    const { data: recentSnapshots } = await supabaseClient
      .from('reference_portfolio_snapshots')
      .select('day_return_pct')
      .order('snapshot_date', { ascending: false })
      .limit(30)

    if (recentSnapshots && recentSnapshots.length >= 5) {
      // Get daily return percentages (filter out nulls and zeros from non-trading days)
      const dailyReturns = recentSnapshots
        .map((s: any) => s.day_return_pct)
        .filter((r: number | null) => r !== null && r !== undefined)

      if (dailyReturns.length >= 5) {
        // Calculate mean daily return
        const meanReturn = dailyReturns.reduce((sum: number, r: number) => sum + r, 0) / dailyReturns.length

        // Calculate standard deviation of daily returns
        const squaredDiffs = dailyReturns.map((r: number) => Math.pow(r - meanReturn, 2))
        const variance = squaredDiffs.reduce((sum: number, d: number) => sum + d, 0) / dailyReturns.length
        const stdDev = Math.sqrt(variance)

        // Sharpe ratio: (mean return - risk free rate) / std dev
        // Annualized: multiply by sqrt(252) for daily returns
        // Using 0 as risk-free rate for simplicity
        if (stdDev > 0) {
          const dailySharpe = meanReturn / stdDev
          sharpeRatio = Math.round(dailySharpe * Math.sqrt(252) * 10000) / 10000  // Annualized
        } else {
          sharpeRatio = meanReturn > 0 ? 3.0 : 0  // Cap at 3.0 if no volatility
        }

        log.info('Calculated Sharpe ratio', {
          requestId,
          sharpeRatio,
          meanReturn: Math.round(meanReturn * 10000) / 10000,
          stdDev: Math.round(stdDev * 10000) / 10000,
          sampleSize: dailyReturns.length
        })

        // Update state with new Sharpe ratio
        await supabaseClient
          .from('reference_portfolio_state')
          .update({
            sharpe_ratio: sharpeRatio,
            updated_at: new Date().toISOString()
          })
          .eq('id', state.id)
      }
    }

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

// =============================================================================
// CHECK EXITS - Monitor positions for stop-loss and take-profit triggers
// =============================================================================
async function handleCheckExits(supabaseClient: any, requestId: string) {
  try {
    log.info('Checking exit conditions', { requestId })

    // Get config
    const { data: config } = await supabaseClient
      .from('reference_portfolio_config')
      .select('*')
      .single()

    if (!config?.is_active) {
      return new Response(
        JSON.stringify({ success: true, message: 'Trading is disabled', closed: 0 }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get state
    const { data: state } = await supabaseClient
      .from('reference_portfolio_state')
      .select('*')
      .single()

    if (!state) {
      return new Response(
        JSON.stringify({ error: 'Portfolio state not found' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get all open positions with stop-loss and take-profit prices
    const { data: positions, error: posError } = await supabaseClient
      .from('reference_portfolio_positions')
      .select('*')
      .eq('is_open', true)

    if (posError) {
      log.error('Failed to fetch positions', posError, { requestId })
      return new Response(
        JSON.stringify({ error: 'Failed to fetch positions' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    if (!positions || positions.length === 0) {
      return new Response(
        JSON.stringify({ success: true, message: 'No open positions', closed: 0 }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get Alpaca credentials
    const credentials = getAlpacaCredentials()
    if (!credentials) {
      return new Response(
        JSON.stringify({ error: 'Alpaca credentials not configured' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    let closed = 0
    let wins = 0
    let losses = 0
    const results: any[] = []

    for (const position of positions) {
      try {
        // Get current price from Alpaca
        const quoteUrl = `${credentials.dataUrl}/v2/stocks/${position.ticker}/quotes/latest`
        const quoteResponse = await fetch(quoteUrl, {
          headers: {
            'APCA-API-KEY-ID': credentials.apiKey,
            'APCA-API-SECRET-KEY': credentials.secretKey
          }
        })

        if (!quoteResponse.ok) {
          log.warn('Failed to get quote', { requestId, ticker: position.ticker })
          continue
        }

        const quote = await quoteResponse.json()
        const currentPrice = quote.quote?.bp || quote.quote?.ap || position.current_price

        if (!currentPrice || currentPrice <= 0) continue

        // Check exit conditions
        let exitReason: string | null = null

        if (position.stop_loss_price && currentPrice <= position.stop_loss_price) {
          exitReason = 'stop_loss'
        } else if (position.take_profit_price && currentPrice >= position.take_profit_price) {
          exitReason = 'take_profit'
        }

        if (!exitReason) continue

        log.info('Exit triggered', {
          requestId,
          ticker: position.ticker,
          exitReason,
          currentPrice,
          stopLoss: position.stop_loss_price,
          takeProfit: position.take_profit_price
        })

        // Place sell order with Alpaca
        const orderUrl = `${credentials.baseUrl}/v2/orders`
        const orderResponse = await fetch(orderUrl, {
          method: 'POST',
          headers: {
            'APCA-API-KEY-ID': credentials.apiKey,
            'APCA-API-SECRET-KEY': credentials.secretKey,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            symbol: position.ticker.toUpperCase(),
            qty: position.quantity,
            side: 'sell',
            type: 'market',
            time_in_force: 'day'
          })
        })

        const orderResult = await orderResponse.json()

        if (!orderResponse.ok) {
          log.error('Sell order failed', { error: orderResult }, { requestId, ticker: position.ticker })
          continue
        }

        log.info('Sell order placed', { requestId, orderId: orderResult.id, ticker: position.ticker })

        // Calculate realized P&L
        const exitValue = currentPrice * position.quantity
        const entryValue = position.entry_price * position.quantity
        const realizedPL = exitValue - entryValue
        const realizedPLPct = ((currentPrice - position.entry_price) / position.entry_price) * 100

        // Determine if win or loss
        const isWin = realizedPL > 0
        if (isWin) wins++
        else losses++

        // Update position as closed
        await supabaseClient
          .from('reference_portfolio_positions')
          .update({
            is_open: false,
            exit_price: currentPrice,
            exit_date: new Date().toISOString(),
            exit_reason: exitReason,
            exit_order_id: orderResult.id,
            realized_pl: realizedPL,
            realized_pl_pct: realizedPLPct,
            current_price: currentPrice,
            market_value: exitValue,
            updated_at: new Date().toISOString()
          })
          .eq('id', position.id)

        // Record the transaction
        await supabaseClient
          .from('reference_portfolio_transactions')
          .insert({
            position_id: position.id,
            ticker: position.ticker,
            transaction_type: 'sell',
            quantity: position.quantity,
            price: currentPrice,
            total_value: exitValue,
            executed_at: new Date().toISOString(),
            alpaca_order_id: orderResult.id,
            exit_reason: exitReason,
            realized_pl: realizedPL,
            realized_pl_pct: realizedPLPct,
            portfolio_value_at_trade: state.portfolio_value,
            status: 'executed'
          })

        // Update portfolio state
        await supabaseClient
          .from('reference_portfolio_state')
          .update({
            cash: state.cash + exitValue,
            buying_power: state.buying_power + exitValue,
            positions_value: state.positions_value - position.market_value,
            open_positions: state.open_positions - 1,
            winning_trades: isWin ? state.winning_trades + 1 : state.winning_trades,
            losing_trades: !isWin ? state.losing_trades + 1 : state.losing_trades,
            trades_today: state.trades_today + 1,
            total_trades: state.total_trades + 1,
            last_trade_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          })
          .eq('id', state.id)

        // Update state object for next iteration
        state.cash += exitValue
        state.buying_power += exitValue
        state.positions_value -= position.market_value
        state.open_positions -= 1
        if (isWin) state.winning_trades += 1
        else state.losing_trades += 1
        state.trades_today += 1
        state.total_trades += 1

        closed++
        results.push({
          ticker: position.ticker,
          exitReason,
          exitPrice: currentPrice,
          entryPrice: position.entry_price,
          quantity: position.quantity,
          realizedPL,
          realizedPLPct: Math.round(realizedPLPct * 100) / 100,
          isWin
        })

        // Small delay between orders
        await new Promise(resolve => setTimeout(resolve, 200))

      } catch (error) {
        log.error('Error checking exit for position', error, { requestId, ticker: position.ticker })
      }
    }

    // Update win rate in state
    if (closed > 0) {
      const totalClosed = state.winning_trades + state.losing_trades
      const winRate = totalClosed > 0 ? (state.winning_trades / totalClosed) * 100 : 0

      await supabaseClient
        .from('reference_portfolio_state')
        .update({
          win_rate: Math.round(winRate * 100) / 100,
          updated_at: new Date().toISOString()
        })
        .eq('id', state.id)
    }

    log.info('Exit check completed', { requestId, checked: positions.length, closed, wins, losses })

    return new Response(
      JSON.stringify({
        success: true,
        message: `Closed ${closed} positions (${wins} wins, ${losses} losses)`,
        summary: { checked: positions.length, closed, wins, losses },
        results
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    log.error('Error in handleCheckExits', error, { requestId })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}
