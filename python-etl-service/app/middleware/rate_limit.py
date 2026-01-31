"""
Rate Limiting Middleware

Provides IP-based rate limiting for the ETL service using a sliding window algorithm.
Configurable per-endpoint limits and global limits.

Environment Variables:
- ETL_RATE_LIMIT_ENABLED: Set to "true" to enable (default: true)
- ETL_RATE_LIMIT_REQUESTS: Max requests per window (default: 100)
- ETL_RATE_LIMIT_WINDOW: Window size in seconds (default: 60)
- ETL_RATE_LIMIT_BURST: Burst allowance above limit (default: 10)
"""

import asyncio
import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, List, Optional, Set, Tuple

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

# Configuration from environment
RATE_LIMIT_ENABLED = os.environ.get("ETL_RATE_LIMIT_ENABLED", "true").lower() == "true"
DEFAULT_REQUESTS_PER_WINDOW = int(os.environ.get("ETL_RATE_LIMIT_REQUESTS", "100"))
DEFAULT_WINDOW_SECONDS = int(os.environ.get("ETL_RATE_LIMIT_WINDOW", "60"))
DEFAULT_BURST_ALLOWANCE = int(os.environ.get("ETL_RATE_LIMIT_BURST", "10"))

# Endpoints exempt from rate limiting
EXEMPT_ENDPOINTS: Set[str] = {
    "/",
    "/health",
    "/health/",
    "/docs",
    "/docs/",
    "/openapi.json",
    "/redoc",
    "/redoc/",
}

# Stricter limits for expensive endpoints
STRICT_LIMIT_ENDPOINTS: Dict[str, Tuple[int, int]] = {
    # (requests, window_seconds)
    "/ml/train": (5, 3600),  # 5 per hour - expensive operation
    "/ml/batch-predict": (20, 60),  # 20 per minute
    "/etl/trigger": (10, 60),  # 10 per minute
    "/error-reports/process": (10, 60),  # 10 per minute
    "/error-reports/reanalyze": (10, 60),  # 10 per minute
    "/enrichment/trigger": (10, 60),  # 10 per minute
}


