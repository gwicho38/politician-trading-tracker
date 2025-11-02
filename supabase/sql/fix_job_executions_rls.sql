-- Fix RLS policies for job_executions table
-- This allows the service role to insert/update/delete records

-- Drop existing policies
DROP POLICY IF EXISTS "Allow all for authenticated users" ON job_executions;
DROP POLICY IF EXISTS "Allow all for service role" ON job_executions;

-- Create new policies that work with service role key
-- Policy 1: Service role has full access (bypasses RLS)
CREATE POLICY "Service role bypass RLS" ON job_executions
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Policy 2: Authenticated users have full access
CREATE POLICY "Authenticated users full access" ON job_executions
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Policy 3: Anonymous users can read only
CREATE POLICY "Anonymous users read only" ON job_executions
    FOR SELECT
    TO anon
    USING (true);

-- Ensure service_role can access the view as well
GRANT SELECT ON job_execution_summary TO service_role;
