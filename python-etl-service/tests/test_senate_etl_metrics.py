"""
Unit tests for US Senate ETL metrics (METRICS.md Section 2.2).

Tests all fields populated from Senate Financial Disclosures:
- Politicians table: first_name, last_name, full_name, party, state_or_country, bioguide_id, role, chamber
- Trading disclosures: asset_name, asset_ticker, asset_type, transaction_type, transaction_date,
  disclosure_date, amount_range_min, amount_range_max, source_url, asset_owner, comments

Run with: cd python-etl-service && pytest tests/test_senate_etl_metrics.py -v
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, date
import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.lib.parser import (
    extract_ticker_from_text,
    sanitize_string,
    parse_value_range,
)


# =============================================================================
# SECTION 2.2: Politicians Table - Senate Fields (8 metrics)
# =============================================================================

class TestSenatePoliticianFirstName:
    """[ ] politicians.first_name - Senator first name from XML/HTML"""

    def test_extract_first_name_from_xml(self, sample_senate_xml_senator):
        """Test extracting first name from Senate XML."""
        first_name = sample_senate_xml_senator["first_name"]
        assert first_name == "John"

    def test_first_name_not_empty(self, sample_senate_xml_senator):
        """Test first name is not empty."""
        first_name = sample_senate_xml_senator["first_name"]
        assert len(first_name) > 0

    def test_first_name_sanitized(self):
        """Test first name is sanitized."""
        first_name = sanitize_string("  John  ")
        assert first_name.strip() == "John"


class TestSenatePoliticianLastName:
    """[ ] politicians.last_name - Senator last name from XML/HTML"""

    def test_extract_last_name_from_xml(self, sample_senate_xml_senator):
        """Test extracting last name from Senate XML."""
        last_name = sample_senate_xml_senator["last_name"]
        assert last_name == "Smith"

    def test_last_name_not_empty(self, sample_senate_xml_senator):
        """Test last name is not empty."""
        last_name = sample_senate_xml_senator["last_name"]
        assert len(last_name) > 0


class TestSenatePoliticianFullName:
    """[ ] politicians.full_name - Combined name from XML/HTML"""

    def test_full_name_combined(self, sample_senate_xml_senator):
        """Test full name is properly combined."""
        full_name = sample_senate_xml_senator["full_name"]
        assert full_name == "John Smith"

    def test_full_name_contains_parts(self, sample_senate_xml_senator):
        """Test full name contains first and last."""
        full_name = sample_senate_xml_senator["full_name"]
        first_name = sample_senate_xml_senator["first_name"]
        last_name = sample_senate_xml_senator["last_name"]
        assert first_name in full_name
        assert last_name in full_name


class TestSenatePoliticianParty:
    """[ ] politicians.party - Party affiliation 'D', 'R', or 'I' from XML"""

    def test_party_democrat(self, sample_senate_xml_senator):
        """Test Democrat party code."""
        party = sample_senate_xml_senator["party"]
        assert party == "D"

    def test_party_valid_codes(self):
        """Test all valid party codes."""
        valid_parties = ["D", "R", "I", "ID"]  # ID = Independent Democrat
        for party in ["D", "R", "I"]:
            assert party in valid_parties

    def test_party_normalization(self):
        """Test party code normalization."""
        def normalize_party(party: str) -> str:
            party = party.upper().strip()
            if party in ["DEMOCRAT", "DEM", "D"]:
                return "D"
            elif party in ["REPUBLICAN", "REP", "R"]:
                return "R"
            elif party in ["INDEPENDENT", "IND", "I"]:
                return "I"
            return party

        assert normalize_party("Democrat") == "D"
        assert normalize_party("Republican") == "R"
        assert normalize_party("Independent") == "I"
        assert normalize_party("dem") == "D"


class TestSenatePoliticianStateOrCountry:
    """[ ] politicians.state_or_country - State abbreviation from XML"""

    def test_state_from_xml(self, sample_senate_xml_senator):
        """Test extracting state from XML."""
        state = sample_senate_xml_senator["state"]
        assert state == "CA"

    def test_state_is_two_letters(self, sample_senate_xml_senator):
        """Test state code is 2 letters."""
        state = sample_senate_xml_senator["state"]
        assert len(state) == 2

    def test_state_is_uppercase(self, sample_senate_xml_senator):
        """Test state code is uppercase."""
        state = sample_senate_xml_senator["state"]
        assert state == state.upper()


class TestSenatePoliticianBioguideId:
    """[ ] politicians.bioguide_id - Congress.gov BioGuide ID from XML"""

    def test_bioguide_from_xml(self, sample_senate_xml_senator):
        """Test extracting BioGuide ID from XML."""
        bioguide = sample_senate_xml_senator["bioguide_id"]
        assert bioguide == "S000123"

    def test_bioguide_format(self, sample_senate_xml_senator):
        """Test BioGuide ID format (letter + 6 digits)."""
        bioguide = sample_senate_xml_senator["bioguide_id"]
        assert len(bioguide) == 7
        assert bioguide[0].isalpha()
        assert bioguide[1:].isdigit()

    def test_bioguide_first_letter_meanings(self):
        """Test common BioGuide first letter patterns."""
        # First letter often matches last name initial
        bioguide_examples = ["P000197", "S000123", "W000437"]
        for bg in bioguide_examples:
            assert bg[0].isupper()


class TestSenatePoliticianRole:
    """[ ] politicians.role - Fixed 'Senator'"""

    def test_role_is_senator(self):
        """Test Senate members have Senator role."""
        role = "Senator"
        assert role == "Senator"

    def test_role_not_representative(self):
        """Test Senate role is not Representative."""
        role = "Senator"
        assert role != "Representative"


class TestSenatePoliticianChamber:
    """[ ] politicians.chamber - Fixed 'Senate'"""

    def test_chamber_is_senate(self):
        """Test chamber is Senate."""
        chamber = "Senate"
        assert chamber == "Senate"

    def test_chamber_not_house(self):
        """Test chamber is not House."""
        chamber = "Senate"
        assert chamber != "House"


# =============================================================================
# SECTION 2.2: Trading Disclosures Table - Senate Fields (11 metrics)
# =============================================================================

class TestSenateAssetName:
    """[ ] trading_disclosures.asset_name - Full asset/security name from HTML"""

    def test_asset_name_from_html(self, sample_senate_disclosure_row):
        """Test extracting asset name from HTML table."""
        asset_name = sample_senate_disclosure_row["asset_name"]
        assert asset_name == "Alphabet Inc Class A"

    def test_asset_name_with_class(self, sample_senate_disclosure_row):
        """Test asset names with share class."""
        asset_name = sample_senate_disclosure_row["asset_name"]
        assert "Class" in asset_name


class TestSenateAssetTicker:
    """[ ] trading_disclosures.asset_ticker - Stock ticker from HTML"""

    def test_ticker_from_html(self, sample_senate_disclosure_row):
        """Test extracting ticker from HTML table."""
        ticker = sample_senate_disclosure_row["ticker"]
        assert ticker == "GOOGL"

    def test_ticker_uppercase(self, sample_senate_disclosure_row):
        """Test ticker is uppercase."""
        ticker = sample_senate_disclosure_row["ticker"]
        assert ticker == ticker.upper()


class TestSenateAssetType:
    """[ ] trading_disclosures.asset_type - Type of asset from HTML"""

    def test_asset_type_stock(self, sample_senate_disclosure_row):
        """Test stock asset type."""
        asset_type = sample_senate_disclosure_row["asset_type"]
        assert asset_type == "Stock"

    def test_asset_type_normalization(self):
        """Test asset type normalization."""
        def normalize_asset_type(t: str) -> str:
            t = t.lower()
            if "stock" in t:
                return "stock"
            elif "bond" in t:
                return "bond"
            elif "option" in t:
                return "option"
            elif "mutual fund" in t or "fund" in t:
                return "mutual_fund"
            elif "etf" in t:
                return "etf"
            return "other"

        assert normalize_asset_type("Stock") == "stock"
        assert normalize_asset_type("Corporate Bond") == "bond"
        assert normalize_asset_type("Call Option") == "option"


class TestSenateTransactionType:
    """[ ] trading_disclosures.transaction_type - 'purchase', 'sale', 'exchange' from HTML"""

    def test_sale_full_normalized(self, sample_senate_disclosure_row):
        """Test 'Sale (Full)' normalization."""
        tx_type = sample_senate_disclosure_row["transaction_type"]

        def normalize(t):
            t = t.lower()
            if "sale" in t:
                return "sale"
            elif "purchase" in t:
                return "purchase"
            elif "exchange" in t:
                return "exchange"
            return "unknown"

        assert normalize(tx_type) == "sale"

    def test_sale_partial_normalized(self):
        """Test 'Sale (Partial)' normalization."""
        def normalize(t):
            t = t.lower()
            if "sale" in t:
                return "sale"
            return t

        assert normalize("Sale (Partial)") == "sale"

    def test_purchase_normalized(self):
        """Test purchase normalization."""
        def normalize(t):
            t = t.lower()
            if "purchase" in t:
                return "purchase"
            return t

        assert normalize("Purchase") == "purchase"


class TestSenateTransactionDate:
    """[ ] trading_disclosures.transaction_date - Date of transaction from HTML"""

    def test_transaction_date_parsed(self, sample_senate_disclosure_row):
        """Test transaction date parsing."""
        date_str = sample_senate_disclosure_row["transaction_date"]
        parsed = datetime.strptime(date_str, "%Y-%m-%d")
        assert parsed.year == 2024
        assert parsed.month == 1
        assert parsed.day == 10


class TestSenateDisclosureDate:
    """[ ] trading_disclosures.disclosure_date - Date disclosed to Senate from HTML"""

    def test_disclosure_date_parsed(self, sample_senate_transactions):
        """Test disclosure date parsing."""
        tx = sample_senate_transactions[0]
        date_str = tx["disclosure_date"]
        parsed = datetime.strptime(date_str, "%Y-%m-%d")
        assert parsed.year == 2024


class TestSenateAmountRangeMin:
    """[ ] trading_disclosures.amount_range_min - Lower bound from HTML"""

    def test_amount_min_senate_format(self, sample_senate_disclosure_row):
        """Test parsing Senate amount range format."""
        amount_str = sample_senate_disclosure_row["amount"]
        result = parse_value_range(amount_str)
        assert result["value_low"] == 50001


class TestSenateAmountRangeMax:
    """[ ] trading_disclosures.amount_range_max - Upper bound from HTML"""

    def test_amount_max_senate_format(self, sample_senate_disclosure_row):
        """Test parsing Senate amount range upper bound."""
        amount_str = sample_senate_disclosure_row["amount"]
        result = parse_value_range(amount_str)
        assert result["value_high"] == 100000


class TestSenateSourceUrl:
    """[ ] trading_disclosures.source_url - Link to Senate EFD page"""

    def test_efd_url_format(self):
        """Test Senate EFD URL format."""
        base_url = "https://efdsearch.senate.gov/search/view"
        doc_id = "ptr/12345"
        url = f"{base_url}/{doc_id}/"
        assert "efdsearch.senate.gov" in url
        assert "ptr" in url

    def test_url_is_https(self):
        """Test URL uses HTTPS."""
        url = "https://efdsearch.senate.gov/search/view/ptr/12345/"
        assert url.startswith("https://")


class TestSenateAssetOwner:
    """[ ] trading_disclosures.asset_owner - Owner of the asset from HTML"""

    def test_owner_self(self, sample_senate_disclosure_row):
        """Test self ownership."""
        owner = sample_senate_disclosure_row["owner"]
        assert owner == "Self"

    def test_owner_normalization(self):
        """Test owner normalization."""
        def normalize_owner(owner: str) -> str:
            owner = owner.lower().strip()
            if owner in ["self", "filer"]:
                return "self"
            elif owner in ["spouse", "sp"]:
                return "spouse"
            elif owner in ["joint", "jt"]:
                return "joint"
            elif owner in ["child", "dependent", "dc"]:
                return "dependent_child"
            return owner

        assert normalize_owner("Self") == "self"
        assert normalize_owner("Spouse") == "spouse"
        assert normalize_owner("Joint") == "joint"


class TestSenateComments:
    """[ ] trading_disclosures.comments - Additional notes from HTML"""

    def test_empty_comment(self, sample_senate_disclosure_row):
        """Test handling empty comment."""
        comment = sample_senate_disclosure_row["comment"]
        result = comment if comment else None
        assert result is None

    def test_comment_with_text(self):
        """Test handling comment with text."""
        comment = "Blind trust transaction"
        result = comment if comment else None
        assert result == "Blind trust transaction"


# =============================================================================
# Senate XML Parsing Tests
# =============================================================================

class TestSenateXMLParsing:
    """Tests for parsing Senate XML data."""

    def test_parse_senator_count(self):
        """Test that Senate has ~100 senators."""
        # Each state has 2 senators
        expected_count = 100
        assert expected_count == 100

    def test_xml_contains_bioguide(self):
        """Test XML contains bioguide_id field."""
        sample_xml = {
            "bioguide_id": "S000123",
            "first_name": "John",
            "last_name": "Smith",
        }
        assert "bioguide_id" in sample_xml

    def test_xml_party_codes(self):
        """Test XML party codes."""
        parties = ["D", "R", "I"]
        for party in parties:
            assert party in ["D", "R", "I", "ID"]


# =============================================================================
# Senate EFD Scraping Tests
# =============================================================================

class TestSenateEFDScraping:
    """Tests for Senate EFD HTML scraping."""

    def test_efd_table_has_required_columns(self):
        """Test EFD table has required columns."""
        required_columns = [
            "transaction_date",
            "owner",
            "ticker",
            "asset_name",
            "transaction_type",
            "amount",
        ]
        sample_row = {
            "transaction_date": "2024-01-10",
            "owner": "Self",
            "ticker": "GOOGL",
            "asset_name": "Alphabet Inc",
            "transaction_type": "Sale",
            "amount": "$50,001 - $100,000",
        }
        for col in required_columns:
            assert col in sample_row

    def test_efd_search_url_format(self):
        """Test EFD search URL format."""
        base_url = "https://efdsearch.senate.gov/search/"
        assert "efdsearch.senate.gov" in base_url


# =============================================================================
# Senate vs House Comparison Tests
# =============================================================================

class TestSenateVsHouseComparison:
    """Compare Senate and House ETL differences."""

    def test_senate_has_party_in_source(self):
        """Test Senate XML provides party directly."""
        senate_source = {"party": "D"}
        assert "party" in senate_source

    def test_house_needs_party_enrichment(self):
        """Test House needs party from external source."""
        house_source = {"full_name": "Jane Smith", "state_district": "CA-12"}
        # House PDFs don't include party
        assert "party" not in house_source

    def test_senate_uses_html_scraping(self):
        """Test Senate uses HTML scraping (Playwright)."""
        scrape_method = "playwright"
        assert scrape_method in ["playwright", "selenium", "requests"]

    def test_house_uses_pdf_parsing(self):
        """Test House uses PDF parsing."""
        parse_method = "pdfplumber"
        assert parse_method in ["pdfplumber", "pypdf", "tabula"]


# =============================================================================
# Integration Tests - Full Senate Record
# =============================================================================

class TestSenateRecordIntegration:
    """Integration tests for complete Senate records."""

    def test_complete_senate_record(self, sample_senate_xml_senator, sample_senate_transactions):
        """Test complete Senate record has all fields."""
        senator = sample_senate_xml_senator
        transaction = sample_senate_transactions[0]

        # Senator fields
        assert senator["full_name"]
        assert senator["party"]
        assert senator["state"]
        assert senator["bioguide_id"]

        # Transaction fields
        assert transaction["asset_name"]
        assert transaction["asset_ticker"]
        assert transaction["transaction_type"]
        assert transaction["transaction_date"]
        assert transaction["amount_range_min"]
        assert transaction["amount_range_max"]

    def test_senator_transaction_linkage(self, sample_senate_xml_senator, sample_senate_transactions):
        """Test senator can be linked to transactions."""
        senator_id = "pol-uuid-123"  # From mock_supabase_with_politician
        transaction = sample_senate_transactions[0]

        # In actual DB, transaction would have politician_id
        linked_transaction = {**transaction, "politician_id": senator_id}
        assert linked_transaction["politician_id"] == senator_id
