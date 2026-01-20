"""
Tests for House ETL service (app/services/house_etl.py).

Tests the core ETL functionality for US House financial disclosures:
- RateLimiter class
- Date validation and correction
- Date extraction from PDF rows
- Metadata row detection
- Transaction parsing from PDF rows
- HouseDisclosureScraper class
- Main ETL function
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any


# =============================================================================
# RateLimiter Tests
# =============================================================================

class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_initial_state(self):
        """RateLimiter starts with default values."""
        from app.services.house_etl import RateLimiter

        limiter = RateLimiter()

        assert limiter.current_delay == 1.0
        assert limiter.consecutive_errors == 0
        assert limiter.total_requests == 0
        assert limiter.total_errors == 0

    @pytest.mark.asyncio
    async def test_wait_delays_execution(self):
        """RateLimiter.wait() delays for current_delay seconds."""
        from app.services.house_etl import RateLimiter
        import asyncio

        limiter = RateLimiter()
        limiter.current_delay = 0.01  # Very short for testing

        start = asyncio.get_event_loop().time()
        await limiter.wait()
        elapsed = asyncio.get_event_loop().time() - start

        assert elapsed >= 0.01

    def test_record_success_increments_requests(self):
        """record_success increments total_requests."""
        from app.services.house_etl import RateLimiter

        limiter = RateLimiter()
        limiter.record_success()

        assert limiter.total_requests == 1
        assert limiter.consecutive_errors == 0

    def test_record_success_reduces_delay(self):
        """record_success reduces delay if above base."""
        from app.services.house_etl import RateLimiter

        limiter = RateLimiter()
        limiter.current_delay = 4.0  # Above base

        limiter.record_success()

        assert limiter.current_delay == 2.0  # Reduced by half

    def test_record_success_does_not_go_below_base(self):
        """record_success does not reduce delay below base."""
        from app.services.house_etl import RateLimiter

        limiter = RateLimiter()
        limiter.current_delay = 1.0  # At base

        limiter.record_success()

        assert limiter.current_delay == 1.0  # Still at base

    def test_record_error_increments_counters(self):
        """record_error increments error counters."""
        from app.services.house_etl import RateLimiter

        limiter = RateLimiter()
        limiter.record_error()

        assert limiter.total_requests == 1
        assert limiter.total_errors == 1
        assert limiter.consecutive_errors == 1

    def test_record_error_increases_delay(self):
        """record_error increases delay."""
        from app.services.house_etl import RateLimiter

        limiter = RateLimiter()
        initial_delay = limiter.current_delay

        limiter.record_error()

        assert limiter.current_delay > initial_delay

    def test_record_error_rate_limit_aggressive_backoff(self):
        """record_error with rate_limit=True backs off aggressively."""
        from app.services.house_etl import RateLimiter

        limiter = RateLimiter()
        initial_delay = limiter.current_delay

        limiter.record_error(is_rate_limit=True)

        # Should back off more aggressively for rate limits
        assert limiter.current_delay >= initial_delay * 4

    def test_record_error_caps_at_max_delay(self):
        """record_error caps delay at max."""
        from app.services.house_etl import RateLimiter, REQUEST_DELAY_MAX

        limiter = RateLimiter()
        limiter.current_delay = REQUEST_DELAY_MAX - 1

        limiter.record_error(is_rate_limit=True)

        assert limiter.current_delay == REQUEST_DELAY_MAX

    def test_get_stats_returns_all_fields(self):
        """get_stats returns complete statistics."""
        from app.services.house_etl import RateLimiter

        limiter = RateLimiter()
        limiter.record_success()
        limiter.record_success()
        limiter.record_error()

        stats = limiter.get_stats()

        assert stats["total_requests"] == 3
        assert stats["total_errors"] == 1
        assert stats["error_rate"] == 1/3
        assert "current_delay" in stats
        assert stats["consecutive_errors"] == 1


# =============================================================================
# Date Validation Tests
# =============================================================================

class TestValidateAndCorrectYear:
    """Tests for _validate_and_correct_year function."""

    def test_valid_dates_unchanged(self):
        """Valid dates are returned unchanged."""
        from app.services.house_etl import _validate_and_correct_year

        tx_date = datetime(2024, 1, 15)
        notif_date = datetime(2024, 1, 25)

        result_tx, result_notif = _validate_and_correct_year(tx_date, notif_date)

        assert result_tx == tx_date
        assert result_notif == notif_date

    def test_corrects_invalid_transaction_year(self):
        """Corrects invalid transaction year using notification year."""
        from app.services.house_etl import _validate_and_correct_year

        tx_date = datetime(3024, 1, 15)  # Invalid year (typo)
        notif_date = datetime(2024, 1, 25)  # Valid

        result_tx, result_notif = _validate_and_correct_year(tx_date, notif_date)

        assert result_tx.year == 2024
        assert result_notif == notif_date

    def test_corrects_invalid_notification_year(self):
        """Corrects invalid notification year using transaction year."""
        from app.services.house_etl import _validate_and_correct_year

        tx_date = datetime(2024, 1, 15)  # Valid
        notif_date = datetime(2220, 1, 25)  # Invalid year (typo)

        result_tx, result_notif = _validate_and_correct_year(tx_date, notif_date)

        assert result_tx == tx_date
        assert result_notif.year == 2024

    def test_handles_transaction_after_notification(self):
        """When corrected tx would be after notif, uses previous year."""
        from app.services.house_etl import _validate_and_correct_year

        tx_date = datetime(3031, 12, 20)  # Invalid, December
        notif_date = datetime(2024, 1, 5)  # Valid, January

        result_tx, result_notif = _validate_and_correct_year(tx_date, notif_date)

        # Transaction in December should be previous year
        assert result_tx.year == 2023

    def test_both_invalid_returned_as_is(self):
        """Both invalid dates are returned as-is."""
        from app.services.house_etl import _validate_and_correct_year

        tx_date = datetime(3024, 1, 15)  # Invalid
        notif_date = datetime(2220, 1, 25)  # Invalid

        result_tx, result_notif = _validate_and_correct_year(tx_date, notif_date)

        # Both invalid - returned unchanged
        assert result_tx == tx_date
        assert result_notif == notif_date


# =============================================================================
# Date Extraction Tests
# =============================================================================

class TestExtractDatesFromRow:
    """Tests for extract_dates_from_row function."""

    def test_extracts_purchase_dates(self):
        """Extracts dates from purchase transaction row."""
        from app.services.house_etl import extract_dates_from_row

        row = ["P 01/15/2024 01/25/2024 $1,001 - $15,000"]

        tx_date, notif_date = extract_dates_from_row(row)

        assert tx_date is not None
        assert notif_date is not None
        assert "2024-01-15" in tx_date
        assert "2024-01-25" in notif_date

    def test_extracts_sale_dates(self):
        """Extracts dates from sale transaction row."""
        from app.services.house_etl import extract_dates_from_row

        row = ["S 12/01/2024 12/05/2024 $15,001 - $50,000"]

        tx_date, notif_date = extract_dates_from_row(row)

        assert tx_date is not None
        assert notif_date is not None
        assert "2024-12-01" in tx_date
        assert "2024-12-05" in notif_date

    def test_extracts_partial_sale_dates(self):
        """Extracts dates from partial sale row."""
        from app.services.house_etl import extract_dates_from_row

        row = ["S (partial) 11/19/2025 11/26/2025 $1,001 - $15,000"]

        tx_date, notif_date = extract_dates_from_row(row)

        assert tx_date is not None
        assert notif_date is not None

    def test_returns_none_for_no_dates(self):
        """Returns (None, None) when no dates found."""
        from app.services.house_etl import extract_dates_from_row

        row = ["Apple Inc.", "AAPL", "stock"]

        tx_date, notif_date = extract_dates_from_row(row)

        assert tx_date is None
        assert notif_date is None

    def test_handles_null_bytes(self):
        """Handles null bytes in row text."""
        from app.services.house_etl import extract_dates_from_row

        row = ["P\x00 01/15/2024\x00 01/25/2024"]

        tx_date, notif_date = extract_dates_from_row(row)

        assert tx_date is not None
        assert notif_date is not None


# =============================================================================
# Metadata Row Detection Tests
# =============================================================================

class TestIsMetadataRow:
    """Tests for is_metadata_row function."""

    def test_detects_filer_status(self):
        """Detects F S: filer status pattern."""
        from app.services.house_etl import is_metadata_row

        assert is_metadata_row("F S: Joint") is True

    def test_detects_sub_owner(self):
        """Detects S O: sub owner pattern."""
        from app.services.house_etl import is_metadata_row

        assert is_metadata_row("S O: Spouse") is True

    def test_detects_owner(self):
        """Detects Owner: pattern."""
        from app.services.house_etl import is_metadata_row

        assert is_metadata_row("Owner: Joint") is True

    def test_detects_filing_id(self):
        """Detects Filing ID pattern."""
        from app.services.house_etl import is_metadata_row

        assert is_metadata_row("Filing ID: 12345") is True

    def test_detects_cap_gains(self):
        """Detects Capital Gains header."""
        from app.services.house_etl import is_metadata_row

        assert is_metadata_row("Cap. Gains > $200?") is True

    def test_returns_false_for_asset_name(self):
        """Returns False for normal asset names."""
        from app.services.house_etl import is_metadata_row

        assert is_metadata_row("Apple Inc. (AAPL)") is False
        assert is_metadata_row("Microsoft Corporation") is False

    def test_handles_null_bytes(self):
        """Handles null bytes in text."""
        from app.services.house_etl import is_metadata_row

        assert is_metadata_row("F\x00 S\x00: Joint") is True


# =============================================================================
# Transaction Parsing Tests
# =============================================================================

class TestParseTransactionFromRow:
    """Tests for parse_transaction_from_row function."""

    @pytest.fixture
    def sample_disclosure(self):
        """Sample disclosure metadata."""
        return {
            "politician_name": "Jane Smith",
            "first_name": "Jane",
            "last_name": "Smith",
            "doc_id": "20012345",
            "filing_type": "P",
            "filing_date": "2024-01-25",
        }

    def test_parses_purchase_transaction(self, sample_disclosure):
        """Parses purchase transaction from row."""
        from app.services.house_etl import parse_transaction_from_row

        row = ["Apple Inc. (AAPL)", "ST", "P 01/15/2024 01/25/2024", "$1,001 - $15,000"]

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is not None
        assert result["asset_name"] == "Apple Inc. (AAPL)"
        assert result["transaction_type"] == "purchase"

    def test_parses_sale_transaction(self, sample_disclosure):
        """Parses sale transaction from row."""
        from app.services.house_etl import parse_transaction_from_row

        row = ["Microsoft Corp (MSFT)", "ST", "S 12/01/2024 12/05/2024", "$15,001 - $50,000"]

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is not None
        assert result["transaction_type"] == "sale"

    def test_extracts_ticker_from_asset_name(self, sample_disclosure):
        """Extracts ticker from asset name."""
        from app.services.house_etl import parse_transaction_from_row

        row = ["NVIDIA Corporation (NVDA)", "ST", "P", "$1,001 - $15,000"]

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is not None
        assert result["asset_ticker"] == "NVDA"

    def test_extracts_value_range(self, sample_disclosure):
        """Extracts value range from row."""
        from app.services.house_etl import parse_transaction_from_row

        row = ["Apple Inc.", "ST", "P", "$15,001 - $50,000"]

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is not None
        assert result["value_low"] == 15001
        assert result["value_high"] == 50000

    def test_returns_none_for_empty_row(self, sample_disclosure):
        """Returns None for empty row."""
        from app.services.house_etl import parse_transaction_from_row

        row = []

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is None

    def test_returns_none_for_header_row(self, sample_disclosure):
        """Returns None for header row."""
        from app.services.house_etl import parse_transaction_from_row

        row = ["Asset", "Type", "Transaction", "Amount", "Date"]

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is None

    def test_returns_none_for_metadata_row(self, sample_disclosure):
        """Returns None for metadata row."""
        from app.services.house_etl import parse_transaction_from_row

        row = ["F S:", "Joint", ""]

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is None

    def test_includes_disclosure_fields(self, sample_disclosure):
        """Includes disclosure metadata in result."""
        from app.services.house_etl import parse_transaction_from_row

        row = ["Apple Inc.", "ST", "P", "$1,001 - $15,000"]

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is not None
        assert result["politician_name"] == "Jane Smith"
        assert result["doc_id"] == "20012345"
        assert result["filing_type"] == "P"
        assert result["source"] == "us_house"

    def test_includes_raw_row(self, sample_disclosure):
        """Includes raw row in result."""
        from app.services.house_etl import parse_transaction_from_row

        row = ["Apple Inc.", "ST", "P", "$1,001 - $15,000"]

        result = parse_transaction_from_row(row, sample_disclosure)

        assert result is not None
        assert "raw_row" in result
        assert len(result["raw_row"]) == 4


# =============================================================================
# HouseDisclosureScraper Tests
# =============================================================================

class TestHouseDisclosureScraper:
    """Tests for HouseDisclosureScraper class."""

    def test_get_zip_url(self):
        """get_zip_url returns correct URL format."""
        from app.services.house_etl import HouseDisclosureScraper

        url = HouseDisclosureScraper.get_zip_url(2024)

        assert "2024FD.ZIP" in url
        assert "disclosures-clerk.house.gov" in url

    def test_get_pdf_url_standard(self):
        """get_pdf_url returns correct URL for standard filing."""
        from app.services.house_etl import HouseDisclosureScraper

        url = HouseDisclosureScraper.get_pdf_url(2024, "12345678", filing_type="A")

        assert "financial-pdfs" in url
        assert "12345678.pdf" in url

    def test_get_pdf_url_ptr(self):
        """get_pdf_url returns PTR URL for P filing type."""
        from app.services.house_etl import HouseDisclosureScraper

        url = HouseDisclosureScraper.get_pdf_url(2024, "12345678", filing_type="P")

        assert "ptr-pdfs" in url
        assert "12345678.pdf" in url

    def test_parse_filing_date_valid(self):
        """parse_filing_date parses valid date."""
        from app.services.house_etl import HouseDisclosureScraper

        result = HouseDisclosureScraper.parse_filing_date("01/25/2024")

        assert result is not None
        assert "2024-01-25" in result

    def test_parse_filing_date_invalid(self):
        """parse_filing_date returns None for invalid date."""
        from app.services.house_etl import HouseDisclosureScraper

        result = HouseDisclosureScraper.parse_filing_date("invalid")

        assert result is None

    def test_parse_filing_date_empty(self):
        """parse_filing_date returns None for empty string."""
        from app.services.house_etl import HouseDisclosureScraper

        result = HouseDisclosureScraper.parse_filing_date("")

        assert result is None

    def test_parse_disclosure_record_valid(self):
        """parse_disclosure_record parses valid line."""
        from app.services.house_etl import HouseDisclosureScraper

        # Format: prefix, last_name, first_name, suffix, filing_type, state_district, year, date, doc_id
        line = "\tSmith\tJane\t\tP\tCA-12\t2024\t01/25/2024\t20012345"

        result = HouseDisclosureScraper.parse_disclosure_record(line, 2024)

        assert result is not None
        assert result["last_name"] == "Smith"
        assert result["first_name"] == "Jane"
        assert result["filing_type"] == "P"
        assert result["doc_id"] == "20012345"
        assert result["year"] == 2024

    def test_parse_disclosure_record_too_few_fields(self):
        """parse_disclosure_record returns None for too few fields."""
        from app.services.house_etl import HouseDisclosureScraper

        line = "Smith\tJane\tP"  # Only 3 fields

        result = HouseDisclosureScraper.parse_disclosure_record(line, 2024)

        assert result is None

    def test_parse_disclosure_record_header_row(self):
        """parse_disclosure_record returns None for header row."""
        from app.services.house_etl import HouseDisclosureScraper

        line = "Prefix\tLast\tFirst\tSuffix\tType\tState\tYear\tDate\tDocID"

        result = HouseDisclosureScraper.parse_disclosure_record(line, 2024)

        assert result is None

    def test_parse_disclosure_index(self):
        """parse_disclosure_index parses full index content."""
        from app.services.house_etl import HouseDisclosureScraper

        content = """Prefix\tLast\tFirst\tSuffix\tType\tState\tYear\tDate\tDocID
