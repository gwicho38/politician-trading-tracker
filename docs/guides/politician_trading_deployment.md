# Politician Trading Data Collection - Supabase Cron Job Setup

## Overview

I've created a complete Supabase Edge Function that replicates your politician trading workflow and calls the same URLs your application uses. This function will run automatically every 6 hours via a cron job.

## Files Created

### 1. Edge Function
- **Location**: `supabase/functions/politician-trading-collect/index.ts`
- **Purpose**: Scrapes all the same data sources as your Python application
- **Data Sources**:
  - US House Financial Disclosures: `https://disclosures-clerk.house.gov/FinancialDisclosure`
  - US Senate Financial Disclosures: `https://efdsearch.senate.gov/search/`
  - QuiverQuant Congress Trading: `https://www.quiverquant.com/congresstrading/`
  - EU Parliament Declarations: `https://www.europarl.europa.eu/meps/en/declarations`
  - California NetFile Portals: `https://public.netfile.com/pub2/`

### 2. Cron Job SQL
- **Location**: `supabase/sql/cron_job.sql`
- **Purpose**: Sets up automated scheduling every 6 hours

## Deployment Instructions

### Step 1: Deploy the Edge Function

```bash
# Make sure you're in the mcli directory
cd /Users/lefv/repos/mcli

# Deploy the function to your Supabase project
supabase functions deploy politician-trading-collect --project-ref uljsqvwkomdrlnofmlad
```

### Step 2: Set Up Environment Variables

Copy the example environment file and add your credentials:

```bash
cp supabase/.env.example supabase/.env.local
```

Then edit `supabase/.env.local` with your actual values:

```bash
# Get these from: Supabase Dashboard → Settings → API
SUPABASE_URL=https://uljsqvwkomdrlnofmlad.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Get this from: Supabase Dashboard → Settings → Database → Connection string
DATABASE_URL=postgresql://postgres:your_actual_password@db.uljsqvwkomdrlnofmlad.supabase.co:5432/postgres
```

**Important**: Add `.env.local` to your `.gitignore` to keep credentials safe!

### Step 3: Create the Cron Job

Connect to your Supabase database and run the cron job SQL:

```bash
# Connect to your database using environment variable
source supabase/.env.local
psql "$DATABASE_URL"

# Run the cron job setup
\i supabase/sql/cron_job.sql
```

Or through the Supabase dashboard:
1. Go to https://app.supabase.com/project/uljsqvwkomdrlnofmlad
2. Navigate to SQL Editor
3. Paste and run the content from `supabase/sql/cron_job.sql`

### Step 4: Verify Setup

Your function URL will be:
```
https://uljsqvwkomdrlnofmlad.supabase.co/functions/v1/politician-trading-collect
```

Test it manually:
```bash
# Load environment variables
source supabase/.env.local

# Test the function
curl -i --location --request POST "$SUPABASE_URL/functions/v1/politician-trading-collect" \
  --header "Authorization: Bearer $SUPABASE_ANON_KEY" \
  --header 'Content-Type: application/json' \
  --data '{}'
```

## How It Works

### Data Collection Process
1. **US House**: Scrapes `disclosures-clerk.house.gov` for financial disclosure links
2. **US Senate**: Scrapes `efdsearch.senate.gov` for EFD reports  
3. **QuiverQuant**: Scrapes their congress trading data table
4. **EU Parliament**: Scrapes MEP declaration pages
5. **California**: Scrapes NetFile portals for San Francisco and Los Angeles

### Data Flow
1. Cron job triggers every 6 hours
2. Edge function makes HTTP requests to all data sources
3. Parses HTML/data from each source
4. Creates database records in your `trading_disclosures` table
5. Updates `data_pull_jobs` table with job status
6. Returns summary of collection results

### Rate Limiting & Error Handling
- 1-second delay between requests
- 3 retry attempts for failed requests
- User-agent rotation
- Graceful error handling per source
- Comprehensive logging

## Monitoring & Management

### View Cron Job Status
```sql
-- Check if cron job is active
SELECT * FROM cron.job WHERE jobname = 'politician-trading-collection';

-- View recent job runs
SELECT * FROM cron.job_run_details 
WHERE jobid IN (SELECT jobid FROM cron.job WHERE jobname = 'politician-trading-collection')
ORDER BY start_time DESC LIMIT 10;
```

### View Collection Results
```sql
-- Check recent data pulls
SELECT * FROM data_pull_jobs 
ORDER BY started_at DESC 
LIMIT 5;

-- Check latest disclosures
SELECT * FROM trading_disclosures 
ORDER BY transaction_date DESC 
LIMIT 10;
```

### Manual Trigger
```sql
-- Manually trigger collection
SELECT net.http_post(
    url := 'https://uljsqvwkomdrlnofmlad.supabase.co/functions/v1/politician-trading-collect',
    headers := jsonb_build_object(
        'Content-Type', 'application/json',
        'Authorization', 'Bearer YOUR_ANON_KEY'
    ),
    body := '{}'::jsonb
);
```

### Stop/Modify Cron Job
```sql
-- Stop the cron job
SELECT cron.unschedule('politician-trading-collection');

-- Reschedule with different timing (e.g., every 12 hours)
SELECT cron.schedule(
    'politician-trading-collection',
    '0 */12 * * *',
    $$ [same command as above] $$
);
```

## Function Features

- **Same URLs**: Uses identical data sources as your Python application
- **Database Integration**: Stores results in your existing Supabase tables
- **Error Resilience**: Continues collecting from other sources if one fails
- **Job Tracking**: Creates job records with detailed status
- **CORS Support**: Handles cross-origin requests properly
- **Logging**: Comprehensive console logging for debugging

## Next Steps

1. Deploy the function: `supabase functions deploy politician-trading-collect --project-ref uljsqvwkomdrlnofmlad`
2. Run the cron job SQL in your database
3. Monitor the first few runs to ensure everything works
4. Adjust timing if needed (currently every 6 hours)

The cron job will now automatically run every 6 hours, calling the same URLs and collecting the same data as your Python application, but from within Supabase's infrastructure!