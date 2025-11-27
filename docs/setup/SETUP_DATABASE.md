# Database Setup - Quick Start

## Problem
You're seeing these errors in the Admin Dashboard:
```
❌ politician_trades: Could not find the table 'public.politician_trades' in the schema cache
❌ user_sessions: Could not find the table 'public.user_sessions' in the schema cache
```

## Solution (5 minutes)

### Step 1: Open Supabase SQL Editor

Go to: https://app.supabase.com/project/uljsqvwkomdrlnofmlad/sql

Or:
1. Visit https://app.supabase.com/
2. Select your project: `uljsqvwkomdrlnofmlad`
3. Click **SQL Editor** in the left sidebar

### Step 2: Run the SQL Script

1. Click **New Query** button
2. Open the file: `supabase/sql/create_missing_tables.sql` in your code editor
3. Copy ALL the SQL content (Ctrl/Cmd + A, then Ctrl/Cmd + C)
4. Paste into the Supabase SQL Editor
5. Click **Run** (or press Ctrl/Cmd + Enter)

### Step 3: Verify Tables Created

You should see a success message:
```
Successfully created politician_trades and user_sessions tables!
```

### Step 4: Check in Admin Dashboard

1. Go back to your Streamlit app
2. Navigate to **Admin** page
3. Click **Supabase** tab
4. You should now see:
   ```
   ✅ politician_trades: Accessible (0 total rows)
   ✅ user_sessions: Accessible (0 total rows)
   ✅ action_logs: Accessible (X total rows)
   ✅ scheduled_jobs: Accessible (X total rows)
   ```

## What Tables Were Created?

### `politician_trades`
Main table for storing all politician trading activity.

**Columns:**
- `id` - Unique identifier
- `politician_name` - Full name of the politician
- `transaction_date` - When the trade occurred
- `disclosure_date` - When it was disclosed
- `ticker` - Stock ticker symbol (e.g., AAPL)
- `transaction_type` - purchase, sale, exchange, etc.
- `amount`, `amount_min`, `amount_max` - Trade amounts
- `party`, `state`, `position` - Politician info
- `source` - Where the data came from
- `raw_data` - Original scraped data (JSONB)

### `user_sessions`
Tracks user authentication sessions.

**Columns:**
- `id` - Unique identifier
- `session_id` - Session identifier
- `user_email` - User's email
- `login_time` - When they logged in
- `last_activity` - Last activity timestamp
- `is_active` - Whether session is active
- `expires_at` - Session expiration time

## Troubleshooting

### Error: "permission denied"
**Solution:** Make sure you're logged into Supabase with the project owner account.

### Error: "relation already exists"
**Solution:** This is fine! It means the table was already created. The script uses `IF NOT EXISTS` so it's safe to run multiple times.

### Still seeing errors after running SQL?
1. Clear your browser cache
2. Refresh the Streamlit app (Ctrl/Cmd + R)
3. Check the **Table Editor** in Supabase to confirm tables exist
4. Verify your connection string in `.streamlit/secrets.toml`

### Tables created but showing 0 rows?
**This is normal!** The tables are empty until you:
1. Run the data collection scrapers
2. Import existing data
3. Start tracking politician trades

## Next Steps

After creating the tables:

1. **Test Data Collection:**
   - Go to **Data Collection** page
   - Run a scraper to populate `politician_trades`

2. **Configure Scheduled Jobs:**
   - Go to **Scheduled Jobs** page
   - Set up automated data collection

3. **View Trading Signals:**
   - Once data is collected, check **Trading Signals** page
   - Analyze politician trading patterns

## Need Help?

- Check logs: **Admin** → **Logs** tab
- Review full documentation: `supabase/README.md`
- File an issue: https://github.com/gwicho38/politician-trading-tracker/issues

## SQL Script Location

The complete SQL script is located at:
```
supabase/sql/create_missing_tables.sql
```

This script:
- ✅ Creates both required tables
- ✅ Sets up indexes for performance
- ✅ Configures Row Level Security (RLS)
- ✅ Creates helpful views
- ✅ Safe to run multiple times (uses IF NOT EXISTS)
