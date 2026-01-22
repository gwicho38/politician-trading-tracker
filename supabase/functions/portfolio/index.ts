import { createClient } from 'supabase'
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

// TODO: Review isServiceRoleRequest - checks if request uses service role key for scheduled jobs
function isServiceRoleRequest(req: Request): boolean {
  const authHeader = req.headers.get('authorization')
  if (!authHeader) return false

  const token = authHeader.replace('Bearer ', '')
  const serviceRoleKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') || ''

  return token === serviceRoleKey
}

// TODO: Review log object - structured JSON logging with levels (info, error, warn)
const log = {
  info: (message: string, metadata?: any) => {
    console.log(JSON.stringify({
      level: 'INFO',
      timestamp: new Date().toISOString(),
      service: 'portfolio',
      message,
      ...metadata
    }))
  },
  error: (message: string, error?: any, metadata?: any) => {
    console.error(JSON.stringify({
      level: 'ERROR',
      timestamp: new Date().toISOString(),
      service: 'portfolio',
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
      service: 'portfolio',
      message,
      ...metadata
    }))
  }
}

// TODO: Review sanitizeRequestForLogging - redacts sensitive headers for logging
function sanitizeRequestForLogging(req: Request): any {
  const headers = Object.fromEntries(req.headers.entries())

  // Remove sensitive headers
  const sensitiveHeaders = ['authorization', 'x-api-key', 'cookie', 'x-supabase-auth']
  sensitiveHeaders.forEach(header => {
    if (headers[header]) {
      headers[header] = '[REDACTED]'
    }
  })

  return {
    method: req.method,
    url: req.url,
    headers,
    contentType: req.headers.get('content-type'),
    userAgent: req.headers.get('user-agent'),
    origin: req.headers.get('origin'),
    referer: req.headers.get('referer')
  }
}

// TODO: Review sanitizeResponseForLogging - truncates response body for logging
function sanitizeResponseForLogging(response: Response, body?: any): any {
  return {
    status: response.status,
    statusText: response.statusText,
    headers: Object.fromEntries(response.headers.entries()),
    contentType: response.headers.get('content-type'),
    contentLength: response.headers.get('content-length'),
    body: body ? JSON.stringify(body).substring(0, 500) + (JSON.stringify(body).length > 500 ? '...' : '') : null
  }
}

// TODO: Review serve handler - portfolio management endpoint
// - Actions: get-portfolio, get-account-info, place-order, sync-positions, reconcile-positions
// - Supports user-specific and service role authentication
serve(async (req) => {
  const startTime = Date.now()
  const requestId = crypto.randomUUID().substring(0, 8)

  // Log full request details
  const requestDetails = sanitizeRequestForLogging(req)
  log.info('Request received', {
    requestId,
    request: requestDetails,
    ip: req.headers.get('x-forwarded-for') || req.headers.get('cf-connecting-ip')
  })

  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    log.info('CORS preflight handled', { requestId })
    const corsResponse = new Response('ok', { headers: corsHeaders })
    log.info('Response sent', {
      requestId,
      response: sanitizeResponseForLogging(corsResponse, 'ok'),
      duration: Date.now() - startTime
    })
    return corsResponse
  }

  try {
    // Initialize Supabase client with service role key
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const url = new URL(req.url)
    let path = url.pathname.split('/').pop()

    // Also check for action in request body (for supabase.functions.invoke)
    let action = path
    if (req.method === 'POST') {
      try {
        const body = await req.clone().json()
        if (body.action) {
          action = body.action
        }
      } catch {
        // Body parsing failed, use path
      }
    }

    log.info('Processing request', {
      requestId,
      path,
      action,
      queryParams: Object.fromEntries(url.searchParams)
    })

    let response: Response

    // Parse body for POST requests
    let bodyParams: any = {}
    if (req.method === 'POST') {
      try {
        bodyParams = await req.clone().json()
        if (bodyParams.action) {
          action = bodyParams.action
        }
      } catch {
        // Body parsing failed, use path
      }
    }

    switch (action) {
      case 'get-portfolio':
      case 'portfolio':
      case '':
      case undefined:
        // Default action - get portfolio
        response = await handleGetPortfolio(supabaseClient, req, requestId)
        break
      case 'get-account-info':
        response = await handleGetAccountInfo(supabaseClient, req, requestId)
        break
      case 'place-order':
        response = await handlePlaceOrder(supabaseClient, req, requestId, bodyParams)
        break
      case 'reconcile-positions':
        response = await handleReconcilePositions(supabaseClient, req, requestId, bodyParams)
        break
      case 'sync-positions':
        response = await handleSyncPositions(supabaseClient, req, requestId, bodyParams)
        break
      default:
        log.warn('Invalid endpoint requested', { requestId, path, action })
        response = new Response(
          JSON.stringify({ error: 'Invalid endpoint', debug: { path, action } }),
          {
            status: 404,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          }
        )
        break
    }

    const duration = Date.now() - startTime

    // Try to parse response body for logging (if JSON)
    let responseBody = null
    if (response.headers.get('content-type')?.includes('application/json')) {
      try {
        // Clone response to read body without consuming it
        const responseClone = response.clone()
        responseBody = await responseClone.json()
      } catch (e) {
        // If we can't parse JSON, just log that it's not JSON
        responseBody = '[NON-JSON RESPONSE]'
      }
    }

    log.info('Response sent', {
      requestId,
      response: sanitizeResponseForLogging(response, responseBody),
      duration
    })

    return response

  } catch (error) {
    const duration = Date.now() - startTime
    const errorResponse = new Response(
      JSON.stringify({ error: error.message }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )

    log.error('Edge function error', error, {
      requestId,
      request: sanitizeRequestForLogging(req),
      response: sanitizeResponseForLogging(errorResponse, { error: error.message }),
      duration
    })

    return errorResponse
  }
})

