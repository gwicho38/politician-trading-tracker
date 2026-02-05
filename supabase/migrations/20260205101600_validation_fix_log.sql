-- Validation Fix Log
-- Tracks all fixes applied to validation discrepancies for audit trail

-- =============================================================================
-- Table: validation_fix_log
-- Stores audit trail of all fix actions applied via admin dashboard
-- =============================================================================

CREATE TABLE IF NOT EXISTS validation_fix_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- References
    validation_result_id UUID REFERENCES trade_validation_results(id) ON DELETE SET NULL,
    trading_disclosure_id UUID REFERENCES trading_disclosures(id) ON DELETE SET NULL,

    -- Action details
    action_type TEXT NOT NULL CHECK (action_type IN (
        'field_update',      -- Single field updated to QQ value
        'accept_all_qq',     -- All mismatched fields updated to QQ values
        'manual_edit',       -- Manual value entered by admin
        'import_trade',      -- New trade imported from QuiverQuant
        'delete_trade',      -- Trade soft-deleted
        'mark_resolved'      -- Issue marked as resolved without data change
    )),

    -- Change details
    field_changed TEXT,      -- Which field was changed (null for bulk/resolve actions)
    old_value TEXT,          -- Previous value
    new_value TEXT,          -- New value

    -- Audit metadata
    performed_by TEXT DEFAULT 'admin',
    performed_at TIMESTAMPTZ DEFAULT now(),
    notes TEXT,

    -- Track if re-validation was triggered
    revalidated BOOLEAN DEFAULT false,
    revalidation_status TEXT  -- Result of re-validation: 'match', 'mismatch', etc.
);

-- =============================================================================
-- Indexes
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_fix_log_validation
    ON validation_fix_log(validation_result_id);

CREATE INDEX IF NOT EXISTS idx_fix_log_disclosure
    ON validation_fix_log(trading_disclosure_id);

CREATE INDEX IF NOT EXISTS idx_fix_log_date
    ON validation_fix_log(performed_at DESC);

CREATE INDEX IF NOT EXISTS idx_fix_log_action_type
    ON validation_fix_log(action_type);

-- =============================================================================
-- Add soft delete column to trading_disclosures
-- =============================================================================

ALTER TABLE trading_disclosures
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_disclosure_deleted
    ON trading_disclosures(deleted_at)
    WHERE deleted_at IS NOT NULL;

-- =============================================================================
-- RLS Policies for validation_fix_log
-- =============================================================================

ALTER TABLE validation_fix_log ENABLE ROW LEVEL SECURITY;

-- Service role has full access (drop first for idempotency)
DROP POLICY IF EXISTS "Service role full access on fix_log" ON validation_fix_log;
CREATE POLICY "Service role full access on fix_log"
    ON validation_fix_log
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Authenticated users can read (drop first for idempotency)
DROP POLICY IF EXISTS "Authenticated read on fix_log" ON validation_fix_log;
CREATE POLICY "Authenticated read on fix_log"
    ON validation_fix_log
    FOR SELECT
    TO authenticated
    USING (true);

-- =============================================================================
-- Grants
-- =============================================================================

GRANT ALL ON validation_fix_log TO service_role;
GRANT SELECT ON validation_fix_log TO authenticated;

-- =============================================================================
-- View: recent_fixes
-- Quick view of recent fix activity
-- =============================================================================

CREATE OR REPLACE VIEW recent_fixes AS
SELECT
    f.id,
    f.action_type,
    f.field_changed,
    f.old_value,
    f.new_value,
    f.performed_at,
    f.notes,
    v.validation_status,
    v.match_key,
    f.revalidation_status
FROM validation_fix_log f
LEFT JOIN trade_validation_results v ON f.validation_result_id = v.id
ORDER BY f.performed_at DESC
LIMIT 100;

GRANT SELECT ON recent_fixes TO service_role;
GRANT SELECT ON recent_fixes TO authenticated;

-- =============================================================================
-- Comments
-- =============================================================================

COMMENT ON TABLE validation_fix_log IS
    'Audit trail of all fixes applied to validation discrepancies via admin dashboard';

COMMENT ON COLUMN validation_fix_log.action_type IS
    'Type of fix: field_update, accept_all_qq, manual_edit, import_trade, delete_trade, mark_resolved';

COMMENT ON COLUMN validation_fix_log.revalidation_status IS
    'Result after re-validating the fixed record against QuiverQuant';
