"""
Tests for Error Reports Routes (app/routes/error_reports.py).

Tests:
- POST /error-reports/process - Process pending error reports
- POST /error-reports/process-one - Process single error report
- GET /error-reports/stats - Get error report statistics
- GET /error-reports/needs-review - Get reports needing review
- POST /error-reports/force-apply - Force apply correction (admin-only)
- POST /error-reports/reanalyze - Reanalyze a report (admin-only)
- POST /error-reports/generate-suggestion - Generate suggestion
- GET /error-reports/health - Check Ollama health
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


# =============================================================================
# Admin Authentication Tests
# =============================================================================

class TestErrorReportsAdminProtection:
    """Tests for admin-only endpoint protection."""

    @pytest.fixture
    def client_with_auth(self, enable_auth):
        """Create a test client with auth enabled."""
        from app.main import app
        return TestClient(app), enable_auth

    def test_force_apply_requires_admin_key(self, client_with_auth):
        """POST /error-reports/force-apply requires admin API key."""
        client, auth_keys = client_with_auth

        # Request without API key should return 401
        response = client.post("/error-reports/force-apply", json={
            "report_id": "test-id",
            "corrections": [{"field": "ticker", "new_value": "AAPL"}]
        })
        assert response.status_code == 401

    def test_force_apply_accepts_admin_key(self, client_with_auth):
        """POST /error-reports/force-apply accepts admin API key."""
        client, auth_keys = client_with_auth

        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.supabase = MagicMock()

            # Mock report found
            mock_response = MagicMock()
            mock_response.data = {
                "id": "test-id",
                "disclosure_id": "disclosure-123"
            }
            mock_processor.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response
            mock_processor._apply_corrections.return_value = True
            mock_processor._update_report_status.return_value = None
            mock_processor_class.return_value = mock_processor

            response = client.post(
                "/error-reports/force-apply",
                json={
                    "report_id": "test-id",
                    "corrections": [{"field": "ticker", "new_value": "AAPL"}]
                },
                headers={"X-API-Key": auth_keys["admin_key"]}
            )

        assert response.status_code == 200

    def test_reanalyze_requires_admin_key(self, client_with_auth):
        """POST /error-reports/reanalyze requires admin API key."""
        client, auth_keys = client_with_auth

        # Request without API key should return 401
        response = client.post("/error-reports/reanalyze", json={
            "report_id": "test-id"
        })
        assert response.status_code == 401

    def test_reanalyze_accepts_admin_key(self, client_with_auth):
        """POST /error-reports/reanalyze accepts admin API key."""
        client, auth_keys = client_with_auth

        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.test_connection.return_value = True
            mock_processor.supabase = MagicMock()
            mock_processor.CONFIDENCE_THRESHOLD = 0.7

            # Mock report found
            mock_response = MagicMock()
            mock_response.data = {
                "id": "test-id",
                "status": "reviewed",
                "disclosure_id": "disclosure-123"
            }
            mock_processor.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response
            mock_processor.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

            # Mock process_report result
            mock_result = MagicMock()
            mock_result.report_id = "test-id"
            mock_result.status = "fixed"
            mock_result.corrections = []
            mock_result.admin_notes = ""
            mock_processor.process_report.return_value = mock_result

            mock_processor_class.return_value = mock_processor

            response = client.post(
                "/error-reports/reanalyze",
                json={"report_id": "test-id"},
                headers={"X-API-Key": auth_keys["admin_key"]}
            )

        assert response.status_code == 200

    def test_regular_api_key_rejected_for_force_apply(self, enable_auth):
        """POST /error-reports/force-apply rejects regular API key (requires admin)."""
        from app.main import app
        from app.middleware import auth

        # Set up different keys
        auth.ETL_API_KEY = "regular_key"
        auth.ETL_ADMIN_API_KEY = "admin_key"

        client = TestClient(app)

        # Regular key should be rejected with 403
        response = client.post(
            "/error-reports/force-apply",
            json={
                "report_id": "test-id",
                "corrections": [{"field": "ticker", "new_value": "AAPL"}]
            },
            headers={"X-API-Key": "regular_key"}
        )
        assert response.status_code == 403

    def test_regular_api_key_rejected_for_reanalyze(self, enable_auth):
        """POST /error-reports/reanalyze rejects regular API key (requires admin)."""
        from app.main import app
        from app.middleware import auth

        # Set up different keys
        auth.ETL_API_KEY = "regular_key"
        auth.ETL_ADMIN_API_KEY = "admin_key"

        client = TestClient(app)

        # Regular key should be rejected with 403
        response = client.post(
            "/error-reports/reanalyze",
            json={"report_id": "test-id"},
            headers={"X-API-Key": "regular_key"}
        )
        assert response.status_code == 403


# =============================================================================
# POST /error-reports/process Tests
# =============================================================================

class TestProcessPendingReports:
    """Tests for POST /error-reports/process endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_process_returns_200(self, client):
        """POST /error-reports/process returns 200."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.test_connection.return_value = True
            mock_processor.process_all_pending.return_value = {
                "processed": 0,
                "successful": 0,
                "errors": 0
            }
            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/process", json={})

        assert response.status_code == 200

    def test_process_returns_503_when_ollama_unavailable(self, client):
        """POST /error-reports/process returns 503 when Ollama unavailable."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.test_connection.return_value = False
            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/process", json={})

        assert response.status_code == 503
        assert "Cannot connect to Ollama" in response.json()["detail"]

    def test_process_with_limit(self, client):
        """POST /error-reports/process respects limit parameter."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.test_connection.return_value = True
            mock_processor.process_all_pending.return_value = {"processed": 5}
            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/process", json={"limit": 5})

        mock_processor.process_all_pending.assert_called_with(limit=5, dry_run=False)

    def test_process_with_dry_run(self, client):
        """POST /error-reports/process supports dry_run mode."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.test_connection.return_value = True
            mock_processor.process_all_pending.return_value = {"processed": 5}
            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/process", json={"dry_run": True})

        mock_processor.process_all_pending.assert_called_with(limit=10, dry_run=True)


