-- Fix politician stats: recompute total_trades/total_volume from trading_disclosures
-- and deactivate orphan politician records with zero disclosures.
--
-- Problem: total_trades and total_volume columns default to 0 and are never updated.
-- ~3,200 politicians show $0/0 trades including ~2,000 phantom non-politician records
-- created by legacy ETL batches (Dec 1 & Dec 10, 2025).
--
-- This migration:
-- 1. Backfills total_trades and total_volume from actual trading_disclosures
-- 2. Deactivates politicians with zero linked disclosures
-- 3. Creates a trigger to keep stats updated on INSERT/UPDATE/DELETE

BEGIN;

-- =============================================================================
-- Step 1: Backfill total_trades and total_volume from trading_disclosures
-- =============================================================================

-- Reset all to 0 first, then update from actual data
UPDATE politicians SET total_trades = 0, total_volume = 0;

UPDATE politicians p
SET
  total_trades = stats.trade_count,
  total_volume = stats.volume
FROM (
  SELECT
    politician_id,
    COUNT(*) as trade_count,
    SUM((COALESCE(amount_range_min, 0) + COALESCE(amount_range_max, 0)) / 2) as volume
  FROM trading_disclosures
  WHERE status = 'active'
    AND deleted_at IS NULL
  GROUP BY politician_id
) stats
WHERE p.id = stats.politician_id;

-- =============================================================================
-- Step 2: Deactivate politicians with zero disclosures
-- =============================================================================

-- Deactivate any politician that has no trading_disclosures linked to them.
-- This removes phantom records from the frontend (which filters is_active=true)
-- without breaking foreign keys.
UPDATE politicians
SET is_active = false
WHERE id NOT IN (
  SELECT DISTINCT politician_id
  FROM trading_disclosures
  WHERE status = 'active'
    AND deleted_at IS NULL
    AND politician_id IS NOT NULL
);

-- =============================================================================
-- Step 3: Create trigger function to keep stats updated
-- =============================================================================

CREATE OR REPLACE FUNCTION update_politician_stats()
RETURNS TRIGGER AS $$
DECLARE
  affected_politician_id UUID;
BEGIN
  -- Determine which politician_id to update
  IF TG_OP = 'DELETE' THEN
    affected_politician_id := OLD.politician_id;
  ELSIF TG_OP = 'UPDATE' THEN
    -- If politician_id changed, update both old and new
    IF OLD.politician_id IS DISTINCT FROM NEW.politician_id THEN
      -- Recompute old politician
      UPDATE politicians SET
        total_trades = COALESCE((
          SELECT COUNT(*) FROM trading_disclosures
          WHERE politician_id = OLD.politician_id
            AND status = 'active' AND deleted_at IS NULL
        ), 0),
        total_volume = COALESCE((
          SELECT SUM((COALESCE(amount_range_min, 0) + COALESCE(amount_range_max, 0)) / 2)
          FROM trading_disclosures
          WHERE politician_id = OLD.politician_id
            AND status = 'active' AND deleted_at IS NULL
        ), 0)
      WHERE id = OLD.politician_id;
    END IF;
    affected_politician_id := NEW.politician_id;
  ELSE
    affected_politician_id := NEW.politician_id;
  END IF;

  -- Skip if no politician_id
  IF affected_politician_id IS NULL THEN
    IF TG_OP = 'DELETE' THEN
      RETURN OLD;
    ELSE
      RETURN NEW;
    END IF;
  END IF;

  -- Recompute stats for the affected politician
  UPDATE politicians SET
    total_trades = COALESCE((
      SELECT COUNT(*) FROM trading_disclosures
      WHERE politician_id = affected_politician_id
        AND status = 'active' AND deleted_at IS NULL
    ), 0),
    total_volume = COALESCE((
      SELECT SUM((COALESCE(amount_range_min, 0) + COALESCE(amount_range_max, 0)) / 2)
      FROM trading_disclosures
      WHERE politician_id = affected_politician_id
        AND status = 'active' AND deleted_at IS NULL
    ), 0)
  WHERE id = affected_politician_id;

  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  ELSE
    RETURN NEW;
  END IF;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- Step 4: Create trigger on trading_disclosures
-- =============================================================================

-- Drop if exists (idempotent)
DROP TRIGGER IF EXISTS trg_update_politician_stats ON trading_disclosures;

CREATE TRIGGER trg_update_politician_stats
  AFTER INSERT OR UPDATE OR DELETE ON trading_disclosures
  FOR EACH ROW
  EXECUTE FUNCTION update_politician_stats();

COMMENT ON FUNCTION update_politician_stats() IS
  'Trigger function: recomputes total_trades and total_volume on politicians table when trading_disclosures change';

COMMIT;
