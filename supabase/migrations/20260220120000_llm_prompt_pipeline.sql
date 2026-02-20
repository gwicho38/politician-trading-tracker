-- ============================================================================
-- LLM Prompt Pipeline Database Schema
-- ============================================================================
-- Creates the tables required for the LLM-powered anomaly detection and
-- prompt feedback pipeline:
--   1. llm_audit_trail       - Audit log for all LLM API calls
--   2. llm_anomaly_signals   - Detected anomalies from LLM analysis
--   3. llm_prompt_recommendations - Self-improvement feedback from LLM
--   4. trading_disclosures columns - LLM validation status tracking
-- ============================================================================


-- ============================================================================
-- 1. LLM AUDIT TRAIL (Immutable log of every LLM API call)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.llm_audit_trail (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT now(),
  service_name TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  prompt_hash TEXT NOT NULL,
  model_used TEXT NOT NULL,
  input_tokens INTEGER,
  output_tokens INTEGER,
  latency_ms INTEGER,
  request_context JSONB,
  raw_response TEXT,
  parsed_output JSONB,
  parse_success BOOLEAN DEFAULT true,
  error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_llm_audit_service
  ON public.llm_audit_trail(service_name);
CREATE INDEX IF NOT EXISTS idx_llm_audit_created
  ON public.llm_audit_trail(created_at);


-- ============================================================================
-- 2. LLM ANOMALY SIGNALS (Detected anomalies from LLM analysis)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.llm_anomaly_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT now(),
  signal_id TEXT UNIQUE NOT NULL,
  filer TEXT NOT NULL,
  classification TEXT NOT NULL,
  severity TEXT NOT NULL,
  confidence INTEGER NOT NULL,
  trades_involved JSONB NOT NULL,
  legislative_context JSONB,
  statistical_evidence JSONB,
  reasoning TEXT,
  trading_signal JSONB,
  self_verification_notes TEXT,
  analysis_window_start DATE,
  analysis_window_end DATE,
  audit_trail_id UUID REFERENCES public.llm_audit_trail(id)
);

CREATE INDEX IF NOT EXISTS idx_anomaly_signals_filer
  ON public.llm_anomaly_signals(filer);
CREATE INDEX IF NOT EXISTS idx_anomaly_signals_created
  ON public.llm_anomaly_signals(created_at);
CREATE INDEX IF NOT EXISTS idx_anomaly_signals_severity
  ON public.llm_anomaly_signals(severity);


-- ============================================================================
-- 3. LLM PROMPT RECOMMENDATIONS (Self-improvement feedback loop)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.llm_prompt_recommendations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT now(),
  feedback_id TEXT UNIQUE NOT NULL,
  analysis_period_start DATE,
  analysis_period_end DATE,
  scorecard JSONB NOT NULL,
  failure_patterns JSONB,
  prompt_recommendations JSONB,
  threshold_adjustments JSONB,
  data_quality_feedback JSONB,
  meta_confidence INTEGER,
  status TEXT DEFAULT 'pending',
  reviewed_by TEXT,
  reviewed_at TIMESTAMPTZ,
  audit_trail_id UUID REFERENCES public.llm_audit_trail(id)
);


-- ============================================================================
-- 4. ENHANCE trading_disclosures TABLE
-- ============================================================================
-- Add LLM validation status tracking columns
ALTER TABLE public.trading_disclosures
  ADD COLUMN IF NOT EXISTS llm_validation_status TEXT DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS llm_validated_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_disclosures_llm_status
  ON public.trading_disclosures(llm_validation_status);


-- ============================================================================
-- 5. ROW LEVEL SECURITY POLICIES
-- ============================================================================

-- Enable RLS on all new tables
ALTER TABLE public.llm_audit_trail ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.llm_anomaly_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.llm_prompt_recommendations ENABLE ROW LEVEL SECURITY;

-- Service role full access on all 3 tables
CREATE POLICY "llm_audit_trail_service_all" ON public.llm_audit_trail
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "llm_anomaly_signals_service_all" ON public.llm_anomaly_signals
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "llm_prompt_recommendations_service_all" ON public.llm_prompt_recommendations
  FOR ALL USING (auth.role() = 'service_role');

-- Anon read access on anomaly signals and prompt recommendations
CREATE POLICY "llm_anomaly_signals_anon_read" ON public.llm_anomaly_signals
  FOR SELECT USING (true);

CREATE POLICY "llm_prompt_recommendations_anon_read" ON public.llm_prompt_recommendations
  FOR SELECT USING (true);


-- ============================================================================
-- 6. COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE public.llm_audit_trail IS
  'Audit log for every LLM API call: prompt version, tokens, latency, parsed output';

COMMENT ON TABLE public.llm_anomaly_signals IS
  'Anomalies detected by LLM analysis of politician trading disclosures';

COMMENT ON TABLE public.llm_prompt_recommendations IS
  'Self-improvement feedback loop: scorecards, failure patterns, prompt recommendations';

COMMENT ON COLUMN public.trading_disclosures.llm_validation_status IS
  'LLM validation status for this disclosure: pending, validated, flagged, error';

COMMENT ON COLUMN public.trading_disclosures.llm_validated_at IS
  'Timestamp when LLM validation was last performed on this disclosure';
