-- Migration: Configure scheduled edge function execution
-- Created: 2025-12-18
-- Description: Sets up pg_cron jobs to periodically invoke edge functions

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_net;

-- =============================================================================
-- SCHEDULED JOBS TABLE (for tracking)
-- =============================================================================

-- Create scheduled_jobs table if not exists
CREATE TABLE IF NOT EXISTS public.scheduled_jobs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    job_id TEXT UNIQUE NOT NULL,
    job_name TEXT NOT NULL,
    job_function TEXT NOT NULL,
    schedule_type TEXT NOT NULL CHECK (schedule_type IN ('cron', 'interval')),
    schedule_value TEXT NOT NULL,
    enabled BOOLEAN DEFAULT true,
    last_run_at TIMESTAMPTZ,
    next_scheduled_run TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Add missing columns if table already exists with older schema
ALTER TABLE public.scheduled_jobs ADD COLUMN IF NOT EXISTS enabled BOOLEAN DEFAULT true;
ALTER TABLE public.scheduled_jobs ADD COLUMN IF NOT EXISTS last_run_at TIMESTAMPTZ;
ALTER TABLE public.scheduled_jobs ADD COLUMN IF NOT EXISTS next_scheduled_run TIMESTAMPTZ;
ALTER TABLE public.scheduled_jobs ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();
ALTER TABLE public.scheduled_jobs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();
ALTER TABLE public.scheduled_jobs ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- Create job_executions table if not exists
CREATE TABLE IF NOT EXISTS public.job_executions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES public.scheduled_jobs(job_id),
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    status TEXT DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
    records_processed INTEGER DEFAULT 0,
    error_message TEXT,
    execution_log JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_job_executions_job_id ON public.job_executions(job_id);
CREATE INDEX IF NOT EXISTS idx_job_executions_started_at ON public.job_executions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_enabled ON public.scheduled_jobs(enabled);

-- =============================================================================
-- INSERT SCHEDULED JOB DEFINITIONS
-- =============================================================================

-- Data Collection Job (every 6 hours)
INSERT INTO public.scheduled_jobs (job_id, job_name, job_function, schedule_type, schedule_value, next_scheduled_run, metadata)
VALUES (
    'data-collection',
    'Data Collection',
    'politician-trading-collect',
    'cron',
    '0 */6 * * *',
    NOW() + INTERVAL '6 hours',
    jsonb_build_object(
        'description', 'Collect financial disclosures from all sources',
        'endpoint', '/functions/v1/politician-trading-collect',
        'timeout_seconds', 300
    )
)
ON CONFLICT (job_id) DO UPDATE SET
    schedule_value = EXCLUDED.schedule_value,
    updated_at = now();

-- Sync Data Job (every 6 hours, 30 min after collection)
INSERT INTO public.scheduled_jobs (job_id, job_name, job_function, schedule_type, schedule_value, next_scheduled_run, metadata)
VALUES (
    'sync-data-full',
    'Full Data Sync',
    'sync-data/sync-full',
    'cron',
    '30 */6 * * *',
    NOW() + INTERVAL '6 hours' + INTERVAL '30 minutes',
    jsonb_build_object(
        'description', 'Sync politicians, trades, and update statistics',
        'endpoint', '/functions/v1/sync-data/sync-full',
        'timeout_seconds', 600
    )
)
ON CONFLICT (job_id) DO UPDATE SET
    schedule_value = EXCLUDED.schedule_value,
    updated_at = now();

-- Update Stats Job (every hour)
INSERT INTO public.scheduled_jobs (job_id, job_name, job_function, schedule_type, schedule_value, next_scheduled_run, metadata)
VALUES (
    'update-stats',
    'Update Dashboard Stats',
    'sync-data/update-stats',
    'cron',
    '0 * * * *',
    NOW() + INTERVAL '1 hour',
    jsonb_build_object(
        'description', 'Update dashboard statistics from trading_disclosures',
        'endpoint', '/functions/v1/sync-data/update-stats',
        'timeout_seconds', 120
    )
)
ON CONFLICT (job_id) DO UPDATE SET
    schedule_value = EXCLUDED.schedule_value,
    updated_at = now();

-- Signal Generation Job (every 2 hours)
INSERT INTO public.scheduled_jobs (job_id, job_name, job_function, schedule_type, schedule_value, next_scheduled_run, metadata)
VALUES (
    'signal-generation',
    'Signal Generation',
    'trading-signals/generate-signals',
    'cron',
    '0 */2 * * *',
    NOW() + INTERVAL '2 hours',
    jsonb_build_object(
        'description', 'Generate trading signals based on politician activity',
        'endpoint', '/functions/v1/trading-signals/generate-signals',
        'timeout_seconds', 180
    )
)
ON CONFLICT (job_id) DO UPDATE SET
    schedule_value = EXCLUDED.schedule_value,
    updated_at = now();