# =============================================================================
# POST /error-reports/process-one Tests
# =============================================================================

class TestProcessSingleReport:
    """Tests for POST /error-reports/process-one endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_process_one_returns_404_when_not_found(self, client):
        """POST /error-reports/process-one returns 404 when report not found."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.test_connection.return_value = True
            mock_processor.supabase = MagicMock()

            mock_response = MagicMock()
            mock_response.data = None
            mock_processor.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/process-one", json={"report_id": "nonexistent"})

        assert response.status_code == 404

    def test_process_one_returns_503_when_ollama_unavailable(self, client):
        """POST /error-reports/process-one returns 503 when Ollama unavailable."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.test_connection.return_value = False
            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/process-one", json={"report_id": "test-id"})

        assert response.status_code == 503

    def test_process_one_returns_503_when_db_not_configured(self, client):
        """POST /error-reports/process-one returns 503 when DB not configured."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.test_connection.return_value = True
            mock_processor.supabase = None
            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/process-one", json={"report_id": "test-id"})

        assert response.status_code == 503


# =============================================================================
# GET /error-reports/stats Tests
# =============================================================================

class TestGetErrorReportStats:
    """Tests for GET /error-reports/stats endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_stats_returns_200(self, client):
        """GET /error-reports/stats returns 200."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.supabase = MagicMock()

            mock_response = MagicMock()
            mock_response.count = 5
            mock_processor.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
            mock_processor_class.return_value = mock_processor

            response = client.get("/error-reports/stats")

        assert response.status_code == 200

    def test_stats_returns_counts(self, client):
        """GET /error-reports/stats returns status counts."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.supabase = MagicMock()

            mock_response = MagicMock()
            mock_response.count = 10
            mock_processor.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
            mock_processor_class.return_value = mock_processor

            response = client.get("/error-reports/stats")

        data = response.json()
        assert "by_status" in data
        assert "by_type" in data
        assert "total" in data

    def test_stats_returns_503_when_db_not_configured(self, client):
        """GET /error-reports/stats returns 503 when DB not configured."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.supabase = None
            mock_processor_class.return_value = mock_processor

            response = client.get("/error-reports/stats")

        assert response.status_code == 503


# =============================================================================
# GET /error-reports/needs-review Tests
# =============================================================================

