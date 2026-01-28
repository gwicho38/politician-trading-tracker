"""
Structured logging configuration with correlation ID support.

Provides JSON-formatted logs with request correlation IDs for tracing
requests across services and improving observability.
"""

import logging
import json
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Context variable for correlation ID - thread-safe and async-safe
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str:
    """Get the current correlation ID, or generate a new one if not set."""
    cid = correlation_id_var.get()
    if cid is None:
        cid = str(uuid.uuid4())
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context."""
    correlation_id_var.set(correlation_id)


def clear_correlation_id() -> None:
    """Clear the correlation ID from the current context."""
    correlation_id_var.set(None)


class StructuredFormatter(logging.Formatter):
    """JSON formatter that includes correlation ID and structured metadata."""

    def __init__(self, service_name: str = "politician-etl"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with structured fields."""
        # Base log entry
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
        }

        # Add correlation ID if available
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        # Add source location
        log_entry["source"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add any extra fields passed to the logger
        if hasattr(record, "extra_fields"):
            log_entry["extra"] = record.extra_fields

        return json.dumps(log_entry, default=str)


class CorrelationLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that automatically includes correlation ID and extra context."""

    def process(
        self, msg: str, kwargs: Dict[str, Any]
    ) -> tuple[str, Dict[str, Any]]:
        """Process the log message to include correlation ID."""
        extra = kwargs.get("extra", {})

        # Add correlation ID
        correlation_id = correlation_id_var.get()
        if correlation_id:
            extra["correlation_id"] = correlation_id

        # Merge with any passed extra fields
        if self.extra:
            extra.update(self.extra)

        # Store extra fields for the formatter
        extra["extra_fields"] = {k: v for k, v in extra.items() if k != "extra_fields"}

        kwargs["extra"] = extra
        return msg, kwargs


def get_logger(name: str, **extra: Any) -> CorrelationLoggerAdapter:
    """Get a logger with correlation ID support.

    Args:
        name: Logger name (typically __name__)
        **extra: Additional context to include in all log messages

    Returns:
        CorrelationLoggerAdapter that includes correlation IDs
    """
    base_logger = logging.getLogger(name)
    return CorrelationLoggerAdapter(base_logger, extra)


def configure_logging(
    level: int = logging.INFO,
    service_name: str = "politician-etl",
    json_format: bool = True,
) -> None:
    """Configure structured logging for the application.

    Args:
        level: Logging level (default: INFO)
        service_name: Service name to include in logs
        json_format: Whether to use JSON format (default: True)
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    if json_format:
        # Use JSON formatter for production
        formatter = StructuredFormatter(service_name=service_name)
    else:
        # Use readable format for development
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | "
            "[%(correlation_id)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


# Convenience function for logging with extra context
def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context: Any,
) -> None:
    """Log a message with additional context fields.

    Args:
        logger: Logger instance
        level: Log level (e.g., logging.INFO)
        message: Log message
        **context: Additional context fields to include
    """
    extra = {"extra_fields": context}
    correlation_id = correlation_id_var.get()
    if correlation_id:
        extra["correlation_id"] = correlation_id
    logger.log(level, message, extra=extra)
