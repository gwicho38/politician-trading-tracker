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
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup
from supabase import Client

from app.lib.parser import (
    extract_ticker_from_text,
    sanitize_string,
    parse_asset_type,
    parse_value_range,
    clean_asset_name,
    is_header_row,
)
from app.lib.database import get_supabase, upload_transaction_to_supabase
from app.lib.pdf_utils import extract_text_from_pdf, extract_tables_from_pdf
from app.lib.politician import find_or_create_politician

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import shared job status from house_etl
from app.services.house_etl import JOB_STATUS, RateLimiter
from app.lib.parser import VALUE_PATTERNS, ASSET_TYPE_CODES

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
        bioguide_id = senator.get("bioguide_id")

        # First check if politician exists by bioguide_id
        if bioguide_id:
            response = (
                supabase.table("politicians")
                .select("id")
                .eq("bioguide_id", bioguide_id)
                .limit(1)
                .execute()
            )

            if response.data:
                # Update existing politician
                politician_id = response.data[0]["id"]
                supabase.table("politicians").update({
                    "first_name": senator.get("first_name"),
                    "last_name": senator.get("last_name"),
                    "full_name": senator["full_name"],
                    "party": senator.get("party"),
                    "state_or_country": senator.get("state"),
                    "role": "Senator",
                }).eq("id", politician_id).execute()

                return politician_id

        # Fall back to name-based matching using the fallback function
        return _upsert_senator_by_name(supabase, senator)

    except Exception as e:
        logger.error(f"Error upserting senator {senator['full_name']}: {e}")
        # Try the fallback
        return _upsert_senator_by_name(supabase, senator)

    return None


def _upsert_senator_by_name(supabase: Client, senator: Dict[str, Any]) -> Optional[str]:
    """Fallback: upsert senator by name matching only."""
    try:
        # Try to find by last name in full_name column
        response = (
            supabase.table("politicians")
            .select("id")
            .ilike("full_name", f"%{senator['last_name']}%")
            .eq("role", "Senator")
            .limit(1)
            .execute()
        )

        if response.data:
            politician_id = response.data[0]["id"]
            supabase.table("politicians").update({
                "first_name": senator.get("first_name"),
                "last_name": senator.get("last_name"),
                "full_name": senator["full_name"],
                "party": senator.get("party"),
                "state_or_country": senator.get("state"),
                "bioguide_id": senator.get("bioguide_id"),
            }).eq("id", politician_id).execute()
            return politician_id

        # Try searching by last_name column
        response = (
            supabase.table("politicians")
            .select("id")
            .ilike("last_name", f"%{senator['last_name']}%")
            .limit(1)
            .execute()
        )

        if response.data:
            politician_id = response.data[0]["id"]
            supabase.table("politicians").update({
                "first_name": senator.get("first_name"),
                "last_name": senator.get("last_name"),
                "full_name": senator["full_name"],
                "party": senator.get("party"),
                "state_or_country": senator.get("state"),
                "role": "Senator",
                "bioguide_id": senator.get("bioguide_id"),
            }).eq("id", politician_id).execute()
            return politician_id

        # Create new
        response = supabase.table("politicians").insert({
            "first_name": senator.get("first_name"),
            "last_name": senator.get("last_name"),
            "full_name": senator["full_name"],
            "party": senator.get("party"),
            "state_or_country": senator.get("state"),
            "role": "Senator",
            "bioguide_id": senator.get("bioguide_id"),
        }).execute()

        if response.data:
            logger.info(f"Created new senator: {senator['full_name']}")
            return response.data[0]["id"]

    except Exception as e:
        logger.error(f"Error in name-based upsert for {senator['full_name']}: {e}")

    return None


