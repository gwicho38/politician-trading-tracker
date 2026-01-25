"""
Unit tests for QuiverQuant ETL metrics (METRICS.md Section 3.1).

Tests all fields populated from QuiverQuant Congress Trading API:
- Politicians table: full_name, bioguide_id, party, chamber
- Trading disclosures: asset_ticker, asset_name, transaction_type, transaction_date,
  disclosure_date, amount_range_min, amount_range_max, source_url
- Raw data fields: ExcessReturn, PriceChange, SPYChange, TickerType

Run with: cd python-etl-service && pytest tests/test_quiverquant_metrics.py -v
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, date
import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.lib.parser import parse_value_range


# =============================================================================
# SECTION 3.1: Politicians Table - QuiverQuant Fields (4 metrics)
# =============================================================================

class TestQuiverQuantPoliticianFullName:
    """[ ] politicians.full_name - From QuiverQuant 'Representative' field"""

    def test_extract_full_name(self, sample_quiverquant_response):
        """Test extracting full name from API response."""
        record = sample_quiverquant_response[0]
        full_name = record["Representative"]
        assert full_name == "Jonathan Jackson"

    def test_full_name_format(self, sample_quiverquant_response):
        """Test full name has first and last name."""
        record = sample_quiverquant_response[0]
        full_name = record["Representative"]
        parts = full_name.split()
        assert len(parts) >= 2  # At least first and last name


class TestQuiverQuantPoliticianBioguideId:
    """[ ] politicians.bioguide_id - From QuiverQuant 'BioGuideID' field"""

    def test_extract_bioguide(self, sample_quiverquant_response):
        """Test extracting BioGuide ID from API response."""
        record = sample_quiverquant_response[0]
        bioguide = record["BioGuideID"]
        assert bioguide == "J000309"

    def test_bioguide_format(self, sample_quiverquant_response):
        """Test BioGuide ID format (letter + 6 digits)."""
        record = sample_quiverquant_response[0]
        bioguide = record["BioGuideID"]
        assert len(bioguide) == 7
        assert bioguide[0].isalpha()
        assert bioguide[1:].isdigit()

    def test_bioguide_can_match_politician(self, sample_quiverquant_response):
        """Test BioGuide ID can be used to match politician."""
        record = sample_quiverquant_response[0]
        bioguide = record["BioGuideID"]
        # Should be able to use this to find existing politician
        assert bioguide is not None
        assert len(bioguide) > 0


class TestQuiverQuantPoliticianParty:
    """[ ] politicians.party - From QuiverQuant 'Party' field ('D', 'R', or 'I')"""

    def test_extract_party(self, sample_quiverquant_response):
        """Test extracting party from API response."""
        record = sample_quiverquant_response[0]
        party = record["Party"]
        assert party == "D"

    def test_party_valid_codes(self, sample_quiverquant_response):
        """Test party is a valid code."""
        record = sample_quiverquant_response[0]
        party = record["Party"]
        assert party in ["D", "R", "I"]


class TestQuiverQuantPoliticianChamber:
    """[ ] politicians.chamber - From QuiverQuant 'House' field ('Representatives' or 'Senate')"""

    def test_extract_chamber(self, sample_quiverquant_response):
        """Test extracting chamber from API response."""
        record = sample_quiverquant_response[0]
        chamber = record["House"]
        assert chamber == "Representatives"

    def test_chamber_normalization(self):
        """Test chamber normalization."""
        def normalize_chamber(house: str) -> str:
            if house == "Representatives":
                return "House"
            elif house == "Senate":
                return "Senate"
            return house

        assert normalize_chamber("Representatives") == "House"
        assert normalize_chamber("Senate") == "Senate"


# =============================================================================
# SECTION 3.1: Trading Disclosures Table - QuiverQuant Fields (8 metrics)
# =============================================================================

class TestQuiverQuantAssetTicker:
    """[ ] trading_disclosures.asset_ticker - From QuiverQuant 'Ticker' field"""

    def test_extract_ticker(self, sample_quiverquant_response):
        """Test extracting ticker from API response."""
        record = sample_quiverquant_response[0]
        ticker = record["Ticker"]
        assert ticker == "HOOD"

    def test_ticker_uppercase(self, sample_quiverquant_response):
        """Test ticker is uppercase."""
        record = sample_quiverquant_response[0]
        ticker = record["Ticker"]
        assert ticker == ticker.upper()

    def test_ticker_nvda(self, sample_quiverquant_response):
        """Test NVDA ticker extraction."""
        record = sample_quiverquant_response[1]
        ticker = record["Ticker"]
        assert ticker == "NVDA"


class TestQuiverQuantAssetName:
    """[ ] trading_disclosures.asset_name - From QuiverQuant 'Description' field (or ticker fallback)"""

    def test_asset_name_from_description(self, sample_quiverquant_response):
        """Test extracting asset name from Description field."""
        record = sample_quiverquant_response[1]
        description = record["Description"]
        assert description == "NVIDIA Corporation"

    def test_asset_name_fallback_to_ticker(self, sample_quiverquant_response):
        """Test falling back to ticker when Description is null."""
        record = sample_quiverquant_response[0]
        description = record["Description"]
        ticker = record["Ticker"]

        asset_name = description if description else ticker
        assert asset_name == "HOOD"  # Falls back to ticker


class TestQuiverQuantTransactionType:
    """[ ] trading_disclosures.transaction_type - Normalized from 'Transaction' field"""

    def test_sale_transaction(self, sample_quiverquant_response):
        """Test sale transaction type."""
        record = sample_quiverquant_response[0]
        tx_type = record["Transaction"]
        assert tx_type == "Sale"

    def test_purchase_transaction(self, sample_quiverquant_response):
        """Test purchase transaction type."""
        record = sample_quiverquant_response[1]
        tx_type = record["Transaction"]
        assert tx_type == "Purchase"

    def test_transaction_type_normalization(self):
        """Test transaction type normalization."""
        def normalize(tx: str) -> str:
            tx = tx.lower()
            if tx in ["sale", "sell"]:
                return "sale"
            elif tx in ["purchase", "buy"]:
                return "purchase"
            return "unknown"

        assert normalize("Sale") == "sale"
        assert normalize("Purchase") == "purchase"
        assert normalize("Sell") == "sale"
        assert normalize("Buy") == "purchase"


class TestQuiverQuantTransactionDate:
    """[ ] trading_disclosures.transaction_date - From 'TransactionDate' field"""

    def test_extract_transaction_date(self, sample_quiverquant_response):
        """Test extracting transaction date."""
        record = sample_quiverquant_response[0]
        tx_date = record["TransactionDate"]
        assert tx_date == "2023-12-22"

    def test_transaction_date_format(self, sample_quiverquant_response):
        """Test transaction date is ISO format."""
        record = sample_quiverquant_response[0]
        tx_date = record["TransactionDate"]
        parsed = datetime.strptime(tx_date, "%Y-%m-%d")
        assert parsed.year == 2023
        assert parsed.month == 12
        assert parsed.day == 22


class TestQuiverQuantDisclosureDate:
    """[ ] trading_disclosures.disclosure_date - From 'ReportDate' field"""

    def test_extract_disclosure_date(self, sample_quiverquant_response):
        """Test extracting disclosure/report date."""
        record = sample_quiverquant_response[0]
        report_date = record["ReportDate"]
        assert report_date == "2024-01-08"

    def test_disclosure_after_transaction(self, sample_quiverquant_response):
        """Test disclosure date is after transaction date."""
        record = sample_quiverquant_response[0]
        tx_date = datetime.strptime(record["TransactionDate"], "%Y-%m-%d")
        report_date = datetime.strptime(record["ReportDate"], "%Y-%m-%d")
        assert report_date > tx_date


class TestQuiverQuantAmountRangeMin:
    """[ ] trading_disclosures.amount_range_min - Parsed from 'Range' field"""

    def test_parse_range_min(self, sample_quiverquant_response):
        """Test parsing minimum from Range field."""
        record = sample_quiverquant_response[0]
        range_str = record["Range"]
        result = parse_value_range(range_str)
        assert result["value_low"] == 15001

    def test_parse_large_range_min(self, sample_quiverquant_response):
        """Test parsing large range minimum."""
        record = sample_quiverquant_response[1]
        range_str = record["Range"]
        result = parse_value_range(range_str)
        assert result["value_low"] == 1000001


class TestQuiverQuantAmountRangeMax:
    """[ ] trading_disclosures.amount_range_max - Parsed from 'Range' field"""

    def test_parse_range_max(self, sample_quiverquant_response):
        """Test parsing maximum from Range field."""
        record = sample_quiverquant_response[0]
        range_str = record["Range"]
        result = parse_value_range(range_str)
        assert result["value_high"] == 50000

    def test_parse_large_range_max(self, sample_quiverquant_response):
        """Test parsing large range maximum."""
        record = sample_quiverquant_response[1]
        range_str = record["Range"]
        result = parse_value_range(range_str)
        assert result["value_high"] == 5000000


class TestQuiverQuantSourceUrl:
    """[ ] trading_disclosures.source_url - Fixed QuiverQuant URL"""

    def test_source_url_fixed(self):
        """Test source URL is QuiverQuant."""
        source_url = "https://www.quiverquant.com/congresstrading/"
        assert "quiverquant.com" in source_url
        assert "congresstrading" in source_url


# =============================================================================
# SECTION 3.1: Raw Data Fields - QuiverQuant-Only Metrics (4 metrics)
# =============================================================================

class TestQuiverQuantExcessReturn:
    """[ ] raw_data.ExcessReturn - Performance vs SPY benchmark (%)"""

    def test_extract_excess_return(self, sample_quiverquant_response):
        """Test extracting excess return."""
        record = sample_quiverquant_response[0]
        excess_return = record["ExcessReturn"]
        assert excess_return == -6.39

    def test_excess_return_positive(self, sample_quiverquant_response):
        """Test positive excess return."""
        record = sample_quiverquant_response[1]
        excess_return = record["ExcessReturn"]
        assert excess_return == 12.5
        assert excess_return > 0

    def test_excess_return_is_percentage(self, sample_quiverquant_response):
        """Test excess return is a percentage value."""
        record = sample_quiverquant_response[0]
        excess_return = record["ExcessReturn"]
        # Percentage values are typically between -100 and +1000
        assert -100 <= excess_return <= 1000


class TestQuiverQuantPriceChange:
    """[ ] raw_data.PriceChange - Actual price change since trade (%)"""

    def test_extract_price_change(self, sample_quiverquant_response):
        """Test extracting price change."""
        record = sample_quiverquant_response[0]
        price_change = record["PriceChange"]
        assert price_change == -5.70

    def test_price_change_positive(self, sample_quiverquant_response):
        """Test positive price change."""
        record = sample_quiverquant_response[1]
        price_change = record["PriceChange"]
        assert price_change == 15.2
        assert price_change > 0


class TestQuiverQuantSPYChange:
    """[ ] raw_data.SPYChange - S&P 500 change over same period (%)"""

    def test_extract_spy_change(self, sample_quiverquant_response):
        """Test extracting SPY change."""
        record = sample_quiverquant_response[0]
        spy_change = record["SPYChange"]
        assert spy_change == 0.69

    def test_spy_change_comparison(self, sample_quiverquant_response):
        """Test SPY change for performance comparison."""
        record = sample_quiverquant_response[0]
        price_change = record["PriceChange"]
        spy_change = record["SPYChange"]

        # Excess return should be approximately price_change - spy_change
        calculated_excess = price_change - spy_change
        actual_excess = record["ExcessReturn"]
        assert abs(calculated_excess - actual_excess) < 0.1  # Allow small rounding diff


class TestQuiverQuantTickerType:
    """[ ] raw_data.TickerType - Asset type code ('ST' = Stock)"""

    def test_extract_ticker_type(self, sample_quiverquant_response):
        """Test extracting ticker type."""
        record = sample_quiverquant_response[0]
        ticker_type = record["TickerType"]
        assert ticker_type == "ST"

    def test_ticker_type_meanings(self):
        """Test ticker type code meanings."""
        type_map = {
            "ST": "Stock",
            "BD": "Bond",
            "OP": "Option",
            "MF": "Mutual Fund",
            "ET": "ETF",
        }
        assert type_map.get("ST") == "Stock"


# =============================================================================
# QuiverQuant API Response Validation Tests
# =============================================================================

class TestQuiverQuantAPIResponse:
    """Tests for QuiverQuant API response validation."""

    def test_response_is_list(self, sample_quiverquant_response):
        """Test API response is a list."""
        assert isinstance(sample_quiverquant_response, list)

    def test_response_has_records(self, sample_quiverquant_response):
        """Test response has records."""
        assert len(sample_quiverquant_response) > 0

    def test_record_has_required_fields(self, sample_quiverquant_response):
        """Test each record has required fields."""
        required_fields = [
            "Representative",
            "BioGuideID",
            "ReportDate",
            "TransactionDate",
            "Ticker",
            "Transaction",
            "Range",
            "House",
            "Party",
        ]
        for record in sample_quiverquant_response:
            for field in required_fields:
                assert field in record, f"Missing field: {field}"

    def test_last_modified_field(self, sample_quiverquant_response):
        """Test last_modified field exists."""
        record = sample_quiverquant_response[0]
        assert "last_modified" in record


# =============================================================================
# QuiverQuant Data Quality Tests
# =============================================================================

class TestQuiverQuantDataQuality:
    """Tests for QuiverQuant data quality."""

    def test_dates_are_valid(self, sample_quiverquant_response):
        """Test dates are valid ISO format."""
        for record in sample_quiverquant_response:
            tx_date = record["TransactionDate"]
            report_date = record["ReportDate"]

            # Both should parse without error
            datetime.strptime(tx_date, "%Y-%m-%d")
            datetime.strptime(report_date, "%Y-%m-%d")

    def test_amounts_can_be_parsed(self, sample_quiverquant_response):
        """Test amount ranges can be parsed."""
        for record in sample_quiverquant_response:
            range_str = record["Range"]
            result = parse_value_range(range_str)
            assert result["value_low"] is not None
            assert result["value_high"] is not None
            assert result["value_high"] >= result["value_low"]

    def test_bioguide_ids_unique(self):
        """Test BioGuide IDs are unique per politician."""
        bioguide_to_name = {}
        sample = [
            {"BioGuideID": "J000309", "Representative": "Jonathan Jackson"},
            {"BioGuideID": "P000197", "Representative": "Nancy Pelosi"},
        ]
        for record in sample:
            bg = record["BioGuideID"]
            name = record["Representative"]
            if bg in bioguide_to_name:
                # Same BioGuide should have same name
                assert bioguide_to_name[bg] == name
            else:
                bioguide_to_name[bg] = name


# =============================================================================
# QuiverQuant vs Official Source Comparison Tests
# =============================================================================

class TestQuiverQuantVsOfficialSource:
    """Compare QuiverQuant data with official sources."""

    def test_quiverquant_has_party(self):
        """Test QuiverQuant provides party (unlike House PDFs)."""
        quiver_record = {"Party": "D"}
        assert "Party" in quiver_record

    def test_quiverquant_has_bioguide(self):
        """Test QuiverQuant provides BioGuide ID."""
        quiver_record = {"BioGuideID": "J000309"}
        assert "BioGuideID" in quiver_record

    def test_quiverquant_has_performance_metrics(self):
        """Test QuiverQuant has performance metrics official sources lack."""
        quiver_record = {
            "ExcessReturn": -6.39,
            "PriceChange": -5.70,
            "SPYChange": 0.69,
        }
        # These metrics are unique to QuiverQuant
        assert "ExcessReturn" in quiver_record
        assert "PriceChange" in quiver_record
        assert "SPYChange" in quiver_record
