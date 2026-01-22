import { createClient } from 'supabase'
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

// TODO: Review log object - structured JSON logging utility with service identification
const log = {
  info: (message: string, metadata?: any) => {
    console.log(JSON.stringify({
      level: 'INFO',
      timestamp: new Date().toISOString(),
      service: 'strategy-follow',
      message,
      ...metadata
    }))
  },
  error: (message: string, error?: any, metadata?: any) => {
    console.error(JSON.stringify({
      level: 'ERROR',
      timestamp: new Date().toISOString(),
      service: 'strategy-follow',
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
      service: 'strategy-follow',
      message,
      ...metadata
    }))
  }
}

// TODO: Review isMarketOpen - checks if US stock market is currently open
// - Market hours: 9:30 AM - 4:00 PM ET, Monday-Friday
// - Note: simplified DST handling (EST offset hardcoded)
function isMarketOpen(): boolean {
  const now = new Date()
  const etOffset = -5 // EST (simplified - should handle DST)
  const utcHour = now.getUTCHours()
  const etHour = (utcHour + etOffset + 24) % 24
  const dayOfWeek = now.getUTCDay()

  // Market hours: 9:30 AM - 4:00 PM ET, Monday-Friday
  const isWeekday = dayOfWeek >= 1 && dayOfWeek <= 5
  const minutes = now.getUTCMinutes()
  const isAfterOpen = etHour > 9 || (etHour === 9 && minutes >= 30)
  const isBeforeClose = etHour < 16

  return isWeekday && isAfterOpen && isBeforeClose
}

// TODO: Review canAccountTrade - validates Alpaca account can execute trades
// - Checks for blocked status flags and minimum buying power ($100)
function canAccountTrade(account: any): { canTrade: boolean; reason?: string } {
  if (account.trading_blocked) {
    return { canTrade: false, reason: 'Account trading is blocked' }
  }
  if (account.account_blocked) {
    return { canTrade: false, reason: 'Account is blocked' }
  }
  if (account.transfers_blocked) {
    return { canTrade: false, reason: 'Account transfers are blocked' }
  }
  // Check for sufficient buying power
  if (parseFloat(account.buying_power) < 100) {
    return { canTrade: false, reason: 'Insufficient buying power (less than $100)' }
  }
  return { canTrade: true }
}

// TODO: Review getAlpacaCredentials - retrieves user's Alpaca API keys from database
// - Supports paper and live trading modes with separate credentials
// - Returns baseUrl and dataUrl configured for trading mode
async function getAlpacaCredentials(
  supabase: any,
  userEmail: string,
  tradingMode: 'paper' | 'live'
): Promise<{ apiKey: string; secretKey: string; baseUrl: string; dataUrl: string } | null> {
  try {
    const { data, error } = await supabase
      .from('user_api_keys')
      .select('paper_api_key, paper_secret_key, live_api_key, live_secret_key')
      .eq('user_email', userEmail)
      .maybeSingle()

    if (error || !data) {
      return null
    }

    const apiKey = tradingMode === 'paper' ? data.paper_api_key : data.live_api_key
    const secretKey = tradingMode === 'paper' ? data.paper_secret_key : data.live_secret_key

    if (!apiKey || !secretKey) {
      return null
    }

    const baseUrl = tradingMode === 'paper'
      ? 'https://paper-api.alpaca.markets'
      : 'https://api.alpaca.markets'
    const dataUrl = 'https://data.alpaca.markets'

    return { apiKey, secretKey, baseUrl, dataUrl }
  } catch (err) {
    log.warn('Could not fetch user credentials', { error: err })
    return null
  }
}

// TODO: Review getAlpacaAccount - fetches account information from Alpaca API
// - Returns account object with equity, buying power, and status flags
async function getAlpacaAccount(credentials: { apiKey: string; secretKey: string; baseUrl: string }) {
  const response = await fetch(`${credentials.baseUrl}/v2/account`, {
    headers: {
      'APCA-API-KEY-ID': credentials.apiKey,
      'APCA-API-SECRET-KEY': credentials.secretKey
    }
  })

  if (!response.ok) {
    throw new Error(`Alpaca account error: ${response.status}`)
  }

  return response.json()
}

