"""
QuiverQuant Validation Service

Validates trading disclosures against QuiverQuant data to identify
mismatches, missing records, and data quality issues.
"""

import logging
import os
import re
from datetime import datetime, timedelta
from typing import Optional

import httpx

from app.lib.database import get_supabase

logger = logging.getLogger(__name__)

QUIVERQUANT_API_URL = "https://api.quiverquant.com/beta/live/congresstrading"


class QuiverValidationService:
    """Service for validating app data against QuiverQuant."""

    def __init__(self):
        self.supabase = get_supabase()
        self.api_key = os.environ.get("QUIVERQUANT_API_KEY")

    async def run_audit(
        self,
        limit: int = 100,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        chamber: Optional[str] = None,
        dry_run: bool = False,
    ) -> dict:
        """
        Run a validation audit comparing app trades against QuiverQuant.

        Args:
            limit: Maximum number of QuiverQuant records to fetch
            from_date: Start date filter (YYYY-MM-DD)
            to_date: End date filter (YYYY-MM-DD)
            chamber: Filter by chamber ('house' or 'senate')
            dry_run: If True, don't store results

        Returns:
            Audit results summary
        """
        if not self.api_key:
            raise ValueError("QUIVERQUANT_API_KEY not configured")

        if not self.supabase:
            raise ValueError("Supabase not configured")

        logger.info(f"Starting QuiverQuant validation audit (limit={limit}, chamber={chamber})")

        # Fetch QuiverQuant data
        qq_data = await self._fetch_quiverquant_data(limit)
        if not qq_data:
            return {"error": "Failed to fetch QuiverQuant data", "validated": 0}

        logger.info(f"Fetched {len(qq_data)} QuiverQuant records")

        # Filter by date if specified
        if from_date:
            qq_data = [t for t in qq_data if (t.get("TransactionDate") or "")[:10] >= from_date]
        if to_date:
            qq_data = [t for t in qq_data if (t.get("TransactionDate") or "")[:10] <= to_date]

        # Filter by chamber if specified
        if chamber:
            chamber_map = {"house": "representatives", "senate": "senate"}
            qq_chamber_val = chamber_map.get(chamber.lower(), chamber.lower())
            qq_data = [t for t in qq_data if (t.get("House") or "").lower() == qq_chamber_val]
            logger.info(f"Filtered to {len(qq_data)} {chamber} records from QuiverQuant")

        # Build QuiverQuant lookup by match key
        # Create dual indexes: one by bioguide_id, one by normalized name
        # This allows matching even when one side lacks bioguide_id
        qq_by_key = {}
        qq_by_name_key = {}
        for trade in qq_data:
            bioguide_id = trade.get("BioGuideID")
            rep_name = trade.get("Representative")

            # Primary key with bioguide_id
            if bioguide_id:
                key = self._create_match_key(
                    bioguide_id,
                    None,  # Don't use name when we have bioguide_id
                    trade.get("Ticker"),
                    trade.get("TransactionDate"),
                    trade.get("Transaction"),
                )
                qq_by_key[key] = trade

            # Secondary key with normalized name (for fallback matching)
            name_key = self._create_match_key(
                None,  # Force name-based key
                rep_name,
                trade.get("Ticker"),
                trade.get("TransactionDate"),
                trade.get("Transaction"),
            )
            qq_by_name_key[name_key] = trade

        logger.info(f"Created {len(qq_by_key)} bioguide keys, {len(qq_by_name_key)} name keys")

        # Fetch app trades
        app_trades = await self._fetch_app_trades(from_date, to_date)
        logger.info(f"Found {len(app_trades)} app trades")

        # Fetch politicians for lookup
        politicians = await self._fetch_politicians()
        pol_by_id = {p["id"]: p for p in politicians if p.get("id")}
        logger.info(f"Loaded {len(pol_by_id)} politicians")

        # Filter app trades by chamber if specified
        if chamber:
            filtered_trades = []
            for trade in app_trades:
                pol = pol_by_id.get(trade.get("politician_id"))
                if pol and (pol.get("chamber") or "").lower() == chamber.lower():
                    filtered_trades.append(trade)
            app_trades = filtered_trades
            logger.info(f"Filtered to {len(app_trades)} {chamber} trades from app")

        # Compare trades
        results = {
            "match": 0,
            "mismatch": 0,
            "app_only": 0,
            "quiver_only": 0,
        }
        root_causes = {}
        app_keys_found = set()

        for app_trade in app_trades:
            politician = pol_by_id.get(app_trade.get("politician_id"))
            bioguide_id = politician.get("bioguide_id") if politician else None
            full_name = politician.get("full_name") if politician else None

            # Create primary key (with bioguide_id if available, else name)
            key = self._create_match_key(
                bioguide_id,
                full_name,
                app_trade.get("asset_ticker"),
                app_trade.get("transaction_date"),
                app_trade.get("transaction_type"),
            )
            app_keys_found.add(key)

            # Also create name-only key for fallback matching
            name_only_key = self._create_match_key(
                None,  # Force name-based key
                full_name,
                app_trade.get("asset_ticker"),
                app_trade.get("transaction_date"),
                app_trade.get("transaction_type"),
            )
            app_keys_found.add(name_only_key)

            # Try to find a match - first by bioguide_id key, then by name key
            quiver_trade = None
            if bioguide_id and key in qq_by_key:
                quiver_trade = qq_by_key[key]
            elif name_only_key in qq_by_name_key:
                quiver_trade = qq_by_name_key[name_only_key]

            if quiver_trade:
                mismatches = self._compare_fields(app_trade, quiver_trade, politician)

                if mismatches:
                    results["mismatch"] += 1
                    root_cause = self._diagnose_root_cause(mismatches, app_trade, quiver_trade)
                    severity = self._get_severity(mismatches)
                    root_causes[root_cause] = root_causes.get(root_cause, 0) + 1

                    if not dry_run:
                        await self._store_validation_result({
                            "trading_disclosure_id": app_trade.get("id"),
                            "quiver_record": quiver_trade,
                            "match_key": key,
                            "validation_status": "mismatch",
                            "field_mismatches": mismatches,
                            "root_cause": root_cause,
                            "severity": severity,
                            "politician_name": politician.get("full_name") if politician else None,
                            "ticker": app_trade.get("asset_ticker"),
                            "transaction_date": app_trade.get("transaction_date"),
                            "transaction_type": app_trade.get("transaction_type"),
                            "chamber": self._get_chamber(politician, quiver_trade),
                        })
                else:
                    results["match"] += 1
                    if not dry_run:
                        await self._store_validation_result({
                            "trading_disclosure_id": app_trade.get("id"),
                            "match_key": key,
                            "validation_status": "match",
                            "politician_name": politician.get("full_name") if politician else None,
                            "ticker": app_trade.get("asset_ticker"),
                            "transaction_date": app_trade.get("transaction_date"),
                            "transaction_type": app_trade.get("transaction_type"),
                            "chamber": self._get_chamber(politician, None),
                        })
            else:
                results["app_only"] += 1
                if not dry_run:
                    await self._store_validation_result({
                        "trading_disclosure_id": app_trade.get("id"),
                        "match_key": key,
                        "validation_status": "app_only",
                        "root_cause": "missing_in_quiver",
                        "severity": "info",
                        "politician_name": politician.get("full_name") if politician else None,
                        "ticker": app_trade.get("asset_ticker"),
                        "transaction_date": app_trade.get("transaction_date"),
                        "transaction_type": app_trade.get("transaction_type"),
                        "chamber": self._get_chamber(politician, None),
                    })

        # Find Quiver-only records
        # Check both bioguide_id-based and name-based keys
        seen_quiver_trades = set()
        for key, quiver_trade in qq_by_key.items():
            trade_id = f"{quiver_trade.get('BioGuideID')}|{quiver_trade.get('Ticker')}|{quiver_trade.get('TransactionDate')}"
            if trade_id in seen_quiver_trades:
                continue

            # Check if this trade was matched via bioguide_id key OR name key
            name_key = self._create_match_key(
                None,
                quiver_trade.get("Representative"),
                quiver_trade.get("Ticker"),
                quiver_trade.get("TransactionDate"),
                quiver_trade.get("Transaction"),
            )
            if key in app_keys_found or name_key in app_keys_found:
                seen_quiver_trades.add(trade_id)
                continue

            seen_quiver_trades.add(trade_id)
            results["quiver_only"] += 1
            root_causes["data_lag"] = root_causes.get("data_lag", 0) + 1

            if not dry_run:
                    await self._store_validation_result({
                        "quiver_record": quiver_trade,
                        "match_key": key,
                        "validation_status": "quiver_only",
                        "root_cause": "data_lag",
                        "severity": "warning",
                        "politician_name": quiver_trade.get("Representative"),
                        "ticker": quiver_trade.get("Ticker"),
                        "transaction_date": quiver_trade.get("TransactionDate"),
                        "transaction_type": quiver_trade.get("Transaction"),
                        "chamber": self._get_chamber(None, quiver_trade),
                    })

        total = sum(results.values())
        logger.info(f"Audit complete: {results}")

        return {
            "validated": total,
            "results": results,
            "root_causes": root_causes,
            "match_rate": (results["match"] / total * 100) if total > 0 else 0,
        }

    async def _fetch_quiverquant_data(self, limit: int) -> list:
        """Fetch data from QuiverQuant API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    QUIVERQUANT_API_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Accept": "application/json",
                    },
                    params={"pagesize": limit},
                    timeout=60.0,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch QuiverQuant data: {e}")
            return []

    async def _fetch_app_trades(
        self, from_date: Optional[str] = None, to_date: Optional[str] = None
    ) -> list:
        """Fetch trading disclosures from app database.

        Only fetches actual trades (purchase/sale), not holdings or other disclosure types.
        """
        try:
            query = (
                self.supabase.table("trading_disclosures")
                .select("id,asset_ticker,transaction_date,disclosure_date,transaction_type,amount_range_min,amount_range_max,politician_id,status")
                .eq("status", "active")
                .in_("transaction_type", ["purchase", "sale", "sale_partial", "sale_full", "exchange"])
                .limit(5000)
            )

            if from_date:
                query = query.gte("transaction_date", from_date)
            if to_date:
                query = query.lte("transaction_date", to_date)

            response = query.execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Failed to fetch app trades: {e}")
            return []

    async def _fetch_politicians(self) -> list:
        """Fetch politicians from app database.

        Uses pagination to get all politicians since Supabase has a 1000 row default limit.
        """
        try:
            all_politicians = []
            page_size = 1000
            offset = 0

            while True:
                response = (
                    self.supabase.table("politicians")
                    .select("id,full_name,bioguide_id,party,chamber")
                    .range(offset, offset + page_size - 1)
                    .execute()
                )
                batch = response.data or []
                all_politicians.extend(batch)

                if len(batch) < page_size:
                    # Last page
                    break
                offset += page_size

            return all_politicians
        except Exception as e:
            logger.error(f"Failed to fetch politicians: {e}")
            return []

    def _create_match_key(
        self,
        bioguide_id: Optional[str],
        name: Optional[str],
        ticker: Optional[str],
        date: Optional[str],
        tx_type: Optional[str],
    ) -> str:
        """Create a normalized match key for comparing trades."""
        # Normalize name - strip "Hon. " prefix and other honorifics
        norm_name = ""
        if name:
            # Remove common prefixes that differ between sources
            clean_name = re.sub(r"^(Hon\.|Dr\.|Mr\.|Mrs\.|Ms\.)\s*", "", name, flags=re.IGNORECASE)
            norm_name = re.sub(r"[^a-z]", "", clean_name.lower())

        # Normalize ticker
        norm_ticker = (ticker or "").upper().strip()

        # Normalize date (just the date part)
        norm_date = (date or "")[:10]

        # Normalize transaction type
        tx_map = {
            "purchase": "buy",
            "sale": "sell",
            "sale (partial)": "sell",
            "sale (full)": "sell",
            "exchange": "exchange",
        }
        norm_type = tx_map.get((tx_type or "").lower(), (tx_type or "").lower())

        # Use bioguide_id if available, otherwise use normalized name
        id_part = bioguide_id or norm_name

        return f"{id_part}|{norm_ticker}|{norm_date}|{norm_type}"

    def _compare_fields(self, app_trade: dict, quiver_trade: dict, politician: dict) -> dict:
        """Compare fields between app and QuiverQuant records."""
        mismatches = {}

        # Compare amount ranges
        app_min = app_trade.get("amount_range_min")
        app_max = app_trade.get("amount_range_max")
        qq_range = quiver_trade.get("Range")

        if qq_range and app_min is not None:
            # Parse QuiverQuant range (e.g., "$1,001 - $15,000")
            qq_min, qq_max = self._parse_amount_range(qq_range)
            if qq_min is not None and abs(app_min - qq_min) > 1:
                mismatches["amount_range_min"] = {
                    "app": app_min,
                    "quiver": qq_min,
                    "severity": "warning",
                }
            if qq_max is not None and app_max is not None and abs(app_max - qq_max) > 1:
                mismatches["amount_range_max"] = {
                    "app": app_max,
                    "quiver": qq_max,
                    "severity": "warning",
                }

        return mismatches

    def _parse_amount_range(self, range_str: str) -> tuple:
        """Parse QuiverQuant amount range string."""
        if not range_str:
            return None, None

        # Remove $ and commas, extract numbers
        numbers = re.findall(r"[\d,]+", range_str.replace(",", ""))
        if len(numbers) >= 2:
            return int(numbers[0]), int(numbers[1])
        elif len(numbers) == 1:
            return int(numbers[0]), int(numbers[0])
        return None, None

    def _diagnose_root_cause(self, mismatches: dict, app_trade: dict, quiver_trade: dict) -> str:
        """Diagnose the root cause of mismatches."""
        if "amount_range_min" in mismatches or "amount_range_max" in mismatches:
            return "amount_parse_error"
        if "transaction_type" in mismatches:
            return "transaction_type_mapping"
        if "ticker" in mismatches:
            return "ticker_mismatch"
        if "transaction_date" in mismatches:
            return "date_parse_error"
        return "unknown"

    def _get_severity(self, mismatches: dict) -> str:
        """Determine overall severity of mismatches."""
        if not mismatches:
            return "info"
        for field_data in mismatches.values():
            if field_data.get("severity") == "critical":
                return "critical"
        return "warning"

    def _get_chamber(self, politician: Optional[dict], quiver_trade: Optional[dict]) -> str:
        """Determine chamber from politician or QuiverQuant data."""
        # Try politician first
        if politician and politician.get("chamber"):
            return politician["chamber"].lower()

        # Try QuiverQuant data
        if quiver_trade and quiver_trade.get("House"):
            house_val = quiver_trade["House"].lower()
            if house_val == "representatives":
                return "house"
            elif house_val == "senate":
                return "senate"

        return "unknown"

    async def _store_validation_result(self, result: dict) -> bool:
        """Store a validation result in the database."""
        try:
            payload = {
                "trading_disclosure_id": result.get("trading_disclosure_id"),
                "match_key": result.get("match_key"),
                "validation_status": result["validation_status"],
                "field_mismatches": result.get("field_mismatches", {}),
                "root_cause": result.get("root_cause"),
                "severity": result.get("severity", "warning"),
                "politician_name": result.get("politician_name"),
                "ticker": result.get("ticker"),
                "transaction_date": result.get("transaction_date"),
                "transaction_type": result.get("transaction_type"),
                "chamber": result.get("chamber", "unknown"),
            }

            # Add QuiverQuant record snapshot
            if result.get("quiver_record"):
                payload["quiver_record"] = result["quiver_record"]

            self.supabase.table("trade_validation_results").insert(payload).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to store validation result: {e}")
            return False
