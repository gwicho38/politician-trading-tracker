import { createClient } from 'jsr:@supabase/supabase-js@2'
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

// Structured logging
const log = {
  info: (message: string, metadata?: any) => {
    console.log(JSON.stringify({
      level: 'INFO',
      timestamp: new Date().toISOString(),
      service: 'signal-feedback',
      message,
      ...metadata
    }))
  },
  error: (message: string, error?: any, metadata?: any) => {
    console.error(JSON.stringify({
      level: 'ERROR',
      timestamp: new Date().toISOString(),
      service: 'signal-feedback',
      message,
      error: error?.message || error,
      ...metadata
    }))
  }
}

serve(async (req) => {
  const requestId = crypto.randomUUID().substring(0, 8)

  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const url = new URL(req.url)
    const pathParts = url.pathname.split('/').filter(Boolean)
    const action = pathParts[pathParts.length - 1] || 'record-outcomes'

    // Also check body for action
    let bodyParams: any = {}
    if (req.method === 'POST') {
      try {
        bodyParams = await req.json()
      } catch {
        // Body parsing failed, use default
      }
    }

    const finalAction = bodyParams.action || action

    log.info('Processing action', { requestId, action: finalAction })

    switch (finalAction) {
      case 'record-outcomes':
        return await handleRecordOutcomes(supabaseClient, requestId)
      case 'analyze-features':
        return await handleAnalyzeFeatures(supabaseClient, requestId, bodyParams)
      case 'evaluate-model':
        return await handleEvaluateModel(supabaseClient, requestId, bodyParams)
      case 'get-summary':
        return await handleGetSummary(supabaseClient, requestId)
      default:
        return await handleRecordOutcomes(supabaseClient, requestId)
    }

  } catch (error) {
    log.error('Edge function error', error, { requestId })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

// =============================================================================
// RECORD OUTCOMES - Label closed positions with outcomes
// =============================================================================
async function handleRecordOutcomes(supabaseClient: any, requestId: string) {
  log.info('Recording signal outcomes', { requestId })

  // Find closed positions that don't have outcome records yet
  const { data: closedPositions, error: posError } = await supabaseClient
    .from('reference_portfolio_positions')
    .select(`
      *,
      entry_signal:trading_signals!entry_signal_id(
        id,
        ticker,
        signal_type,
        confidence_score,
        features,
        model_id,
        model_version,
        ml_enhanced,
        generated_at
      )
    `)
    .eq('is_open', false)
    .not('exit_date', 'is', null)
    .order('exit_date', { ascending: false })
    .limit(100)

  if (posError) {
    log.error('Failed to fetch closed positions', posError, { requestId })
    return new Response(
      JSON.stringify({ error: 'Failed to fetch closed positions' }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  if (!closedPositions || closedPositions.length === 0) {
    log.info('No closed positions to process', { requestId })
    return new Response(
      JSON.stringify({ success: true, message: 'No closed positions to process', recorded: 0 }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Check which positions already have outcome records
  const positionIds = closedPositions.map((p: any) => p.id)
  const { data: existingOutcomes } = await supabaseClient
    .from('signal_outcomes')
    .select('position_id')
    .in('position_id', positionIds)

  const existingPositionIds = new Set((existingOutcomes || []).map((o: any) => o.position_id))

  // Filter to only positions without outcome records
  const newPositions = closedPositions.filter((p: any) => !existingPositionIds.has(p.id))

  if (newPositions.length === 0) {
    log.info('All positions already have outcome records', { requestId })
    return new Response(
      JSON.stringify({ success: true, message: 'All positions already recorded', recorded: 0 }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  log.info('Processing new positions', { requestId, count: newPositions.length })

  // Create outcome records
  const outcomes = newPositions.map((position: any) => {
    const signal = position.entry_signal
    const entryPrice = parseFloat(position.entry_price)
    const exitPrice = parseFloat(position.exit_price)
    const quantity = position.quantity

    // Calculate return
    const returnPct = ((exitPrice - entryPrice) / entryPrice) * 100
    const returnDollars = (exitPrice - entryPrice) * quantity

    // Determine outcome
    let outcome: string
    if (returnPct > 0.5) {
      outcome = 'win'
    } else if (returnPct < -0.5) {
      outcome = 'loss'
    } else {
      outcome = 'breakeven'
    }

    // Calculate holding days
    const entryDate = new Date(position.entry_date)
    const exitDate = new Date(position.exit_date)
    const holdingDays = Math.ceil((exitDate.getTime() - entryDate.getTime()) / (1000 * 60 * 60 * 24))

    // Extract features from signal
    const features = signal?.features || {
      politician_count: position.politician_activity_count || 0,
      buy_sell_ratio: 1,
      bipartisan: false,
      recent_activity_30d: 0,
      net_volume: 0
    }

    return {
      signal_id: signal?.id || null,
      position_id: position.id,
      ticker: position.ticker,
      signal_type: signal?.signal_type || 'unknown',
      signal_confidence: signal?.confidence_score || position.entry_confidence,
      outcome,
      entry_price: entryPrice,
      exit_price: exitPrice,
      return_pct: Math.round(returnPct * 10000) / 10000,
      return_dollars: Math.round(returnDollars * 100) / 100,
      holding_days: holdingDays,
      exit_reason: position.exit_reason,
      features,
      model_id: signal?.model_id || null,
      model_version: signal?.model_version || 'unknown',
      ml_enhanced: signal?.ml_enhanced || false,
      signal_date: signal?.generated_at || null,
      entry_date: position.entry_date,
      exit_date: position.exit_date
    }
  })

  // Insert outcome records
  const { data: inserted, error: insertError } = await supabaseClient
    .from('signal_outcomes')
    .insert(outcomes)
    .select()

  if (insertError) {
    log.error('Failed to insert outcomes', insertError, { requestId })
    return new Response(
      JSON.stringify({ error: 'Failed to insert outcomes: ' + insertError.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Calculate summary stats
  const wins = outcomes.filter((o: any) => o.outcome === 'win').length
  const losses = outcomes.filter((o: any) => o.outcome === 'loss').length
  const avgReturn = outcomes.reduce((sum: number, o: any) => sum + o.return_pct, 0) / outcomes.length

  log.info('Outcomes recorded', {
    requestId,
    recorded: inserted?.length || 0,
    wins,
    losses,
    avgReturn: Math.round(avgReturn * 100) / 100
  })

  return new Response(
    JSON.stringify({
      success: true,
      recorded: inserted?.length || 0,
      summary: {
        wins,
        losses,
        breakeven: outcomes.length - wins - losses,
        avgReturnPct: Math.round(avgReturn * 100) / 100,
        winRate: Math.round((wins / outcomes.length) * 100)
      }
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

// =============================================================================
// ANALYZE FEATURES - Correlate features with outcomes
// =============================================================================
async function handleAnalyzeFeatures(supabaseClient: any, requestId: string, params: any) {
  const windowDays = params.windowDays || 90

  log.info('Analyzing feature importance', { requestId, windowDays })

  // Fetch outcomes with features
  const startDate = new Date()
  startDate.setDate(startDate.getDate() - windowDays)

  const { data: outcomes, error } = await supabaseClient
    .from('signal_outcomes')
    .select('*')
    .neq('outcome', 'open')
    .gte('exit_date', startDate.toISOString())

  if (error) {
    log.error('Failed to fetch outcomes', error, { requestId })
    return new Response(
      JSON.stringify({ error: 'Failed to fetch outcomes' }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  if (!outcomes || outcomes.length < 10) {
    return new Response(
      JSON.stringify({ success: true, message: 'Not enough outcomes for analysis', minRequired: 10, actual: outcomes?.length || 0 }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Define features to analyze
  const features = [
    'politician_count',
    'buy_sell_ratio',
    'bipartisan',
    'recent_activity_30d',
    'net_volume'
  ]

  const analysisDate = new Date().toISOString().split('T')[0]
  const featureAnalysis: any[] = []

  for (const featureName of features) {
    // Extract feature values
    const validOutcomes = outcomes.filter((o: any) =>
      o.features && o.features[featureName] !== undefined && o.features[featureName] !== null
    )

    if (validOutcomes.length < 10) continue

    const featureValues = validOutcomes.map((o: any) => ({
      value: featureName === 'bipartisan' ? (o.features[featureName] ? 1 : 0) : parseFloat(o.features[featureName]) || 0,
      return_pct: o.return_pct,
      outcome: o.outcome
    }))

    // Calculate median
    const sortedValues = [...featureValues].sort((a, b) => a.value - b.value)
    const median = sortedValues[Math.floor(sortedValues.length / 2)].value

    // Split by median
    const highGroup = featureValues.filter(v => v.value > median)
    const lowGroup = featureValues.filter(v => v.value <= median)

    // Calculate metrics
    const avgReturnHigh = highGroup.length > 0
      ? highGroup.reduce((sum, v) => sum + v.return_pct, 0) / highGroup.length
      : 0
    const avgReturnLow = lowGroup.length > 0
      ? lowGroup.reduce((sum, v) => sum + v.return_pct, 0) / lowGroup.length
      : 0

    const winRateHigh = highGroup.length > 0
      ? highGroup.filter(v => v.outcome === 'win').length / highGroup.length
      : 0
    const winRateLow = lowGroup.length > 0
      ? lowGroup.filter(v => v.outcome === 'win').length / lowGroup.length
      : 0

    // Calculate Pearson correlation
    const n = featureValues.length
    const sumX = featureValues.reduce((sum, v) => sum + v.value, 0)
    const sumY = featureValues.reduce((sum, v) => sum + v.return_pct, 0)
    const sumXY = featureValues.reduce((sum, v) => sum + v.value * v.return_pct, 0)
    const sumX2 = featureValues.reduce((sum, v) => sum + v.value * v.value, 0)
    const sumY2 = featureValues.reduce((sum, v) => sum + v.return_pct * v.return_pct, 0)

    const numerator = n * sumXY - sumX * sumY
    const denominator = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY))
    const correlation = denominator !== 0 ? numerator / denominator : 0

    // Determine if feature is useful
    const liftPct = avgReturnHigh - avgReturnLow
    const featureUseful = Math.abs(correlation) > 0.1 || Math.abs(liftPct) > 1

    // Calculate recommended weight based on correlation
    const baseWeight = 0.2
    const recommendedWeight = baseWeight + (correlation * 0.3)

    const analysis = {
      analysis_date: analysisDate,
      analysis_window_days: windowDays,
      feature_name: featureName,
      correlation_with_return: Math.round(correlation * 10000) / 10000,
      correlation_p_value: null, // Would need proper statistical test
      median_value: Math.round(median * 100) / 100,
      avg_return_when_high: Math.round(avgReturnHigh * 10000) / 10000,
      avg_return_when_low: Math.round(avgReturnLow * 10000) / 10000,
      lift_pct: Math.round(liftPct * 10000) / 10000,
      sample_size_total: featureValues.length,
      sample_size_high: highGroup.length,
      sample_size_low: lowGroup.length,
      win_rate_when_high: Math.round(winRateHigh * 10000) / 10000,
      win_rate_when_low: Math.round(winRateLow * 10000) / 10000,
      feature_useful: featureUseful,
      recommended_weight: Math.round(Math.max(0, Math.min(1, recommendedWeight)) * 10000) / 10000
    }

    featureAnalysis.push(analysis)
  }

  // Upsert analysis results
  if (featureAnalysis.length > 0) {
    const { error: upsertError } = await supabaseClient
      .from('feature_importance_history')
      .upsert(featureAnalysis, {
        onConflict: 'analysis_date,feature_name'
      })

    if (upsertError) {
      log.error('Failed to save feature analysis', upsertError, { requestId })
    }
  }

  log.info('Feature analysis complete', { requestId, featuresAnalyzed: featureAnalysis.length })

  return new Response(
    JSON.stringify({
      success: true,
      analysisDate,
      windowDays,
      sampleSize: outcomes.length,
      features: featureAnalysis.sort((a, b) => Math.abs(b.correlation_with_return) - Math.abs(a.correlation_with_return))
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

// =============================================================================
// EVALUATE MODEL - Calculate model performance metrics
// =============================================================================
async function handleEvaluateModel(supabaseClient: any, requestId: string, params: any) {
  const windowDays = params.windowDays || 30
  const modelId = params.modelId

  log.info('Evaluating model performance', { requestId, windowDays, modelId })

  // Get outcomes for evaluation period
  const startDate = new Date()
  startDate.setDate(startDate.getDate() - windowDays)

  let query = supabaseClient
    .from('signal_outcomes')
    .select('*')
    .neq('outcome', 'open')
    .gte('exit_date', startDate.toISOString())

  if (modelId) {
    query = query.eq('model_id', modelId)
  }

  const { data: outcomes, error } = await query

  if (error) {
    log.error('Failed to fetch outcomes for evaluation', error, { requestId })
    return new Response(
      JSON.stringify({ error: 'Failed to fetch outcomes' }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  if (!outcomes || outcomes.length < 5) {
    return new Response(
      JSON.stringify({ success: true, message: 'Not enough outcomes for evaluation', minRequired: 5, actual: outcomes?.length || 0 }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  // Calculate metrics
  const wins = outcomes.filter((o: any) => o.outcome === 'win').length
  const losses = outcomes.filter((o: any) => o.outcome === 'loss').length
  const winRate = wins / outcomes.length

  const returns = outcomes.map((o: any) => o.return_pct)
  const avgReturn = returns.reduce((sum: number, r: number) => sum + r, 0) / returns.length
  const totalReturn = returns.reduce((sum: number, r: number) => sum + r, 0)

  // Calculate Sharpe ratio (simplified - assumes risk-free rate of 0)
  const stdDev = Math.sqrt(
    returns.reduce((sum: number, r: number) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length
  )
  const sharpeRatio = stdDev !== 0 ? avgReturn / stdDev : 0

  // Calculate max drawdown
  let peak = 0
  let maxDrawdown = 0
  let cumulative = 0
  for (const ret of returns) {
    cumulative += ret
    if (cumulative > peak) peak = cumulative
    const drawdown = peak - cumulative
    if (drawdown > maxDrawdown) maxDrawdown = drawdown
  }

  // Confidence calibration
  const highConfidence = outcomes.filter((o: any) => o.signal_confidence >= 0.8)
  const lowConfidence = outcomes.filter((o: any) => o.signal_confidence < 0.7)

  const highConfWinRate = highConfidence.length > 0
    ? highConfidence.filter((o: any) => o.outcome === 'win').length / highConfidence.length
    : 0
  const lowConfWinRate = lowConfidence.length > 0
    ? lowConfidence.filter((o: any) => o.outcome === 'win').length / lowConfidence.length
    : 0

  // Get model info
  let modelVersion = 'mixed'
  const modelVersions = [...new Set(outcomes.map((o: any) => o.model_version))]
  if (modelVersions.length === 1) {
    modelVersion = modelVersions[0]
  }

  const performance = {
    model_id: modelId || null,
    model_version: modelVersion,
    evaluation_date: new Date().toISOString().split('T')[0],
    evaluation_window_days: windowDays,
    total_signals_generated: outcomes.length,
    signals_traded: outcomes.length,
    signals_skipped: 0,
    win_rate: Math.round(winRate * 10000) / 10000,
    avg_return_pct: Math.round(avgReturn * 10000) / 10000,
    total_return_pct: Math.round(totalReturn * 10000) / 10000,
    sharpe_ratio: Math.round(sharpeRatio * 10000) / 10000,
    sortino_ratio: null,
    max_drawdown_pct: Math.round(maxDrawdown * 10000) / 10000,
    confidence_correlation: null,
    high_confidence_win_rate: Math.round(highConfWinRate * 10000) / 10000,
    low_confidence_win_rate: Math.round(lowConfWinRate * 10000) / 10000,
    feature_weights: null,
    baseline_return_pct: null,
    alpha: null
  }

  // Save performance record
  const { error: insertError } = await supabaseClient
    .from('model_performance_history')
    .insert(performance)

  if (insertError) {
    log.warn('Failed to save performance record', { error: insertError.message })
  }

  log.info('Model evaluation complete', { requestId, winRate, avgReturn, sharpeRatio })

  return new Response(
    JSON.stringify({
      success: true,
      performance,
      breakdown: {
        wins,
        losses,
        breakeven: outcomes.length - wins - losses,
        highConfidenceCount: highConfidence.length,
        lowConfidenceCount: lowConfidence.length,
        mlEnhancedCount: outcomes.filter((o: any) => o.ml_enhanced).length
      }
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

// =============================================================================
// GET SUMMARY - Get overall feedback loop summary
// =============================================================================
async function handleGetSummary(supabaseClient: any, requestId: string) {
  log.info('Getting feedback summary', { requestId })

  // Get outcome counts
  const { data: outcomeCounts } = await supabaseClient
    .from('signal_outcomes')
    .select('outcome')

  const outcomes = outcomeCounts || []
  const totalOutcomes = outcomes.length
  const wins = outcomes.filter((o: any) => o.outcome === 'win').length
  const losses = outcomes.filter((o: any) => o.outcome === 'loss').length
  const open = outcomes.filter((o: any) => o.outcome === 'open').length

  // Get latest feature importance
  const { data: latestFeatures } = await supabaseClient
    .from('feature_importance_latest')
    .select('*')
    .limit(10)

  // Get latest model performance
  const { data: latestPerformance } = await supabaseClient
    .from('model_performance_history')
    .select('*')
    .order('evaluation_date', { ascending: false })
    .limit(1)

  return new Response(
    JSON.stringify({
      success: true,
      summary: {
        totalOutcomes,
        closedTrades: totalOutcomes - open,
        wins,
        losses,
        winRate: totalOutcomes - open > 0 ? Math.round((wins / (totalOutcomes - open)) * 100) : 0,
        openPositions: open
      },
      latestFeatureImportance: latestFeatures || [],
      latestModelPerformance: latestPerformance?.[0] || null
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}
