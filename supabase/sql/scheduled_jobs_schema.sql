-- Scheduled Jobs Schema for Job Recovery and Catch-up
-- This table tracks scheduled job definitions, frequencies, and status

-- Scheduled jobs table
CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id VARCHAR(100) NOT NULL UNIQUE,
    job_name VARCHAR(200) NOT NULL,
    job_function VARCHAR(200) NOT NULL,
    schedule_type VARCHAR(20) NOT NULL CHECK (schedule_type IN ('interval', 'cron')),
    schedule_value VARCHAR(100) NOT NULL,
    enabled BOOLEAN DEFAULT true,
    last_successful_run TIMESTAMPTZ,
    last_attempted_run TIMESTAMPTZ,
    next_scheduled_run TIMESTAMPTZ,
    consecutive_failures INTEGER DEFAULT 0,
    max_consecutive_failures INTEGER DEFAULT 3,
    auto_retry_on_startup BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_job_id ON scheduled_jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_enabled ON scheduled_jobs(enabled);
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_next_run ON scheduled_jobs(next_scheduled_run);
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_enabled_next_run ON scheduled_jobs(enabled, next_scheduled_run);

-- RLS (Row Level Security) policies
ALTER TABLE scheduled_jobs ENABLE ROW LEVEL SECURITY;

-- Policy 1: Service role has full access
CREATE POLICY "Service role bypass RLS" ON scheduled_jobs
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Policy 2: Authenticated users have full access
CREATE POLICY "Authenticated users full access" ON scheduled_jobs
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Policy 3: Anonymous users can read only
CREATE POLICY "Anonymous users read only" ON scheduled_jobs
    FOR SELECT
    TO anon
    USING (true);

-- Create a view for job status with last execution info
CREATE OR REPLACE VIEW scheduled_jobs_status AS
SELECT
    sj.id,
    sj.job_id,
    sj.job_name,
    sj.schedule_type,
    sj.schedule_value,
    sj.enabled,
    sj.last_successful_run,
    sj.last_attempted_run,
    sj.next_scheduled_run,
    sj.consecutive_failures,
    sj.max_consecutive_failures,
    sj.auto_retry_on_startup,
    je.status as last_execution_status,
    je.duration_seconds as last_execution_duration,
    je.error_message as last_execution_error,
    je.started_at as last_execution_time,
    CASE
        WHEN NOT sj.enabled THEN 'disabled'
        WHEN sj.consecutive_failures >= sj.max_consecutive_failures THEN 'failed_max_retries'
        WHEN sj.next_scheduled_run IS NULL THEN 'pending_first_run'
        WHEN sj.next_scheduled_run <= NOW() THEN 'overdue'
        ELSE 'scheduled'
    END as job_status
FROM scheduled_jobs sj
LEFT JOIN LATERAL (
    SELECT status, duration_seconds, error_message, started_at
    FROM job_executions
    WHERE job_executions.job_id = sj.job_id
    ORDER BY started_at DESC
    LIMIT 1
) je ON true
ORDER BY sj.next_scheduled_run ASC NULLS LAST;

-- Grant permissions
GRANT SELECT ON scheduled_jobs_status TO anon;
GRANT SELECT ON scheduled_jobs_status TO service_role;

-- Comments for documentation
COMMENT ON TABLE scheduled_jobs IS 'Tracks scheduled job definitions, frequencies, and recovery status';
COMMENT ON COLUMN scheduled_jobs.job_id IS 'Unique identifier matching APScheduler job ID';
COMMENT ON COLUMN scheduled_jobs.job_function IS 'Python function path to execute';
COMMENT ON COLUMN scheduled_jobs.schedule_type IS 'Type of schedule: interval (every N seconds/minutes) or cron';
COMMENT ON COLUMN scheduled_jobs.schedule_value IS 'Schedule definition: e.g. "3600" for interval, "0 */6 * * *" for cron';
COMMENT ON COLUMN scheduled_jobs.last_successful_run IS 'Timestamp of last successful execution';
COMMENT ON COLUMN scheduled_jobs.last_attempted_run IS 'Timestamp of last execution attempt (success or failure)';
COMMENT ON COLUMN scheduled_jobs.next_scheduled_run IS 'Calculated next run time';
COMMENT ON COLUMN scheduled_jobs.consecutive_failures IS 'Number of consecutive failures (resets on success)';
COMMENT ON COLUMN scheduled_jobs.max_consecutive_failures IS 'Stop auto-retry after this many consecutive failures';
COMMENT ON COLUMN scheduled_jobs.auto_retry_on_startup IS 'Whether to attempt catch-up on app startup';

