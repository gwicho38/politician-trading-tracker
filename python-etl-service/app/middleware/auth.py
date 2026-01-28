"""
API Key Authentication Middleware

Provides authentication for the ETL service using API keys.
Supports multiple authentication methods:
1. X-API-Key header (preferred)
2. Authorization: Bearer <key> header
3. api_key query parameter (for backwards compatibility)

Environment Variables:
- ETL_API_KEY: Primary API key for service access
- ETL_ADMIN_API_KEY: Admin API key for sensitive operations (optional)
- ETL_AUTH_DISABLED: Set to "true" to disable auth (dev only)
"""

import hashlib
import hmac
import logging
import os
import secrets
import time
from functools import wraps
from typing import Callable, List, Optional, Set

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, APIKeyQuery

logger = logging.getLogger(__name__)

# API Key headers/params
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_bearer = APIKeyHeader(name="Authorization", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)

# Environment configuration
ETL_API_KEY = os.environ.get("ETL_API_KEY")
ETL_ADMIN_API_KEY = os.environ.get("ETL_ADMIN_API_KEY")
ETL_AUTH_DISABLED = os.environ.get("ETL_AUTH_DISABLED", "false").lower() == "true"

# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS: Set[str] = {
    "/",
    "/health",
    "/health/",
    "/docs",
    "/docs/",
    "/openapi.json",
    "/redoc",
    "/redoc/",
}


def constant_time_compare(a: str, b: str) -> bool:
    """
    Compare two strings in constant time to prevent timing attacks.

    Uses hmac.compare_digest which is designed to prevent timing analysis.
    """
    if not a or not b:
        return False
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def generate_api_key(prefix: str = "etl") -> str:
    """
    Generate a secure random API key.

    Returns a key in format: {prefix}_{random_bytes}
    Example: etl_sk_a1b2c3d4e5f6...
    """
    random_part = secrets.token_urlsafe(32)
    return f"{prefix}_sk_{random_part}"


def extract_api_key(
    header_key: Optional[str] = None,
    bearer_header: Optional[str] = None,
    query_key: Optional[str] = None,
) -> Optional[str]:
    """
    Extract API key from various sources in priority order.

    Priority:
    1. X-API-Key header
    2. Authorization: Bearer header
    3. api_key query parameter
    """
    # Try X-API-Key header first
    if header_key:
        return header_key

    # Try Authorization header (Bearer token)
    if bearer_header:
        if bearer_header.lower().startswith("bearer "):
            return bearer_header[7:]
        return bearer_header

    # Fall back to query parameter
    if query_key:
        return query_key

    return None


def validate_api_key(
    api_key: Optional[str],
    require_admin: bool = False,
) -> bool:
    """
    Validate an API key against configured keys.

    Args:
        api_key: The API key to validate
        require_admin: If True, only accept admin API key

    Returns:
        True if valid, False otherwise
    """
    if not api_key:
        return False

    # Check admin key first if required
    if require_admin:
        if ETL_ADMIN_API_KEY:
            return constant_time_compare(api_key, ETL_ADMIN_API_KEY)
        # If no admin key configured, fall through to regular key
        # but log a warning
        logger.warning("Admin access attempted but ETL_ADMIN_API_KEY not configured")

    # Check regular API key
    if ETL_API_KEY and constant_time_compare(api_key, ETL_API_KEY):
        return True

    # Check admin key (admins can access regular endpoints too)
    if ETL_ADMIN_API_KEY and constant_time_compare(api_key, ETL_ADMIN_API_KEY):
        return True

    return False


async def get_api_key(
    header_key: Optional[str] = Security(api_key_header),
    bearer_header: Optional[str] = Security(api_key_bearer),
    query_key: Optional[str] = Security(api_key_query),
) -> Optional[str]:
    """FastAPI dependency to extract API key from request."""
    return extract_api_key(header_key, bearer_header, query_key)


