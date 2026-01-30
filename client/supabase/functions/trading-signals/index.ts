import { createClient } from 'supabase'
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

// Structured logging utility
const log = {
  info: (message: string, metadata?: Record<string, unknown>) => {
    console.log(JSON.stringify({
      level: 'INFO',
      timestamp: new Date().toISOString(),
      service: 'trading-signals',
      message,
      ...metadata
    }))
  },
  error: (message: string, error?: Error | unknown, metadata?: Record<string, unknown>) => {
    const err = error as Error | undefined
    console.error(JSON.stringify({
      level: 'ERROR',
      timestamp: new Date().toISOString(),
      service: 'trading-signals',
      message,
      error: err?.message || String(error),
      stack: err?.stack,
      ...metadata
    }))
  },
  warn: (message: string, metadata?: Record<string, unknown>) => {
    console.warn(JSON.stringify({
      level: 'WARN',
      timestamp: new Date().toISOString(),
      service: 'trading-signals',
      message,
      ...metadata
    }))
  }
}

// Sanitize request for logging (remove sensitive headers)
function sanitizeRequestForLogging(req: Request): Record<string, unknown> {
  const headers = Object.fromEntries(req.headers.entries()) as Record<string, string>

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
function sanitizeResponseForLogging(response: Response, body?: unknown): Record<string, unknown> {
  return {
    status: response.status,
    statusText: response.statusText,
    headers: Object.fromEntries(response.headers.entries()),
    contentType: response.headers.get('content-type'),
    contentLength: response.headers.get('content-length'),
    body: body ? JSON.stringify(body).substring(0, 500) + (JSON.stringify(body).length > 500 ? '...' : '') : null
  }
}

// Supabase client interface for edge functions
interface SupabaseClient {
  auth: {
    getUser: (token: string) => Promise<{ data: { user: { id: string } | null }; error: Error | null }>;
  };
  from: (table: string) => {
    select: (columns: string, options?: { count?: string; head?: boolean }) => {
      eq: (column: string, value: unknown) => ReturnType<SupabaseClient['from']>['select'];
      gte: (column: string, value: number) => ReturnType<SupabaseClient['from']>['select'];
      order: (column: string, options: { ascending: boolean }) => ReturnType<SupabaseClient['from']>['select'];
      range: (from: number, to: number) => Promise<{ data: TradingSignal[] | null; error: Error | null; count?: number }>;
    };
    insert: (data: unknown) => {
      select: () => Promise<{ data: TradingSignal[] | null; error: Error | null }>;
    };
  };
}

// Trading signal interface
interface TradingSignal {
  id?: string;
  ticker: string;
  asset_name: string;
  signal_type: string;
  signal_strength: string;
  confidence_score: number;
  target_price?: number;
  stop_loss?: number;
  take_profit?: number;
  politician_activity_count?: number;
  buy_sell_ratio?: number;
  generated_at: string;
  is_active: boolean;
  user_id?: string;
  model_version?: string;
  features?: Record<string, unknown>;
  notes?: string;
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
      case 'get-signals':
        response = await handleGetSignals(supabaseClient, req, requestId)
        break
      case 'generate-signals':
        response = await handleGenerateSignals(supabaseClient, req, requestId)
        break
      case 'get-signal-stats':
        response = await handleGetSignalStats(supabaseClient, req, requestId)
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

async function handleGetSignals(supabaseClient: SupabaseClient, req: Request, requestId: string) {
  try {
    const url = new URL(req.url)
    const limit = parseInt(url.searchParams.get('limit') || '100')
    const offset = parseInt(url.searchParams.get('offset') || '0')
    const signalType = url.searchParams.get('signal_type')
    const minConfidence = parseFloat(url.searchParams.get('min_confidence') || '0')

    const handlerStartTime = Date.now()

    log.info('Fetching trading signals - handler started', {
      requestId,
      handler: 'get-signals',
      params: { limit, offset, signalType, minConfidence },
      request: sanitizeRequestForLogging(req)
    })

    let query = supabaseClient
      .from('trading_signals')
      .select('*')
      .eq('is_active', true)
      .order('confidence_score', { ascending: false })
      .range(offset, offset + limit - 1)

    if (signalType && signalType !== 'all') {
      query = query.eq('signal_type', signalType)
    }

    if (minConfidence > 0) {
      query = query.gte('confidence_score', minConfidence)
    }

    const { data: signals, error } = await query

    if (error) {
      log.error('Database query failed', error, { requestId })
      throw new Error(`Failed to fetch signals: ${error.message}`)
    }

    // Get total count for pagination
    const { count, error: countError } = await supabaseClient
      .from('trading_signals')
      .select('*', { count: 'exact', head: true })
      .eq('is_active', true)

    if (countError) {
      log.warn('Count query failed', { requestId, error: countError })
    }

    const responseData = {
      success: true,
      signals: signals || [],
      total: count || 0,
      limit,
      offset
    }

    log.info('Signals fetched successfully - handler completed', {
      requestId,
      handler: 'get-signals',
      signalCount: signals?.length || 0,
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
    log.error('Error in handleGetSignals', error, {
      requestId,
      handler: 'get-signals',
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

async function handleGenerateSignals(supabaseClient: SupabaseClient, req: Request) {
  try {
    const body = await req.json()
    const { lookbackDays = 30, minConfidence = 0.65, fetchMarketData = true } = body

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

    // Here you would implement the actual signal generation logic
    // For now, we'll simulate signal generation
    console.log(`Generating signals for user ${user.id} with parameters:`, {
      lookbackDays,
      minConfidence,
      fetchMarketData
    })

    // Simulate signal generation delay
    await new Promise(resolve => setTimeout(resolve, 2000))

    // Mock generated signals
    const mockSignals = [
      {
        ticker: 'AAPL',
        asset_name: 'Apple Inc.',
        signal_type: 'buy',
        signal_strength: 'strong',
        confidence_score: 0.87,
        target_price: 185.00,
        stop_loss: 165.00,
        take_profit: 200.00,
        politician_activity_count: 15,
        buy_sell_ratio: 2.3,
        generated_at: new Date().toISOString(),
        is_active: true
      },
      {
        ticker: 'MSFT',
        asset_name: 'Microsoft Corporation',
        signal_type: 'strong_buy',
        signal_strength: 'very_strong',
        confidence_score: 0.92,
        target_price: 425.00,
        stop_loss: 380.00,
        take_profit: 450.00,
        politician_activity_count: 22,
        buy_sell_ratio: 3.1,
        generated_at: new Date().toISOString(),
        is_active: true
      }
    ]

    // Insert signals into database
    const signalsToInsert = mockSignals.map(signal => ({
      ...signal,
      user_id: user.id,
      model_version: 'v1.0',
      features: {},
      notes: `Generated with lookback: ${lookbackDays} days, min confidence: ${minConfidence}`
    }))

    const { data: insertedSignals, error: insertError } = await supabaseClient
      .from('trading_signals')
      .insert(signalsToInsert)
      .select()

    if (insertError) {
      throw new Error(`Failed to save signals: ${insertError.message}`)
    }

    return new Response(
      JSON.stringify({
        success: true,
        message: `Generated ${mockSignals.length} trading signals`,
        signals: insertedSignals || [],
        parameters: {
          lookbackDays,
          minConfidence,
          fetchMarketData
        }
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  } catch (error) {
    console.error('Error generating signals:', error)
    return new Response(
      JSON.stringify({ error: error.message }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  }
}

async function handleGetSignalStats(supabaseClient: SupabaseClient, req: Request) {
  try {
    // Get signal statistics
    const { data: signals, error } = await supabaseClient
      .from('trading_signals')
      .select('signal_type, confidence_score')
      .eq('is_active', true)

    if (error) {
      throw new Error(`Failed to fetch signal stats: ${error.message}`)
    }

    // Calculate statistics
    const stats = {
      total_signals: signals?.length || 0,
      average_confidence: 0,
      signal_type_distribution: {} as Record<string, number>,
      high_confidence_signals: 0
    }

    if (signals && signals.length > 0) {
      const confidences = signals.map(s => s.confidence_score)
      stats.average_confidence = confidences.reduce((a, b) => a + b, 0) / confidences.length
      stats.high_confidence_signals = signals.filter(s => s.confidence_score >= 0.8).length

      // Count signal types
      signals.forEach(signal => {
        const type = signal.signal_type
        stats.signal_type_distribution[type] = (stats.signal_type_distribution[type] || 0) + 1
      })
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
    console.error('Error fetching signal stats:', error)
    return new Response(
      JSON.stringify({ error: error.message }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  }
}