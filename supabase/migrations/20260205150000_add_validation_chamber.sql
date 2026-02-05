-- Add chamber column to trade_validation_results for filtering House vs Senate
-- This allows admins to focus on validating one chamber at a time

-- =============================================================================
-- Add chamber column
-- =============================================================================

ALTER TABLE trade_validation_results
ADD COLUMN IF NOT EXISTS chamber TEXT CHECK (chamber IN ('house', 'senate', 'unknown'));

-- =============================================================================
-- Create index for chamber filtering
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_validation_chamber
    ON trade_validation_results(chamber);

-- =============================================================================
-- Backfill chamber from politicians table (for app_only and mismatch records)
-- =============================================================================

UPDATE trade_validation_results v
SET chamber = LOWER(p.chamber)
FROM trading_disclosures td
JOIN politicians p ON td.politician_id = p.id
WHERE v.trading_disclosure_id = td.id
  AND v.chamber IS NULL
  AND p.chamber IS NOT NULL;

-- =============================================================================
-- Backfill chamber from quiver_record JSONB (for quiver_only records)
-- QuiverQuant uses "House" field with values "Representatives" or "Senate"
-- =============================================================================

UPDATE trade_validation_results v
SET chamber = CASE
    WHEN LOWER(v.quiver_record->>'House') = 'representatives' THEN 'house'
    WHEN LOWER(v.quiver_record->>'House') = 'senate' THEN 'senate'
    ELSE 'unknown'
END
WHERE v.validation_status = 'quiver_only'
  AND v.quiver_record IS NOT NULL
  AND v.quiver_record->>'House' IS NOT NULL
  AND v.chamber IS NULL;

-- Set unknown for any remaining records
UPDATE trade_validation_results
SET chamber = 'unknown'
WHERE chamber IS NULL;

-- =============================================================================
-- Comment
-- =============================================================================

COMMENT ON COLUMN trade_validation_results.chamber IS
    'Chamber (house/senate) for filtering validation by legislative body';
