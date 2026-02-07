"""
Chart Data Validation Service

Validates each data point on the Trading Activity and Trade Volume charts
against QuiverQuant data to ensure accuracy.

Compares:
- Monthly buy counts
- Monthly sell counts
- Monthly trading volume
"""

import logging
import os
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.lib.database import get_supabase

logger = logging.getLogger(__name__)

QUIVERQUANT_API_URL = "https://api.quiverquant.com/beta/live/congresstrading"


class ChartValidationService:
    """Service for validating chart data points against QuiverQuant."""

    def __init__(self):
        self.supabase = get_supabase()
        self.api_key = os.environ.get("QUIVERQUANT_API_KEY")

    async def validate_chart_data(
        self,
        from_year: int = 2024,
        to_year: int = 2026,
        store_results: bool = True,
    ) -> Dict[str, Any]:
        """
        Validate all chart data points against QuiverQuant.

        Args:
            from_year: Start year for validation
            to_year: End year for validation
            store_results: Whether to store validation results in database

        Returns:
            Validation results with per-month comparison
        """
        if not self.api_key:
            raise ValueError("QUIVERQUANT_API_KEY not configured")

        if not self.supabase:
            raise ValueError("Supabase not configured")

        logger.info(f"Starting chart validation ({from_year}-{to_year})")

        # Fetch QuiverQuant data (get a large sample)
        qq_data = await self._fetch_quiverquant_data(limit=10000)
        if not qq_data:
            return {"error": "Failed to fetch QuiverQuant data", "validated": 0}

        logger.info(f"Fetched {len(qq_data)} QuiverQuant records")

        # Aggregate QuiverQuant data by month
        qq_monthly = self._aggregate_by_month(qq_data)
        logger.info(f"Aggregated into {len(qq_monthly)} monthly buckets from QuiverQuant")

        # Fetch app chart data
        app_chart_data = await self._fetch_app_chart_data(from_year, to_year)
        logger.info(f"Fetched {len(app_chart_data)} app chart data points")

        # Compare each data point
        results = []
        total_buy_diff = 0
        total_sell_diff = 0
        total_volume_diff = 0

        for app_point in app_chart_data:
            year = app_point["year"]
            month = app_point["month"]
            key = f"{year}-{month:02d}"

            qq_point = qq_monthly.get(key, {"buys": 0, "sells": 0, "volume": 0})

            # Calculate differences
            buy_diff = app_point["buys"] - qq_point["buys"]
            sell_diff = app_point["sells"] - qq_point["sells"]
            volume_diff = app_point["volume"] - qq_point["volume"]

            # Calculate percentage differences (avoid division by zero)
            buy_pct = (buy_diff / qq_point["buys"] * 100) if qq_point["buys"] > 0 else (100 if app_point["buys"] > 0 else 0)
            sell_pct = (sell_diff / qq_point["sells"] * 100) if qq_point["sells"] > 0 else (100 if app_point["sells"] > 0 else 0)
            volume_pct = (volume_diff / qq_point["volume"] * 100) if qq_point["volume"] > 0 else (100 if app_point["volume"] > 0 else 0)

            # Determine status
            status = "match"
            if abs(buy_pct) > 10 or abs(sell_pct) > 10:
                status = "mismatch"
            elif abs(buy_pct) > 5 or abs(sell_pct) > 5:
                status = "warning"

            result = {
                "year": year,
                "month": month,
                "month_label": f"{self._month_name(month)} '{str(year)[-2:]}",
                "app_buys": app_point["buys"],
                "app_sells": app_point["sells"],
                "app_volume": app_point["volume"],
                "qq_buys": qq_point["buys"],
                "qq_sells": qq_point["sells"],
                "qq_volume": qq_point["volume"],
                "buy_diff": buy_diff,
                "sell_diff": sell_diff,
                "volume_diff": volume_diff,
                "buy_pct_diff": round(buy_pct, 1),
                "sell_pct_diff": round(sell_pct, 1),
                "volume_pct_diff": round(volume_pct, 1),
                "status": status,
            }
            results.append(result)

            total_buy_diff += abs(buy_diff)
            total_sell_diff += abs(sell_diff)
            total_volume_diff += abs(volume_diff)

        # Store results if requested
        if store_results:
            await self._store_validation_results(results)

        # Calculate summary statistics
        matches = sum(1 for r in results if r["status"] == "match")
        warnings = sum(1 for r in results if r["status"] == "warning")
        mismatches = sum(1 for r in results if r["status"] == "mismatch")

        summary = {
            "validated_months": len(results),
            "matches": matches,
            "warnings": warnings,
            "mismatches": mismatches,
            "match_rate": round(matches / len(results) * 100, 1) if results else 0,
            "total_buy_diff": total_buy_diff,
            "total_sell_diff": total_sell_diff,
            "total_volume_diff": total_volume_diff,
            "results": results,
        }

        logger.info(f"Chart validation complete: {matches} matches, {warnings} warnings, {mismatches} mismatches")

        return summary

    async def _fetch_quiverquant_data(self, limit: int) -> List[Dict[str, Any]]:
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
                    timeout=120.0,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch QuiverQuant data: {e}")
            return []

    def _aggregate_by_month(self, qq_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate QuiverQuant records by year-month.

        Returns dict keyed by "YYYY-MM" with counts and volume.
        """
        monthly = defaultdict(lambda: {"buys": 0, "sells": 0, "volume": 0})

        for record in qq_data:
            # Parse transaction date
            tx_date = record.get("TransactionDate")
            if not tx_date:
                continue

            try:
                # Handle various date formats
                if "T" in tx_date:
                    dt = datetime.fromisoformat(tx_date.replace("Z", "+00:00"))
                else:
                    dt = datetime.strptime(tx_date[:10], "%Y-%m-%d")

                key = f"{dt.year}-{dt.month:02d}"
            except (ValueError, TypeError):
                continue

            # Determine transaction type
            tx_type = (record.get("Transaction") or "").lower()
            is_buy = "purchase" in tx_type or tx_type == "buy"
            is_sell = "sale" in tx_type or tx_type == "sell"

            if is_buy:
                monthly[key]["buys"] += 1
            elif is_sell:
                monthly[key]["sells"] += 1

            # Parse and add volume
            volume = self._parse_volume(record.get("Range"))
            monthly[key]["volume"] += volume

        return dict(monthly)

    def _parse_volume(self, range_str: Optional[str]) -> float:
        """
        Parse QuiverQuant Range string to get midpoint volume.

        Examples:
            "$1,001 - $15,000" -> 8000.5
            "$15,001 - $50,000" -> 32500.5
        """
        if not range_str:
            return 0

        # Extract numbers from range string
        numbers = re.findall(r"[\d,]+", range_str.replace(",", ""))
        if len(numbers) >= 2:
            min_val = int(numbers[0].replace(",", ""))
            max_val = int(numbers[1].replace(",", ""))
            return (min_val + max_val) / 2
        elif len(numbers) == 1:
            return float(numbers[0].replace(",", ""))

        return 0

    async def _fetch_app_chart_data(
        self, from_year: int, to_year: int
    ) -> List[Dict[str, Any]]:
        """Fetch chart data from app database."""
        try:
            response = (
                self.supabase.table("chart_data")
                .select("year, month, buys, sells, volume")
                .gte("year", from_year)
                .lte("year", to_year)
                .order("year", desc=False)
                .order("month", desc=False)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Failed to fetch app chart data: {e}")
            return []

    async def _store_validation_results(self, results: List[Dict[str, Any]]) -> bool:
        """Store validation results in database."""
        try:
            # Create a summary record in trade_validation_results
            for result in results:
                payload = {
                    "validation_status": result["status"],
                    "match_key": f"chart_{result['year']}_{result['month']:02d}",
                    "field_mismatches": {
                        "buys": {
                            "app": result["app_buys"],
                            "quiver": result["qq_buys"],
                            "diff": result["buy_diff"],
                            "pct_diff": result["buy_pct_diff"],
                        },
                        "sells": {
                            "app": result["app_sells"],
                            "quiver": result["qq_sells"],
                            "diff": result["sell_diff"],
                            "pct_diff": result["sell_pct_diff"],
                        },
                        "volume": {
                            "app": result["app_volume"],
                            "quiver": result["qq_volume"],
                            "diff": result["volume_diff"],
                            "pct_diff": result["volume_pct_diff"],
                        },
                    },
                    "root_cause": "chart_aggregation" if result["status"] != "match" else None,
                    "severity": "warning" if result["status"] == "warning" else (
                        "critical" if result["status"] == "mismatch" else "info"
                    ),
                    "politician_name": None,
                    "ticker": None,
                    "transaction_date": f"{result['year']}-{result['month']:02d}-01",
                    "transaction_type": "chart_validation",
                    "chamber": "all",
                }

                self.supabase.table("trade_validation_results").upsert(
                    payload,
                    on_conflict="match_key",
                ).execute()

            return True
        except Exception as e:
            logger.error(f"Failed to store chart validation results: {e}")
            return False

    def _month_name(self, month: int) -> str:
        """Get abbreviated month name."""
        names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                 "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        return names[month] if 1 <= month <= 12 else ""


# Convenience function
async def validate_charts(
    from_year: int = 2024,
    to_year: int = 2026,
    store_results: bool = True,
) -> Dict[str, Any]:
    """Run chart validation and return results."""
    service = ChartValidationService()
    return await service.validate_chart_data(from_year, to_year, store_results)
