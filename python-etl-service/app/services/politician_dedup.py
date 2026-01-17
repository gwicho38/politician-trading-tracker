"""
Politician Deduplication Service

Identifies and merges duplicate politician records in the database.

Duplicates occur due to:
- Name variations (Hon. prefix, middle names)
- Case differences (McClain vs Mcclain)
- Different spelling/typos

Merge strategy:
1. Group politicians by normalized name
2. Keep the record with the most complete data
3. Update all trading_disclosures to point to the winner
4. Delete duplicate records
"""

import os
import re
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict
from lib.database import get_supabase

from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://uljsqvwkomdrlnofmlad.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")


@dataclass
class DuplicateGroup:
    """A group of duplicate politician records."""
    normalized_name: str
    records: list[dict]
    winner_id: str
    loser_ids: list[str]
    disclosures_to_update: int


class PoliticianDeduplicator:
    """
    Finds and merges duplicate politician records.
    """

    def __init__(self):
        self.supabase = self._get_supabase()

    def _get_supabase(self) -> Client | None:
        """Get Supabase client."""
        return get_supabase()

    def normalize_name(self, name: str) -> str:
        """
        Normalize a politician name for comparison.

        Removes:
        - Honorifics (Hon., Representative, Senator, etc.)
        - Suffixes (Jr., Sr., III, etc.)
        - Extra whitespace
        - Punctuation

        Lowercases and standardizes the name.
        """
        if not name:
            return ""

        # Remove common prefixes
        prefixes = [
            r"^hon\.?\s*",
            r"^honorable\s+",
            r"^representative\s+",
            r"^rep\.?\s*",
            r"^senator\s+",
            r"^sen\.?\s*",
            r"^dr\.?\s*",
            r"^mr\.?\s*",
            r"^mrs\.?\s*",
            r"^ms\.?\s*",
        ]
        normalized = name.lower().strip()
        for prefix in prefixes:
            normalized = re.sub(prefix, "", normalized, flags=re.IGNORECASE)

        # Remove suffixes
        suffixes = [
            r"\s+jr\.?$",
            r"\s+sr\.?$",
            r"\s+ii+$",
            r"\s+iv$",
            r"\s+iii$",
        ]
        for suffix in suffixes:
            normalized = re.sub(suffix, "", normalized, flags=re.IGNORECASE)

        # Remove punctuation except spaces
        normalized = re.sub(r"[^\w\s]", "", normalized)

        # Collapse multiple spaces
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized

    def find_duplicates(self, limit: int = 100) -> list[DuplicateGroup]:
        """
        Find groups of duplicate politicians.

        Returns groups where 2+ records have the same normalized name.
        """
        if not self.supabase:
            return []

        try:
            # Fetch all politicians with pagination (Supabase default limit is 1000)
            all_politicians = []
            page_size = 1000
            offset = 0

            while True:
                response = (
                    self.supabase.table("politicians")
                    .select("id, full_name, first_name, last_name, party, state, chamber, created_at")
                    .range(offset, offset + page_size - 1)
                    .execute()
                )
                if not response.data:
                    break
                all_politicians.extend(response.data)
                if len(response.data) < page_size:
                    break
                offset += page_size

            print(f"[Dedup] Fetched {len(all_politicians)} politicians")

            if not all_politicians:
                return []

            # Group by normalized name
            groups = defaultdict(list)
            for record in all_politicians:
                normalized = self.normalize_name(record.get("full_name", ""))
                if normalized:
                    groups[normalized].append(record)

            # Find groups with duplicates
            duplicate_groups = []
            for normalized_name, records in groups.items():
                if len(records) < 2:
                    continue

                # Determine winner (most complete record)
                winner = self._pick_winner(records)
                losers = [r for r in records if r["id"] != winner["id"]]

                # Count disclosures that need updating
                loser_ids = [r["id"] for r in losers]
                disclosures_count = self._count_disclosures(loser_ids)

                duplicate_groups.append(DuplicateGroup(
                    normalized_name=normalized_name,
                    records=records,
                    winner_id=winner["id"],
                    loser_ids=loser_ids,
                    disclosures_to_update=disclosures_count
                ))

                if len(duplicate_groups) >= limit:
                    break

            return duplicate_groups

        except Exception as e:
            print(f"Error finding duplicates: {e}")
            return []

    def _pick_winner(self, records: list[dict]) -> dict:
        """
        Pick the best record to keep.

        Priority:
        1. Has party data
        2. Has state/chamber data
        3. More complete name (longer full_name usually means more info)
        4. Oldest record (first created)
        """
        def score(record: dict) -> tuple:
            return (
                1 if record.get("party") else 0,
                1 if record.get("state") else 0,
                1 if record.get("chamber") else 0,
                len(record.get("full_name", "")),
                -len(record.get("created_at", "z"))  # Oldest first
            )

        return max(records, key=score)

    def _count_disclosures(self, politician_ids: list[str]) -> int:
        """Count trading disclosures for given politician IDs."""
        if not self.supabase or not politician_ids:
            return 0

        try:
            count = 0
            for pid in politician_ids:
                response = (
                    self.supabase.table("trading_disclosures")
                    .select("id", count="exact")
                    .eq("politician_id", pid)
                    .execute()
                )
                count += response.count or 0
            return count
        except Exception:
            return 0

    def merge_group(self, group: DuplicateGroup, dry_run: bool = False) -> dict:
        """
        Merge a duplicate group.

        1. Update all trading_disclosures to point to winner
        2. Copy any missing data from losers to winner
        3. Delete loser records
        """
        if not self.supabase:
            return {"status": "error", "message": "No database connection"}

        try:
            result = {
                "normalized_name": group.normalized_name,
                "winner_id": group.winner_id,
                "losers_merged": len(group.loser_ids),
                "disclosures_updated": 0,
                "status": "success" if not dry_run else "dry_run"
            }

            if dry_run:
                result["disclosures_to_update"] = group.disclosures_to_update
                return result

            # Get winner's current data
            winner_response = (
                self.supabase.table("politicians")
                .select("*")
                .eq("id", group.winner_id)
                .single()
                .execute()
            )
            winner = winner_response.data

            # Merge data from losers (fill in any missing fields)
            update_data = {}
            for loser_id in group.loser_ids:
                loser_response = (
                    self.supabase.table("politicians")
                    .select("*")
                    .eq("id", loser_id)
                    .single()
                    .execute()
                )
                if loser_response.data:
                    loser = loser_response.data
                    # Copy non-null values to winner if winner's is null
                    for field in ["party", "state", "chamber", "bioguide_id"]:
                        if loser.get(field) and not winner.get(field):
                            update_data[field] = loser[field]
                            winner[field] = loser[field]  # Track for subsequent merges

            # Update winner with merged data
            if update_data:
                update_data["updated_at"] = datetime.utcnow().isoformat()
                self.supabase.table("politicians").update(
                    update_data
                ).eq("id", group.winner_id).execute()

            # Update all disclosures to point to winner
            for loser_id in group.loser_ids:
                update_response = (
                    self.supabase.table("trading_disclosures")
                    .update({"politician_id": group.winner_id})
                    .eq("politician_id", loser_id)
                    .execute()
                )
                if update_response.data:
                    result["disclosures_updated"] += len(update_response.data)

            # Delete loser records
            for loser_id in group.loser_ids:
                self.supabase.table("politicians").delete().eq(
                    "id", loser_id
                ).execute()

            return result

        except Exception as e:
            return {
                "normalized_name": group.normalized_name,
                "status": "error",
                "message": str(e)
            }

    def process_all(self, limit: int = 50, dry_run: bool = False) -> dict:
        """
        Find and merge all duplicate politicians.

        Args:
            limit: Maximum number of duplicate groups to process
            dry_run: If True, report what would happen without making changes

        Returns:
            Summary of processed duplicates
        """
        groups = self.find_duplicates(limit)

        if not groups:
            return {
                "processed": 0,
                "merged": 0,
                "disclosures_updated": 0,
                "errors": 0,
                "dry_run": dry_run,
                "results": []
            }

        results = []
        merged = 0
        disclosures_updated = 0
        errors = 0

        for group in groups:
            result = self.merge_group(group, dry_run)
            results.append(result)

            if result["status"] == "success":
                merged += 1
                disclosures_updated += result.get("disclosures_updated", 0)
            elif result["status"] == "dry_run":
                merged += 1  # Would be merged
            else:
                errors += 1

        return {
            "processed": len(groups),
            "merged": merged,
            "disclosures_updated": disclosures_updated,
            "errors": errors,
            "dry_run": dry_run,
            "results": results
        }

    def preview(self, limit: int = 20) -> dict:
        """
        Preview duplicate groups without merging.
        """
        groups = self.find_duplicates(limit)

        return {
            "duplicate_groups": len(groups),
            "total_duplicates": sum(len(g.loser_ids) for g in groups),
            "groups": [
                {
                    "normalized_name": g.normalized_name,
                    "records": [
                        {
                            "id": r["id"],
                            "full_name": r["full_name"],
                            "party": r.get("party"),
                            "state": r.get("state"),
                            "is_winner": r["id"] == g.winner_id
                        }
                        for r in g.records
                    ],
                    "disclosures_to_update": g.disclosures_to_update
                }
                for g in groups
            ]
        }
