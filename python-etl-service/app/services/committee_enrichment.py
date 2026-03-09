"""
Committee enrichment service.

Fetches committee assignments from Congress.gov API for all politicians
that have a bioguide_id, then upserts into politician_committees table
with GICS sector mappings from committee_sector_map.

Congress.gov API endpoint:
  GET https://api.congress.gov/v3/member/{bioguideId}/committee-assignments
  ?format=json
  Header: X-Api-Key: {CONGRESS_API_KEY}
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

BATCH_SIZE = 500


def get_supabase() -> Client:
    global _supabase_client
    if _supabase_client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        _supabase_client = create_client(url, key)
    return _supabase_client


async def run_committee_enrichment_async(
    limit: Optional[int] = None, job_id: Optional[str] = None
) -> dict:
    """Async version — await this from async contexts (FastAPI, bioguide enrichment, etc.)."""
    return await _run_committee_enrichment_impl(limit, job_id)


def run_committee_enrichment(
    limit: Optional[int] = None, job_id: Optional[str] = None
) -> dict:
    """Sync wrapper — only use from non-async contexts (scripts, tests).

    Raises RuntimeError if called from inside a running event loop.
    In that case, use 'await run_committee_enrichment_async()' instead.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        raise RuntimeError(
            "run_committee_enrichment() called from async context. "
            "Use 'await run_committee_enrichment_async()' instead."
        )
    return asyncio.run(_run_committee_enrichment_impl(limit, job_id))


async def _run_committee_enrichment_impl(
    limit: Optional[int], job_id: Optional[str]
) -> dict:
    """Core implementation — accumulates all records then batch-upserts."""
    # Import JOB_STATUS lazily to avoid circular imports
    job_status = None
    if job_id:
        try:
            from app.services.house_etl import JOB_STATUS
            job_status = JOB_STATUS
            job_status[job_id]["status"] = "running"
            job_status[job_id]["message"] = "Fetching politicians with bioguide_id..."
        except Exception:
            pass

    supabase = get_supabase()
    results = {"processed": 0, "updated": 0, "skipped": 0, "failed": 0}

    try:
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

        if job_status and job_id:
            job_status[job_id]["total"] = len(politicians)
            job_status[job_id]["message"] = f"Processing {len(politicians)} politicians..."

        # Load sector map from DB
        sector_map_resp = supabase.table("committee_sector_map").select("*").execute()
        sector_map = {
            row["committee_code"]: row["gics_sectors"]
            for row in (sector_map_resp.data or [])
        }

        # Accumulate all records across all politicians for a single batched upsert
        all_records = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for i, politician in enumerate(politicians):
                try:
                    bio_id = politician["bioguide_id"]
                    pol_id = politician["id"]

                    committees = await _fetch_committees(client, bio_id)
                    results["processed"] += 1

                    if not committees:
                        results["skipped"] += 1
                        continue

                    for c in committees:
                        code = c.get("systemCode", "")
                        name = c.get("name", "")
                        role = _normalize_role(c.get("title", ""))
                        congress = c.get("congress")
                        gics = sector_map.get(code.upper(), [])

                        all_records.append({
                            "politician_id": pol_id,
                            "committee_name": name,
                            "committee_code": code.upper() if code else None,
                            "gics_sectors": gics,
                            "role": role,
                            "is_leadership": role in ("chair", "ranking_member"),
                            # Fix 2: congress_number is NOT NULL — use 0 as sentinel for unknown
                            "congress_number": congress if congress is not None else 0,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        })

                    results["updated"] += 1

                    if job_status and job_id:
                        job_status[job_id]["progress"] = i + 1

                except Exception as exc:
                    logger.warning(
                        f"[CommitteeEnrichment] Failed for {politician.get('full_name')}: {exc}"
                    )
                    results["failed"] += 1

        # Fix 5: Batch upsert all records in chunks of BATCH_SIZE
        if all_records:
            for i in range(0, len(all_records), BATCH_SIZE):
                batch = all_records[i : i + BATCH_SIZE]
                supabase.table("politician_committees").upsert(
                    batch,
                    on_conflict="politician_id,committee_name,congress_number",
                ).execute()
            logger.info(
                f"[CommitteeEnrichment] Upserted {len(all_records)} records in "
                f"{(len(all_records) + BATCH_SIZE - 1) // BATCH_SIZE} batches"
            )

        logger.info(f"[CommitteeEnrichment] Done: {results}")

        if job_status and job_id:
            job_status[job_id]["status"] = "completed"
            job_status[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
            job_status[job_id]["message"] = (
                f"Completed: {results['updated']} politicians updated, "
                f"{results['skipped']} skipped, {results['failed']} failed, "
                f"{len(all_records)} committee records upserted"
            )

        return results

    except Exception as exc:
        logger.exception(f"[CommitteeEnrichment] Fatal error: {exc}")
        if job_status and job_id:
            job_status[job_id]["status"] = "failed"
            job_status[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
            job_status[job_id]["message"] = f"Failed: {exc}"
        raise


async def _fetch_committees(client: httpx.AsyncClient, bioguide_id: str) -> list[dict]:
    """Fetch committee assignments from Congress.gov API."""
    if not CONGRESS_API_KEY:
        logger.warning("[CommitteeEnrichment] CONGRESS_API_KEY not set — skipping API call")
        return []

    url = f"{CONGRESS_API_BASE}/member/{bioguide_id}/committee-assignments"
    # Fix 3: pass API key as a header, not a query param
    params = {"format": "json", "limit": 250}
    headers = {"X-Api-Key": CONGRESS_API_KEY}

    try:
        resp = await client.get(url, params=params, headers=headers)
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
