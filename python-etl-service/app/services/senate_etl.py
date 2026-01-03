"""
US Senate Financial Disclosure ETL Service

Extracts Periodic Transaction Reports (PTRs) from the Senate EFD database.
Similar structure to house_etl.py but adapted for Senate disclosure format.

Data Source: https://efdsearch.senate.gov/search/
Senator List: https://www.senate.gov/general/contact_information/senators_cfm.xml

Approach:
1. Fetch current senators from Senate.gov XML feed
2. Upsert senators to politicians table (with bioguide_id for deduplication)
3. For each senator, search EFD by last name
4. Parse PTR pages and upload transactions
"""

import asyncio
import logging
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

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
SENATORS_XML_URL = "https://www.senate.gov/general/contact_information/senators_cfm.xml"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Global rate limiter instance
rate_limiter = RateLimiter()


# =============================================================================
# SENATOR LIST FETCHING
# =============================================================================


async def fetch_senators_from_xml() -> List[Dict[str, Any]]:
    """
    Fetch current senators from the official Senate.gov XML feed.

    Returns a list of senator dictionaries with:
    - first_name, last_name, party, state, bioguide_id
    """
    senators = []

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                SENATORS_XML_URL,
                headers={"User-Agent": USER_AGENT},
                timeout=30.0,
            )

            if response.status_code != 200:
                logger.error(f"Failed to fetch senators XML: {response.status_code}")
                return []

            # Parse XML
            root = ET.fromstring(response.text)

            for member in root.findall("member"):
                first_name = member.findtext("first_name", "").strip()
                last_name = member.findtext("last_name", "").strip()
                party = member.findtext("party", "").strip()
                state = member.findtext("state", "").strip()
                bioguide_id = member.findtext("bioguide_id", "").strip()

                if first_name and last_name:
                    senators.append({
                        "first_name": first_name,
                        "last_name": last_name,
                        "party": party,  # D, R, or I
                        "state": state,
                        "bioguide_id": bioguide_id,
                        "full_name": f"{first_name} {last_name}",
                    })

            logger.info(f"Fetched {len(senators)} senators from Senate.gov XML")

    except Exception as e:
        logger.error(f"Error fetching senators XML: {e}")

    return senators


def upsert_senator_to_db(supabase: Client, senator: Dict[str, Any]) -> Optional[str]:
    """
    Upsert a senator to the politicians table.

    Uses bioguide_id as the unique identifier to avoid duplicates.
    Returns the politician_id.
    """
    try:
        # Map party code to full name
        party_map = {"D": "Democratic", "R": "Republican", "I": "Independent"}
        party = party_map.get(senator.get("party"), senator.get("party"))

        # First check if politician exists by bioguide_id in raw_data
        bioguide_id = senator.get("bioguide_id")
        if bioguide_id:
            # Search for existing politician with this bioguide_id
            response = supabase.rpc(
                "find_politician_by_bioguide",
                {"p_bioguide_id": bioguide_id}
            ).execute()

            if response.data and len(response.data) > 0:
                # Update existing politician
                politician_id = response.data[0]["id"]
                supabase.table("politicians").update({
                    "name": senator["full_name"],
                    "party": party,
                    "state": senator.get("state"),
                    "position": "Senator",
                    "jurisdiction": "Federal",
                }).eq("id", politician_id).execute()

                return politician_id

        # Fall back to name-based matching
        response = (
            supabase.table("politicians")
            .select("id")
            .ilike("name", f"%{senator['last_name']}%")
            .eq("position", "Senator")
            .limit(1)
            .execute()
        )

        if response.data:
            # Update existing politician
            politician_id = response.data[0]["id"]
            supabase.table("politicians").update({
                "name": senator["full_name"],
                "party": party,
                "state": senator.get("state"),
                "raw_data": {"bioguide_id": bioguide_id} if bioguide_id else None,
            }).eq("id", politician_id).execute()

            return politician_id

        # Create new politician
        new_politician = {
            "name": senator["full_name"],
            "party": party,
            "state": senator.get("state"),
            "position": "Senator",
            "jurisdiction": "Federal",
            "raw_data": {"bioguide_id": bioguide_id} if bioguide_id else None,
        }

        response = supabase.table("politicians").insert(new_politician).execute()
        if response.data:
            logger.info(f"Created new senator: {senator['full_name']}")
            return response.data[0]["id"]

    except Exception as e:
        # If RPC doesn't exist, fall back to simple name search
        if "find_politician_by_bioguide" in str(e):
            logger.debug("bioguide RPC not found, using name-based matching")
            return _upsert_senator_by_name(supabase, senator)
        logger.error(f"Error upserting senator {senator['full_name']}: {e}")

    return None


