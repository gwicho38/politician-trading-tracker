"""
Tests for California ETL Service (app/services/california_etl.py).

Tests cover:
- Registration in ETL registry
- Stub behavior (returns empty results)
- Graceful completion via run()
"""

import pytest
from app.services.california_etl import CaliforniaETLService
from app.lib.registry import ETLRegistry


class TestCaliforniaRegistration:
    """Tests for CaliforniaETLService registry integration."""

    def test_source_id(self):
        service = CaliforniaETLService()
        assert service.source_id == "california"

    def test_source_name(self):
        service = CaliforniaETLService()
        assert service.source_name == "California Financial Disclosures"

    def test_is_registered_in_registry(self):
        assert ETLRegistry.is_registered("california")

    def test_can_create_from_registry(self):
        service = ETLRegistry.create_instance("california")
        assert isinstance(service, CaliforniaETLService)


class TestCaliforniaStubBehavior:
    """Tests for stub behavior."""

    @pytest.mark.asyncio
    async def test_fetch_disclosures_returns_empty(self):
        service = CaliforniaETLService()
        result = await service.fetch_disclosures()
        assert result == []

    @pytest.mark.asyncio
    async def test_parse_disclosure_passthrough(self):
        service = CaliforniaETLService()
        raw = {"some": "data"}
        result = await service.parse_disclosure(raw)
        assert result == raw

    @pytest.mark.asyncio
    async def test_run_completes_cleanly(self):
        """run() should complete without errors even with no data."""
        service = CaliforniaETLService()
        result = await service.run(job_id="test-ca-job")

        assert result.is_success
        assert result.records_processed == 0
        assert result.records_inserted == 0
        assert len(result.warnings) == 1  # "No disclosures fetched"
