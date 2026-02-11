"""
Tests for EU Parliament ETL Service (app/services/eu_etl.py).

Tests cover:
- Registration in ETL registry
- Stub behavior (returns empty results)
- Graceful completion via run()
"""

import pytest
from app.services.eu_etl import EUParliamentETLService
from app.lib.registry import ETLRegistry


class TestEUParliamentRegistration:
    """Tests for EUParliamentETLService registry integration."""

    def test_source_id(self):
        service = EUParliamentETLService()
        assert service.source_id == "eu_parliament"

    def test_source_name(self):
        service = EUParliamentETLService()
        assert service.source_name == "EU Parliament Declarations"

    def test_is_registered_in_registry(self):
        assert ETLRegistry.is_registered("eu_parliament")

    def test_can_create_from_registry(self):
        service = ETLRegistry.create_instance("eu_parliament")
        assert isinstance(service, EUParliamentETLService)


class TestEUParliamentStubBehavior:
    """Tests for stub behavior."""

    @pytest.mark.asyncio
    async def test_fetch_disclosures_returns_empty(self):
        service = EUParliamentETLService()
        result = await service.fetch_disclosures()
        assert result == []

    @pytest.mark.asyncio
    async def test_parse_disclosure_passthrough(self):
        service = EUParliamentETLService()
        raw = {"some": "data"}
        result = await service.parse_disclosure(raw)
        assert result == raw

    @pytest.mark.asyncio
    async def test_run_completes_cleanly(self):
        """run() should complete without errors even with no data."""
        service = EUParliamentETLService()
        result = await service.run(job_id="test-eu-job")

        assert result.is_success
        assert result.records_processed == 0
        assert result.records_inserted == 0
        assert len(result.warnings) == 1  # "No disclosures fetched"
