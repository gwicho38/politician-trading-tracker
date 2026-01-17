import re
from typing import Optional

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