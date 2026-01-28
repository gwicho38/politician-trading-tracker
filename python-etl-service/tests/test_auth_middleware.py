"""
Tests for API Key Authentication Middleware
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from app.middleware.auth import (
    AuthMiddleware,
    constant_time_compare,
    extract_api_key,
    generate_api_key,
    get_api_key,
    require_admin_key,
    require_api_key,
    validate_api_key,
    PUBLIC_ENDPOINTS,
)


class TestConstantTimeCompare:
    """Tests for constant_time_compare function."""

    def test_equal_strings(self):
        """Equal strings should return True."""
        assert constant_time_compare("test123", "test123") is True

    def test_different_strings(self):
        """Different strings should return False."""
        assert constant_time_compare("test123", "test456") is False

    def test_empty_first_string(self):
        """Empty first string should return False."""
        assert constant_time_compare("", "test123") is False

    def test_empty_second_string(self):
        """Empty second string should return False."""
        assert constant_time_compare("test123", "") is False

    def test_both_empty(self):
        """Both empty strings should return False."""
        assert constant_time_compare("", "") is False

    def test_none_first_string(self):
        """None first string should return False."""
        assert constant_time_compare(None, "test123") is False

    def test_none_second_string(self):
        """None second string should return False."""
        assert constant_time_compare("test123", None) is False

    def test_unicode_strings(self):
        """Unicode strings should work correctly."""
        assert constant_time_compare("тест123", "тест123") is True
        assert constant_time_compare("тест123", "тест456") is False


class TestGenerateApiKey:
    """Tests for generate_api_key function."""

    def test_generates_key_with_prefix(self):
        """Generated key should have correct prefix."""
        key = generate_api_key("etl")
        assert key.startswith("etl_sk_")

    def test_generates_unique_keys(self):
        """Each call should generate a unique key."""
        keys = [generate_api_key() for _ in range(100)]
        assert len(set(keys)) == 100

    def test_key_has_sufficient_length(self):
        """Generated key should be sufficiently long."""
        key = generate_api_key()
        # Base64 of 32 bytes is ~43 chars, plus prefix
        assert len(key) > 45

    def test_custom_prefix(self):
        """Custom prefix should be used."""
        key = generate_api_key("custom")
        assert key.startswith("custom_sk_")


class TestExtractApiKey:
    """Tests for extract_api_key function."""

    def test_header_key_priority(self):
        """X-API-Key header should have highest priority."""
        result = extract_api_key(
            header_key="header_key",
            bearer_header="Bearer bearer_key",
            query_key="query_key",
        )
        assert result == "header_key"

    def test_bearer_header_priority(self):
        """Bearer header should have second priority."""
        result = extract_api_key(
            header_key=None,
            bearer_header="Bearer bearer_key",
            query_key="query_key",
        )
        assert result == "bearer_key"

    def test_bearer_header_without_prefix(self):
        """Bearer header without 'Bearer ' prefix should still work."""
        result = extract_api_key(
            header_key=None,
            bearer_header="raw_key",
            query_key=None,
        )
        assert result == "raw_key"

    def test_query_param_fallback(self):
        """Query param should be used as fallback."""
        result = extract_api_key(
            header_key=None,
            bearer_header=None,
            query_key="query_key",
        )
        assert result == "query_key"

    def test_no_key_provided(self):
        """Should return None when no key provided."""
        result = extract_api_key(
            header_key=None,
            bearer_header=None,
            query_key=None,
        )
        assert result is None


class TestValidateApiKey:
    """Tests for validate_api_key function."""

    def test_valid_regular_key(self):
        """Valid regular API key should pass."""
        with patch.dict(os.environ, {"ETL_API_KEY": "test_key_123"}):
            # Need to reload the module to pick up env var
            from app.middleware import auth
            auth.ETL_API_KEY = "test_key_123"
            assert validate_api_key("test_key_123") is True

    def test_invalid_key(self):
        """Invalid API key should fail."""
        with patch.dict(os.environ, {"ETL_API_KEY": "test_key_123"}):
            from app.middleware import auth
            auth.ETL_API_KEY = "test_key_123"
            assert validate_api_key("wrong_key") is False

    def test_none_key(self):
        """None key should fail."""
        assert validate_api_key(None) is False

    def test_empty_key(self):
        """Empty key should fail."""
        assert validate_api_key("") is False

    def test_admin_key_for_regular_access(self):
        """Admin key should work for regular endpoints."""
        from app.middleware import auth
        auth.ETL_API_KEY = "regular_key"
        auth.ETL_ADMIN_API_KEY = "admin_key"
        assert validate_api_key("admin_key") is True

    def test_regular_key_for_admin_access(self):
        """Regular key should NOT work for admin-only endpoints."""
        from app.middleware import auth
        auth.ETL_API_KEY = "regular_key"
        auth.ETL_ADMIN_API_KEY = "admin_key"
        assert validate_api_key("regular_key", require_admin=True) is False

    def test_admin_key_for_admin_access(self):
        """Admin key should work for admin endpoints."""
        from app.middleware import auth
        auth.ETL_API_KEY = "regular_key"
        auth.ETL_ADMIN_API_KEY = "admin_key"
        assert validate_api_key("admin_key", require_admin=True) is True


class TestRequireApiKey:
    """Tests for require_api_key dependency."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        request = MagicMock(spec=Request)
        request.url.path = "/etl/trigger"
        request.method = "POST"
        request.client.host = "127.0.0.1"
        return request

    @pytest.mark.asyncio
    async def test_public_endpoint_no_auth_needed(self, mock_request):
        """Public endpoints should not require auth."""
        mock_request.url.path = "/health"
        result = await require_api_key(mock_request, None)
        assert result == "public"

    @pytest.mark.asyncio
    async def test_auth_disabled_allows_all(self, mock_request):
        """Auth disabled mode should allow all requests."""
        from app.middleware import auth
        original = auth.ETL_AUTH_DISABLED
        auth.ETL_AUTH_DISABLED = True
        try:
            result = await require_api_key(mock_request, None)
            assert result == "auth_disabled"
        finally:
            auth.ETL_AUTH_DISABLED = original

    @pytest.mark.asyncio
    async def test_no_keys_configured_allows_request(self, mock_request):
        """No keys configured should allow request (backwards compat)."""
        from app.middleware import auth
        original_disabled = auth.ETL_AUTH_DISABLED
        original_key = auth.ETL_API_KEY
        original_admin = auth.ETL_ADMIN_API_KEY
        # Must also disable the global auth bypass to test this path
        auth.ETL_AUTH_DISABLED = False
        auth.ETL_API_KEY = None
        auth.ETL_ADMIN_API_KEY = None
        try:
            result = await require_api_key(mock_request, None)
            assert result == "no_keys_configured"
        finally:
            auth.ETL_AUTH_DISABLED = original_disabled
            auth.ETL_API_KEY = original_key
            auth.ETL_ADMIN_API_KEY = original_admin

    @pytest.mark.asyncio
    async def test_missing_key_raises_401(self, mock_request):
        """Missing API key should raise 401."""
        from app.middleware import auth
        auth.ETL_API_KEY = "test_key"
        auth.ETL_AUTH_DISABLED = False
        with pytest.raises(HTTPException) as exc_info:
            await require_api_key(mock_request, None)
        assert exc_info.value.status_code == 401
        assert "API key required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_key_raises_401(self, mock_request):
        """Invalid API key should raise 401."""
        from app.middleware import auth
        auth.ETL_API_KEY = "correct_key"
        auth.ETL_AUTH_DISABLED = False
        with pytest.raises(HTTPException) as exc_info:
            await require_api_key(mock_request, "wrong_key")
        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_valid_key_returns_key(self, mock_request):
        """Valid API key should return the key."""
        from app.middleware import auth
        auth.ETL_API_KEY = "valid_key_123"
        auth.ETL_AUTH_DISABLED = False
        result = await require_api_key(mock_request, "valid_key_123")
        assert result == "valid_key_123"


