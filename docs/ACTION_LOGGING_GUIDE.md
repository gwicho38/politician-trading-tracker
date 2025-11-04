# Action Logging Implementation Guide

Quick reference for understanding and implementing action logging in the politician-trading-tracker.

## Quick Overview

The application has **10 main action triggers** across:
- **Manual UI buttons:** 7 actions
- **Scheduled jobs:** 1 trigger type  
- **App startup:** 2 recovery actions

## Action Trigger Locations

### 1. Manual Data Collection
- **File:** `pages/1_📥_Data_Collection.py` (line 119)
- **Button:** "🚀 Start Collection"
- **Logging:** Automatic via `PoliticianTradingWorkflow`
- **Database:** `data_pull_jobs` table
- **Logs:** `logs/YYYY-MM-DD.log`

### 2. Manual Ticker Backfill
- **File:** `pages/1_📥_Data_Collection.py` (line 392)
- **Button:** "🔄 Backfill Missing Tickers"
- **Logging:** Via `logger.info()` calls
- **Database:** `trading_disclosures` table updates
- **Logs:** `logs/YYYY-MM-DD.log`

### 3. Add Interval Job (Scheduled)
- **File:** `pages/5_⏰_Scheduled_Jobs.py` (line 233)
- **Button:** "➕ Add Interval Job"
- **Handler:** `scheduler.add_interval_job()`
- **Database:** `scheduled_jobs` table
- **Logs:** `logs/YYYY-MM-DD.log`

### 4. Add Cron Job (Scheduled)
- **File:** `pages/5_⏰_Scheduled_Jobs.py` (line 340)
- **Button:** "➕ Add Cron Job"
- **Handler:** `scheduler.add_cron_job()`
- **Database:** `scheduled_jobs` table
- **Logs:** `logs/YYYY-MM-DD.log`

### 5. Run Job Now (Manual)
- **File:** `pages/5_⏰_Scheduled_Jobs.py` (line 155)
- **Button:** "▶️ Run Now"
- **Handler:** `scheduler.run_job_now(job_id)`
- **Database:** `job_executions` table
- **Logs:** `logs/YYYY-MM-DD.log`

### 6. Pause Job
- **File:** `pages/5_⏰_Scheduled_Jobs.py` (line 148)
- **Button:** "⏸️ Pause"
- **Handler:** `scheduler.pause_job(job_id)`
- **Database:** `scheduled_jobs` table
- **Logs:** `logs/YYYY-MM-DD.log`

### 7. Resume Job
- **File:** `pages/5_⏰_Scheduled_Jobs.py` (line 141)
- **Button:** "▶️ Resume"
- **Handler:** `scheduler.resume_job(job_id)`
- **Database:** `scheduled_jobs` table
- **Logs:** `logs/YYYY-MM-DD.log`

### 8. Remove Job
- **File:** `pages/5_⏰_Scheduled_Jobs.py` (line 162)
- **Button:** "🗑️ Remove"
- **Handler:** `scheduler.remove_job(job_id)`
- **Database:** `scheduled_jobs` table
- **Logs:** `logs/YYYY-MM-DD.log`

### 9. Scheduled Job Execution
- **File:** `src/politician_trading/scheduler/manager.py` (line 325)
- **Trigger:** APScheduler time-based trigger
- **Handler:** Job wrapper function
- **Database:** `job_executions` table
- **Logs:** Both file + database (in `logs` column)

### 10. Job Recovery on Startup
- **File:** `src/politician_trading/scheduler/manager.py` (line 318)
- **Trigger:** App initialization
- **Handler:** `_recover_missed_jobs()`
- **Database:** `scheduled_jobs` and `job_executions` tables
- **Logs:** `logs/YYYY-MM-DD.log`

---

## Current Logging Infrastructure

### File Logging
```
Location: /Users/lefv/repos/politician-trading-tracker/logs/
Format:   JSON (structured)
Handler:  logging.FileHandler
Pattern:  YYYY-MM-DD.log (daily files)
Latest:   logs/latest.log (symlink)
```

### Sample Log Entry (File)
```json
{
    "timestamp": "2025-11-03T14:30:45.123456",
    "level": "INFO",
    "message": "Start Collection button clicked",
    "logger": "data_collection_page",
    "metadata": {
        "us_congress": true,
        "eu_parliament": false,
        "lookback_days": 30,
        "max_retries": 3
    }
}
```

### Console Logging
```
Format:   Colored text with ANSI codes
Handler:  logging.StreamHandler(stdout)
Pattern:  [timestamp] LEVEL [logger_name] message {metadata}
Colors:   DEBUG (cyan), INFO (green), WARNING (yellow), ERROR (red)
```

### Sample Log Entry (Console)
```
2025-11-03T14:30:45 INFO     [data_collection_page] Start Collection button clicked {"us_congress": true, "lookback_days": 30}
```

---

