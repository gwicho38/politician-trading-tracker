-- Test that trading_signals table is accessible and has the correct structure
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'trading_signals' 
ORDER BY ordinal_position;

-- Check if RLS is enabled
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE tablename = 'trading_signals';

-- Check RLS policies
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
FROM pg_policies 
WHERE tablename = 'trading_signals';

-- Try to select from the table (should work with public policy)
SELECT COUNT(*) as signal_count FROM trading_signals LIMIT 5;

-- Test the has_role function
SELECT 
    proname,
    pg_get_function_identity_arguments(oid) as arguments,
    obj_description(oid, 'pg_proc') as description
FROM pg_proc 
WHERE proname = 'has_role';

-- Test has_role function with the admin user
SELECT has_role('a3560fab-9597-479b-8cfa-b089d2a6d504', 'admin') as is_admin;
