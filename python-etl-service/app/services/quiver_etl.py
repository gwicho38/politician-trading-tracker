"""
QuiverQuant Congress Trading ETL Service

Fetches congress trading data from the QuiverQuant REST API and uploads
to Supabase. This replaces the previous Supabase Edge Function approach
which created placeholder politicians with garbage data.

Data Source: https://api.quiverquant.com/beta
API Docs: QuiverQuant Congress Trading API

Fields from API:
- Representative: Politician name (e.g., "Nancy Pelosi")
- BioGuideID: Congress.gov bioguide identifier
- Ticker: Stock ticker symbol
- Description: Asset description
- Transaction: "Purchase" or "Sale (Full)" or "Sale (Partial)" or "Exchange"
- Amount: Range string like "$1,001 - $15,000"
- TransactionDate: ISO date string
- ReportDate: Filing/disclosure date
- House: "House" or "Senate" (chamber)
- District: State/district code
- Party: Political party
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.lib.base_etl import BaseETLService, ETLResult
from app.lib.registry import ETLRegistry
from app.lib.parser import (
    extract_ticker_from_text,
    clean_asset_name,
    parse_value_range,
)

logger = logging.getLogger(__name__)

QUIVERQUANT_API_BASE = "https://api.quiverquant.com/beta"
QUIVERQUANT_BULK_ENDPOINT = f"{QUIVERQUANT_API_BASE}/bulk/congresstrading"


def _parse_qq_amount_range(amount_str: str) -> Dict[str, Optional[float]]:
    """
    Parse QuiverQuant amount range string into min/max values.

    QuiverQuant uses standard disclosure ranges like "$1,001 - $15,000".
    Falls back to the shared parse_value_range for standard patterns.
    """
    if not amount_str:
        return {"value_low": None, "value_high": None}

    # Use the shared parser which handles all standard disclosure ranges
    return parse_value_range(amount_str)


def _map_transaction_type(qq_type: str) -> str:
    """
    Map QuiverQuant transaction type to our standard format.

    QQ uses: Purchase, Sale (Full), Sale (Partial), Exchange, Sale
    We use: purchase, sale, exchange
    """
    if not qq_type:
        return "unknown"

    type_lower = qq_type.lower().strip()

    if "purchase" in type_lower or "buy" in type_lower:
        return "purchase"
    elif "sale" in type_lower or "sell" in type_lower or "sold" in type_lower:
        return "sale"
    elif "exchange" in type_lower:
        return "exchange"
    return "unknown"


def _map_chamber(qq_house: str) -> str:
    """Map QuiverQuant 'House' field to chamber name."""
    if not qq_house:
        return "house"
    house_lower = qq_house.lower().strip()
    if house_lower == "senate":
        return "senate"
    return "house"


def _map_role(qq_house: str) -> str:
    """Map QuiverQuant 'House' field to politician role."""
    if not qq_house:
        return "Representative"
    house_lower = qq_house.lower().strip()
    if house_lower == "senate":
        return "Senator"
    return "Representative"


@ETLRegistry.register
class QuiverQuantETLService(BaseETLService):
    """
    QuiverQuant Congress Trading ETL service.

    Fetches bulk congress trading data from the QuiverQuant API
    and uploads to Supabase via the standard BaseETLService pipeline.
    """

    source_id = "quiverquant"
    source_name = "QuiverQuant Congress Trading"

    def __init__(self):
        super().__init__()
        self.api_key = os.environ.get("QUIVERQUANT_API_KEY", "")

    async def on_start(self, job_id: str, **kwargs):
        """Validate API key is configured before starting."""
        await super().on_start(job_id, **kwargs)
        if not self.api_key:
            raise ValueError(
                "QUIVERQUANT_API_KEY environment variable is not set. "
                "Cannot fetch data from QuiverQuant API."
            )

    async def fetch_disclosures(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch congress trading data from QuiverQuant bulk API.

        Args:
            lookback_days: How many days back to fetch (default: 30)
            limit: Maximum number of records (applied after date filter)

        Returns:
            List of raw QuiverQuant trade records.
        """
        lookback_days = kwargs.get("lookback_days", 30)

        self.logger.info(
            f"Fetching QuiverQuant data (lookback_days={lookback_days})"
        )

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    QUIVERQUANT_BULK_ENDPOINT,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Accept": "application/json",
                    },
                )

                if response.status_code == 401:
                    raise ValueError("QuiverQuant API key is invalid or expired")
                elif response.status_code == 403:
                    raise ValueError("QuiverQuant API key lacks permission for this endpoint")

                response.raise_for_status()
                data = response.json()

        except httpx.HTTPStatusError as e:
            self.logger.error(f"QuiverQuant API error: {e.response.status_code}")
            raise
        except httpx.RequestError as e:
            self.logger.error(f"QuiverQuant request failed: {e}")
            raise

        if not isinstance(data, list):
            self.logger.warning(f"Unexpected API response type: {type(data)}")
            return []

        # Filter by lookback window
        cutoff_date = (
            datetime.now(timezone.utc) - timedelta(days=lookback_days)
        ).strftime("%Y-%m-%d")

        filtered = [
            record
            for record in data
            if (record.get("TransactionDate") or "")[:10] >= cutoff_date
        ]

        self.logger.info(
            f"Fetched {len(data)} total records, "
            f"{len(filtered)} within {lookback_days}-day window"
        )

        return filtered

    async def parse_disclosure(
        self, raw: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Parse a single QuiverQuant record into standardized disclosure format.

        Maps QQ API fields to our standard schema:
        - Representative -> politician_name
        - Ticker -> asset_ticker
        - Description -> asset_name
        - Transaction -> transaction_type
        - Amount -> value_low/value_high
        - TransactionDate -> transaction_date
        - ReportDate -> disclosure_date
        - House -> chamber, role
        """
        representative = raw.get("Representative", "").strip()
        if not representative:
            return None

        # Asset identification
        ticker = raw.get("Ticker", "").strip() or None
        description = raw.get("Description", "").strip()
        asset_name = description or raw.get("Ticker", "Unknown Asset")

        if ticker and ticker in ("--", "N/A", ""):
            ticker = None

        # If no ticker from QQ, try to extract from description
        if not ticker and description:
            ticker = extract_ticker_from_text(description)

        # Clean the asset name
        if asset_name and asset_name != "Unknown Asset":
            asset_name = clean_asset_name(asset_name)

        # Transaction type mapping
        transaction_type = _map_transaction_type(raw.get("Transaction", ""))

        # Amount range
        amount_str = raw.get("Amount", "")
        value_info = _parse_qq_amount_range(amount_str)

        # Dates
        transaction_date = raw.get("TransactionDate")
        if transaction_date:
            transaction_date = transaction_date[:10]  # Just the date part

        disclosure_date = raw.get("ReportDate")
        if disclosure_date:
            disclosure_date = disclosure_date[:10]

        # Chamber and role
        qq_house = raw.get("House", "")
        chamber = _map_chamber(qq_house)
        role = _map_role(qq_house)

        # Politician details
        # QQ provides name as "FirstName LastName" format
        name_parts = representative.split(maxsplit=1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else representative

        return {
            "politician_name": representative,
            "first_name": first_name,
            "last_name": last_name,
            "bioguide_id": raw.get("BioGuideID"),
            "party": raw.get("Party"),
            "state": raw.get("District", "").split("-")[0] if raw.get("District") else None,
            "chamber": chamber,
            "role": role,
            "asset_name": asset_name,
            "asset_ticker": ticker,
            "transaction_type": transaction_type,
            "transaction_date": transaction_date,
            "notification_date": disclosure_date,
            "disclosure_date": disclosure_date,
            "value_low": value_info.get("value_low"),
            "value_high": value_info.get("value_high"),
            "source": "quiverquant",
            "source_url": None,
            "doc_id": f"qq-{raw.get('BioGuideID', 'unknown')}-{transaction_date}-{ticker or 'noticker'}",
        }

    async def validate_disclosure(self, disclosure: Dict[str, Any]) -> bool:
        """
        Validate a parsed QuiverQuant disclosure.

        Requires at minimum an asset name or ticker, and a politician name.
        """
        has_asset = bool(disclosure.get("asset_name")) or bool(
            disclosure.get("asset_ticker")
        )
        has_politician = bool(disclosure.get("politician_name"))

        if not has_asset:
            self.logger.debug(
                f"Skipping disclosure: no asset info for {disclosure.get('politician_name')}"
            )
            return False

        if not has_politician:
            self.logger.debug("Skipping disclosure: no politician name")
            return False

        return True

    async def upload_disclosure(
        self,
        disclosure: Dict[str, Any],
        update_mode: bool = False,
    ) -> Optional[str]:
        """
        Upload a QuiverQuant disclosure to the database.

        Uses bioguide_id for politician matching when available,
        falling back to name-based matching.
        """
        from app.lib.database import get_supabase, upload_transaction_to_supabase
        from app.lib.politician import find_or_create_politician

        try:
            supabase = get_supabase()
            if not supabase:
                return None

            # Find or create politician with bioguide_id priority
            politician_id = find_or_create_politician(
                supabase,
                name=disclosure.get("politician_name"),
                first_name=disclosure.get("first_name"),
                last_name=disclosure.get("last_name"),
                chamber=disclosure.get("chamber", "house"),
                state=disclosure.get("state"),
                bioguide_id=disclosure.get("bioguide_id"),
            )

            if not politician_id:
                self.logger.warning(
                    f"Could not find/create politician: {disclosure.get('politician_name')}"
                )
                return None

            return upload_transaction_to_supabase(
                supabase,
                politician_id,
                disclosure,
                disclosure,
                update_mode=update_mode,
            )

        except Exception as e:
            self.logger.error(f"Upload failed for {disclosure.get('politician_name')}: {e}")
            return None
