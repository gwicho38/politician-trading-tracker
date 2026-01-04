import { createClient } from 'supabase'
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

// Helper to check if request is using service role key (for scheduled jobs)
function isServiceRoleRequest(req: Request): boolean {
  const authHeader = req.headers.get('authorization')
  if (!authHeader) return false

  const token = authHeader.replace('Bearer ', '')
  const serviceRoleKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') || ''

  return token === serviceRoleKey
}

// =============================================================================
// CIRCUIT BREAKER PATTERN
// =============================================================================

interface CircuitBreakerState {
  failures: number
  lastFailure: number
  state: 'closed' | 'open' | 'half-open'
  lastSuccess: number
}

// In-memory circuit breaker (resets on function cold start)
const circuitBreaker: CircuitBreakerState = {
  failures: 0,
  lastFailure: 0,
  state: 'closed',
  lastSuccess: Date.now()
}

const CIRCUIT_BREAKER_CONFIG = {
  failureThreshold: 5,      // Open circuit after 5 failures
  resetTimeout: 30000,      // Try again after 30 seconds
  halfOpenRequests: 2       // Allow 2 requests in half-open state
}

function checkCircuitBreaker(): { allowed: boolean; reason?: string } {
  const now = Date.now()

  if (circuitBreaker.state === 'closed') {
    return { allowed: true }
  }

  if (circuitBreaker.state === 'open') {
    // Check if we should transition to half-open
    if (now - circuitBreaker.lastFailure > CIRCUIT_BREAKER_CONFIG.resetTimeout) {
      circuitBreaker.state = 'half-open'
      circuitBreaker.failures = 0
      return { allowed: true }
    }
    return {
      allowed: false,
      reason: `Circuit breaker open. Retry after ${Math.ceil((CIRCUIT_BREAKER_CONFIG.resetTimeout - (now - circuitBreaker.lastFailure)) / 1000)}s`
    }
  }

  // half-open state - allow limited requests
  return { allowed: true }
}

function recordSuccess() {
  circuitBreaker.failures = 0
  circuitBreaker.state = 'closed'
  circuitBreaker.lastSuccess = Date.now()
}

function recordFailure() {
  circuitBreaker.failures++
  circuitBreaker.lastFailure = Date.now()

  if (circuitBreaker.failures >= CIRCUIT_BREAKER_CONFIG.failureThreshold) {
    circuitBreaker.state = 'open'
  }
}

function getCircuitBreakerStatus(): {
  state: string
  failures: number
  lastSuccess: string
  lastFailure: string | null
} {
  return {
    state: circuitBreaker.state,
    failures: circuitBreaker.failures,
    lastSuccess: new Date(circuitBreaker.lastSuccess).toISOString(),
    lastFailure: circuitBreaker.lastFailure ? new Date(circuitBreaker.lastFailure).toISOString() : null
  }
}

// Structured logging utility
const log = {
  info: (message: string, metadata?: any) => {
    console.log(JSON.stringify({
      level: 'INFO',
      timestamp: new Date().toISOString(),
      service: 'alpaca-account',
      message,
      ...metadata
    }))
  },
  error: (message: string, error?: any, metadata?: any) => {
    console.error(JSON.stringify({
      level: 'ERROR',
      timestamp: new Date().toISOString(),
      service: 'alpaca-account',
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
      service: 'alpaca-account',
      message,
      ...metadata
    }))
  }
}

// Get Alpaca credentials - supports per-user credentials or environment variables
async function getAlpacaCredentials(
  supabase: any,
  userEmail: string | null,
  tradingMode: 'paper' | 'live',
  providedApiKey?: string,
  providedSecretKey?: string
): Promise<{ apiKey: string; secretKey: string; baseUrl: string } | null> {
  // 1. Use provided credentials (for test-connection)
  if (providedApiKey && providedSecretKey) {
    const baseUrl = tradingMode === 'paper'
      ? 'https://paper-api.alpaca.markets'
      : 'https://api.alpaca.markets';
    return { apiKey: providedApiKey, secretKey: providedSecretKey, baseUrl };
  }

  // 2. Try user-specific credentials from user_api_keys table
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
      log.warn('Could not fetch user credentials', { error: err.message });
    }
  }

  // 3. Fallback to environment variables (for system operations)
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
// HANDLER FUNCTIONS
// =============================================================================

