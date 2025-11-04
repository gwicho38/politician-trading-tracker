"""
Base classes and interfaces for the ingestion pipeline.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Generic, TypeVar
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class PipelineStatus(Enum):
    """Pipeline execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineError(Exception):
    """Base exception for pipeline errors"""
    pass


@dataclass
class PipelineMetrics:
    """Metrics collected during pipeline execution"""
    records_input: int = 0
    records_output: int = 0
    records_skipped: int = 0
    records_failed: int = 0
    duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.records_input == 0:
            return 0.0
        return (self.records_output / self.records_input) * 100


@dataclass
class PipelineContext:
    """Context passed between pipeline stages"""
    source_name: str
    source_type: str
    job_id: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PipelineResult(Generic[T]):
    """Result from a pipeline stage"""
    status: PipelineStatus
    data: List[T]
    context: PipelineContext
    metrics: PipelineMetrics
    stage_name: str
    errors: List[Exception] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Check if pipeline stage was successful"""
        return self.status in [PipelineStatus.SUCCESS, PipelineStatus.PARTIAL_SUCCESS]

    @property
    def failed(self) -> bool:
        """Check if pipeline stage failed"""
        return self.status == PipelineStatus.FAILED

    def add_error(self, error: Exception, record_id: Optional[str] = None):
        """Add an error to the result"""
        self.errors.append(error)
        self.metrics.errors.append(f"{record_id or 'Unknown'}: {str(error)}")
        self.metrics.records_failed += 1

    def add_warning(self, warning: str):
        """Add a warning to the result"""
        self.metrics.warnings.append(warning)


class PipelineStage(ABC, Generic[T]):
    """
    Abstract base class for pipeline stages.

    Each stage should:
    1. Accept input data
    2. Process it according to stage logic
    3. Return a PipelineResult with output data
    """

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")

    @abstractmethod
    async def process(
        self,
        data: List[Any],
        context: PipelineContext
    ) -> PipelineResult[T]:
        """
        Process data through this pipeline stage.

        Args:
            data: Input data from previous stage (or source)
            context: Pipeline context with metadata

        Returns:
            PipelineResult with processed data and metrics
        """
        pass

    def _create_result(
        self,
        status: PipelineStatus,
        data: List[T],
        context: PipelineContext,
        metrics: Optional[PipelineMetrics] = None
    ) -> PipelineResult[T]:
        """Helper to create a PipelineResult"""
        if metrics is None:
            metrics = PipelineMetrics()

        return PipelineResult(
            status=status,
            data=data,
            context=context,
            metrics=metrics,
            stage_name=self.name
        )

    async def __call__(
        self,
        data: List[Any],
        context: PipelineContext
    ) -> PipelineResult[T]:
        """Allow stage to be called as a function"""
        return await self.process(data, context)


@dataclass
class RawDisclosure:
    """Raw disclosure data from a source (before cleaning/normalization)"""
    source: str
    source_type: str
    raw_data: Dict[str, Any]
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    source_url: Optional[str] = None
    source_document_id: Optional[str] = None


@dataclass
class CleanedDisclosure:
    """Cleaned disclosure data (validated, no nulls in required fields)"""
    source: str
    politician_name: str
    transaction_date: datetime
    disclosure_date: datetime
    asset_name: str
    transaction_type: str
    raw_data: Dict[str, Any]

    # Optional fields
    asset_ticker: Optional[str] = None
    asset_type: Optional[str] = None
    amount_text: Optional[str] = None
    source_url: Optional[str] = None
    source_document_id: Optional[str] = None


@dataclass
class NormalizedDisclosure:
    """Normalized disclosure ready for database insertion"""
    politician_id: Optional[str]  # None if politician needs to be created
    politician_first_name: str
    politician_last_name: str
    politician_full_name: str
    politician_role: str
    politician_party: Optional[str]
    politician_state: Optional[str]

    transaction_date: datetime
    disclosure_date: datetime
    transaction_type: str

    asset_name: str
    asset_ticker: Optional[str]
    asset_type: Optional[str]

    amount_range_min: Optional[float]
    amount_range_max: Optional[float]
    amount_exact: Optional[float]

    source: str
    source_url: Optional[str]
    source_document_id: Optional[str]
    raw_data: Dict[str, Any]

    # Metadata
    processed_at: datetime = field(default_factory=datetime.utcnow)
