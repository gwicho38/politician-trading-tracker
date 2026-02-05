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
        dry_run: bool = False,
    ) -> dict:
        """
        Run a validation audit comparing app trades against QuiverQuant.

        Args:
            limit: Maximum number of QuiverQuant records to fetch
            from_date: Start date filter (YYYY-MM-DD)
            to_date: End date filter (YYYY-MM-DD)
            dry_run: If True, don't store results

        Returns:
            Audit results summary
        """
        if not self.api_key:
            raise ValueError("QUIVERQUANT_API_KEY not configured")

        if not self.supabase:
            raise ValueError("Supabase not configured")

        logger.info(f"Starting QuiverQuant validation audit (limit={limit})")

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

        # Build QuiverQuant lookup by match key
        qq_by_key = {}
        for trade in qq_data:
            key = self._create_match_key(
                trade.get("BioGuideID"),
                trade.get("Representative"),
                trade.get("Ticker"),
                trade.get("TransactionDate"),
                trade.get("Transaction"),
            )
            qq_by_key[key] = trade

        logger.info(f"Created {len(qq_by_key)} unique match keys")

        # Fetch app trades
        app_trades = await self._fetch_app_trades(from_date, to_date)
        logger.info(f"Found {len(app_trades)} app trades")

        # Fetch politicians for lookup
        politicians = await self._fetch_politicians()
        pol_by_id = {p["id"]: p for p in politicians if p.get("id")}
        logger.info(f"Loaded {len(pol_by_id)} politicians")

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

            key = self._create_match_key(
                politician.get("bioguide_id") if politician else None,
                politician.get("full_name") if politician else None,
                app_trade.get("asset_ticker"),
                app_trade.get("transaction_date"),
                app_trade.get("transaction_type"),
            )
            app_keys_found.add(key)

            if key in qq_by_key:
                quiver_trade = qq_by_key[key]
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
                    })

        # Find Quiver-only records
        for key, quiver_trade in qq_by_key.items():
            if key not in app_keys_found:
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
        """Fetch trading disclosures from app database."""
        try:
            query = (
                self.supabase.table("trading_disclosures")
                .select("id,asset_ticker,transaction_date,disclosure_date,transaction_type,amount_range_min,amount_range_max,politician_id,status")
                .eq("status", "active")
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
        """Fetch politicians from app database."""
        try:
            response = (
                self.supabase.table("politicians")
                .select("id,full_name,bioguide_id,party,chamber")
                .limit(10000)
                .execute()
            )
            return response.data or []
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
        # Normalize name
        norm_name = ""
        if name:
            norm_name = re.sub(r"[^a-z]", "", name.lower())

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

    async def _store_validation_result(self, result: dict) -> bool:
        """Store a validation result in the database."""
        try:
            # Build payload with app_snapshot and quiver_snapshot
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
            }

            # Add snapshots
            if result.get("quiver_record"):
                payload["quiver_snapshot"] = result["quiver_record"]

            self.supabase.table("trade_validation_results").insert(payload).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to store validation result: {e}")
            return False
