-- Migration: Add cc_evaluated_at to ml_training_jobs for async champion/challenger tracking
--
-- The ml-training edge function previously polled for training completion inline,
-- causing 504 timeouts. Now:
--   1. `train` action returns 202 immediately after kicking off ETL training
--   2. `evaluate-training` action runs the C/C gate separately for completed jobs
--
-- cc_evaluated_at = NULL means the job has completed but the C/C gate hasn't run yet.

ALTER TABLE public.ml_training_jobs
  ADD COLUMN IF NOT EXISTS cc_evaluated_at TIMESTAMPTZ;

-- Partial index for fast lookup of "completed but not yet C/C-evaluated" jobs
CREATE INDEX IF NOT EXISTS idx_ml_training_jobs_pending_cc
  ON public.ml_training_jobs(completed_at DESC)
  WHERE status = 'completed' AND cc_evaluated_at IS NULL;
