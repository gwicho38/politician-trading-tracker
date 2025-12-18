"""
US House of Representatives Financial Disclosure Scraper.

This module provides the HouseDisclosureScraper class for downloading and parsing
financial disclosure data from the US House of Representatives.

ETL Pipeline Overview
=====================

EXTRACT Phase:
- download_index(year, config) - Download and parse yearly disclosure index
- fetch_pdf(session, pdf_url) - Download individual PDF disclosures

TRANSFORM Phase:
- parse_disclosure_index() - Parse index into structured records
- parse_pdf_disclosure() - Extract transactions from PDFs using pdfplumber

LOAD Phase:
- save_disclosures() - Save to local JSON
- upload_parsed_disclosures_to_supabase() - Upload to Supabase database
"""

import asyncio
import io
import json
import logging
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from ..config import ScrapingConfig, SupabaseConfig
from ..constants.urls import WebUrls
from ..parsers.pdf_utils import (
    ASSET_TYPE_CODES,
    OwnerParser,
    ValueRangeParser,
    extract_ticker_from_text,
    parse_asset_type,
)

# Optional pdfplumber dependency
try:
    import pdfplumber

    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    pdfplumber = None

# Optional Supabase dependency
try:
    from supabase import Client, create_client

    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None
    create_client = None

logger = logging.getLogger(__name__)


@dataclass
class SupabaseUploadStats:
    """Statistics for Supabase upload operation."""

    politicians_created: int = 0
    politicians_matched: int = 0
    disclosures_inserted: int = 0
    disclosures_skipped: int = 0
    disclosures_failed: int = 0
    errors: List[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"Politicians: {self.politicians_created} created, {self.politicians_matched} matched | "
            f"Disclosures: {self.disclosures_inserted} inserted, {self.disclosures_skipped} skipped, "
            f"{self.disclosures_failed} failed"
        )