class TestGetReportsNeedingReview:
    """Tests for GET /error-reports/needs-review endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_needs_review_returns_200(self, client):
        """GET /error-reports/needs-review returns 200."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.supabase = MagicMock()

            mock_response = MagicMock()
            mock_response.data = []
            mock_processor.supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response
            mock_processor_class.return_value = mock_processor

            response = client.get("/error-reports/needs-review")

        assert response.status_code == 200

    def test_needs_review_returns_reports(self, client):
        """GET /error-reports/needs-review returns reports list."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.supabase = MagicMock()

            mock_response = MagicMock()
            mock_response.data = [
                {"id": "1", "status": "reviewed", "description": "Test"}
            ]
            mock_processor.supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response
            mock_processor_class.return_value = mock_processor

            response = client.get("/error-reports/needs-review")

        data = response.json()
        assert "count" in data
        assert "reports" in data
        assert data["count"] == 1

    def test_needs_review_returns_503_when_db_not_configured(self, client):
        """GET /error-reports/needs-review returns 503 when DB not configured."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.supabase = None
            mock_processor_class.return_value = mock_processor

            response = client.get("/error-reports/needs-review")

        assert response.status_code == 503


# =============================================================================
# POST /error-reports/force-apply Tests
# =============================================================================

class TestForceApplyCorrection:
    """Tests for POST /error-reports/force-apply endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_force_apply_returns_404_when_not_found(self, client):
        """POST /error-reports/force-apply returns 404 when report not found."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.supabase = MagicMock()

            mock_response = MagicMock()
            mock_response.data = None
            mock_processor.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response
            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/force-apply", json={
                "report_id": "nonexistent",
                "corrections": [{"field": "ticker", "new_value": "AAPL"}]
            })

        assert response.status_code == 404

    def test_force_apply_returns_503_when_db_not_configured(self, client):
        """POST /error-reports/force-apply returns 503 when DB not configured."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.supabase = None
            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/force-apply", json={
                "report_id": "test-id",
                "corrections": [{"field": "ticker", "new_value": "AAPL"}]
            })

        assert response.status_code == 503


# =============================================================================
# GET /error-reports/health Tests
# =============================================================================

class TestCheckOllamaHealth:
    """Tests for GET /error-reports/health endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_health_returns_200(self, client):
        """GET /error-reports/health returns 200."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.test_connection.return_value = True
            mock_processor.ollama_client = MagicMock()
            mock_processor.ollama_client.base_url = "http://localhost:11434"
            mock_processor.model = "llama3.1:8b"
            mock_processor_class.return_value = mock_processor

            response = client.get("/error-reports/health")

        assert response.status_code == 200

    def test_health_returns_connection_status(self, client):
        """GET /error-reports/health returns connection status."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.test_connection.return_value = True
            mock_processor.ollama_client = MagicMock()
            mock_processor.ollama_client.base_url = "http://localhost:11434"
            mock_processor.model = "llama3.1:8b"
            mock_processor_class.return_value = mock_processor

            response = client.get("/error-reports/health")

        data = response.json()
        assert "ollama_connected" in data
        assert data["ollama_connected"] is True
        assert "model" in data

    def test_health_shows_disconnected(self, client):
        """GET /error-reports/health shows disconnected when Ollama unavailable."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.test_connection.return_value = False
            mock_processor.ollama_client = MagicMock()
            mock_processor.ollama_client.base_url = "http://localhost:11434"
            mock_processor.model = "llama3.1:8b"
            mock_processor_class.return_value = mock_processor

            response = client.get("/error-reports/health")

        data = response.json()
        assert data["ollama_connected"] is False


# =============================================================================
# POST /error-reports/process-one Extended Tests
# =============================================================================

class TestProcessSingleReportSuccess:
    """Extended tests for POST /error-reports/process-one endpoint success path."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_process_one_returns_success_with_corrections(self, client):
        """POST /error-reports/process-one returns success with corrections."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.test_connection.return_value = True
            mock_processor.supabase = MagicMock()

            # Mock report found
            mock_response = MagicMock()
            mock_response.data = {
                "id": "test-id",
                "status": "pending",
                "description": "Wrong ticker",
                "disclosure_id": "disclosure-123"
            }
            mock_processor.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

            # Mock process_report result with corrections
            from app.services.error_report_processor import CorrectionProposal, ProcessingResult
            mock_result = ProcessingResult(
                report_id="test-id",
                status="fixed",
                corrections=[
                    CorrectionProposal(
                        field="asset_ticker",
                        old_value="AAPL",
                        new_value="GOOG",
                        confidence=0.95,
                        reasoning="User specified correct ticker"
                    )
                ],
                admin_notes="Applied 1 correction"
            )
            mock_processor.process_report.return_value = mock_result
            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/process-one", json={
                "report_id": "test-id",
                "dry_run": False
            })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["report_id"] == "test-id"
        assert data["status"] == "fixed"
        assert len(data["corrections"]) == 1
        assert data["corrections"][0]["field"] == "asset_ticker"
        assert data["corrections"][0]["new_value"] == "GOOG"

    def test_process_one_handles_exception(self, client):
        """POST /error-reports/process-one handles exceptions properly."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.test_connection.return_value = True
            mock_processor.supabase = MagicMock()

            # Make the query raise an exception
            mock_processor.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("Database connection failed")
            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/process-one", json={
                "report_id": "test-id"
            })

        assert response.status_code == 500
        assert "Database connection failed" in response.json()["detail"]