async function handleHealthCheck(
  supabaseClient: any,
  credentials: { apiKey: string; secretKey: string; baseUrl: string },
  tradingMode: 'paper' | 'live',
  requestId: string
): Promise<Response> {
  const startTime = Date.now()

  try {
    // Test Alpaca API connectivity
    const alpacaUrl = `${credentials.baseUrl}/v2/account`
    const response = await fetch(alpacaUrl, {
      method: 'GET',
      headers: {
        'APCA-API-KEY-ID': credentials.apiKey,
        'APCA-API-SECRET-KEY': credentials.secretKey,
        'Content-Type': 'application/json'
      }
    })

    const latency = Date.now() - startTime
    const isHealthy = response.ok

    if (isHealthy) {
      recordSuccess()
    } else {
      recordFailure()
    }

    // Log health check to connection_health_log
    try {
      await supabaseClient
        .from('connection_health_log')
        .insert({
          service_name: 'alpaca',
          endpoint: '/v2/account',
          status: isHealthy ? 'healthy' : 'unhealthy',
          latency_ms: latency,
          response_code: response.status,
          trading_mode: tradingMode,
          metadata: {
            requestId,
            circuitBreaker: getCircuitBreakerStatus()
          }
        })
    } catch (logError) {
      log.warn('Failed to log health check', { error: logError.message })
    }

    return new Response(
      JSON.stringify({
        success: true,
        healthy: isHealthy,
        latency,
        status: response.status,
        tradingMode,
        circuitBreaker: getCircuitBreakerStatus(),
        timestamp: new Date().toISOString()
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    recordFailure()
    const latency = Date.now() - startTime

    // Log failed health check
    try {
      await supabaseClient
        .from('connection_health_log')
        .insert({
          service_name: 'alpaca',
          endpoint: '/v2/account',
          status: 'error',
          latency_ms: latency,
          error_message: error.message,
          trading_mode: tradingMode,
          metadata: {
            requestId,
            circuitBreaker: getCircuitBreakerStatus()
          }
        })
    } catch (logError) {
      log.warn('Failed to log health check error', { error: logError.message })
    }

    return new Response(
      JSON.stringify({
        success: false,
        healthy: false,
        error: error.message,
        latency,
        tradingMode,
        circuitBreaker: getCircuitBreakerStatus(),
        timestamp: new Date().toISOString()
      }),
      { status: 503, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}

async function handleValidateCredentials(
  supabaseClient: any,
  credentials: { apiKey: string; secretKey: string; baseUrl: string },
  tradingMode: 'paper' | 'live',
  requestId: string,
  userEmail: string | null
): Promise<Response> {
  try {
    // Test credentials by calling account endpoint
    const alpacaUrl = `${credentials.baseUrl}/v2/account`
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
      log.warn('Credential validation failed', { requestId, status: response.status, error: errorText })

      return new Response(
        JSON.stringify({
          success: false,
          valid: false,
          error: `Invalid credentials (${response.status})`,
          tradingMode
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    const accountData = await response.json()

    // Update last_validated_at in user_api_keys if user email provided
    if (userEmail) {
      try {
        await supabaseClient
          .from('user_api_keys')
          .update({
            last_validated_at: new Date().toISOString(),
            validation_status: 'valid'
          })
          .eq('user_email', userEmail)
      } catch (updateError) {
        log.warn('Failed to update credential validation status', { error: updateError.message })
      }
    }

    log.info('Credentials validated successfully', { requestId, accountId: accountData.id })

    return new Response(
      JSON.stringify({
        success: true,
        valid: true,
        accountStatus: accountData.status,
        tradingMode,
        timestamp: new Date().toISOString()
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    log.error('Credential validation error', error, { requestId })

    return new Response(
      JSON.stringify({
        success: false,
        valid: false,
        error: error.message,
        tradingMode
      }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}

async function handleConnectionStatus(
  supabaseClient: any,
  requestId: string
): Promise<Response> {
  try {
    // Get recent health check logs
    const { data: healthLogs, error: healthError } = await supabaseClient
      .from('connection_health_log')
      .select('*')
      .eq('service_name', 'alpaca')
      .order('created_at', { ascending: false })
      .limit(10)

    if (healthError) {
      log.warn('Failed to fetch health logs', { error: healthError.message })
    }

    // Calculate connection statistics
    const recentLogs = healthLogs || []
    const healthyCount = recentLogs.filter((l: any) => l.status === 'healthy').length
    const avgLatency = recentLogs.length > 0
      ? recentLogs.reduce((sum: number, l: any) => sum + (l.latency_ms || 0), 0) / recentLogs.length
      : null

    // Determine overall status
    let overallStatus: 'connected' | 'degraded' | 'disconnected' = 'disconnected'
    if (recentLogs.length > 0) {
      const healthRate = healthyCount / recentLogs.length
      if (healthRate >= 0.8) {
        overallStatus = 'connected'
      } else if (healthRate >= 0.5) {
        overallStatus = 'degraded'
      }
    }

    return new Response(
      JSON.stringify({
        success: true,
        status: overallStatus,
        circuitBreaker: getCircuitBreakerStatus(),
        statistics: {
          recentChecks: recentLogs.length,
          healthyChecks: healthyCount,
          healthRate: recentLogs.length > 0 ? (healthyCount / recentLogs.length * 100).toFixed(1) + '%' : 'N/A',
          avgLatencyMs: avgLatency ? Math.round(avgLatency) : null
        },
        recentLogs: recentLogs.slice(0, 5).map((l: any) => ({
          status: l.status,
          latencyMs: l.latency_ms,
          responseCode: l.response_code,
          createdAt: l.created_at
        })),
        timestamp: new Date().toISOString()
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    log.error('Connection status error', error, { requestId })

    return new Response(
      JSON.stringify({
        success: false,
        error: error.message,
        circuitBreaker: getCircuitBreakerStatus()
      }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}

serve(async (req) => {
  const startTime = Date.now()
  const requestId = crypto.randomUUID().substring(0, 8)

  // Log full request details
  log.info('Request received', {
    requestId,
    method: req.method,
    url: req.url
  })

  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    log.info('CORS preflight handled', { requestId })
    const corsResponse = new Response('ok', { headers: corsHeaders })
    return corsResponse
  }

  try {
    // Initialize Supabase client
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    // Parse request body
    let bodyParams: any = {};
    if (req.method === 'POST') {
      try {
        bodyParams = await req.json();
      } catch {
        // Body parsing failed, use empty object
      }
    }

    const action = bodyParams.action || 'get-account';
    const tradingMode: 'paper' | 'live' = bodyParams.tradingMode || 'paper';

    log.info('Processing request', { requestId, action, tradingMode });

    // Check if this is a service role request (scheduled job)
    const isServerRequest = isServiceRoleRequest(req)
    let userEmail: string | null = null;

    if (isServerRequest) {
      log.info('Service role request (scheduled job)', { requestId })
    } else {
      // Validate user authentication for client requests
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

      userEmail = user.email || null;
      log.info('User authenticated', { requestId, userId: user.id, email: userEmail })
    }

    // Get Alpaca credentials (provided, per-user, or environment)
    const credentials = await getAlpacaCredentials(
      supabaseClient,
      userEmail,
      tradingMode,
      bodyParams.apiKey,
      bodyParams.secretKey
    );

    if (!credentials) {
      log.error('No Alpaca credentials available', { requestId });
      return new Response(
        JSON.stringify({
          success: false,
          error: 'No Alpaca credentials configured. Please connect your Alpaca account.'
        }),
        {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Handle different actions

    // Health check endpoint
    if (action === 'health-check') {
      return await handleHealthCheck(supabaseClient, credentials, tradingMode, requestId)
    }

    // Validate credentials endpoint
    if (action === 'validate-credentials') {
      return await handleValidateCredentials(supabaseClient, credentials, tradingMode, requestId, userEmail)
    }

    // Connection status endpoint
    if (action === 'connection-status') {
      return await handleConnectionStatus(supabaseClient, requestId)
    }

    // Check circuit breaker before making API calls
    const circuitCheck = checkCircuitBreaker()
    if (!circuitCheck.allowed) {
      log.warn('Circuit breaker blocking request', { requestId, reason: circuitCheck.reason })
      return new Response(
        JSON.stringify({
          success: false,
          error: circuitCheck.reason,
          circuitBreaker: getCircuitBreakerStatus()
        }),
        { status: 503, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    if (action === 'get-positions') {
      // Fetch positions from Alpaca
      const positionsUrl = `${credentials.baseUrl}/v2/positions`;
      log.info('Fetching positions from Alpaca', { requestId, url: positionsUrl, tradingMode });

      try {
        const posResponse = await fetch(positionsUrl, {
          method: 'GET',
          headers: {
            'APCA-API-KEY-ID': credentials.apiKey,
            'APCA-API-SECRET-KEY': credentials.secretKey,
            'Content-Type': 'application/json'
          }
        });

        if (!posResponse.ok) {
          recordFailure()
          const errorText = await posResponse.text();
          log.error('Alpaca positions API error', { requestId, status: posResponse.status, error: errorText });
          return new Response(
            JSON.stringify({ success: false, error: `Failed to fetch positions (${posResponse.status})` }),
            { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          );
        }

        recordSuccess()
        const positions = await posResponse.json();
        log.info('Positions fetched', { requestId, count: positions.length });

        // Format positions
        const formattedPositions = positions.map((pos: any) => ({
          asset_id: pos.asset_id,
          symbol: pos.symbol,
          exchange: pos.exchange,
          asset_class: pos.asset_class,
          avg_entry_price: parseFloat(pos.avg_entry_price) || 0,
          qty: parseFloat(pos.qty) || 0,
          side: pos.side,
          market_value: parseFloat(pos.market_value) || 0,
          cost_basis: parseFloat(pos.cost_basis) || 0,
          unrealized_pl: parseFloat(pos.unrealized_pl) || 0,
          unrealized_plpc: parseFloat(pos.unrealized_plpc) || 0,
          unrealized_intraday_pl: parseFloat(pos.unrealized_intraday_pl) || 0,
          unrealized_intraday_plpc: parseFloat(pos.unrealized_intraday_plpc) || 0,
          current_price: parseFloat(pos.current_price) || 0,
          lastday_price: parseFloat(pos.lastday_price) || 0,
          change_today: parseFloat(pos.change_today) || 0,
        }));

        return new Response(
          JSON.stringify({
            success: true,
            positions: formattedPositions,
            tradingMode,
          }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        );
      } catch (fetchError) {
        recordFailure()
        throw fetchError
      }
    }

    // Call Alpaca API to get account information
    const alpacaUrl = `${credentials.baseUrl}/v2/account`

    log.info('Calling Alpaca API', { requestId, url: alpacaUrl, tradingMode })

    const response = await fetch(alpacaUrl, {
      method: 'GET',
      headers: {
        'APCA-API-KEY-ID': credentials.apiKey,
        'APCA-API-SECRET-KEY': credentials.secretKey,
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      recordFailure()
      const errorText = await response.text()
      log.error('Alpaca API error', { requestId, status: response.status, error: errorText })

      // For test-connection, return a more helpful error
      if (action === 'test-connection') {
        return new Response(
          JSON.stringify({
            success: false,
            error: `Invalid API credentials or Alpaca API error (${response.status})`
          }),
          {
            status: 200, // Return 200 so the client can handle the error gracefully
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          }
        )
      }

      return new Response(
        JSON.stringify({ error: `Alpaca API error: ${response.status} ${response.statusText}` }),
        {
          status: 500,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    recordSuccess()
    const accountData = await response.json()
    log.info('Alpaca account data retrieved', { requestId, accountId: accountData.id, status: accountData.status })

    // Format response for frontend
    const formattedAccount = {
      portfolio_value: parseFloat(accountData.portfolio_value) || 0,
      cash: parseFloat(accountData.cash) || 0,
      buying_power: parseFloat(accountData.buying_power) || 0,
      status: accountData.status || 'UNKNOWN',
      currency: accountData.currency || 'USD',
      equity: parseFloat(accountData.equity) || 0,
      last_equity: parseFloat(accountData.last_equity) || 0,
      long_market_value: parseFloat(accountData.long_market_value) || 0,
      short_market_value: parseFloat(accountData.short_market_value) || 0,
      pattern_day_trader: accountData.pattern_day_trader || false,
      trading_blocked: accountData.trading_blocked || false,
      transfers_blocked: accountData.transfers_blocked || false,
      account_blocked: accountData.account_blocked || false,
    }

    const duration = Date.now() - startTime

    log.info('Response sent successfully', {
      requestId,
      duration,
      action,
      accountStatus: formattedAccount.status
    })

    return new Response(
      JSON.stringify({
        success: true,
        account: formattedAccount,
        tradingMode,
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )

  } catch (error) {
    recordFailure()
    const duration = Date.now() - startTime
    log.error('Edge function error', error, {
      requestId,
      duration,
      circuitBreaker: getCircuitBreakerStatus()
    })

    return new Response(
      JSON.stringify({
        success: false,
        error: error.message,
        circuitBreaker: getCircuitBreakerStatus()
      }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  }
})
