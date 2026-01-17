import re
from typing import Optional, Any, Dict, Tuple

# Value range patterns for parsing
VALUE_PATTERNS = [
    (r"\$1,001\s*-\s*\$15,000", 1001, 15000),
    (r"\$15,001\s*-\s*\$50,000", 15001, 50000),
    (r"\$50,001\s*-\s*\$100,000", 50001, 100000),
    (r"\$100,001\s*-\s*\$250,000", 100001, 250000),
    (r"\$250,001\s*-\s*\$500,000", 250001, 500000),
    (r"\$500,001\s*-\s*\$1,000,000", 500001, 1000000),
    (r"\$1,000,001\s*-\s*\$5,000,000", 1000001, 5000000),
    (r"Over\s*\$5,000,000", 5000001, 50000000),
]

# Asset type codes
ASSET_TYPE_CODES = {
    "ST": "Stocks (including ADRs)",
    "OP": "Stock Options",
    "MF": "Mutual Funds",
    "OI": "Other Investment",
    "BN": "Bonds",
    "GS": "Government Securities",
    "CS": "Corporate Securities",
}


# def extract_ticker_from_text(text: str) -> Optional[str]:
#     """Extract stock ticker from text like 'Company Name (TICKER) [ST]'."""
#     match = re.search(r"\(([A-Z]{1,5})\)", text)
#     return match.group(1) if match else None

def extract_ticker_from_text(text: str) -> Optional[str]:
    """
    Extract stock ticker from various text formats.

    Handles formats like:
    - "Apple Inc. (AAPL)"
    - "AAPL - Apple Inc."
    - "Microsoft Corporation - MSFT"
    - "TSLA"
    """
    if not text or not isinstance(text, str):
        return None

    text = text.strip()

    # Pattern 1: Ticker in parentheses (most common)
    match = re.search(r"\(([A-Z]{1,5})\)", text)
    if match:
        return match.group(1)

    # Pattern 2: Ticker after dash or hyphen
    match = re.search(r"[-–]\s*([A-Z]{1,5})(?:\s|$)", text)
    if match:
        return match.group(1)

    # Pattern 3: Ticker before dash
    match = re.search(r"^([A-Z]{1,5})\s*[-–]", text)
    if match:
        return match.group(1)

    # Pattern 4: Just a ticker (2-5 uppercase letters) - be careful
    match = re.search(r"\b([A-Z]{2,5})\b", text)
    if match:
        ticker = match.group(1)
        # Exclude common false positives
        excluded = {
            "INC", "LLC", "LTD", "CORP", "CO", "THE", "AND", "OR",
            "ETF", "FUND", "LP", "NA", "US", "USA", "NEW", "OLD",
            "PLC", "ADR", "ADS", "COMMON", "STOCK", "CLASS",
        }
        if ticker not in excluded:
            return ticker

    return None


def sanitize_string(value: Any) -> Optional[str]:
    """Remove null characters and other problematic unicode from strings."""
    if value is None:
        return None
    s = str(value)
    s = s.replace("\x00", "").replace("\u0000", "")
    s = "".join(
        c for c in s if c == "\n" or c == "\t" or (ord(c) >= 32 and ord(c) != 127)
    )
    return s.strip() if s.strip() else ""


def parse_value_range(text: str) -> Dict[str, Optional[float]]:
    """
    Parse value range from text like '$1,001 - $15,000'.

    Handles cases where PDF parsing splits the range across lines with
    intervening text, e.g., "$15,001 -\nCommon Stock (PLTR) [ST] $50,000"
    """
    # First try exact pattern matching (most reliable)
    for pattern, low, high in VALUE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return {"value_low": float(low), "value_high": float(high)}

    # If exact match fails, try extracting all dollar amounts and matching pairs
    # This handles PDF parsing issues where text appears between amount values
    dollar_amounts = re.findall(r'\$[\d,]+', text)
    if len(dollar_amounts) >= 2:
        # Parse the dollar amounts to numeric values
        def parse_dollar(s: str) -> int:
            return int(s.replace('$', '').replace(',', ''))

        amounts = [parse_dollar(d) for d in dollar_amounts]

        # Known disclosure ranges (low, high)
        known_ranges = [
            (1001, 15000),
            (15001, 50000),
            (50001, 100000),
            (100001, 250000),
            (250001, 500000),
            (500001, 1000000),
            (1000001, 5000000),
        ]

        # Try to find a matching pair (check first two amounts found)
        low_val, high_val = amounts[0], amounts[1]
        for range_low, range_high in known_ranges:
            # Check if amounts match a known range (with some tolerance for OCR errors)
            if (abs(low_val - range_low) <= 10 and abs(high_val - range_high) <= 10):
                return {"value_low": float(range_low), "value_high": float(range_high)}
            # Also check if they found the range boundaries in any order
            if low_val == range_low or high_val == range_high:
                if low_val <= high_val:
                    return {"value_low": float(range_low), "value_high": float(range_high)}

    # Check for "Over $5,000,000" pattern
    if re.search(r"over\s*\$5,000,000", text, re.IGNORECASE):
        return {"value_low": 5000001.0, "value_high": 50000000.0}

    return {"value_low": None, "value_high": None}


def parse_asset_type(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse asset type code from text like '[ST]' or '[MF]'."""
    match = re.search(r"\[([A-Z]{2})\]", text)
    if match:
        code = match.group(1)
        return code, ASSET_TYPE_CODES.get(code, code)
    return None, None
