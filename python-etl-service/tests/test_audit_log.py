"""
Tests for Audit Logging Module
"""

import logging
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.lib.audit_log import (
    AuditAction,
    AuditContext,
    AuditEvent,
    audit_log,
    get_client_ip,
    log_audit_event,
)


class TestAuditEvent:
    """Tests for AuditEvent dataclass."""

    def test_creates_with_defaults(self):
        """AuditEvent creates with sensible defaults."""
        event = AuditEvent(action=AuditAction.DATA_READ)

        assert event.action == AuditAction.DATA_READ
        assert event.success is True
        assert event.resource_type is None
        assert event.resource_id is None
        assert event.details == {}
        assert isinstance(event.timestamp, datetime)

    def test_creates_with_all_fields(self):
        """AuditEvent accepts all fields."""
        event = AuditEvent(
            action=AuditAction.DATA_MODIFY,
            success=False,
            resource_type="trading_disclosure",
            resource_id="123",
            actor_ip="192.168.1.1",
            actor_id="user_456",
            correlation_id="corr-789",
            duration_ms=42.5,
            details={"field": "ticker", "new_value": "AAPL"},
            error_message="Validation failed",
        )

        assert event.action == AuditAction.DATA_MODIFY
        assert event.success is False
        assert event.resource_type == "trading_disclosure"
        assert event.resource_id == "123"
        assert event.actor_ip == "192.168.1.1"
        assert event.actor_id == "user_456"
        assert event.duration_ms == 42.5
        assert event.error_message == "Validation failed"

    def test_to_dict_minimal(self):
        """to_dict returns minimal dict for basic event."""
        event = AuditEvent(action=AuditAction.AUTH_SUCCESS)
        result = event.to_dict()

        assert result["audit_event"] is True
        assert result["action"] == "auth.success"
        assert result["success"] is True
        assert "timestamp" in result

    def test_to_dict_full(self):
        """to_dict includes all populated fields."""
        event = AuditEvent(
            action=AuditAction.DATA_MODIFY,
            resource_type="disclosure",
            resource_id="123",
            actor_ip="10.0.0.1",
            duration_ms=100.567,
            details={"changed": "ticker"},
            error_message="Test error",
        )
        result = event.to_dict()

        assert result["resource_type"] == "disclosure"
        assert result["resource_id"] == "123"
        assert result["actor_ip"] == "10.0.0.1"
        assert result["duration_ms"] == 100.57  # Rounded to 2 decimal places
        assert result["details"] == {"changed": "ticker"}
        assert result["error"] == "Test error"


class TestGetClientIp:
    """Tests for get_client_ip function."""

    def test_returns_none_for_none_request(self):
        """Returns None when request is None."""
        assert get_client_ip(None) is None

    def test_extracts_from_x_forwarded_for(self):
        """Extracts first IP from X-Forwarded-For header."""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "10.0.0.1, 10.0.0.2, 10.0.0.3"}

        assert get_client_ip(request) == "10.0.0.1"

    def test_extracts_from_x_real_ip(self):
        """Extracts IP from X-Real-IP header."""
        request = MagicMock()
        request.headers = {"X-Real-IP": "192.168.1.1"}

        assert get_client_ip(request) == "192.168.1.1"

    def test_falls_back_to_client_host(self):
        """Falls back to request.client.host."""
        request = MagicMock()
        request.headers = {}
        request.client.host = "127.0.0.1"

        assert get_client_ip(request) == "127.0.0.1"

    def test_prefers_x_forwarded_for_over_x_real_ip(self):
        """X-Forwarded-For takes precedence over X-Real-IP."""
        request = MagicMock()
        request.headers = {
            "X-Forwarded-For": "10.0.0.1",
            "X-Real-IP": "192.168.1.1",
        }

        assert get_client_ip(request) == "10.0.0.1"


