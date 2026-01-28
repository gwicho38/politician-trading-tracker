"""
Tests for Rate Limiting Middleware
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.middleware.rate_limit import (
    RateLimitMiddleware,
    SlidingWindowRateLimiter,
    check_rate_limit,
    get_rate_limiter,
    reset_rate_limiter,
    EXEMPT_ENDPOINTS,
    STRICT_LIMIT_ENDPOINTS,
)


class TestSlidingWindowRateLimiter:
    """Tests for the SlidingWindowRateLimiter class."""

    @pytest.fixture(autouse=True)
    def reset_limiter(self):
        """Reset the global rate limiter before each test."""
        reset_rate_limiter()
        yield
        reset_rate_limiter()

    @pytest.fixture
    def limiter(self):
        """Create a rate limiter with small limits for testing."""
        return SlidingWindowRateLimiter(
            requests_per_window=5,
            window_seconds=10,
            burst_allowance=2,
        )

    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        request = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers = {}
        request.url.path = "/test"
        return request

    def test_allows_requests_under_limit(self, limiter, mock_request):
        """Requests under the limit should be allowed."""
        # Max is 5 + 2 burst = 7
        for i in range(7):
            allowed, remaining, retry_after = limiter.check_rate_limit(mock_request)
            assert allowed is True
            assert remaining == 7 - i - 1
            assert retry_after == 0

    def test_blocks_requests_over_limit(self, limiter, mock_request):
        """Requests over the limit should be blocked."""
        # Make 7 requests (at limit)
        for _ in range(7):
            limiter.check_rate_limit(mock_request)

        # 8th request should be blocked
        allowed, remaining, retry_after = limiter.check_rate_limit(mock_request)
        assert allowed is False
        assert remaining == 0
        assert retry_after > 0

    def test_different_clients_tracked_separately(self, limiter):
        """Different client IPs should be tracked separately."""
        request1 = MagicMock()
        request1.client.host = "192.168.1.1"
        request1.headers = {}
        request1.url.path = "/test"

        request2 = MagicMock()
        request2.client.host = "192.168.1.2"
        request2.headers = {}
        request2.url.path = "/test"

        # Exhaust limit for client 1
        for _ in range(7):
            limiter.check_rate_limit(request1)

        # Client 1 should be blocked
        allowed1, _, _ = limiter.check_rate_limit(request1)
        assert allowed1 is False

        # Client 2 should still be allowed
        allowed2, _, _ = limiter.check_rate_limit(request2)
        assert allowed2 is True

    def test_uses_x_forwarded_for_header(self, limiter, mock_request):
        """Should use X-Forwarded-For header when present."""
        mock_request.headers = {"X-Forwarded-For": "10.0.0.1, 10.0.0.2"}

        client_key = limiter._get_client_key(mock_request)
        assert client_key == "10.0.0.1"

    def test_uses_x_real_ip_header(self, limiter, mock_request):
        """Should use X-Real-IP header when present."""
        mock_request.headers = {"X-Real-IP": "10.0.0.1"}

        client_key = limiter._get_client_key(mock_request)
        assert client_key == "10.0.0.1"

    def test_sliding_window_allows_after_time(self, limiter, mock_request):
        """After window expires, requests should be allowed again."""
        # Create limiter with very short window for testing
        short_limiter = SlidingWindowRateLimiter(
            requests_per_window=2,
            window_seconds=1,
            burst_allowance=0,
        )

        # Make 2 requests
        short_limiter.check_rate_limit(mock_request)
        short_limiter.check_rate_limit(mock_request)

        # Should be blocked
        allowed, _, _ = short_limiter.check_rate_limit(mock_request)
        assert allowed is False

        # Wait for window to expire
        time.sleep(1.1)

        # Should be allowed again
        allowed, _, _ = short_limiter.check_rate_limit(mock_request)
        assert allowed is True

    def test_limit_override(self, limiter, mock_request):
        """Should respect limit override parameter."""
        # With override of 2, should block after 2 requests
        limiter.check_rate_limit(mock_request, limit_override=2)
        limiter.check_rate_limit(mock_request, limit_override=2)

        allowed, _, _ = limiter.check_rate_limit(mock_request, limit_override=2)
        assert allowed is False

    def test_window_override(self, mock_request):
        """Should respect window override parameter."""
        limiter = SlidingWindowRateLimiter(
            requests_per_window=10,
            window_seconds=60,
            burst_allowance=0,
        )

        # Make 2 requests with 1 second window
        limiter.check_rate_limit(mock_request, limit_override=2, window_override=1)
        limiter.check_rate_limit(mock_request, limit_override=2, window_override=1)

        # Should be blocked
        allowed, _, _ = limiter.check_rate_limit(
            mock_request, limit_override=2, window_override=1
        )
        assert allowed is False

        # Wait for short window
        time.sleep(1.1)

        # Should be allowed
        allowed, _, _ = limiter.check_rate_limit(
            mock_request, limit_override=2, window_override=1
        )
        assert allowed is True

    def test_get_limit_for_endpoint_strict(self, limiter):
        """Should return strict limits for defined endpoints."""
        limit, window = limiter.get_limit_for_endpoint("/ml/train")
        assert limit == 5
        assert window == 3600

    def test_get_limit_for_endpoint_default(self, limiter):
        """Should return None for endpoints without strict limits."""
        limit, window = limiter.get_limit_for_endpoint("/some/other/endpoint")
        assert limit is None
        assert window is None


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    @pytest.fixture(autouse=True)
    def reset_limiter(self):
        """Reset the global rate limiter before each test."""
        reset_rate_limiter()
        yield
        reset_rate_limiter()

    @pytest.fixture
    def app_with_middleware(self):
        """Create a FastAPI app with rate limiting."""
        from app.middleware import rate_limit as rl_module

        # Enable rate limiting and set low limits for testing
        original_enabled = rl_module.RATE_LIMIT_ENABLED
        original_requests = rl_module.DEFAULT_REQUESTS_PER_WINDOW
        original_burst = rl_module.DEFAULT_BURST_ALLOWANCE

        rl_module.RATE_LIMIT_ENABLED = True

        # Reset and create new limiter with test settings
        reset_rate_limiter()
        rl_module._rate_limiter = SlidingWindowRateLimiter(
            requests_per_window=3,
            window_seconds=60,
            burst_allowance=0,
        )

        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        @app.get("/health")
        async def health():
            return {"status": "healthy"}

        yield app

        # Restore
        rl_module.RATE_LIMIT_ENABLED = original_enabled

    def test_allows_requests_under_limit(self, app_with_middleware):
        """Requests under limit should succeed."""
        client = TestClient(app_with_middleware)

        for _ in range(3):
            response = client.get("/test")
            assert response.status_code == 200

    def test_blocks_requests_over_limit(self, app_with_middleware):
        """Requests over limit should return 429."""
        client = TestClient(app_with_middleware)

        # Make 3 requests (at limit)
        for _ in range(3):
            client.get("/test")

        # 4th request should be blocked
        response = client.get("/test")
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]
        assert "Retry-After" in response.headers

    def test_exempt_endpoints_not_limited(self, app_with_middleware):
        """Exempt endpoints should not be rate limited."""
        client = TestClient(app_with_middleware)

        # Health endpoint is exempt
        for _ in range(10):
            response = client.get("/health")
            assert response.status_code == 200

    def test_adds_ratelimit_headers(self, app_with_middleware):
        """Should add X-RateLimit-Remaining header."""
        client = TestClient(app_with_middleware)

        response = client.get("/test")
        assert response.status_code == 200
        assert "x-ratelimit-remaining" in response.headers


class TestRateLimitDisabled:
    """Tests for when rate limiting is disabled."""

    @pytest.fixture(autouse=True)
    def reset_limiter(self):
        """Reset the global rate limiter before each test."""
        reset_rate_limiter()
        yield
        reset_rate_limiter()

    @pytest.fixture
    def app_no_rate_limit(self):
        """Create a FastAPI app with rate limiting disabled."""
        from app.middleware import rate_limit as rl_module

        original_enabled = rl_module.RATE_LIMIT_ENABLED
        rl_module.RATE_LIMIT_ENABLED = False

        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        yield app

        rl_module.RATE_LIMIT_ENABLED = original_enabled

    def test_allows_unlimited_requests(self, app_no_rate_limit):
        """Should allow unlimited requests when disabled."""
        client = TestClient(app_no_rate_limit)

        for _ in range(100):
            response = client.get("/test")
            assert response.status_code == 200


class TestExemptEndpoints:
    """Tests for exempt endpoint configuration."""

    def test_health_is_exempt(self):
        """Health endpoint should be exempt."""
        assert "/health" in EXEMPT_ENDPOINTS

    def test_docs_is_exempt(self):
        """Docs endpoint should be exempt."""
        assert "/docs" in EXEMPT_ENDPOINTS

    def test_root_is_exempt(self):
        """Root endpoint should be exempt."""
        assert "/" in EXEMPT_ENDPOINTS


class TestStrictLimitEndpoints:
    """Tests for strict limit endpoint configuration."""

    def test_ml_train_has_strict_limit(self):
        """ML train endpoint should have strict limits."""
        assert "/ml/train" in STRICT_LIMIT_ENDPOINTS
        limit, window = STRICT_LIMIT_ENDPOINTS["/ml/train"]
        assert limit == 5
        assert window == 3600  # 1 hour

    def test_etl_trigger_has_strict_limit(self):
        """ETL trigger endpoint should have strict limits."""
        assert "/etl/trigger" in STRICT_LIMIT_ENDPOINTS


class TestCheckRateLimitDependency:
    """Tests for the check_rate_limit FastAPI dependency."""

    @pytest.fixture(autouse=True)
    def reset_limiter(self):
        """Reset the global rate limiter before each test."""
        reset_rate_limiter()
        yield
        reset_rate_limiter()

    @pytest.mark.asyncio
    async def test_allows_when_disabled(self):
        """Should allow all requests when disabled."""
        from app.middleware import rate_limit as rl_module

        original = rl_module.RATE_LIMIT_ENABLED
        rl_module.RATE_LIMIT_ENABLED = False

        mock_request = MagicMock()
        mock_request.url.path = "/test"

        # Should not raise
        await check_rate_limit(mock_request)

        rl_module.RATE_LIMIT_ENABLED = original

    @pytest.mark.asyncio
    async def test_allows_exempt_endpoints(self):
        """Should allow exempt endpoints."""
        from app.middleware import rate_limit as rl_module

        original = rl_module.RATE_LIMIT_ENABLED
        rl_module.RATE_LIMIT_ENABLED = True

        mock_request = MagicMock()
        mock_request.url.path = "/health"

        # Should not raise
        await check_rate_limit(mock_request)

        rl_module.RATE_LIMIT_ENABLED = original

    @pytest.mark.asyncio
    async def test_raises_429_when_exceeded(self):
        """Should raise HTTPException with 429 when limit exceeded."""
        from app.middleware import rate_limit as rl_module

        original = rl_module.RATE_LIMIT_ENABLED
        rl_module.RATE_LIMIT_ENABLED = True

        # Create limiter with very low limit
        rl_module._rate_limiter = SlidingWindowRateLimiter(
            requests_per_window=1,
            window_seconds=60,
            burst_allowance=0,
        )

        mock_request = MagicMock()
        mock_request.url.path = "/test"
        mock_request.client.host = "127.0.0.1"
        mock_request.headers = {}

        # First request should succeed
        await check_rate_limit(mock_request)

        # Second request should raise
        with pytest.raises(HTTPException) as exc_info:
            await check_rate_limit(mock_request)

        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in exc_info.value.detail

        rl_module.RATE_LIMIT_ENABLED = original


class TestGetRateLimiter:
    """Tests for get_rate_limiter function."""

    @pytest.fixture(autouse=True)
    def reset_limiter(self):
        """Reset the global rate limiter before each test."""
        reset_rate_limiter()
        yield
        reset_rate_limiter()

    def test_returns_singleton(self):
        """Should return the same instance on multiple calls."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is limiter2

    def test_reset_creates_new_instance(self):
        """Reset should allow creating a new instance."""
        limiter1 = get_rate_limiter()
        reset_rate_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is not limiter2