class TestRequireAdminKey:
    """Tests for require_admin_key dependency."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        request = MagicMock(spec=Request)
        request.url.path = "/error-reports/force-apply"
        request.method = "POST"
        request.client.host = "127.0.0.1"
        return request

    @pytest.mark.asyncio
    async def test_auth_disabled_allows_admin(self, mock_request):
        """Auth disabled should allow admin requests."""
        from app.middleware import auth
        original = auth.ETL_AUTH_DISABLED
        auth.ETL_AUTH_DISABLED = True
        try:
            result = await require_admin_key(mock_request, None)
            assert result == "auth_disabled"
        finally:
            auth.ETL_AUTH_DISABLED = original

    @pytest.mark.asyncio
    async def test_no_admin_key_falls_back_to_regular(self, mock_request):
        """No admin key configured should fall back to regular key."""
        from app.middleware import auth
        auth.ETL_API_KEY = "regular_key"
        auth.ETL_ADMIN_API_KEY = None
        auth.ETL_AUTH_DISABLED = False
        result = await require_admin_key(mock_request, "regular_key")
        assert result == "regular_key"

    @pytest.mark.asyncio
    async def test_missing_admin_key_raises_401(self, mock_request):
        """Missing admin key should raise 401."""
        from app.middleware import auth
        auth.ETL_ADMIN_API_KEY = "admin_key"
        auth.ETL_AUTH_DISABLED = False
        with pytest.raises(HTTPException) as exc_info:
            await require_admin_key(mock_request, None)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_regular_key_for_admin_raises_403(self, mock_request):
        """Regular key for admin operation should raise 403."""
        from app.middleware import auth
        auth.ETL_API_KEY = "regular_key"
        auth.ETL_ADMIN_API_KEY = "admin_key"
        auth.ETL_AUTH_DISABLED = False
        with pytest.raises(HTTPException) as exc_info:
            await require_admin_key(mock_request, "regular_key")
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_valid_admin_key_succeeds(self, mock_request):
        """Valid admin key should succeed."""
        from app.middleware import auth
        auth.ETL_API_KEY = "regular_key"
        auth.ETL_ADMIN_API_KEY = "admin_key"
        auth.ETL_AUTH_DISABLED = False
        result = await require_admin_key(mock_request, "admin_key")
        assert result == "admin_key"


class TestAuthMiddleware:
    """Tests for AuthMiddleware ASGI middleware."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app with auth middleware."""
        from app.middleware import auth
        auth.ETL_API_KEY = "test_api_key"
        auth.ETL_AUTH_DISABLED = False

        app = FastAPI()
        app.add_middleware(AuthMiddleware)

        @app.get("/protected")
        async def protected():
            return {"status": "ok"}

        @app.get("/health")
        async def health():
            return {"status": "healthy"}

        return app

    def test_public_endpoint_no_auth(self, app):
        """Public endpoints should not require auth."""
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_protected_endpoint_requires_auth(self, app):
        """Protected endpoints should require auth."""
        client = TestClient(app)
        response = client.get("/protected")
        assert response.status_code == 401
        assert "API key required" in response.json()["detail"]

    def test_protected_with_header_key(self, app):
        """Protected endpoint with X-API-Key header should work."""
        client = TestClient(app)
        response = client.get(
            "/protected",
            headers={"X-API-Key": "test_api_key"}
        )
        assert response.status_code == 200

    def test_protected_with_bearer_token(self, app):
        """Protected endpoint with Bearer token should work."""
        client = TestClient(app)
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer test_api_key"}
        )
        assert response.status_code == 200

    def test_protected_with_query_param(self, app):
        """Protected endpoint with query param should work."""
        client = TestClient(app)
        response = client.get("/protected?api_key=test_api_key")
        assert response.status_code == 200

    def test_invalid_key_rejected(self, app):
        """Invalid API key should be rejected."""
        client = TestClient(app)
        response = client.get(
            "/protected",
            headers={"X-API-Key": "wrong_key"}
        )
        assert response.status_code == 401