class TestLogAuditEvent:
    """Tests for log_audit_event function."""

    def test_creates_and_logs_event(self):
        """Creates event and logs it."""
        with patch("app.lib.audit_log.logger") as mock_logger:
            event = log_audit_event(
                action=AuditAction.DATA_READ,
                resource_type="disclosure",
                resource_id="123",
            )

        assert isinstance(event, AuditEvent)
        assert event.action == AuditAction.DATA_READ
        assert event.success is True
        mock_logger.info.assert_called_once()

    def test_logs_failure_at_warning_level(self):
        """Failed events are logged at warning level."""
        with patch("app.lib.audit_log.logger") as mock_logger:
            log_audit_event(
                action=AuditAction.DATA_MODIFY,
                success=False,
                error_message="Failed to modify",
            )

        mock_logger.warning.assert_called_once()

    def test_logs_auth_failure_at_warning_level(self):
        """Auth failures are logged at warning level."""
        with patch("app.lib.audit_log.logger") as mock_logger:
            log_audit_event(
                action=AuditAction.AUTH_FAILURE,
                success=True,  # Even when "success" is True
            )

        mock_logger.warning.assert_called_once()

    def test_extracts_ip_from_request(self):
        """Extracts actor IP from request object."""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "10.0.0.5"}

        with patch("app.lib.audit_log.logger"):
            event = log_audit_event(
                action=AuditAction.DATA_READ,
                request=request,
            )

        assert event.actor_ip == "10.0.0.5"

    def test_includes_correlation_id(self):
        """Includes correlation ID from context."""
        with patch("app.lib.audit_log.get_correlation_id", return_value="test-corr-id"):
            with patch("app.lib.audit_log.logger"):
                event = log_audit_event(action=AuditAction.DATA_READ)

        assert event.correlation_id == "test-corr-id"


class TestAuditLogDecorator:
    """Tests for audit_log decorator."""

    @pytest.mark.asyncio
    async def test_logs_successful_async_function(self):
        """Decorator logs successful async function execution."""
        @audit_log(AuditAction.DATA_READ, resource_type="test_resource")
        async def test_func():
            return "success"

        with patch("app.lib.audit_log.log_audit_event") as mock_log:
            result = await test_func()

        assert result == "success"
        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args[1]
        assert call_kwargs["action"] == AuditAction.DATA_READ
        assert call_kwargs["success"] is True
        assert call_kwargs["resource_type"] == "test_resource"

    @pytest.mark.asyncio
    async def test_logs_failed_async_function(self):
        """Decorator logs failed async function execution."""
        @audit_log(AuditAction.DATA_MODIFY)
        async def test_func():
            raise ValueError("Test error")

        with patch("app.lib.audit_log.log_audit_event") as mock_log:
            with pytest.raises(ValueError):
                await test_func()

        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args[1]
        assert call_kwargs["success"] is False
        assert call_kwargs["error_message"] == "Test error"

    def test_logs_successful_sync_function(self):
        """Decorator logs successful sync function execution."""
        @audit_log(AuditAction.DATA_CREATE)
        def test_func():
            return "created"

        with patch("app.lib.audit_log.log_audit_event") as mock_log:
            result = test_func()

        assert result == "created"
        mock_log.assert_called_once()
        assert mock_log.call_args[1]["success"] is True

    def test_logs_failed_sync_function(self):
        """Decorator logs failed sync function execution."""
        @audit_log(AuditAction.DATA_DELETE)
        def test_func():
            raise RuntimeError("Delete failed")

        with patch("app.lib.audit_log.log_audit_event") as mock_log:
            with pytest.raises(RuntimeError):
                test_func()

        assert mock_log.call_args[1]["success"] is False

    @pytest.mark.asyncio
    async def test_extracts_resource_id(self):
        """Decorator extracts resource ID using provided function."""
        @audit_log(
            AuditAction.DATA_READ,
            get_resource_id=lambda resource_id, **kw: resource_id,
        )
        async def test_func(resource_id: str):
            return f"read {resource_id}"

        with patch("app.lib.audit_log.log_audit_event") as mock_log:
            await test_func(resource_id="res-123")

        assert mock_log.call_args[1]["resource_id"] == "res-123"

    @pytest.mark.asyncio
    async def test_extracts_details(self):
        """Decorator extracts details using provided function."""
        @audit_log(
            AuditAction.DATA_MODIFY,
            get_details=lambda **kw: {"field": kw.get("field")},
        )
        async def test_func(field: str = "default"):
            return "modified"

        with patch("app.lib.audit_log.log_audit_event") as mock_log:
            await test_func(field="ticker")

        assert mock_log.call_args[1]["details"] == {"field": "ticker"}

    @pytest.mark.asyncio
    async def test_measures_duration(self):
        """Decorator measures operation duration."""
        @audit_log(AuditAction.DATA_READ)
        async def test_func():
            import asyncio
            await asyncio.sleep(0.05)  # 50ms
            return "done"

        with patch("app.lib.audit_log.log_audit_event") as mock_log:
            await test_func()

        duration = mock_log.call_args[1]["duration_ms"]
        assert duration >= 40  # Allow some margin


