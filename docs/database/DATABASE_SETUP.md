# Database Setup Guide

This guide will help you set up the Supabase database for the Politician Trading Tracker.

## Quick Setup

### 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Create a new project
3. Note your project URL and API keys

### 2. Run SQL Migrations

You need to run two SQL migration files in order:

#### Step 1: Politician Trading Schema

1. Go to your Supabase project dashboard
2. Click on **SQL Editor** in the left sidebar
3. Click **New query**
4. Copy the contents of `supabase/sql/politician_trading_schema.sql`
5. Paste into the SQL editor
6. Click **Run** or press `Ctrl+Enter`

This creates:
- `politicians` table
- `trading_disclosures` table
- `data_pull_jobs` table
- `data_sources` table
- Necessary indexes and triggers

#### Step 2: Trading Schema

1. In SQL Editor, click **New query** again
2. Copy the contents of `supabase/sql/trading_schema.sql`
3. Paste into the SQL editor
4. Click **Run** or press `Ctrl+Enter`

This creates:
- `trading_signals` table (with `confidence_score` column)
- `trading_orders` table
- `portfolios` table
- `positions` table
- Views for active signals, portfolio performance, etc.
- Row Level Security policies

### 3. Verify Tables Were Created

Run this query to verify all tables exist:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

You should see:
- `politicians`
- `trading_disclosures`
- `data_pull_jobs`
- `data_sources`
- `trading_signals`
- `trading_orders`
- `portfolios`
- `positions`

### 4. Configure API Keys

Get your API keys from Supabase:

1. Go to **Settings** → **API**
2. Copy:
   - `Project URL` (SUPABASE_URL)
   - `anon/public` key (SUPABASE_ANON_KEY)
   - `service_role` key (SUPABASE_SERVICE_KEY) - keep this secret!

Add these to your Streamlit Cloud secrets or `.env` file.

## Troubleshooting

### Error: "column trading_signals.confidence_score does not exist"

**Cause**: The `trading_schema.sql` migration hasn't been run yet.

**Solution**:
1. Run the `trading_schema.sql` migration as described above
2. If you already ran it, the table might be outdated. Drop and recreate:

```sql
-- CAUTION: This will delete all trading data
DROP TABLE IF EXISTS trading_signals CASCADE;
DROP TABLE IF EXISTS trading_orders CASCADE;
DROP TABLE IF EXISTS portfolios CASCADE;
DROP TABLE IF EXISTS positions CASCADE;

-- Then run trading_schema.sql again
```

### Error: "relation trading_disclosures does not exist"

**Cause**: The `politician_trading_schema.sql` migration hasn't been run.

**Solution**: Run the `politician_trading_schema.sql` migration first.

### Checking Column Exists

To verify the `confidence_score` column exists:

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'trading_signals'
ORDER BY ordinal_position;
```

You should see `confidence_score` listed as type `numeric`.

## Migration Order

**IMPORTANT**: Always run migrations in this order:

1. `politician_trading_schema.sql` - Creates base tables
2. `trading_schema.sql` - Creates trading tables (references politician tables)

## Updating Existing Database

If you have an existing database and need to update the schema:

### Add Missing Columns

If `confidence_score` is missing from `trading_signals`:

```sql
ALTER TABLE trading_signals
ADD COLUMN IF NOT EXISTS confidence_score DECIMAL(5,4)
CHECK (confidence_score >= 0 AND confidence_score <= 1);
```

### Add Missing Indexes

```sql
CREATE INDEX IF NOT EXISTS idx_trading_signals_confidence
ON trading_signals(confidence_score DESC);
```

## Data Seeding

To add test data:

```bash
# From project root
politician-trading-seed
```

Or manually insert test politician:

```sql
INSERT INTO politicians (first_name, last_name, full_name, role, party, state_or_country)
VALUES ('Nancy', 'Pelosi', 'Nancy Pelosi', 'US_HOUSE_REP', 'Democrat', 'California');
```

## Row Level Security (RLS)

The migrations automatically enable RLS on all tables. Current policies allow all authenticated users to read/write.

For production, you may want to restrict access:

```sql
-- Example: Only allow read access
DROP POLICY IF EXISTS "Allow all operations for authenticated users" ON trading_signals;

CREATE POLICY "Allow read for all users" ON trading_signals
    FOR SELECT USING (true);

CREATE POLICY "Allow insert for authenticated users" ON trading_signals
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');
```

## Backup

Before making schema changes, always backup your data:

1. Go to **Database** → **Backups** in Supabase dashboard
2. Click **Create backup**
3. Or export tables manually:

```sql
COPY trading_signals TO '/path/to/backup.csv' CSV HEADER;
```

## Support

If you encounter issues:

1. Check the Supabase logs in **Logs** → **Postgres Logs**
2. Verify your API keys are correct
3. Ensure you're using the correct project URL
4. File an issue on GitHub with error details
