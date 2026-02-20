import { createClient } from 'supabase'
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { corsHeaders } from '../_shared/cors.ts'

// TODO: Review - Structured logging utility object with info, error, and warn methods
// Logs JSON-formatted messages with timestamp, service name, and optional metadata
const log = {
  // TODO: Review - Log info level messages with optional metadata
  info: (message: string, metadata?: any) => {
    console.log(JSON.stringify({
      level: 'INFO',
      timestamp: new Date().toISOString(),
      service: 'reference-portfolio',
      message,
      ...metadata
    }))
  },
  // TODO: Review - Log error level messages with error details and stack trace
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
  // TODO: Review - Log warning level messages with optional metadata
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
  // Extended hours + crypto config
  extended_hours_enabled?: boolean
  extended_hours_limit_buffer_pct?: number
  crypto_enabled?: boolean
  crypto_base_position_size_pct?: number
  crypto_max_positions?: number
  crypto_stop_loss_pct?: number
  crypto_take_profit_pct?: number
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

// TODO: Review - Retrieves Alpaca API credentials from environment variables
// Returns null if credentials are not configured, otherwise returns apiKey, secretKey, baseUrl, and dataUrl
function getAlpacaCredentials(tradingMode: string = 'paper'): { apiKey: string; secretKey: string; baseUrl: string; dataUrl: string } | null {
  const apiKey = Deno.env.get('ALPACA_API_KEY')
  const secretKey = Deno.env.get('ALPACA_SECRET_KEY')
  const paper = tradingMode === 'paper'
  const baseUrl = Deno.env.get('ALPACA_BASE_URL') || (paper ? 'https://paper-api.alpaca.markets' : 'https://api.alpaca.markets')
  // Market data API is separate from trading API
  const dataUrl = 'https://data.alpaca.markets'

  if (!apiKey || !secretKey) {
    return null
  }

  return { apiKey, secretKey, baseUrl, dataUrl }
}

// TODO: Review - Calculates position size based on portfolio value, signal confidence, and config constraints
// Returns shares count, position value, and confidence multiplier applied
function calculatePositionSize(
  portfolioValue: number,
  confidence: number,
  currentPrice: number,
  config: ReferencePortfolioConfig,
  assetType: string = 'stock'
): { shares: number; positionValue: number; multiplier: number } {
  // Use crypto-specific base size if applicable
  const basePct = assetType === 'crypto'
    ? (config.crypto_base_position_size_pct || 0.5)
    : config.base_position_size_pct

  const baseSize = portfolioValue * (basePct / 100)

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

  // Fractional for crypto, integer for stocks
  const shares = assetType === 'crypto'
    ? parseFloat((positionValue / currentPrice).toFixed(8))
    : Math.floor(positionValue / currentPrice)

  return { shares, positionValue: shares * currentPrice, multiplier }
}

// Market status from Alpaca Clock API — handles DST, half-days, holidays automatically
interface MarketStatus {
  isOpen: boolean           // true during regular hours (9:30 AM - 4:00 PM ET)
  isExtendedHours: boolean  // true during pre-market (4 AM-9:30 AM) or post-market (4 PM-8 PM ET)
  nextOpen: string
  nextClose: string
}

async function getMarketStatus(credentials: ReturnType<typeof getAlpacaCredentials>): Promise<MarketStatus> {
  if (!credentials) {
    return { isOpen: false, isExtendedHours: false, nextOpen: '', nextClose: '' }
  }

  try {
    const response = await fetch(`${credentials.baseUrl}/v2/clock`, {
      headers: {
        'APCA-API-KEY-ID': credentials.apiKey,
        'APCA-API-SECRET-KEY': credentials.secretKey,
      }
    })

    if (!response.ok) {
      log.error('Failed to fetch market clock', { status: response.status })
      return { isOpen: false, isExtendedHours: false, nextOpen: '', nextClose: '' }
    }

    const clock = await response.json()
    // clock: { timestamp, is_open, next_open, next_close }

    let isExtendedHours = false
    if (!clock.is_open) {
      const now = new Date(clock.timestamp)
      const dayOfWeek = now.getUTCDay()
      const isWeekday = dayOfWeek >= 1 && dayOfWeek <= 5

      if (isWeekday) {
        const nextOpen = new Date(clock.next_open)
        const nextClose = new Date(clock.next_close)
        const hoursUntilOpen = (nextOpen.getTime() - now.getTime()) / (1000 * 60 * 60)
        const hoursSinceClose = nextClose < now ? (now.getTime() - nextClose.getTime()) / (1000 * 60 * 60) : -1

        // Pre-market: within 5.5 hours of open (4 AM ET = 5.5 hrs before 9:30 AM)
        // Post-market: within 4 hours of close (8 PM ET = 4 hrs after 4 PM)
        isExtendedHours = (hoursUntilOpen > 0 && hoursUntilOpen <= 5.5) ||
                          (hoursSinceClose >= 0 && hoursSinceClose <= 4)
      }
    }

    return {
      isOpen: clock.is_open,
      isExtendedHours,
      nextOpen: clock.next_open,
      nextClose: clock.next_close,
    }
  } catch (error) {
    log.error('Market clock request failed', { error })
    return { isOpen: false, isExtendedHours: false, nextOpen: '', nextClose: '' }
  }
}

// Backward-compatible wrapper for callers that just need a boolean
async function isMarketOpenAsync(credentials: ReturnType<typeof getAlpacaCredentials>): Promise<boolean> {
  const status = await getMarketStatus(credentials)
  return status.isOpen
}

// Fetch latest bid/ask quote from Alpaca (stocks or crypto)
async function fetchLatestQuote(
  ticker: string,
  credentials: ReturnType<typeof getAlpacaCredentials>
): Promise<{ bidPrice: number; askPrice: number }> {
  if (!credentials) throw new Error('Alpaca credentials not configured')

  const isCrypto = ticker.includes('/')
  const endpoint = isCrypto
    ? `${credentials.dataUrl}/v1beta3/crypto/us/latest/quotes?symbols=${encodeURIComponent(ticker)}`
    : `${credentials.dataUrl}/v2/stocks/${ticker}/quotes/latest`

  const response = await fetch(endpoint, {
    headers: {
      'APCA-API-KEY-ID': credentials.apiKey,
      'APCA-API-SECRET-KEY': credentials.secretKey,
    }
  })

  if (!response.ok) {
    throw new Error(`Quote fetch failed for ${ticker}: ${response.status}`)
  }

  const data = await response.json()

  if (isCrypto) {
    const quoteData = data.quotes?.[ticker]
    return { bidPrice: quoteData?.bp || 0, askPrice: quoteData?.ap || 0 }
  }

  return { bidPrice: data.quote?.bp || 0, askPrice: data.quote?.ap || 0 }
}

// Build order request with appropriate type/TIF based on market status and asset type
interface OrderRequest {
  symbol: string
  qty: string | number
  side: 'buy' | 'sell'
  type: 'market' | 'limit'
  time_in_force: 'day' | 'gtc'
  limit_price?: string
  extended_hours?: boolean
}

async function buildOrderRequest(
  ticker: string,
  qty: number,
  side: 'buy' | 'sell',
  assetType: string,
  marketStatus: MarketStatus,
  credentials: ReturnType<typeof getAlpacaCredentials>,
  config: ReferencePortfolioConfig
): Promise<OrderRequest> {
  // Crypto: always GTC, market order, fractional qty
  if (assetType === 'crypto') {
    return {
      symbol: ticker,
      qty: qty.toFixed(8).replace(/\.?0+$/, ''),
      side,
      type: 'market',
      time_in_force: 'gtc',
    }
  }

  // Regular market hours: market order, day TIF
  if (marketStatus.isOpen) {
    return {
      symbol: ticker,
      qty: Math.floor(qty),
      side,
      type: 'market',
      time_in_force: 'day',
    }
  }

  // Extended hours: limit order with buffer, extended_hours flag
  if (marketStatus.isExtendedHours && config.extended_hours_enabled) {
    const bufferPct = (config.extended_hours_limit_buffer_pct || 0.5) / 100
    const quote = await fetchLatestQuote(ticker, credentials)
    let limitPrice: number

    if (side === 'buy') {
      limitPrice = (quote.askPrice || quote.bidPrice) * (1 + bufferPct)
    } else {
      limitPrice = (quote.bidPrice || quote.askPrice) * (1 - bufferPct)
    }

    return {
      symbol: ticker,
      qty: Math.floor(qty),
      side,
      type: 'limit',
      time_in_force: 'day',
      limit_price: limitPrice.toFixed(2),
      extended_hours: true,
    }
  }

  // Market closed and extended hours disabled: market order (Alpaca will reject if truly closed)
  return {
    symbol: ticker,
    qty: Math.floor(qty),
    side,
    type: 'market',
    time_in_force: 'day',
  }
}

// =============================================================================
// RECALCULATE TRADE METRICS - Recompute all trade metrics from ground truth
// =============================================================================
// Queries all closed positions and recomputes winning_trades, losing_trades,
// win_rate, avg_win, avg_loss, and profit_factor from the actual data.
// This prevents counter drift from concurrent updates or failed transactions.
async function recalculateTradeMetrics(supabaseClient: any, stateId: string) {
  const { data: closedPositions } = await supabaseClient
    .from('reference_portfolio_positions')
    .select('realized_pl, realized_pl_pct')
    .eq('is_open', false)
    .not('realized_pl', 'is', null)

  if (!closedPositions || closedPositions.length === 0) {
    await supabaseClient
      .from('reference_portfolio_state')
      .update({
        winning_trades: 0,
        losing_trades: 0,
        win_rate: 0,
        avg_win: 0,
        avg_loss: 0,
        profit_factor: 0,
        updated_at: new Date().toISOString()
      })
      .eq('id', stateId)
    return
  }

  const wins = closedPositions.filter((p: any) => p.realized_pl > 0)
  const losses = closedPositions.filter((p: any) => p.realized_pl <= 0)

  const winningTrades = wins.length
  const losingTrades = losses.length
  const totalClosed = winningTrades + losingTrades
  const winRate = totalClosed > 0 ? Math.round((winningTrades / totalClosed) * 10000) / 100 : 0

  // avg_win and avg_loss are in percentage terms (from realized_pl_pct)
  const winsWithPct = wins.filter((p: any) => p.realized_pl_pct != null)
  const lossesWithPct = losses.filter((p: any) => p.realized_pl_pct != null)

  const avgWin = winsWithPct.length > 0
    ? Math.round(winsWithPct.reduce((sum: number, p: any) => sum + p.realized_pl_pct, 0) / winsWithPct.length * 100) / 100
    : 0
  const avgLoss = lossesWithPct.length > 0
    ? Math.round(lossesWithPct.reduce((sum: number, p: any) => sum + p.realized_pl_pct, 0) / lossesWithPct.length * 100) / 100
    : 0

  // profit_factor = sum of dollar wins / sum of dollar losses
  const totalWinDollars = wins.reduce((sum: number, p: any) => sum + p.realized_pl, 0)
  const totalLossDollars = Math.abs(losses.reduce((sum: number, p: any) => sum + p.realized_pl, 0))
  const profitFactor = totalLossDollars > 0
    ? Math.round((totalWinDollars / totalLossDollars) * 10000) / 10000
    : (totalWinDollars > 0 ? 99.99 : 0)

  await supabaseClient
    .from('reference_portfolio_state')
    .update({
      winning_trades: winningTrades,
      losing_trades: losingTrades,
      win_rate: winRate,
      avg_win: avgWin,
      avg_loss: avgLoss,
      profit_factor: profitFactor,
      updated_at: new Date().toISOString()
    })
    .eq('id', stateId)

  log.info('Trade metrics recalculated from ground truth', {
    winningTrades, losingTrades, winRate, avgWin, avgLoss, profitFactor
  })
}

// =============================================================================
// VERIFY ALPACA POSITION - Check if a position exists in Alpaca before selling
// =============================================================================
// Returns { exists, alpacaQty } or { exists: false } if position not found.
// Prevents creating unintended short positions by selling non-existent positions.
async function verifyAlpacaPosition(
  ticker: string,
  credentials: ReturnType<typeof getAlpacaCredentials>
): Promise<{ exists: boolean; alpacaQty: number; side: string }> {
  if (!credentials) return { exists: false, alpacaQty: 0, side: '' }

  try {
    const response = await fetch(`${credentials.baseUrl}/v2/positions/${encodeURIComponent(ticker.toUpperCase())}`, {
      headers: {
        'APCA-API-KEY-ID': credentials.apiKey,
        'APCA-API-SECRET-KEY': credentials.secretKey,
      }
    })

    if (!response.ok) {
      // 404 means position doesn't exist
      return { exists: false, alpacaQty: 0, side: '' }
    }

    const position = await response.json()
    return {
      exists: true,
      alpacaQty: Math.abs(parseFloat(position.qty)),
      side: position.side || 'long'
    }
  } catch {
    return { exists: false, alpacaQty: 0, side: '' }
  }
}

// TODO: Review - Main HTTP request handler that routes actions to appropriate handlers
// Supports actions: get-state, get-positions, get-trades, get-performance, execute-signals, update-positions, take-snapshot, reset-daily-trades, check-exits
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
// Always fetches live data from Alpaca first, falls back to database
// =============================================================================
// TODO: Review - Fetches current portfolio state, merging live Alpaca data with database records
// Returns portfolio value, cash, positions value, returns, drawdown, and market status
async function handleGetState(supabaseClient: any, requestId: string) {
  try {
    // Get config and state from database
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

    const initialCapital = state.config?.initial_capital || 1000000

    // Always fetch live data from Alpaca first
    const credentials = getAlpacaCredentials()
    let alpacaData: {
      equity: number | null
      cash: number | null
      buying_power: number | null
      positions_value: number | null
      source: 'alpaca' | 'database'
    } = {
      equity: null,
      cash: null,
      buying_power: null,
      positions_value: null,
      source: 'database'
    }

    if (credentials) {
      try {
        // Fetch account data from Alpaca
        const accountUrl = `${credentials.baseUrl}/v2/account`
        const accountResponse = await fetch(accountUrl, {
          headers: {
            'APCA-API-KEY-ID': credentials.apiKey,
            'APCA-API-SECRET-KEY': credentials.secretKey
          }
        })

        if (accountResponse.ok) {
          const account = await accountResponse.json()
          // FIX: Use only long_market_value for positions_value display
          // This ensures the value is always positive for a long-only strategy
          // short_market_value can cause the total to be negative when margin is used
          const longMarketValue = parseFloat(account.long_market_value) || 0
          const shortMarketValue = parseFloat(account.short_market_value) || 0

          // For display purposes, use the larger of:
          // 1. long_market_value (standard case)
          // 2. equity - cash (if that's positive and makes more sense)
          const calculatedPositionsValue = parseFloat(account.equity) - parseFloat(account.cash)
          const displayPositionsValue = longMarketValue > 0
            ? longMarketValue
            : Math.max(0, calculatedPositionsValue)

          alpacaData = {
            equity: parseFloat(account.equity),
            cash: parseFloat(account.cash),
            buying_power: parseFloat(account.buying_power),
            positions_value: displayPositionsValue,
            source: 'alpaca'
          }
          log.info('Fetched live Alpaca data for get-state', {
            requestId,
            equity: alpacaData.equity,
            cash: alpacaData.cash,
            longMarketValue,
            shortMarketValue,
            displayPositionsValue
          })
        } else {
          log.warn('Alpaca API failed, using database values', {
            requestId,
            status: accountResponse.status
          })
        }
      } catch (alpacaError) {
        log.warn('Failed to fetch Alpaca data, using database values', {
          requestId,
          error: alpacaError.message
        })
      }
    }

    // Get authoritative market status from Alpaca Clock API
    const marketStatus = await getMarketStatus(credentials)

    // Use Alpaca values if available, otherwise fall back to database
    const portfolioValue = alpacaData.equity ?? state.portfolio_value
    const cashValue = alpacaData.cash ?? state.cash
    const buyingPower = alpacaData.buying_power ?? state.buying_power
    const positionsValue = alpacaData.positions_value ?? state.positions_value

    // Calculate returns based on live portfolio value
    const totalReturn = portfolioValue - initialCapital
    const totalReturnPct = (totalReturn / initialCapital) * 100

    // Calculate current drawdown
    const peakValue = Math.max(state.peak_portfolio_value || initialCapital, portfolioValue)
    const currentDrawdown = ((peakValue - portfolioValue) / peakValue) * 100

    return new Response(
      JSON.stringify({
        success: true,
        state: {
          ...state,
          // Override with live Alpaca values
          portfolio_value: portfolioValue,
          cash: cashValue,
          buying_power: buyingPower,
          positions_value: positionsValue,
          total_return: totalReturn,
          total_return_pct: totalReturnPct,
          current_drawdown: currentDrawdown,
          peak_portfolio_value: peakValue,
          is_market_open: marketStatus.isOpen,
          is_extended_hours: marketStatus.isExtendedHours,
          data_source: alpacaData.source
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
// Always fetches live position data from Alpaca first
// =============================================================================
// TODO: Review - Retrieves portfolio positions, optionally including closed positions
// Merges live Alpaca position data with database records for current prices and P&L
async function handleGetPositions(supabaseClient: any, requestId: string, bodyParams: any) {
  try {
    const includesClosed = bodyParams.include_closed === true
    const limit = bodyParams.limit || 100

    // Get database positions for historical context (entry date, signals, etc.)
    let query = supabaseClient
      .from('reference_portfolio_positions')
      .select('*')
      .order('entry_date', { ascending: false })
      .limit(limit)

    if (!includesClosed) {
      query = query.eq('is_open', true)
    }

    const { data: dbPositions, error } = await query

    if (error) {
      log.error('Failed to fetch positions from database', error, { requestId })
      return new Response(
        JSON.stringify({ error: 'Failed to fetch positions' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // For open positions, fetch live data from Alpaca
    let positions = dbPositions || []
    let dataSource = 'database'

    if (!includesClosed) {
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

            // Merge Alpaca live data with database records (skip shorts)
            positions = positions.map((dbPos: any) => {
              const alpacaPos = alpacaPositionMap.get(dbPos.ticker.toUpperCase())
              if (alpacaPos) {
                // Skip short positions — our system is long-only
                if (alpacaPos.side === 'short') {
                  return { ...dbPos, data_source: 'database' }
                }
                return {
                  ...dbPos,
                  // Override with live Alpaca values
                  current_price: parseFloat(alpacaPos.current_price),
                  market_value: Math.max(0, parseFloat(alpacaPos.market_value)),
                  unrealized_pl: parseFloat(alpacaPos.unrealized_pl),
                  unrealized_pl_pct: parseFloat(alpacaPos.unrealized_plpc) * 100,
                  quantity: parseInt(alpacaPos.qty),
                  avg_entry_price: parseFloat(alpacaPos.avg_entry_price),
                  cost_basis: parseFloat(alpacaPos.cost_basis),
                  data_source: 'alpaca'
                }
              }
              return { ...dbPos, data_source: 'database' }
            })

            dataSource = 'alpaca'
            log.info('Fetched live Alpaca positions', {
              requestId,
              alpacaCount: alpacaPositions.length,
              dbCount: dbPositions?.length || 0
            })
          } else {
            log.warn('Alpaca positions API failed, using database values', {
              requestId,
              status: alpacaResponse.status
            })
          }
        } catch (alpacaError) {
          log.warn('Failed to fetch Alpaca positions, using database values', {
            requestId,
            error: alpacaError.message
          })
        }
      }
    }

    return new Response(
      JSON.stringify({
        success: true,
        positions: positions,
        count: positions.length,
        data_source: dataSource
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
// TODO: Review - Retrieves paginated trade history from the transactions table
// Supports limit and offset parameters for pagination
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
// TODO: Review - Fetches portfolio performance history from Alpaca API
// Supports timeframes: 1d, 1w, 1m, 3m, ytd, 1y and transforms data to snapshot format
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
// TODO: Review - Processes pending trading signals from queue and executes buy/sell orders via Alpaca
// Handles position sizing, confidence thresholds, daily trade limits, and updates portfolio state
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

    // Note: position limit checks are done per-signal below (stock vs crypto counted separately)

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

    // Get Alpaca credentials using trading mode from config
    const credentials = getAlpacaCredentials(config.trading_mode || 'paper')
    if (!credentials) {
      log.error('No Alpaca credentials configured', null, { requestId })
      return new Response(
        JSON.stringify({ error: 'Alpaca credentials not configured' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get market status for order type selection
    const marketStatus = await getMarketStatus(credentials)
    log.info('Market status for execution', { requestId, isOpen: marketStatus.isOpen, isExtendedHours: marketStatus.isExtendedHours })

    // Get existing positions with full details for sell signal handling
    const { data: existingPositions } = await supabaseClient
      .from('reference_portfolio_positions')
      .select('*')
      .eq('is_open', true)

    const existingTickers = new Set((existingPositions || []).map((p: any) => p.ticker.toUpperCase()))
    const positionsByTicker = new Map((existingPositions || []).map((p: any) => [p.ticker.toUpperCase(), p]))
    const openPositionCount = existingPositions?.length || 0
    // Count positions by asset type for independent caps
    let stockPositionCount = (existingPositions || []).filter((p: any) => (p.asset_type || 'stock') === 'stock').length
    let cryptoPositionCount = (existingPositions || []).filter((p: any) => p.asset_type === 'crypto').length
    const cryptoMaxPositions = config.crypto_max_positions || 5

    let executed = 0
    let skipped = 0
    let failed = 0
    let sellsExecuted = 0
    const results: any[] = []

    for (const queued of queuedSignals) {
      const signal = queued.signal as TradingSignal

      if (!signal) {
        await updateQueueStatus(supabaseClient, queued.id, 'skipped', 'Signal not found')
        skipped++
        continue
      }

      const ticker = signal.ticker.toUpperCase()
      const isBuySignal = ['buy', 'strong_buy'].includes(signal.signal_type)
      const isSellSignal = ['sell', 'strong_sell'].includes(signal.signal_type)
      const hasPosition = existingTickers.has(ticker)

      // Check confidence threshold for all signals
      if (signal.confidence_score < config.min_confidence_threshold) {
        await updateQueueStatus(supabaseClient, queued.id, 'skipped', 'Below confidence threshold')
        skipped++
        continue
      }

      // Risk check: don't enter new positions with low confidence when portfolio is crowded
      if (isBuySignal && signal.confidence_score < 0.70 && openPositionCount >= 15) {
        await updateQueueStatus(supabaseClient, queued.id, 'skipped', 'Low confidence with high position count')
        skipped++
        continue
      }

      // Handle SELL signals - close existing positions
      if (isSellSignal) {
        if (!hasPosition) {
          await updateQueueStatus(supabaseClient, queued.id, 'skipped', 'Sell signal but no position to close')
          skipped++
          continue
        }

        const position = positionsByTicker.get(ticker)
        if (!position) {
          await updateQueueStatus(supabaseClient, queued.id, 'skipped', 'Position not found')
          skipped++
          continue
        }

        try {
          // Verify position exists in Alpaca before selling (prevents creating shorts)
          const alpacaCheck = await verifyAlpacaPosition(ticker, credentials)
          if (!alpacaCheck.exists) {
            log.warn('Position not found in Alpaca, closing DB record without order', { requestId, ticker })
            const currentPrice = position.current_price || position.entry_price
            const exitValue = currentPrice * position.quantity
            const realizedPL = exitValue - (position.entry_price * position.quantity)
            const realizedPLPct = ((currentPrice - position.entry_price) / position.entry_price) * 100

            await supabaseClient
              .from('reference_portfolio_positions')
              .update({
                is_open: false,
                exit_price: currentPrice,
                exit_date: new Date().toISOString(),
                exit_reason: 'position_not_found',
                realized_pl: realizedPL,
                realized_pl_pct: realizedPLPct,
                updated_at: new Date().toISOString()
              })
              .eq('id', position.id)

            state.open_positions -= 1
            existingTickers.delete(ticker)
            positionsByTicker.delete(ticker)
            sellsExecuted++
            executed++
            results.push({ ticker, action: 'sell', exitReason: 'position_not_found', realizedPL })
            await updateQueueStatus(supabaseClient, queued.id, 'executed', null, position.id)
            continue
          }

          // Use Alpaca's actual quantity to prevent selling more than we hold
          const sellQty = Math.min(position.quantity, alpacaCheck.alpacaQty)

          // Get current price from Alpaca
          const quoteUrl = `${credentials.dataUrl}/v2/stocks/${ticker}/quotes/latest`
          const quoteResponse = await fetch(quoteUrl, {
            headers: {
              'APCA-API-KEY-ID': credentials.apiKey,
              'APCA-API-SECRET-KEY': credentials.secretKey
            }
          })

          let currentPrice = position.current_price
          if (quoteResponse.ok) {
            const quote = await quoteResponse.json()
            currentPrice = quote.quote?.bp || quote.quote?.ap || position.current_price
          }

          // Place sell order with Alpaca (order type based on market status)
          const orderUrl = `${credentials.baseUrl}/v2/orders`
          const orderRequest = await buildOrderRequest(
            ticker, sellQty, 'sell',
            position.asset_type || 'stock', marketStatus, credentials, config
          )

          log.info('Placing sell order from signal', { requestId, ticker, shares: sellQty, dbQty: position.quantity, alpacaQty: alpacaCheck.alpacaQty, signalType: signal.signal_type, orderType: orderRequest.type })

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
            log.error('Sell order failed', { error: orderResult }, { requestId, ticker })
            await updateQueueStatus(supabaseClient, queued.id, 'failed', orderResult.message || 'Sell order rejected')
            failed++
            continue
          }

          log.info('Sell order placed successfully', { requestId, orderId: orderResult.id, ticker })

          // Calculate realized P&L
          const exitValue = currentPrice * position.quantity
          const entryValue = position.entry_price * position.quantity
          const realizedPL = exitValue - entryValue
          const realizedPLPct = ((currentPrice - position.entry_price) / position.entry_price) * 100
          const isWin = realizedPL > 0

          // Update position as closed
          await supabaseClient
            .from('reference_portfolio_positions')
            .update({
              is_open: false,
              exit_price: currentPrice,
              exit_date: new Date().toISOString(),
              exit_signal_id: signal.id,
              exit_reason: `signal_${signal.signal_type}`,
              exit_order_id: orderResult.id,
              realized_pl: realizedPL,
              realized_pl_pct: realizedPLPct,
              updated_at: new Date().toISOString()
            })
            .eq('id', position.id)

          // Record the sell transaction
          await supabaseClient
            .from('reference_portfolio_transactions')
            .insert({
              position_id: position.id,
              ticker: ticker,
              transaction_type: 'sell',
              quantity: position.quantity,
              price: currentPrice,
              total_value: exitValue,
              signal_id: signal.id,
              signal_confidence: signal.confidence_score,
              signal_type: signal.signal_type,
              executed_at: new Date().toISOString(),
              alpaca_order_id: orderResult.id,
              alpaca_client_order_id: orderResult.client_order_id,
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
              trades_today: state.trades_today + 1,
              total_trades: state.total_trades + 1,
              winning_trades: isWin ? state.winning_trades + 1 : state.winning_trades,
              losing_trades: !isWin ? state.losing_trades + 1 : state.losing_trades,
              last_trade_at: new Date().toISOString(),
              updated_at: new Date().toISOString()
            })
            .eq('id', state.id)

          // Update local state for subsequent iterations
          state.cash += exitValue
          state.buying_power += exitValue
          state.open_positions -= 1
          state.trades_today += 1
          if (isWin) state.winning_trades += 1
          else state.losing_trades += 1

          // Update queue status
          await updateQueueStatus(supabaseClient, queued.id, 'executed', null, position.id)

          // Remove from existing positions
          existingTickers.delete(ticker)
          positionsByTicker.delete(ticker)

          sellsExecuted++
          executed++
          results.push({
            ticker,
            action: 'sell',
            shares: position.quantity,
            price: currentPrice,
            value: exitValue,
            realizedPL,
            realizedPLPct: realizedPLPct.toFixed(2) + '%',
            orderId: orderResult.id
          })

          // Small delay between orders
          await new Promise(resolve => setTimeout(resolve, 200))

        } catch (error) {
          log.error('Error processing sell signal', error, { requestId, ticker })
          await updateQueueStatus(supabaseClient, queued.id, 'failed', error.message)
          failed++
        }

        continue
      }

      // Handle BUY signals - open new positions
      if (!isBuySignal) {
        await updateQueueStatus(supabaseClient, queued.id, 'skipped', 'Unknown signal type')
        skipped++
        continue
      }

      // Skip if we already have a position in this ticker
      if (hasPosition) {
        await updateQueueStatus(supabaseClient, queued.id, 'skipped', 'Already have position')
        skipped++
        continue
      }

      // Check asset-type-specific position limits
      const signalAssetType = (signal as any).asset_type || 'stock'
      if (signalAssetType === 'crypto') {
        if (!config.crypto_enabled) {
          await updateQueueStatus(supabaseClient, queued.id, 'skipped', 'Crypto trading disabled')
          skipped++
          continue
        }
        if (cryptoPositionCount >= cryptoMaxPositions) {
          await updateQueueStatus(supabaseClient, queued.id, 'skipped', 'Max crypto positions reached')
          skipped++
          continue
        }
      } else {
        if (stockPositionCount >= config.max_portfolio_positions) {
          await updateQueueStatus(supabaseClient, queued.id, 'skipped', 'Max stock positions reached')
          skipped++
          continue
        }
      }

      try {
        // Get current price from Alpaca (use crypto endpoint for crypto pairs)
        const isCryptoBuy = signalAssetType === 'crypto'
        const quoteUrl = isCryptoBuy
          ? `${credentials.dataUrl}/v1beta3/crypto/us/latest/quotes?symbols=${encodeURIComponent(signal.ticker)}`
          : `${credentials.dataUrl}/v2/stocks/${signal.ticker}/quotes/latest`
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
        let currentPrice: number
        if (isCryptoBuy) {
          const cryptoQuote = quote.quotes?.[signal.ticker]
          currentPrice = cryptoQuote?.ap || cryptoQuote?.bp || 0
        } else {
          currentPrice = quote.quote?.ap || quote.quote?.bp || 0
        }

        if (currentPrice <= 0) {
          await updateQueueStatus(supabaseClient, queued.id, 'failed', 'Invalid price')
          failed++
          continue
        }

        // Calculate position size (asset-type-aware for fractional crypto)
        const { shares, positionValue, multiplier } = calculatePositionSize(
          state.portfolio_value,
          signal.confidence_score,
          currentPrice,
          config,
          signalAssetType
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

        // Place order with Alpaca (order type based on market status)
        const orderUrl = `${credentials.baseUrl}/v2/orders`
        const signalAssetType = signal.asset_type || 'stock'
        const orderRequest = await buildOrderRequest(
          signal.ticker.toUpperCase(), shares, 'buy',
          signalAssetType, marketStatus, credentials, config
        )

        log.info('Placing order', { requestId, ticker: signal.ticker, shares, positionValue, orderType: orderRequest.type, assetType: signalAssetType })

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

        // Calculate stop loss, take profit, and trailing stop prices (crypto uses wider bands)
        const slPct = signalAssetType === 'crypto' ? (config.crypto_stop_loss_pct || 15) : config.default_stop_loss_pct
        const tpPct = signalAssetType === 'crypto' ? (config.crypto_take_profit_pct || 25) : config.default_take_profit_pct
        const stopLossPrice = currentPrice * (1 - slPct / 100)
        const takeProfitPrice = currentPrice * (1 + tpPct / 100)
        const trailingStopPrice = config.trailing_stop_pct
          ? currentPrice * (1 - config.trailing_stop_pct / 100)
          : null

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
            highest_price: currentPrice,
            trailing_stop_price: trailingStopPrice,
            position_size_pct: (positionValue / state.portfolio_value) * 100,
            confidence_weight: multiplier,
            is_open: true,
            asset_type: signalAssetType,
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
            status: 'executed',
            asset_type: signalAssetType,
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
        // Track position counts by asset type
        if (signalAssetType === 'crypto') cryptoPositionCount++
        else stockPositionCount++

        results.push({
          ticker: signal.ticker,
          shares,
          price: currentPrice,
          value: positionValue,
          orderId: orderResult.id,
          assetType: signalAssetType,
        })

        // Small delay between orders
        await new Promise(resolve => setTimeout(resolve, 200))

      } catch (error) {
        log.error('Error processing signal', error, { requestId, ticker: signal.ticker })
        await updateQueueStatus(supabaseClient, queued.id, 'failed', error.message)
        failed++
      }
    }

    // Recalculate trade metrics from ground truth after any sells
    if (sellsExecuted > 0) {
      await recalculateTradeMetrics(supabaseClient, state.id)
    }

    log.info('Signal execution completed', { requestId, executed, skipped, failed, sellsExecuted })

    return new Response(
      JSON.stringify({
        success: true,
        message: `Executed ${executed} trades (${sellsExecuted} sells), skipped ${skipped}, failed ${failed}`,
        summary: { executed, skipped, failed, sellsExecuted },
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

// TODO: Review - Helper function to update signal queue entry status after processing
// Updates status, skip reason, transaction ID, and processed timestamp
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
// TODO: Review - Syncs position prices and P&L from Alpaca, updates portfolio state
// Calculates day return, total return, drawdown, and updates peak portfolio value
async function handleUpdatePositions(supabaseClient: any, requestId: string) {
  try {
    log.info('Updating positions', { requestId })

    // Get config for initial_capital and trading_mode
    const { data: config } = await supabaseClient
      .from('reference_portfolio_config')
      .select('initial_capital, trading_mode')
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

    // Count open positions from database — will be adjusted after Alpaca reconciliation
    let openPositionsCount = positions?.length || 0
    let reconciledCount = 0

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
    const credentials = getAlpacaCredentials(config?.trading_mode || 'paper')
    let alpacaSyncSuccess = false
    let alpacaEquity: number | null = null
    let alpacaCash: number | null = null

    // Track Alpaca's actual positions value from account API
    let alpacaPositionsValue: number | null = null

    if (credentials) {
      try {
        // First, get account info to get the actual equity, cash, and positions value
        const alpacaAccountUrl = `${credentials.baseUrl}/v2/account`
        const accountResponse = await fetch(alpacaAccountUrl, {
          headers: {
            'APCA-API-KEY-ID': credentials.apiKey,
            'APCA-API-SECRET-KEY': credentials.secretKey
          }
        })

        if (accountResponse.ok) {
          const accountData = await accountResponse.json()
          alpacaEquity = parseFloat(accountData.equity)
          alpacaCash = parseFloat(accountData.cash)
          // FIX: Use only long_market_value for positions_value
          // short_market_value can make this negative when margin is used
          const longMarketValue = parseFloat(accountData.long_market_value) || 0
          alpacaPositionsValue = longMarketValue > 0 ? longMarketValue : Math.max(0, alpacaEquity - alpacaCash)
          log.info('Alpaca account fetched', {
            requestId,
            equity: alpacaEquity,
            cash: alpacaCash,
            longMarketValue,
            positionsValue: alpacaPositionsValue
          })
        }

        // Then get positions
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
          log.info('Alpaca positions fetched', { requestId, alpacaCount: alpacaPositions.length, dbCount: positions.length })

          // Reset totals for Alpaca data
          totalPositionsValue = 0
          totalUnrealizedPL = 0
          let reconciled = 0

          for (const position of positions) {
            const alpacaPosition = alpacaPositionMap.get(position.ticker.toUpperCase())

            if (alpacaPosition) {
              // Skip short positions — our system is long-only
              if (alpacaPosition.side === 'short') {
                log.warn('Skipping short position from Alpaca sync', { requestId, ticker: position.ticker })
                const dbMarketValue = Math.max(0, position.quantity * (position.current_price || position.entry_price))
                totalPositionsValue += dbMarketValue
                continue
              }

              const currentPrice = parseFloat(alpacaPosition.current_price)
              // Ensure market_value is non-negative for long positions
              const marketValue = Math.max(0, parseFloat(alpacaPosition.market_value))
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
              // Position marked open in DB but absent from Alpaca — Alpaca already closed it
              // (e.g., stop-loss or take-profit filled externally)
              log.warn('DB-open position absent from Alpaca — marking closed', {
                requestId,
                ticker: position.ticker,
                entryPrice: position.entry_price,
                quantity: position.quantity
              })

              const exitPrice = position.current_price || position.entry_price
              const exitValue = exitPrice * position.quantity
              const entryValue = position.entry_price * position.quantity
              const realizedPL = exitValue - entryValue
              const realizedPLPct = position.entry_price > 0
                ? ((exitPrice - position.entry_price) / position.entry_price) * 100
                : 0

              await supabaseClient
                .from('reference_portfolio_positions')
                .update({
                  is_open: false,
                  exit_price: exitPrice,
                  exit_date: new Date().toISOString(),
                  exit_reason: 'alpaca_closed',
                  realized_pl: realizedPL,
                  realized_pl_pct: realizedPLPct,
                  updated_at: new Date().toISOString()
                })
                .eq('id', position.id)

              // Do NOT add this position's value to totals — it's closed
              reconciled++
              reconciledCount++
            }
          }

          if (reconciled > 0) {
            log.info('Reconciled orphaned positions', { requestId, reconciled, remainingOpen: openPositionsCount - reconciledCount })
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
      // Use Alpaca equity as source of truth if available, otherwise calculate from DB
      const portfolioValue = alpacaEquity !== null ? alpacaEquity : (state.cash + totalPositionsValue)
      const cashValue = alpacaCash !== null ? alpacaCash : state.cash

      // FIX: Use Alpaca's positions_value from account API as source of truth
      // This ensures consistency with handleGetState and prevents negative values
      // from mismatched DB positions
      const finalPositionsValue = alpacaPositionsValue !== null
        ? alpacaPositionsValue
        : Math.max(0, totalPositionsValue) // Ensure non-negative if using DB sum

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

      log.info('Updating portfolio state', {
        requestId,
        portfolioValue,
        cashValue,
        positionsValue: finalPositionsValue,
        alpacaPositionsValueUsed: alpacaPositionsValue !== null,
        alpacaEquityUsed: alpacaEquity !== null
      })

      await supabaseClient
        .from('reference_portfolio_state')
        .update({
          positions_value: finalPositionsValue,
          portfolio_value: portfolioValue,
          cash: cashValue, // Also update cash from Alpaca
          total_return: totalReturn,
          total_return_pct: totalReturnPct,
          day_return: Math.round(dayReturn * 100) / 100,
          day_return_pct: Math.round(dayReturnPct * 10000) / 10000,
          peak_portfolio_value: peakValue,
          current_drawdown: currentDrawdown,
          max_drawdown: maxDrawdown,
          open_positions: Math.max(0, openPositionsCount - reconciledCount), // Subtract positions closed during reconciliation
          last_sync_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        })
        .eq('id', state.id)
    }

    // FIX: Use finalPositionsValue in logging and summary
    const summaryPositionsValue = alpacaPositionsValue !== null
      ? alpacaPositionsValue
      : Math.max(0, totalPositionsValue)

    // Self-healing: recalculate trade metrics from ground truth on every position update
    if (state) {
      await recalculateTradeMetrics(supabaseClient, state.id)
    }

    log.info('Positions updated', {
      requestId,
      updated,
      openPositionsCount,
      positionsValue: summaryPositionsValue,
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
          positionsValue: summaryPositionsValue,
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
// TODO: Review - Internal helper that syncs position data from Alpaca before taking snapshots
// Updates position prices, market values, unrealized P&L, and portfolio state
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

    let openPositionsCount = positions?.length || 0
    let syncReconciledCount = 0

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
    let alpacaEquity: number | null = null
    let alpacaCash: number | null = null
    let alpacaPositionsValue: number | null = null

    if (credentials) {
      try {
        // First, get account info to get the actual equity, cash, and positions value
        const alpacaAccountUrl = `${credentials.baseUrl}/v2/account`
        const accountResponse = await fetch(alpacaAccountUrl, {
          headers: {
            'APCA-API-KEY-ID': credentials.apiKey,
            'APCA-API-SECRET-KEY': credentials.secretKey
          }
        })

        if (accountResponse.ok) {
          const accountData = await accountResponse.json()
          alpacaEquity = parseFloat(accountData.equity)
          alpacaCash = parseFloat(accountData.cash)
          // FIX: Use only long_market_value for positions_value
          const longMarketValue = parseFloat(accountData.long_market_value) || 0
          alpacaPositionsValue = longMarketValue > 0 ? longMarketValue : Math.max(0, alpacaEquity - alpacaCash)
        }

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
              // Skip short positions — our system is long-only
              if (alpacaPosition.side === 'short') {
                log.warn('Skipping short position from Alpaca sync (snapshot)', { requestId, ticker: position.ticker })
                const dbMarketValue = Math.max(0, position.quantity * (position.current_price || position.entry_price))
                totalPositionsValue += dbMarketValue
                continue
              }

              const currentPrice = parseFloat(alpacaPosition.current_price)
              // Ensure market_value is non-negative for long positions
              const marketValue = Math.max(0, parseFloat(alpacaPosition.market_value))
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
              // Position marked open in DB but absent from Alpaca — close it
              log.warn('Snapshot sync: DB-open position absent from Alpaca — marking closed', {
                requestId, ticker: position.ticker, entryPrice: position.entry_price
              })

              const exitPrice = position.current_price || position.entry_price
              const exitValue = exitPrice * position.quantity
              const entryValue = position.entry_price * position.quantity
              const realizedPL = exitValue - entryValue
              const realizedPLPct = position.entry_price > 0
                ? ((exitPrice - position.entry_price) / position.entry_price) * 100
                : 0

              await supabaseClient
                .from('reference_portfolio_positions')
                .update({
                  is_open: false,
                  exit_price: exitPrice,
                  exit_date: new Date().toISOString(),
                  exit_reason: 'alpaca_closed',
                  realized_pl: realizedPL,
                  realized_pl_pct: realizedPLPct,
                  updated_at: new Date().toISOString()
                })
                .eq('id', position.id)

              syncReconciledCount++
            }
          }

          if (syncReconciledCount > 0) {
            log.info('Snapshot sync reconciled orphaned positions', {
              requestId, reconciled: syncReconciledCount
            })
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
      // Use Alpaca equity as source of truth if available
      const portfolioValue = alpacaEquity !== null ? alpacaEquity : (state.cash + totalPositionsValue)
      const cashValue = alpacaCash !== null ? alpacaCash : state.cash

      // FIX: Use Alpaca's positions_value from account API as source of truth
      const finalPositionsValue = alpacaPositionsValue !== null
        ? alpacaPositionsValue
        : Math.max(0, totalPositionsValue) // Ensure non-negative if using DB sum

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
          positions_value: finalPositionsValue,
          portfolio_value: portfolioValue,
          cash: cashValue, // Also update cash from Alpaca
          total_return: totalReturn,
          total_return_pct: totalReturnPct,
          day_return: Math.round(dayReturn * 100) / 100,
          day_return_pct: Math.round(dayReturnPct * 10000) / 10000,
          peak_portfolio_value: peakValue,
          current_drawdown: currentDrawdown,
          max_drawdown: maxDrawdown,
          open_positions: Math.max(0, openPositionsCount - syncReconciledCount),
          last_sync_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        })
        .eq('id', state.id)

      log.info('Positions synced for snapshot', {
        requestId,
        openPositionsCount: Math.max(0, openPositionsCount - syncReconciledCount),
        positionsValue: finalPositionsValue,
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
// TODO: Review - Records daily portfolio performance snapshot for historical tracking
// Syncs with Alpaca first, calculates returns, Sharpe ratio, and benchmark comparison
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
// TODO: Review - Resets daily trade counter and day return at market open
// Should be called via scheduled job at start of each trading day
async function handleResetDailyTrades(supabaseClient: any, requestId: string) {
  try {
    // Get the current state ID first
    const { data: currentState } = await supabaseClient
      .from('reference_portfolio_state')
      .select('id, trades_today')
      .single()

    if (!currentState) {
      log.warn('No portfolio state found to reset', { requestId })
      return new Response(
        JSON.stringify({ success: false, message: 'No portfolio state found' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    log.info('Resetting daily trades', { requestId, currentTradesToday: currentState.trades_today, stateId: currentState.id })

    const { error: updateError, count } = await supabaseClient
      .from('reference_portfolio_state')
      .update({
        trades_today: 0,
        day_return: 0,
        day_return_pct: 0,
        updated_at: new Date().toISOString()
      })
      .eq('id', currentState.id)

    if (updateError) {
      log.error('Failed to reset daily trades', updateError, { requestId })
      return new Response(
        JSON.stringify({ success: false, error: updateError.message }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    log.info('Daily trades reset successfully', { requestId, previousTradesToday: currentState.trades_today })

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
// TODO: Review - Monitors open positions for stop-loss and take-profit triggers
// Automatically closes positions when price thresholds are hit, updates win/loss stats
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

    // Get market status for order type selection
    const marketStatus = await getMarketStatus(credentials)

    let closed = 0
    let wins = 0
    let losses = 0
    const results: any[] = []

    for (const position of positions) {
      try {
        // Get current price from Alpaca (use fetchLatestQuote for crypto support)
        const isCrypto = (position.asset_type || 'stock') === 'crypto'
        const quoteUrl = isCrypto
          ? `${credentials.dataUrl}/v1beta3/crypto/us/latest/quotes?symbols=${encodeURIComponent(position.ticker)}`
          : `${credentials.dataUrl}/v2/stocks/${position.ticker}/quotes/latest`
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
        let currentPrice: number
        if (isCrypto) {
          const cryptoQuote = quote.quotes?.[position.ticker]
          currentPrice = cryptoQuote?.bp || cryptoQuote?.ap || position.current_price
        } else {
          currentPrice = quote.quote?.bp || quote.quote?.ap || position.current_price
        }

        if (!currentPrice || currentPrice <= 0) continue

        // Use crypto-specific exit thresholds if applicable
        const stopLossPct = isCrypto ? (config.crypto_stop_loss_pct || 15) : config.default_stop_loss_pct
        const takeProfitPct = isCrypto ? (config.crypto_take_profit_pct || 25) : config.default_take_profit_pct

        // Update highest price and trailing stop (for all positions, even if not exiting)
        const highestPrice = Math.max(position.highest_price || position.entry_price, currentPrice)
        const trailingStopPrice = config.trailing_stop_pct
          ? highestPrice * (1 - config.trailing_stop_pct / 100)
          : null

        // Update position with new highest price and trailing stop
        if (highestPrice > (position.highest_price || 0) || !position.trailing_stop_price) {
          await supabaseClient
            .from('reference_portfolio_positions')
            .update({
              highest_price: highestPrice,
              trailing_stop_price: trailingStopPrice,
              updated_at: new Date().toISOString()
            })
            .eq('id', position.id)
        }

        // FIRST: Verify position still exists in Alpaca before any threshold checks.
        // This catches positions closed externally (e.g., by Alpaca stop-loss fills)
        // that would otherwise be orphaned in the DB forever.
        const alpacaExitCheck = await verifyAlpacaPosition(position.ticker.toUpperCase(), credentials)
        if (!alpacaExitCheck.exists) {
          log.warn('Position not found in Alpaca during exit check, closing DB record', {
            requestId, ticker: position.ticker
          })
          const exitValue = currentPrice * position.quantity
          const entryValue = position.entry_price * position.quantity
          const realizedPL = exitValue - entryValue
          const realizedPLPct = ((currentPrice - position.entry_price) / position.entry_price) * 100
          const isWin = realizedPL > 0
          if (isWin) wins++
          else losses++

          await supabaseClient
            .from('reference_portfolio_positions')
            .update({
              is_open: false,
              exit_price: currentPrice,
              exit_date: new Date().toISOString(),
              exit_reason: 'position_not_found',
              realized_pl: realizedPL,
              realized_pl_pct: realizedPLPct,
              updated_at: new Date().toISOString()
            })
            .eq('id', position.id)

          state.open_positions -= 1
          closed++
          results.push({
            ticker: position.ticker, exitReason: 'position_not_found',
            exitPrice: currentPrice, entryPrice: position.entry_price,
            quantity: position.quantity, realizedPL, isWin
          })
          continue
        }

        // Position exists in Alpaca — now check exit conditions
        let exitReason: string | null = null

        // 1. Check time-based exit (stale position)
        if (config.max_hold_days) {
          const entryDate = new Date(position.entry_date)
          const now = new Date()
          const daysHeld = Math.floor((now.getTime() - entryDate.getTime()) / (1000 * 60 * 60 * 24))

          if (daysHeld >= config.max_hold_days) {
            exitReason = 'timeout'
            log.info('Time-based exit triggered', {
              requestId,
              ticker: position.ticker,
              daysHeld,
              maxHoldDays: config.max_hold_days
            })
          }
        }

        // 2. Check trailing stop (dynamic stop that follows price up)
        if (!exitReason && trailingStopPrice && currentPrice <= trailingStopPrice) {
          exitReason = 'trailing_stop'
          log.info('Trailing stop triggered', {
            requestId,
            ticker: position.ticker,
            currentPrice,
            trailingStopPrice,
            highestPrice
          })
        }

        // 3. Check fixed stop-loss (only if trailing stop not triggered)
        if (!exitReason && position.stop_loss_price && currentPrice <= position.stop_loss_price) {
          exitReason = 'stop_loss'
        }

        // 4. Check take-profit
        if (!exitReason && position.take_profit_price && currentPrice >= position.take_profit_price) {
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

        // Use Alpaca's actual quantity to prevent selling more than we hold
        const exitSellQty = Math.min(position.quantity, alpacaExitCheck.alpacaQty)

        // Place sell order with Alpaca (order type based on market status)
        const orderUrl = `${credentials.baseUrl}/v2/orders`
        const exitOrderRequest = await buildOrderRequest(
          position.ticker.toUpperCase(), exitSellQty, 'sell',
          position.asset_type || 'stock', marketStatus, credentials, config
        )
        const orderResponse = await fetch(orderUrl, {
          method: 'POST',
          headers: {
            'APCA-API-KEY-ID': credentials.apiKey,
            'APCA-API-SECRET-KEY': credentials.secretKey,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(exitOrderRequest)
        })

        const orderResult = await orderResponse.json()

        if (!orderResponse.ok) {
          log.error('Sell order failed', { error: orderResult }, { requestId, ticker: position.ticker })
          continue
        }

        log.info('Sell order placed', { requestId, orderId: orderResult.id, ticker: position.ticker, sellQty: exitSellQty })

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

    // Recalculate all trade metrics from ground truth (closed positions)
    if (closed > 0) {
      await recalculateTradeMetrics(supabaseClient, state.id)
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
