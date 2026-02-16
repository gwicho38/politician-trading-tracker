-- Fix raw EU party values that weren't abbreviated
UPDATE politicians
SET party = 'PfE'
WHERE party ILIKE '%patriots for europe%';

UPDATE politicians
SET party = 'ESN'
WHERE party ILIKE '%europe of sovereign%';

-- Fix any other truncated raw group names
UPDATE politicians
SET party = 'EPP'
WHERE party ILIKE '%european people%' AND party != 'EPP';

UPDATE politicians
SET party = 'S&D'
WHERE party ILIKE '%progressive alliance%' AND party != 'S&D';

UPDATE politicians
SET party = 'Renew'
WHERE party ILIKE '%renew europe%' AND party != 'Renew';

UPDATE politicians
SET party = 'Greens/EFA'
WHERE (party ILIKE '%greens%' OR party ILIKE '%free alliance%')
  AND party != 'Greens/EFA';

UPDATE politicians
SET party = 'ECR'
WHERE party ILIKE '%conservatives and reformists%' AND party != 'ECR';

UPDATE politicians
SET party = 'ID'
WHERE party ILIKE '%identity and democracy%' AND party != 'ID';

UPDATE politicians
SET party = 'GUE/NGL'
WHERE party ILIKE '%the left group%' AND party != 'GUE/NGL';

UPDATE politicians
SET party = 'NI'
WHERE party ILIKE '%non-attached%' AND party != 'NI';
