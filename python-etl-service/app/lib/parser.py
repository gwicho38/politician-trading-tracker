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

# Maximum valid trade amount - the largest disclosure range is "Over $5,000,000"
# We use $50M as a reasonable upper bound for the high end estimate
# Any amount above this is clearly a parsing error (e.g., from malformed PDF text)
MAX_VALID_TRADE_AMOUNT = 50_000_000  # $50 million

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

    Also handles:
    - Decimal dollar amounts: '$.00', '$16,750.00'
    - Schedule C beginning/ending value pairs: '$.00 $16,750.00'
    - Single exact amounts: '$20,000.00'
    - PDF parsing splits: "$15,001 -\nCommon Stock (PLTR) [ST] $50,000"
    """
    # First try exact pattern matching for standard Congressional ranges
    for pattern, low, high in VALUE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return {"value_low": float(low), "value_high": float(high)}

    # Check for "Over $5,000,000" pattern
    if re.search(r"over\s*\$5,000,000", text, re.IGNORECASE):
        return {"value_low": 5000001.0, "value_high": 50000000.0}

    # Extract all dollar amounts (including decimals like $.00 and $16,750.00)
    dollar_amounts = re.findall(r'\$[\d,]*\.?\d+', text)
    if not dollar_amounts:
        return {"value_low": None, "value_high": None}

    def parse_dollar(s: str) -> float:
        return float(s.replace('$', '').replace(',', ''))

    amounts = [parse_dollar(d) for d in dollar_amounts]

    if len(amounts) >= 2:
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

        # Try to match a known Congressional range pair
        low_val, high_val = amounts[0], amounts[1]
        for range_low, range_high in known_ranges:
            if (abs(low_val - range_low) <= 10 and abs(high_val - range_high) <= 10):
                return {"value_low": float(range_low), "value_high": float(range_high)}
            if low_val == range_low or high_val == range_high:
                if low_val <= high_val:
                    return {"value_low": float(range_low), "value_high": float(range_high)}

        # No known range matched — treat as beginning/ending value pair
        # (common in Schedule C filings: "$.00 $16,750.00")
        # Use the maximum non-zero amount as the value
        max_amount = max(amounts)
        if max_amount > 0:
            return {"value_low": max_amount, "value_high": max_amount}

    elif len(amounts) == 1:
        # Single dollar amount — use as exact value
        if amounts[0] > 0:
            return {"value_low": amounts[0], "value_high": amounts[0]}

    return {"value_low": None, "value_high": None}


def parse_asset_type(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse asset type code from text like '[ST]' or '[MF]'."""
    match = re.search(r"\[([A-Z]{2})\]", text)
    if match:
        code = match.group(1)
        return code, ASSET_TYPE_CODES.get(code, code)
    return None, None


def clean_asset_name(name: Optional[str]) -> Optional[str]:
    """Clean asset name by removing trailing metadata and normalizing whitespace.

    PDF table cells often contain multiple lines with metadata appended:
    'Apple Inc (AAPL) [ST]\\nF S: New\\nS O: Brokerage Account'

    We want just: 'Apple Inc (AAPL) [ST]'

    Args:
        name: Raw asset name from PDF

    Returns:
        Cleaned asset name, truncated to 200 chars max
    """
    if not name:
        return None

    # Split by newlines and process line by line
    lines = name.split("\n")
    clean_lines = []

    for line in lines:
        line = line.strip()
        # Stop if we hit metadata lines
        if re.match(r"^(F\s*S|S\s*O|Owner|Filer|Status|Type)\s*:", line, re.IGNORECASE):
            break
        # Skip empty lines
        if not line:
            continue
        clean_lines.append(line)

    result = " ".join(clean_lines).strip()

    # Normalize whitespace (replace multiple spaces/newlines with single space)
    result = re.sub(r'\s+', ' ', result).strip()

    # Remove transaction data pattern that's mixed into asset name
    # Pattern: "S 02/25/2025 02/25/2025 $1,001 - $15,000" or partial
    result = re.sub(
        r"\s+[PS]\s+\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}/\d{1,2}/\d{4}\s+\$[\d,]+\s*-\s*(\$[\d,]+)?",
        "",
        result,
    )
    # Also handle "(partial)" notation
    result = re.sub(
        r"\s+[PS]\s*\(partial\)\s+\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}/\d{1,2}/\d{4}\s+\$[\d,]+\s*-\s*(\$[\d,]+)?",
        "",
        result,
        flags=re.IGNORECASE,
    )

    # Remove trailing metadata that didn't have a newline
    result = re.sub(r"\s+(F\s*S|S\s*O)\s*:.*$", "", result, flags=re.IGNORECASE)

    # If still too long, try to extract just the first meaningful part
    if len(result) > 200:
        for marker in ["Company:", "Description:"]:
            if marker in result:
                result = result.split(marker)[0].strip()
                break

    # Truncate to 200 chars max (database limit)
    return result[:200] if result and len(result) > 200 else (result if result else None)


