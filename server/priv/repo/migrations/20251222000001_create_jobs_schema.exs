defmodule Server.Repo.Migrations.CreateJobsSchema do
  use Ecto.Migration

  def up do
    # Create the jobs schema
    execute "CREATE SCHEMA IF NOT EXISTS jobs"

    # Create scheduled_jobs table in jobs schema
    execute """
    CREATE TABLE IF NOT EXISTS jobs.scheduled_jobs (
      id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
      job_id TEXT UNIQUE NOT NULL,
      job_name TEXT NOT NULL,
      job_function TEXT NOT NULL,
      schedule_type TEXT NOT NULL CHECK (schedule_type IN ('cron', 'interval')),
      schedule_value TEXT NOT NULL,
      enabled BOOLEAN DEFAULT true,
      last_run_at TIMESTAMPTZ,
      last_successful_run TIMESTAMPTZ,
      last_attempted_run TIMESTAMPTZ,
      next_scheduled_run TIMESTAMPTZ,
      consecutive_failures INTEGER DEFAULT 0,
      max_consecutive_failures INTEGER DEFAULT 3,
      auto_retry_on_startup BOOLEAN DEFAULT true,
      metadata JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ DEFAULT now(),
      updated_at TIMESTAMPTZ DEFAULT now()
    )
    """

    # Create job_executions table in jobs schema
    execute """
    CREATE TABLE IF NOT EXISTS jobs.job_executions (
      id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
      job_id TEXT NOT NULL,
      started_at TIMESTAMPTZ DEFAULT now(),
      completed_at TIMESTAMPTZ,
      status TEXT DEFAULT 'running' CHECK (status IN ('running', 'success', 'failed', 'completed')),
      duration_seconds NUMERIC(10, 3),
      records_processed INTEGER DEFAULT 0,
      error_message TEXT,
      logs TEXT,
      execution_log JSONB DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ DEFAULT now()
    )
    """

    # Create indexes
    execute "CREATE INDEX IF NOT EXISTS idx_jobs_executions_job_id ON jobs.job_executions(job_id)"
    execute "CREATE INDEX IF NOT EXISTS idx_jobs_executions_started_at ON jobs.job_executions(started_at DESC)"
    execute "CREATE INDEX IF NOT EXISTS idx_jobs_scheduled_enabled ON jobs.scheduled_jobs(enabled)"

    # Insert default job definitions
    execute """
    INSERT INTO jobs.scheduled_jobs (job_id, job_name, job_function, schedule_type, schedule_value, metadata)
    VALUES
      ('scheduled-sync', 'Scheduled Sync', 'scheduled-sync', 'cron', '0 */4 * * *',
       '{"description": "Update stats, chart data, and politician parties"}'::jsonb),
      ('signal-generation', 'Signal Generation', 'trading-signals', 'cron', '30 */4 * * *',
       '{"description": "Generate trading signals from disclosure data"}'::jsonb),
      ('update-stats', 'Update Dashboard Stats', 'sync-data/update-stats', 'cron', '0 * * * *',
       '{"description": "Refresh dashboard statistics hourly"}'::jsonb),
      ('data_collection', 'Automated Data Collection', 'data-collection', 'interval', '7200',
       '{"description": "Collect politician trading disclosures every 2 hours"}'::jsonb),
      ('data_collection_daily', 'Daily Data Collection', 'data-collection-daily', 'cron', '0 2 * * *',
       '{"description": "Full data collection run daily at 2 AM"}'::jsonb),
      ('ticker_backfill_daily', 'Daily Ticker Backfill', 'ticker-backfill', 'cron', '0 3 * * *',
       '{"description": "Extract and populate missing ticker symbols daily at 3 AM"}'::jsonb)
    ON CONFLICT (job_id) DO UPDATE SET
      job_name = EXCLUDED.job_name,
      schedule_type = EXCLUDED.schedule_type,
      schedule_value = EXCLUDED.schedule_value,
      metadata = EXCLUDED.metadata,
      updated_at = now()
    """
  end

  def down do
    execute "DROP TABLE IF EXISTS jobs.job_executions"
    execute "DROP TABLE IF EXISTS jobs.scheduled_jobs"
    execute "DROP SCHEMA IF EXISTS jobs"
  end
end
