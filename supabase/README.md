# Supabase Database Setup

This directory contains SQL scripts to set up your Supabase database for the Politician Trading Tracker application.

## Quick Start

### Option 1: Using Supabase Dashboard (Recommended)

1. Go to your Supabase project dashboard: https://app.supabase.com/project/uljsqvwkomdrlnofmlad
2. Click on **SQL Editor** in the left sidebar
3. Click **New Query**
4. Copy and paste the contents of `sql/create_missing_tables.sql`
5. Click **Run** (or press Cmd/Ctrl + Enter)
6. Verify the tables were created in the **Table Editor**

### Option 2: Using CLI

If you have the Supabase CLI installed:

```bash
# From the project root
supabase db push
```

Or execute the SQL file directly:

```bash
psql "postgresql://postgres:[YOUR-PASSWORD]@db.uljsqvwkomdrlnofmlad.supabase.co:5432/postgres" -f supabase/sql/create_missing_tables.sql
```

## Database Schema Files

### Core Tables

- **`create_missing_tables.sql`** - Creates the essential tables:
  - `politician_trades` - Main trading data table
  - `user_sessions` - User authentication session tracking

### Additional Schemas

- **`politician_trading_schema.sql`** - Original comprehensive schema with:
  - `politicians` - Politician profiles
  - `trading_disclosures` - Individual trade disclosures
  - `data_pull_jobs` - Data scraping job tracking
  - `data_sources` - Data source configuration

- **`scheduled_jobs_schema.sql`** - Scheduled job management
- **`trading_schema.sql`** - Trading operations and portfolio management
- **`job_executions_schema.sql`** - Job execution tracking

## Required Tables

The application expects these tables to exist:

| Table Name | Purpose | Status |
|------------|---------|--------|
| `politician_trades` | Main trading data | ⚠️ Create with `create_missing_tables.sql` |
| `user_sessions` | Auth session tracking | ⚠️ Create with `create_missing_tables.sql` |
| `action_logs` | Application action logging | ✅ Already exists |
| `scheduled_jobs` | Job scheduling | ✅ Already exists |

## Table Relationships

```
politician_trades (main trading data)
├── Indexed by: ticker, politician_name, transaction_date
└── No foreign keys (standalone table)

user_sessions (auth tracking)
├── Indexed by: user_email, session_id, last_activity
└── No foreign keys (standalone table)
```

## Row Level Security (RLS)

All tables have RLS enabled with the following policies:

### `politician_trades`
- ✅ Authenticated users: Full read/write access
- ✅ Anonymous users: Read-only access (public data)

### `user_sessions`
- ✅ Users can view/update their own sessions
- ✅ Authenticated users can create sessions
- ❌ Anonymous users: No access

## Verifying Table Creation

After running the SQL scripts, verify tables exist:

1. **Via Supabase Dashboard:**
   - Go to **Table Editor**
   - Check that `politician_trades` and `user_sessions` appear in the list

2. **Via Admin Dashboard:**
   - Run your Streamlit app: `uv run streamlit run app.py`
   - Navigate to the **Admin** page
   - Check the **Supabase** tab
   - Should show: ✅ `politician_trades`: Accessible (X total rows)

3. **Via SQL Query:**
   ```sql
   SELECT table_name
   FROM information_schema.tables
   WHERE table_schema = 'public'
   AND table_name IN ('politician_trades', 'user_sessions');
   ```

## Troubleshooting

### Error: "Could not find the table 'public.politician_trades' in the schema cache"

**Solution:** The table doesn't exist yet. Run `create_missing_tables.sql` in the Supabase SQL Editor.

### Error: "permission denied for table"

**Solution:** Check RLS policies. The user needs to be authenticated or the table needs anon access.

### Error: "relation already exists"

**Solution:** This is fine - it means the table is already created. The scripts use `CREATE TABLE IF NOT EXISTS`.

## Migrations

To add new columns or modify existing tables:

1. Create a new migration file: `sql/migration_YYYYMMDD_description.sql`
2. Use `ALTER TABLE` statements (safer than `CREATE OR REPLACE`)
3. Test on a development instance first
4. Run on production via SQL Editor

Example migration:
```sql
-- Add new column to politician_trades
ALTER TABLE politician_trades
ADD COLUMN IF NOT EXISTS notes TEXT;

-- Add index if needed
CREATE INDEX IF NOT EXISTS idx_politician_trades_notes
ON politician_trades(notes);
```

## Backup and Restore

### Backup (via CLI)
```bash
pg_dump "postgresql://postgres:[PASSWORD]@db.uljsqvwkomdrlnofmlad.supabase.co:5432/postgres" > backup.sql
```

### Restore (via CLI)
```bash
psql "postgresql://postgres:[PASSWORD]@db.uljsqvwkomdrlnofmlad.supabase.co:5432/postgres" < backup.sql
```

### Backup (via Dashboard)
Supabase provides automatic daily backups. Check your project's **Database** → **Backups** section.

## Support

- Supabase Docs: https://supabase.com/docs
- Project Dashboard: https://app.supabase.com/project/uljsqvwkomdrlnofmlad
- Issues: https://github.com/gwicho38/politician-trading-tracker/issues
