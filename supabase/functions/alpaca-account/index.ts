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

    log.info('User authenticated', { requestId, userId: user.id })

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

    // Call Alpaca API to get account information
    const alpacaUrl = `${alpacaBaseUrl || (alpacaPaper ? 'https://paper-api.alpaca.markets' : 'https://api.alpaca.markets')}/v2/account`

    log.info('Calling Alpaca API', { requestId, url: alpacaUrl, paper: alpacaPaper })

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
        JSON.stringify({ error: `Alpaca API error: ${response.status} ${response.statusText}` }),
        {
          status: 500,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    const accountData = await response.json()
    log.info('Alpaca account data retrieved', { requestId, accountId: accountData.id, status: accountData.status })

    // Format response for frontend
    const formattedAccount = {
      portfolio_value: accountData.portfolio_value || '0.00',
      cash: accountData.cash || '0.00',
      buying_power: accountData.buying_power || '0.00',
      status: accountData.status || 'UNKNOWN'
    }

    const duration = Date.now() - startTime

    log.info('Response sent successfully', {
      requestId,
      duration,
      accountStatus: formattedAccount.status
    })

    return new Response(
      JSON.stringify({
        success: true,
        account: formattedAccount
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )

  } catch (error) {
    const duration = Date.now() - startTime
    log.error('Edge function error', error, {
      requestId,
      duration
    })

    return new Response(
      JSON.stringify({ error: error.message }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  }
})