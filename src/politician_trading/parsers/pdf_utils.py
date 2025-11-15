"""
PDF parsing utilities for House financial disclosures.

This module provides helper functions for parsing House financial disclosure PDFs
according to the enhanced parsing specifications.
"""

import re
import logging
from decimal import Decimal
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

import yfinance as yf

# Optional fuzzy matching dependency
try:
    from rapidfuzz import fuzz, process

    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    fuzz = None
    process = None

logger = logging.getLogger(__name__)


# Asset type codes from House disclosure system
# https://fd.house.gov/reference/asset-type-codes.aspx
ASSET_TYPE_CODES = {
    "4K": "401K and Other Non-Federal Retirement Accounts",
    "5C": "529 College Savings Plan",
    "5F": "529 Portfolio",
    "5P": "529 Prepaid Tuition Plan",
    "AB": "Asset-Backed Securities",
    "BA": "Bank Accounts, Money Market Accounts and CDs",
    "BK": "Brokerage Accounts",
    "CO": "Collectibles",
    "CS": "Corporate Securities (Bonds and Notes)",
    "CT": "Cryptocurrency",
    "DB": "Defined Benefit Pension",
    "DO": "Debts Owed to the Filer",
    "DS": "Delaware Statutory Trust",
    "EF": "Exchange Traded Funds (ETF)",
    "EQ": "Excepted/Qualified Blind Trust",
    "ET": "Exchange Traded Notes",
    "FA": "Farms",
    "FE": "Foreign Exchange Position (Currency)",
    "FN": "Fixed Annuity",
    "FU": "Futures",
    "GS": "Government Securities and Agency Debt",
    "HE": "Hedge Funds & Private Equity Funds (EIF)",
    "HN": "Hedge Funds & Private Equity Funds (non-EIF)",
    "IC": "Investment Club",
    "IH": "IRA (Held in Cash)",
    "IP": "Intellectual Property & Royalties",
    "IR": "IRA",
    "MA": "Managed Accounts (e.g., SMA and UMA)",
    "MF": "Mutual Funds",
    "MO": "Mineral/Oil/Solar Energy Rights",
    "OI": "Ownership Interest (Holding Investments)",
    "OL": "Ownership Interest (Engaged in a Trade or Business)",
    "OP": "Options",
    "OT": "Other",
    "PE": "Pensions",
    "PM": "Precious Metals",
    "PS": "Stock (Not Publicly Traded)",
    "RE": "Real Estate Invest. Trust (REIT)",
    "RF": "REIT (EIF)",
    "RN": "REIT (non-EIF)",
    "RP": "Real Property",
    "RS": "Restricted Stock Units (RSUs)",
    "SA": "Stock Appreciation Right",
    "ST": "Stocks (including ADRs)",
    "TR": "Trust",
    "VA": "Variable Annuity",
    "VI": "Variable Insurance",
    "WU": "Whole/Universal Insurance",
}


def parse_asset_type(text: str) -> tuple[Optional[str], Optional[str]]:
    """
    Parse asset type code from text.

    Args:
        text: Text that may contain asset type code like [ST], [MF], etc.

    Returns:
        Tuple of (code, description) or (None, None) if not found
    """
    if not text:
        return None, None

    # Look for pattern [XX] where XX is 2-3 uppercase letters/digits
    match = re.search(r"\[([A-Z0-9]{2,3})\]", text)
    if match:
        code = match.group(1)
        description = ASSET_TYPE_CODES.get(code)
        return code, description

    return None, None


