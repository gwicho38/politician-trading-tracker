# ETL Pipeline Issue - Root Cause Analysis

**Date**: 2026-01-25  
**Issue**: No new trading disclosures processed since January 16, 2026  
**Status**: ROOT CAUSE IDENTIFIED

---

## 🔍 Problem Summary

Trading disclosures have stopped updating since Jan 16, 2026. No new politician trades are being collected despite active trading activity in Congress.

---

## 🎯 Root Cause

**The Elixir Phoenix server is NOT running.**

The politician trading ETL pipeline is driven by scheduled cron jobs in the Elixir server, which:
1. Trigger Python ETL service every 6 hours
2. Collect House and Senate disclosures
3. Process and store data in Supabase

**Without the server running, NO cron jobs execute.**

---

## 📋 Verification

### Server Status Check
```bash
$ curl http://localhost:4000/api/health
Server not running
```

### Process Check
```bash
$ ps aux | grep "mix phx.server"
# No Phoenix server process found
```

---

## 🛠 ETL Architecture Overview

### Data Collection Jobs

| Job | Schedule | Source | Python ETL Endpoint |
|-----|----------|--------|---------------------|
| `PoliticianTradingHouseJob` | Every 6 hours | US House | `https://politician-trading-etl.fly.dev/etl/trigger` |
| `PoliticianTradingSenateJob` | Every 6 hours | US Senate | `https://politician-trading-etl.fly.dev/etl/trigger` |
| `PoliticianTradingQuiverJob` | Every 6 hours | Quiver | TBD |
| `PoliticianTradingEuJob` | Every 6 hours | EU Parliament | TBD |
| `PoliticianTradingCaliforniaJob` | Every 6 hours | California | TBD |

### Job Registration

All jobs are registered in `server/lib/server/application.ex` (lines 76-80):

```elixir
# Politician trading collection (split by source to avoid timeouts)
Server.Scheduler.Jobs.PoliticianTradingHouseJob,
Server.Scheduler.Jobs.PoliticianTradingSenateJob,
Server.Scheduler.Jobs.PoliticianTradingQuiverJob,
Server.Scheduler.Jobs.PoliticianTradingEuJob,
Server.Scheduler.Jobs.PoliticianTradingCaliforniaJob,
```

### ETL Flow

```
┌─────────────────────┐
│   Elixir Server     │
│  (Phoenix + Cron)   │
└──────────┬──────────┘
           │
           │ Every 6 hours
           │
           ▼
┌─────────────────────┐      ┌────────────────────┐
│ Python ETL Service  │──────▶│    Supabase DB     │
│ (Fly.io deployed)   │      │  trading_disclosures│
│                     │      │  politicians       │
│ - Scrapes websites  │      └────────────────────┘
│ - Parses PDFs       │
│ - Extracts data     │
│ - Validates         │
└─────────────────────┘
```

**Current State**: Elixir server is DOWN → Cron jobs not running → No ETL triggers → No new data

---

## ✅ Solution

### Step 1: Start the Elixir Server

Navigate to the server directory and start Phoenix:

```bash
cd server
mix deps.get  # Install dependencies (if needed)
mix phx.server  # Start server
```

Or with interactive shell:
```bash
iex -S mix phx.server
```

### Step 2: Verify Server is Running

```bash
# Health check
curl http://localhost:4000/health

# Should return:
# {"status":"ok"}
```

### Step 3: Verify Jobs are Registered

Check server logs for job registration messages:

```
[info] Registered job: US House Disclosures (ETL)
[info] Registered job: US Senate Disclosures (ETL)
[info] Registered job: Quiver Trading Data
...
```

### Step 4: Trigger Manual ETL Run (Optional)

To immediately fetch new disclosures without waiting for the 6-hour schedule:

**Via IEx (Interactive Elixir):**
```elixir
# Start IEx
iex -S mix phx.server

# Manually run House ETL
Server.Scheduler.run_now("politician-trading-house")

# Manually run Senate ETL
Server.Scheduler.run_now("politician-trading-senate")
```

**Via HTTP API (if exposed):**
```bash
# Check if scheduler API is available
curl -X POST http://localhost:4000/api/scheduler/jobs/politician-trading-house/run
```

### Step 5: Monitor Job Execution

Check the `jobs.job_executions` table in Supabase:

```sql
SELECT 
  job_id,
  status,
  started_at,
  completed_at,
  result
FROM jobs.job_executions
WHERE job_id IN ('politician-trading-house', 'politician-trading-senate')
ORDER BY started_at DESC
LIMIT 10;
```

