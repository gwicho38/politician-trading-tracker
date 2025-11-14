"""
Logging Framework for Politician Trading Tracker
Inspired by lsh-framework's logger with Python implementation
Provides structured logging with file and stdout output
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from enum import IntEnum


class LogLevel(IntEnum):
    """Log levels matching Python's logging levels"""

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARN = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class ColoredFormatter(logging.Formatter):
    """Custom formatter with ANSI color codes for terminal output"""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\x1b[36m",  # Cyan
        "INFO": "\x1b[32m",  # Green
        "WARNING": "\x1b[33m",  # Yellow
        "ERROR": "\x1b[31m",  # Red
        "CRITICAL": "\x1b[41m",  # Red background
    }
    RESET = "\x1b[0m"
    DIM = "\x1b[2m"
    MAGENTA = "\x1b[35m"

    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors and sys.stdout.isatty()

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors and structure"""
        # Timestamp
        timestamp = datetime.fromtimestamp(record.created).isoformat()

        # Level name
        level_name = record.levelname

        if self.use_colors:
            # Colored output
            color = self.COLORS.get(level_name, "")
            parts = [
                f"{self.DIM}{timestamp}{self.RESET}",
                f"{color}{level_name.ljust(8)}{self.RESET}",
            ]

            # Context (logger name)
            if record.name != "root":
                parts.append(f"{self.MAGENTA}[{record.name}]{self.RESET}")

            # Message
            parts.append(record.getMessage())

            # Metadata (if present)
            if hasattr(record, "metadata") and record.metadata:
                metadata_str = json.dumps(record.metadata)
                parts.append(f"{self.DIM}{metadata_str}{self.RESET}")

            return " ".join(parts)
        else:
            # Plain text output
            parts = [
                timestamp,
                level_name.ljust(8),
            ]

            if record.name != "root":
                parts.append(f"[{record.name}]")

            parts.append(record.getMessage())

            if hasattr(record, "metadata") and record.metadata:
                parts.append(json.dumps(record.metadata))

            return " ".join(parts)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Add metadata if present
        if hasattr(record, "metadata") and record.metadata:
            log_data["metadata"] = record.metadata

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Add source location
        log_data["source"] = {
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
        }

        return json.dumps(log_data)


class PTTLogger:
    """
    Politician Trading Tracker Logger
    Provides structured logging with file and stdout output
    """

    def __init__(
        self,
        name: str = "politician_trading",
        level: Optional[str] = None,
        log_dir: Optional[Path] = None,
        enable_file_logging: bool = True,
        enable_json: bool = False,
        enable_colors: bool = True,
    ):
        """
        Initialize logger

        Args:
            name: Logger name (context)
            level: Log level (DEBUG, INFO, WARN, ERROR, CRITICAL)
            log_dir: Directory for log files (default: logs/)
            enable_file_logging: Enable file output
            enable_json: Use JSON format for logs
            enable_colors: Use ANSI colors for console output
        """
        self.logger = logging.getLogger(name)

        # Get log level from env or parameter
        if level is None:
            level = os.getenv("LOG_LEVEL", "INFO").upper()

        self.logger.setLevel(getattr(logging, level, logging.INFO))

        # Clear existing handlers
        self.logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.logger.level)

        if enable_json:
            console_handler.setFormatter(JSONFormatter())
        else:
            console_handler.setFormatter(ColoredFormatter(use_colors=enable_colors))

        self.logger.addHandler(console_handler)

        # File handler
        if enable_file_logging:
            if log_dir is None:
                # Default to logs/ directory in project root
                project_root = Path(__file__).parent.parent.parent.parent
                log_dir = project_root / "logs"

            log_dir.mkdir(parents=True, exist_ok=True)

            # Create dated log file
            log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(self.logger.level)

            # Always use JSON for file logs for easier parsing
            file_handler.setFormatter(JSONFormatter())
            self.logger.addHandler(file_handler)

            # Also create a latest.log symlink
            latest_log = log_dir / "latest.log"
            if latest_log.exists() or latest_log.is_symlink():
                latest_log.unlink()
            try:
                latest_log.symlink_to(log_file.name)
            except (OSError, NotImplementedError):
                # Symlinks may not be supported on all systems
                pass

    def child(self, context: str) -> "PTTLogger":
        """
        Create a child logger with additional context

        Args:
            context: Additional context to append to logger name

        Returns:
            New PTTLogger instance with extended context
        """
        current_name = self.logger.name
        new_name = f"{current_name}:{context}"

        child_logger = PTTLogger(
            name=new_name,
            level=logging.getLevelName(self.logger.level),
            enable_file_logging=False,  # Reuse parent's file handler
            enable_json=False,
            enable_colors=True,
        )

        # Copy parent's handlers
        for handler in self.logger.handlers:
            child_logger.logger.addHandler(handler)

        return child_logger

    def _log_with_metadata(
        self, level: int, message: str, metadata: Optional[Dict[str, Any]] = None
    ):
        """Internal method to log with metadata"""
        extra = {"metadata": metadata} if metadata else {}
        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Log debug message"""
        self._log_with_metadata(logging.DEBUG, message, metadata)

    def info(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Log info message"""
        self._log_with_metadata(logging.INFO, message, metadata)

    def warn(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Log warning message"""
        self._log_with_metadata(logging.WARNING, message, metadata)

    def warning(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Alias for warn"""
        self.warn(message, metadata)

    def error(
        self,
        message: str,
        error: Optional[Exception] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log error message"""
        extra = {"metadata": metadata} if metadata else {}
        self.logger.error(message, exc_info=error, extra=extra)

    def critical(
        self,
        message: str,
        error: Optional[Exception] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log critical message"""
        extra = {"metadata": metadata} if metadata else {}
        self.logger.critical(message, exc_info=error, extra=extra)

    def exception(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Log exception with traceback"""
        extra = {"metadata": metadata} if metadata else {}
        self.logger.exception(message, extra=extra)


# Global logger instance
_default_logger: Optional[PTTLogger] = None


def get_logger(name: Optional[str] = None, level: Optional[str] = None, **kwargs) -> PTTLogger:
    """
    Get or create a logger instance

    Args:
        name: Logger name (context). If None, returns default logger
        level: Log level override
        **kwargs: Additional arguments passed to PTTLogger constructor

    Returns:
        PTTLogger instance
    """
    global _default_logger

    if name is None:
        if _default_logger is None:
            _default_logger = PTTLogger(level=level, **kwargs)
        return _default_logger

    return PTTLogger(name=name, level=level, **kwargs)


# Convenience function to create child loggers
def create_logger(context: str, level: Optional[str] = None) -> PTTLogger:
    """
    Create a logger with specific context

    Args:
        context: Logger context/name
        level: Log level

    Returns:
        PTTLogger instance
    """
    return PTTLogger(name=f"politician_trading:{context}", level=level)


# Default logger
logger = get_logger()
