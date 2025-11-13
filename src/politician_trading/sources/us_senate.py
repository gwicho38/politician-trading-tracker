"""
US Senate disclosure source.

Fetches financial disclosures from the Senate EFD (Electronic Financial Disclosure) database.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from bs4 import BeautifulSoup
import re

from .base_source import BaseSource, SourceConfig

logger = logging.getLogger(__name__)


class USSenateSource(BaseSource):
    """
    US Senate financial disclosures.

    Source: https://efdsearch.senate.gov
    Report Type: Periodic Transaction Reports (PTRs)
    """

    def _create_default_config(self) -> SourceConfig:
        """Create default configuration"""
        return SourceConfig(
            name="US Senate",
            source_type="us_senate",
            base_url="https://efdsearch.senate.gov",
            request_delay=2.0,  # Respectful rate limiting for government servers
            max_retries=3,
            timeout=60,
            headers={"User-Agent": "Mozilla/5.0 (compatible; PoliticianTradingBot/1.0)"},
        )

    async def _fetch_data(self, lookback_days: int, **kwargs) -> Any:
        """
        Fetch PTRs from Senate EFD database.

        Args:
            lookback_days: How many days back to search
            **kwargs: Additional parameters

        Returns:
            HTML response from search
        """
        search_url = f"{self.config.base_url}/search/"

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)

        # EFD search parameters
        params = {
            "report_type": "11",  # Periodic Transaction Report (PTR)
            "submitted_start_date": start_date.strftime("%m/%d/%Y"),
            "submitted_end_date": end_date.strftime("%m/%d/%Y"),
        }

        self.logger.info(
            f"Searching Senate EFD database: {start_date.strftime('%Y-%m-%d')} "
            f"to {end_date.strftime('%Y-%m-%d')}"
        )

        try:
            # Make search request
            response = await self._make_request(search_url, method="GET", params=params)

            if isinstance(response, str):
                self.logger.info("Received Senate search results (HTML response)")
                return response
            else:
                self.logger.warning("Unexpected response type from Senate EFD")
                return ""

        except Exception as e:
            self.logger.error(f"Error fetching Senate data: {e}", exc_info=True)
            return ""

    async def _parse_response(self, response_data: Any) -> List[Dict[str, Any]]:
        """
        Parse Senate EFD search results.

        The Senate EFD returns HTML search results with links to individual reports.
        Each report would need to be parsed for full transaction details.

        Args:
            response_data: HTML response from search

        Returns:
            List of disclosure dictionaries
        """
        disclosures = []

        if not response_data or not isinstance(response_data, str):
            self.logger.warning("No valid HTML response to parse")
            return disclosures

        try:
            soup = BeautifulSoup(response_data, "html.parser")

            # Find result rows - Senate EFD uses a results table
            # The exact selector may need adjustment based on current site structure
            result_rows = (
                soup.find_all("tr", class_="searchResultOdd")
                + soup.find_all("tr", class_="searchResultEven")
                or soup.select("table.table tr")
                or soup.find_all("tr")
            )

            self.logger.info(f"Found {len(result_rows)} potential result rows")

            for row in result_rows:
                try:
                    disclosure = self._parse_result_row(row)
                    if disclosure:
                        disclosures.append(disclosure)
                except Exception as e:
                    self.logger.warning(f"Failed to parse row: {e}")
                    continue

            self.logger.info(f"Successfully parsed {len(disclosures)} Senate disclosures")

        except Exception as e:
            self.logger.error(f"Error parsing Senate results: {e}", exc_info=True)

        return disclosures

    def _parse_result_row(self, row) -> Optional[Dict[str, Any]]:
        """
        Parse a single Senate EFD result row.

        Args:
            row: BeautifulSoup row element

        Returns:
            Disclosure dictionary or None if invalid
        """
        cells = row.find_all("td")

        if len(cells) < 3:  # Need at least 3 cells for valid data
            return None

        try:
            # Extract text from cells
            cell_texts = [cell.get_text(strip=True) for cell in cells]

            # Find politician name (usually in first cell)
            politician_name = ""
            for text in cell_texts:
                if (
                    len(text) > 3
                    and any(c.isalpha() for c in text)
                    and not text.isdigit()
                    and "pdf" not in text.lower()
                ):
                    clean_name = (
                        text.replace("Hon.", "").replace("Sen.", "").replace("Senator", "").strip()
                    )
                    if len(clean_name) > 3 and " " in clean_name:
                        politician_name = clean_name
                        break

            if not politician_name:
                self.logger.debug("Could not extract politician name from row")
                return None

            # Find filing date
            filing_date = None
            for text in cell_texts:
                # Look for date pattern MM/DD/YYYY
                date_match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", text)
                if date_match:
                    try:
                        filing_date = datetime.strptime(date_match.group(1), "%m/%d/%Y").isoformat()
                        break
                    except (ValueError, TypeError):
                        pass

            # Find report link
            report_url = None
            pdf_link = row.find("a", href=True)
            if pdf_link:
                href = pdf_link["href"]
                if href.startswith("http"):
                    report_url = href
                else:
                    report_url = f"{self.config.base_url}{href}"

            # Extract report type
            report_type = ""
            for text in cell_texts:
                if "periodic" in text.lower() or "transaction" in text.lower():
                    report_type = text
                    break

            # Create disclosure dictionary
            # Note: Full transaction details would require parsing the PDF/detailed report
            disclosure = {
                "politician_name": politician_name,
                "transaction_date": filing_date or datetime.now().isoformat(),
                "disclosure_date": filing_date or datetime.now().isoformat(),
                "asset_name": "Multiple Assets",  # PTRs contain multiple transactions
                "transaction_type": "purchase",  # Default - actual type in PDF
                "amount": "See Report",  # Actual amounts in PDF
                "source_url": report_url,
                "document_id": self._extract_document_id(report_url),
                "report_type": report_type,
                "requires_pdf_parsing": True,
                "extraction_method": "senate_efd_search",
            }

            return disclosure

        except Exception as e:
            self.logger.warning(f"Error parsing result row: {e}")
            return None

    def _extract_document_id(self, url: Optional[str]) -> Optional[str]:
        """Extract document ID from report URL"""
        if not url:
            return None

        # Senate EFD URLs typically have an ID parameter
        match = re.search(r"[?&]id=([^&]+)", url)
        if match:
            return match.group(1)

        # Or extract from path
        match = re.search(r"/(\d+)\.pdf", url)
        if match:
            return match.group(1)

        return None