## Database Tables for Logging

### `job_executions` Table
Stores execution history of all scheduled jobs.

```sql
- id (UUID) - Primary key
- job_id (VARCHAR) - Job identifier (e.g., "data_collection")
- status (VARCHAR) - 'success', 'failed', 'cancelled'
- started_at (TIMESTAMPTZ) - Execution start time
- completed_at (TIMESTAMPTZ) - Execution end time
- duration_seconds (DECIMAL) - Total execution time
- error_message (TEXT) - Error if failed
- logs (TEXT) - Full execution logs (newline separated)
- metadata (JSONB) - Additional context
- created_at (TIMESTAMPTZ) - Record creation time
```

**Useful Queries:**
```sql
-- Last 10 executions of a job
SELECT * FROM job_executions 
WHERE job_id = 'data_collection'
ORDER BY started_at DESC
LIMIT 10;

-- Failed executions today
SELECT * FROM job_executions
WHERE status = 'failed' 
AND started_at >= NOW() - INTERVAL '1 day'
ORDER BY started_at DESC;

-- Success rate for a job
SELECT 
    job_id,
    COUNT(*) as total,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successes,
    ROUND(100.0 * SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM job_executions
WHERE started_at >= NOW() - INTERVAL '7 days'
GROUP BY job_id;
```

### `scheduled_jobs` Table
Stores job definitions and status.

```sql
- id (UUID) - Primary key
- job_id (VARCHAR) - Unique job identifier
- job_name (VARCHAR) - Human-readable name
- job_function (VARCHAR) - Full Python path
- schedule_type (VARCHAR) - 'interval' or 'cron'
- schedule_value (VARCHAR) - Schedule definition
- enabled (BOOLEAN) - Whether job is active
- last_successful_run (TIMESTAMPTZ) - Last success time
- last_attempted_run (TIMESTAMPTZ) - Last attempt time
- next_scheduled_run (TIMESTAMPTZ) - Next run time
- consecutive_failures (INTEGER) - Failure counter
- max_consecutive_failures (INTEGER) - Failure threshold
- auto_retry_on_startup (BOOLEAN) - Recover on startup
- metadata (JSONB) - Job metadata
- created_at / updated_at (TIMESTAMPTZ) - Timestamps
```

**Useful Queries:**
```sql
-- All enabled jobs
SELECT job_id, job_name, schedule_type, schedule_value, next_scheduled_run
FROM scheduled_jobs
WHERE enabled = true
ORDER BY next_scheduled_run;

-- Jobs that are overdue
SELECT job_id, job_name, next_scheduled_run, consecutive_failures
FROM scheduled_jobs
WHERE enabled = true AND next_scheduled_run <= NOW();

-- Job status summary
SELECT 
    job_id,
    job_name,
    CASE 
        WHEN NOT enabled THEN 'disabled'
        WHEN consecutive_failures >= max_consecutive_failures THEN 'failed_max_retries'
        WHEN next_scheduled_run <= NOW() THEN 'overdue'
        ELSE 'scheduled'
    END as job_status,
    last_successful_run,
    consecutive_failures
FROM scheduled_jobs;
```

### `scheduled_jobs_status` View
Pre-built view combining job definitions with last execution status.

```sql
SELECT * FROM scheduled_jobs_status
WHERE job_status IN ('overdue', 'failed_max_retries')
ORDER BY job_id;
```

### `job_execution_summary` View
Pre-built view with aggregated statistics per job.

```sql
SELECT * FROM job_execution_summary
ORDER BY last_execution DESC;
```

---

## Recommended Implementation: Action Logs Table

Create a dedicated table for user actions:

```sql
CREATE TABLE action_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action_type VARCHAR(50) NOT NULL,
    user_id VARCHAR(255),
    action_timestamp TIMESTAMPTZ DEFAULT NOW(),
    action_details JSONB,
    job_id VARCHAR(100),
    job_execution_id UUID,
    status VARCHAR(20),
    result_message TEXT,
    error_message TEXT,
    source VARCHAR(50),
    ip_address VARCHAR(45),
    user_agent TEXT,
    request_duration_seconds DECIMAL(10,3),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_action_logs_action_type ON action_logs(action_type);
CREATE INDEX idx_action_logs_user_id ON action_logs(user_id);
CREATE INDEX idx_action_logs_timestamp ON action_logs(action_timestamp DESC);
CREATE INDEX idx_action_logs_job_id ON action_logs(job_id);
CREATE INDEX idx_action_logs_status ON action_logs(status);
```

---

## Logging Utility Functions (Recommended)

### Create `src/politician_trading/utils/action_logger.py`:

```python
from datetime import datetime
from typing import Optional, Dict, Any
from politician_trading.database.database import SupabaseClient
from politician_trading.config import SupabaseConfig
from politician_trading.utils.logger import create_logger

logger = create_logger("action_logger")

def log_action(
    action_type: str,
    status: str,
    action_details: Dict[str, Any] = None,
    job_id: Optional[str] = None,
    job_execution_id: Optional[str] = None,
    error_message: Optional[str] = None,
    result_message: Optional[str] = None,
    source: str = "ui_button",
    user_id: Optional[str] = None,
    duration_seconds: Optional[float] = None
) -> Optional[str]:
    """
    Log an action to action_logs table.
    
    Args:
        action_type: Type of action (e.g., 'data_collection_start')
        status: Action status ('initiated', 'in_progress', 'completed', 'failed')
        action_details: Dict of action-specific data
        job_id: Job ID if related to a scheduled job
        job_execution_id: Job execution ID if related to job execution
        error_message: Error message if action failed
        result_message: Result/success message
        source: Source of action ('ui_button', 'scheduled_job', 'api', 'recovery')
        user_id: Username or user ID
        duration_seconds: Duration of action
        
    Returns:
        action_log_id if successful, None if failed
    """
    try:
        config = SupabaseConfig.from_env()
        db = SupabaseClient(config)
        
        action_record = {
            "action_type": action_type,
            "status": status,
            "action_details": action_details or {},
            "job_id": job_id,
            "job_execution_id": job_execution_id,
            "error_message": error_message,
            "result_message": result_message,
            "source": source,
            "user_id": user_id,
            "action_timestamp": datetime.now().isoformat(),
            "request_duration_seconds": duration_seconds,
        }
        
        response = db.client.table("action_logs").insert(action_record).execute()
        
        if response.data:
            action_id = response.data[0]["id"]
            logger.debug(f"Logged action: {action_type}", metadata={
                "action_id": action_id,
                "status": status,
                "user_id": user_id
            })
            return action_id
        return None
        
    except Exception as e:
        logger.error(f"Failed to log action {action_type}: {e}", metadata={
            "action_type": action_type,
            "status": status
        })
        # Don't fail main operation if logging fails
        return None
```

---

## Integration Points

### In Data Collection Page (`pages/1_📥_Data_Collection.py`)

**Add logging at line 120 (after Start Collection button clicked):**
```python
from politician_trading.utils.action_logger import log_action

if st.button("🚀 Start Collection", ...):
    user_id = st.session_state.get("user_email", "unknown")
    action_id = log_action(
        action_type="data_collection_start",
        status="initiated",
        source="ui_button",
        user_id=user_id,
        action_details={
            "sources": enabled_sources,
            "lookback_days": lookback_days,
            "max_retries": max_retries
        }
    )
    # Continue with collection...
```

### In Scheduled Jobs Manager (`src/politician_trading/scheduler/manager.py`)

**Add logging when job completes (in job wrapper, around line 360):**
```python
from politician_trading.utils.action_logger import log_action

duration = time.time() - start_time

log_action(
    action_type="job_execution",
    status="completed",
    source="scheduled_job",
    job_id=job_id,
    action_details={"result": result},
    duration_seconds=duration
)
```

---

## Log Querying Examples

### Using Python/Streamlit:

```python
from politician_trading.database.database import SupabaseClient
from politician_trading.config import SupabaseConfig

config = SupabaseConfig.from_env()
db = SupabaseClient(config)

# Get recent data collection actions
response = db.client.table("action_logs")\
    .select("*")\
    .eq("action_type", "data_collection_start")\
    .order("action_timestamp", desc=True)\
    .limit(10)\
    .execute()

for action in response.data:
    print(f"{action['action_timestamp']}: {action['action_type']} - {action['status']}")
```

### Using SQL (Supabase console):

```sql
-- All actions in the last 24 hours
SELECT action_type, status, COUNT(*) as count
FROM action_logs
WHERE action_timestamp >= NOW() - INTERVAL '1 day'
GROUP BY action_type, status
ORDER BY count DESC;

-- User activity
SELECT user_id, COUNT(*) as action_count, COUNT(DISTINCT action_type) as unique_actions
FROM action_logs
WHERE action_timestamp >= NOW() - INTERVAL '7 days'
GROUP BY user_id
ORDER BY action_count DESC;

-- Failed actions
SELECT * FROM action_logs
WHERE status = 'failed' AND action_timestamp >= NOW() - INTERVAL '1 day'
ORDER BY action_timestamp DESC;
```

---

## Next Steps

1. Create `action_logs` table in Supabase using the schema above
2. Create `src/politician_trading/utils/action_logger.py` with the utility function
3. Integrate logging at the 10 action trigger points
4. Add UI page to display action logs and analytics
5. Create Streamlit dashboard showing action history and statistics

---

**Last Updated:** November 3, 2025
**Related Documents:** 
- `/docs/CODEBASE_ARCHITECTURE.md` - Detailed architecture analysis
- `/docs/logging.md` - Logging framework documentation
- `/src/politician_trading/utils/logger.py` - Logger implementation
