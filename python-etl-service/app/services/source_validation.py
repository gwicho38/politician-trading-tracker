"""
Source Data Validation Service

Validates app data against the original House/Senate disclosure sources.
This provides ground-truth validation since we're comparing against the
same sources our ETL scrapes from.

Validates:
- Total filing counts per month
- Individual disclosure records
- Trading disclosure counts match source filings
"""

import asyncio
import io
import logging
import os
import re
import zipfile
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.lib.database import get_supabase

logger = logging.getLogger(__name__)

# House Clerk URLs
HOUSE_BASE_URL = "https://disclosures-clerk.house.gov"
HOUSE_ZIP_URL_TEMPLATE = "{base_url}/public_disc/financial-pdfs/{year}FD.ZIP"

# Filing types
FILING_TYPE_PTR = "P"  # Periodic Transaction Report (trades)
FILING_TYPE_FD = "FD"  # Financial Disclosure (annual)
FILING_TYPE_NEW = "O"  # New Member


class SourceValidationService:
    """Service for validating app data against original disclosure sources."""

    def __init__(self):
        self.supabase = get_supabase()

    async def validate_house_data(
        self,
        year: int = 2025,
        store_results: bool = True,
    ) -> Dict[str, Any]:
        """
        Validate House trading data against official Clerk index.

        Args:
            year: Year to validate
            store_results: Whether to store validation results

        Returns:
            Validation results with per-month comparison
        """
        if not self.supabase:
            raise ValueError("Supabase not configured")

        logger.info(f"Starting House source validation for {year}")

        # Step 1: Fetch and parse the official House index
        official_index = await self._fetch_house_index(year)
        if not official_index:
            return {"error": f"Failed to fetch House index for {year}", "validated": 0}

        logger.info(f"Fetched {len(official_index)} total filings from House index")

        # Step 2: Aggregate official filings by month
        official_by_month = self._aggregate_filings_by_month(official_index)
        logger.info(f"Official data spans {len(official_by_month)} months")

        # Step 3: Fetch our app's trading disclosures
        app_disclosures = await self._fetch_app_disclosures(year)
        logger.info(f"Fetched {len(app_disclosures)} app trading disclosures")

        # Step 4: Aggregate app disclosures by month
        app_by_month = self._aggregate_app_disclosures_by_month(app_disclosures)

        # Step 5: Fetch chart_data for comparison
        chart_data = await self._fetch_chart_data(year)
        chart_by_month = {f"{year}-{c['month']:02d}": c for c in chart_data}

        # Step 6: Compare each month
        results = []
        all_months = sorted(set(list(official_by_month.keys()) + list(app_by_month.keys())))

        for month_key in all_months:
            official = official_by_month.get(month_key, {
                "total_filings": 0,
                "ptr_filings": 0,
                "doc_ids": set(),
            })
            app = app_by_month.get(month_key, {
                "total_disclosures": 0,
                "buys": 0,
                "sells": 0,
                "doc_ids": set(),
            })
            chart = chart_by_month.get(month_key, {
                "buys": 0,
                "sells": 0,
                "volume": 0,
            })

            # Find missing doc_ids (in official but not in app)
            missing_docs = official["doc_ids"] - app["doc_ids"]
            extra_docs = app["doc_ids"] - official["doc_ids"]

            # Calculate differences
            ptr_diff = app["total_disclosures"] - official["ptr_filings"]

            # Determine status
            coverage_pct = (len(app["doc_ids"]) / len(official["doc_ids"]) * 100) if official["doc_ids"] else 100

            if coverage_pct >= 95:
                status = "match"
            elif coverage_pct >= 80:
                status = "warning"
            else:
                status = "mismatch"

            result = {
                "year": year,
                "month": int(month_key.split("-")[1]),
                "month_key": month_key,
                "month_label": self._format_month_label(month_key),
                # Official source data
                "official_total_filings": official["total_filings"],
                "official_ptr_filings": official["ptr_filings"],
                "official_doc_count": len(official["doc_ids"]),
                # App data
                "app_disclosures": app["total_disclosures"],
                "app_buys": app["buys"],
                "app_sells": app["sells"],
                "app_doc_count": len(app["doc_ids"]),
                # Chart data
                "chart_buys": chart.get("buys", 0),
                "chart_sells": chart.get("sells", 0),
                "chart_volume": chart.get("volume", 0),
                # Comparison
                "coverage_pct": round(coverage_pct, 1),
                "missing_doc_count": len(missing_docs),
                "extra_doc_count": len(extra_docs),
                "missing_docs": list(missing_docs)[:20],  # First 20 for reference
                "status": status,
            }
            results.append(result)

        # Store results if requested
        if store_results:
            await self._store_validation_results(results, year)

        # Calculate summary
        total_official_ptrs = sum(r["official_ptr_filings"] for r in results)
        total_app_disclosures = sum(r["app_disclosures"] for r in results)
        matches = sum(1 for r in results if r["status"] == "match")
        warnings = sum(1 for r in results if r["status"] == "warning")
        mismatches = sum(1 for r in results if r["status"] == "mismatch")

        overall_coverage = (total_app_disclosures / total_official_ptrs * 100) if total_official_ptrs > 0 else 0

        return {
            "year": year,
            "source": "house_clerk",
            "validated_months": len(results),
            "matches": matches,
            "warnings": warnings,
            "mismatches": mismatches,
            "total_official_ptr_filings": total_official_ptrs,
            "total_app_disclosures": total_app_disclosures,
            "overall_coverage_pct": round(overall_coverage, 1),
            "results": results,
        }

    async def validate_individual_records(
        self,
        year: int,
        month: Optional[int] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Validate individual disclosure records against source.

        Checks that each official filing has a corresponding app record.

        Args:
            year: Year to validate
            month: Optional month filter (1-12)
            limit: Max records to return

        Returns:
            Per-record validation results
        """
        if not self.supabase:
            raise ValueError("Supabase not configured")

        # Fetch official index
        official_index = await self._fetch_house_index(year)
        if not official_index:
            return {"error": f"Failed to fetch House index for {year}"}

        # Filter to PTR filings only
        ptr_filings = [f for f in official_index if f.get("filing_type") == FILING_TYPE_PTR]

        # Filter by month if specified
        if month:
            ptr_filings = [
                f for f in ptr_filings
                if self._get_filing_month(f.get("filing_date")) == month
            ]

        logger.info(f"Validating {len(ptr_filings)} PTR filings")

        # Fetch app source documents
        app_docs = await self._fetch_app_source_documents(year)
        app_doc_ids = {d["source_document_id"] for d in app_docs if d.get("source_document_id")}

        # Compare each filing
        results = []
        for filing in ptr_filings[:limit]:
            doc_id = filing.get("doc_id")
            in_app = doc_id in app_doc_ids

            results.append({
                "doc_id": doc_id,
                "politician_name": filing.get("politician_name"),
                "filing_date": filing.get("filing_date"),
                "filing_type": filing.get("filing_type"),
                "in_app": in_app,
                "status": "match" if in_app else "missing",
            })

        # Summary
        matched = sum(1 for r in results if r["status"] == "match")
        missing = sum(1 for r in results if r["status"] == "missing")

        return {
            "year": year,
            "month": month,
            "total_checked": len(results),
            "matched": matched,
            "missing": missing,
            "coverage_pct": round(matched / len(results) * 100, 1) if results else 0,
            "results": results,
        }

    async def _fetch_house_index(self, year: int) -> List[Dict[str, Any]]:
        """Fetch and parse the House disclosure index for a year."""
        url = HOUSE_ZIP_URL_TEMPLATE.format(base_url=HOUSE_BASE_URL, year=year)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; ValidationBot/1.0)"},
                )

                if response.status_code != 200:
                    logger.error(f"Failed to download House ZIP: {response.status_code}")
                    return []

                zip_content = response.content
                logger.info(f"Downloaded House ZIP: {len(zip_content):,} bytes")

                # Extract index file
                txt_filename = f"{year}FD.txt"
                with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
                    if txt_filename not in z.namelist():
                        logger.error(f"Index file {txt_filename} not found in ZIP")
                        return []

                    with z.open(txt_filename) as f:
                        content = f.read().decode("utf-8", errors="ignore")

                # Parse index
                return self._parse_house_index(content, year)

        except Exception as e:
            logger.error(f"Error fetching House index: {e}")
            return []

    def _parse_house_index(self, content: str, year: int) -> List[Dict[str, Any]]:
        """Parse House disclosure index content."""
        lines = content.strip().split("\n")
        filings = []

        for line in lines[1:]:  # Skip header
            fields = line.split("\t")
            if len(fields) < 9:
                continue

            prefix, last_name, first_name, suffix = fields[0:4]
            filing_type, state_district, file_year = fields[4:7]
            filing_date_str, doc_id = fields[7:9]

            doc_id = doc_id.strip()
            if not doc_id or doc_id == "DocID":
                continue

            # Parse filing date
            filing_date = None
            if filing_date_str:
                try:
                    filing_date = datetime.strptime(filing_date_str.strip(), "%m/%d/%Y").isoformat()
                except ValueError:
                    pass

            # Build full name
            name_parts = [p.strip() for p in [prefix, first_name, last_name, suffix] if p.strip()]
            full_name = " ".join(name_parts)

            filings.append({
                "doc_id": doc_id,
                "politician_name": full_name,
                "filing_type": filing_type.strip(),
                "filing_date": filing_date,
                "state_district": state_district.strip(),
                "year": year,
            })

        return filings

    def _aggregate_filings_by_month(self, filings: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Aggregate official filings by month."""
        by_month = defaultdict(lambda: {
            "total_filings": 0,
            "ptr_filings": 0,
            "doc_ids": set(),
        })

        for filing in filings:
            month = self._get_filing_month(filing.get("filing_date"))
            year = filing.get("year")
            if not month or not year:
                continue

            key = f"{year}-{month:02d}"
            by_month[key]["total_filings"] += 1
            by_month[key]["doc_ids"].add(filing.get("doc_id"))

            if filing.get("filing_type") == FILING_TYPE_PTR:
                by_month[key]["ptr_filings"] += 1

        return dict(by_month)

    def _get_filing_month(self, filing_date: Optional[str]) -> Optional[int]:
        """Extract month from filing date string."""
        if not filing_date:
            return None
        try:
            dt = datetime.fromisoformat(filing_date)
            return dt.month
        except (ValueError, TypeError):
            return None

    async def _fetch_app_disclosures(self, year: int) -> List[Dict[str, Any]]:
        """Fetch trading disclosures from app database for a year."""
        try:
            # Query disclosures with disclosure_date in the given year
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"

            response = (
                self.supabase.table("trading_disclosures")
                .select("id, source_document_id, disclosure_date, transaction_type, politician_id")
                .eq("status", "active")
                .gte("disclosure_date", start_date)
                .lte("disclosure_date", end_date)
                .limit(10000)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Failed to fetch app disclosures: {e}")
            return []

    async def _fetch_app_source_documents(self, year: int) -> List[Dict[str, Any]]:
        """Fetch unique source documents from app database."""
        try:
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"

            response = (
                self.supabase.table("trading_disclosures")
                .select("source_document_id")
                .eq("status", "active")
                .gte("disclosure_date", start_date)
                .lte("disclosure_date", end_date)
                .limit(10000)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Failed to fetch source documents: {e}")
            return []

    def _aggregate_app_disclosures_by_month(
        self, disclosures: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Aggregate app disclosures by month."""
        by_month = defaultdict(lambda: {
            "total_disclosures": 0,
            "buys": 0,
            "sells": 0,
            "doc_ids": set(),
        })

        for d in disclosures:
            date_str = d.get("disclosure_date")
            if not date_str:
                continue

            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                key = f"{dt.year}-{dt.month:02d}"
            except (ValueError, TypeError):
                continue

            by_month[key]["total_disclosures"] += 1

            tx_type = (d.get("transaction_type") or "").lower()
            if tx_type == "purchase":
                by_month[key]["buys"] += 1
            elif tx_type in ("sale", "sale_partial", "sale_full"):
                by_month[key]["sells"] += 1

            doc_id = d.get("source_document_id")
            if doc_id:
                by_month[key]["doc_ids"].add(doc_id)

        return dict(by_month)

    async def _fetch_chart_data(self, year: int) -> List[Dict[str, Any]]:
        """Fetch chart_data for a year."""
        try:
            response = (
                self.supabase.table("chart_data")
                .select("month, buys, sells, volume")
                .eq("year", year)
                .order("month")
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Failed to fetch chart data: {e}")
            return []

    def _format_month_label(self, month_key: str) -> str:
        """Format month key as display label."""
        month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        try:
            year, month = month_key.split("-")
            return f"{month_names[int(month)]} '{year[-2:]}"
        except (ValueError, IndexError):
            return month_key

    async def _store_validation_results(
        self, results: List[Dict[str, Any]], year: int
    ) -> bool:
        """Store validation results in database."""
        try:
            for result in results:
                # Remove non-serializable sets
                result_clean = {k: v for k, v in result.items() if not isinstance(v, set)}

                payload = {
                    "validation_status": result["status"],
                    "match_key": f"source_house_{year}_{result['month']:02d}",
                    "field_mismatches": {
                        "official_ptr_filings": result["official_ptr_filings"],
                        "app_disclosures": result["app_disclosures"],
                        "coverage_pct": result["coverage_pct"],
                        "missing_doc_count": result["missing_doc_count"],
                        "chart_buys": result["chart_buys"],
                        "chart_sells": result["chart_sells"],
                    },
                    "root_cause": "source_coverage" if result["status"] != "match" else None,
                    "severity": "warning" if result["status"] == "warning" else (
                        "critical" if result["status"] == "mismatch" else "info"
                    ),
                    "politician_name": None,
                    "ticker": None,
                    "transaction_date": f"{year}-{result['month']:02d}-01",
                    "transaction_type": "source_validation",
                    "chamber": "house",
                }

                self.supabase.table("trade_validation_results").upsert(
                    payload,
                    on_conflict="match_key",
                ).execute()

            return True
        except Exception as e:
            logger.error(f"Failed to store validation results: {e}")
            return False


    async def validate_all_years(
        self,
        from_year: int = 2008,
        to_year: int = 2026,
        store_results: bool = True,
    ) -> Dict[str, Any]:
        """
        Validate all historical data across multiple years.

        Fetches all app source_document_ids first (without date filter),
        then validates against each year's official House index.

        Args:
            from_year: Start year for validation
            to_year: End year for validation
            store_results: Whether to store validation results

        Returns:
            Comprehensive validation results across all years
        """
        if not self.supabase:
            raise ValueError("Supabase not configured")

        logger.info(f"Starting comprehensive House validation ({from_year}-{to_year})")

        # Step 1: Fetch ALL app source document IDs (no date filter)
        all_app_doc_ids = await self._fetch_all_app_source_documents()
        logger.info(f"Found {len(all_app_doc_ids)} unique source documents in app")

        yearly_results = []
        total_official_ptrs = 0
        total_matched = 0
        total_missing = 0

        # Step 2: Validate each year
        for year in range(from_year, to_year + 1):
            logger.info(f"Validating year {year}...")

            # Fetch official index for this year
            official_index = await self._fetch_house_index(year)
            if not official_index:
                yearly_results.append({
                    "year": year,
                    "status": "error",
                    "error": f"Failed to fetch House index for {year}",
                })
                continue

            # Filter to PTR filings only
            ptr_filings = [f for f in official_index if f.get("filing_type") == FILING_TYPE_PTR]
            official_ptr_doc_ids = {f["doc_id"] for f in ptr_filings if f.get("doc_id")}

            # Calculate matches
            matched_docs = official_ptr_doc_ids & all_app_doc_ids
            missing_docs = official_ptr_doc_ids - all_app_doc_ids

            coverage_pct = (len(matched_docs) / len(official_ptr_doc_ids) * 100) if official_ptr_doc_ids else 100

            if coverage_pct >= 95:
                status = "match"
            elif coverage_pct >= 80:
                status = "warning"
            else:
                status = "mismatch"

            year_result = {
                "year": year,
                "official_ptr_count": len(official_ptr_doc_ids),
                "matched_count": len(matched_docs),
                "missing_count": len(missing_docs),
                "coverage_pct": round(coverage_pct, 1),
                "status": status,
                "sample_missing": list(missing_docs)[:10],
            }
            yearly_results.append(year_result)

            total_official_ptrs += len(official_ptr_doc_ids)
            total_matched += len(matched_docs)
            total_missing += len(missing_docs)

            # Store results if requested
            if store_results:
                await self._store_yearly_validation(year_result)

        # Calculate overall summary
        overall_coverage = (total_matched / total_official_ptrs * 100) if total_official_ptrs > 0 else 0

        matches = sum(1 for r in yearly_results if r.get("status") == "match")
        warnings = sum(1 for r in yearly_results if r.get("status") == "warning")
        mismatches = sum(1 for r in yearly_results if r.get("status") == "mismatch")
        errors = sum(1 for r in yearly_results if r.get("status") == "error")

        return {
            "source": "house_clerk",
            "from_year": from_year,
            "to_year": to_year,
            "years_validated": len(yearly_results) - errors,
            "total_app_documents": len(all_app_doc_ids),
            "total_official_ptr_filings": total_official_ptrs,
            "total_matched": total_matched,
            "total_missing": total_missing,
            "overall_coverage_pct": round(overall_coverage, 1),
            "summary": {
                "matches": matches,
                "warnings": warnings,
                "mismatches": mismatches,
                "errors": errors,
            },
            "yearly_results": yearly_results,
        }

    async def _fetch_all_app_source_documents(self) -> set:
        """Fetch all unique source document IDs from app database (no date filter)."""
        try:
            all_doc_ids = set()
            offset = 0
            page_size = 10000

            while True:
                response = (
                    self.supabase.table("trading_disclosures")
                    .select("source_document_id")
                    .eq("status", "active")
                    .not_.is_("source_document_id", "null")
                    .range(offset, offset + page_size - 1)
                    .execute()
                )

                if not response.data:
                    break

                for row in response.data:
                    doc_id = row.get("source_document_id")
                    if doc_id:
                        all_doc_ids.add(str(doc_id))

                if len(response.data) < page_size:
                    break

                offset += page_size
                logger.info(f"Fetched {len(all_doc_ids)} source documents so far...")

            return all_doc_ids
        except Exception as e:
            logger.error(f"Failed to fetch all source documents: {e}")
            return set()

    async def _store_yearly_validation(self, result: Dict[str, Any]) -> bool:
        """Store yearly validation result."""
        try:
            year = result["year"]
            payload = {
                "validation_status": result["status"],
                "match_key": f"source_house_yearly_{year}",
                "field_mismatches": {
                    "official_ptr_count": result["official_ptr_count"],
                    "matched_count": result["matched_count"],
                    "missing_count": result["missing_count"],
                    "coverage_pct": result["coverage_pct"],
                },
                "root_cause": "source_coverage" if result["status"] != "match" else None,
                "severity": "warning" if result["status"] == "warning" else (
                    "critical" if result["status"] == "mismatch" else "info"
                ),
                "politician_name": None,
                "ticker": None,
                "transaction_date": f"{year}-01-01",
                "transaction_type": "yearly_source_validation",
                "chamber": "house",
            }

            self.supabase.table("trade_validation_results").upsert(
                payload,
                on_conflict="match_key",
            ).execute()

            return True
        except Exception as e:
            logger.error(f"Failed to store yearly validation: {e}")
            return False


# Convenience functions
async def validate_house_source(year: int = 2025, store: bool = True) -> Dict[str, Any]:
    """Validate House data against official source."""
    service = SourceValidationService()
    return await service.validate_house_data(year, store)


async def validate_records(year: int, month: Optional[int] = None, limit: int = 100) -> Dict[str, Any]:
    """Validate individual records against source."""
    service = SourceValidationService()
    return await service.validate_individual_records(year, month, limit)


async def validate_all_historical(from_year: int = 2008, to_year: int = 2026, store: bool = True) -> Dict[str, Any]:
    """Validate all historical data across years."""
    service = SourceValidationService()
    return await service.validate_all_years(from_year, to_year, store)


class CountBasedValidationService:
    """
    Alternative validation that compares record counts rather than exact document IDs.

    Useful when source_document_id isn't populated, but we want to verify
    we have approximately the right number of records.
    """

    def __init__(self):
        self.supabase = get_supabase()

    async def validate_counts(
        self,
        from_year: int = 2008,
        to_year: int = 2026,
        chamber: str = "house",
    ) -> Dict[str, Any]:
        """
        Compare record counts against official source counts.

        This doesn't require source_document_id - it just compares:
        - Number of official PTR filings per year
        - Number of trading_disclosures records per year
        - Chart data aggregates per year

        Args:
            from_year: Start year
            to_year: End year
            chamber: Chamber to validate (house or senate)

        Returns:
            Count comparison results
        """
        if not self.supabase:
            raise ValueError("Supabase not configured")

        logger.info(f"Starting count-based validation ({from_year}-{to_year})")

        yearly_results = []

        for year in range(from_year, to_year + 1):
            logger.info(f"Validating counts for {year}...")

            # Get official PTR count
            official_count = await self._get_official_ptr_count(year)

            # Get app disclosure count (by disclosure_date)
            app_by_disclosure = await self._get_app_disclosure_count(year, "disclosure_date")

            # Get app disclosure count (by transaction_date) - may differ
            app_by_transaction = await self._get_app_disclosure_count(year, "transaction_date")

            # Get chart data totals
            chart_totals = await self._get_chart_data_totals(year)

            # Get unique politicians count
            app_politicians = await self._get_app_politicians_count(year)
            official_politicians = await self._get_official_politicians_count(year)

            # Calculate ratios
            disclosure_ratio = (app_by_disclosure / official_count * 100) if official_count > 0 else 0
            transaction_ratio = (app_by_transaction / official_count * 100) if official_count > 0 else 0
            chart_ratio = ((chart_totals["buys"] + chart_totals["sells"]) / official_count * 100) if official_count > 0 else 0

            # Determine status based on chart data ratio (most reliable)
            if chart_ratio >= 90:
                status = "good"
            elif chart_ratio >= 50:
                status = "partial"
            else:
                status = "low"

            yearly_results.append({
                "year": year,
                "official_ptr_count": official_count,
                "app_disclosures_by_disclosure_date": app_by_disclosure,
                "app_disclosures_by_transaction_date": app_by_transaction,
                "chart_buys": chart_totals["buys"],
                "chart_sells": chart_totals["sells"],
                "chart_total_trades": chart_totals["buys"] + chart_totals["sells"],
                "chart_volume": chart_totals["volume"],
                "app_unique_politicians": app_politicians,
                "official_unique_politicians": official_politicians,
                "disclosure_ratio_pct": round(disclosure_ratio, 1),
                "transaction_ratio_pct": round(transaction_ratio, 1),
                "chart_ratio_pct": round(chart_ratio, 1),
                "status": status,
            })

        # Calculate totals
        total_official = sum(r["official_ptr_count"] for r in yearly_results)
        total_chart_trades = sum(r["chart_total_trades"] for r in yearly_results)
        total_app_disclosures = sum(r["app_disclosures_by_disclosure_date"] for r in yearly_results)

        overall_chart_ratio = (total_chart_trades / total_official * 100) if total_official > 0 else 0

        good_years = sum(1 for r in yearly_results if r["status"] == "good")
        partial_years = sum(1 for r in yearly_results if r["status"] == "partial")
        low_years = sum(1 for r in yearly_results if r["status"] == "low")

        return {
            "validation_type": "count_based",
            "from_year": from_year,
            "to_year": to_year,
            "chamber": chamber,
            "total_official_ptrs": total_official,
            "total_chart_trades": total_chart_trades,
            "total_app_disclosures": total_app_disclosures,
            "overall_chart_ratio_pct": round(overall_chart_ratio, 1),
            "summary": {
                "good_years": good_years,
                "partial_years": partial_years,
                "low_years": low_years,
            },
            "yearly_results": yearly_results,
            "interpretation": self._get_interpretation(overall_chart_ratio, total_official, total_chart_trades),
        }

    async def _get_official_ptr_count(self, year: int) -> int:
        """Get count of PTR filings from official House index."""
        try:
            url = HOUSE_ZIP_URL_TEMPLATE.format(base_url=HOUSE_BASE_URL, year=year)

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; ValidationBot/1.0)"},
                )

                if response.status_code != 200:
                    return 0

                zip_content = response.content
                txt_filename = f"{year}FD.txt"

                with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
                    if txt_filename not in z.namelist():
                        return 0

                    with z.open(txt_filename) as f:
                        content = f.read().decode("utf-8", errors="ignore")

                # Count PTR filings (filing_type = "P")
                count = 0
                for line in content.strip().split("\n")[1:]:
                    fields = line.split("\t")
                    if len(fields) >= 5 and fields[4].strip() == "P":
                        count += 1

                return count

        except Exception as e:
            logger.error(f"Error getting official PTR count: {e}")
            return 0

    async def _get_app_disclosure_count(self, year: int, date_field: str) -> int:
        """Get count of app disclosures for a year."""
        try:
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"

            response = (
                self.supabase.table("trading_disclosures")
                .select("id", count="exact")
                .eq("status", "active")
                .gte(date_field, start_date)
                .lte(date_field, end_date)
                .execute()
            )
            return response.count or 0
        except Exception as e:
            logger.error(f"Error getting app disclosure count: {e}")
            return 0

    async def _get_chart_data_totals(self, year: int) -> Dict[str, int]:
        """Get chart data totals for a year."""
        try:
            response = (
                self.supabase.table("chart_data")
                .select("buys, sells, volume")
                .eq("year", year)
                .execute()
            )

            buys = sum(r.get("buys", 0) for r in (response.data or []))
            sells = sum(r.get("sells", 0) for r in (response.data or []))
            volume = sum(r.get("volume", 0) for r in (response.data or []))

            return {"buys": buys, "sells": sells, "volume": volume}
        except Exception as e:
            logger.error(f"Error getting chart data: {e}")
            return {"buys": 0, "sells": 0, "volume": 0}

    async def _get_app_politicians_count(self, year: int) -> int:
        """Get count of unique politicians in app data for a year."""
        try:
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"

            response = (
                self.supabase.table("trading_disclosures")
                .select("politician_id")
                .eq("status", "active")
                .gte("disclosure_date", start_date)
                .lte("disclosure_date", end_date)
                .execute()
            )

            unique_ids = set(r["politician_id"] for r in (response.data or []) if r.get("politician_id"))
            return len(unique_ids)
        except Exception as e:
            logger.error(f"Error getting app politicians count: {e}")
            return 0

    async def _get_official_politicians_count(self, year: int) -> int:
        """Get count of unique politicians in official index for a year."""
        try:
            url = HOUSE_ZIP_URL_TEMPLATE.format(base_url=HOUSE_BASE_URL, year=year)

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; ValidationBot/1.0)"},
                )

                if response.status_code != 200:
                    return 0

                zip_content = response.content
                txt_filename = f"{year}FD.txt"

                with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
                    if txt_filename not in z.namelist():
                        return 0

                    with z.open(txt_filename) as f:
                        content = f.read().decode("utf-8", errors="ignore")

                # Get unique politicians from PTR filings
                politicians = set()
                for line in content.strip().split("\n")[1:]:
                    fields = line.split("\t")
                    if len(fields) >= 5 and fields[4].strip() == "P":
                        # fields[1] is last name, fields[2] is first name
                        name = f"{fields[2].strip()} {fields[1].strip()}"
                        politicians.add(name.lower())

                return len(politicians)

        except Exception as e:
            logger.error(f"Error getting official politicians count: {e}")
            return 0

    def _get_interpretation(self, ratio: float, official: int, chart: int) -> str:
        """Generate human-readable interpretation of results."""
        if ratio >= 100:
            return f"Chart data ({chart:,} trades) exceeds official PTR count ({official:,}). This is expected since one PTR filing can contain multiple trades."
        elif ratio >= 80:
            return f"Good coverage. Chart data ({chart:,} trades) represents {ratio:.1f}% of official filings ({official:,}). Data is likely complete."
        elif ratio >= 50:
            return f"Partial coverage. Chart data ({chart:,} trades) represents {ratio:.1f}% of official filings ({official:,}). Some data may be missing."
        else:
            return f"Low coverage. Chart data ({chart:,} trades) represents only {ratio:.1f}% of official filings ({official:,}). Significant data gap detected."


async def validate_counts(from_year: int = 2008, to_year: int = 2026) -> Dict[str, Any]:
    """Run count-based validation."""
    service = CountBasedValidationService()
    return await service.validate_counts(from_year, to_year)
