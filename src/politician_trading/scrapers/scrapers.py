"""
Web scrapers for politician trading data
"""

import asyncio
import io
import logging
import re
import zipfile
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

# Optional OCR dependencies for PDF parsing
try:
    from pdf2image import convert_from_bytes
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    convert_from_bytes = None
    pytesseract = None

from ..config import ScrapingConfig
from ..models import Politician, TradingDisclosure, TransactionType, DisclosureStatus, CapitalGain, AssetHolding
from ..parsers import (
    TickerResolver,
    ValueRangeParser,
    OwnerParser,
    DateParser,
    extract_ticker_from_text,
    parse_asset_type,
    ASSET_TYPE_CODES,
)
from ..utils.circuit_breaker import get_circuit_breaker, CircuitBreakerError

logger = logging.getLogger(__name__)


class BaseScraper:
    """Base class for all scrapers with circuit breaker support"""

    def __init__(self, config: ScrapingConfig, circuit_breaker_name: Optional[str] = None):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None

        # Initialize circuit breaker for this scraper
        self.circuit_breaker_name = circuit_breaker_name or self.__class__.__name__
        self.circuit_breaker = get_circuit_breaker(
            name=self.circuit_breaker_name,
            failure_threshold=config.max_retries + 2,  # Allow slightly more than max_retries
            recovery_timeout=120,  # 2 minutes before trying again
            expected_exception=Exception
        )
        logger.debug(f"Initialized circuit breaker for {self.circuit_breaker_name}")

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            headers={"User-Agent": self.config.user_agent},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def fetch_page(self, url: str, **kwargs) -> Optional[str]:
        """Fetch a web page with error handling, rate limiting, and circuit breaker"""
        try:
            # Use circuit breaker to protect against cascading failures
            return await self.circuit_breaker.call(self._fetch_page_impl, url, **kwargs)
        except CircuitBreakerError as e:
            logger.error(f"Circuit breaker open for {self.circuit_breaker_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return None

    async def _fetch_page_impl(self, url: str, **kwargs) -> Optional[str]:
        """Internal implementation of page fetching with retry logic"""
        for attempt in range(self.config.max_retries):
            try:
                await asyncio.sleep(self.config.request_delay)

                async with self.session.get(url, **kwargs) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 429:  # Rate limited
                        logger.warning(f"Rate limited (429) for {url}")
                        await asyncio.sleep(self.config.request_delay * 2)
                    elif response.status >= 500:
                        # Server errors - likely temporary
                        logger.warning(f"Server error {response.status} for {url}")
                        if attempt < self.config.max_retries - 1:
                            await asyncio.sleep(self.config.request_delay * (attempt + 1))
                    else:
                        # Client errors (4xx) - don't retry
                        logger.warning(f"Client error {response.status} for {url}")
                        return None

            except asyncio.TimeoutError:
                logger.error(f"Timeout (attempt {attempt + 1}) for {url}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.request_delay * (attempt + 1))
            except aiohttp.ClientError as e:
                logger.error(f"Client error (attempt {attempt + 1}) for {url}: {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.request_delay * (attempt + 1))
            except Exception as e:
                logger.error(f"Unexpected error (attempt {attempt + 1}) for {url}: {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.request_delay * (attempt + 1))

        # All retries exhausted
        raise Exception(f"Failed to fetch {url} after {self.config.max_retries} attempts")

    def parse_amount_range(
        self, amount_text: str
    ) -> Tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
        """Parse amount text into range values"""
        if not amount_text:
            return None, None, None

        amount_text = amount_text.replace(",", "").replace("$", "").strip()

        # Look for range patterns like "$1,001 - $15,000"
        range_match = re.search(r"(\d+(?:\.\d{2})?)\s*[-–]\s*(\d+(?:\.\d{2})?)", amount_text)
        if range_match:
            min_val = Decimal(range_match.group(1))
            max_val = Decimal(range_match.group(2))
            return min_val, max_val, None

        # Look for exact amounts
        exact_match = re.search(r"(\d+(?:\.\d{2})?)", amount_text)
        if exact_match:
            exact_val = Decimal(exact_match.group(1))
            return None, None, exact_val

        # Handle standard ranges
        range_mappings = {
            "$1,001 - $15,000": (Decimal("1001"), Decimal("15000")),
            "$15,001 - $50,000": (Decimal("15001"), Decimal("50000")),
            "$50,001 - $100,000": (Decimal("50001"), Decimal("100000")),
            "$100,001 - $250,000": (Decimal("100001"), Decimal("250000")),
            "$250,001 - $500,000": (Decimal("250001"), Decimal("500000")),
            "$500,001 - $1,000,000": (Decimal("500001"), Decimal("1000000")),
            "$1,000,001 - $5,000,000": (Decimal("1000001"), Decimal("5000000")),
            "$5,000,001 - $25,000,000": (Decimal("5000001"), Decimal("25000000")),
            "$25,000,001 - $50,000,000": (Decimal("25000001"), Decimal("50000000")),
            "Over $50,000,000": (Decimal("50000001"), None),
        }

        for pattern, (min_val, max_val) in range_mappings.items():
            if pattern.lower() in amount_text.lower():
                return min_val, max_val, None

        return None, None, None


class CongressTradingScraper(BaseScraper):
    """Scraper for US Congress trading data"""

    def __init__(self, config: ScrapingConfig):
        super().__init__(config, circuit_breaker_name="US_Congress")
        self.ticker_resolver = TickerResolver()

    def _parse_amount_from_pdf_text(
        self, text: str
    ) -> Tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
        """Parse amount/value from OCR'd PDF text

        This is an enhanced version of parse_amount_range that handles
        the specific patterns found in House disclosure PDFs after OCR.

        Args:
            text: Text extracted from PDF via OCR

        Returns:
            Tuple of (min_amount, max_amount, exact_amount)
        """
        if not text:
            return None, None, None

        # Clean up text - remove commas for parsing
        text = text.replace(",", "")

        # Standard House disclosure ranges (with regex for OCR variations)
        range_mappings = {
            r"\$1,?001\s*-\s*\$15,?000": (Decimal("1001"), Decimal("15000")),
            r"\$15,?001\s*-\s*\$50,?000": (Decimal("15001"), Decimal("50000")),
            r"\$50,?001\s*-\s*\$100,?000": (Decimal("50001"), Decimal("100000")),
            r"\$100,?001\s*-\s*\$250,?000": (Decimal("100001"), Decimal("250000")),
            r"\$250,?001\s*-\s*\$500,?000": (Decimal("250001"), Decimal("500000")),
            r"\$500,?001\s*-\s*\$1,?000,?000": (Decimal("500001"), Decimal("1000000")),
            r"\$1,?000,?001\s*-\s*\$5,?000,?000": (Decimal("1000001"), Decimal("5000000")),
            r"\$5,?000,?001\s*-\s*\$25,?000,?000": (Decimal("5000001"), Decimal("25000000")),
            r"\$25,?000,?001\s*-\s*\$50,?000,?000": (Decimal("25000001"), Decimal("50000000")),
            r"Over\s+\$50,?000,?000": (Decimal("50000001"), None),
        }

        # Check standard ranges
        for pattern, (min_val, max_val) in range_mappings.items():
            if re.search(pattern, text, re.IGNORECASE):
                return min_val, max_val, None

        # Look for custom range patterns: $X - $Y or $X-$Y
        range_match = re.search(r"\$(\d+)\s*-\s*\$(\d+)", text)
        if range_match:
            min_val = Decimal(range_match.group(1))
            max_val = Decimal(range_match.group(2))
            return min_val, max_val, None

        # Look for exact amounts: $X or $X.XX
        exact_match = re.search(r"\$(\d+(?:\.\d{2})?)", text)
        if exact_match:
            exact_val = Decimal(exact_match.group(1))
            return None, None, exact_val

        return None, None, None

    def _extract_transactions_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract transaction details from OCR'd PDF text

        Looks for patterns like:
        - " P " for Purchase, " S " for Sale, " E " for Exchange
        - Ticker symbols in parentheses: (AAPL), (MSFT)
        - Amount ranges: $1,001 - $15,000
        - Dates: MM/DD/YYYY

        Args:
            text: OCR'd text from PDF

        Returns:
            List of transaction dictionaries with extracted data
        """
        transactions = []

        # Split by double newlines to get paragraphs/sections
        sections = text.split("\n\n")

        for section in sections:
            # Remove single newlines within section for easier parsing
            line = section.replace("\r", "").replace("\n", " ")

            # Look for transaction type indicators
            transaction_type = None
            if " P " in line or " Purchase " in line or "Purchase" in line:
                transaction_type = "PURCHASE"
            elif " S " in line or " Sale " in line or "Sale" in line:
                transaction_type = "SALE"
            elif " E " in line or " Exchange " in line or "Exchange" in line:
                transaction_type = "EXCHANGE"

            if not transaction_type:
                continue

            # Extract ticker symbol from parentheses
            ticker = None
            opening_paren = -1
            closing_paren = line.find(")")
            if closing_paren != -1:
                opening_paren = line.rfind("(", 0, closing_paren)
                if opening_paren != -1:
                    potential_ticker = line[opening_paren + 1 : closing_paren].strip()
                    # Tickers are usually 1-5 uppercase letters
                    if (
                        potential_ticker
                        and potential_ticker.isupper()
                        and 1 <= len(potential_ticker) <= 5
                    ):
                        ticker = potential_ticker

            # Extract asset name (usually before the ticker in parentheses)
            asset_name = None
            if ticker and opening_paren != -1:
                # Look backwards from opening paren for the asset name
                before_ticker = line[:opening_paren].strip()
                # Asset name is typically the last few words before the ticker
                words = before_ticker.split()
                if len(words) >= 2:
                    asset_name = " ".join(words[-5:])  # Take up to last 5 words

            # Extract amount range
            amount_min, amount_max, amount_exact = self._parse_amount_from_pdf_text(line)

            # Extract transaction date (MM/DD/YYYY)
            transaction_date = None
            date_pattern = r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"
            date_match = re.search(date_pattern, line)
            if date_match:
                try:
                    month, day, year = date_match.groups()
                    transaction_date = datetime(int(year), int(month), int(day))
                except (ValueError, TypeError):
                    pass

            # Only add transaction if we found a ticker
            if ticker:
                transaction = {
                    "ticker": ticker,
                    "asset_name": asset_name or ticker,
                    "transaction_type": transaction_type,
                    "transaction_date": transaction_date,
                    "amount_min": amount_min,
                    "amount_max": amount_max,
                    "amount_exact": amount_exact,
                    "raw_text": line[:200],  # Keep snippet for debugging
                }
                transactions.append(transaction)

        return transactions

    async def _parse_house_pdf(
        self, pdf_url: str, pdf_content: bytes = None, session: aiohttp.ClientSession = None,
        filing_metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Parse a House disclosure PDF to extract transaction details

        Uses pdfplumber for text extraction (faster than OCR),
        then enhanced parsing to extract detailed transaction data.

        Args:
            pdf_url: URL of the PDF to parse
            pdf_content: Optional pre-downloaded PDF bytes
            session: Optional aiohttp session for downloading
            filing_metadata: Optional metadata (filer_id, filing_date, etc.)

        Returns:
            List of transaction dictionaries with extracted data
        """
        transactions = []

        try:
            # Download PDF if not provided
            if pdf_content is None:
                if session is None:
                    async with aiohttp.ClientSession() as temp_session:
                        async with temp_session.get(pdf_url) as response:
                            if response.status != 200:
                                logger.warning(
                                    f"Failed to download PDF: {pdf_url} (status {response.status})"
                                )
                                return []
                            pdf_content = await response.read()
                else:
                    async with session.get(pdf_url) as response:
                        if response.status != 200:
                            logger.warning(
                                f"Failed to download PDF: {pdf_url} (status {response.status})"
                            )
                            return []
                        pdf_content = await response.read()

            # Try pdfplumber first (fast, works for most PDFs)
            try:
                import pdfplumber
                import io

                full_text = ""
                with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            full_text += page_text + "\n"

                logger.info(f"Extracted {len(full_text)} characters via pdfplumber")

                # Use enhanced parser
                if filing_metadata is None:
                    filing_metadata = {}

                transactions = self._extract_transactions_section(full_text, filing_metadata)
                logger.info(f"Extracted {len(transactions)} transactions using enhanced parser")

            except Exception as pdfplumber_error:
                # Fall back to OCR if pdfplumber fails
                logger.warning(f"pdfplumber failed: {pdfplumber_error}")

                if not OCR_AVAILABLE:
                    logger.error("OCR dependencies (pdf2image, pytesseract) not available - cannot fall back to OCR")
                    logger.info("To enable OCR fallback, install: pip install pdf2image pytesseract poppler-utils")
                else:
                    logger.info("Falling back to OCR")

                    # Convert PDF pages to images at 600 DPI for better OCR
                    logger.info(f"Converting PDF to images ({len(pdf_content)} bytes)")
                    pages = convert_from_bytes(pdf_content, dpi=600)

                    # Extract text from each page
                    full_text = ""
                    for i, page in enumerate(pages):
                        logger.debug(f"OCR processing page {i + 1}/{len(pages)}")
                        text = pytesseract.image_to_string(page)
                        full_text += text + "\n\n"

                    logger.info(f"Extracted {len(full_text)} characters via OCR")

                    # Use enhanced parser
                    transactions = self._extract_transactions_section(full_text, filing_metadata or {})
                    logger.info(f"Extracted {len(transactions)} transactions from OCR text")

        except Exception as e:
            logger.error(f"Error parsing PDF {pdf_url}: {e}")

        return transactions

    async def _download_and_parse_house_index(
        self,
        year: int,
        session: aiohttp.ClientSession,
        base_url: str = "https://disclosures-clerk.house.gov",
    ) -> List[Dict[str, Any]]:
        """Download and parse House disclosure ZIP index file

        Downloads the annual ZIP file containing tab-separated index of all filings.
        This is much faster and more reliable than form-based scraping.

        Args:
            year: Year to scrape
            session: aiohttp session for HTTP requests
            base_url: Base URL for House disclosure site

        Returns:
            List of disclosure metadata dictionaries
        """
        disclosures = []
        zip_url = f"{base_url}/public_disc/financial-pdfs/{year}FD.ZIP"

        try:
            logger.info(f"Downloading House disclosure index for {year}...")

            # Download the ZIP index file
            async with session.get(zip_url) as response:
                if response.status != 200:
                    logger.error(f"Failed to download index: {response.status}")
                    return []

                zip_content = await response.read()
                logger.info(f"Downloaded index file ({len(zip_content)} bytes)")

                # Extract the index file from the ZIP
                with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
                    # The ZIP contains a TXT file with the index
                    txt_filename = f"{year}FD.txt"

                    if txt_filename not in z.namelist():
                        logger.error(f"Expected file {txt_filename} not found in ZIP")
                        logger.info(f"Available files: {z.namelist()}")
                        return []

                    # Read the index file
                    with z.open(txt_filename) as f:
                        index_content = f.read().decode("utf-8", errors="ignore")

                    logger.info("Extracted index file")

                    # Parse the tab-separated index file
                    lines = index_content.strip().split("\n")
                    logger.info(f"Found {len(lines)} filing records in index")

                    # Skip header line (line 0)
                    for i, line in enumerate(lines[1:], start=1):
                        fields = line.split("\t")

                        if len(fields) < 9:
                            continue  # Skip malformed lines

                        # Extract key information
                        # Field indices: [0]=Prefix, [1]=Last, [2]=First, [3]=Suffix, [4]=FilingType,
                        #                [5]=StateDst, [6]=Year, [7]=FilingDate, [8]=DocID
                        prefix = fields[0].strip()
                        last_name = fields[1].strip()
                        first_name = fields[2].strip()
                        suffix = fields[3].strip()
                        filing_type = fields[4].strip()
                        state_district = fields[5].strip()
                        # Note: fields[6] is file_year but not used (year param already known)
                        filing_date_str = fields[7].strip()
                        doc_id = fields[8].strip()  # Important: strip removes \r

                        if not doc_id or doc_id == "DocID":  # Skip header or empty
                            continue

                        # Build full name with prefix/suffix
                        name_parts = [p for p in [prefix, first_name, last_name, suffix] if p]
                        full_name = " ".join(name_parts)

                        # Parse filing date
                        filing_date = None
                        if filing_date_str:
                            try:
                                filing_date = datetime.strptime(filing_date_str, "%m/%d/%Y")
                            except (ValueError, TypeError):
                                try:
                                    filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d")
                                except (ValueError, TypeError):
                                    pass

                        # Build PDF URL - CRITICAL: Use financial-pdfs, not ptr-pdfs
                        pdf_url = f"{base_url}/public_disc/financial-pdfs/{year}/{doc_id}.pdf"

                        # Create disclosure metadata
                        disclosure_info = {
                            "politician_name": full_name,
                            "first_name": first_name,
                            "last_name": last_name,
                            "state_district": state_district,
                            "filing_type": filing_type,
                            "filing_date": filing_date,
                            "doc_id": doc_id,
                            "pdf_url": pdf_url,
                            "year": year,
                        }

                        disclosures.append(disclosure_info)

                    logger.info(f"Successfully parsed {len(disclosures)} House disclosure records")

        except zipfile.BadZipFile as e:
            logger.error(f"Invalid ZIP file: {e}")
        except Exception as e:
            logger.error(f"Error downloading/parsing index: {e}", exc_info=True)

        return disclosures

    async def scrape_house_disclosures(
        self,
        year: Optional[int] = None,
        parse_pdfs: bool = False,
        max_pdfs_per_run: Optional[int] = None,
    ) -> List[TradingDisclosure]:
        """Scrape House financial disclosures using ZIP index approach

        This implementation downloads the annual ZIP index file which contains
        metadata for ALL House filings. This is much faster and more reliable
        than the old form-based scraping approach.

        Args:
            year: Year to scrape (defaults to current year)
            parse_pdfs: If True, download and parse PDFs to extract transactions (slow!)
            max_pdfs_per_run: Maximum number of PDFs to parse per run (for rate limiting)

        Returns:
            List of TradingDisclosure objects with metadata (and transactions if parse_pdfs=True)
        """
        disclosures = []

        if year is None:
            year = datetime.now().year

        base_url = "https://disclosures-clerk.house.gov"

        try:
            logger.info(f"Starting House disclosures scrape for {year} using ZIP index approach")

            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout * 3),  # Longer for PDFs
                headers={"User-Agent": self.config.user_agent},
            ) as session:
                # Download and parse the ZIP index file
                disclosure_metadata_list = await self._download_and_parse_house_index(
                    year=year, session=session, base_url=base_url
                )

                if not disclosure_metadata_list:
                    logger.warning(f"No House disclosures found for {year}")
                    return []

                logger.info(
                    f"Retrieved metadata for {len(disclosure_metadata_list)} House disclosures"
                )

                # Convert metadata dictionaries to TradingDisclosure objects
                parsed_pdf_count = 0

                for metadata in disclosure_metadata_list:
                    # Check if we've hit the PDF parsing limit
                    if parse_pdfs and max_pdfs_per_run and parsed_pdf_count >= max_pdfs_per_run:
                        logger.info(
                            f"Reached max_pdfs_per_run limit ({max_pdfs_per_run}), skipping remaining PDF parsing"
                        )
                        parse_pdfs = False  # Stop parsing for remaining items

                    # Optionally parse the PDF to extract transactions
                    transactions_data = []
                    if parse_pdfs:
                        try:
                            logger.info(
                                f"Parsing PDF {parsed_pdf_count + 1}/{max_pdfs_per_run or '∞'}: {metadata['politician_name']}"
                            )

                            # Prepare filing metadata for enhanced parser
                            filing_meta = {
                                "filer_id": metadata.get("doc_id"),
                                "filing_date": metadata.get("filing_date"),
                                "doc_id": metadata.get("doc_id"),
                            }

                            transactions_data = await self._parse_house_pdf(
                                pdf_url=metadata["pdf_url"],
                                session=session,
                                filing_metadata=filing_meta
                            )

                            if transactions_data:
                                logger.info(f"  Found {len(transactions_data)} transactions")

                            parsed_pdf_count += 1

                            # Rate limiting between PDF downloads
                            await asyncio.sleep(self.config.request_delay)

                        except Exception as e:
                            logger.error(
                                f"  Error parsing PDF for {metadata['politician_name']}: {e}"
                            )

                    # Create TradingDisclosure object for each transaction found
                    # If no transactions, create one disclosure with the metadata
                    if transactions_data:
                        for txn in transactions_data:
                            disclosure = TradingDisclosure(
                                politician_id="",  # Will be set later
                                asset_name=txn.get("asset_name", "Unknown"),
                                asset_ticker=txn.get("ticker"),
                                transaction_type=TransactionType[
                                    txn.get("transaction_type", "PURCHASE")
                                ],
                                transaction_date=txn.get("transaction_date")
                                or metadata.get("filing_date"),
                                amount_range_min=txn.get("amount_min"),
                                amount_range_max=txn.get("amount_max"),
                                amount_exact=txn.get("amount_exact"),
                                disclosure_date=metadata.get("filing_date"),
                                source_url=metadata["pdf_url"],
                                status=DisclosureStatus.PENDING,
                                raw_data={
                                    "politician_name": metadata["politician_name"],
                                    "doc_id": metadata["doc_id"],
                                    "filing_type": metadata["filing_type"],
                                },
                                # Enhanced fields from Phase 5 parser
                                filer_id=txn.get("filer_id"),
                                filing_date=txn.get("filing_date"),
                                ticker_confidence_score=txn.get("ticker_confidence_score"),
                                asset_owner=txn.get("asset_owner"),
                                specific_owner_text=txn.get("specific_owner_text"),
                                asset_type_code=txn.get("asset_type_code"),
                                notification_date=txn.get("notification_date"),
                                filing_status=txn.get("filing_status"),
                                quantity=txn.get("quantity"),
                            )
                            disclosures.append(disclosure)
                    else:
                        # Create disclosure with metadata only (no transaction details yet)
                        disclosure = TradingDisclosure(
                            politician_id="",  # Will be set later
                            asset_name=f"{metadata['filing_type']} Filing",
                            asset_ticker=None,
                            transaction_type=TransactionType.PURCHASE,  # Default, unknown
                            transaction_date=metadata.get("filing_date"),
                            amount_range_min=None,
                            amount_range_max=None,
                            amount_exact=None,
                            disclosure_date=metadata.get("filing_date"),
                            source_url=metadata["pdf_url"],
                            status=(
                                DisclosureStatus.PENDING
                                if not parse_pdfs
                                else DisclosureStatus.PROCESSED
                            ),
                            raw_data={
                                "politician_name": metadata["politician_name"],
                                "doc_id": metadata["doc_id"],
                                "filing_type": metadata["filing_type"],
                            },
                        )
                        disclosures.append(disclosure)

                # Rate limiting
                await asyncio.sleep(self.config.request_delay)

                logger.info(f"Successfully created {len(disclosures)} House disclosure records")
                if parse_pdfs:
                    logger.info(f"Parsed {parsed_pdf_count} PDFs for transaction details")

        except Exception as e:
            logger.error(f"House disclosures scrape failed: {e}", exc_info=True)

        return disclosures

    async def scrape_senate_disclosures(self) -> List[TradingDisclosure]:
        """Scrape Senate financial disclosures from the official EFD database"""
        disclosures = []
        base_url = "https://efdsearch.senate.gov"
        # The search endpoint needs to be the correct path
        search_url = f"{base_url}/search/view/ptr/"  # PTR = Periodic Transaction Report

        try:
            logger.info("Starting Senate disclosures scrape from EFD database")

            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                headers={"User-Agent": self.config.user_agent},
            ) as session:
                # Try the public PTR listing page first
                async with session.get(search_url) as response:
                    if response.status == 200:
                        html = await response.text()

                        # Log response details for debugging
                        logger.debug(f"Senate search page HTML preview: {html[:1000]}")
                        logger.debug(f"Senate response headers: {dict(response.headers)}")
                        logger.debug(f"Senate search URL with params: {response.url}")

                        disclosures = await self._parse_senate_results(html, base_url)
                        logger.info(f"Found {len(disclosures)} Senate disclosures")
                    else:
                        logger.warning(f"Senate search failed with status {response.status}")

                # Rate limiting
                await asyncio.sleep(self.config.request_delay)

        except Exception as e:
            logger.error(f"Senate disclosures scrape failed: {e}")
            # Return empty list on error rather than sample data

        return disclosures

    async def _parse_house_results(self, html: str, base_url: str) -> List[TradingDisclosure]:
        """Parse House disclosure search results"""
        disclosures = []

        try:
            soup = BeautifulSoup(html, "html.parser")

            # Look for disclosure result rows - try multiple selectors
            result_rows = (
                soup.find_all("tr", class_="disclosure-row")
                or soup.select('tr[id*="GridView"]')
                or soup.select("table tr")
                or soup.find_all("tr")
            )

            logger.info(f"Found {len(result_rows)} potential result rows")

            for row in result_rows[:20]:  # Limit to 20 most recent
                cells = row.find_all("td")
                if len(cells) >= 3:  # At least 3 columns
                    # Extract text from each cell to identify the structure
                    cell_texts = [
                        cell.get_text(strip=True) for cell in cells if cell.get_text(strip=True)
                    ]

                    if not cell_texts:
                        continue

                    # Try to identify which cell contains the politician name
                    # Names usually contain letters and may have titles like "Rep.", "Hon."
                    politician_name = ""

                    for text in cell_texts:
                        # Look for text that looks like a person's name
                        if (
                            len(text) > 3
                            and any(c.isalpha() for c in text)
                            and not text.isdigit()
                            and not text.startswith("20")  # Not a year
                            and "pdf" not in text.lower()
                            and "view" not in text.lower()
                        ):
                            # Clean up potential name
                            clean_name = (
                                text.replace("Hon.", "")
                                .replace("Rep.", "")
                                .replace("Sen.", "")
                                .strip()
                            )
                            if len(clean_name) > 3 and " " in clean_name:  # Likely full name
                                politician_name = clean_name
                                break

                    if not politician_name:
                        politician_name = cell_texts[0]  # Fallback to first cell

                    # Extract other information
                    filing_year = next(
                        (
                            text
                            for text in cell_texts
                            if text.isdigit() and len(text) == 4 and text.startswith("20")
                        ),
                        "",
                    )
                    filing_type = next(
                        (
                            text
                            for text in cell_texts
                            if "periodic" in text.lower() or "annual" in text.lower()
                        ),
                        "",
                    )

                    # Look for PDF link
                    pdf_link = row.find("a", href=True)
                    if pdf_link:
                        pdf_url = urljoin(base_url, pdf_link["href"])

                        # Create basic disclosure entry
                        # Note: Actual transaction details would require PDF parsing
                        disclosure = TradingDisclosure(
                            politician_id="",  # To be filled by matcher
                            transaction_date=datetime.now() - timedelta(days=30),  # Estimate
                            disclosure_date=datetime.now() - timedelta(days=15),  # Estimate
                            transaction_type=TransactionType.PURCHASE,  # Default
                            asset_name="Unknown Asset",  # Would need PDF parsing
                            asset_type="stock",
                            amount_range_min=Decimal("1001"),
                            amount_range_max=Decimal("15000"),
                            source_url=pdf_url,
                            raw_data={
                                "politician_name": politician_name,
                                "filing_year": filing_year,
                                "filing_type": filing_type,
                                "requires_pdf_parsing": True,
                                "extraction_method": "house_search_results",
                            },
                        )
                        disclosures.append(disclosure)

        except Exception as e:
            logger.error(f"Error parsing House results: {e}")

        return disclosures

    async def _parse_senate_results(self, html: str, base_url: str) -> List[TradingDisclosure]:
        """Parse Senate EFD search results"""
        disclosures = []

        try:
            soup = BeautifulSoup(html, "html.parser")

            # Look for search result rows
            result_rows = soup.find_all("tr", class_="searchresult") or soup.select("tbody tr")

            logger.debug(f"Senate parser found {len(result_rows)} potential result rows")

            # Log table structure if available
            tables = soup.find_all("table")
            logger.debug(f"Found {len(tables)} tables in Senate results")

            for row in result_rows[:20]:  # Limit to 20 most recent
                cells = row.find_all("td")
                if len(cells) >= 4:
                    # Extract information
                    name = cells[0].get_text(strip=True) if cells[0] else ""
                    report_type = cells[1].get_text(strip=True) if cells[1] else ""
                    filing_date = cells[2].get_text(strip=True) if cells[2] else ""

                    # Look for report link
                    report_link = row.find("a", href=True)
                    if report_link and "ptr" in report_type.lower():  # Periodic Transaction Report
                        report_url = urljoin(base_url, report_link["href"])

                        # Create disclosure entry
                        # Note: Actual transaction details would require report parsing
                        disclosure = TradingDisclosure(
                            politician_id="",  # To be filled by matcher
                            transaction_date=datetime.now() - timedelta(days=30),  # Estimate
                            disclosure_date=self._parse_date(filing_date) or datetime.now(),
                            transaction_type=TransactionType.PURCHASE,  # Default
                            asset_name="Unknown Asset",  # Would need report parsing
                            asset_type="stock",
                            amount_range_min=Decimal("1001"),
                            amount_range_max=Decimal("50000"),
                            source_url=report_url,
                            raw_data={
                                "politician_name": name,
                                "report_type": report_type,
                                "filing_date": filing_date,
                                "requires_report_parsing": True,
                            },
                        )
                        disclosures.append(disclosure)

        except Exception as e:
            logger.error(f"Error parsing Senate results: {e}")

        return disclosures

    def _extract_transactions_section(self, pdf_text: str, filing_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Extract transaction data from House disclosure PDF.

        This enhanced parser handles the actual PTR format, which looks like:

        Advanced Micro Devices, Inc. (AMD) P 01/08/2025 01/10/2025 $1,001 - $15,000
        [ST]
        Filing Status: New
        Specific Owner: DG Trust

        Args:
            pdf_text: Full text extracted from PDF
            filing_metadata: Optional metadata (filer_id, filing_date, etc.)

        Returns:
            List of transaction dictionaries with enhanced fields
        """
        transactions = []
        filing_metadata = filing_metadata or {}

        # Split text into lines for line-by-line parsing
        lines = pdf_text.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines and headers
            if not line or 'Transaction' in line or 'Owner' in line or 'Type' in line:
                i += 1
                continue

            # Look for transaction type indicator (P, S, E) with dates and amounts
            # Pattern: Asset name (TICKER) TYPE DATE DATE $AMOUNT
            trans_match = re.search(
                r'(.+?)\s+([PSE])\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(\$[\d,]+ - \$[\d,]+|\$[\d,]+|Over \$[\d,]+)',
                line
            )

            if not trans_match:
                i += 1
                continue

            # Parse the main transaction line
            asset_part = trans_match.group(1).strip()
            trans_type_code = trans_match.group(2)
            transaction_date_str = trans_match.group(3)
            notification_date_str = trans_match.group(4)
            amount_str = trans_match.group(5)

            # Map transaction type
            transaction_type = {
                'P': 'PURCHASE',
                'S': 'SALE',
                'E': 'EXCHANGE'
            }.get(trans_type_code, 'UNKNOWN')

            # Extract asset name from asset_part
            asset_name = asset_part.strip()

            # Parse dates
            transaction_date = DateParser.parse(transaction_date_str)
            notification_date = DateParser.parse(notification_date_str)

            # Parse value range
            value_data = ValueRangeParser.parse(amount_str)

            # Initialize fields
            explicit_ticker = None
            asset_type_code = None
            asset_type_desc = None
            specific_owner = None
            filing_status = None

            # The actual structure is:
            # Line i-2 (or earlier): S          O : DG Trust  (optional owner)
            # Line i-1 (or earlier): F      S     : New       (filing status)
            # Line i:                Transaction line         (current line)
            # Line i+1:              (TICKER) [TYPE]          (ticker and asset type)

            # Check NEXT line for ticker and asset type (most reliable)
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()

                # Look for ticker in parentheses like "(AMZN) [ST]"
                ticker_from_next_line = extract_ticker_from_text(next_line)
                if ticker_from_next_line:
                    explicit_ticker = ticker_from_next_line

                # Asset type code like [ST], [MF], etc.
                code_match = re.search(r'\[([A-Z0-9]{2,3})\]', next_line)
                if code_match:
                    asset_type_code = code_match.group(1)
                    asset_type_desc = ASSET_TYPE_CODES.get(asset_type_code)

            # Check previous 4 lines for owner and filing status
            for j in range(max(0, i - 4), i):
                prev_line = lines[j].strip()

                # Specific Owner pattern: "S          O : DG Trust"
                if not specific_owner:
                    owner_match = re.search(r'S\s+O\s*:\s*(.+)', prev_line, re.IGNORECASE)
                    if owner_match:
                        owner_text = owner_match.group(1).strip()
                        # Remove any trailing junk like "ID Owner Asset Transaction"
                        owner_text = re.sub(r'\s*(ID|Owner|Asset|Transaction|Date|Type|Gains|Cap\.|Notification|Amount).*$', '', owner_text, flags=re.IGNORECASE)
                        if owner_text and len(owner_text) > 2:  # Must have substance
                            specific_owner = owner_text

                # Filing Status pattern: "F      S     : New"
                if not filing_status:
                    status_match = re.search(r'F\s+S\s*:\s*(.+)', prev_line, re.IGNORECASE)
                    if status_match:
                        filing_status = status_match.group(1).strip()

            # Determine asset owner
            if specific_owner:
                # Check if it's a trust or specific ownership
                owner_text = specific_owner.lower()
                if 'trust' in owner_text or 'sp' in owner_text:
                    asset_owner = "SPOUSE"
                elif 'joint' in owner_text or 'jt' in owner_text:
                    asset_owner = "JOINT"
                elif 'dependent' in owner_text or 'dep' in owner_text or 'dc' in owner_text:
                    asset_owner = "DEPENDENT"
                else:
                    asset_owner = "SELF"
            else:
                asset_owner = "SELF"

            # Resolve ticker if not explicit
            ticker = explicit_ticker
            ticker_confidence = 1.0 if explicit_ticker else 0.0

            if not ticker and asset_name:
                ticker, ticker_confidence = self.ticker_resolver.resolve(asset_name)

            # Build transaction record
            transaction = {
                "ticker": ticker,
                "ticker_confidence_score": ticker_confidence,
                "asset_name": asset_name,
                "asset_type_code": asset_type_code,
                "asset_type": asset_type_desc,
                "transaction_type": transaction_type,
                "transaction_date": transaction_date,
                "notification_date": notification_date,
                "asset_owner": asset_owner,
                "specific_owner_text": specific_owner,

                # Value information
                "value_low": value_data["value_low"],
                "value_high": value_data["value_high"],
                "is_range": value_data["is_range"],

                # Filing metadata
                "filer_id": filing_metadata.get("filer_id"),
                "filing_date": filing_metadata.get("filing_date"),
                "filing_status": filing_status,

                # Raw data for debugging
                "raw_text": line[:500],
                "validation_flags": {},
            }

            transactions.append(transaction)
            logger.debug(f"Extracted transaction: {asset_name} ({ticker}) - {transaction_type} - {amount_str}")

            i += 1

        logger.info(f"Extracted {len(transactions)} enhanced transactions from PDF")
        return transactions

    def _extract_capital_gains_section(self, pdf_text: str, filing_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Extract capital gains data from House disclosure PDF.

        Args:
            pdf_text: Full text extracted from PDF
            filing_metadata: Optional metadata

        Returns:
            List of capital gain dictionaries
        """
        capital_gains = []
        filing_metadata = filing_metadata or {}

        # Look for capital gains section (often in Part III or separate schedule)
        cg_patterns = [
            r'CAPITAL\s+GAINS',
            r'PART\s+III[:\s]',
            r'SCHEDULE\s+[A-Z].*GAINS',
        ]

        cg_match = None
        for pattern in cg_patterns:
            cg_match = re.search(pattern, pdf_text, re.IGNORECASE)
            if cg_match:
                break

        if not cg_match:
            logger.debug("No capital gains section found in PDF")
            return capital_gains

        # Extract relevant section
        search_text = pdf_text[cg_match.end():]
        # Stop at next major section
        next_section = re.search(r'PART\s+(?:IV|V|4|5)[:\s]', search_text, re.IGNORECASE)
        if next_section:
            search_text = search_text[:next_section.start()]

        # Parse each line looking for gain entries
        lines = search_text.split("\n")

        for line in lines:
            # Look for patterns indicating a capital gain entry
            # Typically: Asset name, date acquired, date sold, gain type, amount

            # Extract asset name
            asset_name = None
            words = line.split()
            if len(words) >= 3:
                # Heuristic: first few words are asset name
                asset_name = " ".join(words[:4])

            # Extract dates
            date_pattern = r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b'
            dates = re.findall(date_pattern, line)
            date_acquired = None
            date_sold = None
            if len(dates) >= 2:
                try:
                    date_acquired = datetime(int(dates[0][2]), int(dates[0][0]), int(dates[0][1]))
                    date_sold = datetime(int(dates[1][2]), int(dates[1][0]), int(dates[1][1]))
                except (ValueError, IndexError):
                    pass

            # Extract gain type (short-term vs long-term)
            gain_type = None
            if re.search(r'SHORT[- ]TERM', line, re.IGNORECASE):
                gain_type = "SHORT_TERM"
            elif re.search(r'LONG[- ]TERM', line, re.IGNORECASE):
                gain_type = "LONG_TERM"

            # Extract gain amount
            value_data = ValueRangeParser.parse(line)
            gain_amount = value_data["midpoint"]

            # Extract ticker if present
            ticker = extract_ticker_from_text(line)

            # Only add if we have meaningful data
            if asset_name and (date_sold or gain_amount):
                capital_gain = {
                    "asset_name": asset_name,
                    "asset_ticker": ticker,
                    "date_acquired": date_acquired,
                    "date_sold": date_sold,
                    "gain_type": gain_type,
                    "gain_amount": gain_amount,
                    "asset_owner": OwnerParser.parse(line),
                    "raw_data": {"raw_text": line[:500]},
                }
                capital_gains.append(capital_gain)

        logger.info(f"Extracted {len(capital_gains)} capital gains")
        return capital_gains

    def _extract_asset_holdings_section(self, pdf_text: str, filing_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Extract Part V: Assets and Unearned Income data from House disclosure PDF.

        Args:
            pdf_text: Full text extracted from PDF
            filing_metadata: Optional metadata

        Returns:
            List of asset holding dictionaries
        """
        holdings = []
        filing_metadata = filing_metadata or {}

        # Look for Part V section
        part_v_match = re.search(r'PART\s+V[:\s]|PART\s+5[:\s]', pdf_text, re.IGNORECASE)
        if not part_v_match:
            logger.debug("No Part V section found in PDF")
            return holdings

        # Extract relevant section
        search_text = pdf_text[part_v_match.end():]
        # Stop at next major section (Part VI)
        next_section = re.search(r'PART\s+(?:VI|6)[:\s]', search_text, re.IGNORECASE)
        if next_section:
            search_text = search_text[:next_section.start()]

        # Split into asset blocks
        sections = search_text.split("\n\n")

        for section in sections:
            line = section.replace("\r", "").replace("\n", " ")

            # Extract asset name (usually first significant words)
            words = line.split()
            if len(words) < 2:
                continue

            asset_name = " ".join(words[:6])  # Take first few words

            # Extract asset type code (e.g., [ST], [BA], [OT])
            asset_type = None
            type_match = re.search(r'\[([A-Z]{2,3})\]', line)
            if type_match:
                asset_type = type_match.group(1)

            # Extract ticker
            ticker = extract_ticker_from_text(line)

            # If no explicit ticker, try to resolve
            ticker_confidence = 1.0 if ticker else 0.0
            if not ticker:
                ticker, ticker_confidence = self.ticker_resolver.resolve(asset_name)

            # Parse value range
            value_data = ValueRangeParser.parse(line)

            # Parse owner
            owner = OwnerParser.parse(line)

            # Extract income information
            # Look for income type indicators
            income_type = None
            if re.search(r'DIVIDEND|DIV', line, re.IGNORECASE):
                income_type = "Dividends"
            elif re.search(r'INTEREST|INT', line, re.IGNORECASE):
                income_type = "Interest"
            elif re.search(r'RENT', line, re.IGNORECASE):
                income_type = "Rent"
            elif re.search(r'CAPITAL GAIN', line, re.IGNORECASE):
                income_type = "Capital Gains"

            # Only add if we have an asset name
            if asset_name and asset_name.strip():
                holding = {
                    "asset_name": asset_name.strip(),
                    "asset_type": asset_type,
                    "asset_ticker": ticker,
                    "owner": owner,
                    "value_low": value_data["value_low"],
                    "value_high": value_data["value_high"],
                    "value_category": value_data["original_text"] if value_data["is_range"] else None,
                    "income_type": income_type,
                    "filing_date": filing_metadata.get("filing_date"),
                    "filing_doc_id": filing_metadata.get("doc_id"),
                    "raw_data": {
                        "raw_text": line[:500],
                        "ticker_confidence_score": ticker_confidence,
                    },
                }
                holdings.append(holding)

        logger.info(f"Extracted {len(holdings)} asset holdings from Part V")
        return holdings

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats from disclosure sites"""
        if not date_str:
            return None

        date_formats = ["%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%B %d, %Y"]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_str}")
        return None


class QuiverQuantScraper(BaseScraper):
    """Scraper for QuiverQuant congress trading data as a backup source"""

    async def scrape_congress_trades(self) -> List[Dict[str, Any]]:
        """Scrape congress trading data from QuiverQuant"""
        trades = []

        try:
            # This would implement scraping from QuiverQuant's public data
            # Note: Respect their robots.txt and terms of service
            logger.info("Starting QuiverQuant scrape")

            url = "https://www.quiverquant.com/congresstrading/"
            html = await self.fetch_page(url)

            if html:
                # Log response details for debugging
                logger.debug(f"QuiverQuant page HTML preview: {html[:1000]}")
                logger.debug(f"QuiverQuant page HTML length: {len(html)} bytes")

                soup = BeautifulSoup(html, "html.parser")

                # Parse the trading data table (simplified example)
                # In reality, this might require handling JavaScript rendering
                trade_rows = soup.select("table tr")

                logger.debug(f"QuiverQuant found {len(trade_rows)} table rows")

                # Check if the page requires JavaScript
                if "javascript" in html.lower() and len(trade_rows) < 2:
                    logger.warning("QuiverQuant page appears to require JavaScript rendering")

                # Filter out header rows and empty rows
                for idx, row in enumerate(trade_rows):
                    cells = row.select("td")
                    # Skip rows with no td elements (likely header rows with th elements)
                    if len(cells) < 3:
                        continue

                    # Extract cell contents and try to identify the correct fields
                    cell_texts = [cell.get_text(strip=True) for cell in cells]

                    # Filter out empty rows
                    if not any(cell_texts):
                        continue

                    logger.debug(
                        f"QuiverQuant row {idx}: {len(cells)} cells, texts: {cell_texts[:5]}"
                    )

                    # Try to identify which cell contains what data
                    politician_name = cell_texts[0] if len(cell_texts) > 0 else ""

                    # Look for date-like patterns (YYYY-MM-DD, MM/DD/YYYY, etc.)
                    transaction_date = ""
                    ticker = ""
                    asset_name = ""
                    transaction_type = ""
                    amount = ""

                    for i, text in enumerate(
                        cell_texts[1:], 1
                    ):  # Skip first cell (politician name)
                        # Check if this looks like a date
                        if self._looks_like_date(text):
                            transaction_date = text
                        # Check if this looks like a ticker (all caps, short)
                        elif text.isupper() and len(text) <= 5 and text.isalpha():
                            ticker = text
                        # Check if this looks like a company name (has mixed case, contains "Inc", "Corp", "Ltd", etc.)
                        elif any(
                            word in text
                            for word in ["Inc", "Corp", "Ltd", "LLC", "Corporation", "Company"]
                        ):
                            asset_name = text
                        # Check if this contains transaction type keywords
                        elif any(
                            word in text.lower() for word in ["purchase", "sale", "buy", "sell"]
                        ):
                            # Split transaction type and amount if combined
                            if "$" in text:
                                # Split on $ to separate transaction type from amount
                                parts = text.split("$", 1)
                                transaction_type = parts[0].strip()
                                amount = "$" + parts[1] if len(parts) > 1 else ""
                            else:
                                transaction_type = text
                        # Check if this looks like an amount (contains $ or numbers with ,)
                        elif "$" in text or ("," in text and any(c.isdigit() for c in text)):
                            amount = text
                        # If not identified as anything else and has mixed case, might be asset name
                        elif text and not text.isupper() and not text.islower() and len(text) > 6:
                            asset_name = text

                    # Only create trade data if we have essential fields
                    if politician_name and (transaction_date or ticker):
                        trade_data = {
                            "politician_name": politician_name,
                            "transaction_date": transaction_date,
                            "ticker": ticker,
                            "asset_name": asset_name,
                            "transaction_type": transaction_type,
                            "amount": amount,
                            "source": "quiverquant",
                        }
                        trades.append(trade_data)

                    # Limit to prevent excessive data collection
                    if len(trades) >= 10:
                        logger.info("Reached limit of 10 trades, stopping")
                        break

        except Exception as e:
            logger.error(f"QuiverQuant scrape failed: {e}")

        return trades

    def _looks_like_date(self, text: str) -> bool:
        """Check if a string looks like a date"""
        if not text or len(text) < 8:
            return False

        # Common date patterns
        date_patterns = [
            r"\d{4}-\d{1,2}-\d{1,2}",  # YYYY-MM-DD
            r"\d{1,2}/\d{1,2}/\d{4}",  # MM/DD/YYYY
            r"\d{1,2}-\d{1,2}-\d{4}",  # MM-DD-YYYY
            r"\w{3}\s+\d{1,2},?\s+\d{4}",  # Month DD, YYYY
        ]

        import re

        for pattern in date_patterns:
            if re.search(pattern, text):
                return True
        return False

    def parse_quiver_trade(self, trade_data: Dict[str, Any]) -> Optional[TradingDisclosure]:
        """Parse QuiverQuant trade data into TradingDisclosure"""
        try:
            # Debug: Log the trade data structure
            logger.debug(f"Parsing QuiverQuant trade data: {trade_data}")
            # Parse transaction type
            transaction_type_map = {
                "purchase": TransactionType.PURCHASE,
                "sale": TransactionType.SALE,
                "buy": TransactionType.PURCHASE,
                "sell": TransactionType.SALE,
            }

            transaction_type = transaction_type_map.get(
                trade_data.get("transaction_type", "").lower(), TransactionType.PURCHASE
            )

            # Parse date
            date_str = trade_data.get("transaction_date", "")
            if not date_str or date_str.strip() == "" or not self._looks_like_date(date_str):
                # Use estimated date if no valid date found
                transaction_date = datetime.now() - timedelta(days=30)  # Estimate 30 days ago
            else:
                # Try multiple date formats
                try:
                    # Standard format
                    transaction_date = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    try:
                        # Alternative format
                        transaction_date = datetime.strptime(date_str, "%m/%d/%Y")
                    except ValueError:
                        try:
                            # Try MM-DD-YYYY
                            transaction_date = datetime.strptime(date_str, "%m-%d-%Y")
                        except ValueError:
                            logger.warning(
                                f"Could not parse date '{date_str}', using estimated date"
                            )
                            transaction_date = datetime.now() - timedelta(days=30)

            # Parse amount
            amount_min, amount_max, amount_exact = self.parse_amount_range(
                trade_data.get("amount", "")
            )

            # Get asset name and ticker - use separate fields if available
            asset_name = trade_data.get("asset_name", "")
            asset_ticker = trade_data.get("ticker", "")

            # If asset_name is empty, try to use ticker as fallback
            if not asset_name and asset_ticker:
                asset_name = asset_ticker

            disclosure = TradingDisclosure(
                politician_id="",  # Will be filled after politician matching
                transaction_date=transaction_date,
                disclosure_date=datetime.now(),  # QuiverQuant aggregation date
                transaction_type=transaction_type,
                asset_name=asset_name,
                asset_ticker=asset_ticker,
                asset_type="stock",
                amount_range_min=amount_min,
                amount_range_max=amount_max,
                amount_exact=amount_exact,
                source_url="https://www.quiverquant.com/congresstrading/",
                raw_data=trade_data,
            )

            return disclosure

        except Exception as e:
            logger.error(f"Failed to parse QuiverQuant trade: {e}")
            return None


class EUParliamentScraper(BaseScraper):
    """Scraper for EU Parliament member declarations"""

    async def scrape_mep_declarations(self) -> List[TradingDisclosure]:
        """Scrape MEP financial declarations from official EU Parliament site"""
        disclosures = []

        try:
            logger.info("Starting EU Parliament MEP declarations scrape")
            base_url = "https://www.europarl.europa.eu"

            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                headers={"User-Agent": self.config.user_agent},
            ) as session:
                # Get list of current MEPs
                mep_list_url = f"{base_url}/meps/en/full-list/all"

                async with session.get(mep_list_url) as response:
                    if response.status == 200:
                        html = await response.text()
                        mep_data = await self._extract_mep_urls(html, base_url)
                        logger.info(f"Found {len(mep_data)} MEP profiles to check")

                        # Check declarations for a subset of MEPs (to avoid overwhelming the server)
                        for i, mep_info in enumerate(mep_data[:50]):  # Limit to 50 MEPs
                            try:
                                mep_disclosures = await self._scrape_mep_profile(
                                    session, mep_info["url"], mep_info
                                )
                                disclosures.extend(mep_disclosures)

                                # Rate limiting - EU Parliament is more sensitive
                                await asyncio.sleep(self.config.request_delay * 2)

                                if i > 0 and i % 10 == 0:
                                    logger.info(f"Processed {i} MEP profiles")

                            except Exception as e:
                                logger.warning(
                                    f"Failed to process MEP profile {mep_info['url']}: {e}"
                                )
                                continue
                    else:
                        logger.warning(f"Failed to access MEP list: {response.status}")

                logger.info(f"Collected {len(disclosures)} EU Parliament disclosures")

        except Exception as e:
            logger.error(f"EU Parliament scrape failed: {e}")

        return disclosures

    async def _extract_mep_urls(self, html: str, base_url: str) -> List[Dict[str, str]]:
        """Extract MEP profile URLs and names from the MEP list page"""
        mep_data = []

        try:
            soup = BeautifulSoup(html, "html.parser")

            # Look for MEP profile links - they usually contain both name and link
            mep_links = soup.find_all("a", href=True)

            seen_urls = set()

            for link in mep_links:
                href = link.get("href", "")
                if "/meps/en/" in href and "/home" in href:
                    full_url = urljoin(base_url, href)

                    if full_url not in seen_urls:
                        # Extract MEP name from link text or nearby elements
                        mep_name = ""

                        # Try to get name from link text
                        link_text = link.get_text(strip=True)
                        if (
                            link_text
                            and len(link_text) > 3
                            and not link_text.lower().startswith("http")
                        ):
                            mep_name = link_text

                        # If no name in link, look in parent elements
                        if not mep_name:
                            parent = link.parent
                            if parent:
                                # Look for text that looks like a name
                                for text_node in parent.stripped_strings:
                                    if (
                                        len(text_node) > 3
                                        and " " in text_node
                                        and not text_node.startswith("http")
                                        and not text_node.isdigit()
                                    ):
                                        mep_name = text_node
                                        break

                        # Extract country/party info if available
                        country = ""
                        party = ""

                        # Look for country and party info near the link
                        container = link.find_parent(["div", "article", "section"])
                        if container:
                            text_elements = list(container.stripped_strings)
                            for i, text in enumerate(text_elements):
                                if text == mep_name and i < len(text_elements) - 2:
                                    # Country and party usually come after name
                                    country = (
                                        text_elements[i + 1] if i + 1 < len(text_elements) else ""
                                    )
                                    party = (
                                        text_elements[i + 2] if i + 2 < len(text_elements) else ""
                                    )

                        if mep_name:  # Only add if we found a name
                            mep_data.append(
                                {
                                    "url": full_url,
                                    "name": mep_name,
                                    "country": country,
                                    "party": party,
                                }
                            )
                            seen_urls.add(full_url)

                            # Limit to prevent overwhelming the servers
                            if len(mep_data) >= 50:
                                break

        except Exception as e:
            logger.error(f"Error extracting MEP data: {e}")

        return mep_data

    async def _scrape_mep_profile(
        self, session: aiohttp.ClientSession, mep_url: str, mep_info: Dict[str, str] = None
    ) -> List[TradingDisclosure]:
        """Scrape financial interests from an individual MEP profile"""
        disclosures = []

        try:
            async with session.get(mep_url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    # Use extracted MEP name from list, or try to extract from profile
                    if mep_info and mep_info.get("name"):
                        mep_name = mep_info["name"]
                        mep_country = mep_info.get("country", "")
                        mep_party = mep_info.get("party", "")
                    else:
                        # Fallback: extract from profile page
                        name_element = soup.find("h1", class_="ep-header-title")
                        mep_name = (
                            name_element.get_text(strip=True) if name_element else "Unknown MEP"
                        )
                        mep_country = ""
                        mep_party = ""

                    # Look for financial interests section
                    # EU Parliament declarations are typically in a specific section
                    interests_section = (
                        soup.find("div", id="financial-interests")
                        or soup.find("section", class_="ep-a-section")
                        or soup.find("div", class_="ep-m-content-block")
                    )

                    if interests_section:
                        # Parse financial interests
                        # Note: EU declarations focus more on activities and interests than specific trades
                        interest_items = interests_section.find_all(
                            ["p", "li", "div"], recursive=True
                        )

                        for item in interest_items:
                            item_text = item.get_text(strip=True).lower()

                            # Look for financial keywords
                            if any(
                                keyword in item_text
                                for keyword in [
                                    "shareholding",
                                    "investment",
                                    "director",
                                    "board",
                                    "financial interest",
                                    "remuneration",
                                    "consulting",
                                ]
                            ):
                                # Create disclosure for detected financial interest
                                disclosure = TradingDisclosure(
                                    politician_id="",  # To be filled by matcher
                                    transaction_date=datetime.now()
                                    - timedelta(days=90),  # Estimate
                                    disclosure_date=datetime.now() - timedelta(days=60),  # Estimate
                                    transaction_type=TransactionType.PURCHASE,  # Default for interests
                                    asset_name=self._extract_company_name(item_text),
                                    asset_type="interest",
                                    amount_range_min=Decimal(
                                        "0"
                                    ),  # EU doesn't always specify amounts
                                    amount_range_max=Decimal("0"),
                                    source_url=mep_url,
                                    raw_data={
                                        "politician_name": mep_name,
                                        "country": mep_country,
                                        "party": mep_party,
                                        "interest_type": "financial_activity",
                                        "interest_description": item.get_text(strip=True)[
                                            :500
                                        ],  # Truncate
                                        "region": "eu",
                                        "extraction_method": "mep_profile_scraping",
                                        "requires_manual_review": True,
                                    },
                                )
                                disclosures.append(disclosure)

        except Exception as e:
            logger.warning(f"Error scraping MEP profile {mep_url}: {e}")

        return disclosures

    def _extract_company_name(self, text: str) -> str:
        """Extract company/organization name from interest description"""
        # Simple heuristic to extract potential company names
        words = text.split()

        # Look for capitalized sequences that might be company names
        potential_names = []
        current_name = []

        for word in words:
            if word[0].isupper() and len(word) > 2:
                current_name.append(word)
            else:
                if current_name and len(current_name) <= 4:  # Reasonable company name length
                    potential_names.append(" ".join(current_name))
                current_name = []

        if current_name and len(current_name) <= 4:
            potential_names.append(" ".join(current_name))

        # Return the first reasonable candidate or default
        return potential_names[0] if potential_names else "Financial Interest"


class PoliticianMatcher:
    """Matches scraped names to politician records"""

    def __init__(self, politicians: List[Politician]):
        self.politicians = politicians
        self._build_lookup()

    def _build_lookup(self):
        """Build lookup dictionaries for fast matching"""
        self.name_lookup = {}
        self.bioguide_lookup = {}

        for politician in self.politicians:
            # Full name variations
            full_name = politician.full_name.lower()
            self.name_lookup[full_name] = politician

            # Last, First format
            if politician.first_name and politician.last_name:
                last_first = f"{politician.last_name.lower()}, {politician.first_name.lower()}"
                self.name_lookup[last_first] = politician

                # First Last format
                first_last = f"{politician.first_name.lower()} {politician.last_name.lower()}"
                self.name_lookup[first_last] = politician

            # Bioguide ID lookup
            if politician.bioguide_id:
                self.bioguide_lookup[politician.bioguide_id] = politician

    def find_politician(self, name: str, bioguide_id: str = None) -> Optional[Politician]:
        """Find politician by name or bioguide ID"""
        if bioguide_id and bioguide_id in self.bioguide_lookup:
            return self.bioguide_lookup[bioguide_id]

        if name:
            name_clean = name.lower().strip()

            # Direct match
            if name_clean in self.name_lookup:
                return self.name_lookup[name_clean]

            # Fuzzy matching (simplified)
            for lookup_name, politician in self.name_lookup.items():
                if self._names_similar(name_clean, lookup_name):
                    return politician

        return None

    def add_politician(self, politician: Politician):
        """Add a newly created politician to the matcher's cache"""
        # Add to politicians list
        self.politicians.append(politician)

        # Add to name lookup
        full_name = politician.full_name.lower()
        self.name_lookup[full_name] = politician

        # Last, First format
        if politician.first_name and politician.last_name:
            last_first = f"{politician.last_name.lower()}, {politician.first_name.lower()}"
            self.name_lookup[last_first] = politician

            # First Last format
            first_last = f"{politician.first_name.lower()} {politician.last_name.lower()}"
            self.name_lookup[first_last] = politician

        # Bioguide ID lookup
        if politician.bioguide_id:
            self.bioguide_lookup[politician.bioguide_id] = politician

    def _names_similar(self, name1: str, name2: str) -> bool:
        """Simple similarity check for names"""
        # Remove common prefixes/suffixes
        prefixes = ["rep.", "sen.", "senator", "representative", "mr.", "mrs.", "ms."]
        suffixes = ["jr.", "sr.", "ii", "iii", "iv"]

        for prefix in prefixes:
            name1 = name1.replace(prefix, "").strip()
            name2 = name2.replace(prefix, "").strip()

        for suffix in suffixes:
            name1 = name1.replace(suffix, "").strip()
            name2 = name2.replace(suffix, "").strip()

        # Check if one name contains the other
        return name1 in name2 or name2 in name1


# Import specialized scrapers after base classes are defined
try:
    from .scrapers_uk import UKParliamentScraper, run_uk_parliament_collection

    UK_SCRAPER_AVAILABLE = True
except Exception as e:
    logger.debug(f"UK scraper import failed: {e}")
    UKParliamentScraper = None
    run_uk_parliament_collection = None
    UK_SCRAPER_AVAILABLE = False

try:
    from .scrapers_california import CaliforniaNetFileScraper, run_california_collection

    CALIFORNIA_SCRAPER_AVAILABLE = True
except Exception as e:
    logger.debug(f"California scraper import failed: {e}")
    CaliforniaNetFileScraper = None
    run_california_collection = None
    CALIFORNIA_SCRAPER_AVAILABLE = False

try:
    from .scrapers_eu import EUMemberStatesScraper, run_eu_member_states_collection

    EU_MEMBER_STATES_SCRAPER_AVAILABLE = True
except Exception as e:
    logger.debug(f"EU member states scraper import failed: {e}")
    EUMemberStatesScraper = None
    run_eu_member_states_collection = None
    EU_MEMBER_STATES_SCRAPER_AVAILABLE = False

try:
    from .scrapers_us_states import USStatesScraper, run_us_states_collection

    US_STATES_SCRAPER_AVAILABLE = True
except Exception as e:
    logger.debug(f"US states scraper import failed: {e}")
    USStatesScraper = None
    run_us_states_collection = None
    US_STATES_SCRAPER_AVAILABLE = False


# Workflow functions using imported scrapers
async def run_uk_parliament_workflow(config: ScrapingConfig) -> List[TradingDisclosure]:
    """Run UK Parliament data collection workflow"""
    if not UK_SCRAPER_AVAILABLE:
        logger.warning("UK Parliament scraper not available")
        return []

    logger.info("Starting UK Parliament financial interests collection")
    try:
        disclosures = await run_uk_parliament_collection(config)
        logger.info(f"Successfully collected {len(disclosures)} UK Parliament disclosures")
        return disclosures
    except Exception as e:
        logger.error(f"UK Parliament collection failed: {e}")
        return []


async def run_california_workflow(config: ScrapingConfig) -> List[TradingDisclosure]:
    """Run California NetFile and state disclosure collection workflow"""
    if not CALIFORNIA_SCRAPER_AVAILABLE:
        logger.warning("California scraper not available")
        return []

    logger.info("Starting California financial disclosures collection")
    try:
        disclosures = await run_california_collection(config)
        logger.info(f"Successfully collected {len(disclosures)} California disclosures")
        return disclosures
    except Exception as e:
        logger.error(f"California collection failed: {e}")
        return []


async def run_eu_member_states_workflow(config: ScrapingConfig) -> List[TradingDisclosure]:
    """Run EU member states financial disclosure collection workflow"""
    if not EU_MEMBER_STATES_SCRAPER_AVAILABLE:
        logger.warning("EU member states scraper not available")
        return []

    logger.info("Starting EU member states financial disclosures collection")
    try:
        disclosures = await run_eu_member_states_collection(config)
        logger.info(f"Successfully collected {len(disclosures)} EU member states disclosures")
        return disclosures
    except Exception as e:
        logger.error(f"EU member states collection failed: {e}")
        return []


async def run_us_states_workflow(config: ScrapingConfig) -> List[TradingDisclosure]:
    """Run US states financial disclosure collection workflow"""
    if not US_STATES_SCRAPER_AVAILABLE:
        logger.warning("US states scraper not available")
        return []

    logger.info("Starting US states financial disclosures collection")
    try:
        disclosures = await run_us_states_collection(config)
        logger.info(f"Successfully collected {len(disclosures)} US states disclosures")
        return disclosures
    except Exception as e:
        logger.error(f"US states collection failed: {e}")
        return []


# Export the new workflow function
__all__ = [
    "BaseScraper",
    "CongressTradingScraper",
    "QuiverQuantScraper",
    "EUParliamentScraper",
    "PoliticianMatcher",
    "run_uk_parliament_workflow",
    "run_california_workflow",
    "run_eu_member_states_workflow",
    "run_us_states_workflow",
]
