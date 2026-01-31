"""
Job Execution Logger

Logs ETL job executions to the job_executions table in Supabase.
This provides persistent tracking of job runs that survives service restarts.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from supabase import Client

logger = logging.getLogger(__name__)


def log_job_execution(
    supabase_client: Client,
    job_id: str,
    status: str,
    started_at: datetime,
    completed_at: Optional[datetime] = None,
    error_message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Log a job execution to the job_executions table.

    Args:
        supabase_client: Supabase client instance
        job_id: Job identifier (e.g., 'politician-trading-house')
        status: Job status ('success', 'failed', 'running')
        started_at: When the job started
        completed_at: When the job completed (optional)
        error_message: Error message if failed (optional)
        metadata: Additional metadata dict (optional)

    Returns:
        The execution record ID if successful, None otherwise
    """
    try:
        completed = completed_at or datetime.now(timezone.utc)
        duration = (completed - started_at).total_seconds() if completed_at else None

        record = {
            "id": str(uuid4()),
            "job_id": job_id,
            "status": status,
            "started_at": started_at.isoformat(),
            "completed_at": completed.isoformat() if completed_at else None,
            "duration_seconds": duration,
            "error_message": error_message,
            "metadata": metadata or {},
        }

        result = supabase_client.table("job_executions").insert(record).execute()

        if result.data:
            logger.info(f"Logged job execution: {job_id} ({status})")
            return record["id"]
        else:
            logger.warning(f"Failed to log job execution: {job_id}")
            return None

    except Exception as e:
        logger.error(f"Error logging job execution: {e}")
        return None


def cleanup_old_executions(
    supabase_client: Client,
    days: int = 30,
    job_id_prefix: Optional[str] = None,
) -> int:
    """
    Delete job executions older than specified days.

    Args:
        supabase_client: Supabase client instance
        days: Delete records older than this many days (default: 30)
        job_id_prefix: Optional prefix to filter jobs (e.g., 'politician-trading')

    Returns:
        Number of records deleted
    """
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        query = supabase_client.table("job_executions").delete().lt(
            "started_at", cutoff
        )

        if job_id_prefix:
            query = query.like("job_id", f"{job_id_prefix}%")

        result = query.execute()
        count = len(result.data) if result.data else 0

        logger.info(f"Cleaned up {count} job executions older than {days} days")
        return count

    except Exception as e:
        logger.error(f"Error cleaning up job executions: {e}")
        return 0


class JobExecutionContext:
    """
    Context manager for tracking job executions.

    Usage:
        async with JobExecutionContext(supabase, "my-job") as ctx:
            # Do work
            ctx.add_metadata("records_processed", 100)
        # Automatically logs on exit
    """

    def __init__(
        self,
        supabase_client: Client,
        job_id: str,
        auto_cleanup: bool = True,
        cleanup_days: int = 30,
    ) -> None:
        self.supabase = supabase_client
        self.job_id = job_id
        self.auto_cleanup = auto_cleanup
        self.cleanup_days = cleanup_days
        self.started_at = None
        self.metadata = {}
        self.error = None

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to be logged with the execution."""
        self.metadata[key] = value

    def set_error(self, error: str) -> None:
        """Set error message for failed execution."""
        self.error = error

    async def __aenter__(self):
        self.started_at = datetime.now(timezone.utc)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        completed_at = datetime.now(timezone.utc)
        status = "failed" if exc_val or self.error else "success"
        error_msg = str(exc_val) if exc_val else self.error

        log_job_execution(
            self.supabase,
            job_id=self.job_id,
            status=status,
            started_at=self.started_at,
            completed_at=completed_at,
            error_message=error_msg,
            metadata=self.metadata,
        )

        # Optionally cleanup old records (1% chance to avoid every-run overhead)
        if self.auto_cleanup:
            import random
            if random.random() < 0.01:  # 1% chance
                cleanup_old_executions(
                    self.supabase,
                    days=self.cleanup_days,
                )

        # Don't suppress exceptions
        return False
