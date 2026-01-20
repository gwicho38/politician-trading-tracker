"""
Base ETL Service Abstract Class

Provides a standardized interface for ETL data sources with:
- Common result tracking
- Job status management
- Error handling patterns
- Lifecycle hooks for customization

Usage:
    from app.lib.base_etl import BaseETLService, ETLResult
    from app.lib.registry import ETLRegistry

    @ETLRegistry.register
    class MyETLService(BaseETLService):
        source_id = "my_source"
        source_name = "My Data Source"

        async def fetch_disclosures(self, **kwargs):
            # Fetch raw data from source
            return [...]

        async def parse_disclosure(self, raw):
            # Parse single disclosure
            return {...}
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
import logging
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class ETLResult:
    """
    Standardized result from an ETL job.

    Tracks counts for processed, inserted, updated, and failed records,
    along with any errors encountered during execution.
    """
    records_processed: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    records_failed: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate job duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        total = self.records_processed
        if total == 0:
            return 100.0
        failed = self.records_failed
        return ((total - failed) / total) * 100

    @property
    def is_success(self) -> bool:
        """Check if job completed without critical failures."""
        return len(self.errors) == 0

    def add_error(self, error: str):
        """Add an error message."""
        self.errors.append(error)
        logger.error(f"ETL Error: {error}")

    def add_warning(self, warning: str):
        """Add a warning message."""
        self.warnings.append(warning)
        logger.warning(f"ETL Warning: {warning}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "records_processed": self.records_processed,
            "records_inserted": self.records_inserted,
            "records_updated": self.records_updated,
            "records_skipped": self.records_skipped,
            "records_failed": self.records_failed,
            "errors": self.errors,
            "warnings": self.warnings,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "success_rate": self.success_rate,
            "is_success": self.is_success,
            "metadata": self.metadata,
        }


@dataclass
class JobStatus:
    """
    In-memory job status tracking.

    Used for real-time progress updates during ETL execution.
    """
    status: str = "queued"  # queued, running, completed, failed
    progress: int = 0
    total: Optional[int] = None
    message: str = "Job queued"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[ETLResult] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status,
            "progress": self.progress,
            "total": self.total,
            "message": self.message,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result.to_dict() if self.result else None,
        }


class BaseETLService(ABC):
    """
    Abstract base class for ETL data sources.

    Subclasses must implement:
    - source_id: Unique identifier (e.g., 'house', 'senate')
    - source_name: Human-readable name
    - fetch_disclosures(): Fetch raw data from source
    - parse_disclosure(): Parse single disclosure to standard format

    Optional overrides:
    - validate_disclosure(): Custom validation logic
    - upload_disclosure(): Custom upload logic
    - on_start(): Hook called before processing
    - on_complete(): Hook called after processing
    """

    # Subclasses must define these as class attributes
    source_id: str
    source_name: str

    def __init__(self):
        """Initialize the ETL service."""
        self.logger = logging.getLogger(f"{__name__}.{self.source_id}")
        self._job_status: Dict[str, JobStatus] = {}

    # =========================================================================
    # Abstract Methods - Must be implemented by subclasses
    # =========================================================================

    @abstractmethod
    async def fetch_disclosures(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch raw disclosure data from the source.

        Args:
            **kwargs: Source-specific parameters (year, lookback_days, etc.)

        Returns:
            List of raw disclosure dictionaries from the source.
        """
        pass

    @abstractmethod
    async def parse_disclosure(
        self, raw: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Parse a single raw disclosure into standardized format.

        Args:
            raw: Raw disclosure data from fetch_disclosures()

        Returns:
            Standardized disclosure dict, or None if invalid/skipped.
        """
        pass

    # =========================================================================
    # Optional Hooks - Can be overridden by subclasses
    # =========================================================================

    async def validate_disclosure(self, disclosure: Dict[str, Any]) -> bool:
        """
        Validate a parsed disclosure before upload.

        Override to add custom validation logic.

        Args:
            disclosure: Parsed disclosure from parse_disclosure()

        Returns:
            True if valid, False to skip.
        """
        # Default: require at minimum an asset_name
        return bool(disclosure.get("asset_name"))

    async def upload_disclosure(
        self,
        disclosure: Dict[str, Any],
        update_mode: bool = False,
    ) -> Optional[str]:
        """
        Upload a disclosure to the database.

        Override to customize upload behavior.

        Args:
            disclosure: Validated disclosure to upload
            update_mode: If True, upsert instead of insert

        Returns:
            Disclosure ID if successful, None if failed/skipped.
        """
        # Default implementation uses shared database utilities
        from app.lib.database import get_supabase, upload_transaction_to_supabase
        from app.lib.politician import find_or_create_politician

        try:
            supabase = get_supabase()
            if not supabase:
                return None

            # Get or create politician
            politician_id = find_or_create_politician(
                supabase,
                name=disclosure.get("politician_name"),
                first_name=disclosure.get("first_name"),
                last_name=disclosure.get("last_name"),
                chamber=disclosure.get("chamber", "house"),
                state=disclosure.get("state"),
            )

            if not politician_id:
                return None

            # Upload transaction
            return upload_transaction_to_supabase(
                supabase,
                politician_id,
                disclosure,
                disclosure,  # Use same dict for disclosure metadata
                update_mode=update_mode,
            )

        except Exception as e:
            self.logger.error(f"Upload failed: {e}")
            return None

    async def on_start(self, job_id: str, **kwargs):
        """
        Hook called before processing begins.

        Override to add setup logic (e.g., reset rate limiters).
        """
        self.logger.info(f"Starting {self.source_name} ETL job {job_id}")

    async def on_complete(self, job_id: str, result: ETLResult):
        """
        Hook called after processing completes.

        Override to add cleanup or notification logic.
        """
        self.logger.info(
            f"Completed {self.source_name} ETL job {job_id}: "
            f"{result.records_inserted} inserted, "
            f"{result.records_failed} failed"
        )

    # =========================================================================
    # Job Status Management
    # =========================================================================

    def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """Get current status for a job."""
        return self._job_status.get(job_id)

    def update_job_status(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        total: Optional[int] = None,
        message: Optional[str] = None,
    ):
        """Update job status fields."""
        if job_id not in self._job_status:
            self._job_status[job_id] = JobStatus()

        job = self._job_status[job_id]
        if status is not None:
            job.status = status
        if progress is not None:
            job.progress = progress
        if total is not None:
            job.total = total
        if message is not None:
            job.message = message

    # =========================================================================
    # Main Execution Flow
    # =========================================================================

    async def run(
        self,
        job_id: str,
        limit: Optional[int] = None,
        update_mode: bool = False,
        **kwargs,
    ) -> ETLResult:
        """
        Execute the standard ETL pipeline.

        This method orchestrates:
        1. on_start() hook
        2. fetch_disclosures() to get raw data
        3. For each disclosure:
           a. parse_disclosure()
           b. validate_disclosure()
           c. upload_disclosure()
        4. on_complete() hook

        Args:
            job_id: Unique job identifier for status tracking
            limit: Optional limit on records to process (for testing)
            update_mode: If True, upsert instead of insert
            **kwargs: Passed to fetch_disclosures()

        Returns:
            ETLResult with processing statistics and errors.
        """
        result = ETLResult(started_at=datetime.utcnow())

        # Initialize job status
        self._job_status[job_id] = JobStatus(
            status="running",
            started_at=datetime.utcnow().isoformat(),
            message=f"Starting {self.source_name} ETL...",
        )

        try:
            # Start hook
            await self.on_start(job_id, **kwargs)

            # Fetch raw disclosures
            self.update_job_status(job_id, message="Fetching disclosures...")
            raw_disclosures = await self.fetch_disclosures(**kwargs)

            if not raw_disclosures:
                result.add_warning("No disclosures fetched from source")
                self.update_job_status(
                    job_id,
                    status="completed",
                    message="No disclosures to process",
                )
                result.completed_at = datetime.utcnow()
                return result

            # Apply limit if specified
            to_process = raw_disclosures[:limit] if limit else raw_disclosures
            total = len(to_process)
            self.update_job_status(job_id, total=total)

            self.logger.info(f"Processing {total} disclosures")

            # Process each disclosure
            for i, raw in enumerate(to_process):
                result.records_processed += 1
                self.update_job_status(
                    job_id,
                    progress=i + 1,
                    message=f"Processing {i + 1}/{total}...",
                )

                try:
                    # Parse
                    parsed = await self.parse_disclosure(raw)
                    if not parsed:
                        result.records_skipped += 1
                        continue

                    # Validate
                    if not await self.validate_disclosure(parsed):
                        result.records_skipped += 1
                        continue

                    # Upload
                    disclosure_id = await self.upload_disclosure(
                        parsed, update_mode=update_mode
                    )

                    if disclosure_id:
                        if update_mode:
                            result.records_updated += 1
                        else:
                            result.records_inserted += 1
                    else:
                        result.records_skipped += 1

                except Exception as e:
                    result.records_failed += 1
                    result.add_error(f"Failed to process disclosure: {e}")

            # Complete
            result.completed_at = datetime.utcnow()
            self._job_status[job_id].status = "completed"
            self._job_status[job_id].completed_at = datetime.utcnow().isoformat()
            self._job_status[job_id].result = result
            self._job_status[job_id].message = (
                f"Completed: {result.records_inserted} inserted, "
                f"{result.records_updated} updated, "
                f"{result.records_failed} failed"
            )

            # Complete hook
            await self.on_complete(job_id, result)

        except Exception as e:
            result.add_error(f"ETL job failed: {e}")
            result.completed_at = datetime.utcnow()
            self._job_status[job_id].status = "failed"
            self._job_status[job_id].completed_at = datetime.utcnow().isoformat()
            self._job_status[job_id].message = f"Failed: {e}"
            self.logger.exception(f"ETL job {job_id} failed")

        return result

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(source_id={self.source_id})>"
