import { createClient } from 'supabase'
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { corsHeaders } from '../_shared/cors.ts'

// Reference portfolio configuration
const REFERENCE_PORTFOLIO_MIN_CONFIDENCE = 0.70
const REFERENCE_PORTFOLIO_SIGNAL_TYPES = ['buy', 'strong_buy', 'sell', 'strong_sell']

// TODO: Review queueSignalsForReferencePortfolio - queues high-confidence signals for automated portfolio
// - Filters signals meeting min confidence threshold (0.70)
// - Upserts to reference_portfolio_signal_queue table for background processing
async function queueSignalsForReferencePortfolio(supabaseClient: any, signals: any[], requestId: string) {
  if (!signals || signals.length === 0) return

  // Filter signals that meet reference portfolio criteria
  // Use lower confidence threshold for sell signals to exit positions faster
  const eligibleSignals = signals.filter(signal => {
    const isSellSignal = ['sell', 'strong_sell'].includes(signal.signal_type)
    const confidenceThreshold = isSellSignal 
      ? REFERENCE_PORTFOLIO_MIN_CONFIDENCE * 0.85  // 85% of buy threshold (0.60 if buy is 0.70)
      : REFERENCE_PORTFOLIO_MIN_CONFIDENCE
    
    return signal.confidence_score >= confidenceThreshold &&
      REFERENCE_PORTFOLIO_SIGNAL_TYPES.includes(signal.signal_type)
  })

  if (eligibleSignals.length === 0) {
    console.log(JSON.stringify({
      level: 'INFO',
      timestamp: new Date().toISOString(),
      service: 'trading-signals',
      message: 'No signals eligible for reference portfolio',
      requestId,
      totalSignals: signals.length,
      minConfidence: REFERENCE_PORTFOLIO_MIN_CONFIDENCE
    }))
    return
  }

  // Queue signals for reference portfolio processing
  const queueEntries = eligibleSignals.map(signal => ({
    signal_id: signal.id,
    status: 'pending'
  }))

  const { error } = await supabaseClient
    .from('reference_portfolio_signal_queue')
    .upsert(queueEntries, { onConflict: 'signal_id', ignoreDuplicates: true })

  if (error) {
    console.error(JSON.stringify({
      level: 'ERROR',
      timestamp: new Date().toISOString(),
      service: 'trading-signals',
      message: 'Failed to queue signals for reference portfolio',
      requestId,
      error: error.message,
      signalCount: eligibleSignals.length
    }))
  } else {
    console.log(JSON.stringify({
      level: 'INFO',
      timestamp: new Date().toISOString(),
      service: 'trading-signals',
      message: 'Signals queued for reference portfolio',
      requestId,
      queuedCount: eligibleSignals.length,
      tickers: eligibleSignals.map(s => s.ticker)
    }))
  }
}

// TODO: Review log object - structured JSON logging utility with service identification
const log = {
  info: (message: string, metadata?: any) => {
    console.log(JSON.stringify({
      level: 'INFO',
      timestamp: new Date().toISOString(),
      service: 'trading-signals',
      message,
      ...metadata
    }))
  },
  error: (message: string, error?: any, metadata?: any) => {
    console.error(JSON.stringify({
      level: 'ERROR',
      timestamp: new Date().toISOString(),
      service: 'trading-signals',
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
      service: 'trading-signals',
      message,
      ...metadata
    }))
  }
}

// TODO: Review sanitizeRequestForLogging - removes sensitive headers before logging
// - Redacts authorization, x-api-key, cookie, x-supabase-auth
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

// TODO: Review sanitizeResponseForLogging - extracts loggable response metadata
// - Truncates body to 500 chars to prevent log bloat
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

// TODO: Review serve handler - main entry point for trading signals edge function
// - Routes to: get-signals, generate-signals, regenerate-signals, get-signal-stats,
//   update-target-prices, preview-signals, test
// - Logs full request/response details with timing metrics
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
        // Get-signals is public - create a new client without auth context
        const publicClient = createClient(
          Deno.env.get('SUPABASE_URL') ?? '',
          Deno.env.get('SUPABASE_ANON_KEY') ?? ''
        )
        response = await handleGetSignals(publicClient, req, requestId)
        break
      case 'generate-signals':
        response = await handleGenerateSignals(supabaseClient, req, requestId)
        break
      case 'regenerate-signals':
        // Service-level regeneration for scheduled jobs (no user auth required)
        response = await handleRegenerateSignals(supabaseClient, req, requestId)
        break
      case 'get-signal-stats':
        response = await handleGetSignalStats(supabaseClient, req, requestId)
        break
      case 'update-target-prices':
        response = await handleUpdateTargetPrices(supabaseClient, req, requestId)
        break
      case 'preview-signals':
        // Preview signals with custom weights (no DB persist, no auth required)
        response = await handlePreviewSignals(supabaseClient, req, requestId)
        break
      case 'test':
        log.info('Test endpoint called', { requestId })
        response = new Response(
          JSON.stringify({ success: true, message: 'Trading signals function is working', timestamp: new Date().toISOString() }),
          {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          }
        )
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

