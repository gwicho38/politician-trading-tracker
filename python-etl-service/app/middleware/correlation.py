"""
Correlation ID middleware for FastAPI.

Extracts or generates correlation IDs for request tracing.
"""

import uuid
import time
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.lib.logging_config import (
    set_correlation_id,
    clear_correlation_id,
    get_correlation_id,
)

logger = logging.getLogger(__name__)

# Standard header names for correlation ID
CORRELATION_ID_HEADER = "X-Correlation-ID"
REQUEST_ID_HEADER = "X-Request-ID"


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware that manages correlation IDs for request tracing.

    Features:
    - Extracts correlation ID from incoming request headers
    - Generates new correlation ID if not present
    - Adds correlation ID to response headers
    - Logs request start/end with timing
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process the request with correlation ID tracking."""
        # Extract or generate correlation ID
        correlation_id = (
            request.headers.get(CORRELATION_ID_HEADER)
            or request.headers.get(REQUEST_ID_HEADER)
            or str(uuid.uuid4())
        )

        # Set correlation ID in context
        set_correlation_id(correlation_id)

        # Log request start
        start_time = time.time()
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "correlation_id": correlation_id,
                "extra_fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "query": str(request.query_params),
                    "client_ip": request.client.host if request.client else None,
                },
            },
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log request completion
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"- {response.status_code} ({duration_ms:.2f}ms)",
                extra={
                    "correlation_id": correlation_id,
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": round(duration_ms, 2),
                    },
                },
            )

            # Add correlation ID to response headers
            response.headers[CORRELATION_ID_HEADER] = correlation_id

            return response

        except Exception as e:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log error
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"- {type(e).__name__}: {str(e)} ({duration_ms:.2f}ms)",
                extra={
                    "correlation_id": correlation_id,
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "duration_ms": round(duration_ms, 2),
                    },
                },
                exc_info=True,
            )
            raise

        finally:
            # Clear correlation ID from context
            clear_correlation_id()


def get_request_correlation_id(request: Request) -> str:
    """Get the correlation ID for a request.

    Can be used in route handlers to access the correlation ID.
    """
    return get_correlation_id()
