-- Job Executions Schema for APScheduler Job History
-- This table stores the execution history of scheduled jobs for persistence across app restarts

-- Job executions table
CREATE TABLE IF NOT EXISTS job_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('success', 'failed', 'cancelled')),
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL,
    duration_seconds DECIMAL(10,3),
    error_message TEXT,
    logs TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_job_executions_job_id ON job_executions(job_id);
CREATE INDEX IF NOT EXISTS idx_job_executions_status ON job_executions(status);
CREATE INDEX IF NOT EXISTS idx_job_executions_started_at ON job_executions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_job_executions_created_at ON job_executions(created_at DESC);

-- Composite index for efficient queries by job_id and time
CREATE INDEX IF NOT EXISTS idx_job_executions_job_id_started_at ON job_executions(job_id, started_at DESC);

-- RLS (Row Level Security) policies
ALTER TABLE job_executions ENABLE ROW LEVEL SECURITY;

-- Policy 1: Service role has full access (bypasses RLS)
CREATE POLICY "Service role bypass RLS" ON job_executions
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Policy 2: Authenticated users have full access
CREATE POLICY "Authenticated users full access" ON job_executions
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Policy 3: Anonymous users can read only
CREATE POLICY "Anonymous users read only" ON job_executions
    FOR SELECT
    TO anon
    USING (true);

-- Create a view for recent job execution summary
CREATE OR REPLACE VIEW job_execution_summary AS
SELECT
    job_id,
    COUNT(*) as total_executions,
    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful_executions,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_executions,
    COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_executions,
    MAX(started_at) as last_execution,
    AVG(duration_seconds) as avg_duration_seconds,
    MIN(duration_seconds) as min_duration_seconds,
    MAX(duration_seconds) as max_duration_seconds
FROM job_executions
WHERE started_at >= NOW() - INTERVAL '30 days'
GROUP BY job_id
ORDER BY last_execution DESC;

-- Grant permissions to anon and service_role for read access to the view
GRANT SELECT ON job_execution_summary TO anon;
GRANT SELECT ON job_execution_summary TO service_role;

-- Comments for documentation
COMMENT ON TABLE job_executions IS 'Stores execution history of scheduled jobs from APScheduler';
COMMENT ON COLUMN job_executions.job_id IS 'Job identifier matching APScheduler job ID like data_collection or ticker_backfill';
COMMENT ON COLUMN job_executions.logs IS 'Full log output captured during job execution';
COMMENT ON COLUMN job_executions.metadata IS 'Additional context like job configuration and environment details';
COMMENT ON COLUMN job_executions.duration_seconds IS 'Total execution time in seconds';

-- Optional: Add a function to clean up old job executions (keep last 1000 per job)
CREATE OR REPLACE FUNCTION cleanup_old_job_executions()
RETURNS void AS $$
BEGIN
    DELETE FROM job_executions
    WHERE id IN (
        SELECT id
        FROM (
            SELECT id,
                   ROW_NUMBER() OVER (PARTITION BY job_id ORDER BY started_at DESC) as rn
            FROM job_executions
        ) ranked
        WHERE rn > 1000
    );
END;
$$ LANGUAGE plpgsql;

-- Optional: Schedule cleanup to run periodically (if using pg_cron extension)
-- SELECT cron.schedule('cleanup-old-job-executions', '0 2 * * *', 'SELECT cleanup_old_job_executions()');
