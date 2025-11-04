# Politician Trading Tracker - Codebase Architecture Analysis

## Executive Summary

The politician-trading-tracker is a sophisticated Streamlit-based application that collects and analyzes politician trading disclosures from multiple sources globally. The application has:

- **Multiple action triggers** for data collection (manual, scheduled, manual job execution)
- **Comprehensive logging system** with file and console output
- **Database schema** with tables for politicians, disclosures, jobs, and execution history
- **In-app scheduler** using APScheduler for background job execution
- **Persistent job tracking** for recovery and failure handling

---

## 1. ALL ACTION TRIGGERS (Entry Points)

### A. Manual Action Triggers (UI-Based)

#### 1.1 Data Collection Page (`pages/1_📥_Data_Collection.py`)
- **Trigger:** "🚀 Start Collection" button
- **Handler:** Lines 119-131
- **Actions:**
  - Loads selected data sources (US Congress, EU Parliament, UK Parliament, California, US States, QuiverQuant)
  - Configures collection parameters (lookback period, retry count)
  - Initializes `PoliticianTradingWorkflow` with selected sources
  - Executes full data collection asynchronously
  - Updates UI with progress and results

```python
if st.button("🚀 Start Collection", disabled=st.session_state.collection_running, width="stretch"):
    logger.info("Start Collection button clicked", metadata={...})
    st.session_state.collection_running = True
    # Initiates: workflow.run_full_collection()
```

**Log Location:** Captured in `logs/YYYY-MM-DD.log`

#### 1.2 Ticker Backfill (Manual)
- **Trigger:** "🔄 Backfill Missing Tickers" button (Data Collection Page, Line 392)
- **Handler:** Lines 392-468
- **Actions:**
  - Queries disclosures with missing/empty tickers
  - Extracts tickers from asset names
  - Updates database records
  - Provides progress feedback

**Log Location:** `logs/YYYY-MM-DD.log`

#### 1.3 Scheduled Jobs Management UI (`pages/5_⏰_Scheduled_Jobs.py`)
- **Trigger 1:** "➕ Add Interval Job" (Line 233)
  - Configures interval-based schedules (hours, minutes, seconds)
  - Calls `scheduler.add_interval_job()`
  - Persists to database for recovery
  
- **Trigger 2:** "➕ Add Cron Job" (Line 340)
  - Configures cron-style schedules
  - Calls `scheduler.add_cron_job()`
  - Persists to database
  
- **Trigger 3:** "▶️ Run Now" (Line 155)
  - Manually trigger job to run immediately
  - Calls `scheduler.run_job_now(job_id)`
  
- **Trigger 4:** "⏸️ Pause" / "▶️ Resume" (Lines 141-153)
  - Pause/resume scheduled jobs
  - Calls `scheduler.pause_job()` / `scheduler.resume_job()`

**Log Location:** `logs/YYYY-MM-DD.log` and `job_executions` table

#### 1.4 Main App Initialization (`app.py`)
- **Trigger:** App startup
- **Handler:** Lines 56-62
- **Actions:**
  - Initializes scheduler singleton
  - Loads jobs from database
  - Recovers missed jobs
  - Starts background scheduler

```python
scheduler = get_scheduler()  # Lines 59
# This triggers:
# - _load_jobs_from_database()
# - _recover_missed_jobs()
# - scheduler.start()
```

---

### B. Scheduled Triggers (APScheduler)

#### 2.1 Interval-Based Jobs
**Location:** `src/politician_trading/scheduler/manager.py`

- **Data Collection Job**
  - Default: Every 24 hours
  - Created via: `scheduler.add_interval_job()`
  - Function: `politician_trading.scheduler.jobs.data_collection_job()`
  - Execution: Background thread pool
  
- **Ticker Backfill Job**
  - Default: Every 168 hours (7 days)
  - Function: `politician_trading.scheduler.jobs.ticker_backfill_job()`

**Scheduling Code (manager.py, Line 512-640):**
```python
def add_interval_job(self, func, job_id, name, hours, minutes, seconds):
    trigger = IntervalTrigger(hours=hours, minutes=minutes, seconds=seconds)
    self.scheduler.add_job(wrapped_func, trigger=trigger, id=job_id)
    # Also registers in database via _register_job_in_database()
```

