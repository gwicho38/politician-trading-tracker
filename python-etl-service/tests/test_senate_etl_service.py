"""
Tests for Senate ETL service (app/services/senate_etl.py).

Tests the core ETL functionality for US Senate financial disclosures:
- Senator fetching from XML
- Senator database operations
- Transaction parsing from PDF rows
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any


# =============================================================================
# fetch_senators_from_xml Tests
# =============================================================================

class TestFetchSenatorsFromXml:
    """Tests for fetch_senators_from_xml function."""

    @pytest.mark.asyncio
    async def test_parses_senator_xml_correctly(self):
        """fetch_senators_from_xml parses XML response correctly."""
        from app.services.senate_etl import fetch_senators_from_xml

        mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
<contact_information>
    <member>
        <first_name>John</first_name>
        <last_name>Smith</last_name>
        <party>D</party>
        <state>NY</state>
        <bioguide_id>S000123</bioguide_id>
    </member>
    <member>
        <first_name>Jane</first_name>
        <last_name>Doe</last_name>
        <party>R</party>
        <state>CA</state>
        <bioguide_id>D000456</bioguide_id>
    </member>
</contact_information>"""

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_xml

        with patch("app.services.senate_etl.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            senators = await fetch_senators_from_xml()

            assert len(senators) == 2
            assert senators[0]["first_name"] == "John"
            assert senators[0]["last_name"] == "Smith"
            assert senators[0]["party"] == "D"
            assert senators[0]["state"] == "NY"
            assert senators[0]["bioguide_id"] == "S000123"
            assert senators[0]["full_name"] == "John Smith"

    @pytest.mark.asyncio
    async def test_handles_http_error(self):
        """fetch_senators_from_xml returns empty list on HTTP error."""
        from app.services.senate_etl import fetch_senators_from_xml

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("app.services.senate_etl.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            senators = await fetch_senators_from_xml()

            assert senators == []

    @pytest.mark.asyncio
    async def test_handles_exception(self):
        """fetch_senators_from_xml returns empty list on exception."""
        from app.services.senate_etl import fetch_senators_from_xml

        with patch("app.services.senate_etl.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Network error")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            senators = await fetch_senators_from_xml()

            assert senators == []

    @pytest.mark.asyncio
    async def test_skips_members_without_names(self):
        """fetch_senators_from_xml skips members missing name fields."""
        from app.services.senate_etl import fetch_senators_from_xml

        mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
<contact_information>
    <member>
        <first_name></first_name>
        <last_name>Smith</last_name>
        <party>D</party>
    </member>
    <member>
        <first_name>John</first_name>
        <last_name></last_name>
        <party>R</party>
    </member>
    <member>
        <first_name>Jane</first_name>
        <last_name>Doe</last_name>
        <party>D</party>
    </member>
</contact_information>"""

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_xml

        with patch("app.services.senate_etl.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            senators = await fetch_senators_from_xml()

            # Only Jane Doe should be included (both names present)
            assert len(senators) == 1
            assert senators[0]["first_name"] == "Jane"


# =============================================================================
# upsert_senator_to_db Tests
# =============================================================================

class TestUpsertSenatorToDb:
    """Tests for upsert_senator_to_db function."""

    @pytest.fixture
    def mock_supabase(self):
        """Create mock Supabase client."""
        client = MagicMock()
        table_mock = MagicMock()
        client.table.return_value = table_mock
        return client

    @pytest.fixture
    def sample_senator(self):
        """Sample senator data."""
        return {
            "first_name": "John",
            "last_name": "Smith",
            "full_name": "John Smith",
            "party": "D",
            "state": "NY",
            "bioguide_id": "S000123",
        }

    def test_finds_existing_by_bioguide_id(self, mock_supabase, sample_senator):
        """upsert_senator_to_db finds existing senator by bioguide_id."""
        from app.services.senate_etl import upsert_senator_to_db

        table_mock = mock_supabase.table.return_value
        table_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "existing-uuid"}]
        )
        table_mock.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        result = upsert_senator_to_db(mock_supabase, sample_senator)

        assert result == "existing-uuid"

    def test_updates_existing_senator(self, mock_supabase, sample_senator):
        """upsert_senator_to_db updates existing senator data."""
        from app.services.senate_etl import upsert_senator_to_db

        table_mock = mock_supabase.table.return_value
        table_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "existing-uuid"}]
        )
        table_mock.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        upsert_senator_to_db(mock_supabase, sample_senator)

        # Verify update was called
        table_mock.update.assert_called_once()
        update_call = table_mock.update.call_args
        update_data = update_call[0][0]
        assert update_data["first_name"] == "John"
        assert update_data["role"] == "Senator"

    def test_falls_back_to_name_search(self, mock_supabase, sample_senator):
        """upsert_senator_to_db falls back to name search if no bioguide match."""
        from app.services.senate_etl import upsert_senator_to_db

        table_mock = mock_supabase.table.return_value

        # First search by bioguide returns nothing
        table_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        # Second search by name returns a match
        table_mock.select.return_value.ilike.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "name-match-uuid"}]
        )
        table_mock.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        result = upsert_senator_to_db(mock_supabase, sample_senator)

        assert result == "name-match-uuid"


# =============================================================================
# _upsert_senator_by_name Tests
# =============================================================================

class TestUpsertSenatorByName:
    """Tests for _upsert_senator_by_name function."""

    @pytest.fixture
    def mock_supabase(self):
        """Create mock Supabase client."""
        client = MagicMock()
        table_mock = MagicMock()
        client.table.return_value = table_mock
        return client

    @pytest.fixture
    def sample_senator(self):
        """Sample senator data."""
        return {
            "first_name": "John",
            "last_name": "Smith",
            "full_name": "John Smith",
            "party": "D",
            "state": "NY",
            "bioguide_id": "S000123",
        }

    def test_finds_by_full_name(self, mock_supabase, sample_senator):
        """_upsert_senator_by_name finds by full_name column."""
        from app.services.senate_etl import _upsert_senator_by_name

        table_mock = mock_supabase.table.return_value
        table_mock.select.return_value.ilike.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "fullname-match-uuid"}]
        )
        table_mock.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        result = _upsert_senator_by_name(mock_supabase, sample_senator)

        assert result == "fullname-match-uuid"

    def test_finds_by_last_name_column(self, mock_supabase, sample_senator):
        """_upsert_senator_by_name falls back to last_name column."""
        from app.services.senate_etl import _upsert_senator_by_name

        table_mock = mock_supabase.table.return_value

        # First search by full_name returns nothing
        first_response = MagicMock(data=[])
        # Second search by last_name returns match
        second_response = MagicMock(data=[{"id": "lastname-match-uuid"}])

        table_mock.select.return_value.ilike.return_value.eq.return_value.limit.return_value.execute.side_effect = [
            first_response
        ]
        table_mock.select.return_value.ilike.return_value.limit.return_value.execute.return_value = second_response
        table_mock.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        result = _upsert_senator_by_name(mock_supabase, sample_senator)

        assert result == "lastname-match-uuid"

    def test_creates_new_senator(self, mock_supabase, sample_senator):
        """_upsert_senator_by_name creates new senator if not found."""
        from app.services.senate_etl import _upsert_senator_by_name

        table_mock = mock_supabase.table.return_value

        # No matches found
        table_mock.select.return_value.ilike.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        table_mock.select.return_value.ilike.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        # Insert returns new ID
        table_mock.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "new-senator-uuid"}]
        )

        result = _upsert_senator_by_name(mock_supabase, sample_senator)

        assert result == "new-senator-uuid"
        table_mock.insert.assert_called_once()


# =============================================================================
# parse_transaction_from_row Tests
# =============================================================================

class TestSenateParseTransactionFromRow:
    """Tests for Senate parse_transaction_from_row function."""

    @pytest.fixture
    def sample_disclosure(self):
        """Sample disclosure metadata."""
        return {
            "politician_name": "John Smith",
            "first_name": "John",
            "last_name": "Smith",
            "filing_date": "2024-01-25",
        }

    def test_parses_purchase_transaction(self, sample_disclosure):
        """parse_transaction_from_row parses purchase transaction."""
        from app.services.senate_etl import parse_transaction_from_row

        row = ["Apple Inc. (AAPL)", "Stock", "Purchase", "$15,001 - $50,000", "01/15/2024"]

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is not None
        assert "Apple" in result["asset_name"]
        assert result["transaction_type"] == "purchase"

    def test_parses_sale_transaction(self, sample_disclosure):
        """parse_transaction_from_row parses sale transaction."""
        from app.services.senate_etl import parse_transaction_from_row

        row = ["Microsoft Corp (MSFT)", "Stock", "Sale", "$50,001 - $100,000", "01/20/2024"]

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is not None
        assert result["transaction_type"] == "sale"

    def test_extracts_ticker(self, sample_disclosure):
        """parse_transaction_from_row extracts ticker from asset name."""
        from app.services.senate_etl import parse_transaction_from_row

        row = ["NVIDIA Corporation (NVDA)", "Stock", "Purchase", "$1,001 - $15,000"]

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is not None
        assert result["asset_ticker"] == "NVDA"

    def test_extracts_value_range(self, sample_disclosure):
        """parse_transaction_from_row extracts value range."""
        from app.services.senate_etl import parse_transaction_from_row

        row = ["Apple Inc.", "Stock", "Sale", "$15,001 - $50,000"]

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is not None
        assert result["value_low"] == 15001
        assert result["value_high"] == 50000

    def test_returns_none_for_empty_row(self, sample_disclosure):
        """parse_transaction_from_row returns None for empty row."""
        from app.services.senate_etl import parse_transaction_from_row

        row = []

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is None

    def test_returns_none_for_short_row(self, sample_disclosure):
        """parse_transaction_from_row returns None for row with < 2 cells."""
        from app.services.senate_etl import parse_transaction_from_row

        row = ["Only one cell"]

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is None

    def test_returns_none_for_header_row(self, sample_disclosure):
        """parse_transaction_from_row returns None for header row."""
        from app.services.senate_etl import parse_transaction_from_row

        row = ["Asset", "Type", "Transaction", "Amount", "Date"]

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is None

    def test_skips_metadata_cells(self, sample_disclosure):
        """parse_transaction_from_row skips metadata cells and finds asset."""
        from app.services.senate_etl import parse_transaction_from_row

        # Put the asset name in a later cell so it gets picked up after skipping metadata
        row = ["", "Apple Inc. (AAPL)", "Purchase", "$1,001 - $15,000"]

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is not None
        assert "Apple" in result["asset_name"]
        assert result["transaction_type"] == "purchase"

    def test_extracts_transaction_date(self, sample_disclosure):
        """parse_transaction_from_row extracts transaction date."""
        from app.services.senate_etl import parse_transaction_from_row

        row = ["Apple Inc.", "Stock", "Purchase", "$1,001 - $15,000", "01/15/2024"]

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is not None
        assert result["transaction_date"] is not None
        assert "2024-01-15" in result["transaction_date"]

    def test_uses_disclosure_date_as_notification(self, sample_disclosure):
        """parse_transaction_from_row uses disclosure filing_date as notification_date."""
        from app.services.senate_etl import parse_transaction_from_row

        row = ["Apple Inc.", "Stock", "Purchase", "$1,001 - $15,000"]

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is not None
        assert result["notification_date"] == "2024-01-25"

    def test_handles_p_s_codes(self, sample_disclosure):
        """parse_transaction_from_row handles P/S single-letter codes."""
        from app.services.senate_etl import parse_transaction_from_row

        row = ["Apple Inc.", "Stock", "P", "$1,001 - $15,000"]

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is not None
        assert result["transaction_type"] == "purchase"

    def test_handles_sale_code(self, sample_disclosure):
        """parse_transaction_from_row handles S sale code."""
        from app.services.senate_etl import parse_transaction_from_row

        row = ["Microsoft Corp", "Stock", "S", "$15,001 - $50,000"]

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is not None
        assert result["transaction_type"] == "sale"

    def test_returns_none_without_transaction_or_value(self, sample_disclosure):
        """parse_transaction_from_row returns None without transaction type or value."""
        from app.services.senate_etl import parse_transaction_from_row

        # Row without transaction type or $ value
        row = ["Apple Inc.", "Stock", "N/A", "N/A"]

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is None

    def test_defaults_to_unknown_transaction_type(self, sample_disclosure):
        """parse_transaction_from_row defaults to 'unknown' when type not found but has value."""
        from app.services.senate_etl import parse_transaction_from_row

        row = ["Apple Inc.", "Stock", "", "$1,001 - $15,000"]

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is not None
        assert result["transaction_type"] == "unknown"


# =============================================================================
# Integration Tests
# =============================================================================

class TestSenateETLIntegration:
    """Integration-style tests for Senate ETL."""

    def test_senate_xml_constants_defined(self):
        """Verify Senate XML URL constants are defined."""
        from app.services.senate_etl import SENATORS_XML_URL, SENATE_BASE_URL

        assert "senate.gov" in SENATORS_XML_URL
        assert "efdsearch.senate.gov" in SENATE_BASE_URL

    def test_rate_limiter_imported_from_house_etl(self):
        """Verify rate_limiter is imported from house_etl."""
        from app.services.senate_etl import rate_limiter
        from app.services.house_etl import RateLimiter

        assert isinstance(rate_limiter, RateLimiter)

    def test_job_status_shared_with_house_etl(self):
        """Verify JOB_STATUS is shared with house_etl."""
        from app.services.senate_etl import JOB_STATUS
        from app.services.house_etl import JOB_STATUS as HOUSE_JOB_STATUS

        assert JOB_STATUS is HOUSE_JOB_STATUS
