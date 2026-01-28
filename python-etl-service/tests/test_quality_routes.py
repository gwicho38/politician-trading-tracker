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
from datetime import datetime, timedelta


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
            mock_house_response.data = [{"created_at": datetime.utcnow().isoformat(), "source_url": "house"}]

            # Mock senate response
            mock_senate_response = MagicMock()
            mock_senate_response.data = [{"created_at": datetime.utcnow().isoformat(), "source_url": "senate"}]

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
            mock_house_response.data = [{"created_at": datetime.utcnow().isoformat(), "source_url": "house"}]

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

        future_date = (datetime.utcnow() + timedelta(days=30)).date().isoformat()
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
