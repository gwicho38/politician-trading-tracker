"""
Type definitions for Politician Trading Tracker.

This module provides TypedDict definitions for common data structures used throughout
the codebase. Using TypedDicts instead of Dict[str, Any] improves:

1. Type safety - catch key typos and type mismatches at development time
2. IDE support - autocompletion and inline documentation
3. Code clarity - explicit structure documentation

Usage:
    from politician_trading.types import CollectionResult, JobResult

    async def collect_data() -> CollectionResult:
        return {
            "started_at": datetime.utcnow().isoformat(),
            "jobs": {...},
            "summary": {...},
        }
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional, TypedDict, Union


# =============================================================================
# Workflow Result Types
# =============================================================================


class JobSummary(TypedDict, total=False):
    """Summary statistics for a single job execution.

    Attributes:
        total_new_disclosures: Number of new disclosures found
        total_updated_disclosures: Number of existing disclosures updated
        errors: List of error messages encountered
    """
    total_new_disclosures: int
    total_updated_disclosures: int
    errors: List[str]


class JobResult(TypedDict, total=False):
    """Result from a single data collection job.

    Attributes:
        status: Job status ("success", "partial", "failed")
        new_disclosures: Count of new disclosures
        updated_disclosures: Count of updated disclosures
        records_processed: Total records processed
        errors: List of error messages
        duration_seconds: How long the job took
        source: Data source identifier
    """
    status: str
    new_disclosures: int
    updated_disclosures: int
    records_processed: int
    errors: List[str]
    duration_seconds: float
    source: str


class CollectionResult(TypedDict):
    """Result from a full collection workflow.

    Attributes:
        started_at: ISO timestamp when collection started
        completed_at: ISO timestamp when collection finished
        jobs: Results from each individual job
        summary: Aggregated statistics across all jobs
    """
    started_at: str
    completed_at: str
    jobs: dict[str, JobResult]
    summary: JobSummary


class QuickCheckResult(TypedDict):
    """Result from a quick status check.

    Attributes:
        database_connected: Whether database is reachable
        last_collection: Timestamp of most recent data collection
        disclosure_count: Total disclosures in database
        politician_count: Total politicians in database
        sources_status: Health status per data source
    """
    database_connected: bool
    last_collection: Optional[str]
    disclosure_count: int
    politician_count: int
    sources_status: dict[str, str]


# =============================================================================
# Scraper Result Types
# =============================================================================


class ScrapedDisclosure(TypedDict, total=False):
    """Raw disclosure data as scraped from a source.

    This represents the intermediate format between raw HTML/PDF
    and the TradingDisclosure model.

    Attributes:
        politician_name: Full name of the politician
        politician_id: Internal ID if known
        transaction_date: Date of the transaction
        disclosure_date: Date disclosed/filed
        transaction_type: "purchase", "sale", etc.
        asset_name: Name of the asset
        asset_ticker: Stock ticker if resolved
        amount_min: Lower bound of amount range
        amount_max: Upper bound of amount range
        source_url: URL of the disclosure document
        source_document_id: Document identifier
        raw_text: Original text from source
    """
    politician_name: str
    politician_id: Optional[str]
    transaction_date: str
    disclosure_date: str
    transaction_type: str
    asset_name: str
    asset_ticker: Optional[str]
    amount_min: Optional[float]
    amount_max: Optional[float]
    source_url: str
    source_document_id: Optional[str]
    raw_text: Optional[str]


class ParsedPDFResult(TypedDict, total=False):
    """Result from parsing a PDF disclosure document.

    Attributes:
        transactions: List of extracted transactions
        capital_gains: List of capital gains (if any)
        holdings: List of asset holdings (if any)
        metadata: Document metadata (filer info, dates, etc.)
        parse_confidence: Overall confidence in the parse (0.0-1.0)
        errors: Any errors during parsing
        raw_text: Full extracted text
    """
    transactions: List[ScrapedDisclosure]
    capital_gains: List[dict[str, Any]]
    holdings: List[dict[str, Any]]
    metadata: dict[str, Any]
    parse_confidence: float
    errors: List[str]
    raw_text: str


# =============================================================================
# Database Query Types
# =============================================================================


class PoliticianQuery(TypedDict, total=False):
    """Parameters for querying politicians.

    Attributes:
        role: Filter by political role
        party: Filter by party
        state: Filter by state (US) or country (international)
        active_only: Only return currently serving politicians
        limit: Maximum results to return
        offset: Pagination offset
    """
    role: str
    party: str
    state: str
    active_only: bool
    limit: int
    offset: int


class DisclosureQuery(TypedDict, total=False):
    """Parameters for querying disclosures.

    Attributes:
        politician_id: Filter by politician
        ticker: Filter by asset ticker
        transaction_type: Filter by transaction type
        date_from: Start date filter
        date_to: End date filter
        status: Filter by processing status
        limit: Maximum results
        offset: Pagination offset
    """
    politician_id: str
    ticker: str
    transaction_type: str
    date_from: str
    date_to: str
    status: str
    limit: int
    offset: int


class DatabaseStats(TypedDict):
    """Database statistics.

    Attributes:
        total_politicians: Count of politician records
        total_disclosures: Count of disclosure records
        disclosures_by_status: Counts per status
        disclosures_by_source: Counts per data source
        latest_disclosure_date: Most recent disclosure
        oldest_disclosure_date: Oldest disclosure
    """
    total_politicians: int
    total_disclosures: int
    disclosures_by_status: dict[str, int]
    disclosures_by_source: dict[str, int]
    latest_disclosure_date: Optional[str]
    oldest_disclosure_date: Optional[str]


# =============================================================================
# Signal Generation Types
# =============================================================================


class SignalFeatures(TypedDict, total=False):
    """Features used to generate a trading signal.

    Attributes:
        politician_count: Number of politicians trading this asset
        buy_count: Number of buy transactions
        sell_count: Number of sell transactions
        total_volume: Estimated total transaction volume
        avg_transaction_size: Average transaction amount
        days_since_first: Days since first politician transaction
        historical_return_avg: Average return after similar signals
        sector: Asset sector
        market_cap: Market capitalization
    """
    politician_count: int
    buy_count: int
    sell_count: int
    total_volume: float
    avg_transaction_size: float
    days_since_first: int
    historical_return_avg: Optional[float]
    sector: Optional[str]
    market_cap: Optional[str]


class SignalOutput(TypedDict):
    """Output from signal generation.

    Attributes:
        ticker: Stock ticker
        signal_type: "buy", "sell", "hold"
        confidence: Confidence score 0.0-1.0
        features: Features that contributed to the signal
        disclosure_ids: IDs of related disclosures
        generated_at: When the signal was generated
    """
    ticker: str
    signal_type: str
    confidence: float
    features: SignalFeatures
    disclosure_ids: List[str]
    generated_at: str


# =============================================================================
# Trading Execution Types
# =============================================================================


class OrderRequest(TypedDict, total=False):
    """Request to execute a trading order.

    Attributes:
        ticker: Stock ticker to trade
        side: "buy" or "sell"
        quantity: Number of shares
        order_type: "market", "limit", "stop", "stop_limit"
        limit_price: Limit price (for limit orders)
        stop_price: Stop price (for stop orders)
        time_in_force: "day", "gtc", "ioc", "fok"
    """
    ticker: str
    side: str
    quantity: int
    order_type: str
    limit_price: Optional[float]
    stop_price: Optional[float]
    time_in_force: str


class OrderResponse(TypedDict, total=False):
    """Response from order execution.

    Attributes:
        order_id: Unique order identifier
        status: Order status
        filled_quantity: Shares filled so far
        filled_avg_price: Average fill price
        submitted_at: When order was submitted
        error: Error message if failed
    """
    order_id: str
    status: str
    filled_quantity: int
    filled_avg_price: Optional[float]
    submitted_at: str
    error: Optional[str]


class PortfolioSummary(TypedDict):
    """Summary of portfolio state.

    Attributes:
        cash: Available cash
        portfolio_value: Total portfolio value
        buying_power: Available buying power
        positions: List of current positions
        total_return_pct: Total return percentage
        day_return_pct: Today's return percentage
    """
    cash: float
    portfolio_value: float
    buying_power: float
    positions: List[dict[str, Any]]
    total_return_pct: Optional[float]
    day_return_pct: Optional[float]


# =============================================================================
# Monitoring Types
# =============================================================================


class HealthStatus(TypedDict):
    """Health status for a component.

    Attributes:
        status: "healthy", "degraded", "unhealthy"
        last_check: When last checked
        message: Human-readable status message
        metrics: Component-specific metrics
    """
    status: str
    last_check: str
    message: str
    metrics: dict[str, Any]


class ScraperHealth(TypedDict):
    """Health status for a scraper.

    Attributes:
        scraper_name: Name of the scraper
        status: Current health status
        last_success: Last successful run
        last_failure: Last failed run
        success_rate: Success rate over window
        avg_duration: Average run duration
        error_count: Recent error count
    """
    scraper_name: str
    status: str
    last_success: Optional[str]
    last_failure: Optional[str]
    success_rate: float
    avg_duration: float
    error_count: int


class AlertInfo(TypedDict):
    """Alert notification info.

    Attributes:
        alert_id: Unique alert identifier
        severity: "info", "warning", "error", "critical"
        source: Component that raised the alert
        message: Alert message
        timestamp: When alert was raised
        acknowledged: Whether alert has been acknowledged
    """
    alert_id: str
    severity: str
    source: str
    message: str
    timestamp: str
    acknowledged: bool


# =============================================================================
# API Response Types
# =============================================================================


class APIError(TypedDict):
    """Standard API error response.

    Attributes:
        error: Error type/code
        message: Human-readable error message
        details: Additional error details
    """
    error: str
    message: str
    details: Optional[dict[str, Any]]


class PaginatedResponse(TypedDict):
    """Standard paginated response.

    Attributes:
        data: List of items
        total: Total count
        limit: Items per page
        offset: Current offset
        has_more: Whether more items exist
    """
    data: List[Any]
    total: int
    limit: int
    offset: int
    has_more: bool


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Workflow
    "JobSummary",
    "JobResult",
    "CollectionResult",
    "QuickCheckResult",
    # Scraper
    "ScrapedDisclosure",
    "ParsedPDFResult",
    # Database
    "PoliticianQuery",
    "DisclosureQuery",
    "DatabaseStats",
    # Signals
    "SignalFeatures",
    "SignalOutput",
    # Trading
    "OrderRequest",
    "OrderResponse",
    "PortfolioSummary",
    # Monitoring
    "HealthStatus",
    "ScraperHealth",
    "AlertInfo",
    # API
    "APIError",
    "PaginatedResponse",
]
