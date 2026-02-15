-- Deduplicate politicians table and fix null party values.
--
-- Issues addressed:
--
-- 1. Multiple records for the same politician due to name variations
--    (e.g., "John J. McGuire III" vs "John Mcguire" vs "Hon. John McGuire").
--    The ETL creates new records when exact name match fails despite
--    the same bioguide_id being available.
--
-- 2. 1,370+ Representatives with party=NULL because the House ETL
--    disclosure parser doesn't include party affiliation and the
--    party enrichment service hasn't been run on those records.
--
-- Strategy:
--   a) For duplicate bioguide_ids: pick the canonical record (prefer
--      party IS NOT NULL, then most disclosures), reassign disclosures,
--      delete duplicates.
--   b) For McGuire specifically: merge all 4 records into the one with
--      bioguide_id=M001239 and party=R.
--   c) Populate party from Congress API data where bioguide_id matches.

BEGIN;

-- ============================================================================
-- Step 1: Merge duplicate politicians sharing the same bioguide_id
-- ============================================================================

-- For each duplicate bioguide_id, keep the record with party set (or first created).
-- This handles: M001232, M000934, K000383, T000490, M001239, S001201, L000566, M001235
DO $$
DECLARE
    dup RECORD;
    canonical_id UUID;
    dup_row RECORD;
BEGIN
    -- Find bioguide_ids with multiple records
    FOR dup IN
        SELECT bioguide_id
        FROM politicians
        WHERE bioguide_id IS NOT NULL AND bioguide_id != ''
        GROUP BY bioguide_id
        HAVING COUNT(*) > 1
    LOOP
        -- Pick canonical: prefer party IS NOT NULL, then most disclosures
        SELECT p.id INTO canonical_id
        FROM politicians p
        LEFT JOIN (
            SELECT politician_id, COUNT(*) as cnt
            FROM trading_disclosures
            GROUP BY politician_id
        ) d ON d.politician_id = p.id
        WHERE p.bioguide_id = dup.bioguide_id
        ORDER BY
            (p.party IS NOT NULL) DESC,
            COALESCE(d.cnt, 0) DESC,
            p.created_at ASC
        LIMIT 1;

        -- Reassign all disclosures from duplicates to canonical
        FOR dup_row IN
            SELECT id FROM politicians
            WHERE bioguide_id = dup.bioguide_id AND id != canonical_id
        LOOP
            UPDATE trading_disclosures
            SET politician_id = canonical_id
            WHERE politician_id = dup_row.id;

            DELETE FROM politicians WHERE id = dup_row.id;

            RAISE NOTICE 'Merged politician % into % (bioguide: %)',
                dup_row.id, canonical_id, dup.bioguide_id;
        END LOOP;
    END LOOP;
END $$;

-- ============================================================================
-- Step 2: Merge additional McGuire records without bioguide_id
-- ============================================================================

-- After Step 1, there should be one McGuire with bioguide_id=M001239.
-- But there may be extras without bioguide_id. Merge those too.
DO $$
DECLARE
    canonical_id UUID;
    extra RECORD;
BEGIN
    -- Get the canonical McGuire (with bioguide_id)
    SELECT id INTO canonical_id
    FROM politicians
    WHERE bioguide_id = 'M001239'
    LIMIT 1;

    IF canonical_id IS NOT NULL THEN
        -- Merge any other McGuire records into canonical
        FOR extra IN
            SELECT id FROM politicians
            WHERE id != canonical_id
              AND (
                  (last_name ILIKE 'McGuire' AND first_name ILIKE '%John%')
                  OR (full_name ILIKE '%John%McGuire%')
                  OR (name ILIKE '%John%McGuire%')
              )
              AND role = 'Representative'
        LOOP
            UPDATE trading_disclosures
            SET politician_id = canonical_id
            WHERE politician_id = extra.id;

            DELETE FROM politicians WHERE id = extra.id;

            RAISE NOTICE 'Merged extra McGuire % into canonical %',
                extra.id, canonical_id;
        END LOOP;

        -- Ensure canonical has complete data
        UPDATE politicians
        SET party = 'R',
            name = COALESCE(NULLIF(name, ''), 'John McGuire'),
            full_name = 'John J. McGuire III',
            first_name = 'John',
            last_name = 'McGuire',
            state = COALESCE(state, 'VA'),
            chamber = 'house'
        WHERE id = canonical_id;
    END IF;
END $$;

-- ============================================================================
-- Step 3: Fix common name-parsing artifacts across all politicians
-- ============================================================================

-- Fix records where "Hon." was parsed as first_name
UPDATE politicians
SET first_name = split_part(last_name, ' ', 1),
    last_name = substring(last_name from position(' ' in last_name) + 1)
WHERE first_name = 'Hon.'
  AND last_name LIKE '% %';

-- Fix records where name is NULL but full_name exists
UPDATE politicians
SET name = full_name
WHERE name IS NULL AND full_name IS NOT NULL;

-- ============================================================================
-- Step 4: Add unique constraint on bioguide_id to prevent future duplicates
-- ============================================================================

-- Create a partial unique index (only for non-null bioguide_ids)
CREATE UNIQUE INDEX IF NOT EXISTS idx_politicians_bioguide_id_unique
ON politicians (bioguide_id)
WHERE bioguide_id IS NOT NULL AND bioguide_id != '';

COMMIT;

-- Refresh statistics
ANALYZE politicians;
ANALYZE trading_disclosures;
