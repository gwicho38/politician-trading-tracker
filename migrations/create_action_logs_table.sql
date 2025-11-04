-- Migration: Create action_logs table for tracking all user actions and system events
-- Created: 2025-11-03
-- Description: This table logs all actions triggered in the system including manual UI actions,
--              scheduled jobs, and automatic recovery operations.

-- Create action_logs table
CREATE TABLE IF NOT EXISTS action_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Action identification
    action_type VARCHAR(50) NOT NULL,  -- e.g., 'data_collection_start', 'job_execution', 'ticker_backfill'
    action_name VARCHAR(255),          -- Human-readable action name

    -- User/source information
    user_id VARCHAR(255),              -- User identifier (email, username, etc.)
    source VARCHAR(50) NOT NULL,       -- 'ui_button', 'scheduled_job', 'api', 'recovery', 'system'

    -- Timing
    action_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_seconds DECIMAL(10,3),

    -- Status tracking
    status VARCHAR(20) NOT NULL,       -- 'initiated', 'in_progress', 'completed', 'failed', 'cancelled'
    result_message TEXT,               -- Success message or summary
    error_message TEXT,                -- Error message if failed

    -- Context and relationships
    action_details JSONB,              -- Action-specific data (parameters, configuration, etc.)
    job_id VARCHAR(100),               -- Related scheduled job ID (if applicable)
    job_execution_id UUID,             -- Related job execution ID (if applicable)

    -- Request metadata
    ip_address VARCHAR(45),            -- IPv4 or IPv6 address
    user_agent TEXT,                   -- Browser/client user agent
    session_id VARCHAR(255),           -- Session identifier

    -- Audit timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_action_logs_action_type ON action_logs(action_type);
CREATE INDEX IF NOT EXISTS idx_action_logs_user_id ON action_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_action_logs_timestamp ON action_logs(action_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_action_logs_job_id ON action_logs(job_id);
CREATE INDEX IF NOT EXISTS idx_action_logs_status ON action_logs(status);
CREATE INDEX IF NOT EXISTS idx_action_logs_source ON action_logs(source);
CREATE INDEX IF NOT EXISTS idx_action_logs_created_at ON action_logs(created_at DESC);

-- Create composite indexes for common filter combinations
CREATE INDEX IF NOT EXISTS idx_action_logs_type_status ON action_logs(action_type, status);
CREATE INDEX IF NOT EXISTS idx_action_logs_user_timestamp ON action_logs(user_id, action_timestamp DESC);

-- Create index on JSONB column for efficient querying
CREATE INDEX IF NOT EXISTS idx_action_logs_action_details ON action_logs USING GIN (action_details);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_action_logs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to call the function
DROP TRIGGER IF EXISTS trigger_update_action_logs_updated_at ON action_logs;
CREATE TRIGGER trigger_update_action_logs_updated_at
    BEFORE UPDATE ON action_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_action_logs_updated_at();

-- Create view for recent actions summary
CREATE OR REPLACE VIEW action_logs_summary AS
SELECT
    action_type,
    source,
    status,
    COUNT(*) as total_count,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_count,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_count,
    AVG(duration_seconds) as avg_duration_seconds,
    MAX(action_timestamp) as last_occurrence,
    MIN(action_timestamp) as first_occurrence
FROM action_logs
WHERE action_timestamp >= NOW() - INTERVAL '7 days'
GROUP BY action_type, source, status
ORDER BY total_count DESC;

-- Create view for user activity summary
CREATE OR REPLACE VIEW user_activity_summary AS
SELECT
    user_id,
    COUNT(*) as total_actions,
    COUNT(DISTINCT action_type) as unique_action_types,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_actions,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_actions,
    MAX(action_timestamp) as last_activity,
    MIN(action_timestamp) as first_activity
FROM action_logs
WHERE user_id IS NOT NULL
GROUP BY user_id
ORDER BY total_actions DESC;

-- Create view for job execution tracking
CREATE OR REPLACE VIEW job_action_history AS
SELECT
    al.id,
    al.action_type,
    al.job_id,
    al.job_execution_id,
    al.action_timestamp,
    al.status,
    al.duration_seconds,
    al.error_message,
    al.action_details,
    sj.job_name,
    sj.schedule_type
FROM action_logs al
LEFT JOIN scheduled_jobs sj ON al.job_id = sj.job_id
WHERE al.job_id IS NOT NULL
ORDER BY al.action_timestamp DESC;

-- Add comments to document the table
COMMENT ON TABLE action_logs IS 'Logs all actions triggered in the system including manual, scheduled, and automatic operations';
COMMENT ON COLUMN action_logs.action_type IS 'Type of action performed (e.g., data_collection_start, job_execution)';
COMMENT ON COLUMN action_logs.source IS 'Source that triggered the action (ui_button, scheduled_job, api, recovery, system)';
COMMENT ON COLUMN action_logs.status IS 'Current status of the action (initiated, in_progress, completed, failed, cancelled)';
COMMENT ON COLUMN action_logs.action_details IS 'JSON object containing action-specific parameters and configuration';
COMMENT ON COLUMN action_logs.job_id IS 'Reference to scheduled_jobs.job_id if action is related to a scheduled job';
COMMENT ON COLUMN action_logs.job_execution_id IS 'Reference to job_executions.id if action is related to a job execution';

-- Grant permissions (adjust based on your Supabase setup)
-- GRANT SELECT, INSERT, UPDATE ON action_logs TO authenticated;
-- GRANT SELECT ON action_logs_summary TO authenticated;
-- GRANT SELECT ON user_activity_summary TO authenticated;
-- GRANT SELECT ON job_action_history TO authenticated;
