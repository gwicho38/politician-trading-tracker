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


class SignalType(Enum):
    """Types of trading signals"""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"


class SignalStrength(Enum):
    """Signal strength levels"""

    VERY_WEAK = "very_weak"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class OrderStatus(Enum):
    """Order execution status"""

    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderType(Enum):
    """Types of orders"""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class TradingMode(Enum):
    """Trading mode"""

    PAPER = "paper"
    LIVE = "live"


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

    # Enhanced fields from Phase 5 parser (Issue #16)
    filer_id: Optional[str] = None  # House disclosure document ID
    filing_date: Optional[str] = None  # Date the disclosure was filed
    ticker_confidence_score: Optional[Decimal] = None  # 0.0-1.0 confidence in ticker resolution
    asset_owner: Optional[str] = None  # SELF, SPOUSE, JOINT, DEPENDENT
    specific_owner_text: Optional[str] = None  # Specific owner text from disclosure (e.g., "DG Trust")
    asset_type_code: Optional[str] = None  # House disclosure asset type code ([ST], [MF], etc.)
    notification_date: Optional[datetime] = None  # Date transaction was notified
    filing_status: Optional[str] = None  # New, Amendment, etc.
    quantity: Optional[Decimal] = None  # Quantity of shares/units if specified

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


# =============================================================================
# Trading Signal and Order Models
# =============================================================================


@dataclass
class TradingSignal:
    """Predictive trading signal based on politician trading activity"""

    id: Optional[Any] = None  # Can be UUID or str
    ticker: str = ""
    asset_name: str = ""

    # Signal details
    signal_type: SignalType = SignalType.HOLD
    signal_strength: SignalStrength = SignalStrength.MODERATE
    confidence_score: float = 0.0  # 0.0 to 1.0

    # Price targets
    target_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None

    # Signal generation info
    generated_at: datetime = field(default_factory=datetime.utcnow)
    valid_until: Optional[datetime] = None
    model_version: str = ""

    # Supporting data
    politician_activity_count: int = 0  # Number of politicians trading this asset
    total_transaction_volume: Optional[Decimal] = None
    buy_sell_ratio: float = 0.0  # Ratio of buys to sells
    avg_politician_return: Optional[float] = None  # Historical returns

    # Feature data for the signal
    features: Dict[str, Any] = field(default_factory=dict)

    # Related disclosures
    disclosure_ids: List[str] = field(default_factory=list)

    # Status
    is_active: bool = True
    notes: str = ""

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TradingOrder:
    """Trading order execution record"""

    id: Optional[str] = None
    signal_id: Optional[str] = None  # Foreign key to TradingSignal

    # Order details
    ticker: str = ""
    order_type: OrderType = OrderType.MARKET
    side: str = "buy"  # buy or sell
    quantity: int = 0
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    trailing_percent: Optional[float] = None

    # Execution details
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    filled_avg_price: Optional[Decimal] = None
    commission: Optional[Decimal] = None

    # Trading mode
    trading_mode: TradingMode = TradingMode.PAPER

    # Alpaca order info
    alpaca_order_id: Optional[str] = None
    alpaca_client_order_id: Optional[str] = None

    # Timestamps
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None

    # Error information
    error_message: Optional[str] = None
    reject_reason: Optional[str] = None

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Portfolio:
    """Portfolio tracking for paper and live trading"""

    id: Optional[str] = None
    name: str = ""
    trading_mode: TradingMode = TradingMode.PAPER

    # Portfolio metrics
    cash: Decimal = Decimal("0")
    portfolio_value: Decimal = Decimal("0")
    buying_power: Decimal = Decimal("0")

    # Performance metrics
    total_return: Optional[float] = None
    total_return_pct: Optional[float] = None
    day_return: Optional[float] = None
    day_return_pct: Optional[float] = None

    # Risk metrics
    max_drawdown: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    win_rate: Optional[float] = None

    # Position counts
    long_positions: int = 0
    short_positions: int = 0

    # Alpaca account info
    alpaca_account_id: Optional[str] = None
    alpaca_account_status: Optional[str] = None

    # Configuration
    max_position_size: Optional[Decimal] = None
    max_portfolio_risk: Optional[float] = None
    is_active: bool = True

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Position:
    """Individual position in a portfolio"""

    id: Optional[str] = None
    portfolio_id: str = ""

    # Position details
    ticker: str = ""
    asset_name: str = ""
    quantity: int = 0
    side: str = "long"  # long or short

    # Cost basis
    avg_entry_price: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")

    # Current value
    current_price: Decimal = Decimal("0")
    market_value: Decimal = Decimal("0")
    unrealized_pl: Decimal = Decimal("0")
    unrealized_pl_pct: float = 0.0

    # Realized P&L (for closed positions)
    realized_pl: Optional[Decimal] = None
    realized_pl_pct: Optional[float] = None

    # Entry/exit info
    opened_at: datetime = field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None

    # Related signals and orders
    signal_ids: List[str] = field(default_factory=list)
    order_ids: List[str] = field(default_factory=list)

    # Risk management
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None

    # Status
    is_open: bool = True

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# Enhanced House Disclosure Models (Issue #16)
# =============================================================================


@dataclass
class CapitalGain:
    """Capital gain reported in House financial disclosure"""

    id: Optional[str] = None
    politician_id: str = ""
    disclosure_id: Optional[str] = None

    # Asset information
    asset_name: str = ""
    asset_ticker: Optional[str] = None

    # Transaction dates
    date_acquired: Optional[datetime] = None
    date_sold: Optional[datetime] = None

    # Gain information
    gain_type: Optional[str] = None  # SHORT_TERM or LONG_TERM
    gain_amount: Optional[Decimal] = None

    # Owner attribution
    asset_owner: str = "SELF"  # SELF, SPOUSE, JOINT, DEPENDENT

    # Additional context
    comments: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AssetHolding:
    """Asset holding from Part V of House financial disclosure"""

    id: Optional[str] = None
    politician_id: str = ""

    # Filing information
    filing_date: Optional[datetime] = None
    filing_doc_id: Optional[str] = None

    # Asset information
    asset_name: str = ""
    asset_type: Optional[str] = None  # [OT], [BA], [ST], [MF], etc.
    asset_ticker: Optional[str] = None
    asset_description: Optional[str] = None

    # Owner attribution
    owner: str = "SELF"  # SELF, SPOUSE, JOINT, DEPENDENT

    # Valuation
    value_low: Optional[Decimal] = None
    value_high: Optional[Decimal] = None
    value_category: Optional[str] = None  # e.g., "$1,001-$15,000"

    # Income information
    income_type: Optional[str] = None  # Dividends, Interest, Rent, etc.
    current_year_income: Optional[Decimal] = None
    preceding_year_income: Optional[Decimal] = None

    # Additional context
    comments: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
