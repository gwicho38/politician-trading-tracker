-- Database health fixes: connection exhaustion prevention + stale data cleanup
-- Addresses 503/connection pool exhaustion issues identified 2026-03-10/11

-- ============================================================
-- 1. Prevent idle-in-transaction connections from piling up.
--    The old get_jurisdiction_stats RPC held connections for 25s;
--    any similar future query spike would exhaust the 60-connection pool.
--    Killing connections stuck in an idle transaction after 10s prevents that.
-- ============================================================
ALTER DATABASE postgres SET idle_in_transaction_session_timeout = '10s';

-- ============================================================
-- 2. Drop the old get_jurisdiction_stats RPC (no longer called by the
--    frontend — replaced by direct queries + onTotalChange callback).
--    Removing it eliminates the risk of any leftover client code or
--    retry logic triggering the slow 25s-timeout query.
-- ============================================================
DROP FUNCTION IF EXISTS get_jurisdiction_stats(text[]);

-- ============================================================
-- 3. Truncate the stale jobs.job_executions table (177K rows from
--    Dec 28 – Jan 11, 2026 — superceded by public.job_executions).
--    This reclaims ~36MB of storage and removes a large scan target.
-- ============================================================
TRUNCATE TABLE jobs.job_executions;
VACUUM ANALYZE jobs.job_executions;

-- ============================================================
-- 4. Archive old public.job_executions rows (keep last 30 days).
--    The table had 24K rows; older ones are noise for monitoring.
-- ============================================================
DELETE FROM public.job_executions
WHERE created_at < NOW() - INTERVAL '30 days';

VACUUM ANALYZE public.job_executions;

-- ============================================================
-- 5. Vacuum the hot tables that accumulated dead rows.
--    trading_disclosures had 37K dead rows (ETL UPSERTs create churn).
-- ============================================================
VACUUM ANALYZE trading_disclosures;
VACUUM ANALYZE trading_signals;
VACUUM ANALYZE politicians;
VACUUM ANALYZE scheduled_jobs;

-- ============================================================
-- 6. Schedule automatic cleanup of old job_executions via pg_cron
--    (pg_cron extension is already installed on this project).
--    Runs daily at 03:00 UTC, keeps 30 days of history.
-- ============================================================
SELECT cron.schedule(
  'cleanup-job-executions',
  '0 3 * * *',
  $$DELETE FROM public.job_executions WHERE created_at < NOW() - INTERVAL '30 days'$$
);

-- ============================================================
-- 7. Add indexes to support the scheduler queries more efficiently.
--    The UPDATE scheduled_jobs SET last_attempted_run query (800K+ calls)
--    always filters by id — should already be indexed by PK, but
--    job_executions queries benefit from a created_at index for cleanup.
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_job_executions_created_at
  ON public.job_executions(created_at);

CREATE INDEX IF NOT EXISTS idx_job_executions_status_created
  ON public.job_executions(status, created_at)
  WHERE status = 'failed';
