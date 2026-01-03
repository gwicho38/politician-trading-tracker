"""
US Senate Financial Disclosure ETL Service

Extracts Periodic Transaction Reports (PTRs) from the Senate EFD database.
Similar structure to house_etl.py but adapted for Senate disclosure format.

Data Source: https://efdsearch.senate.gov/search/
"""

import asyncio
import io
import logging
import os
import re
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import httpx
import pdfplumber
from bs4 import BeautifulSoup
from supabase import create_client, Client

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import shared job status from house_etl
from app.services.house_etl import JOB_STATUS, RateLimiter, VALUE_PATTERNS, ASSET_TYPE_CODES

# Constants
SENATE_BASE_URL = "https://efdsearch.senate.gov"
SENATE_SEARCH_URL = f"{SENATE_BASE_URL}/search/"
SENATE_PTR_URL = f"{SENATE_BASE_URL}/search/view/ptr/"
USER_AGENT = "Mozilla/5.0 (compatible; PoliticianTradingETL/1.0)"

# Global rate limiter instance
rate_limiter = RateLimiter()


# =============================================================================
# SUPABASE UTILITIES
# =============================================================================


def get_supabase_client() -> Client:
    """Get authenticated Supabase client."""
    url = os.getenv("SUPABASE_URL", "https://uljsqvwkomdrlnofmlad.supabase.co")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not key:
        raise ValueError("SUPABASE_SERVICE_KEY not configured")
    return create_client(url, key)


def find_or_create_politician(
    supabase: Client, name: str, state: Optional[str] = None
) -> Optional[str]:
    """Find or create a politician record, returning the ID."""
    if not name or name == "Unknown":
        return None

    # Clean the name
    clean_name = name.strip()
    # Remove common prefixes
    for prefix in ["Sen.", "Senator", "Hon.", "Honorable"]:
        clean_name = clean_name.replace(prefix, "").strip()

    # Try to find existing politician
    try:
        response = (
            supabase.table("politicians")
            .select("id")
            .ilike("name", f"%{clean_name}%")
            .limit(1)
            .execute()
        )

        if response.data:
            return response.data[0]["id"]

        # Create new politician
        new_politician = {
            "name": clean_name,
            "jurisdiction": "Federal",
            "position": "Senator",
            "party": None,
            "state": state,
        }

        response = supabase.table("politicians").insert(new_politician).execute()
        if response.data:
            logger.info(f"Created new politician: {clean_name}")
            return response.data[0]["id"]

    except Exception as e:
        logger.error(f"Error finding/creating politician {name}: {e}")

    return None


def upload_transaction_to_supabase(
    supabase: Client,
    politician_id: str,
    transaction: Dict[str, Any],
    disclosure_info: Dict[str, Any],
) -> Optional[str]:
    """Upload a transaction to Supabase trading_disclosures table."""
    try:
        record = {
            "politician_id": politician_id,
            "asset_name": transaction.get("asset_name"),
            "asset_ticker": transaction.get("ticker"),
            "asset_type": transaction.get("asset_type"),
            "transaction_type": transaction.get("transaction_type", "unknown"),
            "transaction_date": transaction.get("transaction_date"),
            "disclosure_date": transaction.get("notification_date") or disclosure_info.get("filing_date"),
            "amount_range_min": transaction.get("value_low"),
            "amount_range_max": transaction.get("value_high"),
            "source_url": disclosure_info.get("source_url"),
            "raw_data": {
                "doc_id": disclosure_info.get("doc_id"),
                "filing_date": disclosure_info.get("filing_date"),
                "source": "us_senate",
            },
        }

        # Upsert using unique constraint on (politician_id, asset_name, transaction_date, source_url)
        response = (
            supabase.table("trading_disclosures")
            .upsert(record, on_conflict="politician_id,asset_name,transaction_date,source_url")
            .execute()
        )

        if response.data:
            return response.data[0]["id"]

    except Exception as e:
        logger.error(f"Error uploading transaction: {e}")

    return None


