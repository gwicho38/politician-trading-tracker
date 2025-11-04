"""
Amount range parser transformer.
"""

from typing import Tuple, Optional
import re
import logging

logger = logging.getLogger(__name__)


class AmountParser:
    """
    Parses amount ranges from disclosure text.

    Handles various formats:
    - "$1,001 - $15,000"
    - "$50,000+"
    - "$25,000"
    - "Over $1,000,000"
    """

    # Standard disclosure ranges (common in House/Senate disclosures)
    STANDARD_RANGES = {
        "$1,001 - $15,000": (1001, 15000),
        "$15,001 - $50,000": (15001, 50000),
        "$50,001 - $100,000": (50001, 100000),
        "$100,001 - $250,000": (100001, 250000),
        "$250,001 - $500,000": (250001, 500000),
        "$500,001 - $1,000,000": (500001, 1000000),
        "$1,000,001 - $5,000,000": (1000001, 5000000),
        "$5,000,001 - $25,000,000": (5000001, 25000000),
        "$25,000,001 - $50,000,000": (25000001, 50000000),
        "Over $50,000,000": (50000001, None),
    }

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse(
        self,
        amount_text: Optional[str]
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Parse amount from text.

        Args:
            amount_text: Text containing amount or range

        Returns:
            Tuple of (min, max, exact) where exact is used for single values
        """
        if not amount_text:
            return None, None, None

        # Clean the text
        amount_text = str(amount_text).strip()

        # Check for standard ranges (exact match)
        if amount_text in self.STANDARD_RANGES:
            min_val, max_val = self.STANDARD_RANGES[amount_text]
            self.logger.debug(f"Matched standard range: {amount_text} -> ({min_val}, {max_val})")
            return min_val, max_val, None

        # Try to parse as range: "$X - $Y" or "$X-$Y"
        range_match = re.search(
            r'\$\s*([\d,]+(?:\.\d{2})?)\s*[-–]\s*\$\s*([\d,]+(?:\.\d{2})?)',
            amount_text
        )
        if range_match:
            try:
                min_val = self._parse_number(range_match.group(1))
                max_val = self._parse_number(range_match.group(2))
                self.logger.debug(f"Parsed range: {amount_text} -> ({min_val}, {max_val})")
                return min_val, max_val, None
            except ValueError as e:
                self.logger.warning(f"Failed to parse range numbers: {e}")

        # Try "Over $X" or "$X+"
        over_match = re.search(
            r'(?:over|above|\>)\s*\$\s*([\d,]+(?:\.\d{2})?)',
            amount_text,
            re.IGNORECASE
        )
        if over_match:
            try:
                min_val = self._parse_number(over_match.group(1))
                self.logger.debug(f"Parsed 'over': {amount_text} -> ({min_val}, None)")
                return min_val, None, None
            except ValueError as e:
                self.logger.warning(f"Failed to parse 'over' number: {e}")

        # Try "Under $X" or "$X or less"
        under_match = re.search(
            r'(?:under|below|less than|\<)\s*\$\s*([\d,]+(?:\.\d{2})?)',
            amount_text,
            re.IGNORECASE
        )
        if under_match:
            try:
                max_val = self._parse_number(under_match.group(1))
                self.logger.debug(f"Parsed 'under': {amount_text} -> (None, {max_val})")
                return None, max_val, None
            except ValueError as e:
                self.logger.warning(f"Failed to parse 'under' number: {e}")

        # Try single amount: "$X"
        single_match = re.search(r'\$\s*([\d,]+(?:\.\d{2})?)', amount_text)
        if single_match:
            try:
                exact_val = self._parse_number(single_match.group(1))
                self.logger.debug(f"Parsed exact: {amount_text} -> {exact_val}")
                return None, None, exact_val
            except ValueError as e:
                self.logger.warning(f"Failed to parse single number: {e}")

        # Could not parse
        self.logger.warning(f"Could not parse amount from: {amount_text}")
        return None, None, None

    def _parse_number(self, number_str: str) -> float:
        """
        Parse a number string with possible commas.

        Args:
            number_str: String like "1,234,567.89"

        Returns:
            Parsed float value
        """
        # Remove commas
        number_str = number_str.replace(',', '')

        # Convert to float
        return float(number_str)
