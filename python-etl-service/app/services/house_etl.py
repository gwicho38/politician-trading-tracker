"""
US House Financial Disclosure ETL Service

Adapted from .mcli/workflows/01_us_house.ipynb
Extracts real disclosure data from government PDFs and uploads to Supabase.
"""

import asyncio
import io
import logging
import os
import re
import zipfile
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import httpx
import pdfplumber
from supabase import create_client, Client

from lib.parser import (
    extract_ticker_from_text, 
    sanitize_string, 
    parse_value_range, 
    parse_asset_type
)
from lib.database import get_supabase, upload_transaction_to_supabase

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Job status tracking (in-memory for now)
JOB_STATUS: Dict[str, Dict[str, Any]] = {}

# Constants
HOUSE_BASE_URL = "https://disclosures-clerk.house.gov"
ZIP_URL_TEMPLATE = "{base_url}/public_disc/financial-pdfs/{year}FD.ZIP"
PDF_URL_TEMPLATE = "{base_url}/public_disc/financial-pdfs/{year}/{doc_id}.pdf"
PTR_PDF_URL_TEMPLATE = "{base_url}/public_disc/ptr-pdfs/{year}/{doc_id}.pdf"
USER_AGENT = "Mozilla/5.0 (compatible; PoliticianTradingETL/1.0)"

# Rate limiting configuration
REQUEST_DELAY_BASE = 1.0  # Base delay between requests (seconds)
REQUEST_DELAY_MAX = 60.0  # Maximum delay after backoffs (seconds)
MAX_RETRIES = 5  # Maximum retries per request
BACKOFF_MULTIPLIER = 2.0  # Exponential backoff multiplier
RATE_LIMIT_CODES = {429, 503, 502, 504}  # HTTP codes that trigger backoff


class RateLimiter:
    """Adaptive rate limiter with exponential backoff."""

    def __init__(self):
        self.current_delay = REQUEST_DELAY_BASE
        self.consecutive_errors = 0
        self.total_requests = 0
        self.total_errors = 0

    async def wait(self):
        """Wait for the current delay period."""
        await asyncio.sleep(self.current_delay)

    def record_success(self):
        """Record a successful request and gradually reduce delay."""
        self.total_requests += 1
        self.consecutive_errors = 0
        # Gradually reduce delay back to base after successes
        if self.current_delay > REQUEST_DELAY_BASE:
            self.current_delay = max(
                REQUEST_DELAY_BASE,
                self.current_delay / BACKOFF_MULTIPLIER
            )
            logger.debug(f"Rate limiter: delay reduced to {self.current_delay:.1f}s")

    def record_error(self, is_rate_limit: bool = False):
        """Record an error and increase delay."""
        self.total_requests += 1
        self.total_errors += 1
        self.consecutive_errors += 1

        if is_rate_limit:
            # Aggressive backoff for rate limiting
            self.current_delay = min(
                REQUEST_DELAY_MAX,
                self.current_delay * BACKOFF_MULTIPLIER * 2
            )
            logger.warning(
                f"Rate limit hit! Backing off to {self.current_delay:.1f}s "
                f"(consecutive errors: {self.consecutive_errors})"
            )
        else:
            # Normal backoff for other errors
            self.current_delay = min(
                REQUEST_DELAY_MAX,
                self.current_delay * BACKOFF_MULTIPLIER
            )
            logger.warning(f"Error recorded, delay increased to {self.current_delay:.1f}s")

    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        return {
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "error_rate": self.total_errors / max(1, self.total_requests),
            "current_delay": self.current_delay,
            "consecutive_errors": self.consecutive_errors,
        }


# Global rate limiter instance
rate_limiter = RateLimiter()



# =============================================================================
# PDF PARSING UTILITIES
# ============================================================================

