-- Migration: Create ml_retraining_stats table for batch retraining orchestration
-- Tracks data changes since last training and triggers retraining when threshold reached

-- Create the ml_retraining_stats table (singleton pattern)
CREATE TABLE IF NOT EXISTS public.ml_retraining_stats (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Tracking state
  last_training_at TIMESTAMPTZ,             -- When model was last trained
  last_check_at TIMESTAMPTZ,                -- When we last counted changes
  changes_since_training INTEGER DEFAULT 0, -- Running count (cached)

  -- Configuration (stored for runtime flexibility)
  threshold INTEGER DEFAULT 500,             -- Changes needed to trigger retrain
  check_interval_minutes INTEGER DEFAULT 60, -- How often to check

  -- Singleton pattern - ensures only one row exists
  singleton_key INTEGER UNIQUE DEFAULT 1 CHECK (singleton_key = 1),

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Initialize with single row, using last active model training time or fallback
INSERT INTO public.ml_retraining_stats (last_training_at, last_check_at)
SELECT
  COALESCE(
    (SELECT MAX(training_completed_at) FROM ml_models WHERE status = 'active'),
    NOW() - INTERVAL '1 year'
  ),
  NOW()
WHERE NOT EXISTS (SELECT 1 FROM public.ml_retraining_stats);

-- Create index for faster lookups (though singleton, good practice)
CREATE INDEX IF NOT EXISTS idx_ml_retraining_stats_singleton
  ON public.ml_retraining_stats(singleton_key);

-- Function to count disclosure changes since a given timestamp
-- Used by the batch retraining job to determine if threshold reached
CREATE OR REPLACE FUNCTION count_disclosure_changes_since(since_ts TIMESTAMPTZ)
RETURNS INTEGER AS $$
  SELECT COUNT(*)::INTEGER
  FROM trading_disclosures
  WHERE updated_at > since_ts
    AND status = 'active';
$$ LANGUAGE sql STABLE;

-- Function to get current retraining stats with live change count
-- Returns the stats row enriched with current change count
CREATE OR REPLACE FUNCTION get_retraining_stats()
RETURNS TABLE (
  last_training_at TIMESTAMPTZ,
  last_check_at TIMESTAMPTZ,
  threshold INTEGER,
  current_change_count INTEGER
) AS $$
  SELECT
    s.last_training_at,
    s.last_check_at,
    s.threshold,
    count_disclosure_changes_since(s.last_training_at) as current_change_count
  FROM ml_retraining_stats s
  WHERE s.singleton_key = 1;
$$ LANGUAGE sql STABLE;

-- Function to reset stats after training is triggered
-- Called by the Elixir job after successfully triggering training
CREATE OR REPLACE FUNCTION reset_retraining_stats(training_ts TIMESTAMPTZ)
RETURNS VOID AS $$
  UPDATE ml_retraining_stats
  SET
    last_training_at = training_ts,
    last_check_at = NOW(),
    changes_since_training = 0,
    updated_at = NOW()
  WHERE singleton_key = 1;
$$ LANGUAGE sql;

-- Function to update last check timestamp (called each hour)
CREATE OR REPLACE FUNCTION update_retraining_check()
RETURNS VOID AS $$
  UPDATE ml_retraining_stats
  SET
    last_check_at = NOW(),
    updated_at = NOW()
  WHERE singleton_key = 1;
$$ LANGUAGE sql;

-- Trigger to update updated_at on any change
CREATE OR REPLACE FUNCTION update_ml_retraining_stats_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_ml_retraining_stats_updated_at
  ON public.ml_retraining_stats;

CREATE TRIGGER trigger_update_ml_retraining_stats_updated_at
  BEFORE UPDATE ON public.ml_retraining_stats
  FOR EACH ROW
  EXECUTE FUNCTION update_ml_retraining_stats_updated_at();

-- Enable Row Level Security
ALTER TABLE public.ml_retraining_stats ENABLE ROW LEVEL SECURITY;

-- Service role has full access (for scheduler and admin)
DROP POLICY IF EXISTS "Service role has full access to retraining stats" ON public.ml_retraining_stats;
CREATE POLICY "Service role has full access to retraining stats"
  ON public.ml_retraining_stats
  FOR ALL
  USING (auth.role() = 'service_role');

-- Anon/authenticated can read (for monitoring dashboards)
DROP POLICY IF EXISTS "Public can read retraining stats" ON public.ml_retraining_stats;
CREATE POLICY "Public can read retraining stats"
  ON public.ml_retraining_stats
  FOR SELECT
  USING (true);

-- Add comments for documentation
COMMENT ON TABLE public.ml_retraining_stats IS
  'Singleton table tracking ML model retraining state. Used to trigger batch retraining when data changes exceed threshold.';

COMMENT ON COLUMN public.ml_retraining_stats.last_training_at IS
  'Timestamp of last successful model training. Changes are counted from this point.';

COMMENT ON COLUMN public.ml_retraining_stats.threshold IS
  'Number of disclosure changes required to trigger automatic retraining.';

COMMENT ON FUNCTION count_disclosure_changes_since IS
  'Counts trading disclosures updated since given timestamp. Used to check retraining threshold.';

COMMENT ON FUNCTION get_retraining_stats IS
  'Returns retraining stats with live change count. Called by Elixir scheduler job.';

COMMENT ON FUNCTION reset_retraining_stats IS
  'Resets stats after training triggered. Sets new baseline timestamp.';
