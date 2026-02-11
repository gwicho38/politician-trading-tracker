"""
QuiverQuant Congress Trading ETL Service

Fetches congress trading data from the QuiverQuant REST API and uploads
to Supabase. This replaces the previous Supabase Edge Function approach
which created placeholder politicians with garbage data.

Data Source: https://api.quiverquant.com/beta
API Docs: QuiverQuant Congress Trading API

Fields from API (bulk/congresstrading endpoint):
- Name: Politician name (e.g., "Nancy Pelosi")
- BioGuideID: Congress.gov bioguide identifier
- Ticker: Stock ticker symbol
- Description: Asset description (often null)
- Transaction: "Purchase" or "Sale" or "Exchange"
- Trade_Size_USD: Dollar amount as string (e.g., "1001.0")
- Traded: Transaction date ISO string (e.g., "2026-01-30")
- Filed: Filing/disclosure date (e.g., "2026-02-10")
- Chamber: "Representatives" or "Senate"
- District: State/district code (e.g., " VA05")
- Party: Political party ("R", "D")
- State: State abbreviation (often null)
- excess_return: Calculated excess return (informational)
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


def _parse_qq_trade_size(trade_size: str) -> Dict[str, Optional[float]]:
    """
    Parse QuiverQuant Trade_Size_USD field into min/max values.

    The API returns a single dollar amount string (e.g., "1001.0", "15001.0")
    which represents the lower bound of the disclosure range bracket.
    We map these to the standard STOCK Act disclosure ranges.
    """
    if not trade_size:
        return {"value_low": None, "value_high": None}

    try:
        value = float(trade_size)
    except (ValueError, TypeError):
        # Fall back to range parser for any range-format strings
        return parse_value_range(trade_size)

    # Map QQ's single values to standard disclosure range brackets
    # QQ uses the lower bound of each bracket
    BRACKETS = [
        (1001, 1001, 15000),
        (15001, 15001, 50000),
        (50001, 50001, 100000),
        (100001, 100001, 250000),
        (250001, 250001, 500000),
        (500001, 500001, 1000000),
        (1000001, 1000001, 5000000),
        (5000001, 5000001, 25000000),
        (25000001, 25000001, 50000000),
    ]

    for threshold, low, high in BRACKETS:
        if value <= threshold:
            return {"value_low": float(low), "value_high": float(high)}

    # Above $25M bracket
    if value > 25000000:
        return {"value_low": 25000001.0, "value_high": 50000000.0}

    # Fallback: use the value as both min and max
    return {"value_low": value, "value_high": value}


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


def _map_chamber(qq_chamber: str) -> str:
    """Map QuiverQuant 'Chamber' field to chamber name.

    QQ uses "Representatives" or "Senate".
    """
    if not qq_chamber:
        return "house"
    chamber_lower = qq_chamber.lower().strip()
    if chamber_lower == "senate":
        return "senate"
    return "house"


def _map_role(qq_chamber: str) -> str:
    """Map QuiverQuant 'Chamber' field to politician role.

    QQ uses "Representatives" or "Senate".
    """
    if not qq_chamber:
        return "Representative"
    chamber_lower = qq_chamber.lower().strip()
    if chamber_lower == "senate":
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
            if (record.get("Traded") or "")[:10] >= cutoff_date
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
        - Name -> politician_name
        - Ticker -> asset_ticker
        - Description -> asset_name (fallback to Ticker)
        - Transaction -> transaction_type
        - Trade_Size_USD -> value_low/value_high
        - Traded -> transaction_date
        - Filed -> disclosure_date
        - Chamber -> chamber, role
        """
        name = (raw.get("Name") or "").strip()
        if not name:
            return None

        # Asset identification
        ticker = (raw.get("Ticker") or "").strip() or None
        description = (raw.get("Description") or "").strip()
        asset_name = description or ticker or "Unknown Asset"

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

        # Trade size (single USD value, not a range)
        trade_size = raw.get("Trade_Size_USD", "")
        value_info = _parse_qq_trade_size(str(trade_size) if trade_size else "")

        # Dates
        transaction_date = raw.get("Traded")
        if transaction_date:
            transaction_date = str(transaction_date)[:10]

        disclosure_date = raw.get("Filed")
        if disclosure_date:
            disclosure_date = str(disclosure_date)[:10]

        # Chamber and role
        qq_chamber = raw.get("Chamber", "")
        chamber = _map_chamber(qq_chamber)
        role = _map_role(qq_chamber)

        # Politician details
        # QQ provides name as "FirstName LastName" format (sometimes with prefix like "Mr.")
        clean_name = name
        for prefix in ("Mr. ", "Mrs. ", "Ms. ", "Dr. ", "Hon. ", "Sen. ", "Rep. "):
            if clean_name.startswith(prefix):
                clean_name = clean_name[len(prefix):]

        name_parts = clean_name.split(maxsplit=1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else clean_name

        # State: prefer State field, fall back to parsing District
        state = raw.get("State") or None
        if not state and raw.get("District"):
            district_str = raw["District"].strip()
            # District format is like "VA05" or " VA05"
            state = district_str[:2] if len(district_str) >= 2 else None

        return {
            "politician_name": clean_name,
            "first_name": first_name,
            "last_name": last_name,
            "bioguide_id": raw.get("BioGuideID"),
            "party": raw.get("Party"),
            "state": state,
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
