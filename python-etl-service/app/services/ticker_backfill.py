"""
Ticker backfill service - fills in missing tickers for trading disclosures.
"""

import os
import re
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Job status tracking (shared with house_etl)
from app.services.house_etl import JOB_STATUS
from app.lib.parser import extract_ticker_from_text
from app.lib.database import get_supabase

def extract_ticker_from_asset_name(asset_name: str) -> Optional[str]:
    """Extract ticker from asset name with common company mappings."""
    if not asset_name:
        return None

    # Try direct extraction first
    ticker = extract_ticker_from_text(asset_name)
    if ticker:
        return ticker

    # Handle special cases via common mappings
    asset_lower = asset_name.lower()

    common_mappings = {
        "apple": "AAPL",
        "microsoft": "MSFT",
        "amazon": "AMZN",
        "google": "GOOGL",
        "alphabet": "GOOGL",
        "tesla": "TSLA",
        "meta platforms": "META",
        "meta ": "META",
        "facebook": "META",
        "nvidia": "NVDA",
        "netflix": "NFLX",
        "disney": "DIS",
        "intel": "INTC",
        "amd": "AMD",
        "advanced micro": "AMD",
        "paypal": "PYPL",
        "salesforce": "CRM",
        "oracle": "ORCL",
        "cisco": "CSCO",
        "adobe": "ADBE",
        "broadcom": "AVGO",
        "qualcomm": "QCOM",
        "texas instruments": "TXN",
        "jpmorgan": "JPM",
        "jp morgan": "JPM",
        "goldman sachs": "GS",
        "morgan stanley": "MS",
        "bank of america": "BAC",
        "wells fargo": "WFC",
        "citigroup": "C",
        "exxon": "XOM",
        "chevron": "CVX",
        "pfizer": "PFE",
        "johnson & johnson": "JNJ",
        "johnson and johnson": "JNJ",
        "procter & gamble": "PG",
        "procter and gamble": "PG",
        "coca-cola": "KO",
        "coca cola": "KO",
        "pepsi": "PEP",
        "pepsico": "PEP",
        "walmart": "WMT",
        "home depot": "HD",
        "costco": "COST",
        "target": "TGT",
        "starbucks": "SBUX",
        "mcdonald": "MCD",
        "uber": "UBER",
        "airbnb": "ABNB",
        "doordash": "DASH",
        "palantir": "PLTR",
        "snowflake": "SNOW",
        "crowdstrike": "CRWD",
        "okta": "OKTA",
        "datadog": "DDOG",
        "zoom": "ZM",
        "slack": "WORK",
        "shopify": "SHOP",
        "square": "SQ",
        "block inc": "SQ",
        "roku": "ROKU",
        "spotify": "SPOT",
        "twitter": "X",
        "snap": "SNAP",
        "pinterest": "PINS",
        "robinhood": "HOOD",
        "coinbase": "COIN",
    }

    for name, ticker in common_mappings.items():
        if name in asset_lower:
            return ticker

    return None


