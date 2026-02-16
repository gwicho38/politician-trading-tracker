-- Create parties lookup table
CREATE TABLE IF NOT EXISTS parties (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code       VARCHAR(20) NOT NULL UNIQUE,
  name       VARCHAR(100) NOT NULL,
  short_name VARCHAR(30),
  jurisdiction VARCHAR(10) NOT NULL DEFAULT 'US',
  color      VARCHAR(7) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- RLS
ALTER TABLE parties ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow anon read access" ON parties FOR SELECT USING (true);
CREATE POLICY "Allow service role full access" ON parties FOR ALL
  USING (auth.role() = 'service_role');

-- Seed known parties
INSERT INTO parties (code, name, short_name, jurisdiction, color) VALUES
  ('D',          'Democratic Party',                                   'Democrat',    'US', '#3B82F6'),
  ('R',          'Republican Party',                                   'Republican',  'US', '#EF4444'),
  ('I',          'Independent',                                        'Independent', 'US', '#EAB308'),
  ('EPP',        'European People''s Party',                           'EPP',         'EU', '#38BDF8'),
  ('S&D',        'Progressive Alliance of Socialists and Democrats',   'S&D',         'EU', '#3B82F6'),
  ('Renew',      'Renew Europe',                                       'Renew',       'EU', '#EAB308'),
  ('Greens/EFA', 'Greens/European Free Alliance',                      'Greens/EFA',  'EU', '#22C55E'),
  ('ECR',        'European Conservatives and Reformists',              'ECR',         'EU', '#EF4444'),
  ('ID',         'Identity and Democracy',                             'ID',          'EU', '#6366F1'),
  ('GUE/NGL',    'The Left in the European Parliament',               'GUE/NGL',     'EU', '#F43F5E'),
  ('NI',         'Non-Inscrits',                                       'Non-Inscrit', 'EU', '#94A3B8'),
  ('PfE',        'Patriots for Europe',                                'Patriots',    'EU', '#0E7490')
ON CONFLICT (code) DO NOTHING;

-- Index for fast lookups by jurisdiction
CREATE INDEX IF NOT EXISTS idx_parties_jurisdiction ON parties(jurisdiction);
