defmodule Server.Repo.Migrations.CleanupLegacyJobs do
  @moduledoc """
  Remove legacy job records that were created with edge function names
  instead of proper Elixir module names.

  These jobs were duplicates of jobs now properly registered via Elixir modules:
  - signal-generation (duplicate of trading-signals)
  - scheduled-sync (duplicate of scheduled-sync module)
  - update-stats (duplicate of sync-data module)
  - data_collection (duplicate of politician-trading job)
  - data_collection_daily (duplicate of politician-trading job)
  - ticker_backfill_daily (no longer needed)
  """

  use Ecto.Migration

  def up do
    # Delete the legacy jobs that have incorrect job_function values
    # These were inserted by 20251222000001_create_jobs_schema.exs with edge function names
    # instead of Elixir module names, causing "module not available" errors
    execute """
    DELETE FROM jobs.scheduled_jobs
    WHERE job_id IN (
      'signal-generation',
      'update-stats',
      'data_collection',
      'data_collection_daily',
      'ticker_backfill_daily'
    )
    AND job_function NOT LIKE 'Elixir.%'
    """

    # Also clean up any executions for these jobs
    execute """
    DELETE FROM jobs.job_executions
    WHERE job_id IN (
      'signal-generation',
      'update-stats',
      'data_collection',
      'data_collection_daily',
      'ticker_backfill_daily'
    )
    """
  end

  def down do
    # Re-insert the legacy jobs if needed (not recommended)
    execute """
    INSERT INTO jobs.scheduled_jobs (job_id, job_name, job_function, schedule_type, schedule_value, metadata)
    VALUES
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
    ON CONFLICT (job_id) DO NOTHING
    """
  end
end