async def require_api_key(
    request: Request,
    api_key: Optional[str] = Depends(get_api_key),
) -> str:
    """
    FastAPI dependency that requires a valid API key.

    Raises HTTPException 401 if no valid key provided.
    """
    # Allow public endpoints without auth
    if request.url.path in PUBLIC_ENDPOINTS:
        return "public"

    # Check if auth is disabled (dev mode)
    if ETL_AUTH_DISABLED:
        logger.debug("Auth disabled, allowing request")
        return "auth_disabled"

    # Check if API key is configured
    if not ETL_API_KEY and not ETL_ADMIN_API_KEY:
        logger.warning(
            "No API keys configured. Set ETL_API_KEY environment variable. "
            "Allowing request for backwards compatibility."
        )
        return "no_keys_configured"

    # Validate the provided key
    if not api_key:
        logger.warning(
            "API request without authentication",
            extra={
                "path": request.url.path,
                "method": request.method,
                "client_ip": request.client.host if request.client else "unknown",
            }
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide via X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not validate_api_key(api_key):
        logger.warning(
            "Invalid API key provided",
            extra={
                "path": request.url.path,
                "method": request.method,
                "client_ip": request.client.host if request.client else "unknown",
                "key_prefix": api_key[:8] if len(api_key) > 8 else "***",
            }
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key


async def require_admin_key(
    request: Request,
    api_key: Optional[str] = Depends(get_api_key),
) -> str:
    """
    FastAPI dependency that requires admin API key.

    Use this for sensitive operations like:
    - Force applying corrections
    - Activating ML models
    - Running all jobs
    """
    # Check if auth is disabled (dev mode)
    if ETL_AUTH_DISABLED:
        logger.debug("Auth disabled, allowing admin request")
        return "auth_disabled"

    # Check if admin key is configured
    if not ETL_ADMIN_API_KEY:
        # Fall back to regular API key if no admin key configured
        if ETL_API_KEY and api_key and constant_time_compare(api_key, ETL_API_KEY):
            logger.warning(
                "Admin operation using regular API key (no admin key configured)",
                extra={"path": request.url.path}
            )
            return api_key
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin API key required for this operation",
        )

    # Validate admin key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not validate_api_key(api_key, require_admin=True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin API key",
        )

    return api_key


def api_key_auth(admin_only: bool = False):
    """
    Decorator for requiring API key authentication on route handlers.

    Usage:
        @router.post("/trigger")
        @api_key_auth()
        async def trigger_etl():
            ...

        @router.post("/force-apply")
        @api_key_auth(admin_only=True)
        async def force_apply():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if not request:
                # Try to find request in args
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request:
                api_key = await get_api_key(
                    request.headers.get("X-API-Key"),
                    request.headers.get("Authorization"),
                    request.query_params.get("api_key"),
                )

                if admin_only:
                    await require_admin_key(request, api_key)
                else:
                    await require_api_key(request, api_key)

            return await func(*args, **kwargs)
        return wrapper
    return decorator


class AuthMiddleware:
    """
    ASGI middleware for API key authentication.

    This middleware checks all requests for valid API keys,
    except for public endpoints defined in PUBLIC_ENDPOINTS.

    Usage in FastAPI:
        app.add_middleware(AuthMiddleware)
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Get request path
        path = scope.get("path", "")

        # Allow public endpoints
        if path in PUBLIC_ENDPOINTS:
            await self.app(scope, receive, send)
            return

        # Check if auth is disabled
        if ETL_AUTH_DISABLED:
            await self.app(scope, receive, send)
            return

        # Check if any API keys are configured
        if not ETL_API_KEY and not ETL_ADMIN_API_KEY:
            # No keys configured - allow for backwards compatibility
            # but log warning
            logger.warning(
                "AuthMiddleware: No API keys configured, allowing request",
                extra={"path": path}
            )
            await self.app(scope, receive, send)
            return

        # Extract headers
        headers = dict(scope.get("headers", []))

        # Try to get API key from headers
        api_key = None

        # X-API-Key header
        x_api_key = headers.get(b"x-api-key")
        if x_api_key:
            api_key = x_api_key.decode("utf-8")

        # Authorization header
        if not api_key:
            auth_header = headers.get(b"authorization")
            if auth_header:
                auth_value = auth_header.decode("utf-8")
                if auth_value.lower().startswith("bearer "):
                    api_key = auth_value[7:]

        # Query string (less preferred)
        if not api_key:
            query_string = scope.get("query_string", b"").decode("utf-8")
            for param in query_string.split("&"):
                if param.startswith("api_key="):
                    api_key = param[8:]
                    break

        # Validate key
        if not validate_api_key(api_key):
            # Return 401 Unauthorized
            response_body = b'{"detail":"API key required. Provide via X-API-Key header."}'

            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"www-authenticate", b"ApiKey"],
                ],
            })
            await send({
                "type": "http.response.body",
                "body": response_body,
            })
            return

        # Valid key - proceed
        await self.app(scope, receive, send)
