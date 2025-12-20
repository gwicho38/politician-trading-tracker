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
      service: 'orders',
      message,
      ...metadata
    }))
  },
  error: (message: string, error?: any, metadata?: any) => {
    console.error(JSON.stringify({
      level: 'ERROR',
      timestamp: new Date().toISOString(),
      service: 'orders',
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
      service: 'orders',
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

    log.info('Processing request', {
      requestId,
      path,
      action,
      queryParams: Object.fromEntries(url.searchParams),
      bodyParams
    })

    let response: Response

    switch (action) {
      case 'get-orders':
        response = await handleGetOrders(supabaseClient, req, requestId, bodyParams)
        break
      case 'get-order-stats':
        response = await handleGetOrderStats(supabaseClient, req, requestId)
        break
      case 'place-order':
        response = await handlePlaceOrder(supabaseClient, req, requestId, bodyParams)
        break
      case 'place-orders':
        response = await handlePlaceOrders(supabaseClient, req, requestId, bodyParams)
        break
      case 'sync-orders':
        response = await handleSyncOrders(supabaseClient, req, requestId, bodyParams)
        break
      case 'orders':
        // Default action when called via supabase.functions.invoke('orders')
        response = await handleGetOrders(supabaseClient, req, requestId, bodyParams)
        break
      default:
        log.warn('Invalid endpoint requested', { requestId, action })
        response = new Response(
          JSON.stringify({ error: 'Invalid endpoint' }),
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

async function handleGetOrders(supabaseClient: any, req: Request, requestId: string, bodyParams: any = {}) {
  const handlerStartTime = Date.now()

  try {
    const url = new URL(req.url)
    // Support both URL params and body params
    const limit = parseInt(url.searchParams.get('limit') || bodyParams.limit || '100')
    const offset = parseInt(url.searchParams.get('offset') || bodyParams.offset || '0')
    const statusFilter = url.searchParams.get('status') || bodyParams.status
    const tradingMode = url.searchParams.get('trading_mode') || bodyParams.trading_mode || 'paper'

    log.info('Fetching orders - handler started', {
      requestId,
      handler: 'get-orders',
      params: { limit, offset, statusFilter, tradingMode },
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

    // Get orders from database (handle case where table doesn't exist yet)
    let orders: any[] = []
    let count = 0

    try {
      let query = supabaseClient
        .from('trading_orders')
        .select('*')
        .eq('trading_mode', tradingMode)
        .order('submitted_at', { ascending: false })
        .range(offset, offset + limit - 1)

      // Apply status filter if specified
      if (statusFilter && statusFilter !== 'all') {
        if (statusFilter === 'open') {
          query = query.in('status', ['new', 'accepted', 'pending_new', 'partially_filled'])
        } else if (statusFilter === 'closed') {
          query = query.in('status', ['filled', 'canceled', 'rejected', 'expired'])
        } else {
          query = query.eq('status', statusFilter)
        }
      }

      const { data, error } = await query

      if (error) {
        log.warn('Could not fetch orders', { error: error.message })
      } else {
        orders = data || []
      }

      // Get total count for pagination
      let countQuery = supabaseClient
        .from('trading_orders')
        .select('*', { count: 'exact', head: true })
        .eq('trading_mode', tradingMode)

      if (statusFilter && statusFilter !== 'all') {
        if (statusFilter === 'open') {
          countQuery = countQuery.in('status', ['new', 'accepted', 'pending_new', 'partially_filled'])
        } else if (statusFilter === 'closed') {
          countQuery = countQuery.in('status', ['filled', 'canceled', 'rejected', 'expired'])
        } else {
          countQuery = countQuery.eq('status', statusFilter)
        }
      }

      const countResult = await countQuery
      count = countResult.count || 0
    } catch (e) {
      log.warn('Exception fetching orders', { error: e.message })
    }

    // Transform orders to match frontend expectations (filled_qty -> filled_quantity)
    const transformedOrders = (orders || []).map((order: any) => ({
      ...order,
      filled_quantity: order.filled_qty || 0,
      // Ensure alpaca_order_id exists for display
      alpaca_order_id: order.alpaca_order_id || order.id
    }))

    const responseData = {
      success: true,
      orders: transformedOrders,
      total: count || 0,
      limit,
      offset
    }

    log.info('Orders fetched successfully - handler completed', {
      requestId,
      handler: 'get-orders',
      orderCount: orders?.length || 0,
      totalCount: count || 0,
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
    log.error('Error in handleGetOrders', error, {
      requestId,
      handler: 'get-orders',
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

async function handleGetOrderStats(supabaseClient: any, req: Request) {
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

    // Get order statistics
    const { data: orders, error } = await supabaseClient
      .from('trading_orders')
      .select('status, side, filled_avg_price, quantity, submitted_at')
      .eq('trading_mode', tradingMode)

    if (error) {
      throw new Error(`Failed to fetch order stats: ${error.message}`)
    }

    // Calculate statistics
    const stats = {
      total_orders: orders?.length || 0,
      status_distribution: {} as Record<string, number>,
      side_distribution: {} as Record<string, number>,
      average_fill_price: 0,
      total_volume: 0,
      success_rate: 0
    }

    if (orders && orders.length > 0) {
      // Count statuses and sides
      let totalFilledPrice = 0
      let filledOrderCount = 0

      orders.forEach(order => {
        // Status distribution
        const status = order.status
        stats.status_distribution[status] = (stats.status_distribution[status] || 0) + 1

        // Side distribution
        const side = order.side
        stats.side_distribution[side] = (stats.side_distribution[side] || 0) + 1

        // Volume and pricing
        stats.total_volume += order.quantity

        if (order.filled_avg_price) {
          totalFilledPrice += order.filled_avg_price * order.quantity
          filledOrderCount++
        }
      })

      // Calculate averages
      if (filledOrderCount > 0) {
        stats.average_fill_price = totalFilledPrice / filledOrderCount
      }

      // Calculate success rate (filled orders / total orders)
      const filledOrders = stats.status_distribution['filled'] || 0
      stats.success_rate = (filledOrders / orders.length) * 100
    }

    return new Response(
      JSON.stringify({
        success: true,
        stats
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  } catch (error) {
    console.error('Error fetching order stats:', error)
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
// PLACE ORDER HANDLER
// =============================================================================

async function handlePlaceOrder(supabaseClient: any, req: Request, requestId: string, bodyParams: any = {}) {
  const handlerStartTime = Date.now()

  try {
    // Validate authentication
    const authHeader = req.headers.get('authorization')
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

    if (authError || !user) {
      return new Response(
        JSON.stringify({ error: 'Invalid authentication' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Validate required fields
    const { ticker, side, quantity, order_type = 'market', limit_price, signal_id } = bodyParams

    if (!ticker || !side || !quantity) {
      return new Response(
        JSON.stringify({ error: 'Missing required fields: ticker, side, quantity' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    if (!['buy', 'sell'].includes(side)) {
      return new Response(
        JSON.stringify({ error: 'Side must be "buy" or "sell"' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    if (quantity <= 0) {
      return new Response(
        JSON.stringify({ error: 'Quantity must be greater than 0' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    log.info('Placing order', {
      requestId,
      ticker,
      side,
      quantity,
      order_type,
      limit_price,
      userId: user.id
    })

    // Get Alpaca API credentials from environment
    const alpacaApiKey = Deno.env.get('ALPACA_API_KEY')
    const alpacaSecretKey = Deno.env.get('ALPACA_SECRET_KEY')
    const alpacaPaper = Deno.env.get('ALPACA_PAPER') === 'true'
    const alpacaBaseUrl = Deno.env.get('ALPACA_BASE_URL') || (alpacaPaper ? 'https://paper-api.alpaca.markets' : 'https://api.alpaca.markets')

    if (!alpacaApiKey || !alpacaSecretKey) {
      return new Response(
        JSON.stringify({ error: 'Alpaca API credentials not configured' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Build Alpaca order request
    const orderRequest: any = {
      symbol: ticker.toUpperCase(),
      qty: quantity,
      side: side,
      type: order_type,
      time_in_force: 'day'
    }

    // Add limit price for limit orders
    if (order_type === 'limit' && limit_price) {
      orderRequest.limit_price = limit_price
    }

    // Call Alpaca API to place order
    const alpacaUrl = `${alpacaBaseUrl}/v2/orders`

    log.info('Calling Alpaca API to place order', { requestId, url: alpacaUrl, order: orderRequest })

    const response = await fetch(alpacaUrl, {
      method: 'POST',
      headers: {
        'APCA-API-KEY-ID': alpacaApiKey,
        'APCA-API-SECRET-KEY': alpacaSecretKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(orderRequest)
    })

    const alpacaResponse = await response.json()

    if (!response.ok) {
      log.error('Alpaca API error', { requestId, status: response.status, error: alpacaResponse })
      return new Response(
        JSON.stringify({ error: alpacaResponse.message || 'Failed to place order with Alpaca' }),
        { status: response.status, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    log.info('Alpaca order placed successfully', { requestId, orderId: alpacaResponse.id, status: alpacaResponse.status })

    // Save order to database
    const orderRecord = {
      user_id: user.id,
      alpaca_order_id: alpacaResponse.id,
      alpaca_client_order_id: alpacaResponse.client_order_id || null,
      ticker: ticker.toUpperCase(),
      side: side,
      quantity: quantity,
      order_type: order_type,
      limit_price: limit_price || null,
      status: alpacaResponse.status || 'pending',
      trading_mode: alpacaPaper ? 'paper' : 'live',
      signal_id: signal_id || null,
      submitted_at: alpacaResponse.submitted_at || new Date().toISOString(),
      filled_quantity: parseFloat(alpacaResponse.filled_qty) || 0,
      filled_avg_price: parseFloat(alpacaResponse.filled_avg_price) || null,
      broker: 'alpaca'
    }

    log.info('Saving order to database', { requestId, orderRecord })

    const { data: savedOrder, error: saveError } = await supabaseClient
      .from('trading_orders')
      .insert(orderRecord)
      .select()
      .single()

    if (saveError) {
      log.error('Failed to save order to database', { requestId, error: saveError.message, code: saveError.code })
      // Don't fail the request - order was placed successfully with Alpaca
    } else {
      log.info('Order saved to database', { requestId, savedOrderId: savedOrder?.id })
    }

    const duration = Date.now() - handlerStartTime

    log.info('Order placed successfully', {
      requestId,
      orderId: alpacaResponse.id,
      duration
    })

    return new Response(
      JSON.stringify({
        success: true,
        order: {
          id: savedOrder?.id || alpacaResponse.id,
          alpaca_order_id: alpacaResponse.id,
          ticker: ticker.toUpperCase(),
          side,
          quantity,
          order_type,
          status: alpacaResponse.status,
          submitted_at: alpacaResponse.submitted_at
        }
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    log.error('Error placing order', error, { requestId, duration: Date.now() - handlerStartTime })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}

// =============================================================================
// PLACE MULTIPLE ORDERS HANDLER (for cart checkout)
// =============================================================================

async function handlePlaceOrders(supabaseClient: any, req: Request, requestId: string, bodyParams: any = {}) {
  const handlerStartTime = Date.now()

  try {
    // Validate authentication
    const authHeader = req.headers.get('authorization')
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

    if (authError || !user) {
      return new Response(
        JSON.stringify({ error: 'Invalid authentication' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const { orders } = bodyParams

    if (!orders || !Array.isArray(orders) || orders.length === 0) {
      return new Response(
        JSON.stringify({ error: 'No orders provided' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    log.info('Placing multiple orders', { requestId, orderCount: orders.length, userId: user.id })

    // Get Alpaca API credentials
    const alpacaApiKey = Deno.env.get('ALPACA_API_KEY')
    const alpacaSecretKey = Deno.env.get('ALPACA_SECRET_KEY')
    const alpacaPaper = Deno.env.get('ALPACA_PAPER') === 'true'
    const alpacaBaseUrl = Deno.env.get('ALPACA_BASE_URL') || (alpacaPaper ? 'https://paper-api.alpaca.markets' : 'https://api.alpaca.markets')

    if (!alpacaApiKey || !alpacaSecretKey) {
      return new Response(
        JSON.stringify({ error: 'Alpaca API credentials not configured' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const results: any[] = []
    const alpacaUrl = `${alpacaBaseUrl}/v2/orders`

    // Process each order
    for (const order of orders) {
      const { ticker, side, quantity, order_type = 'market', limit_price, signal_id } = order

      // Validate order
      if (!ticker || !side || !quantity) {
        results.push({
          ticker: ticker || 'unknown',
          success: false,
          error: 'Missing required fields'
        })
        continue
      }

      if (!['buy', 'sell'].includes(side)) {
        results.push({
          ticker,
          success: false,
          error: 'Invalid side'
        })
        continue
      }

      try {
        // Build Alpaca order request
        const orderRequest: any = {
          symbol: ticker.toUpperCase(),
          qty: quantity,
          side: side,
          type: order_type,
          time_in_force: 'day'
        }

        if (order_type === 'limit' && limit_price) {
          orderRequest.limit_price = limit_price
        }

        // Place order with Alpaca
        const response = await fetch(alpacaUrl, {
          method: 'POST',
          headers: {
            'APCA-API-KEY-ID': alpacaApiKey,
            'APCA-API-SECRET-KEY': alpacaSecretKey,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(orderRequest)
        })

        const alpacaResponse = await response.json()

        if (!response.ok) {
          results.push({
            ticker: ticker.toUpperCase(),
            success: false,
            error: alpacaResponse.message || 'Alpaca API error'
          })
          continue
        }

        // Save order to database
        const orderRecord = {
          user_id: user.id,
          alpaca_order_id: alpacaResponse.id,
          alpaca_client_order_id: alpacaResponse.client_order_id || null,
          ticker: ticker.toUpperCase(),
          side,
          quantity,
          order_type,
          limit_price: limit_price || null,
          status: alpacaResponse.status || 'pending',
          trading_mode: alpacaPaper ? 'paper' : 'live',
          signal_id: signal_id || null,
          submitted_at: alpacaResponse.submitted_at || new Date().toISOString(),
          filled_quantity: parseFloat(alpacaResponse.filled_qty) || 0,
          filled_avg_price: parseFloat(alpacaResponse.filled_avg_price) || null,
          broker: 'alpaca'
        }

        const { error: insertError } = await supabaseClient.from('trading_orders').insert(orderRecord)
        if (insertError) {
          log.warn('Failed to save order to database', { ticker, error: insertError.message })
        }

        results.push({
          ticker: ticker.toUpperCase(),
          success: true,
          order_id: alpacaResponse.id,
          status: alpacaResponse.status
        })

        // Small delay between orders to avoid rate limiting
        await new Promise(resolve => setTimeout(resolve, 100))

      } catch (orderError) {
        results.push({
          ticker: ticker.toUpperCase(),
          success: false,
          error: orderError.message
        })
      }
    }

    const successCount = results.filter(r => r.success).length
    const failCount = results.filter(r => !r.success).length
    const duration = Date.now() - handlerStartTime

    log.info('Multiple orders processed', {
      requestId,
      total: orders.length,
      success: successCount,
      failed: failCount,
      duration
    })

    return new Response(
      JSON.stringify({
        success: failCount === 0,
        message: `${successCount} orders placed, ${failCount} failed`,
        results,
        summary: {
          total: orders.length,
          success: successCount,
          failed: failCount
        }
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    log.error('Error placing multiple orders', error, { requestId, duration: Date.now() - handlerStartTime })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}

// =============================================================================
// SYNC ORDERS FROM ALPACA
// =============================================================================

async function handleSyncOrders(supabaseClient: any, req: Request, requestId: string, bodyParams: any = {}) {
  const handlerStartTime = Date.now()

  try {
    // Validate authentication
    const authHeader = req.headers.get('authorization')
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

    if (authError || !user) {
      return new Response(
        JSON.stringify({ error: 'Invalid authentication' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    log.info('Syncing orders from Alpaca', { requestId, userId: user.id })

    // Get Alpaca API credentials
    const alpacaApiKey = Deno.env.get('ALPACA_API_KEY')
    const alpacaSecretKey = Deno.env.get('ALPACA_SECRET_KEY')
    const alpacaPaper = Deno.env.get('ALPACA_PAPER') === 'true'
    const alpacaBaseUrl = Deno.env.get('ALPACA_BASE_URL') || (alpacaPaper ? 'https://paper-api.alpaca.markets' : 'https://api.alpaca.markets')

    if (!alpacaApiKey || !alpacaSecretKey) {
      return new Response(
        JSON.stringify({ error: 'Alpaca API credentials not configured' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Fetch orders from Alpaca
    const status = bodyParams.status || 'all' // all, open, closed
    const limit = bodyParams.limit || 100
    const alpacaUrl = `${alpacaBaseUrl}/v2/orders?status=${status}&limit=${limit}`

    log.info('Fetching orders from Alpaca', { requestId, url: alpacaUrl })

    const response = await fetch(alpacaUrl, {
      method: 'GET',
      headers: {
        'APCA-API-KEY-ID': alpacaApiKey,
        'APCA-API-SECRET-KEY': alpacaSecretKey,
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      const errorText = await response.text()
      log.error('Alpaca API error', { requestId, status: response.status, error: errorText })
      return new Response(
        JSON.stringify({ error: `Alpaca API error: ${response.status}` }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const alpacaOrders = await response.json()
    log.info('Fetched orders from Alpaca', { requestId, count: alpacaOrders.length })

    // Sync each order to database
    let synced = 0
    let skipped = 0
    let errors = 0

    for (const order of alpacaOrders) {
      try {
        // Check if order already exists
        const { data: existing } = await supabaseClient
          .from('trading_orders')
          .select('id')
          .eq('alpaca_order_id', order.id)
          .maybeSingle()

        if (existing) {
          // Update existing order
          const { error: updateError } = await supabaseClient
            .from('trading_orders')
            .update({
              status: order.status,
              filled_quantity: parseFloat(order.filled_qty) || 0,
              filled_avg_price: parseFloat(order.filled_avg_price) || null,
              filled_at: order.filled_at || null,
              canceled_at: order.canceled_at || null,
              expired_at: order.expired_at || null,
              updated_at: new Date().toISOString()
            })
            .eq('alpaca_order_id', order.id)

          if (updateError) {
            log.warn('Failed to update order', { orderId: order.id, error: updateError.message })
            errors++
          } else {
            skipped++ // Updated existing
          }
        } else {
          // Insert new order
          const orderRecord = {
            user_id: user.id,
            alpaca_order_id: order.id,
            alpaca_client_order_id: order.client_order_id || null,
            ticker: order.symbol,
            side: order.side,
            quantity: parseFloat(order.qty) || 0,
            order_type: order.type,
            limit_price: parseFloat(order.limit_price) || null,
            stop_price: parseFloat(order.stop_price) || null,
            status: order.status,
            trading_mode: alpacaPaper ? 'paper' : 'live',
            submitted_at: order.submitted_at || null,
            filled_quantity: parseFloat(order.filled_qty) || 0,
            filled_avg_price: parseFloat(order.filled_avg_price) || null,
            filled_at: order.filled_at || null,
            canceled_at: order.canceled_at || null,
            expired_at: order.expired_at || null,
            broker: 'alpaca'
          }

          const { error: insertError } = await supabaseClient
            .from('trading_orders')
            .insert(orderRecord)

          if (insertError) {
            log.error('Failed to insert order', { orderId: order.id, error: insertError.message, code: insertError.code })
            errors++
          } else {
            synced++
          }
        }
      } catch (orderError) {
        log.error('Error processing order', { orderId: order.id, error: orderError.message })
        errors++
      }
    }

    const duration = Date.now() - handlerStartTime

    log.info('Orders sync completed', {
      requestId,
      total: alpacaOrders.length,
      synced,
      skipped,
      errors,
      duration
    })

    return new Response(
      JSON.stringify({
        success: true,
        message: `Synced ${synced} new orders, updated ${skipped}, ${errors} errors`,
        summary: {
          total: alpacaOrders.length,
          synced,
          updated: skipped,
          errors
        }
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    log.error('Error syncing orders', error, { requestId, duration: Date.now() - handlerStartTime })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}