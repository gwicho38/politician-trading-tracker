"""
Utility functions for extracting and cleaning stock tickers
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def extract_ticker_from_text(text: str) -> Optional[str]:
    """
    Extract stock ticker from various text formats.

    Handles formats like:
    - "Apple Inc. (AAPL)"
    - "AAPL - Apple Inc."
    - "Microsoft Corporation - MSFT"
    - "TSLA"
    - "Apple Inc. Common Stock (AAPL)"

    Args:
        text: Text potentially containing a ticker symbol

    Returns:
        Cleaned ticker symbol or None if not found
    """
    if not text or not isinstance(text, str):
        return None

    text = text.strip()

    # Pattern 1: Ticker in parentheses (most common)
    # Examples: "Apple Inc. (AAPL)", "Tesla Motors (TSLA)"
    match = re.search(r"\(([A-Z]{1,5})\)", text)
    if match:
        return match.group(1)

    # Pattern 2: Ticker after dash or hyphen
    # Examples: "AAPL - Apple Inc.", "Microsoft - MSFT"
    match = re.search(r"[-–]\s*([A-Z]{1,5})(?:\s|$)", text)
    if match:
        return match.group(1)

    # Pattern 3: Ticker before dash
    # Examples: "AAPL - Apple Inc."
    match = re.search(r"^([A-Z]{1,5})\s*[-–]", text)
    if match:
        return match.group(1)

    # Pattern 4: Just a ticker (2-5 uppercase letters)
    # Examples: "AAPL", "MSFT", "GOOGL"
    match = re.search(r"\b([A-Z]{2,5})\b", text)
    if match:
        ticker = match.group(1)
        # Exclude common false positives
        excluded = {
            "INC",
            "LLC",
            "LTD",
            "CORP",
            "CO",
            "THE",
            "AND",
            "OR",
            "ETF",
            "FUND",
            "LP",
            "NA",
        }
        if ticker not in excluded:
            return ticker

    return None


def clean_ticker(ticker: Optional[str]) -> Optional[str]:
    """
    Clean and validate a ticker symbol.

    Args:
        ticker: Raw ticker string

    Returns:
        Cleaned ticker or None if invalid
    """
    if not ticker:
        return None

    # Remove whitespace and convert to uppercase
    ticker = str(ticker).strip().upper()

    # Remove common suffixes and prefixes
    ticker = ticker.replace("STOCK", "").replace("COMMON", "").strip()

    # Extract just the ticker if it's in a longer string
    extracted = extract_ticker_from_text(ticker)
    if extracted:
        ticker = extracted

    # Validate: 1-5 uppercase letters, optionally with a dot
    if re.match(r"^[A-Z]{1,5}(?:\.[A-Z])?$", ticker):
        return ticker

    return None


def extract_ticker_from_asset_name(asset_name: str) -> Optional[str]:
    """
    Extract ticker from asset name field.

    This is the main function to use when processing disclosure data.

    Args:
        asset_name: The asset/security name from disclosure

    Returns:
        Extracted and cleaned ticker symbol or None
    """
    if not asset_name:
        return None

    # Try direct extraction first
    ticker = extract_ticker_from_text(asset_name)
    if ticker:
        return clean_ticker(ticker)

    # Handle special cases
    asset_name_lower = asset_name.lower()

    # Common company names to ticker mappings (for when ticker isn't in the text)
    common_mappings = {
        "apple": "AAPL",
        "microsoft": "MSFT",
        "amazon": "AMZN",
        "google": "GOOGL",
        "alphabet": "GOOGL",
        "tesla": "TSLA",
        "meta": "META",
        "facebook": "META",
        "nvidia": "NVDA",
        "netflix": "NFLX",
        "disney": "DIS",
    }

    for name, ticker in common_mappings.items():
        if name in asset_name_lower:
            logger.info(f"Mapped '{asset_name}' to ticker '{ticker}' via common mappings")
            return ticker

    return None


def validate_ticker(ticker: Optional[str]) -> bool:
    """
    Validate if a string is a valid ticker symbol.

    Args:
        ticker: Ticker to validate

    Returns:
        True if valid ticker format, False otherwise
    """
    if not ticker:
        return False

    ticker = str(ticker).strip().upper()

    # Valid tickers: 1-5 uppercase letters, optionally with a dot
    return bool(re.match(r"^[A-Z]{1,5}(?:\.[A-Z])?$", ticker))
