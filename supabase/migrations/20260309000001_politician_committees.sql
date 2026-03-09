-- Stores committee assignments for politicians.
-- Populated by BioguideEnrichmentJob via Congress.gov API.
-- Used to compute committee_sector_alignment feature in ML pipeline.

CREATE TABLE IF NOT EXISTS public.politician_committees (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  politician_id UUID NOT NULL REFERENCES public.politicians(id) ON DELETE CASCADE,
  committee_name TEXT NOT NULL,
  committee_code TEXT,
  -- GICS sectors this committee's jurisdiction maps to
  gics_sectors TEXT[] NOT NULL DEFAULT '{}',
  role TEXT CHECK (role IN ('chair', 'ranking_member', 'member')) DEFAULT 'member',
  is_leadership BOOLEAN NOT NULL DEFAULT false,
  congress_number INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (politician_id, committee_name, congress_number)
);

CREATE INDEX idx_politician_committees_politician_id
  ON public.politician_committees (politician_id);

CREATE INDEX idx_politician_committees_gics
  ON public.politician_committees USING GIN (gics_sectors);

COMMENT ON TABLE public.politician_committees IS
  'Committee assignments for politicians, used for committee-sector alignment ML feature.';

-- Static mapping: committee codes to GICS sectors
-- Used when populating gics_sectors during enrichment
CREATE TABLE IF NOT EXISTS public.committee_sector_map (
  committee_code TEXT PRIMARY KEY,
  committee_name TEXT NOT NULL,
  gics_sectors TEXT[] NOT NULL DEFAULT '{}'
);

INSERT INTO public.committee_sector_map (committee_code, committee_name, gics_sectors) VALUES
  ('SSFI', 'Senate Finance',                   ARRAY['Financials', 'Health Care']),
  ('SSBK', 'Senate Banking',                   ARRAY['Financials', 'Real Estate']),
  ('SSEG', 'Senate Energy and Natural Resources', ARRAY['Energy', 'Utilities', 'Materials']),
  ('SSAF', 'Senate Armed Services',             ARRAY['Industrials', 'Information Technology']),
  ('SSCM', 'Senate Commerce',                   ARRAY['Communication Services', 'Consumer Discretionary', 'Information Technology']),
  ('SSJD', 'Senate Judiciary',                  ARRAY['Communication Services', 'Information Technology']),
  ('SSHR', 'Senate Health, Education, Labor',   ARRAY['Health Care', 'Consumer Staples']),
  ('HSAG', 'House Agriculture',                 ARRAY['Consumer Staples', 'Materials']),
  ('HSAP', 'House Appropriations',              ARRAY['Industrials']),
  ('HSAS', 'House Armed Services',              ARRAY['Industrials', 'Information Technology']),
  ('HSBA', 'House Financial Services',          ARRAY['Financials', 'Real Estate']),
  ('HSIF', 'House Energy and Commerce',         ARRAY['Energy', 'Health Care', 'Communication Services']),
  ('HSJL', 'House Judiciary',                   ARRAY['Communication Services', 'Information Technology']),
  ('HSSM', 'House Small Business',              ARRAY['Industrials', 'Consumer Discretionary']),
  ('HSSY', 'House Science, Space, Technology',  ARRAY['Information Technology', 'Communication Services']),
  ('HSWM', 'House Ways and Means',              ARRAY['Financials', 'Health Care'])
ON CONFLICT DO NOTHING;
