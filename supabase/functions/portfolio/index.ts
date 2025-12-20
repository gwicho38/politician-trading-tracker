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

// Sanitize request for logging (remove sensitive headers)
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

// Sanitize response for logging
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