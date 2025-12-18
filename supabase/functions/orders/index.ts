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

    const responseData = {
      success: true,
      orders: orders || [],
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