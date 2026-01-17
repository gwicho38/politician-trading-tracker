import { createClient } from 'supabase'
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

// =============================================================================
// LOGGING UTILITY
// =============================================================================

type LogLevel = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR'

interface LogMetadata {
  [key: string]: unknown
}

function log(level: LogLevel, fn: string, message: string, metadata?: LogMetadata) {
  const timestamp = new Date().toISOString()
  const prefix = `[${timestamp}] [${level}] [${fn}]`

  if (metadata) {
    console.log(`${prefix} ${message}`, JSON.stringify(metadata))
  } else {
    console.log(`${prefix} ${message}`)
  }
}

const logger = {
  debug: (fn: string, message: string, metadata?: LogMetadata) => log('DEBUG', fn, message, metadata),
  info: (fn: string, message: string, metadata?: LogMetadata) => log('INFO', fn, message, metadata),
  warn: (fn: string, message: string, metadata?: LogMetadata) => log('WARN', fn, message, metadata),
  error: (fn: string, message: string, metadata?: LogMetadata) => log('ERROR', fn, message, metadata),
}

// =============================================================================
// SYNC-DATA ENDPOINT CALLER
// =============================================================================

async function callSyncDataEndpoint(endpoint: string, supabaseUrl: string, serviceRoleKey: string): Promise<{ success: boolean; data?: any; error?: string }> {
  try {
    const response = await fetch(`${supabaseUrl}/functions/v1/sync-data/${endpoint}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${serviceRoleKey}`,
        'apikey': serviceRoleKey,
        'Content-Type': 'application/json'
      }
    })

    if (!response.ok) {
      const errorText = await response.text()
      return { success: false, error: `HTTP ${response.status}: ${errorText}` }
    }

    const data = await response.json()
    return { success: true, data }
  } catch (error) {
    return { success: false, error: error.message }
  }
}

// =============================================================================
// MAIN SCHEDULED SYNC HANDLER
// =============================================================================