# =============================================================================
# GET /error-reports/stats Exception Tests
# =============================================================================

class TestGetErrorReportStatsExceptions:
    """Exception handling tests for GET /error-reports/stats endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_stats_handles_db_exception(self, client):
        """GET /error-reports/stats handles database exceptions properly."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.supabase = MagicMock()

            # Make the query raise an exception
            mock_processor.supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("DB error")
            mock_processor_class.return_value = mock_processor

            response = client.get("/error-reports/stats")

        assert response.status_code == 500
        assert "Error fetching stats" in response.json()["detail"]


# =============================================================================
# GET /error-reports/needs-review Exception Tests
# =============================================================================

class TestGetReportsNeedingReviewExceptions:
    """Exception handling tests for GET /error-reports/needs-review endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_needs_review_handles_db_exception(self, client):
        """GET /error-reports/needs-review handles database exceptions properly."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.supabase = MagicMock()

            # Make the query raise an exception
            mock_processor.supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.side_effect = Exception("Connection timeout")
            mock_processor_class.return_value = mock_processor

            response = client.get("/error-reports/needs-review")

        assert response.status_code == 500


# =============================================================================
# POST /error-reports/force-apply Extended Tests
# =============================================================================

class TestForceApplyCorrectionExtended:
    """Extended tests for POST /error-reports/force-apply endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_force_apply_returns_400_when_no_disclosure_id(self, client):
        """POST /error-reports/force-apply returns 400 when report has no disclosure_id."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.supabase = MagicMock()

            # Mock report found but without disclosure_id
            mock_response = MagicMock()
            mock_response.data = {
                "id": "test-id",
                "disclosure_id": None  # No disclosure_id
            }
            mock_processor.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response
            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/force-apply", json={
                "report_id": "test-id",
                "corrections": [{"field": "ticker", "new_value": "AAPL"}]
            })

        assert response.status_code == 400
        assert "no disclosure_id" in response.json()["detail"]

    def test_force_apply_returns_500_when_apply_fails(self, client):
        """POST /error-reports/force-apply returns 500 when correction application fails."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.supabase = MagicMock()

            # Mock report found
            mock_response = MagicMock()
            mock_response.data = {
                "id": "test-id",
                "disclosure_id": "disclosure-123"
            }
            mock_processor.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response
            mock_processor._apply_corrections.return_value = False  # Application fails
            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/force-apply", json={
                "report_id": "test-id",
                "corrections": [{"field": "ticker", "new_value": "AAPL"}]
            })

        assert response.status_code == 500
        assert "Failed to apply corrections" in response.json()["detail"]

    def test_force_apply_handles_exception(self, client):
        """POST /error-reports/force-apply handles exceptions properly."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.supabase = MagicMock()

            # Mock report found
            mock_response = MagicMock()
            mock_response.data = {
                "id": "test-id",
                "disclosure_id": "disclosure-123"
            }
            mock_processor.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response
            mock_processor._apply_corrections.side_effect = Exception("Unexpected error")
            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/force-apply", json={
                "report_id": "test-id",
                "corrections": [{"field": "ticker", "new_value": "AAPL"}]
            })

        assert response.status_code == 500


