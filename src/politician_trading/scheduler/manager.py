"""
Scheduler Manager for In-App Job Scheduling

Manages APScheduler for running scheduled jobs within the Streamlit app.
Uses singleton pattern to ensure only one scheduler runs across Streamlit reruns.
"""

import atexit
import logging
import time
from datetime import datetime
from threading import Lock
from typing import Any, Callable, Dict, List, Optional

# Try to import APScheduler, gracefully handle if not installed
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    BackgroundScheduler = None
    CronTrigger = None
    IntervalTrigger = None
    EVENT_JOB_EXECUTED = None
    EVENT_JOB_ERROR = None

from politician_trading.config import SupabaseConfig
from politician_trading.database.database import SupabaseClient
from politician_trading.utils.logger import create_logger
from politician_trading.utils.action_logger import start_action, complete_action, fail_action

logger = create_logger("scheduler_manager")


class LogCaptureHandler(logging.Handler):
    """Custom logging handler that captures logs for a job execution"""

    def __init__(self, max_lines: int = 1000):
        super().__init__()
        self.max_lines = max_lines
        self.logs: List[str] = []
        self._lock = Lock()

    def emit(self, record: logging.LogRecord):
        """Capture a log record"""
        try:
            msg = self.format(record)
            with self._lock:
                self.logs.append(msg)
                # Keep only last N lines
                if len(self.logs) > self.max_lines:
                    self.logs = self.logs[-self.max_lines :]
        except Exception:
            self.handleError(record)

    def get_logs(self) -> List[str]:
        """Get captured logs"""
        with self._lock:
            return self.logs.copy()

    def clear(self):
        """Clear captured logs"""
        with self._lock:
            self.logs = []


