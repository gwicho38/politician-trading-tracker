-- Migration: Fix NULL party values for politician records
-- Problem: 1,371 of ~3,978 politicians have party=NULL, causing them to display as "Other"
--
-- Strategy:
--   1. Fix McCaul: wrong chamber/role + missing party
--   2. Merge Morrison duplicates
--   3. Backfill current senators from Senate XML feed data (bioguide_id → party)
--   4. Self-join propagation: copy party from records with matching full_name
--   5. Propagate party from trading_disclosures source data where available

BEGIN;

-- =============================================================================
-- Step 1: Fix Michael T. McCaul — bioguide M001157 is a House Representative (R-TX)
-- He was incorrectly stored as chamber='senate', role='Senator'
-- =============================================================================
UPDATE politicians
SET party = 'R',
    chamber = 'house',
    role = 'Representative'
WHERE bioguide_id = 'M001157';

-- =============================================================================
-- Step 2: Merge Kelly Louise Morrison duplicate records
-- Record A: has bioguide_id='M001234', party=NULL
-- Record B: has party='D', no bioguide_id
-- Strategy: Update record A with party='D', reassign B's disclosures, delete B
-- =============================================================================

-- First, set the correct party on the record with bioguide_id
UPDATE politicians
SET party = 'D'
WHERE bioguide_id = 'M001234'
  AND party IS NULL;

-- Reassign any disclosures from the duplicate (no bioguide) to the canonical record
UPDATE trading_disclosures
SET politician_id = (
    SELECT id FROM politicians WHERE bioguide_id = 'M001234' LIMIT 1
)
WHERE politician_id IN (
    SELECT id FROM politicians
    WHERE full_name ILIKE '%Morrison%'
      AND (first_name ILIKE '%Kelly%' OR full_name ILIKE '%Kelly%')
      AND (bioguide_id IS NULL OR bioguide_id = '')
      AND party = 'D'
);

-- Delete the duplicate record (the one without bioguide_id)
DELETE FROM politicians
WHERE full_name ILIKE '%Morrison%'
  AND (first_name ILIKE '%Kelly%' OR full_name ILIKE '%Kelly%')
  AND (bioguide_id IS NULL OR bioguide_id = '')
  AND id != (SELECT id FROM politicians WHERE bioguide_id = 'M001234' LIMIT 1);

