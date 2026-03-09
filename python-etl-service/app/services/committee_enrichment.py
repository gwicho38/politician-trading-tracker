"""
Committee enrichment service.

Fetches committee assignments from Congress.gov API for all politicians
that have a bioguide_id, then upserts into politician_committees table
with GICS sector mappings from committee_sector_map.

Congress.gov API endpoint:
  GET https://api.congress.gov/v3/member/{bioguideId}/committee-assignments
  ?api_key={CONGRESS_API_KEY}&format=json
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional
import httpx
from supabase import create_client, Client

logger = logging.getLogger(__name__)

CONGRESS_API_BASE = "https://api.congress.gov/v3"
CONGRESS_API_KEY = os.environ.get("CONGRESS_API_KEY", "")

_supabase_client: Optional[Client] = None


def get_supabase() -> Client:
    global _supabase_client
    if _supabase_client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        _supabase_client = create_client(url, key)
    return _supabase_client


def run_committee_enrichment(limit: Optional[int] = None) -> dict:
    """
    Synchronous wrapper for async committee enrichment.
    Returns a result dict with counts of processed/updated/failed politicians.
    """
    return asyncio.run(_run_committee_enrichment_async(limit))


async def _run_committee_enrichment_async(limit: Optional[int]) -> dict:
    supabase = get_supabase()
    results = {"processed": 0, "updated": 0, "skipped": 0, "failed": 0}

    # Fetch politicians with a bioguide_id
    query = (
        supabase.table("politicians")
        .select("id, bioguide_id, full_name")
        .not_.is_("bioguide_id", "null")
    )
    if limit:
        query = query.limit(limit)

    resp = query.execute()
    politicians = resp.data or []
    logger.info(f"[CommitteeEnrichment] Processing {len(politicians)} politicians")

    # Load sector map from DB
    sector_map_resp = supabase.table("committee_sector_map").select("*").execute()
    sector_map = {row["committee_code"]: row["gics_sectors"] for row in (sector_map_resp.data or [])}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for politician in politicians:
            try:
                bio_id = politician["bioguide_id"]
                pol_id = politician["id"]

                committees = await _fetch_committees(client, bio_id)
                results["processed"] += 1

                if not committees:
                    results["skipped"] += 1
                    continue

                records = []
                for c in committees:
                    code = c.get("systemCode", "")
                    name = c.get("name", "")
                    role = _normalize_role(c.get("title", ""))
                    congress = c.get("congress")
                    gics = sector_map.get(code.upper(), [])

                    records.append({
                        "politician_id": pol_id,
                        "committee_name": name,
                        "committee_code": code.upper() if code else None,
                        "gics_sectors": gics,
                        "role": role,
                        "is_leadership": role in ("chair", "ranking_member"),
                        "congress_number": congress,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    })

                if records:
                    supabase.table("politician_committees").upsert(
                        records,
                        on_conflict="politician_id,committee_name,congress_number",
                    ).execute()
                    results["updated"] += 1

            except Exception as exc:
                logger.warning(
                    f"[CommitteeEnrichment] Failed for {politician.get('full_name')}: {exc}"
                )
                results["failed"] += 1

    logger.info(f"[CommitteeEnrichment] Done: {results}")
    return results


async def _fetch_committees(client: httpx.AsyncClient, bioguide_id: str) -> list[dict]:
    """Fetch committee assignments from Congress.gov API."""
    if not CONGRESS_API_KEY:
        logger.warning("[CommitteeEnrichment] CONGRESS_API_KEY not set — skipping API call")
        return []

    url = f"{CONGRESS_API_BASE}/member/{bioguide_id}/committee-assignments"
    params = {"api_key": CONGRESS_API_KEY, "format": "json", "limit": 250}

    try:
        resp = await client.get(url, params=params)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
        return data.get("committeeAssignments", [])
    except httpx.HTTPStatusError as exc:
        logger.warning(f"[CommitteeEnrichment] HTTP {exc.response.status_code} for {bioguide_id}")
        return []
    except Exception as exc:
        logger.warning(f"[CommitteeEnrichment] Error fetching {bioguide_id}: {exc}")
        return []


def _normalize_role(title: str) -> str:
    """Map Congress.gov role titles to our enum values."""
    lower = (title or "").lower()
    if "chair" in lower and "ranking" not in lower:
        return "chair"
    if "ranking" in lower:
        return "ranking_member"
    return "member"
