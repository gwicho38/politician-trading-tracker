"""
Audit Logging Module

Provides structured audit logging for sensitive operations with support for:
- Tracking who performed what action and when
- Recording success/failure status
- Capturing relevant context (IP, user, resource IDs)
- Supporting compliance and security monitoring

Usage:
    from app.lib.audit_log import audit_log, AuditAction

    @audit_log(AuditAction.DATA_MODIFY, resource_type="trading_disclosure")
    async def force_apply_correction(request: ForceApplyRequest):
        ...

    # Or manually:
    log_audit_event(
        action=AuditAction.DATA_MODIFY,
        resource_type="trading_disclosure",
        resource_id="123",
        success=True,
        details={"field": "ticker", "old_value": "AAPL", "new_value": "GOOG"},
    )
"""

import functools
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from fastapi import Request

from app.lib.logging_config import get_correlation_id

logger = logging.getLogger("audit")


class AuditAction(str, Enum):
    """Types of auditable actions."""

    # Authentication & Authorization
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    AUTH_ADMIN_ACCESS = "auth.admin_access"

    # Data Operations
    DATA_CREATE = "data.create"
    DATA_READ = "data.read"
    DATA_MODIFY = "data.modify"
    DATA_DELETE = "data.delete"

    # Model Operations
    MODEL_TRAIN = "model.train"
    MODEL_ACTIVATE = "model.activate"
    MODEL_PREDICT = "model.predict"

    # ETL Operations
    ETL_TRIGGER = "etl.trigger"
    ETL_COMPLETE = "etl.complete"
    ETL_FAILURE = "etl.failure"

    # Error Corrections
    ERROR_REPORT_PROCESS = "error_report.process"
    ERROR_REPORT_APPLY = "error_report.apply"
    ERROR_REPORT_REANALYZE = "error_report.reanalyze"

    # System Operations
    SYSTEM_CONFIG_CHANGE = "system.config_change"
    SYSTEM_RATE_LIMIT = "system.rate_limit"


@dataclass
class AuditEvent:
    """Represents an auditable event."""

    action: AuditAction
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool = True
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    actor_ip: Optional[str] = None
    actor_id: Optional[str] = None
    correlation_id: Optional[str] = None
    duration_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        result = {
            "audit_event": True,
            "action": self.action.value,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
        }

        if self.resource_type:
            result["resource_type"] = self.resource_type
        if self.resource_id:
            result["resource_id"] = self.resource_id
        if self.actor_ip:
            result["actor_ip"] = self.actor_ip
        if self.actor_id:
            result["actor_id"] = self.actor_id
        if self.correlation_id:
            result["correlation_id"] = self.correlation_id
        if self.duration_ms is not None:
            result["duration_ms"] = round(self.duration_ms, 2)
        if self.details:
            result["details"] = self.details
        if self.error_message:
            result["error"] = self.error_message

        return result


def get_client_ip(request: Optional[Request]) -> Optional[str]:
    """Extract client IP from request, handling proxies."""
    if not request:
        return None

    # Check forwarded headers
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    if request.client:
        return request.client.host

    return None


def log_audit_event(
    action: AuditAction,
    success: bool = True,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    actor_ip: Optional[str] = None,
    actor_id: Optional[str] = None,
    duration_ms: Optional[float] = None,
    details: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    request: Optional[Request] = None,
) -> AuditEvent:
    """
    Log an audit event.

    Args:
        action: The type of action being audited
        success: Whether the action succeeded
        resource_type: Type of resource affected (e.g., "trading_disclosure")
        resource_id: ID of the affected resource
        actor_ip: IP address of the actor (extracted from request if not provided)
        actor_id: ID of the actor (user ID, API key prefix, etc.)
        duration_ms: How long the operation took
        details: Additional context about the action
        error_message: Error message if action failed
        request: FastAPI request object for extracting IP

    Returns:
        The created AuditEvent
    """
    # Extract IP from request if not provided
    if not actor_ip and request:
        actor_ip = get_client_ip(request)

    event = AuditEvent(
        action=action,
        success=success,
        resource_type=resource_type,
        resource_id=resource_id,
        actor_ip=actor_ip,
        actor_id=actor_id,
        correlation_id=get_correlation_id(),
        duration_ms=duration_ms,
        details=details or {},
        error_message=error_message,
    )

    # Log with appropriate level based on success and action type
    log_data = event.to_dict()

    if not success:
        logger.warning("Audit: %s failed", action.value, extra={"extra_fields": log_data})
    elif action in (
        AuditAction.AUTH_FAILURE,
        AuditAction.SYSTEM_RATE_LIMIT,
        AuditAction.ETL_FAILURE,
    ):
        logger.warning("Audit: %s", action.value, extra={"extra_fields": log_data})
    elif action in (
        AuditAction.DATA_MODIFY,
        AuditAction.DATA_DELETE,
        AuditAction.MODEL_ACTIVATE,
        AuditAction.MODEL_TRAIN,
        AuditAction.ERROR_REPORT_APPLY,
        AuditAction.AUTH_ADMIN_ACCESS,
    ):
        # Sensitive operations logged at INFO level but flagged
        logger.info("Audit: %s", action.value, extra={"extra_fields": log_data})
    else:
        logger.info("Audit: %s", action.value, extra={"extra_fields": log_data})

    return event