serve(async (req) => {
  const requestId = crypto.randomUUID().slice(0, 8)
  const fn = 'scheduled-sync'
  const startTime = Date.now()

  logger.info(fn, `Scheduled sync started`, { requestId })

  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL') ?? ''
    const serviceRoleKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''

    // Parse query params to determine which tasks to run
    const url = new URL(req.url)
    const mode = url.searchParams.get('mode') || 'daily' // 'daily', 'full', or 'quick'

    const results: Record<string, any> = {}

    if (mode === 'full') {
      // Full sync: includes data collection (heavy)
      logger.info(fn, 'Running FULL sync mode...', { requestId })

      const syncResult = await callSyncDataEndpoint('sync-full', supabaseUrl, serviceRoleKey)
      results.syncFull = syncResult
      logger.info(fn, `sync-full ${syncResult.success ? 'completed' : 'failed'}`, { requestId })
    }

    // Daily/Quick: Update aggregations (lightweight)
    logger.info(fn, 'Step 1: Running update-chart-data...', { requestId })
    const chartResult = await callSyncDataEndpoint('update-chart-data', supabaseUrl, serviceRoleKey)
    results.chartData = chartResult
    logger.info(fn, `update-chart-data ${chartResult.success ? 'completed' : 'failed'}`, { requestId })

    logger.info(fn, 'Step 2: Running update-stats...', { requestId })
    const statsResult = await callSyncDataEndpoint('update-stats', supabaseUrl, serviceRoleKey)
    results.stats = statsResult
    logger.info(fn, `update-stats ${statsResult.success ? 'completed' : 'failed'}`, { requestId })

    if (mode !== 'quick') {
      // Daily: Update politician parties (1 batch)
      logger.info(fn, 'Step 3: Running update-politician-parties...', { requestId })
      const partyResult = await callSyncDataEndpoint('update-politician-parties', supabaseUrl, serviceRoleKey)
      results.politicianParties = partyResult
      logger.info(fn, `update-politician-parties ${partyResult.success ? 'completed' : 'failed'}`, { requestId })
    }

    // Sync strategy followers (if market is open, the function will check)
    logger.info(fn, 'Step 4: Running strategy-follow sync-all-active...', { requestId })
    try {
      const strategyFollowResult = await fetch(`${supabaseUrl}/functions/v1/strategy-follow`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${serviceRoleKey}`,
          'apikey': serviceRoleKey,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action: 'sync-all-active' })
      })
      const strategyFollowData = await strategyFollowResult.json()
      results.strategyFollow = { success: strategyFollowResult.ok, data: strategyFollowData }
      logger.info(fn, `strategy-follow ${strategyFollowResult.ok ? 'completed' : 'failed'}`, { requestId, data: strategyFollowData })
    } catch (strategyError) {
      results.strategyFollow = { success: false, error: strategyError.message }
      logger.warn(fn, `strategy-follow failed: ${strategyError.message}`, { requestId })
    }

    // Reference Portfolio: Update positions and check for stop-loss/take-profit exits
    logger.info(fn, 'Step 5: Running reference-portfolio update-positions...', { requestId })
    try {
      const updatePosResult = await fetch(`${supabaseUrl}/functions/v1/reference-portfolio`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${serviceRoleKey}`,
          'apikey': serviceRoleKey,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action: 'update-positions' })
      })
      const updatePosData = await updatePosResult.json()
      results.referenceUpdatePositions = { success: updatePosResult.ok, data: updatePosData }
      logger.info(fn, `reference-portfolio update-positions ${updatePosResult.ok ? 'completed' : 'failed'}`, { requestId })
    } catch (refError) {
      results.referenceUpdatePositions = { success: false, error: refError.message }
      logger.warn(fn, `reference-portfolio update-positions failed: ${refError.message}`, { requestId })
    }

    logger.info(fn, 'Step 6: Running reference-portfolio check-exits...', { requestId })
    try {
      const checkExitsResult = await fetch(`${supabaseUrl}/functions/v1/reference-portfolio`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${serviceRoleKey}`,
          'apikey': serviceRoleKey,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action: 'check-exits' })
      })
      const checkExitsData = await checkExitsResult.json()
      results.referenceCheckExits = { success: checkExitsResult.ok, data: checkExitsData }
      logger.info(fn, `reference-portfolio check-exits ${checkExitsResult.ok ? 'completed' : 'failed'}`, { requestId, data: checkExitsData })
    } catch (refError) {
      results.referenceCheckExits = { success: false, error: refError.message }
      logger.warn(fn, `reference-portfolio check-exits failed: ${refError.message}`, { requestId })
    }

    const duration = Date.now() - startTime
    logger.info(fn, `Scheduled sync completed`, { requestId, duration: `${duration}ms`, mode })

    // Try to log sync run to database for monitoring (optional - table may not exist)
    try {
      const supabaseClient = createClient(supabaseUrl, serviceRoleKey)
      await supabaseClient
        .from('sync_logs')
        .insert({
          sync_type: 'scheduled',
          status: 'completed',
          results: results,
          duration_ms: duration,
          request_id: requestId
        })
    } catch (logError) {
      // Sync logs table may not exist yet, that's ok
      logger.warn(fn, `Could not log to sync_logs: ${logError.message}`)
    }

    return new Response(
      JSON.stringify({
        success: true,
        message: `Scheduled sync completed (${mode} mode)`,
        mode,
        requestId,
        duration: `${duration}ms`,
        results
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  } catch (error) {
    const duration = Date.now() - startTime
    logger.error(fn, `Scheduled sync failed: ${error.message}`, { requestId, stack: error.stack, duration })

    // Try to log failure
    try {
      const supabaseClient = createClient(
        Deno.env.get('SUPABASE_URL') ?? '',
        Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
      )
      await supabaseClient
        .from('sync_logs')
        .insert({
          sync_type: 'scheduled',
          status: 'failed',
          error_message: error.message,
          duration_ms: duration,
          request_id: requestId
        })
        .single()
    } catch (logError) {
      logger.error(fn, `Failed to log sync failure: ${logError.message}`)
    }

    return new Response(
      JSON.stringify({
        success: false,
        error: error.message,
        requestId,
        duration: `${duration}ms`
      }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  }
})
