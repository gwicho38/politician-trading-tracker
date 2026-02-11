"""
Tests for QuiverQuant ETL Service (app/services/quiver_etl.py).

Tests cover:
- QuiverQuantETLService registration and attributes
- API data fetching with auth
- Date filtering by lookback_days
- Field mapping (Representative, Ticker, Amount range, etc.)
- Transaction type mapping
- Validation logic
- Error handling for missing API key
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone

from app.services.quiver_etl import (
    QuiverQuantETLService,
    _parse_qq_amount_range,
    _map_transaction_type,
    _map_chamber,
    _map_role,
)
from app.lib.registry import ETLRegistry


# =============================================================================
# Helper: Sample QuiverQuant API record
# =============================================================================

def _qq_record(**overrides):
    """Create a sample QuiverQuant API record with reasonable defaults."""
    base = {
        "Representative": "Nancy Pelosi",
        "BioGuideID": "P000197",
        "Ticker": "AAPL",
        "Description": "Apple Inc.",
        "Transaction": "Purchase",
        "Amount": "$1,001 - $15,000",
        "TransactionDate": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "ReportDate": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "House": "House",
        "District": "CA-11",
        "Party": "D",
    }
    base.update(overrides)
    return base


# =============================================================================
# Registration Tests
# =============================================================================

class TestQuiverQuantRegistration:
    """Tests for QuiverQuantETLService registry integration."""

    def test_source_id(self):
        service = QuiverQuantETLService()
        assert service.source_id == "quiverquant"

    def test_source_name(self):
        service = QuiverQuantETLService()
        assert service.source_name == "QuiverQuant Congress Trading"

    def test_is_registered_in_registry(self):
        assert ETLRegistry.is_registered("quiverquant")

    def test_can_create_from_registry(self):
        service = ETLRegistry.create_instance("quiverquant")
        assert isinstance(service, QuiverQuantETLService)


# =============================================================================
# Amount Range Parsing Tests
# =============================================================================

class TestAmountRangeParsing:
    """Tests for _parse_qq_amount_range helper."""

    def test_standard_range(self):
        result = _parse_qq_amount_range("$1,001 - $15,000")
        assert result["value_low"] == 1001
        assert result["value_high"] == 15000

    def test_high_range(self):
        result = _parse_qq_amount_range("$500,001 - $1,000,000")
        assert result["value_low"] == 500001
        assert result["value_high"] == 1000000

    def test_empty_string(self):
        result = _parse_qq_amount_range("")
        assert result["value_low"] is None
        assert result["value_high"] is None

    def test_none_value(self):
        result = _parse_qq_amount_range(None)
        assert result["value_low"] is None
        assert result["value_high"] is None


# =============================================================================
# Transaction Type Mapping Tests
# =============================================================================

class TestTransactionTypeMapping:
    """Tests for _map_transaction_type helper."""

    def test_purchase(self):
        assert _map_transaction_type("Purchase") == "purchase"

    def test_sale_full(self):
        assert _map_transaction_type("Sale (Full)") == "sale"

    def test_sale_partial(self):
        assert _map_transaction_type("Sale (Partial)") == "sale"

    def test_sale_plain(self):
        assert _map_transaction_type("Sale") == "sale"

    def test_exchange(self):
        assert _map_transaction_type("Exchange") == "exchange"

    def test_unknown(self):
        assert _map_transaction_type("Something Else") == "unknown"

    def test_empty(self):
        assert _map_transaction_type("") == "unknown"

    def test_none(self):
        assert _map_transaction_type(None) == "unknown"


# =============================================================================
# Chamber and Role Mapping Tests
# =============================================================================

class TestChamberMapping:
    """Tests for _map_chamber and _map_role helpers."""

    def test_house_chamber(self):
        assert _map_chamber("House") == "house"

    def test_senate_chamber(self):
        assert _map_chamber("Senate") == "senate"

    def test_default_chamber(self):
        assert _map_chamber("") == "house"

    def test_house_role(self):
        assert _map_role("House") == "Representative"

    def test_senate_role(self):
        assert _map_role("Senate") == "Senator"


# =============================================================================
# on_start() Tests
# =============================================================================

class TestOnStart:
    """Tests for on_start hook (API key validation)."""

    @pytest.mark.asyncio
    async def test_raises_without_api_key(self):
        service = QuiverQuantETLService()
        service.api_key = ""
        with pytest.raises(ValueError, match="QUIVERQUANT_API_KEY"):
            await service.on_start("test-job")

    @pytest.mark.asyncio
    async def test_succeeds_with_api_key(self):
        service = QuiverQuantETLService()
        service.api_key = "test-key-123"
        await service.on_start("test-job")  # Should not raise


# =============================================================================
# fetch_disclosures() Tests
# =============================================================================

class TestFetchDisclosures:
    """Tests for fetch_disclosures method."""

    @pytest.mark.asyncio
    async def test_fetches_with_auth_header(self):
        service = QuiverQuantETLService()
        service.api_key = "test-api-key"

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        mock_data = [_qq_record(TransactionDate=today)]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.quiver_etl.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await service.fetch_disclosures(lookback_days=30)

            # Verify auth header was sent
            call_kwargs = mock_client.get.call_args
            assert "Bearer test-api-key" in call_kwargs.kwargs["headers"]["Authorization"]

            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_filters_by_lookback_days(self):
        service = QuiverQuantETLService()
        service.api_key = "test-key"

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d")

        mock_data = [
            _qq_record(TransactionDate=today, Representative="Recent"),
            _qq_record(TransactionDate=old_date, Representative="Old"),
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_data
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.quiver_etl.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await service.fetch_disclosures(lookback_days=30)
            assert len(result) == 1
            assert result[0]["Representative"] == "Recent"

    @pytest.mark.asyncio
    async def test_raises_on_401(self):
        """Should raise ValueError on 401 (bad API key)."""
        service = QuiverQuantETLService()
        service.api_key = "bad-key"

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch("app.services.quiver_etl.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            with pytest.raises(ValueError, match="invalid or expired"):
                await service.fetch_disclosures(lookback_days=30)


# =============================================================================
# parse_disclosure() Tests
# =============================================================================

class TestParseDisclosure:
    """Tests for parse_disclosure method."""

    @pytest.mark.asyncio
    async def test_maps_basic_fields(self):
        service = QuiverQuantETLService()
        raw = _qq_record()
        result = await service.parse_disclosure(raw)

        assert result["politician_name"] == "Nancy Pelosi"
        assert result["asset_ticker"] == "AAPL"
        assert result["asset_name"] == "Apple Inc."
        assert result["transaction_type"] == "purchase"
        assert result["bioguide_id"] == "P000197"

    @pytest.mark.asyncio
    async def test_maps_senate_role(self):
        service = QuiverQuantETLService()
        raw = _qq_record(House="Senate")
        result = await service.parse_disclosure(raw)

        assert result["chamber"] == "senate"
        assert result["role"] == "Senator"

    @pytest.mark.asyncio
    async def test_maps_house_role(self):
        service = QuiverQuantETLService()
        raw = _qq_record(House="House")
        result = await service.parse_disclosure(raw)

        assert result["chamber"] == "house"
        assert result["role"] == "Representative"

    @pytest.mark.asyncio
    async def test_maps_amount_range(self):
        service = QuiverQuantETLService()
        raw = _qq_record(Amount="$15,001 - $50,000")
        result = await service.parse_disclosure(raw)

        assert result["value_low"] == 15001
        assert result["value_high"] == 50000

    @pytest.mark.asyncio
    async def test_extracts_state_from_district(self):
        service = QuiverQuantETLService()
        raw = _qq_record(District="CA-11")
        result = await service.parse_disclosure(raw)

        assert result["state"] == "CA"

    @pytest.mark.asyncio
    async def test_parses_name_parts(self):
        service = QuiverQuantETLService()
        raw = _qq_record(Representative="John Smith Jr")
        result = await service.parse_disclosure(raw)

        assert result["first_name"] == "John"
        assert result["last_name"] == "Smith Jr"

    @pytest.mark.asyncio
    async def test_returns_none_for_empty_representative(self):
        service = QuiverQuantETLService()
        raw = _qq_record(Representative="")
        result = await service.parse_disclosure(raw)

        assert result is None

    @pytest.mark.asyncio
    async def test_handles_missing_ticker(self):
        service = QuiverQuantETLService()
        raw = _qq_record(Ticker="", Description="Some Real Estate Asset")
        result = await service.parse_disclosure(raw)

        assert result["asset_name"] == "Some Real Estate Asset"
        # Ticker might be None or extracted from description

    @pytest.mark.asyncio
    async def test_date_truncation(self):
        """Dates should be truncated to YYYY-MM-DD format."""
        service = QuiverQuantETLService()
        raw = _qq_record(
            TransactionDate="2025-01-15T00:00:00Z",
            ReportDate="2025-01-20T12:30:00Z",
        )
        result = await service.parse_disclosure(raw)

        assert result["transaction_date"] == "2025-01-15"
        assert result["disclosure_date"] == "2025-01-20"


# =============================================================================
# validate_disclosure() Tests
# =============================================================================

class TestValidateDisclosure:
    """Tests for validate_disclosure method."""

    @pytest.mark.asyncio
    async def test_valid_disclosure(self):
        service = QuiverQuantETLService()
        disclosure = {"asset_name": "Apple Inc.", "politician_name": "Nancy Pelosi"}
        assert await service.validate_disclosure(disclosure) is True

    @pytest.mark.asyncio
    async def test_valid_with_ticker_only(self):
        service = QuiverQuantETLService()
        disclosure = {"asset_ticker": "AAPL", "politician_name": "Nancy Pelosi"}
        assert await service.validate_disclosure(disclosure) is True

    @pytest.mark.asyncio
    async def test_rejects_no_asset(self):
        service = QuiverQuantETLService()
        disclosure = {"politician_name": "Nancy Pelosi"}
        assert await service.validate_disclosure(disclosure) is False

    @pytest.mark.asyncio
    async def test_rejects_no_politician(self):
        service = QuiverQuantETLService()
        disclosure = {"asset_name": "Apple Inc."}
        assert await service.validate_disclosure(disclosure) is False
