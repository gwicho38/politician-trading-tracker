"""
SectorCache - Maps stock tickers to sector ETFs for sector_performance feature.

Uses in-memory cache with JSON file persistence.
Pre-seeded with common congressional trading tickers to reduce cold-start.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

CACHE_FILE = "/tmp/sector_cache.json"

# SPDR Sector ETFs
SECTOR_ETFS = [
    "XLK",  # Technology
    "XLF",  # Financials
    "XLV",  # Health Care
    "XLE",  # Energy
    "XLI",  # Industrials
    "XLC",  # Communication Services
    "XLY",  # Consumer Discretionary
    "XLP",  # Consumer Staples
    "XLRE",  # Real Estate
    "XLU",  # Utilities
    "XLB",  # Materials
]

# Pre-seeded mapping: ticker -> sector ETF
# Common tickers in congressional trading disclosures
_PRESEED: Dict[str, str] = {
    # Technology
    "AAPL": "XLK", "MSFT": "XLK", "GOOGL": "XLK", "GOOG": "XLK",
    "NVDA": "XLK", "META": "XLC", "AMZN": "XLY", "TSLA": "XLY",
    "AMD": "XLK", "INTC": "XLK", "CRM": "XLK", "ORCL": "XLK",
    "ADBE": "XLK", "NOW": "XLK", "CSCO": "XLK", "AVGO": "XLK",
    "QCOM": "XLK", "TXN": "XLK", "AMAT": "XLK", "MU": "XLK",
    # Financials
    "JPM": "XLF", "BAC": "XLF", "GS": "XLF", "MS": "XLF",
    "WFC": "XLF", "C": "XLF", "BLK": "XLF", "SCHW": "XLF",
    "AXP": "XLF", "V": "XLK", "MA": "XLK",
    # Health Care
    "JNJ": "XLV", "UNH": "XLV", "PFE": "XLV", "ABBV": "XLV",
    "LLY": "XLV", "MRK": "XLV", "TMO": "XLV", "ABT": "XLV",
    "MRNA": "XLV", "ISRG": "XLV", "BMY": "XLV", "GILD": "XLV",
    # Energy
    "XOM": "XLE", "CVX": "XLE", "COP": "XLE", "SLB": "XLE",
    "EOG": "XLE", "OXY": "XLE",
    # Industrials
    "BA": "XLI", "RTX": "XLI", "HON": "XLI", "LMT": "XLI",
    "CAT": "XLI", "GE": "XLI", "DE": "XLI", "NOC": "XLI",
    "GD": "XLI", "UPS": "XLI",
    # Communication
    "DIS": "XLC", "NFLX": "XLC", "CMCSA": "XLC", "T": "XLC",
    "VZ": "XLC", "TMUS": "XLC",
    # Consumer
    "WMT": "XLP", "PG": "XLP", "KO": "XLP", "PEP": "XLP",
    "COST": "XLP", "HD": "XLY", "NKE": "XLY", "SBUX": "XLY",
    "MCD": "XLY", "LOW": "XLY", "TGT": "XLY",
    # Real Estate
    "AMT": "XLRE", "PLD": "XLRE", "CCI": "XLRE",
    # Utilities
    "NEE": "XLU", "DUK": "XLU", "SO": "XLU",
    # Materials
    "LIN": "XLB", "APD": "XLB", "FCX": "XLB",
}


class SectorCache:
    """In-memory ticker-to-sector mapping with JSON file persistence."""

    def __init__(self):
        self._cache: Dict[str, str] = _PRESEED.copy()
        self._load_from_file()

    def _load_from_file(self):
        """Load cached mappings from JSON file."""
        try:
            path = Path(CACHE_FILE)
            if path.exists():
                with open(path) as f:
                    stored = json.load(f)
                self._cache.update(stored)
        except Exception as e:
            logger.debug(f"Could not load sector cache: {e}")

    def _save_to_file(self):
        """Persist cache to JSON file."""
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump(self._cache, f)
        except Exception as e:
            logger.debug(f"Could not save sector cache: {e}")

    def get_sector(self, ticker: str) -> Optional[str]:
        """Get sector ETF for a ticker. Returns None if unknown."""
        return self._cache.get(ticker.upper())

    def batch_resolve(self, tickers: list[str]) -> Dict[str, str]:
        """
        Resolve sector ETFs for a list of tickers.
        Uses yfinance for any cache misses.
        Returns mapping of ticker -> sector ETF.
        """
        result = {}
        misses = []

        for t in tickers:
            t_upper = t.upper()
            if t_upper in self._cache:
                result[t_upper] = self._cache[t_upper]
            else:
                misses.append(t_upper)

        if misses:
            self._resolve_via_yfinance(misses)
            for t in misses:
                if t in self._cache:
                    result[t] = self._cache[t]

        return result

    def _resolve_via_yfinance(self, tickers: list[str]):
        """Resolve unknown tickers via yfinance sector info."""
        try:
            import yfinance as yf
        except ImportError:
            return

        sector_to_etf = {
            "Technology": "XLK",
            "Financial Services": "XLF",
            "Healthcare": "XLV",
            "Energy": "XLE",
            "Industrials": "XLI",
            "Communication Services": "XLC",
            "Consumer Cyclical": "XLY",
            "Consumer Defensive": "XLP",
            "Real Estate": "XLRE",
            "Utilities": "XLU",
            "Basic Materials": "XLB",
        }

        resolved_any = False
        for ticker in tickers[:20]:  # Limit to avoid rate limits
            try:
                info = yf.Ticker(ticker).info
                sector = info.get("sector", "")
                etf = sector_to_etf.get(sector)
                if etf:
                    self._cache[ticker] = etf
                    resolved_any = True
            except Exception:
                pass

        if resolved_any:
            self._save_to_file()


# Module-level singleton
_sector_cache: Optional[SectorCache] = None


def get_sector_cache() -> SectorCache:
    """Get or create the module-level SectorCache singleton."""
    global _sector_cache
    if _sector_cache is None:
        _sector_cache = SectorCache()
    return _sector_cache