@dataclass
class RateLimitEntry:
    """Tracks request timestamps for a client."""
    timestamps: List[float] = field(default_factory=list)
    lock: Lock = field(default_factory=Lock)


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter with configurable limits.

    Uses a sliding window algorithm that tracks individual request timestamps
    within the window, providing smoother rate limiting than fixed windows.
    """

    def __init__(
        self,
        requests_per_window: int = DEFAULT_REQUESTS_PER_WINDOW,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
        burst_allowance: int = DEFAULT_BURST_ALLOWANCE,
    ):
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.burst_allowance = burst_allowance
        self.max_requests = requests_per_window + burst_allowance

        # Client tracking: key -> RateLimitEntry
        self._clients: Dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        self._cleanup_lock = Lock()
        self._last_cleanup = time.time()

    def _get_client_key(self, request: Request) -> str:
        """
        Get a unique key for the client.

        Uses X-Forwarded-For header if available (for reverse proxies),
        otherwise falls back to direct client IP.
        """
        # Check for forwarded headers (reverse proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Direct connection
        if request.client:
            return request.client.host

        return "unknown"

    def _cleanup_old_entries(self, current_time: float) -> None:
        """
        Periodically clean up expired entries to prevent memory growth.

        Called automatically during rate limit checks.
        """
        # Only cleanup every 60 seconds
        if current_time - self._last_cleanup < 60:
            return

        with self._cleanup_lock:
            if current_time - self._last_cleanup < 60:
                return  # Double-check after acquiring lock

            cutoff = current_time - self.window_seconds
            keys_to_remove = []

            for key, entry in self._clients.items():
                with entry.lock:
                    # Remove timestamps outside window
                    entry.timestamps = [t for t in entry.timestamps if t > cutoff]
                    if not entry.timestamps:
                        keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._clients[key]

            self._last_cleanup = current_time

    def check_rate_limit(
        self,
        request: Request,
        limit_override: Optional[int] = None,
        window_override: Optional[int] = None,
    ) -> Tuple[bool, int, int]:
        """
        Check if a request is within rate limits.

        Args:
            request: The incoming request
            limit_override: Override the default request limit
            window_override: Override the default window size

        Returns:
            Tuple of (allowed, remaining_requests, retry_after_seconds)
        """
        current_time = time.time()

        # Periodic cleanup
        self._cleanup_old_entries(current_time)

        # Get limits to use
        max_requests = limit_override if limit_override else self.max_requests
        window = window_override if window_override else self.window_seconds

        client_key = self._get_client_key(request)
        entry = self._clients[client_key]

        with entry.lock:
            # Remove timestamps outside current window
            cutoff = current_time - window
            entry.timestamps = [t for t in entry.timestamps if t > cutoff]

            current_count = len(entry.timestamps)

            if current_count >= max_requests:
                # Rate limit exceeded
                # Calculate retry-after based on oldest timestamp in window
                if entry.timestamps:
                    oldest = entry.timestamps[0]
                    retry_after = int(oldest + window - current_time) + 1
                else:
                    retry_after = window

                return False, 0, retry_after

            # Add current request timestamp
            entry.timestamps.append(current_time)

            remaining = max_requests - len(entry.timestamps)
            return True, remaining, 0

    def get_limit_for_endpoint(
        self, path: str
    ) -> Tuple[Optional[int], Optional[int]]:
        """
        Get the rate limit configuration for a specific endpoint.

        Returns (limit, window) tuple, or (None, None) for default limits.
        """
        # Check for strict limits
        for endpoint, (limit, window) in STRICT_LIMIT_ENDPOINTS.items():
            if path.startswith(endpoint):
                return limit, window

        return None, None


# Global rate limiter instance
_rate_limiter: Optional[SlidingWindowRateLimiter] = None


def get_rate_limiter() -> SlidingWindowRateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = SlidingWindowRateLimiter()
    return _rate_limiter


async def check_rate_limit(request: Request) -> None:
    """
    FastAPI dependency for rate limiting.

    Usage:
        @router.get("/endpoint")
        async def endpoint(_: None = Depends(check_rate_limit)):
            ...
    """
    if not RATE_LIMIT_ENABLED:
        return

    # Check if endpoint is exempt
    if request.url.path in EXEMPT_ENDPOINTS:
        return

    limiter = get_rate_limiter()

    # Get endpoint-specific limits
    limit_override, window_override = limiter.get_limit_for_endpoint(request.url.path)

    allowed, remaining, retry_after = limiter.check_rate_limit(
        request,
        limit_override=limit_override,
        window_override=window_override,
    )

    if not allowed:
        logger.warning(
            "Rate limit exceeded",
            extra={
                "client_ip": limiter._get_client_key(request),
                "path": request.url.path,
                "retry_after": retry_after,
            }
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Remaining": "0",
            },
        )


class RateLimitMiddleware:
    """
    ASGI middleware for rate limiting.

    Applies rate limiting to all requests except exempt endpoints.
    Uses sliding window algorithm with per-endpoint configuration.

    Usage in FastAPI:
        app.add_middleware(RateLimitMiddleware)
    """

    def __init__(self, app):
        self.app = app
        self.limiter = get_rate_limiter()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Check if rate limiting is enabled
        if not RATE_LIMIT_ENABLED:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Check if endpoint is exempt
        if path in EXEMPT_ENDPOINTS:
            await self.app(scope, receive, send)
            return

        # Build a minimal request object for rate limit check
        class MinimalRequest:
            def __init__(self, scope):
                self.headers = dict(
                    (k.decode("utf-8"), v.decode("utf-8"))
                    for k, v in scope.get("headers", [])
                )
                self.client = type("Client", (), {
                    "host": scope.get("client", ("unknown", 0))[0]
                })()
                self.url = type("URL", (), {"path": scope.get("path", "")})()

        request = MinimalRequest(scope)

        # Get endpoint-specific limits
        limit_override, window_override = self.limiter.get_limit_for_endpoint(path)

        allowed, remaining, retry_after = self.limiter.check_rate_limit(
            request,
            limit_override=limit_override,
            window_override=window_override,
        )

        if not allowed:
            # Return 429 response
            response_body = f'{{"detail":"Rate limit exceeded. Try again in {retry_after} seconds."}}'.encode()

            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"retry-after", str(retry_after).encode()],
                    [b"x-ratelimit-remaining", b"0"],
                ],
            })
            await send({
                "type": "http.response.body",
                "body": response_body,
            })
            return

        # Add rate limit headers to response
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append([b"x-ratelimit-remaining", str(remaining).encode()])
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)


def reset_rate_limiter() -> None:
    """Reset the global rate limiter. Useful for testing."""
    global _rate_limiter
    _rate_limiter = None
