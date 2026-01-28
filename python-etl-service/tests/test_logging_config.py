"""
Tests for structured logging configuration (app/lib/logging_config.py).

Tests:
- Correlation ID management
- Structured formatter
- Logger adapter
"""

import json
import logging
import pytest
from unittest.mock import MagicMock

from app.lib.logging_config import (
    correlation_id_var,
    get_correlation_id,
    set_correlation_id,
    clear_correlation_id,
    StructuredFormatter,
    CorrelationLoggerAdapter,
    get_logger,
    configure_logging,
)


# =============================================================================
# Correlation ID Tests
# =============================================================================

class TestCorrelationId:
    """Tests for correlation ID context management."""

    def setup_method(self):
        """Clear correlation ID before each test."""
        clear_correlation_id()

    def teardown_method(self):
        """Clear correlation ID after each test."""
        clear_correlation_id()

    def test_get_correlation_id_generates_new_when_empty(self):
        """get_correlation_id generates UUID when not set."""
        cid = get_correlation_id()
        assert cid is not None
        assert len(cid) == 36  # UUID format

    def test_get_correlation_id_returns_same_value(self):
        """get_correlation_id returns same value on subsequent calls."""
        cid1 = get_correlation_id()
        cid2 = get_correlation_id()
        assert cid1 == cid2

    def test_set_correlation_id(self):
        """set_correlation_id sets custom value."""
        set_correlation_id("test-correlation-123")
        assert get_correlation_id() == "test-correlation-123"

    def test_clear_correlation_id(self):
        """clear_correlation_id removes the value."""
        set_correlation_id("test-123")
        clear_correlation_id()
        # Should generate new UUID
        cid = get_correlation_id()
        assert cid != "test-123"


# =============================================================================
# StructuredFormatter Tests
# =============================================================================

class TestStructuredFormatter:
    """Tests for JSON structured logging formatter."""

    def test_format_basic_message(self):
        """Formatter produces valid JSON with required fields."""
        formatter = StructuredFormatter(service_name="test-service")
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "Test message"
        assert data["service"] == "test-service"
        assert "timestamp" in data
        assert "source" in data
        assert data["source"]["file"] == "test.py"
        assert data["source"]["line"] == 10

    def test_format_includes_correlation_id(self):
        """Formatter includes correlation ID when set."""
        set_correlation_id("test-correlation-456")
        try:
            formatter = StructuredFormatter()
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="Test",
                args=(),
                exc_info=None,
            )

            output = formatter.format(record)
            data = json.loads(output)

            assert data["correlation_id"] == "test-correlation-456"
        finally:
            clear_correlation_id()

    def test_format_without_correlation_id(self):
        """Formatter works without correlation ID."""
        clear_correlation_id()
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="Warning message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert "correlation_id" not in data
        assert data["level"] == "WARNING"


# =============================================================================
# CorrelationLoggerAdapter Tests
# =============================================================================

class TestCorrelationLoggerAdapter:
    """Tests for the correlation-aware logger adapter."""

    def setup_method(self):
        clear_correlation_id()

    def teardown_method(self):
        clear_correlation_id()

    def test_adapter_adds_correlation_id(self):
        """Adapter includes correlation ID in extra."""
        set_correlation_id("adapter-test-123")

        base_logger = logging.getLogger("test.adapter")
        adapter = CorrelationLoggerAdapter(base_logger, {})

        msg, kwargs = adapter.process("Test message", {})

        assert msg == "Test message"
        assert "extra" in kwargs
        assert kwargs["extra"]["correlation_id"] == "adapter-test-123"

    def test_adapter_merges_extra(self):
        """Adapter merges provided extra with correlation ID."""
        set_correlation_id("merge-test")

        base_logger = logging.getLogger("test.merge")
        adapter = CorrelationLoggerAdapter(base_logger, {"service": "test-svc"})

        msg, kwargs = adapter.process("Test", {"extra": {"custom": "value"}})

        assert kwargs["extra"]["correlation_id"] == "merge-test"
        assert kwargs["extra"]["service"] == "test-svc"


# =============================================================================
# get_logger Tests
# =============================================================================

class TestGetLogger:
    """Tests for the get_logger convenience function."""

    def test_get_logger_returns_adapter(self):
        """get_logger returns a CorrelationLoggerAdapter."""
        logger = get_logger("test.module")
        assert isinstance(logger, CorrelationLoggerAdapter)

    def test_get_logger_with_extra(self):
        """get_logger accepts extra context."""
        logger = get_logger("test.extra", component="worker")
        assert logger.extra.get("component") == "worker"


# =============================================================================
# configure_logging Tests
# =============================================================================

class TestConfigureLogging:
    """Tests for logging configuration."""

    def test_configure_logging_sets_level(self):
        """configure_logging sets the root logger level."""
        configure_logging(level=logging.DEBUG, json_format=False)
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_configure_logging_json_format(self):
        """configure_logging uses JSON formatter when requested."""
        configure_logging(level=logging.INFO, json_format=True)
        root = logging.getLogger()
        # Check that at least one handler uses StructuredFormatter
        json_handlers = [
            h for h in root.handlers
            if isinstance(h.formatter, StructuredFormatter)
        ]
        assert len(json_handlers) > 0