def _validate_and_correct_year(tx_date: datetime, notif_date: datetime) -> Tuple[datetime, datetime]:
    """
    Validate years are within reasonable range and attempt to correct typos.

    PDF OCR can produce typos like "3031" instead of "2021" or "2220" instead of "2022".
    If the transaction year is unreasonable but the notification year is valid,
    use the notification year to infer the correct transaction year.

    Valid range: 2008 (earliest disclosure data) to current year + 1
    """
    current_year = datetime.now().year
    min_year = 2008
    max_year = current_year + 1

    tx_year_valid = min_year <= tx_date.year <= max_year
    notif_year_valid = min_year <= notif_date.year <= max_year

    if tx_year_valid and notif_year_valid:
        return tx_date, notif_date

    # If transaction year is invalid but notification is valid, use notification year
    if not tx_year_valid and notif_year_valid:
        corrected_tx = tx_date.replace(year=notif_date.year)
        # If tx would be after notification, it's likely the previous year
        if corrected_tx > notif_date:
            corrected_tx = tx_date.replace(year=notif_date.year - 1)
        logger.warning(
            f"Corrected transaction year typo: {tx_date.year} -> {corrected_tx.year} "
            f"(original: {tx_date.strftime('%m/%d/%Y')}, notif: {notif_date.strftime('%m/%d/%Y')})"
        )
        return corrected_tx, notif_date

    # If notification year is invalid but transaction is valid, use transaction year
    if tx_year_valid and not notif_year_valid:
        corrected_notif = notif_date.replace(year=tx_date.year)
        # Notification should be same year or later
        if corrected_notif < tx_date:
            corrected_notif = notif_date.replace(year=tx_date.year + 1)
        logger.warning(
            f"Corrected notification year typo: {notif_date.year} -> {corrected_notif.year}"
        )
        return tx_date, corrected_notif

    # Both invalid - log and return as-is (will likely fail validation elsewhere)
    logger.error(f"Both dates have invalid years: tx={tx_date.year}, notif={notif_date.year}")
    return tx_date, notif_date


