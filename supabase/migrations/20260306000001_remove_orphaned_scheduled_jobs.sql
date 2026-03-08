-- Remove orphaned scheduled_jobs entries that have no corresponding Elixir scheduler module.
-- These were added to the scheduled_jobs tables but the backing scheduler jobs were
-- removed or renamed, causing them to appear as perpetually "never ran" in audits.
-- Orphaned IDs: daily-scheduled-sync, reference-portfolio-snapshot, signal-generation, update-stats

DELETE FROM public.scheduled_jobs
WHERE job_id IN (
  'daily-scheduled-sync',
  'reference-portfolio-snapshot',
  'signal-generation',
  'update-stats'
);

DELETE FROM jobs.scheduled_jobs
WHERE job_id IN (
  'daily-scheduled-sync',
  'reference-portfolio-snapshot',
  'signal-generation',
  'update-stats'
);

DELETE FROM jobs.job_executions
WHERE job_id IN (
  'daily-scheduled-sync',
  'reference-portfolio-snapshot',
  'signal-generation',
  'update-stats'
);