-- Function to calculate next run time based on schedule
CREATE OR REPLACE FUNCTION calculate_next_run(
    p_schedule_type VARCHAR,
    p_schedule_value VARCHAR,
    p_last_run TIMESTAMPTZ
)
RETURNS TIMESTAMPTZ AS $$
DECLARE
    v_next_run TIMESTAMPTZ;
    v_interval_seconds INTEGER;
BEGIN
    -- If no last run, schedule for immediate execution
    IF p_last_run IS NULL THEN
        RETURN NOW();
    END IF;

    IF p_schedule_type = 'interval' THEN
        -- Parse interval in seconds
        v_interval_seconds := p_schedule_value::INTEGER;
        v_next_run := p_last_run + (v_interval_seconds || ' seconds')::INTERVAL;
    ELSIF p_schedule_type = 'cron' THEN
        -- For cron, we can't easily calculate in PostgreSQL
        -- Return a conservative estimate (add 1 hour)
        -- The actual cron calculation should be done in Python
        v_next_run := p_last_run + INTERVAL '1 hour';
    ELSE
        -- Unknown schedule type, default to 1 hour
        v_next_run := p_last_run + INTERVAL '1 hour';
    END IF;

    RETURN v_next_run;
END;
$$ LANGUAGE plpgsql;

-- Function to update job after execution
CREATE OR REPLACE FUNCTION update_job_after_execution(
    p_job_id VARCHAR,
    p_success BOOLEAN,
    p_next_run TIMESTAMPTZ DEFAULT NULL
)
RETURNS void AS $$
BEGIN
    IF p_success THEN
        -- Success: reset consecutive failures, update last successful run
        UPDATE scheduled_jobs
        SET
            last_successful_run = NOW(),
            last_attempted_run = NOW(),
            consecutive_failures = 0,
            next_scheduled_run = COALESCE(
                p_next_run,
                calculate_next_run(schedule_type, schedule_value, NOW())
            ),
            updated_at = NOW()
        WHERE job_id = p_job_id;
    ELSE
        -- Failure: increment consecutive failures, update last attempted run
        UPDATE scheduled_jobs
        SET
            last_attempted_run = NOW(),
            consecutive_failures = consecutive_failures + 1,
            next_scheduled_run = COALESCE(
                p_next_run,
                calculate_next_run(schedule_type, schedule_value, NOW())
            ),
            updated_at = NOW()
        WHERE job_id = p_job_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update updated_at timestamp
DROP TRIGGER IF EXISTS update_scheduled_jobs_updated_at ON scheduled_jobs;
CREATE TRIGGER update_scheduled_jobs_updated_at
    BEFORE UPDATE ON scheduled_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default scheduled jobs
INSERT INTO scheduled_jobs (job_id, job_name, job_function, schedule_type, schedule_value, next_scheduled_run, metadata) VALUES ('data_collection', 'Data Collection Job', 'politician_trading.scheduler.jobs.data_collection_job', 'interval', '21600', NOW(), jsonb_build_object('description', 'Collect politician trading data')) ON CONFLICT (job_id) DO NOTHING;

INSERT INTO scheduled_jobs (job_id, job_name, job_function, schedule_type, schedule_value, next_scheduled_run, metadata) VALUES ('ticker_backfill', 'Ticker Backfill Job', 'politician_trading.scheduler.jobs.ticker_backfill_job', 'interval', '86400', NOW() + INTERVAL '1 hour', jsonb_build_object('description', 'Backfill missing ticker symbols')) ON CONFLICT (job_id) DO NOTHING;

INSERT INTO scheduled_jobs (job_id, job_name, job_function, schedule_type, schedule_value, next_scheduled_run, metadata) VALUES ('signal-generation', 'Signal Generation', 'politician_trading.scheduler.jobs.signal_generation_job', 'interval', '7200', NOW() + INTERVAL '2 hours', jsonb_build_object('description', 'Generate trading signals based on collected data')) ON CONFLICT (job_id) DO NOTHING;
