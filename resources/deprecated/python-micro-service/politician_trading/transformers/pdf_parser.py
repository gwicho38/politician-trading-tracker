"""
PDF Parser for Senate disclosure documents.

Handles downloading and parsing PDF financial disclosure forms from the Senate website.
"""

import re
import logging
from typing import Optional, Dict, List, Any
import aiohttp
from io import BytesIO

logger = logging.getLogger(__name__)


class SenatePDFParser:
    """
    Parser for Senate PTR (Periodic Transaction Report) PDFs.

    These PDFs contain transaction details that need to be extracted:
    - Transaction dates
    - Asset names and tickers
    - Transaction types (purchase, sale, exchange)
    - Amount ranges
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def parse_pdf_url(self, pdf_url: str, politician_name: str) -> List[Dict[str, Any]]:
        """
        Download and parse a Senate PTR PDF.

        Args:
            pdf_url: URL to the PDF document
            politician_name: Name of the politician for context

        Returns:
            List of transaction dictionaries extracted from the PDF
        """
        self.logger.info(f"Parsing PDF for {politician_name}: {pdf_url}")

        try:
            # Download PDF
            pdf_content = await self._download_pdf(pdf_url)

            if not pdf_content:
                self.logger.warning(f"Failed to download PDF: {pdf_url}")
                return []

            # Parse PDF content
            transactions = await self._parse_pdf_content(pdf_content, politician_name, pdf_url)

            self.logger.info(f"Extracted {len(transactions)} transactions from PDF")
            return transactions

        except Exception as e:
            self.logger.error(f"Error parsing PDF {pdf_url}: {e}", exc_info=True)
            return []

    async def _download_pdf(self, pdf_url: str) -> Optional[bytes]:
        """
        Download PDF from URL.

        Senate URLs are often HTML pages that link to the actual PDF.
        This method handles both direct PDF links and HTML pages.
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; PoliticianTradingBot/1.0)"}

            async with self.session.get(pdf_url, headers=headers, timeout=30) as response:
                if response.status != 200:
                    self.logger.warning(f"PDF download failed with status {response.status}")
                    return None

                content = await response.read()
                content_type = response.headers.get("Content-Type", "").lower()

                # Check if it's actually a PDF
                if content_type.startswith("application/pdf") or content[:4] == b"%PDF":
                    self.logger.debug(f"Downloaded PDF: {len(content)} bytes")
                    return content

                # If it's HTML, try to find the PDF link
                elif "text/html" in content_type:
                    self.logger.debug("Response is HTML, looking for PDF link")
                    pdf_link = self._extract_pdf_link_from_html(content, pdf_url)

                    if pdf_link:
                        self.logger.info(f"Found PDF link: {pdf_link}")
                        # Recursively download the actual PDF
                        return await self._download_pdf(pdf_link)
                    else:
                        self.logger.warning("No PDF link found in HTML page")
                        return None

                else:
                    self.logger.warning(f"Unknown content type: {content_type}")
                    return None

        except Exception as e:
            self.logger.error(f"Error downloading PDF: {e}", exc_info=True)
            return None

    def _extract_pdf_link_from_html(self, html_content: bytes, base_url: str) -> Optional[str]:
        """Extract PDF download link from HTML page"""
        try:
            from bs4 import BeautifulSoup
            from urllib.parse import urljoin

            soup = BeautifulSoup(html_content, "html.parser")

            # Look for PDF links in common patterns
            pdf_patterns = [
                'a[href*=".pdf"]',  # Direct PDF links
                'a[href*="/download/"]',  # Download endpoints
                'a[href*="/view/"]',  # View endpoints
                'iframe[src*=".pdf"]',  # PDF in iframe
            ]

            for pattern in pdf_patterns:
                elements = soup.select(pattern)
                if elements:
                    href = elements[0].get("href") or elements[0].get("src")
                    if href:
                        # Make absolute URL
                        full_url = urljoin(base_url, href)
                        return full_url

            # Also check for any link with "pdf" in text
            for link in soup.find_all("a"):
                text = link.get_text().lower()
                if "pdf" in text or "download" in text:
                    href = link.get("href")
                    if href:
                        full_url = urljoin(base_url, href)
                        return full_url

            return None

        except ImportError:
            self.logger.warning("BeautifulSoup not available for HTML parsing")
            return None
        except Exception as e:
            self.logger.error(f"Error extracting PDF link: {e}")
            return None

    async def _parse_pdf_content(
        self, pdf_content: bytes, politician_name: str, pdf_url: str
    ) -> List[Dict[str, Any]]:
        """
        Parse PDF content to extract transactions.

        Note: This is a placeholder implementation. Full PDF parsing requires:
        - pdfplumber or PyPDF2 for text extraction
        - OCR (pytesseract) for scanned PDFs
        - Complex text parsing logic for different PDF formats

        For now, we'll use a simpler approach with pdfplumber if available,
        otherwise return a placeholder that can be processed manually.
        """
        transactions = []

        try:
            # Try to import pdfplumber
            try:
                import pdfplumber

                # Parse PDF with pdfplumber
                with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                    text = ""
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"

                    if text:
                        self.logger.debug(f"Extracted {len(text)} characters from PDF")
                        transactions = self._extract_transactions_from_text(
                            text, politician_name, pdf_url
                        )
                    else:
                        self.logger.warning("No text extracted from PDF - may be scanned image")

            except ImportError:
                self.logger.warning(
                    "pdfplumber not available - PDF parsing disabled. "
                    "Install with: uv pip install pdfplumber"
                )
                # Return a placeholder transaction indicating PDF needs manual review
                transactions = [
                    {
                        "politician_name": politician_name,
                        "asset_name": "PDF requires manual review",
                        "asset_type": "PDF_NEEDS_PARSING",
                        "transaction_type": "unknown",
                        "source_url": pdf_url,
                        "extraction_method": "pdf_placeholder",
                        "notes": "pdfplumber library not installed - manual review required",
                    }
                ]

        except Exception as e:
            self.logger.error(f"Error in PDF content parsing: {e}", exc_info=True)

        return transactions

    def _extract_transactions_from_text(
        self, text: str, politician_name: str, pdf_url: str
    ) -> List[Dict[str, Any]]:
        """
        Extract transaction data from PDF text.

        This uses regex patterns to find common transaction formats in PTR forms.
        """
        transactions = []

        # Common patterns in PTR forms
        # Date pattern: MM/DD/YYYY or MM-DD-YYYY
        date_pattern = r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b"

        # Ticker pattern: 1-5 uppercase letters in parentheses or standalone
        ticker_pattern = r"\b([A-Z]{1,5})\b|\(([A-Z]{1,5})\)"

        # Amount patterns
        amount_pattern = r"\$[\d,]+(?:\s*-\s*\$[\d,]+)?|Over \$[\d,]+"

        # Transaction type keywords
        transaction_keywords = {
            "purchase": r"\b(purchase|bought|buy|acquired)\b",
            "sale": r"\b(sale|sold|sell|disposed)\b",
            "exchange": r"\b(exchange|swap)\b",
        }

        # Split into lines and look for transaction patterns
        lines = text.split("\n")

        for i, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 10:
                continue

            # Look for lines that might contain transaction data
            # Typically has: date, asset name/ticker, type, amount

            # Find dates
            dates = re.findall(date_pattern, line)

            # Find tickers
            tickers = []
            for match in re.finditer(ticker_pattern, line):
                ticker = match.group(1) or match.group(2)
                if ticker:
                    tickers.append(ticker)

            # Find amounts
            amounts = re.findall(amount_pattern, line)

            # Find transaction type
            trans_type = "unknown"
            for type_name, pattern in transaction_keywords.items():
                if re.search(pattern, line, re.IGNORECASE):
                    trans_type = type_name
                    break

            # If we found key elements, create a transaction
            if dates and (tickers or amounts):
                transaction = {
                    "politician_name": politician_name,
                    "transaction_date": dates[0] if dates else "",
                    "asset_name": line[:100],  # Use line as asset description
                    "asset_ticker": tickers[0] if tickers else None,
                    "transaction_type": trans_type,
                    "amount": amounts[0] if amounts else "Unknown",
                    "source_url": pdf_url,
                    "extraction_method": "pdf_text_extraction",
                    "raw_text": line,
                }
                transactions.append(transaction)
                self.logger.debug(
                    f"Extracted transaction: {transaction.get('asset_ticker', 'N/A')}"
                )

        # If no transactions found, create a placeholder
        if not transactions:
            self.logger.warning("No transactions extracted from PDF text")
            transactions = [
                {
                    "politician_name": politician_name,
                    "asset_name": "PDF parsed but no transactions found",
                    "asset_type": "PDF_NO_TRANSACTIONS",
                    "transaction_type": "unknown",
                    "source_url": pdf_url,
                    "extraction_method": "pdf_no_match",
                    "notes": "PDF text extracted but no transaction patterns matched - may need manual review",
                }
            ]

        return transactions

    def should_parse_pdf(self, disclosure: Dict[str, Any]) -> bool:
        """
        Check if a disclosure record needs PDF parsing.

        Args:
            disclosure: Disclosure record dictionary

        Returns:
            True if this is a PDF-only disclosure that needs parsing
        """
        # Check for PDF indicator fields
        asset_type = disclosure.get("asset_type", "").upper()
        asset_name = disclosure.get("asset_name", "").lower()
        ticker = disclosure.get("asset_ticker", "").upper()

        # Indicators that this is a PDF-only record
        is_pdf_only = (
            asset_type == "PDF DISCLOSED FILING"
            or ticker == "N/A"
            or "scanned pdf" in asset_name
            or "ptr_link" in asset_name
        )

        # Check if there's a PDF URL
        raw_data = disclosure.get("raw_data", {})
        if isinstance(raw_data, str):
            try:
                import json

                raw_data = json.loads(raw_data)
            except (json.JSONDecodeError, ValueError):
                raw_data = {}

        pdf_url = raw_data.get("ptr_link") or disclosure.get("source_url", "")
        has_pdf_url = pdf_url and "efdsearch.senate.gov" in pdf_url

        return is_pdf_only and has_pdf_url
