"""
Comprehensive Data Sources Configuration for Politician Trading/Financial Disclosure Data

This file contains the definitive mapping of all publicly accessible politician
trading and financial disclosure sources across US federal, state, EU, and national levels.

Based on 2025 research of available public databases and APIs.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Literal, Optional


class DisclosureType(Enum):
    """Types of financial disclosures available"""

    STOCK_TRANSACTIONS = "stock_transactions"  # Individual buy/sell transactions
    FINANCIAL_INTERESTS = "financial_interests"  # General financial interests/assets
    ASSET_DECLARATIONS = "asset_declarations"  # Property, investments, etc.
    INCOME_SOURCES = "income_sources"  # Outside income sources
    CONFLICT_INTERESTS = "conflict_interests"  # Potential conflicts of interest


class AccessMethod(Enum):
    """How data can be accessed"""

    WEB_SCRAPING = "web_scraping"  # HTML scraping required
    API = "api"  # JSON/XML API available
    PDF_PARSING = "pdf_parsing"  # PDF documents to parse
    MANUAL_DOWNLOAD = "manual_download"  # Manual download required
    DATABASE_QUERY = "database_query"  # Direct database access


@dataclass
class DataSource:
    """Configuration for a single data source"""

    name: str
    jurisdiction: str  # e.g., "US-Federal", "US-CA", "EU", "DE"
    institution: str  # e.g., "House", "Senate", "Bundestag"
    url: str
    disclosure_types: List[DisclosureType]
    access_method: AccessMethod
    update_frequency: str  # e.g., "daily", "weekly", "monthly"
    threshold_amount: Optional[int] = None  # Minimum disclosure amount in USD
    data_format: str = "html"  # html, json, xml, pdf
    api_key_required: bool = False
    rate_limits: Optional[str] = None
    historical_data_available: bool = True
    notes: Optional[str] = None
    status: Literal["active", "inactive", "testing", "planned"] = "active"


# =============================================================================
# US FEDERAL SOURCES
# =============================================================================

US_FEDERAL_SOURCES = [
    DataSource(
        name="US House Financial Disclosures",
        jurisdiction="US-Federal",
        institution="House of Representatives",
        url="https://disclosures-clerk.house.gov/FinancialDisclosure",
        disclosure_types=[DisclosureType.STOCK_TRANSACTIONS, DisclosureType.ASSET_DECLARATIONS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Real-time (within 30 days of filing)",
        threshold_amount=1000,  # $1,000+ transactions must be reported
        data_format="html",
        historical_data_available=True,
        notes="STOCK Act requires prompt disclosure of transactions >$1,000. 8-year archive available.",
        status="active",
    ),
    DataSource(
        name="US Senate Financial Disclosures",
        jurisdiction="US-Federal",
        institution="Senate",
        url="https://efd.senate.gov",
        disclosure_types=[DisclosureType.STOCK_TRANSACTIONS, DisclosureType.ASSET_DECLARATIONS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Real-time (within 30 days of filing)",
        threshold_amount=1000,  # $1,000+ transactions must be reported
        data_format="html",
        historical_data_available=True,
        notes="Filing threshold $150,160 for 2025. 6-year retention after leaving office.",
        status="active",
    ),
    DataSource(
        name="Office of Government Ethics",
        jurisdiction="US-Federal",
        institution="Executive Branch",
        url="https://www.oge.gov/web/OGE.nsf/Officials Individual Disclosures Search Collection",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.ASSET_DECLARATIONS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Annually",
        data_format="pdf",
        historical_data_available=True,
        notes="Executive branch officials, judges, and senior staff disclosures",
        status="active",
    ),
]

# =============================================================================
# US STATE SOURCES (Selected Major States)
# =============================================================================

US_STATE_SOURCES = [
    # California
    DataSource(
        name="California FPPC Form 700",
        jurisdiction="US-CA",
        institution="State Legislature",
        url="https://netfile.com/Connect2/api/public/list/ANC",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.INCOME_SOURCES],
        access_method=AccessMethod.API,
        update_frequency="Annually (April deadline)",
        threshold_amount=2000,
        data_format="json",
        api_key_required=False,
        notes="Fair Political Practices Commission Form 700. NetFile API available.",
        status="active",
    ),
    # New York
    DataSource(
        name="New York State Financial Disclosure",
        jurisdiction="US-NY",
        institution="State Legislature",
        url="https://ethics.ny.gov/financial-disclosure-statements-elected-officials",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.INCOME_SOURCES],
        access_method=AccessMethod.PDF_PARSING,
        update_frequency="Annually (May 15 deadline)",
        data_format="pdf",
        notes="Commission on Ethics and Lobbying in Government",
        status="active",
    ),
    # Florida
    DataSource(
        name="Florida Financial Disclosure",
        jurisdiction="US-FL",
        institution="State Legislature",
        url="https://ethics.state.fl.us/FinancialDisclosure/",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.ASSET_DECLARATIONS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Annually (July 1 deadline, grace period until Sept 1)",
        data_format="html",
        notes="All elected state and local public officers required to file",
        status="active",
    ),
    # Texas
    DataSource(
        name="Texas Ethics Commission",
        jurisdiction="US-TX",
        institution="State Legislature",
        url="https://www.ethics.state.tx.us/search/cf/",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Annually",
        data_format="html",
        status="active",
    ),
    # Michigan
    DataSource(
        name="Michigan Personal Financial Disclosure",
        jurisdiction="US-MI",
        institution="State Legislature",
        url="https://www.michigan.gov/sos/elections/disclosure/personal-financial-disclosure",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Annually",
        data_format="html",
        notes="Candidates for Governor, Lt. Gov, SoS, AG, and Legislature required",
        status="active",
    ),
]

# =============================================================================
# EU PARLIAMENT SOURCES
# =============================================================================

EU_PARLIAMENT_SOURCES = [
    DataSource(
        name="MEP Financial Interest Declarations",
        jurisdiction="EU",
        institution="European Parliament",
        url="https://www.europarl.europa.eu/meps/en/home",
        disclosure_types=[DisclosureType.INCOME_SOURCES, DisclosureType.CONFLICT_INTERESTS],
        access_method=AccessMethod.PDF_PARSING,
        update_frequency="Per legislative term (5 years)",
        threshold_amount=5000,  # €5,000+ outside income must be declared
        data_format="pdf",
        notes="Individual MEP pages have declarations. Third-party aggregation by EU Integrity Watch.",
        status="active",
    ),
    DataSource(
        name="EU Integrity Watch",
        jurisdiction="EU",
        institution="Third-party aggregator",
        url="https://www.integritywatch.eu/mepincomes",
        disclosure_types=[DisclosureType.INCOME_SOURCES, DisclosureType.CONFLICT_INTERESTS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Updated after MEP declarations",
        data_format="html",
        notes="Automated extraction from Parliament PDFs. Interactive database available.",
        status="active",
    ),
]

# =============================================================================
# EUROPEAN NATIONAL SOURCES
# =============================================================================

EU_NATIONAL_SOURCES = [
    # Germany
    DataSource(
        name="German Bundestag Member Interests",
        jurisdiction="DE",
        institution="Bundestag",
        url="https://www.bundestag.de/abgeordnete",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.INCOME_SOURCES],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Updated as required",
        threshold_amount=None,  # 5% company ownership threshold (down from 25% in 2021)
        data_format="html",
        notes="Transparency Act 2021. Company ownership >5%, tougher bribery laws (1-10 years prison).",
        status="active",
    ),
    # France
    DataSource(
        name="French Parliament Financial Declarations",
        jurisdiction="FR",
        institution="National Assembly & Senate",
        url="https://www.hatvp.fr/",  # High Authority for Transparency in Public Life
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.ASSET_DECLARATIONS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Annually",
        data_format="html",
        notes="HATVP publishes declarations. Asset declarations for MEPs since 2019. Penalties: 3 years prison + €45,000 fine.",
        status="active",
    ),
    # United Kingdom
    DataSource(
        name="UK Parliament Register of Members' Financial Interests",
        jurisdiction="UK",
        institution="House of Commons",
        url="https://www.parliament.uk/mps-lords-and-offices/standards-and-financial-interests/parliamentary-commissioner-for-standards/registers-of-interests/register-of-members-financial-interests/",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.INCOME_SOURCES],
        access_method=AccessMethod.API,
        update_frequency="Updated every 2 weeks during sitting periods",
        threshold_amount=70000,  # £70,000+ shareholdings (or >15% company ownership)
        data_format="json",
        api_key_required=False,
        notes="Open Parliament Licence API available. Register updated bi-weekly.",
        status="active",
    ),
    DataSource(
        name="UK House of Lords Register of Interests",
        jurisdiction="UK",
        institution="House of Lords",
        url="https://members.parliament.uk/members/lords/interests/register-of-lords-interests",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.INCOME_SOURCES],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Updated regularly",
        data_format="html",
        notes="More detailed shareholding disclosure than Commons. Searchable database.",
        status="active",
    ),
    # Spain
    DataSource(
        name="Spanish Parliament Transparency Portal",
        jurisdiction="ES",
        institution="Congress of Deputies & Senate",
        url="https://www.congreso.es/transparencia",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Updated as required",
        data_format="html",
        notes="Deputies and senators publish institutional agendas with interest representatives. No lobbyist register.",
        status="active",
    ),
    # Italy
    DataSource(
        name="Italian Parliament Financial Declarations",
        jurisdiction="IT",
        institution="Camera dei Deputati & Senato",
        url="https://www.camera.it/leg19/1",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Per legislative term",
        data_format="html",
        notes="Individual member pages contain declarations. Limited standardization.",
        status="testing",
    ),
]

# =============================================================================
# THIRD-PARTY AGGREGATORS AND APIS
# =============================================================================

THIRD_PARTY_SOURCES = [
    DataSource(
        name="Senate Stock Watcher (GitHub)",
        jurisdiction="US-Federal",
        institution="Third-party aggregator",
        url="https://github.com/timothycarambat/senate-stock-watcher-data",
        disclosure_types=[DisclosureType.STOCK_TRANSACTIONS],
        access_method=AccessMethod.API,
        update_frequency="Continuously updated from Senate filings",
        data_format="json",
        api_key_required=False,
        rate_limits="GitHub rate limits",
        notes="FREE! Automated aggregation of Senate PTR filings. JSON dataset updated continuously. All historical data available in all_transactions.json. No API key required!",
        status="active",
    ),
    DataSource(
        name="OpenSecrets Personal Finances",
        jurisdiction="US-Federal",
        institution="Third-party aggregator",
        url="https://www.opensecrets.org/personal-finances",
        disclosure_types=[DisclosureType.ASSET_DECLARATIONS, DisclosureType.STOCK_TRANSACTIONS],
        access_method=AccessMethod.API,
        update_frequency="Updated from federal filings",
        data_format="json",
        api_key_required=True,
        rate_limits="1000 requests/day",
        notes="Center for Responsive Politics aggregation of federal disclosures.",
        status="active",
    ),
    DataSource(
        name="LegiStorm Financial Disclosures",
        jurisdiction="US-Federal",
        institution="Third-party aggregator",
        url="https://www.legistorm.com/financial_disclosure.html",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.STOCK_TRANSACTIONS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Real-time from government sources",
        data_format="html",
        notes="Subscription service with enhanced search and analysis tools.",
        status="active",
    ),
    DataSource(
        name="QuiverQuant Congressional Trading",
        jurisdiction="US-Federal",
        institution="Third-party aggregator",
        url="https://www.quiverquant.com/congresstrading/",
        disclosure_types=[DisclosureType.STOCK_TRANSACTIONS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Real-time",
        data_format="html",
        api_key_required=False,
        rate_limits="Web scraping rate limits apply",
        notes="Financial data company focusing on congressional stock trades. Web interface with trade details, filing dates, and performance metrics. Premium API available.",
        status="active",
    ),
    DataSource(
        name="QuiverQuant API",
        jurisdiction="US-Federal",
        institution="Third-party aggregator",
        url="https://api.quiverquant.com/beta/live/congresstrading",
        disclosure_types=[DisclosureType.STOCK_TRANSACTIONS],
        access_method=AccessMethod.API,
        update_frequency="Real-time",
        data_format="json",
        api_key_required=True,
        rate_limits="Varies by subscription",
        notes="Premium API for QuiverQuant congressional trading data. Requires subscription.",
        status="active",
    ),
    DataSource(
        name="StockNear Politicians",
        jurisdiction="US-Federal",
        institution="Third-party aggregator",
        url="https://stocknear.com/politicians",
        disclosure_types=[DisclosureType.STOCK_TRANSACTIONS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Real-time",
        data_format="html",
        api_key_required=False,
        notes="Tracks 299 politicians with trade counts, districts, last trade dates, and party affiliation. Pro subscription for unlimited access.",
        status="active",
    ),
    DataSource(
        name="Barchart Politician Insider Trading",
        jurisdiction="US-Federal",
        institution="Third-party aggregator",
        url="https://www.barchart.com/investing-ideas/politician-insider-trading",
        disclosure_types=[DisclosureType.STOCK_TRANSACTIONS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Updated within 45 days of transaction",
        data_format="html",
        threshold_amount=None,
        notes="Tracks House and Senate trades from last 60 days. Includes buy/sell counts and transaction totals. CSV export available.",
        status="active",
    ),
    DataSource(
        name="ProPublica Congress API",
        jurisdiction="US-Federal",
        institution="Third-party aggregator",
        url="https://api.propublica.org/congress/v1",
        disclosure_types=[DisclosureType.STOCK_TRANSACTIONS, DisclosureType.FINANCIAL_INTERESTS],
        access_method=AccessMethod.API,
        update_frequency="Daily",
        data_format="json",
        api_key_required=True,
        rate_limits="5000 requests/day (free tier)",
        notes="DEPRECATED: ProPublica Congress API is no longer available as of 2025. Use Senate Stock Watcher or Finnhub instead.",
        status="inactive",
    ),
    DataSource(
        name="Finnhub Congressional Trading",
        jurisdiction="US-Federal",
        institution="Third-party aggregator",
        url="https://finnhub.io/docs/api/congressional-trading",
        disclosure_types=[DisclosureType.STOCK_TRANSACTIONS],
        access_method=AccessMethod.API,
        update_frequency="Real-time",
        data_format="json",
        api_key_required=True,
        rate_limits="30 requests/second (free tier)",
        notes="FREE API key available at finnhub.io. Provides congressional trading data by stock symbol. Response includes representative name, transaction date/type, and amount ranges.",
        status="active",
    ),
    DataSource(
        name="SEC Edgar Insider Trading",
        jurisdiction="US-Federal",
        institution="Official government source",
        url="https://data.sec.gov",
        disclosure_types=[DisclosureType.STOCK_TRANSACTIONS],
        access_method=AccessMethod.API,
        update_frequency="Real-time",
        data_format="json",
        api_key_required=False,
        rate_limits="10 requests/second",
        notes="FREE! Official SEC data. Access company submissions and Form 4 insider trading filings via data.sec.gov/submissions/CIK##########.json. Requires User-Agent header.",
        status="active",
    ),
]

# =============================================================================
# CORPORATE REGISTRY & FINANCIAL DISCLOSURE SOURCES
# =============================================================================

CORPORATE_REGISTRY_SOURCES = [
    DataSource(
        name="UK Companies House REST API",
        jurisdiction="UK",
        institution="Companies House (UK company registry)",
        url="https://api.companieshouse.gov.uk/",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.ASSET_DECLARATIONS],
        access_method=AccessMethod.API,
        update_frequency="Real-time",
        data_format="json",
        api_key_required=True,
        rate_limits="600 requests per 5 minutes per key",
        notes="HTTP Basic Auth using API key as username. Endpoints: /company/{company_number}, /company/{company_number}/filing-history, /officers, /persons-with-significant-control, /search/companies. Some filings/accounts documents are metadata only, not full financial statement parsing. Docs: https://developer.company-information.service.gov.uk/",
        status="active",
    ),
    DataSource(
        name="UK Companies House Streaming API",
        jurisdiction="UK",
        institution="Companies House (UK company registry)",
        url="https://stream.companieshouse.gov.uk/",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.ASSET_DECLARATIONS],
        access_method=AccessMethod.API,
        update_frequency="Real-time (streaming)",
        data_format="json",
        api_key_required=True,
        rate_limits="Streaming connection",
        notes="Streaming API for real-time company changes. Requires stream key obtained via registration. Streams: company information, filing history, insolvency, charges. Delivers JSON events as changes occur. Useful for real-time updates vs polling REST API. Docs: https://www.api.gov.uk/ch/companies-house-streaming/",
        status="active",
    ),
    DataSource(
        name="GetEDGE API (ASIC Australia)",
        jurisdiction="Australia",
        institution="ASIC (Australian Securities and Investments Commission)",
        url="https://getedge.com.au/docs/api",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.ASSET_DECLARATIONS],
        access_method=AccessMethod.API,
        update_frequency="Real-time",
        data_format="json",
        api_key_required=True,
        rate_limits="Varies by subscription",
        notes="Token (API key) authentication. 60-character API key via account portal. Endpoints: Company Registration, Name Change, Business Name Registration, Registry Agent Services, Document production. Oriented to registry/incorporation/document services rather than full financial disclosure data. Requires 'software provider' / digital agent status for some endpoints. Docs: https://getedge.com.au/docs/api",
        status="active",
    ),
    DataSource(
        name="Info-Financière API (France)",
        jurisdiction="France",
        institution="AMF (Autorité des marchés financiers)",
        url="https://info-financiere.gouv.fr/api/v1/console",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.STOCK_TRANSACTIONS],
        access_method=AccessMethod.API,
        update_frequency="Real-time",
        data_format="json",
        api_key_required=False,
        rate_limits="10,000 API calls per IP per day",
        notes="FREE! Open access (accès libre) via OpenData service for publicly listed/regulated disclosures. Returns metadata + original documents (PDF, HTML, XML) plus links. Documents are in issuer's original language and format - not always fully parsed. Some regulatory constraints on personal data/redaction may apply. Docs: https://www.data.gouv.fr/dataservices/api-info-financiere/",
        status="active",
    ),
    DataSource(
        name="Hong Kong Companies Registry e-Monitor API",
        jurisdiction="Hong Kong",
        institution="Companies Registry (Hong Kong)",
        url="https://www.cr.gov.hk/en/electronic/e-servicesportal/",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.ASSET_DECLARATIONS],
        access_method=AccessMethod.API,
        update_frequency="Real-time (notifications)",
        data_format="json",
        api_key_required=True,
        rate_limits="N/A (notification-based)",
        notes="Notification/subscription API - not full search/document retrieval. Users must register and subscribe to 'Other Companies' service (HK$17/year per company) to receive notifications via API. Notifications are JSON via HTTPS POST to subscriber's endpoint. Payload includes change data and encrypted API key header for verification. API endpoint must support HTTPS and validate certificate. Docs: https://www.cr.gov.hk/en/electronic/e-servicesportal/faq/e-monitor.htm",
        status="active",
    ),
    DataSource(
        name="Hong Kong Companies Registry (General)",
        jurisdiction="Hong Kong",
        institution="Companies Registry (Hong Kong)",
        url="https://www.cr.gov.hk/en/electronic/e-servicesportal/",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.ASSET_DECLARATIONS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Real-time",
        data_format="html",
        api_key_required=True,
        rate_limits="Portal-based",
        notes="Requires login/account. Public search services via portal. Not a fully open API. Outputs may be HTML, images, document scans; limited structured data. Corporate registry made more restrictive: directors' residential address/identity data partly redacted; only limited shareholder details publicly accessible. No full open API - requires portal access or purchase.",
        status="planned",
    ),
    DataSource(
        name="OpenCorporates API",
        jurisdiction="Global",
        institution="Third-party aggregator (multi-jurisdiction)",
        url="https://api.opencorporates.com/v0.4/",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.ASSET_DECLARATIONS],
        access_method=AccessMethod.API,
        update_frequency="Daily",
        data_format="json",
        api_key_required=True,
        rate_limits="Varies by tier (free + paid)",
        notes="Global multi-jurisdiction aggregator. Endpoints: /companies/{jurisdiction}/{company_id}, /companies/search, /officers, /filings, /events. Supports pagination. Query parameters: q, jurisdiction_code, company_number, per_page, page, order. Depth of filings/events data depends on jurisdiction and data source - many 'filings' may just be metadata or pointers to documents rather than full statements. Rate limits apply per key. Docs: https://api.opencorporates.com/documentation/API-Reference",
        status="active",
    ),
    DataSource(
        name="Transparent Data - Company Registers API",
        jurisdiction="EU/Europe",
        institution="Third-party aggregator (EU registry metadata)",
        url="https://apidoc.transparentdata.pl/company_registers_api.html",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.ASSET_DECLARATIONS],
        access_method=AccessMethod.API,
        update_frequency="Daily",
        data_format="json",
        api_key_required=True,
        rate_limits="Varies by subscription",
        notes="EU/Europe registry aggregator. Covers registry/legal metadata rather than full financial statements or regulatory filings. Likely JSON REST style with parameters for jurisdiction, company registration number, etc. Docs: https://apidoc.transparentdata.pl/company_registers_api.html",
        status="active",
    ),
    DataSource(
        name="XBRL/ESEF/UKSEF via filings.xbrl.org",
        jurisdiction="EU/UK/Ukraine",
        institution="XBRL International (standardized financial reporting)",
        url="https://filings.xbrl.org/",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.ASSET_DECLARATIONS],
        access_method=AccessMethod.API,
        update_frequency="Daily",
        data_format="json",
        api_key_required=False,
        rate_limits="None specified",
        notes="FREE! JSON:API compliant responses. Filtering via query parameters (filter[...]), pagination, sorting. Covers EU/UK/Ukraine filings. Some jurisdictions' filings missing (e.g., Germany, Ireland) as of current state. Endpoints: /filings, /entities, /validation_messages. Docs: https://filings.xbrl.org/docs/api",
        status="active",
    ),
    DataSource(
        name="XBRL US API",
        jurisdiction="USA",
        institution="XBRL US (financial data standardization)",
        url="https://github.com/xbrlus/xbrl-api",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.STOCK_TRANSACTIONS],
        access_method=AccessMethod.API,
        update_frequency="Real-time (~15 min latency from SEC)",
        data_format="json",
        api_key_required=True,
        rate_limits="Varies by tier",
        notes="FREE API key available. JSON/REST endpoints for company, filing, facts. Fact-level retrieval mapping XBRL tags to numeric values. Latency ~15 minutes behind SEC updates. Best for programmatic fact extraction from SEC filings. Docs: https://github.com/xbrlus/xbrl-api",
        status="active",
    ),
    DataSource(
        name="XBRLAnalyst API",
        jurisdiction="USA",
        institution="Third-party aggregator (SEC filings)",
        url="https://www.finddynamics.com/",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.STOCK_TRANSACTIONS],
        access_method=AccessMethod.API,
        update_frequency="Real-time",
        data_format="json",
        api_key_required=True,
        rate_limits="Varies by subscription",
        notes="Endpoints for firms, filings, statements, metrics. JSON (default) or XML (via format parameter). Free (limited) access for non-registered users for core metrics; full access for subscribers. Focused on US public companies (SEC filings).",
        status="active",
    ),
]

# =============================================================================
# CONSOLIDATED SOURCE MAPPING
# =============================================================================

ALL_DATA_SOURCES = {
    "us_federal": US_FEDERAL_SOURCES,
    "us_states": US_STATE_SOURCES,
    "eu_parliament": EU_PARLIAMENT_SOURCES,
    "eu_national": EU_NATIONAL_SOURCES,
    "third_party": THIRD_PARTY_SOURCES,
    "corporate_registry": CORPORATE_REGISTRY_SOURCES,
}

# Summary statistics
TOTAL_SOURCES = sum(len(sources) for sources in ALL_DATA_SOURCES.values())
ACTIVE_SOURCES = sum(
    len([s for s in sources if s.status == "active"]) for sources in ALL_DATA_SOURCES.values()
)


def get_sources_by_jurisdiction(jurisdiction: str) -> List[DataSource]:
    """Get all sources for a specific jurisdiction (e.g., 'US-CA', 'DE', 'EU')"""
    all_sources = []
    for source_group in ALL_DATA_SOURCES.values():
        all_sources.extend([s for s in source_group if s.jurisdiction == jurisdiction])
    return all_sources


def get_sources_by_type(disclosure_type: DisclosureType) -> List[DataSource]:
    """Get all sources that provide a specific type of disclosure"""
    all_sources = []
    for source_group in ALL_DATA_SOURCES.values():
        all_sources.extend([s for s in source_group if disclosure_type in s.disclosure_types])
    return all_sources


def get_api_sources() -> List[DataSource]:
    """Get all sources that provide API access"""
    all_sources = []
    for source_group in ALL_DATA_SOURCES.values():
        all_sources.extend([s for s in source_group if s.access_method == AccessMethod.API])
    return all_sources


# Export for use in workflow configuration
__all__ = [
    "DataSource",
    "DisclosureType",
    "AccessMethod",
    "ALL_DATA_SOURCES",
    "get_sources_by_jurisdiction",
    "get_sources_by_type",
    "get_api_sources",
    "TOTAL_SOURCES",
    "ACTIVE_SOURCES",
]