class HouseDisclosureScraper:
    """
    Static class for scraping US House financial disclosure data.

    Filing Types
    ============
    - P: Periodic Transaction Report (PTR) - Stock trades within 45 days
    - A: Annual Financial Disclosure
    - C: Candidate/New Member Report
    - O: Original/Initial Report
    - T: Termination Report
    - D: Due Date Extension
    - X: Amendment
    - W: Waiver

    PDF URL Patterns
    ================
    - PTR filings (type 'P'): /public_disc/ptr-pdfs/{year}/{doc_id}.pdf
    - All other filings: /public_disc/financial-pdfs/{year}/{doc_id}.pdf
    """

    # Constants
    DATE_FORMAT = "%m/%d/%Y"
    INDEX_FILENAME_TEMPLATE = "{year}FD.txt"
    ZIP_URL_TEMPLATE = "{base_url}/public_disc/financial-pdfs/{year}FD.ZIP"
    PDF_URL_TEMPLATE = "{base_url}/public_disc/financial-pdfs/{year}/{doc_id}.pdf"
    PTR_PDF_URL_TEMPLATE = "{base_url}/public_disc/ptr-pdfs/{year}/{doc_id}.pdf"
    SOURCE_NAME = "us_house"
    MIN_FIELDS_COUNT = 9

    # =========================================================================
    # EXTRACT PHASE - URL Building
    # =========================================================================

    @staticmethod
    def get_base_url() -> str:
        """Get the base URL for House disclosures."""
        return WebUrls.HOUSE_CLERK_DISCLOSURES

    @staticmethod
    def get_zip_url(year: int) -> str:
        """Get the ZIP file URL for a given year."""
        return HouseDisclosureScraper.ZIP_URL_TEMPLATE.format(
            base_url=HouseDisclosureScraper.get_base_url(), year=year
        )

    @staticmethod
    def get_pdf_url(year: int, doc_id: str, filing_type: str = "") -> str:
        """
        Get the PDF URL for a specific disclosure document.

        Args:
            year: Filing year
            doc_id: Document ID from the index
            filing_type: Filing type code ('P' for PTR uses different path)

        Returns:
            Full URL to the PDF document

        Note:
            PTR filings (type 'P') use /ptr-pdfs/ directory
            All other filings use /financial-pdfs/ directory
        """
        if filing_type == "P":
            return HouseDisclosureScraper.PTR_PDF_URL_TEMPLATE.format(
                base_url=HouseDisclosureScraper.get_base_url(), year=year, doc_id=doc_id
            )
        return HouseDisclosureScraper.PDF_URL_TEMPLATE.format(
            base_url=HouseDisclosureScraper.get_base_url(), year=year, doc_id=doc_id
        )

    # =========================================================================
    # EXTRACT PHASE - Data Fetching
    # =========================================================================

    @staticmethod
    async def fetch_zip_content(
        session: aiohttp.ClientSession, url: str
    ) -> Optional[bytes]:
        """Download ZIP file content from URL."""
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Failed to download: {response.status}")
                    return None

                content = await response.read()
                logger.info(f"Downloaded {len(content):,} bytes")
                return content
        except Exception as e:
            logger.error(f"Error downloading ZIP: {e}")
            return None

    @staticmethod
    async def fetch_pdf(
        session: aiohttp.ClientSession, pdf_url: str
    ) -> Optional[bytes]:
        """Download a PDF document."""
        try:
            async with session.get(pdf_url) as response:
                if response.status != 200:
                    logger.error(f"Failed to download PDF: {response.status} - {pdf_url}")
                    return None

                content = await response.read()

                # Verify it's actually a PDF
                if not content.startswith(b"%PDF"):
                    logger.error(f"Downloaded content is not a valid PDF: {pdf_url}")
                    return None

                logger.debug(f"Downloaded PDF: {len(content):,} bytes")
                return content
        except Exception as e:
            logger.error(f"Error downloading PDF: {e}")
            return None

    @staticmethod
    def extract_index_file(zip_content: bytes, year: int) -> Optional[str]:
        """Extract the disclosure index text file from ZIP content."""
        txt_filename = HouseDisclosureScraper.INDEX_FILENAME_TEMPLATE.format(year=year)

        try:
            with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
                if txt_filename not in z.namelist():
                    logger.error(f"Index file {txt_filename} not found in ZIP")
                    return None

                with z.open(txt_filename) as f:
                    return f.read().decode("utf-8", errors="ignore")
        except Exception as e:
            logger.error(f"Error extracting index file: {e}")
            return None

    # =========================================================================
    # TRANSFORM PHASE - Data Parsing
    # =========================================================================

    @staticmethod
    def parse_filing_date(date_str: str) -> Optional[str]:
        """Parse a filing date string to ISO format."""
        if not date_str:
            return None
        try:
            return datetime.strptime(
                date_str.strip(), HouseDisclosureScraper.DATE_FORMAT
            ).isoformat()
        except ValueError:
            return None

    @staticmethod
    def build_full_name(
        prefix: str, first_name: str, last_name: str, suffix: str
    ) -> str:
        """Build a full name from component parts."""
        name_parts = [
            p.strip() for p in [prefix, first_name, last_name, suffix] if p.strip()
        ]
        return " ".join(name_parts)

    @staticmethod
    def parse_disclosure_record(
        line: str, year: int, base_url: str
    ) -> Optional[Dict[str, Any]]:
        """Parse a single disclosure record from tab-separated line."""
        fields = line.split("\t")
        if len(fields) < HouseDisclosureScraper.MIN_FIELDS_COUNT:
            return None

        prefix, last_name, first_name, suffix = fields[0:4]
        filing_type, state_district, file_year = fields[4:7]
        filing_date_str, doc_id = fields[7:9]

        doc_id = doc_id.strip()
        filing_type = filing_type.strip()
        if not doc_id or doc_id == "DocID":
            return None

        # Use correct URL template based on filing type
        pdf_url = HouseDisclosureScraper.get_pdf_url(year, doc_id, filing_type)

        return {
            "politician_name": HouseDisclosureScraper.build_full_name(
                prefix, first_name, last_name, suffix
            ),
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "state_district": state_district.strip(),
            "filing_type": filing_type,
            "filing_date": HouseDisclosureScraper.parse_filing_date(filing_date_str),
            "doc_id": doc_id,
            "pdf_url": pdf_url,
            "year": year,
            "source": HouseDisclosureScraper.SOURCE_NAME,
        }

    @staticmethod
    def parse_disclosure_index(
        content: str, year: int, base_url: str
    ) -> List[Dict[str, Any]]:
        """Parse all disclosure records from index file content."""
        lines = content.strip().split("\n")
        logger.info(f"Found {len(lines)} records in index")

        disclosures = []
        for line in lines[1:]:  # Skip header
            record = HouseDisclosureScraper.parse_disclosure_record(line, year, base_url)
            if record:
                disclosures.append(record)

        return disclosures

    @staticmethod
    def compute_filing_statistics(disclosures: List[Dict[str, Any]]) -> Dict[str, int]:
        """Compute filing type statistics from disclosures."""
        filing_types: Dict[str, int] = {}
        for d in disclosures:
            ft = d.get("filing_type", "Unknown")
            filing_types[ft] = filing_types.get(ft, 0) + 1
        return filing_types

    # =========================================================================
    # LOAD PHASE - Data Persistence
    # =========================================================================

    @staticmethod
    def save_disclosures(
        disclosures: List[Dict[str, Any]],
        output_file: Path,
        year: int,
        filing_types: Dict[str, int],
    ) -> None:
        """Save disclosures to JSON file with metadata."""
        with open(output_file, "w") as f:
            json.dump(
                {
                    "metadata": {
                        "source": HouseDisclosureScraper.SOURCE_NAME,
                        "year": year,
                        "downloaded_at": datetime.now().isoformat(),
                        "total_records": len(disclosures),
                        "filing_types": filing_types,
                    },
                    "disclosures": disclosures,
                },
                f,
                indent=2,
            )

    @staticmethod
    def load_disclosures(input_file: Path) -> Optional[Dict[str, Any]]:
        """Load disclosures from JSON file."""
        if not input_file.exists():
            return None
        with open(input_file) as f:
            return json.load(f)

    # =========================================================================
    # HIGH-LEVEL ORCHESTRATORS
    # =========================================================================

    @staticmethod
    async def download_index(
        year: int, config: ScrapingConfig
    ) -> List[Dict[str, Any]]:
        """
        Download and parse the House disclosure index file.

        This is a high-level method that combines:
        1. fetch_zip_content() - Download the ZIP
        2. extract_index_file() - Extract the index text
        3. parse_disclosure_index() - Parse into records
        """
        base_url = HouseDisclosureScraper.get_base_url()
        zip_url = HouseDisclosureScraper.get_zip_url(year)

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=config.timeout * 2),
            headers={"User-Agent": config.user_agent},
        ) as session:
            logger.info(f"Downloading House disclosure index for {year}...")

            zip_content = await HouseDisclosureScraper.fetch_zip_content(
                session, zip_url
            )
            if not zip_content:
                return []

            index_content = HouseDisclosureScraper.extract_index_file(zip_content, year)
            if not index_content:
                return []

            return HouseDisclosureScraper.parse_disclosure_index(
                index_content, year, base_url
            )


