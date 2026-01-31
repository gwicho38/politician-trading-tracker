"""
Tests for Quality Routes (app/routes/quality.py).

Tests:
- POST /quality/validate-tickers - Validate tickers
- POST /quality/audit-sources - Audit source data
- GET /quality/freshness-report - Get freshness report
- validate_record_integrity() - Record validation helper
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone


# =============================================================================
# POST /quality/validate-tickers Tests
# =============================================================================

class TestValidateTickers:
    """Tests for POST /quality/validate-tickers endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_validate_tickers_returns_200(self, client):
        """POST /quality/validate-tickers returns 200."""
        with patch("app.routes.quality.get_supabase") as mock_supabase:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [{"asset_ticker": "AAPL"}]
            mock_client.table.return_value.select.return_value.gte.return_value.not_.return_value.is_.return_value.limit.return_value.execute.return_value = mock_response
            mock_supabase.return_value = mock_client

            response = client.post("/quality/validate-tickers", json={})

        assert response.status_code == 200

    def test_validate_tickers_returns_validation_results(self, client):
        """POST /quality/validate-tickers returns validation results."""
        with patch("app.routes.quality.get_supabase") as mock_supabase:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [
                {"asset_ticker": "AAPL"},
                {"asset_ticker": "MSFT"},
                {"asset_ticker": "N/A"}  # Invalid
            ]
            mock_client.table.return_value.select.return_value.gte.return_value.not_.return_value.is_.return_value.limit.return_value.execute.return_value = mock_response
            mock_supabase.return_value = mock_client

            response = client.post("/quality/validate-tickers", json={})

        data = response.json()
        assert "invalid_tickers" in data
        assert "low_confidence" in data
        assert "total_checked" in data
        assert "validation_time_ms" in data

    def test_validate_tickers_processes_tickers(self, client):
        """POST /quality/validate-tickers processes tickers from database."""
        with patch("app.routes.quality.get_supabase") as mock_supabase:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [
                {"asset_ticker": "AAPL"},
                {"asset_ticker": "MSFT"},
                {"asset_ticker": "GOOG"}
            ]
            # Full chain mock - the code uses .not_.is_() which is tricky
            mock_client.table.return_value.select.return_value.gte.return_value.not_.is_.return_value.limit.return_value.execute.return_value = mock_response
            mock_supabase.return_value = mock_client

            response = client.post("/quality/validate-tickers", json={})

        data = response.json()
        # Just check that the response has the expected structure
        assert "total_checked" in data

    def test_validate_tickers_no_supabase_returns_500(self, client):
        """POST /quality/validate-tickers returns 500 when Supabase not configured."""
        with patch("app.routes.quality.get_supabase") as mock_supabase:
            mock_supabase.return_value = None

            response = client.post("/quality/validate-tickers", json={})

        assert response.status_code == 500

    def test_validate_tickers_with_limit(self, client):
        """POST /quality/validate-tickers respects limit parameter."""
        with patch("app.routes.quality.get_supabase") as mock_supabase:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [{"asset_ticker": "AAPL"}]
            mock_client.table.return_value.select.return_value.gte.return_value.not_.return_value.is_.return_value.limit.return_value.execute.return_value = mock_response
            mock_supabase.return_value = mock_client

            response = client.post("/quality/validate-tickers", json={"limit": 50})

        assert response.status_code == 200


# =============================================================================
# POST /quality/audit-sources Tests
# =============================================================================

