-- Migration: Cleanup non-US House politicians
-- Issue: #59 - Database cleanup: Remove non-US House politicians
--
-- Current state:
--   - 1000 politicians, only 61 are actual US House members
--   - Non-House disclosures from EU, state sources should be removed
--   - Politicians without disclosures should be removed
--
-- This migration:
--   1. Deletes non-US House disclosures (EU, state sources)
--   2. Deletes politicians who are not US House members

-- Start transaction for safety
BEGIN;

-- Step 1: Delete non-US House disclosures
-- These are from sources like:
--   - texas_ethics_commission
--   - massachusetts_ethics
--   - german_bundestag
--   - french_assemblee
--   - italian_camera, italian_senato
--   - spanish_congreso
--   - dutch_tweede_kamer
--   - new_york_jcope
DELETE FROM trading_disclosures
WHERE raw_data->>'source' IS NOT NULL
  AND raw_data->>'source' NOT IN ('us_house', 'quiverquant');

-- Log the count for verification
DO $$
DECLARE
  deleted_disclosures INTEGER;
BEGIN
  GET DIAGNOSTICS deleted_disclosures = ROW_COUNT;
  RAISE NOTICE 'Deleted % non-US House disclosures', deleted_disclosures;
END $$;

-- Step 2: Identify US House politicians to keep
-- These are politicians who have at least one disclosure from us_house source
CREATE TEMP TABLE us_house_politician_ids AS
SELECT DISTINCT politician_id
FROM trading_disclosures
WHERE raw_data->>'source' = 'us_house'
  OR raw_data->>'source' = 'quiverquant';

-- Step 3: Delete politicians who are NOT US House members
-- This includes senators, governors, state officials, and EU politicians
DELETE FROM politicians
WHERE id NOT IN (SELECT politician_id FROM us_house_politician_ids);

-- Log the count for verification
DO $$
DECLARE
  deleted_politicians INTEGER;
  remaining_politicians INTEGER;
BEGIN
  GET DIAGNOSTICS deleted_politicians = ROW_COUNT;
  SELECT COUNT(*) INTO remaining_politicians FROM politicians;
  RAISE NOTICE 'Deleted % non-US House politicians', deleted_politicians;
  RAISE NOTICE 'Remaining politicians: %', remaining_politicians;
END $$;

-- Cleanup temp table
DROP TABLE us_house_politician_ids;

-- Verify final counts
DO $$
DECLARE
  politician_count INTEGER;
  disclosure_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO politician_count FROM politicians;
  SELECT COUNT(*) INTO disclosure_count FROM trading_disclosures;
  RAISE NOTICE 'Final counts - Politicians: %, Disclosures: %', politician_count, disclosure_count;
END $$;

COMMIT;