// TODO: Review handleGetPortfolio - fetches user's open positions
// - Returns positions sorted by market value
async function handleGetPortfolio(supabaseClient: any, req: Request, requestId: string) {
  const handlerStartTime = Date.now()

  try {
    const url = new URL(req.url)
    const tradingMode = url.searchParams.get('trading_mode') || 'paper'

    log.info('Fetching portfolio - handler started', {
      requestId,
      handler: 'get-portfolio',
      params: { tradingMode },
      request: sanitizeRequestForLogging(req)
    })

    // Check if this is a service role request (scheduled job)
    const isServerRequest = isServiceRoleRequest(req)

    if (isServerRequest) {
      log.info('Service role request (scheduled job)', { requestId })
    } else {
      // Validate authentication for client requests
      const authHeader = req.headers.get('authorization')
      if (!authHeader) {
        return new Response(
          JSON.stringify({ error: 'Authentication required' }),
          {
            status: 401,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          }
        )
      }

      // Get user from JWT
      const { data: { user }, error: authError } = await supabaseClient.auth.getUser(
        authHeader.replace('Bearer ', '')
      )

      if (authError || !user) {
        return new Response(
          JSON.stringify({ error: 'Invalid authentication' }),
          {
            status: 401,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          }
        )
      }

      log.info('User authenticated', { requestId, userId: user.id })
    }

    // Get positions from database (handle case where table doesn't exist yet)
    let positions: any[] = []
    try {
      const { data, error } = await supabaseClient
        .from('positions')
        .select('*')
        .eq('is_open', true)
        .order('market_value', { ascending: false })

      if (error) {
        // Log error but don't fail - table might not exist yet
        log.warn('Could not fetch positions', { error: error.message })
      } else {
        positions = data || []
      }
    } catch (e) {
      log.warn('Exception fetching positions', { error: e.message })
    }

    const responseData = {
      success: true,
      positions
    }

    log.info('Portfolio fetched successfully - handler completed', {
      requestId,
      handler: 'get-portfolio',
      positionCount: positions?.length || 0,
      duration: Date.now() - handlerStartTime,
      response: responseData
    })

    return new Response(
      JSON.stringify(responseData),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  } catch (error) {
    log.error('Error in handleGetPortfolio', error, {
      requestId,
      handler: 'get-portfolio',
      request: sanitizeRequestForLogging(req),
      duration: Date.now() - handlerStartTime
    })

    const errorResponse = new Response(
      JSON.stringify({ error: error.message }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )

    return errorResponse
  }
}

// TODO: Review handlePlaceOrder - places order via Alpaca API
// - Validates order parameters and authentication
// - Saves order to trading_orders table
async function handlePlaceOrder(supabaseClient: any, req: Request, requestId: string, bodyParams: any) {
  const handlerStartTime = Date.now()

  try {
    log.info('Placing order - handler started', {
      requestId,
      handler: 'place-order',
      params: bodyParams
    })

    // Validate authentication
    const authHeader = req.headers.get('authorization')
    if (!authHeader) {
      return new Response(
        JSON.stringify({ error: 'Authentication required' }),
        {
          status: 401,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Get user from JWT
    const { data: { user }, error: authError } = await supabaseClient.auth.getUser(
      authHeader.replace('Bearer ', '')
    )

    if (authError || !user) {
      return new Response(
        JSON.stringify({ error: 'Invalid authentication' }),
        {
          status: 401,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Validate order parameters
    const { ticker, quantity, side, order_type, limit_price, trading_mode } = bodyParams

    if (!ticker || !quantity || !side) {
      return new Response(
        JSON.stringify({ error: 'Missing required fields: ticker, quantity, side' }),
        {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Get Alpaca API credentials from environment
    const alpacaApiKey = Deno.env.get('ALPACA_API_KEY')
    const alpacaSecretKey = Deno.env.get('ALPACA_SECRET_KEY')
    const alpacaPaper = Deno.env.get('ALPACA_PAPER') === 'true'
    const alpacaBaseUrl = Deno.env.get('ALPACA_BASE_URL')

    if (!alpacaApiKey || !alpacaSecretKey) {
      log.error('Missing Alpaca API credentials', { requestId })
      return new Response(
        JSON.stringify({ error: 'Alpaca API credentials not configured' }),
        {
          status: 500,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Prepare Alpaca order payload
    const orderPayload: any = {
      symbol: ticker.toUpperCase(),
      qty: String(quantity),
      side: side.toLowerCase(),
      type: (order_type || 'market').toLowerCase(),
      time_in_force: 'day'
    }

    // Add limit price for limit orders
    if (order_type === 'limit' && limit_price) {
      orderPayload.limit_price = String(limit_price)
    }

    log.info('Calling Alpaca API to place order', { requestId, orderPayload })

    // Call Alpaca API to place order
    const baseUrl = alpacaBaseUrl || (alpacaPaper ? 'https://paper-api.alpaca.markets' : 'https://api.alpaca.markets')
    const alpacaResponse = await fetch(`${baseUrl}/v2/orders`, {
      method: 'POST',
      headers: {
        'APCA-API-KEY-ID': alpacaApiKey,
        'APCA-API-SECRET-KEY': alpacaSecretKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(orderPayload)
    })

    const alpacaData = await alpacaResponse.json()

    if (!alpacaResponse.ok) {
      log.error('Alpaca order placement failed', { requestId, status: alpacaResponse.status, error: alpacaData })
      return new Response(
        JSON.stringify({
          error: alpacaData.message || 'Failed to place order with Alpaca',
          details: alpacaData
        }),
        {
          status: alpacaResponse.status,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    log.info('Alpaca order placed successfully', { requestId, orderId: alpacaData.id })

    // Save order to database
    const orderRecord = {
      user_id: user.id,
      ticker: ticker.toUpperCase(),
      side: side.toLowerCase(),
      quantity: quantity,
      order_type: order_type || 'market',
      limit_price: limit_price || null,
      status: alpacaData.status || 'new',
      filled_qty: parseFloat(alpacaData.filled_qty) || 0,
      filled_avg_price: alpacaData.filled_avg_price ? parseFloat(alpacaData.filled_avg_price) : null,
      trading_mode: trading_mode || 'paper',
      alpaca_order_id: alpacaData.id,
      submitted_at: alpacaData.submitted_at || new Date().toISOString()
    }

    const { data: insertedOrder, error: insertError } = await supabaseClient
      .from('trading_orders')
      .insert(orderRecord)
      .select()
      .single()

    if (insertError) {
      log.warn('Failed to save order to database', { requestId, error: insertError.message })
      // Don't fail the request - order was placed successfully
    } else {
      log.info('Order saved to database', { requestId, orderId: insertedOrder?.id })
    }

    const responseData = {
      success: true,
      order: {
        id: insertedOrder?.id || alpacaData.id,
        alpaca_order_id: alpacaData.id,
        ticker: ticker.toUpperCase(),
        side: side,
        quantity: quantity,
        order_type: order_type || 'market',
        status: alpacaData.status,
        submitted_at: alpacaData.submitted_at
      }
    }

    log.info('Order placed successfully - handler completed', {
      requestId,
      handler: 'place-order',
      duration: Date.now() - handlerStartTime,
      orderId: alpacaData.id
    })

    return new Response(
      JSON.stringify(responseData),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  } catch (error) {
    log.error('Error in handlePlaceOrder', error, {
      requestId,
      handler: 'place-order',
      duration: Date.now() - handlerStartTime
    })

    return new Response(
      JSON.stringify({ error: error.message }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  }
}

// TODO: Review handleGetAccountInfo - returns account info (currently mock data)
async function handleGetAccountInfo(supabaseClient: any, req: Request, requestId: string) {
  try {
    const url = new URL(req.url)
    const tradingMode = url.searchParams.get('trading_mode') || 'paper'

    // Validate authentication
    const authHeader = req.headers.get('authorization')
    if (!authHeader) {
      return new Response(
        JSON.stringify({ error: 'Authentication required' }),
        {
          status: 401,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Get user from JWT
    const { data: { user }, error: authError } = await supabaseClient.auth.getUser(
      authHeader.replace('Bearer ', '')
    )

    if (authError || !user) {
      return new Response(
        JSON.stringify({ error: 'Invalid authentication' }),
        {
          status: 401,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // For now, return mock account data since we don't have real Alpaca integration
    // In a real implementation, this would call the Alpaca API
    const mockAccountInfo = {
      portfolio_value: "125000.00",
      cash: "25000.00",
      buying_power: "50000.00",
      last_equity: "120000.00",
      long_market_value: "100000.00",
      status: "ACTIVE"
    }

    return new Response(
      JSON.stringify({
        success: true,
        account: mockAccountInfo
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  } catch (error) {
    console.error('Error fetching account info:', error)
    return new Response(
      JSON.stringify({ error: error.message }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  }
}

// =============================================================================
// POSITION SYNC HANDLER - Syncs positions from Alpaca to local database
// =============================================================================

// TODO: Review handleSyncPositions - syncs positions from Alpaca to local database
// - Fetches positions from Alpaca API
// - Creates/updates position records in positions table
// - Marks positions as closed if no longer in Alpaca
async function handleSyncPositions(supabaseClient: any, req: Request, requestId: string, bodyParams: any) {
  const handlerStartTime = Date.now()

  try {
    const tradingMode: 'paper' | 'live' = bodyParams.tradingMode || 'paper'

    // Check if this is a service role request (scheduled job)
    const isServerRequest = isServiceRoleRequest(req)

    let userId: string | null = null
    let userEmail: string | null = null

    if (!isServerRequest) {
      // Validate authentication for client requests
      const authHeader = req.headers.get('authorization')
      if (!authHeader) {
        return new Response(
          JSON.stringify({ error: 'Authentication required' }),
          { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }

      const { data: { user }, error: authError } = await supabaseClient.auth.getUser(
        authHeader.replace('Bearer ', '')
      )

      if (authError || !user) {
        return new Response(
          JSON.stringify({ error: 'Invalid authentication' }),
          { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }

      userId = user.id
      userEmail = user.email || null
    }

    log.info('Syncing positions from Alpaca', { requestId, userId, tradingMode })

    // Get Alpaca API credentials
    const alpacaApiKey = Deno.env.get('ALPACA_API_KEY')
    const alpacaSecretKey = Deno.env.get('ALPACA_SECRET_KEY')
    const alpacaPaper = Deno.env.get('ALPACA_PAPER') === 'true'
    const alpacaBaseUrl = Deno.env.get('ALPACA_BASE_URL')

    if (!alpacaApiKey || !alpacaSecretKey) {
      return new Response(
        JSON.stringify({ error: 'Alpaca API credentials not configured' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const baseUrl = alpacaBaseUrl || (alpacaPaper ? 'https://paper-api.alpaca.markets' : 'https://api.alpaca.markets')

    // Fetch positions from Alpaca
    const alpacaResponse = await fetch(`${baseUrl}/v2/positions`, {
      method: 'GET',
      headers: {
        'APCA-API-KEY-ID': alpacaApiKey,
        'APCA-API-SECRET-KEY': alpacaSecretKey,
        'Content-Type': 'application/json'
      }
    })

    if (!alpacaResponse.ok) {
      const errorText = await alpacaResponse.text()
      log.error('Alpaca API error fetching positions', { requestId, status: alpacaResponse.status, error: errorText })
      return new Response(
        JSON.stringify({ error: `Alpaca API error: ${alpacaResponse.status}` }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const alpacaPositions = await alpacaResponse.json()
    log.info('Fetched positions from Alpaca', { requestId, count: alpacaPositions.length })

    // Sync each position
    let synced = 0
    let updated = 0
    let errors = 0

    for (const position of alpacaPositions) {
      try {
        const positionRecord = {
          user_id: userId,
          ticker: position.symbol,
          quantity: parseFloat(position.qty) || 0,
          avg_entry_price: parseFloat(position.avg_entry_price) || 0,
          market_value: parseFloat(position.market_value) || 0,
          cost_basis: parseFloat(position.cost_basis) || 0,
          unrealized_pl: parseFloat(position.unrealized_pl) || 0,
          unrealized_plpc: parseFloat(position.unrealized_plpc) || 0,
          current_price: parseFloat(position.current_price) || 0,
          side: position.side,
          trading_mode: tradingMode,
          is_open: true,
          alpaca_asset_id: position.asset_id,
          last_synced_at: new Date().toISOString()
        }

        // Check if position exists
        const { data: existing } = await supabaseClient
          .from('positions')
          .select('id')
          .eq('ticker', position.symbol)
          .eq('trading_mode', tradingMode)
          .eq('user_id', userId)
          .maybeSingle()

        if (existing) {
          // Update existing
          const { error: updateError } = await supabaseClient
            .from('positions')
            .update(positionRecord)
            .eq('id', existing.id)

          if (updateError) {
            log.warn('Failed to update position', { ticker: position.symbol, error: updateError.message })
            errors++
          } else {
            updated++
          }
        } else {
          // Insert new
          const { error: insertError } = await supabaseClient
            .from('positions')
            .insert(positionRecord)

          if (insertError) {
            log.warn('Failed to insert position', { ticker: position.symbol, error: insertError.message })
            errors++
          } else {
            synced++
          }
        }
      } catch (e) {
        log.error('Error processing position', { ticker: position.symbol, error: e.message })
        errors++
      }
    }

    // Mark positions as closed if not in Alpaca response
    const alpacaSymbols = alpacaPositions.map((p: any) => p.symbol)
    if (userId) {
      const { error: closeError } = await supabaseClient
        .from('positions')
        .update({ is_open: false, closed_at: new Date().toISOString() })
        .eq('user_id', userId)
        .eq('trading_mode', tradingMode)
        .eq('is_open', true)
        .not('ticker', 'in', `(${alpacaSymbols.map((s: string) => `'${s}'`).join(',')})`)

      if (closeError) {
        log.warn('Failed to close stale positions', { error: closeError.message })
      }
    }

    const duration = Date.now() - handlerStartTime

    log.info('Position sync completed', {
      requestId,
      total: alpacaPositions.length,
      synced,
      updated,
      errors,
      duration
    })

    return new Response(
      JSON.stringify({
        success: true,
        message: `Synced ${synced} new positions, updated ${updated}, ${errors} errors`,
        summary: { total: alpacaPositions.length, synced, updated, errors }
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    log.error('Error syncing positions', error, { requestId, duration: Date.now() - handlerStartTime })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}

// =============================================================================
// POSITION RECONCILIATION HANDLER - Detects drift between Alpaca and local
// =============================================================================

// TODO: Review handleReconcilePositions - detects and optionally corrects drift between Alpaca and local
// - Compares quantity, avg_entry_price, market_value between sources
// - Can auto-correct drift if autoCorrect=true
// - Logs health check results to connection_health_log

interface PositionDrift {
  ticker: string
  field: string
  localValue: any
  alpacaValue: any
  difference?: number
}

async function handleReconcilePositions(supabaseClient: any, req: Request, requestId: string, bodyParams: any) {
  const handlerStartTime = Date.now()

  try {
    const tradingMode: 'paper' | 'live' = bodyParams.tradingMode || 'paper'
    const autoCorrect = bodyParams.autoCorrect === true

    // Check if this is a service role request (scheduled job)
    const isServerRequest = isServiceRoleRequest(req)

    let userId: string | null = null

    if (!isServerRequest) {
      const authHeader = req.headers.get('authorization')
      if (!authHeader) {
        return new Response(
          JSON.stringify({ error: 'Authentication required' }),
          { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }

      const { data: { user }, error: authError } = await supabaseClient.auth.getUser(
        authHeader.replace('Bearer ', '')
      )

      if (authError || !user) {
        return new Response(
          JSON.stringify({ error: 'Invalid authentication' }),
          { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }

      userId = user.id
    }

    log.info('Reconciling positions', { requestId, userId, tradingMode, autoCorrect })

    // Get Alpaca credentials
    const alpacaApiKey = Deno.env.get('ALPACA_API_KEY')
    const alpacaSecretKey = Deno.env.get('ALPACA_SECRET_KEY')
    const alpacaPaper = Deno.env.get('ALPACA_PAPER') === 'true'
    const alpacaBaseUrl = Deno.env.get('ALPACA_BASE_URL')

    if (!alpacaApiKey || !alpacaSecretKey) {
      return new Response(
        JSON.stringify({ error: 'Alpaca API credentials not configured' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const baseUrl = alpacaBaseUrl || (alpacaPaper ? 'https://paper-api.alpaca.markets' : 'https://api.alpaca.markets')

    // Fetch positions from Alpaca
    const alpacaResponse = await fetch(`${baseUrl}/v2/positions`, {
      method: 'GET',
      headers: {
        'APCA-API-KEY-ID': alpacaApiKey,
        'APCA-API-SECRET-KEY': alpacaSecretKey,
        'Content-Type': 'application/json'
      }
    })

    if (!alpacaResponse.ok) {
      const errorText = await alpacaResponse.text()
      return new Response(
        JSON.stringify({ error: `Alpaca API error: ${alpacaResponse.status}` }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const alpacaPositions = await alpacaResponse.json()

    // Get local positions
    let localPositionsQuery = supabaseClient
      .from('positions')
      .select('*')
      .eq('trading_mode', tradingMode)
      .eq('is_open', true)

    if (userId) {
      localPositionsQuery = localPositionsQuery.eq('user_id', userId)
    }

    const { data: localPositions, error: localError } = await localPositionsQuery

    if (localError) {
      log.warn('Could not fetch local positions', { error: localError.message })
    }

    // Build maps for comparison
    const alpacaMap = new Map(alpacaPositions.map((p: any) => [p.symbol, p]))
    const localMap = new Map((localPositions || []).map((p: any) => [p.ticker, p]))

    const drifts: PositionDrift[] = []
    const missingLocal: string[] = []
    const missingAlpaca: string[] = []
    let correctedCount = 0

    // Check for drift and missing positions
    for (const [symbol, alpacaPos] of alpacaMap) {
      const localPos = localMap.get(symbol)

      if (!localPos) {
        missingLocal.push(symbol)
        continue
      }

      // Compare key fields
      const alpacaQty = parseFloat(alpacaPos.qty) || 0
      const localQty = localPos.quantity || 0
      if (Math.abs(alpacaQty - localQty) > 0.001) {
        drifts.push({
          ticker: symbol,
          field: 'quantity',
          localValue: localQty,
          alpacaValue: alpacaQty,
          difference: alpacaQty - localQty
        })
      }

      const alpacaAvgPrice = parseFloat(alpacaPos.avg_entry_price) || 0
      const localAvgPrice = localPos.avg_entry_price || 0
      if (Math.abs(alpacaAvgPrice - localAvgPrice) > 0.01) {
        drifts.push({
          ticker: symbol,
          field: 'avg_entry_price',
          localValue: localAvgPrice,
          alpacaValue: alpacaAvgPrice,
          difference: alpacaAvgPrice - localAvgPrice
        })
      }

      const alpacaMarketValue = parseFloat(alpacaPos.market_value) || 0
      const localMarketValue = localPos.market_value || 0
      if (Math.abs(alpacaMarketValue - localMarketValue) > 1) {
        drifts.push({
          ticker: symbol,
          field: 'market_value',
          localValue: localMarketValue,
          alpacaValue: alpacaMarketValue,
          difference: alpacaMarketValue - localMarketValue
        })
      }
    }

    // Check for positions in local but not in Alpaca
    for (const [ticker, localPos] of localMap) {
      if (!alpacaMap.has(ticker)) {
        missingAlpaca.push(ticker)
      }
    }

    // Auto-correct if requested
    if (autoCorrect && (drifts.length > 0 || missingLocal.length > 0 || missingAlpaca.length > 0)) {
      // Sync positions to correct drift
      for (const [symbol, alpacaPos] of alpacaMap) {
        const positionRecord = {
          user_id: userId,
          ticker: symbol,
          quantity: parseFloat(alpacaPos.qty) || 0,
          avg_entry_price: parseFloat(alpacaPos.avg_entry_price) || 0,
          market_value: parseFloat(alpacaPos.market_value) || 0,
          cost_basis: parseFloat(alpacaPos.cost_basis) || 0,
          unrealized_pl: parseFloat(alpacaPos.unrealized_pl) || 0,
          unrealized_plpc: parseFloat(alpacaPos.unrealized_plpc) || 0,
          current_price: parseFloat(alpacaPos.current_price) || 0,
          side: alpacaPos.side,
          trading_mode: tradingMode,
          is_open: true,
          alpaca_asset_id: alpacaPos.asset_id,
          last_synced_at: new Date().toISOString()
        }

        const { error: upsertError } = await supabaseClient
          .from('positions')
          .upsert(positionRecord, { onConflict: 'ticker,trading_mode,user_id' })

        if (!upsertError) {
          correctedCount++
        }
      }

      // Mark missing-in-Alpaca positions as closed
      if (missingAlpaca.length > 0 && userId) {
        await supabaseClient
          .from('positions')
          .update({ is_open: false, closed_at: new Date().toISOString() })
          .eq('user_id', userId)
          .eq('trading_mode', tradingMode)
          .in('ticker', missingAlpaca)
      }

      log.info('Auto-corrected position drift', { requestId, correctedCount })
    }

    // Log health check result
    const healthStatus = drifts.length === 0 && missingLocal.length === 0 && missingAlpaca.length === 0
      ? 'healthy'
      : 'degraded'

    try {
      await supabaseClient
        .from('connection_health_log')
        .insert({
          connection_type: 'alpaca_trading',
          status: healthStatus,
          endpoint_url: `${baseUrl}/v2/positions`,
          diagnostics: {
            driftCount: drifts.length,
            missingLocalCount: missingLocal.length,
            missingAlpacaCount: missingAlpaca.length,
            corrected: autoCorrect,
            correctedCount
          },
          checked_by: isServerRequest ? 'scheduler' : 'user'
        })
    } catch (e) {
      log.warn('Failed to log health check', { error: e.message })
    }

    const duration = Date.now() - handlerStartTime

    log.info('Position reconciliation completed', {
      requestId,
      driftCount: drifts.length,
      missingLocal: missingLocal.length,
      missingAlpaca: missingAlpaca.length,
      corrected: autoCorrect ? correctedCount : 0,
      duration
    })

    return new Response(
      JSON.stringify({
        success: true,
        healthy: healthStatus === 'healthy',
        summary: {
          alpacaPositions: alpacaPositions.length,
          localPositions: localPositions?.length || 0,
          driftCount: drifts.length,
          missingInLocal: missingLocal.length,
          missingInAlpaca: missingAlpaca.length,
          corrected: autoCorrect ? correctedCount : 0
        },
        drifts,
        missingLocal,
        missingAlpaca
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    log.error('Error reconciling positions', error, { requestId, duration: Date.now() - handlerStartTime })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}