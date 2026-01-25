-- Ensure RLS is enabled on the tables
ALTER TABLE politicians ENABLE ROW LEVEL SECURITY;
ALTER TABLE trading_disclosures ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist to avoid conflicts
DROP POLICY IF EXISTS "Allow anon read access" ON politicians;
DROP POLICY IF EXISTS "Allow anon read access" ON trading_disclosures;

-- Recreate policies to allow public read access
CREATE POLICY "Allow anon read access" ON politicians
    FOR SELECT USING (true);

CREATE POLICY "Allow anon read access" ON trading_disclosures
    FOR SELECT USING (true);

-- Grant select permissions on the view
GRANT SELECT ON top_tickers TO anon;
GRANT SELECT ON top_tickers TO authenticated;