# Type variable for generic decorator
F = TypeVar("F", bound=Callable[..., Any])


def audit_log(
    action: AuditAction,
    resource_type: Optional[str] = None,
    get_resource_id: Optional[Callable[..., str]] = None,
    get_details: Optional[Callable[..., Dict[str, Any]]] = None,
) -> Callable[[F], F]:
    """
    Decorator for automatic audit logging of endpoint handlers.

    Args:
        action: The audit action type
        resource_type: Type of resource (e.g., "trading_disclosure")
        get_resource_id: Function to extract resource ID from args/kwargs
        get_details: Function to extract additional details from args/kwargs

    Example:
        @router.post("/models/{model_id}/activate")
        @audit_log(
            AuditAction.MODEL_ACTIVATE,
            resource_type="ml_model",
            get_resource_id=lambda model_id, **kw: model_id,
        )
        async def activate_model(model_id: str):
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            request = kwargs.get("request")

            # Try to extract resource ID
            resource_id = None
            if get_resource_id:
                try:
                    resource_id = get_resource_id(*args, **kwargs)
                except Exception:
                    pass

            # Try to extract details
            details = {}
            if get_details:
                try:
                    details = get_details(*args, **kwargs) or {}
                except Exception:
                    pass

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                log_audit_event(
                    action=action,
                    success=True,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    duration_ms=duration_ms,
                    details=details,
                    request=request,
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000

                log_audit_event(
                    action=action,
                    success=False,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    duration_ms=duration_ms,
                    details=details,
                    error_message=str(e),
                    request=request,
                )

                raise

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            request = kwargs.get("request")

            # Try to extract resource ID
            resource_id = None
            if get_resource_id:
                try:
                    resource_id = get_resource_id(*args, **kwargs)
                except Exception:
                    pass

            # Try to extract details
            details = {}
            if get_details:
                try:
                    details = get_details(*args, **kwargs) or {}
                except Exception:
                    pass

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                log_audit_event(
                    action=action,
                    success=True,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    duration_ms=duration_ms,
                    details=details,
                    request=request,
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000

                log_audit_event(
                    action=action,
                    success=False,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    duration_ms=duration_ms,
                    details=details,
                    error_message=str(e),
                    request=request,
                )

                raise

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


class AuditContext:
    """
    Context manager for audit logging with automatic timing.

    Example:
        with AuditContext(AuditAction.DATA_MODIFY, resource_type="disclosure") as ctx:
            ctx.resource_id = "123"
            # ... perform operation ...
            ctx.details["changes"] = {"field": "value"}
    """

    def __init__(
        self,
        action: AuditAction,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        request: Optional[Request] = None,
    ):
        self.action = action
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.request = request
        self.details: Dict[str, Any] = {}
        self.success = True
        self.error_message: Optional[str] = None
        self._start_time: float = 0

    def __enter__(self) -> "AuditContext":
        self._start_time = time.time()
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> bool:
        duration_ms = (time.time() - self._start_time) * 1000

        if exc_val:
            self.success = False
            self.error_message = str(exc_val)

        log_audit_event(
            action=self.action,
            success=self.success,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            duration_ms=duration_ms,
            details=self.details,
            error_message=self.error_message,
            request=self.request,
        )

        return False  # Don't suppress exceptions
