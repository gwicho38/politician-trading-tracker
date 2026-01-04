-- Data Quality Testing System Schema
-- Implements tiered quality checks with email alerting and auto-correction

-- ============================================================================
-- 1. DATA QUALITY CHECKS REGISTRY
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.data_quality_checks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  check_id TEXT UNIQUE NOT NULL,
  check_name TEXT NOT NULL,
  check_tier INTEGER NOT NULL CHECK (check_tier IN (1, 2, 3)),
  check_category TEXT NOT NULL CHECK (
    check_category IN ('schema', 'freshness', 'integrity', 'reconciliation',
                       'anomaly', 'ticker', 'accuracy', 'signal', 'user_report')
  ),
  description TEXT,
  query_template TEXT,
  threshold_config JSONB DEFAULT '{}',
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed default checks
INSERT INTO public.data_quality_checks (check_id, check_name, check_tier, check_category, description, is_active) VALUES
  ('schema-required-fields', 'Required Fields Check', 1, 'schema', 'Validates required fields are present', true),
  ('schema-data-types', 'Data Type Validation', 1, 'schema', 'Validates data types match expected formats', true),
  ('freshness-etl-jobs', 'ETL Job Freshness', 1, 'freshness', 'Checks ETL jobs are running on schedule', true),
  ('integrity-orphaned-records', 'Orphaned Records Check', 1, 'integrity', 'Finds records with missing foreign keys', true),
  ('integrity-constraints', 'Constraint Violations', 1, 'integrity', 'Checks for business rule violations', true),
  ('reconciliation-cross-source', 'Cross-Source Reconciliation', 2, 'reconciliation', 'Compares same trades across sources', true),
  ('anomaly-statistical', 'Statistical Anomaly Detection', 2, 'anomaly', 'Detects unusual patterns using z-scores', true),
  ('ticker-validation', 'Ticker Validation', 2, 'ticker', 'Validates tickers against exchange data', true),
  ('accuracy-source-audit', 'Source Accuracy Audit', 3, 'accuracy', 'Re-fetches and compares sample records', true),
  ('signal-backtesting', 'Signal Backtesting', 3, 'signal', 'Compares predictions vs actual returns', true),
  ('user-reports-triage', 'User Report Triage', 3, 'user_report', 'Processes user-submitted error reports', true)
ON CONFLICT (check_id) DO NOTHING;

-- ============================================================================
-- 2. DATA QUALITY RESULTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.data_quality_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  check_id TEXT NOT NULL REFERENCES public.data_quality_checks(check_id) ON DELETE CASCADE,
  execution_id UUID,

  started_at TIMESTAMPTZ NOT NULL,
  completed_at TIMESTAMPTZ,
  duration_ms INTEGER,

  status TEXT NOT NULL CHECK (status IN ('running', 'passed', 'warning', 'failed', 'error')),
  records_checked INTEGER DEFAULT 0,
  issues_found INTEGER DEFAULT 0,

  issue_summary JSONB DEFAULT '{}',
  summary TEXT,
  check_config JSONB DEFAULT '{}',

  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dq_results_check_id ON public.data_quality_results(check_id);