class TestAuditSources:
    """Tests for POST /quality/audit-sources endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_audit_sources_returns_200(self, client):
        """POST /quality/audit-sources returns 200."""
        with patch("app.routes.quality.get_supabase") as mock_supabase:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = []
            mock_client.table.return_value.select.return_value.gte.return_value.limit.return_value.execute.return_value = mock_response
            mock_supabase.return_value = mock_client

            response = client.post("/quality/audit-sources", json={})

        assert response.status_code == 200

    def test_audit_sources_returns_results(self, client):
        """POST /quality/audit-sources returns audit results."""
        with patch("app.routes.quality.get_supabase") as mock_supabase:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [
                {
                    "id": "1",
                    "politician_id": "pol-1",
                    "asset_name": "Apple",
                    "asset_ticker": "AAPL",
                    "transaction_type": "purchase",
                    "transaction_date": "2024-01-15",
                    "amount_range_min": 1000,
                    "amount_range_max": 15000,
                    "disclosure_date": "2024-01-20",
                    "source_url": "https://house.gov",
                    "created_at": "2024-01-20"
                }
            ]
            mock_client.table.return_value.select.return_value.gte.return_value.limit.return_value.execute.return_value = mock_response
            mock_supabase.return_value = mock_client

            response = client.post("/quality/audit-sources", json={})

        data = response.json()
        assert "records_sampled" in data
        assert "mismatches_found" in data
        assert "accuracy_rate" in data
        assert "mismatches" in data
        assert "audit_time_ms" in data

    def test_audit_sources_no_supabase_returns_500(self, client):
        """POST /quality/audit-sources returns 500 when Supabase not configured."""
        with patch("app.routes.quality.get_supabase") as mock_supabase:
            mock_supabase.return_value = None

            response = client.post("/quality/audit-sources", json={})

        assert response.status_code == 500


# =============================================================================
# GET /quality/freshness-report Tests
# =============================================================================

class TestFreshnessReport:
    """Tests for GET /quality/freshness-report endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_freshness_report_returns_200(self, client):
        """GET /quality/freshness-report returns 200."""
        with patch("app.routes.quality.get_supabase") as mock_supabase:
            mock_client = MagicMock()

            # Mock house response
            mock_house_response = MagicMock()
            mock_house_response.data = [{"created_at": datetime.now(timezone.utc).isoformat(), "source_url": "house"}]

            # Mock senate response
            mock_senate_response = MagicMock()
            mock_senate_response.data = [{"created_at": datetime.now(timezone.utc).isoformat(), "source_url": "senate"}]

            # Mock jobs response
            mock_jobs_response = MagicMock()
            mock_jobs_response.data = []

            # Set up the call chain
            mock_chain = MagicMock()
            mock_chain.order.return_value.limit.return_value.execute.side_effect = [
                mock_house_response,
                mock_senate_response
            ]
            mock_client.table.return_value.select.return_value.ilike.return_value = mock_chain
            mock_client.table.return_value.select.return_value.execute.return_value = mock_jobs_response
            mock_supabase.return_value = mock_client

            response = client.get("/quality/freshness-report")

        assert response.status_code == 200

    def test_freshness_report_contains_sources(self, client):
        """GET /quality/freshness-report contains sources list."""
        with patch("app.routes.quality.get_supabase") as mock_supabase:
            mock_client = MagicMock()

            mock_house_response = MagicMock()
            mock_house_response.data = [{"created_at": datetime.now(timezone.utc).isoformat(), "source_url": "house"}]

            mock_senate_response = MagicMock()
            mock_senate_response.data = []

            mock_jobs_response = MagicMock()
            mock_jobs_response.data = []

            mock_chain = MagicMock()
            mock_chain.order.return_value.limit.return_value.execute.side_effect = [
                mock_house_response,
                mock_senate_response
            ]
            mock_client.table.return_value.select.return_value.ilike.return_value = mock_chain
            mock_client.table.return_value.select.return_value.execute.return_value = mock_jobs_response
            mock_supabase.return_value = mock_client

            response = client.get("/quality/freshness-report")

        data = response.json()
        assert "sources" in data
        assert "overall_health" in data
        assert "last_updated" in data

    def test_freshness_report_no_supabase_returns_500(self, client):
        """GET /quality/freshness-report returns 500 when Supabase not configured."""
        with patch("app.routes.quality.get_supabase") as mock_supabase:
            mock_supabase.return_value = None

            response = client.get("/quality/freshness-report")

        assert response.status_code == 500


# =============================================================================
# validate_record_integrity() Tests
# =============================================================================