-- =============================================================================
-- PG_CRON JOBS (actual scheduling)
-- =============================================================================

-- Note: pg_cron is only available on Supabase Pro plans
-- These jobs use pg_net to call edge functions via HTTP

-- Helper function to invoke edge function
CREATE OR REPLACE FUNCTION public.invoke_edge_function(
    function_path TEXT,
    body JSONB DEFAULT '{}'::jsonb
) RETURNS void AS $$
DECLARE
    supabase_url TEXT;
    service_role_key TEXT;
BEGIN
    -- Get config from vault or environment
    supabase_url := current_setting('app.settings.supabase_url', true);
    service_role_key := current_setting('app.settings.service_role_key', true);

    IF supabase_url IS NULL OR service_role_key IS NULL THEN
        RAISE NOTICE 'Supabase settings not configured. Set app.settings.supabase_url and app.settings.service_role_key';
        RETURN;
    END IF;

    -- Make HTTP request using pg_net
    PERFORM net.http_post(
        url := supabase_url || function_path,
        headers := jsonb_build_object(
            'Content-Type', 'application/json',
            'Authorization', 'Bearer ' || service_role_key
        ),
        body := body
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to log job execution
CREATE OR REPLACE FUNCTION public.log_job_execution(
    p_job_id TEXT,
    p_status TEXT,
    p_records_processed INTEGER DEFAULT 0,
    p_error_message TEXT DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    execution_id UUID;
BEGIN
    INSERT INTO public.job_executions (job_id, status, records_processed, error_message, completed_at)
    VALUES (p_job_id, p_status, p_records_processed, p_error_message, CASE WHEN p_status != 'running' THEN now() END)
    RETURNING id INTO execution_id;

    -- Update last_run_at on scheduled_jobs
    UPDATE public.scheduled_jobs
    SET last_run_at = now(), updated_at = now()
    WHERE job_id = p_job_id;

    RETURN execution_id;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- CRON JOB SCHEDULING
-- Uncomment and run manually if you have pg_cron enabled (Supabase Pro)
-- =============================================================================
--
-- To enable scheduled jobs, run these in the Supabase SQL Editor:
--
-- SELECT cron.schedule('data-collection-cron', '0 */6 * * *',
--     $$SELECT public.invoke_edge_function('/functions/v1/politician-trading-collect')$$);
--
-- SELECT cron.schedule('sync-data-cron', '30 */6 * * *',
--     $$SELECT public.invoke_edge_function('/functions/v1/sync-data/sync-full')$$);
--
-- SELECT cron.schedule('update-stats-cron', '0 * * * *',
--     $$SELECT public.invoke_edge_function('/functions/v1/sync-data/update-stats')$$);
--
-- SELECT cron.schedule('signal-generation-cron', '0 */2 * * *',
--     $$SELECT public.invoke_edge_function('/functions/v1/trading-signals/generate-signals')$$);

-- =============================================================================
-- RLS POLICIES
-- =============================================================================

-- Enable RLS
ALTER TABLE public.scheduled_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.job_executions ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (for idempotent migration)
DROP POLICY IF EXISTS "Allow authenticated to view scheduled_jobs" ON public.scheduled_jobs;
DROP POLICY IF EXISTS "Allow authenticated to view job_executions" ON public.job_executions;

-- Allow authenticated users to read scheduled jobs
CREATE POLICY "Allow authenticated to view scheduled_jobs" ON public.scheduled_jobs
    FOR SELECT TO authenticated
    USING (true);

-- Allow authenticated users to view job executions
CREATE POLICY "Allow authenticated to view job_executions" ON public.job_executions
    FOR SELECT TO authenticated
    USING (true);

-- =============================================================================
-- GRANTS
-- =============================================================================

GRANT SELECT ON public.scheduled_jobs TO authenticated;
GRANT SELECT ON public.job_executions TO authenticated;
GRANT EXECUTE ON FUNCTION public.invoke_edge_function TO service_role;
GRANT EXECUTE ON FUNCTION public.log_job_execution TO service_role;

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE public.scheduled_jobs IS 'Registry of scheduled edge function jobs';
COMMENT ON TABLE public.job_executions IS 'Execution history for scheduled jobs';
COMMENT ON FUNCTION public.invoke_edge_function IS 'Helper to invoke edge functions via pg_net';
COMMENT ON FUNCTION public.log_job_execution IS 'Log job execution status';
