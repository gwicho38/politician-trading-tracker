import { createClient } from 'jsr:@supabase/supabase-js@2'
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { corsHeaders } from '../_shared/cors.ts'
import { runCCGate, type CCGateResult } from './_lib.ts'

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
const ETL_API_URL = Deno.env.get('ETL_API_URL') || 'https://politician-trading-etl.fly.dev'
const ETL_API_KEY = Deno.env.get('ETL_ADMIN_API_KEY') || Deno.env.get('ETL_API_KEY') || ''

// Training mode decision thresholds
const FINE_TUNE_MAX_AGE_DAYS = 30     // Fine-tune if model is younger than 30 days
const SCRATCH_MIN_PERF_DROP = 0.10    // Train from scratch if accuracy dropped >10pp from peak
const MIN_OUTCOMES_FOR_FINE_TUNE = 20 // Need at least 20 new outcomes for fine-tuning to be meaningful

// ---------------------------------------------------------------------------
// Structured logging (matches signal-feedback pattern)
// ---------------------------------------------------------------------------
const log = {
  info: (message: string, metadata?: Record<string, unknown>) => {
    console.log(JSON.stringify({
      level: 'INFO',
      timestamp: new Date().toISOString(),
      service: 'ml-training',
      message,
      ...metadata,
    }))
  },
  warn: (message: string, metadata?: Record<string, unknown>) => {
    console.warn(JSON.stringify({
      level: 'WARN',
      timestamp: new Date().toISOString(),
      service: 'ml-training',
      message,
      ...metadata,
    }))
  },
  error: (message: string, error?: unknown, metadata?: Record<string, unknown>) => {
    console.error(JSON.stringify({
      level: 'ERROR',
      timestamp: new Date().toISOString(),
      service: 'ml-training',
      message,
      error: error instanceof Error ? error.message : error,
      ...metadata,
    }))
  },
}

// ---------------------------------------------------------------------------
// Handler
// ---------------------------------------------------------------------------
serve(async (req: Request) => {
  const requestId = crypto.randomUUID().substring(0, 8)

  // CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '',
    )

    // Parse request body
    let body: Record<string, unknown> = {}
    if (req.method === 'POST') {
      try {
        body = await req.json()
      } catch {
        // Body parsing failed, use defaults
      }
    }

    const action = (body.action as string) || 'train'

    if (action === 'train') {
      return await handleTrain(supabaseClient, body, requestId)
    }

    if (action === 'evaluate-training') {
      return await handleEvaluateTraining(supabaseClient, body, requestId)
    }

    return new Response(
      JSON.stringify({ error: `Unknown action: ${action}` }),
      { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
    )
  } catch (error) {
    log.error('Edge function error', error, { requestId })
    return new Response(
      JSON.stringify({ error: error instanceof Error ? error.message : String(error) }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
    )
  }
})

