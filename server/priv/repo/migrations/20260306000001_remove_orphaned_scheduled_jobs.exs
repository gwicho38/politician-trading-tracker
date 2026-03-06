defmodule Server.Repo.Migrations.RemoveOrphanedScheduledJobs do
  @moduledoc """
  Remove scheduled_jobs entries that have no corresponding Elixir module.

  These are legacy entries that accumulate in the jobs.scheduled_jobs table
  but are never executed because no job module registers them. They show up
  as perpetual "never ran" entries in health audits.

  Orphaned IDs:
  - daily-scheduled-sync  (no module; sync handled by SyncDataJob/sync-data)
  - reference-portfolio-snapshot (duplicate; PortfolioSnapshotJob uses portfolio-snapshot)
  - signal-generation     (duplicate of trading-signals; flagged in prior cleanup migration)
  - update-stats          (no standalone module; handled via SyncDataJob path routing)
  """

  use Ecto.Migration

  def up do
    execute """
    DELETE FROM jobs.scheduled_jobs
    WHERE job_id IN (
      'daily-scheduled-sync',
      'reference-portfolio-snapshot',
      'signal-generation',
      'update-stats'
    )
    """

    execute """
    DELETE FROM jobs.job_executions
    WHERE job_id IN (
      'daily-scheduled-sync',
      'reference-portfolio-snapshot',
      'signal-generation',
      'update-stats'
    )
    """
  end

  def down do
    # These entries are intentionally not restored — they were orphaned
    :ok
  end
end
