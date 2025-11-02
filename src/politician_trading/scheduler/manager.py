"""
Scheduler Manager for In-App Job Scheduling

Manages APScheduler for running scheduled jobs within the Streamlit app.
Uses singleton pattern to ensure only one scheduler runs across Streamlit reruns.
"""

import asyncio
import atexit
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from politician_trading.utils.logger import create_logger

logger = create_logger("scheduler_manager")


class JobHistory:
    """Tracks job execution history"""

    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.executions: List[Dict[str, Any]] = []
        self._lock = Lock()

    def add_execution(self, job_id: str, status: str, error: Optional[str] = None):
        """Add a job execution record"""
        with self._lock:
            execution = {
                "job_id": job_id,
                "timestamp": datetime.now(),
                "status": status,
                "error": error,
            }
            self.executions.insert(0, execution)  # Most recent first
            if len(self.executions) > self.max_history:
                self.executions = self.executions[: self.max_history]

    def get_history(self, job_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get execution history, optionally filtered by job_id"""
        with self._lock:
            if job_id:
                return [e for e in self.executions if e["job_id"] == job_id]
            return self.executions.copy()

    def get_last_execution(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the last execution for a specific job"""
        history = self.get_history(job_id)
        return history[0] if history else None


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

        self.scheduler = BackgroundScheduler(
            timezone="UTC",
            job_defaults={
                "coalesce": True,  # Combine multiple pending executions into one
                "max_instances": 1,  # Prevent concurrent executions of same job
                "misfire_grace_time": 300,  # 5 minutes grace for missed jobs
            },
        )

        self.job_history = JobHistory()
        self._job_metadata: Dict[str, Dict[str, Any]] = {}

        # Register event listeners
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)

        # Start the scheduler
        self.scheduler.start()
        logger.info("Scheduler started successfully")

        # Ensure scheduler shuts down gracefully
        atexit.register(self._shutdown)

        self._initialized = True

    def _job_executed(self, event):
        """Handler for successful job execution"""
        job_id = event.job_id
        logger.info(f"Job executed successfully: {job_id}")
        self.job_history.add_execution(job_id, "success")

    def _job_error(self, event):
        """Handler for job execution errors"""
        job_id = event.job_id
        exception = str(event.exception) if event.exception else "Unknown error"
        logger.error(f"Job failed: {job_id}", error=event.exception)
        self.job_history.add_execution(job_id, "error", exception)

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

            # Add job
            self.scheduler.add_job(
                func,
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

            logger.info(f"Added cron job: {name}", metadata={"job_id": job_id, "schedule": cron_expression or f"{hour}:{minute:02d}"})
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
        logger.info(f"add_interval_job called", metadata={
            "job_id": job_id,
            "name": name,
            "hours": hours,
            "minutes": minutes,
            "seconds": seconds,
            "replace_existing": replace_existing,
            "func_name": func.__name__ if hasattr(func, '__name__') else str(func)
        })

        try:
            # Check if job already exists
            existing_job = self.scheduler.get_job(job_id)
            if existing_job:
                logger.info(f"Found existing job with id {job_id}", metadata={
                    "existing_job_name": existing_job.name,
                    "replace_existing": replace_existing
                })
                if not replace_existing:
                    logger.warning(f"Job {job_id} already exists and replace_existing=False")
                    return False

            # Create trigger
            logger.info(f"Creating IntervalTrigger", metadata={
                "hours": hours,
                "minutes": minutes,
                "seconds": seconds
            })
            trigger = IntervalTrigger(hours=hours, minutes=minutes, seconds=seconds, timezone="UTC")
            logger.info(f"IntervalTrigger created successfully")

            # Add job
            logger.info(f"Calling scheduler.add_job for {job_id}")
            self.scheduler.add_job(
                func,
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

            logger.info(f"Added interval job: {name}", metadata={
                "job_id": job_id,
                "interval": " ".join(interval_str),
                "metadata_stored": metadata_to_store,
                "return_value": True
            })
            return True

        except Exception as e:
            logger.error(f"Failed to add interval job: {name}", error=e, metadata={
                "job_id": job_id,
                "exception_type": type(e).__name__,
                "return_value": False
            })
            return False

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job"""
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
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to pause job: {job_id}", error=e)
            return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job"""
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

    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self.scheduler.running


# Global function to get the singleton scheduler instance
def get_scheduler() -> SchedulerManager:
    """Get the global SchedulerManager instance"""
    return SchedulerManager()
