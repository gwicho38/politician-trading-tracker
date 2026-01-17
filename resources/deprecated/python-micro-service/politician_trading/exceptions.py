"""
Custom exception hierarchy for Politician Trading Tracker.

This module defines a hierarchy of exceptions that provide clear error categorization
and context for debugging. All exceptions inherit from PTTError.

Exception Hierarchy:
    PTTError (base)
    ├── ConfigurationError - Invalid or missing configuration
    ├── DatabaseError - Database connection or query failures
    │   ├── ConnectionError - Failed to connect to database
    │   └── QueryError - Query execution failed
    ├── ScrapingError - Web scraping failures
    │   ├── RateLimitError - Rate limited by source
    │   ├── SourceUnavailableError - Source website down/unreachable
    │   └── AuthenticationError - Auth required or failed
    ├── ParseError - Data parsing failures
    │   ├── PDFParseError - PDF parsing failed
    │   ├── HTMLParseError - HTML parsing failed
    │   └── DataValidationError - Parsed data failed validation
    ├── TickerResolutionError - Could not resolve asset to ticker
    ├── WorkflowError - Workflow orchestration failures
    │   ├── JobExecutionError - Individual job failed
    │   └── SchedulingError - Scheduler configuration/execution failed
    └── TradingError - Trading execution failures
        ├── OrderExecutionError - Order could not be executed
        └── InsufficientFundsError - Not enough buying power

Usage:
    from politician_trading.exceptions import ScrapingError, RateLimitError

    try:
        await scrape_source(url)
    except RateLimitError as e:
        logger.warning(f"Rate limited by {e.source}: retry after {e.retry_after}s")
        await asyncio.sleep(e.retry_after)
    except ScrapingError as e:
        logger.error(f"Scraping failed: {e}")
"""

from typing import Any, Optional


class PTTError(Exception):
    """Base exception for all Politician Trading Tracker errors.

    All custom exceptions in this project inherit from PTTError, allowing
    callers to catch all project-specific errors with a single except clause.

    Attributes:
        message: Human-readable error description
        context: Additional context about the error (source, parameters, etc.)
    """

    def __init__(self, message: str, context: Optional[dict[str, Any]] = None) -> None:
        self.message = message
        self.context = context or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.context:
            ctx_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            return f"{self.message} ({ctx_str})"
        return self.message


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigurationError(PTTError):
    """Raised when configuration is invalid or missing.

    Examples:
        - Missing required environment variable
        - Invalid configuration value
        - Incompatible configuration options
    """
    pass


# =============================================================================
# Database Errors
# =============================================================================


class DatabaseError(PTTError):
    """Base class for database-related errors."""
    pass


