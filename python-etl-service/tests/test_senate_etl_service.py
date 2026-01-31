"""
Tests for Senate ETL service (app/services/senate_etl.py).

Tests the core ETL functionality for US Senate financial disclosures:
- Senator fetching from XML
- Senator database operations
- Transaction parsing from PDF rows
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
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


# =============================================================================
# upsert_senator_to_db Exception Tests
# =============================================================================

class TestUpsertSenatorExceptionHandling:
    """Tests for exception handling in upsert_senator_to_db."""

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

    def test_handles_bioguide_search_exception(self, mock_supabase, sample_senator):
        """upsert_senator_to_db handles exception during bioguide search."""
        from app.services.senate_etl import upsert_senator_to_db

        table_mock = mock_supabase.table.return_value
        # First call throws exception
        table_mock.select.return_value.eq.return_value.limit.return_value.execute.side_effect = Exception("DB error")
        # Second call (fallback) succeeds
        table_mock.select.return_value.ilike.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "fallback-uuid"}]
        )
        table_mock.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        result = upsert_senator_to_db(mock_supabase, sample_senator)

        assert result == "fallback-uuid"

    def test_returns_none_when_no_bioguide_and_fallback_fails(self, mock_supabase, sample_senator):
        """upsert_senator_to_db returns None when no bioguide_id and fallback fails."""
        from app.services.senate_etl import upsert_senator_to_db

        # Senator without bioguide_id
        senator_no_bioguide = {**sample_senator, "bioguide_id": ""}

        table_mock = mock_supabase.table.return_value
        # All searches return empty
        table_mock.select.return_value.ilike.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        table_mock.select.return_value.ilike.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        table_mock.insert.return_value.execute.return_value = MagicMock(data=[])

        result = upsert_senator_to_db(mock_supabase, senator_no_bioguide)

        assert result is None


class TestUpsertSenatorByNameExceptionHandling:
    """Tests for exception handling in _upsert_senator_by_name."""

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

    def test_handles_exception_returns_none(self, mock_supabase, sample_senator):
        """_upsert_senator_by_name returns None on exception."""
        from app.services.senate_etl import _upsert_senator_by_name

        table_mock = mock_supabase.table.return_value
        table_mock.select.side_effect = Exception("DB error")

        result = _upsert_senator_by_name(mock_supabase, sample_senator)

        assert result is None


# =============================================================================
# parse_datatables_record Tests
# =============================================================================

class TestParseDatatablesRecord:
    """Tests for parse_datatables_record function."""

    @pytest.fixture
    def sample_senator(self):
        """Sample senator data."""
        return {
            "first_name": "John",
            "last_name": "Smith",
            "full_name": "John Smith",
            "politician_id": "senator-uuid",
        }

    def test_parses_valid_record(self, sample_senator):
        """parse_datatables_record parses valid record."""
        from app.services.senate_etl import parse_datatables_record

        record = [
            "John",
            "Smith",
            "Senator",
            "Periodic Transaction Report",
            "01/15/2024",
            '<a href="/search/view/ptr/83de647b-ddf0-49c3-bd56-8b32f23c0e78/">View</a>',
        ]

        result = parse_datatables_record(record, sample_senator)

        assert result is not None
        assert result["politician_name"] == "John Smith"
        assert result["report_type"] == "PTR"
        assert "2024-01-15" in result["filing_date"]
        assert result["doc_id"] == "83de647b-ddf0-49c3-bd56-8b32f23c0e78"

    def test_returns_none_for_short_record(self, sample_senator):
        """parse_datatables_record returns None for short record."""
        from app.services.senate_etl import parse_datatables_record

        record = ["John", "Smith", "Senator"]

        result = parse_datatables_record(record, sample_senator)

        assert result is None

    def test_returns_none_for_non_ptr(self, sample_senator):
        """parse_datatables_record returns None for non-PTR reports."""
        from app.services.senate_etl import parse_datatables_record

        record = [
            "John",
            "Smith",
            "Senator",
            "Annual Financial Disclosure",
            "01/15/2024",
            '<a href="/search/view/annual/abc123/">View</a>',
        ]

        result = parse_datatables_record(record, sample_senator)

        assert result is None

    def test_returns_none_without_href(self, sample_senator):
        """parse_datatables_record returns None without href attribute."""
        from app.services.senate_etl import parse_datatables_record

        record = [
            "John",
            "Smith",
            "Senator",
            "Periodic Transaction Report",
            "01/15/2024",
            "No link here",
        ]

        result = parse_datatables_record(record, sample_senator)

        assert result is None

    def test_handles_full_url(self, sample_senator):
        """parse_datatables_record handles full URL in link."""
        from app.services.senate_etl import parse_datatables_record

        record = [
            "John",
            "Smith",
            "Senator",
            "Periodic Transaction Report",
            "01/15/2024",
            '<a href="https://efdsearch.senate.gov/search/view/ptr/83de647b-ddf0-49c3-bd56-8b32f23c0e78/">View</a>',
        ]

        result = parse_datatables_record(record, sample_senator)

        assert result is not None
        assert "https://efdsearch.senate.gov" in result["source_url"]

    def test_handles_invalid_date(self, sample_senator):
        """parse_datatables_record handles invalid date format."""
        from app.services.senate_etl import parse_datatables_record

        record = [
            "John",
            "Smith",
            "Senator",
            "Periodic Transaction Report",
            "not-a-date",
            '<a href="/search/view/ptr/83de647b-ddf0-49c3-bd56-8b32f23c0e78/">View</a>',
        ]

        result = parse_datatables_record(record, sample_senator)

        assert result is not None
        assert result["filing_date"] is None

    def test_uses_senator_name_as_fallback(self, sample_senator):
        """parse_datatables_record uses senator full_name when record name empty."""
        from app.services.senate_etl import parse_datatables_record

        record = [
            "",
            "",
            "Senator",
            "Periodic Transaction Report",
            "01/15/2024",
            '<a href="/search/view/ptr/83de647b-ddf0-49c3-bd56-8b32f23c0e78/">View</a>',
        ]

        result = parse_datatables_record(record, sample_senator)

        assert result is not None
        assert result["politician_name"] == "John Smith"


# =============================================================================
# parse_ptr_page Tests (BeautifulSoup)
# =============================================================================

class TestParsePtrPage:
    """Tests for parse_ptr_page function (HTTP/BeautifulSoup version)."""

    @pytest.fixture
    def mock_client(self):
        """Create mock httpx client."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_parses_transactions_from_html(self, mock_client):
        """parse_ptr_page parses transactions from HTML table."""
        from app.services.senate_etl import parse_ptr_page

        html = """
        <html>
        <h1>Periodic Transaction Report for 01/15/2024</h1>
        <table class="table-striped">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Transaction Date</th>
                    <th>Owner</th>
                    <th>Ticker</th>
                    <th>Asset Name</th>
                    <th>Asset Type</th>
                    <th>Type</th>
                    <th>Amount</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>1</td>
                    <td>01/10/2024</td>
                    <td>Self</td>
                    <td>AAPL</td>
                    <td>Apple Inc</td>
                    <td>Stock</td>
                    <td>Purchase</td>
                    <td>$1,001 - $15,000</td>
                </tr>
            </tbody>
        </table>
        </html>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_client.get.return_value = mock_response

        transactions = await parse_ptr_page(mock_client, "https://test.url/ptr/123/")

        assert len(transactions) == 1
        assert transactions[0]["asset_name"] == "Apple Inc"
        assert transactions[0]["asset_ticker"] == "AAPL"
        assert transactions[0]["transaction_type"] == "purchase"

    @pytest.mark.asyncio
    async def test_returns_empty_on_http_error(self, mock_client):
        """parse_ptr_page returns empty list on HTTP error."""
        from app.services.senate_etl import parse_ptr_page

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.get.return_value = mock_response

        transactions = await parse_ptr_page(mock_client, "https://test.url/ptr/123/")

        assert transactions == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_table(self, mock_client):
        """parse_ptr_page returns empty list when no table found."""
        from app.services.senate_etl import parse_ptr_page

        html = "<html><body><p>No table here</p></body></html>"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_client.get.return_value = mock_response

        transactions = await parse_ptr_page(mock_client, "https://test.url/ptr/123/")

        assert transactions == []

    @pytest.mark.asyncio
    async def test_handles_exception(self, mock_client):
        """parse_ptr_page handles exception gracefully."""
        from app.services.senate_etl import parse_ptr_page

        mock_client.get.side_effect = Exception("Network error")

        transactions = await parse_ptr_page(mock_client, "https://test.url/ptr/123/")

        assert transactions == []

    @pytest.mark.asyncio
    async def test_parses_sale_transaction(self, mock_client):
        """parse_ptr_page parses sale transactions."""
        from app.services.senate_etl import parse_ptr_page

        html = """
        <html>
        <h1>PTR</h1>
        <table>
            <tbody>
                <tr>
                    <td>1</td>
                    <td>01/10/2024</td>
                    <td>Self</td>
                    <td>MSFT</td>
                    <td>Microsoft Corp</td>
                    <td>Stock</td>
                    <td>Sale (Full)</td>
                    <td>$15,001 - $50,000</td>
                </tr>
            </tbody>
        </table>
        </html>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_client.get.return_value = mock_response

        transactions = await parse_ptr_page(mock_client, "https://test.url/ptr/123/")

        assert len(transactions) == 1
        assert transactions[0]["transaction_type"] == "sale"

    @pytest.mark.asyncio
    async def test_parses_exchange_transaction(self, mock_client):
        """parse_ptr_page parses exchange transactions."""
        from app.services.senate_etl import parse_ptr_page

        html = """
        <html>
        <table>
            <tbody>
                <tr>
                    <td>1</td>
                    <td>01/10/2024</td>
                    <td>Self</td>
                    <td>XYZ</td>
                    <td>XYZ Fund</td>
                    <td>Fund</td>
                    <td>Exchange</td>
                    <td>$1,001 - $15,000</td>
                </tr>
            </tbody>
        </table>
        </html>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_client.get.return_value = mock_response

        transactions = await parse_ptr_page(mock_client, "https://test.url/ptr/123/")

        assert len(transactions) == 1
        assert transactions[0]["transaction_type"] == "exchange"

    @pytest.mark.asyncio
    async def test_skips_placeholder_tickers(self, mock_client):
        """parse_ptr_page handles -- and N/A tickers."""
        from app.services.senate_etl import parse_ptr_page

        html = """
        <html>
        <table>
            <tbody>
                <tr>
                    <td>1</td>
                    <td>01/10/2024</td>
                    <td>Self</td>
                    <td>--</td>
                    <td>Some Asset</td>
                    <td>Other</td>
                    <td>Purchase</td>
                    <td>$1,001 - $15,000</td>
                </tr>
            </tbody>
        </table>
        </html>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_client.get.return_value = mock_response

        transactions = await parse_ptr_page(mock_client, "https://test.url/ptr/123/")

        assert len(transactions) == 1
        assert transactions[0]["asset_ticker"] is None

    @pytest.mark.asyncio
    async def test_extracts_filing_date_from_h1(self, mock_client):
        """parse_ptr_page extracts filing date from h1."""
        from app.services.senate_etl import parse_ptr_page

        html = """
        <html>
        <h1>Periodic Transaction Report for 02/20/2024</h1>
        <table>
            <tbody>
                <tr>
                    <td>1</td>
                    <td></td>
                    <td>Self</td>
                    <td>AAPL</td>
                    <td>Apple</td>
                    <td>Stock</td>
                    <td>Purchase</td>
                    <td>$1,001 - $15,000</td>
                </tr>
            </tbody>
        </table>
        </html>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_client.get.return_value = mock_response

        transactions = await parse_ptr_page(mock_client, "https://test.url/ptr/123/")

        assert len(transactions) == 1
        assert "2024-02-20" in transactions[0]["notification_date"]


# =============================================================================
# download_senate_pdf Tests
# =============================================================================

class TestDownloadSenatePdf:
    """Tests for download_senate_pdf function."""

    @pytest.fixture
    def mock_client(self):
        """Create mock httpx client."""
        return AsyncMock()

    @pytest.fixture
    def mock_rate_limiter(self):
        """Create mock rate limiter."""
        with patch("app.services.senate_etl.rate_limiter") as mock_rl:
            mock_rl.wait = AsyncMock()
            mock_rl.record_success = MagicMock()
            mock_rl.record_error = MagicMock()
            yield mock_rl

    @pytest.mark.asyncio
    async def test_downloads_pdf_successfully(self, mock_client, mock_rate_limiter):
        """download_senate_pdf downloads PDF content."""
        from app.services.senate_etl import download_senate_pdf

        pdf_content = b"%PDF-1.4 ... (pdf content)"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = pdf_content
        mock_client.get.return_value = mock_response

        result = await download_senate_pdf(mock_client, "https://test.url/pdf")

        assert result == pdf_content
        mock_rate_limiter.record_success.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_for_non_pdf(self, mock_client, mock_rate_limiter):
        """download_senate_pdf returns None for non-PDF content."""
        from app.services.senate_etl import download_senate_pdf

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"<html>Not a PDF</html>"
        mock_client.get.return_value = mock_response

        result = await download_senate_pdf(mock_client, "https://test.url/pdf")

        assert result is None

    @pytest.mark.asyncio
    async def test_handles_rate_limit_error(self, mock_client, mock_rate_limiter):
        """download_senate_pdf handles 429 rate limit error."""
        from app.services.senate_etl import download_senate_pdf

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_client.get.return_value = mock_response

        result = await download_senate_pdf(mock_client, "https://test.url/pdf")

        assert result is None
        mock_rate_limiter.record_error.assert_called_once_with(is_rate_limit=True)

    @pytest.mark.asyncio
    async def test_handles_server_errors(self, mock_client, mock_rate_limiter):
        """download_senate_pdf handles 5xx errors."""
        from app.services.senate_etl import download_senate_pdf

        for status_code in [502, 503, 504]:
            mock_rate_limiter.reset_mock()

            mock_response = MagicMock()
            mock_response.status_code = status_code
            mock_client.get.return_value = mock_response

            result = await download_senate_pdf(mock_client, "https://test.url/pdf")

            assert result is None
            mock_rate_limiter.record_error.assert_called_with(is_rate_limit=True)

    @pytest.mark.asyncio
    async def test_handles_other_errors(self, mock_client, mock_rate_limiter):
        """download_senate_pdf handles other HTTP errors."""
        from app.services.senate_etl import download_senate_pdf

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.get.return_value = mock_response

        result = await download_senate_pdf(mock_client, "https://test.url/pdf")

        assert result is None
        mock_rate_limiter.record_error.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_handles_exception(self, mock_client, mock_rate_limiter):
        """download_senate_pdf handles exceptions."""
        from app.services.senate_etl import download_senate_pdf

        mock_client.get.side_effect = Exception("Network error")

        result = await download_senate_pdf(mock_client, "https://test.url/pdf")

        assert result is None
        mock_rate_limiter.record_error.assert_called_once_with()


# =============================================================================
# process_senate_disclosure Tests
# =============================================================================

class TestProcessSenateDisclosure:
    """Tests for process_senate_disclosure function."""

    @pytest.fixture
    def mock_client(self):
        """Create mock httpx client."""
        return AsyncMock()

    @pytest.fixture
    def mock_supabase(self):
        """Create mock Supabase client."""
        return MagicMock()

    @pytest.fixture
    def sample_disclosure(self):
        """Sample disclosure data."""
        return {
            "politician_name": "John Smith",
            "politician_id": "senator-uuid",
            "source_url": "https://efdsearch.senate.gov/search/view/ptr/abc123/",
            "filing_date": "2024-01-15",
        }

    @pytest.mark.asyncio
    async def test_returns_zero_for_no_source_url(self, mock_client, mock_supabase):
        """process_senate_disclosure returns 0 for disclosure without source_url."""
        from app.services.senate_etl import process_senate_disclosure

        disclosure = {"politician_name": "John Smith"}

        with patch("app.services.senate_etl.rate_limiter"):
            result = await process_senate_disclosure(mock_client, mock_supabase, disclosure)

        assert result == 0

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_transactions(self, mock_client, mock_supabase, sample_disclosure):
        """process_senate_disclosure returns 0 when no transactions found."""
        from app.services.senate_etl import process_senate_disclosure

        with patch("app.services.senate_etl.rate_limiter") as mock_rl:
            mock_rl.wait = AsyncMock()
            mock_rl.record_success = MagicMock()

            with patch("app.services.senate_etl.parse_ptr_page", return_value=[]):
                result = await process_senate_disclosure(mock_client, mock_supabase, sample_disclosure)

        assert result == 0

    @pytest.mark.asyncio
    async def test_uploads_transactions(self, mock_client, mock_supabase, sample_disclosure):
        """process_senate_disclosure uploads transactions."""
        from app.services.senate_etl import process_senate_disclosure

        transactions = [
            {"asset_name": "Apple", "transaction_type": "purchase"},
            {"asset_name": "Microsoft", "transaction_type": "sale"},
        ]

        with patch("app.services.senate_etl.rate_limiter") as mock_rl:
            mock_rl.wait = AsyncMock()
            mock_rl.record_success = MagicMock()

            with patch("app.services.senate_etl.parse_ptr_page", return_value=transactions):
                with patch("app.services.senate_etl.upload_transaction_to_supabase", return_value=True) as mock_upload:
                    result = await process_senate_disclosure(mock_client, mock_supabase, sample_disclosure)

        assert result == 2
        assert mock_upload.call_count == 2

    @pytest.mark.asyncio
    async def test_finds_politician_when_not_in_disclosure(self, mock_client, mock_supabase):
        """process_senate_disclosure finds politician when not in disclosure."""
        from app.services.senate_etl import process_senate_disclosure

        disclosure = {
            "politician_name": "John Smith",
            "source_url": "https://test.url/ptr/123/",
        }

        transactions = [{"asset_name": "Apple", "transaction_type": "purchase"}]

        with patch("app.services.senate_etl.rate_limiter") as mock_rl:
            mock_rl.wait = AsyncMock()
            mock_rl.record_success = MagicMock()

            with patch("app.services.senate_etl.parse_ptr_page", return_value=transactions):
                with patch("app.services.senate_etl.find_or_create_politician", return_value="found-uuid") as mock_find:
                    with patch("app.services.senate_etl.upload_transaction_to_supabase", return_value=True):
                        result = await process_senate_disclosure(mock_client, mock_supabase, disclosure)

        mock_find.assert_called_once_with(mock_supabase, name="John Smith", chamber="senate")
        assert result == 1

    @pytest.mark.asyncio
    async def test_returns_zero_when_politician_not_found(self, mock_client, mock_supabase):
        """process_senate_disclosure returns 0 when politician not found."""
        from app.services.senate_etl import process_senate_disclosure

        disclosure = {
            "politician_name": "Unknown Person",
            "source_url": "https://test.url/ptr/123/",
        }

        transactions = [{"asset_name": "Apple", "transaction_type": "purchase"}]

        with patch("app.services.senate_etl.rate_limiter") as mock_rl:
            mock_rl.wait = AsyncMock()
            mock_rl.record_success = MagicMock()

            with patch("app.services.senate_etl.parse_ptr_page", return_value=transactions):
                with patch("app.services.senate_etl.find_or_create_politician", return_value=None):
                    result = await process_senate_disclosure(mock_client, mock_supabase, disclosure)

        assert result == 0


# =============================================================================
# run_senate_etl Tests
# =============================================================================

class TestRunSenateEtl:
    """Tests for run_senate_etl main function."""

    @pytest.fixture
    def mock_job_status(self):
        """Create mock job status."""
        from app.services.senate_etl import JOB_STATUS
        job_id = "test-job-123"
        JOB_STATUS[job_id] = {
            "status": "pending",
            "message": "",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        return job_id

    @pytest.mark.asyncio
    async def test_fails_when_senators_fetch_fails(self, mock_job_status):
        """run_senate_etl fails when senator fetch fails."""
        from app.services.senate_etl import run_senate_etl, JOB_STATUS

        with patch("app.services.senate_etl.get_supabase", return_value=MagicMock()):
            with patch("app.services.senate_etl.fetch_senators_from_xml", return_value=[]):
                await run_senate_etl(mock_job_status, lookback_days=30)

        assert JOB_STATUS[mock_job_status]["status"] == "error"
        assert "Failed to fetch senators" in JOB_STATUS[mock_job_status]["message"]

    @pytest.mark.asyncio
    async def test_handles_main_exception(self, mock_job_status):
        """run_senate_etl handles exception and logs failure."""
        from app.services.senate_etl import run_senate_etl, JOB_STATUS

        with patch("app.services.senate_etl.get_supabase", side_effect=Exception("DB connection failed")):
            with pytest.raises(Exception, match="DB connection failed"):
                await run_senate_etl(mock_job_status, lookback_days=30)

        assert JOB_STATUS[mock_job_status]["status"] == "error"
        assert "DB connection failed" in JOB_STATUS[mock_job_status]["message"]

    @pytest.mark.asyncio
    async def test_processes_senators_and_disclosures(self, mock_job_status):
        """run_senate_etl processes senators and disclosures."""
        from app.services.senate_etl import run_senate_etl, JOB_STATUS

        senators = [
            {"first_name": "John", "last_name": "Smith", "full_name": "John Smith", "party": "D", "state": "NY", "bioguide_id": "S123"},
        ]

        disclosures = [
            {"politician_name": "John Smith", "source_url": "https://test.url/ptr/123/", "is_paper": False},
        ]

        with patch("app.services.senate_etl.get_supabase", return_value=MagicMock()):
            with patch("app.services.senate_etl.fetch_senators_from_xml", return_value=senators):
                with patch("app.services.senate_etl.upsert_senator_to_db", return_value="senator-uuid"):
                    with patch("app.services.senate_etl.fetch_senate_ptr_list_playwright", return_value=disclosures):
                        with patch("app.services.senate_etl.process_disclosures_playwright", return_value=(5, 0)):
                            with patch("app.services.senate_etl.log_job_execution"):
                                await run_senate_etl(mock_job_status, lookback_days=30)

        assert JOB_STATUS[mock_job_status]["status"] == "completed"
        assert "1 senators" in JOB_STATUS[mock_job_status]["message"]
        assert "5 transactions" in JOB_STATUS[mock_job_status]["message"]

    @pytest.mark.asyncio
    async def test_filters_paper_disclosures(self, mock_job_status):
        """run_senate_etl filters out paper disclosures."""
        from app.services.senate_etl import run_senate_etl, JOB_STATUS

        senators = [{"first_name": "John", "last_name": "Smith", "full_name": "John Smith", "party": "D", "state": "NY", "bioguide_id": "S123"}]

        disclosures = [
            {"politician_name": "John Smith", "source_url": "https://test.url/ptr/123/", "is_paper": False},
            {"politician_name": "John Smith", "source_url": "https://test.url/paper/456/", "is_paper": True},
            {"politician_name": "John Smith", "source_url": "https://test.url/ptr/789/", "is_paper": False},
        ]

        with patch("app.services.senate_etl.get_supabase", return_value=MagicMock()):
            with patch("app.services.senate_etl.fetch_senators_from_xml", return_value=senators):
                with patch("app.services.senate_etl.upsert_senator_to_db", return_value="senator-uuid"):
                    with patch("app.services.senate_etl.fetch_senate_ptr_list_playwright", return_value=disclosures):
                        with patch("app.services.senate_etl.process_disclosures_playwright", return_value=(3, 0)) as mock_process:
                            with patch("app.services.senate_etl.log_job_execution"):
                                await run_senate_etl(mock_job_status, lookback_days=30)

        # Only electronic disclosures should be processed
        electronic_disclosures = mock_process.call_args[0][0]
        assert len(electronic_disclosures) == 2
        assert all(not d.get("is_paper") for d in electronic_disclosures)


# =============================================================================
# Constants Tests
# =============================================================================

class TestSenateETLConstants:
    """Tests for module constants and imports."""

    def test_constants_defined(self):
        """Verify all constants are defined."""
        from app.services.senate_etl import (
            SENATE_BASE_URL,
            SENATE_SEARCH_URL,
            SENATE_PTR_URL,
            SENATORS_XML_URL,
            USER_AGENT,
        )

        assert SENATE_BASE_URL == "https://efdsearch.senate.gov"
        assert "search" in SENATE_SEARCH_URL
        assert "ptr" in SENATE_PTR_URL
        assert "senate.gov" in SENATORS_XML_URL
        assert "Mozilla" in USER_AGENT

    def test_parser_imports_available(self):
        """Verify parser imports are available."""
        from app.services.senate_etl import (
            extract_ticker_from_text,
            sanitize_string,
            parse_asset_type,
            parse_value_range,
            clean_asset_name,
            is_header_row,
        )

        # Just verify they're callable
        assert callable(extract_ticker_from_text)
        assert callable(sanitize_string)
        assert callable(parse_asset_type)
        assert callable(parse_value_range)
        assert callable(clean_asset_name)
        assert callable(is_header_row)