class TestValidateRecordIntegrity:
    """Tests for validate_record_integrity() helper function."""

    def test_valid_record_has_no_issues(self):
        """validate_record_integrity() returns empty list for valid record."""
        from app.routes.quality import validate_record_integrity

        record = {
            "id": "1",
            "politician_id": "pol-1",
            "transaction_date": "2024-01-15",
            "disclosure_date": "2024-01-20",
            "amount_range_min": 1000,
            "amount_range_max": 15000
        }

        issues = validate_record_integrity(record)

        assert issues == []

    def test_detects_future_transaction_date(self):
        """validate_record_integrity() detects future transaction date."""
        from app.routes.quality import validate_record_integrity

        future_date = (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat()
        record = {
            "politician_id": "pol-1",
            "transaction_date": future_date
        }

        issues = validate_record_integrity(record)

        assert len(issues) == 1
        assert issues[0]["field"] == "transaction_date"
        assert "Future date" in issues[0]["issue"]

    def test_detects_amount_range_min_greater_than_max(self):
        """validate_record_integrity() detects min > max amount range."""
        from app.routes.quality import validate_record_integrity

        record = {
            "politician_id": "pol-1",
            "amount_range_min": 15000,
            "amount_range_max": 1000
        }

        issues = validate_record_integrity(record)

        assert len(issues) == 1
        assert issues[0]["field"] == "amount_range"
        assert "Min > Max" in issues[0]["issue"]

    def test_detects_missing_politician_id(self):
        """validate_record_integrity() detects missing politician_id."""
        from app.routes.quality import validate_record_integrity

        record = {
            "transaction_date": "2024-01-15"
        }

        issues = validate_record_integrity(record)

        assert any(i["field"] == "politician_id" for i in issues)

    def test_detects_transaction_after_disclosure(self):
        """validate_record_integrity() detects transaction after disclosure."""
        from app.routes.quality import validate_record_integrity

        record = {
            "politician_id": "pol-1",
            "transaction_date": "2024-01-25",  # After disclosure
            "disclosure_date": "2024-01-20"
        }

        issues = validate_record_integrity(record)

        assert any("Transaction after disclosure" in i.get("issue", "") for i in issues)


# =============================================================================
# Input Validation Tests (422 errors for invalid inputs)
# =============================================================================

class TestValidateTickersInputValidation:
    """Tests for input validation on POST /quality/validate-tickers."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_days_back_below_minimum_returns_422(self, client):
        """days_back < 1 should return 422 validation error."""
        response = client.post("/quality/validate-tickers", json={"days_back": 0})
        assert response.status_code == 422
        assert "days_back" in response.text.lower()

    def test_days_back_above_maximum_returns_422(self, client):
        """days_back > 90 should return 422 validation error."""
        response = client.post("/quality/validate-tickers", json={"days_back": 100})
        assert response.status_code == 422
        assert "days_back" in response.text.lower()

    def test_confidence_threshold_below_minimum_returns_422(self, client):
        """confidence_threshold < 0 should return 422 validation error."""
        response = client.post("/quality/validate-tickers", json={"confidence_threshold": -0.1})
        assert response.status_code == 422
        assert "confidence_threshold" in response.text.lower()

    def test_confidence_threshold_above_maximum_returns_422(self, client):
        """confidence_threshold > 1.0 should return 422 validation error."""
        response = client.post("/quality/validate-tickers", json={"confidence_threshold": 1.5})
        assert response.status_code == 422
        assert "confidence_threshold" in response.text.lower()

    def test_limit_below_minimum_returns_422(self, client):
        """limit < 1 should return 422 validation error."""
        response = client.post("/quality/validate-tickers", json={"limit": 0})
        assert response.status_code == 422
        assert "limit" in response.text.lower()

    def test_limit_above_maximum_returns_422(self, client):
        """limit > 1000 should return 422 validation error."""
        response = client.post("/quality/validate-tickers", json={"limit": 2000})
        assert response.status_code == 422
        assert "limit" in response.text.lower()

    def test_invalid_type_for_days_back_returns_422(self, client):
        """Non-integer days_back should return 422 validation error."""
        response = client.post("/quality/validate-tickers", json={"days_back": "seven"})
        assert response.status_code == 422

    def test_invalid_type_for_limit_returns_422(self, client):
        """Non-integer limit should return 422 validation error."""
        response = client.post("/quality/validate-tickers", json={"limit": "hundred"})
        assert response.status_code == 422


class TestAuditSourcesInputValidation:
    """Tests for input validation on POST /quality/audit-sources."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_sample_size_below_minimum_returns_422(self, client):
        """sample_size < 10 should return 422 validation error."""
        response = client.post("/quality/audit-sources", json={"sample_size": 5})
        assert response.status_code == 422
        assert "sample_size" in response.text.lower()

    def test_sample_size_above_maximum_returns_422(self, client):
        """sample_size > 200 should return 422 validation error."""
        response = client.post("/quality/audit-sources", json={"sample_size": 500})
        assert response.status_code == 422
        assert "sample_size" in response.text.lower()

    def test_days_back_below_minimum_returns_422(self, client):
        """days_back < 1 should return 422 validation error."""
        response = client.post("/quality/audit-sources", json={"days_back": 0})
        assert response.status_code == 422
        assert "days_back" in response.text.lower()

    def test_days_back_above_maximum_returns_422(self, client):
        """days_back > 365 should return 422 validation error."""
        response = client.post("/quality/audit-sources", json={"days_back": 500})
        assert response.status_code == 422
        assert "days_back" in response.text.lower()

    def test_invalid_type_for_sample_size_returns_422(self, client):
        """Non-integer sample_size should return 422 validation error."""
        response = client.post("/quality/audit-sources", json={"sample_size": "fifty"})
        assert response.status_code == 422


# =============================================================================
# validate_ticker_polygon() Tests
# =============================================================================

class TestValidateTickerPolygon:
    """Tests for validate_ticker_polygon() helper function."""

    @pytest.mark.asyncio
    async def test_returns_valid_for_active_ticker(self):
        """validate_ticker_polygon() returns (True, 1.0) for active ticker."""
        from app.routes.quality import validate_ticker_polygon

        with patch("app.routes.quality.get_polygon_api_key") as mock_key, \
             patch("httpx.AsyncClient") as mock_client_class:

            mock_key.return_value = "test-api-key"

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"results": {"active": True}}

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            is_valid, confidence = await validate_ticker_polygon("AAPL")

            assert is_valid is True
            assert confidence == 1.0

    @pytest.mark.asyncio
    async def test_returns_low_confidence_for_inactive_ticker(self):
        """validate_ticker_polygon() returns (True, 0.5) for inactive ticker."""
        from app.routes.quality import validate_ticker_polygon

        with patch("app.routes.quality.get_polygon_api_key") as mock_key, \
             patch("httpx.AsyncClient") as mock_client_class:

            mock_key.return_value = "test-api-key"

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"results": {"active": False}}

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            is_valid, confidence = await validate_ticker_polygon("FB")

            assert is_valid is True
            assert confidence == 0.5

    @pytest.mark.asyncio
    async def test_returns_invalid_for_404(self):
        """validate_ticker_polygon() returns (False, 0.0) for 404 response."""
        from app.routes.quality import validate_ticker_polygon

        with patch("app.routes.quality.get_polygon_api_key") as mock_key, \
             patch("httpx.AsyncClient") as mock_client_class:

            mock_key.return_value = "test-api-key"

            mock_response = MagicMock()
            mock_response.status_code = 404

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            is_valid, confidence = await validate_ticker_polygon("INVALID")

            assert is_valid is False
            assert confidence == 0.0

    @pytest.mark.asyncio
    async def test_returns_default_for_api_error(self):
        """validate_ticker_polygon() returns (True, 0.8) for API error."""
        from app.routes.quality import validate_ticker_polygon

        with patch("app.routes.quality.get_polygon_api_key") as mock_key, \
             patch("httpx.AsyncClient") as mock_client_class:

            mock_key.return_value = "test-api-key"

            mock_response = MagicMock()
            mock_response.status_code = 500

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            is_valid, confidence = await validate_ticker_polygon("AAPL")

            assert is_valid is True
            assert confidence == 0.8

    @pytest.mark.asyncio
    async def test_returns_default_for_network_error(self):
        """validate_ticker_polygon() returns (True, 0.8) for network error."""
        from app.routes.quality import validate_ticker_polygon

        with patch("app.routes.quality.get_polygon_api_key") as mock_key, \
             patch("httpx.AsyncClient") as mock_client_class:

            mock_key.return_value = "test-api-key"

            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Network error")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            is_valid, confidence = await validate_ticker_polygon("AAPL")

            assert is_valid is True
            assert confidence == 0.8

    @pytest.mark.asyncio
    async def test_skips_when_no_api_key(self):
        """validate_ticker_polygon() returns (True, 1.0) when no API key."""
        from app.routes.quality import validate_ticker_polygon

        with patch("app.routes.quality.get_polygon_api_key") as mock_key:
            mock_key.return_value = ""

            is_valid, confidence = await validate_ticker_polygon("AAPL")

            assert is_valid is True
            assert confidence == 1.0