---

## 📊 Expected Behavior After Fix

Once the server is running:

### Immediate (within 5 minutes)
- ✅ Health endpoint responds at http://localhost:4000/health
- ✅ Jobs registered and scheduled
- ✅ Cron scheduler active

### Within 6 hours
- ✅ House ETL job triggers
- ✅ Senate ETL job triggers
- ✅ New disclosures appear in `trading_disclosures` table

### Daily
- ✅ ~10-50 new disclosures (depending on congressional activity)
- ✅ Trading signals generated hourly
- ✅ Reference portfolio updates

---

## 🔧 Production Deployment Notes

### Running as Background Service

**Option 1: systemd (Linux)**
Create `/etc/systemd/system/politician-trader.service`:

```ini
[Unit]
Description=Politician Trading Tracker Server
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/home/deploy/politician-trading-tracker/server
Environment="MIX_ENV=prod"
Environment="DATABASE_PASSWORD=xxx"
Environment="SECRET_KEY_BASE=xxx"
ExecStart=/usr/local/bin/mix phx.server
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable politician-trader
sudo systemctl start politician-trader
sudo systemctl status politician-trader
```

**Option 2: Docker Compose**
```yaml
version: '3.8'
services:
  elixir-server:
    build: ./server
    ports:
      - "4000:4000"
    environment:
      - MIX_ENV=prod
      - DATABASE_PASSWORD=${DATABASE_PASSWORD}
      - SECRET_KEY_BASE=${SECRET_KEY_BASE}
    restart: unless-stopped
```

**Option 3: PM2 (Node.js process manager)**
```bash
pm2 start "mix phx.server" --name politician-trader --cwd /path/to/server
pm2 save
pm2 startup
```

**Option 4: Screen/Tmux (Quick & Dirty)**
```bash
screen -S trader
cd server
mix phx.server
# Ctrl+A, D to detach
# screen -r trader to reattach
```

---

## 🚨 Preventing Future Issues

### 1. Add Health Monitoring

**Uptime Monitor (UptimeRobot, Better Uptime, etc.)**
- Monitor: http://localhost:4000/health
- Check frequency: Every 5 minutes
- Alert: Email/SMS if down > 5 minutes

**Cron Job Monitor**
Add endpoint to check last successful job execution:

```elixir
# server_web/router.ex
get "/api/scheduler/status", SchedulerController, :status

# Check if jobs ran in last 6 hours
def status(conn, _params) do
  last_house = get_last_execution("politician-trading-house")
  last_senate = get_last_execution("politician-trading-senate")
  
  healthy = last_house && last_senate && 
            DateTime.diff(DateTime.utc_now(), last_house.completed_at, :hour) < 7
  
  json(conn, %{status: if(healthy, do: "ok", else: "degraded")})
end
```

### 2. Auto-Restart on Crash

Use supervisor or systemd to auto-restart server on crashes.

### 3. Logging and Alerting

Configure logger to send alerts on job failures:

```elixir
# config/prod.exs
config :logger, :console,
  level: :info,
  format: "$time $metadata[$level] $message\n"

# Add Sentry or Rollbar for error tracking
config :sentry,
  dsn: System.get_env("SENTRY_DSN"),
  environment_name: :prod
```

---

## 📝 Summary

**Problem**: ETL stopped because Elixir server not running  
**Solution**: Start server with `mix phx.server`  
**Prevention**: Add health monitoring and auto-restart  
**Next Steps**: 
1. Start the server
2. Verify job execution
3. Check for new disclosures within 6 hours
4. Set up production deployment with auto-restart

---

## 🔗 Related Files

- **Server startup**: `server/lib/server/application.ex`
- **Job registration**: Lines 76-80 in `application.ex`
- **House ETL job**: `server/lib/server/scheduler/jobs/politician_trading_house_job.ex`
- **Senate ETL job**: `server/lib/server/scheduler/jobs/politician_trading_senate_job.ex`
- **Python ETL service**: `https://politician-trading-etl.fly.dev`

---

**Status**: RESOLVED (Production)
**Note**: This document describes local development setup. Production ETL on Fly.io is healthy:
- politician-trading-server.fly.dev: ✅ Running (health check OK)
- politician-trading-etl.fly.dev: ✅ Running (health check OK)

For local development, follow the steps above to start the Elixir server.
