import { createClient } from 'supabase'
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { corsHeaders } from '../_shared/cors.ts'
import { isServiceRoleRequest } from '../_shared/auth.ts'
import { decrypt, encrypt, isEncryptionEnabled } from '../_shared/crypto.ts'

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

// TODO: Review checkCircuitBreaker - implements circuit breaker pattern for API resilience
// - Returns whether request is allowed based on circuit state (closed/open/half-open)
// - Automatically transitions between states based on failure threshold and timeout
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

// TODO: Review recordSuccess - resets circuit breaker on successful API call
function recordSuccess() {
  circuitBreaker.failures = 0
  circuitBreaker.state = 'closed'
  circuitBreaker.lastSuccess = Date.now()
}

// TODO: Review recordFailure - increments failure count and opens circuit if threshold reached
function recordFailure() {
  circuitBreaker.failures++
  circuitBreaker.lastFailure = Date.now()

  if (circuitBreaker.failures >= CIRCUIT_BREAKER_CONFIG.failureThreshold) {
    circuitBreaker.state = 'open'
  }
}

// TODO: Review getCircuitBreakerStatus - returns current circuit breaker state for diagnostics
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

// TODO: Review log object - structured JSON logging with levels (info, error, warn)
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

// TODO: Review getAlpacaCredentials - retrieves Alpaca API credentials
// - Priority: provided params > user_api_keys table > environment variables
// - Supports both paper and live trading modes
// - Decrypts stored credentials if encryption is enabled
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
        const encryptedApiKey = tradingMode === 'paper' ? data.paper_api_key : data.live_api_key;
        const encryptedSecretKey = tradingMode === 'paper' ? data.paper_secret_key : data.live_secret_key;

        if (encryptedApiKey && encryptedSecretKey) {
          // Decrypt credentials (handles both encrypted and legacy unencrypted values)
          const apiKey = await decrypt(encryptedApiKey);
          const secretKey = await decrypt(encryptedSecretKey);

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

// TODO: Review handleHealthCheck - tests Alpaca API connectivity
// - Calls /v2/account endpoint to verify connection
// - Records results to connection_health_log table
// - Updates circuit breaker state based on result
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
          connection_type: tradingMode === 'paper' ? 'alpaca_trading' : 'alpaca_trading',
          endpoint_url: '/v2/account',
          status: isHealthy ? 'healthy' : 'unhealthy',
          response_time_ms: latency,
          http_status_code: response.status,
          diagnostics: {
            requestId,
            tradingMode,
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
          connection_type: 'alpaca_trading',
          endpoint_url: '/v2/account',
          status: 'unhealthy',
          response_time_ms: latency,
          error_message: error.message,
          diagnostics: {
            requestId,
            tradingMode,
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

// TODO: Review handleValidateCredentials - validates Alpaca API credentials
// - Tests credentials by calling account endpoint
// - Updates last_validated_at in user_api_keys table on success
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

// TODO: Review handleConnectionStatus - retrieves connection statistics
// - Fetches recent health check logs from connection_health_log
// - Calculates overall status (connected/degraded/disconnected) based on health rate
async function handleConnectionStatus(
  supabaseClient: any,
  requestId: string
): Promise<Response> {
  try {
    // Get recent health check logs
    const { data: healthLogs, error: healthError } = await supabaseClient
      .from('connection_health_log')
      .select('*')
      .eq('connection_type', 'alpaca_trading')
      .order('checked_at', { ascending: false })
      .limit(10)

    if (healthError) {
      log.warn('Failed to fetch health logs', { error: healthError.message })
    }

    // Calculate connection statistics
    const recentLogs = healthLogs || []
    const healthyCount = recentLogs.filter((l: any) => l.status === 'healthy').length
    const avgLatency = recentLogs.length > 0
      ? recentLogs.reduce((sum: number, l: any) => sum + (l.response_time_ms || 0), 0) / recentLogs.length
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
          latencyMs: l.response_time_ms,
          responseCode: l.http_status_code,
          createdAt: l.checked_at
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

// TODO: Review serve handler - main Alpaca account management endpoint
// - Actions: get-account, get-positions, get-orders, close-position, close-all-shorts,
//            health-check, validate-credentials, connection-status, test-connection
// - Supports user-specific and service role authentication
// - Implements circuit breaker protection for API calls
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

    // Save credentials endpoint (encrypts before storing)
    if (action === 'save-credentials') {
      if (!userEmail) {
        return new Response(
          JSON.stringify({ success: false, error: 'User authentication required to save credentials' }),
          { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }

      const { apiKey, secretKey } = bodyParams
      if (!apiKey || !secretKey) {
        return new Response(
          JSON.stringify({ success: false, error: 'API key and secret key are required' }),
          { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }

      try {
        // Encrypt credentials before storage
        const encryptedApiKey = await encrypt(apiKey)
        const encryptedSecretKey = await encrypt(secretKey)

        log.info('Encrypting credentials', {
          requestId,
          tradingMode,
          encryptionEnabled: isEncryptionEnabled(),
          apiKeyEncrypted: encryptedApiKey.startsWith('enc:'),
          secretKeyEncrypted: encryptedSecretKey.startsWith('enc:')
        })

        // Prepare update data based on trading mode
        const updateData = tradingMode === 'paper'
          ? {
              paper_api_key: encryptedApiKey,
              paper_secret_key: encryptedSecretKey,
              paper_validated_at: new Date().toISOString(),
            }
          : {
              live_api_key: encryptedApiKey,
              live_secret_key: encryptedSecretKey,
              live_validated_at: new Date().toISOString(),
            }

        // Check if user record exists
        const { data: existing } = await supabaseClient
          .from('user_api_keys')
          .select('id')
          .eq('user_email', userEmail)
          .maybeSingle()

        if (existing) {
          // Update existing record
          const { error: updateError } = await supabaseClient
            .from('user_api_keys')
            .update(updateData)
            .eq('user_email', userEmail)

          if (updateError) {
            log.error('Failed to update credentials', { requestId, error: updateError.message })
            return new Response(
              JSON.stringify({ success: false, error: 'Failed to save credentials' }),
              { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
            )
          }
        } else {
          // Insert new record
          const { error: insertError } = await supabaseClient
            .from('user_api_keys')
            .insert({
              user_email: userEmail,
              ...updateData,
            })

          if (insertError) {
            log.error('Failed to insert credentials', { requestId, error: insertError.message })
            return new Response(
              JSON.stringify({ success: false, error: 'Failed to save credentials' }),
              { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
            )
          }
        }

        log.info('Credentials saved successfully', { requestId, tradingMode, encrypted: isEncryptionEnabled() })

        return new Response(
          JSON.stringify({
            success: true,
            message: 'Credentials saved successfully',
            encrypted: isEncryptionEnabled()
          }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      } catch (error) {
        log.error('Error saving credentials', error, { requestId })
        return new Response(
          JSON.stringify({ success: false, error: 'Failed to encrypt or save credentials' }),
          { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }
    }

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

    // Close a specific position by symbol
    if (action === 'close-position') {
      const symbol = bodyParams.symbol
      if (!symbol) {
        return new Response(
          JSON.stringify({ success: false, error: 'Symbol is required' }),
          { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      }

      try {
        const closeUrl = `${credentials.baseUrl}/v2/positions/${encodeURIComponent(symbol)}`
        log.info('Closing position', { requestId, symbol, url: closeUrl })

        const closeResponse = await fetch(closeUrl, {
          method: 'DELETE',
          headers: {
            'APCA-API-KEY-ID': credentials.apiKey,
            'APCA-API-SECRET-KEY': credentials.secretKey,
            'Content-Type': 'application/json'
          }
        })

        if (!closeResponse.ok) {
          recordFailure()
          const errorText = await closeResponse.text()
          log.error('Failed to close position', { requestId, symbol, status: closeResponse.status, error: errorText })
          return new Response(
            JSON.stringify({ success: false, error: `Failed to close ${symbol} (${closeResponse.status}): ${errorText}` }),
            { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }

        recordSuccess()
        const order = await closeResponse.json()
        log.info('Position close order submitted', { requestId, symbol, orderId: order.id, side: order.side })

        return new Response(
          JSON.stringify({ success: true, symbol, order }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      } catch (fetchError) {
        recordFailure()
        throw fetchError
      }
    }

    // Close all short positions
    if (action === 'close-all-shorts') {
      try {
        // First get all positions
        const positionsUrl = `${credentials.baseUrl}/v2/positions`
        const posResponse = await fetch(positionsUrl, {
          method: 'GET',
          headers: {
            'APCA-API-KEY-ID': credentials.apiKey,
            'APCA-API-SECRET-KEY': credentials.secretKey,
            'Content-Type': 'application/json'
          }
        })

        if (!posResponse.ok) {
          recordFailure()
          return new Response(
            JSON.stringify({ success: false, error: `Failed to fetch positions (${posResponse.status})` }),
            { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }

        const positions = await posResponse.json()
        const shorts = positions.filter((p: any) => p.side === 'short')
        log.info('Found short positions to close', { requestId, count: shorts.length })

        if (shorts.length === 0) {
          return new Response(
            JSON.stringify({ success: true, message: 'No short positions found', closed: [] }),
            { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }

        // Close each short position sequentially
        const results: any[] = []
        for (const pos of shorts) {
          const symbol = pos.symbol
          try {
            const closeUrl = `${credentials.baseUrl}/v2/positions/${encodeURIComponent(symbol)}`
            const closeResponse = await fetch(closeUrl, {
              method: 'DELETE',
              headers: {
                'APCA-API-KEY-ID': credentials.apiKey,
                'APCA-API-SECRET-KEY': credentials.secretKey,
                'Content-Type': 'application/json'
              }
            })

            if (closeResponse.ok) {
              const order = await closeResponse.json()
              results.push({ symbol, success: true, orderId: order.id, qty: parseFloat(pos.qty), market_value: parseFloat(pos.market_value) })
              log.info('Closed short position', { requestId, symbol, orderId: order.id })
            } else {
              const errorText = await closeResponse.text()
              results.push({ symbol, success: false, error: `${closeResponse.status}: ${errorText}` })
              log.error('Failed to close short', { requestId, symbol, status: closeResponse.status, error: errorText })
            }
          } catch (err) {
            results.push({ symbol, success: false, error: err.message })
            log.error('Error closing short', err, { requestId, symbol })
          }
        }

        recordSuccess()
        const closedCount = results.filter(r => r.success).length
        const totalValue = results.filter(r => r.success).reduce((sum, r) => sum + Math.abs(r.market_value || 0), 0)

        return new Response(
          JSON.stringify({
            success: true,
            message: `Closed ${closedCount}/${shorts.length} short positions`,
            totalMarketValue: totalValue,
            results
          }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      } catch (fetchError) {
        recordFailure()
        throw fetchError
      }
    }

    // Get all orders (recent)
    if (action === 'get-orders') {
      const status = bodyParams.status || 'all'
      const limit = bodyParams.limit || 50

      try {
        const ordersUrl = `${credentials.baseUrl}/v2/orders?status=${status}&limit=${limit}&direction=desc`
        const ordResponse = await fetch(ordersUrl, {
          method: 'GET',
          headers: {
            'APCA-API-KEY-ID': credentials.apiKey,
            'APCA-API-SECRET-KEY': credentials.secretKey,
            'Content-Type': 'application/json'
          }
        })

        if (!ordResponse.ok) {
          recordFailure()
          const errorText = await ordResponse.text()
          return new Response(
            JSON.stringify({ success: false, error: `Failed to fetch orders (${ordResponse.status})` }),
            { status: 200, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
          )
        }

        recordSuccess()
        const orders = await ordResponse.json()
        const formattedOrders = orders.map((o: any) => ({
          id: o.id,
          symbol: o.symbol,
          side: o.side,
          type: o.type,
          qty: o.qty,
          filled_qty: o.filled_qty,
          status: o.status,
          submitted_at: o.submitted_at,
          filled_at: o.filled_at,
          filled_avg_price: o.filled_avg_price,
          time_in_force: o.time_in_force,
        }))

        return new Response(
          JSON.stringify({ success: true, orders: formattedOrders, count: formattedOrders.length }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
      } catch (fetchError) {
        recordFailure()
        throw fetchError
      }
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
