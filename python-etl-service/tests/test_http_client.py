"""
Tests for the resilient HTTP client (app/lib/http_client.py).

Tests:
- Exponential backoff calculation
- Retry on transient failures (timeouts, connection errors)
- Retry on specific HTTP status codes (429, 500, 502, 503, 504)
- No retry on client errors (4xx except 429)
- Retry-After header handling
- ResilientClient context manager
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx


# =============================================================================
# calculate_backoff_delay() Tests
# =============================================================================


class TestCalculateBackoffDelay:
    """Tests for calculate_backoff_delay() function."""

    def test_first_attempt_uses_base_delay(self):
        """First attempt (attempt=0) should use approximately base delay."""
        from app.lib.http_client import calculate_backoff_delay

        delay = calculate_backoff_delay(0, base_delay=1.0, jitter=False)
        assert delay == 1.0

    def test_exponential_growth(self):
        """Delay should grow exponentially with each attempt."""
        from app.lib.http_client import calculate_backoff_delay

        delay0 = calculate_backoff_delay(0, base_delay=1.0, jitter=False)
        delay1 = calculate_backoff_delay(1, base_delay=1.0, jitter=False)
        delay2 = calculate_backoff_delay(2, base_delay=1.0, jitter=False)

        assert delay0 == 1.0
        assert delay1 == 2.0
        assert delay2 == 4.0

    def test_respects_max_delay(self):
        """Delay should be capped at max_delay."""
        from app.lib.http_client import calculate_backoff_delay

        delay = calculate_backoff_delay(10, base_delay=1.0, max_delay=5.0, jitter=False)
        assert delay == 5.0

    def test_jitter_adds_randomness(self):
        """Jitter should add randomness to delay."""
        from app.lib.http_client import calculate_backoff_delay

        delays = [calculate_backoff_delay(1, base_delay=1.0, jitter=True) for _ in range(10)]

        # All delays should be between 2.0 and 2.5 (2.0 * 1.0 to 2.0 * 1.25)
        for delay in delays:
            assert 2.0 <= delay <= 2.5

        # With jitter, delays should not all be identical
        assert len(set(delays)) > 1

    def test_no_jitter_gives_consistent_delay(self):
        """Without jitter, delays should be consistent."""
        from app.lib.http_client import calculate_backoff_delay

        delays = [calculate_backoff_delay(1, base_delay=1.0, jitter=False) for _ in range(5)]
        assert all(d == 2.0 for d in delays)


# =============================================================================
# resilient_request() Tests
# =============================================================================


class TestResilientRequest:
    """Tests for resilient_request() function."""

    @pytest.fixture
    def mock_response_200(self):
        """Create a successful response mock."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200
        response.raise_for_status = MagicMock()
        return response

    @pytest.fixture
    def mock_response_500(self):
        """Create a 500 error response mock."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 500
        response.headers = {}
        response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Server Error", request=MagicMock(), response=response
            )
        )
        return response

    @pytest.fixture
    def mock_response_429(self):
        """Create a 429 rate limit response mock."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 429
        response.headers = {"Retry-After": "2"}
        response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Too Many Requests", request=MagicMock(), response=response
            )
        )
        return response

    @pytest.mark.asyncio
    async def test_successful_request_no_retry(self, mock_response_200):
        """Successful request should not retry."""
        from app.lib.http_client import resilient_request

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(return_value=mock_response_200)

        response = await resilient_request(
            "GET", "https://example.com", client=mock_client
        )

        assert response.status_code == 200
        assert mock_client.request.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_500(self, mock_response_500, mock_response_200):
        """Should retry on 500 error and succeed on retry."""
        from app.lib.http_client import resilient_request

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(
            side_effect=[mock_response_500, mock_response_200]
        )

        response = await resilient_request(
            "GET",
            "https://example.com",
            client=mock_client,
            max_retries=3,
            base_delay=0.01,  # Fast for testing
        )

        assert response.status_code == 200
        assert mock_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_timeout(self, mock_response_200):
        """Should retry on timeout and succeed on retry."""
        from app.lib.http_client import resilient_request

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(
            side_effect=[httpx.TimeoutException("Timeout"), mock_response_200]
        )

        response = await resilient_request(
            "GET",
            "https://example.com",
            client=mock_client,
            max_retries=3,
            base_delay=0.01,
        )

        assert response.status_code == 200
        assert mock_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_connection_error(self, mock_response_200):
        """Should retry on connection error and succeed on retry."""
        from app.lib.http_client import resilient_request

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(
            side_effect=[httpx.ConnectError("Connection failed"), mock_response_200]
        )

        response = await resilient_request(
            "GET",
            "https://example.com",
            client=mock_client,
            max_retries=3,
            base_delay=0.01,
        )

        assert response.status_code == 200
        assert mock_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_exhausts_retries(self, mock_response_500):
        """Should exhaust retries and raise error."""
        from app.lib.http_client import resilient_request

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(return_value=mock_response_500)

        with pytest.raises(httpx.HTTPStatusError):
            await resilient_request(
                "GET",
                "https://example.com",
                client=mock_client,
                max_retries=2,
                base_delay=0.01,
            )

        # Initial + 2 retries = 3 total
        assert mock_client.request.call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_404(self):
        """Should not retry on 404 (client error)."""
        from app.lib.http_client import resilient_request

        response_404 = MagicMock(spec=httpx.Response)
        response_404.status_code = 404
        response_404.headers = {}
        response_404.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Not Found", request=MagicMock(), response=response_404
            )
        )

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(return_value=response_404)

        with pytest.raises(httpx.HTTPStatusError):
            await resilient_request(
                "GET",
                "https://example.com",
                client=mock_client,
                max_retries=3,
                base_delay=0.01,
            )

        # Only 1 request, no retries for 404
        assert mock_client.request.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_429(self, mock_response_429, mock_response_200):
        """Should retry on 429 (rate limit) with Retry-After header."""
        from app.lib.http_client import resilient_request

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(
            side_effect=[mock_response_429, mock_response_200]
        )

        response = await resilient_request(
            "GET",
            "https://example.com",
            client=mock_client,
            max_retries=3,
            base_delay=0.01,
        )

        assert response.status_code == 200
        assert mock_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_custom_retry_status_codes(self, mock_response_200):
        """Should respect custom retry status codes."""
        from app.lib.http_client import resilient_request

        response_418 = MagicMock(spec=httpx.Response)
        response_418.status_code = 418  # I'm a teapot
        response_418.headers = {}
        response_418.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(
            side_effect=[response_418, mock_response_200]
        )

        # Retry on 418
        response = await resilient_request(
            "GET",
            "https://example.com",
            client=mock_client,
            max_retries=3,
            base_delay=0.01,
            retry_on_status={418},
        )

        assert response.status_code == 200
        assert mock_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_raise_for_status_false(self):
        """With raise_for_status=False, should return response without raising."""
        from app.lib.http_client import resilient_request

        # Create a non-retryable error response (400 Bad Request)
        response_400 = MagicMock(spec=httpx.Response)
        response_400.status_code = 400
        response_400.headers = {}
        response_400.raise_for_status = MagicMock()  # Doesn't raise because we pass raise_for_status=False

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(return_value=response_400)

        response = await resilient_request(
            "GET",
            "https://example.com",
            client=mock_client,
            max_retries=2,
            base_delay=0.01,
            raise_for_status=False,  # Don't raise on error
        )

        # Should return the 400 response without raising (400 is not in retry codes)
        assert response.status_code == 400
        assert mock_client.request.call_count == 1

    @pytest.mark.asyncio
    async def test_creates_client_when_not_provided(self, mock_response_200):
        """Should create client when not provided."""
        from app.lib.http_client import resilient_request

        with patch("app.lib.http_client.httpx.AsyncClient") as MockAsyncClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.request = AsyncMock(return_value=mock_response_200)
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            MockAsyncClient.return_value = mock_client_instance

            response = await resilient_request("GET", "https://example.com")

            assert response.status_code == 200
            MockAsyncClient.assert_called_once()