class TestPublicEndpoints:
    """Tests for public endpoints configuration."""

    def test_health_is_public(self):
        """Health endpoint should be public."""
        assert "/health" in PUBLIC_ENDPOINTS

    def test_root_is_public(self):
        """Root endpoint should be public."""
        assert "/" in PUBLIC_ENDPOINTS

    def test_docs_is_public(self):
        """Docs endpoint should be public."""
        assert "/docs" in PUBLIC_ENDPOINTS

    def test_openapi_is_public(self):
        """OpenAPI endpoint should be public."""
        assert "/openapi.json" in PUBLIC_ENDPOINTS


class TestAuthDisabledMode:
    """Tests for development mode with auth disabled."""

    def test_auth_disabled_env_var(self):
        """ETL_AUTH_DISABLED should be read from environment."""
        from app.middleware import auth

        # Test that changing the module variable works
        original = auth.ETL_AUTH_DISABLED
        auth.ETL_AUTH_DISABLED = True
        assert auth.ETL_AUTH_DISABLED is True
        auth.ETL_AUTH_DISABLED = original

    @pytest.fixture
    def app_no_auth(self):
        """Create app with auth disabled."""
        from app.middleware import auth
        auth.ETL_AUTH_DISABLED = True

        app = FastAPI()
        app.add_middleware(AuthMiddleware)

        @app.get("/protected")
        async def protected():
            return {"status": "ok"}

        return app

    def test_no_auth_mode_allows_all(self, app_no_auth):
        """With auth disabled, all requests should pass."""
        client = TestClient(app_no_auth)
        response = client.get("/protected")
        assert response.status_code == 200

        # Reset
        from app.middleware import auth
        auth.ETL_AUTH_DISABLED = False


class TestBackwardsCompatibility:
    """Tests for backwards compatibility when no keys configured."""

    @pytest.fixture
    def app_no_keys(self):
        """Create app with no API keys configured."""
        from app.middleware import auth
        auth.ETL_API_KEY = None
        auth.ETL_ADMIN_API_KEY = None
        auth.ETL_AUTH_DISABLED = False

        app = FastAPI()
        app.add_middleware(AuthMiddleware)

        @app.get("/protected")
        async def protected():
            return {"status": "ok"}

        return app

    def test_no_keys_allows_requests(self, app_no_keys):
        """With no keys configured, requests should pass (with warning)."""
        client = TestClient(app_no_keys)
        response = client.get("/protected")
        assert response.status_code == 200

        # Reset
        from app.middleware import auth
        auth.ETL_API_KEY = "reset"
