-- Fix congress_number to be NOT NULL with DEFAULT 0.
-- In PostgreSQL, two NULLs are not considered equal in a UNIQUE constraint,
-- so (politician_id, committee_name, NULL) could be inserted multiple times,
-- breaking deduplication.
-- Sentinel value 0 means "current congress / unknown congress number".

UPDATE public.politician_committees SET congress_number = 0 WHERE congress_number IS NULL;

ALTER TABLE public.politician_committees
  ALTER COLUMN congress_number SET NOT NULL,
  ALTER COLUMN congress_number SET DEFAULT 0;

COMMENT ON COLUMN public.politician_committees.congress_number IS
  'Congress number for this assignment. 0 = current/unknown congress (sentinel for UNIQUE constraint).';
