-- Fix 500 errors on trading_disclosures queries that filter by politician attributes
-- (e.g., chamber/role, party) via PostgREST inner joins.
--
-- Root cause: No index on trading_disclosures.politician_id means every inner join
-- with politicians requires a sequential scan of 125K+ rows. Combined with
-- the anon role's statement timeout, this causes consistent 500 errors.

-- Step 1: Add index on the foreign key used for ALL politician joins
CREATE INDEX IF NOT EXISTS idx_disclosures_politician_id
  ON trading_disclosures(politician_id);

-- Step 2: Compound index for the most common filtered join pattern:
-- WHERE status='active' joined on politician_id, ordered by disclosure_date
CREATE INDEX IF NOT EXISTS idx_disclosures_status_politician_date
  ON trading_disclosures(status, politician_id, disclosure_date DESC);

-- Step 3: Add index on politicians.role for chamber filtering (MEP, Senator, Representative)
CREATE INDEX IF NOT EXISTS idx_politicians_role
  ON politicians(role);

-- Step 4: Add index on politicians.party for party filtering
CREATE INDEX IF NOT EXISTS idx_politicians_party
  ON politicians(party)
  WHERE party IS NOT NULL;

-- Step 5: Clean up garbage EU Parliament placeholder data
-- These 30 records were created by a test run, not the real EU ETL:
-- - All tied to a single "EU MEP (Placeholder)" politician
-- - Source URLs point to CSS files instead of actual disclosure PDFs
-- - Asset names are all "EU Asset" (not real financial interests)
-- - All have status='pending'
DELETE FROM trading_disclosures
WHERE politician_id IN (
  SELECT id FROM politicians WHERE full_name = 'EU MEP (Placeholder)'
);

DELETE FROM politicians
WHERE full_name = 'EU MEP (Placeholder)';

-- Step 6: Update statistics for query planner after index creation
ANALYZE trading_disclosures;
ANALYZE politicians;