class TestAuditContext:
    """Tests for AuditContext context manager."""

    def test_logs_on_exit(self):
        """Logs audit event when context exits."""
        with patch("app.lib.audit_log.log_audit_event") as mock_log:
            with AuditContext(AuditAction.DATA_READ) as ctx:
                ctx.resource_id = "123"

        mock_log.assert_called_once()
        assert mock_log.call_args[1]["resource_id"] == "123"
        assert mock_log.call_args[1]["success"] is True

    def test_logs_failure_on_exception(self):
        """Logs failure when exception occurs."""
        with patch("app.lib.audit_log.log_audit_event") as mock_log:
            with pytest.raises(ValueError):
                with AuditContext(AuditAction.DATA_MODIFY) as ctx:
                    raise ValueError("Test error")

        assert mock_log.call_args[1]["success"] is False
        assert mock_log.call_args[1]["error_message"] == "Test error"

    def test_allows_setting_details(self):
        """Allows adding details during execution."""
        with patch("app.lib.audit_log.log_audit_event") as mock_log:
            with AuditContext(AuditAction.DATA_MODIFY, resource_type="disclosure") as ctx:
                ctx.details["old_value"] = "AAPL"
                ctx.details["new_value"] = "GOOG"

        details = mock_log.call_args[1]["details"]
        assert details["old_value"] == "AAPL"
        assert details["new_value"] == "GOOG"

    def test_measures_duration(self):
        """Measures duration of context execution."""
        with patch("app.lib.audit_log.log_audit_event") as mock_log:
            with AuditContext(AuditAction.DATA_READ):
                time.sleep(0.05)  # 50ms

        duration = mock_log.call_args[1]["duration_ms"]
        assert duration >= 40  # Allow some margin


class TestAuditActionEnum:
    """Tests for AuditAction enum."""

    def test_has_auth_actions(self):
        """Has authentication-related actions."""
        assert AuditAction.AUTH_SUCCESS.value == "auth.success"
        assert AuditAction.AUTH_FAILURE.value == "auth.failure"
        assert AuditAction.AUTH_ADMIN_ACCESS.value == "auth.admin_access"

    def test_has_data_actions(self):
        """Has data operation actions."""
        assert AuditAction.DATA_CREATE.value == "data.create"
        assert AuditAction.DATA_READ.value == "data.read"
        assert AuditAction.DATA_MODIFY.value == "data.modify"
        assert AuditAction.DATA_DELETE.value == "data.delete"

    def test_has_model_actions(self):
        """Has ML model actions."""
        assert AuditAction.MODEL_TRAIN.value == "model.train"
        assert AuditAction.MODEL_ACTIVATE.value == "model.activate"

    def test_has_etl_actions(self):
        """Has ETL operation actions."""
        assert AuditAction.ETL_TRIGGER.value == "etl.trigger"
        assert AuditAction.ETL_COMPLETE.value == "etl.complete"
        assert AuditAction.ETL_FAILURE.value == "etl.failure"

    def test_has_error_report_actions(self):
        """Has error report actions."""
        assert AuditAction.ERROR_REPORT_PROCESS.value == "error_report.process"
        assert AuditAction.ERROR_REPORT_APPLY.value == "error_report.apply"
        assert AuditAction.ERROR_REPORT_REANALYZE.value == "error_report.reanalyze"