async def run_ticker_backfill(job_id: str, limit: Optional[int] = None):
    """
    Run ticker backfill job.

    Queries all disclosures with missing tickers and attempts to extract
    tickers from asset_name.

    Args:
        job_id: Unique job identifier for status tracking
        limit: Optional limit on records to process (for testing)
    """
    JOB_STATUS[job_id]["status"] = "running"
    JOB_STATUS[job_id]["message"] = "Initializing..."

    try:
        supabase = get_supabase()
        logger.info("Connected to Supabase")

        # Query disclosures with null or empty tickers
        JOB_STATUS[job_id]["message"] = "Querying disclosures with missing tickers..."

        query = supabase.table("trading_disclosures").select(
            "id, asset_name, asset_ticker"
        ).is_("asset_ticker", "null")

        if limit:
            query = query.limit(limit)

        response = query.execute()
        null_tickers = response.data or []

        # Also get empty string tickers
        query2 = supabase.table("trading_disclosures").select(
            "id, asset_name, asset_ticker"
        ).eq("asset_ticker", "")

        if limit:
            remaining = limit - len(null_tickers)
            if remaining > 0:
                query2 = query2.limit(remaining)
            else:
                query2 = query2.limit(0)

        response2 = query2.execute()
        empty_tickers = response2.data or []

        all_disclosures = null_tickers + empty_tickers
        total = len(all_disclosures)

        logger.info(f"Found {total} disclosures with missing tickers")
        JOB_STATUS[job_id]["total"] = total
        JOB_STATUS[job_id]["message"] = f"Found {total} disclosures to process"

        if total == 0:
            JOB_STATUS[job_id]["status"] = "completed"
            JOB_STATUS[job_id]["completed_at"] = datetime.utcnow().isoformat()
            JOB_STATUS[job_id]["message"] = "No disclosures need ticker backfill"
            return

        updated = 0
        failed = 0
        no_ticker_found = 0

        for i, disclosure in enumerate(all_disclosures):
            JOB_STATUS[job_id]["progress"] = i + 1
            JOB_STATUS[job_id]["message"] = f"Processing {i + 1}/{total}"

            disclosure_id = disclosure["id"]
            asset_name = disclosure.get("asset_name")

            if not asset_name:
                no_ticker_found += 1
                continue

            # Extract ticker
            ticker = extract_ticker_from_asset_name(asset_name)

            if ticker:
                try:
                    supabase.table("trading_disclosures").update(
                        {"asset_ticker": ticker}
                    ).eq("id", disclosure_id).execute()
                    updated += 1
                    logger.debug(f"Updated {disclosure_id}: {asset_name[:50]} -> {ticker}")
                except Exception as e:
                    failed += 1
                    logger.error(f"Failed to update {disclosure_id}: {e}")
            else:
                no_ticker_found += 1

        # Complete
        JOB_STATUS[job_id]["status"] = "completed"
        JOB_STATUS[job_id]["completed_at"] = datetime.utcnow().isoformat()
        JOB_STATUS[job_id]["message"] = (
            f"Completed: {updated} updated, {no_ticker_found} no ticker found, {failed} failed"
        )

        logger.info(
            f"Ticker backfill complete - Updated: {updated}, "
            f"No ticker found: {no_ticker_found}, Failed: {failed}"
        )

    except Exception as e:
        logger.error(f"Ticker backfill job failed: {e}")
        JOB_STATUS[job_id]["status"] = "failed"
        JOB_STATUS[job_id]["completed_at"] = datetime.utcnow().isoformat()
        JOB_STATUS[job_id]["message"] = f"Error: {str(e)}"
        raise


def extract_transaction_type_from_raw(raw_data: dict) -> Optional[str]:
    """
    Extract transaction type (purchase/sale) from raw_data.

    House disclosure PDFs embed P/S in the row data like:
    "Stock Name [ST] P 01/15/2025 01/20/2025 $1,001 - $15,000"
    """
    raw_row = raw_data.get("raw_row", [])
    if not raw_row:
        return None

    # Combine all cells into one text for searching
    full_text = " ".join(str(cell) for cell in raw_row if cell)
    full_lower = full_text.lower()

    # Check for full words first
    if any(kw in full_lower for kw in ["purchase", "bought", "buy"]):
        return "purchase"
    elif any(kw in full_lower for kw in ["sale", "sold", "sell", "exchange"]):
        return "sale"

    # Check for P/S patterns with dates (most common in House PDFs)
    # Pattern: "P 01/15/2025" or "S 12/01/2024"
    if re.search(r"\bP\s+\d{1,2}/\d{1,2}/\d{4}", full_text):
        return "purchase"
    elif re.search(r"\bS\s+\d{1,2}/\d{1,2}/\d{4}", full_text):
        return "sale"

    # Check for P/S with (partial) notation
    if re.search(r"\bP\s*\(partial\)\s+\d{1,2}/", full_text, re.IGNORECASE):
        return "purchase"
    elif re.search(r"\bS\s*\(partial\)\s+\d{1,2}/", full_text, re.IGNORECASE):
        return "sale"

    return None