CREATE INDEX IF NOT EXISTS idx_dq_results_status ON public.data_quality_results(status);
CREATE INDEX IF NOT EXISTS idx_dq_results_created ON public.data_quality_results(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_dq_results_started ON public.data_quality_results(started_at DESC);

-- ============================================================================
-- 3. DATA QUALITY ISSUES
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.data_quality_issues (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  result_id UUID REFERENCES public.data_quality_results(id) ON DELETE CASCADE,

  severity TEXT NOT NULL CHECK (severity IN ('critical', 'warning', 'info')),
  issue_type TEXT NOT NULL,

  table_name TEXT NOT NULL,
  record_id UUID,
  field_name TEXT,

  expected_value TEXT,
  actual_value TEXT,
  description TEXT NOT NULL,

  status TEXT DEFAULT 'open' CHECK (status IN ('open', 'acknowledged', 'auto_fixed', 'manually_fixed', 'ignored')),
  resolved_at TIMESTAMPTZ,
  resolved_by TEXT,
  resolution_notes TEXT,

  correction_id UUID,

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dq_issues_result ON public.data_quality_issues(result_id);
CREATE INDEX IF NOT EXISTS idx_dq_issues_severity ON public.data_quality_issues(severity);
CREATE INDEX IF NOT EXISTS idx_dq_issues_status ON public.data_quality_issues(status);
CREATE INDEX IF NOT EXISTS idx_dq_issues_type ON public.data_quality_issues(issue_type);
CREATE INDEX IF NOT EXISTS idx_dq_issues_table_record ON public.data_quality_issues(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_dq_issues_created ON public.data_quality_issues(created_at DESC);

-- ============================================================================
-- 4. DATA QUALITY CORRECTIONS (Auto-fix Audit Trail)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.data_quality_corrections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id UUID REFERENCES public.data_quality_issues(id) ON DELETE SET NULL,

  table_name TEXT NOT NULL,
  record_id UUID NOT NULL,
  field_name TEXT NOT NULL,

  correction_type TEXT NOT NULL CHECK (
    correction_type IN ('date_format', 'ticker_cleanup', 'duplicate_merge',
                        'value_range', 'politician_match', 'source_reconcile', 'other')
  ),
  old_value TEXT,
  new_value TEXT,

  corrected_by TEXT NOT NULL DEFAULT 'auto',
  confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
  approved_by UUID,
  approved_at TIMESTAMPTZ,

  can_rollback BOOLEAN DEFAULT true,
  rolled_back BOOLEAN DEFAULT false,
  rolled_back_at TIMESTAMPTZ,
  rollback_reason TEXT,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dq_corrections_table_record ON public.data_quality_corrections(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_dq_corrections_type ON public.data_quality_corrections(correction_type);
CREATE INDEX IF NOT EXISTS idx_dq_corrections_created ON public.data_quality_corrections(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_dq_corrections_issue ON public.data_quality_corrections(issue_id);

-- Add foreign key back to issues table (if not exists)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'fk_dq_issues_correction'
      AND table_name = 'data_quality_issues'
  ) THEN
    ALTER TABLE public.data_quality_issues
      ADD CONSTRAINT fk_dq_issues_correction
      FOREIGN KEY (correction_id) REFERENCES public.data_quality_corrections(id) ON DELETE SET NULL;
  END IF;
END $$;

-- ============================================================================
-- 5. DATA QUALITY QUARANTINE
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.data_quality_quarantine (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  table_name TEXT NOT NULL,
  original_record_id UUID,

  quarantine_reason TEXT NOT NULL,
  issue_ids UUID[] DEFAULT '{}',

  original_data JSONB NOT NULL,
  suggested_corrections JSONB DEFAULT '{}',

  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'merged')),
  reviewed_by UUID,
  reviewed_at TIMESTAMPTZ,
  review_notes TEXT,

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dq_quarantine_status ON public.data_quality_quarantine(status);
CREATE INDEX IF NOT EXISTS idx_dq_quarantine_table ON public.data_quality_quarantine(table_name);
CREATE INDEX IF NOT EXISTS idx_dq_quarantine_created ON public.data_quality_quarantine(created_at DESC);

-- ============================================================================
-- 6. EMAIL ALERT CONFIGURATION
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.email_alert_config (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_level TEXT NOT NULL CHECK (alert_level IN ('critical', 'warning', 'info')),

  recipients TEXT[] NOT NULL,

  delivery_mode TEXT NOT NULL CHECK (delivery_mode IN ('immediate', 'daily_digest', 'weekly_summary')),
  digest_time TIME DEFAULT '08:00:00',
  digest_day INTEGER CHECK (digest_day >= 0 AND digest_day <= 6),

  check_categories TEXT[],
  min_issues INTEGER DEFAULT 1,

  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed default alert configurations
INSERT INTO public.email_alert_config (alert_level, recipients, delivery_mode, check_categories, is_active) VALUES
  ('critical', ARRAY['admin@politiciantrading.app'], 'immediate', NULL, true),
  ('warning', ARRAY['admin@politiciantrading.app'], 'daily_digest', NULL, true),
  ('info', ARRAY['admin@politiciantrading.app'], 'weekly_summary', NULL, true)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 7. EMAIL ALERT LOG
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.email_alert_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  config_id UUID REFERENCES public.email_alert_config(id) ON DELETE SET NULL,

  subject TEXT NOT NULL,
  recipients TEXT[] NOT NULL,
  body_preview TEXT,

  status TEXT NOT NULL CHECK (status IN ('pending', 'sent', 'failed')),
  sent_at TIMESTAMPTZ,
  error_message TEXT,

  result_ids UUID[],
  issue_count INTEGER DEFAULT 0,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_alert_log_status ON public.email_alert_log(status);
CREATE INDEX IF NOT EXISTS idx_email_alert_log_created ON public.email_alert_log(created_at DESC);

-- ============================================================================
-- 8. DATA QUALITY METRICS (Aggregated View)
-- ============================================================================

CREATE OR REPLACE VIEW public.data_quality_metrics AS
SELECT
  DATE(r.started_at) as check_date,
  c.check_tier,
  c.check_category,
  COUNT(*) as total_checks,
  SUM(CASE WHEN r.status = 'passed' THEN 1 ELSE 0 END) as passed_checks,
  SUM(CASE WHEN r.status = 'warning' THEN 1 ELSE 0 END) as warning_checks,
  SUM(CASE WHEN r.status = 'failed' THEN 1 ELSE 0 END) as failed_checks,
  SUM(r.issues_found) as total_issues,
  AVG(r.duration_ms) as avg_duration_ms
FROM public.data_quality_results r
JOIN public.data_quality_checks c ON r.check_id = c.check_id
WHERE r.started_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(r.started_at), c.check_tier, c.check_category
ORDER BY check_date DESC, c.check_tier;

-- ============================================================================
-- 9. HELPER FUNCTIONS
-- ============================================================================

-- Function to get open issues count by severity
CREATE OR REPLACE FUNCTION get_open_issues_summary()
RETURNS TABLE (
  severity TEXT,
  count BIGINT
) AS $$
  SELECT
    severity,
    COUNT(*) as count
  FROM public.data_quality_issues
  WHERE status = 'open'
  GROUP BY severity
  ORDER BY
    CASE severity
      WHEN 'critical' THEN 1
      WHEN 'warning' THEN 2
      ELSE 3
    END;
$$ LANGUAGE sql STABLE;

-- Function to record a quality check result
CREATE OR REPLACE FUNCTION record_quality_check(
  p_check_id TEXT,
  p_status TEXT,
  p_records_checked INTEGER,
  p_issues_found INTEGER,
  p_summary TEXT,
  p_duration_ms INTEGER
)
RETURNS UUID AS $$
DECLARE
  v_result_id UUID;
BEGIN
  INSERT INTO public.data_quality_results (
    check_id, started_at, completed_at, status,
    records_checked, issues_found, summary, duration_ms
  ) VALUES (
    p_check_id, NOW() - (p_duration_ms || ' milliseconds')::INTERVAL, NOW(), p_status,
    p_records_checked, p_issues_found, p_summary, p_duration_ms
  )
  RETURNING id INTO v_result_id;

  RETURN v_result_id;
END;
$$ LANGUAGE plpgsql;

-- Function to record an issue
CREATE OR REPLACE FUNCTION record_quality_issue(
  p_result_id UUID,
  p_severity TEXT,
  p_issue_type TEXT,
  p_table_name TEXT,
  p_record_id UUID,
  p_field_name TEXT,
  p_expected TEXT,
  p_actual TEXT,
  p_description TEXT
)
RETURNS UUID AS $$
DECLARE
  v_issue_id UUID;
BEGIN
  INSERT INTO public.data_quality_issues (
    result_id, severity, issue_type, table_name, record_id,
    field_name, expected_value, actual_value, description
  ) VALUES (
    p_result_id, p_severity, p_issue_type, p_table_name, p_record_id,
    p_field_name, p_expected, p_actual, p_description
  )
  RETURNING id INTO v_issue_id;

  RETURN v_issue_id;
END;
$$ LANGUAGE plpgsql;

-- Function to record a correction
CREATE OR REPLACE FUNCTION record_correction(
  p_issue_id UUID,
  p_table_name TEXT,
  p_record_id UUID,
  p_field_name TEXT,
  p_correction_type TEXT,
  p_old_value TEXT,
  p_new_value TEXT,
  p_confidence DECIMAL
)
RETURNS UUID AS $$
DECLARE
  v_correction_id UUID;
BEGIN
  INSERT INTO public.data_quality_corrections (
    issue_id, table_name, record_id, field_name,
    correction_type, old_value, new_value, confidence_score
  ) VALUES (
    p_issue_id, p_table_name, p_record_id, p_field_name,
    p_correction_type, p_old_value, p_new_value, p_confidence
  )
  RETURNING id INTO v_correction_id;

  -- Update issue status
  IF p_issue_id IS NOT NULL THEN
    UPDATE public.data_quality_issues
    SET status = 'auto_fixed', correction_id = v_correction_id, resolved_at = NOW(), resolved_by = 'auto'
    WHERE id = p_issue_id;
  END IF;

  RETURN v_correction_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get recent check results
CREATE OR REPLACE FUNCTION get_recent_check_results(p_limit INTEGER DEFAULT 50)
RETURNS TABLE (
  id UUID,
  check_id TEXT,
  check_name TEXT,
  check_tier INTEGER,
  status TEXT,
  issues_found INTEGER,
  started_at TIMESTAMPTZ,
  duration_ms INTEGER,
  summary TEXT
) AS $$
  SELECT
    r.id,
    r.check_id,
    c.check_name,
    c.check_tier,
    r.status,
    r.issues_found,
    r.started_at,
    r.duration_ms,
    r.summary
  FROM public.data_quality_results r
  JOIN public.data_quality_checks c ON r.check_id = c.check_id
  ORDER BY r.started_at DESC
  LIMIT p_limit;
$$ LANGUAGE sql STABLE;

-- ============================================================================
-- 10. RLS POLICIES
-- ============================================================================

ALTER TABLE public.data_quality_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.data_quality_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.data_quality_issues ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.data_quality_corrections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.data_quality_quarantine ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.email_alert_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.email_alert_log ENABLE ROW LEVEL SECURITY;

-- Service role has full access (drop first to make idempotent)
DROP POLICY IF EXISTS "Service role full access" ON public.data_quality_checks;
DROP POLICY IF EXISTS "Service role full access" ON public.data_quality_results;
DROP POLICY IF EXISTS "Service role full access" ON public.data_quality_issues;
DROP POLICY IF EXISTS "Service role full access" ON public.data_quality_corrections;
DROP POLICY IF EXISTS "Service role full access" ON public.data_quality_quarantine;
DROP POLICY IF EXISTS "Service role full access" ON public.email_alert_config;
DROP POLICY IF EXISTS "Service role full access" ON public.email_alert_log;

CREATE POLICY "Service role full access" ON public.data_quality_checks FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON public.data_quality_results FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON public.data_quality_issues FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON public.data_quality_corrections FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON public.data_quality_quarantine FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON public.email_alert_config FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON public.email_alert_log FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Authenticated users can read (drop first to make idempotent)
DROP POLICY IF EXISTS "Authenticated read" ON public.data_quality_checks;
DROP POLICY IF EXISTS "Authenticated read" ON public.data_quality_results;
DROP POLICY IF EXISTS "Authenticated read" ON public.data_quality_issues;
DROP POLICY IF EXISTS "Authenticated read" ON public.data_quality_corrections;
DROP POLICY IF EXISTS "Authenticated read" ON public.data_quality_quarantine;

CREATE POLICY "Authenticated read" ON public.data_quality_checks FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated read" ON public.data_quality_results FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated read" ON public.data_quality_issues FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated read" ON public.data_quality_corrections FOR SELECT TO authenticated USING (true);
CREATE POLICY "Authenticated read" ON public.data_quality_quarantine FOR SELECT TO authenticated USING (true);

-- ============================================================================
-- 11. TRIGGERS
-- ============================================================================

-- Update updated_at on data_quality_issues
CREATE OR REPLACE FUNCTION update_dq_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_dq_issues_updated_at ON public.data_quality_issues;
CREATE TRIGGER update_dq_issues_updated_at
  BEFORE UPDATE ON public.data_quality_issues
  FOR EACH ROW EXECUTE FUNCTION update_dq_updated_at();

DROP TRIGGER IF EXISTS update_dq_quarantine_updated_at ON public.data_quality_quarantine;
CREATE TRIGGER update_dq_quarantine_updated_at
  BEFORE UPDATE ON public.data_quality_quarantine
  FOR EACH ROW EXECUTE FUNCTION update_dq_updated_at();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE public.data_quality_checks IS 'Registry of all data quality checks with tier and category';
COMMENT ON TABLE public.data_quality_results IS 'Results from each quality check execution';
COMMENT ON TABLE public.data_quality_issues IS 'Individual data quality issues found by checks';
COMMENT ON TABLE public.data_quality_corrections IS 'Audit trail of auto-corrections with rollback support';
COMMENT ON TABLE public.data_quality_quarantine IS 'Records that cannot be auto-fixed and need manual review';
COMMENT ON TABLE public.email_alert_config IS 'Configuration for email alerts by severity level';
COMMENT ON TABLE public.email_alert_log IS 'Log of sent email alerts';