def extract_dates_from_row(row: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract transaction date and notification date from a PDF table row.

    House disclosure PDFs embed dates in formats like:
    - "S 11/19/2025 11/26/2025 $1,001 - $15,000"
    - "P 01/15/2025 01/20/2025 $15,001 - $50,000"
    - "S (partial) 12/01/2024 12/05/2024 $1,001 - $15,000"

    The first date is the transaction date (when the buy/sell occurred).
    The second date is the notification/disclosure date (when it was reported).

    Returns:
        Tuple of (transaction_date, notification_date) in ISO format, or (None, None)
    """
    # Combine all cells into one text for pattern matching
    row_text = " ".join(str(cell).replace("\x00", "") for cell in row if cell)

    # Pattern: P/S followed by two dates
    # Matches: "P 01/15/2025 01/20/2025" or "S (partial) 12/01/2024 12/05/2024"
    date_pattern = r"[PS]\s*(?:\(partial\))?\s*(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}/\d{1,2}/\d{4})"
    match = re.search(date_pattern, row_text, re.IGNORECASE)

    if match:
        try:
            tx_date = datetime.strptime(match.group(1), "%m/%d/%Y")
            notif_date = datetime.strptime(match.group(2), "%m/%d/%Y")
            tx_date, notif_date = _validate_and_correct_year(tx_date, notif_date)
            return tx_date.isoformat(), notif_date.isoformat()
        except ValueError:
            pass

    # Fallback: look for any two consecutive dates
    date_only_pattern = r"(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}/\d{1,2}/\d{4})"
    match = re.search(date_only_pattern, row_text)

    if match:
        try:
            tx_date = datetime.strptime(match.group(1), "%m/%d/%Y")
            notif_date = datetime.strptime(match.group(2), "%m/%d/%Y")
            tx_date, notif_date = _validate_and_correct_year(tx_date, notif_date)
            return tx_date.isoformat(), notif_date.isoformat()
        except ValueError:
            pass

    return None, None


def clean_asset_name(name: str) -> str:
    """Clean asset name by removing trailing metadata like F S:, S O:, etc.

    PDF table cells often contain multiple lines with metadata appended:
    'Apple Inc (AAPL) [ST]\nF S: New\nS O: Brokerage Account'

    We want just: 'Apple Inc (AAPL) [ST]'
    """
    if not name:
        return name

    # Split by newlines and process line by line
    lines = name.split("\n")
    clean_lines = []

    for line in lines:
        line = line.strip()
        # Stop if we hit metadata lines
        if re.match(r"^(F\s*S|S\s*O|Owner|Filer|Status|Type)\s*:", line, re.IGNORECASE):
            break
        # Skip empty lines
        if not line:
            continue
        clean_lines.append(line)

    result = " ".join(clean_lines).strip()

    # Remove transaction data pattern that's mixed into asset name
    # Pattern: "S 02/25/2025 02/25/2025 $1,001 - $15,000" or partial like "P 01/17/2025 02/04/2025 $15,001 -"
    # The second amount may be missing due to newlines in the PDF
    result = re.sub(
        r"\s+[PS]\s+\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}/\d{1,2}/\d{4}\s+\$[\d,]+\s*-\s*(\$[\d,]+)?",
        "",
        result,
    )
    # Also handle "(partial)" notation like "S (partial) 01/08/2025..."
    result = re.sub(
        r"\s+[PS]\s*\(partial\)\s+\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}/\d{1,2}/\d{4}\s+\$[\d,]+\s*-\s*(\$[\d,]+)?",
        "",
        result,
        flags=re.IGNORECASE,
    )

    # Also remove any trailing metadata that didn't have a newline
    # e.g., "Stock Name [ST] F S: New" -> "Stock Name [ST]"
    result = re.sub(r"\s+(F\s*S|S\s*O)\s*:.*$", "", result, flags=re.IGNORECASE)

    return result if result else None


def extract_text_from_pdf(pdf_bytes: bytes) -> Optional[str]:
    """Extract all text from a PDF file."""
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
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            return [
                table for page in pdf.pages for table in (page.extract_tables() or [])
            ]
    except Exception as e:
        logger.error(f"Failed to extract tables from PDF: {e}")
        return []


def is_header_row(row_text: str) -> bool:
    """Check if a row is a header row.

    PDF tables sometimes split headers across multiple rows, e.g.:
    Row 0: ['ID', 'Owner', 'Asset', 'Transaction', ...]
    Row 1: ['', '', '', 'Type', ...]  ← continuation of header

    We need to detect both full headers and these continuation rows.
    """
    text_lower = row_text.lower().strip()

    # Standard header keywords
    headers = ["asset", "owner", "value", "income", "description", "transaction", "notification"]
    if any(header in text_lower for header in headers):
        return True

    # Exact match for standalone header continuation words
    # These appear in continuation rows with mostly empty cells
    standalone_headers = ["type", "date", "amount", "cap.", "gains"]
    words = [w.strip() for w in text_lower.split() if w.strip()]
    if words and all(w in standalone_headers or w.startswith("$") or w == ">" for w in words):
        return True

    return False


def is_metadata_row(text: str) -> bool:
    """Check if text is metadata rather than an actual asset.

    These are common metadata patterns in House disclosure PDFs:
    - F S: (Filer Status)
    - S O: (Sub Owner)
    - Owner:
    - Filing ID:

    Note: PDF text often contains null bytes (\x00) that must be
    stripped before pattern matching.
    """
    # Remove null bytes first - they break regex patterns
    text_clean = text.replace("\x00", "").strip()

    metadata_patterns = [
        r"^F\s*S\s*:",  # Filer Status
        r"^S\s*O\s*:",  # Sub Owner
        r"^Owner\s*:",
        r"^Filing\s*(ID|Date)\s*:",
        r"^Document\s*ID\s*:",
        r"^Filer\s*:",
        r"^Status\s*:",
        r"^Type\s*:",
        r"^Cap.*Gains",  # Capital Gains headers
        r"^Div.*Only",   # Dividends Only
        r"^L\s*:",       # Location
        r"^D\s*:",       # Description
        r"^C\s*:",       # Comment
    ]
    for pattern in metadata_patterns:
        if re.match(pattern, text_clean, re.IGNORECASE):
            return True
    return False


def parse_transaction_from_row(
    row: List[str], disclosure: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Parse a transaction from a table row."""
    if not row or len(row) < 3:
        return None

    row_text = " ".join(str(cell) for cell in row if cell)
    if not row_text.strip() or is_header_row(row_text):
        return None

    # Extract asset info from first non-empty cell that's not metadata
    asset_name = None
    asset_ticker = None
    asset_type_code = None
    asset_type = None

    for cell in row:
        if not cell or len(str(cell).strip()) <= 2:
            continue
        cell_str = str(cell).strip()
        # Skip metadata rows
        if is_metadata_row(cell_str):
            continue
        asset_name = sanitize_string(cell_str)
        # Clean trailing metadata from asset name
        asset_name = clean_asset_name(asset_name)
        asset_ticker = extract_ticker_from_text(cell_str)
        asset_type_code, asset_type = parse_asset_type(cell_str)
        break

    if not asset_name:
        return None

    # Double-check: skip if the entire asset_name looks like metadata
    if is_metadata_row(asset_name):
        return None

    # Extract value range
    value_info = {"value_low": None, "value_high": None}
    for cell in row:
        if cell and "$" in str(cell):
            value_info = parse_value_range(str(cell))
            break

    # Extract transaction type - check for P/S letter patterns FIRST (most reliable for House PDFs)
    # Then fall back to keywords if no P/S found
    transaction_type = None

    # Priority 1: Check for P/S letter patterns (most reliable for House disclosures)
    for cell in row:
        if cell:
            # Remove null bytes before pattern matching
            cell_str = str(cell).replace("\x00", "").strip()
            # Match P/S followed by date pattern (embedded in asset cell)
            # Pattern: "P 01/15/2025" or "S 12/01/2024" anywhere in the text
            if re.search(r"\bP\s+\d{1,2}/\d{1,2}/\d{4}", cell_str):
                transaction_type = "purchase"
                break
            elif re.search(r"\bS\s+\d{1,2}/\d{1,2}/\d{4}", cell_str):
                transaction_type = "sale"
                break
            # Match standalone P or S (in its own cell)
            elif re.match(r"^P(\s|$)", cell_str):
                transaction_type = "purchase"
                break
            elif re.match(r"^S(\s|$)", cell_str):
                transaction_type = "sale"
                break
            # Also check for P/S with (partial) notation
            elif re.search(r"\bP\s*\(partial\)\s+\d{1,2}/", cell_str, re.IGNORECASE):
                transaction_type = "purchase"
                break
            elif re.search(r"\bS\s*\(partial\)\s+\d{1,2}/", cell_str, re.IGNORECASE):
                transaction_type = "sale"
                break

    # Priority 2: Fall back to keywords if no P/S pattern found
    # Only check text BEFORE metadata markers to avoid false positives from descriptions
    if transaction_type is None:
        # Clean and truncate text before metadata markers
        row_clean = row_text.replace("\x00", "")
        # Find first metadata marker and only search before it
        for marker in ["F S:", "S O:", "\nD:", "\nC:", "\nL:"]:
            idx = row_clean.find(marker)
            if idx != -1:
                row_clean = row_clean[:idx]
        row_lower = row_clean.lower()

        if any(kw in row_lower for kw in ["purchase", "bought", "buy"]):
            transaction_type = "purchase"
        elif any(kw in row_lower for kw in ["sale", "sold", "sell", "exchange"]):
            transaction_type = "sale"

    # Extract transaction and notification dates from the row
    transaction_date, notification_date = extract_dates_from_row(row)

    # Skip rows that lack BOTH transaction type AND value info
    # These are likely footer rows or incomplete data
    has_transaction_type = transaction_type is not None
    has_value_info = value_info.get("value_low") is not None or value_info.get("value_high") is not None

    if not has_transaction_type and not has_value_info:
        return None

    return {
        "politician_name": disclosure.get("politician_name"),
        "doc_id": disclosure.get("doc_id"),
        "filing_type": disclosure.get("filing_type"),
        "filing_date": disclosure.get("filing_date"),
        "source": "us_house",
        "asset_name": asset_name,
        "asset_ticker": asset_ticker,
        "asset_type_code": asset_type_code,
        "asset_type": asset_type,
        "value_low": value_info.get("value_low"),
        "value_high": value_info.get("value_high"),
        "transaction_type": transaction_type,
        "transaction_date": transaction_date,
        "notification_date": notification_date,
        "raw_row": [str(c) if c else "" for c in row],
    }


# =============================================================================
# HOUSE DISCLOSURE SCRAPER
# =============================================================================


class HouseDisclosureScraper:
    """Scraper for US House financial disclosure data."""

    @staticmethod
    def get_zip_url(year: int) -> str:
        """Get the ZIP file URL for a given year."""
        return ZIP_URL_TEMPLATE.format(base_url=HOUSE_BASE_URL, year=year)

    @staticmethod
    def get_pdf_url(year: int, doc_id: str, filing_type: str = "") -> str:
        """Get the PDF URL for a specific disclosure document."""
        if filing_type == "P":
            return PTR_PDF_URL_TEMPLATE.format(
                base_url=HOUSE_BASE_URL, year=year, doc_id=doc_id
            )
        return PDF_URL_TEMPLATE.format(
            base_url=HOUSE_BASE_URL, year=year, doc_id=doc_id
        )

    @staticmethod
    async def fetch_zip_content(client: httpx.AsyncClient, url: str) -> Optional[bytes]:
        """Download ZIP file content from URL."""
        try:
            response = await client.get(url)
            if response.status_code != 200:
                logger.error(f"Failed to download: {response.status_code}")
                return None
            logger.info(f"Downloaded {len(response.content):,} bytes")
            return response.content
        except Exception as e:
            logger.error(f"Error fetching ZIP: {e}")
            return None

    @staticmethod
    async def fetch_pdf(
        client: httpx.AsyncClient,
        pdf_url: str,
        max_retries: int = MAX_RETRIES
    ) -> Optional[bytes]:
        """Download a PDF document with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                # Wait according to rate limiter before making request
                await rate_limiter.wait()

                response = await client.get(pdf_url)

                if response.status_code == 200:
                    content = response.content
                    if not content.startswith(b"%PDF"):
                        logger.error(f"Downloaded content is not a valid PDF")
                        rate_limiter.record_error(is_rate_limit=False)
                        return None

                    rate_limiter.record_success()
                    return content

                elif response.status_code in RATE_LIMIT_CODES:
                    # Rate limited - back off aggressively
                    rate_limiter.record_error(is_rate_limit=True)
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        try:
                            wait_time = int(retry_after)
                            logger.warning(f"Rate limited, waiting {wait_time}s (Retry-After header)")
                            await asyncio.sleep(wait_time)
                        except ValueError:
                            pass
                    if attempt < max_retries - 1:
                        logger.warning(f"Retry {attempt + 1}/{max_retries} for {pdf_url}")
                        continue
                    else:
                        logger.error(f"Max retries exceeded for {pdf_url}")
                        return None

                elif response.status_code == 404:
                    # Not found - don't retry
                    logger.warning(f"PDF not found (404): {pdf_url}")
                    return None

                else:
                    # Other error
                    rate_limiter.record_error(is_rate_limit=False)
                    logger.error(f"Failed to download PDF: {response.status_code}")
                    if attempt < max_retries - 1:
                        continue
                    return None

            except httpx.TimeoutException:
                rate_limiter.record_error(is_rate_limit=False)
                logger.warning(f"Timeout fetching PDF (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    continue
                return None

            except Exception as e:
                rate_limiter.record_error(is_rate_limit=False)
                logger.error(f"Error fetching PDF: {e}")
                if attempt < max_retries - 1:
                    continue
                return None

        return None

    @staticmethod
    def extract_index_file(zip_content: bytes, year: int) -> Optional[str]:
        """Extract the disclosure index text file from ZIP content."""
        txt_filename = f"{year}FD.txt"

        with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
            if txt_filename not in z.namelist():
                logger.error(f"Index file {txt_filename} not found in ZIP")
                return None

            with z.open(txt_filename) as f:
                return f.read().decode("utf-8", errors="ignore")

    @staticmethod
    def parse_filing_date(date_str: str) -> Optional[str]:
        """Parse a filing date string to ISO format."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str.strip(), "%m/%d/%Y").isoformat()
        except ValueError:
            return None

    @staticmethod
    def parse_disclosure_record(
        line: str, year: int
    ) -> Optional[Dict[str, Any]]:
        """Parse a single disclosure record from tab-separated line."""
        fields = line.split("\t")
        if len(fields) < 9:
            return None

        prefix, last_name, first_name, suffix = fields[0:4]
        filing_type, state_district, file_year = fields[4:7]
        filing_date_str, doc_id = fields[7:9]

        doc_id = doc_id.strip()
        filing_type = filing_type.strip()
        if not doc_id or doc_id == "DocID":
            return None

        # Build full name
        name_parts = [
            p.strip() for p in [prefix, first_name, last_name, suffix] if p.strip()
        ]
        full_name = " ".join(name_parts)

        # Get PDF URL
        pdf_url = HouseDisclosureScraper.get_pdf_url(year, doc_id, filing_type)

        return {
            "politician_name": full_name,
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "state_district": state_district.strip(),
            "filing_type": filing_type,
            "filing_date": HouseDisclosureScraper.parse_filing_date(filing_date_str),
            "doc_id": doc_id,
            "pdf_url": pdf_url,
            "year": year,
            "source": "us_house",
        }

    @staticmethod
    def parse_disclosure_index(content: str, year: int) -> List[Dict[str, Any]]:
        """Parse all disclosure records from index file content."""
        lines = content.strip().split("\n")
        logger.info(f"Found {len(lines)} records in index")

        disclosures = []
        for line in lines[1:]:  # Skip header
            record = HouseDisclosureScraper.parse_disclosure_record(line, year)
            if record:
                disclosures.append(record)

        return disclosures


# =============================================================================
# SUPABASE UPLOAD
# =============================================================================



def find_or_create_politician(
    supabase_client: Client, disclosure: Dict[str, Any]
) -> Optional[str]:
    """Find existing politician or create a new one."""
    first_name = disclosure.get("first_name", "").strip()
    last_name = disclosure.get("last_name", "").strip()
    full_name = disclosure.get("politician_name", f"{first_name} {last_name}").strip()

    state_district = disclosure.get("state_district", "")
    state = state_district[:2] if len(state_district) >= 2 else None

    # Try to find existing politician
    try:
        response = (
            supabase_client.table("politicians")
            .select("id")
            .match(
                {"first_name": first_name, "last_name": last_name, "role": "Representative"}
            )
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


# =============================================================================
# MAIN ETL FUNCTION
# =============================================================================


async def run_house_etl(
    job_id: str,
    year: int = 2025,
    limit: Optional[int] = None,
    update_mode: bool = False,
):
    """
    Run the complete House disclosure ETL pipeline.

    This function:
    1. Downloads the yearly disclosure index ZIP
    2. Parses all disclosure records
    3. Downloads and parses PDFs for PTR filings
    4. Uploads transactions to Supabase

    Args:
        job_id: Unique job identifier for status tracking
        year: Year to process (default: 2025)
        limit: Optional limit on number of PDFs (for testing). If None, processes all.
        update_mode: If True, upsert to update existing records with new parsing.
    """
    JOB_STATUS[job_id]["status"] = "running"
    mode_str = " (UPDATE MODE)" if update_mode else ""
    JOB_STATUS[job_id]["message"] = f"Initializing{mode_str}..."

    # Reset rate limiter for this job
    global rate_limiter
    rate_limiter = RateLimiter()
    logger.info(f"Starting ETL for year {year} with rate limiter reset")

    try:
        # Initialize Supabase client
        try:
            supabase_client = get_supabase()
        except ValueError as e:
            JOB_STATUS[job_id]["status"] = "failed"
            JOB_STATUS[job_id]["message"] = str(e)
            return

        async with httpx.AsyncClient(
            timeout=60.0, headers={"User-Agent": USER_AGENT}
        ) as client:

            # Step 1: Download ZIP index
            JOB_STATUS[job_id]["message"] = f"Downloading {year} disclosure index..."
            zip_url = HouseDisclosureScraper.get_zip_url(year)
            zip_content = await HouseDisclosureScraper.fetch_zip_content(client, zip_url)

            if not zip_content:
                JOB_STATUS[job_id]["status"] = "failed"
                JOB_STATUS[job_id]["message"] = "Failed to download ZIP index"
                return

            # Step 2: Extract and parse index
            JOB_STATUS[job_id]["message"] = "Parsing disclosure index..."
            index_content = HouseDisclosureScraper.extract_index_file(zip_content, year)

            if not index_content:
                JOB_STATUS[job_id]["status"] = "failed"
                JOB_STATUS[job_id]["message"] = "Failed to extract index file"
                return

            disclosures = HouseDisclosureScraper.parse_disclosure_index(
                index_content, year
            )
            logger.info(f"Parsed {len(disclosures)} disclosure records")

            # Step 3: Filter to PTR filings (stock trades)
            ptr_disclosures = [d for d in disclosures if d.get("filing_type") == "P"]
            logger.info(f"Found {len(ptr_disclosures)} PTR filings")

            # Process all PTR filings, or limit if specified (for testing)
            to_process = ptr_disclosures[:limit] if limit else ptr_disclosures
            JOB_STATUS[job_id]["total"] = len(to_process)

            # Step 4: Process each PDF
            politicians_created = 0
            transactions_uploaded = 0
            politician_cache: Dict[str, str] = {}

            for i, disclosure in enumerate(to_process):
                JOB_STATUS[job_id]["progress"] = i + 1
                JOB_STATUS[job_id][
                    "message"
                ] = f"Processing {disclosure['politician_name']} ({i+1}/{len(to_process)})"

                # Fetch PDF
                pdf_bytes = await HouseDisclosureScraper.fetch_pdf(
                    client, disclosure["pdf_url"]
                )

                if not pdf_bytes:
                    logger.warning(f"Failed to download PDF for {disclosure['doc_id']}")
                    continue

                # Parse PDF
                tables = extract_tables_from_pdf(pdf_bytes)

                transactions = []
                for table in tables:
                    for row in table:
                        txn = parse_transaction_from_row(row, disclosure)
                        if txn:
                            transactions.append(txn)
                            logger.debug(
                                f"Parsed transaction: {txn.get('asset_name', 'N/A')[:50]} | "
                                f"type={txn.get('transaction_type')}"
                            )

                logger.info(f"Found {len(transactions)} transactions in {disclosure['doc_id']}")

                if not transactions:
                    logger.debug(f"No transactions found in {disclosure['doc_id']}")
                    continue

                # Get or create politician
                cache_key = f"{disclosure['first_name']}_{disclosure['last_name']}"

                if cache_key in politician_cache:
                    politician_id = politician_cache[cache_key]
                else:
                    politician_id = find_or_create_politician(supabase_client, disclosure)
                    if politician_id:
                        politician_cache[cache_key] = politician_id
                        politicians_created += 1
                    else:
                        logger.error(
                            f"Failed to create politician: {disclosure['politician_name']}"
                        )
                        continue

                # Upload transactions
                for txn in transactions:
                    disclosure_id = upload_transaction_to_supabase(
                        supabase_client, politician_id, txn, disclosure,
                        update_mode=update_mode,
                    )
                    if disclosure_id:
                        transactions_uploaded += 1
                        action = "Updated" if update_mode else "Uploaded"
                        logger.info(
                            f"{action}: {txn.get('asset_ticker', txn.get('asset_name', 'N/A')[:30])}"
                        )

                # Rate limiting is now handled in fetch_pdf via RateLimiter
                # Log progress periodically
                if (i + 1) % 50 == 0:
                    stats = rate_limiter.get_stats()
                    logger.info(
                        f"Progress: {i + 1}/{len(to_process)} PDFs | "
                        f"Delay: {stats['current_delay']:.1f}s | "
                        f"Errors: {stats['total_errors']}"
                    )

            # Complete
            stats = rate_limiter.get_stats()
            JOB_STATUS[job_id]["status"] = "completed"
            JOB_STATUS[job_id]["completed_at"] = datetime.utcnow().isoformat()
            JOB_STATUS[job_id]["rate_limiter_stats"] = stats
            JOB_STATUS[job_id][
                "message"
            ] = f"Completed: {transactions_uploaded} transactions from {len(to_process)} PDFs"

            logger.info(
                f"ETL Complete - Politicians: {politicians_created}, "
                f"Transactions: {transactions_uploaded}, "
                f"Rate limit errors: {stats['total_errors']}, "
                f"Final delay: {stats['current_delay']:.1f}s"
            )

    except Exception as e:
        logger.exception(f"ETL failed: {e}")
        JOB_STATUS[job_id]["status"] = "failed"
        JOB_STATUS[job_id]["message"] = str(e)
        JOB_STATUS[job_id]["completed_at"] = datetime.utcnow().isoformat()
