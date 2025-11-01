# Scheduled Jobs Quick Start

Quick reference for setting up automated data collection.

## Scripts Created

1. **`scripts/scheduled_data_collection.py`** - Main data collection job
2. **`scripts/backfill_tickers.py`** - Ticker backfill job (enhanced with logging)
3. **`scripts/test_scheduled_jobs.sh`** - Test script for validation

## Quick Setup

### 1. Test the Scripts

```bash
cd /Users/lefv/repos/politician-trading-tracker

# Test both scripts
./scripts/test_scheduled_jobs.sh

# Or test individually
python3 scripts/scheduled_data_collection.py
python3 scripts/backfill_tickers.py
```

### 2. Configure Data Sources

Edit `scripts/scheduled_data_collection.py` to enable/disable sources:

```python
# Line ~36-40
enable_us_congress = True      # Currently enabled
enable_eu_parliament = False   # Change to True to enable
enable_uk_parliament = False   # Change to True to enable
enable_california = False      # Change to True to enable
enable_us_states = False       # Change to True to enable
```

### 3. Install Cron Jobs

```bash
# Edit crontab
crontab -e

# Add these lines for daily collection:
# Daily data collection at 2 AM
0 2 * * * cd /Users/lefv/repos/politician-trading-tracker && /usr/bin/python3 scripts/scheduled_data_collection.py >> logs/cron.log 2>&1

# Weekly ticker backfill on Sunday at 3 AM
0 3 * * 0 cd /Users/lefv/repos/politician-trading-tracker && /usr/bin/python3 scripts/backfill_tickers.py >> logs/cron.log 2>&1

# Save and exit (:wq in vi, Ctrl+X in nano)
```

### 4. Verify Cron Installation

```bash
# Check installed cron jobs
crontab -l

# Should show the two jobs you just added
```

## Monitoring

### View Logs

```bash
# Follow cron output
tail -f logs/cron.log

# View structured logs (JSON)
tail -f logs/latest.log | jq '.'

# View only scheduled job logs
cat logs/latest.log | jq 'select(.logger | contains("scheduled"))'

# Check for errors
cat logs/latest.log | jq 'select(.level == "ERROR")'
```

### Check Last Run

```bash
# View last data collection result
cat logs/latest.log | jq 'select(.message == "Data collection completed")' | tail -1

# View last backfill result
cat logs/latest.log | jq 'select(.message == "Ticker backfill completed")' | tail -1
```

## Schedules

**Recommended**:
- Data collection: Daily at 2 AM
- Ticker backfill: Weekly on Sunday at 3 AM

**Alternative schedules** (see full docs for more):

```cron
# Twice daily
0 2,14 * * * cd /Users/lefv/repos/politician-trading-tracker && /usr/bin/python3 scripts/scheduled_data_collection.py >> logs/cron.log 2>&1

# Hourly (for very active monitoring)
0 * * * * cd /Users/lefv/repos/politician-trading-tracker && /usr/bin/python3 scripts/scheduled_data_collection.py >> logs/cron.log 2>&1

# Weekly on Sunday
0 2 * * 0 cd /Users/lefv/repos/politician-trading-tracker && /usr/bin/python3 scripts/scheduled_data_collection.py >> logs/cron.log 2>&1
```

## Troubleshooting

**Job not running?**
```bash
# Check cron service (macOS)
sudo launchctl list | grep cron

# Check cron logs (macOS)
log show --predicate 'process == "cron"' --last 1h
```

**Permission errors?**
```bash
# Ensure scripts are executable
chmod +x scripts/*.py scripts/*.sh

# Ensure logs directory exists
mkdir -p logs
```

**Environment variables missing?**
```bash
# Verify .env file exists and has required variables
cat .env | grep SUPABASE
```

## Full Documentation

For complete documentation, see:
- **[docs/scheduled-jobs.md](./scheduled-jobs.md)** - Full setup guide with all options
- **[docs/logging-locations.md](./logging-locations.md)** - Logging reference

## What Gets Logged

Both scripts log comprehensively:

**Data Collection**:
- Enabled sources
- Database connection
- Collection results per source
- Total new/updated disclosures
- Errors with full context

**Ticker Backfill**:
- Number of disclosures missing tickers
- Progress updates every 100 items
- Update success/failure per ticker
- Summary of all updates

All logs are written to:
- `logs/latest.log` (JSON format, current day)
- `logs/YYYY-MM-DD.log` (JSON format, archived by date)
- `logs/cron.log` (stdout/stderr from cron)