// TODO: Review getAlpacaPositions - fetches current portfolio positions from Alpaca
// - Returns array of positions with symbol, quantity, and market value
async function getAlpacaPositions(credentials: { apiKey: string; secretKey: string; baseUrl: string }) {
  const response = await fetch(`${credentials.baseUrl}/v2/positions`, {
    headers: {
      'APCA-API-KEY-ID': credentials.apiKey,
      'APCA-API-SECRET-KEY': credentials.secretKey
    }
  })

  if (!response.ok) {
    throw new Error(`Alpaca positions error: ${response.status}`)
  }

  return response.json()
}

// TODO: Review getQuote - fetches latest quote for a ticker from Alpaca data API
// - Returns ask price (ap) or bid price (bp), null on failure
async function getQuote(
  ticker: string,
  credentials: { apiKey: string; secretKey: string; dataUrl: string }
) {
  const response = await fetch(`${credentials.dataUrl}/v2/stocks/${ticker}/quotes/latest`, {
    headers: {
      'APCA-API-KEY-ID': credentials.apiKey,
      'APCA-API-SECRET-KEY': credentials.secretKey
    }
  })

  if (!response.ok) {
    return null
  }

  const data = await response.json()
  return data.quote?.ap || data.quote?.bp || null
}

// TODO: Review serve handler - main entry point for strategy subscription management
// - Routes to: get-subscription, subscribe, unsubscribe, sync-now, get-trades, sync-all-active
// - Validates user auth for user actions, service role key for scheduled actions
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

    // Check for service role key for scheduled actions (sync-all-active)
    const authHeader = req.headers.get('authorization')
    const serviceRoleKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')
    const isServiceCall = authHeader?.replace('Bearer ', '') === serviceRoleKey

    // Handle service-level actions (called by scheduler)
    if (action === 'sync-all-active') {
      if (!isServiceCall) {
        return new Response(
          JSON.stringify({ error: 'Service authentication required for this action' }),
          { status: 403, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }
      log.info('Processing scheduled sync for all active subscriptions', { requestId })
      const response = await handleSyncAllActive(supabaseClient, requestId)
      log.info('Request completed', { requestId, duration: Date.now() - startTime })
      return response
    }

    // Validate user authentication for all other actions
    if (!authHeader) {
      return new Response(
        JSON.stringify({ error: 'Authentication required' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get user from JWT
    const { data: { user }, error: authError } = await supabaseClient.auth.getUser(
      authHeader.replace('Bearer ', '')
    )

    if (authError || !user?.email) {
      return new Response(
        JSON.stringify({ error: 'Invalid authentication' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const userEmail = user.email

    log.info('Processing action', { requestId, action, userEmail })

    let response: Response

    switch (action) {
      case 'get-subscription':
        response = await handleGetSubscription(supabaseClient, requestId, userEmail)
        break
      case 'subscribe':
        response = await handleSubscribe(supabaseClient, requestId, userEmail, bodyParams)
        break
      case 'unsubscribe':
        response = await handleUnsubscribe(supabaseClient, requestId, userEmail)
        break
      case 'sync-now':
        response = await handleSyncNow(supabaseClient, requestId, userEmail, bodyParams)
        break
      case 'get-trades':
        response = await handleGetTrades(supabaseClient, requestId, userEmail, bodyParams)
        break
      default:
        response = await handleGetSubscription(supabaseClient, requestId, userEmail)
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
// GET SUBSCRIPTION - Get user's current strategy subscription
// =============================================================================
// TODO: Review handleGetSubscription - retrieves user's active strategy subscription
// - Calls get_user_subscription RPC function
// - Returns subscription details and isFollowing status
async function handleGetSubscription(supabaseClient: any, requestId: string, userEmail: string) {
  try {
    const { data: subscription, error } = await supabaseClient
      .rpc('get_user_subscription', { user_email_param: userEmail })

    if (error) {
      log.error('Failed to fetch subscription', error, { requestId })
      return new Response(
        JSON.stringify({ error: 'Failed to fetch subscription' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // get_user_subscription returns a table result (array), get first row
    const sub = subscription && subscription.length > 0 ? subscription[0] : null

    return new Response(
      JSON.stringify({
        success: true,
        subscription: sub,
        isFollowing: !!sub && sub.is_active
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    log.error('Error in handleGetSubscription', error, { requestId })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}

// =============================================================================
// SUBSCRIBE - Create or update strategy subscription
// =============================================================================
// TODO: Review handleSubscribe - creates/updates user's strategy subscription
// - Supports reference, preset, or custom strategy types
// - Validates Alpaca credentials before creating subscription
// - Upserts to user_strategy_subscriptions table
async function handleSubscribe(
  supabaseClient: any,
  requestId: string,
  userEmail: string,
  bodyParams: any
) {
  try {
    const {
      strategyType,
      presetId,
      customWeights,
      tradingMode = 'paper',
      syncExistingPositions = false
    } = bodyParams

    // Validate strategy type
    if (!['reference', 'preset', 'custom'].includes(strategyType)) {
      return new Response(
        JSON.stringify({ error: 'Invalid strategy type. Must be reference, preset, or custom.' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Validate preset ID if type is preset
    if (strategyType === 'preset' && !presetId) {
      return new Response(
        JSON.stringify({ error: 'Preset ID required for preset strategy type' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Validate custom weights if type is custom
    if (strategyType === 'custom' && !customWeights) {
      return new Response(
        JSON.stringify({ error: 'Custom weights required for custom strategy type' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Check if user has Alpaca credentials for the trading mode
    const credentials = await getAlpacaCredentials(supabaseClient, userEmail, tradingMode)
    if (!credentials) {
      return new Response(
        JSON.stringify({
          error: `No Alpaca ${tradingMode} trading credentials found. Please connect your Alpaca account first.`
        }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Verify credentials work
    try {
      await getAlpacaAccount(credentials)
    } catch (err) {
      return new Response(
        JSON.stringify({
          error: `Failed to verify Alpaca credentials: ${err.message}`
        }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    log.info('Creating/updating subscription', {
      requestId,
      userEmail,
      strategyType,
      presetId,
      tradingMode,
      syncExistingPositions
    })

    // Upsert subscription (only one per user)
    const { data: subscription, error: upsertError } = await supabaseClient
      .from('user_strategy_subscriptions')
      .upsert({
        user_email: userEmail,
        strategy_type: strategyType,
        preset_id: strategyType === 'preset' ? presetId : null,
        custom_weights: strategyType === 'custom' ? customWeights : null,
        trading_mode: tradingMode,
        is_active: true,
        sync_existing_positions: syncExistingPositions,
        updated_at: new Date().toISOString()
      }, { onConflict: 'user_email' })
      .select()
      .single()

    if (upsertError) {
      log.error('Failed to create subscription', upsertError, { requestId })
      return new Response(
        JSON.stringify({ error: 'Failed to create subscription' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get strategy name for display
    let strategyName = 'Reference Strategy'
    if (strategyType === 'preset' && presetId) {
      const { data: preset } = await supabaseClient
        .from('signal_weight_presets')
        .select('name')
        .eq('id', presetId)
        .single()
      strategyName = preset?.name || 'Custom Preset'
    } else if (strategyType === 'custom') {
      strategyName = 'Custom Weights'
    }

    // If sync_existing_positions is enabled, trigger initial sync
    if (syncExistingPositions) {
      // This will be handled by sync-now action
      log.info('Initial sync requested, will sync on next call', { requestId })
    }

    return new Response(
      JSON.stringify({
        success: true,
        message: `Successfully subscribed to ${strategyName}`,
        subscription: {
          ...subscription,
          strategy_name: strategyName
        }
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    log.error('Error in handleSubscribe', error, { requestId })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}

// =============================================================================
// UNSUBSCRIBE - Deactivate strategy subscription
// =============================================================================
// TODO: Review handleUnsubscribe - deactivates user's strategy subscription
// - Sets is_active to false rather than deleting the record
async function handleUnsubscribe(supabaseClient: any, requestId: string, userEmail: string) {
  try {
    const { error } = await supabaseClient
      .from('user_strategy_subscriptions')
      .update({
        is_active: false,
        updated_at: new Date().toISOString()
      })
      .eq('user_email', userEmail)

    if (error) {
      log.error('Failed to unsubscribe', error, { requestId })
      return new Response(
        JSON.stringify({ error: 'Failed to unsubscribe' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    return new Response(
      JSON.stringify({
        success: true,
        message: 'Successfully unsubscribed from strategy'
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    log.error('Error in handleUnsubscribe', error, { requestId })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}

// =============================================================================
// SYNC NOW - Manually trigger position sync with followed strategy
// =============================================================================
// TODO: Review handleSyncNow - manually triggers portfolio sync with subscribed strategy
// - Validates market is open (unless force=true)
// - Calculates target allocations based on strategy type
// - Executes rebalancing trades (buy under-allocated, sell over-allocated)
// - Records trade history in user_strategy_trades table
async function handleSyncNow(
  supabaseClient: any,
  requestId: string,
  userEmail: string,
  bodyParams: any
) {
  try {
    // Get user's subscription
    const { data: subscriptions } = await supabaseClient
      .rpc('get_user_subscription', { user_email_param: userEmail })

    const subscription = subscriptions && subscriptions.length > 0 ? subscriptions[0] : null

    if (!subscription || !subscription.is_active) {
      return new Response(
        JSON.stringify({ error: 'No active subscription found' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const tradingMode = subscription.trading_mode as 'paper' | 'live'

    // Check if market is open (skip for force sync)
    const forceSync = bodyParams?.force === true
    if (!forceSync && !isMarketOpen()) {
      return new Response(
        JSON.stringify({
          success: false,
          error: 'Market is currently closed',
          message: 'Trades can only be executed during market hours (9:30 AM - 4:00 PM ET, Mon-Fri)'
        }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get Alpaca credentials
    const credentials = await getAlpacaCredentials(supabaseClient, userEmail, tradingMode)
    if (!credentials) {
      return new Response(
        JSON.stringify({ error: 'Alpaca credentials not found' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    log.info('Starting strategy sync', {
      requestId,
      userEmail,
      strategyType: subscription.strategy_type,
      tradingMode
    })

    // Get user's account info and validate it can trade
    const account = await getAlpacaAccount(credentials)
    const accountStatus = canAccountTrade(account)
    if (!accountStatus.canTrade) {
      return new Response(
        JSON.stringify({
          success: false,
          error: accountStatus.reason,
          message: `Cannot execute trades: ${accountStatus.reason}`
        }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const userEquity = parseFloat(account.equity)
    const buyingPower = parseFloat(account.buying_power)

    // Get user's current positions
    const userPositions = await getAlpacaPositions(credentials)
    const userPositionMap = new Map(
      userPositions.map((p: any) => [p.symbol, {
        qty: parseInt(p.qty),
        marketValue: parseFloat(p.market_value)
      }])
    )

    // Get target allocations based on strategy type
    let targetAllocations: Map<string, number> = new Map()

    if (subscription.strategy_type === 'reference') {
      // Get reference portfolio positions
      const { data: refPositions } = await supabaseClient
        .from('reference_portfolio_positions')
        .select('ticker, market_value')
        .eq('is_open', true)

      // Get reference portfolio total value
      const { data: refState } = await supabaseClient
        .from('reference_portfolio_state')
        .select('portfolio_value')
        .single()

      const refTotalValue = refState?.portfolio_value || 100000

      // Calculate allocation percentages
      if (refPositions) {
        for (const pos of refPositions) {
          const allocPct = pos.market_value / refTotalValue
          targetAllocations.set(pos.ticker.toUpperCase(), allocPct)
        }
      }
    } else if (subscription.strategy_type === 'preset' || subscription.strategy_type === 'custom') {
      // For preset/custom strategies, get signals generated with those weights
      // Call the trading-signals preview function
      const weights = subscription.strategy_type === 'custom'
        ? subscription.custom_weights
        : await getPresetWeights(supabaseClient, subscription.preset_id)

      if (weights) {
        // Fetch preview signals
        const signalResponse = await fetch(
          `${Deno.env.get('SUPABASE_URL')}/functions/v1/trading-signals/preview-signals`,
          {
            method: 'POST',
            headers: {
              'apikey': Deno.env.get('SUPABASE_ANON_KEY') || '',
              'Authorization': `Bearer ${Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              weights,
              lookbackDays: 90,
              useML: true
            })
          }
        )

        if (signalResponse.ok) {
          const signalData = await signalResponse.json()
          const signals = signalData.signals || []

          // Only use buy/strong_buy signals with good confidence
          const buySignals = signals.filter((s: any) =>
            ['buy', 'strong_buy'].includes(s.signal_type) &&
            s.confidence_score >= 0.6
          )

          // Equal weight among selected signals (max 10 positions)
          const maxPositions = Math.min(buySignals.length, 10)
          const allocPerPosition = 0.1 // 10% per position

          for (let i = 0; i < maxPositions; i++) {
            targetAllocations.set(buySignals[i].ticker.toUpperCase(), allocPerPosition)
          }
        }
      }
    }

    log.info('Target allocations calculated', {
      requestId,
      targetCount: targetAllocations.size,
      targets: Array.from(targetAllocations.entries())
    })

    // Calculate required trades
    const trades: Array<{
      ticker: string
      side: 'buy' | 'sell'
      quantity: number
      reason: string
    }> = []

    // Check positions to sell (not in target or over-allocated)
    for (const [ticker, position] of userPositionMap) {
      const targetAlloc = targetAllocations.get(ticker) || 0
      const currentAlloc = position.marketValue / userEquity

      if (targetAlloc === 0) {
        // Sell entire position - not in strategy
        trades.push({
          ticker,
          side: 'sell',
          quantity: position.qty,
          reason: 'Position not in strategy'
        })
      } else if (currentAlloc > targetAlloc * 1.1) {
        // Over-allocated by more than 10%, reduce
        const targetValue = userEquity * targetAlloc
        const currentPrice = position.marketValue / position.qty
        const targetQty = Math.floor(targetValue / currentPrice)
        const sellQty = position.qty - targetQty

        if (sellQty > 0) {
          trades.push({
            ticker,
            side: 'sell',
            quantity: sellQty,
            reason: 'Rebalancing - over-allocated'
          })
        }
      }
    }

    // Check positions to buy (new or under-allocated)
    for (const [ticker, targetAlloc] of targetAllocations) {
      const currentPosition = userPositionMap.get(ticker)
      const currentAlloc = currentPosition
        ? currentPosition.marketValue / userEquity
        : 0

      if (currentAlloc < targetAlloc * 0.9) {
        // Under-allocated by more than 10%, buy more
        const targetValue = userEquity * targetAlloc
        const currentValue = currentPosition?.marketValue || 0
        const buyValue = targetValue - currentValue

        if (buyValue > 100 && buyValue <= buyingPower) { // Min $100 trade
          // Get current price
          const price = await getQuote(ticker, credentials as any)
          if (price && price > 0) {
            const buyQty = Math.floor(buyValue / price)
            if (buyQty > 0) {
              trades.push({
                ticker,
                side: 'buy',
                quantity: buyQty,
                reason: currentPosition ? 'Rebalancing - under-allocated' : 'New position'
              })
            }
          }
        }
      }
    }

    log.info('Trades calculated', {
      requestId,
      tradeCount: trades.length,
      trades
    })

    // Execute trades
    let executed = 0
    let failed = 0
    const results: any[] = []

    for (const trade of trades) {
      try {
        // Place order with Alpaca
        const orderResponse = await fetch(`${credentials.baseUrl}/v2/orders`, {
          method: 'POST',
          headers: {
            'APCA-API-KEY-ID': credentials.apiKey,
            'APCA-API-SECRET-KEY': credentials.secretKey,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            symbol: trade.ticker,
            qty: trade.quantity,
            side: trade.side,
            type: 'market',
            time_in_force: 'day'
          })
        })

        const orderResult = await orderResponse.json()

        if (!orderResponse.ok) {
          log.warn('Order failed', { ticker: trade.ticker, error: orderResult })
          failed++
          results.push({
            ...trade,
            success: false,
            error: orderResult.message || 'Order rejected'
          })

          // Record failed trade
          await supabaseClient
            .from('user_strategy_trades')
            .insert({
              subscription_id: subscription.id,
              user_email: userEmail,
              ticker: trade.ticker,
              side: trade.side,
              quantity: trade.quantity,
              status: 'failed',
              error_message: orderResult.message || 'Order rejected'
            })

          continue
        }

        log.info('Order placed', {
          requestId,
          ticker: trade.ticker,
          side: trade.side,
          qty: trade.quantity,
          orderId: orderResult.id
        })

        executed++
        results.push({
          ...trade,
          success: true,
          orderId: orderResult.id
        })

        // Record successful trade
        await supabaseClient
          .from('user_strategy_trades')
          .insert({
            subscription_id: subscription.id,
            user_email: userEmail,
            ticker: trade.ticker,
            side: trade.side,
            quantity: trade.quantity,
            status: 'submitted',
            alpaca_order_id: orderResult.id,
            executed_at: new Date().toISOString()
          })

        // Small delay between orders
        await new Promise(resolve => setTimeout(resolve, 100))

      } catch (err) {
        log.error('Error executing trade', err, { requestId, ticker: trade.ticker })
        failed++
        results.push({
          ...trade,
          success: false,
          error: err.message
        })
      }
    }

    // Update last synced timestamp
    await supabaseClient
      .from('user_strategy_subscriptions')
      .update({
        last_synced_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      })
      .eq('user_email', userEmail)

    return new Response(
      JSON.stringify({
        success: true,
        message: `Sync completed: ${executed} trades executed, ${failed} failed`,
        summary: {
          tradesPlanned: trades.length,
          executed,
          failed
        },
        results
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    log.error('Error in handleSyncNow', error, { requestId })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}

// TODO: Review getPresetWeights - retrieves signal weights from a preset configuration
// - Fetches from signal_weight_presets table by ID
// - Returns weight parameters for signal generation
async function getPresetWeights(supabaseClient: any, presetId: string) {
  const { data: preset } = await supabaseClient
    .from('signal_weight_presets')
    .select('*')
    .eq('id', presetId)
    .single()

  if (!preset) return null

  return {
    base_confidence: preset.base_confidence,
    politician_count_5_plus: preset.politician_count_5_plus,
    politician_count_3_4: preset.politician_count_3_4,
    politician_count_2: preset.politician_count_2,
    recent_activity_5_plus: preset.recent_activity_5_plus,
    recent_activity_2_4: preset.recent_activity_2_4,
    bipartisan_bonus: preset.bipartisan_bonus,
    volume_1m_plus: preset.volume_1m_plus,
    volume_100k_plus: preset.volume_100k_plus,
    strong_signal_bonus: preset.strong_signal_bonus,
    moderate_signal_bonus: preset.moderate_signal_bonus,
    strong_buy_threshold: preset.strong_buy_threshold,
    buy_threshold: preset.buy_threshold,
    strong_sell_threshold: preset.strong_sell_threshold,
    sell_threshold: preset.sell_threshold
  }
}

// =============================================================================
// GET TRADES - Get user's strategy trade history
// =============================================================================
// TODO: Review handleGetTrades - retrieves user's strategy trade history
// - Calls get_recent_strategy_trades RPC function with configurable limit
async function handleGetTrades(
  supabaseClient: any,
  requestId: string,
  userEmail: string,
  bodyParams: any
) {
  try {
    const limit = bodyParams.limit || 20

    const { data: trades, error } = await supabaseClient
      .rpc('get_recent_strategy_trades', {
        user_email_param: userEmail,
        limit_param: limit
      })

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
        count: trades?.length || 0
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
// SYNC ALL ACTIVE - Scheduled job to sync all active subscriptions
// =============================================================================
// TODO: Review handleSyncAllActive - scheduled job to sync all active user subscriptions
// - Requires service role authentication
// - Checks market is open before processing
// - Iterates all active subscriptions with 500ms rate limiting
async function handleSyncAllActive(supabaseClient: any, requestId: string) {
  try {
    // Check if market is open first
    if (!isMarketOpen()) {
      log.info('Market closed, skipping scheduled sync', { requestId })
      return new Response(
        JSON.stringify({
          success: true,
          message: 'Market is closed, no syncs performed',
          summary: { skipped: true, reason: 'market_closed' }
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get all active subscriptions
    const { data: subscriptions, error: subError } = await supabaseClient
      .from('user_strategy_subscriptions')
      .select('user_email, strategy_type, trading_mode')
      .eq('is_active', true)

    if (subError) {
      log.error('Failed to fetch active subscriptions', subError, { requestId })
      return new Response(
        JSON.stringify({ error: 'Failed to fetch subscriptions' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    if (!subscriptions || subscriptions.length === 0) {
      log.info('No active subscriptions to sync', { requestId })
      return new Response(
        JSON.stringify({
          success: true,
          message: 'No active subscriptions to sync',
          summary: { processed: 0, succeeded: 0, failed: 0 }
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    log.info('Starting sync for active subscriptions', {
      requestId,
      count: subscriptions.length
    })

    // Process each subscription
    const results: Array<{
      userEmail: string;
      success: boolean;
      error?: string;
      tradesPlanned?: number;
      tradesExecuted?: number;
      tradesFailed?: number;
    }> = []
    let succeeded = 0
    let failed = 0
    let totalTradesExecuted = 0
    let totalTradesFailed = 0

    for (const sub of subscriptions) {
      try {
        // Call internal sync function directly (bypass Response parsing)
        const syncResult = await performSyncForUser(supabaseClient, requestId, sub.user_email)
        results.push({
          userEmail: sub.user_email,
          success: syncResult.success,
          error: syncResult.error,
          tradesPlanned: syncResult.trades,
          tradesExecuted: syncResult.executed,
          tradesFailed: syncResult.failed
        })
        if (syncResult.success) {
          succeeded++
          totalTradesExecuted += syncResult.executed || 0
          totalTradesFailed += syncResult.failed || 0
        } else {
          failed++
        }
      } catch (err) {
        log.error('Error syncing user', err, { requestId, userEmail: sub.user_email })
        results.push({ userEmail: sub.user_email, success: false, error: err.message })
        failed++
      }

      // Rate limit: 500ms between users to avoid Alpaca API throttling
      await new Promise(resolve => setTimeout(resolve, 500))
    }

    log.info('Scheduled sync completed', {
      requestId,
      processed: subscriptions.length,
      succeeded,
      failed,
      totalTradesExecuted,
      totalTradesFailed
    })

    return new Response(
      JSON.stringify({
        success: true,
        message: `Synced ${succeeded}/${subscriptions.length} subscriptions, ${totalTradesExecuted} trades executed`,
        summary: {
          subscriptionsProcessed: subscriptions.length,
          subscriptionsSucceeded: succeeded,
          subscriptionsFailed: failed,
          totalTradesExecuted,
          totalTradesFailed
        },
        results
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    log.error('Error in handleSyncAllActive', error, { requestId })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}

// TODO: Review performSyncForUser - internal sync implementation for scheduled jobs
// - Performs full trade execution (same logic as handleSyncNow)
// - Returns structured result instead of Response for batch processing
// - Calculates target allocations, computes trades, and executes orders
async function performSyncForUser(
  supabaseClient: any,
  requestId: string,
  userEmail: string
): Promise<{ success: boolean; error?: string; executed?: number; failed?: number; trades?: number }> {
  try {
    // Get subscription
    const { data: subscriptions } = await supabaseClient
      .rpc('get_user_subscription', { user_email_param: userEmail })

    const subscription = subscriptions?.[0]
    if (!subscription?.is_active) {
      return { success: false, error: 'No active subscription' }
    }

    const tradingMode = subscription.trading_mode as 'paper' | 'live'

    // Get credentials
    const credentials = await getAlpacaCredentials(supabaseClient, userEmail, tradingMode)
    if (!credentials) {
      return { success: false, error: 'No Alpaca credentials' }
    }

    // Get account and validate
    const account = await getAlpacaAccount(credentials)
    const accountStatus = canAccountTrade(account)
    if (!accountStatus.canTrade) {
      return { success: false, error: accountStatus.reason }
    }

    const userEquity = parseFloat(account.equity)
    const buyingPower = parseFloat(account.buying_power)

    // Get user's current positions
    const userPositions = await getAlpacaPositions(credentials)
    const userPositionMap = new Map(
      userPositions.map((p: any) => [p.symbol, {
        qty: parseInt(p.qty),
        marketValue: parseFloat(p.market_value)
      }])
    )

    // Get target allocations based on strategy type
    let targetAllocations: Map<string, number> = new Map()

    if (subscription.strategy_type === 'reference') {
      // Get reference portfolio positions
      const { data: refPositions } = await supabaseClient
        .from('reference_portfolio_positions')
        .select('ticker, market_value')
        .eq('is_open', true)

      // Get reference portfolio total value
      const { data: refState } = await supabaseClient
        .from('reference_portfolio_state')
        .select('portfolio_value')
        .single()

      const refTotalValue = refState?.portfolio_value || 100000

      // Calculate allocation percentages
      if (refPositions) {
        for (const pos of refPositions) {
          const allocPct = pos.market_value / refTotalValue
          targetAllocations.set(pos.ticker.toUpperCase(), allocPct)
        }
      }
    } else if (subscription.strategy_type === 'preset' || subscription.strategy_type === 'custom') {
      const weights = subscription.strategy_type === 'custom'
        ? subscription.custom_weights
        : await getPresetWeights(supabaseClient, subscription.preset_id)

      if (weights) {
        const signalResponse = await fetch(
          `${Deno.env.get('SUPABASE_URL')}/functions/v1/trading-signals/preview-signals`,
          {
            method: 'POST',
            headers: {
              'apikey': Deno.env.get('SUPABASE_ANON_KEY') || '',
              'Authorization': `Bearer ${Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ weights, lookbackDays: 90, useML: true })
          }
        )

        if (signalResponse.ok) {
          const signalData = await signalResponse.json()
          const signals = signalData.signals || []
          const buySignals = signals.filter((s: any) =>
            ['buy', 'strong_buy'].includes(s.signal_type) && s.confidence_score >= 0.6
          )
          const maxPositions = Math.min(buySignals.length, 10)
          const allocPerPosition = 0.1

          for (let i = 0; i < maxPositions; i++) {
            targetAllocations.set(buySignals[i].ticker.toUpperCase(), allocPerPosition)
          }
        }
      }
    }

    // Calculate required trades
    const trades: Array<{ ticker: string; side: 'buy' | 'sell'; quantity: number; reason: string }> = []

    // Positions to sell
    for (const [ticker, position] of userPositionMap) {
      const targetAlloc = targetAllocations.get(ticker) || 0
      const currentAlloc = position.marketValue / userEquity

      if (targetAlloc === 0) {
        trades.push({ ticker, side: 'sell', quantity: position.qty, reason: 'Position not in strategy' })
      } else if (currentAlloc > targetAlloc * 1.1) {
        const targetValue = userEquity * targetAlloc
        const currentPrice = position.marketValue / position.qty
        const targetQty = Math.floor(targetValue / currentPrice)
        const sellQty = position.qty - targetQty
        if (sellQty > 0) {
          trades.push({ ticker, side: 'sell', quantity: sellQty, reason: 'Rebalancing - over-allocated' })
        }
      }
    }

    // Positions to buy
    for (const [ticker, targetAlloc] of targetAllocations) {
      const currentPosition = userPositionMap.get(ticker)
      const currentAlloc = currentPosition ? currentPosition.marketValue / userEquity : 0

      if (currentAlloc < targetAlloc * 0.9) {
        const targetValue = userEquity * targetAlloc
        const currentValue = currentPosition?.marketValue || 0
        const buyValue = targetValue - currentValue

        if (buyValue > 100 && buyValue <= buyingPower) {
          const price = await getQuote(ticker, credentials as any)
          if (price && price > 0) {
            const buyQty = Math.floor(buyValue / price)
            if (buyQty > 0) {
              trades.push({ ticker, side: 'buy', quantity: buyQty, reason: currentPosition ? 'Rebalancing' : 'New position' })
            }
          }
        }
      }
    }

    log.info('Scheduled sync trades calculated', { requestId, userEmail, tradeCount: trades.length })

    // Execute trades
    let executed = 0
    let failed = 0

    for (const trade of trades) {
      try {
        const orderResponse = await fetch(`${credentials.baseUrl}/v2/orders`, {
          method: 'POST',
          headers: {
            'APCA-API-KEY-ID': credentials.apiKey,
            'APCA-API-SECRET-KEY': credentials.secretKey,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            symbol: trade.ticker,
            qty: trade.quantity,
            side: trade.side,
            type: 'market',
            time_in_force: 'day'
          })
        })

        const orderResult = await orderResponse.json()

        if (!orderResponse.ok) {
          failed++
          await supabaseClient.from('user_strategy_trades').insert({
            subscription_id: subscription.id,
            user_email: userEmail,
            ticker: trade.ticker,
            side: trade.side,
            quantity: trade.quantity,
            status: 'failed',
            error_message: orderResult.message || 'Order rejected'
          })
        } else {
          executed++
          await supabaseClient.from('user_strategy_trades').insert({
            subscription_id: subscription.id,
            user_email: userEmail,
            ticker: trade.ticker,
            side: trade.side,
            quantity: trade.quantity,
            status: 'submitted',
            alpaca_order_id: orderResult.id,
            executed_at: new Date().toISOString()
          })
        }

        // Rate limit between orders
        await new Promise(resolve => setTimeout(resolve, 100))
      } catch (err) {
        failed++
        log.error('Trade execution error', err, { requestId, userEmail, ticker: trade.ticker })
      }
    }

    // Update last synced timestamp
    await supabaseClient
      .from('user_strategy_subscriptions')
      .update({ last_synced_at: new Date().toISOString(), updated_at: new Date().toISOString() })
      .eq('user_email', userEmail)

    log.info('Scheduled sync completed for user', { requestId, userEmail, executed, failed, trades: trades.length })
    return { success: true, executed, failed, trades: trades.length }

  } catch (err) {
    log.error('performSyncForUser error', err, { requestId, userEmail })
    return { success: false, error: err.message }
  }
}