# =============================================================================
# POST /error-reports/reanalyze Extended Tests
# =============================================================================

class TestReanalyzeReportExtended:
    """Extended tests for POST /error-reports/reanalyze endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_reanalyze_returns_503_when_ollama_unavailable(self, client):
        """POST /error-reports/reanalyze returns 503 when Ollama unavailable."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.test_connection.return_value = False
            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/reanalyze", json={
                "report_id": "test-id"
            })

        assert response.status_code == 503
        assert "Cannot connect to Ollama" in response.json()["detail"]

    def test_reanalyze_returns_503_when_db_not_configured(self, client):
        """POST /error-reports/reanalyze returns 503 when DB not configured."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.test_connection.return_value = True
            mock_processor.supabase = None
            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/reanalyze", json={
                "report_id": "test-id"
            })

        assert response.status_code == 503
        assert "Database not configured" in response.json()["detail"]

    def test_reanalyze_returns_404_when_not_found(self, client):
        """POST /error-reports/reanalyze returns 404 when report not found."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.test_connection.return_value = True
            mock_processor.supabase = MagicMock()
            mock_processor.CONFIDENCE_THRESHOLD = 0.8

            mock_response = MagicMock()
            mock_response.data = None
            mock_processor.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response
            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/reanalyze", json={
                "report_id": "nonexistent"
            })

        assert response.status_code == 404


# =============================================================================
# POST /error-reports/generate-suggestion Tests
# =============================================================================

class TestGenerateSuggestion:
    """Tests for POST /error-reports/generate-suggestion endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_generate_suggestion_returns_503_when_ollama_unavailable(self, client):
        """POST /error-reports/generate-suggestion returns 503 when Ollama unavailable."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.test_connection.return_value = False
            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/generate-suggestion", json={
                "report_id": "test-id"
            })

        assert response.status_code == 503
        assert "Cannot connect to Ollama" in response.json()["detail"]

    def test_generate_suggestion_returns_503_when_db_not_configured(self, client):
        """POST /error-reports/generate-suggestion returns 503 when DB not configured."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.test_connection.return_value = True
            mock_processor.supabase = None
            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/generate-suggestion", json={
                "report_id": "test-id"
            })

        assert response.status_code == 503
        assert "Database not configured" in response.json()["detail"]

    def test_generate_suggestion_returns_404_when_not_found(self, client):
        """POST /error-reports/generate-suggestion returns 404 when report not found."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.test_connection.return_value = True
            mock_processor.supabase = MagicMock()

            mock_response = MagicMock()
            mock_response.data = None
            mock_processor.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response
            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/generate-suggestion", json={
                "report_id": "nonexistent"
            })

        assert response.status_code == 404

    def test_generate_suggestion_returns_no_corrections(self, client):
        """POST /error-reports/generate-suggestion returns no_corrections when LLM can't determine."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.test_connection.return_value = True
            mock_processor.supabase = MagicMock()
            mock_processor.CONFIDENCE_THRESHOLD = 0.8

            # Mock report found
            mock_response = MagicMock()
            mock_response.data = {
                "id": "test-id",
                "error_type": "other",
                "description": "Something is wrong",
                "disclosure_snapshot": {
                    "politician_name": "John Doe",
                    "asset_name": "Apple Inc"
                }
            }
            mock_processor.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

            # Mock interpret_corrections returns empty
            mock_processor.interpret_corrections.return_value = []
            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/generate-suggestion", json={
                "report_id": "test-id"
            })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "no_corrections"
        assert data["corrections"] == []

    def test_generate_suggestion_returns_suggestions(self, client):
        """POST /error-reports/generate-suggestion returns suggestions successfully."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.test_connection.return_value = True
            mock_processor.supabase = MagicMock()
            mock_processor.CONFIDENCE_THRESHOLD = 0.8

            # Mock report found
            mock_response = MagicMock()
            mock_response.data = {
                "id": "test-id",
                "error_type": "wrong_ticker",
                "description": "The ticker should be GOOG not AAPL",
                "status": "pending",
                "disclosure_snapshot": {
                    "politician_name": "John Doe",
                    "asset_name": "Apple Inc"
                }
            }
            mock_processor.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

            # Mock interpret_corrections returns corrections
            from app.services.error_report_processor import CorrectionProposal
            mock_processor.interpret_corrections.return_value = [
                CorrectionProposal(
                    field="asset_ticker",
                    old_value="AAPL",
                    new_value="GOOG",
                    confidence=0.95,
                    reasoning="User clearly stated the correct ticker"
                ),
                CorrectionProposal(
                    field="asset_name",
                    old_value="Apple Inc",
                    new_value="Alphabet Inc",
                    confidence=0.7,
                    reasoning="Inferred from ticker change"
                )
            ]
            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/generate-suggestion", json={
                "report_id": "test-id",
                "model": "llama3.1:8b"
            })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "suggestions_generated"
        assert data["model"] == "llama3.1:8b"
        assert len(data["corrections"]) == 2
        # Check high confidence correction
        assert data["corrections"][0]["field"] == "asset_ticker"
        assert data["corrections"][0]["would_auto_apply"] is True
        # Check low confidence correction
        assert data["corrections"][1]["field"] == "asset_name"
        assert data["corrections"][1]["would_auto_apply"] is False
        # Check summary
        assert data["summary"]["total_suggestions"] == 2
        assert data["summary"]["high_confidence"] == 1
        assert data["summary"]["low_confidence"] == 1

    def test_generate_suggestion_handles_exception(self, client):
        """POST /error-reports/generate-suggestion handles exceptions properly."""
        with patch("app.routes.error_reports.ErrorReportProcessor") as mock_processor_class:
            mock_processor = MagicMock()
            mock_processor.test_connection.return_value = True
            mock_processor.supabase = MagicMock()

            # Mock report found
            mock_response = MagicMock()
            mock_response.data = {
                "id": "test-id",
                "error_type": "wrong_ticker",
                "description": "Wrong ticker"
            }
            mock_processor.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_response

            # Mock interpret_corrections raises exception
            mock_processor.interpret_corrections.side_effect = Exception("LLM request timeout")
            mock_processor_class.return_value = mock_processor

            response = client.post("/error-reports/generate-suggestion", json={
                "report_id": "test-id"
            })

        assert response.status_code == 500
        assert "LLM request timeout" in response.json()["detail"]


