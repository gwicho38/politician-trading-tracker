# Politician Trading Data Collection - Deployment Guide

This guide covers deploying the politician trading data collection workflow to Supabase with automated cron job scheduling.

## Prerequisites

- Supabase project with credentials
- Python environment with mcli installed
- Supabase CLI (optional, for Edge Functions)

## Quick Start

### 1. Database Setup

First, create the database schema in your Supabase project:

```bash
# Setup the workflow (creates tables if needed)
mcli politician-trading setup --create-tables --verify
```

Or manually execute the SQL schema:
1. Open your Supabase SQL editor
2. Copy and paste the contents of `schema.sql`
3. Execute the SQL

### 2. Test the Workflow

```bash
# Test the basic workflow
mcli politician-trading run

# Check system status
mcli politician-trading status

# Check system health
mcli politician-trading health

# View detailed statistics
mcli politician-trading stats
```

### 3. Setup Automated Collection

#### Option A: Supabase Edge Function + Cron (Recommended)

1. Create a Supabase Edge Function:

```bash
# Create the Edge Function
supabase functions new politician-trading-collect

# Deploy the function
supabase functions deploy politician-trading-collect
```

2. Copy the Edge Function code from `supabase_functions.py` to your function.

3. Set up the cron job:

```bash
# Show cron job setup instructions
mcli politician-trading cron-job --create
```

#### Option B: Direct Database Cron Job

Execute the cron job SQL from `supabase_functions.py` in your Supabase SQL editor.

## Configuration

### Environment Variables

The workflow uses the following configuration:

```python
# Default Supabase configuration
SUPABASE_URL = "https://uljsqvwkomdrlnofmlad.supabase.co"
SUPABASE_KEY = "your_anon_key"

# Scraping configuration
REQUEST_DELAY = 2.0  # Delay between requests (seconds)
MAX_RETRIES = 3      # Maximum retry attempts
TIMEOUT = 30         # Request timeout (seconds)
```

### Custom Configuration

Create a custom configuration file:

```python
from mcli.workflow.politician_trading.config import WorkflowConfig, SupabaseConfig, ScrapingConfig

config = WorkflowConfig(
    supabase=SupabaseConfig(
        url="your_supabase_url",
        key="your_supabase_key"
    ),
    scraping=ScrapingConfig(
        request_delay=1.0,
        max_retries=5,
        timeout=60,
        user_agent="YourBot/1.0"
    )
)
```

## Monitoring

### Health Checks

```bash
# One-time health check
mcli politician-trading health

# Continuous monitoring
mcli politician-trading monitor --interval 30

# JSON output for automation
mcli politician-trading health --json
```

### Statistics

```bash
# View system statistics
mcli politician-trading stats

# JSON output
mcli politician-trading stats --json
```

## Data Sources

The workflow collects data from:

### US Sources
- **House Financial Disclosures**: `https://disclosures-clerk.house.gov`
- **Senate Financial Disclosures**: `https://efdsearch.senate.gov`
- **QuiverQuant** (backup): `https://www.quiverquant.com/congresstrading/`

### EU Sources
- **EU Parliament Declarations**: `https://www.europarl.europa.eu/meps/en/declarations`

## Database Schema

### Core Tables

- **politicians**: Politician information and roles
- **trading_disclosures**: Individual trading transactions/disclosures
- **data_pull_jobs**: Job execution tracking and status
- **data_sources**: Data source configuration and health

### Key Views

- **recent_trading_activity**: Recent trading activity summary
- **job_status_summary**: Job execution statistics

## Cron Job Scheduling

### Recommended Schedule

```sql
-- Every 6 hours for full collection
SELECT cron.schedule(
    'politician-trading-collection',
    '0 */6 * * *',
    'SELECT net.http_post(...)'
);

-- Every 2 hours for status checks  
SELECT cron.schedule(
    'politician-trading-status',
    '0 */2 * * *',
    'INSERT INTO data_pull_jobs (...)'
);
```

### Monitoring Cron Jobs

```sql
-- View scheduled jobs
SELECT * FROM cron.job;

-- View execution history
SELECT * FROM cron.job_run_details 
ORDER BY start_time DESC 
LIMIT 10;

-- Monitor failures
SELECT * FROM cron_job_monitoring;
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Verify credentials
   mcli politician-trading setup --verify
   ```

2. **Schema Creation Failed**
   - Manually execute `schema.sql` in Supabase SQL editor
   - Check database permissions

3. **Scraping Failures**
   - Check internet connectivity
   - Verify rate limiting configuration
   - Review scraper logs

4. **Cron Job Not Running**
   - Check cron job syntax
   - Verify Edge Function deployment
   - Review cron execution logs

### Log Analysis

```bash
# View recent jobs with errors
mcli politician-trading status --json | jq '.recent_jobs[] | select(.status == "failed")'

# Monitor in real-time
mcli politician-trading monitor --interval 10
```

## Security Considerations

1. **API Keys**: Store Supabase keys securely
2. **Rate Limiting**: Respect website robots.txt and terms of service
3. **Data Privacy**: Handle politician data according to applicable laws
4. **Access Control**: Configure Supabase RLS policies appropriately

## Performance Optimization

1. **Database Indexes**: Schema includes optimized indexes
2. **Request Rate Limiting**: Configurable delays between requests
3. **Async Processing**: All operations use async/await patterns
4. **Connection Pooling**: Supabase client handles connection pooling

## Scaling Considerations

- **Horizontal Scaling**: Use multiple Supabase Edge Functions
- **Data Partitioning**: Consider partitioning large tables by date
- **Caching**: Implement Redis caching for frequently accessed data
- **Archiving**: Archive old job records periodically

## Support

For issues or questions:
1. Check the logs with `mcli politician-trading health`
2. Review the troubleshooting section
3. Check Supabase dashboard for database issues
4. Review cron job execution logs