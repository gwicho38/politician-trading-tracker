-- Migration: Add scheduled job for reference portfolio signal execution
-- Created: 2026-01-15
-- Description: Creates pg_cron job to process queued trading signals for the reference portfolio
-- This was missing, causing no trades to be executed after January 8th

-- =============================================================================
-- ADD REFERENCE PORTFOLIO JOBS TO SCHEDULED_JOBS TABLE
-- =============================================================================

INSERT INTO public.scheduled_jobs (job_id, job_name, job_function, schedule_type, schedule_value, enabled, metadata)
VALUES
    -- Execute queued signals - every 15 minutes during market hours
    ('reference-portfolio-execute', 'Reference Portfolio Execute Signals', 'reference-portfolio', 'cron', '*/15 * * * *', true,
     '{"description": "Process queued trading signals for reference portfolio"}'::jsonb),

    -- Update positions and sync prices - every hour
    ('reference-portfolio-sync', 'Reference Portfolio Sync', 'reference-portfolio', 'cron', '30 * * * *', true,
     '{"description": "Update position prices and portfolio metrics"}'::jsonb),

    -- Daily snapshot - once per day at market close (4:15 PM ET = 21:15 UTC)
    ('reference-portfolio-snapshot', 'Reference Portfolio Daily Snapshot', 'reference-portfolio', 'cron', '15 21 * * 1-5', true,
     '{"description": "Create daily performance snapshot for reference portfolio"}'::jsonb)
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

-- Remove any existing reference portfolio cron jobs first
SELECT cron.unschedule(jobname)
FROM cron.job
WHERE jobname LIKE '%reference-portfolio%';

-- Schedule: Execute signals every 15 minutes
-- This processes the reference_portfolio_signal_queue and executes trades
SELECT cron.schedule(
    'reference-portfolio-execute-cron',
    '*/15 * * * *',
    $$SELECT public.invoke_scheduled_function('reference-portfolio-execute', '/functions/v1/reference-portfolio', '{"action": "execute-signals"}'::jsonb)$$
);

-- Schedule: Update positions hourly (at :30)
-- This syncs current prices and updates portfolio metrics
SELECT cron.schedule(
    'reference-portfolio-sync-cron',
    '30 * * * *',
    $$SELECT public.invoke_scheduled_function('reference-portfolio-sync', '/functions/v1/reference-portfolio', '{"action": "update-positions"}'::jsonb)$$
);

-- Schedule: Create daily snapshot at market close (4:15 PM ET = 21:15 UTC, weekdays only)
SELECT cron.schedule(
    'reference-portfolio-snapshot-cron',
    '15 21 * * 1-5',
    $$SELECT public.invoke_scheduled_function('reference-portfolio-snapshot', '/functions/v1/reference-portfolio', '{"action": "create-snapshot"}'::jsonb)$$
);

-- =============================================================================
-- VERIFY CRON JOBS
-- =============================================================================

-- This will show all scheduled cron jobs (uncomment to verify)
-- SELECT * FROM cron.job WHERE jobname LIKE '%reference-portfolio%';

COMMENT ON TABLE public.scheduled_jobs IS
'Tracks scheduled jobs including the reference portfolio execution jobs added 2026-01-15';
