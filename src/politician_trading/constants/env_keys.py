"""
Environment variable key constants.

These constants provide a single source of truth for all environment
variable keys used throughout the application.
"""


class EnvKeys:
    """Environment variable key names."""

    # Supabase configuration
    SUPABASE_URL = "SUPABASE_URL"
    SUPABASE_ANON_KEY = "SUPABASE_ANON_KEY"
    SUPABASE_KEY = "SUPABASE_KEY"  # Alternative to SUPABASE_ANON_KEY
    SUPABASE_SERVICE_KEY = "SUPABASE_SERVICE_KEY"
    SUPABASE_SERVICE_ROLE_KEY = "SUPABASE_SERVICE_ROLE_KEY"

    # Alpaca trading configuration
    ALPACA_API_KEY = "ALPACA_API_KEY"
    ALPACA_SECRET_KEY = "ALPACA_SECRET_KEY"
    ALPACA_PAPER_API_KEY = "ALPACA_PAPER_API_KEY"
    ALPACA_PAPER_SECRET_KEY = "ALPACA_PAPER_SECRET_KEY"
    ALPACA_PAPER = "ALPACA_PAPER"
    ALPACA_BASE_URL = "ALPACA_BASE_URL"

    # Third-party API keys
    QUIVER_API_KEY = "QUIVER_API_KEY"
    QUIVERQUANT_API_KEY = "QUIVERQUANT_API_KEY"
    PROPUBLICA_API_KEY = "PROPUBLICA_API_KEY"
    FINNHUB_API_KEY = "FINNHUB_API_KEY"
    UK_COMPANIES_HOUSE_API_KEY = "UK_COMPANIES_HOUSE_API_KEY"
    OPENCORPORATES_API_KEY = "OPENCORPORATES_API_KEY"
    XBRL_US_API_KEY = "XBRL_US_API_KEY"

    # Authentication
    GOOGLE_CLIENT_ID = "GOOGLE_CLIENT_ID"
    GOOGLE_CLIENT_SECRET = "GOOGLE_CLIENT_SECRET"
    API_ENCRYPTION_KEY = "API_ENCRYPTION_KEY"

    # Application configuration
    LOG_LEVEL = "LOG_LEVEL"
    ENVIRONMENT = "ENVIRONMENT"
    DEBUG = "DEBUG"

    # Trading strategy configuration
    SIGNAL_LOOKBACK_DAYS = "SIGNAL_LOOKBACK_DAYS"
    TRADING_MIN_CONFIDENCE = "TRADING_MIN_CONFIDENCE"

    # Risk management configuration
    RISK_MAX_POSITION_SIZE_PCT = "RISK_MAX_POSITION_SIZE_PCT"
    RISK_MAX_PORTFOLIO_RISK_PCT = "RISK_MAX_PORTFOLIO_RISK_PCT"
    RISK_MAX_TOTAL_EXPOSURE_PCT = "RISK_MAX_TOTAL_EXPOSURE_PCT"
    RISK_MAX_POSITIONS = "RISK_MAX_POSITIONS"

    # Scraping configuration
    SCRAPING_DELAY = "SCRAPING_DELAY"
    MAX_RETRIES = "MAX_RETRIES"
    TIMEOUT = "TIMEOUT"

    # Streamlit configuration
    STREAMLIT_API_TOKEN = "STREAMLIT_API_TOKEN"

    # Stripe payment configuration
    STRIPE_SECRET_KEY = "STRIPE_SECRET_KEY"
    STRIPE_PUBLISHABLE_KEY = "STRIPE_PUBLISHABLE_KEY"
    STRIPE_WEBHOOK_SECRET = "STRIPE_WEBHOOK_SECRET"


class EnvDefaults:
    """
    Default values for environment variables.

    Note: Sensitive values like Supabase URLs and keys should ALWAYS be
    loaded from environment variables or secure configuration, never
    hardcoded. The defaults below are for non-sensitive configuration only.
    """

    # Alpaca defaults
    ALPACA_PAPER = "true"
    ALPACA_BASE_URL = "https://paper-api.alpaca.markets"

    # Scraping defaults
    REQUEST_DELAY = 2.0
    MAX_RETRIES = 3
    TIMEOUT = 30

    # Trading strategy defaults
    SIGNAL_LOOKBACK_DAYS = 30
    TRADING_MIN_CONFIDENCE = 0.6

    # Risk management defaults
    RISK_MAX_POSITION_SIZE_PCT = 10.0
    RISK_MAX_PORTFOLIO_RISK_PCT = 2.0
    RISK_MAX_TOTAL_EXPOSURE_PCT = 80.0
    RISK_MAX_POSITIONS = 20

    # Log level
    LOG_LEVEL = "INFO"