// ---------------------------------------------------------------------------
// Action: train
// Kicks off ETL training and returns 202 immediately.
// Baseline model metrics are stored in ml_training_jobs.config so the
// evaluate-training action can run the C/C gate later.
// ---------------------------------------------------------------------------
async function handleTrain(
  supabaseClient: ReturnType<typeof createClient>,
  body: Record<string, unknown>,
  requestId: string,
): Promise<Response> {
  const useOutcomes = (body.use_outcomes as boolean) ?? false
  const outcomeWindowDays = (body.outcome_window_days as number) ?? 90
  const compareToCurrent = (body.compare_to_current as boolean) ?? true
  const lookbackDays = (body.lookback_days as number) ?? 365
  const triggeredBy = (body.triggered_by as string) || 'scheduler'
  const autoTrainingMode = (body.auto_training_mode as boolean) ?? false
  const explicitFineTune = body.fine_tune as boolean | undefined

  log.info('Starting ML training (async)', {
    requestId,
    useOutcomes,
    compareToCurrent,
    lookbackDays,
    triggeredBy,
    autoTrainingMode,
  })

  // ------------------------------------------------------------------
  // Step 1: Snapshot current active model metrics for later C/C gate
  // ------------------------------------------------------------------
  let currentModelMetrics: Record<string, number> | null = null
  let currentModelId: string | null = null
  let currentModelVersion: string | null = null
  let currentModelCreatedAt: string | null = null

  if (compareToCurrent) {
    const { data: currentModel } = await supabaseClient
      .from('ml_models')
      .select('id, metrics, model_version, created_at')
      .eq('status', 'active')
      .order('created_at', { ascending: false })
      .limit(1)
      .maybeSingle()

    if (currentModel) {
      currentModelMetrics = currentModel.metrics
      currentModelId = currentModel.id
      currentModelVersion = currentModel.model_version
      currentModelCreatedAt = currentModel.created_at
      log.info('Current active model found', {
        requestId,
        modelId: currentModelId,
        modelVersion: currentModelVersion,
        accuracy: currentModelMetrics?.accuracy,
        createdAt: currentModelCreatedAt,
      })
    } else {
      log.info('No active model found — new model will be promoted unconditionally', { requestId })
    }
  }

  // ------------------------------------------------------------------
  // Step 1b: Decide training mode (fine-tune vs scratch)
  // ------------------------------------------------------------------
  let fineTune = false
  let trainingModeReason = 'default: train from scratch'

  if (explicitFineTune !== undefined) {
    fineTune = explicitFineTune
    trainingModeReason = `explicit: ${fineTune ? 'fine-tune' : 'from scratch'}`
  } else if (autoTrainingMode && currentModelId) {
    const modelAgeDays = currentModelCreatedAt
      ? Math.floor((Date.now() - new Date(currentModelCreatedAt).getTime()) / (1000 * 60 * 60 * 24))
      : 999

    const { count: newOutcomeCount } = await supabaseClient
      .from('signal_outcomes')
      .select('id', { count: 'exact', head: true })
      .gte('created_at', currentModelCreatedAt || '2020-01-01')

    const { data: peakPerf } = await supabaseClient
      .from('model_performance_history')
      .select('win_rate')
      .order('win_rate', { ascending: false })
      .limit(1)
      .maybeSingle()

    const currentAccuracy = currentModelMetrics?.accuracy ?? 0
    const peakWinRate = peakPerf?.win_rate ?? currentAccuracy
    const perfDrop = peakWinRate - (currentModelMetrics?.accuracy ?? peakWinRate)

    log.info('Training mode decision inputs', {
      requestId,
      modelAgeDays,
      newOutcomeCount: newOutcomeCount ?? 0,
      currentAccuracy,
      peakWinRate,
      perfDrop,
    })

    if (perfDrop >= SCRATCH_MIN_PERF_DROP) {
      fineTune = false
      trainingModeReason = `scratch: performance dropped ${(perfDrop * 100).toFixed(1)}pp from peak (threshold: ${(SCRATCH_MIN_PERF_DROP * 100).toFixed(0)}pp)`
    } else if (modelAgeDays <= FINE_TUNE_MAX_AGE_DAYS && (newOutcomeCount ?? 0) >= MIN_OUTCOMES_FOR_FINE_TUNE) {
      fineTune = true
      trainingModeReason = `fine-tune: model is ${modelAgeDays}d old (<${FINE_TUNE_MAX_AGE_DAYS}d), ${newOutcomeCount} new outcomes (>=${MIN_OUTCOMES_FOR_FINE_TUNE})`
    } else if (modelAgeDays > FINE_TUNE_MAX_AGE_DAYS) {
      fineTune = false
      trainingModeReason = `scratch: model is ${modelAgeDays}d old (>${FINE_TUNE_MAX_AGE_DAYS}d threshold)`
    } else {
      fineTune = false
      trainingModeReason = `scratch: only ${newOutcomeCount ?? 0} new outcomes (<${MIN_OUTCOMES_FOR_FINE_TUNE} threshold for fine-tune)`
    }
  }

  log.info('Training mode decided', { requestId, fineTune, trainingModeReason })

  // ------------------------------------------------------------------
  // Step 2: Trigger training via Python ETL service
  // ------------------------------------------------------------------
  const trainPayload: Record<string, unknown> = {
    lookback_days: lookbackDays,
    use_outcomes: useOutcomes,
    outcome_weight: 2.0,
    triggered_by: triggeredBy,
    fine_tune: fineTune,
  }
  if (fineTune && currentModelId) {
    trainPayload.base_model_id = currentModelId
  }

  const trainResponse = await fetch(`${ETL_API_URL}/ml/train`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': ETL_API_KEY,
    },
    body: JSON.stringify(trainPayload),
  })

  if (!trainResponse.ok) {
    const errText = await trainResponse.text()
    throw new Error(`ETL /ml/train returned ${trainResponse.status}: ${errText}`)
  }

  const trainResult = await trainResponse.json()
  const jobId: string = trainResult.job_id
  log.info('Training job created — returning 202 immediately', { requestId, jobId })

  // ------------------------------------------------------------------
  // Step 3: Persist baseline context in ml_training_jobs.config so the
  // evaluate-training action can run the C/C gate without re-querying.
  // ------------------------------------------------------------------
  const { error: updateError } = await supabaseClient
    .from('ml_training_jobs')
    .update({
      config: {
        baseline_model_id: currentModelId,
        baseline_metrics: currentModelMetrics,
        compare_to_current: compareToCurrent,
        triggered_by: triggeredBy,
        fine_tune: fineTune,
        training_mode_reason: trainingModeReason,
        lookback_days: lookbackDays,
        use_outcomes: useOutcomes,
        outcome_window_days: outcomeWindowDays,
      },
    })
    .eq('id', jobId)

  if (updateError) {
    // Non-fatal — C/C gate can still run without the stored context (will skip comparison)
    log.warn('Failed to store baseline context in training job', { requestId, jobId, error: updateError.message })
  }

  // 202 Accepted — training is running asynchronously
  return new Response(
    JSON.stringify({
      status: 'training_queued',
      job_id: jobId,
      training_mode: fineTune ? 'fine-tune' : 'from-scratch',
      training_mode_reason: trainingModeReason,
      baseline_model_id: currentModelId,
      message: `Training job ${jobId} queued. Call action=evaluate-training after completion to run C/C gate.`,
    }),
    { status: 202, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
  )
}

