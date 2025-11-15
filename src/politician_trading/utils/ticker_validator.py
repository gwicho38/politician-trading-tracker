"""
Ticker symbol validation against NASDAQ/NYSE market data

This module provides validation of ticker symbols against known US exchanges
to ensure data quality and catch parsing errors.
"""

import logging
import re
from typing import Optional, Dict, Set, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TickerValidator:
    """
    Validates ticker symbols against known US stock exchanges

    Uses cached lists of valid ticker symbols from NASDAQ and NYSE
    to validate parsed tickers and identify potential errors.
    """

    def __init__(self):
        # Common US stock ticker patterns
        self.ticker_pattern = re.compile(r"^[A-Z]{1,5}$")  # 1-5 uppercase letters

        # Cache of known valid tickers
        self._valid_tickers: Optional[Set[str]] = None
        self._last_refresh: Optional[datetime] = None
        self._refresh_interval = timedelta(hours=24)

        # Load initial ticker data
        self._load_common_tickers()

    def _load_common_tickers(self):
        """
        Load common ticker symbols from known lists

        In production, this would fetch from:
        - NASDAQ API
        - NYSE API
        - SEC EDGAR API
        - Financial data providers

        For now, includes most common tickers to catch obvious errors
        """
        # Top US stocks by market cap (partial list for validation)
        common_tickers = {
            # Technology
            "AAPL",
            "MSFT",
            "GOOGL",
            "GOOG",
            "AMZN",
            "META",
            "NVDA",
            "TSLA",
            "ADBE",
            "NFLX",
            "CRM",
            "INTC",
            "AMD",
            "CSCO",
            "ORCL",
            "IBM",
            "QCOM",
            "TXN",
            "AVGO",
            "INTU",
            "NOW",
            "PANW",
            "SNOW",
            "CRWD",
            # Finance
            "JPM",
            "BAC",
            "WFC",
            "C",
            "GS",
            "MS",
            "BLK",
            "SCHW",
            "AXP",
            "BK",
            "USB",
            "PNC",
            "TFC",
            "COF",
            "FRC",
            "STT",
            "BX",
            "KKR",
            # Healthcare
            "JNJ",
            "UNH",
            "PFE",
            "ABBV",
            "TMO",
            "MRK",
            "ABT",
            "DHR",
            "LLY",
            "BMY",
            "AMGN",
            "GILD",
            "CVS",
            "CI",
            "ISRG",
            "MDT",
            "SYK",
            "VRTX",
            # Consumer
            "AMZN",
            "TSLA",
            "HD",
            "NKE",
            "MCD",
            "SBUX",
            "TGT",
            "LOW",
            "TJX",
            "DIS",
            "CMCSA",
            "VZ",
            "T",
            "NFLX",
            "PYPL",
            "MA",
            "V",
            "COST",
            # Energy
            "XOM",
            "CVX",
            "COP",
            "SLB",
            "EOG",
            "MPC",
            "PSX",
            "VLO",
            "OXY",
            "HAL",
            "PXD",
            "KMI",
            "WMB",
            "LNG",
            "FANG",
            "DVN",
            "HES",
            "MRO",
            # Industrials
            "BA",
            "CAT",
            "GE",
            "HON",
            "UNP",
            "UPS",
            "RTX",
            "LMT",
            "DE",
            "MMM",
            "FDX",
            "NSC",
            "CSX",
            "EMR",
            "ETN",
            "ITW",
            "PH",
            "CMI",
            # Materials
            "LIN",
            "APD",
            "ECL",
            "SHW",
            "FCX",
            "NEM",
            "DD",
            "DOW",
            "PPG",
            "NUE",
            "VMC",
            "MLM",
            "ALB",
            "CF",
            "MOS",
            "IFF",
            "CE",
            "FMC",
            # Utilities
            "NEE",
            "DUK",
            "SO",
            "D",
            "AEP",
            "EXC",
            "SRE",
            "PEG",
            "XEL",
            "ED",
            "ES",
            "AWK",
            "PPL",
            "ETR",
            "FE",
            "EIX",
            "DTE",
            "AEE",
            # Real Estate / REITs
            "AMT",
            "PLD",
            "CCI",
            "EQIX",
            "PSA",
            "SPG",
            "WELL",
            "DLR",
            "O",
            "AVB",
            "EQR",
            "SBAC",
            "VTR",
            "ARE",
            "MAA",
            "UDR",
            "ESS",
            "EXR",
            # Consumer Staples
            "WMT",
            "PG",
            "KO",
            "PEP",
            "PM",
            "COST",
            "MO",
            "CL",
            "MDLZ",
            "EL",
            "KMB",
            "GIS",
            "KHC",
            "SYY",
            "HSY",
            "K",
            "TSN",
            "CAG",
            # ETFs (commonly held)
            "SPY",
            "QQQ",
            "IWM",
            "DIA",
            "VTI",
            "VOO",
            "IVV",
            "VEA",
            "VWO",
            "AGG",
            "BND",
            "LQD",
            "HYG",
            "TLT",
            "GLD",
            "SLV",
            "USO",
            "XLE",
            # Cryptocurren cy-related
            "COIN",
            "MSTR",
            "RIOT",
            "MARA",
            "SI",
            "HUT",
            "BTBT",
            "CAN",
            # Other notable companies
            "BRK.A",
            "BRK.B",
            "BRKB",
            "BRKA",  # Berkshire Hathaway
        }

        self._valid_tickers = common_tickers
        self._last_refresh = datetime.now()
        logger.info(f"Loaded {len(self._valid_tickers)} common ticker symbols")

    def validate_ticker(self, ticker: Optional[str]) -> Tuple[bool, str, float]:
        """
        Validate a ticker symbol

        Args:
            ticker: Ticker symbol to validate

        Returns:
            Tuple of (is_valid, reason, confidence)
            - is_valid: True if ticker passes validation
            - reason: Description of validation result
            - confidence: Confidence score (0.0-1.0)
        """
        if not ticker:
            return False, "No ticker provided", 0.0

        # Clean ticker
        ticker_clean = ticker.upper().strip()

        # Check pattern
        if not self.ticker_pattern.match(ticker_clean):
            return False, f"Invalid ticker format: {ticker}", 0.0

        # Check against known tickers
        if self._valid_tickers and ticker_clean in self._valid_tickers:
            return True, "Ticker found in known symbols", 1.0

        # Not in our list, but could still be valid (our list isn't exhaustive)
        # Perform heuristic checks

        # Single letter tickers are rare but exist (e.g., F for Ford, X for US Steel)
        if len(ticker_clean) == 1:
            return True, "Single-letter ticker (uncommon but valid)", 0.6

        # 2-3 letters is most common
        if 2 <= len(ticker_clean) <= 3:
            return True, "Standard ticker length (2-3 letters)", 0.7

        # 4-5 letters is common for NASDAQ
        if 4 <= len(ticker_clean) <= 5:
            return True, "Extended ticker length (4-5 letters)", 0.7

        return False, "Ticker length out of range", 0.3

    def bulk_validate(self, tickers: list[str]) -> Dict[str, Tuple[bool, str, float]]:
        """
        Validate multiple ticker symbols

        Args:
            tickers: List of ticker symbols

        Returns:
            Dict mapping ticker to validation result tuple
        """
        results = {}
        for ticker in tickers:
            results[ticker] = self.validate_ticker(ticker)
        return results

    def get_invalid_tickers(self, tickers: list[str]) -> list[str]:
        """
        Filter list to only invalid tickers

        Args:
            tickers: List of ticker symbols

        Returns:
            List of ticker symbols that failed validation
        """
        invalid = []
        for ticker in tickers:
            is_valid, _, _ = self.validate_ticker(ticker)
            if not is_valid:
                invalid.append(ticker)
        return invalid

    def suggest_corrections(self, ticker: str) -> list[str]:
        """
        Suggest corrections for an invalid ticker

        Args:
            ticker: Potentially invalid ticker symbol

        Returns:
            List of suggested corrections
        """
        if not self._valid_tickers:
            return []

        ticker_clean = ticker.upper().strip()
        suggestions = []

        # Look for similar tickers
        for valid_ticker in self._valid_tickers:
            # Exact prefix match
            if valid_ticker.startswith(ticker_clean):
                suggestions.append(valid_ticker)

            # Single character difference
            if len(valid_ticker) == len(ticker_clean):
                diff_count = sum(a != b for a, b in zip(valid_ticker, ticker_clean))
                if diff_count == 1:
                    suggestions.append(valid_ticker)

        return suggestions[:5]  # Return top 5 suggestions

    def update_ticker_cache(self, additional_tickers: Set[str]):
        """
        Add additional tickers to the validation cache

        Args:
            additional_tickers: Set of ticker symbols to add
        """
        if not self._valid_tickers:
            self._valid_tickers = set()

        before_count = len(self._valid_tickers)
        self._valid_tickers.update(ticker.upper().strip() for ticker in additional_tickers)
        after_count = len(self._valid_tickers)

        logger.info(f"Updated ticker cache: {before_count} -> {after_count} symbols")


# Global instance
_validator = TickerValidator()


def validate_ticker(ticker: Optional[str]) -> Tuple[bool, str, float]:
    """
    Validate a ticker symbol using the global validator

    Args:
        ticker: Ticker symbol to validate

    Returns:
        Tuple of (is_valid, reason, confidence)
    """
    return _validator.validate_ticker(ticker)


def bulk_validate_tickers(tickers: list[str]) -> Dict[str, Tuple[bool, str, float]]:
    """
    Validate multiple tickers using the global validator

    Args:
        tickers: List of ticker symbols

    Returns:
        Dict mapping ticker to validation result
    """
    return _validator.bulk_validate(tickers)


def get_ticker_suggestions(ticker: str) -> list[str]:
    """
    Get suggested corrections for an invalid ticker

    Args:
        ticker: Potentially invalid ticker symbol

    Returns:
        List of suggested corrections
    """
    return _validator.suggest_corrections(ticker)
