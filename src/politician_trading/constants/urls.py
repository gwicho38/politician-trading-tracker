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

    # Government disclosure sources - US Federal
    HOUSE_DISCLOSURES = "https://disclosures-clerk.house.gov/FinancialDisclosure"
    SENATE_DISCLOSURES = "https://efdsearch.senate.gov/search/"
    SENATE_EFD = "https://efd.senate.gov"

    # Third-party data sources
    QUIVERQUANT = "https://api.quiverquant.com/beta/live/congresstrading"
    PROPUBLICA = "https://api.propublica.org/congress/v1"

    # UK sources
    UK_COMPANIES_HOUSE = "https://api.companieshouse.gov.uk"
    UK_PARLIAMENT = "https://members-api.parliament.uk"
    UK_PARLIAMENT_INTERESTS = "https://interests-api.parliament.uk/api/v1"

    # EU sources
    INFO_FINANCIERE_GOUV_FR = "https://info-financiere.gouv.fr/api/v1"

    # Corporate registry APIs
    OPENCORPORATES = "https://api.opencorporates.com"
    OPENCORPORATES_V04 = "https://api.opencorporates.com/v0.4"
    XBRL_US = "https://api.xbrl.us/api/v1"
    XBRL_FILINGS = "https://filings.xbrl.org/api"

    # Financial data APIs
    FINNHUB = "https://finnhub.io/api/v1"
    SEC_DATA = "https://data.sec.gov"

    # California
    NETFILE = "https://netfile.com/Connect2/api/public/list/ANC"

    # UK sources (with trailing slash variations)
    UK_COMPANIES_HOUSE_SLASH = "https://api.companieshouse.gov.uk/"
    UK_COMPANIES_HOUSE_STREAM = "https://stream.companieshouse.gov.uk/"

    # Documentation APIs
    FINNHUB_DOCS = "https://finnhub.io/docs/api/congressional-trading"
    INFO_FINANCIERE_CONSOLE = "https://info-financiere.gouv.fr/api/v1/console"
    OPENCORPORATES_V04_SLASH = "https://api.opencorporates.com/v0.4/"
    TRANSPARENT_DATA_PL = "https://apidoc.transparentdata.pl/company_registers_api.html"

    # Regional corporate registries
    GETEDGE_AU = "https://getedge.com.au/docs/api"
    HK_COMPANIES_REGISTRY = "https://www.cr.gov.hk/en/electronic/e-servicesportal/"


