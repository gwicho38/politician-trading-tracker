"""
URL and API endpoint constants.

These constants define external URLs and API endpoints used throughout
the application.
"""


class ApiUrls:
    """External API base URLs."""

    # Alpaca Trading API
    ALPACA_PAPER = "https://paper-api.alpaca.markets"
    ALPACA_LIVE = "https://api.alpaca.markets"
    ALPACA_DATA = "https://data.alpaca.markets"

    # Government disclosure sources
    HOUSE_DISCLOSURES = "https://disclosures-clerk.house.gov/FinancialDisclosure"
    SENATE_DISCLOSURES = "https://efdsearch.senate.gov/search/"
    SENATE_EFD = "https://efd.senate.gov"

    # Third-party data sources
    QUIVERQUANT_API = "https://api.quiverquant.com/beta/live/congresstrading"
    PROPUBLICA_API = "https://api.propublica.org/congress/v1"

    # UK sources
    UK_COMPANIES_HOUSE = "https://api.company-information.service.gov.uk"
    UK_PARLIAMENT = "https://members-api.parliament.uk"

    # Other
    OPENCORPORATES = "https://api.opencorporates.com"


class WebUrls:
    """Web interface URLs (non-API)."""

    # Application URLs
    GITHUB_REPO = "https://github.com/gwicho38/politician-trading-tracker"
    SUPABASE_DASHBOARD = "https://supabase.com/dashboard"

    # Trading platform URLs
    ALPACA_DASHBOARD = "https://app.alpaca.markets/"
    ALPACA_PAPER_DASHBOARD = "https://paper-api.alpaca.markets"

    # Data source websites
    QUIVERQUANT_WEBSITE = "https://quiverquant.com/"

    # Local development
    LOCALHOST = "http://localhost:8501"
    STREAMLIT_SHARING = "https://share.streamlit.io"


class ConfigDefaults:
    """Default configuration values for timeouts, retries, and limits."""

    # Timeouts (seconds)
    DEFAULT_TIMEOUT = 30
    LONG_TIMEOUT = 60
    SHORT_TIMEOUT = 10

    # Retry configuration
    DEFAULT_MAX_RETRIES = 3
    MAX_RETRIES_HIGH = 5
    MAX_RETRIES_LOW = 2

    # Request delays (seconds)
    DEFAULT_REQUEST_DELAY = 1.0
    RESPECTFUL_DELAY = 2.0
    CAUTIOUS_DELAY = 3.0
    RATE_LIMIT_DELAY = 0.11  # Just over rate limit threshold

    # Query limits
    LIMIT_SMALL = 1
    LIMIT_MEDIUM = 10
    LIMIT_LARGE = 50
    LIMIT_XLARGE = 100

    # Financial thresholds
    DISCLOSURE_THRESHOLD_USD = 1000
    FILING_THRESHOLD_2025_USD = 150160

    # Trading configuration
    MIN_CONFIDENCE = 0.6
    HIGH_CONFIDENCE = 0.65
    MAX_POSITION_SIZE_PCT = 10.0
    MAX_PORTFOLIO_RISK_PCT = 2.0
    MAX_TOTAL_EXPOSURE_PCT = 80.0
    MAX_POSITIONS = 20

    # Time periods (days)
    DEFAULT_LOOKBACK_DAYS = 30
    RETENTION_DAYS = 365
