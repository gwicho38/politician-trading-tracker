# Database Migrations

This directory contains SQL migration scripts for the Supabase PostgreSQL database.

## Applying Migrations

### Via Supabase Dashboard

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Create a new query
4. Copy and paste the migration SQL
5. Click **Run** to execute

### Via `psql` Command Line

If you have direct database access:

```bash
psql <your-database-connection-string> -f migrations/001_enhanced_disclosure_fields.sql
```

### Verification

After running a migration, verify it worked:

```sql
-- Check new columns exist
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'trading_disclosures'
AND column_name IN ('filer_id', 'quantity', 'asset_owner', 'comments');

-- Check new tables exist
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('capital_gains', 'asset_holdings');
```

## Migration List

| # | File | Description | Status |
|---|------|-------------|--------|
| 001 | `001_enhanced_disclosure_fields.sql` | Add enhanced parsing fields and tables | ⏳ Pending |

## Rollback

To rollback a migration, you'll need to manually drop the added columns/tables. Example for migration 001:

```sql
-- Drop new tables
DROP TABLE IF EXISTS asset_holdings CASCADE;
DROP TABLE IF EXISTS capital_gains CASCADE;

-- Drop new columns from trading_disclosures
ALTER TABLE trading_disclosures
DROP COLUMN IF EXISTS filer_id,
DROP COLUMN IF NOT EXISTS filing_date,
DROP COLUMN IF NOT EXISTS period_start_date,
DROP COLUMN IF EXISTS period_end_date,
DROP COLUMN IF EXISTS quantity,
DROP COLUMN IF EXISTS price_per_unit,
DROP COLUMN IF EXISTS is_range,
DROP COLUMN IF EXISTS asset_owner,
DROP COLUMN IF EXISTS comments,
DROP COLUMN IF EXISTS ticker_confidence_score,
DROP COLUMN IF EXISTS validation_flags,
DROP COLUMN IF EXISTS raw_pdf_text;

-- Drop indexes
DROP INDEX IF EXISTS idx_disclosures_filer_id;
DROP INDEX IF EXISTS idx_disclosures_filing_date;
DROP INDEX IF EXISTS idx_disclosures_asset_owner;
DROP INDEX IF EXISTS idx_disclosures_ticker_confidence;
```

## Best Practices

1. **Backup first**: Always backup your database before running migrations
2. **Test in development**: Test migrations in a development/staging environment first
3. **Read the migration**: Review the SQL before executing
4. **Check for conflicts**: Ensure no conflicts with existing data
5. **Monitor performance**: Large migrations may take time on big tables

## Notes

- Migrations are designed to be idempotent where possible (`IF NOT EXISTS`, `IF EXISTS`)
- New columns allow NULL values to avoid breaking existing data
- Indexes are created to optimize common queries
- Foreign key constraints use `ON DELETE CASCADE` for data integrity
