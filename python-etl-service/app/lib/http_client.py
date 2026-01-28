"""
Resilient HTTP Client with Retry Logic

Provides a reusable HTTP client wrapper with:
- Exponential backoff retry for transient failures
- Configurable retry behavior per request
- Structured logging with correlation IDs
- Timeout handling
- Rate limit detection

Usage:
    from app.lib.http_client import resilient_request, ResilientClient

    # Simple usage with default settings
    response = await resilient_request(
        "POST",
        "https://api.example.com/endpoint",
        json={"key": "value"},
    )

    # With custom retry settings
    response = await resilient_request(
        "GET",
        "https://api.example.com/data",
        max_retries=5,
        base_delay=2.0,
        retry_on_status=[429, 500, 502, 503, 504],
    )

    # Using context manager for multiple requests
    async with ResilientClient() as client:
        response1 = await client.get("https://api1.example.com")
        response2 = await client.post("https://api2.example.com", json={...})
"""

import asyncio
import logging
import random
from typing import Any, Dict, List, Optional, Set, Union

import httpx

logger = logging.getLogger(__name__)

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0  # seconds
DEFAULT_MAX_DELAY = 30.0  # seconds
DEFAULT_TIMEOUT = 30.0  # seconds
DEFAULT_RETRY_STATUS_CODES: Set[int] = {429, 500, 502, 503, 504}

# Exceptions that should trigger retry
RETRYABLE_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ReadError,
    httpx.WriteError,
)


def calculate_backoff_delay(
    attempt: int,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    jitter: bool = True,
) -> float:
    """
    Calculate exponential backoff delay with optional jitter.

    Args:
        attempt: The retry attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay cap in seconds
        jitter: Whether to add random jitter to prevent thundering herd

    Returns:
        Delay in seconds
    """
    delay = min(base_delay * (2 ** attempt), max_delay)
    if jitter:
        # Add random jitter between 0% and 25% of delay
        delay = delay * (1 + random.random() * 0.25)
    return delay


async def resilient_request(
    method: str,
    url: str,
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    timeout: float = DEFAULT_TIMEOUT,
    retry_on_status: Optional[Set[int]] = None,
    raise_for_status: bool = True,
    client: Optional[httpx.AsyncClient] = None,
    **kwargs: Any,
) -> httpx.Response:
    """
    Make an HTTP request with automatic retry on transient failures.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        url: Request URL
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay for exponential backoff in seconds (default: 1.0)
        max_delay: Maximum delay between retries in seconds (default: 30.0)
        timeout: Request timeout in seconds (default: 30.0)
        retry_on_status: HTTP status codes to retry on (default: {429, 500, 502, 503, 504})
        raise_for_status: Whether to raise HTTPStatusError for 4xx/5xx responses (default: True)
        client: Optional httpx.AsyncClient to reuse (creates new one if not provided)
        **kwargs: Additional arguments passed to httpx.AsyncClient.request()

    Returns:
        httpx.Response object

    Raises:
        httpx.HTTPStatusError: If raise_for_status=True and response is 4xx/5xx after retries
        httpx.TimeoutException: If all retries timeout
        httpx.RequestError: For other request failures after retries
    """
    retry_codes = retry_on_status or DEFAULT_RETRY_STATUS_CODES
    last_exception: Optional[Exception] = None
    last_response: Optional[httpx.Response] = None

    # Set timeout if not already in kwargs
    if "timeout" not in kwargs:
        kwargs["timeout"] = timeout

    async def make_request(http_client: httpx.AsyncClient) -> httpx.Response:
        nonlocal last_exception, last_response

        for attempt in range(max_retries + 1):
            try:
                response = await http_client.request(method, url, **kwargs)
                last_response = response

                # Check if we should retry based on status code
                if response.status_code in retry_codes and attempt < max_retries:
                    delay = calculate_backoff_delay(attempt, base_delay, max_delay)

                    # Check for Retry-After header
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        try:
                            delay = max(delay, float(retry_after))
                        except ValueError:
                            pass  # Ignore invalid Retry-After header

                    logger.warning(
                        f"Retryable status {response.status_code} from {url}, "
                        f"attempt {attempt + 1}/{max_retries + 1}, "
                        f"waiting {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                    continue

                # Success or non-retryable status
                if raise_for_status:
                    response.raise_for_status()
                return response

            except RETRYABLE_EXCEPTIONS as e:
                last_exception = e
                if attempt < max_retries:
                    delay = calculate_backoff_delay(attempt, base_delay, max_delay)
                    logger.warning(
                        f"Request to {url} failed with {type(e).__name__}: {e}, "
                        f"attempt {attempt + 1}/{max_retries + 1}, "
                        f"waiting {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(
                        f"Request to {url} failed after {max_retries + 1} attempts: {e}"
                    )
                    raise

            except httpx.HTTPStatusError:
                # Don't retry client errors (4xx) except for rate limiting
                raise

        # If we get here, we exhausted retries due to retryable status codes
        if last_response is not None:
            if raise_for_status:
                last_response.raise_for_status()
            return last_response

        # Should not reach here, but raise last exception if we do
        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected state in resilient_request")

    # Use provided client or create a new one
    if client:
        return await make_request(client)
    else:
        async with httpx.AsyncClient() as new_client:
            return await make_request(new_client)


class ResilientClient:
    """
    Context manager for making multiple resilient HTTP requests.

    Example:
        async with ResilientClient(max_retries=5) as client:
            response1 = await client.get("https://api.example.com/data")
            response2 = await client.post("https://api.example.com/submit", json={...})
    """

    def __init__(
        self,
        *,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_delay: float = DEFAULT_BASE_DELAY,
        max_delay: float = DEFAULT_MAX_DELAY,
        timeout: float = DEFAULT_TIMEOUT,
        retry_on_status: Optional[Set[int]] = None,
        raise_for_status: bool = True,
        **client_kwargs: Any,
    ):
        """
        Initialize the resilient client.

        Args:
            max_retries: Maximum retry attempts (default: 3)
            base_delay: Base backoff delay in seconds (default: 1.0)
            max_delay: Maximum backoff delay in seconds (default: 30.0)
            timeout: Request timeout in seconds (default: 30.0)
            retry_on_status: HTTP status codes to retry (default: {429, 500, 502, 503, 504})
            raise_for_status: Raise on 4xx/5xx responses (default: True)
            **client_kwargs: Additional arguments for httpx.AsyncClient
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.timeout = timeout
        self.retry_on_status = retry_on_status or DEFAULT_RETRY_STATUS_CODES
        self.raise_for_status = raise_for_status
        self.client_kwargs = client_kwargs
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "ResilientClient":
        self._client = httpx.AsyncClient(timeout=self.timeout, **self.client_kwargs)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make a request with retry logic."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        return await resilient_request(
            method,
            url,
            max_retries=self.max_retries,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            timeout=self.timeout,
            retry_on_status=self.retry_on_status,
            raise_for_status=self.raise_for_status,
            client=self._client,
            **kwargs,
        )

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make a GET request with retry logic."""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make a POST request with retry logic."""
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make a PUT request with retry logic."""
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make a DELETE request with retry logic."""
        return await self.request("DELETE", url, **kwargs)

    async def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make a PATCH request with retry logic."""
        return await self.request("PATCH", url, **kwargs)
