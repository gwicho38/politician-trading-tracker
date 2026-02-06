-- Populate chamber column for politicians
-- "Hon." prefix indicates House members (parsed from House PDFs)
-- Senators from Senate data don't have "Hon." prefix

-- First, set House members (those with "Hon." prefix)
UPDATE politicians
SET chamber = 'house'
WHERE full_name LIKE 'Hon.%'
  AND (chamber IS NULL OR chamber = '');

-- Set known Senators by bioguide_id pattern (senators often have different IDs)
-- Actually, let's use a more reliable method - check if they have trades in QuiverQuant Senate data
-- For now, set remaining politicians with bioguide_id to unknown
UPDATE politicians
SET chamber = 'unknown'
WHERE bioguide_id IS NOT NULL
  AND bioguide_id != ''
  AND (chamber IS NULL OR chamber = '')
  AND full_name NOT LIKE 'Hon.%';

-- Show results
-- SELECT chamber, COUNT(*) as count FROM politicians WHERE bioguide_id IS NOT NULL GROUP BY chamber;