# =============================================================================
# FILING TYPE CONSTANTS
# =============================================================================

# Filing types that contain financial/trading data worth parsing
PARSEABLE_FILING_TYPES = {"P", "A", "B", "C", "H", "T"}

# Filing types to skip (no financial data)
SKIP_FILING_TYPES = {"D", "E", "G", "O", "W", "X"}


# =============================================================================
# PDF PARSING FUNCTIONS
# =============================================================================


def extract_text_from_pdf(pdf_bytes: bytes) -> Optional[str]:
    """Extract all text from a PDF file."""
    if not PDFPLUMBER_AVAILABLE:
        logger.error("pdfplumber not available")
        return None

    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            text_parts = [
                page.extract_text() for page in pdf.pages if page.extract_text()
            ]
            return "\n".join(text_parts) if text_parts else None
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {e}")
        return None


def extract_tables_from_pdf(pdf_bytes: bytes) -> List[List[List[str]]]:
    """Extract all tables from a PDF file."""
    if not PDFPLUMBER_AVAILABLE:
        return []

    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            return [
                table for page in pdf.pages for table in (page.extract_tables() or [])
            ]
    except Exception as e:
        logger.error(f"Failed to extract tables from PDF: {e}")
        return []


def is_header_row(row_text: str) -> bool:
    """Check if a row is a header row."""
    headers = ["asset", "owner", "value", "income", "description", "tx. type", "amount", "cap."]
    row_lower = row_text.lower()
    # Must match at least 2 header keywords to be considered a header
    matches = sum(1 for header in headers if header in row_lower)
    return matches >= 2


def is_empty_or_null_row(row: List[str]) -> bool:
    """Check if a row is empty or contains only null/None values."""
    if not row:
        return True
    # Check if all cells are empty, None, or just whitespace
    return all(
        cell is None or str(cell).strip() == "" or str(cell).strip() == "None"
        for cell in row
    )


def extract_asset_info(row: List[str]) -> Dict[str, Any]:
    """Extract asset name, ticker, and type from row."""
    result = {}
    for cell in row:
        if not cell or len(str(cell).strip()) <= 2:
            continue

        asset_text = str(cell).strip()
        # Skip if it looks like just an owner code or amount
        if asset_text.upper() in {"SP", "JT", "DC", "P", "S", "E"}:
            continue
        if asset_text.startswith("$"):
            continue

        result["asset_name"] = asset_text

        ticker = extract_ticker_from_text(asset_text)
        if ticker:
            result["asset_ticker"] = ticker

        asset_code, asset_desc = parse_asset_type(asset_text)
        if asset_code:
            result["asset_type_code"] = asset_code
            result["asset_type"] = asset_desc
        break

    return result


def extract_value_info(row: List[str]) -> Dict[str, Any]:
    """Extract value range information from row."""
    for cell in row:
        if not cell or "$" not in str(cell):
            continue

        value_info = ValueRangeParser.parse(str(cell))
        result = {}
        if value_info.get("value_low") is not None:
            result["value_low"] = float(value_info["value_low"])
        if value_info.get("value_high") is not None:
            result["value_high"] = float(value_info["value_high"])
        if value_info.get("midpoint") is not None:
            result["value_midpoint"] = float(value_info["midpoint"])
        return result

    return {}


def extract_owner_info(row: List[str]) -> Optional[str]:
    """Extract owner designation from row."""
    owner_codes = {"SP", "JT", "DC", "SELF", "SPOUSE", "JOINT", "DEPENDENT"}
    for cell in row:
        if cell and str(cell).strip().upper() in owner_codes:
            return OwnerParser.parse(str(cell).strip())
    return None


def extract_transaction_type_from_row(row: List[str]) -> Optional[str]:
    """Extract transaction type (P/S) from row for PTR filings."""
    for cell in row:
        if not cell:
            continue
        cell_text = str(cell).strip().upper()
        # Look for P (Purchase) or S (Sale) indicators
        if cell_text == "P" or cell_text.startswith("P\n") or "(partial)" in cell_text.lower():
            if "S" in cell_text.split("\n")[0] if "\n" in cell_text else cell_text == "S":
                return "sale"
            return "purchase"
        if cell_text == "S" or cell_text.startswith("S\n") or cell_text.startswith("S "):
            return "sale"

    return None


