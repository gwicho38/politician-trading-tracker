"""
QuiverQuant disclosure source.

Fetches aggregated congressional trading data from QuiverQuant.
This is a third-party aggregator that provides easier access to trading data.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from bs4 import BeautifulSoup
import re

from .base_source import BaseSource, SourceConfig
from ..storage import StorageManager

logger = logging.getLogger(__name__)


class QuiverQuantSource(BaseSource):
    """
    QuiverQuant congressional trading data.

    Source: https://www.quiverquant.com/congresstrading/
    Type: Third-party aggregator (free web scraping or paid API)
    """

    def __init__(self, config: Optional[SourceConfig] = None):
        """
        Initialize QuiverQuant source.

        Args:
            config: Optional source configuration
        """
        super().__init__(config)
        self.storage_manager: Optional[StorageManager] = None  # Set externally if needed

    def _create_default_config(self) -> SourceConfig:
        """Create default configuration"""
        return SourceConfig(
            name="QuiverQuant",
            source_type="quiverquant",
            base_url="https://www.quiverquant.com",
            request_delay=3.0,  # Be respectful with rate limiting
            max_retries=2,
            timeout=30,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )

    async def _fetch_data(self, lookback_days: int, **kwargs) -> Any:
        """
        Fetch congressional trading data from QuiverQuant.

        Note: QuiverQuant uses JavaScript for rendering, so this may need
        to be updated to use Selenium or similar if the page structure changes.

        Args:
            lookback_days: Not used (QuiverQuant shows recent trades)
            **kwargs: Additional parameters (api_key for paid access)

        Returns:
            HTML response or JSON if using API
        """
        # Check if API key provided (for paid access)
        api_key = kwargs.get('api_key')

        if api_key:
            return await self._fetch_via_api(api_key, lookback_days)
        else:
            return await self._fetch_via_web()

    async def _fetch_via_web(self) -> str:
        """Fetch via web scraping (free tier)"""
        url = f"{self.config.base_url}/congresstrading/"

        self.logger.info(f"Fetching QuiverQuant data via web scraping: {url}")

        try:
            response = await self._make_request(url, method="GET")

            if isinstance(response, str):
                self.logger.info("Received QuiverQuant HTML response")
                return response
            else:
                self.logger.warning("Unexpected response type from QuiverQuant")
                return ""

        except Exception as e:
            self.logger.error(f"Error fetching QuiverQuant web data: {e}", exc_info=True)
            return ""

    async def _fetch_via_api(self, api_key: str, lookback_days: int) -> Dict:
        """Fetch via paid API (if available)"""
        api_url = "https://api.quiverquant.com/beta/live/congresstrading"

        self.logger.info(f"Fetching QuiverQuant data via API")

        try:
            headers = {
                **self.config.headers,
                'Authorization': f'Bearer {api_key}'
            }

            response = await self._make_request(
                api_url,
                method="GET",
                headers=headers
            )

            # QuiverQuant API returns a list directly
            if isinstance(response, (dict, list)):
                record_count = len(response) if isinstance(response, list) else len(response.get('trades', response.get('data', [])))
                self.logger.info(f"Received QuiverQuant API response with {record_count} trades")

                # Save raw API response to storage if storage manager available
                if self.storage_manager:
                    try:
                        # Wrap list in dict for consistent storage format
                        response_to_store = {'trades': response} if isinstance(response, list) else response

                        storage_path, file_id = await self.storage_manager.save_api_response(
                            response_data=response_to_store,
                            source='quiverquant',
                            endpoint='/congresstrading',
                            metadata={'url': api_url, 'lookback_days': lookback_days}
                        )
                        self.logger.info(f"Saved API response to storage: {storage_path} (file_id: {file_id})")
                    except Exception as storage_error:
                        self.logger.error(f"Failed to save API response to storage: {storage_error}", exc_info=True)
                        # Continue processing even if storage fails

                return response
            else:
                self.logger.warning(f"Unexpected API response format: {type(response)}")
                return []

        except Exception as e:
            self.logger.error(f"Error fetching QuiverQuant API data: {e}", exc_info=True)
            return {}

    async def _parse_response(self, response_data: Any) -> List[Dict[str, Any]]:
        """
        Parse QuiverQuant response.

        Args:
            response_data: HTML string, JSON dict, or JSON list

        Returns:
            List of disclosure dictionaries
        """
        if isinstance(response_data, list):
            # API returns list directly
            return self._parse_api_response(response_data)
        elif isinstance(response_data, dict):
            # API returns dict (possibly with 'trades' key)
            return self._parse_api_response(response_data)
        elif isinstance(response_data, str):
            # Web scraping returns HTML
            return self._parse_web_response(response_data)
        else:
            self.logger.warning(f"Unknown response format: {type(response_data)}")
            return []

    def _parse_api_response(self, data) -> List[Dict[str, Any]]:
        """Parse JSON API response (list or dict)"""
        disclosures = []

        try:
            # Handle both list and dict responses
            if isinstance(data, list):
                trades = data
            elif isinstance(data, dict):
                trades = data.get('trades', data.get('data', []))
            else:
                self.logger.warning(f"Unexpected data type: {type(data)}")
                return []

            for trade in trades:
                # Map QuiverQuant API fields to our schema
                disclosure = {
                    'politician_name': trade.get('Representative', ''),
                    'transaction_date': trade.get('TransactionDate', ''),
                    'disclosure_date': trade.get('ReportDate', ''),
                    'asset_name': trade.get('Description') or trade.get('AssetDescription', ''),
                    'asset_ticker': trade.get('Ticker', ''),
                    'transaction_type': self._normalize_transaction_type(trade.get('Transaction', '')),
                    'amount': trade.get('Range') or trade.get('Amount', ''),
                    'source_url': 'https://www.quiverquant.com/congresstrading/',
                    'document_id': trade.get('FilingID'),
                    'extraction_method': 'quiverquant_api',
                    # Additional fields from QuiverQuant
                    'chamber': trade.get('House', ''),  # Senate or House
                    'party': trade.get('Party', ''),
                    'bio_guide_id': trade.get('BioGuideID', ''),
                }

                if disclosure['politician_name']:
                    disclosures.append(disclosure)

            self.logger.info(f"Parsed {len(disclosures)} trades from QuiverQuant API")

        except Exception as e:
            self.logger.error(f"Error parsing QuiverQuant API response: {e}", exc_info=True)

        return disclosures

    def _parse_web_response(self, html: str) -> List[Dict[str, Any]]:
        """Parse HTML web response"""
        disclosures = []

        if not html:
            return disclosures

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Find trading table (structure may vary)
            trade_rows = soup.select('table tr, tbody tr')

            self.logger.info(f"Found {len(trade_rows)} potential trade rows")

            for row in trade_rows[1:]:  # Skip header row
                try:
                    disclosure = self._parse_trade_row(row)
                    if disclosure:
                        disclosures.append(disclosure)
                except Exception as e:
                    self.logger.debug(f"Failed to parse row: {e}")
                    continue

            self.logger.info(f"Successfully parsed {len(disclosures)} trades from QuiverQuant web")

        except Exception as e:
            self.logger.error(f"Error parsing QuiverQuant HTML: {e}", exc_info=True)

        return disclosures

    def _parse_trade_row(self, row) -> Optional[Dict[str, Any]]:
        """Parse a single trade row from HTML table"""
        cells = row.find_all('td')

        if len(cells) < 4:  # Need at least 4 columns
            return None

        try:
            cell_texts = [cell.get_text(strip=True) for cell in cells]

            politician_name = ""
            transaction_date = ""
            ticker = ""
            asset_name = ""
            transaction_type = ""
            amount = ""

            for i, text in enumerate(cell_texts):
                if not text:
                    continue

                # Politician name
                if not politician_name and len(text) > 3 and ' ' in text and not self._looks_like_date(text):
                    politician_name = text

                # Date
                elif self._looks_like_date(text):
                    transaction_date = text

                # Ticker
                elif text.isupper() and 1 <= len(text) <= 5 and text.isalpha():
                    ticker = text

                # Asset name
                elif any(word in text for word in ['Inc', 'Corp', 'Ltd', 'LLC', 'Corporation']):
                    asset_name = text

                # Transaction type
                elif any(word in text.lower() for word in ['purchase', 'sale', 'buy', 'sell']):
                    if '$' in text:
                        parts = text.split('$', 1)
                        transaction_type = parts[0].strip()
                        amount = '$' + parts[1] if len(parts) > 1 else ''
                    else:
                        transaction_type = text

                # Amount
                elif '$' in text or (',' in text and any(c.isdigit() for c in text)):
                    amount = text

                # Fallback asset name
                elif not asset_name and len(text) > 6 and not text.isupper():
                    asset_name = text

            # Create disclosure if we have minimum required fields
            if politician_name and (transaction_date or ticker):
                return {
                    'politician_name': politician_name,
                    'transaction_date': self._parse_date(transaction_date),
                    'disclosure_date': self._parse_date(transaction_date),
                    'asset_name': asset_name or ticker or 'Unknown',
                    'asset_ticker': ticker,
                    'transaction_type': self._normalize_transaction_type(transaction_type),
                    'amount': amount,
                    'source_url': 'https://www.quiverquant.com/congresstrading/',
                    'extraction_method': 'quiverquant_web'
                }

        except Exception as e:
            self.logger.debug(f"Error parsing trade row: {e}")

        return None

    def _looks_like_date(self, text: str) -> bool:
        """Check if text looks like a date"""
        if not text or len(text) < 8:
            return False

        date_patterns = [
            r'\d{4}-\d{1,2}-\d{1,2}',
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{1,2}-\d{1,2}-\d{4}',
            r'\w{3}\s+\d{1,2},?\s+\d{4}',
        ]

        for pattern in date_patterns:
            if re.search(pattern, text):
                return True

        return False

    def _parse_date(self, date_str: str) -> str:
        """Parse date to ISO format"""
        if not date_str:
            return datetime.now().isoformat()

        formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%m-%d-%Y',
            '%B %d, %Y',
            '%b %d, %Y',
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.isoformat()
            except:
                continue

        return date_str

    def _normalize_transaction_type(self, trans_type: str) -> str:
        """Normalize transaction type"""
        if not trans_type:
            return 'purchase'

        trans_type = trans_type.lower().strip()

        type_map = {
            'purchase': 'purchase',
            'buy': 'purchase',
            'bought': 'purchase',
            'sale': 'sale',
            'sell': 'sale',
            'sold': 'sale',
            'exchange': 'exchange',
            'swap': 'exchange',
        }

        for key, value in type_map.items():
            if key in trans_type:
                return value

        return 'purchase'