# =============================================================================
# PDF PARSING UTILITIES
# =============================================================================


def extract_ticker_from_text(text: str) -> Optional[str]:
    """Extract stock ticker from text like 'Company Name (TICKER)'."""
    match = re.search(r"\(([A-Z]{1,5})\)", text)
    return match.group(1) if match else None


def parse_asset_type(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse asset type from Senate disclosure format."""
    # Senate often uses full words instead of codes
    text_lower = text.lower()

    if "stock" in text_lower or "equity" in text_lower:
        return "ST", "Stocks"
    elif "option" in text_lower:
        return "OP", "Stock Options"
    elif "mutual fund" in text_lower or "etf" in text_lower:
        return "MF", "Mutual Funds"
    elif "bond" in text_lower:
        return "BN", "Bonds"
    elif "treasury" in text_lower or "government" in text_lower:
        return "GS", "Government Securities"

    # Also check for bracketed codes like House
    match = re.search(r"\[([A-Z]{2})\]", text)
    if match:
        code = match.group(1)
        return code, ASSET_TYPE_CODES.get(code, code)

    return None, None


def parse_value_range(text: str) -> Dict[str, Optional[float]]:
    """Parse value range from text."""
    for pattern, low, high in VALUE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return {"value_low": float(low), "value_high": float(high)}
    return {"value_low": None, "value_high": None}


def sanitize_string(value: Any) -> Optional[str]:
    """Remove null characters and other problematic unicode."""
    if value is None:
        return None
    s = str(value)
    s = s.replace("\x00", "").replace("\u0000", "")
    s = "".join(c for c in s if c == "\n" or c == "\t" or (ord(c) >= 32 and ord(c) != 127))
    return s.strip() if s.strip() else None


def extract_tables_from_pdf(pdf_bytes: bytes) -> List[List[List[str]]]:
    """Extract all tables from a PDF file."""
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            return [table for page in pdf.pages for table in (page.extract_tables() or [])]
    except Exception as e:
        logger.error(f"Failed to extract tables from PDF: {e}")
        return []


def extract_text_from_pdf(pdf_bytes: bytes) -> Optional[str]:
    """Extract all text from a PDF file."""
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            text_parts = [page.extract_text() for page in pdf.pages if page.extract_text()]
            return "\n".join(text_parts) if text_parts else None
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {e}")
        return None


def is_header_row(row_text: str) -> bool:
    """Check if a row is a header row."""
    text_lower = row_text.lower().strip()
    headers = ["asset", "owner", "value", "income", "description", "transaction", "type", "date", "amount"]
    return any(header in text_lower for header in headers)


def parse_transaction_from_row(row: List[str], disclosure: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse a transaction from a Senate PDF table row."""
    if not row or len(row) < 2:
        return None

    row_text = " ".join(str(cell) for cell in row if cell)
    if not row_text.strip() or is_header_row(row_text):
        return None

    # Extract asset info
    asset_name = None
    asset_ticker = None
    asset_type_code = None
    asset_type = None

    for cell in row:
        if not cell or len(str(cell).strip()) <= 2:
            continue
        cell_str = sanitize_string(str(cell))
        if not cell_str:
            continue

        # Skip metadata lines
        if any(x in cell_str.lower() for x in ["owner:", "filer:", "filing id:", "comment"]):
            continue

        asset_name = cell_str
        asset_ticker = extract_ticker_from_text(cell_str)
        asset_type_code, asset_type = parse_asset_type(cell_str)
        break

    if not asset_name:
        return None

    # Extract value range
    value_info = {"value_low": None, "value_high": None}
    for cell in row:
        if cell and "$" in str(cell):
            value_info = parse_value_range(str(cell))
            break

    # Extract transaction type
    transaction_type = None
    row_lower = row_text.lower()

    # Check for explicit keywords
    if any(kw in row_lower for kw in ["purchase", "bought", "buy"]):
        transaction_type = "purchase"
    elif any(kw in row_lower for kw in ["sale", "sold", "sell", "exchange"]):
        transaction_type = "sale"

    # Also check for P/S codes (some Senate PDFs use these)
    if transaction_type is None:
        for cell in row:
            if cell:
                cell_str = str(cell).strip()
                if re.match(r"^P(\s|$)", cell_str):
                    transaction_type = "purchase"
                    break
                elif re.match(r"^S(\s|$)", cell_str):
                    transaction_type = "sale"
                    break

    # Extract dates
    transaction_date = None
    notification_date = disclosure.get("filing_date")

    # Look for date patterns
    date_pattern = r"(\d{1,2}/\d{1,2}/\d{4})"
    for cell in row:
        if cell:
            matches = re.findall(date_pattern, str(cell))
            if matches:
                try:
                    transaction_date = datetime.strptime(matches[0], "%m/%d/%Y").isoformat()
                    if len(matches) > 1:
                        notification_date = datetime.strptime(matches[1], "%m/%d/%Y").isoformat()
                except ValueError:
                    pass
                break

    return {
        "asset_name": asset_name,
        "ticker": asset_ticker,
        "asset_type_code": asset_type_code,
        "asset_type": asset_type,
        "transaction_type": transaction_type or "unknown",
        "value_low": value_info.get("value_low"),
        "value_high": value_info.get("value_high"),
        "transaction_date": transaction_date,
        "notification_date": notification_date,
    }


# =============================================================================
# SENATE SCRAPING FUNCTIONS
# =============================================================================


async def accept_senate_agreement(client: httpx.AsyncClient) -> bool:
    """
    Accept the Senate EFD usage agreement.

    The Senate EFD site requires accepting terms before searching.
    This function visits the home page, gets the CSRF token, and submits the agreement.
    """
    try:
        # Visit home page to get cookies and CSRF token
        response = await client.get(
            f"{SENATE_BASE_URL}/search/home/",
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=30.0,
        )

        soup = BeautifulSoup(response.text, "html.parser")

        # Look for CSRF token
        csrf_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
        csrf_token = csrf_input.get("value") if csrf_input else None

        # Submit agreement form
        form_data = {
            "prohibition_agreement": "1",  # Checkbox checked
        }
        if csrf_token:
            form_data["csrfmiddlewaretoken"] = csrf_token

        # Submit the agreement
        agree_response = await client.post(
            f"{SENATE_BASE_URL}/search/home/",
            data=form_data,
            headers={
                "User-Agent": USER_AGENT,
                "Referer": f"{SENATE_BASE_URL}/search/home/",
            },
            follow_redirects=True,
            timeout=30.0,
        )

        # Check if we now have access to search
        if agree_response.status_code == 200:
            # Look for search form elements to verify we have access
            agree_soup = BeautifulSoup(agree_response.text, "html.parser")

            # Check if we're now on the search page (has first_name input)
            if agree_soup.find("input", {"name": "first_name"}):
                logger.info("Successfully accepted Senate EFD agreement")
                return True

            # Check if there's still an agreement checkbox
            if agree_soup.find("input", {"name": "prohibition_agreement"}):
                logger.warning("Agreement not accepted - checkbox still present")
                return False

            # Assume success if no obvious failure
            logger.info("Senate EFD agreement likely accepted")
            return True

        logger.warning(f"Failed to accept agreement: {agree_response.status_code}")
        return False

    except Exception as e:
        logger.error(f"Error accepting Senate agreement: {e}")
        return False


async def fetch_senate_ptr_list(
    client: httpx.AsyncClient,
    lookback_days: int = 30,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Fetch list of Senate PTR filings via AJAX search.

    Uses the DataTables AJAX endpoint to get PTR (Periodic Transaction Report) filings.
    Returns a list of disclosures with politician name, filing date, and source URL.
    """
    disclosures = []

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)

    try:
        # First, accept the usage agreement
        if not await accept_senate_agreement(client):
            logger.warning("Could not accept Senate EFD agreement, proceeding anyway")

        # Get CSRF token from cookie
        csrf_token = client.cookies.get("csrftoken", "")

        # Use the DataTables AJAX endpoint
        ajax_data = {
            "draw": "1",
            "start": "0",
            "length": str(limit),
            "report_types": '["11"]',  # 11 = PTR
            "filer_types": '["1"]',    # 1 = Senator
            "submitted_start_date": start_date.strftime("%m/%d/%Y"),
            "submitted_end_date": end_date.strftime("%m/%d/%Y"),
            "candidate_state": "",
            "senator_state": "",
            "office_id": "",
            "first_name": "",
            "last_name": "",
        }

        response = await client.post(
            f"{SENATE_BASE_URL}/search/report/data/",
            data=ajax_data,
            headers={
                "User-Agent": USER_AGENT,
                "Referer": f"{SENATE_BASE_URL}/search/",
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": csrf_token,
                "Accept": "application/json",
            },
            timeout=60.0,
        )

        if response.status_code == 200:
            try:
                data = response.json()
                records = data.get("data", [])
                logger.info(f"AJAX search returned {len(records)} records")

                for record in records:
                    # Record format: [first_name, last_name, office, report_type, date, link_html]
                    if len(record) >= 5:
                        first_name = record[0] if record[0] else ""
                        last_name = record[1] if record[1] else ""
                        full_name = f"{first_name} {last_name}".strip()
                        filing_date_str = record[4] if len(record) > 4 else ""

                        # Parse link from HTML
                        link_html = record[5] if len(record) > 5 else ""
                        link_match = re.search(r'href="([^"]+)"', link_html)
                        report_url = None
                        doc_id = None
                        if link_match:
                            href = link_match.group(1)
                            report_url = f"{SENATE_BASE_URL}{href}" if not href.startswith("http") else href
                            # Extract UUID from URL like /search/view/ptr/83de647b-ddf0-49c3-bd56-8b32f23c0e78/
                            uuid_match = re.search(r'/ptr/([a-f0-9-]+)/', href)
                            if uuid_match:
                                doc_id = uuid_match.group(1)

                        # Parse filing date
                        filing_date = None
                        if filing_date_str:
                            try:
                                filing_date = datetime.strptime(filing_date_str, "%m/%d/%Y").isoformat()
                            except ValueError:
                                pass

                        if full_name and report_url:
                            disclosures.append({
                                "politician_name": full_name,
                                "report_type": "PTR",
                                "filing_date": filing_date,
                                "source_url": report_url,
                                "doc_id": doc_id,
                            })

                logger.info(f"Parsed {len(disclosures)} Senate disclosures from AJAX")
                return disclosures

            except Exception as e:
                logger.warning(f"Failed to parse AJAX response: {e}")

        elif response.status_code == 503:
            logger.warning("Senate EFD AJAX endpoint under maintenance, skipping")
            return []
        else:
            logger.warning(f"AJAX search failed: {response.status_code}")

    except Exception as e:
        logger.error(f"Error fetching Senate PTR list: {e}", exc_info=True)

    return disclosures


async def parse_ptr_page(
    client: httpx.AsyncClient,
    url: str,
) -> List[Dict[str, Any]]:
    """
    Parse a Senate PTR page to extract transactions.

    PTR pages have a table with columns:
    #, Transaction Date, Owner, Ticker, Asset Name, Asset Type, Type, Amount, Comment
    """
    transactions = []

    try:
        response = await client.get(
            url,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=30.0,
        )

        if response.status_code != 200:
            logger.warning(f"Failed to fetch PTR page {url}: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        # Get filing date from h1
        h1 = soup.find("h1")
        filing_date = None
        if h1:
            date_match = re.search(r"for\s+(\d{1,2}/\d{1,2}/\d{4})", h1.get_text())
            if date_match:
                try:
                    filing_date = datetime.strptime(date_match.group(1), "%m/%d/%Y").isoformat()
                except ValueError:
                    pass

        # Find the transaction table
        table = soup.find("table", class_="table-striped")
        if not table:
            table = soup.find("table")

        if not table:
            logger.debug(f"No table found on PTR page {url}")
            return []

        # Get header row to understand column order
        thead = table.find("thead")
        headers = []
        if thead:
            headers = [th.get_text(strip=True).lower() for th in thead.find_all("th")]

        # Default column mapping if headers not found
        col_map = {
            "transaction_date": 1,
            "owner": 2,
            "ticker": 3,
            "asset_name": 4,
            "asset_type": 5,
            "type": 6,
            "amount": 7,
            "comment": 8,
        }

        # Update column map based on actual headers
        for i, header in enumerate(headers):
            if "date" in header and "transaction" in header:
                col_map["transaction_date"] = i
            elif "owner" in header:
                col_map["owner"] = i
            elif "ticker" in header:
                col_map["ticker"] = i
            elif "asset" in header and "name" in header:
                col_map["asset_name"] = i
            elif "asset" in header and "type" in header:
                col_map["asset_type"] = i
            elif "type" in header and "asset" not in header:
                col_map["type"] = i
            elif "amount" in header:
                col_map["amount"] = i

        # Parse table rows
        tbody = table.find("tbody")
        rows = tbody.find_all("tr") if tbody else table.find_all("tr")[1:]

        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 6:
                continue

            def get_cell(key: str) -> str:
                idx = col_map.get(key, -1)
                if 0 <= idx < len(cells):
                    return cells[idx].get_text(strip=True)
                return ""

            # Extract transaction data
            transaction_date_str = get_cell("transaction_date")
            ticker = get_cell("ticker")
            asset_name = get_cell("asset_name")
            asset_type = get_cell("asset_type")
            transaction_type_str = get_cell("type")
            amount_str = get_cell("amount")

            # Clean ticker
            if ticker == "--" or ticker == "N/A":
                ticker = None

            # Parse transaction date
            transaction_date = None
            if transaction_date_str:
                try:
                    transaction_date = datetime.strptime(transaction_date_str, "%m/%d/%Y").isoformat()
                except ValueError:
                    pass

            # Parse transaction type
            transaction_type = "unknown"
            if transaction_type_str:
                type_lower = transaction_type_str.lower()
                if "purchase" in type_lower or "buy" in type_lower:
                    transaction_type = "purchase"
                elif "sale" in type_lower or "sell" in type_lower or "sold" in type_lower:
                    transaction_type = "sale"
                elif "exchange" in type_lower:
                    transaction_type = "exchange"

            # Parse amount
            value_info = parse_value_range(amount_str)

            if asset_name and asset_name != "--":
                transactions.append({
                    "asset_name": sanitize_string(asset_name),
                    "ticker": ticker,
                    "asset_type": asset_type if asset_type != "--" else None,
                    "transaction_type": transaction_type,
                    "transaction_date": transaction_date,
                    "notification_date": filing_date,
                    "value_low": value_info.get("value_low"),
                    "value_high": value_info.get("value_high"),
                })

        logger.debug(f"Parsed {len(transactions)} transactions from PTR page")

    except Exception as e:
        logger.error(f"Error parsing PTR page {url}: {e}")

    return transactions


async def download_senate_pdf(
    client: httpx.AsyncClient,
    url: str,
) -> Optional[bytes]:
    """Download a Senate disclosure PDF."""
    try:
        await rate_limiter.wait()

        response = await client.get(
            url,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=60.0,
        )

        if response.status_code == 200:
            content = response.content
            if content.startswith(b"%PDF"):
                rate_limiter.record_success()
                return content
            else:
                logger.warning(f"Downloaded content is not a PDF from {url}")
                return None
        elif response.status_code in {429, 503, 502, 504}:
            rate_limiter.record_error(is_rate_limit=True)
        else:
            rate_limiter.record_error()
            logger.warning(f"Failed to download PDF from {url}: {response.status_code}")

    except Exception as e:
        rate_limiter.record_error()
        logger.error(f"Error downloading PDF: {e}")

    return None


async def process_senate_disclosure(
    client: httpx.AsyncClient,
    supabase: Client,
    disclosure: Dict[str, Any],
) -> int:
    """
    Process a single Senate disclosure.

    Senate disclosures are HTML pages, not PDFs. We parse the transaction
    table directly from the page.
    """
    transactions_uploaded = 0

    source_url = disclosure.get("source_url")
    if not source_url:
        return 0

    # Apply rate limiting
    await rate_limiter.wait()

    # Parse the PTR page directly (it's HTML, not PDF)
    transactions = await parse_ptr_page(client, source_url)

    if not transactions:
        logger.debug(f"No transactions found for {disclosure.get('politician_name')}")
        rate_limiter.record_success()
        return 0

    # Find or create politician
    politician_id = find_or_create_politician(
        supabase, disclosure.get("politician_name")
    )

    if not politician_id:
        logger.warning(f"Could not find/create politician: {disclosure.get('politician_name')}")
        return 0

    # Upload each transaction
    for transaction in transactions:
        result = upload_transaction_to_supabase(
            supabase, politician_id, transaction, disclosure
        )
        if result:
            transactions_uploaded += 1

    rate_limiter.record_success()
    return transactions_uploaded


# =============================================================================
# MAIN ETL FUNCTION
# =============================================================================


async def run_senate_etl(
    job_id: str,
    lookback_days: int = 30,
    limit: Optional[int] = None,
    update_mode: bool = False,
) -> None:
    """
    Run the Senate ETL pipeline.

    Args:
        job_id: Unique job identifier for status tracking
        lookback_days: How many days back to search for disclosures
        limit: Maximum number of disclosures to process
        update_mode: If True, upsert instead of skip existing
    """
    JOB_STATUS[job_id]["status"] = "running"
    JOB_STATUS[job_id]["message"] = "Fetching Senate PTR list..."

    total_transactions = 0
    disclosures_processed = 0
    errors = 0

    try:
        # Get Supabase client
        supabase = get_supabase_client()

        async with httpx.AsyncClient() as client:
            # Fetch list of disclosures
            disclosures = await fetch_senate_ptr_list(
                client,
                lookback_days=lookback_days,
                limit=limit or 100,
            )

            JOB_STATUS[job_id]["total"] = len(disclosures)
            JOB_STATUS[job_id]["message"] = f"Processing {len(disclosures)} disclosures..."

            logger.info(f"[Senate ETL] Processing {len(disclosures)} disclosures")

            # Process each disclosure
            for i, disclosure in enumerate(disclosures):
                try:
                    transactions = await process_senate_disclosure(
                        client, supabase, disclosure
                    )
                    total_transactions += transactions
                    disclosures_processed += 1

                    JOB_STATUS[job_id]["progress"] = i + 1
                    JOB_STATUS[job_id]["message"] = (
                        f"Processed {i + 1}/{len(disclosures)} disclosures, "
                        f"{total_transactions} transactions uploaded"
                    )

                except Exception as e:
                    errors += 1
                    logger.error(f"Error processing disclosure: {e}")
                    continue

        # Update final status
        JOB_STATUS[job_id]["status"] = "completed"
        JOB_STATUS[job_id]["message"] = (
            f"Completed: {disclosures_processed} disclosures processed, "
            f"{total_transactions} transactions uploaded, "
            f"{errors} errors"
        )
        JOB_STATUS[job_id]["completed_at"] = datetime.utcnow().isoformat()

        logger.info(
            f"[Senate ETL] Completed: {disclosures_processed} disclosures, "
            f"{total_transactions} transactions, {errors} errors"
        )

    except Exception as e:
        JOB_STATUS[job_id]["status"] = "error"
        JOB_STATUS[job_id]["message"] = f"ETL failed: {str(e)}"
        JOB_STATUS[job_id]["completed_at"] = datetime.utcnow().isoformat()
        logger.error(f"[Senate ETL] Failed: {e}", exc_info=True)
        raise
