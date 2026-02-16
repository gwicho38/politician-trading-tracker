-- Add covering index on politicians(role, id) to speed up PostgREST joins
-- filtered by role. This allows index-only scans when finding all politician
-- IDs for a given role (e.g. 'MEP', 'Senator', 'Representative').
CREATE INDEX IF NOT EXISTS idx_politicians_role_id
  ON politicians(role, id);

-- Update table statistics for optimal query planning
ANALYZE politicians;
ANALYZE trading_disclosures;
