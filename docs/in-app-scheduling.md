# In-App Scheduling Guide

Complete guide to using in-app scheduled jobs within the Streamlit application.

## Overview

The Politician Trading Tracker includes built-in job scheduling using APScheduler, allowing automated data collection and maintenance tasks to run directly within the Streamlit app—no system cron access required.

## Key Features

- ✅ **Cloud-friendly**: Works on Streamlit Cloud, Heroku, Render, and other platforms
- ✅ **No system access needed**: Everything runs within the Streamlit app
- ✅ **Visual management**: Full UI for creating, monitoring, and managing jobs
- ✅ **Job history tracking**: View execution history and errors
- ✅ **Manual triggers**: Run any job on-demand from the UI
- ✅ **Flexible scheduling**: Support for both interval-based and cron-style schedules
- ✅ **Automatic startup**: Scheduler starts when the app starts
- ✅ **Singleton pattern**: Only one scheduler runs even with multiple workers

## How It Works

### Architecture

```
Streamlit App Start
        ↓
Initialize Scheduler (singleton)
        ↓
Load Jobs from UI/Config
        ↓
APScheduler Background Thread
        ↓
Jobs Execute on Schedule
        ↓
Results Logged & Tracked
```

### Components

1. **Scheduler Manager** (`src/politician_trading/scheduler/manager.py`)
   - Singleton instance manages APScheduler
   - Handles job lifecycle (add, remove, pause, resume)
   - Tracks execution history
   - Provides job metadata and status

2. **Job Functions** (`src/politician_trading/scheduler/jobs.py`)
   - `data_collection_job()`: Automated disclosure collection
   - `ticker_backfill_job()`: Find and update missing tickers
   - Designed to be called by APScheduler

3. **UI Page** (`pages/5_⏰_Scheduled_Jobs.py`)
   - Visual job management interface
   - View active jobs and their status
   - Add new jobs with custom schedules
   - View execution history
   - Manual job triggering

## Using In-App Scheduling

### Accessing the Scheduler UI

1. Start the Streamlit app:
   ```bash
   streamlit run app.py
   ```

2. Navigate to **⏰ Scheduled Jobs** in the sidebar

3. The scheduler automatically starts when the app starts

### Creating a Scheduled Job

#### Option 1: Quick Setup (Recommended)

1. Go to the **➕ Add New Job** tab
2. Select job type:
   - **Data Collection**: Automated disclosure scraping
   - **Ticker Backfill**: Update missing ticker symbols
3. Choose schedule type:
   - **Interval**: Run every X hours/minutes
   - **Cron**: Run at specific times (e.g., daily at 2 AM)
4. Configure settings and click **Add Job**

**Example: Daily Data Collection at 2 AM**
- Job type: Data Collection
- Schedule type: Cron (Time-based)
- Hour: 2
- Minute: 0
- Day of week: Every day

**Example: Ticker Backfill Every Week**
- Job type: Ticker Backfill
- Schedule type: Cron (Time-based)
- Hour: 3
- Minute: 0
- Day of week: Sunday

**Example: Data Collection Every 6 Hours**
- Job type: Data Collection
- Schedule type: Interval
- Hours: 6
- Minutes: 0

### Managing Jobs

#### View Active Jobs

The **📋 Active Jobs** tab shows all configured jobs with:
- Current status (running/paused)
- Next scheduled run time
- Last execution status
- Job controls

#### Job Controls

