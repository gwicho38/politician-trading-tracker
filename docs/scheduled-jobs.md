# Scheduled Jobs Configuration

This document describes how to set up automated scheduled jobs for the Politician Trading Tracker to collect and update trading disclosure data regularly.

## Overview

The application provides two main scheduled job scripts:

1. **`scheduled_data_collection.py`** - Collects new trading disclosures from configured sources
2. **`backfill_tickers.py`** - Finds and updates missing ticker symbols in existing disclosures

## Prerequisites

- Python 3.10 or higher
- All dependencies installed (`uv sync` or equivalent)
- Environment variables configured (`.env` file with database credentials)
- Cron access on the server/machine

## Scripts

### 1. Data Collection Script

**Path**: `scripts/scheduled_data_collection.py`

**Purpose**: Automatically scrape and collect new politician trading disclosures from enabled sources.

**Configuration**: Edit the script to enable/disable sources:

```python
data_sources = {
    "us_congress": True,      # US Congress (House & Senate)
    "eu_parliament": False,   # EU Parliament
    "uk_parliament": False,   # UK Parliament
    "california": False,      # California state legislators
}

lookback_days = 7  # Number of days to look back (7 for weekly, 1 for daily)
```

**Usage**:
```bash
# Manual run
cd /Users/lefv/repos/politician-trading-tracker
python3 scripts/scheduled_data_collection.py

# Check exit code
echo $?  # 0 = success, 1 = errors occurred
```

**Logging**:
- Console output: Human-readable progress
- File logs: `logs/latest.log` (JSON format)
- Logger name: `politician_trading:scheduled_collection`

### 2. Ticker Backfill Script

**Path**: `scripts/backfill_tickers.py`

**Purpose**: Find disclosures with missing ticker symbols and populate them.

**Usage**:
```bash
# Manual run
cd /Users/lefv/repos/politician-trading-tracker
python3 scripts/backfill_tickers.py

# Check exit code
echo $?  # 0 = success, 1 = errors occurred
```

**Logging**:
- Console output: Progress with emoji indicators
- File logs: `logs/latest.log` (JSON format)
- Logger name: `politician_trading:scheduled_backfill`

## Cron Setup

### Recommended Schedule

```cron
# Politician Trading Tracker - Scheduled Jobs

# Collect new disclosures daily at 2 AM
0 2 * * * cd /Users/lefv/repos/politician-trading-tracker && /usr/bin/python3 scripts/scheduled_data_collection.py >> logs/cron.log 2>&1

# Backfill missing tickers weekly on Sunday at 3 AM
0 3 * * 0 cd /Users/lefv/repos/politician-trading-tracker && /usr/bin/python3 scripts/backfill_tickers.py >> logs/cron.log 2>&1
```

### Alternative Schedules

**Daily collection (every day at 2 AM)**:
```cron
0 2 * * * cd /Users/lefv/repos/politician-trading-tracker && /usr/bin/python3 scripts/scheduled_data_collection.py >> logs/cron.log 2>&1
```

**Twice daily collection (2 AM and 2 PM)**:
```cron
0 2,14 * * * cd /Users/lefv/repos/politician-trading-tracker && /usr/bin/python3 scripts/scheduled_data_collection.py >> logs/cron.log 2>&1
```

**Weekly collection (Sunday at 2 AM)**:
```cron
0 2 * * 0 cd /Users/lefv/repos/politician-trading-tracker && /usr/bin/python3 scripts/scheduled_data_collection.py >> logs/cron.log 2>&1
```

**Hourly collection (for high-frequency monitoring)**:
```cron
0 * * * * cd /Users/lefv/repos/politician-trading-tracker && /usr/bin/python3 scripts/scheduled_data_collection.py >> logs/cron.log 2>&1
```

### Installing Cron Jobs

1. Open your crontab for editing:
```bash
crontab -e
```

2. Add the desired cron jobs (see examples above)

3. Save and exit (in vi: `:wq`, in nano: `Ctrl+X` then `Y`)

4. Verify the cron jobs are installed:
```bash
crontab -l
```

### Environment Variables for Cron

Cron jobs run in a minimal environment. Ensure your `.env` file is in the project root and is readable, or specify environment variables directly in the crontab:

```cron
# Option 1: Load from .env (already handled by scripts)
0 2 * * * cd /Users/lefv/repos/politician-trading-tracker && /usr/bin/python3 scripts/scheduled_data_collection.py >> logs/cron.log 2>&1

# Option 2: Specify variables in crontab
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-key-here
0 2 * * * cd /Users/lefv/repos/politician-trading-tracker && /usr/bin/python3 scripts/scheduled_data_collection.py >> logs/cron.log 2>&1
```

## Monitoring and Logs

### Log Files

All scheduled jobs write to multiple log destinations:

1. **Cron output**: `logs/cron.log` (stdout/stderr from cron)
2. **Application logs**: `logs/latest.log` (JSON structured logs)
3. **Daily rotated logs**: `logs/YYYY-MM-DD.log` (archived by date)

### Viewing Logs

**Check recent cron execution**:
```bash
tail -f logs/cron.log
```

**Check structured logs**:
```bash
# View all scheduled collection logs
cat logs/latest.log | jq 'select(.logger | contains("scheduled_collection"))'

# View today's collection results
cat logs/latest.log | jq 'select(.message == "Data collection completed")'

# View backfill results
cat logs/latest.log | jq 'select(.logger | contains("scheduled_backfill"))'

# Check for errors
cat logs/latest.log | jq 'select(.level == "ERROR")'
```

**Monitor real-time execution**:
```bash
# Watch all logs
tail -f logs/latest.log | jq '.'

# Watch only scheduled jobs
tail -f logs/latest.log | jq 'select(.logger | contains("scheduled"))'
```

