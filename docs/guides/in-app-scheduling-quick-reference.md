# In-App Scheduling Quick Reference

Quick guide to using in-app scheduled jobs.

## Quick Start

### 1. Access the Scheduler

```bash
# Start the app
streamlit run app.py

# Navigate to: ⏰ Scheduled Jobs (in sidebar)
```

The scheduler starts automatically when the app starts.

### 2. Create a Job (UI Method)

**Daily Data Collection at 2 AM:**
1. Go to **➕ Add New Job** tab
2. Select "Data Collection"
3. Select "Cron (Time-based)"
4. Set Hour: 2, Minute: 0
5. Select data sources (US Congress recommended)
6. Click **➕ Add Cron Job**

**Weekly Ticker Backfill (Sunday 3 AM):**
1. Go to **➕ Add New Job** tab
2. Select "Ticker Backfill"
3. Select "Cron (Time-based)"
4. Set Hour: 3, Minute: 0, Day: Sunday
5. Click **➕ Add Cron Job**

**Every 6 Hours Collection:**
1. Go to **➕ Add New Job** tab
2. Select "Data Collection"
3. Select "Interval"
4. Set Hours: 6
5. Click **➕ Add Interval Job**

### 3. Manage Jobs

**Pause a job:**
- Go to **📋 Active Jobs**
- Click **⏸️ Pause** button

**Run immediately:**
- Click **▶️ Run Now** button

**Remove a job:**
- Click **🗑️ Remove** button

### 4. Monitor

**View job status:**
- **📋 Active Jobs** tab shows next run time
- **📊 Job History** tab shows past executions

**Check logs:**
```bash
# View all scheduled job logs
cat logs/latest.log | jq 'select(.logger | contains("scheduled"))'

# Watch live
tail -f logs/latest.log | jq 'select(.logger | contains("scheduled"))'

# View errors only
cat logs/latest.log | jq 'select(.level == "ERROR") | select(.logger | contains("scheduled"))'
```

## Common Schedules

| Schedule | Config |
|----------|--------|
| **Daily at 2 AM** | Cron: Hour=2, Minute=0 |
| **Every 6 hours** | Interval: Hours=6 |
| **Every 12 hours** | Interval: Hours=12 |
| **Weekly (Sunday 3 AM)** | Cron: Hour=3, Minute=0, Day=Sunday |
| **Twice daily (2 AM, 2 PM)** | Create two jobs: Hour=2 and Hour=14 |

## Available Jobs

### Data Collection
- **What**: Scrape trading disclosures from configured sources
- **Sources**: US Congress, EU Parliament, UK Parliament, California
- **Recommended**: Daily or every 6-12 hours
- **Duration**: 2-10 minutes (depends on sources and volume)

### Ticker Backfill
- **What**: Find and update missing ticker symbols
- **Recommended**: Weekly
- **Duration**: 1-5 minutes (depends on missing tickers)

## Job Controls

| Button | Action |
|--------|--------|
| **▶️ Resume** | Restart a paused job |
| **⏸️ Pause** | Temporarily stop a job |
| **▶️ Run Now** | Execute immediately |
| **🗑️ Remove** | Delete permanently |

## Status Indicators

| Icon | Meaning |
|------|---------|
| ✅ | Job succeeded |
| ❌ | Job failed |
| ⏸️ | Job is paused |
| ▶️ | Job is active |

## Troubleshooting

### Job Not Running?

1. Check scheduler status (top of page)
2. Ensure job not paused
3. Check "Next Run" time
4. View logs for errors

### Job Failing?

1. Go to **📊 Job History**
2. Find failed execution
3. Read error message
4. Check logs:
   ```bash
   cat logs/latest.log | jq 'select(.level == "ERROR")'
   ```

### Scheduler Not Starting?

```bash
# Check if APScheduler is installed
uv pip list | grep -i apscheduler

# Install if missing
uv pip install "APScheduler>=3.10.0"

# Check app logs
cat logs/latest.log | jq 'select(.message | contains("Scheduler"))'
```

## Best Practices

✅ **DO:**
- Start with conservative schedules (daily, not hourly)
- Test jobs with "Run Now" before scheduling
- Monitor job history regularly
- Check logs for errors
- Keep app running (for cloud deployments)

❌ **DON'T:**
- Over-schedule (too frequent jobs)
- Run jobs too close together
- Ignore failed jobs
- Forget to test before scheduling

## Important Notes

⚠️ **Jobs only run while the Streamlit app is running**
- App must stay active for jobs to execute
- Ideal for cloud platforms (Streamlit Cloud, Heroku, Render, etc.)
- Consider system cron as backup for critical jobs

✅ **Works on:**
- Streamlit Cloud
- Heroku
- Render
- Railway
- Self-hosted servers

## Quick Commands

```bash
# Start app
streamlit run app.py

# View scheduled job logs
cat logs/latest.log | jq 'select(.logger | contains("scheduled"))'

# View last collection result
cat logs/latest.log | jq 'select(.message == "Data collection completed")' | tail -1

# View last backfill result
cat logs/latest.log | jq 'select(.message == "Ticker backfill completed")' | tail -1

# Check for errors
cat logs/latest.log | jq 'select(.level == "ERROR") | select(.logger | contains("scheduled"))'

# Watch live logs
tail -f logs/latest.log | jq 'select(.logger | contains("scheduled"))'
```

## Programmatic Usage

```python
from politician_trading.scheduler import get_scheduler

# Get scheduler instance
scheduler = get_scheduler()

# Get all jobs
jobs = scheduler.get_jobs()

# Get specific job info
info = scheduler.get_job_info("data_collection")

# Run a job now
scheduler.run_job_now("data_collection")

# Pause a job
scheduler.pause_job("data_collection")

# Resume a job
scheduler.resume_job("data_collection")

# Remove a job
scheduler.remove_job("data_collection")
```

## Complete Documentation

For full details, see:
- **[In-App Scheduling Guide](./in-app-scheduling.md)** - Complete guide
- **[System Cron Setup](./scheduled-jobs.md)** - Alternative/backup
- **[Logging Guide](./logging.md)** - Log format and analysis

## Support

- Check the UI's **⚙️ Settings** tab for helpful info
- Review logs in `logs/latest.log`
- See full documentation in `docs/`