# Note: find_or_create_politician moved to app.lib.politician
# Note: clean_asset_name moved to app.lib.parser
# Note: upload_transaction_to_supabase moved to app.lib.database
# Note: extract_tables_from_pdf, extract_text_from_pdf moved to app.lib.pdf_utils
# Note: is_header_row moved to app.lib.parser


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

    # Skip rows that lack BOTH transaction type AND value info
    # These are likely footer rows or incomplete data
    has_transaction_type = transaction_type is not None
    has_value_info = value_info.get("value_low") is not None or value_info.get("value_high") is not None

    if not has_transaction_type and not has_value_info:
        return None

    return {
        "asset_name": asset_name,
        "asset_ticker": asset_ticker,
        "asset_type_code": asset_type_code,
        "asset_type": asset_type,
        "transaction_type": transaction_type or "unknown",
        "value_low": value_info.get("value_low"),
        "value_high": value_info.get("value_high"),
        "transaction_date": transaction_date,
        "notification_date": notification_date,
    }


# =============================================================================
# PLAYWRIGHT-BASED SENATE SCRAPING (bypasses anti-bot protection)
# =============================================================================


async def search_all_ptr_disclosures_playwright(
    lookback_days: int = 30,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Search for all PTR disclosures using Playwright browser automation.

    The Senate EFD site has anti-bot protection that blocks programmatic AJAX requests.
    Using a real browser (Playwright) bypasses this protection.

    Returns list of disclosure metadata (source_url, filing_date, politician_name, etc.)
    """
    from playwright.async_api import async_playwright

    disclosures = []

    try:
        logger.info("[Playwright] Starting browser automation for EFD search...")
        async with async_playwright() as p:
            # Launch headless browser with Docker-compatible flags
            logger.info("[Playwright] Launching Chromium browser...")
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--no-first-run",
                    "--no-zygote",
                    "--disable-software-rasterizer",
                    "--disable-background-networking",
                    "--disable-default-apps",
                    "--disable-sync",
                    "--disable-translate",
                    "--mute-audio",
                    "--hide-scrollbars",
                    "--metrics-recording-only",
                ],
            )
            logger.info("[Playwright] Browser launched successfully")
            context = await browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 720},
            )
            logger.info("[Playwright] Created browser context")
            logger.info("[Playwright] Creating new page (with 60s timeout)...")
            try:
                page = await asyncio.wait_for(context.new_page(), timeout=60.0)
            except asyncio.TimeoutError:
                logger.error("[Playwright] TIMEOUT: new_page() took longer than 60s")
                raise Exception("Failed to create new page - timeout after 60s")
            logger.info("[Playwright] Created new page successfully")

            # Step 1: Navigate to home page and accept agreement
            logger.info("[Playwright] Navigating to Senate EFD home page...")
            await page.goto(f"{SENATE_BASE_URL}/search/home/", wait_until="domcontentloaded", timeout=60000)
            logger.info("[Playwright] Page loaded, checking for agreement")

            # Accept agreement by clicking checkbox
            checkbox = page.locator("input[name='prohibition_agreement']")
            if await checkbox.count() > 0:
                await checkbox.click()
                logger.info("[Playwright] Accepted usage agreement")
                await page.wait_for_url("**/search/", timeout=10000)

            # Step 2: Fill search form
            logger.info("[Playwright] Filling search form for PTRs")

            # Check "Senator" checkbox
            await page.locator("text=Senator").first.click()

            # Check "Periodic Transactions" checkbox
            await page.locator("text=Periodic Transactions").click()

            # Click Search button
            await page.locator("button:has-text('Search Reports')").click()

            # Wait for results to load
            await page.wait_for_selector("table#filedReports tbody tr", timeout=30000)

            # Step 3: Parse ALL pages of results (handle pagination)
            page_num = 1
            total_pages = None

            while True:
                logger.info(f"[Playwright] Parsing results page {page_num}")

                # Wait for table to be populated
                await page.wait_for_selector("table#filedReports tbody tr", timeout=10000)

                # Get the status text to know total records
                status_text = await page.locator(".dataTables_info").text_content()
                logger.debug(f"[Playwright] Status: {status_text}")

                # Parse the table rows
                rows = await page.locator("table#filedReports tbody tr").all()

                for row in rows:
                    cells = await row.locator("td").all()
                    if len(cells) >= 5:
                        first_name = await cells[0].text_content()
                        last_name = await cells[1].text_content()
                        office = await cells[2].text_content()
                        report_cell = cells[3]
                        date_filed = await cells[4].text_content()

                        # Get the link from report cell
                        link = report_cell.locator("a")
                        if await link.count() > 0:
                            href = await link.get_attribute("href")
                            report_text = await link.text_content()

                            # Only include PTRs
                            if "Periodic" in (report_text or ""):
                                full_name = f"{first_name.strip()} {last_name.strip()}"

                                # Parse filing date
                                filing_date = None
                                if date_filed:
                                    try:
                                        filing_date = datetime.strptime(
                                            date_filed.strip(), "%m/%d/%Y"
                                        ).isoformat()
                                    except ValueError:
                                        pass

                                # Build full URL
                                if href and not href.startswith("http"):
                                    href = f"{SENATE_BASE_URL}{href}"

                                # Extract doc_id from URL
                                doc_id = None
                                uuid_match = re.search(r'/(?:ptr|paper)/([a-f0-9-]+)/', href or "")
                                if uuid_match:
                                    doc_id = uuid_match.group(1)

                                disclosures.append({
                                    "politician_name": full_name,
                                    "first_name": first_name.strip() if first_name else "",
                                    "last_name": last_name.strip() if last_name else "",
                                    "report_type": "PTR",
                                    "filing_date": filing_date,
                                    "source_url": href,
                                    "doc_id": doc_id,
                                    "is_paper": "/paper/" in (href or ""),
                                })

                # Check limit
                if limit and len(disclosures) >= limit:
                    logger.info(f"[Playwright] Reached limit of {limit} disclosures")
                    break

                # Check if there's a next page (pagination)
                next_button = page.locator(".paginate_button.next:not(.disabled)")
                if await next_button.count() > 0:
                    await next_button.click()
                    # Wait for table to update (AJAX reload)
                    await page.wait_for_timeout(500)
                    await page.wait_for_load_state("networkidle")
                    page_num += 1

                    # Safety limit to avoid infinite loops
                    if page_num > 100:
                        logger.warning("[Playwright] Reached max page limit (100)")
                        break
                else:
                    logger.info(f"[Playwright] No more pages (processed {page_num} pages)")
                    break

            await browser.close()

    except Exception as e:
        logger.error(f"[Playwright] Error during search: {e}", exc_info=True)

    logger.info(f"[Playwright] Found {len(disclosures)} total PTR disclosures")
    return disclosures


async def parse_ptr_page_playwright(
    page,  # Playwright page object
    url: str,
) -> List[Dict[str, Any]]:
    """
    Parse a PTR page using Playwright (required for session-protected pages).

    PTR pages have a table with transactions:
    #, Transaction Date, Owner, Ticker, Asset Name, Asset Type, Type, Amount, Comment
    """
    transactions = []

    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)

        # Check if we got redirected to agreement page
        if "/home/" in page.url:
            logger.warning(f"Redirected to home page when accessing {url}")
            return []

        # Wait for page to load
        await page.wait_for_load_state("domcontentloaded")

        # Get filing date from page title/header
        h1 = await page.locator("h1").first.text_content()
        filing_date = None
        if h1:
            date_match = re.search(r"for\s+(\d{1,2}/\d{1,2}/\d{4})", h1)
            if date_match:
                try:
                    filing_date = datetime.strptime(date_match.group(1), "%m/%d/%Y").isoformat()
                except ValueError:
                    pass

        # Find the transaction table
        table = page.locator("table.table-striped")
        if await table.count() == 0:
            table = page.locator("table").first

        if await table.count() == 0:
            logger.debug(f"No table found on PTR page {url}")
            return []

        # Parse table rows
        rows = await table.locator("tbody tr").all()
        if not rows:
            rows = await table.locator("tr").all()

        for row in rows:
            cells = await row.locator("td").all()
            if len(cells) < 6:
                continue

            # Get cell texts
            cell_texts = []
            for cell in cells:
                text = await cell.text_content()
                cell_texts.append(text.strip() if text else "")

            # Skip header rows
            if any(h in cell_texts[0].lower() for h in ["#", "transaction", "date", "owner"]):
                continue

            # Parse transaction fields (typical column order)
            # #, Transaction Date, Owner, Ticker, Asset Name, Asset Type, Type, Amount, Comment
            transaction_date_str = cell_texts[1] if len(cell_texts) > 1 else ""
            ticker = cell_texts[3] if len(cell_texts) > 3 else ""
            asset_name = cell_texts[4] if len(cell_texts) > 4 else ""
            asset_type = cell_texts[5] if len(cell_texts) > 5 else ""
            tx_type_str = cell_texts[6] if len(cell_texts) > 6 else ""
            amount_str = cell_texts[7] if len(cell_texts) > 7 else ""

            # Clean ticker
            if ticker in ["--", "N/A", ""]:
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
            if tx_type_str:
                type_lower = tx_type_str.lower()
                if "purchase" in type_lower or "buy" in type_lower:
                    transaction_type = "purchase"
                elif "sale" in type_lower or "sell" in type_lower or "sold" in type_lower:
                    transaction_type = "sale"
                elif "exchange" in type_lower:
                    transaction_type = "exchange"

            # Parse amount
            value_info = parse_value_range(amount_str)

            if asset_name and asset_name not in ["--", ""]:
                transactions.append({
                    "asset_name": sanitize_string(asset_name),
                    "asset_ticker": ticker,
                    "asset_type": asset_type if asset_type not in ["--", ""] else None,
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


async def process_disclosures_playwright(
    disclosures: List[Dict[str, Any]],
    supabase: Client,
) -> Tuple[int, int]:
    """
    Process disclosures using a single Playwright browser session.

    Returns (transactions_uploaded, errors)
    """
    from playwright.async_api import async_playwright

    total_transactions = 0
    errors = 0

    try:
        logger.info("[Playwright] Starting browser for disclosure processing...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--no-first-run",
                    "--no-zygote",
                    "--disable-software-rasterizer",
                    "--disable-background-networking",
                    "--disable-default-apps",
                    "--disable-sync",
                    "--disable-translate",
                    "--mute-audio",
                    "--hide-scrollbars",
                    "--metrics-recording-only",
                ],
            )
            logger.info("[Playwright] Browser launched for disclosure processing")
            context = await browser.new_context(user_agent=USER_AGENT)
            logger.info("[Playwright] Creating page for disclosure processing...")
            try:
                page = await asyncio.wait_for(context.new_page(), timeout=60.0)
            except asyncio.TimeoutError:
                logger.error("[Playwright] TIMEOUT: new_page() took longer than 60s")
                raise Exception("Failed to create new page - timeout after 60s")
            logger.info("[Playwright] Page created for disclosure processing")

            # Accept agreement first
            await page.goto(f"{SENATE_BASE_URL}/search/home/", wait_until="domcontentloaded", timeout=60000)
            checkbox = page.locator("input[name='prohibition_agreement']")
            if await checkbox.count() > 0:
                await checkbox.click()
                await page.wait_for_url("**/search/", timeout=10000)
            logger.info("[Playwright] Session established for processing")

            # Process each disclosure
            for i, disclosure in enumerate(disclosures):
                try:
                    # Skip paper filings (images, can't parse)
                    if disclosure.get("is_paper"):
                        logger.debug(f"Skipping paper filing: {disclosure.get('source_url')}")
                        continue

                    source_url = disclosure.get("source_url")
                    if not source_url:
                        continue

                    # Parse PTR page
                    transactions = await parse_ptr_page_playwright(page, source_url)

                    if not transactions:
                        continue

                    politician_id = disclosure.get("politician_id")
                    if not politician_id:
                        politician_id = find_or_create_politician(
                            supabase, name=disclosure.get("politician_name"), chamber="senate"
                        )

                    if not politician_id:
                        logger.warning(f"Could not find politician: {disclosure.get('politician_name')}")
                        continue

                    # Upload transactions
                    for transaction in transactions:
                        result = upload_transaction_to_supabase(
                            supabase, politician_id, transaction, disclosure
                        )
                        if result:
                            total_transactions += 1

                    # Rate limit
                    await page.wait_for_timeout(500)

                except Exception as e:
                    errors += 1
                    logger.error(f"Error processing disclosure {i}: {e}")

            await browser.close()

    except Exception as e:
        logger.error(f"[Playwright] Error in process_disclosures: {e}", exc_info=True)
        errors += 1

    return total_transactions, errors


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


async def fetch_senate_ptr_list_playwright(
    senators: List[Dict[str, Any]],
    lookback_days: int = 30,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch list of Senate PTR filings using Playwright browser automation.

    Uses a single browser session to search for all PTRs, then matches
    them to senators based on name.

    Returns a combined list of all disclosures found.
    """
    # Get all PTR disclosures in one batch search
    all_disclosures = await search_all_ptr_disclosures_playwright(
        lookback_days=lookback_days,
        limit=limit,
    )

    # Create a lookup for senators by last name
    senator_lookup = {}
    for senator in senators:
        last_name = senator.get("last_name", "").upper()
        if last_name:
            if last_name not in senator_lookup:
                senator_lookup[last_name] = []
            senator_lookup[last_name].append(senator)

    # Match disclosures to senators
    matched_disclosures = []
    for disclosure in all_disclosures:
        last_name = disclosure.get("last_name", "").upper()
        first_name = disclosure.get("first_name", "").upper()

        if last_name in senator_lookup:
            # Find best match by first name
            best_match = None
            for senator in senator_lookup[last_name]:
                senator_first = senator.get("first_name", "").upper()
                if senator_first and first_name.startswith(senator_first[:3]):
                    best_match = senator
                    break
            if not best_match:
                best_match = senator_lookup[last_name][0]

            disclosure["politician_id"] = best_match.get("politician_id")
            disclosure["politician_name"] = best_match.get("full_name")

        matched_disclosures.append(disclosure)

    logger.info(f"Matched {len(matched_disclosures)} disclosures to senators")
    return matched_disclosures


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
                    "asset_ticker": ticker,
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
            supabase, name=disclosure.get("politician_name"), chamber="senate"
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
    Run the Senate ETL pipeline using Playwright for anti-bot protection.

    Pipeline:
    1. Fetch current senators from Senate.gov XML feed
    2. Upsert senators to politicians table
    3. Use Playwright to search EFD for all PTR disclosures
    4. Parse PTR pages and upload transactions

    Args:
        job_id: Unique job identifier for status tracking
        lookback_days: How many days back to search for disclosures
        limit: Maximum number of disclosures to process (for testing)
        update_mode: If True, upsert instead of skip existing
    """
    JOB_STATUS[job_id]["status"] = "running"
    JOB_STATUS[job_id]["message"] = "Fetching senators from Senate.gov..."

    total_transactions = 0
    disclosures_processed = 0
    errors = 0

    try:
        # Get Supabase client
        supabase = get_supabase()

        # Step 1: Fetch senators from XML
        senators = await fetch_senators_from_xml()
        if not senators:
            JOB_STATUS[job_id]["status"] = "error"
            JOB_STATUS[job_id]["message"] = "Failed to fetch senators list"
            return

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

        # Step 3: Fetch disclosures using Playwright (bypasses anti-bot protection)
        JOB_STATUS[job_id]["message"] = "Searching EFD for disclosures (using browser)..."

        disclosures = await fetch_senate_ptr_list_playwright(
            senators=senators,
            lookback_days=lookback_days,
            limit=limit,
        )

        # Filter to electronic PTRs only (paper filings are images)
        electronic_disclosures = [d for d in disclosures if not d.get("is_paper")]
        paper_count = len(disclosures) - len(electronic_disclosures)

        JOB_STATUS[job_id]["total"] = len(electronic_disclosures)
        JOB_STATUS[job_id]["message"] = f"Processing {len(electronic_disclosures)} electronic disclosures ({paper_count} paper skipped)..."

        logger.info(f"[Senate ETL] Processing {len(electronic_disclosures)} electronic disclosures ({paper_count} paper skipped)")

        # Step 4: Process disclosures using Playwright (PTR pages also need session)
        total_transactions, errors = await process_disclosures_playwright(
            electronic_disclosures, supabase
        )
        disclosures_processed = len(electronic_disclosures) - errors

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
