"""
Tests for Health Routes (app/routes/health.py).

Tests:
- GET /health - Health check endpoint
"""

import pytest
from fastapi.testclient import TestClient


# =============================================================================
# Health Route Tests
# =============================================================================

class TestHealthRoutes:
    """Tests for health check routes."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_health_returns_200(self, client):
        """GET /health returns 200 status."""
        response = client.get("/health")

        assert response.status_code == 200

    def test_health_returns_healthy_status(self, client):
        """GET /health returns healthy status."""
        response = client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"

    def test_health_is_json(self, client):
        """GET /health returns JSON content type."""
        response = client.get("/health")

        assert "application/json" in response.headers["content-type"]
