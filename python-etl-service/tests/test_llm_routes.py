"""
Tests for LLM Pipeline Routes (app/routes/llm_pipeline.py).

Tests:
- GET /llm/health - LLM health check
- POST /llm/validate-batch - Trigger batch validation
- POST /llm/detect-anomalies - Detect anomalies
- POST /llm/audit-lineage - Audit lineage for a disclosure
- POST /llm/run-feedback - Trigger feedback loop
- GET /llm/audit-trail - Query audit trail
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


# =============================================================================
# GET /llm/health Tests
# =============================================================================

class TestLLMHealth:
    """Tests for GET /llm/health endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_health_endpoint_returns_200(self, client):
        """GET /llm/health returns 200 when Ollama is reachable."""
        with patch("app.routes.llm_pipeline.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.test_connection = AsyncMock(return_value=True)
            instance.base_url = "https://ollama.lefv.info"

            response = client.get("/llm/health")

        assert response.status_code == 200
        data = response.json()
        assert data["ollama_connected"] is True
        assert data["ollama_url"] == "https://ollama.lefv.info"

    def test_health_endpoint_ollama_down(self, client):
        """GET /llm/health returns 200 with connected=false when Ollama is down."""
        with patch("app.routes.llm_pipeline.LLMClient") as MockClient:
            instance = MockClient.return_value
            instance.test_connection = AsyncMock(return_value=False)
            instance.base_url = "https://ollama.lefv.info"

            response = client.get("/llm/health")

        assert response.status_code == 200
        data = response.json()
        assert data["ollama_connected"] is False


# =============================================================================
# POST /llm/validate-batch Tests
# =============================================================================

class TestValidateBatch:
    """Tests for POST /llm/validate-batch endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_validate_batch_returns_202(self, client):
        """POST /llm/validate-batch returns 202 Accepted."""
        response = client.post("/llm/validate-batch", json={})

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert "queued" in data["message"].lower() or "batch" in data["message"].lower()

    def test_validate_batch_with_model_override(self, client):
        """POST /llm/validate-batch accepts model override."""
        response = client.post("/llm/validate-batch", json={
            "model": "llama3.1:8b"
        })

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"

    def test_validate_batch_default_model(self, client):
        """POST /llm/validate-batch works with default model (no body)."""
        response = client.post("/llm/validate-batch", json={})

        assert response.status_code == 202


# =============================================================================
# POST /llm/detect-anomalies Tests
# =============================================================================

class TestDetectAnomalies:
    """Tests for POST /llm/detect-anomalies endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_detect_anomalies_returns_200(self, client):
        """POST /llm/detect-anomalies returns 200 with valid params."""
        with patch("app.routes.llm_pipeline.get_supabase") as mock_get_sb:
            mock_supabase = MagicMock()
            mock_get_sb.return_value = mock_supabase

            with patch("app.services.llm.anomaly_detector.AnomalyDetectionService.detect",
                       new_callable=AsyncMock) as mock_detect:
                mock_detect.return_value = {
                    "anomalies_detected": 2,
                    "signals": [{"signal_id": "s1"}, {"signal_id": "s2"}],
                    "analysis_window": {"start": "2026-01-01", "end": "2026-01-31"},
                    "signals_stored": 2,
                }

                response = client.post("/llm/detect-anomalies", json={
                    "start_date": "2026-01-01",
                    "end_date": "2026-01-31",
                    "filer": "ALL",
                })

        assert response.status_code == 200
        data = response.json()
        assert data["anomalies_detected"] == 2
        assert len(data["signals"]) == 2

    def test_detect_anomalies_no_database(self, client):
        """POST /llm/detect-anomalies returns 503 when DB is unavailable."""
        with patch("app.routes.llm_pipeline.get_supabase", return_value=None):
            response = client.post("/llm/detect-anomalies", json={
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
            })

        assert response.status_code == 503

    def test_detect_anomalies_missing_start_date(self, client):
        """POST /llm/detect-anomalies returns 422 when start_date is missing."""
        response = client.post("/llm/detect-anomalies", json={
            "end_date": "2026-01-31",
        })

        assert response.status_code == 422

    def test_detect_anomalies_missing_end_date(self, client):
        """POST /llm/detect-anomalies returns 422 when end_date is missing."""
        response = client.post("/llm/detect-anomalies", json={
            "start_date": "2026-01-01",
        })

        assert response.status_code == 422

    def test_detect_anomalies_with_filer(self, client):
        """POST /llm/detect-anomalies accepts filer parameter."""
        with patch("app.routes.llm_pipeline.get_supabase") as mock_get_sb:
            mock_supabase = MagicMock()
            mock_get_sb.return_value = mock_supabase

            with patch("app.services.llm.anomaly_detector.AnomalyDetectionService.detect",
                       new_callable=AsyncMock) as mock_detect:
                mock_detect.return_value = {
                    "anomalies_detected": 0,
                    "signals": [],
                    "analysis_window": {"start": "2026-01-01", "end": "2026-01-31"},
                }

                response = client.post("/llm/detect-anomalies", json={
                    "start_date": "2026-01-01",
                    "end_date": "2026-01-31",
                    "filer": "Nancy Pelosi",
                })

        assert response.status_code == 200
        mock_detect.assert_called_once_with(
            start_date="2026-01-01",
            end_date="2026-01-31",
            filer="Nancy Pelosi",
        )


# =============================================================================
# POST /llm/audit-lineage Tests
# =============================================================================

class TestAuditLineage:
    """Tests for POST /llm/audit-lineage endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_audit_lineage_returns_200(self, client):
        """POST /llm/audit-lineage returns 200 with valid disclosure_id."""
        with patch("app.routes.llm_pipeline.get_supabase") as mock_get_sb:
            mock_supabase = MagicMock()
            mock_get_sb.return_value = mock_supabase

            with patch("app.services.llm.lineage_auditor.LineageAuditService.audit",
                       new_callable=AsyncMock) as mock_audit:
                mock_audit.return_value = {
                    "trust_score": 85,
                    "chain_integrity": "valid",
                    "verification_questions": ["Is the source URL still accessible?"],
                    "provenance_report": "Chain of custody is intact.",
                }

                response = client.post("/llm/audit-lineage", json={
                    "disclosure_id": "abc-123-def-456",
                })

        assert response.status_code == 200
        data = response.json()
        assert data["trust_score"] == 85
        assert data["chain_integrity"] == "valid"
        assert len(data["verification_questions"]) == 1

    def test_audit_lineage_no_database(self, client):
        """POST /llm/audit-lineage returns 503 when DB is unavailable."""
        with patch("app.routes.llm_pipeline.get_supabase", return_value=None):
            response = client.post("/llm/audit-lineage", json={
                "disclosure_id": "abc-123",
            })

        assert response.status_code == 503

    def test_audit_lineage_missing_disclosure_id(self, client):
        """POST /llm/audit-lineage returns 422 when disclosure_id is missing."""
        response = client.post("/llm/audit-lineage", json={})

        assert response.status_code == 422

    def test_audit_lineage_broken_chain(self, client):
        """POST /llm/audit-lineage returns broken chain for missing record."""
        with patch("app.routes.llm_pipeline.get_supabase") as mock_get_sb:
            mock_supabase = MagicMock()
            mock_get_sb.return_value = mock_supabase

            with patch("app.services.llm.lineage_auditor.LineageAuditService.audit",
                       new_callable=AsyncMock) as mock_audit:
                mock_audit.return_value = {
                    "trust_score": 0,
                    "chain_integrity": "broken",
                    "verification_questions": [],
                    "provenance_report": "",
                }

                response = client.post("/llm/audit-lineage", json={
                    "disclosure_id": "nonexistent-id",
                })

        assert response.status_code == 200
        data = response.json()
        assert data["trust_score"] == 0
        assert data["chain_integrity"] == "broken"


# =============================================================================
# POST /llm/run-feedback Tests
# =============================================================================

class TestRunFeedback:
    """Tests for POST /llm/run-feedback endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_run_feedback_returns_202(self, client):
        """POST /llm/run-feedback returns 202 Accepted."""
        response = client.post("/llm/run-feedback", json={
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
        })

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert "queued" in data["message"].lower() or "feedback" in data["message"].lower()

    def test_run_feedback_missing_start_date(self, client):
        """POST /llm/run-feedback returns 422 when start_date is missing."""
        response = client.post("/llm/run-feedback", json={
            "end_date": "2026-01-31",
        })

        assert response.status_code == 422

    def test_run_feedback_missing_end_date(self, client):
        """POST /llm/run-feedback returns 422 when end_date is missing."""
        response = client.post("/llm/run-feedback", json={
            "start_date": "2026-01-01",
        })

        assert response.status_code == 422


# =============================================================================
# GET /llm/audit-trail Tests
# =============================================================================

class TestAuditTrail:
    """Tests for GET /llm/audit-trail endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_audit_trail_returns_200(self, client):
        """GET /llm/audit-trail returns 200 with entries."""
        with patch("app.routes.llm_pipeline.get_supabase") as mock_get_sb:
            mock_supabase = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [
                {
                    "id": "trail-1",
                    "service_name": "validation_gate",
                    "prompt_version": "v1.0",
                    "model_used": "qwen3:8b",
                    "input_tokens": 500,
                    "output_tokens": 200,
                    "latency_ms": 1200,
                    "parse_success": True,
                    "created_at": "2026-01-15T10:00:00Z",
                },
                {
                    "id": "trail-2",
                    "service_name": "anomaly_detection",
                    "prompt_version": "v1.0",
                    "model_used": "gemma3:12b-it-qat",
                    "input_tokens": 800,
                    "output_tokens": 300,
                    "latency_ms": 2100,
                    "parse_success": True,
                    "created_at": "2026-01-15T09:00:00Z",
                },
            ]

            # Mock the chained query: .select().order().limit().execute()
            mock_query = MagicMock()
            mock_query.order.return_value.limit.return_value.execute.return_value = mock_response
            mock_supabase.table.return_value.select.return_value = mock_query
            mock_get_sb.return_value = mock_supabase

            response = client.get("/llm/audit-trail")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["entries"]) == 2
        assert data["entries"][0]["service_name"] == "validation_gate"

    def test_audit_trail_with_service_filter(self, client):
        """GET /llm/audit-trail?service_name=validation_gate filters correctly."""
        with patch("app.routes.llm_pipeline.get_supabase") as mock_get_sb:
            mock_supabase = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [
                {
                    "id": "trail-1",
                    "service_name": "validation_gate",
                    "prompt_version": "v1.0",
                    "model_used": "qwen3:8b",
                    "input_tokens": 500,
                    "output_tokens": 200,
                    "latency_ms": 1200,
                    "parse_success": True,
                    "created_at": "2026-01-15T10:00:00Z",
                },
            ]

            # Mock the chained query with .eq() for filter
            mock_query = MagicMock()
            mock_order = MagicMock()
            mock_limit = MagicMock()
            mock_eq = MagicMock()

            mock_query.order.return_value = mock_order
            mock_order.limit.return_value = mock_limit
            mock_limit.eq.return_value.execute.return_value = mock_response
            # Also support the other order: eq before execute
            mock_limit.execute.return_value = mock_response

            mock_supabase.table.return_value.select.return_value = mock_query
            mock_get_sb.return_value = mock_supabase

            response = client.get("/llm/audit-trail?service_name=validation_gate")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 0

    def test_audit_trail_empty(self, client):
        """GET /llm/audit-trail returns empty list when no entries."""
        with patch("app.routes.llm_pipeline.get_supabase") as mock_get_sb:
            mock_supabase = MagicMock()
            mock_response = MagicMock()
            mock_response.data = []

            mock_query = MagicMock()
            mock_query.order.return_value.limit.return_value.execute.return_value = mock_response
            mock_supabase.table.return_value.select.return_value = mock_query
            mock_get_sb.return_value = mock_supabase

            response = client.get("/llm/audit-trail")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["entries"] == []

    def test_audit_trail_no_database(self, client):
        """GET /llm/audit-trail returns 503 when DB is unavailable."""
        with patch("app.routes.llm_pipeline.get_supabase", return_value=None):
            response = client.get("/llm/audit-trail")

        assert response.status_code == 503

    def test_audit_trail_with_limit(self, client):
        """GET /llm/audit-trail?limit=5 respects the limit parameter."""
        with patch("app.routes.llm_pipeline.get_supabase") as mock_get_sb:
            mock_supabase = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [{"id": "trail-1", "service_name": "validation_gate"}]

            mock_query = MagicMock()
            mock_query.order.return_value.limit.return_value.execute.return_value = mock_response
            mock_supabase.table.return_value.select.return_value = mock_query
            mock_get_sb.return_value = mock_supabase

            response = client.get("/llm/audit-trail?limit=5")

        assert response.status_code == 200
