-- =============================================================================
-- Inspect trading_signals table schema
-- =============================================================================
--
-- Run this query in Supabase SQL Editor to see the complete schema
-- of the trading_signals table, including all columns and their constraints.
--
-- This will help identify any columns that have NOT NULL constraints
-- that the application isn't populating.
--

-- Show all columns with their properties
SELECT
    column_name,
    data_type,
    CASE
        WHEN character_maximum_length IS NOT NULL
        THEN data_type || '(' || character_maximum_length || ')'
        WHEN numeric_precision IS NOT NULL
        THEN data_type || '(' || numeric_precision || ',' || numeric_scale || ')'
        ELSE data_type
    END as full_type,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'trading_signals'
ORDER BY ordinal_position;

-- Show constraints on the table
SELECT
    con.conname AS constraint_name,
    con.contype AS constraint_type,
    CASE con.contype
        WHEN 'c' THEN 'CHECK'
        WHEN 'f' THEN 'FOREIGN KEY'
        WHEN 'p' THEN 'PRIMARY KEY'
        WHEN 'u' THEN 'UNIQUE'
        WHEN 't' THEN 'TRIGGER'
        WHEN 'x' THEN 'EXCLUSION'
        ELSE con.contype::text
    END AS constraint_type_desc,
    pg_get_constraintdef(con.oid) AS constraint_definition
FROM pg_constraint con
JOIN pg_class rel ON rel.oid = con.conrelid
JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
WHERE nsp.nspname = 'public'
  AND rel.relname = 'trading_signals'
ORDER BY con.contype, con.conname;

-- Show indexes on the table
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'trading_signals'
ORDER BY indexname;

-- Summary: Count of nullable vs non-nullable columns
SELECT
    is_nullable,
    COUNT(*) as column_count
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'trading_signals'
GROUP BY is_nullable;