### Success Criteria

**Data Collection**:
- Exit code 0
- Log message: "Scheduled collection job completed successfully"
- `total_new_disclosures` > 0 (if new data available)

**Ticker Backfill**:
- Exit code 0
- Log message: "Ticker backfill completed"
- `total_updated` count shows number of tickers found

### Error Handling

Both scripts:
- Return exit code 0 on success
- Return exit code 1 on failure
- Log all errors with full context to `logs/latest.log`
- Continue processing even if individual items fail

**Check for failures**:
```bash
# Check exit codes in cron log
grep -i "error\|failed" logs/cron.log

# Check error logs
cat logs/latest.log | jq 'select(.level == "ERROR") | select(.logger | contains("scheduled"))'
```

## Testing

### Test Scripts Manually

Before setting up cron, test scripts manually:

```bash
# Test data collection
cd /Users/lefv/repos/politician-trading-tracker
python3 scripts/scheduled_data_collection.py

# Check logs
cat logs/latest.log | jq 'select(.logger == "politician_trading:scheduled_collection")' | tail -20

# Test ticker backfill
python3 scripts/backfill_tickers.py

# Check logs
cat logs/latest.log | jq 'select(.logger == "politician_trading:scheduled_backfill")' | tail -20
```

### Test Cron Schedule

Use `cron-next` or similar tools to verify cron schedule:

```bash
# Install cron-next (if needed)
npm install -g cron-next

# Test schedule - daily at 2 AM
cron-next "0 2 * * *"
# Output: Next run: 2025-11-02 02:00:00

# Test schedule - weekly on Sunday at 3 AM
cron-next "0 3 * * 0"
# Output: Next run: 2025-11-03 03:00:00
```

### Simulate Cron Environment

Test scripts in a cron-like environment:

```bash
# Run with minimal environment (like cron)
env -i HOME=$HOME PATH=/usr/bin:/bin python3 scripts/scheduled_data_collection.py

# Should still work because scripts load .env explicitly
```

## Customization

### Adjusting Collection Parameters

Edit `scripts/scheduled_data_collection.py`:

```python
# Change lookback period
lookback_days = 1  # Daily collection
lookback_days = 7  # Weekly collection
lookback_days = 30  # Monthly collection

# Enable/disable sources
data_sources = {
    "us_congress": True,      # Always enabled
    "eu_parliament": True,    # Enable EU data
    "uk_parliament": False,   # Disabled
    "california": True,       # Enable California
}
```

### Email Notifications

Add email notifications on failure:

```cron
MAILTO=your-email@example.com

# Collection with email on error
0 2 * * * cd /Users/lefv/repos/politician-trading-tracker && /usr/bin/python3 scripts/scheduled_data_collection.py >> logs/cron.log 2>&1 || echo "Data collection failed" | mail -s "PTT Collection Failed" $MAILTO
```

### Slack/Discord Notifications

Integrate with webhooks:

```bash
#!/bin/bash
# scripts/notify.sh

WEBHOOK_URL="your-webhook-url"
MESSAGE="$1"

curl -X POST -H 'Content-type: application/json' \
  --data "{\"text\":\"$MESSAGE\"}" \
  $WEBHOOK_URL
```

```cron
# Collection with Slack notification
0 2 * * * cd /Users/lefv/repos/politician-trading-tracker && /usr/bin/python3 scripts/scheduled_data_collection.py >> logs/cron.log 2>&1 && ./scripts/notify.sh "Data collection completed" || ./scripts/notify.sh "Data collection FAILED"
```

## Troubleshooting

### Cron Not Running

**Check cron service**:
```bash
# macOS
sudo launchctl list | grep cron

# Linux
sudo systemctl status cron
```

**Check cron logs**:
```bash
# macOS
log show --predicate 'process == "cron"' --last 1h

# Linux
grep CRON /var/log/syslog
```

### Permission Issues

```bash
# Ensure scripts are executable
chmod +x scripts/*.py

# Ensure logs directory exists and is writable
mkdir -p logs
chmod 755 logs
```

### Environment Variable Issues

```bash
# Test that .env is loaded
cd /Users/lefv/repos/politician-trading-tracker
python3 -c "from dotenv import load_dotenv; import os; load_dotenv(); print('SUPABASE_URL:', os.getenv('SUPABASE_URL'))"
```

### Path Issues

```bash
# Use absolute paths in crontab
which python3
# /usr/bin/python3

# Update crontab with absolute path
0 2 * * * cd /Users/lefv/repos/politician-trading-tracker && /usr/bin/python3 scripts/scheduled_data_collection.py >> logs/cron.log 2>&1
```

## Best Practices

1. **Test Before Scheduling**: Always test scripts manually before adding to cron
2. **Monitor Logs**: Regularly check logs for errors or warnings
3. **Use Absolute Paths**: Use full paths for Python, scripts, and log files in crontab
4. **Handle Failures Gracefully**: Scripts continue processing even if individual items fail
5. **Rotate Logs**: The logging system automatically rotates daily; clean up old logs periodically
6. **Set Appropriate Frequency**: Don't over-scrape sources; daily or weekly is usually sufficient
7. **Monitor Resource Usage**: Check database size and API rate limits
8. **Document Changes**: Update this file when modifying schedules or scripts

## Migration from lsh-framework Daemon

Previously, this project may have used the lsh-framework daemon for scheduling. The new approach uses standard cron jobs with standalone Python scripts that:

- Are simpler and more portable
- Don't require a daemon process
- Integrate with standard cron monitoring
- Use the same logging framework
- Are easier to debug and maintain

To migrate:
1. Stop the lsh-framework daemon (if running)
2. Remove daemon configuration
3. Set up cron jobs as documented above
4. Monitor logs to ensure jobs run successfully
