"""
Database table and column name constants.

These constants provide a single source of truth for all database table
and column names used throughout the application.
"""


class Tables:
    """Database table names."""

    # Core tables
    POLITICIANS = "politicians"
    TRADING_DISCLOSURES = "trading_disclosures"
    TRADING_SIGNALS = "trading_signals"
    TRADING_ORDERS = "trading_orders"
    PORTFOLIOS = "portfolios"
    POSITIONS = "positions"

    # Job management tables
    DATA_PULL_JOBS = "data_pull_jobs"
    SCHEDULED_JOBS = "scheduled_jobs"
    JOB_EXECUTIONS = "job_executions"
    SCHEDULED_JOBS_STATUS = "scheduled_jobs_status"
    JOB_EXECUTION_SUMMARY = "job_execution_summary"

    # Logging and monitoring tables
    ACTION_LOGS = "action_logs"
    ACTION_LOGS_SUMMARY = "action_logs_summary"

    # Storage and data sources
    STORED_FILES = "stored_files"
    DATA_SOURCES = "data_sources"

    # User management tables
    USER_API_KEYS = "user_api_keys"
    USER_SESSIONS = "user_sessions"


class Columns:
    """Database column names organized by logical grouping."""

    class Common:
        """Commonly used columns across multiple tables."""

        ID = "id"
        CREATED_AT = "created_at"
        UPDATED_AT = "updated_at"
        STATUS = "status"
        IS_ACTIVE = "is_active"
        ENABLED = "enabled"

    class Politician:
        """Politician table columns."""

        ID = "id"
        FIRST_NAME = "first_name"
        LAST_NAME = "last_name"
        FULL_NAME = "full_name"
        ROLE = "role"
        PARTY = "party"
        CHAMBER = "chamber"
        STATE = "state"
        DISTRICT = "district"
        CREATED_AT = "created_at"
        UPDATED_AT = "updated_at"

    class Disclosure:
        """Trading disclosure table columns."""

        ID = "id"
        POLITICIAN_ID = "politician_id"
        DISCLOSURE_ID = "disclosure_id"
        ASSET_TICKER = "asset_ticker"
        ASSET_NAME = "asset_name"
        TRANSACTION_TYPE = "transaction_type"
        TRANSACTION_DATE = "transaction_date"
        DISCLOSURE_DATE = "disclosure_date"
        AMOUNT_MIN = "amount_min"
        AMOUNT_MAX = "amount_max"
        COMMENT = "comment"
        CREATED_AT = "created_at"
        UPDATED_AT = "updated_at"

    class Signal:
        """Trading signal table columns."""

        ID = "id"
        DISCLOSURE_ID = "disclosure_id"
        POLITICIAN_ID = "politician_id"
        ASSET_TICKER = "asset_ticker"
        SIGNAL_TYPE = "signal_type"
        CONFIDENCE = "confidence"
        RATIONALE = "rationale"
        CREATED_AT = "created_at"
        UPDATED_AT = "updated_at"

    class Order:
        """Trading order table columns."""

        ID = "id"
        SIGNAL_ID = "signal_id"
        PORTFOLIO_ID = "portfolio_id"
        ASSET_TICKER = "asset_ticker"
        ORDER_TYPE = "order_type"
        SIDE = "side"
        QUANTITY = "quantity"
        LIMIT_PRICE = "limit_price"
        STATUS = "status"
        ALPACA_ORDER_ID = "alpaca_order_id"
        FILLED_QTY = "filled_qty"
        FILLED_AVG_PRICE = "filled_avg_price"
        SUBMITTED_AT = "submitted_at"
        FILLED_AT = "filled_at"
        CREATED_AT = "created_at"
        UPDATED_AT = "updated_at"

    class Job:
        """Job-related table columns."""

        ID = "id"
        JOB_ID = "job_id"
        JOB_TYPE = "job_type"
        STATUS = "status"
        ENABLED = "enabled"
        AUTO_RETRY_ON_STARTUP = "auto_retry_on_startup"
        STARTED_AT = "started_at"
        COMPLETED_AT = "completed_at"
        ERROR_MESSAGE = "error_message"
        LAST_ACTIVITY = "last_activity"
        RECORDS_PROCESSED = "records_processed"
        CREATED_AT = "created_at"
        UPDATED_AT = "updated_at"

    class Storage:
        """Storage and file-related columns."""

        ID = "id"
        STORAGE_BUCKET = "storage_bucket"
        STORAGE_PATH = "storage_path"
        FILE_NAME = "file_name"
        FILE_SIZE = "file_size"
        CONTENT_TYPE = "content_type"
        PARSE_STATUS = "parse_status"
        SOURCE_TYPE = "source_type"
        CREATED_AT = "created_at"
        UPDATED_AT = "updated_at"

    class ActionLog:
        """Action log table columns."""

        ID = "id"
        ACTION_ID = "action_id"
        ACTION_TYPE = "action_type"
        USER_EMAIL = "user_email"
        USER_ID = "user_id"
        STATUS = "status"
        DETAILS = "details"
        RESULT_MESSAGE = "result_message"
        STARTED_AT = "started_at"
        COMPLETED_AT = "completed_at"
        CREATED_AT = "created_at"

    class User:
        """User-related table columns."""

        ID = "id"
        USER_EMAIL = "user_email"
        USER_ID = "user_id"
        API_KEY = "api_key"
        API_KEY_HASH = "api_key_hash"
        SERVICE = "service"
        SESSION_ID = "session_id"
        IS_ACTIVE = "is_active"
        EXPIRES_AT = "expires_at"
        LAST_USED_AT = "last_used_at"
        CREATED_AT = "created_at"
        UPDATED_AT = "updated_at"
