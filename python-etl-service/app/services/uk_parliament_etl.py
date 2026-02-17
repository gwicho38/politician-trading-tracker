"""
UK Parliament Register of Interests ETL Service.

Fetches MP financial interests (shareholdings, employment, gifts, property)
from the official Register of Interests API and loads them into
trading_disclosures with per-MP incremental upload.

Data sources:
- Members API: https://members-api.parliament.uk/api/Members/Search
- Interests API: https://interests-api.parliament.uk/api/v1/Interests
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.lib.base_etl import BaseETLService, ETLResult, JobStatus
from app.lib.database import get_supabase, upload_transaction_to_supabase
from app.lib.politician import find_or_create_politician
from app.lib.registry import ETLRegistry

logger = logging.getLogger(__name__)

MEMBERS_API_BASE = "https://members-api.parliament.uk/api"
INTERESTS_API_BASE = "https://interests-api.parliament.uk/api/v1"

# UK Parliament interest category ID -> transaction_type
CATEGORY_MAP: Dict[int, str] = {
    # Income categories
    1: "income",    # Ad hoc payments (subcategory of Employment)
    2: "income",    # Ongoing paid employment (subcategory of Employment)
    12: "income",   # Employment and earnings (parent)
    # Holding categories
    7: "holding",   # Land and property
    8: "holding",   # Shareholdings
    # Gift categories
    3: "gift",      # Donations and other support
    4: "gift",      # Gifts, benefits and hospitality from UK sources
    5: "gift",      # Visits outside the UK
    6: "gift",      # Gifts and benefits from sources outside the UK
    # Other categories
    9: "other",     # Miscellaneous
    10: "other",    # Family members employed
    11: "other",    # Family members engaged in lobbying
}


@ETLRegistry.register
class UKParliamentETLService(BaseETLService):
    """
    UK Parliament financial interests ETL service.

    Fetches MP interests from the Register of Interests API,
    parses all 10 categories of financial declarations, and uploads
    to trading_disclosures with per-MP incremental upload.
    """

    source_id = "uk_parliament"
    source_name = "UK Parliament"

    async def fetch_disclosures(self, **kwargs) -> List[Dict[str, Any]]:
        """Not used — run() handles fetch+upload per MP."""
        return []

    async def parse_disclosure(
        self, raw: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Validate and pass through a pre-parsed interest record."""
        if not raw.get("asset_name"):
            return None
        return raw

    async def upload_disclosure(
        self,
        disclosure: Dict[str, Any],
        update_mode: bool = False,
    ) -> Optional[str]:
        """Upload a disclosure using the pre-resolved politician_id."""
        try:
            supabase = get_supabase()
            if not supabase:
                return None

            politician_id = disclosure.get("politician_id")
            if not politician_id:
                # Fallback: resolve politician (shouldn't happen in normal flow)
                politician_id = find_or_create_politician(
                    supabase,
                    name=disclosure.get("politician_name"),
                    first_name=disclosure.get("first_name"),
                    last_name=disclosure.get("last_name"),
                    chamber="uk_parliament",
                    state=disclosure.get("state"),
                    bioguide_id=disclosure.get("bioguide_id"),
                    party=disclosure.get("party"),
                )

            if not politician_id:
                return None

            return upload_transaction_to_supabase(
                supabase, politician_id, disclosure, disclosure,
                update_mode=update_mode,
            )

        except Exception as e:
            self.logger.error(f"Upload failed: {e}")
            return None

    # =========================================================================
    # Data Fetching
    # =========================================================================

    async def _fetch_mp_list(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch current House of Commons MPs from the Members API.

        Args:
            limit: Max MPs to return (for testing).

        Returns:
            List of dicts with id, name, first_name, last_name, party, constituency.
        """
        mps: List[Dict[str, Any]] = []
        skip = 0
        take = 20

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                resp = await client.get(
                    f"{MEMBERS_API_BASE}/Members/Search",
                    params={
                        "House": 1,  # Commons
                        "IsCurrentMember": True,
                        "skip": skip,
                        "take": take,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                items = data.get("items", [])
                for item in items:
                    member = item.get("value", {})
                    name = member.get("nameDisplayAs", "")
                    name_parts = member.get("nameListAs", "").split(", ", 1)
                    last_name = name_parts[0].strip() if name_parts else ""
                    first_name = (
                        name_parts[1].strip() if len(name_parts) > 1 else ""
                    )

                    party_info = member.get("latestParty", {})
                    house_info = member.get("latestHouseMembership", {})

                    mps.append({
                        "id": member.get("id"),
                        "name": name,
                        "first_name": first_name,
                        "last_name": last_name,
                        "party": party_info.get("name", ""),
                        "constituency": house_info.get("membershipFrom", ""),
                    })

                    if limit and len(mps) >= limit:
                        return mps

                total = data.get("totalResults", 0)
                skip += len(items)
                if skip >= total or not items:
                    break

        self.logger.info(f"Fetched {len(mps)} MPs from Members API")
        return mps

    async def _fetch_mp_interests(
        self, mp_id: int
    ) -> List[Dict[str, Any]]:
        """Fetch all interests for a single MP from the Interests API.

        Args:
            mp_id: The Parliament Members API ID for the MP.

        Returns:
            List of raw interest dicts from the API, with child interests expanded.
        """
        interests: List[Dict[str, Any]] = []
        skip = 0
        take = 20

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                resp = await client.get(
                    f"{INTERESTS_API_BASE}/Interests",
                    params={
                        "MemberId": mp_id,
                        "ExpandChildInterests": True,
                        "skip": skip,
                        "take": take,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                items = data.get("items", [])
                for item in items:
                    # Interests API returns items directly (no "value" wrapper)
                    interests.append(item)

                total = data.get("totalResults", 0)
                skip += len(items)
                if skip >= total or not items:
                    break

        return interests

    # =========================================================================
    # Parsing
    # =========================================================================

    def _parse_interest(
        self, interest: Dict[str, Any], mp: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Parse a single interest (with children) into disclosure records.

        Parent interests without children produce one record.
        Parent interests with children produce one record per child
        (the child carries the payment details).

        Args:
            interest: Raw interest dict from the Interests API.
            mp: MP dict from _fetch_mp_list().

        Returns:
            List of disclosure dicts ready for parse_disclosure/upload.
        """
        category_id = interest.get("category", {}).get("id", 0)
        transaction_type = CATEGORY_MAP.get(category_id, "other")
        summary = (interest.get("summary") or "")[:200]
        reg_date = interest.get("registrationDate")
        pub_date = interest.get("publishedDate")

        base = {
            "politician_name": mp["name"],
            "first_name": mp["first_name"],
            "last_name": mp["last_name"],
            "bioguide_id": str(mp["id"]),
            "chamber": "uk_parliament",
            "party": mp["party"],
            "state": "United Kingdom",
            "district": mp["constituency"],
            "source": "uk_parliament",
            "filing_date": reg_date,
            "notification_date": pub_date,
        }

        children = interest.get("childInterests") or []

        if children:
            records = []
            for child in children:
                record = {**base}
                record["asset_name"] = summary
                record["transaction_type"] = transaction_type
                record["doc_id"] = str(
                    child.get("id", interest.get("id", ""))
                )

                amount = self._extract_amount(child.get("fields", []))
                record["value_low"] = amount
                record["value_high"] = amount

                received_date = self._extract_field(
                    child.get("fields", []), "ReceivedDate"
                )
                record["transaction_date"] = received_date or reg_date

                record["raw_data"] = {
                    "parent_interest_id": interest.get("id"),
                    "child_interest_id": child.get("id"),
                    "category": interest.get("category", {}).get("name"),
                    "fields": child.get("fields", []),
                }

                records.append(record)
            return records
        else:
            record = {**base}
            record["asset_name"] = summary
            record["transaction_type"] = transaction_type
            record["doc_id"] = str(interest.get("id", ""))
            record["transaction_date"] = reg_date

            amount = self._extract_amount(interest.get("fields", []))
            record["value_low"] = amount
            record["value_high"] = amount

            record["raw_data"] = {
                "interest_id": interest.get("id"),
                "category": interest.get("category", {}).get("name"),
                "fields": interest.get("fields", []),
            }

            return [record]

    @staticmethod
    def _extract_amount(fields: List[Dict[str, Any]]) -> Optional[float]:
        """Extract GBP amount from interest fields."""
        for f in fields:
            type_info = f.get("typeInfo") or {}
            if type_info.get("currencyCode") == "GBP":
                try:
                    return float(f["value"])
                except (ValueError, KeyError, TypeError):
                    pass
            if f.get("name") == "Value" and f.get("value"):
                try:
                    return float(f["value"])
                except (ValueError, TypeError):
                    pass
        return None

    @staticmethod
    def _extract_field(
        fields: List[Dict[str, Any]], name: str
    ) -> Optional[str]:
        """Extract a named field value from the fields list."""
        for f in fields:
            if f.get("name") == name:
                return f.get("value")
        return None

    # =========================================================================
    # Main Execution — Incremental Per-MP Upload
    # =========================================================================

    async def run(
        self,
        job_id: str,
        limit: Optional[int] = None,
        update_mode: bool = False,
        **kwargs,
    ) -> ETLResult:
        """Execute UK Parliament ETL with incremental per-MP uploads."""
        result = ETLResult(started_at=datetime.now(timezone.utc))
        self._job_status[job_id] = JobStatus(
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
            message=f"Starting {self.source_name} ETL...",
        )

        try:
            await self.on_start(job_id, **kwargs)

            supabase = get_supabase()
            if not supabase:
                result.add_error("Supabase client not available")
                self._job_status[job_id].status = "failed"
                self._job_status[job_id].message = "Supabase unavailable"
                return result

            self.update_job_status(job_id, message="Fetching MP list...")
            mps = await self._fetch_mp_list(limit=limit)

            if not mps:
                result.add_warning("No MPs fetched from Members API")
                self.update_job_status(
                    job_id, status="completed",
                    message="No MPs to process",
                )
                result.completed_at = datetime.now(timezone.utc)
                return result

            total_mps = len(mps)
            self.update_job_status(job_id, total=total_mps)
            self.logger.info(
                f"Processing {total_mps} MPs with incremental upload"
            )

            for i, mp in enumerate(mps):
                mp_name = mp["name"]
                uploaded = result.records_inserted + result.records_updated
                self.update_job_status(
                    job_id, progress=i + 1,
                    message=(
                        f"MP {i + 1}/{total_mps}: {mp_name} "
                        f"({uploaded} uploaded)"
                    ),
                )

                try:
                    interests = await self._fetch_mp_interests(mp["id"])
                except Exception as e:
                    result.records_failed += 1
                    result.add_error(
                        f"Failed to fetch interests for {mp_name}: {e}"
                    )
                    continue

                # Resolve politician once per MP
                politician_id = find_or_create_politician(
                    supabase,
                    name=mp["name"],
                    first_name=mp["first_name"],
                    last_name=mp["last_name"],
                    chamber="uk_parliament",
                    state="United Kingdom",
                    district=mp["constituency"],
                    bioguide_id=str(mp["id"]),
                    party=mp["party"],
                )

                if not politician_id:
                    result.records_failed += 1
                    result.add_error(
                        f"Failed to create politician for {mp_name}"
                    )
                    continue

                # Parse and upload each interest immediately
                for interest in interests:
                    records = self._parse_interest(interest, mp)
                    for record in records:
                        result.records_processed += 1
                        try:
                            parsed = await self.parse_disclosure(record)
                            if not parsed:
                                result.records_skipped += 1
                                continue

                            if not await self.validate_disclosure(parsed):
                                result.records_skipped += 1
                                continue

                            # Inject pre-resolved politician_id
                            parsed["politician_id"] = politician_id

                            disclosure_id = await self.upload_disclosure(
                                parsed, update_mode=update_mode
                            )

                            if disclosure_id:
                                if update_mode:
                                    result.records_updated += 1
                                else:
                                    result.records_inserted += 1
                            else:
                                result.records_skipped += 1

                        except Exception as e:
                            result.records_failed += 1
                            result.add_error(f"Failed to upload: {e}")

                if interests:
                    uploaded = result.records_inserted + result.records_updated
                    self.logger.info(
                        f"MP {i + 1}/{total_mps} {mp_name}: "
                        f"uploaded {len(interests)} interests "
                        f"(total: {uploaded})"
                    )

            # Complete
            result.completed_at = datetime.now(timezone.utc)
            self._job_status[job_id].status = "completed"
            self._job_status[job_id].completed_at = (
                datetime.now(timezone.utc).isoformat()
            )
            self._job_status[job_id].result = result
            self._job_status[job_id].message = (
                f"Completed: {result.records_inserted} inserted, "
                f"{result.records_updated} updated, "
                f"{result.records_failed} failed"
            )
            await self.on_complete(job_id, result)

        except Exception as e:
            result.add_error(f"ETL job failed: {e}")
            result.completed_at = datetime.now(timezone.utc)
            self._job_status[job_id].status = "failed"
            self._job_status[job_id].completed_at = (
                datetime.now(timezone.utc).isoformat()
            )
            self._job_status[job_id].message = f"Failed: {e}"
            self.logger.exception(f"UK Parliament ETL failed: {e}")

        return result
