-- Check if trading_signals table exists and has required columns
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'trading_signals' 
ORDER BY ordinal_position;

-- Check if we can select from the table
SELECT COUNT(*) as signal_count FROM trading_signals;
