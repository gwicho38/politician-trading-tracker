"""
Tests for base ETL service (app/lib/base_etl.py).

Tests:
- ETLResult - Result tracking dataclass
- JobStatus - Job status dataclass
- BaseETLService - Abstract base class
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


# =============================================================================
# ETLResult Tests
# =============================================================================

class TestETLResult:
    """Tests for ETLResult dataclass."""

    def test_default_values(self):
        """ETLResult initializes with default zero values."""
        from app.lib.base_etl import ETLResult

        result = ETLResult()

        assert result.records_processed == 0
        assert result.records_inserted == 0
        assert result.records_updated == 0
        assert result.records_skipped == 0
        assert result.records_failed == 0
        assert result.errors == []
        assert result.warnings == []
        assert result.started_at is None
        assert result.completed_at is None
        assert result.metadata == {}

    def test_duration_seconds_calculation(self):
        """ETLResult calculates duration correctly."""
        from app.lib.base_etl import ETLResult

        start = datetime(2024, 1, 1, 10, 0, 0)
        end = datetime(2024, 1, 1, 10, 5, 30)

        result = ETLResult(started_at=start, completed_at=end)

        assert result.duration_seconds == 330.0  # 5 minutes 30 seconds

    def test_duration_seconds_none_when_incomplete(self):
        """ETLResult returns None duration when times not set."""
        from app.lib.base_etl import ETLResult

        result = ETLResult(started_at=datetime.now())

        assert result.duration_seconds is None

    def test_success_rate_with_no_failures(self):
        """ETLResult success_rate is 100% with no failures."""
        from app.lib.base_etl import ETLResult

        result = ETLResult(records_processed=100, records_inserted=100)

        assert result.success_rate == 100.0

    def test_success_rate_with_failures(self):
        """ETLResult success_rate accounts for failures."""
        from app.lib.base_etl import ETLResult

        result = ETLResult(records_processed=100, records_failed=25)

        assert result.success_rate == 75.0

    def test_success_rate_with_zero_processed(self):
        """ETLResult success_rate is 100% when no records processed."""
        from app.lib.base_etl import ETLResult

        result = ETLResult()

        assert result.success_rate == 100.0

    def test_is_success_with_no_errors(self):
        """ETLResult is_success is True with no errors."""
        from app.lib.base_etl import ETLResult

        result = ETLResult(records_failed=5)  # Failures but no errors

        assert result.is_success is True

    def test_is_success_with_errors(self):
        """ETLResult is_success is False with errors."""
        from app.lib.base_etl import ETLResult

        result = ETLResult()
        result.add_error("Something went wrong")

        assert result.is_success is False

    def test_add_error(self):
        """ETLResult add_error appends error message."""
        from app.lib.base_etl import ETLResult

        result = ETLResult()
        result.add_error("Error 1")
        result.add_error("Error 2")

        assert len(result.errors) == 2
        assert "Error 1" in result.errors
        assert "Error 2" in result.errors

    def test_add_warning(self):
        """ETLResult add_warning appends warning message."""
        from app.lib.base_etl import ETLResult

        result = ETLResult()
        result.add_warning("Warning 1")
        result.add_warning("Warning 2")

        assert len(result.warnings) == 2
        assert "Warning 1" in result.warnings

    def test_to_dict_serialization(self):
        """ETLResult to_dict produces correct dictionary."""
        from app.lib.base_etl import ETLResult

        start = datetime(2024, 1, 1, 10, 0, 0)
        end = datetime(2024, 1, 1, 10, 5, 0)

        result = ETLResult(
            records_processed=100,
            records_inserted=80,
            records_updated=10,
            records_skipped=5,
            records_failed=5,
            started_at=start,
            completed_at=end,
        )
        result.add_error("Test error")
        result.add_warning("Test warning")

        data = result.to_dict()

        assert data["records_processed"] == 100
        assert data["records_inserted"] == 80
        assert data["records_updated"] == 10
        assert data["records_skipped"] == 5
        assert data["records_failed"] == 5
        assert data["duration_seconds"] == 300.0
        assert data["success_rate"] == 95.0
        assert data["is_success"] is False
        assert "Test error" in data["errors"]
        assert "Test warning" in data["warnings"]
        assert data["started_at"] == "2024-01-01T10:00:00"
        assert data["completed_at"] == "2024-01-01T10:05:00"


# =============================================================================
# JobStatus Tests
# =============================================================================

class TestJobStatus:
    """Tests for JobStatus dataclass."""

    def test_default_values(self):
        """JobStatus initializes with default values."""
        from app.lib.base_etl import JobStatus

        status = JobStatus()

        assert status.status == "queued"
        assert status.progress == 0
        assert status.total is None
        assert status.message == "Job queued"
        assert status.started_at is None
        assert status.completed_at is None
        assert status.result is None

    def test_to_dict_serialization(self):
        """JobStatus to_dict produces correct dictionary."""
        from app.lib.base_etl import JobStatus

        status = JobStatus(
            status="running",
            progress=50,
            total=100,
            message="Processing...",
            started_at="2024-01-01T10:00:00",
        )

        data = status.to_dict()

        assert data["status"] == "running"
        assert data["progress"] == 50
        assert data["total"] == 100
        assert data["message"] == "Processing..."
        assert data["started_at"] == "2024-01-01T10:00:00"
        assert data["completed_at"] is None
        assert data["result"] is None

    def test_to_dict_with_result(self):
        """JobStatus to_dict includes ETLResult."""
        from app.lib.base_etl import JobStatus, ETLResult

        result = ETLResult(records_processed=10, records_inserted=10)
        status = JobStatus(
            status="completed",
            progress=100,
            total=100,
            result=result,
        )

        data = status.to_dict()

        assert data["result"] is not None
        assert data["result"]["records_processed"] == 10


# =============================================================================
# BaseETLService Tests
# =============================================================================

class TestBaseETLService:
    """Tests for BaseETLService abstract class."""

    @pytest.fixture
    def concrete_etl_service(self):
        """Create a concrete implementation of BaseETLService."""
        from app.lib.base_etl import BaseETLService

        class TestETLService(BaseETLService):
            source_id = "test"
            source_name = "Test Source"

            def __init__(self):
                super().__init__()
                self.fetch_called = False
                self.parse_called = False
                self.disclosures_to_return = []

            async def fetch_disclosures(self, **kwargs):
                self.fetch_called = True
                self.fetch_kwargs = kwargs
                return self.disclosures_to_return

            async def parse_disclosure(self, raw):
                self.parse_called = True
                return raw  # Return as-is for testing

        return TestETLService()

    # -------------------------------------------------------------------------
    # Initialization Tests
    # -------------------------------------------------------------------------

    def test_service_initialization(self, concrete_etl_service):
        """BaseETLService initializes correctly."""
        assert concrete_etl_service.source_id == "test"
        assert concrete_etl_service.source_name == "Test Source"
        assert concrete_etl_service._job_status == {}

    def test_repr(self, concrete_etl_service):
        """BaseETLService has correct string representation."""
        repr_str = repr(concrete_etl_service)

        assert "TestETLService" in repr_str
        assert "source_id=test" in repr_str

    # -------------------------------------------------------------------------
    # Job Status Tests
    # -------------------------------------------------------------------------

    def test_get_job_status_none_when_not_started(self, concrete_etl_service):
        """get_job_status returns None for unknown job."""
        status = concrete_etl_service.get_job_status("unknown-job")

        assert status is None

    def test_update_job_status_creates_new(self, concrete_etl_service):
        """update_job_status creates new status if not exists."""
        concrete_etl_service.update_job_status(
            "job-1",
            status="running",
            progress=10,
            total=100,
            message="Starting...",
        )

        status = concrete_etl_service.get_job_status("job-1")
        assert status.status == "running"
        assert status.progress == 10
        assert status.total == 100
        assert status.message == "Starting..."

    def test_update_job_status_updates_existing(self, concrete_etl_service):
        """update_job_status updates existing status."""
        concrete_etl_service.update_job_status("job-1", status="running")
        concrete_etl_service.update_job_status("job-1", progress=50, message="Halfway")

        status = concrete_etl_service.get_job_status("job-1")
        assert status.status == "running"  # Unchanged
        assert status.progress == 50
        assert status.message == "Halfway"

    # -------------------------------------------------------------------------
    # Validation Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_default_validation_requires_asset_name(self, concrete_etl_service):
        """Default validate_disclosure requires asset_name."""
        valid = await concrete_etl_service.validate_disclosure(
            {"asset_name": "Apple Inc."}
        )
        invalid = await concrete_etl_service.validate_disclosure({"ticker": "AAPL"})

        assert valid is True
        assert invalid is False

    @pytest.mark.asyncio
    async def test_default_validation_rejects_empty_asset_name(self, concrete_etl_service):
        """Default validate_disclosure rejects empty asset_name."""
        result = await concrete_etl_service.validate_disclosure({"asset_name": ""})

        assert result is False

    # -------------------------------------------------------------------------
    # Run Method Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_run_with_no_disclosures(self, concrete_etl_service):
        """run() handles case with no disclosures fetched."""
        concrete_etl_service.disclosures_to_return = []

        result = await concrete_etl_service.run("job-1")

        assert result.records_processed == 0
        assert result.records_inserted == 0
        assert "No disclosures" in result.warnings[0]

    @pytest.mark.asyncio
    async def test_run_calls_fetch_disclosures(self, concrete_etl_service):
        """run() calls fetch_disclosures with kwargs."""
        concrete_etl_service.disclosures_to_return = []

        await concrete_etl_service.run("job-1", year=2024, lookback=30)

        assert concrete_etl_service.fetch_called is True
        assert concrete_etl_service.fetch_kwargs["year"] == 2024
        assert concrete_etl_service.fetch_kwargs["lookback"] == 30

    @pytest.mark.asyncio
    async def test_run_processes_disclosures(self, concrete_etl_service):
        """run() processes each disclosure."""
        concrete_etl_service.disclosures_to_return = [
            {"asset_name": "Asset 1"},
            {"asset_name": "Asset 2"},
        ]

        # Mock upload to succeed
        with patch.object(
            concrete_etl_service,
            "upload_disclosure",
            new_callable=AsyncMock,
            return_value="uuid-123"
        ):
            result = await concrete_etl_service.run("job-1")

        assert result.records_processed == 2
        assert result.records_inserted == 2

    @pytest.mark.asyncio
    async def test_run_respects_limit(self, concrete_etl_service):
        """run() respects limit parameter."""
        concrete_etl_service.disclosures_to_return = [
            {"asset_name": "Asset 1"},
            {"asset_name": "Asset 2"},
            {"asset_name": "Asset 3"},
        ]

        with patch.object(
            concrete_etl_service,
            "upload_disclosure",
            new_callable=AsyncMock,
            return_value="uuid-123"
        ):
            result = await concrete_etl_service.run("job-1", limit=2)

        assert result.records_processed == 2

    @pytest.mark.asyncio
    async def test_run_handles_parse_returning_none(self, concrete_etl_service):
        """run() skips disclosures where parse returns None."""
        from app.lib.base_etl import BaseETLService

        class SkippingService(BaseETLService):
            source_id = "skip"
            source_name = "Skip Service"

            async def fetch_disclosures(self, **kwargs):
                return [{"raw": "data1"}, {"raw": "data2"}]

            async def parse_disclosure(self, raw):
                return None  # Always skip

        service = SkippingService()
        result = await service.run("job-1")

        assert result.records_processed == 2
        assert result.records_skipped == 2
        assert result.records_inserted == 0

    @pytest.mark.asyncio
    async def test_run_handles_validation_failure(self, concrete_etl_service):
        """run() skips disclosures that fail validation."""
        concrete_etl_service.disclosures_to_return = [
            {"asset_name": "Valid"},
            {"no_asset_name": "Invalid"},
        ]

        with patch.object(
            concrete_etl_service,
            "upload_disclosure",
            new_callable=AsyncMock,
            return_value="uuid-123"
        ):
            result = await concrete_etl_service.run("job-1")

        assert result.records_processed == 2
        assert result.records_inserted == 1
        assert result.records_skipped == 1

    @pytest.mark.asyncio
    async def test_run_handles_upload_failure(self, concrete_etl_service):
        """run() handles upload returning None."""
        concrete_etl_service.disclosures_to_return = [
            {"asset_name": "Asset 1"},
        ]

        with patch.object(
            concrete_etl_service,
            "upload_disclosure",
            new_callable=AsyncMock,
            return_value=None
        ):
            result = await concrete_etl_service.run("job-1")

        assert result.records_processed == 1
        assert result.records_skipped == 1
        assert result.records_inserted == 0

    @pytest.mark.asyncio
    async def test_run_counts_updated_in_update_mode(self, concrete_etl_service):
        """run() counts records_updated when update_mode=True."""
        concrete_etl_service.disclosures_to_return = [
            {"asset_name": "Asset 1"},
        ]

        with patch.object(
            concrete_etl_service,
            "upload_disclosure",
            new_callable=AsyncMock,
            return_value="uuid-123"
        ):
            result = await concrete_etl_service.run("job-1", update_mode=True)

        assert result.records_updated == 1
        assert result.records_inserted == 0

    @pytest.mark.asyncio
    async def test_run_handles_exception_in_disclosure(self, concrete_etl_service):
        """run() handles exception during disclosure processing."""
        concrete_etl_service.disclosures_to_return = [
            {"asset_name": "Asset 1"},
        ]

        with patch.object(
            concrete_etl_service,
            "upload_disclosure",
            new_callable=AsyncMock,
            side_effect=Exception("Upload failed")
        ):
            result = await concrete_etl_service.run("job-1")

        assert result.records_processed == 1
        assert result.records_failed == 1
        assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_run_sets_job_status_on_completion(self, concrete_etl_service):
        """run() updates job status on completion."""
        concrete_etl_service.disclosures_to_return = [
            {"asset_name": "Asset 1"},
        ]

        with patch.object(
            concrete_etl_service,
            "upload_disclosure",
            new_callable=AsyncMock,
            return_value="uuid-123"
        ):
            await concrete_etl_service.run("job-1")

        status = concrete_etl_service.get_job_status("job-1")
        assert status.status == "completed"
        assert status.result is not None
        assert status.completed_at is not None

    @pytest.mark.asyncio
    async def test_run_sets_timestamps(self, concrete_etl_service):
        """run() sets started_at and completed_at timestamps."""
        concrete_etl_service.disclosures_to_return = []

        result = await concrete_etl_service.run("job-1")

        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.completed_at >= result.started_at

    @pytest.mark.asyncio
    async def test_run_handles_fatal_exception(self, concrete_etl_service):
        """run() handles fatal exception and sets failed status."""
        from app.lib.base_etl import BaseETLService

        class FailingService(BaseETLService):
            source_id = "fail"
            source_name = "Failing Service"

            async def fetch_disclosures(self, **kwargs):
                raise Exception("Network error")

            async def parse_disclosure(self, raw):
                return raw

        service = FailingService()
        result = await service.run("job-1")

        assert result.is_success is False
        assert len(result.errors) == 1
        assert "Network error" in result.errors[0]

        status = service.get_job_status("job-1")
        assert status.status == "failed"

    # -------------------------------------------------------------------------
    # Hook Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_on_start_hook_called(self, concrete_etl_service):
        """run() calls on_start hook."""
        concrete_etl_service.disclosures_to_return = []

        on_start_called = []

        async def custom_on_start(job_id, **kwargs):
            on_start_called.append(job_id)

        with patch.object(
            concrete_etl_service,
            "on_start",
            new_callable=AsyncMock,
            side_effect=custom_on_start
        ):
            await concrete_etl_service.run("job-1", year=2024)

        assert "job-1" in on_start_called

    @pytest.mark.asyncio
    async def test_on_complete_hook_called(self, concrete_etl_service):
        """run() calls on_complete hook when disclosures are processed."""
        # Need some disclosures for on_complete to be called
        concrete_etl_service.disclosures_to_return = [
            {"asset_name": "Asset 1"},
        ]

        on_complete_called = []

        async def custom_on_complete(job_id, result):
            on_complete_called.append((job_id, result))

        with patch.object(
            concrete_etl_service,
            "upload_disclosure",
            new_callable=AsyncMock,
            return_value="uuid-123"
        ):
            with patch.object(
                concrete_etl_service,
                "on_complete",
                new_callable=AsyncMock,
                side_effect=custom_on_complete
            ):
                await concrete_etl_service.run("job-1")

        assert len(on_complete_called) == 1
        assert on_complete_called[0][0] == "job-1"
