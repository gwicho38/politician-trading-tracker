"""
Status string constants for various workflows and states.

These constants provide consistent status values across the application.
"""


class JobStatus:
    """Job execution status values."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SUCCESS = "success"
    ERROR = "error"
    PAUSED = "paused"
    CANCELED = "canceled"


class OrderStatus:
    """Trading order status values (Alpaca-compatible)."""

    # Pre-submission statuses
    PENDING_NEW = "pending_new"

    # Submission statuses
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    PENDING_CANCEL = "pending_cancel"
    PENDING_REPLACE = "pending_replace"

    # Terminal statuses
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    REPLACED = "replaced"

    # Alpaca-specific statuses
    STOPPED = "stopped"
    SUSPENDED = "suspended"
    CALCULATED = "calculated"


class ParseStatus:
    """File parsing status values."""

    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProcessingStatus:
    """General data processing status values."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PROCESSED = "processed"
    DUPLICATE = "duplicate"
    NEEDS_REVIEW = "needs_review"


class TransactionType:
    """Transaction type values for trading disclosures."""

    # Basic transaction types
    PURCHASE = "purchase"
    SALE = "sale"
    BUY = "buy"
    SELL = "sell"

    # Advanced transaction types
    EXCHANGE = "exchange"
    OPTION_PURCHASE = "option_purchase"
    OPTION_SALE = "option_sale"
    OPTION_EXERCISE = "option_exercise"

    # Additional types
    PARTIAL_SALE = "partial_sale"
    FULL_SALE = "full_sale"


class SignalType:
    """Trading signal type values."""

    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class TradingMode:
    """Trading mode values."""

    PAPER = "paper"
    LIVE = "live"

    # Capitalized versions (UI display)
    PAPER_DISPLAY = "Paper"
    LIVE_DISPLAY = "Live"


class ActionType:
    """Action log type values."""

    # Authentication actions
    LOGIN_ATTEMPT = "login_attempt"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    SESSION_TIMEOUT = "session_timeout"
    SESSION_TERMINATED = "session_terminated"

    # Data collection actions
    DATA_COLLECTION_START = "data_collection_start"
    DATA_COLLECTION_SUCCESS = "data_collection_success"
    DATA_COLLECTION_FAILURE = "data_collection_failure"
    TICKER_BACKFILL = "ticker_backfill"

    # Job management actions
    JOB_EXECUTION = "job_execution"
    JOB_PAUSE = "job_pause"
    JOB_RESUME = "job_resume"
    JOB_MANUAL_RUN = "job_manual_run"
    JOB_REMOVE = "job_remove"
    JOB_CREATE = "job_create"
    JOB_UPDATE = "job_update"

    # Trading actions
    TRADE_EXECUTE = "trade_execute"
    TRADE_CANCEL = "trade_cancel"
    SIGNAL_GENERATE = "signal_generate"

    # Subscription actions
    SUBSCRIPTION_CHECK = "subscription_check"
    SUBSCRIPTION_UPDATE = "subscription_update"

    # Admin actions
    ADMIN_ACCESS = "admin_access"
    ADMIN_ACTION = "admin_action"


class PoliticianRole:
    """Politician role/chamber values."""

    # US roles
    US_HOUSE_REPRESENTATIVE = "us_house_representative"
    US_SENATOR = "us_senator"
    US_REPRESENTATIVE = "Representative"  # Display name
    US_SENATOR_DISPLAY = "Senator"  # Display name

    # Chamber names
    HOUSE = "House"
    SENATE = "Senate"

    # Lowercase variants
    HOUSE_LOWER = "house"
    SENATE_LOWER = "senate"

    # EU roles
    EU_MEP = "eu_mep"
    EU_MEMBER_DISPLAY = "MEP"


class DataSourceType:
    """Data source/job type identifiers."""

    # US Federal
    US_CONGRESS = "us_congress"
    US_HOUSE = "us_house"
    US_SENATE = "us_senate"

    # US States
    US_STATES = "us_states"
    CALIFORNIA = "california"
    TEXAS = "texas"
    NEW_YORK = "new_york"

    # International
    EU_PARLIAMENT = "eu_parliament"
    EU_MEMBER_STATES = "eu_member_states"
    UK_PARLIAMENT = "uk_parliament"

    # Third party
    QUIVER_QUANT = "quiverquant"
    PROPUBLICA = "propublica"