# =============================================================================
# Request Model Tests
# =============================================================================

class TestRequestModels:
    """Tests for request model defaults and validation."""

    def test_process_request_defaults(self):
        """ProcessRequest has expected defaults."""
        from app.routes.error_reports import ProcessRequest
        request = ProcessRequest()
        assert request.limit == 10
        assert request.model == "llama3.1:8b"
        assert request.dry_run is False

    def test_process_one_request_defaults(self):
        """ProcessOneRequest has expected defaults."""
        from app.routes.error_reports import ProcessOneRequest
        request = ProcessOneRequest(report_id="test-id")
        assert request.report_id == "test-id"
        assert request.model == "llama3.1:8b"
        assert request.dry_run is False

    def test_force_apply_request_structure(self):
        """ForceApplyRequest accepts corrections list."""
        from app.routes.error_reports import ForceApplyRequest
        request = ForceApplyRequest(
            report_id="test-id",
            corrections=[
                {"field": "ticker", "new_value": "AAPL"},
                {"field": "amount", "old_value": 100, "new_value": 200}
            ]
        )
        assert request.report_id == "test-id"
        assert len(request.corrections) == 2

    def test_reanalyze_request_defaults(self):
        """ReanalyzeRequest has expected defaults."""
        from app.routes.error_reports import ReanalyzeRequest
        request = ReanalyzeRequest(report_id="test-id")
        assert request.report_id == "test-id"
        assert request.model == "llama3.1:8b"
        assert request.confidence_threshold == 0.5
        assert request.dry_run is False

    def test_generate_suggestion_request_defaults(self):
        """GenerateSuggestionRequest has expected defaults."""
        from app.routes.error_reports import GenerateSuggestionRequest
        request = GenerateSuggestionRequest(report_id="test-id")
        assert request.report_id == "test-id"
        assert request.model == "llama3.1:8b"
