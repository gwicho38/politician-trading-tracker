-- QuiverQuant Validation System
-- Tracks validation results comparing our data against QuiverQuant

-- =============================================================================
-- Table: trade_validation_results
-- Stores the results of comparing each trade against QuiverQuant data
-- =============================================================================

CREATE TABLE IF NOT EXISTS trade_validation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to our trade (NULL if quiver_only)
    trading_disclosure_id UUID REFERENCES trading_disclosures(id) ON DELETE CASCADE,

    -- Raw QuiverQuant record for reference
    quiver_record JSONB,

    -- Match key used for comparison
    match_key TEXT,  -- e.g., "P000197|NVDA|2026-01-15|sale"

    -- Validation status
    validation_status TEXT NOT NULL CHECK (validation_status IN (
        'match',        -- All fields match within tolerance
        'mismatch',     -- Trade found but fields don't match
        'app_only',     -- Trade exists in app but not in QuiverQuant
        'quiver_only'   -- Trade exists in QuiverQuant but not in app
    )),

    -- Detailed field-by-field comparison results
    -- Format: {"field_name": {"app": "value", "quiver": "value", "severity": "critical|warning", "match": true|false}}
    field_mismatches JSONB DEFAULT '{}',

    -- Diagnosed root cause
    root_cause TEXT CHECK (root_cause IN (
        'name_normalization',
        'date_parse_error',
        'amount_parse_error',
        'transaction_type_mapping',
        'missing_in_source',
        'data_lag',
        'source_correction',
        'ticker_mismatch',
        'unknown',
        NULL  -- For matches
    )),

    -- Severity level (critical = must fix, warning = review)
    severity TEXT DEFAULT 'warning' CHECK (severity IN ('critical', 'warning', 'info')),

    -- Timestamps
    validated_at TIMESTAMPTZ DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- =============================================================================
-- Indexes for efficient querying
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_validation_status
    ON trade_validation_results(validation_status);

CREATE INDEX IF NOT EXISTS idx_validation_root_cause
    ON trade_validation_results(root_cause)
    WHERE root_cause IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_validation_severity
    ON trade_validation_results(severity);

CREATE INDEX IF NOT EXISTS idx_validation_disclosure
    ON trade_validation_results(trading_disclosure_id);

CREATE INDEX IF NOT EXISTS idx_validation_match_key
    ON trade_validation_results(match_key);

CREATE INDEX IF NOT EXISTS idx_validation_unresolved
    ON trade_validation_results(validation_status, resolved_at)
    WHERE resolved_at IS NULL AND validation_status != 'match';

CREATE INDEX IF NOT EXISTS idx_validation_date
    ON trade_validation_results(validated_at DESC);

-- =============================================================================
-- Add validation status to trading_disclosures
-- =============================================================================

ALTER TABLE trading_disclosures
ADD COLUMN IF NOT EXISTS quiver_validation_status TEXT DEFAULT 'pending'
    CHECK (quiver_validation_status IN ('pending', 'validated', 'mismatch', 'unmatched'));

ALTER TABLE trading_disclosures
ADD COLUMN IF NOT EXISTS quiver_validated_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_disclosure_quiver_validation
    ON trading_disclosures(quiver_validation_status);

-- =============================================================================
-- Trigger to update updated_at
-- =============================================================================

CREATE OR REPLACE FUNCTION update_validation_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_validation_updated_at ON trade_validation_results;
CREATE TRIGGER trigger_validation_updated_at
    BEFORE UPDATE ON trade_validation_results
    FOR EACH ROW
    EXECUTE FUNCTION update_validation_updated_at();

-- =============================================================================
-- View: validation_summary
-- Provides quick stats on validation status
-- =============================================================================

CREATE OR REPLACE VIEW validation_summary AS
SELECT
    validation_status,
    root_cause,
    severity,
    COUNT(*) as count,
    COUNT(*) FILTER (WHERE resolved_at IS NULL) as unresolved_count,
    MAX(validated_at) as last_validated
FROM trade_validation_results
GROUP BY validation_status, root_cause, severity
ORDER BY
    CASE validation_status
        WHEN 'mismatch' THEN 1
        WHEN 'quiver_only' THEN 2
        WHEN 'app_only' THEN 3
        ELSE 4
    END,
    CASE severity
        WHEN 'critical' THEN 1
        WHEN 'warning' THEN 2
        ELSE 3
    END;

-- =============================================================================
-- RLS Policies
-- =============================================================================

ALTER TABLE trade_validation_results ENABLE ROW LEVEL SECURITY;

-- Allow all for service role
CREATE POLICY "Service role full access on validation"
    ON trade_validation_results
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Allow read for authenticated users
CREATE POLICY "Authenticated read on validation"
    ON trade_validation_results
    FOR SELECT
    TO authenticated
    USING (true);

-- Allow read for anon (for dashboard stats)
CREATE POLICY "Anon read on validation"
    ON trade_validation_results
    FOR SELECT
    TO anon
    USING (true);

-- =============================================================================
-- Grant permissions
-- =============================================================================

GRANT ALL ON trade_validation_results TO service_role;
GRANT SELECT ON trade_validation_results TO authenticated;
GRANT SELECT ON trade_validation_results TO anon;
GRANT SELECT ON validation_summary TO authenticated;
GRANT SELECT ON validation_summary TO anon;

-- =============================================================================
-- Comments for documentation
-- =============================================================================

COMMENT ON TABLE trade_validation_results IS
    'Stores results of comparing trades against QuiverQuant API data';

COMMENT ON COLUMN trade_validation_results.validation_status IS
    'match=all fields match, mismatch=found but different, app_only/quiver_only=exists in one source only';

COMMENT ON COLUMN trade_validation_results.field_mismatches IS
    'JSON object with field-by-field comparison: {field: {app: val, quiver: val, severity: level, match: bool}}';

COMMENT ON COLUMN trade_validation_results.root_cause IS
    'Diagnosed reason for mismatch to help fix data quality issues';