def _upsert_senator_by_name(supabase: Client, senator: Dict[str, Any]) -> Optional[str]:
    """Fallback: upsert senator by name matching only."""
    try:
        party_map = {"D": "Democratic", "R": "Republican", "I": "Independent"}
        party = party_map.get(senator.get("party"), senator.get("party"))

        # Try to find by last name
        response = (
            supabase.table("politicians")
            .select("id")
            .ilike("name", f"%{senator['last_name']}%")
            .limit(1)
            .execute()
        )

        if response.data:
            politician_id = response.data[0]["id"]
            supabase.table("politicians").update({
                "name": senator["full_name"],
                "party": party,
                "state": senator.get("state"),
                "position": "Senator",
                "jurisdiction": "Federal",
            }).eq("id", politician_id).execute()
            return politician_id

        # Create new
        response = supabase.table("politicians").insert({
            "name": senator["full_name"],
            "party": party,
            "state": senator.get("state"),
            "position": "Senator",
            "jurisdiction": "Federal",
        }).execute()

        if response.data:
            logger.info(f"Created new senator: {senator['full_name']}")
            return response.data[0]["id"]

    except Exception as e:
        logger.error(f"Error in name-based upsert for {senator['full_name']}: {e}")

    return None


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


async def search_senator_disclosures(
    client: httpx.AsyncClient,
    senator: Dict[str, Any],
    lookback_days: int = 30,
) -> List[Dict[str, Any]]:
    """
    Search for a senator's disclosures using the two-step EFD search flow.

    Step 1: POST to /search/ with last_name to set up session
    Step 2: POST to /search/report/data/ with DataTables params to get results
    Step 3: Handle pagination if needed

    Returns list of disclosure metadata (source_url, filing_date, etc.)
    """
    disclosures = []
    last_name = senator.get("last_name", "")

    if not last_name:
        return []

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)

    # Use a long date range to get historical data
    # The EFD site has data going back to 2012
    start_date_str = "01/01/2012 00:00:00"
    end_date_str = end_date.strftime("%m/%d/%Y %H:%M:%S")

    try:
        # Get CSRF token from cookie
        csrf_token = client.cookies.get("csrftoken", "")

        # Step 1: POST to /search/ to set up session with last_name filter
        search_data = {
            "first_name": "",
            "last_name": last_name,
            "submitted_start_date": "",
            "submitted_end_date": "",
            "csrfmiddlewaretoken": csrf_token,
        }

        search_response = await client.post(
            SENATE_SEARCH_URL,
            data=search_data,
            headers={
                "User-Agent": USER_AGENT,
                "Referer": SENATE_SEARCH_URL,
                "Origin": SENATE_BASE_URL,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            follow_redirects=True,
            timeout=30.0,
        )

        if search_response.status_code != 200:
            logger.warning(f"Search POST failed for {last_name}: {search_response.status_code}")
            return []

        # Update CSRF token if it changed
        csrf_token = client.cookies.get("csrftoken", csrf_token)

        # Step 2: POST to DataTables endpoint with pagination
        page_start = 0
        page_size = 100
        total_records = None

        while total_records is None or page_start < total_records:
            # DataTables AJAX request format
            ajax_data = {
                "draw": str(page_start // page_size + 1),
                "columns[0][data]": "0",
                "columns[0][name]": "",
                "columns[0][searchable]": "true",
                "columns[0][orderable]": "true",
                "columns[1][data]": "1",
                "columns[1][name]": "",
                "columns[1][searchable]": "true",
                "columns[1][orderable]": "true",
                "columns[2][data]": "2",
                "columns[2][name]": "",
                "columns[2][searchable]": "true",
                "columns[2][orderable]": "true",
                "columns[3][data]": "3",
                "columns[3][name]": "",
                "columns[3][searchable]": "true",
                "columns[3][orderable]": "true",
                "columns[4][data]": "4",
                "columns[4][name]": "",
                "columns[4][searchable]": "true",
                "columns[4][orderable]": "true",
                "columns[5][data]": "5",
                "columns[5][name]": "",
                "columns[5][searchable]": "false",
                "columns[5][orderable]": "false",
                "order[0][column]": "4",  # Order by date
                "order[0][dir]": "desc",  # Newest first
                "start": str(page_start),
                "length": str(page_size),
                "search[value]": "",
                "search[regex]": "false",
                "report_types": '["11"]',  # 11 = PTR (Periodic Transaction Report)
                "filer_types": '["1","2","3","4","5"]',  # All filer types
                "submitted_start_date": start_date_str,
                "submitted_end_date": end_date_str,
                "candidate_state": "",
                "senator_state": "",
                "office_id": "",
                "first_name": "",
                "last_name": last_name,
            }

            ajax_response = await client.post(
                f"{SENATE_BASE_URL}/search/report/data/",
                data=ajax_data,
                headers={
                    "User-Agent": USER_AGENT,
                    "Referer": SENATE_SEARCH_URL,
                    "Origin": SENATE_BASE_URL,
                    "X-Requested-With": "XMLHttpRequest",
                    "X-CSRFToken": csrf_token,
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                },
                timeout=60.0,
            )

            if ajax_response.status_code == 503:
                logger.warning(f"EFD AJAX endpoint under maintenance for {last_name}")
                break

            if ajax_response.status_code != 200:
                logger.warning(f"AJAX search failed for {last_name}: {ajax_response.status_code}")
                break

            try:
                data = ajax_response.json()
                records = data.get("data", [])
                total_records = data.get("recordsTotal", 0)

                logger.debug(f"Page {page_start//page_size + 1}: {len(records)} records for {last_name}")

                for record in records:
                    disclosure = parse_datatables_record(record, senator)
                    if disclosure:
                        disclosures.append(disclosure)

                # Move to next page
                page_start += page_size

                # Limit to recent records based on lookback_days
                if page_start >= min(total_records, 500):  # Cap at 500 records per senator
                    break

                # Rate limit between pages
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.warning(f"Failed to parse AJAX response for {last_name}: {e}")
                break

        logger.info(f"Found {len(disclosures)} PTR disclosures for {senator['full_name']}")

    except Exception as e:
        logger.error(f"Error searching disclosures for {last_name}: {e}")

    return disclosures


def parse_datatables_record(record: List, senator: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse a DataTables record from the EFD search results.

    Record format: [first_name, last_name, office, report_type, date, link_html]
    """
    if len(record) < 5:
        return None

    try:
        first_name = record[0] if record[0] else ""
        last_name = record[1] if record[1] else ""
        full_name = f"{first_name} {last_name}".strip()
        report_type = record[3] if len(record) > 3 else ""
        filing_date_str = record[4] if len(record) > 4 else ""
        link_html = record[5] if len(record) > 5 else ""

        # Only process PTR (Periodic Transaction Reports)
        if "Periodic" not in report_type:
            return None

        # Parse link from HTML
        link_match = re.search(r'href="([^"]+)"', link_html)
        if not link_match:
            return None

        href = link_match.group(1)
        report_url = f"{SENATE_BASE_URL}{href}" if not href.startswith("http") else href

        # Extract UUID from URL like /search/view/ptr/83de647b-ddf0-49c3-bd56-8b32f23c0e78/
        uuid_match = re.search(r'/ptr/([a-f0-9-]+)/', href)
        doc_id = uuid_match.group(1) if uuid_match else None

        # Parse filing date
        filing_date = None
        if filing_date_str:
            try:
                filing_date = datetime.strptime(filing_date_str, "%m/%d/%Y").isoformat()
            except ValueError:
                pass

        return {
            "politician_name": full_name or senator.get("full_name"),
            "politician_id": senator.get("politician_id"),  # If we have it
            "report_type": "PTR",
            "filing_date": filing_date,
            "source_url": report_url,
            "doc_id": doc_id,
        }

    except Exception as e:
        logger.debug(f"Error parsing DataTables record: {e}")
        return None


async def fetch_senate_ptr_list(
    client: httpx.AsyncClient,
    senators: List[Dict[str, Any]],
    lookback_days: int = 30,
) -> List[Dict[str, Any]]:
    """
    Fetch list of Senate PTR filings for all senators.

    Iterates through each senator and searches for their disclosures.
    Returns a combined list of all disclosures found.
    """
    all_disclosures = []

    # First, accept the usage agreement
    if not await accept_senate_agreement(client):
        logger.warning("Could not accept Senate EFD agreement, proceeding anyway")

    # Search for each senator
    for i, senator in enumerate(senators):
        try:
            logger.info(f"Searching disclosures for {senator['full_name']} ({i+1}/{len(senators)})")

            disclosures = await search_senator_disclosures(
                client, senator, lookback_days
            )
            all_disclosures.extend(disclosures)

            # Rate limit between senators
            await asyncio.sleep(1.0)

        except Exception as e:
            logger.error(f"Error searching for {senator['full_name']}: {e}")
            continue

    logger.info(f"Total: {len(all_disclosures)} PTR disclosures from {len(senators)} senators")
    return all_disclosures


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

    # Use politician_id from disclosure if already set, otherwise find/create
    politician_id = disclosure.get("politician_id")
    if not politician_id:
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

    Pipeline:
    1. Fetch current senators from Senate.gov XML feed
    2. Upsert senators to politicians table
    3. For each senator, search EFD for PTR disclosures
    4. Parse PTR pages and upload transactions

    Args:
        job_id: Unique job identifier for status tracking
        lookback_days: How many days back to search for disclosures
        limit: Maximum number of senators to process (for testing)
        update_mode: If True, upsert instead of skip existing
    """
    JOB_STATUS[job_id]["status"] = "running"
    JOB_STATUS[job_id]["message"] = "Fetching senators from Senate.gov..."

    total_transactions = 0
    disclosures_processed = 0
    senators_processed = 0
    errors = 0

    try:
        # Get Supabase client
        supabase = get_supabase_client()

        # Step 1: Fetch senators from XML
        senators = await fetch_senators_from_xml()
        if not senators:
            JOB_STATUS[job_id]["status"] = "error"
            JOB_STATUS[job_id]["message"] = "Failed to fetch senators list"
            return

        # Apply limit if specified (for testing)
        if limit and limit < len(senators):
            logger.info(f"Limiting to first {limit} senators")
            senators = senators[:limit]

        JOB_STATUS[job_id]["message"] = f"Upserting {len(senators)} senators to database..."
        logger.info(f"[Senate ETL] Upserting {len(senators)} senators to database")

        # Step 2: Upsert senators to database
        senator_ids = {}
        for senator in senators:
            politician_id = upsert_senator_to_db(supabase, senator)
            if politician_id:
                senator["politician_id"] = politician_id
                senator_ids[senator["last_name"]] = politician_id

        logger.info(f"[Senate ETL] Upserted {len(senator_ids)} senators")

        async with httpx.AsyncClient() as client:
            # Step 3: Fetch disclosures for all senators
            JOB_STATUS[job_id]["message"] = f"Searching EFD for disclosures..."

            disclosures = await fetch_senate_ptr_list(
                client,
                senators=senators,
                lookback_days=lookback_days,
            )

            JOB_STATUS[job_id]["total"] = len(disclosures)
            JOB_STATUS[job_id]["message"] = f"Processing {len(disclosures)} disclosures..."

            logger.info(f"[Senate ETL] Processing {len(disclosures)} disclosures")

            # Step 4: Process each disclosure
            for i, disclosure in enumerate(disclosures):
                try:
                    # Use politician_id from senator search if available
                    if not disclosure.get("politician_id"):
                        # Try to match by name
                        politician_id = find_or_create_politician(
                            supabase, disclosure.get("politician_name")
                        )
                        disclosure["politician_id"] = politician_id

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
            f"Completed: {len(senators)} senators, {disclosures_processed} disclosures, "
            f"{total_transactions} transactions, {errors} errors"
        )
        JOB_STATUS[job_id]["completed_at"] = datetime.utcnow().isoformat()

        logger.info(
            f"[Senate ETL] Completed: {len(senators)} senators, {disclosures_processed} disclosures, "
            f"{total_transactions} transactions, {errors} errors"
        )

    except Exception as e:
        JOB_STATUS[job_id]["status"] = "error"
        JOB_STATUS[job_id]["message"] = f"ETL failed: {str(e)}"
        JOB_STATUS[job_id]["completed_at"] = datetime.utcnow().isoformat()
        logger.error(f"[Senate ETL] Failed: {e}", exc_info=True)
        raise
