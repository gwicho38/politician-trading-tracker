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

// TODO: Review getAlpacaCredentials - retrieves Alpaca API credentials
// - Priority: user_api_keys table > environment variables
// - Supports both paper and live trading modes
async function getAlpacaCredentials(
  supabase: any,
  userEmail: string | null,
  tradingMode: 'paper' | 'live'
): Promise<{ apiKey: string; secretKey: string; baseUrl: string } | null> {
  // 1. Try user-specific credentials from user_api_keys table
  if (userEmail) {
    try {
      const { data, error } = await supabase
        .from('user_api_keys')
        .select('paper_api_key, paper_secret_key, live_api_key, live_secret_key')
        .eq('user_email', userEmail)
        .maybeSingle();

      if (!error && data) {
        const apiKey = tradingMode === 'paper' ? data.paper_api_key : data.live_api_key;
        const secretKey = tradingMode === 'paper' ? data.paper_secret_key : data.live_secret_key;

        if (apiKey && secretKey) {
          const baseUrl = tradingMode === 'paper'
            ? 'https://paper-api.alpaca.markets'
            : 'https://api.alpaca.markets';
          return { apiKey, secretKey, baseUrl };
        }
      }
    } catch (err) {
      console.warn('Could not fetch user credentials:', err);
    }
  }

  // 2. Fallback to environment variables (for system operations)
  const envApiKey = Deno.env.get('ALPACA_API_KEY');
  const envSecretKey = Deno.env.get('ALPACA_SECRET_KEY');
  const envPaper = Deno.env.get('ALPACA_PAPER') === 'true';
  const envBaseUrl = Deno.env.get('ALPACA_BASE_URL');

  if (envApiKey && envSecretKey) {
    const baseUrl = envBaseUrl || (envPaper ? 'https://paper-api.alpaca.markets' : 'https://api.alpaca.markets');
    return { apiKey: envApiKey, secretKey: envSecretKey, baseUrl };
  }

  return null;
}

// =============================================================================
// ORDER STATE MACHINE AND AUDIT FUNCTIONS
// =============================================================================

// TODO: Review generateIdempotencyKey - creates unique key to prevent duplicate orders
// - Combines user, ticker, side, quantity, signal_id, and timestamp
function generateIdempotencyKey(
  userId: string,
  ticker: string,
  side: string,
  quantity: number,
  signalId: string | null
): string {
  const timestamp = Math.floor(Date.now() / 60000) // Minute-level granularity
  const components = [userId, ticker.toUpperCase(), side, quantity.toString(), signalId || 'no-signal', timestamp.toString()]
  return `order_${components.join('_')}_${crypto.randomUUID().substring(0, 8)}`
}

// TODO: Review checkIdempotency - checks if order already exists by idempotency key
async function checkIdempotency(
  supabaseClient: any,
  idempotencyKey: string
): Promise<{ exists: boolean; existingOrder?: any }> {
  try {
    const { data, error } = await supabaseClient
      .from('trading_orders')
      .select('*')
      .eq('idempotency_key', idempotencyKey)
      .maybeSingle()

    if (error) {
      console.warn('Idempotency check error:', error.message)
      return { exists: false }
    }

    return { exists: !!data, existingOrder: data }
  } catch {
    return { exists: false }
  }
}

// TODO: Review recordOrderStateTransition - records order status changes to audit log
// - Tracks previous/new status, source, fill details, and raw event
async function recordOrderStateTransition(
  supabaseClient: any,
  orderId: string,
  previousStatus: string | null,
  newStatus: string,
  source: 'user_action' | 'alpaca_webhook' | 'alpaca_poll' | 'system_timeout' | 'scheduler' | 'unknown',
  details?: {
    filledQty?: number
    avgPrice?: number
    errorCode?: string
    errorMessage?: string
    alpacaEventId?: string
    alpacaEventTimestamp?: string
    rawEvent?: any
  }
): Promise<void> {
  try {
    const { error } = await supabaseClient
      .from('order_state_log')
      .insert({
        order_id: orderId,
        previous_status: previousStatus,
        new_status: newStatus,
        source,
        filled_qty_at_state: details?.filledQty || null,
        avg_price_at_state: details?.avgPrice || null,
        error_code: details?.errorCode || null,
        error_message: details?.errorMessage || null,
        alpaca_event_id: details?.alpacaEventId || null,
        alpaca_event_timestamp: details?.alpacaEventTimestamp || null,
        raw_event: details?.rawEvent || null,
      })

    if (error) {
      console.warn('Failed to record order state transition:', error.message)
    }
  } catch (err) {
    console.warn('Error recording order state transition:', err)
  }
}