class TickerResolver:
    """Resolves company names to ticker symbols using various strategies"""

    def __init__(self):
        self._cache: Dict[str, Tuple[Optional[str], float]] = {}
        self._common_tickers = self._load_common_tickers()

    def _load_common_tickers(self) -> Dict[str, str]:
        """Load common company name -> ticker mappings"""
        # Common mappings to avoid API calls
        return {
            "apple inc": "AAPL",
            "microsoft corporation": "MSFT",
            "amazon.com inc": "AMZN",
            "alphabet inc": "GOOGL",
            "meta platforms inc": "META",
            "tesla inc": "TSLA",
            "nvidia corporation": "NVDA",
            "berkshire hathaway": "BRK.B",
            "jpmorgan chase": "JPM",
            "johnson & johnson": "JNJ",
            "visa inc": "V",
            "procter & gamble": "PG",
            "unitedhealth group": "UNH",
            "home depot": "HD",
            "mastercard": "MA",
            "pfizer inc": "PFE",
            "coca-cola": "KO",
            "pepsico": "PEP",
            "walmart": "WMT",
            "netflix": "NFLX",
            "adobe": "ADBE",
            "salesforce": "CRM",
            "cisco systems": "CSCO",
            "intel corporation": "INTC",
            "verizon": "VZ",
            "at&t": "T",
            "bank of america": "BAC",
            "wells fargo": "WFC",
            "goldman sachs": "GS",
            "morgan stanley": "MS",
            "citigroup": "C",
            "american express": "AXP",
            "3m company": "MMM",
            "caterpillar": "CAT",
            "boeing": "BA",
            "general electric": "GE",
            "exxon mobil": "XOM",
            "chevron": "CVX",
            "conocophillips": "COP",
        }

    def resolve(self, asset_name: str) -> Tuple[Optional[str], float]:
        """
        Resolve ticker symbol from asset name.

        Args:
            asset_name: Asset name from disclosure (e.g., "Apple Inc")

        Returns:
            Tuple of (ticker_symbol, confidence_score)
            confidence_score is 0.0-1.0, where:
            - 1.0 = Exact match in common tickers
            - 0.8-0.9 = Fuzzy match in common tickers
            - 0.6-0.7 = Yahoo Finance lookup succeeded
            - 0.0 = Could not resolve
        """
        if not asset_name or not asset_name.strip():
            return None, 0.0

        # Check cache
        cache_key = asset_name.lower().strip()
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Strategy 1: Exact match in common tickers
        ticker, confidence = self._exact_match(asset_name)
        if ticker:
            self._cache[cache_key] = (ticker, confidence)
            return ticker, confidence

        # Strategy 2: Fuzzy match in common tickers
        ticker, confidence = self._fuzzy_match(asset_name)
        if ticker and confidence >= 0.75:
            self._cache[cache_key] = (ticker, confidence)
            return ticker, confidence

        # Strategy 3: Yahoo Finance lookup (slow, use sparingly)
        ticker, confidence = self._yfinance_lookup(asset_name)
        self._cache[cache_key] = (ticker, confidence)
        return ticker, confidence

    def _exact_match(self, asset_name: str) -> Tuple[Optional[str], float]:
        """Check for exact match in common tickers"""
        normalized = asset_name.lower().strip()
        # Remove common suffixes
        for suffix in [" inc", " corp", " corporation", " llc", " ltd", " company", " co"]:
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)].strip()

        if normalized in self._common_tickers:
            return self._common_tickers[normalized], 1.0

        return None, 0.0

    def _fuzzy_match(self, asset_name: str) -> Tuple[Optional[str], float]:
        """Fuzzy match against common tickers"""
        if not RAPIDFUZZ_AVAILABLE:
            logger.debug("rapidfuzz not available - skipping fuzzy matching")
            return None, 0.0

        normalized = asset_name.lower().strip()

        # Use rapidfuzz to find best match
        result = process.extractOne(
            normalized,
            self._common_tickers.keys(),
            scorer=fuzz.ratio,
            score_cutoff=75,  # Only return if >75% match
        )

        if result:
            matched_name, score, _ = result
            confidence = score / 100.0  # Convert to 0-1 scale
            return self._common_tickers[matched_name], confidence

        return None, 0.0

    def _yfinance_lookup(self, asset_name: str) -> Tuple[Optional[str], float]:
        """Attempt to resolve via Yahoo Finance (slow)"""
        try:
            # Try searching - this is an approximation
            # yfinance doesn't have a great search API, so we'll try the name as ticker first
            normalized = asset_name.upper().replace(" ", "").replace(".", "")[:5]

            ticker = yf.Ticker(normalized)
            info = ticker.info

            # If we got valid info, it's probably right
            if info and "shortName" in info:
                logger.debug(f"Yahoo Finance resolved '{asset_name}' to {normalized}")
                return normalized, 0.65

        except Exception as e:
            logger.debug(f"Yahoo Finance lookup failed for '{asset_name}': {e}")

        return None, 0.0