class ConnectionError(DatabaseError):
    """Failed to connect to the database.

    Attributes:
        host: Database host that was unreachable
        port: Database port
    """

    def __init__(
        self,
        message: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        context = kwargs.pop("context", {})
        if host:
            context["host"] = host
        if port:
            context["port"] = port
        super().__init__(message, context=context)
        self.host = host
        self.port = port


class QueryError(DatabaseError):
    """Database query execution failed.

    Attributes:
        query: The query that failed (may be truncated for large queries)
        table: The table involved, if applicable
    """

    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        table: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        context = kwargs.pop("context", {})
        if table:
            context["table"] = table
        if query:
            # Truncate long queries for readability
            context["query"] = query[:200] + "..." if len(query) > 200 else query
        super().__init__(message, context=context)
        self.query = query
        self.table = table


# =============================================================================
# Scraping Errors
# =============================================================================


class ScrapingError(PTTError):
    """Base class for web scraping errors.

    Attributes:
        source: The data source that failed (e.g., "us_house", "eu_parliament")
        url: The URL that was being scraped
    """

    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        url: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        context = kwargs.pop("context", {})
        if source:
            context["source"] = source
        if url:
            context["url"] = url
        super().__init__(message, context=context)
        self.source = source
        self.url = url


class RateLimitError(ScrapingError):
    """Rate limited by the source website.

    Attributes:
        retry_after: Seconds to wait before retrying (if known)
    """

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
        if retry_after:
            self.context["retry_after"] = retry_after


class SourceUnavailableError(ScrapingError):
    """Source website is down or unreachable.

    Attributes:
        status_code: HTTP status code if available
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(message, **kwargs)
        self.status_code = status_code
        if status_code:
            self.context["status_code"] = status_code


class AuthenticationError(ScrapingError):
    """Authentication required or failed for source."""
    pass


# =============================================================================
# Parse Errors
# =============================================================================


class ParseError(PTTError):
    """Base class for data parsing errors.

    Attributes:
        document_id: ID of the document that failed to parse
        raw_content: Sample of the content that couldn't be parsed
    """

    def __init__(
        self,
        message: str,
        document_id: Optional[str] = None,
        raw_content: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        context = kwargs.pop("context", {})
        if document_id:
            context["document_id"] = document_id
        if raw_content:
            # Include just a sample for debugging
            context["raw_sample"] = raw_content[:100] + "..." if len(raw_content) > 100 else raw_content
        super().__init__(message, context=context)
        self.document_id = document_id
        self.raw_content = raw_content


class PDFParseError(ParseError):
    """Failed to parse a PDF document.

    Attributes:
        page_number: The page that failed, if applicable
    """

    def __init__(
        self,
        message: str,
        page_number: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(message, **kwargs)
        self.page_number = page_number
        if page_number is not None:
            self.context["page"] = page_number


class HTMLParseError(ParseError):
    """Failed to parse HTML content.

    Attributes:
        selector: The CSS/XPath selector that failed to match
    """

    def __init__(
        self,
        message: str,
        selector: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(message, **kwargs)
        self.selector = selector
        if selector:
            self.context["selector"] = selector


class DataValidationError(ParseError):
    """Parsed data failed validation.

    Attributes:
        field: The field that failed validation
        expected: What was expected
        actual: What was received
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        expected: Optional[Any] = None,
        actual: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        context = kwargs.pop("context", {})
        if field:
            context["field"] = field
        if expected is not None:
            context["expected"] = expected
        if actual is not None:
            context["actual"] = actual
        super().__init__(message, context=context, **kwargs)
        self.field = field
        self.expected = expected
        self.actual = actual


# =============================================================================
# Ticker Resolution Errors
# =============================================================================


class TickerResolutionError(PTTError):
    """Could not resolve an asset name to a ticker symbol.

    Attributes:
        asset_name: The asset name that couldn't be resolved
        candidates: Possible ticker candidates that were considered
    """

    def __init__(
        self,
        message: str,
        asset_name: Optional[str] = None,
        candidates: Optional[list[str]] = None,
        **kwargs: Any
    ) -> None:
        context = kwargs.pop("context", {})
        if asset_name:
            context["asset_name"] = asset_name
        if candidates:
            context["candidates"] = candidates
        super().__init__(message, context=context)
        self.asset_name = asset_name
        self.candidates = candidates or []


# =============================================================================
# Workflow Errors
# =============================================================================


class WorkflowError(PTTError):
    """Base class for workflow orchestration errors.

    Attributes:
        job_id: ID of the affected job
        job_type: Type of job (e.g., "us_house", "signal_generation")
    """

    def __init__(
        self,
        message: str,
        job_id: Optional[str] = None,
        job_type: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        context = kwargs.pop("context", {})
        if job_id:
            context["job_id"] = job_id
        if job_type:
            context["job_type"] = job_type
        super().__init__(message, context=context)
        self.job_id = job_id
        self.job_type = job_type


class JobExecutionError(WorkflowError):
    """A job failed during execution.

    Attributes:
        records_processed: Number of records processed before failure
        original_error: The underlying exception that caused the failure
    """

    def __init__(
        self,
        message: str,
        records_processed: int = 0,
        original_error: Optional[Exception] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(message, **kwargs)
        self.records_processed = records_processed
        self.original_error = original_error
        self.context["records_processed"] = records_processed
        if original_error:
            self.context["original_error"] = type(original_error).__name__


class SchedulingError(WorkflowError):
    """Scheduler configuration or execution failed."""
    pass


# =============================================================================
# Trading Errors
# =============================================================================


class TradingError(PTTError):
    """Base class for trading execution errors.

    Attributes:
        ticker: The ticker symbol involved
        order_id: The order ID, if applicable
    """

    def __init__(
        self,
        message: str,
        ticker: Optional[str] = None,
        order_id: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        context = kwargs.pop("context", {})
        if ticker:
            context["ticker"] = ticker
        if order_id:
            context["order_id"] = order_id
        super().__init__(message, context=context)
        self.ticker = ticker
        self.order_id = order_id


class OrderExecutionError(TradingError):
    """Order could not be executed.

    Attributes:
        reject_reason: Reason the order was rejected
    """

    def __init__(
        self,
        message: str,
        reject_reason: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(message, **kwargs)
        self.reject_reason = reject_reason
        if reject_reason:
            self.context["reject_reason"] = reject_reason


class InsufficientFundsError(TradingError):
    """Not enough buying power to execute the order.

    Attributes:
        required: Amount required
        available: Amount available
    """

    def __init__(
        self,
        message: str,
        required: Optional[float] = None,
        available: Optional[float] = None,
        **kwargs: Any
    ) -> None:
        context = kwargs.pop("context", {})
        if required is not None:
            context["required"] = required
        if available is not None:
            context["available"] = available
        super().__init__(message, context=context, **kwargs)
        self.required = required
        self.available = available


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Base
    "PTTError",
    # Configuration
    "ConfigurationError",
    # Database
    "DatabaseError",
    "ConnectionError",
    "QueryError",
    # Scraping
    "ScrapingError",
    "RateLimitError",
    "SourceUnavailableError",
    "AuthenticationError",
    # Parsing
    "ParseError",
    "PDFParseError",
    "HTMLParseError",
    "DataValidationError",
    # Ticker
    "TickerResolutionError",
    # Workflow
    "WorkflowError",
    "JobExecutionError",
    "SchedulingError",
    # Trading
    "TradingError",
    "OrderExecutionError",
    "InsufficientFundsError",
]
