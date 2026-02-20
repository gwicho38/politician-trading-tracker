import { createClient } from 'jsr:@supabase/supabase-js@2'
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { corsHeaders } from '../_shared/cors.ts'

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
const ETL_API_URL = Deno.env.get('ETL_API_URL') || 'https://politician-trading-etl.fly.dev'
const ETL_API_KEY = Deno.env.get('ETL_ADMIN_API_KEY') || Deno.env.get('ETL_API_KEY') || ''

// Champion/Challenger thresholds
const MIN_ACCURACY_IMPROVEMENT = 0.02 // 2 percentage-point improvement
const MIN_F1_IMPROVEMENT = 0.03       // 3 percentage-point improvement

// Training mode decision thresholds
const FINE_TUNE_MAX_AGE_DAYS = 30     // Fine-tune if model is younger than 30 days
const SCRATCH_MIN_PERF_DROP = 0.10    // Train from scratch if accuracy dropped >10pp from peak
const MIN_OUTCOMES_FOR_FINE_TUNE = 20 // Need at least 20 new outcomes for fine-tuning to be meaningful

// Polling limits
const MAX_WAIT_MS = 300_000    // 5 minutes
const POLL_INTERVAL_MS = 10_000 // 10 seconds

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
    const useOutcomes = (body.use_outcomes as boolean) ?? false
    const outcomeWindowDays = (body.outcome_window_days as number) ?? 90
    const compareToCurrent = (body.compare_to_current as boolean) ?? true
    const lookbackDays = (body.lookback_days as number) ?? 365
    const triggeredBy = (body.triggered_by as string) || 'scheduler'
    const autoTrainingMode = (body.auto_training_mode as boolean) ?? false
    const explicitFineTune = body.fine_tune as boolean | undefined

    if (action !== 'train') {
      return new Response(
        JSON.stringify({ error: `Unknown action: ${action}` }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      )
    }

    log.info('Starting ML training', {
      requestId,
      useOutcomes,
      compareToCurrent,
      lookbackDays,
      triggeredBy,
      autoTrainingMode,
    })

    // ------------------------------------------------------------------
    // Step 1: Snapshot current active model metrics for later comparison
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
          f1Weighted: currentModelMetrics?.f1_weighted,
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
      // Caller explicitly chose
      fineTune = explicitFineTune
      trainingModeReason = `explicit: ${fineTune ? 'fine-tune' : 'from scratch'}`
    } else if (autoTrainingMode && currentModelId) {
      // Auto-decide based on model age, performance trend, and outcome data volume
      const modelAgeDays = currentModelCreatedAt
        ? Math.floor((Date.now() - new Date(currentModelCreatedAt).getTime()) / (1000 * 60 * 60 * 24))
        : 999

      // Check how many new outcomes exist since last training
      const { count: newOutcomeCount } = await supabaseClient
        .from('signal_outcomes')
        .select('id', { count: 'exact', head: true })
        .gte('created_at', currentModelCreatedAt || '2020-01-01')

      // Check peak accuracy from model_performance_history
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
        // Large performance degradation — market regime has shifted, start fresh
        fineTune = false
        trainingModeReason = `scratch: performance dropped ${(perfDrop * 100).toFixed(1)}pp from peak (threshold: ${(SCRATCH_MIN_PERF_DROP * 100).toFixed(0)}pp)`
      } else if (modelAgeDays <= FINE_TUNE_MAX_AGE_DAYS && (newOutcomeCount ?? 0) >= MIN_OUTCOMES_FOR_FINE_TUNE) {
        // Model is recent and we have enough new outcomes — fine-tune
        fineTune = true
        trainingModeReason = `fine-tune: model is ${modelAgeDays}d old (<${FINE_TUNE_MAX_AGE_DAYS}d), ${newOutcomeCount} new outcomes (>=${MIN_OUTCOMES_FOR_FINE_TUNE})`
      } else if (modelAgeDays > FINE_TUNE_MAX_AGE_DAYS) {
        // Model is old — train from scratch with full data
        fineTune = false
        trainingModeReason = `scratch: model is ${modelAgeDays}d old (>${FINE_TUNE_MAX_AGE_DAYS}d threshold)`
      } else {
        // Not enough new outcomes to justify fine-tuning, but model isn't old
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
    log.info('Training job created', { requestId, jobId })

    // ------------------------------------------------------------------
    // Step 3: Poll for completion (max 5 minutes)
    // ------------------------------------------------------------------
    let jobStatus = 'pending'
    let newModelMetrics: Record<string, number> | null = null
    let newModelId: string | null = null
    const startTime = Date.now()

    while (Date.now() - startTime < MAX_WAIT_MS) {
      await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL_MS))

      const statusResponse = await fetch(`${ETL_API_URL}/ml/train/${jobId}`, {
        headers: { 'X-API-Key': ETL_API_KEY },
      })

      if (statusResponse.ok) {
        const statusData = await statusResponse.json()
        jobStatus = statusData.status

        if (jobStatus === 'completed') {
          newModelMetrics = statusData.metrics ?? null
          newModelId = statusData.model_id ?? null
          log.info('Training job completed', {
            requestId,
            jobId,
            newModelId,
            accuracy: newModelMetrics?.accuracy,
            f1Weighted: newModelMetrics?.f1_weighted,
          })
          break
        }

        if (jobStatus === 'failed') {
          throw new Error(`Training job ${jobId} failed: ${statusData.error || 'unknown'}`)
        }
      }
    }

    // If still running after timeout, return a pending acknowledgment
    if (jobStatus !== 'completed') {
      log.info('Training still running after poll timeout', { requestId, jobId })
      return new Response(
        JSON.stringify({
          success: true,
          message: 'Training started but not yet complete — poll /ml/train/' + jobId,
          job_id: jobId,
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      )
    }

    // ------------------------------------------------------------------
    // Step 4: Champion / Challenger gate
    // ------------------------------------------------------------------
    let promoted = true
    let reason = 'No current model to compare against — auto-promoting'

    if (compareToCurrent && currentModelMetrics && newModelMetrics) {
      const oldAcc = currentModelMetrics.accuracy ?? 0
      const newAcc = newModelMetrics.accuracy ?? 0
      const oldF1 = currentModelMetrics.f1_weighted ?? 0
      const newF1 = newModelMetrics.f1_weighted ?? 0

      const accImprovement = newAcc - oldAcc
      const f1Improvement = newF1 - oldF1

      const meetsAccuracy = accImprovement >= MIN_ACCURACY_IMPROVEMENT
      const meetsF1 = f1Improvement >= MIN_F1_IMPROVEMENT

      if (meetsAccuracy || meetsF1) {
        promoted = true
        reason =
          `Promoted: accuracy ${accImprovement >= 0 ? '+' : ''}${(accImprovement * 100).toFixed(1)}%` +
          `, F1 ${f1Improvement >= 0 ? '+' : ''}${(f1Improvement * 100).toFixed(1)}%`
      } else {
        promoted = false
        reason =
          `Below threshold: accuracy ${accImprovement >= 0 ? '+' : ''}${(accImprovement * 100).toFixed(1)}%` +
          ` (need +${(MIN_ACCURACY_IMPROVEMENT * 100).toFixed(0)}%)` +
          `, F1 ${f1Improvement >= 0 ? '+' : ''}${(f1Improvement * 100).toFixed(1)}%` +
          ` (need +${(MIN_F1_IMPROVEMENT * 100).toFixed(0)}%)`
      }

      log.info('Champion/Challenger result', { requestId, promoted, reason })

      // If challenger lost, demote it back to candidate and restore champion
      if (!promoted) {
        // The ETL service auto-promotes the newly trained model to 'active'.
        // We need to revert: set the new model to 'candidate' and re-activate the old one.
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

          if (currentModelId) {
            await supabaseClient
              .from('ml_models')
              .update({ status: 'active' })
              .eq('id', currentModelId)
          }

          log.info('Reverted model promotion', {
            requestId,
            demotedModelId: newestActive.id,
            restoredModelId: currentModelId,
          })
        }
      }
    }

    // ------------------------------------------------------------------
    // Step 5: Log to model_retraining_events
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
        trigger_type: triggeredBy === 'scheduler' ? 'scheduled' : 'manual',
        trigger_reason: `${fineTune ? 'fine-tune' : 'scratch'}, use_outcomes=${useOutcomes}, lookback=${lookbackDays}d`,
        old_model_metrics: currentModelMetrics,
        new_model_metrics: newModelMetrics,
        improvement_pct: improvementPct,
        deployed: promoted,
        deployment_reason: reason,
      })

    if (insertError) {
      log.error('Failed to log retraining event', insertError, { requestId })
    }

    // ------------------------------------------------------------------
    // Response
    // ------------------------------------------------------------------
    return new Response(
      JSON.stringify({
        success: true,
        job_id: jobId,
        model_id: newModelId,
        promoted,
        reason,
        metrics: newModelMetrics,
        training_mode: fineTune ? 'fine-tune' : 'from-scratch',
        training_mode_reason: trainingModeReason,
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
    )
  } catch (error) {
    log.error('Edge function error', error, { requestId })
    return new Response(
      JSON.stringify({ error: error instanceof Error ? error.message : String(error) }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
    )
  }
})
