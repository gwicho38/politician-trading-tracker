"""
Tests for Enrichment Routes (app/routes/enrichment.py).

Tests:
- POST /enrichment/trigger - Trigger party enrichment
- GET /enrichment/status/{job_id} - Get job status
- GET /enrichment/preview - Preview politicians needing enrichment
- POST /enrichment/name/trigger - Trigger name enrichment
- GET /enrichment/name/status/{job_id} - Get name enrichment status
- GET /enrichment/name/preview - Preview placeholder names
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient


# =============================================================================
# POST /enrichment/trigger Tests
# =============================================================================

class TestTriggerEnrichment:
    """Tests for POST /enrichment/trigger endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client with mocked background tasks."""
        from app.main import app
        with patch("app.routes.enrichment.run_job_in_background") as mock_run:
            mock_run.return_value = None
            yield TestClient(app, raise_server_exceptions=False)

    def test_trigger_returns_200(self, client):
        """POST /enrichment/trigger returns 200."""
        response = client.post("/enrichment/trigger", json={})

        assert response.status_code == 200

    def test_trigger_returns_job_id(self, client):
        """POST /enrichment/trigger returns job ID."""
        response = client.post("/enrichment/trigger", json={})
        data = response.json()

        assert "job_id" in data
        assert len(data["job_id"]) == 8  # Short UUID

    def test_trigger_returns_started_status(self, client):
        """POST /enrichment/trigger returns started status."""
        response = client.post("/enrichment/trigger", json={})
        data = response.json()

        assert data["status"] == "started"

    def test_trigger_with_limit(self, client):
        """POST /enrichment/trigger with limit parameter."""
        response = client.post("/enrichment/trigger", json={"limit": 50})
        data = response.json()

        assert response.status_code == 200
        assert "50" in data["message"]


# =============================================================================
# GET /enrichment/status/{job_id} Tests
# =============================================================================

class TestGetEnrichmentStatus:
    """Tests for GET /enrichment/status/{job_id} endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client with mocked background tasks."""
        from app.main import app
        with patch("app.routes.enrichment.run_job_in_background") as mock_run:
            mock_run.return_value = None
            yield TestClient(app, raise_server_exceptions=False)

    def test_status_for_existing_job(self, client):
        """GET /enrichment/status/{job_id} returns status for existing job."""
        # First trigger a job
        trigger_response = client.post("/enrichment/trigger", json={})
        job_id = trigger_response.json()["job_id"]

        # Then check status
        response = client.get(f"/enrichment/status/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert "status" in data

    def test_status_for_nonexistent_job_returns_404(self):
        """GET /enrichment/status/{job_id} returns 404 for nonexistent job."""
        from app.main import app
        client = TestClient(app)
        response = client.get("/enrichment/status/nonexistent-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


# =============================================================================
# GET /enrichment/preview Tests
# =============================================================================

class TestPreviewEnrichment:
    """Tests for GET /enrichment/preview endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_preview_returns_200(self, client):
        """GET /enrichment/preview returns 200."""
        with patch("app.services.party_enrichment.get_supabase") as mock_supabase:
            mock_client = MagicMock()
            mock_count_response = MagicMock()
            mock_count_response.count = 10
            mock_sample_response = MagicMock()
            mock_sample_response.data = [{"id": "1", "full_name": "Test"}]

            # Chain mock for both queries
            mock_client.table.return_value.select.return_value.is_.return_value.limit.return_value.execute.side_effect = [
                mock_count_response,
                mock_sample_response
            ]
            mock_supabase.return_value = mock_client

            response = client.get("/enrichment/preview")

        assert response.status_code == 200

    def test_preview_returns_count_and_sample(self, client):
        """GET /enrichment/preview returns total count and sample."""
        with patch("app.services.party_enrichment.get_supabase") as mock_supabase:
            mock_client = MagicMock()
            mock_count_response = MagicMock()
            mock_count_response.count = 25

            mock_sample_response = MagicMock()
            mock_sample_response.data = [
                {"id": "1", "full_name": "Test Person", "state": "CA", "chamber": "House"}
            ]

            # Chain mock for both queries
            mock_client.table.return_value.select.return_value.is_.return_value.limit.return_value.execute.side_effect = [
                mock_count_response,
                mock_sample_response
            ]
            mock_supabase.return_value = mock_client

            response = client.get("/enrichment/preview")

        data = response.json()
        assert "total_missing_party" in data
        assert "sample" in data


# =============================================================================
# POST /enrichment/name/trigger Tests
# =============================================================================

class TestTriggerNameEnrichment:
    """Tests for POST /enrichment/name/trigger endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client with mocked background tasks."""
        from app.main import app
        with patch("app.routes.enrichment.run_name_job_in_background") as mock_run:
            mock_run.return_value = None
            yield TestClient(app, raise_server_exceptions=False)

    def test_trigger_returns_200(self, client):
        """POST /enrichment/name/trigger returns 200."""
        response = client.post("/enrichment/name/trigger", json={})

        assert response.status_code == 200

    def test_trigger_returns_job_id(self, client):
        """POST /enrichment/name/trigger returns job ID."""
        response = client.post("/enrichment/name/trigger", json={})
        data = response.json()

        assert "job_id" in data

    def test_trigger_returns_started_status(self, client):
        """POST /enrichment/name/trigger returns started status."""
        response = client.post("/enrichment/name/trigger", json={})
        data = response.json()

        assert data["status"] == "started"


# =============================================================================
# GET /enrichment/name/status/{job_id} Tests
# =============================================================================

class TestGetNameEnrichmentStatus:
    """Tests for GET /enrichment/name/status/{job_id} endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client with mocked background tasks."""
        from app.main import app
        with patch("app.routes.enrichment.run_name_job_in_background") as mock_run:
            mock_run.return_value = None
            yield TestClient(app, raise_server_exceptions=False)

    def test_status_for_existing_job(self, client):
        """GET /enrichment/name/status/{job_id} returns status for existing job."""
        # First trigger a job
        trigger_response = client.post("/enrichment/name/trigger", json={})
        job_id = trigger_response.json()["job_id"]

        # Then check status
        response = client.get(f"/enrichment/name/status/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id

    def test_status_for_nonexistent_job_returns_404(self):
        """GET /enrichment/name/status/{job_id} returns 404 for nonexistent job."""
        from app.main import app
        client = TestClient(app)
        response = client.get("/enrichment/name/status/nonexistent-id")

        assert response.status_code == 404


# =============================================================================
# GET /enrichment/name/preview Tests
# =============================================================================

class TestPreviewNameEnrichment:
    """Tests for GET /enrichment/name/preview endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_preview_returns_200(self, client):
        """GET /enrichment/name/preview returns 200."""
        with patch("app.services.party_enrichment.get_supabase") as mock_supabase:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = []

            mock_client.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value = mock_response
            mock_supabase.return_value = mock_client

            response = client.get("/enrichment/name/preview")

        assert response.status_code == 200

    def test_preview_returns_placeholder_count(self, client):
        """GET /enrichment/name/preview returns placeholder count."""
        with patch("app.services.party_enrichment.get_supabase") as mock_supabase:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [
                {"id": "1", "full_name": "House Member (Placeholder)", "party": None}
            ]

            mock_client.table.return_value.select.return_value.ilike.return_value.limit.return_value.execute.return_value = mock_response
            mock_supabase.return_value = mock_client

            response = client.get("/enrichment/name/preview")

        data = response.json()
        assert "total_placeholder_names" in data
        assert "sample" in data
