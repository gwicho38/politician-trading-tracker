"""
Source Document ID Backfill Service

Backfills missing source_document_id values in trading_disclosures by matching
records against the official House Clerk disclosure index.

Matching strategy:
1. Download official House index for each year
2. For each PTR filing, find matching app records by:
   - Politician name (fuzzy match)
   - Filing date within a reasonable window
3. Update source_document_id for matched records
"""

import asyncio
import io
import logging
import re
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx

from app.lib.database import get_supabase

logger = logging.getLogger(__name__)

# House Clerk URLs
HOUSE_BASE_URL = "https://disclosures-clerk.house.gov"
HOUSE_ZIP_URL_TEMPLATE = "{base_url}/public_disc/financial-pdfs/{year}FD.ZIP"

# Filing types
FILING_TYPE_PTR = "P"  # Periodic Transaction Report (trades)


class SourceDocumentBackfillService:
    """Service for backfilling missing source_document_id values."""

    def __init__(self):
        self.supabase = get_supabase()

    async def backfill_year(
        self,
        year: int,
        dry_run: bool = True,
        similarity_threshold: float = 0.8,
    ) -> Dict[str, Any]:
        """
        Backfill source_document_id for a specific year.

        Args:
            year: Year to backfill
            dry_run: If True, don't actually update records
            similarity_threshold: Minimum name similarity for matching (0-1)

        Returns:
            Backfill results with match statistics
        """
        if not self.supabase:
            raise ValueError("Supabase not configured")

        logger.info(f"Starting backfill for {year} (dry_run={dry_run})")

        # Step 1: Fetch official House index
        official_index = await self._fetch_house_index(year)
        if not official_index:
            return {"error": f"Failed to fetch House index for {year}", "updated": 0}

        # Filter to PTR filings only
        ptr_filings = [f for f in official_index if f.get("filing_type") == FILING_TYPE_PTR]
        logger.info(f"Found {len(ptr_filings)} PTR filings in House index")

        # Step 2: Fetch app disclosures without source_document_id
        app_records = await self._fetch_records_without_source_id(year)
        logger.info(f"Found {len(app_records)} app records without source_document_id")

        if not app_records:
            return {
                "year": year,
                "official_ptrs": len(ptr_filings),
                "records_without_id": 0,
                "matched": 0,
                "updated": 0,
                "message": "No records need backfilling",
            }

        # Step 3: Build lookup structures
        # Group official filings by normalized politician name
        official_by_name = defaultdict(list)
        for filing in ptr_filings:
            normalized_name = self._normalize_name(filing.get("politician_name", ""))
            if normalized_name:
                official_by_name[normalized_name].append(filing)

        # Step 4: Match app records to official filings
        matches = []
        unmatched = []

        for record in app_records:
            # Get politician name from record
            politician_name = record.get("politician_name")
            if not politician_name:
                # Try to fetch from politicians table
                politician_id = record.get("politician_id")
                if politician_id:
                    politician_name = await self._get_politician_name(politician_id)

            if not politician_name:
                unmatched.append({"record_id": record["id"], "reason": "no_name"})
                continue

            normalized_app_name = self._normalize_name(politician_name)
            disclosure_date = record.get("disclosure_date")

            # Try exact name match first
            best_match = None
            best_score = 0

            # Check exact matches
            if normalized_app_name in official_by_name:
                for filing in official_by_name[normalized_app_name]:
                    score = self._calculate_match_score(record, filing)
                    if score > best_score:
                        best_score = score
                        best_match = filing

            # If no exact match, try fuzzy matching
            if not best_match or best_score < similarity_threshold:
                for name, filings in official_by_name.items():
                    name_similarity = self._name_similarity(normalized_app_name, name)
                    if name_similarity >= similarity_threshold:
                        for filing in filings:
                            score = self._calculate_match_score(record, filing, name_similarity)
                            if score > best_score:
                                best_score = score
                                best_match = filing

            if best_match and best_score >= similarity_threshold:
                matches.append({
                    "record_id": record["id"],
                    "doc_id": best_match["doc_id"],
                    "politician_name": politician_name,
                    "matched_name": best_match.get("politician_name"),
                    "score": round(best_score, 3),
                    "disclosure_date": disclosure_date,
                    "filing_date": best_match.get("filing_date"),
                })
            else:
                unmatched.append({
                    "record_id": record["id"],
                    "politician_name": politician_name,
                    "reason": "no_match",
                    "best_score": round(best_score, 3) if best_score else 0,
                })

        logger.info(f"Matched {len(matches)} records, {len(unmatched)} unmatched")

        # Step 5: Update records if not dry run
        updated = 0
        if not dry_run and matches:
            updated = await self._update_source_document_ids(matches)

        return {
            "year": year,
            "dry_run": dry_run,
            "official_ptrs": len(ptr_filings),
            "records_without_id": len(app_records),
            "matched": len(matches),
            "unmatched": len(unmatched),
            "updated": updated,
            "sample_matches": matches[:10],
            "sample_unmatched": unmatched[:10],
        }

    async def backfill_all_years(
        self,
        from_year: int = 2020,
        to_year: int = 2026,
        dry_run: bool = True,
        similarity_threshold: float = 0.8,
    ) -> Dict[str, Any]:
        """
        Backfill source_document_id for all years.

        Args:
            from_year: Start year
            to_year: End year
            dry_run: If True, don't actually update records
            similarity_threshold: Minimum name similarity for matching

        Returns:
            Comprehensive backfill results
        """
        results = []
        total_matched = 0
        total_updated = 0
        total_unmatched = 0

        for year in range(from_year, to_year + 1):
            logger.info(f"Processing year {year}...")
            year_result = await self.backfill_year(
                year=year,
                dry_run=dry_run,
                similarity_threshold=similarity_threshold,
            )
            results.append(year_result)

            if "error" not in year_result:
                total_matched += year_result.get("matched", 0)
                total_updated += year_result.get("updated", 0)
                total_unmatched += year_result.get("unmatched", 0)

        return {
            "from_year": from_year,
            "to_year": to_year,
            "dry_run": dry_run,
            "total_matched": total_matched,
            "total_updated": total_updated,
            "total_unmatched": total_unmatched,
            "yearly_results": results,
        }

    async def _fetch_house_index(self, year: int) -> List[Dict[str, Any]]:
        """Fetch and parse the House disclosure index for a year."""
        url = HOUSE_ZIP_URL_TEMPLATE.format(base_url=HOUSE_BASE_URL, year=year)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; BackfillBot/1.0)"},
                )

                if response.status_code != 200:
                    logger.error(f"Failed to download House ZIP: {response.status_code}")
                    return []

                zip_content = response.content

                # Extract index file
                txt_filename = f"{year}FD.txt"
                with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
                    if txt_filename not in z.namelist():
                        return []

                    with z.open(txt_filename) as f:
                        content = f.read().decode("utf-8", errors="ignore")

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

    async def _fetch_records_without_source_id(self, year: int) -> List[Dict[str, Any]]:
        """Fetch trading disclosures without source_document_id for a year, with politician names."""
        try:
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"

            # Fetch records with politician join to get names
            response = (
                self.supabase.table("trading_disclosures")
                .select("id, politician_id, disclosure_date, transaction_date, transaction_type, politicians(name)")
                .eq("status", "active")
                .is_("source_document_id", "null")
                .gte("disclosure_date", start_date)
                .lte("disclosure_date", end_date)
                .limit(5000)
                .execute()
            )

            # Flatten the politician name from the join
            records = []
            for row in (response.data or []):
                politician_data = row.get("politicians")
                if politician_data:
                    row["politician_name"] = politician_data.get("name")
                else:
                    row["politician_name"] = None
                records.append(row)

            return records
        except Exception as e:
            logger.error(f"Failed to fetch records: {e}")
            return []

    async def _get_politician_name(self, politician_id: str) -> Optional[str]:
        """Fetch politician name by ID (fallback method)."""
        try:
            response = (
                self.supabase.table("politicians")
                .select("name")
                .eq("id", politician_id)
                .single()
                .execute()
            )
            return response.data.get("name") if response.data else None
        except Exception:
            return None

    def _normalize_name(self, name: str) -> str:
        """Normalize politician name for matching."""
        if not name:
            return ""

        # Remove honorifics and suffixes
        name = re.sub(r"\b(Hon\.?|Rep\.?|Senator|Jr\.?|Sr\.?|III|II|IV)\b", "", name, flags=re.IGNORECASE)

        # Remove punctuation and extra spaces
        name = re.sub(r"[.,]", "", name)
        name = " ".join(name.split())

        return name.lower().strip()

    def _name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names."""
        if not name1 or not name2:
            return 0.0
        return SequenceMatcher(None, name1, name2).ratio()

    def _calculate_match_score(
        self,
        record: Dict[str, Any],
        filing: Dict[str, Any],
        name_similarity: float = 1.0,
    ) -> float:
        """
        Calculate overall match score between record and filing.

        Factors:
        - Name similarity (weight: 0.6)
        - Date proximity (weight: 0.4)
        """
        # Name component
        name_score = name_similarity * 0.6

        # Date component - check if filing date is within reasonable window
        record_date = record.get("disclosure_date") or record.get("transaction_date")
        filing_date = filing.get("filing_date")

        date_score = 0.0
        if record_date and filing_date:
            try:
                if isinstance(record_date, str):
                    record_dt = datetime.fromisoformat(record_date.replace("Z", "+00:00"))
                else:
                    record_dt = record_date

                if isinstance(filing_date, str):
                    filing_dt = datetime.fromisoformat(filing_date)
                else:
                    filing_dt = filing_date

                # Calculate days difference
                days_diff = abs((record_dt.replace(tzinfo=None) - filing_dt.replace(tzinfo=None)).days)

                # Score based on proximity (full score within 7 days, declining after)
                if days_diff <= 7:
                    date_score = 0.4
                elif days_diff <= 30:
                    date_score = 0.4 * (1 - (days_diff - 7) / 23)
                elif days_diff <= 90:
                    date_score = 0.2 * (1 - (days_diff - 30) / 60)

            except (ValueError, TypeError):
                pass

        return name_score + date_score

    async def _update_source_document_ids(self, matches: List[Dict[str, Any]]) -> int:
        """Update source_document_id for matched records."""
        updated = 0
        for match in matches:
            try:
                self.supabase.table("trading_disclosures").update({
                    "source_document_id": match["doc_id"],
                }).eq("id", match["record_id"]).execute()
                updated += 1
            except Exception as e:
                logger.error(f"Failed to update record {match['record_id']}: {e}")

        return updated


# Convenience functions
async def backfill_year(year: int, dry_run: bool = True, threshold: float = 0.8) -> Dict[str, Any]:
    """Backfill source_document_id for a specific year."""
    service = SourceDocumentBackfillService()
    return await service.backfill_year(year, dry_run, threshold)


async def backfill_all(
    from_year: int = 2020,
    to_year: int = 2026,
    dry_run: bool = True,
    threshold: float = 0.8,
) -> Dict[str, Any]:
    """Backfill source_document_id for all years."""
    service = SourceDocumentBackfillService()
    return await service.backfill_all_years(from_year, to_year, dry_run, threshold)
