"""
Tests for Dedup Routes (app/routes/dedup.py).

Tests:
- GET /dedup/preview - Preview duplicate groups
- POST /dedup/process - Process and merge duplicates
- GET /dedup/health - Check dedup service health
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


# =============================================================================
# GET /dedup/preview Tests
# =============================================================================

class TestPreviewDuplicates:
    """Tests for GET /dedup/preview endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_preview_returns_200(self, client):
        """GET /dedup/preview returns 200."""
        with patch("app.routes.dedup.PoliticianDeduplicator") as mock_dedup:
            mock_instance = MagicMock()
            mock_instance.preview.return_value = {
                "duplicate_groups": 0,
                "total_duplicates": 0,
                "groups": []
            }
            mock_dedup.return_value = mock_instance

            response = client.get("/dedup/preview")

        assert response.status_code == 200

    def test_preview_returns_groups(self, client):
        """GET /dedup/preview returns duplicate groups."""
        with patch("app.routes.dedup.PoliticianDeduplicator") as mock_dedup:
            mock_instance = MagicMock()
            mock_instance.preview.return_value = {
                "duplicate_groups": 2,
                "total_duplicates": 4,
                "groups": [
                    {"normalized_name": "john smith", "records": [], "disclosures_to_update": 5}
                ]
            }
            mock_dedup.return_value = mock_instance

            response = client.get("/dedup/preview")

        data = response.json()
        assert "duplicate_groups" in data
        assert "total_duplicates" in data
        assert "groups" in data

    def test_preview_with_limit(self, client):
        """GET /dedup/preview respects limit parameter."""
        with patch("app.routes.dedup.PoliticianDeduplicator") as mock_dedup:
            mock_instance = MagicMock()
            mock_instance.preview.return_value = {"duplicate_groups": 0, "total_duplicates": 0, "groups": []}
            mock_dedup.return_value = mock_instance

            response = client.get("/dedup/preview?limit=5")

        mock_instance.preview.assert_called_with(5)
        assert response.status_code == 200


# =============================================================================
# POST /dedup/process Tests
# =============================================================================

class TestProcessDuplicates:
    """Tests for POST /dedup/process endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_process_returns_200(self, client):
        """POST /dedup/process returns 200."""
        with patch("app.routes.dedup.PoliticianDeduplicator") as mock_dedup:
            mock_instance = MagicMock()
            mock_instance.process_all.return_value = {
                "processed": 0,
                "merged": 0,
                "disclosures_updated": 0,
                "errors": 0,
                "dry_run": False,
                "results": []
            }
            mock_dedup.return_value = mock_instance

            response = client.post("/dedup/process", json={})

        assert response.status_code == 200

    def test_process_with_dry_run(self, client):
        """POST /dedup/process with dry_run returns preview."""
        with patch("app.routes.dedup.PoliticianDeduplicator") as mock_dedup:
            mock_instance = MagicMock()
            mock_instance.process_all.return_value = {
                "processed": 5,
                "merged": 5,
                "disclosures_updated": 0,
                "errors": 0,
                "dry_run": True,
                "results": []
            }
            mock_dedup.return_value = mock_instance

            response = client.post("/dedup/process", json={"dry_run": True})

        data = response.json()
        assert data["dry_run"] is True
        mock_instance.process_all.assert_called_with(50, True)

    def test_process_with_limit(self, client):
        """POST /dedup/process respects limit parameter."""
        with patch("app.routes.dedup.PoliticianDeduplicator") as mock_dedup:
            mock_instance = MagicMock()
            mock_instance.process_all.return_value = {
                "processed": 10,
                "merged": 10,
                "disclosures_updated": 25,
                "errors": 0,
                "dry_run": False,
                "results": []
            }
            mock_dedup.return_value = mock_instance

            response = client.post("/dedup/process", json={"limit": 10})

        mock_instance.process_all.assert_called_with(10, False)
        assert response.status_code == 200

    def test_process_returns_statistics(self, client):
        """POST /dedup/process returns processing statistics."""
        with patch("app.routes.dedup.PoliticianDeduplicator") as mock_dedup:
            mock_instance = MagicMock()
            mock_instance.process_all.return_value = {
                "processed": 10,
                "merged": 8,
                "disclosures_updated": 25,
                "errors": 2,
                "dry_run": False,
                "results": []
            }
            mock_dedup.return_value = mock_instance

            response = client.post("/dedup/process", json={})

        data = response.json()
        assert data["processed"] == 10
        assert data["merged"] == 8
        assert data["disclosures_updated"] == 25
        assert data["errors"] == 2


# =============================================================================
# GET /dedup/health Tests
# =============================================================================

class TestDedupHealth:
    """Tests for GET /dedup/health endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_health_returns_200(self, client):
        """GET /dedup/health returns 200."""
        with patch("app.routes.dedup.PoliticianDeduplicator") as mock_dedup:
            mock_instance = MagicMock()
            mock_instance.supabase = MagicMock()
            mock_dedup.return_value = mock_instance

            response = client.get("/dedup/health")

        assert response.status_code == 200

    def test_health_returns_healthy_with_db(self, client):
        """GET /dedup/health returns healthy when database connected."""
        with patch("app.routes.dedup.PoliticianDeduplicator") as mock_dedup:
            mock_instance = MagicMock()
            mock_instance.supabase = MagicMock()  # Non-None value
            mock_dedup.return_value = mock_instance

            response = client.get("/dedup/health")

        data = response.json()
        assert data["status"] == "healthy"
        assert data["database_connected"] is True

    def test_health_returns_degraded_without_db(self, client):
        """GET /dedup/health returns degraded when database not connected."""
        with patch("app.routes.dedup.PoliticianDeduplicator") as mock_dedup:
            mock_instance = MagicMock()
            mock_instance.supabase = None
            mock_dedup.return_value = mock_instance

            response = client.get("/dedup/health")

        data = response.json()
        assert data["status"] == "degraded"
        assert data["database_connected"] is False