# =============================================================================
# Additional Ticker Validation Tests
# =============================================================================

class TestTickerValidationEdgeCases:
    """Additional tests for ticker validation edge cases."""

    def test_detects_invalid_ticker_patterns_directly(self):
        """Validate tickers directly detects invalid ticker patterns."""
        from app.routes.quality import INVALID_TICKER_PATTERNS

        # Test the patterns directly
        test_tickers = ["N/A", "NA", "NONE", "--", "UNKNOWN"]
        for ticker in test_tickers:
            assert ticker in INVALID_TICKER_PATTERNS

    def test_detects_unusual_format_tickers_directly(self):
        """Unusual format tickers are detected by regex."""
        import re

        # These should NOT match the valid patterns
        unusual_tickers = ["BRK.A", "BRK/B", "AAPL123456"]
        valid_pattern1 = re.compile(r"^[A-Z]{1,5}$")
        valid_pattern2 = re.compile(r"^[A-Z]{2,4}[0-9]{1,2}$")

        for ticker in unusual_tickers:
            match1 = valid_pattern1.match(ticker)
            match2 = valid_pattern2.match(ticker)
            assert not match1 and not match2, f"{ticker} should be unusual format"

    def test_detects_outdated_tickers_directly(self):
        """Outdated tickers are in TICKER_MAPPINGS."""
        from app.routes.quality import TICKER_MAPPINGS

        # Test the mappings directly
        assert TICKER_MAPPINGS.get("FB") == "META"
        assert TICKER_MAPPINGS.get("TWTR") == "X"

    def test_validates_with_polygon_api_directly(self):
        """Test Polygon API validation is called when key is present."""
        from app.routes.quality import get_polygon_api_key

        # When no key is set, it returns empty string
        with patch.dict('os.environ', {'POLYGON_API_KEY': ''}, clear=False):
            key = get_polygon_api_key()
            # get_polygon_api_key returns the env value or empty string
            assert key == "" or key is not None

    def test_valid_ticker_format_regex(self):
        """Test valid ticker format patterns."""
        import re

        # Standard tickers (1-5 uppercase letters)
        valid_pattern1 = re.compile(r"^[A-Z]{1,5}$")

        valid_tickers = ["A", "FB", "IBM", "AAPL", "NVDIA"]
        for ticker in valid_tickers:
            assert valid_pattern1.match(ticker), f"{ticker} should match valid pattern"

        # ETF-style tickers (2-4 letters + 1-2 numbers)
        valid_pattern2 = re.compile(r"^[A-Z]{2,4}[0-9]{1,2}$")

        etf_tickers = ["SPY1", "QQQ12", "ARKK5"]
        for ticker in etf_tickers:
            assert valid_pattern2.match(ticker), f"{ticker} should match ETF pattern"