#### 2.2 Cron-Based Jobs
**Location:** `src/politician_trading/scheduler/manager.py`, Lines 424-510

- Configured via UI with hour, minute, day_of_week
- Example: Daily at 2 AM UTC
- Execution: Background thread pool

**Trigger Creation (manager.py, Line 468):**
```python
trigger = CronTrigger(hour=hour, minute=minute, day_of_week=day_of_week)
```

#### 2.3 Job Recovery on App Startup
**Location:** `src/politician_trading/scheduler/manager.py`, Lines 751-793

- **Function:** `_recover_missed_jobs()`
- **Trigger:** On `SchedulerManager.__init__()` (Line 318)
- **Query:** 
  ```sql
  SELECT * FROM scheduled_jobs
  WHERE enabled=true AND auto_retry_on_startup=true 
  AND next_scheduled_run <= NOW()
  AND consecutive_failures < max_consecutive_failures
  ```
- **Actions:**
  - Fetches overdue jobs from database
  - Executes missed jobs immediately
  - Updates job status in database

---

## 2. CURRENT LOGGING PATTERNS

### 2.1 Logging Implementation
**Location:** `src/politician_trading/utils/logger.py`

**Logger Class:** `PTTLogger`
- Uses Python's standard `logging` module
- Supports colored terminal output (ANSI codes)
- JSON formatting for file storage
- Structured logging with metadata support

### 2.2 Log Output Configuration

#### Console Output (stdout)
- **Format:** Colored text with ANSI codes
- **Handler:** `logging.StreamHandler(sys.stdout)`
- **Formatter:** `ColoredFormatter`
- **Levels:** DEBUG, INFO, WARNING (yellow), ERROR (red), CRITICAL (red background)

#### File Output
- **Location:** `logs/YYYY-MM-DD.log`
- **Format:** JSON (structured logging)
- **Handler:** `logging.FileHandler`
- **Formatter:** `JSONFormatter`
- **Latest Log:** Symlink `logs/latest.log` points to today's log
- **Retention:** Directory structure: `logs/2025-11-03.log`

### 2.3 Logging in Different Contexts

#### Data Collection Pages
```python
logger = create_logger("data_collection_page")
logger.info("Start Collection button clicked", metadata={...})
```

#### Scheduler
```python
logger = create_logger("scheduler_manager")
logger.info("Adding cron job", metadata={"job_id": "...", "schedule": "..."})
```

#### Database Operations
```python
logger = create_logger("database")
logger.info("Supabase client initialized successfully")
logger.error("Failed to upsert politician", error=e)
```

#### Scheduled Jobs
```python
logger = create_logger("scheduled_jobs")
logger.info("Starting scheduled data collection job (in-app)")
```

### 2.4 Metadata Logging Pattern
All loggers support structured metadata:
```python
logger.info("Message", metadata={
    "key1": "value1",
    "key2": 123,
    "list": ["item1", "item2"]
})
```

**Output (File):**
```json
{
    "timestamp": "2025-11-03T14:30:45.123456",
    "level": "INFO",
    "message": "Message",
    "logger": "scheduler_manager",
    "metadata": {
        "key1": "value1",
        "key2": 123
    }
}
```

### 2.5 Log Levels Used
- **DEBUG:** Detailed diagnostic information
- **INFO:** Confirmation of expected events
- **WARNING:** Warnings about potential issues
- **ERROR:** Error events with exception info
- **CRITICAL:** Critical errors

### 2.6 Existing Log Locations
```
/Users/lefv/repos/politician-trading-tracker/
├── logs/
│   ├── 2025-11-03.log       (today's log)
│   ├── 2025-11-02.log       (previous days)
│   ├── latest.log           (symlink to today's)
│   └── [YYYY-MM-DD].log     (dated logs)
```

---

## 3. DATABASE SCHEMA & LOGGING TABLES

### 3.1 Core Data Tables

#### Table: `politicians`
- Stores politician information
- Fields: id, first_name, last_name, full_name, role, party, state_or_country, district, term dates, bioguide_id, eu_id, timestamps

