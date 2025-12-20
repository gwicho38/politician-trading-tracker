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
      case 'get-signal-stats':
        response = await handleGetSignalStats(supabaseClient, req, requestId)
        break
      case 'update-target-prices':
        response = await handleUpdateTargetPrices(supabaseClient, req, requestId)
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

    // Insert signals into database
    const signalsToInsert = topSignals.map(signal => ({
      ...signal,
      user_id: user.id
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

// Handler to update existing signals with target prices
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

// Fetch current stock price from Yahoo Finance
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

// Batch fetch stock prices with rate limiting
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

// Calculate target price based on signal type and current price
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