// TODO: Review recordSignalLifecycleOnOrder - updates signal lifecycle when order placed
// - Records transition from generated -> ordered -> filled states
async function recordSignalLifecycleOnOrder(
  supabaseClient: any,
  signalId: string,
  orderId: string,
  previousState: string,
  newState: string,
  reason: string,
  transitionedBy: string
): Promise<void> {
  try {
    const { error } = await supabaseClient
      .from('signal_lifecycle')
      .insert({
        signal_id: signalId,
        order_id: orderId,
        previous_state: previousState,
        current_state: newState,
        transition_reason: reason,
        transitioned_by: transitionedBy,
      })

    if (error) {
      console.warn('Failed to record signal lifecycle:', error.message)
    }
  } catch (err) {
    console.warn('Error recording signal lifecycle:', err)
  }
}

// TODO: Review getCurrentSignalState - gets most recent signal lifecycle state
async function getCurrentSignalState(
  supabaseClient: any,
  signalId: string
): Promise<string | null> {
  try {
    const { data, error } = await supabaseClient
      .from('signal_lifecycle')
      .select('current_state')
      .eq('signal_id', signalId)
      .order('created_at', { ascending: false })
      .limit(1)
      .maybeSingle()

    if (error || !data) {
      return 'generated' // Default state if no lifecycle entry exists
    }

    return data.current_state
  } catch {
    return 'generated'
  }
}

// TODO: Review log object - structured JSON logging with levels (info, error, warn)
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

// TODO: Review serve handler - main order management endpoint
// - Actions: get-orders, get-order-stats, place-order, place-orders, sync-orders
// - Supports user-specific and service role authentication
// - Records order state transitions and signal lifecycle updates
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

// TODO: Review handleGetOrders - fetches user's orders with filtering/pagination
// - Supports status filter (all, open, closed, specific status)
// - Returns transformed orders with filled_quantity field
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
        .eq('user_id', user.id)  // Filter by current user
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
        .eq('user_id', user.id)  // Filter by current user
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

// TODO: Review handleGetOrderStats - calculates order statistics for user
// - Returns status distribution, side distribution, avg fill price, success rate
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

    // Get order statistics (filtered by user)
    const { data: orders, error } = await supabaseClient
      .from('trading_orders')
      .select('status, side, filled_avg_price, quantity, submitted_at')
      .eq('user_id', user.id)  // Filter by current user
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