#### Table: `trading_disclosures`
- Stores individual trading disclosures
- Fields: id, politician_id, transaction_date, disclosure_date, transaction_type, asset_name, asset_ticker, asset_type, amount ranges, source info, status, processing_notes, timestamps

#### Table: `data_pull_jobs`
- Tracks overall data collection jobs
- Fields: id, job_type, status (pending/running/completed/failed), started_at, completed_at, records (found/processed/new/updated/failed), error_message, error_details, config_snapshot, created_at
- Note: Used for data collection tracking (not execution history)

#### Table: `data_sources`
- Tracks data source information
- Fields: id, name, url, source_type, region, is_active, last_successful_pull, last_attempt, consecutive_failures, request_config, timestamps

### 3.2 Execution & Job Tracking Tables

#### Table: `job_executions` (APScheduler history)
**Location:** `supabase/sql/job_executions_schema.sql`

```sql
CREATE TABLE job_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id VARCHAR(100) NOT NULL,                 -- e.g., "data_collection"
    status VARCHAR(20) NOT NULL,                  -- 'success', 'failed', 'cancelled'
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL,
    duration_seconds DECIMAL(10,3),
    error_message TEXT,                           -- Error if job failed
    logs TEXT,                                    -- Full execution logs
    metadata JSONB,                               -- Additional context
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Indexes:**
- `idx_job_executions_job_id` - Query by job ID
- `idx_job_executions_status` - Query by status
- `idx_job_executions_started_at` - Recent jobs
- `idx_job_executions_job_id_started_at` - Combined query

**View:** `job_execution_summary` - Summary stats per job

**RLS Policies:**
- Service role: Full access
- Authenticated users: Full access
- Anonymous: Read only

#### Table: `scheduled_jobs` (Job definitions)
**Location:** `supabase/sql/scheduled_jobs_schema.sql`

```sql
CREATE TABLE scheduled_jobs (
    id UUID PRIMARY KEY,
    job_id VARCHAR(100) UNIQUE,                   -- e.g., "data_collection"
    job_name VARCHAR(200),                        -- Human-readable name
    job_function VARCHAR(200),                    -- Full Python path
    schedule_type VARCHAR(20),                    -- 'interval' or 'cron'
    schedule_value VARCHAR(100),                  -- '3600' or '0 2 * * *'
    enabled BOOLEAN DEFAULT true,
    last_successful_run TIMESTAMPTZ,
    last_attempted_run TIMESTAMPTZ,
    next_scheduled_run TIMESTAMPTZ,
    consecutive_failures INTEGER DEFAULT 0,
    max_consecutive_failures INTEGER DEFAULT 3,
    auto_retry_on_startup BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Indexes:**
- `idx_scheduled_jobs_job_id` - Lookup by job ID
- `idx_scheduled_jobs_enabled` - Find enabled jobs
- `idx_scheduled_jobs_next_run` - Find overdue jobs
- `idx_scheduled_jobs_enabled_next_run` - Combined query

**View:** `scheduled_jobs_status` - Shows job status with last execution

**Functions:**
- `update_job_after_execution()` - Update job status after run
- `calculate_next_run()` - Calculate next scheduled run time
- `cleanup_old_job_executions()` - Maintenance function

**RLS Policies:** Same as job_executions

### 3.3 Relationship: How Tables Connect

```
scheduled_jobs                          job_executions
     |                                      |
     |-- job_id ----------------------> job_id
     |                                      |
     |-- job_function (Python path)     (executes)
     |                                      |
     |-- schedule_value                     |-- status (success/failed)
     |                                      |-- logs (full output)
     |-- next_scheduled_run                 |-- error_message
     |-- last_successful_run                |-- duration_seconds
     |-- consecutive_failures               |
     |-- max_consecutive_failures
```

---

## 4. SCHEDULER IMPLEMENTATION & JOB EXECUTION

### 4.1 Scheduler Architecture
**Location:** `src/politician_trading/scheduler/manager.py`

**Pattern:** Singleton (ensures only one scheduler across Streamlit reruns)

```python
class SchedulerManager:
    _instance: Optional["SchedulerManager"] = None
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                cls._instance = super().__new__(cls)
        return cls._instance
```

### 4.2 Scheduler Lifecycle

#### Initialization (Line 262)
1. Create `BackgroundScheduler` instance
2. Configure job defaults:
   - `coalesce=True` - Combine multiple pending executions
   - `max_instances=1` - Prevent concurrent execution
   - `misfire_grace_time=300` - 5-minute grace for missed jobs
3. Initialize database client for history persistence
4. Create `JobHistory` instance
5. Register event listeners:
   - `EVENT_JOB_EXECUTED` → `_job_executed()`
   - `EVENT_JOB_ERROR` → `_job_error()`
6. Start scheduler
7. Load jobs from database
8. Recover missed jobs
9. Register shutdown hook

#### Job Loading (Lines 954-1093)
```python
def _load_jobs_from_database(self):
    """Load all enabled jobs from database into scheduler"""
    # Query scheduled_jobs table where enabled=true
    # For each job:
    #   - Import job function dynamically
    #   - Create CronTrigger or IntervalTrigger
    #   - Wrap function for log capture
    #   - Add to APScheduler
    #   - Store metadata
```

#### Job Recovery (Lines 751-793)
```python
def _recover_missed_jobs(self):
    """Execute jobs that missed their scheduled time"""
    # Query overdue jobs:
    #   WHERE enabled=true AND auto_retry_on_startup=true
    #   AND next_scheduled_run <= NOW()
    #   AND consecutive_failures < max_consecutive_failures
    # For each overdue job:
    #   - Import function
    #   - Execute with log capture
    #   - Update status in database
```

### 4.3 Job Execution Flow

```
User clicks "Run Now" or Scheduled time arrives
    |
    v
scheduler.get_job(job_id).modify(next_run_time=NOW())
    |
    v
APScheduler executes job in thread pool
    |
    v
_create_job_wrapper() wraps the function
    |
    +-- Create LogCaptureHandler (capture logs)
    +-- Add to root logger
    +-- Record start_time
    +-- Execute actual job function
    |
    v (Success)
    +-- Capture logs
    +-- Calculate duration
    +-- job_history.add_execution(status="success")
    +-- Update database via _persist_to_database()
    |
    v (Failure)
    +-- Capture logs + error
    +-- Calculate duration
    +-- job_history.add_execution(status="error")
    +-- Update database
    +-- Re-raise exception
```

### 4.4 Log Capture During Job Execution
**Class:** `LogCaptureHandler` (Lines 40-70)

```python
class LogCaptureHandler(logging.Handler):
    def __init__(self, max_lines: int = 1000):
        self.logs: List[str] = []  # Stores captured logs
        self._lock = Lock()
    
    def emit(self, record: logging.LogRecord):
        msg = self.format(record)
        self.logs.append(msg)
        # Keep only last N lines
        if len(self.logs) > self.max_lines:
            self.logs = self.logs[-self.max_lines:]
```

**Execution Wrapper (Lines 325-403):**
```python
def _create_job_wrapper(self, func: Callable, job_id: str):
    def wrapper():
        log_handler = LogCaptureHandler(max_lines=1000)
        root_logger.addHandler(log_handler)
        
        try:
            result = func()  # Execute actual job
            logs = log_handler.get_logs()
            self.job_history.add_execution(job_id=job_id, status="success", logs=logs)
        except Exception as e:
            logs = log_handler.get_logs()
            self.job_history.add_execution(job_id=job_id, status="error", error=str(e), logs=logs)
        finally:
            root_logger.removeHandler(log_handler)
    return wrapper
```

### 4.5 Job History Persistence
**Class:** `JobHistory` (Lines 72-242)

**In-Memory Storage:**
```python
self.executions: List[Dict[str, Any]] = []  # Stores up to max_history (100)
```

**Database Persistence:**
```python
def _persist_to_database(self, execution: Dict[str, Any]):
    """Insert execution record to job_executions table"""
    db_record = {
        "job_id": execution["job_id"],
        "status": execution["status"],
        "started_at": execution["timestamp"],
        "completed_at": execution["timestamp"],
        "duration_seconds": execution.get("duration_seconds"),
        "error_message": execution.get("error"),
        "logs": "\n".join(execution.get("logs", [])),
        "metadata": {},
    }
    response = self.db_client.client.table("job_executions").insert(db_record).execute()
```

### 4.6 Job Status Updates
**Function:** `update_job_after_execution()` (PostgreSQL)

**Success Path:**
```sql
UPDATE scheduled_jobs
SET last_successful_run = NOW(),
    last_attempted_run = NOW(),
    consecutive_failures = 0,
    next_scheduled_run = calculate_next_run(...),
    updated_at = NOW()
WHERE job_id = ?
```

**Failure Path:**
```sql
UPDATE scheduled_jobs
SET last_attempted_run = NOW(),
    consecutive_failures = consecutive_failures + 1,
    next_scheduled_run = calculate_next_run(...),
    updated_at = NOW()
WHERE job_id = ?
```

---

## 5. ERROR HANDLING & RESULT TRACKING

### 5.1 Error Handling in Data Collection
**Location:** `src/politician_trading/workflow.py`

**Pattern:** Try-catch with logging and graceful failure

```python
async def _collect_us_congress_data(self):
    logger.info("Starting US Congress data collection")
    try:
        # Collection logic
    except Exception as e:
        logger.error(f"US Congress collection failed: {e}")
        # Return partial results (don't crash workflow)
        return {
            "status": "error",
            "new_disclosures": 0,
            "error": str(e)
        }
```

### 5.2 Result Tracking in DataPullJob
**Model:** `DataPullJob` (src/models.py, Lines 168-193)

```python
@dataclass
class DataPullJob:
    id: str
    job_type: str  # "us_congress", "eu_parliament", etc.
    status: str    # "pending", "running", "completed", "failed"
    
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    # Results
    records_found: int         # Total records discovered
    records_processed: int     # Records successfully processed
    records_new: int          # New records added
    records_updated: int      # Existing records updated
    records_failed: int       # Records that failed
    
    # Error information
    error_message: Optional[str]
    error_details: Dict[str, Any]
    
    # Configuration snapshot
    config_snapshot: Dict[str, Any]
```

### 5.3 Job Execution Error Tracking
**Table:** `job_executions`

Fields for error tracking:
- `status` - 'success', 'failed', 'cancelled'
- `error_message` - Text description of error
- `logs` - Full execution logs including stack traces
- `duration_seconds` - How long job ran before failure

### 5.4 Consecutive Failure Tracking
**Table:** `scheduled_jobs`

Fields:
- `consecutive_failures` - Counter of failed runs
- `max_consecutive_failures` - Threshold before disabling (default: 3)
- When failures exceed threshold:
  - Job marked as disabled (enabled = false)
  - No longer loaded on startup
  - Can be manually re-enabled via UI

---

## 6. RECOMMENDATIONS FOR ACTION LOGGING

### 6.1 Create Dedicated Action Log Table

```sql
CREATE TABLE action_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action_type VARCHAR(50) NOT NULL,          -- 'data_collection_start', 'job_pause', etc.
    user_id VARCHAR(255),                       -- Username or ID from auth
    action_timestamp TIMESTAMPTZ DEFAULT NOW(),
    action_details JSONB,                       -- Action-specific data
    
    -- Link to job if applicable
    job_id VARCHAR(100),
    job_execution_id UUID,
    
    -- Result
    status VARCHAR(20),                         -- 'initiated', 'in_progress', 'completed', 'failed'
    result_message TEXT,
    error_message TEXT,
    
    -- Metadata
    source VARCHAR(50),                         -- 'ui_button', 'scheduled_job', 'api', 'recovery'
    ip_address VARCHAR(45),
    user_agent TEXT,
    request_duration_seconds DECIMAL(10,3),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Indexes:**
```sql
CREATE INDEX idx_action_logs_action_type ON action_logs(action_type);
CREATE INDEX idx_action_logs_user_id ON action_logs(user_id);
CREATE INDEX idx_action_logs_timestamp ON action_logs(action_timestamp DESC);
CREATE INDEX idx_action_logs_job_id ON action_logs(job_id);
CREATE INDEX idx_action_logs_status ON action_logs(status);
```

### 6.2 Integration Points for Action Logging

**When to Log Actions:**

1. **Data Collection Started**
   - Source: Data Collection page button click
   - Log: Selected sources, lookback period, user, timestamp
   - Location: `pages/1_📥_Data_Collection.py` line 120

2. **Data Collection Completed**
   - Log: Results summary (new/updated/failed records)
   - Location: After `workflow.run_full_collection()` completes

3. **Job Created/Modified**
   - Log: Job ID, schedule, user, timestamp
   - Location: `scheduler.add_interval_job()` / `add_cron_job()`

4. **Job Executed**
   - Log: Job ID, duration, status, errors
   - Location: After `_create_job_wrapper()` execution

5. **Job Paused/Resumed**
   - Log: Job ID, user, action, timestamp
   - Location: `scheduler.pause_job()` / `resume_job()`

6. **Job Missed/Recovered**
   - Log: Job ID, missed time, recovery result
   - Location: `_recover_missed_jobs()`

### 6.3 Where to Integrate Action Logging

**For Data Collection Triggers:**
- Modify `pages/1_📥_Data_Collection.py` line 120:
  ```python
  # Log action initiation
  log_action("data_collection_start", {
      "sources": [enabled_sources],
      "lookback_days": lookback_days,
      "user": get_current_user()
  })
  ```

**For Scheduled Jobs:**
- Modify `src/politician_trading/scheduler/manager.py`:
  - Line 233: Log job creation
  - Line 325-403: Log job execution in wrapper
  - Line 642-681: Log pause/resume/remove operations

**For Manual Job Triggers:**
- Modify `pages/5_⏰_Scheduled_Jobs.py`:
  - Line 155: "Run Now" action
  - Line 141-153: Pause/Resume actions
  - Line 162: Remove job action

### 6.4 Logging Implementation Pattern

Create a utility function in `src/politician_trading/utils/action_logger.py`:

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
    user_id: Optional[str] = None
):
    """Log an action to the action_logs table"""
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
        }
        
        db.client.table("action_logs").insert(action_record).execute()
        logger.debug(f"Logged action: {action_type}", metadata={"status": status})
        
    except Exception as e:
        logger.error(f"Failed to log action {action_type}: {e}")
        # Don't fail main operation if logging fails
```

### 6.5 View for Action Analytics

```sql
CREATE OR REPLACE VIEW action_analytics AS
SELECT
    action_type,
    DATE(action_timestamp) as action_date,
    COUNT(*) as action_count,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
    COUNT(DISTINCT user_id) as unique_users,
    AVG(request_duration_seconds) as avg_duration_seconds
FROM action_logs
WHERE action_timestamp >= NOW() - INTERVAL '30 days'
GROUP BY action_type, DATE(action_timestamp)
ORDER BY action_date DESC, action_count DESC;
```

---

## Summary Table: All Action Triggers

| Trigger | Location | Handler | Logging | Database |
|---------|----------|---------|---------|----------|
| Start Collection | Data Collection page | `run_full_collection()` | `logs/YYYY-MM-DD.log` | `data_pull_jobs` |
| Backfill Tickers | Data Collection page | Manual ticker extraction | `logs/YYYY-MM-DD.log` | `trading_disclosures` |
| Add Interval Job | Scheduled Jobs page | `add_interval_job()` | `logs/YYYY-MM-DD.log` | `scheduled_jobs` |
| Add Cron Job | Scheduled Jobs page | `add_cron_job()` | `logs/YYYY-MM-DD.log` | `scheduled_jobs` |
| Run Now | Scheduled Jobs page | `run_job_now()` | `logs/YYYY-MM-DD.log` | `job_executions` |
| Pause Job | Scheduled Jobs page | `pause_job()` | `logs/YYYY-MM-DD.log` | `scheduled_jobs` |
| Resume Job | Scheduled Jobs page | `resume_job()` | `logs/YYYY-MM-DD.log` | `scheduled_jobs` |
| Remove Job | Scheduled Jobs page | `remove_job()` | `logs/YYYY-MM-DD.log` | `scheduled_jobs` |
| Scheduled Execution | APScheduler | Job wrapper | `logs/YYYY-MM-DD.log` | `job_executions` |
| Job Recovery | App startup | `_recover_missed_jobs()` | `logs/YYYY-MM-DD.log` | `job_executions` |

---

**Document Generated:** November 3, 2025
**Application Version:** Latest commit 773c5e8 "Add bidirectional sync between database and scheduler for jobs"
