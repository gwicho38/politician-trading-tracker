"""
Data models for politician trading information
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional


class PoliticianRole(Enum):
    """Political roles"""

    US_HOUSE_REP = "us_house_representative"
    US_SENATOR = "us_senator"
    UK_MP = "uk_member_of_parliament"
    EU_MEP = "eu_parliament_member"
    EU_COMMISSIONER = "eu_commissioner"
    EU_COUNCIL_MEMBER = "eu_council_member"

    # EU Member State Roles
    GERMAN_BUNDESTAG = "german_bundestag_member"
    FRENCH_DEPUTY = "french_national_assembly_deputy"
    ITALIAN_DEPUTY = "italian_chamber_deputy"
    ITALIAN_SENATOR = "italian_senate_member"
    SPANISH_DEPUTY = "spanish_congress_deputy"
    DUTCH_MP = "dutch_tweede_kamer_member"

    # US State Roles
    TEXAS_STATE_OFFICIAL = "texas_state_official"
    NEW_YORK_STATE_OFFICIAL = "new_york_state_official"
    FLORIDA_STATE_OFFICIAL = "florida_state_official"
    ILLINOIS_STATE_OFFICIAL = "illinois_state_official"
    PENNSYLVANIA_STATE_OFFICIAL = "pennsylvania_state_official"
    MASSACHUSETTS_STATE_OFFICIAL = "massachusetts_state_official"
    CALIFORNIA_STATE_OFFICIAL = "california_state_official"


class TransactionType(Enum):
    """Types of financial transactions"""

    PURCHASE = "purchase"
    SALE = "sale"
    EXCHANGE = "exchange"
    OPTION_PURCHASE = "option_purchase"
    OPTION_SALE = "option_sale"


class DisclosureStatus(Enum):
    """Status of disclosure processing"""

    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    DUPLICATE = "duplicate"


@dataclass
class Politician:
    """Politician information"""

    id: Optional[str] = None
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    role: str = "House"  # Can be string or PoliticianRole enum
    party: str = ""
    state_or_country: str = ""
    district: Optional[str] = None
    term_start: Optional[datetime] = None
    term_end: Optional[datetime] = None

    # External identifiers
    bioguide_id: Optional[str] = None  # US Congress bioguide ID
    eu_id: Optional[str] = None  # EU Parliament ID

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TradingDisclosure:
    """Individual trading disclosure"""

    id: Optional[str] = None
    politician_id: str = ""
    politician_bioguide_id: Optional[str] = None  # For lookups before politician_id is assigned

    # Transaction details
    transaction_date: datetime = field(default_factory=datetime.utcnow)
    disclosure_date: datetime = field(default_factory=datetime.utcnow)
    transaction_type: TransactionType = TransactionType.PURCHASE

    # Asset information
    asset_name: str = ""
    asset_ticker: Optional[str] = None
    asset_type: str = ""  # stock, bond, option, etc.

    # Financial details
    amount_range_min: Optional[Decimal] = None
    amount_range_max: Optional[Decimal] = None
    amount_exact: Optional[Decimal] = None

    # Source information
    source_url: str = ""
    source_document_id: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    # Processing status
    status: DisclosureStatus = DisclosureStatus.PENDING
    processing_notes: str = ""

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DataPullJob:
    """Information about data pull jobs"""

    id: Optional[str] = None
    job_type: str = ""  # "us_congress", "eu_parliament", etc.
    status: str = "pending"  # pending, running, completed, failed

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    records_found: int = 0
    records_processed: int = 0
    records_new: int = 0
    records_updated: int = 0
    records_failed: int = 0

    # Error information
    error_message: Optional[str] = None
    error_details: Dict[str, Any] = field(default_factory=dict)

    # Configuration used
    config_snapshot: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DataSource:
    """Information about data sources"""

    id: Optional[str] = None
    name: str = ""
    url: str = ""
    source_type: str = ""  # "official", "aggregator", "api"
    region: str = ""  # "us", "eu"

    # Status tracking
    is_active: bool = True
    last_successful_pull: Optional[datetime] = None
    last_attempt: Optional[datetime] = None
    consecutive_failures: int = 0

    # Configuration
    request_config: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# Corporate Registry Models
# =============================================================================


@dataclass
class Company:
    """Corporate registry company information"""

    id: Optional[str] = None
    company_number: str = ""  # Registration number in jurisdiction
    company_name: str = ""
    jurisdiction: str = ""  # Country/region code (e.g., "GB", "US", "FR")

    # Company details
    company_type: Optional[str] = None
    status: str = "active"  # active, dissolved, liquidation, etc.
    incorporation_date: Optional[datetime] = None
    registered_address: Optional[str] = None

    # Business information
    sic_codes: List[str] = field(default_factory=list)  # Standard Industrial Classification
    nature_of_business: Optional[str] = None

    # Source information
    source: str = ""  # "uk_companies_house", "opencorporates", etc.
    source_url: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CompanyOfficer:
    """Company officer/director information"""

    id: Optional[str] = None
    company_id: str = ""  # Foreign key to Company

    # Officer details
    name: str = ""
    officer_role: str = ""  # director, secretary, etc.
    appointed_on: Optional[datetime] = None
    resigned_on: Optional[datetime] = None

    # Personal details (may be limited by privacy laws)
    nationality: Optional[str] = None
    occupation: Optional[str] = None
    country_of_residence: Optional[str] = None
    date_of_birth: Optional[datetime] = None  # Often only month/year available

    # Address (often redacted for privacy)
    address: Optional[str] = None

    # Source information
    source: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PersonWithSignificantControl:
    """Person with significant control (PSC) - UK Companies House"""

    id: Optional[str] = None
    company_id: str = ""  # Foreign key to Company

    # PSC details
    name: str = ""
    kind: str = (
        ""  # individual-person-with-significant-control, corporate-entity-person-with-significant-control, etc.
    )

    # Control nature
    natures_of_control: List[str] = field(
        default_factory=list
    )  # ownership-of-shares-75-to-100-percent, etc.
    notified_on: Optional[datetime] = None

    # Personal details (may be redacted)
    nationality: Optional[str] = None
    country_of_residence: Optional[str] = None
    date_of_birth: Optional[datetime] = None  # Usually only month/year

    # Address
    address: Optional[str] = None

    # Source information
    source: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class FinancialPublication:
    """Financial publication/disclosure (e.g., France Info-Financière)"""

    id: Optional[str] = None
    publication_id: str = ""  # Source publication ID

    # Publication details
    title: str = ""
    publication_type: str = ""  # prospectus, annual-report, regulatory-filing, etc.
    publication_date: datetime = field(default_factory=datetime.utcnow)

    # Issuer/company
    issuer_name: Optional[str] = None
    issuer_id: Optional[str] = None  # LEI, ISIN, or other identifier
    company_id: Optional[str] = None  # Foreign key to Company (if linked)

    # Document information
    document_url: Optional[str] = None
    document_format: Optional[str] = None  # pdf, html, xml
    language: Optional[str] = None

    # Source information
    source: str = ""  # "info_financiere", "xbrl_filings", etc.
    jurisdiction: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class XBRLFiling:
    """XBRL financial statement filing"""

    id: Optional[str] = None
    filing_id: str = ""  # Source filing ID

    # Filing details
    entity_name: str = ""
    entity_id: Optional[str] = None  # LEI or other identifier
    company_id: Optional[str] = None  # Foreign key to Company (if linked)

    # Filing information
    filing_date: datetime = field(default_factory=datetime.utcnow)
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    fiscal_year: Optional[int] = None
    fiscal_period: Optional[str] = None  # Q1, Q2, FY, etc.

    # Document
    document_url: Optional[str] = None
    taxonomy: Optional[str] = None  # ESEF, UKSEF, US-GAAP, etc.

    # Source information
    source: str = ""  # "xbrl_filings", "xbrl_us", etc.
    jurisdiction: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
