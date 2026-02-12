-- Reactivate all politicians regardless of disclosure count.
-- The frontend serves as a public outreach tool tracking both current and
-- historical politicians, so is_active should always be true.
--
-- Also updates the trigger to re-activate politicians when disclosures are added.

BEGIN;

-- =============================================================================
-- Step 1: Reactivate all politicians
-- =============================================================================
UPDATE politicians SET is_active = true WHERE is_active = false;

-- =============================================================================
-- Step 2: Update trigger to re-activate politicians when disclosures are added
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

  -- Recompute stats for the affected politician and ensure they are active
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
    ), 0),
    is_active = true
  WHERE id = affected_politician_id;

  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  ELSE
    RETURN NEW;
  END IF;
END;
$$ LANGUAGE plpgsql;

COMMIT;