// TODO: Review handlePlaceOrder - places single order via Alpaca API
// - Validates order parameters and idempotency
// - Saves order to database with state transition audit
// - Updates signal lifecycle if order is from a signal
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

    const userEmail = user.email || null;

    // Validate required fields
    const { ticker, side, quantity, order_type = 'market', limit_price, signal_id, tradingMode = 'paper' } = bodyParams

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

    // Generate idempotency key to prevent duplicate orders
    const idempotencyKey = generateIdempotencyKey(user.id, ticker, side, quantity, signal_id)

    // Check if this order was already submitted
    const { exists: duplicateExists, existingOrder } = await checkIdempotency(supabaseClient, idempotencyKey)
    if (duplicateExists && existingOrder) {
      log.info('Duplicate order detected, returning existing order', {
        requestId,
        idempotencyKey,
        existingOrderId: existingOrder.id
      })
      return new Response(
        JSON.stringify({
          success: true,
          message: 'Order already exists',
          order: existingOrder,
          duplicate: true
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    log.info('Placing order', {
      requestId,
      ticker,
      side,
      quantity,
      order_type,
      limit_price,
      tradingMode,
      userId: user.id,
      userEmail,
      idempotencyKey
    })

    // Get Alpaca API credentials (per-user or environment)
    const credentials = await getAlpacaCredentials(supabaseClient, userEmail, tradingMode);

    if (!credentials) {
      return new Response(
        JSON.stringify({ error: 'No Alpaca credentials configured. Please connect your Alpaca account.' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
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
    const alpacaUrl = `${credentials.baseUrl}/v2/orders`

    log.info('Calling Alpaca API to place order', { requestId, url: alpacaUrl, order: orderRequest, tradingMode })

    const response = await fetch(alpacaUrl, {
      method: 'POST',
      headers: {
        'APCA-API-KEY-ID': credentials.apiKey,
        'APCA-API-SECRET-KEY': credentials.secretKey,
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

    // Save order to database with idempotency key
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
      trading_mode: tradingMode,
      signal_id: signal_id || null,
      submitted_at: alpacaResponse.submitted_at || new Date().toISOString(),
      filled_quantity: parseFloat(alpacaResponse.filled_qty) || 0,
      filled_avg_price: parseFloat(alpacaResponse.filled_avg_price) || null,
      broker: 'alpaca',
      idempotency_key: idempotencyKey
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

      // Record initial state transition
      await recordOrderStateTransition(
        supabaseClient,
        savedOrder.id,
        null, // No previous status
        alpacaResponse.status || 'pending',
        'user_action',
        {
          filledQty: parseFloat(alpacaResponse.filled_qty) || 0,
          avgPrice: parseFloat(alpacaResponse.filled_avg_price) || null,
          rawEvent: alpacaResponse
        }
      )

      // If this order is from a signal, update signal lifecycle
      if (signal_id) {
        const previousState = await getCurrentSignalState(supabaseClient, signal_id)
        await recordSignalLifecycleOnOrder(
          supabaseClient,
          signal_id,
          savedOrder.id,
          previousState || 'generated',
          'ordered',
          `Order placed via ${tradingMode} trading`,
          `user:${user.email || user.id}`
        )
        log.info('Signal lifecycle updated', { requestId, signalId: signal_id, newState: 'ordered' })
      }
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

// TODO: Review handlePlaceOrders - places multiple orders for cart checkout
// - Processes array of orders with idempotency checks
// - Returns individual success/failure results for each order
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

    const userEmail = user.email || null;
    const { orders, tradingMode = 'paper' } = bodyParams

    if (!orders || !Array.isArray(orders) || orders.length === 0) {
      return new Response(
        JSON.stringify({ error: 'No orders provided' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    log.info('Placing multiple orders', { requestId, orderCount: orders.length, userId: user.id, tradingMode, userEmail })

    // Get Alpaca API credentials (per-user or environment)
    const credentials = await getAlpacaCredentials(supabaseClient, userEmail, tradingMode);

    if (!credentials) {
      return new Response(
        JSON.stringify({ error: 'No Alpaca credentials configured. Please connect your Alpaca account.' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const results: any[] = []
    const alpacaUrl = `${credentials.baseUrl}/v2/orders`

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
        // Generate idempotency key for this order
        const orderIdempotencyKey = generateIdempotencyKey(user.id, ticker, side, quantity, signal_id)

        // Check for duplicate
        const { exists: duplicateExists, existingOrder } = await checkIdempotency(supabaseClient, orderIdempotencyKey)
        if (duplicateExists && existingOrder) {
          results.push({
            ticker: ticker.toUpperCase(),
            success: true,
            order_id: existingOrder.alpaca_order_id,
            status: existingOrder.status,
            duplicate: true
          })
          continue
        }

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
            'APCA-API-KEY-ID': credentials.apiKey,
            'APCA-API-SECRET-KEY': credentials.secretKey,
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

        // Save order to database with idempotency key
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
          trading_mode: tradingMode,
          signal_id: signal_id || null,
          submitted_at: alpacaResponse.submitted_at || new Date().toISOString(),
          filled_quantity: parseFloat(alpacaResponse.filled_qty) || 0,
          filled_avg_price: parseFloat(alpacaResponse.filled_avg_price) || null,
          broker: 'alpaca',
          idempotency_key: orderIdempotencyKey
        }

        const { data: savedOrder, error: insertError } = await supabaseClient
          .from('trading_orders')
          .insert(orderRecord)
          .select()
          .single()

        if (insertError) {
          log.warn('Failed to save order to database', { ticker, error: insertError.message })
        } else {
          // Record state transition
          await recordOrderStateTransition(
            supabaseClient,
            savedOrder.id,
            null,
            alpacaResponse.status || 'pending',
            'user_action',
            {
              filledQty: parseFloat(alpacaResponse.filled_qty) || 0,
              avgPrice: parseFloat(alpacaResponse.filled_avg_price) || null,
              rawEvent: alpacaResponse
            }
          )

          // Update signal lifecycle if from signal
          if (signal_id) {
            const previousState = await getCurrentSignalState(supabaseClient, signal_id)
            await recordSignalLifecycleOnOrder(
              supabaseClient,
              signal_id,
              savedOrder.id,
              previousState || 'generated',
              'ordered',
              `Order placed from cart checkout (${tradingMode})`,
              `user:${user.email || user.id}`
            )
          }
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

// TODO: Review handleSyncOrders - syncs orders from Alpaca for specific user
// - Fetches orders from Alpaca API and updates local database
// - Records state transitions for status changes
// - Updates signal lifecycle when orders fill
async function handleSyncOrders(supabaseClient: any, req: Request, requestId: string, bodyParams: any = {}) {
  const handlerStartTime = Date.now()

  try {
    const tradingMode: 'paper' | 'live' = bodyParams.tradingMode || 'paper'

    // Check if this is a service role request (scheduled job)
    const authHeader = req.headers.get('authorization')
    if (!authHeader) {
      return new Response(
        JSON.stringify({ error: 'Authentication required' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Check if using service role key (scheduled jobs)
    if (isServiceRoleRequest(req)) {
      // For scheduled jobs, sync orders for ALL users who have Alpaca credentials
      log.info('Service role sync - syncing orders for all users with credentials', { requestId, tradingMode })
      return await handleServiceRoleSyncOrders(supabaseClient, requestId, bodyParams, handlerStartTime)
    }

    // Get user from JWT for user-specific sync
    const { data: { user }, error: authError } = await supabaseClient.auth.getUser(
      authHeader.replace('Bearer ', '')
    )

    if (authError || !user) {
      return new Response(
        JSON.stringify({ error: 'Invalid authentication' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const userId = user.id
    const userEmail = user.email || null
    log.info('Syncing orders from Alpaca', { requestId, userId, tradingMode })

    // Get Alpaca API credentials (per-user or environment)
    const credentials = await getAlpacaCredentials(supabaseClient, userEmail, tradingMode);

    if (!credentials) {
      return new Response(
        JSON.stringify({ error: 'No Alpaca credentials configured. Please connect your Alpaca account.' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Fetch orders from Alpaca
    const status = bodyParams.status || 'all' // all, open, closed
    const limit = bodyParams.limit || 100
    const alpacaUrl = `${credentials.baseUrl}/v2/orders?status=${status}&limit=${limit}`

    log.info('Fetching orders from Alpaca', { requestId, url: alpacaUrl, tradingMode })

    const response = await fetch(alpacaUrl, {
      method: 'GET',
      headers: {
        'APCA-API-KEY-ID': credentials.apiKey,
        'APCA-API-SECRET-KEY': credentials.secretKey,
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
        // Check if order already exists FOR THIS USER
        const { data: existing } = await supabaseClient
          .from('trading_orders')
          .select('id')
          .eq('alpaca_order_id', order.id)
          .eq('user_id', userId)  // Filter by current user
          .maybeSingle()

        if (existing) {
          // Get current status before update
          const { data: currentOrder } = await supabaseClient
            .from('trading_orders')
            .select('id, status')
            .eq('alpaca_order_id', order.id)
            .eq('user_id', userId)
            .single()

          const previousStatus = currentOrder?.status
          const newStatus = order.status

          // Update existing order (only if it belongs to this user)
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
            .eq('user_id', userId)  // Only update user's own orders

          if (updateError) {
            log.warn('Failed to update order', { orderId: order.id, error: updateError.message })
            errors++
          } else {
            // Record state transition if status changed
            if (currentOrder && previousStatus !== newStatus) {
              await recordOrderStateTransition(
                supabaseClient,
                currentOrder.id,
                previousStatus,
                newStatus,
                'alpaca_poll',
                {
                  filledQty: parseFloat(order.filled_qty) || 0,
                  avgPrice: parseFloat(order.filled_avg_price) || null,
                  alpacaEventId: order.id,
                  rawEvent: order
                }
              )

              // If order is filled and has signal_id, update signal lifecycle
              if (newStatus === 'filled' && currentOrder) {
                const { data: fullOrder } = await supabaseClient
                  .from('trading_orders')
                  .select('signal_id')
                  .eq('id', currentOrder.id)
                  .single()

                if (fullOrder?.signal_id) {
                  const previousState = await getCurrentSignalState(supabaseClient, fullOrder.signal_id)
                  await recordSignalLifecycleOnOrder(
                    supabaseClient,
                    fullOrder.signal_id,
                    currentOrder.id,
                    previousState || 'ordered',
                    'filled',
                    'Order filled via Alpaca sync',
                    'alpaca_poll'
                  )
                }
              }
            }
            skipped++ // Updated existing
          }
        } else {
          // Insert new order with user_id
          const orderRecord = {
            user_id: userId,  // Always set user_id for data isolation
            alpaca_order_id: order.id,
            alpaca_client_order_id: order.client_order_id || null,
            ticker: order.symbol,
            side: order.side,
            quantity: parseFloat(order.qty) || 0,
            order_type: order.type,
            limit_price: parseFloat(order.limit_price) || null,
            stop_price: parseFloat(order.stop_price) || null,
            status: order.status,
            trading_mode: tradingMode,
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

// =============================================================================
// SERVICE ROLE SYNC ORDERS (for scheduled jobs)
// =============================================================================

// TODO: Review handleServiceRoleSyncOrders - syncs orders for all users via scheduled job
// - Uses environment credentials to sync existing orders only
// - Does not create new orders (only updates existing)
async function handleServiceRoleSyncOrders(
  supabaseClient: any,
  requestId: string,
  bodyParams: any,
  handlerStartTime: number
): Promise<Response> {
  const tradingMode: 'paper' | 'live' = bodyParams.tradingMode || 'paper'

  try {
    // For scheduled jobs, use environment credentials to sync ALL existing orders
    const envApiKey = Deno.env.get('ALPACA_API_KEY')
    const envSecretKey = Deno.env.get('ALPACA_SECRET_KEY')
    const envPaper = Deno.env.get('ALPACA_PAPER') === 'true'
    const envBaseUrl = Deno.env.get('ALPACA_BASE_URL')

    if (!envApiKey || !envSecretKey) {
      // No environment credentials - return success with no action
      log.info('No environment Alpaca credentials configured, skipping scheduled sync', { requestId })
      return new Response(
        JSON.stringify({
          success: true,
          message: 'No environment credentials configured for scheduled sync',
          summary: { total: 0, synced: 0, updated: 0, errors: 0 }
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const baseUrl = envBaseUrl || (envPaper ? 'https://paper-api.alpaca.markets' : 'https://api.alpaca.markets')

    // Fetch orders from Alpaca using environment credentials
    const status = bodyParams.status || 'all'
    const limit = bodyParams.limit || 100
    const alpacaUrl = `${baseUrl}/v2/orders?status=${status}&limit=${limit}`

    log.info('Fetching orders from Alpaca (scheduled sync)', { requestId, url: alpacaUrl, tradingMode })

    const response = await fetch(alpacaUrl, {
      method: 'GET',
      headers: {
        'APCA-API-KEY-ID': envApiKey,
        'APCA-API-SECRET-KEY': envSecretKey,
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      const errorText = await response.text()
      log.error('Alpaca API error (scheduled sync)', { requestId, status: response.status, error: errorText })
      return new Response(
        JSON.stringify({ error: `Alpaca API error: ${response.status}` }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const alpacaOrders = await response.json()
    log.info('Fetched orders from Alpaca (scheduled sync)', { requestId, count: alpacaOrders.length })

    // Sync each order - update existing orders by alpaca_order_id (no user filter)
    let synced = 0
    let updated = 0
    let errors = 0

    for (const order of alpacaOrders) {
      try {
        // Check if order exists (by alpaca_order_id, any user)
        const { data: existing } = await supabaseClient
          .from('trading_orders')
          .select('id, status, user_id')
          .eq('alpaca_order_id', order.id)
          .maybeSingle()

        if (existing) {
          const previousStatus = existing.status
          const newStatus = order.status

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
            log.warn('Failed to update order (scheduled)', { orderId: order.id, error: updateError.message })
            errors++
          } else {
            // Record state transition if status changed
            if (previousStatus !== newStatus) {
              await recordOrderStateTransition(
                supabaseClient,
                existing.id,
                previousStatus,
                newStatus,
                'scheduler',
                {
                  filledQty: parseFloat(order.filled_qty) || 0,
                  avgPrice: parseFloat(order.filled_avg_price) || null,
                  alpacaEventId: order.id,
                  rawEvent: order
                }
              )
            }
            updated++
          }
        }
        // Note: We don't create new orders in scheduled sync - only update existing ones
        // New orders should only be created through user-initiated actions
      } catch (orderError) {
        log.error('Error processing order (scheduled)', { orderId: order.id, error: orderError.message })
        errors++
      }
    }

    const duration = Date.now() - handlerStartTime

    log.info('Scheduled orders sync completed', {
      requestId,
      total: alpacaOrders.length,
      synced,
      updated,
      errors,
      duration
    })

    return new Response(
      JSON.stringify({
        success: true,
        message: `Scheduled sync: updated ${updated} orders, ${errors} errors`,
        summary: {
          total: alpacaOrders.length,
          synced,
          updated,
          errors
        }
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    log.error('Error in scheduled orders sync', error, { requestId, duration: Date.now() - handlerStartTime })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}