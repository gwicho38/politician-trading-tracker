-- Fix RLS policies to allow anon users to read public data
-- The existing policy only allows authenticated users, but views need anon access too

-- Add SELECT policy for anon users on politicians table
CREATE POLICY "Allow anon read access" ON politicians
    FOR SELECT USING (true);

-- Add SELECT policy for anon users on trading_disclosures table  
CREATE POLICY "Allow anon read access" ON trading_disclosures
    FOR SELECT USING (true);

-- This allows the top_tickers view and other public views to work for all users
