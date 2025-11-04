"""
US House of Representatives disclosure source.

Fetches financial disclosures from the House Clerk's office.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging
from bs4 import BeautifulSoup

from .base_source import BaseSource, SourceConfig

logger = logging.getLogger(__name__)


class USHouseSource(BaseSource):
    """
    US House of Representatives financial disclosures.

    Source: https://disclosures-clerk.house.gov/FinancialDisclosure
    """

    def _create_default_config(self) -> SourceConfig:
        """Create default configuration"""
        return SourceConfig(
            name="US House of Representatives",
            source_type="us_house",
            base_url="https://disclosures-clerk.house.gov/FinancialDisclosure",
            request_delay=2.0,  # Be respectful with government servers
            max_retries=3,
            timeout=60,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; PoliticianTradingBot/1.0)'
            }
        )

    async def _fetch_data(self, lookback_days: int, **kwargs) -> Any:
        """
        Fetch disclosures from House website.

        The House uses an ASPX form with ViewState - we need to handle that.
        """
        # This is a simplified version - real implementation would handle ASPX ViewState
        url = f"{self.config.base_url}"

        try:
            # Step 1: Get the main page to get ViewState
            main_page = await self._make_request(url)

            # Step 2: Parse form data (simplified - real version would extract ViewState)
            # For now, return placeholder
            # TODO: Implement full ASPX form handling

            self.logger.warning(
                "US House source is using placeholder data. "
                "Full ASPX implementation needed."
            )

            return {
                'status': 'placeholder',
                'message': 'Real implementation coming soon'
            }

        except Exception as e:
            self.logger.error(f"Error fetching House data: {e}", exc_info=True)
            return {}

    async def _parse_response(self, response_data: Any) -> List[Dict[str, Any]]:
        """
        Parse House disclosure response.

        Args:
            response_data: Response from House website

        Returns:
            List of disclosure dictionaries
        """
        disclosures = []

        # TODO: Implement real parsing
        # For now, return empty list
        self.logger.info("Parsing House disclosures (placeholder)")

        return disclosures

    def _parse_disclosure_row(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a single disclosure row into standard format.

        Args:
            row_data: Raw row data from House website

        Returns:
            Standardized disclosure dictionary
        """
        return {
            'politician_name': row_data.get('name', ''),
            'transaction_date': self._parse_date(row_data.get('transaction_date')),
            'disclosure_date': self._parse_date(row_data.get('disclosure_date')),
            'asset_name': row_data.get('asset', ''),
            'asset_ticker': row_data.get('ticker'),
            'transaction_type': self._normalize_transaction_type(row_data.get('type', '')),
            'amount': row_data.get('amount', ''),
            'source_url': row_data.get('url', ''),
            'document_id': row_data.get('doc_id'),
        }

    def _parse_date(self, date_str: str) -> str:
        """Parse date string to ISO format"""
        if not date_str:
            return ''

        try:
            # House typically uses MM/DD/YYYY
            dt = datetime.strptime(date_str, '%m/%d/%Y')
            return dt.isoformat()
        except:
            return date_str

    def _normalize_transaction_type(self, trans_type: str) -> str:
        """Normalize transaction type"""
        trans_type = trans_type.lower().strip()

        type_map = {
            'p': 'purchase',
            'purchase': 'purchase',
            's': 'sale',
            'sale': 'sale',
            'e': 'exchange',
            'exchange': 'exchange',
        }

        return type_map.get(trans_type, trans_type)
