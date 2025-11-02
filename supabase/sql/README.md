# Database Schema Setup

This directory contains SQL schema files for the Politician Trading Tracker application.

## Files

### `politician_trading_schema.sql`
Main schema for politicians, trading disclosures, data sources, and data pull jobs.

**Tables:**
- `politicians` - Information about politicians being tracked
- `trading_disclosures` - Individual trading transactions/disclosures
- `data_pull_jobs` - Tracks data collection jobs (from scrapers)
- `data_sources` - Configuration for data sources

### `job_executions_schema.sql`
Schema for APScheduler job execution history (NEW).

**Tables:**
- `job_executions` - Execution history for scheduled jobs with full logs

**Features:**
- Persists job executions across app restarts
- Stores full log output for each execution
- Tracks execution duration and status
- Includes view for execution summary statistics

### `fix_trading_schema.sql`
Incremental schema updates for trading signals and orders tables.

## Setup Instructions

### Initial Setup

1. **Create Supabase Project** (if not already done)
   - Go to https://supabase.com
   - Create a new project
   - Note your project URL and service role key

2. **Run Base Schema**
   ```sql
   -- In Supabase SQL Editor, run:
   supabase/sql/politician_trading_schema.sql
   ```

3. **Run Job Executions Schema**
   ```sql
   -- In Supabase SQL Editor, run:
   supabase/sql/job_executions_schema.sql
   ```

4. **Run Fix Script** (if you have existing tables)
   ```sql
   -- In Supabase SQL Editor, run:
   supabase/sql/fix_trading_schema.sql
   ```

### Environment Variables

Ensure these environment variables are set:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
# or
SUPABASE_KEY=your-anon-key
```

For Streamlit Cloud, add these to `.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"
```

## Job Executions Table

The `job_executions` table provides persistence for scheduled job history:

### Schema

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `job_id` | VARCHAR(100) | Job identifier (e.g., "data_collection") |
| `status` | VARCHAR(20) | "success", "failed", or "cancelled" |
| `started_at` | TIMESTAMPTZ | When job execution started |
| `completed_at` | TIMESTAMPTZ | When job execution finished |
| `duration_seconds` | DECIMAL(10,3) | Execution duration |
| `error_message` | TEXT | Error message if failed |
| `logs` | TEXT | Full log output (newline-separated) |
| `metadata` | JSONB | Additional execution context |
| `created_at` | TIMESTAMPTZ | Record creation time |

### Indexes

- `idx_job_executions_job_id` - Query by job ID
- `idx_job_executions_status` - Filter by status
- `idx_job_executions_started_at` - Order by execution time
- `idx_job_executions_job_id_started_at` - Composite for efficient job history queries

### Views

**`job_execution_summary`** - Aggregated statistics per job:
- Total executions (last 30 days)
- Success/failure counts
- Last execution time
- Average/min/max duration

### Cleanup

Old job executions are automatically managed:
- JobHistory class keeps most recent 100 executions per job in memory
- Database stores unlimited history (configurable via cleanup function)

To manually clean up old executions:

```sql
-- Keep only last 1000 executions per job
SELECT cleanup_old_job_executions();
```

## Row Level Security (RLS)

All tables have RLS enabled with policies:
- Authenticated users: Full access
- Service role: Full access
- Anon role: Read-only access to views

## Migration from In-Memory History

Job history is automatically loaded from the database on app initialization. No migration needed - just run the schema and restart the app.

## Monitoring

### Check Job Execution Status

```sql
-- Recent executions
SELECT job_id, status, started_at, duration_seconds
FROM job_executions
ORDER BY started_at DESC
LIMIT 20;

-- Job execution summary
SELECT * FROM job_execution_summary;

-- Failed executions
SELECT job_id, started_at, error_message
FROM job_executions
WHERE status = 'failed'
ORDER BY started_at DESC;
```

### View Logs for Specific Execution

```sql
SELECT logs
FROM job_executions
WHERE job_id = 'data_collection'
ORDER BY started_at DESC
LIMIT 1;
```

## Troubleshooting

### Job history not persisting

1. Check database connection:
   ```python
   from politician_trading.config import SupabaseConfig
   config = SupabaseConfig.from_env()
   print(config.url)  # Should show your Supabase URL
   ```

2. Check table exists:
   ```sql
   SELECT * FROM information_schema.tables
   WHERE table_name = 'job_executions';
   ```

3. Check RLS policies:
   ```sql
   SELECT * FROM pg_policies
   WHERE tablename = 'job_executions';
   ```

### Logs show "Failed to load job history from database"

- Ensure `job_executions_schema.sql` has been run
- Check your service role key has proper permissions
- Verify RLS policies are configured correctly

## Architecture Notes

- **JobHistory class** (`src/politician_trading/scheduler/manager.py`) handles both in-memory caching and database persistence
- Executions are written to database as they occur (append-only)
- On app startup, recent history is loaded from database into memory
- The UI displays the in-memory cache (which includes database-loaded executions)
- This provides fast access while maintaining persistence across restarts