def is_header_row(row_text: str) -> bool:
    """Check if a row is a header row.

    PDF tables sometimes split headers across multiple rows, e.g.:
    Row 0: ['ID', 'Owner', 'Asset', 'Transaction', ...]
    Row 1: ['', '', '', 'Type', ...]  ← continuation of header

    We need to detect both full headers and these continuation rows.

    Args:
        row_text: Combined text from all cells in the row

    Returns:
        True if row appears to be a header row
    """
    text_lower = row_text.lower().strip()

    # Standard header keywords
    headers = [
        "asset", "owner", "value", "income", "description",
        "transaction", "notification"
    ]
    if any(header in text_lower for header in headers):
        return True

    # Exact match for standalone header continuation words
    # These appear in continuation rows with mostly empty cells
    standalone_headers = ["type", "date", "amount", "cap.", "gains"]
    words = [w.strip() for w in text_lower.split() if w.strip()]
    if words and all(w in standalone_headers or w.startswith("$") or w == ">" for w in words):
        return True

    return False


def validate_trade_amount(amount: Optional[float]) -> bool:
    """Validate that a trade amount is within reasonable bounds.

    Congressional financial disclosures have defined ranges with a maximum
    of "Over $5,000,000". We use $50M as a reasonable upper bound.
    Any amount above this is clearly a PDF parsing error.

    Args:
        amount: The trade amount to validate (can be None)

    Returns:
        True if the amount is valid (None or <= MAX_VALID_TRADE_AMOUNT)
        False if the amount is invalid (> MAX_VALID_TRADE_AMOUNT)
    """
    if amount is None:
        return True
    return amount <= MAX_VALID_TRADE_AMOUNT


def validate_and_sanitize_amounts(
    value_low: Optional[float], value_high: Optional[float]
) -> Tuple[Optional[float], Optional[float]]:
    """Validate and sanitize trade amount values.

    If either value exceeds the maximum valid trade amount, both are
    set to None to prevent corrupted data from entering the database.

    Args:
        value_low: Lower bound of amount range
        value_high: Upper bound of amount range

    Returns:
        Tuple of (sanitized_low, sanitized_high) - both None if invalid
    """
    if not validate_trade_amount(value_low) or not validate_trade_amount(value_high):
        # Log would be at warning level in the calling code
        return None, None
    return value_low, value_high


def normalize_name(name: str) -> str:
    """Normalize a politician name for comparison.

    Removes:
    - Honorifics (Hon., Representative, Senator, etc.)
    - Suffixes (Jr., Sr., III, etc.)
    - Extra whitespace
    - Punctuation

    Lowercases and standardizes the name.

    Args:
        name: Raw politician name

    Returns:
        Normalized lowercase name for comparison
    """
    if not name:
        return ""

    result = name

    # Remove common prefixes (case-insensitive)
    prefixes = [
        r"^hon\.?\s*",
        r"^honorable\s+",
        r"^representative\s+",
        r"^rep\.?\s*",
        r"^senator\s+",
        r"^sen\.?\s*",
        r"^dr\.?\s*",
        r"^mr\.?\s*",
        r"^mrs\.?\s*",
        r"^ms\.?\s*",
    ]
    for prefix in prefixes:
        result = re.sub(prefix, "", result, flags=re.IGNORECASE)

    # Remove common suffixes
    suffixes = [" Jr.", " Jr", " Sr.", " Sr", " III", " II", " IV", " M.D.", " Ph.D."]
    for suffix in suffixes:
        result = result.replace(suffix, "")

    # Remove punctuation and extra whitespace
    result = re.sub(r"[.,]", "", result)
    result = re.sub(r"\s+", " ", result)

    return result.lower().strip()