- **▶️ Resume**: Restart a paused job
- **⏸️ Pause**: Temporarily stop a job (doesn't delete it)
- **▶️ Run Now**: Immediately execute a job
- **🗑️ Remove**: Delete a job permanently

#### View Execution History

The **📊 Job History** tab shows:
- Last 50 job executions
- Timestamp of each run
- Success/failure status
- Error messages for failed jobs
- Filter by specific job

### Configuring Data Sources

When creating a **Data Collection** job, you can choose which sources to scrape:

- **US Congress**: House and Senate disclosures
- **EU Parliament**: EU member disclosures
- **UK Parliament**: UK MP disclosures
- **California**: State legislature disclosures

These selections are stored in Streamlit session state and persist for that job.

## Important Considerations

### App Uptime

**⚠️ Jobs only run while the Streamlit app is running**

- If you stop the app, jobs won't execute
- For production, deploy to a platform that keeps apps running 24/7
- Consider using system cron as a backup for critical jobs

### Cloud Deployments

**Works great on:**
- ✅ Streamlit Cloud (Community or Teams)
- ✅ Heroku
- ✅ Render
- ✅ Railway
- ✅ Google Cloud Run (with always-on instances)
- ✅ AWS ECS/Fargate (with service that stays running)

**Considerations:**
- Some free tiers may put apps to sleep after inactivity
- Ensure your deployment keeps the app running continuously
- Check platform docs for always-on options

### Multiple Workers

If deploying with multiple Streamlit workers/instances:

- The singleton pattern prevents duplicate schedulers **within a single process**
- Multiple processes (workers) will each have their own scheduler
- Jobs may execute multiple times concurrently
- **Solution**: Use a single worker, or implement distributed locking (advanced)

For most deployments, a single worker is sufficient and recommended.

### Resource Usage

- Jobs run in background threads within the Streamlit process
- Heavy jobs may impact app responsiveness
- Consider job duration and frequency
- Monitor app resource usage

## Monitoring

### View Logs

All job executions are logged to `logs/latest.log`:

```bash
# View all scheduled job logs
cat logs/latest.log | jq 'select(.logger | contains("scheduled"))'

# View data collection job logs
cat logs/latest.log | jq 'select(.logger == "politician_trading:scheduled_jobs") | select(.message | contains("collection"))'

# View job errors
cat logs/latest.log | jq 'select(.level == "ERROR") | select(.logger | contains("scheduled"))'

# Watch live
tail -f logs/latest.log | jq 'select(.logger | contains("scheduled"))'
```

### Job Status Indicators

- **✅ Success**: Job completed without errors
- **❌ Error**: Job failed (see error message)
- **⏸️ Paused**: Job is disabled
- **▶️ Active**: Job is scheduled to run

### Next Run Time

The UI shows when each job will run next:
- **"in X minutes"**: Less than 1 hour away
- **"in X hours"**: Less than 24 hours away
- **"in X days"**: More than 24 hours away
- **"Paused"**: Job is disabled

## Comparison: In-App vs System Cron

| Feature | In-App Scheduling | System Cron |
|---------|-------------------|-------------|
| **Cloud Platform Support** | ✅ Universal | ❌ Limited |
| **System Access Required** | ❌ No | ✅ Yes |
| **Visual Management** | ✅ UI included | ❌ Command-line only |
| **Setup Difficulty** | ⭐ Easy | ⭐⭐⭐ Moderate |
| **Reliability** | Depends on app uptime | ✅ Independent |
| **Resource Usage** | Shares with app | ✅ Separate process |
| **Job History** | ✅ Built-in tracking | ❌ Manual logging |
| **Manual Triggers** | ✅ One-click | ❌ CLI required |

### Recommended Approach

**For Cloud Deployments:**
- Use in-app scheduling (primary)
- Ensure app stays running
- Monitor via UI and logs

**For Self-Hosted/VPS:**
- Use system cron (primary)
- Use in-app scheduling as backup/supplement
- Manual triggers via UI when needed

**Hybrid (Best of Both):**
- Set up both in-app and system cron
- In-app for flexibility and monitoring
- System cron for reliability and independence
- Different schedules to avoid conflicts (e.g., in-app every 6h, cron daily)

## Troubleshooting

### Jobs Not Running

**Check scheduler status:**
1. Go to **⏰ Scheduled Jobs** page
2. Look for "✅ Scheduler is running" at top
3. If not running, try reloading the page

**Check job status:**
1. Go to **📋 Active Jobs** tab
2. Ensure job is not paused
3. Check "Next Run" time is in the future

**Check logs:**
```bash
cat logs/latest.log | jq 'select(.logger == "politician_trading:scheduler_manager")'
```

### Jobs Failing

1. Go to **📊 Job History** tab
2. Find failed execution
3. Read error message
4. Check full logs for more context:
   ```bash
   cat logs/latest.log | jq 'select(.level == "ERROR") | select(.logger | contains("scheduled"))'
   ```

### Scheduler Not Starting

**Check app logs:**
```bash
cat logs/latest.log | jq 'select(.message | contains("Scheduler"))'
```

**Common issues:**
- APScheduler not installed: `uv pip install "APScheduler>=3.10.0"`
- Import errors: Check Python path and module installation
- Permission errors: Ensure logs directory is writable

### Multiple Executions

If jobs are running more than once:

1. **Check for duplicate jobs:**
   - Go to **📋 Active Jobs**
   - Look for jobs with same name/ID
   - Remove duplicates

2. **Check multiple workers:**
   - Each worker process has its own scheduler
   - Configure deployment to use single worker
   - Or implement distributed locking (advanced)

## Advanced Usage

### Adding Custom Jobs

To add custom job functions:

1. Create job function in `src/politician_trading/scheduler/jobs.py`:

```python
def my_custom_job():
    """My custom scheduled job"""
    logger.info("Running my custom job")
    try:
        # Your code here
        pass
    except Exception as e:
        logger.error("Custom job failed", error=e)
        raise  # Re-raise for APScheduler tracking
```

2. Import in UI page `pages/5_⏰_Scheduled_Jobs.py`:

```python
from politician_trading.scheduler.jobs import my_custom_job
```

3. Add to job type dropdown and configuration

### Programmatic Job Management

Use the scheduler API directly:

```python
from politician_trading.scheduler import get_scheduler

scheduler = get_scheduler()

# Add a job
scheduler.add_cron_job(
    func=my_function,
    job_id="my_job",
    name="My Job",
    hour=2,
    minute=0,
    description="Runs daily at 2 AM"
)

# Run a job now
scheduler.run_job_now("my_job")

# Get job info
info = scheduler.get_job_info("my_job")
print(info["next_run"])

# Remove a job
scheduler.remove_job("my_job")
```

### Job Persistence

**Current Implementation:**
- Jobs are configured via UI each time
- Jobs are lost when app restarts
- Must recreate jobs after restart

**Future Enhancement:**
- Store job configurations in database
- Automatically restore jobs on startup
- Export/import job configurations

## Best Practices

1. **Start Simple**
   - Begin with one or two jobs
   - Use conservative schedules (e.g., daily, not hourly)
   - Monitor execution and adjust

2. **Monitor Regularly**
   - Check job history weekly
   - Watch for failures
   - Adjust schedules based on actual data volume

3. **Test Before Scheduling**
   - Use "Run Now" button to test jobs
   - Verify jobs complete successfully
   - Check logs for errors

4. **Avoid Overlapping Executions**
   - Space out jobs appropriately
   - Data collection and backfill shouldn't run simultaneously
   - Use different times/days

5. **Resource Management**
   - Don't over-schedule (too frequent jobs)
   - Monitor app performance
   - Consider job duration

6. **Have a Backup Plan**
   - Set up system cron as backup (if possible)
   - Document manual run procedures
   - Keep scripts in `scripts/` directory for manual execution

## Migration Guide

### From System Cron to In-App

If you already have system cron jobs:

1. **Note your existing schedule:**
   ```bash
   crontab -l
   ```

2. **Disable cron jobs** (or adjust frequency to avoid conflicts):
   ```bash
   crontab -e
   # Comment out or remove politician-trading jobs
   ```

3. **Set up in-app jobs with same schedule:**
   - Use the UI to recreate each job
   - Match the schedule to your cron settings
   - Test with "Run Now" before waiting for scheduled time

4. **Monitor both for a week:**
   - Keep cron jobs active but less frequent
   - Watch in-app jobs execute successfully
   - Once confident, fully remove cron jobs

### From In-App to System Cron

If you need to switch back:

1. **Note in-app job schedules** from UI
2. **Set up cron jobs** using `docs/scheduled-jobs.md`
3. **Remove in-app jobs** via UI
4. **Monitor cron execution** via logs

## FAQ

**Q: Do jobs run if I close my browser?**
A: Yes! Jobs run in the Streamlit app server, not in your browser. Closing the browser tab doesn't affect scheduled jobs.

**Q: What happens if the app restarts?**
A: The scheduler starts automatically, but jobs must be recreated via the UI. Job configurations are not persisted yet.

**Q: Can I schedule jobs to run every minute?**
A: Yes, technically, but it's not recommended. Very frequent jobs can impact app performance. Minimum recommended interval is 15 minutes.

**Q: How many jobs can I have?**
A: No hard limit, but practically 5-10 jobs is reasonable. Too many jobs may impact performance.

**Q: Can jobs run for a long time?**
A: Yes, but be aware that long-running jobs use resources and may affect app responsiveness. Aim for jobs under 5 minutes.

**Q: Does this work on Streamlit Cloud free tier?**
A: Yes! In-app scheduling works great on Streamlit Cloud. The app must stay running (not put to sleep), which is typical for the free tier as long as you access it regularly.

**Q: Can I export job configurations?**
A: Not yet, but this is planned for a future update.

## Next Steps

- **Try it**: Create your first scheduled job via the UI
- **Monitor**: Watch the execution history
- **Optimize**: Adjust schedules based on your data volume
- **Automate**: Set up additional jobs for other maintenance tasks

## Related Documentation

- [System Cron Setup](./scheduled-jobs.md) - Alternative/backup using system cron
- [Quick Start](./scheduled-jobs-quick-start.md) - Quick reference for cron
- [Logging Guide](./logging.md) - Understanding log output
- [Logging Locations](./logging-locations.md) - Where to find logs
