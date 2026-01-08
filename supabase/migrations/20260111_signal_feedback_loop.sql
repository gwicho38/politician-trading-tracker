-- Signal Feedback Loop Schema
-- Tracks trading outcomes and feature importance for model retraining
-- This closes the loop: signals → trades → outcomes → model improvement

-- ============================================================================
-- 1. Signal Outcomes - Links signals to actual trade outcomes
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.signal_outcomes (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- References
  signal_id UUID REFERENCES public.trading_signals(id) ON DELETE SET NULL,
  position_id UUID REFERENCES public.reference_portfolio_positions(id) ON DELETE SET NULL,

  -- Signal metadata at trade time
  ticker TEXT NOT NULL,
  signal_type TEXT NOT NULL,
  signal_confidence DECIMAL(5,4),

  -- Outcome classification
  outcome TEXT CHECK (outcome IN ('win', 'loss', 'breakeven', 'open')) DEFAULT 'open',

  -- Outcome metrics
  entry_price DECIMAL(12,4),
  exit_price DECIMAL(12,4),
  return_pct DECIMAL(8,4),
  return_dollars DECIMAL(15,2),
  holding_days INTEGER,
  exit_reason TEXT CHECK (exit_reason IN ('signal', 'stop_loss', 'take_profit', 'manual', 'timeout', NULL)),

  -- Features snapshot at signal generation (for correlation analysis)
  features JSONB NOT NULL DEFAULT '{}',
  -- Example: {
  --   "politician_count": 5,
  --   "buy_sell_ratio": 2.5,
  --   "bipartisan": true,
  --   "recent_activity_30d": 8,
  --   "net_volume": 500000,
  --   "party_alignment": 0.7
  -- }

  -- Model that generated this signal
  model_id UUID REFERENCES public.ml_models(id) ON DELETE SET NULL,
  model_version TEXT,
  ml_enhanced BOOLEAN DEFAULT false,

  -- Timestamps
  signal_date TIMESTAMPTZ,
  entry_date TIMESTAMPTZ,
  exit_date TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_signal_outcomes_signal ON public.signal_outcomes(signal_id);
CREATE INDEX IF NOT EXISTS idx_signal_outcomes_position ON public.signal_outcomes(position_id);
CREATE INDEX IF NOT EXISTS idx_signal_outcomes_outcome ON public.signal_outcomes(outcome);
CREATE INDEX IF NOT EXISTS idx_signal_outcomes_ticker ON public.signal_outcomes(ticker);
CREATE INDEX IF NOT EXISTS idx_signal_outcomes_model ON public.signal_outcomes(model_id);
CREATE INDEX IF NOT EXISTS idx_signal_outcomes_exit_date ON public.signal_outcomes(exit_date DESC);

-- ============================================================================
-- 2. Feature Importance History - Tracks feature correlations over time
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.feature_importance_history (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Analysis period
  analysis_date DATE NOT NULL,
  analysis_window_days INTEGER DEFAULT 90,

  -- Feature being analyzed
  feature_name TEXT NOT NULL,

  -- Correlation metrics
  correlation_with_return DECIMAL(6,4),  -- Pearson correlation
  correlation_p_value DECIMAL(8,6),      -- Statistical significance

  -- Split analysis (high vs low feature values)
  median_value DECIMAL(12,4),
  avg_return_when_high DECIMAL(8,4),     -- Return when feature > median
  avg_return_when_low DECIMAL(8,4),      -- Return when feature <= median
  lift_pct DECIMAL(8,4),                 -- Difference in returns

  -- Sample sizes
  sample_size_total INTEGER,
  sample_size_high INTEGER,
  sample_size_low INTEGER,

  -- Win rate analysis
  win_rate_when_high DECIMAL(5,4),
  win_rate_when_low DECIMAL(5,4),

  -- Recommendation
  feature_useful BOOLEAN,  -- Is this feature predictive?
  recommended_weight DECIMAL(5,4),  -- Suggested weight adjustment

  created_at TIMESTAMPTZ DEFAULT now()
);

-- Unique constraint: one analysis per feature per date
CREATE UNIQUE INDEX IF NOT EXISTS idx_feature_importance_unique
  ON public.feature_importance_history(analysis_date, feature_name);

CREATE INDEX IF NOT EXISTS idx_feature_importance_date
  ON public.feature_importance_history(analysis_date DESC);

-- ============================================================================
-- 3. Model Performance Tracking - Compare model versions over time
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.model_performance_history (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Model reference
  model_id UUID REFERENCES public.ml_models(id) ON DELETE CASCADE,
  model_version TEXT NOT NULL,

  -- Evaluation period
  evaluation_date DATE NOT NULL,
  evaluation_window_days INTEGER DEFAULT 30,

  -- Signal statistics
  total_signals_generated INTEGER,
  signals_traded INTEGER,
  signals_skipped INTEGER,

  -- Performance metrics
  win_rate DECIMAL(5,4),
  avg_return_pct DECIMAL(8,4),
  total_return_pct DECIMAL(10,4),
  sharpe_ratio DECIMAL(6,4),
  sortino_ratio DECIMAL(6,4),
  max_drawdown_pct DECIMAL(6,4),

  -- Confidence calibration (how accurate are confidence scores?)
  confidence_correlation DECIMAL(6,4),  -- Correlation: confidence vs return
  high_confidence_win_rate DECIMAL(5,4),  -- Win rate when confidence > 0.8
  low_confidence_win_rate DECIMAL(5,4),   -- Win rate when confidence < 0.7

  -- Feature weights at evaluation time
  feature_weights JSONB,

  -- Comparison to baseline
  baseline_return_pct DECIMAL(8,4),  -- S&P 500 or benchmark return
  alpha DECIMAL(8,4),  -- Excess return over baseline

  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_model_performance_model
  ON public.model_performance_history(model_id);
CREATE INDEX IF NOT EXISTS idx_model_performance_date
  ON public.model_performance_history(evaluation_date DESC);

-- ============================================================================
-- 4. Retraining Events - Track when and why models are retrained
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.model_retraining_events (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Models involved
  old_model_id UUID REFERENCES public.ml_models(id) ON DELETE SET NULL,
  new_model_id UUID REFERENCES public.ml_models(id) ON DELETE SET NULL,

  -- Trigger info
  trigger_type TEXT CHECK (trigger_type IN ('scheduled', 'performance_degradation', 'manual', 'feature_drift')),
  trigger_reason TEXT,

  -- Training data
  training_samples INTEGER,
  outcome_samples INTEGER,  -- How many had actual outcomes
  training_window_days INTEGER,

  -- Performance comparison
  old_model_metrics JSONB,
  new_model_metrics JSONB,
  improvement_pct DECIMAL(8,4),

  -- Deployment decision
  deployed BOOLEAN DEFAULT false,
  deployment_reason TEXT,

  -- Feature weight changes
  weight_changes JSONB,
  -- Example: {"bipartisan": {"old": 0.15, "new": 0.22, "change": 0.07}}

  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_retraining_events_date
  ON public.model_retraining_events(created_at DESC);

-- ============================================================================
-- 5. RLS Policies
-- ============================================================================
ALTER TABLE public.signal_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feature_importance_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.model_performance_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.model_retraining_events ENABLE ROW LEVEL SECURITY;

-- Public read access (transparency)
DROP POLICY IF EXISTS "public_read_signal_outcomes" ON public.signal_outcomes;
CREATE POLICY "public_read_signal_outcomes" ON public.signal_outcomes
  FOR SELECT USING (true);

DROP POLICY IF EXISTS "public_read_feature_importance" ON public.feature_importance_history;
CREATE POLICY "public_read_feature_importance" ON public.feature_importance_history
  FOR SELECT USING (true);

DROP POLICY IF EXISTS "public_read_model_performance" ON public.model_performance_history;
CREATE POLICY "public_read_model_performance" ON public.model_performance_history
  FOR SELECT USING (true);

DROP POLICY IF EXISTS "public_read_retraining_events" ON public.model_retraining_events;
CREATE POLICY "public_read_retraining_events" ON public.model_retraining_events
  FOR SELECT USING (true);

-- Service role write access
DROP POLICY IF EXISTS "service_write_signal_outcomes" ON public.signal_outcomes;
CREATE POLICY "service_write_signal_outcomes" ON public.signal_outcomes
  FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "service_write_feature_importance" ON public.feature_importance_history;
CREATE POLICY "service_write_feature_importance" ON public.feature_importance_history
  FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "service_write_model_performance" ON public.model_performance_history;
CREATE POLICY "service_write_model_performance" ON public.model_performance_history
  FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "service_write_retraining_events" ON public.model_retraining_events;
CREATE POLICY "service_write_retraining_events" ON public.model_retraining_events
  FOR ALL USING (auth.role() = 'service_role');

-- ============================================================================
-- 6. Helpful Views
-- ============================================================================

-- View: Recent feature importance summary
CREATE OR REPLACE VIEW public.feature_importance_latest AS
SELECT
  feature_name,
  correlation_with_return,
  lift_pct,
  win_rate_when_high,
  win_rate_when_low,
  sample_size_total,
  feature_useful,
  recommended_weight,
  analysis_date
FROM public.feature_importance_history
WHERE analysis_date = (SELECT MAX(analysis_date) FROM public.feature_importance_history)
ORDER BY ABS(correlation_with_return) DESC;

-- View: Model performance comparison
CREATE OR REPLACE VIEW public.model_performance_comparison AS
SELECT
  m.model_name,
  m.model_version,
  p.evaluation_date,
  p.win_rate,
  p.avg_return_pct,
  p.sharpe_ratio,
  p.alpha,
  p.signals_traded,
  p.high_confidence_win_rate
FROM public.model_performance_history p
JOIN public.ml_models m ON p.model_id = m.id
ORDER BY p.evaluation_date DESC, p.sharpe_ratio DESC;

-- View: Outcome summary by model
CREATE OR REPLACE VIEW public.outcome_summary_by_model AS
SELECT
  model_version,
  ml_enhanced,
  COUNT(*) as total_trades,
  COUNT(*) FILTER (WHERE outcome = 'win') as wins,
  COUNT(*) FILTER (WHERE outcome = 'loss') as losses,
  ROUND(AVG(return_pct)::numeric, 4) as avg_return_pct,
  ROUND((COUNT(*) FILTER (WHERE outcome = 'win')::decimal / NULLIF(COUNT(*) FILTER (WHERE outcome != 'open'), 0))::numeric, 4) as win_rate,
  ROUND(AVG(holding_days)::numeric, 1) as avg_holding_days
FROM public.signal_outcomes
WHERE outcome != 'open'
GROUP BY model_version, ml_enhanced
ORDER BY avg_return_pct DESC;

-- ============================================================================
-- 7. Updated At Trigger
-- ============================================================================
CREATE OR REPLACE FUNCTION public.update_signal_outcomes_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS signal_outcomes_updated_at ON public.signal_outcomes;
CREATE TRIGGER signal_outcomes_updated_at
  BEFORE UPDATE ON public.signal_outcomes
  FOR EACH ROW
  EXECUTE FUNCTION public.update_signal_outcomes_updated_at();
