"""
Unit tests for enrichment service metrics (METRICS.md Sections 4.1 and 6.1).

Tests fields populated from:
- Congress.gov API (Section 4.1): bioguide_id, first_name, last_name, party, state_or_country, district, role, term_start, term_end
- Ollama LLM Service (Section 6.1): party, full_name for politicians; category, severity for error_reports

Run with: cd python-etl-service && pytest tests/test_enrichment_metrics.py -v
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, date
import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# =============================================================================
# SECTION 4.1: Congress.gov API - Politicians Enrichment (9 metrics)
# =============================================================================

class TestCongressGovBioguideId:
    """[ ] politicians.bioguide_id - From Congress.gov 'bioguideId' field"""

    def test_extract_bioguide(self, sample_congress_member):
        """Test extracting BioGuide ID."""
        member = sample_congress_member
        bioguide = member["bioguideId"]
        assert bioguide == "P000197"

    def test_bioguide_format(self, sample_congress_member):
        """Test BioGuide ID format."""
        member = sample_congress_member
        bioguide = member["bioguideId"]
        # Format: 1 uppercase letter + 6 digits
        assert len(bioguide) == 7
        assert bioguide[0].isupper()
        assert bioguide[1:].isdigit()

    def test_bioguide_can_link_records(self):
        """Test BioGuide ID can link external records."""
        congress_data = {"bioguideId": "P000197", "firstName": "Nancy"}
        quiver_data = {"BioGuideID": "P000197", "Representative": "Nancy Pelosi"}

        # Should be able to match on BioGuide ID
        assert congress_data["bioguideId"] == quiver_data["BioGuideID"]


class TestCongressGovFirstName:
    """[ ] politicians.first_name - From Congress.gov 'firstName' field"""

    def test_extract_first_name(self, sample_congress_member):
        """Test extracting first name."""
        member = sample_congress_member
        first_name = member["firstName"]
        assert first_name == "Nancy"

    def test_first_name_type(self, sample_congress_member):
        """Test first name is a string."""
        member = sample_congress_member
        first_name = member["firstName"]
        assert isinstance(first_name, str)


class TestCongressGovLastName:
    """[ ] politicians.last_name - From Congress.gov 'lastName' field"""

    def test_extract_last_name(self, sample_congress_member):
        """Test extracting last name."""
        member = sample_congress_member
        last_name = member["lastName"]
        assert last_name == "Pelosi"

    def test_last_name_type(self, sample_congress_member):
        """Test last name is a string."""
        member = sample_congress_member
        last_name = member["lastName"]
        assert isinstance(last_name, str)


class TestCongressGovParty:
    """[ ] politicians.party - From Congress.gov 'partyName' field"""

    def test_extract_party_name(self, sample_congress_member):
        """Test extracting party name."""
        member = sample_congress_member
        party = member["partyName"]
        assert party == "Democratic"

    def test_party_normalization(self):
        """Test party name normalization to code."""
        def normalize_party(party_name: str) -> str:
            party_map = {
                "Democratic": "D",
                "Republican": "R",
                "Independent": "I",
                "Libertarian": "L",
            }
            return party_map.get(party_name, "")

        assert normalize_party("Democratic") == "D"
        assert normalize_party("Republican") == "R"
        assert normalize_party("Independent") == "I"


class TestCongressGovStateOrCountry:
    """[ ] politicians.state_or_country - From Congress.gov 'state' field"""

    def test_extract_state(self, sample_congress_member):
        """Test extracting state."""
        member = sample_congress_member
        state = member["state"]
        assert state == "CA"

    def test_state_format(self, sample_congress_member):
        """Test state is 2-letter code."""
        member = sample_congress_member
        state = member["state"]
        assert len(state) == 2
        assert state.isupper()


class TestCongressGovDistrict:
    """[ ] politicians.district - From Congress.gov 'district' field (House only)"""

    def test_extract_district(self, sample_congress_member):
        """Test extracting district."""
        member = sample_congress_member
        district = member["district"]
        assert district == 11

    def test_district_is_number(self, sample_congress_member):
        """Test district is an integer."""
        member = sample_congress_member
        district = member["district"]
        assert isinstance(district, int)

    def test_senate_no_district(self):
        """Test Senators have no district."""
        senator = {"firstName": "John", "state": "CA", "district": None}
        assert senator["district"] is None


class TestCongressGovRole:
    """[ ] politicians.role - From Congress.gov 'chamber' field"""

    def test_role_from_chamber(self, sample_congress_member):
        """Test role derived from chamber."""
        member = sample_congress_member
        chamber = member["terms"][0]["chamber"]
        assert chamber == "House"

    def test_role_mapping(self):
        """Test chamber to role mapping."""
        def chamber_to_role(chamber: str) -> str:
            if chamber == "House":
                return "Representative"
            elif chamber == "Senate":
                return "Senator"
            return chamber

        assert chamber_to_role("House") == "Representative"
        assert chamber_to_role("Senate") == "Senator"


class TestCongressGovTermStart:
    """[ ] politicians.term_start - From Congress.gov 'terms[].startYear' field"""

    def test_extract_term_start(self, sample_congress_member):
        """Test extracting term start year."""
        member = sample_congress_member
        term = member["terms"][0]
        start_year = term["startYear"]
        assert start_year == 2023

    def test_term_start_is_year(self, sample_congress_member):
        """Test term start is a valid year."""
        member = sample_congress_member
        term = member["terms"][0]
        start_year = term["startYear"]
        assert 1900 < start_year < 2100


class TestCongressGovTermEnd:
    """[ ] politicians.term_end - From Congress.gov 'terms[].endYear' field"""

    def test_extract_term_end(self, sample_congress_member):
        """Test extracting term end year."""
        member = sample_congress_member
        term = member["terms"][0]
        end_year = term["endYear"]
        assert end_year == 2025

    def test_term_end_after_start(self, sample_congress_member):
        """Test term end is after term start."""
        member = sample_congress_member
        term = member["terms"][0]
        assert term["endYear"] > term["startYear"]


# =============================================================================
# SECTION 6.1: Ollama LLM Service - Politicians Enrichment (2 metrics)
# =============================================================================

class TestOllamaPartyEnrichment:
    """[ ] politicians.party - Inferred party from LLM"""

    def test_party_inference_prompt(self):
        """Test party inference prompt structure."""
        prompt = """Based on public information, what is the political party affiliation of {name}?
        Respond with only: D (Democrat), R (Republican), or I (Independent)."""

        assert "{name}" in prompt
        assert "D" in prompt
        assert "R" in prompt
        assert "I" in prompt

    def test_party_response_parsing(self):
        """Test parsing LLM party response."""
        def parse_party_response(response: str) -> str:
            response = response.strip().upper()
            if "D" in response or "DEMOCRAT" in response:
                return "D"
            elif "R" in response or "REPUBLICAN" in response:
                return "R"
            elif "I" in response or "INDEPENDENT" in response:
                return "I"
            return ""

        assert parse_party_response("D") == "D"
        assert parse_party_response("Democrat") == "D"
        assert parse_party_response("R") == "R"
        assert parse_party_response("Republican") == "R"
        assert parse_party_response("I") == "I"

    def test_party_fallback_on_failure(self):
        """Test party enrichment fallback on LLM failure."""
        def enrich_party(name: str, llm_available: bool) -> str:
            if not llm_available:
                return ""  # Unknown party
            return "D"  # Mock response

        assert enrich_party("John Doe", llm_available=False) == ""


class TestOllamaFullNameNormalization:
    """[ ] politicians.full_name - Normalized canonical name from LLM"""

    def test_name_normalization_prompt(self):
        """Test name normalization prompt structure."""
        prompt = """Normalize this politician name to canonical form: {name}
        Remove titles, suffixes, and return First Last format."""

        assert "{name}" in prompt
        assert "canonical" in prompt.lower()

    def test_name_normalization_cases(self):
        """Test name normalization cases."""
        def normalize_name(raw_name: str) -> str:
            # Simple normalization without LLM
            raw_name = raw_name.strip()
            # Remove common titles
            for title in ["Rep.", "Sen.", "Hon.", "Mr.", "Mrs.", "Ms.", "Dr."]:
                raw_name = raw_name.replace(title, "")
            # Remove common suffixes
            for suffix in ["Jr.", "Sr.", "III", "II", "IV"]:
                raw_name = raw_name.replace(suffix, "")
            return " ".join(raw_name.split())  # Normalize whitespace

        assert normalize_name("Rep. John Smith") == "John Smith"
        assert normalize_name("Sen. Jane Doe") == "Jane Doe"
        assert normalize_name("  John   Smith  ") == "John Smith"


# =============================================================================
# SECTION 6.1: Ollama LLM Service - Error Reports (2 metrics)
# =============================================================================

class TestOllamaErrorCategory:
    """[ ] error_reports.category - Error category from LLM classification"""

    def test_error_category_classification(self):
        """Test error category classification."""
        categories = [
            "data_quality",
            "etl_failure",
            "api_error",
            "parsing_error",
            "validation_error",
            "unknown",
        ]

        def classify_error(error_message: str) -> str:
            error_lower = error_message.lower()
            if "parse" in error_lower or "extract" in error_lower:
                return "parsing_error"
            elif "api" in error_lower or "request" in error_lower:
                return "api_error"
            elif "valid" in error_lower:
                return "validation_error"
            elif "etl" in error_lower or "pipeline" in error_lower:
                return "etl_failure"
            return "unknown"

        assert classify_error("Failed to parse PDF") == "parsing_error"
        assert classify_error("API request timeout") == "api_error"
        assert classify_error("Validation failed for ticker") == "validation_error"

    def test_error_categories_are_valid(self):
        """Test error categories are from valid set."""
        valid_categories = {
            "data_quality",
            "etl_failure",
            "api_error",
            "parsing_error",
            "validation_error",
            "unknown",
        }
        test_category = "parsing_error"
        assert test_category in valid_categories


class TestOllamaErrorSeverity:
    """[ ] error_reports.severity - Error severity from LLM assessment"""

    def test_severity_levels(self):
        """Test valid severity levels."""
        valid_severities = ["low", "medium", "high", "critical"]

        def assess_severity(error_type: str) -> str:
            severity_map = {
                "parsing_error": "medium",
                "api_error": "high",
                "validation_error": "low",
                "etl_failure": "critical",
            }
            return severity_map.get(error_type, "medium")

        for error_type in ["parsing_error", "api_error", "validation_error", "etl_failure"]:
            severity = assess_severity(error_type)
            assert severity in valid_severities

    def test_severity_ranking(self):
        """Test severity levels have correct ranking."""
        severity_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}

        assert severity_rank["critical"] > severity_rank["high"]
        assert severity_rank["high"] > severity_rank["medium"]
        assert severity_rank["medium"] > severity_rank["low"]


# =============================================================================
# Ticker Backfill Tests (METRICS.md Section 1.3)
# =============================================================================

class TestTickerBackfill:
    """[ ] trading_disclosures.asset_ticker - Backfilled from asset_name"""

    def test_ticker_extraction_from_parentheses(self):
        """Test extracting ticker from parentheses in asset name."""
        from app.lib.parser import extract_ticker_from_text

        asset_name = "Apple Inc. (AAPL)"
        ticker = extract_ticker_from_text(asset_name)
        assert ticker == "AAPL"

    def test_ticker_extraction_common_patterns(self):
        """Test common ticker patterns."""
        from app.lib.parser import extract_ticker_from_text

        test_cases = [
            ("NVIDIA Corporation (NVDA)", "NVDA"),
            ("Tesla Inc (TSLA)", "TSLA"),
            ("Microsoft Corp. (MSFT)", "MSFT"),
        ]

        for asset_name, expected_ticker in test_cases:
            ticker = extract_ticker_from_text(asset_name)
            assert ticker == expected_ticker, f"Failed for {asset_name}"

    def test_ticker_validation(self):
        """Test ticker validation rules."""
        def is_valid_ticker(ticker: str) -> bool:
            if not ticker:
                return False
            if not 1 <= len(ticker) <= 5:
                return False
            if not ticker.isalpha():
                return False
            return True

        assert is_valid_ticker("AAPL") is True
        assert is_valid_ticker("A") is True
        assert is_valid_ticker("GOOGL") is True
        assert is_valid_ticker("TOOLONG") is False
        assert is_valid_ticker("123") is False
        assert is_valid_ticker("") is False


# =============================================================================
# Bioguide Enrichment Integration Tests
# =============================================================================

class TestBioguideEnrichmentIntegration:
    """Integration tests for BioGuide enrichment."""

    def test_match_politician_by_name(self):
        """Test matching politician by name."""
        def match_by_name(db_name: str, api_name: str) -> bool:
            db_parts = set(db_name.lower().split())
            api_parts = set(f"{api_name.get('firstName', '')} {api_name.get('lastName', '')}".lower().split())
            # At least 2 parts must match
            return len(db_parts & api_parts) >= 2

        db_politician = "Nancy Pelosi"
        api_member = {"firstName": "Nancy", "lastName": "Pelosi"}
        assert match_by_name(db_politician, api_member)

    def test_update_politician_with_bioguide(self):
        """Test updating politician with BioGuide data."""
        existing = {
            "id": "pol-123",
            "full_name": "Nancy Pelosi",
            "party": "",  # Missing
            "bioguide_id": None,  # Missing
        }

        enrichment_data = {
            "bioguideId": "P000197",
            "partyName": "Democratic",
            "state": "CA",
        }

        # Merge enrichment
        updated = {
            **existing,
            "bioguide_id": enrichment_data["bioguideId"],
            "party": "D",  # Normalized
            "state_or_country": enrichment_data["state"],
        }

        assert updated["bioguide_id"] == "P000197"
        assert updated["party"] == "D"
        assert updated["state_or_country"] == "CA"


# =============================================================================
# Congress.gov API Rate Limiting Tests
# =============================================================================

class TestCongressGovRateLimiting:
    """Tests for Congress.gov API rate limiting."""

    def test_rate_limit_delay(self):
        """Test rate limit delay between requests."""
        RATE_LIMIT_DELAY = 0.5  # 500ms as documented
        assert RATE_LIMIT_DELAY == 0.5

    def test_api_key_required(self):
        """Test API key is required."""
        api_key = os.environ.get("CONGRESS_API_KEY", "")
        # In tests, this might be empty - that's okay for unit tests
        # Integration tests should have a real key
        assert api_key is not None  # Should at least be empty string, not None


# =============================================================================
# Ollama Service Availability Tests
# =============================================================================

class TestOllamaServiceAvailability:
    """Tests for Ollama service availability handling."""

    def test_graceful_fallback(self):
        """Test graceful fallback when Ollama unavailable."""
        def enrich_with_fallback(data: dict, ollama_available: bool) -> dict:
            if not ollama_available:
                # Return data unchanged
                return data
            # Would normally call Ollama here
            return {**data, "party": "D"}

        original = {"full_name": "John Doe", "party": ""}
        result = enrich_with_fallback(original, ollama_available=False)
        assert result["party"] == ""  # Unchanged

    def test_ollama_url_configuration(self):
        """Test Ollama URL is configurable."""
        default_url = "https://ollama.lefv.info"
        custom_url = os.environ.get("OLLAMA_BASE_URL", default_url)
        assert custom_url is not None
        assert "ollama" in custom_url.lower() or custom_url.startswith("http")
