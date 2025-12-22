-- Migration: Enable pg_cron scheduled jobs for Edge Functions
-- Created: 2025-12-22
-- Description: Creates pg_cron jobs to invoke Edge Functions on schedule

-- =============================================================================
-- PREREQUISITES CHECK
-- =============================================================================

-- Ensure extensions are enabled (should already exist from previous migration)
CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_net;

-- =============================================================================
-- UPDATED INVOKE FUNCTION (uses Supabase built-in URL)
-- =============================================================================

-- Drop and recreate with proper Supabase integration
CREATE OR REPLACE FUNCTION public.invoke_scheduled_function(
    function_name TEXT,
    function_path TEXT DEFAULT NULL,
    request_body JSONB DEFAULT '{}'::jsonb
) RETURNS BIGINT AS $$
DECLARE
    project_url TEXT;
    anon_key TEXT;
    full_path TEXT;
    request_id BIGINT;
BEGIN
    -- Use Supabase's built-in project reference
    -- The URL format is: https://<project_ref>.supabase.co
    project_url := 'https://uljsqvwkomdrlnofmlad.supabase.co';

    -- Use the service role key (stored as a secret in Supabase)
    -- For pg_cron, we use the anon key since the functions handle their own auth
    anon_key := 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsanNxdndrb21kcmxub2ZtbGFkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4MDIyNDQsImV4cCI6MjA3MjM3ODI0NH0.QCpfcEpxGX_5Wn8ljf_J2KWjJLGdF8zRsV_7OatxmHI';

    -- Build full path
    full_path := COALESCE(function_path, '/functions/v1/' || function_name);

    -- Log the job start
    INSERT INTO public.job_executions (job_id, status, started_at)
    VALUES (function_name, 'running', now())
    ON CONFLICT DO NOTHING;

    -- Make HTTP POST request using pg_net
    SELECT net.http_post(
        url := project_url || full_path,
        headers := jsonb_build_object(
            'Content-Type', 'application/json',
            'Authorization', 'Bearer ' || anon_key,
            'apikey', anon_key
        ),
        body := request_body
    ) INTO request_id;

    -- Update job tracking
    UPDATE public.scheduled_jobs
    SET last_run_at = now(),
        updated_at = now()
    WHERE job_id = function_name;

    RETURN request_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute to postgres (for cron)
GRANT EXECUTE ON FUNCTION public.invoke_scheduled_function TO postgres;

-- =============================================================================
-- CLEAN UP OLD SCHEDULED JOBS AND RECREATE
-- =============================================================================

-- Remove duplicates and update to match new schedule
DELETE FROM public.scheduled_jobs WHERE job_id IN ('data-collection', 'sync-data-full', 'ticker_backfill');

-- Upsert the correct job definitions
INSERT INTO public.scheduled_jobs (job_id, job_name, job_function, schedule_type, schedule_value, enabled, metadata)
VALUES
    -- Scheduled sync (stats, chart data) - every 4 hours
    ('scheduled-sync', 'Scheduled Sync', 'scheduled-sync', 'cron', '0 */4 * * *', true,
     '{"description": "Update stats, chart data, and politician parties"}'::jsonb),

    -- Signal generation - every 4 hours at :30
    ('signal-generation', 'Signal Generation', 'trading-signals', 'cron', '30 */4 * * *', true,
     '{"description": "Generate trading signals from disclosure data"}'::jsonb),

    -- Update stats only - hourly for dashboard freshness
    ('update-stats', 'Update Dashboard Stats', 'sync-data/update-stats', 'cron', '0 * * * *', true,
     '{"description": "Refresh dashboard statistics hourly"}'::jsonb)
ON CONFLICT (job_id) DO UPDATE SET
    job_name = EXCLUDED.job_name,
    job_function = EXCLUDED.job_function,
    schedule_type = EXCLUDED.schedule_type,
    schedule_value = EXCLUDED.schedule_value,
    enabled = EXCLUDED.enabled,
    metadata = EXCLUDED.metadata,
    updated_at = now();

-- =============================================================================
-- PG_CRON JOB SCHEDULING
-- =============================================================================

-- Remove any existing cron jobs for these functions
SELECT cron.unschedule(jobname)
FROM cron.job
WHERE jobname LIKE '%scheduled-sync%'
   OR jobname LIKE '%signal-generation%'
   OR jobname LIKE '%update-stats%';

-- Schedule: Scheduled Sync (every 4 hours)
-- This updates chart data, dashboard stats, and politician parties
SELECT cron.schedule(
    'scheduled-sync-cron',
    '0 */4 * * *',
    $$SELECT public.invoke_scheduled_function('scheduled-sync', '/functions/v1/scheduled-sync?mode=daily')$$
);

-- Schedule: Signal Generation (every 4 hours at :30)
SELECT cron.schedule(
    'signal-generation-cron',
    '30 */4 * * *',
    $$SELECT public.invoke_scheduled_function('signal-generation', '/functions/v1/trading-signals')$$
);

-- Schedule: Update Stats (hourly)
-- Lightweight job to keep dashboard fresh
SELECT cron.schedule(
    'update-stats-cron',
    '0 * * * *',
    $$SELECT public.invoke_scheduled_function('update-stats', '/functions/v1/sync-data/update-stats')$$
);

-- =============================================================================
-- VERIFY CRON JOBS
-- =============================================================================

-- This will show all scheduled cron jobs
-- SELECT * FROM cron.job;

COMMENT ON FUNCTION public.invoke_scheduled_function IS
'Invokes a Supabase Edge Function via HTTP POST and logs the execution.
Used by pg_cron for scheduled job execution.';