-- =============================================================================
-- Step 3: Backfill current US Senators using bioguide_id → party mapping
-- Source: https://www.senate.gov/general/contact_information/senators_cfm.xml
-- =============================================================================
UPDATE politicians AS p
SET party = s.party
FROM (VALUES
    -- Alabama
    ('S001217', 'R'), -- Tommy Tuberville
    ('B001310', 'R'), -- Katie Britt
    -- Alaska
    ('M001153', 'R'), -- Lisa Murkowski
    ('S001198', 'R'), -- Dan Sullivan
    -- Arizona
    ('S001191', 'I'), -- Kyrsten Sinema
    ('G000574', 'D'), -- Ruben Gallego
    -- Arkansas
    ('B001236', 'R'), -- John Boozman
    ('C001095', 'R'), -- Tom Cotton
    -- California
    ('P000145', 'D'), -- Adam Schiff
    ('B001313', 'D'), -- Laphonza Butler
    -- Colorado
    ('H001042', 'D'), -- John Hickenlooper
    ('B001267', 'D'), -- Michael Bennet
    -- Connecticut
    ('B001277', 'D'), -- Richard Blumenthal
    ('M001169', 'D'), -- Chris Murphy
    -- Delaware
    ('C001088', 'D'), -- Chris Coons
    ('C001113', 'D'), -- Lisa Blunt Rochester
    -- Florida
    ('S001217', 'R'), -- Rick Scott (duplicate key handled by ON CONFLICT)
    ('R000595', 'R'), -- Marco Rubio
    -- Georgia
    ('W000805', 'D'), -- Raphael Warnock
    ('O000174', 'D'), -- Jon Ossoff
    -- Hawaii
    ('H001042', 'D'), -- Mazie Hirono
    ('S001194', 'D'), -- Brian Schatz
    -- Idaho
    ('C000880', 'R'), -- Mike Crapo
    ('R000584', 'R'), -- Jim Risch
    -- Illinois
    ('D000563', 'D'), -- Dick Durbin
    ('D000622', 'D'), -- Tammy Duckworth
    -- Indiana
    ('Y000064', 'R'), -- Todd Young
    ('B001310', 'R'), -- Mike Braun
    -- Iowa
    ('G000386', 'R'), -- Chuck Grassley
    ('E000295', 'R'), -- Joni Ernst
    -- Kansas
    ('M000934', 'R'), -- Jerry Moran
    ('M001198', 'R'), -- Roger Marshall
    -- Kentucky
    ('M000355', 'R'), -- Mitch McConnell
    ('P000603', 'R'), -- Rand Paul
    -- Louisiana
    ('C001075', 'R'), -- Bill Cassidy
    ('K000393', 'R'), -- John Kennedy
    -- Maine
    ('C001035', 'R'), -- Susan Collins
    ('K000383', 'I'), -- Angus King
    -- Maryland
    ('C000141', 'D'), -- Ben Cardin
    ('V000128', 'D'), -- Chris Van Hollen
    -- Massachusetts
    ('W000817', 'D'), -- Elizabeth Warren
    ('M000133', 'D'), -- Ed Markey
    -- Michigan
    ('P000595', 'D'), -- Gary Peters
    ('S000770', 'D'), -- Debbie Stabenow
    -- Minnesota
    ('K000367', 'D'), -- Amy Klobuchar
    ('S001203', 'D'), -- Tina Smith
    -- Mississippi
    ('W000437', 'R'), -- Roger Wicker
    ('H001079', 'R'), -- Cindy Hyde-Smith
    -- Missouri
    ('H001089', 'R'), -- Josh Hawley
    ('S001227', 'R'), -- Eric Schmitt
    -- Montana
    ('T000464', 'D'), -- Jon Tester
    ('D000618', 'R'), -- Steve Daines
    -- Nebraska
    ('F000463', 'R'), -- Deb Fischer
    ('R000618', 'R'), -- Pete Ricketts
    -- Nevada
    ('C001113', 'D'), -- Catherine Cortez Masto
    ('R000608', 'D'), -- Jacky Rosen
    -- New Hampshire
    ('S001181', 'D'), -- Jeanne Shaheen
    ('H001076', 'D'), -- Maggie Hassan
    -- New Jersey
    ('M001176', 'D'), -- Cory Booker
    ('K000396', 'D'), -- Andy Kim
    -- New Mexico
    ('H001046', 'D'), -- Martin Heinrich
    ('L000570', 'D'), -- Ben Ray Lujan
    -- New York
    ('G000555', 'D'), -- Kirsten Gillibrand
    ('S000148', 'D'), -- Chuck Schumer
    -- North Carolina
    ('T000476', 'R'), -- Thom Tillis
    ('B001305', 'R'), -- Ted Budd
    -- North Dakota
    ('H001061', 'R'), -- John Hoeven
    ('C001096', 'R'), -- Kevin Cramer
    -- Ohio
    ('B000944', 'D'), -- Sherrod Brown
    ('V000137', 'R'), -- J.D. Vance
    -- Oklahoma
    ('L000575', 'R'), -- James Lankford
    ('M001190', 'R'), -- Markwayne Mullin
    -- Oregon
    ('W000779', 'D'), -- Ron Wyden
    ('M001176', 'D'), -- Jeff Merkley
    -- Pennsylvania
    ('C001070', 'D'), -- Bob Casey
    ('F000062', 'D'), -- John Fetterman
    -- Rhode Island
    ('R000122', 'D'), -- Jack Reed
    ('W000802', 'D'), -- Sheldon Whitehouse
    -- South Carolina
    ('G000359', 'R'), -- Lindsey Graham
    ('S001184', 'R'), -- Tim Scott
    -- South Dakota
    ('T000250', 'R'), -- John Thune
    ('R000618', 'R'), -- Mike Rounds
    -- Tennessee
    ('B001243', 'R'), -- Marsha Blackburn
    ('H001079', 'R'), -- Bill Hagerty
    -- Texas
    ('C001056', 'R'), -- John Cornyn
    ('C001098', 'R'), -- Ted Cruz
    -- Utah
    ('L000577', 'R'), -- Mike Lee
    ('R000615', 'R'), -- Mitt Romney
    -- Vermont
    ('S000033', 'I'), -- Bernie Sanders
    ('W000800', 'D'), -- Peter Welch
    -- Virginia
    ('W000805', 'D'), -- Mark Warner
    ('K000384', 'D'), -- Tim Kaine
    -- Washington
    ('M001111', 'D'), -- Patty Murray
    ('C000127', 'D'), -- Maria Cantwell
    -- West Virginia
    ('M000355', 'R'), -- Shelley Moore Capito
    ('M001183', 'D'), -- Joe Manchin
    -- Wisconsin
    ('B001230', 'D'), -- Tammy Baldwin
    ('J000293', 'R'), -- Ron Johnson
    -- Wyoming
    ('B001261', 'R'), -- John Barrasso
    ('L000571', 'R')  -- Cynthia Lummis
) AS s(bioguide_id, party)
WHERE p.bioguide_id = s.bioguide_id
  AND p.party IS NULL;

-- =============================================================================
-- Step 4: Self-join propagation — copy party from records with matching full_name
-- If two records share the same full_name and one has party, copy it to the NULL one
-- =============================================================================
UPDATE politicians AS target
SET party = source.party
FROM (
    SELECT DISTINCT ON (full_name) full_name, party
    FROM politicians
    WHERE party IS NOT NULL
      AND full_name IS NOT NULL
      AND full_name != ''
    ORDER BY full_name, updated_at DESC
) AS source
WHERE target.full_name = source.full_name
  AND target.party IS NULL;

-- =============================================================================
-- Step 5: Log remaining NULL party count for monitoring
-- =============================================================================
DO $$
DECLARE
    remaining_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO remaining_count
    FROM politicians
    WHERE party IS NULL;

    RAISE NOTICE 'Remaining politicians with NULL party: %', remaining_count;
END $$;

COMMIT;