class ValueRangeParser:
    """Parses value ranges from disclosure text"""

    # Common range patterns in House disclosures
    RANGE_PATTERNS = [
        # "$1,001 - $15,000"
        r"\$?([\d,]+)\s*-\s*\$?([\d,]+)",
        # "$1,001-$15,000"
        r"\$?([\d,]+)-\$?([\d,]+)",
        # "$1,001 to $15,000"
        r"\$?([\d,]+)\s+to\s+\$?([\d,]+)",
        # "Over $50,000,000"
        r"[Oo]ver\s+\$?([\d,]+)",
        # "$15,000 or less"
        r"\$?([\d,]+)\s+or\s+less",
    ]

    @staticmethod
    def parse(value_text: str) -> Dict[str, Any]:
        """
        Parse value range from text.

        Args:
            value_text: Text like "$1,001 - $15,000"

        Returns:
            Dict with keys:
            - value_low: Lower bound (Decimal)
            - value_high: Upper bound (Decimal)
            - is_range: Boolean
            - midpoint: Calculated midpoint (Decimal)
            - original_text: Original input
        """
        if not value_text or not value_text.strip():
            return {
                "value_low": None,
                "value_high": None,
                "is_range": False,
                "midpoint": None,
                "original_text": value_text,
            }

        cleaned = value_text.replace(",", "").strip()

        # Try each pattern
        for pattern in ValueRangeParser.RANGE_PATTERNS:
            match = re.search(pattern, cleaned, re.IGNORECASE)
            if match:
                groups = match.groups()

                if len(groups) == 2:
                    # Range pattern
                    try:
                        low = Decimal(groups[0])
                        high = Decimal(groups[1])
                        return {
                            "value_low": low,
                            "value_high": high,
                            "is_range": True,
                            "midpoint": (low + high) / 2,
                            "original_text": value_text,
                        }
                    except (ValueError, ArithmeticError) as e:
                        logger.warning(f"Failed to parse range '{value_text}': {e}")
                        continue

                elif len(groups) == 1:
                    # Single value (over/under pattern)
                    try:
                        value = Decimal(groups[0])
                        if "over" in cleaned.lower():
                            return {
                                "value_low": value,
                                "value_high": None,
                                "is_range": False,
                                "midpoint": value,
                                "original_text": value_text,
                            }
                        else:  # "or less"
                            return {
                                "value_low": None,
                                "value_high": value,
                                "is_range": False,
                                "midpoint": value / 2,
                                "original_text": value_text,
                            }
                    except (ValueError, ArithmeticError) as e:
                        logger.warning(f"Failed to parse value '{value_text}': {e}")
                        continue

        # If no pattern matched, try single number
        try:
            # Remove $ and commas, try to parse as single number
            number_match = re.search(r"([\d,]+(?:\.\d+)?)", cleaned)
            if number_match:
                value = Decimal(number_match.group(1).replace(",", ""))
                return {
                    "value_low": value,
                    "value_high": value,
                    "is_range": False,
                    "midpoint": value,
                    "original_text": value_text,
                }
        except (ValueError, ArithmeticError) as e:
            logger.warning(f"Failed to parse as single value '{value_text}': {e}")

        # Could not parse
        return {
            "value_low": None,
            "value_high": None,
            "is_range": False,
            "midpoint": None,
            "original_text": value_text,
        }