// TODO: Review handleGetSignals - retrieves active trading signals with pagination
// - Supports filtering by signal_type and min_confidence via query params
// - Returns paginated results with total count for UI
async function handleGetSignals(supabaseClient: any, req: Request, requestId: string) {
  const handlerStartTime = Date.now()
  try {
    const url = new URL(req.url)
    const limit = parseInt(url.searchParams.get('limit') || '100')
    const offset = parseInt(url.searchParams.get('offset') || '0')
    const signalType = url.searchParams.get('signal_type')
    const minConfidence = parseFloat(url.searchParams.get('min_confidence') || '0')

    log.info('Fetching trading signals - handler started', {
      requestId,
      handler: 'get-signals',
      params: { limit, offset, signalType, minConfidence },
      request: sanitizeRequestForLogging(req)
    })

    // First, let's check if the table exists and get a simple count
    log.info('Checking table existence', { requestId })
    const { count: tableCheck, error: tableError } = await supabaseClient
      .from('trading_signals')
      .select('*', { count: 'exact', head: true })

    if (tableError) {
      log.error('Table check failed', tableError, { requestId })
      throw new Error(`Table check failed: ${tableError.message}`)
    }

    log.info('Table exists, count:', { requestId, count: tableCheck })

    // Now try to get some data
    let query = supabaseClient
      .from('trading_signals')
      .select('*')
      .eq('is_active', true)
      .order('created_at', { ascending: false }) // Use created_at instead of confidence_score initially
      .limit(limit)

    // Remove filters that might cause issues
    // if (signalType && signalType !== 'all') {
    //   query = query.eq('signal_type', signalType)
    // }

    // if (minConfidence > 0) {
    //   query = query.gte('confidence_score', minConfidence)
    // }

    log.info('Executing query', { requestId })
    const { data: signals, error } = await query

    if (error) {
      log.error('Database query failed', error, { requestId })
      throw new Error(`Failed to fetch signals: ${error.message}`)
    }

    log.info('Query successful', { requestId, signalCount: signals?.length || 0 })

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

// TODO: Review handleGenerateSignals - generates new trading signals from disclosure data
// - Requires authentication; aggregates disclosures by ticker over lookback period
// - Calculates confidence from politician count, bipartisan activity, volume
// - Optionally fetches market data and calculates target prices
// - Records audit trail and queues for reference portfolio
async function handleGenerateSignals(supabaseClient: any, req: Request, requestId: string) {
  const handlerStartTime = Date.now()
  try {
    const body = await req.json()
    const { lookbackDays = 30, minConfidence = 0.65, fetchMarketData = true } = body

    log.info('Generating signals - handler started', {
      requestId,
      handler: 'generate-signals',
      params: { lookbackDays, minConfidence, fetchMarketData }
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

    // Calculate date range for lookback
    const endDate = new Date()
    const startDate = new Date()
    startDate.setDate(startDate.getDate() - lookbackDays)
    const startDateStr = startDate.toISOString().split('T')[0]

    log.info('Querying trading disclosures', {
      requestId,
      startDate: startDateStr,
      lookbackDays
    })

    // Query trading disclosures within the lookback period
    const { data: disclosures, error: disclosureError } = await supabaseClient
      .from('trading_disclosures')
      .select(`
        id,
        asset_ticker,
        asset_name,
        transaction_type,
        amount_range_min,
        amount_range_max,
        transaction_date,
        politician_id,
        politician:politicians(id, full_name, party)
      `)
      .eq('status', 'active')
      .not('asset_ticker', 'is', null)
      .gte('transaction_date', startDateStr)
      .order('transaction_date', { ascending: false })

    if (disclosureError) {
      log.error('Failed to fetch disclosures', disclosureError, { requestId })
      throw new Error(`Failed to fetch disclosures: ${disclosureError.message}`)
    }

    log.info('Disclosures fetched', {
      requestId,
      count: disclosures?.length || 0
    })

    if (!disclosures || disclosures.length === 0) {
      return new Response(
        JSON.stringify({
          success: true,
          message: 'No trading activity found in the lookback period',
          signals: [],
          parameters: { lookbackDays, minConfidence, fetchMarketData }
        }),
        {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Aggregate disclosures by ticker
    const tickerData: Record<string, {
      ticker: string
      assetName: string
      buys: number
      sells: number
      buyVolume: number
      sellVolume: number
      politicians: Set<string>
      parties: Set<string>
      recentActivity: number
      disclosureIds: string[]
    }> = {}

    const thirtyDaysAgo = new Date()
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)

    for (const disclosure of disclosures) {
      const ticker = disclosure.asset_ticker?.toUpperCase()
      if (!ticker || ticker.length < 1 || ticker.length > 10) continue
      // Skip non-stock tickers (real estate, bonds, etc.)
      if (ticker.includes(' ') || ticker.includes('[') || ticker.includes('(')) continue

      if (!tickerData[ticker]) {
        tickerData[ticker] = {
          ticker,
          assetName: disclosure.asset_name || ticker,
          buys: 0,
          sells: 0,
          buyVolume: 0,
          sellVolume: 0,
          politicians: new Set(),
          parties: new Set(),
          recentActivity: 0,
          disclosureIds: []
        }
      }

      const data = tickerData[ticker]
      const txType = (disclosure.transaction_type || '').toLowerCase()
      const minVal = disclosure.amount_range_min || 0
      const maxVal = disclosure.amount_range_max || minVal
      const volume = (minVal + maxVal) / 2

      if (txType.includes('purchase') || txType.includes('buy')) {
        data.buys++
        data.buyVolume += volume
      } else if (txType.includes('sale') || txType.includes('sell')) {
        data.sells++
        data.sellVolume += volume
      }

      if (disclosure.politician_id) {
        data.politicians.add(disclosure.politician_id)
      }
      if (disclosure.politician?.party) {
        data.parties.add(disclosure.politician.party)
      }

      // Track recent activity (last 30 days)
      const txDate = new Date(disclosure.transaction_date)
      if (txDate >= thirtyDaysAgo) {
        data.recentActivity++
      }

      data.disclosureIds.push(disclosure.id)
    }

    log.info('Aggregated ticker data', {
      requestId,
      uniqueTickers: Object.keys(tickerData).length
    })

    // Generate signals for tickers with enough activity
    const generatedSignals: any[] = []
    const MIN_POLITICIANS = 2
    const MIN_TRANSACTIONS = 3

    for (const [ticker, data] of Object.entries(tickerData)) {
      const totalTx = data.buys + data.sells
      const politicianCount = data.politicians.size

      // Filter: require minimum politicians and transactions
      if (politicianCount < MIN_POLITICIANS || totalTx < MIN_TRANSACTIONS) {
        continue
      }

      // Calculate buy/sell ratio
      const buySellRatio = data.sells > 0 ? data.buys / data.sells : data.buys > 0 ? 10 : 1

      // Calculate confidence based on various factors
      let confidence = 0.5

      // Factor 1: Politician count (more = more confidence)
      if (politicianCount >= 5) confidence += 0.15
      else if (politicianCount >= 3) confidence += 0.10
      else confidence += 0.05

      // Factor 2: Recent activity
      if (data.recentActivity >= 5) confidence += 0.10
      else if (data.recentActivity >= 2) confidence += 0.05

      // Factor 3: Bipartisan activity (both D and R trading)
      if (data.parties.has('D') && data.parties.has('R')) {
        confidence += 0.10
      }

      // Factor 4: Volume magnitude
      const netVolume = data.buyVolume - data.sellVolume
      if (Math.abs(netVolume) > 1000000) confidence += 0.10
      else if (Math.abs(netVolume) > 100000) confidence += 0.05

      // Determine signal type based on buy/sell ratio
      let signalType: string
      let signalStrength: string

      if (buySellRatio >= 3.0) {
        signalType = 'strong_buy'
        signalStrength = 'very_strong'
        confidence = Math.min(confidence + 0.15, 0.95)
      } else if (buySellRatio >= 2.0) {
        signalType = 'buy'
        signalStrength = 'strong'
        confidence = Math.min(confidence + 0.10, 0.90)
      } else if (buySellRatio <= 0.33) {
        signalType = 'strong_sell'
        signalStrength = 'very_strong'
        confidence = Math.min(confidence + 0.15, 0.95)
      } else if (buySellRatio <= 0.5) {
        signalType = 'sell'
        signalStrength = 'strong'
        confidence = Math.min(confidence + 0.10, 0.90)
      } else {
        signalType = 'hold'
        signalStrength = 'moderate'
      }

      // Skip if below minimum confidence
      if (confidence < minConfidence) {
        continue
      }

      // Skip HOLD signals (only generate actionable signals)
      if (signalType === 'hold') {
        continue
      }

      generatedSignals.push({
        ticker,
        asset_name: data.assetName,
        signal_type: signalType,
        signal_strength: signalStrength,
        confidence_score: Math.round(confidence * 100) / 100,
        politician_activity_count: politicianCount,
        buy_sell_ratio: Math.round(buySellRatio * 100) / 100,
        total_transaction_volume: Math.round(data.buyVolume + data.sellVolume),
        generated_at: new Date().toISOString(),
        is_active: true,
        model_version: 'v2.0',
        features: {
          buys: data.buys,
          sells: data.sells,
          buyVolume: data.buyVolume,
          sellVolume: data.sellVolume,
          recentActivity: data.recentActivity,
          bipartisan: data.parties.has('D') && data.parties.has('R')
        },
        notes: `Generated from ${totalTx} transactions by ${politicianCount} politicians over ${lookbackDays} days`
      })
    }

    log.info('Signals generated', {
      requestId,
      signalCount: generatedSignals.length
    })

    if (generatedSignals.length === 0) {
      return new Response(
        JSON.stringify({
          success: true,
          message: 'No signals met the minimum confidence threshold',
          signals: [],
          parameters: { lookbackDays, minConfidence, fetchMarketData }
        }),
        {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Sort by confidence (highest first) and limit to top 50
    generatedSignals.sort((a, b) => b.confidence_score - a.confidence_score)
    const topSignals = generatedSignals.slice(0, 50)

    // Fetch market data and calculate target prices if requested
    if (fetchMarketData) {
      log.info('Fetching market data for signals', {
        requestId,
        tickerCount: topSignals.length
      })

      const tickers = topSignals.map(s => s.ticker)
      const prices = await fetchStockPrices(tickers)

      log.info('Market data fetched', {
        requestId,
        pricesFound: Object.keys(prices).length,
        pricesMissing: tickers.filter(t => !prices[t]).length
      })

      // Add target prices to signals
      for (const signal of topSignals) {
        const currentPrice = prices[signal.ticker]
        if (currentPrice) {
          const targets = calculateTargetPrice(
            currentPrice,
            signal.signal_type,
            signal.signal_strength
          )
          signal.target_price = targets.target
          signal.stop_loss = targets.stopLoss
          signal.take_profit = targets.takeProfit
          signal.features = {
            ...signal.features,
            current_price: currentPrice
          }
        }
      }
    }

    // Get or create model reference for lineage tracking
    const modelVersion = 'v2.0'
    let modelId: string | null = null

    const activeModel = await getActiveModel(supabaseClient)
    if (activeModel) {
      modelId = activeModel.id
      log.info('Using active ML model for lineage', {
        requestId,
        modelId,
        modelVersion: activeModel.model_version
      })
    } else {
      // Fall back to heuristic model reference
      modelId = await getOrCreateLegacyModel(supabaseClient, modelVersion)
      log.info('Using heuristic model for lineage', {
        requestId,
        modelId,
        modelVersion
      })
    }

    // Insert signals into database with lineage tracking
    const signalsToInsert = topSignals.map(signal => ({
      ...signal,
      user_id: user.id,
      model_id: modelId,
      generation_context: {
        lookbackDays,
        minConfidence,
        fetchMarketData,
        source: 'generate-signals',
        timestamp: new Date().toISOString(),
        user_id: user.id,
      },
      reproducibility_hash: computeReproducibilityHash(signal.features, modelId),
    }))

    const { data: insertedSignals, error: insertError } = await supabaseClient
      .from('trading_signals')
      .insert(signalsToInsert)
      .select()

    if (insertError) {
      log.error('Failed to insert signals', insertError, { requestId })
      throw new Error(`Failed to save signals: ${insertError.message}`)
    }

    log.info('Signals inserted successfully', {
      requestId,
      insertedCount: insertedSignals?.length || 0,
      duration: Date.now() - handlerStartTime
    })

    // Queue high-confidence signals for reference portfolio
    await queueSignalsForReferencePortfolio(supabaseClient, insertedSignals || [], requestId)

    // Record audit trail and lifecycle entries for each inserted signal
    if (insertedSignals && insertedSignals.length > 0) {
      const batchSize = 10
      for (let i = 0; i < insertedSignals.length; i += batchSize) {
        const batch = insertedSignals.slice(i, i + batchSize)
        await Promise.all(batch.map(async (signal: any) => {
          await recordSignalAudit(
            supabaseClient,
            signal.id,
            'created',
            signal,
            modelId,
            modelVersion,
            'edge_function',
            `user:${user.email || user.id}`,
            { lookbackDays, minConfidence, fetchMarketData, handler: 'generate-signals' }
          )
          await recordSignalLifecycle(
            supabaseClient,
            signal.id,
            null,
            'generated',
            'Signal generated by user request',
            `user:${user.email || user.id}`
          )
        }))
      }
      log.info('Audit trail recorded', {
        requestId,
        signalCount: insertedSignals.length
      })
    }

    return new Response(
      JSON.stringify({
        success: true,
        message: `Generated ${insertedSignals?.length || 0} trading signals from ${disclosures.length} disclosures`,
        signals: insertedSignals || [],
        parameters: { lookbackDays, minConfidence, fetchMarketData },
        stats: {
          totalDisclosures: disclosures.length,
          uniqueTickers: Object.keys(tickerData).length,
          signalsGenerated: insertedSignals?.length || 0
        }
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  } catch (error) {
    log.error('Error generating signals', error, {
      requestId,
      handler: 'generate-signals',
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

// TODO: Review handleUpdateTargetPrices - updates existing signals with current market prices
// - Fetches all active signals and retrieves current stock prices
// - Calculates target_price, stop_loss, and take_profit based on signal type
// - Batch updates signals with new price targets
async function handleUpdateTargetPrices(supabaseClient: any, req: Request, requestId: string) {
  const handlerStartTime = Date.now()
  try {
    log.info('Updating target prices for existing signals', { requestId })

    // Get all active signals without target prices
    const { data: signals, error: fetchError } = await supabaseClient
      .from('trading_signals')
      .select('id, ticker, signal_type, signal_strength')
      .eq('is_active', true)

    if (fetchError) {
      throw new Error(`Failed to fetch signals: ${fetchError.message}`)
    }

    if (!signals || signals.length === 0) {
      return new Response(
        JSON.stringify({ success: true, message: 'No signals to update', updated: 0 }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    log.info('Fetching prices for signals', { requestId, signalCount: signals.length })

    // Get unique tickers
    const uniqueTickers = [...new Set(signals.map((s: any) => s.ticker))]
    const prices = await fetchStockPrices(uniqueTickers)

    log.info('Prices fetched', {
      requestId,
      pricesFound: Object.keys(prices).length,
      pricesMissing: uniqueTickers.filter(t => !prices[t]).length
    })

    // Update each signal with target prices
    let updatedCount = 0
    let failedCount = 0

    for (const signal of signals) {
      const currentPrice = prices[signal.ticker]
      if (!currentPrice) {
        failedCount++
        continue
      }

      const targets = calculateTargetPrice(
        currentPrice,
        signal.signal_type,
        signal.signal_strength
      )

      const { error: updateError } = await supabaseClient
        .from('trading_signals')
        .update({
          target_price: targets.target,
          stop_loss: targets.stopLoss,
          take_profit: targets.takeProfit,
          updated_at: new Date().toISOString()
        })
        .eq('id', signal.id)

      if (updateError) {
        log.warn('Failed to update signal', { requestId, signalId: signal.id, error: updateError.message })
        failedCount++
      } else {
        updatedCount++
      }
    }

    log.info('Target prices updated', {
      requestId,
      updated: updatedCount,
      failed: failedCount,
      duration: Date.now() - handlerStartTime
    })

    return new Response(
      JSON.stringify({
        success: true,
        message: `Updated ${updatedCount} signals with target prices`,
        updated: updatedCount,
        failed: failedCount,
        pricesAvailable: Object.keys(prices).length
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    log.error('Error updating target prices', error, { requestId })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}

// TODO: Review fetchStockPrice - fetches single stock price from Yahoo Finance API
// - Uses chart endpoint with 1-day interval
// - Returns regularMarketPrice or null on failure
async function fetchStockPrice(ticker: string): Promise<number | null> {
  try {
    const response = await fetch(
      `https://query1.finance.yahoo.com/v8/finance/chart/${ticker}?interval=1d&range=1d`,
      {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
      }
    )

    if (!response.ok) {
      return null
    }

    const data = await response.json()
    const price = data?.chart?.result?.[0]?.meta?.regularMarketPrice
    return typeof price === 'number' ? price : null
  } catch (error) {
    console.warn(`Failed to fetch price for ${ticker}:`, error)
    return null
  }
}

// TODO: Review fetchStockPrices - batch fetches stock prices with rate limiting
// - Processes tickers in batches of 5 with 200ms delay between batches
// - Returns map of ticker -> price for successful fetches
async function fetchStockPrices(tickers: string[]): Promise<Record<string, number>> {
  const prices: Record<string, number> = {}
  const BATCH_SIZE = 5
  const DELAY_MS = 200

  for (let i = 0; i < tickers.length; i += BATCH_SIZE) {
    const batch = tickers.slice(i, i + BATCH_SIZE)
    const batchPromises = batch.map(async (ticker) => {
      const price = await fetchStockPrice(ticker)
      if (price !== null) {
        prices[ticker] = price
      }
    })

    await Promise.all(batchPromises)

    // Rate limiting delay between batches
    if (i + BATCH_SIZE < tickers.length) {
      await new Promise(resolve => setTimeout(resolve, DELAY_MS))
    }
  }

  return prices
}

// TODO: Review calculateTargetPrice - computes price targets based on signal type/strength
// - Uses strength multipliers: very_strong=10%, strong=7%, moderate=5%, weak=3%
// - Buy signals: target higher, stop_loss lower; Sell signals: inverse
function calculateTargetPrice(
  currentPrice: number,
  signalType: string,
  signalStrength: string
): { target: number, stopLoss: number, takeProfit: number } {
  // Base percentage moves based on signal strength
  const strengthMultipliers: Record<string, number> = {
    'very_strong': 0.10,  // 10%
    'strong': 0.07,       // 7%
    'moderate': 0.05,     // 5%
    'weak': 0.03          // 3%
  }

  const multiplier = strengthMultipliers[signalStrength] || 0.05

  if (signalType.includes('buy')) {
    // Buy signals: target is higher, stop loss is lower
    const target = currentPrice * (1 + multiplier)
    const stopLoss = currentPrice * (1 - multiplier * 0.5)  // Tighter stop loss
    const takeProfit = currentPrice * (1 + multiplier * 1.5) // Wider take profit
    return {
      target: Math.round(target * 100) / 100,
      stopLoss: Math.round(stopLoss * 100) / 100,
      takeProfit: Math.round(takeProfit * 100) / 100
    }
  } else if (signalType.includes('sell')) {
    // Sell signals: target is lower, stop loss is higher
    const target = currentPrice * (1 - multiplier)
    const stopLoss = currentPrice * (1 + multiplier * 0.5)  // Tighter stop loss
    const takeProfit = currentPrice * (1 - multiplier * 1.5) // Wider take profit
    return {
      target: Math.round(target * 100) / 100,
      stopLoss: Math.round(stopLoss * 100) / 100,
      takeProfit: Math.round(takeProfit * 100) / 100
    }
  }

  // Hold signal - no target
  return {
    target: currentPrice,
    stopLoss: currentPrice * 0.95,
    takeProfit: currentPrice * 1.05
  }
}

// TODO: Review handleRegenerateSignals - service-level signal regeneration for scheduled jobs
// - No user auth required; optionally clears old signals before regenerating
// - Uses ML predictions when available, with heuristic fallback
// - Records audit trail and queues high-confidence signals for reference portfolio
async function handleRegenerateSignals(supabaseClient: any, req: Request, requestId: string) {
  const handlerStartTime = Date.now()
  try {
    const body = await req.json().catch(() => ({}))
    const { lookbackDays = 90, minConfidence = 0.60, clearOld = true, useML = ML_ENABLED } = body

    log.info('Regenerating signals (service-level) - handler started', {
      requestId,
      handler: 'regenerate-signals',
      params: { lookbackDays, minConfidence, clearOld, useML }
    })

    // Clear old signals if requested
    if (clearOld) {
      log.info('Clearing old signals', { requestId })
      const { error: deleteError } = await supabaseClient
        .from('trading_signals')
        .delete()
        .eq('is_active', true)

      if (deleteError) {
        log.warn('Failed to clear old signals', { requestId, error: deleteError.message })
      } else {
        log.info('Old signals cleared', { requestId })
      }
    }

    // Calculate date range for lookback
    const startDate = new Date()
    startDate.setDate(startDate.getDate() - lookbackDays)
    const startDateStr = startDate.toISOString().split('T')[0]

    log.info('Querying trading disclosures', {
      requestId,
      startDate: startDateStr,
      lookbackDays
    })

    // Query trading disclosures within the lookback period
    const { data: disclosures, error: disclosureError } = await supabaseClient
      .from('trading_disclosures')
      .select(`
        id,
        asset_ticker,
        asset_name,
        transaction_type,
        amount_range_min,
        amount_range_max,
        transaction_date,
        politician_id,
        politician:politicians(id, full_name, party)
      `)
      .not('asset_ticker', 'is', null)
      .or('transaction_type.ilike.%purchase%,transaction_type.ilike.%sale%,transaction_type.ilike.%buy%,transaction_type.ilike.%sell%')
      .gte('transaction_date', startDateStr)
      .order('transaction_date', { ascending: false })
      .limit(10000)

    if (disclosureError) {
      log.error('Failed to fetch disclosures', disclosureError, { requestId })
      throw new Error(`Failed to fetch disclosures: ${disclosureError.message}`)
    }

    log.info('Disclosures fetched', {
      requestId,
      count: disclosures?.length || 0
    })

    if (!disclosures || disclosures.length === 0) {
      return new Response(
        JSON.stringify({
          success: true,
          message: 'No actionable trading activity found in the lookback period',
          signals: [],
          parameters: { lookbackDays, minConfidence }
        }),
        {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Aggregate disclosures by ticker
    const tickerData: Record<string, {
      ticker: string
      assetName: string
      buys: number
      sells: number
      buyVolume: number
      sellVolume: number
      politicians: Set<string>
      parties: Set<string>
      recentActivity: number
      disclosureIds: string[]
    }> = {}

    const thirtyDaysAgo = new Date()
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)

    for (const disclosure of disclosures) {
      const ticker = disclosure.asset_ticker?.toUpperCase()
      if (!ticker || ticker.length < 1 || ticker.length > 10) continue
      // Skip non-stock tickers (real estate, bonds, etc.)
      if (ticker.includes(' ') || ticker.includes('[') || ticker.includes('(')) continue

      if (!tickerData[ticker]) {
        tickerData[ticker] = {
          ticker,
          assetName: disclosure.asset_name || ticker,
          buys: 0,
          sells: 0,
          buyVolume: 0,
          sellVolume: 0,
          politicians: new Set(),
          parties: new Set(),
          recentActivity: 0,
          disclosureIds: []
        }
      }

      const data = tickerData[ticker]
      const txType = (disclosure.transaction_type || '').toLowerCase()
      const minVal = disclosure.amount_range_min || 0
      const maxVal = disclosure.amount_range_max || minVal
      const volume = (minVal + maxVal) / 2

      if (txType.includes('purchase') || txType.includes('buy')) {
        data.buys++
        data.buyVolume += volume
      } else if (txType.includes('sale') || txType.includes('sell')) {
        data.sells++
        data.sellVolume += volume
      }

      if (disclosure.politician_id) {
        data.politicians.add(disclosure.politician_id)
      }
      if (disclosure.politician?.party) {
        data.parties.add(disclosure.politician.party)
      }

      // Track recent activity (last 30 days)
      const txDate = new Date(disclosure.transaction_date)
      if (txDate >= thirtyDaysAgo) {
        data.recentActivity++
      }

      data.disclosureIds.push(disclosure.id)
    }

    log.info('Aggregated ticker data', {
      requestId,
      uniqueTickers: Object.keys(tickerData).length
    })

    // Generate signals - relaxed criteria for more signals
    const generatedSignals: any[] = []
    const mlFeaturesList: MlFeatures[] = []
    const signalDataMap = new Map<string, { signal: any; heuristicType: string; heuristicConfidence: number }>()
    const MIN_POLITICIANS = 1  // Relaxed from 2
    const MIN_TRANSACTIONS = 2  // Relaxed from 3

    for (const [ticker, data] of Object.entries(tickerData)) {
      const totalTx = data.buys + data.sells
      const politicianCount = data.politicians.size

      // Filter: require minimum politicians and transactions
      if (politicianCount < MIN_POLITICIANS || totalTx < MIN_TRANSACTIONS) {
        continue
      }

      // Calculate buy/sell ratio
      const buySellRatio = data.sells > 0 ? data.buys / data.sells : data.buys > 0 ? 10 : 1

      // Calculate confidence based on various factors
      let confidence = 0.5

      // Factor 1: Politician count (more = more confidence)
      if (politicianCount >= 5) confidence += 0.15
      else if (politicianCount >= 3) confidence += 0.10
      else if (politicianCount >= 2) confidence += 0.05

      // Factor 2: Transaction count
      if (totalTx >= 10) confidence += 0.10
      else if (totalTx >= 5) confidence += 0.05

      // Factor 3: Recent activity
      if (data.recentActivity >= 5) confidence += 0.10
      else if (data.recentActivity >= 2) confidence += 0.05

      // Factor 4: Bipartisan activity (both D and R trading)
      if (data.parties.has('D') && data.parties.has('R')) {
        confidence += 0.10
      }

      // Factor 5: Volume magnitude
      const netVolume = data.buyVolume - data.sellVolume
      if (Math.abs(netVolume) > 1000000) confidence += 0.10
      else if (Math.abs(netVolume) > 100000) confidence += 0.05

      // Determine signal type based on buy/sell ratio
      let signalType: string
      let signalStrength: string

      if (buySellRatio >= 3.0) {
        signalType = 'strong_buy'
        signalStrength = 'very_strong'
        confidence = Math.min(confidence + 0.15, 0.95)
      } else if (buySellRatio >= 1.5) {
        signalType = 'buy'
        signalStrength = 'strong'
        confidence = Math.min(confidence + 0.10, 0.90)
      } else if (buySellRatio <= 0.33) {
        signalType = 'strong_sell'
        signalStrength = 'very_strong'
        confidence = Math.min(confidence + 0.15, 0.95)
      } else if (buySellRatio <= 0.67) {
        signalType = 'sell'
        signalStrength = 'strong'
        confidence = Math.min(confidence + 0.10, 0.90)
      } else {
        signalType = 'hold'
        signalStrength = 'moderate'
      }

      // Skip if below minimum confidence
      if (confidence < minConfidence) {
        continue
      }

      // Skip HOLD signals (only generate actionable signals)
      if (signalType === 'hold') {
        continue
      }

      const signal = {
        ticker,
        asset_name: data.assetName,
        signal_type: signalType,
        signal_strength: signalStrength,
        confidence_score: Math.round(confidence * 100) / 100,
        politician_activity_count: politicianCount,
        buy_sell_ratio: Math.round(buySellRatio * 100) / 100,
        total_transaction_volume: Math.round(data.buyVolume + data.sellVolume),
        generated_at: new Date().toISOString(),
        is_active: true,
        model_version: 'v2.1-service',
        ml_enhanced: false,
        features: {
          buys: data.buys,
          sells: data.sells,
          buyVolume: data.buyVolume,
          sellVolume: data.sellVolume,
          recentActivity: data.recentActivity,
          bipartisan: data.parties.has('D') && data.parties.has('R')
        },
        notes: `Generated from ${totalTx} transactions by ${politicianCount} politicians over ${lookbackDays} days`
      }

      generatedSignals.push(signal)

      // Collect ML features for batch prediction
      if (useML) {
        mlFeaturesList.push({
          ticker,
          politician_count: politicianCount,
          buy_sell_ratio: buySellRatio,
          recent_activity_30d: data.recentActivity,
          bipartisan: data.parties.has('D') && data.parties.has('R'),
          net_volume: netVolume,
        })
        signalDataMap.set(ticker, {
          signal,
          heuristicType: signalType,
          heuristicConfidence: confidence,
        })
      }
    }

    log.info('Signals generated (heuristic)', {
      requestId,
      signalCount: generatedSignals.length,
      mlFeaturesCount: mlFeaturesList.length
    })

    // Read dynamic ML blend weight from config
    const { data: blendConfig } = await supabaseClient
      .from('reference_portfolio_config')
      .select('ml_blend_weight')
      .limit(1)
      .maybeSingle()
    const mlBlendWeight = blendConfig?.ml_blend_weight ?? ML_BLEND_WEIGHT

    // Single batch ML prediction call (instead of N sequential calls)
    let mlPredictionCount = 0
    let mlEnhancedCount = 0
    if (useML && mlFeaturesList.length > 0) {
      log.info('Starting batch ML prediction for regenerate', { requestId, tickerCount: mlFeaturesList.length, mlBlendWeight })
      const mlPredictions = await getBatchMlPredictions(mlFeaturesList)
      mlPredictionCount = mlPredictions.size
      log.info('ML predictions received for regenerate', { requestId, count: mlPredictionCount })

      // Apply ML predictions to signals
      for (const [ticker, mlResult] of mlPredictions) {
        const data = signalDataMap.get(ticker)
        if (data) {
          const blended = blendSignals(
            data.heuristicType,
            data.heuristicConfidence,
            mlResult.prediction,
            mlResult.confidence,
            mlBlendWeight
          )
          data.signal.signal_type = blended.signalType
          data.signal.confidence_score = Math.round(blended.confidence * 100) / 100
          data.signal.ml_enhanced = blended.mlEnhanced
          if (blended.mlEnhanced) mlEnhancedCount++
        }
      }
      log.info('ML blending completed for regenerate', { requestId, mlEnhancedCount })
    }

    if (generatedSignals.length === 0) {
      return new Response(
        JSON.stringify({
          success: true,
          message: 'No signals met the minimum confidence threshold',
          signals: [],
          parameters: { lookbackDays, minConfidence }
        }),
        {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Sort by confidence (highest first) and limit to top 100
    generatedSignals.sort((a, b) => b.confidence_score - a.confidence_score)
    const topSignals = generatedSignals.slice(0, 100)

    // Get or create model reference for lineage tracking
    const modelVersion = useML && mlEnhancedCount > 0 ? 'v2.1-ml-enhanced' : 'v2.1-service'
    let modelId: string | null = null
    const activeModel = await getActiveModel(supabaseClient)
    if (activeModel) {
      modelId = activeModel.id
    } else {
      // Fall back to heuristic model
      modelId = await getOrCreateLegacyModel(supabaseClient, modelVersion)
    }

    log.info('Model lineage resolved', { requestId, modelId, modelVersion })

    // Add lineage data to signals
    const signalsWithLineage = topSignals.map(signal => ({
      ...signal,
      model_id: modelId,
      model_version: modelVersion,
      generation_context: {
        lookbackDays,
        minConfidence,
        source: 'regenerate-signals',
        timestamp: new Date().toISOString(),
        mlEnabled: useML,
      },
      reproducibility_hash: computeReproducibilityHash(signal.features, modelId),
    }))

    // Insert signals into database (no user_id for service-level)
    const { data: insertedSignals, error: insertError } = await supabaseClient
      .from('trading_signals')
      .insert(signalsWithLineage)
      .select()

    if (insertError) {
      log.error('Failed to insert signals', insertError, { requestId })
      throw new Error(`Failed to save signals: ${insertError.message}`)
    }

    log.info('Signals inserted successfully', {
      requestId,
      insertedCount: insertedSignals?.length || 0,
      duration: Date.now() - handlerStartTime
    })

    // Queue high-confidence signals for reference portfolio
    await queueSignalsForReferencePortfolio(supabaseClient, insertedSignals || [], requestId)

    // Record audit trail and lifecycle entries for each inserted signal
    if (insertedSignals && insertedSignals.length > 0) {
      log.info('Recording audit trail entries', { requestId, count: insertedSignals.length })

      // Record in parallel batches to avoid overwhelming the DB
      const batchSize = 10
      for (let i = 0; i < insertedSignals.length; i += batchSize) {
        const batch = insertedSignals.slice(i, i + batchSize)
        await Promise.all(batch.map(async (signal: any) => {
          // Record audit trail
          await recordSignalAudit(
            supabaseClient,
            signal.id,
            'created',
            signal,
            modelId,
            modelVersion,
            'edge_function',
            'scheduler',
            { lookbackDays, minConfidence, handler: 'regenerate-signals' }
          )

          // Record initial lifecycle state
          await recordSignalLifecycle(
            supabaseClient,
            signal.id,
            null,
            'generated',
            'Signal generated by scheduled regeneration',
            'scheduler'
          )
        }))
      }

      log.info('Audit trail entries recorded', { requestId })
    }

    return new Response(
      JSON.stringify({
        success: true,
        message: `Regenerated ${insertedSignals?.length || 0} trading signals from ${disclosures.length} disclosures`,
        signals: insertedSignals || [],
        parameters: { lookbackDays, minConfidence },
        stats: {
          totalDisclosures: disclosures.length,
          uniqueTickers: Object.keys(tickerData).length,
          signalsGenerated: insertedSignals?.length || 0,
          modelId,
          modelVersion,
          mlEnabled: useML,
          mlPredictionCount,
          mlEnhancedCount,
        }
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  } catch (error) {
    log.error('Error regenerating signals', error, {
      requestId,
      handler: 'regenerate-signals',
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

// TODO: Review handleGetSignalStats - retrieves aggregate statistics for active signals
// - Calculates total count, average confidence, and signal type distribution
// - Returns high_confidence_signals count (>=0.8 confidence)
async function handleGetSignalStats(supabaseClient: any, req: Request) {
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

// Interface for configurable signal weights
interface SignalWeights {
  baseConfidence: number
  politicianCount5Plus: number
  politicianCount3_4: number
  politicianCount2: number
  recentActivity5Plus: number
  recentActivity2_4: number
  bipartisanBonus: number
  volume1MPlus: number
  volume100KPlus: number
  strongSignalBonus: number
  moderateSignalBonus: number
  strongBuyThreshold: number
  buyThreshold: number
  strongSellThreshold: number
  sellThreshold: number
}

// Default weights (matching current hardcoded values)
const DEFAULT_WEIGHTS: SignalWeights = {
  baseConfidence: 0.50,
  politicianCount5Plus: 0.15,
  politicianCount3_4: 0.10,
  politicianCount2: 0.05,
  recentActivity5Plus: 0.10,
  recentActivity2_4: 0.05,
  bipartisanBonus: 0.10,
  volume1MPlus: 0.10,
  volume100KPlus: 0.05,
  strongSignalBonus: 0.15,
  moderateSignalBonus: 0.10,
  strongBuyThreshold: 3.0,
  buyThreshold: 2.0,
  strongSellThreshold: 0.33,
  sellThreshold: 0.5,
}

// ML Integration Configuration
// Call ETL directly for ML (Phoenix proxy adds latency)
const ETL_API_URL = Deno.env.get('ETL_API_URL') || 'https://politician-trading-etl.fly.dev'
// ML enabled by default - quick health check prevents blocking on cold starts
const ML_ENABLED = Deno.env.get('ML_ENABLED') !== 'false'
const ML_BLEND_WEIGHT = 0.2 // 20% ML, 80% heuristic (reduced from 0.4 to test if ML is adding noise)
const ML_TIMEOUT_MS = 10000 // 10 second timeout for batch prediction

// Alpaca API configuration for market data
const ALPACA_API_KEY = Deno.env.get('ALPACA_API_KEY')
const ALPACA_SECRET_KEY = Deno.env.get('ALPACA_SECRET_KEY')
const ALPACA_DATA_URL = 'https://data.alpaca.markets'

// Market data cache (1 hour TTL)
const marketDataCache = new Map<string, { value: number; timestamp: number }>()
const MARKET_DATA_CACHE_TTL_MS = 60 * 60 * 1000 // 1 hour

// Sector ETF mapping
const SECTOR_ETF_MAP: Record<string, string> = {
  // Technology
  'AAPL': 'XLK', 'MSFT': 'XLK', 'GOOGL': 'XLK', 'GOOG': 'XLK', 'NVDA': 'XLK', 'META': 'XLK',
  'TSLA': 'XLK', 'NFLX': 'XLK', 'ADBE': 'XLK', 'CRM': 'XLK', 'ORCL': 'XLK', 'CSCO': 'XLK',
  
  // Healthcare
  'JNJ': 'XLV', 'UNH': 'XLV', 'PFE': 'XLV', 'ABBV': 'XLV', 'TMO': 'XLV', 'MRK': 'XLV',
  'LLY': 'XLV', 'ABT': 'XLV', 'DHR': 'XLV', 'BMY': 'XLV',
  
  // Finance
  'JPM': 'XLF', 'BAC': 'XLF', 'WFC': 'XLF', 'GS': 'XLF', 'MS': 'XLF', 'C': 'XLF',
  'BLK': 'XLF', 'SCHW': 'XLF', 'AXP': 'XLF', 'USB': 'XLF',
  
  // Consumer
  'AMZN': 'XLY', 'HD': 'XLY', 'MCD': 'XLY', 'NKE': 'XLY', 'SBUX': 'XLY', 'TGT': 'XLY',
  'WMT': 'XLP', 'PG': 'XLP', 'KO': 'XLP', 'PEP': 'XLP', 'COST': 'XLP',
  
  // Energy
  'XOM': 'XLE', 'CVX': 'XLE', 'COP': 'XLE', 'SLB': 'XLE', 'EOG': 'XLE',
  
  // Industrials
  'BA': 'XLI', 'CAT': 'XLI', 'GE': 'XLI', 'MMM': 'XLI', 'HON': 'XLI', 'UPS': 'XLI',
  
  // Real Estate
  'AMT': 'XLRE', 'PLD': 'XLRE', 'CCI': 'XLRE', 'EQIX': 'XLRE',
  
  // Utilities
  'NEE': 'XLU', 'DUK': 'XLU', 'SO': 'XLU', 'D': 'XLU',
  
  // Materials
  'LIN': 'XLB', 'APD': 'XLB', 'SHW': 'XLB', 'FCX': 'XLB',
  
  // Communication
  'DIS': 'XLC', 'CMCSA': 'XLC', 'VZ': 'XLC', 'T': 'XLC', 'TMUS': 'XLC',
}

// TODO: Review getMarketMomentum - calculates 20-day price momentum for a ticker
// Uses Alpaca bars API to get historical prices and calculate percentage change
// Returns 0 if data unavailable or error occurs
async function getMarketMomentum(ticker: string): Promise<number> {
  const cacheKey = `momentum_${ticker}`
  const cached = marketDataCache.get(cacheKey)
  
  if (cached && Date.now() - cached.timestamp < MARKET_DATA_CACHE_TTL_MS) {
    return cached.value
  }

  if (!ALPACA_API_KEY || !ALPACA_SECRET_KEY) {
    return 0 // No credentials, return neutral
  }

  try {
    const endDate = new Date()
    const startDate = new Date()
    startDate.setDate(startDate.getDate() - 25) // 25 days to ensure 20 trading days

    const url = `${ALPACA_DATA_URL}/v2/stocks/${ticker}/bars?timeframe=1Day&start=${startDate.toISOString().split('T')[0]}&end=${endDate.toISOString().split('T')[0]}&limit=25`
    
    const response = await fetch(url, {
      headers: {
        'APCA-API-KEY-ID': ALPACA_API_KEY,
        'APCA-API-SECRET-KEY': ALPACA_SECRET_KEY
      }
    })

    if (!response.ok) return 0

    const data = await response.json()
    const bars = data.bars || []

    if (bars.length < 2) return 0

    // Calculate momentum: (current - 20 days ago) / 20 days ago
    const oldestPrice = bars[0].c
    const latestPrice = bars[bars.length - 1].c
    const momentum = ((latestPrice - oldestPrice) / oldestPrice) * 100

    // Cache the result
    marketDataCache.set(cacheKey, { value: momentum, timestamp: Date.now() })

    return momentum
  } catch (error) {
    log.warn('Failed to fetch market momentum', { ticker, error: error.message })
    return 0
  }
}

// TODO: Review getSectorPerformance - calculates sector ETF performance for a ticker
// Maps ticker to sector ETF (e.g., AAPL -> XLK), fetches 20-day performance
// Returns 0 if sector unknown or data unavailable
async function getSectorPerformance(ticker: string): Promise<number> {
  const sectorETF = SECTOR_ETF_MAP[ticker] || 'SPY' // Default to S&P 500
  const cacheKey = `sector_${sectorETF}`
  
  const cached = marketDataCache.get(cacheKey)
  if (cached && Date.now() - cached.timestamp < MARKET_DATA_CACHE_TTL_MS) {
    return cached.value
  }

  if (!ALPACA_API_KEY || !ALPACA_SECRET_KEY) {
    return 0 // No credentials, return neutral
  }

  try {
    const endDate = new Date()
    const startDate = new Date()
    startDate.setDate(startDate.getDate() - 25) // 25 days to ensure 20 trading days

    const url = `${ALPACA_DATA_URL}/v2/stocks/${sectorETF}/bars?timeframe=1Day&start=${startDate.toISOString().split('T')[0]}&end=${endDate.toISOString().split('T')[0]}&limit=25`
    
    const response = await fetch(url, {
      headers: {
        'APCA-API-KEY-ID': ALPACA_API_KEY,
        'APCA-API-SECRET-KEY': ALPACA_SECRET_KEY
      }
    })

    if (!response.ok) return 0

    const data = await response.json()
    const bars = data.bars || []

    if (bars.length < 2) return 0

    // Calculate sector performance: (current - 20 days ago) / 20 days ago
    const oldestPrice = bars[0].c
    const latestPrice = bars[bars.length - 1].c
    const performance = ((latestPrice - oldestPrice) / oldestPrice) * 100

    // Cache the result
    marketDataCache.set(cacheKey, { value: performance, timestamp: Date.now() })

    return performance
  } catch (error) {
    log.warn('Failed to fetch sector performance', { ticker, sector: sectorETF, error: error.message })
    return 0
  }
}

// =============================================================================
// MODEL LINEAGE AND AUDIT TRAIL FUNCTIONS
// =============================================================================

interface ActiveModelInfo {
  id: string
  model_version: string
  weights_hash?: string
}

// TODO: Review getActiveModel - retrieves the currently active ML model for signal generation
// - Queries ml_models table for active status, ordered by training completion
// - Returns model ID and version for lineage tracking
async function getActiveModel(supabaseClient: any): Promise<ActiveModelInfo | null> {
  try {
    const { data, error } = await supabaseClient
      .from('ml_models')
      .select('id, model_version, feature_importance')
      .eq('status', 'active')
      .order('training_completed_at', { ascending: false })
      .limit(1)
      .single()

    if (error || !data) {
      return null
    }

    return {
      id: data.id,
      model_version: data.model_version,
    }
  } catch {
    return null
  }
}

// TODO: Review getOrCreateLegacyModel - creates/retrieves heuristic model reference for lineage
// - First checks for existing legacy model with matching version
// - Creates new 'heuristic' model entry if none exists
async function getOrCreateLegacyModel(supabaseClient: any, modelVersion: string): Promise<string | null> {
  try {
    // First try to find existing legacy model
    const { data: existing, error: findError } = await supabaseClient
      .from('ml_models')
      .select('id')
      .eq('model_name', 'heuristic')
      .eq('model_version', modelVersion)
      .limit(1)
      .single()

    if (existing && !findError) {
      return existing.id
    }

    // Create legacy model reference
    const { data: created, error: createError } = await supabaseClient
      .from('ml_models')
      .insert({
        model_name: 'heuristic',
        model_version: modelVersion,
        model_type: 'gradient_boosting', // Placeholder
        status: 'active',
        metrics: { type: 'heuristic', description: 'Rule-based signal generation' },
        feature_importance: {},
        training_completed_at: new Date().toISOString(),
      })
      .select('id')
      .single()

    if (createError) {
      log.warn('Failed to create legacy model', { error: createError.message })
      return null
    }

    return created?.id || null
  } catch (error) {
    log.warn('Error in getOrCreateLegacyModel', { error: error.message })
    return null
  }
}

// TODO: Review computeReproducibilityHash - generates hash for signal reproducibility tracking
// - Combines features, model ID, and hour-level timestamp
// - Enables verification that same inputs produce same outputs
function computeReproducibilityHash(features: any, modelId: string | null): string {
  const data = JSON.stringify({
    features: features,
    modelId: modelId,
    timestamp: Math.floor(Date.now() / 3600000), // Hour-level precision
  })
  // Simple hash (in production, use crypto.subtle.digest)
  let hash = 0
  for (let i = 0; i < data.length; i++) {
    const char = data.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash // Convert to 32bit integer
  }
  return `hash_${Math.abs(hash).toString(16)}`
}

// TODO: Review recordSignalAudit - records audit trail entry for signal lifecycle events
// - Captures signal snapshot, model lineage, and triggering system/user
// - Events: created, updated, executed, expired, invalidated
async function recordSignalAudit(
  supabaseClient: any,
  signalId: string,
  eventType: 'created' | 'updated' | 'executed' | 'expired' | 'invalidated',
  signalSnapshot: any,
  modelId: string | null,
  modelVersion: string,
  sourceSystem: string,
  triggeredBy: string | null,
  metadata: any = {}
): Promise<void> {
  try {
    const { error } = await supabaseClient
      .from('signal_audit_trail')
      .insert({
        signal_id: signalId,
        event_type: eventType,
        signal_snapshot: signalSnapshot,
        model_id: modelId,
        model_version: modelVersion,
        source_system: sourceSystem,
        triggered_by: triggeredBy,
        metadata: metadata,
      })

    if (error) {
      log.warn('Failed to record signal audit', { signalId, error: error.message })
    }
  } catch (error) {
    log.warn('Error recording signal audit', { signalId, error: error.message })
  }
}

// TODO: Review recordSignalLifecycle - records state transitions in signal lifecycle
// - Tracks previous_state -> current_state with reason and actor
// - Enables signal journey analysis and debugging
async function recordSignalLifecycle(
  supabaseClient: any,
  signalId: string,
  previousState: string | null,
  currentState: string,
  reason: string,
  transitionedBy: string = 'system'
): Promise<void> {
  try {
    const { error } = await supabaseClient
      .from('signal_lifecycle')
      .insert({
        signal_id: signalId,
        previous_state: previousState,
        current_state: currentState,
        transition_reason: reason,
        transitioned_by: transitionedBy,
      })

    if (error) {
      log.warn('Failed to record signal lifecycle', { signalId, error: error.message })
    }
  } catch (error) {
    log.warn('Error recording signal lifecycle', { signalId, error: error.message })
  }
}

// Signal type to numeric mapping for ML blending
const SIGNAL_TYPE_MAP: Record<string, number> = {
  'strong_buy': 2,
  'buy': 1,
  'hold': 0,
  'sell': -1,
  'strong_sell': -2,
}

const NUMERIC_TO_SIGNAL: Record<number, string> = {
  2: 'strong_buy',
  1: 'buy',
  0: 'hold',
  '-1': 'sell',
  '-2': 'strong_sell',
}

// Feature set for ML prediction
interface MlFeatures {
  ticker: string
  politician_count: number
  buy_sell_ratio: number
  recent_activity_30d: number
  bipartisan: boolean
  net_volume: number
}

// Cache for ML model availability (avoid repeated checks)
let mlModelAvailable: boolean | null = null
let mlModelCheckTime = 0
const ML_MODEL_CHECK_CACHE_SUCCESS_MS = 60000 // Cache successful checks for 1 minute
const ML_MODEL_CHECK_CACHE_FAIL_MS = 5000 // Cache failures for 5 seconds only (allow retries)

// TODO: Review checkMlModelAvailable - checks if ML prediction service is available
// - Caches result for 1 minute (success) or 5 seconds (failure)
// - Uses 5s timeout to prevent blocking on cold starts
async function checkMlModelAvailable(): Promise<boolean> {
  const now = Date.now()
  const cacheMs = mlModelAvailable ? ML_MODEL_CHECK_CACHE_SUCCESS_MS : ML_MODEL_CHECK_CACHE_FAIL_MS
  if (mlModelAvailable !== null && (now - mlModelCheckTime) < cacheMs) {
    log.info('ML model availability (cached)', { available: mlModelAvailable })
    return mlModelAvailable
  }

  try {
    log.info('Checking ML model availability', { url: `${ETL_API_URL}/ml/models/active` })
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 5000) // 5s timeout for health check

    const response = await fetch(`${ETL_API_URL}/ml/models/active`, {
      method: 'GET',
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    mlModelAvailable = response.ok
    mlModelCheckTime = now
    log.info('ML model availability check completed', { available: mlModelAvailable, status: response.status })
    return mlModelAvailable
  } catch (error) {
    log.warn('ML model availability check failed', { error: error.message })
    mlModelAvailable = false
    mlModelCheckTime = now
    return false
  }
}

// TODO: Review getBatchMlPredictions - fetches ML predictions for multiple tickers in single call
// - Builds feature vectors and calls ETL batch-predict endpoint
// - Returns map of ticker -> {prediction, confidence} for successful predictions
async function getBatchMlPredictions(
  featuresList: MlFeatures[]
): Promise<Map<string, { prediction: number; confidence: number }>> {
  const results = new Map<string, { prediction: number; confidence: number }>()

  if (!ML_ENABLED || featuresList.length === 0) return results

  // Quick check if model is available (cached)
  const modelAvailable = await checkMlModelAvailable()
  if (!modelAvailable) {
    log.info('ML model not available, skipping predictions')
    return results
  }

  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), ML_TIMEOUT_MS)

    // Fetch market momentum and sector performance for all tickers in parallel
    log.info('Fetching market data for ML features', { tickerCount: featuresList.length })
    const marketDataPromises = featuresList.map(async (f) => {
      const [momentum, sector] = await Promise.all([
        getMarketMomentum(f.ticker),
        getSectorPerformance(f.ticker)
      ])
      return { ticker: f.ticker, momentum, sector }
    })

    const marketData = await Promise.all(marketDataPromises)
    const marketDataMap = new Map(marketData.map(d => [d.ticker, { momentum: d.momentum, sector: d.sector }]))

    // Build batch request with all tickers - API expects flat FeatureVector objects
    const tickers = featuresList.map(f => {
      const data = marketDataMap.get(f.ticker) || { momentum: 0, sector: 0 }
      return {
        ticker: f.ticker,
        politician_count: f.politician_count,
        buy_sell_ratio: f.buy_sell_ratio,
        recent_activity_30d: f.recent_activity_30d,
        bipartisan: f.bipartisan,
        net_volume: f.net_volume,
        volume_magnitude: Math.log1p(Math.abs(f.net_volume)),
        party_alignment: 0.5,
        committee_relevance: 0.5,
        disclosure_delay: 30,
        sentiment_score: 0,
        market_momentum: data.momentum,
        sector_performance: data.sector,
      }
    })

    log.info('Calling ETL batch-predict', { tickerCount: tickers.length, url: `${ETL_API_URL}/ml/batch-predict` })

    const response = await fetch(`${ETL_API_URL}/ml/batch-predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tickers, use_cache: true }),
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    if (!response.ok) {
      log.warn('ML batch prediction request failed', { status: response.status })
      return results
    }

    const data = await response.json()

    // Parse batch response - format: [{ ticker, prediction, signal_type, confidence, ... }]
    if (Array.isArray(data)) {
      for (const pred of data) {
        if (pred.ticker && pred.signal_type !== 'error') {
          results.set(pred.ticker, { prediction: pred.prediction, confidence: pred.confidence })
        }
      }
    }

    log.info('ML batch prediction completed', { tickerCount: featuresList.length, successCount: results.size })
  } catch (error) {
    if (error.name === 'AbortError') {
      log.warn('ML batch prediction timed out')
    } else {
      log.warn('ML batch prediction error', { error: error.message })
    }
  }

  return results
}

// TODO: Review blendSignals - combines heuristic and ML signal predictions
// - Uses 40% ML / 60% heuristic blend weight
// - Boosts confidence when signals agree, reduces when they disagree
function blendSignals(
  heuristicType: string,
  heuristicConfidence: number,
  mlPrediction: number | null,
  mlConfidence: number | null,
  blendWeight: number = ML_BLEND_WEIGHT
): { signalType: string; confidence: number; mlEnhanced: boolean } {
  if (mlPrediction === null || mlConfidence === null) {
    return { signalType: heuristicType, confidence: heuristicConfidence, mlEnhanced: false }
  }

  const heuristicNumeric = SIGNAL_TYPE_MAP[heuristicType] ?? 0

  // Calculate blended confidence using dynamic weight
  const blendedConfidence = heuristicConfidence * (1 - blendWeight) + mlConfidence * blendWeight

  // If signals agree, boost confidence
  if (heuristicNumeric === mlPrediction) {
    return {
      signalType: heuristicType,
      confidence: Math.min(blendedConfidence * 1.1, 0.98),
      mlEnhanced: true,
    }
  }

  // If signals disagree, use heuristic but reduce confidence
  return {
    signalType: heuristicType,
    confidence: blendedConfidence * 0.85,
    mlEnhanced: true,
  }
}

// Lambda execution result with trace
interface LambdaResult {
  signals: any[]
  trace: {
    console_output: string[]
    execution_time_ms: number
    signals_processed: number
    signals_modified: number
    errors: any[]
    sample_transformations: any[]
  } | null
  error: string | null
}

// TODO: Review applyUserLambda - executes user-defined Python lambda on signals
// - Calls ETL apply-lambda endpoint with 15s timeout
// - Returns transformed signals with execution trace for debugging
async function applyUserLambda(
  signals: any[],
  lambdaCode: string,
  requestId: string
): Promise<LambdaResult> {
  if (!lambdaCode || !lambdaCode.trim() || signals.length === 0) {
    return { signals, trace: null, error: null }
  }

  try {
    log.info('Applying user lambda', { requestId, signalCount: signals.length })

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 15000) // 15s timeout

    const response = await fetch(`${ETL_API_URL}/signals/apply-lambda`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        signals,
        lambdaCode,
      }),
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      log.warn('Lambda application failed', {
        requestId,
        status: response.status,
        error: errorData.detail || 'Unknown error'
      })
      return { signals, trace: null, error: errorData.detail || 'Lambda execution failed' }
    }

    const data = await response.json()

    if (data.success && Array.isArray(data.signals)) {
      log.info('User lambda applied successfully', {
        requestId,
        transformedCount: data.signals.length,
        hasTrace: !!data.trace
      })
      return {
        signals: data.signals,
        trace: data.trace || null,
        error: null
      }
    }

    return { signals, trace: null, error: 'Unexpected response format' }
  } catch (error) {
    if (error.name === 'AbortError') {
      log.warn('Lambda application timed out', { requestId })
      return { signals, trace: null, error: 'Lambda execution timed out' }
    } else {
      log.warn('Lambda application error', { requestId, error: error.message })
      return { signals, trace: null, error: error.message }
    }
  }
}

// TODO: Review handlePreviewSignals - previews signals with custom weights without persisting
// - Supports configurable weight parameters for signal calculation
// - Optionally applies ML predictions and user-defined lambdas
// - Returns preview results without database writes for experimentation
async function handlePreviewSignals(supabaseClient: any, req: Request, requestId: string) {
  const handlerStartTime = Date.now()
  try {
    const body = await req.json()
    const { lookbackDays = 30, weights: providedWeights, useML = ML_ENABLED, userLambda } = body

    // Merge provided weights with defaults
    const weights: SignalWeights = {
      ...DEFAULT_WEIGHTS,
      ...(providedWeights || {})
    }

    log.info('Preview signals - handler started', {
      requestId,
      handler: 'preview-signals',
      params: { lookbackDays },
      weights
    })

    // Calculate date range for lookback
    const startDate = new Date()
    startDate.setDate(startDate.getDate() - lookbackDays)
    const startDateStr = startDate.toISOString().split('T')[0]

    log.info('Querying trading disclosures for preview', {
      requestId,
      startDate: startDateStr,
      lookbackDays
    })

    // Query trading disclosures within the lookback period
    const { data: disclosures, error: disclosureError } = await supabaseClient
      .from('trading_disclosures')
      .select(`
        id,
        asset_ticker,
        asset_name,
        transaction_type,
        amount_range_min,
        amount_range_max,
        transaction_date,
        politician_id,
        politician:politicians(id, full_name, party)
      `)
      .eq('status', 'active')
      .not('asset_ticker', 'is', null)
      .gte('transaction_date', startDateStr)
      .order('transaction_date', { ascending: false })

    if (disclosureError) {
      log.error('Failed to fetch disclosures for preview', disclosureError, { requestId })
      throw new Error(`Failed to fetch disclosures: ${disclosureError.message}`)
    }

    log.info('Disclosures fetched for preview', {
      requestId,
      count: disclosures?.length || 0
    })

    if (!disclosures || disclosures.length === 0) {
      return new Response(
        JSON.stringify({
          success: true,
          preview: true,
          message: 'No trading activity found in the lookback period',
          signals: [],
          weights,
          stats: {
            totalDisclosures: 0,
            uniqueTickers: 0,
            signalsGenerated: 0
          }
        }),
        {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Aggregate disclosures by ticker
    const tickerData: Record<string, {
      ticker: string
      assetName: string
      buys: number
      sells: number
      buyVolume: number
      sellVolume: number
      politicians: Set<string>
      parties: Set<string>
      recentActivity: number
      disclosureIds: string[]
    }> = {}

    const thirtyDaysAgo = new Date()
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)

    for (const disclosure of disclosures) {
      const ticker = disclosure.asset_ticker?.toUpperCase()
      if (!ticker || ticker.length < 1 || ticker.length > 10) continue
      // Skip non-stock tickers (real estate, bonds, etc.)
      if (ticker.includes(' ') || ticker.includes('[') || ticker.includes('(')) continue

      if (!tickerData[ticker]) {
        tickerData[ticker] = {
          ticker,
          assetName: disclosure.asset_name || ticker,
          buys: 0,
          sells: 0,
          buyVolume: 0,
          sellVolume: 0,
          politicians: new Set(),
          parties: new Set(),
          recentActivity: 0,
          disclosureIds: []
        }
      }

      const data = tickerData[ticker]
      const txType = (disclosure.transaction_type || '').toLowerCase()
      const minVal = disclosure.amount_range_min || 0
      const maxVal = disclosure.amount_range_max || minVal
      const volume = (minVal + maxVal) / 2

      if (txType.includes('purchase') || txType.includes('buy')) {
        data.buys++
        data.buyVolume += volume
      } else if (txType.includes('sale') || txType.includes('sell')) {
        data.sells++
        data.sellVolume += volume
      }

      if (disclosure.politician_id) {
        data.politicians.add(disclosure.politician_id)
      }
      if (disclosure.politician?.party) {
        data.parties.add(disclosure.politician.party)
      }

      // Track recent activity (last 30 days)
      const txDate = new Date(disclosure.transaction_date)
      if (txDate >= thirtyDaysAgo) {
        data.recentActivity++
      }

      data.disclosureIds.push(disclosure.id)
    }

    log.info('Aggregated ticker data for preview', {
      requestId,
      uniqueTickers: Object.keys(tickerData).length
    })

    // Generate signals for all tickers with activity (more lenient for preview)
    const generatedSignals: any[] = []
    const MIN_POLITICIANS = 1  // More lenient for preview
    const MIN_TRANSACTIONS = 2

    // First pass: generate heuristic signals and collect ML features
    const mlFeaturesList: MlFeatures[] = []
    const signalDataMap = new Map<string, {
      signal: any
      heuristicType: string
      heuristicConfidence: number
    }>()

    for (const [ticker, data] of Object.entries(tickerData)) {
      const totalTx = data.buys + data.sells
      const politicianCount = data.politicians.size

      // Filter: require minimum politicians and transactions
      if (politicianCount < MIN_POLITICIANS || totalTx < MIN_TRANSACTIONS) {
        continue
      }

      // Calculate buy/sell ratio
      const buySellRatio = data.sells > 0 ? data.buys / data.sells : data.buys > 0 ? 10 : 1

      // Calculate confidence using configurable weights
      let confidence = weights.baseConfidence

      // Factor 1: Politician count (more = more confidence)
      if (politicianCount >= 5) confidence += weights.politicianCount5Plus
      else if (politicianCount >= 3) confidence += weights.politicianCount3_4
      else if (politicianCount >= 2) confidence += weights.politicianCount2

      // Factor 2: Recent activity
      if (data.recentActivity >= 5) confidence += weights.recentActivity5Plus
      else if (data.recentActivity >= 2) confidence += weights.recentActivity2_4

      // Factor 3: Bipartisan activity (both D and R trading)
      if (data.parties.has('D') && data.parties.has('R')) {
        confidence += weights.bipartisanBonus
      }

      // Factor 4: Volume magnitude
      const netVolume = data.buyVolume - data.sellVolume
      if (Math.abs(netVolume) > 1000000) confidence += weights.volume1MPlus
      else if (Math.abs(netVolume) > 100000) confidence += weights.volume100KPlus

      // Determine signal type based on buy/sell ratio using configurable thresholds
      let signalType: string
      let signalStrength: string

      if (buySellRatio >= weights.strongBuyThreshold) {
        signalType = 'strong_buy'
        signalStrength = 'very_strong'
        confidence = Math.min(confidence + weights.strongSignalBonus, 0.95)
      } else if (buySellRatio >= weights.buyThreshold) {
        signalType = 'buy'
        signalStrength = 'strong'
        confidence = Math.min(confidence + weights.moderateSignalBonus, 0.90)
      } else if (buySellRatio <= weights.strongSellThreshold) {
        signalType = 'strong_sell'
        signalStrength = 'very_strong'
        confidence = Math.min(confidence + weights.strongSignalBonus, 0.95)
      } else if (buySellRatio <= weights.sellThreshold) {
        signalType = 'sell'
        signalStrength = 'strong'
        confidence = Math.min(confidence + weights.moderateSignalBonus, 0.90)
      } else {
        signalType = 'hold'
        signalStrength = 'moderate'
      }

      // Build signal object (ML enhancement applied later)
      const signal = {
        ticker,
        asset_name: data.assetName,
        signal_type: signalType,
        signal_strength: signalStrength,
        confidence_score: Math.round(confidence * 100) / 100,
        politician_activity_count: politicianCount,
        buy_sell_ratio: Math.round(buySellRatio * 100) / 100,
        total_transaction_volume: Math.round(data.buyVolume + data.sellVolume),
        ml_enhanced: false,
        features: {
          buys: data.buys,
          sells: data.sells,
          buyVolume: data.buyVolume,
          sellVolume: data.sellVolume,
          recentActivity: data.recentActivity,
          bipartisan: data.parties.has('D') && data.parties.has('R')
        }
      }

      generatedSignals.push(signal)

      // Collect ML features for batch prediction
      if (useML) {
        mlFeaturesList.push({
          ticker,
          politician_count: politicianCount,
          buy_sell_ratio: buySellRatio,
          recent_activity_30d: data.recentActivity,
          bipartisan: data.parties.has('D') && data.parties.has('R'),
          net_volume: netVolume,
        })
        signalDataMap.set(ticker, {
          signal,
          heuristicType: signalType,
          heuristicConfidence: confidence,
        })
      }
    }

    // Read dynamic ML blend weight from config
    const { data: genBlendConfig } = await supabaseClient
      .from('reference_portfolio_config')
      .select('ml_blend_weight')
      .limit(1)
      .maybeSingle()
    const genMlBlendWeight = genBlendConfig?.ml_blend_weight ?? ML_BLEND_WEIGHT

    // Single batch ML prediction call (instead of N sequential calls)
    let mlPredictionCount = 0
    if (useML && mlFeaturesList.length > 0) {
      log.info('Starting batch ML prediction', { tickerCount: mlFeaturesList.length, mlBlendWeight: genMlBlendWeight })
      const mlPredictions = await getBatchMlPredictions(mlFeaturesList)
      mlPredictionCount = mlPredictions.size
      log.info('ML predictions received', { count: mlPredictionCount })

      // Apply ML predictions to signals
      for (const [ticker, mlResult] of mlPredictions) {
        const data = signalDataMap.get(ticker)
        if (data) {
          const blended = blendSignals(
            data.heuristicType,
            data.heuristicConfidence,
            mlResult.prediction,
            mlResult.confidence,
            genMlBlendWeight
          )
          data.signal.signal_type = blended.signalType
          data.signal.confidence_score = Math.round(blended.confidence * 100) / 100
          data.signal.ml_enhanced = blended.mlEnhanced
        }
      }
    }

    // Sort by confidence (highest first) and limit to top 100 for preview
    generatedSignals.sort((a, b) => b.confidence_score - a.confidence_score)
    let topSignals = generatedSignals.slice(0, 100)

    // Count ML-enhanced signals (before lambda)
    const mlEnhancedCount = topSignals.filter(s => s.ml_enhanced).length

    // Apply user lambda if provided
    let lambdaApplied = false
    let lambdaError: string | null = null
    let lambdaTrace: LambdaResult['trace'] = null
    if (userLambda && userLambda.trim()) {
      log.info('Applying user lambda to preview signals', { requestId, signalCount: topSignals.length })
      const lambdaResult = await applyUserLambda(topSignals, userLambda, requestId)
      topSignals = lambdaResult.signals
      lambdaTrace = lambdaResult.trace
      lambdaError = lambdaResult.error
      lambdaApplied = !lambdaError
      if (lambdaError) {
        log.warn('User lambda failed', { requestId, error: lambdaError })
      }
    }

    log.info('Preview signals generated', {
      requestId,
      totalGenerated: generatedSignals.length,
      returned: topSignals.length,
      mlEnabled: useML,
      mlEnhancedCount,
      lambdaApplied,
      duration: Date.now() - handlerStartTime
    })

    return new Response(
      JSON.stringify({
        success: true,
        preview: true,
        signals: topSignals,
        weights,
        lambdaApplied,
        lambdaError,
        lambdaTrace,
        stats: {
          totalDisclosures: disclosures.length,
          uniqueTickers: Object.keys(tickerData).length,
          signalsGenerated: topSignals.length,
          mlEnabled: useML,
          mlEnhancedCount,
          mlPredictionCount,
          mlFeaturesCount: mlFeaturesList.length,
          lambdaApplied,
          signalTypeDistribution: topSignals.reduce((acc, s) => {
            acc[s.signal_type] = (acc[s.signal_type] || 0) + 1
            return acc
          }, {} as Record<string, number>)
        }
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  } catch (error) {
    log.error('Error in preview signals', error, {
      requestId,
      handler: 'preview-signals',
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