class JobHistory:
    """Tracks job execution history with logs and persists to database"""

    def __init__(
        self,
        max_history: int = 100,
        max_log_lines: int = 1000,
        db_client: Optional[SupabaseClient] = None,
    ):
        self.max_history = max_history
        self.max_log_lines = max_log_lines
        self.executions: List[Dict[str, Any]] = []
        self._lock = Lock()
        self.db_client = db_client

        # Load history from database if available
        if self.db_client:
            self._load_from_database()

    def _load_from_database(self):
        """Load recent job execution history from database"""
        try:
            logger.info("Loading job execution history from database")

            # Query recent executions (last 100)
            response = (
                self.db_client.client.table("job_executions")
                .select("*")
                .order("started_at", desc=True)
                .limit(self.max_history)
                .execute()
            )

            if response.data:
                logger.info(f"Loaded {len(response.data)} job executions from database")

                # Convert database records to execution format
                for record in reversed(response.data):  # Reverse to maintain chronological order
                    execution = {
                        "job_id": record["job_id"],
                        "timestamp": datetime.fromisoformat(
                            record["started_at"].replace("Z", "+00:00")
                        ),
                        "status": record["status"],
                        "error": record.get("error_message"),
                        "logs": record.get("logs", "").split("\n") if record.get("logs") else [],
                        "duration_seconds": (
                            float(record["duration_seconds"])
                            if record.get("duration_seconds")
                            else None
                        ),
                        "db_id": record["id"],  # Store database ID for reference
                    }
                    self.executions.insert(0, execution)
            else:
                logger.info("No job executions found in database")

        except Exception as e:
            logger.error(f"Failed to load job history from database: {e}")
            # Continue without database history - app should still work

    def _persist_to_database(self, execution: Dict[str, Any]) -> Optional[str]:
        """Persist a job execution to the database"""
        if not self.db_client:
            return None

        try:
            # Prepare data for database
            db_record = {
                "job_id": execution["job_id"],
                "status": execution["status"],
                "started_at": execution["timestamp"].isoformat(),
                "completed_at": (execution["timestamp"]).isoformat(),  # Will be same initially
                "duration_seconds": execution.get("duration_seconds"),
                "error_message": execution.get("error"),
                "logs": "\n".join(execution.get("logs", [])),
                "metadata": {},
            }

            # Insert to database
            response = self.db_client.client.table("job_executions").insert(db_record).execute()

            if response.data:
                db_id = response.data[0]["id"]
                logger.debug(f"Persisted job execution to database: {db_id}")
                return db_id

        except Exception as e:
            logger.error(f"Failed to persist job execution to database: {e}")
            # Continue without persistence - app should still work

        return None

    def _update_in_database(self, db_id: str, **updates):
        """Update an existing execution record in the database"""
        if not self.db_client or not db_id:
            return

        try:
            # Prepare update data
            db_updates = {}

            if "duration_seconds" in updates:
                db_updates["duration_seconds"] = updates["duration_seconds"]
                # Also update completed_at time
                db_updates["completed_at"] = datetime.now().isoformat()

            if "logs" in updates:
                db_updates["logs"] = "\n".join(updates["logs"])

            if db_updates:
                self.db_client.client.table("job_executions").update(db_updates).eq(
                    "id", db_id
                ).execute()
                logger.debug(f"Updated job execution in database: {db_id}")

        except Exception as e:
            logger.error(f"Failed to update job execution in database: {e}")

    def add_execution(
        self,
        job_id: str,
        status: str,
        error: Optional[str] = None,
        logs: Optional[List[str]] = None,
    ):
        """Add a job execution record with logs and persist to database"""
        with self._lock:
            execution = {
                "job_id": job_id,
                "timestamp": datetime.now(),
                "status": status,
                "error": error,
                "logs": logs or [],
                "duration_seconds": None,  # Will be updated if available
            }

            # Persist to database and get ID
            db_id = self._persist_to_database(execution)
            if db_id:
                execution["db_id"] = db_id

            self.executions.insert(0, execution)  # Most recent first
            if len(self.executions) > self.max_history:
                self.executions = self.executions[: self.max_history]

    def update_execution(self, job_id: str, timestamp: datetime, **updates):
        """Update an existing execution record (e.g., add duration, final logs) and database"""
        with self._lock:
            for execution in self.executions:
                if execution["job_id"] == job_id and execution["timestamp"] == timestamp:
                    execution.update(updates)

                    # Update in database if we have a db_id
                    db_id = execution.get("db_id")
                    if db_id:
                        self._update_in_database(db_id, **updates)

                    break

    def get_history(
        self, job_id: Optional[str] = None, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get execution history, optionally filtered by job_id and limited"""
        with self._lock:
            if job_id:
                history = [e for e in self.executions if e["job_id"] == job_id]
            else:
                history = self.executions.copy()

            if limit:
                history = history[:limit]

            return history

    def get_last_execution(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the last execution for a specific job"""
        history = self.get_history(job_id)
        return history[0] if history else None

    def get_logs(self, job_id: str, timestamp: datetime) -> List[str]:
        """Get logs for a specific job execution"""
        with self._lock:
            for execution in self.executions:
                if execution["job_id"] == job_id and execution["timestamp"] == timestamp:
                    return execution.get("logs", [])
            return []


class SchedulerManager:
    """
    Manages APScheduler for in-app job scheduling.

    Singleton pattern ensures only one scheduler runs even with Streamlit reruns.
    """

    _instance: Optional["SchedulerManager"] = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the scheduler (only once due to singleton)"""
        if self._initialized:
            return

        logger.info("Initializing SchedulerManager")

        # Check if APScheduler is available
        if not APSCHEDULER_AVAILABLE:
            logger.warning("APScheduler not available - scheduler features disabled")
            self.scheduler = None
            self.job_history = JobHistory(db_client=None)
            self._job_metadata = {}
            self._log_handlers = {}
            self.db_client = None
            self._initialized = True
            return

        self.scheduler = BackgroundScheduler(
            timezone="UTC",
            job_defaults={
                "coalesce": True,  # Combine multiple pending executions into one
                "max_instances": 1,  # Prevent concurrent executions of same job
                "misfire_grace_time": 300,  # 5 minutes grace for missed jobs
            },
        )

        # Initialize database client for job history persistence
        db_client = None
        try:
            config = SupabaseConfig.from_env()
            db_client = SupabaseClient(config)
            logger.info("Database client initialized for job history persistence")
        except Exception as e:
            logger.warning(f"Failed to initialize database client for job history: {e}")
            logger.warning("Job history will not be persisted to database")

        self.job_history = JobHistory(db_client=db_client)
        self._job_metadata: Dict[str, Dict[str, Any]] = {}
        self._log_handlers: Dict[str, LogCaptureHandler] = {}  # Track log handlers per job
        self.db_client = db_client  # Store for job recovery

        # Register event listeners
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)

        # Start the scheduler
        self.scheduler.start()
        logger.info("Scheduler started successfully")

        # Load jobs from database into scheduler
        if self.db_client:
            self._load_jobs_from_database()

        # Run job recovery/catch-up for missed jobs
        if self.db_client:
            self._recover_missed_jobs()

        # Ensure scheduler shuts down gracefully
        atexit.register(self._shutdown)

        self._initialized = True

    def _create_job_wrapper(self, func: Callable, job_id: str):
        """
        Create a wrapper function that captures logs during execution.

        Args:
            func: Original job function
            job_id: Job identifier

        Returns:
            Wrapped function that captures logs
        """

        def wrapper():
            # Create log handler for this execution
            log_handler = LogCaptureHandler(max_lines=1000)
            log_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            log_handler.setFormatter(formatter)

            # Store handler for this job
            execution_key = f"{job_id}_{datetime.now().isoformat()}"
            self._log_handlers[execution_key] = log_handler

            # Add handler to root logger
            root_logger = logging.getLogger()
            root_logger.addHandler(log_handler)

            start_time = time.time()
            log_handler.logs.append(f"🚀 Starting job: {job_id}")

            # Start action logging
            action_id = start_action(
                action_type="job_execution",
                action_name=f"Scheduled Job: {job_id}",
                source="scheduled_job",
                job_id=job_id,
                action_details={"scheduled": True},
            )

            try:
                # Execute the actual job function
                logger.info(f"Executing job: {job_id}", metadata={"action_id": action_id})
                result = func()

                duration = time.time() - start_time
                log_handler.logs.append(f"✅ Job completed successfully in {duration:.2f}s")

                # Get logs and clean up
                logs = log_handler.get_logs()
                root_logger.removeHandler(log_handler)

                # Store execution with logs
                execution = self.job_history.add_execution(
                    job_id=job_id,
                    status="success",
                    logs=logs,
                )
                self.job_history.update_execution(
                    job_id=job_id,
                    timestamp=self.job_history.get_last_execution(job_id)["timestamp"],
                    duration_seconds=duration,
                )

                # Complete action logging
                if action_id:
                    complete_action(
                        action_id=action_id,
                        result_message=f"Job completed successfully in {duration:.2f}s",
                        action_details={
                            "scheduled": True,
                            "duration_seconds": duration,
                            "db_execution_id": execution.get("db_id") if execution else None,
                        },
                    )

                return result

            except Exception as e:
                duration = time.time() - start_time
                log_handler.logs.append(f"❌ Job failed after {duration:.2f}s: {str(e)}")

                # Get logs and clean up
                logs = log_handler.get_logs()
                root_logger.removeHandler(log_handler)

                # Store execution with logs
                execution = self.job_history.add_execution(
                    job_id=job_id,
                    status="error",
                    error=str(e),
                    logs=logs,
                )
                self.job_history.update_execution(
                    job_id=job_id,
                    timestamp=self.job_history.get_last_execution(job_id)["timestamp"],
                    duration_seconds=duration,
                )

                # Fail action logging
                if action_id:
                    fail_action(
                        action_id=action_id,
                        error_message=str(e),
                        action_details={
                            "scheduled": True,
                            "duration_seconds": duration,
                            "db_execution_id": execution.get("db_id") if execution else None,
                        },
                    )

                raise

        return wrapper

    def _job_executed(self, event):
        """Handler for successful job execution"""
        job_id = event.job_id
        logger.info(f"Job executed successfully: {job_id}")
        # Execution already recorded in wrapper

    def _job_error(self, event):
        """Handler for job execution errors"""
        job_id = event.job_id
        str(event.exception) if event.exception else "Unknown error"
        logger.error(f"Job failed: {job_id}", error=event.exception)
        # Execution already recorded in wrapper

    def _shutdown(self):
        """Shutdown the scheduler gracefully"""
        if self.scheduler.running:
            logger.info("Shutting down scheduler")
            self.scheduler.shutdown(wait=False)

    def add_cron_job(
        self,
        func: Callable,
        job_id: str,
        name: str,
        cron_expression: str = None,
        hour: int = None,
        minute: int = 0,
        day_of_week: str = None,
        description: str = "",
        replace_existing: bool = True,
    ) -> bool:
        """
        Add a cron-style scheduled job.

        Args:
            func: Function to execute
            job_id: Unique job identifier
            name: Human-readable job name
            cron_expression: Full cron expression (e.g., "0 2 * * *")
            hour: Hour to run (0-23), alternative to cron_expression
            minute: Minute to run (0-59), default 0
            day_of_week: Day of week (mon,tue,wed,thu,fri,sat,sun), optional
            description: Job description
            replace_existing: Replace if job already exists

        Returns:
            True if job was added successfully
        """
        if not self.scheduler:
            logger.warning("Cannot add cron job - scheduler not available")
            return False

        try:
            # Check if job already exists
            existing_job = self.scheduler.get_job(job_id)
            if existing_job and not replace_existing:
                logger.warning(f"Job {job_id} already exists and replace_existing=False")
                return False

            # Create trigger
            if cron_expression:
                trigger = CronTrigger.from_crontab(cron_expression, timezone="UTC")
            else:
                trigger = CronTrigger(
                    hour=hour, minute=minute, day_of_week=day_of_week, timezone="UTC"
                )

            # Wrap function to capture logs
            wrapped_func = self._create_job_wrapper(func, job_id)

            # Add job
            self.scheduler.add_job(
                wrapped_func,
                trigger=trigger,
                id=job_id,
                name=name,
                replace_existing=replace_existing,
            )

            # Store metadata
            self._job_metadata[job_id] = {
                "name": name,
                "description": description,
                "type": "cron",
                "schedule": cron_expression
                or f"hour={hour}, minute={minute}, day_of_week={day_of_week}",
                "added_at": datetime.now(),
            }

            # Register job in database for recovery
            if self.db_client:
                self._register_job_in_database(
                    job_id=job_id,
                    job_name=name,
                    job_function=f"{func.__module__}.{func.__name__}",
                    schedule_type="cron",
                    schedule_value=cron_expression or f"{hour} {minute} * * {day_of_week or '*'}",
                    metadata={"description": description},
                )

            logger.info(
                f"Added cron job: {name}",
                metadata={"job_id": job_id, "schedule": cron_expression or f"{hour}:{minute:02d}"},
            )
            return True

        except Exception as e:
            logger.error(f"Failed to add cron job: {name}", error=e)
            return False

    def add_interval_job(
        self,
        func: Callable,
        job_id: str,
        name: str,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
        description: str = "",
        replace_existing: bool = True,
    ) -> bool:
        """
        Add an interval-based scheduled job.

        Args:
            func: Function to execute
            job_id: Unique job identifier
            name: Human-readable job name
            hours: Interval in hours
            minutes: Interval in minutes
            seconds: Interval in seconds
            description: Job description
            replace_existing: Replace if job already exists

        Returns:
            True if job was added successfully
        """
        if not self.scheduler:
            logger.warning("Cannot add interval job - scheduler not available")
            return False

        logger.info(
            "add_interval_job called",
            metadata={
                "job_id": job_id,
                "name": name,
                "hours": hours,
                "minutes": minutes,
                "seconds": seconds,
                "replace_existing": replace_existing,
                "func_name": func.__name__ if hasattr(func, "__name__") else str(func),
            },
        )

        try:
            # Check if job already exists
            existing_job = self.scheduler.get_job(job_id)
            if existing_job:
                logger.info(
                    f"Found existing job with id {job_id}",
                    metadata={
                        "existing_job_name": existing_job.name,
                        "replace_existing": replace_existing,
                    },
                )
                if not replace_existing:
                    logger.warning(f"Job {job_id} already exists and replace_existing=False")
                    return False

            # Create trigger
            logger.info(
                "Creating IntervalTrigger",
                metadata={"hours": hours, "minutes": minutes, "seconds": seconds},
            )
            trigger = IntervalTrigger(hours=hours, minutes=minutes, seconds=seconds, timezone="UTC")
            logger.info("IntervalTrigger created successfully")

            # Wrap function to capture logs
            logger.info(f"Wrapping function to capture logs for {job_id}")
            wrapped_func = self._create_job_wrapper(func, job_id)

            # Add job
            logger.info(f"Calling scheduler.add_job for {job_id}")
            self.scheduler.add_job(
                wrapped_func,
                trigger=trigger,
                id=job_id,
                name=name,
                replace_existing=replace_existing,
            )
            logger.info(f"scheduler.add_job completed successfully for {job_id}")

            # Store metadata
            interval_str = []
            if hours:
                interval_str.append(f"{hours}h")
            if minutes:
                interval_str.append(f"{minutes}m")
            if seconds:
                interval_str.append(f"{seconds}s")

            metadata_to_store = {
                "name": name,
                "description": description,
                "type": "interval",
                "schedule": " ".join(interval_str),
                "added_at": datetime.now(),
            }

            self._job_metadata[job_id] = metadata_to_store

            # Convert datetime to string for JSON serialization
            metadata_for_log = {
                "job_id": job_id,
                "interval": " ".join(interval_str),
                "metadata_stored": {
                    **metadata_to_store,
                    "added_at": metadata_to_store["added_at"].isoformat(),
                },
                "return_value": True,
            }

            # Register job in database for recovery
            if self.db_client:
                total_seconds = hours * 3600 + minutes * 60 + seconds
                self._register_job_in_database(
                    job_id=job_id,
                    job_name=name,
                    job_function=f"{func.__module__}.{func.__name__}",
                    schedule_type="interval",
                    schedule_value=str(total_seconds),
                    metadata={
                        "description": description,
                        "hours": hours,
                        "minutes": minutes,
                        "seconds": seconds,
                    },
                )

            logger.info(f"Added interval job: {name}", metadata=metadata_for_log)
            return True

        except Exception as e:
            logger.error(
                f"Failed to add interval job: {name}",
                error=e,
                metadata={
                    "job_id": job_id,
                    "exception_type": type(e).__name__,
                    "return_value": False,
                },
            )
            return False

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job"""
        if not self.scheduler:
            logger.warning("Cannot remove job - scheduler not available")
            return False
        try:
            self.scheduler.remove_job(job_id)
            if job_id in self._job_metadata:
                del self._job_metadata[job_id]
            logger.info(f"Removed job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove job: {job_id}", error=e)
            return False

    def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job"""
        if not self.scheduler:
            logger.warning("Cannot pause job - scheduler not available")
            return False
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to pause job: {job_id}", error=e)
            return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job"""
        if not self.scheduler:
            logger.warning("Cannot resume job - scheduler not available")
            return False
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Resumed job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to resume job: {job_id}", error=e)
            return False

    def run_job_now(self, job_id: str) -> bool:
        """
        Manually trigger a job to run now.

        Note: This runs the job in the scheduler's thread pool.
        """
        if not self.scheduler:
            logger.warning("Cannot run job - scheduler not available")
            return False
        try:
            job = self.scheduler.get_job(job_id)
            if not job:
                logger.error(f"Job not found: {job_id}")
                return False

            job.modify(next_run_time=datetime.now())
            logger.info(f"Triggered job to run now: {job_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to trigger job: {job_id}", error=e)
            return False

    def get_jobs(self) -> List[Dict[str, Any]]:
        """Get all scheduled jobs with metadata"""
        if not self.scheduler:
            return []

        jobs = []
        for job in self.scheduler.get_jobs():
            metadata = self._job_metadata.get(job.id, {})
            last_execution = self.job_history.get_last_execution(job.id)

            job_info = {
                "id": job.id,
                "name": job.name or metadata.get("name", job.id),
                "description": metadata.get("description", ""),
                "type": metadata.get("type", "unknown"),
                "schedule": metadata.get("schedule", str(job.trigger)),
                "next_run": job.next_run_time,
                "is_paused": job.next_run_time is None,
                "last_execution": last_execution,
            }
            jobs.append(job_info)

        return jobs

    def get_job_info(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific job"""
        job = self.scheduler.get_job(job_id)
        if not job:
            return None

        metadata = self._job_metadata.get(job_id, {})
        history = self.job_history.get_history(job_id)

        return {
            "id": job.id,
            "name": job.name or metadata.get("name", job.id),
            "description": metadata.get("description", ""),
            "type": metadata.get("type", "unknown"),
            "schedule": metadata.get("schedule", str(job.trigger)),
            "next_run": job.next_run_time,
            "is_paused": job.next_run_time is None,
            "added_at": metadata.get("added_at"),
            "execution_history": history[:10],  # Last 10 executions
        }

    def _recover_missed_jobs(self):
        """
        Recover and execute missed scheduled jobs on startup.

        Queries the scheduled_jobs table for overdue jobs and executes them
        if they haven't exceeded max_consecutive_failures.
        """
        logger.info("🔄 Checking for missed scheduled jobs...")

        try:
            # Query for overdue jobs that should be retried
            overdue_jobs = self._get_overdue_jobs()

            if not overdue_jobs:
                logger.info("✅ No missed jobs to recover")
                return

            logger.info(f"Found {len(overdue_jobs)} overdue job(s) to recover")

            for job_record in overdue_jobs:
                job_id = job_record["job_id"]
                job_name = job_record["job_name"]
                consecutive_failures = job_record["consecutive_failures"]
                max_failures = job_record["max_consecutive_failures"]
                last_run = job_record.get("last_attempted_run")

                logger.info(f"📋 Attempting to recover job: {job_name} ({job_id})")
                logger.info(f"   Last run: {last_run or 'Never'}")
                logger.info(f"   Consecutive failures: {consecutive_failures}/{max_failures}")

                # Execute the missed job
                success = self._execute_missed_job(job_record)

                if success:
                    logger.info(f"✅ Successfully recovered job: {job_id}")
                else:
                    logger.warning(f"⚠️  Failed to recover job: {job_id}")

        except Exception as e:
            logger.error(f"❌ Error during job recovery: {e}")
            import traceback

            traceback.print_exc()

    def _get_overdue_jobs(self) -> List[Dict[str, Any]]:
        """
        Query database for jobs that are overdue and should be executed.

        Returns jobs where:
        - enabled = true
        - auto_retry_on_startup = true
        - next_scheduled_run <= NOW()
        - consecutive_failures < max_consecutive_failures
        """
        try:
            response = (
                self.db_client.client.table("scheduled_jobs")
                .select("*")
                .eq("enabled", True)
                .eq("auto_retry_on_startup", True)
                .lte("next_scheduled_run", datetime.now().isoformat())
                .execute()
            )

            if not response.data:
                return []

            # Filter out jobs that have exceeded max failures
            overdue_jobs = [
                job
                for job in response.data
                if job["consecutive_failures"] < job["max_consecutive_failures"]
            ]

            return overdue_jobs

        except Exception as e:
            logger.error(f"Error querying overdue jobs: {e}")
            return []

    def _execute_missed_job(self, job_record: Dict[str, Any]) -> bool:
        """
        Execute a missed job and update its status.

        Args:
            job_record: Database record for the scheduled job

        Returns:
            True if execution succeeded, False otherwise
        """
        job_id = job_record["job_id"]
        job_function = job_record["job_function"]

        try:
            # Import and get the job function
            logger.info(f"🔄 Loading job function: {job_function}")

            module_path, function_name = job_function.rsplit(".", 1)

            import importlib

            module = importlib.import_module(module_path)
            func = getattr(module, function_name)

            # Create wrapper to capture logs and execution
            wrapped_func = self._create_job_wrapper(func, job_id)

            # Execute the job
            logger.info(f"▶️  Executing missed job: {job_id}")
            wrapped_func()

            # Update job status in database - success
            self._update_job_status(job_id, success=True)

            return True

        except Exception as e:
            logger.error(f"❌ Error executing missed job {job_id}: {e}")
            import traceback

            traceback.print_exc()

            # Update job status in database - failure
            self._update_job_status(job_id, success=False, error=str(e))

            return False

    def _update_job_status(self, job_id: str, success: bool, error: Optional[str] = None):
        """
        Update scheduled job status after execution.

        Args:
            job_id: Job identifier
            success: Whether execution succeeded
            error: Error message if failed
        """
        try:
            # Call the database function to update job status
            if success:
                logger.info(f"✅ Updating job status: {job_id} - SUCCESS")
                self.db_client.client.rpc(
                    "update_job_after_execution", {"p_job_id": job_id, "p_success": True}
                ).execute()
            else:
                logger.warning(f"⚠️  Updating job status: {job_id} - FAILED")
                logger.warning(f"   Error: {error}")
                self.db_client.client.rpc(
                    "update_job_after_execution", {"p_job_id": job_id, "p_success": False}
                ).execute()

        except Exception as e:
            logger.error(f"Error updating job status for {job_id}: {e}")

    def _register_job_in_database(
        self,
        job_id: str,
        job_name: str,
        job_function: str,
        schedule_type: str,
        schedule_value: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Register a scheduled job in the database for recovery tracking.

        Args:
            job_id: Unique job identifier
            job_name: Human-readable job name
            job_function: Full Python function path (e.g., 'module.submodule.function_name')
            schedule_type: 'interval' or 'cron'
            schedule_value: Schedule definition (seconds for interval, cron expression for cron)
            metadata: Additional job metadata
        """
        try:
            logger.info(f"📝 Registering job in database: {job_id}")

            # Calculate next_scheduled_run
            if schedule_type == "interval":
                next_run = datetime.now()
            else:
                next_run = datetime.now()

            job_record = {
                "job_id": job_id,
                "job_name": job_name,
                "job_function": job_function,
                "schedule_type": schedule_type,
                "schedule_value": schedule_value,
                "enabled": True,
                "next_scheduled_run": next_run.isoformat(),
                "metadata": metadata or {},
            }

            # Upsert job record (insert or update if exists)
            self.db_client.client.table("scheduled_jobs").upsert(
                job_record, on_conflict="job_id"
            ).execute()

            logger.info(f"✅ Job registered in database: {job_id}")

        except Exception as e:
            logger.error(f"Failed to register job {job_id} in database: {e}")
            # Don't fail the job scheduling if database registration fails

    def _load_jobs_from_database(self):
        """
        Load all enabled jobs from the database and add them to the scheduler.
        This ensures database-defined jobs are scheduled even if the app restarts.
        """
        logger.info("📂 Loading jobs from database into scheduler...")

        try:
            # Get all enabled jobs from database
            response = (
                self.db_client.client.table("scheduled_jobs")
                .select("*")
                .eq("enabled", True)
                .execute()
            )

            if not response.data:
                logger.info("No enabled jobs found in database")
                return

            db_jobs = response.data
            logger.info(f"Found {len(db_jobs)} enabled jobs in database")

            # Get currently scheduled job IDs
            current_job_ids = {job.id for job in self.scheduler.get_jobs()}
            logger.info(f"Currently {len(current_job_ids)} jobs in scheduler")

            # Add jobs that aren't already scheduled
            loaded_count = 0
            skipped_count = 0

            for db_job in db_jobs:
                job_id = db_job["job_id"]
                job_name = db_job["job_name"]
                job_function_path = db_job["job_function"]
                schedule_type = db_job["schedule_type"]
                schedule_value = db_job["schedule_value"]
                metadata = db_job.get("metadata", {})

                # Skip if already in scheduler
                if job_id in current_job_ids:
                    logger.debug(f"Job '{job_name}' already in scheduler - skipping")
                    skipped_count += 1
                    continue

                try:
                    # Dynamically import the job function
                    module_path, function_name = job_function_path.rsplit(".", 1)
                    import importlib

                    module = importlib.import_module(module_path)
                    func = getattr(module, function_name)

                    # Add job based on schedule type
                    if schedule_type == "cron":
                        # Parse cron expression (minute hour day month day_of_week)
                        parts = schedule_value.split()
                        if len(parts) >= 5:
                            minute, hour, day, month, day_of_week = parts[:5]

                            # Convert cron wildcards to None for CronTrigger
                            minute = None if minute == "*" else minute
                            hour = None if hour == "*" else hour
                            day = None if day == "*" else day
                            month = None if month == "*" else month
                            day_of_week = None if day_of_week == "*" else day_of_week

                            trigger = CronTrigger(
                                minute=minute,
                                hour=hour,
                                day=day,
                                month=month,
                                day_of_week=day_of_week,
                                timezone="UTC",
                            )

                            wrapped_func = self._create_job_wrapper(func, job_id)
                            self.scheduler.add_job(
                                wrapped_func,
                                trigger=trigger,
                                id=job_id,
                                name=job_name,
                                replace_existing=False,
                            )

                            # Store metadata
                            self._job_metadata[job_id] = {
                                "name": job_name,
                                "description": metadata.get("description", ""),
                                "type": "cron",
                                "schedule": schedule_value,
                                "added_at": datetime.now(),
                                "loaded_from_database": True,
                            }

                            logger.info(
                                f"✅ Loaded cron job from database: {job_name} (schedule: {schedule_value})"
                            )
                            loaded_count += 1

                        else:
                            logger.error(
                                f"Invalid cron expression for job {job_name}: {schedule_value}"
                            )

                    elif schedule_type == "interval":
                        # Interval in seconds
                        seconds = int(schedule_value)
                        trigger = IntervalTrigger(seconds=seconds, timezone="UTC")

                        wrapped_func = self._create_job_wrapper(func, job_id)
                        self.scheduler.add_job(
                            wrapped_func,
                            trigger=trigger,
                            id=job_id,
                            name=job_name,
                            replace_existing=False,
                        )

                        # Store metadata
                        self._job_metadata[job_id] = {
                            "name": job_name,
                            "description": metadata.get("description", ""),
                            "type": "interval",
                            "schedule": f"every {seconds}s",
                            "added_at": datetime.now(),
                            "loaded_from_database": True,
                        }

                        logger.info(
                            f"✅ Loaded interval job from database: {job_name} (every {seconds}s)"
                        )
                        loaded_count += 1

                    else:
                        logger.error(f"Unknown schedule type for job {job_name}: {schedule_type}")

                except Exception as e:
                    logger.error(
                        f"Failed to load job {job_name} from database",
                        error=e,
                        metadata={"job_id": job_id, "job_function": job_function_path},
                    )

            logger.info(
                f"✅ Database job loading complete: {loaded_count} loaded, {skipped_count} skipped"
            )

        except Exception as e:
            logger.error("Failed to load jobs from database", error=e)
            # Don't crash the scheduler if database loading fails

    def is_running(self) -> bool:
        """Check if scheduler is running"""
        if not self.scheduler:
            return False
        return self.scheduler.running


# Global function to get the singleton scheduler instance
def get_scheduler() -> SchedulerManager:
    """Get the global SchedulerManager instance"""
    return SchedulerManager()