// ---------------------------------------------------------------------------
// Action: evaluate-training
// Runs the Champion/Challenger gate for a completed (but unevaluated) training job.
// Called by DailyModelEvalJob ~1h after triggering training, or when it detects
// a pending unevaluated job.
//
// Body params:
//   job_id (optional): specific job to evaluate; if omitted, finds the most
//                      recent completed job where cc_evaluated_at IS NULL
// ---------------------------------------------------------------------------
async function handleEvaluateTraining(
  supabaseClient: ReturnType<typeof createClient>,
  body: Record<string, unknown>,
  requestId: string,
): Promise<Response> {
  const explicitJobId = body.job_id as string | undefined

  log.info('Running evaluate-training', { requestId, explicitJobId })

  // ------------------------------------------------------------------
  // Find the job to evaluate
  // ------------------------------------------------------------------
  let jobId: string
  let storedConfig: Record<string, unknown> = {}

  if (explicitJobId) {
    const { data: job, error } = await supabaseClient
      .from('ml_training_jobs')
      .select('id, status, model_id, config, cc_evaluated_at')
      .eq('id', explicitJobId)
      .maybeSingle()

    if (error || !job) {
      return new Response(
        JSON.stringify({ error: `Training job ${explicitJobId} not found` }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      )
    }

    if (job.status !== 'completed') {
      return new Response(
        JSON.stringify({
          success: true,
          message: `Job ${explicitJobId} not yet completed (status: ${job.status})`,
          job_status: job.status,
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      )
    }

    if (job.cc_evaluated_at) {
      return new Response(
        JSON.stringify({
          success: true,
          message: `Job ${explicitJobId} already evaluated at ${job.cc_evaluated_at}`,
          already_evaluated: true,
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      )
    }

    jobId = job.id
    storedConfig = (job.config as Record<string, unknown>) ?? {}
  } else {
    // Auto-discover: most recent completed job not yet C/C-evaluated
    const { data: pendingJobs } = await supabaseClient
      .from('ml_training_jobs')
      .select('id, status, model_id, config, cc_evaluated_at, completed_at')
      .eq('status', 'completed')
      .is('cc_evaluated_at', null)
      .order('completed_at', { ascending: false })
      .limit(1)

    if (!pendingJobs || pendingJobs.length === 0) {
      log.info('No pending unevaluated training jobs found', { requestId })
      return new Response(
        JSON.stringify({ success: true, message: 'No pending training jobs to evaluate' }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      )
    }

    jobId = pendingJobs[0].id
    storedConfig = (pendingJobs[0].config as Record<string, unknown>) ?? {}
    log.info('Auto-discovered unevaluated job', { requestId, jobId })
  }

  // ------------------------------------------------------------------
  // Fetch training result from ETL to get new model metrics
  // ------------------------------------------------------------------
  const statusResponse = await fetch(`${ETL_API_URL}/ml/train/${jobId}`, {
    headers: { 'X-API-Key': ETL_API_KEY },
  })

  if (!statusResponse.ok) {
    throw new Error(`ETL /ml/train/${jobId} returned ${statusResponse.status}`)
  }

  const statusData = await statusResponse.json()
  const newModelMetrics: Record<string, number> | null = statusData.metrics ?? null
  const newModelId: string | null = statusData.model_id ?? null

  log.info('Training job result fetched', {
    requestId,
    jobId,
    newModelId,
    accuracy: newModelMetrics?.accuracy,
    f1Weighted: newModelMetrics?.f1_weighted,
  })

  // ------------------------------------------------------------------
  // Recover baseline from stored config
  // ------------------------------------------------------------------
  const currentModelId = (storedConfig.baseline_model_id as string | null) ?? null
  const currentModelMetrics = (storedConfig.baseline_metrics as Record<string, number> | null) ?? null
  const compareToCurrent = (storedConfig.compare_to_current as boolean) ?? true
  const fineTune = (storedConfig.fine_tune as boolean) ?? false
  const useOutcomes = (storedConfig.use_outcomes as boolean) ?? false
  const lookbackDays = (storedConfig.lookback_days as number) ?? 365

  // ------------------------------------------------------------------
  // Run Champion/Challenger gate
  // ------------------------------------------------------------------
  const ccResult = runCCGate(currentModelMetrics, newModelMetrics, compareToCurrent)

  log.info('Champion/Challenger result', {
    requestId,
    jobId,
    promoted: ccResult.promoted,
    reason: ccResult.reason,
  })

  // ------------------------------------------------------------------
  // Apply C/C gate: demote challenger if it lost
  // ------------------------------------------------------------------
  if (!ccResult.promoted && currentModelId) {
    // The ETL service auto-promotes the newly trained model to 'active'.
    // Revert: demote new model to 'candidate', restore old champion.
    const { data: newestActive } = await supabaseClient
      .from('ml_models')
      .select('id')
      .eq('status', 'active')
      .order('created_at', { ascending: false })
      .limit(1)
      .maybeSingle()

    if (newestActive && newestActive.id !== currentModelId) {
      await supabaseClient
        .from('ml_models')
        .update({ status: 'candidate' })
        .eq('id', newestActive.id)

      await supabaseClient
        .from('ml_models')
        .update({ status: 'active' })
        .eq('id', currentModelId)

      log.info('Reverted model promotion', {
        requestId,
        demotedModelId: newestActive.id,
        restoredModelId: currentModelId,
      })
    }
  }

  // ------------------------------------------------------------------
  // Log to model_retraining_events
  // ------------------------------------------------------------------
  const improvementPct =
    newModelMetrics?.accuracy != null && currentModelMetrics?.accuracy != null
      ? (newModelMetrics.accuracy - currentModelMetrics.accuracy) * 100
      : null

  const { error: insertError } = await supabaseClient
    .from('model_retraining_events')
    .insert({
      old_model_id: currentModelId,
      new_model_id: newModelId,
      trigger_type: storedConfig.triggered_by === 'scheduler' ? 'scheduled' : 'manual',
      trigger_reason: `${fineTune ? 'fine-tune' : 'scratch'}, use_outcomes=${useOutcomes}, lookback=${lookbackDays}d`,
      old_model_metrics: currentModelMetrics,
      new_model_metrics: newModelMetrics,
      improvement_pct: improvementPct,
      deployed: ccResult.promoted,
      deployment_reason: ccResult.reason,
    })

  if (insertError) {
    log.error('Failed to log retraining event', insertError, { requestId })
  }

  // ------------------------------------------------------------------
  // Mark job as C/C-evaluated
  // ------------------------------------------------------------------
  await supabaseClient
    .from('ml_training_jobs')
    .update({ cc_evaluated_at: new Date().toISOString() })
    .eq('id', jobId)

  return new Response(
    JSON.stringify({
      success: true,
      job_id: jobId,
      model_id: newModelId,
      promoted: ccResult.promoted,
      reason: ccResult.reason,
      metrics: newModelMetrics,
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
  )
}
