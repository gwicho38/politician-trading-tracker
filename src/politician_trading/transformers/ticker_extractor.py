"""
Ticker extraction transformer.
"""

from typing import Optional
import logging

# Import existing ticker utilities
from ..utils.ticker_utils import extract_ticker_from_asset_name, validate_ticker

logger = logging.getLogger(__name__)


class TickerExtractor:
    """
    Extracts stock ticker symbols from asset names.

    Wraps the existing ticker extraction utilities into a transformer class.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def extract(self, asset_name: str) -> Optional[str]:
        """
        Extract ticker from asset name.

        Args:
            asset_name: Asset/security name

        Returns:
            Ticker symbol or None if not found
        """
        if not asset_name:
            return None

        ticker = extract_ticker_from_asset_name(asset_name)

        if ticker:
            # Validate extracted ticker
            if validate_ticker(ticker):
                self.logger.debug(f"Extracted ticker '{ticker}' from '{asset_name}'")
                return ticker
            else:
                self.logger.warning(f"Invalid ticker format: '{ticker}' from '{asset_name}'")

        return None

    def validate(self, ticker: str) -> bool:
        """
        Validate ticker format.

        Args:
            ticker: Ticker to validate

        Returns:
            True if valid ticker format
        """
        return validate_ticker(ticker)