def extract_transaction_type(row_text: str) -> Optional[str]:
    """Extract transaction type from row text."""
    row_lower = row_text.lower()

    type_keywords = {
        "purchase": ["purchase", "bought", "buy", " p "],
        "sale": ["sale", "sold", "sell", " s "],
        "exchange": ["exchange", "swap"],
    }

    for txn_type, keywords in type_keywords.items():
        if any(kw in row_lower for kw in keywords):
            return txn_type
    return None


def extract_transaction_date(row: List[str]) -> Optional[str]:
    """Extract transaction date from row."""
    import re
    date_pattern = r"\b(\d{1,2}/\d{1,2}/\d{4})\b"

    for cell in row:
        if not cell:
            continue
        match = re.search(date_pattern, str(cell))
        if match:
            return match.group(1)
    return None


def parse_filer_info_from_text(text: str) -> Dict[str, Any]:
    """Extract filer information from PDF text."""
    import re
    filer_info = {}

    # Name pattern
    name_match = re.search(r"Name:\s*(.+?)(?:\n|Status:|$)", text, re.IGNORECASE)
    if name_match:
        filer_info["filer_name"] = name_match.group(1).strip()

    # Status pattern
    status_match = re.search(r"Status:\s*(.+?)(?:\n|State|$)", text, re.IGNORECASE)
    if status_match:
        filer_info["filer_status"] = status_match.group(1).strip()

    # State/District pattern
    state_match = re.search(r"State/District:\s*([A-Z]{2}\d*)", text, re.IGNORECASE)
    if state_match:
        filer_info["state_district"] = state_match.group(1).strip()

    # Filing Type pattern
    filing_type_match = re.search(r"Filing Type:\s*(.+?)(?:\n|Filing Year|$)", text, re.IGNORECASE)
    if filing_type_match:
        filer_info["filing_type_desc"] = filing_type_match.group(1).strip()

    # Filing Year pattern
    year_match = re.search(r"Filing Year:\s*(\d{4})", text, re.IGNORECASE)
    if year_match:
        filer_info["filing_year"] = year_match.group(1).strip()

    # Filing Date pattern
    date_match = re.search(r"Filing Date:\s*(\d{1,2}/\d{1,2}/\d{4})", text, re.IGNORECASE)
    if date_match:
        filer_info["filing_date"] = date_match.group(1).strip()

    return filer_info