class OwnerParser:
    """Parses owner designation from disclosure text"""

    # Owner mappings
    OWNER_MAP = {
        "jt": "JOINT",
        "joint": "JOINT",
        "sp": "SPOUSE",
        "spouse": "SPOUSE",
        "s": "SPOUSE",
        "self": "SELF",
        "filer": "SELF",
        "dep": "DEPENDENT",
        "dependent": "DEPENDENT",
        "dc": "DEPENDENT",  # Dependent child
    }

    @staticmethod
    def parse(owner_text: str) -> str:
        """
        Parse owner designation.

        Args:
            owner_text: Text like "JT", "SP", "Self", etc.

        Returns:
            Standardized owner: "SELF", "SPOUSE", "JOINT", or "DEPENDENT"
            Defaults to "SELF" if cannot parse
        """
        if not owner_text or not owner_text.strip():
            return "SELF"

        normalized = owner_text.lower().strip()

        # Direct lookup
        if normalized in OwnerParser.OWNER_MAP:
            return OwnerParser.OWNER_MAP[normalized]

        # Partial match
        for key, value in OwnerParser.OWNER_MAP.items():
            if key in normalized:
                return value

        # Default to SELF
        logger.debug(f"Could not parse owner '{owner_text}', defaulting to SELF")
        return "SELF"


class DateParser:
    """Parses dates from disclosure text"""

    # Common date formats in House disclosures
    DATE_FORMATS = [
        "%m/%d/%Y",  # 11/15/2024
        "%m-%d-%Y",  # 11-15-2024
        "%m/%d/%y",  # 11/15/24
        "%m-%d-%y",  # 11-15-24
        "%Y-%m-%d",  # 2024-11-15 (ISO)
        "%B %d, %Y",  # November 15, 2024
        "%b %d, %Y",  # Nov 15, 2024
        "%m/%d/%Y %H:%M",  # 11/15/2024 14:30
    ]

    @staticmethod
    def parse(date_text: str) -> Optional[datetime]:
        """
        Parse date from text.

        Args:
            date_text: Date string

        Returns:
            datetime object or None if cannot parse
        """
        if not date_text or not date_text.strip():
            return None

        cleaned = date_text.strip()

        # Try each format
        for fmt in DateParser.DATE_FORMATS:
            try:
                return datetime.strptime(cleaned, fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse date '{date_text}'")
        return None

    @staticmethod
    def to_iso(date_text: str) -> Optional[str]:
        """Parse date and return ISO format string"""
        dt = DateParser.parse(date_text)
        return dt.isoformat() if dt else None


def extract_ticker_from_text(text: str) -> Optional[str]:
    """
    Extract explicit ticker symbol from text.

    Looks for patterns like:
    - (AAPL)
    - Ticker: GOOGL
    - Symbol: TSLA

    NOTE: Does NOT match brackets [XX] because those are asset type codes!

    Args:
        text: Text that may contain ticker

    Returns:
        Ticker symbol or None
    """
    if not text:
        return None

    # Pattern 1: Parentheses - this is the most reliable for tickers
    match = re.search(r"\(([A-Z]{1,5})\)", text)
    if match:
        potential = match.group(1)
        # Filter out asset type codes that might be in parens
        if potential not in ASSET_TYPE_CODES:
            return potential

    # Pattern 2: "Ticker:" or "Symbol:"
    match = re.search(r"(?:Ticker|Symbol):\s*([A-Z]{1,5})", text, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern 3: Standalone uppercase 1-5 letters at end
    match = re.search(r"\b([A-Z]{1,5})\s*$", text)
    if match:
        potential = match.group(1)
        # Filter out common false positives AND asset type codes
        if (
            potential not in ["INC", "LLC", "LTD", "CORP", "CO", "LP"]
            and potential not in ASSET_TYPE_CODES
        ):
            return potential

    return None