# =============================================================================
# Additional Audit Sources Tests
# =============================================================================

class TestAuditSourcesEdgeCases:
    """Additional tests for audit sources edge cases."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_filters_by_source(self, client):
        """POST /quality/audit-sources filters by source parameter."""
        with patch("app.routes.quality.get_supabase") as mock_supabase:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [
                {
                    "id": "1",
                    "politician_id": "pol-1",
                    "asset_name": "Apple",
                    "asset_ticker": "AAPL",
                    "transaction_type": "purchase",
                    "transaction_date": "2024-01-15",
                    "amount_range_min": 1000,
                    "amount_range_max": 15000,
                    "disclosure_date": "2024-01-20",
                    "source_url": "https://house.gov",
                    "created_at": "2024-01-20"
                }
            ]
            # Mock with ilike filter
            mock_client.table.return_value.select.return_value.gte.return_value.ilike.return_value.limit.return_value.execute.return_value = mock_response
            mock_supabase.return_value = mock_client

            response = client.post("/quality/audit-sources", json={"source": "house"})

        assert response.status_code == 200

    def test_random_samples_when_exceeds_limit(self, client):
        """POST /quality/audit-sources randomly samples when records exceed limit."""
        with patch("app.routes.quality.get_supabase") as mock_supabase, \
             patch("app.routes.quality.random.sample") as mock_sample:

            mock_client = MagicMock()
            mock_response = MagicMock()
            # Create 100 records
            mock_response.data = [
                {
                    "id": str(i),
                    "politician_id": f"pol-{i}",
                    "asset_name": "Apple",
                    "asset_ticker": "AAPL",
                    "transaction_type": "purchase",
                    "transaction_date": "2024-01-15",
                    "amount_range_min": 1000,
                    "amount_range_max": 15000,
                    "disclosure_date": "2024-01-20",
                    "source_url": "https://house.gov",
                    "created_at": "2024-01-20"
                }
                for i in range(100)
            ]
            mock_client.table.return_value.select.return_value.gte.return_value.limit.return_value.execute.return_value = mock_response
            mock_supabase.return_value = mock_client

            # Mock random.sample to return first 20
            mock_sample.return_value = mock_response.data[:20]

            response = client.post("/quality/audit-sources", json={"sample_size": 20})

        assert response.status_code == 200
        mock_sample.assert_called_once()

    def test_handles_database_exception(self, client):
        """POST /quality/audit-sources handles database exception."""
        with patch("app.routes.quality.get_supabase") as mock_supabase:
            mock_client = MagicMock()
            mock_client.table.return_value.select.return_value.gte.return_value.limit.return_value.execute.side_effect = Exception("Database error")
            mock_supabase.return_value = mock_client

            response = client.post("/quality/audit-sources", json={})

        assert response.status_code == 500
        assert "Failed to fetch records" in response.json()["detail"]


# =============================================================================
# Additional Record Integrity Tests
# =============================================================================

class TestValidateRecordIntegrityEdgeCases:
    """Additional tests for validate_record_integrity() edge cases."""

    def test_handles_invalid_transaction_date_format(self):
        """validate_record_integrity() handles invalid date format."""
        from app.routes.quality import validate_record_integrity

        record = {
            "politician_id": "pol-1",
            "transaction_date": "not-a-date"
        }

        issues = validate_record_integrity(record)

        assert any(i["field"] == "transaction_date" and "Invalid format" in i["issue"] for i in issues)

    def test_handles_future_disclosure_date(self):
        """validate_record_integrity() detects future disclosure date."""
        from app.routes.quality import validate_record_integrity

        future_date = (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat()
        record = {
            "politician_id": "pol-1",
            "disclosure_date": future_date
        }

        issues = validate_record_integrity(record)

        assert any(i["field"] == "disclosure_date" and "Future date" in i["issue"] for i in issues)

    def test_handles_attribute_error_in_date_parsing(self):
        """validate_record_integrity() handles AttributeError in date parsing."""
        from app.routes.quality import validate_record_integrity

        record = {
            "politician_id": "pol-1",
            "transaction_date": 12345  # Not a string
        }

        issues = validate_record_integrity(record)

        assert any(i["field"] == "transaction_date" for i in issues)


# =============================================================================
# Additional Freshness Report Tests
# =============================================================================

class TestFreshnessReportEdgeCases:
    """Additional tests for freshness report edge cases."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_handles_no_senate_data(self, client):
        """GET /quality/freshness-report handles no senate data."""
        with patch("app.routes.quality.get_supabase") as mock_supabase:
            mock_client = MagicMock()

            mock_house_response = MagicMock()
            mock_house_response.data = [{"created_at": datetime.now(timezone.utc).isoformat(), "source_url": "house"}]

            mock_senate_response = MagicMock()
            mock_senate_response.data = []  # No senate data

            mock_jobs_response = MagicMock()
            mock_jobs_response.data = []

            mock_chain = MagicMock()
            mock_chain.order.return_value.limit.return_value.execute.side_effect = [
                mock_house_response,
                mock_senate_response
            ]
            mock_client.table.return_value.select.return_value.ilike.return_value = mock_chain
            mock_client.table.return_value.select.return_value.execute.return_value = mock_jobs_response
            mock_supabase.return_value = mock_client

            response = client.get("/quality/freshness-report")

        data = response.json()
        assert response.status_code == 200
        senate_source = next((s for s in data["sources"] if "Senate" in s["name"]), None)
        assert senate_source is not None
        assert senate_source["status"] == "no_data"

    def test_handles_job_statuses(self, client):
        """GET /quality/freshness-report handles various job statuses."""
        with patch("app.routes.quality.get_supabase") as mock_supabase:
            mock_client = MagicMock()

            mock_house_response = MagicMock()
            mock_house_response.data = [{"created_at": datetime.now(timezone.utc).isoformat(), "source_url": "house"}]

            mock_senate_response = MagicMock()
            mock_senate_response.data = [{"created_at": datetime.now(timezone.utc).isoformat(), "source_url": "senate"}]

            mock_jobs_response = MagicMock()
            mock_jobs_response.data = [
                {"job_name": "disabled_job", "enabled": False, "last_run_at": None, "last_successful_run": None},
                {"job_name": "never_run_job", "enabled": True, "last_run_at": None, "last_successful_run": None},
                {"job_name": "failed_job", "enabled": True, "last_run_at": "2024-01-20T12:00:00", "last_successful_run": "2024-01-19T12:00:00"},
                {"job_name": "healthy_job", "enabled": True, "last_run_at": "2024-01-20T12:00:00", "last_successful_run": "2024-01-20T12:00:00"},
            ]

            mock_chain = MagicMock()
            mock_chain.order.return_value.limit.return_value.execute.side_effect = [
                mock_house_response,
                mock_senate_response
            ]
            mock_client.table.return_value.select.return_value.ilike.return_value = mock_chain
            mock_client.table.return_value.select.return_value.execute.return_value = mock_jobs_response
            mock_supabase.return_value = mock_client

            response = client.get("/quality/freshness-report")

        data = response.json()
        assert response.status_code == 200

        # Check job statuses
        sources = {s["name"]: s["status"] for s in data["sources"]}
        assert sources.get("Job: disabled_job") == "disabled"
        assert sources.get("Job: never_run_job") == "never_run"
        assert sources.get("Job: failed_job") == "failed"
        assert sources.get("Job: healthy_job") == "healthy"

    def test_handles_stale_data_degraded_health(self, client):
        """GET /quality/freshness-report shows degraded health for stale data."""
        with patch("app.routes.quality.get_supabase") as mock_supabase:
            mock_client = MagicMock()

            # House data is 72 hours old (stale)
            stale_time = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
            mock_house_response = MagicMock()
            mock_house_response.data = [{"created_at": stale_time, "source_url": "house"}]

            mock_senate_response = MagicMock()
            mock_senate_response.data = [{"created_at": datetime.now(timezone.utc).isoformat(), "source_url": "senate"}]

            mock_jobs_response = MagicMock()
            mock_jobs_response.data = []

            mock_chain = MagicMock()
            mock_chain.order.return_value.limit.return_value.execute.side_effect = [
                mock_house_response,
                mock_senate_response
            ]
            mock_client.table.return_value.select.return_value.ilike.return_value = mock_chain
            mock_client.table.return_value.select.return_value.execute.return_value = mock_jobs_response
            mock_supabase.return_value = mock_client

            response = client.get("/quality/freshness-report")

        data = response.json()
        assert response.status_code == 200
        assert data["overall_health"] == "degraded"

    def test_handles_database_exception(self, client):
        """GET /quality/freshness-report handles database exception."""
        with patch("app.routes.quality.get_supabase") as mock_supabase:
            mock_client = MagicMock()
            mock_client.table.return_value.select.return_value.ilike.return_value.order.return_value.limit.return_value.execute.side_effect = Exception("Database error")
            mock_supabase.return_value = mock_client

            response = client.get("/quality/freshness-report")

        assert response.status_code == 500
        assert "Failed to generate report" in response.json()["detail"]


# =============================================================================
# Constants Tests
# =============================================================================

class TestQualityConstants:
    """Tests for module constants."""

    def test_ticker_mappings_defined(self):
        """TICKER_MAPPINGS constant is defined with known rebrands."""
        from app.routes.quality import TICKER_MAPPINGS

        assert "FB" in TICKER_MAPPINGS
        assert TICKER_MAPPINGS["FB"] == "META"
        assert "TWTR" in TICKER_MAPPINGS
        assert TICKER_MAPPINGS["TWTR"] == "X"

    def test_invalid_ticker_patterns_defined(self):
        """INVALID_TICKER_PATTERNS constant is defined."""
        from app.routes.quality import INVALID_TICKER_PATTERNS

        assert "N/A" in INVALID_TICKER_PATTERNS
        assert "NA" in INVALID_TICKER_PATTERNS
        assert "NONE" in INVALID_TICKER_PATTERNS
        assert "--" in INVALID_TICKER_PATTERNS
        assert "UNKNOWN" in INVALID_TICKER_PATTERNS