class WebUrls:
    """Web interface URLs (non-API)."""

    # Application URLs
    GITHUB_REPO = "https://github.com/gwicho38/politician-trading-tracker"
    SUPABASE_DASHBOARD = "https://supabase.com/dashboard"

    # Trading platform URLs
    ALPACA_DASHBOARD = "https://app.alpaca.markets/"
    ALPACA_PAPER_DASHBOARD_OVERVIEW = "https://app.alpaca.markets/paper/dashboard/overview"
    ALPACA_LIVE_DASHBOARD_OVERVIEW = "https://app.alpaca.markets/live/dashboard/overview"

    # Data source websites
    QUIVERQUANT = "https://quiverquant.com/"
    QUIVERQUANT_WWW = "https://www.quiverquant.com"
    QUIVERQUANT_CONGRESSTRADING = "https://www.quiverquant.com/congresstrading/"
    PROPUBLICA = "https://www.propublica.org/"

    # US Federal disclosure websites
    HOUSE_CLERK_DISCLOSURES = "https://disclosures-clerk.house.gov"
    SENATE_EFD_SEARCH = "https://efdsearch.senate.gov"
    OGE_DISCLOSURES = "https://www.oge.gov/web/OGE.nsf/Officials Individual Disclosures Search Collection"

    # US State ethics websites
    CALIFORNIA_SOS = "https://www.sos.ca.gov/campaign-lobbying/cal-access-resources"
    CALIFORNIA_FPPC = "https://www.fppc.ca.gov/"
    TEXAS_ETHICS = "https://www.ethics.state.tx.us"
    TEXAS_ETHICS_SEARCH = "https://www.ethics.state.tx.us/search/cf/"
    NEW_YORK_ETHICS = "https://ethics.ny.gov/financial-disclosure-statements-elected-officials"
    NEW_YORK_JCOPE = "https://www.jcope.ny.gov"
    FLORIDA_ETHICS = "https://ethics.state.fl.us/FinancialDisclosure/"
    FLORIDA_ETHICS_WWW = "https://www.ethics.state.fl.us"
    ILLINOIS_ETHICS = "https://ethics.illinois.gov"
    PENNSYLVANIA_ETHICS = "https://www.ethics.pa.gov"
    MICHIGAN_SOS = "https://www.michigan.gov/sos/elections/disclosure/personal-financial-disclosure"
    MASSACHUSETTS_ETHICS = "https://www.mass.gov/orgs/state-ethics-commission"

    # EU Parliament websites
    EU_PARLIAMENT = "https://www.europarl.europa.eu"
    EU_PARLIAMENT_MEPS = "https://www.europarl.europa.eu/meps/en/home"
    EU_PARLIAMENT_DECLARATIONS = "https://www.europarl.europa.eu/meps/en/declarations"
    EU_INTEGRITY_WATCH = "https://www.integritywatch.eu/mepincomes"

    # Germany
    BUNDESTAG = "https://www.bundestag.de"
    BUNDESTAG_ABGEORDNETE = "https://www.bundestag.de/abgeordnete"

    # France
    ASSEMBLEE_NATIONALE = "https://www2.assemblee-nationale.fr"
    SENAT_FR = "https://www.senat.fr"
    HATVP = "https://www.hatvp.fr"

    # Italy
    CAMERA_IT = "https://www.camera.it"
    SENATO_IT = "https://www.senato.it"

    # Spain
    CONGRESO_ES = "https://www.congreso.es"
    SENADO_ES = "https://www.senado.es"

    # Netherlands
    TWEEDEKAMER = "https://www.tweedekamer.nl"
    EERSTEKAMER = "https://www.eerstekamer.nl"

    # UK Parliament websites
    UK_PARLIAMENT = "https://www.parliament.uk"
    UK_PARLIAMENT_REGISTER = "https://www.parliament.uk/mps-lords-and-offices/standards-and-financial-interests/"
    UK_PARLIAMENT_MEMBERS_REGISTER = "https://www.parliament.uk/mps-lords-and-offices/standards-and-financial-interests/parliamentary-commissioner-for-standards/registers-of-interests/register-of-members-financial-interests/"

    # GitHub data sources
    SENATE_STOCK_WATCHER = "https://raw.githubusercontent.com/timothycarambat/senate-stock-watcher-data/master"

    # Third party
    STOCKNEAR = "https://stocknear.com/politicians"

    # Local development
    LOCALHOST = "http://localhost:5173"  # React dev server
    # STREAMLIT_SHARING = "https://share.streamlit.io"  # Removed - now using React UI

    # Test/placeholder URLs
    TEST_EXAMPLE = "https://test.example.com"
    SUPABASE_PLACEHOLDER = "https://xxxxx.supabase.co"
    SUPABASE_PLACEHOLDER_PROMPT = "https://xxxxx.supabase.co (enter to update)"

    # Third party data aggregators
    OPENSECRETS = "https://www.opensecrets.org/personal-finances"
    LEGISTORM = "https://www.legistorm.com/financial_disclosure.html"
    BARCHART = "https://www.barchart.com/investing-ideas/politician-insider-trading"
    FINDDYNAMICS = "https://www.finddynamics.com/"

    # GitHub data sources
    SENATE_STOCK_WATCHER_REPO = "https://github.com/timothycarambat/senate-stock-watcher-data"
    XBRL_API_REPO = "https://github.com/xbrlus/xbrl-api"

    # XBRL websites
    XBRL_FILINGS = "https://filings.xbrl.org/"

    # UK additional URLs
    UK_LORDS_REGISTER = "https://members.parliament.uk/members/lords/interests/register-of-lords-interests"

    # Spain additional
    CONGRESO_TRANSPARENCIA = "https://www.congreso.es/transparencia"

    # Italy additional
    CAMERA_IT_LEG19 = "https://www.camera.it/leg19/1"

    # Project-specific Supabase
    SUPABASE_PROJECT = "https://uljsqvwkomdrlnofmlad.supabase.co"


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
    MAX_LOOKBACK_DAYS = 1825  # 5 years
    RETENTION_DAYS = 365
