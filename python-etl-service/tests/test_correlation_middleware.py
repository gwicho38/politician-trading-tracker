"""
Tests for correlation ID middleware (app/middleware/correlation.py).

Tests:
- Correlation ID extraction from headers
- Correlation ID generation
- Response header injection
- Request logging
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.correlation import (
    CorrelationMiddleware,
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
)
from app.lib.logging_config import clear_correlation_id


# =============================================================================
# Test App Setup
# =============================================================================

def create_test_app():
    """Create a minimal FastAPI app with correlation middleware."""
    app = FastAPI()
    app.add_middleware(CorrelationMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    @app.get("/error")
    async def error_endpoint():
        raise ValueError("Test error")

    return app


# =============================================================================
# Middleware Tests
# =============================================================================

class TestCorrelationMiddleware:
    """Tests for CorrelationMiddleware."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_test_app()
        return TestClient(app, raise_server_exceptions=False)

    def setup_method(self):
        clear_correlation_id()

    def teardown_method(self):
        clear_correlation_id()

    def test_generates_correlation_id_when_missing(self, client):
        """Middleware generates correlation ID when not in request."""
        response = client.get("/test")

        assert response.status_code == 200
        assert CORRELATION_ID_HEADER in response.headers
        # Should be a valid UUID format
        cid = response.headers[CORRELATION_ID_HEADER]
        assert len(cid) == 36

    def test_uses_provided_correlation_id(self, client):
        """Middleware uses correlation ID from X-Correlation-ID header."""
        response = client.get(
            "/test",
            headers={CORRELATION_ID_HEADER: "custom-correlation-123"}
        )

        assert response.status_code == 200
        assert response.headers[CORRELATION_ID_HEADER] == "custom-correlation-123"

    def test_uses_request_id_header(self, client):
        """Middleware uses X-Request-ID as fallback."""
        response = client.get(
            "/test",
            headers={REQUEST_ID_HEADER: "request-id-456"}
        )

        assert response.status_code == 200
        assert response.headers[CORRELATION_ID_HEADER] == "request-id-456"

    def test_correlation_id_header_preferred_over_request_id(self, client):
        """X-Correlation-ID takes precedence over X-Request-ID."""
        response = client.get(
            "/test",
            headers={
                CORRELATION_ID_HEADER: "correlation-preferred",
                REQUEST_ID_HEADER: "request-fallback",
            }
        )

        assert response.headers[CORRELATION_ID_HEADER] == "correlation-preferred"

    def test_error_returns_500_status(self, client):
        """Middleware allows errors to propagate with proper status code."""
        response = client.get(
            "/error",
            headers={CORRELATION_ID_HEADER: "error-request-789"}
        )

        # Error should result in 500 status
        assert response.status_code == 500

    def test_different_requests_get_different_ids(self, client):
        """Each request without ID gets a unique correlation ID."""
        response1 = client.get("/test")
        response2 = client.get("/test")

        cid1 = response1.headers[CORRELATION_ID_HEADER]
        cid2 = response2.headers[CORRELATION_ID_HEADER]

        assert cid1 != cid2