async def run_transaction_type_backfill(job_id: str, limit: Optional[int] = None):
    """
    Backfill transaction_type for disclosures with 'unknown' type.

    Re-parses raw_data to extract P (purchase) or S (sale) from House disclosures.

    Args:
        job_id: Unique job identifier for status tracking
        limit: Optional limit on records to process (for testing)
    """
    JOB_STATUS[job_id]["status"] = "running"
    JOB_STATUS[job_id]["message"] = "Initializing..."

    try:
        supabase = get_supabase()
        logger.info("Connected to Supabase")

        # Query disclosures with 'unknown' transaction_type
        JOB_STATUS[job_id]["message"] = "Querying disclosures with unknown transaction_type..."

        query = supabase.table("trading_disclosures").select(
            "id, transaction_type, raw_data, asset_name"
        ).eq("transaction_type", "unknown")

        if limit:
            query = query.limit(limit)

        response = query.execute()
        disclosures = response.data or []
        total = len(disclosures)

        logger.info(f"Found {total} disclosures with unknown transaction_type")
        JOB_STATUS[job_id]["total"] = total
        JOB_STATUS[job_id]["message"] = f"Found {total} disclosures to process"

        if total == 0:
            JOB_STATUS[job_id]["status"] = "completed"
            JOB_STATUS[job_id]["completed_at"] = datetime.utcnow().isoformat()
            JOB_STATUS[job_id]["message"] = "No disclosures need transaction_type backfill"
            return

        updated = 0
        failed = 0
        no_type_found = 0
        deleted = 0

        for i, disclosure in enumerate(disclosures):
            JOB_STATUS[job_id]["progress"] = i + 1
            JOB_STATUS[job_id]["message"] = f"Processing {i + 1}/{total}"

            disclosure_id = disclosure["id"]
            raw_data = disclosure.get("raw_data") or {}
            asset_name = disclosure.get("asset_name", "")

            # Check if this is a metadata-only record that shouldn't exist
            if asset_name and is_metadata_only(asset_name):
                try:
                    supabase.table("trading_disclosures").delete().eq("id", disclosure_id).execute()
                    deleted += 1
                    logger.debug(f"Deleted metadata-only record: {disclosure_id}")
                    continue
                except Exception as e:
                    logger.error(f"Failed to delete {disclosure_id}: {e}")

            # Try to extract transaction type from raw_data
            tx_type = extract_transaction_type_from_raw(raw_data)

            if tx_type:
                try:
                    supabase.table("trading_disclosures").update(
                        {"transaction_type": tx_type}
                    ).eq("id", disclosure_id).execute()
                    updated += 1
                    logger.debug(f"Updated {disclosure_id}: {asset_name[:50]} -> {tx_type}")
                except Exception as e:
                    failed += 1
                    logger.error(f"Failed to update {disclosure_id}: {e}")
            else:
                no_type_found += 1

        # Complete
        JOB_STATUS[job_id]["status"] = "completed"
        JOB_STATUS[job_id]["completed_at"] = datetime.utcnow().isoformat()
        JOB_STATUS[job_id]["message"] = (
            f"Completed: {updated} updated, {no_type_found} not found, {deleted} deleted, {failed} failed"
        )

        logger.info(
            f"Transaction type backfill complete - Updated: {updated}, "
            f"Not found: {no_type_found}, Deleted: {deleted}, Failed: {failed}"
        )

    except Exception as e:
        logger.error(f"Transaction type backfill job failed: {e}")
        JOB_STATUS[job_id]["status"] = "failed"
        JOB_STATUS[job_id]["completed_at"] = datetime.utcnow().isoformat()
        JOB_STATUS[job_id]["message"] = f"Error: {str(e)}"
        raise


def is_metadata_only(asset_name: str) -> bool:
    """Check if an asset_name is actually just metadata that shouldn't be a record."""
    if not asset_name:
        return True

    # These patterns indicate metadata rows, not actual assets
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
        r"^TD Ameritrade",  # Brokerage account names
        r"^Charles Schwab",
        r"^Fidelity",
        r"^Vanguard",
        r"^E\*TRADE",
        r"^Merrill",
    ]

    for pattern in metadata_patterns:
        if re.match(pattern, asset_name.strip(), re.IGNORECASE):
            return True

    return False
