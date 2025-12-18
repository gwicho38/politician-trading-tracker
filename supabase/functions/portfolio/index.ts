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
    const path = url.pathname.split('/').pop()

    log.info('Processing request', {
      requestId,
      path,
      queryParams: Object.fromEntries(url.searchParams)
    })

    let response: Response

    switch (path) {
      case 'get-portfolio':
        response = await handleGetPortfolio(supabaseClient, req, requestId)
        break
      case 'get-account-info':
        response = await handleGetAccountInfo(supabaseClient, req, requestId)
        break
      default:
        log.warn('Invalid endpoint requested', { requestId, path })
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

    // Get positions from database
    const { data: positions, error } = await supabaseClient
      .from('positions')
      .select('*')
      .eq('is_open', true)
      .order('market_value', { ascending: false })

    if (error) {
      throw new Error(`Failed to fetch positions: ${error.message}`)
    }

    const responseData = {
      success: true,
      positions: positions || []
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