def parse_ptr_transaction(row: List[str], disclosure: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse a PTR (Periodic Transaction Report) row.

    PTR format has columns: Asset | Owner | Date | Tx. Type | Amount | Cap. Gains > $200?
    """
    if not row or len(row) < 4:
        return None

    row_text = " ".join(str(cell) for cell in row if cell)
    if not row_text.strip() or is_header_row(row_text) or is_empty_or_null_row(row):
        return None

    asset_info = extract_asset_info(row)
    if "asset_name" not in asset_info:
        return None

    # Extract transaction-specific info
    tx_date = extract_transaction_date(row)
    tx_type = extract_transaction_type_from_row(row) or extract_transaction_type(row_text)
    value_info = extract_value_info(row)

    return {
        "politician_name": disclosure.get("politician_name"),
        "doc_id": disclosure.get("doc_id"),
        "filing_type": disclosure.get("filing_type"),
        "filing_date": disclosure.get("filing_date"),
        "source": "us_house",
        "schedule": "B",  # PTR transactions are Schedule B
        **asset_info,
        **value_info,
        "owner": extract_owner_info(row),
        "transaction_type": tx_type or "unknown",
        "transaction_date": tx_date,
        "raw_row": [str(c) if c else "" for c in row],
    }


def parse_schedule_a_asset(row: List[str], disclosure: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse a Schedule A (Assets) row for Financial Disclosure reports.

    Schedule A format has columns: Asset | Owner | Value of Asset | Income Type(s) | Income | Tx. > $1,000?
    """
    if not row or len(row) < 3:
        return None

    row_text = " ".join(str(cell) for cell in row if cell)
    if not row_text.strip() or is_header_row(row_text) or is_empty_or_null_row(row):
        return None

    asset_info = extract_asset_info(row)
    if "asset_name" not in asset_info:
        return None

    value_info = extract_value_info(row)

    # Extract income information if present
    income_info = {}
    for cell in row:
        if cell and any(kw in str(cell).lower() for kw in ["dividend", "interest", "capital gain", "tax-deferred"]):
            income_info["income_type"] = str(cell).strip()
            break

    return {
        "politician_name": disclosure.get("politician_name"),
        "doc_id": disclosure.get("doc_id"),
        "filing_type": disclosure.get("filing_type"),
        "filing_date": disclosure.get("filing_date"),
        "source": "us_house",
        "schedule": "A",  # Assets are Schedule A
        **asset_info,
        **value_info,
        **income_info,
        "owner": extract_owner_info(row),
        "transaction_type": "holding",  # Schedule A is holdings, not transactions
        "raw_row": [str(c) if c else "" for c in row],
    }


def parse_schedule_b_transaction(row: List[str], disclosure: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse a Schedule B (Transactions) row for Financial Disclosure reports.

    Schedule B format has columns: Asset | Owner | Date | Tx. Type | Amount | Cap. Gains > $200?
    """
    # Same as PTR format
    return parse_ptr_transaction(row, disclosure)


def parse_blind_trust_assets(text: str, disclosure: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse blind trust communication PDF which has a letter format with embedded asset tables.
    """
    import re
    transactions = []

    # Look for asset listings in the text
    # Pattern: asset name followed by value range
    asset_pattern = r"([A-Za-z][A-Za-z0-9\s\.,&'-]+(?:\([A-Z]{1,5}\))?(?:\s*\[[A-Z]{2,3}\])?)\s+(\$[\d,]+\s*-\s*\$[\d,]+|\$[\d,]+)"

    for match in re.finditer(asset_pattern, text):
        asset_name = match.group(1).strip()
        value_text = match.group(2).strip()

        # Skip if asset name is too short or looks like a header
        if len(asset_name) < 5:
            continue
        if any(kw in asset_name.lower() for kw in ["asset", "value", "amount", "description"]):
            continue

        value_info = ValueRangeParser.parse(value_text)

        ticker = extract_ticker_from_text(asset_name)
        asset_code, asset_desc = parse_asset_type(asset_name)

        transaction = {
            "politician_name": disclosure.get("politician_name"),
            "doc_id": disclosure.get("doc_id"),
            "filing_type": disclosure.get("filing_type"),
            "filing_date": disclosure.get("filing_date"),
            "source": "us_house",
            "schedule": "blind_trust",
            "asset_name": asset_name,
            "transaction_type": "holding",
        }

        if ticker:
            transaction["asset_ticker"] = ticker
        if asset_code:
            transaction["asset_type_code"] = asset_code
            transaction["asset_type"] = asset_desc
        if value_info.get("value_low") is not None:
            transaction["value_low"] = float(value_info["value_low"])
        if value_info.get("value_high") is not None:
            transaction["value_high"] = float(value_info["value_high"])
        if value_info.get("midpoint") is not None:
            transaction["value_midpoint"] = float(value_info["midpoint"])

        transactions.append(transaction)

    return transactions


def parse_transaction_from_row(
    row: List[str], disclosure: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Parse a transaction from a table row (generic fallback)."""
    if not row or len(row) < 3:
        return None

    row_text = " ".join(str(cell) for cell in row if cell)
    if not row_text.strip() or is_header_row(row_text) or is_empty_or_null_row(row):
        return None

    asset_info = extract_asset_info(row)
    if "asset_name" not in asset_info:
        return None

    return {
        "politician_name": disclosure.get("politician_name"),
        "doc_id": disclosure.get("doc_id"),
        "filing_type": disclosure.get("filing_type"),
        "filing_date": disclosure.get("filing_date"),
        "source": "us_house",
        **asset_info,
        **extract_value_info(row),
        "owner": extract_owner_info(row),
        "transaction_type": extract_transaction_type(row_text),
        "transaction_date": extract_transaction_date(row),
        "raw_row": [str(c) if c else "" for c in row],
    }


def detect_schedule_type(text: str) -> str:
    """Detect which schedule we're parsing based on text content."""
    text_lower = text.lower()
    if "schedule b:" in text_lower or "transactions" in text_lower:
        return "B"
    if "schedule a:" in text_lower or "assets" in text_lower:
        return "A"
    return "unknown"


def parse_pdf_by_filing_type(
    pdf_bytes: bytes, disclosure: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Parse PDF disclosure based on filing type.

    Filing types:
    - P: PTR (Periodic Transaction Report) - transaction-focused
    - A, C, H, T: Financial Disclosure Reports - Schedule A (assets) and optionally Schedule B
    - B: Blind Trust Communication - letter format with asset tables
    """
    filing_type = disclosure.get("filing_type", "").upper()
    text = extract_text_from_pdf(pdf_bytes)
    tables = extract_tables_from_pdf(pdf_bytes)

    # Extract filer info from text
    filer_info = parse_filer_info_from_text(text) if text else {}

    transactions = []
    parse_errors = []

    if not text:
        parse_errors.append("Failed to extract text from PDF")

    # Parse based on filing type
    if filing_type == "P":
        # PTR - Periodic Transaction Report (Schedule B transactions)
        for table in tables:
            for row in table:
                txn = parse_ptr_transaction(row, disclosure)
                if txn:
                    transactions.append(txn)

    elif filing_type == "B":
        # Blind Trust - parse from text (letter format)
        if text:
            blind_trust_assets = parse_blind_trust_assets(text, disclosure)
            transactions.extend(blind_trust_assets)
        # Also try tables if present
        for table in tables:
            for row in table:
                txn = parse_schedule_a_asset(row, disclosure)
                if txn:
                    transactions.append(txn)

    elif filing_type in {"A", "C", "H", "T"}:
        # Financial Disclosure Reports - parse Schedule A (assets) and Schedule B (transactions)
        current_schedule = "A"  # Default to Schedule A

        for table in tables:
            for row in table:
                row_text = " ".join(str(cell) for cell in row if cell)

                # Detect schedule switches
                if "schedule b" in row_text.lower() or "transaction" in row_text.lower():
                    current_schedule = "B"
                elif "schedule a" in row_text.lower() or "assets" in row_text.lower():
                    current_schedule = "A"

                if current_schedule == "A":
                    txn = parse_schedule_a_asset(row, disclosure)
                else:
                    txn = parse_schedule_b_transaction(row, disclosure)

                if txn:
                    transactions.append(txn)

    else:
        # Unknown or skip filing type - use generic parser
        for table in tables:
            for row in table:
                txn = parse_transaction_from_row(row, disclosure)
                if txn:
                    transactions.append(txn)

    return {
        "disclosure": disclosure,
        "filer_info": filer_info,
        "text": text,
        "text_length": len(text) if text else 0,
        "tables": tables,
        "table_count": len(tables),
        "transactions": transactions,
        "transaction_count": len(transactions),
        "parse_errors": parse_errors,
    }


def parse_pdf_disclosure(pdf_bytes: bytes, disclosure: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a PDF disclosure to extract text and transactions."""
    # Use filing-type-aware parsing
    return parse_pdf_by_filing_type(pdf_bytes, disclosure)


async def fetch_and_parse_disclosure(
    session: aiohttp.ClientSession, disclosure: Dict[str, Any], delay: float
) -> Optional[Dict[str, Any]]:
    """Fetch and parse a single disclosure PDF."""
    pdf_bytes = await HouseDisclosureScraper.fetch_pdf(session, disclosure["pdf_url"])

    if not pdf_bytes:
        logger.error(f"Failed to download PDF for {disclosure['politician_name']}")
        return None

    parsed = parse_pdf_disclosure(pdf_bytes, disclosure)

    logger.info(
        f"  - Text: {parsed['text_length']:,} chars | "
        f"Tables: {parsed['table_count']} | "
        f"Transactions: {parsed['transaction_count']}"
    )

    await asyncio.sleep(delay)
    return parsed


# =============================================================================
# ETL PIPELINE ORCHESTRATOR
# =============================================================================


async def run_house_etl_pipeline(
    year: int,
    config: ScrapingConfig,
    max_pdfs: int = 50,
    filing_type_filter: Optional[str] = "P",
    filing_types: Optional[List[str]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Run the complete ETL pipeline for House disclosures.

    Args:
        year: Year to process
        config: Scraping configuration
        max_pdfs: Maximum number of PDFs to process
        filing_type_filter: Filter by single filing type (e.g., 'P' for PTR) - deprecated
        filing_types: List of filing types to include (e.g., ['P', 'A', 'C'])
                     If None, uses PARSEABLE_FILING_TYPES

    Returns:
        Tuple of (all_disclosures, parsed_results)
    """
    # Determine which filing types to process
    if filing_types is not None:
        types_to_process = set(filing_types)
    elif filing_type_filter:
        types_to_process = {filing_type_filter}
    else:
        types_to_process = PARSEABLE_FILING_TYPES

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=config.timeout * 2),
        headers={"User-Agent": config.user_agent},
    ) as session:
        # Step 1: Download ZIP
        logger.info(f"Downloading House disclosure index for {year}...")
        zip_content = await HouseDisclosureScraper.fetch_zip_content(
            session, HouseDisclosureScraper.get_zip_url(year)
        )
        if not zip_content:
            logger.error("Failed to download ZIP index")
            return [], []

        # Step 2: Extract index
        index_content = HouseDisclosureScraper.extract_index_file(zip_content, year)
        if not index_content:
            logger.error("Failed to extract index file")
            return [], []

        # Step 3: Parse disclosures
        disclosures = HouseDisclosureScraper.parse_disclosure_index(
            index_content, year, HouseDisclosureScraper.get_base_url()
        )
        logger.info(f"Parsed {len(disclosures)} disclosure records")

        if not disclosures:
            return [], []

        # Step 4: Filter by filing types (skip D, E, G, O, W, X)
        filtered = [
            d for d in disclosures
            if d.get("filing_type") in types_to_process
        ]

        # Log filing type breakdown
        type_counts = {}
        for d in filtered:
            ft = d.get("filing_type", "?")
            type_counts[ft] = type_counts.get(ft, 0) + 1
        logger.info(f"Found {len(filtered)} parseable filings: {type_counts}")

        to_process = filtered[:max_pdfs] if max_pdfs else filtered

        # Step 5: Process each disclosure
        parsed_results = []
        for i, disclosure in enumerate(to_process):
            logger.info(
                f"[{i+1}/{len(to_process)}] Processing: "
                f"{disclosure['politician_name']} ({disclosure['filing_type']})"
            )

            result = await fetch_and_parse_disclosure(
                session, disclosure, config.request_delay
            )
            if result:
                parsed_results.append(result)

        return disclosures, parsed_results


async def run_multi_year_house_etl(
    years: List[int],
    config: ScrapingConfig,
    supabase_client: "Client",
    filing_types: Optional[List[str]] = None,
    max_pdfs_per_year: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run the House ETL pipeline for multiple years and upload to Supabase.

    Args:
        years: List of years to process (e.g., [2020, 2021, 2022, 2023, 2024, 2025])
        config: Scraping configuration
        supabase_client: Supabase client instance
        filing_types: List of filing types to process (default: PARSEABLE_FILING_TYPES)
        max_pdfs_per_year: Maximum PDFs per year (None = no limit)

    Returns:
        Summary statistics for the entire run
    """
    total_stats = {
        "years_processed": [],
        "total_disclosures_found": 0,
        "total_disclosures_inserted": 0,
        "total_disclosures_skipped": 0,
        "total_disclosures_failed": 0,
        "total_politicians_created": 0,
        "year_stats": {},
        "errors": [],
    }

    types_to_use = list(filing_types) if filing_types else list(PARSEABLE_FILING_TYPES)
    logger.info(f"Processing years {years} with filing types: {types_to_use}")

    for year in years:
        logger.info(f"\n{'='*60}\nProcessing year {year}\n{'='*60}")

        try:
            # Run ETL pipeline for this year
            all_disclosures, parsed_results = await run_house_etl_pipeline(
                year=year,
                config=config,
                max_pdfs=max_pdfs_per_year,
                filing_types=types_to_use,
            )

            year_stat = {
                "disclosures_found": len(all_disclosures),
                "disclosures_parsed": len(parsed_results),
                "inserted": 0,
                "skipped": 0,
                "failed": 0,
            }

            # Upload to Supabase
            if parsed_results:
                upload_stats = upload_parsed_disclosures_to_supabase(
                    supabase_client=supabase_client,
                    parsed_disclosures=parsed_results,
                    skip_duplicates=True,
                )

                year_stat["inserted"] = upload_stats.disclosures_inserted
                year_stat["skipped"] = upload_stats.disclosures_skipped
                year_stat["failed"] = upload_stats.disclosures_failed

                total_stats["total_disclosures_inserted"] += upload_stats.disclosures_inserted
                total_stats["total_disclosures_skipped"] += upload_stats.disclosures_skipped
                total_stats["total_disclosures_failed"] += upload_stats.disclosures_failed
                total_stats["total_politicians_created"] += upload_stats.politicians_created

                if upload_stats.errors:
                    total_stats["errors"].extend(upload_stats.errors[:10])  # Keep first 10 errors

                logger.info(
                    f"Year {year} complete: "
                    f"{upload_stats.disclosures_inserted} inserted, "
                    f"{upload_stats.disclosures_skipped} skipped, "
                    f"{upload_stats.disclosures_failed} failed"
                )

            total_stats["years_processed"].append(year)
            total_stats["total_disclosures_found"] += len(all_disclosures)
            total_stats["year_stats"][year] = year_stat

        except Exception as e:
            logger.error(f"Error processing year {year}: {e}")
            total_stats["errors"].append(f"Year {year}: {str(e)}")
            total_stats["year_stats"][year] = {"error": str(e)}

    logger.info(f"\n{'='*60}\nMulti-year ETL Complete\n{'='*60}")
    logger.info(
        f"Total: {total_stats['total_disclosures_inserted']} inserted, "
        f"{total_stats['total_disclosures_skipped']} skipped, "
        f"{total_stats['total_disclosures_failed']} failed"
    )

    return total_stats


# =============================================================================
# SUPABASE UPLOAD FUNCTIONS
# =============================================================================


def sanitize_string(value: Any) -> Optional[str]:
    """Remove null characters and other problematic unicode from strings."""
    if value is None:
        return None
    s = str(value)
    # Remove null characters and other control characters
    s = s.replace("\x00", "").replace("\u0000", "")
    # Remove other non-printable control characters except newline/tab
    s = "".join(
        c for c in s if c == "\n" or c == "\t" or (ord(c) >= 32 and ord(c) != 127)
    )
    return s.strip() if s.strip() else None


def find_or_create_politician(
    supabase_client: "Client", disclosure: Dict[str, Any]
) -> Optional[str]:
    """
    Find existing politician or create a new one.

    Returns:
        Politician UUID or None if failed
    """
    first_name = disclosure.get("first_name", "").strip()
    last_name = disclosure.get("last_name", "").strip()
    full_name = disclosure.get("politician_name", f"{first_name} {last_name}").strip()

    # Extract state from state_district (e.g., "CA12" -> "CA")
    state_district = disclosure.get("state_district", "")
    state = state_district[:2] if len(state_district) >= 2 else None

    # Try to find existing politician
    try:
        response = (
            supabase_client.table("politicians")
            .select("id")
            .match({"first_name": first_name, "last_name": last_name, "role": "Representative"})
            .execute()
        )

        if response.data and len(response.data) > 0:
            logger.debug(f"Found existing politician: {full_name}")
            return response.data[0]["id"]
    except Exception as e:
        logger.debug(f"Error finding politician: {e}")

    # Create new politician
    try:
        politician_data = {
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "role": "Representative",
            "state_or_country": state,
            "district": state_district,
        }

        response = supabase_client.table("politicians").insert(politician_data).execute()

        if response.data and len(response.data) > 0:
            logger.info(f"Created new politician: {full_name}")
            return response.data[0]["id"]
    except Exception as e:
        logger.error(f"Error creating politician {full_name}: {e}")

    return None


def check_disclosure_exists(
    supabase_client: "Client", politician_id: str, transaction: Dict[str, Any]
) -> bool:
    """Check if a disclosure already exists in the database."""
    try:
        # Sanitize and truncate asset name
        asset_name = sanitize_string(transaction.get("asset_name", ""))
        if not asset_name:
            return False
        asset_name = asset_name[:200]

        transaction_type = transaction.get("transaction_type") or "unknown"

        response = (
            supabase_client.table("trading_disclosures")
            .select("id")
            .match(
                {
                    "politician_id": politician_id,
                    "asset_name": asset_name,
                    "transaction_type": transaction_type,
                }
            )
            .execute()
        )

        return response.data and len(response.data) > 0
    except Exception as e:
        logger.debug(f"Error checking disclosure existence: {e}")
        return False


def upload_transaction_to_supabase(
    supabase_client: "Client",
    politician_id: str,
    transaction: Dict[str, Any],
    disclosure: Dict[str, Any],
) -> Optional[str]:
    """Upload a single transaction to Supabase trading_disclosures table."""
    try:
        # Parse dates
        filing_date = transaction.get("filing_date") or disclosure.get("filing_date")
        if filing_date and "T" in str(filing_date):
            filing_date = str(filing_date).replace("T", " ")[:19]

        # Sanitize asset name
        asset_name = sanitize_string(transaction.get("asset_name", ""))
        if not asset_name:
            logger.warning("Empty asset name after sanitization, skipping")
            return None
        asset_name = asset_name[:200]

        # Sanitize raw_row data
        raw_row = transaction.get("raw_row", [])
        sanitized_raw_row = [sanitize_string(cell) for cell in raw_row]

        # Prepare disclosure data
        disclosure_data = {
            "politician_id": politician_id,
            "transaction_date": filing_date,
            "disclosure_date": filing_date,
            "transaction_type": transaction.get("transaction_type") or "unknown",
            "asset_name": asset_name,
            "asset_ticker": sanitize_string(transaction.get("asset_ticker")),
            "asset_type": sanitize_string(
                transaction.get("asset_type") or transaction.get("asset_type_code")
            ),
            "amount_range_min": transaction.get("value_low"),
            "amount_range_max": transaction.get("value_high"),
            "source_url": disclosure.get("pdf_url"),
            "source_document_id": disclosure.get("doc_id"),
            "raw_data": {
                "source": "us_house",
                "year": disclosure.get("year"),
                "filing_type": disclosure.get("filing_type"),
                "state_district": disclosure.get("state_district"),
                "owner": sanitize_string(transaction.get("owner")),
                "raw_row": sanitized_raw_row,
            },
            "status": "active",
        }

        response = (
            supabase_client.table("trading_disclosures").insert(disclosure_data).execute()
        )

        if response.data and len(response.data) > 0:
            return response.data[0]["id"]

    except Exception as e:
        logger.error(f"Error uploading transaction: {e}")

    return None


def upload_parsed_disclosures_to_supabase(
    supabase_client: "Client",
    parsed_disclosures: List[Dict[str, Any]],
    skip_duplicates: bool = True,
) -> SupabaseUploadStats:
    """
    Upload all parsed disclosures to Supabase.

    Args:
        supabase_client: Supabase client instance
        parsed_disclosures: List of parsed disclosure results from ETL pipeline
        skip_duplicates: If True, skip disclosures that already exist

    Returns:
        SupabaseUploadStats with upload statistics
    """
    stats = SupabaseUploadStats()
    politician_cache: Dict[str, str] = {}  # Cache: "first_last" -> politician_id

    for parsed in parsed_disclosures:
        disclosure = parsed.get("disclosure", {})
        transactions = parsed.get("transactions", [])

        if not transactions:
            logger.debug(f"No transactions for {disclosure.get('politician_name')}, skipping")
            continue

        # Get or create politician
        cache_key = f"{disclosure.get('first_name')}_{disclosure.get('last_name')}"

        if cache_key in politician_cache:
            politician_id = politician_cache[cache_key]
            stats.politicians_matched += 1
        else:
            politician_id = find_or_create_politician(supabase_client, disclosure)
            if politician_id:
                politician_cache[cache_key] = politician_id
                stats.politicians_created += 1
            else:
                stats.errors.append(
                    f"Failed to create politician: {disclosure.get('politician_name')}"
                )
                continue

        # Upload each transaction
        for transaction in transactions:
            # Skip duplicate check
            if skip_duplicates and check_disclosure_exists(
                supabase_client, politician_id, transaction
            ):
                logger.debug(f"Skipping duplicate: {transaction.get('asset_name')}")
                stats.disclosures_skipped += 1
                continue

            # Upload transaction
            disclosure_id = upload_transaction_to_supabase(
                supabase_client, politician_id, transaction, disclosure
            )

            if disclosure_id:
                stats.disclosures_inserted += 1
                logger.info(
                    f"Inserted disclosure: {disclosure_id} - "
                    f"{transaction.get('asset_ticker', transaction.get('asset_name', 'N/A')[:30])}"
                )
            else:
                stats.disclosures_failed += 1
                stats.errors.append(
                    f"Failed to insert: {transaction.get('asset_name', 'N/A')[:50]}"
                )

    return stats
