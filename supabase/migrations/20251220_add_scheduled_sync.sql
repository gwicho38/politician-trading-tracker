-- Migration: Add scheduled-sync job and sync_logs table
-- Created: 2025-12-20
-- Description: Adds daily sync job and logging table

-- =============================================================================
-- SYNC LOGS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.sync_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    sync_type TEXT NOT NULL CHECK (sync_type IN ('scheduled', 'manual', 'webhook')),
    status TEXT NOT NULL CHECK (status IN ('started', 'completed', 'failed')),
    results JSONB DEFAULT '{}'::jsonb,
    error_message TEXT,
    duration_ms INTEGER,
    request_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for querying logs
CREATE INDEX IF NOT EXISTS idx_sync_logs_created_at ON public.sync_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_logs_status ON public.sync_logs(status);
CREATE INDEX IF NOT EXISTS idx_sync_logs_sync_type ON public.sync_logs(sync_type);

-- =============================================================================
-- SCHEDULED JOB DEFINITION
-- =============================================================================

-- Daily Scheduled Sync Job (runs at 2 AM UTC)
INSERT INTO public.scheduled_jobs (job_id, job_name, job_function, schedule_type, schedule_value, next_scheduled_run, metadata)
VALUES (
    'daily-scheduled-sync',
    'Daily Scheduled Sync',
    'scheduled-sync',
    'cron',
    '0 2 * * *',
    NOW() + INTERVAL '1 day',
    jsonb_build_object(
        'description', 'Daily comprehensive sync: data collection, chart updates, stats, politician parties',
        'endpoint', '/functions/v1/scheduled-sync',
        'timeout_seconds', 900
    )
)
ON CONFLICT (job_id) DO UPDATE SET
    schedule_value = EXCLUDED.schedule_value,
    metadata = EXCLUDED.metadata,
    updated_at = now();

-- =============================================================================
-- RLS POLICIES
-- =============================================================================

ALTER TABLE public.sync_logs ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Allow authenticated to view sync_logs" ON public.sync_logs;
DROP POLICY IF EXISTS "Allow service_role to insert sync_logs" ON public.sync_logs;

-- Allow authenticated users to read sync logs
CREATE POLICY "Allow authenticated to view sync_logs" ON public.sync_logs
    FOR SELECT TO authenticated
    USING (true);

-- Allow anon to insert (for edge functions)
CREATE POLICY "Allow anon to insert sync_logs" ON public.sync_logs
    FOR INSERT TO anon
    WITH CHECK (true);

-- =============================================================================
-- GRANTS
-- =============================================================================

GRANT SELECT ON public.sync_logs TO authenticated;
GRANT INSERT ON public.sync_logs TO anon;
GRANT ALL ON public.sync_logs TO service_role;

-- =============================================================================
-- CRON JOB (for Supabase Pro)
-- =============================================================================
-- Uncomment and run manually in SQL Editor if you have pg_cron enabled:
--
-- SELECT cron.schedule('daily-scheduled-sync-cron', '0 2 * * *',
--     $$SELECT public.invoke_edge_function('/functions/v1/scheduled-sync')$$);

COMMENT ON TABLE public.sync_logs IS 'Logs of scheduled and manual sync operations';
