-- Migration: Cleanup non-US House politicians (v2 - fixed FK constraint issue)
-- Issue: #59 - Database cleanup: Remove non-US House politicians
--
-- Fix: Delete disclosures first before deleting politicians
-- Only keep politicians who have at least one 'us_house' source disclosure

-- Step 1: Identify US House politicians to keep
-- These are politicians who have at least one disclosure from us_house source
CREATE TEMP TABLE us_house_politician_ids AS
SELECT DISTINCT politician_id
FROM trading_disclosures
WHERE raw_data->>'source' = 'us_house';

-- Step 2: Delete ALL disclosures for non-US House politicians
-- This includes quiverquant disclosures for Senators, etc.
DELETE FROM trading_disclosures
WHERE politician_id NOT IN (SELECT politician_id FROM us_house_politician_ids);

-- Log the count for verification
DO $$
DECLARE
  deleted_disclosures INTEGER;
BEGIN
  GET DIAGNOSTICS deleted_disclosures = ROW_COUNT;
  RAISE NOTICE 'Deleted % disclosures for non-US House politicians', deleted_disclosures;
END $$;

-- Step 3: Delete politicians who are NOT US House members
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