\tSmith\tJane\t\tP\tCA-12\t2024\t01/25/2024\t20012345
\tDoe\tJohn\t\tP\tNY-03\t2024\t01/26/2024\t20012346"""

        disclosures = HouseDisclosureScraper.parse_disclosure_index(content, 2024)

        assert len(disclosures) == 2
        assert disclosures[0]["last_name"] == "Smith"
        assert disclosures[1]["last_name"] == "Doe"


# =============================================================================
# Fetch PDF Tests (with mocks)
# =============================================================================

class TestFetchPdf:
    """Tests for PDF fetching functionality."""

    @pytest.mark.asyncio
    async def test_fetch_pdf_success(self):
        """fetch_pdf returns PDF bytes on success."""
        from app.services.house_etl import HouseDisclosureScraper, RateLimiter
        import app.services.house_etl as house_etl

        # Reset rate limiter
        house_etl.rate_limiter = RateLimiter()
        house_etl.rate_limiter.current_delay = 0  # Skip delays for testing

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"%PDF-1.4 test content"
        mock_client.get.return_value = mock_response

        result = await HouseDisclosureScraper.fetch_pdf(
            mock_client, "https://example.com/test.pdf"
        )

        assert result == b"%PDF-1.4 test content"

    @pytest.mark.asyncio
    async def test_fetch_pdf_not_found(self):
        """fetch_pdf returns None on 404."""
        from app.services.house_etl import HouseDisclosureScraper, RateLimiter
        import app.services.house_etl as house_etl

        house_etl.rate_limiter = RateLimiter()
        house_etl.rate_limiter.current_delay = 0

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.get.return_value = mock_response

        result = await HouseDisclosureScraper.fetch_pdf(
            mock_client, "https://example.com/test.pdf"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_pdf_invalid_content(self):
        """fetch_pdf returns None for non-PDF content."""
        from app.services.house_etl import HouseDisclosureScraper, RateLimiter
        import app.services.house_etl as house_etl

        house_etl.rate_limiter = RateLimiter()
        house_etl.rate_limiter.current_delay = 0

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"<html>Not a PDF</html>"
        mock_client.get.return_value = mock_response

        result = await HouseDisclosureScraper.fetch_pdf(
            mock_client, "https://example.com/test.pdf"
        )

        assert result is None


# =============================================================================
# Integration-Style Tests
# =============================================================================

class TestHouseETLIntegration:
    """Integration-style tests for House ETL."""

    def test_full_row_parsing_pipeline(self):
        """Tests the full row parsing pipeline with realistic data."""
        from app.services.house_etl import parse_transaction_from_row

        # Realistic House disclosure PDF row
        row = [
            "NVIDIA Corporation (NVDA) ST P 01/15/2025 01/25/2025 $15,001 - $50,000 N F S: Joint",
            None,
            None,
            None,
        ]

        disclosure = {
            "politician_name": "Nancy Pelosi",
            "first_name": "Nancy",
            "last_name": "Pelosi",
            "doc_id": "20012345",
            "filing_type": "P",
            "filing_date": "2025-01-25",
            "state_district": "CA-12",
        }

        result = parse_transaction_from_row(row, disclosure)

        # Should extract transaction despite metadata at end
        assert result is not None
        assert "NVIDIA" in result["asset_name"]
        assert result["asset_ticker"] == "NVDA"

    def test_job_status_initialization(self):
        """Tests that JOB_STATUS is properly initialized."""
        from app.services.house_etl import JOB_STATUS

        # JOB_STATUS should be a dictionary
        assert isinstance(JOB_STATUS, dict)