# =============================================================================
# ResilientClient Tests
# =============================================================================


class TestResilientClient:
    """Tests for ResilientClient class."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """ResilientClient should work as context manager."""
        from app.lib.http_client import ResilientClient

        with patch("app.lib.http_client.httpx.AsyncClient") as MockAsyncClient:
            mock_instance = AsyncMock()
            mock_instance.aclose = AsyncMock()
            MockAsyncClient.return_value = mock_instance

            async with ResilientClient() as client:
                assert client._client is not None

            mock_instance.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_method(self):
        """ResilientClient.get() should make GET request."""
        from app.lib.http_client import ResilientClient

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("app.lib.http_client.httpx.AsyncClient") as MockAsyncClient:
            mock_instance = AsyncMock()
            mock_instance.request = AsyncMock(return_value=mock_response)
            mock_instance.aclose = AsyncMock()
            MockAsyncClient.return_value = mock_instance

            async with ResilientClient() as client:
                response = await client.get("https://example.com")

            assert response.status_code == 200
            mock_instance.request.assert_called_once()
            call_args = mock_instance.request.call_args
            assert call_args[0][0] == "GET"
            assert call_args[0][1] == "https://example.com"

    @pytest.mark.asyncio
    async def test_post_method(self):
        """ResilientClient.post() should make POST request."""
        from app.lib.http_client import ResilientClient

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 201
        mock_response.raise_for_status = MagicMock()

        with patch("app.lib.http_client.httpx.AsyncClient") as MockAsyncClient:
            mock_instance = AsyncMock()
            mock_instance.request = AsyncMock(return_value=mock_response)
            mock_instance.aclose = AsyncMock()
            MockAsyncClient.return_value = mock_instance

            async with ResilientClient() as client:
                response = await client.post(
                    "https://example.com",
                    json={"key": "value"}
                )

            assert response.status_code == 201
            call_args = mock_instance.request.call_args
            assert call_args[0][0] == "POST"

    @pytest.mark.asyncio
    async def test_raises_error_without_context_manager(self):
        """Should raise error if used without context manager."""
        from app.lib.http_client import ResilientClient

        client = ResilientClient()
        with pytest.raises(RuntimeError, match="Client not initialized"):
            await client.get("https://example.com")

    @pytest.mark.asyncio
    async def test_custom_retry_settings(self):
        """ResilientClient should use custom retry settings."""
        from app.lib.http_client import ResilientClient

        client = ResilientClient(
            max_retries=5,
            base_delay=2.0,
            max_delay=60.0,
            timeout=120.0,
            retry_on_status={418, 500},
        )

        assert client.max_retries == 5
        assert client.base_delay == 2.0
        assert client.max_delay == 60.0
        assert client.timeout == 120.0
        assert client.retry_on_status == {418, 500}

    @pytest.mark.asyncio
    async def test_put_method(self):
        """ResilientClient.put() should make PUT request."""
        from app.lib.http_client import ResilientClient

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("app.lib.http_client.httpx.AsyncClient") as MockAsyncClient:
            mock_instance = AsyncMock()
            mock_instance.request = AsyncMock(return_value=mock_response)
            mock_instance.aclose = AsyncMock()
            MockAsyncClient.return_value = mock_instance

            async with ResilientClient() as client:
                response = await client.put("https://example.com", json={})

            call_args = mock_instance.request.call_args
            assert call_args[0][0] == "PUT"

    @pytest.mark.asyncio
    async def test_delete_method(self):
        """ResilientClient.delete() should make DELETE request."""
        from app.lib.http_client import ResilientClient

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 204
        mock_response.raise_for_status = MagicMock()

        with patch("app.lib.http_client.httpx.AsyncClient") as MockAsyncClient:
            mock_instance = AsyncMock()
            mock_instance.request = AsyncMock(return_value=mock_response)
            mock_instance.aclose = AsyncMock()
            MockAsyncClient.return_value = mock_instance

            async with ResilientClient() as client:
                response = await client.delete("https://example.com/item/1")

            call_args = mock_instance.request.call_args
            assert call_args[0][0] == "DELETE"

    @pytest.mark.asyncio
    async def test_patch_method(self):
        """ResilientClient.patch() should make PATCH request."""
        from app.lib.http_client import ResilientClient

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("app.lib.http_client.httpx.AsyncClient") as MockAsyncClient:
            mock_instance = AsyncMock()
            mock_instance.request = AsyncMock(return_value=mock_response)
            mock_instance.aclose = AsyncMock()
            MockAsyncClient.return_value = mock_instance

            async with ResilientClient() as client:
                response = await client.patch("https://example.com", json={"update": True})

            call_args = mock_instance.request.call_args
            assert call_args[0][0] == "PATCH"


# =============================================================================
# Integration-style Tests
# =============================================================================


class TestRetryBehavior:
    """Integration-style tests for retry behavior."""

    @pytest.mark.asyncio
    async def test_multiple_retries_then_success(self):
        """Should retry multiple times before succeeding."""
        from app.lib.http_client import resilient_request

        response_500 = MagicMock(spec=httpx.Response)
        response_500.status_code = 500
        response_500.headers = {}

        response_200 = MagicMock(spec=httpx.Response)
        response_200.status_code = 200
        response_200.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        # Fail twice, then succeed
        mock_client.request = AsyncMock(
            side_effect=[response_500, response_500, response_200]
        )

        response = await resilient_request(
            "GET",
            "https://example.com",
            client=mock_client,
            max_retries=3,
            base_delay=0.01,
        )

        assert response.status_code == 200
        assert mock_client.request.call_count == 3

    @pytest.mark.asyncio
    async def test_mixed_errors_then_success(self):
        """Should handle mixed error types before succeeding."""
        from app.lib.http_client import resilient_request

        response_200 = MagicMock(spec=httpx.Response)
        response_200.status_code = 200
        response_200.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(
            side_effect=[
                httpx.TimeoutException("Timeout"),
                httpx.ConnectError("Connect failed"),
                response_200,
            ]
        )

        response = await resilient_request(
            "GET",
            "https://example.com",
            client=mock_client,
            max_retries=3,
            base_delay=0.01,
        )

        assert response.status_code == 200
        assert mock_client.request.call_count == 3

    @pytest.mark.asyncio
    async def test_timeout_exhausts_all_retries(self):
        """Continuous timeouts should exhaust all retries."""
        from app.lib.http_client import resilient_request

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(
            side_effect=httpx.TimeoutException("Timeout")
        )

        with pytest.raises(httpx.TimeoutException):
            await resilient_request(
                "GET",
                "https://example.com",
                client=mock_client,
                max_retries=2,
                base_delay=0.01,
            )

        # 1 initial + 2 retries = 3 total
        assert mock_client.request.call_count == 3
