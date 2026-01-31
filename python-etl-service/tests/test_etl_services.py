"""
Tests for ETL Service wrapper implementations.

Tests cover:
- HouseETLService class
- SenateETLService class
- Registry integration
- ETLResult tracking
- Error handling
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

from app.services.etl_services import (
    HouseETLService,
    SenateETLService,
    init_services,
)
from app.lib.base_etl import ETLResult
from app.lib.registry import ETLRegistry


class TestHouseETLService:
    """Tests for HouseETLService class."""

    def test_source_id(self):
        """Test source_id is set correctly."""
        service = HouseETLService()
        assert service.source_id == "house"

    def test_source_name(self):
        """Test source_name is set correctly."""
        service = HouseETLService()
        assert service.source_name == "US House of Representatives"

    def test_is_registered_in_registry(self):
        """Test service is registered with ETLRegistry."""
        assert "house" in ETLRegistry.list_sources()

    def test_can_create_from_registry(self):
        """Test service can be created via registry."""
        service = ETLRegistry.create_instance("house")
        assert isinstance(service, HouseETLService)

    @pytest.mark.asyncio
    async def test_fetch_disclosures_returns_empty_list(self):
        """Test fetch_disclosures returns empty list (delegated to run_house_etl)."""
        service = HouseETLService()
        result = await service.fetch_disclosures()
        assert result == []

    @pytest.mark.asyncio
    async def test_parse_disclosure_returns_raw(self):
        """Test parse_disclosure passes through raw data."""
        service = HouseETLService()
        raw_data = {"id": "123", "name": "Test"}
        result = await service.parse_disclosure(raw_data)
        assert result == raw_data

    @pytest.mark.asyncio
    async def test_run_success(self):
        """Test successful run of House ETL."""
        service = HouseETLService()

        mock_job_status = {
            "test-job-123": {
                "status": "completed",
                "message": "Completed: 50 transactions from 10 PDFs",
                "total": 10,
                "rate_limiter_stats": {"calls": 100},
            }
        }

        with patch("app.services.house_etl.run_house_etl", new_callable=AsyncMock) as mock_run:
            with patch.dict("app.services.house_etl.JOB_STATUS", mock_job_status, clear=True):
                result = await service.run(
                    job_id="test-job-123",
                    year=2025,
                    limit=10,
                    update_mode=False,
                )

        assert isinstance(result, ETLResult)
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.records_inserted == 50
        assert result.records_processed == 10
        assert result.metadata["year"] == 2025
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_run_with_failed_status(self):
        """Test run handles failed status from job."""
        service = HouseETLService()

        mock_job_status = {
            "test-job-fail": {
                "status": "failed",
                "message": "Network timeout",
                "total": 0,
            }
        }

        with patch("app.services.house_etl.run_house_etl", new_callable=AsyncMock):
            with patch.dict("app.services.house_etl.JOB_STATUS", mock_job_status, clear=True):
                result = await service.run(job_id="test-job-fail", year=2025)

        assert len(result.errors) > 0
        assert "Network timeout" in result.errors[0]

    @pytest.mark.asyncio
    async def test_run_handles_exception(self):
        """Test run handles exceptions gracefully."""
        service = HouseETLService()

        with patch(
            "app.services.house_etl.run_house_etl",
            new_callable=AsyncMock,
            side_effect=Exception("Database connection failed"),
        ):
            result = await service.run(job_id="test-job-error", year=2025)

        assert len(result.errors) > 0
        assert "Database connection failed" in result.errors[0]
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_run_parses_transaction_count(self):
        """Test run correctly parses transaction count from message."""
        service = HouseETLService()

        test_cases = [
            ("Completed: 100 transactions from 20 PDFs", 100),
            ("Processed 25 transactions", 25),
            ("Found 0 transactions", 0),
        ]

        for message, expected_count in test_cases:
            mock_job_status = {
                "test-job": {
                    "status": "completed",
                    "message": message,
                    "total": 5,
                }
            }

            with patch("app.services.house_etl.run_house_etl", new_callable=AsyncMock):
                with patch.dict("app.services.house_etl.JOB_STATUS", mock_job_status, clear=True):
                    result = await service.run(job_id="test-job", year=2025)

            assert result.records_inserted == expected_count, f"Failed for message: {message}"

    @pytest.mark.asyncio
    async def test_run_handles_unparseable_message(self):
        """Test run handles messages without transaction counts."""
        service = HouseETLService()

        mock_job_status = {
            "test-job": {
                "status": "completed",
                "message": "Job completed successfully",  # No transaction count
                "total": 5,
            }
        }

        with patch("app.services.house_etl.run_house_etl", new_callable=AsyncMock):
            with patch.dict("app.services.house_etl.JOB_STATUS", mock_job_status, clear=True):
                result = await service.run(job_id="test-job", year=2025)

        # Should not crash, records_inserted stays at default (0)
        assert result.records_inserted == 0
        assert len(result.errors) == 0


class TestSenateETLService:
    """Tests for SenateETLService class."""

    def test_source_id(self):
        """Test source_id is set correctly."""
        service = SenateETLService()
        assert service.source_id == "senate"

    def test_source_name(self):
        """Test source_name is set correctly."""
        service = SenateETLService()
        assert service.source_name == "US Senate"

    def test_is_registered_in_registry(self):
        """Test service is registered with ETLRegistry."""
        assert "senate" in ETLRegistry.list_sources()

    def test_can_create_from_registry(self):
        """Test service can be created via registry."""
        service = ETLRegistry.create_instance("senate")
        assert isinstance(service, SenateETLService)

    @pytest.mark.asyncio
    async def test_fetch_disclosures_returns_empty_list(self):
        """Test fetch_disclosures returns empty list (delegated to run_senate_etl)."""
        service = SenateETLService()
        result = await service.fetch_disclosures()
        assert result == []

    @pytest.mark.asyncio
    async def test_parse_disclosure_returns_raw(self):
        """Test parse_disclosure passes through raw data."""
        service = SenateETLService()
        raw_data = {"id": "456", "senator": "Test Senator"}
        result = await service.parse_disclosure(raw_data)
        assert result == raw_data

    @pytest.mark.asyncio
    async def test_run_success(self):
        """Test successful run of Senate ETL."""
        service = SenateETLService()

        mock_job_status = {
            "senate-job-123": {
                "status": "completed",
                "message": "Completed: 75 transactions from Senate disclosures",
                "total": 15,
            }
        }

        with patch("app.services.senate_etl.run_senate_etl", new_callable=AsyncMock):
            with patch.dict("app.services.house_etl.JOB_STATUS", mock_job_status, clear=True):
                result = await service.run(
                    job_id="senate-job-123",
                    lookback_days=30,
                    limit=20,
                    update_mode=True,
                )

        assert isinstance(result, ETLResult)
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.records_inserted == 75
        assert result.records_processed == 15
        assert result.metadata["lookback_days"] == 30
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_run_with_failed_status(self):
        """Test run handles failed status from job."""
        service = SenateETLService()

        mock_job_status = {
            "senate-job-fail": {
                "status": "failed",
                "message": "EFD database unavailable",
                "total": 0,
            }
        }

        with patch("app.services.senate_etl.run_senate_etl", new_callable=AsyncMock):
            with patch.dict("app.services.house_etl.JOB_STATUS", mock_job_status, clear=True):
                result = await service.run(job_id="senate-job-fail", lookback_days=7)

        assert len(result.errors) > 0
        assert "EFD database unavailable" in result.errors[0]

    @pytest.mark.asyncio
    async def test_run_handles_exception(self):
        """Test run handles exceptions gracefully."""
        service = SenateETLService()

        with patch(
            "app.services.senate_etl.run_senate_etl",
            new_callable=AsyncMock,
            side_effect=Exception("Senate scraper timeout"),
        ):
            result = await service.run(job_id="senate-job-error", lookback_days=30)

        assert len(result.errors) > 0
        assert "Senate scraper timeout" in result.errors[0]
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_run_parses_transaction_count(self):
        """Test run correctly parses transaction count from message."""
        service = SenateETLService()

        mock_job_status = {
            "senate-job": {
                "status": "completed",
                "message": "Processed 150 transactions from EFD",
                "total": 30,
            }
        }

        with patch("app.services.senate_etl.run_senate_etl", new_callable=AsyncMock):
            with patch.dict("app.services.house_etl.JOB_STATUS", mock_job_status, clear=True):
                result = await service.run(job_id="senate-job", lookback_days=14)

        assert result.records_inserted == 150

    @pytest.mark.asyncio
    async def test_run_with_default_parameters(self):
        """Test run with default parameters."""
        service = SenateETLService()

        mock_job_status = {
            "default-job": {
                "status": "completed",
                "message": "Done",
                "total": 5,
            }
        }

        with patch("app.services.senate_etl.run_senate_etl", new_callable=AsyncMock) as mock_run:
            with patch.dict("app.services.house_etl.JOB_STATUS", mock_job_status, clear=True):
                result = await service.run(job_id="default-job")

        # Verify default lookback_days was passed
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["lookback_days"] == 30
        assert call_kwargs["limit"] is None
        assert call_kwargs["update_mode"] is False


class TestETLRegistry:
    """Tests for ETLRegistry integration with services."""

    def test_list_sources_includes_house(self):
        """Test house source is listed."""
        sources = ETLRegistry.list_sources()
        assert "house" in sources

    def test_list_sources_includes_senate(self):
        """Test senate source is listed."""
        sources = ETLRegistry.list_sources()
        assert "senate" in sources

    def test_get_service_class_house(self):
        """Test getting service class for house."""
        service_class = ETLRegistry.get("house")
        assert service_class is not None
        assert service_class.source_id == "house"
        assert service_class.source_name == "US House of Representatives"

    def test_get_service_class_senate(self):
        """Test getting service class for senate."""
        service_class = ETLRegistry.get("senate")
        assert service_class is not None
        assert service_class.source_id == "senate"
        assert service_class.source_name == "US Senate"

    def test_create_instance_invalid_source(self):
        """Test creating instance with invalid source raises error."""
        with pytest.raises(KeyError, match="Unknown ETL source"):
            ETLRegistry.create_instance("invalid_source")


class TestInitServices:
    """Tests for init_services function."""

    def test_init_services_runs_without_error(self):
        """Test init_services completes without error."""
        # Should not raise any exceptions
        init_services()

    def test_services_registered_after_init(self):
        """Test services are registered after init_services."""
        init_services()
        sources = ETLRegistry.list_sources()
        assert len(sources) >= 2
        assert "house" in sources
        assert "senate" in sources


class TestETLResultTracking:
    """Tests for ETLResult tracking in services."""

    @pytest.mark.asyncio
    async def test_house_etl_result_has_timestamps(self):
        """Test House ETL result has proper timestamps."""
        service = HouseETLService()

        mock_job_status = {"ts-job": {"status": "completed", "message": "", "total": 0}}

        with patch("app.services.house_etl.run_house_etl", new_callable=AsyncMock):
            with patch.dict("app.services.house_etl.JOB_STATUS", mock_job_status, clear=True):
                before = datetime.now(timezone.utc)
                result = await service.run(job_id="ts-job", year=2025)
                after = datetime.now(timezone.utc)

        assert result.started_at >= before
        assert result.completed_at <= after
        assert result.started_at <= result.completed_at

    @pytest.mark.asyncio
    async def test_senate_etl_result_metadata(self):
        """Test Senate ETL result includes proper metadata."""
        service = SenateETLService()

        mock_job_status = {
            "meta-job": {
                "status": "completed",
                "message": "Done",
                "total": 10,
            }
        }

        with patch("app.services.senate_etl.run_senate_etl", new_callable=AsyncMock):
            with patch.dict("app.services.house_etl.JOB_STATUS", mock_job_status, clear=True):
                result = await service.run(job_id="meta-job", lookback_days=7)

        assert "lookback_days" in result.metadata
        assert result.metadata["lookback_days"] == 7
        assert "source_status" in result.metadata
