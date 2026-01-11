"""
BioGuide ID Enrichment Service

Fetches bioguide_id from Congress.gov API for politicians that don't have one.
This enables cross-referencing with official Congress data and other data sources.
"""

import asyncio
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
from supabase import create_client, Client

from app.services.house_etl import JOB_STATUS

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Congress.gov API configuration
CONGRESS_API_URL = "https://api.congress.gov/v3"
CONGRESS_API_KEY = os.environ.get("CONGRESS_API_KEY")


def get_supabase_client() -> Client:
    """Create Supabase client from environment variables."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

    return create_client(url, key)


def normalize_name(name: str) -> str:
    """Normalize a name for matching."""
    if not name:
        return ""
    # Handle "Last, First" format
    if ", " in name:
        parts = name.split(", ", 1)
        name = f"{parts[1]} {parts[0]}"
    # Remove common suffixes/prefixes
    for suffix in [" Jr.", " Jr", " Sr.", " Sr", " III", " II", " IV", "Hon. ", "Sen. ", "Rep. "]:
        name = name.replace(suffix, "")
    return name.lower().strip()


async def fetch_congress_members() -> List[Dict[str, Any]]:
    """Fetch all current Congress members from Congress.gov API."""
    if not CONGRESS_API_KEY:
        logger.error("CONGRESS_API_KEY not set")
        return []

    all_members = []
    offset = 0
    page_size = 250

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            params = {
                "api_key": CONGRESS_API_KEY,
                "format": "json",
                "limit": page_size,
                "offset": offset,
                "currentMember": "true"
            }

            try:
                response = await client.get(f"{CONGRESS_API_URL}/member", params=params)

                if response.status_code != 200:
                    logger.error(f"Congress.gov API error: {response.status_code}")
                    break

                data = response.json()
                members = data.get("members", [])

                if not members:
                    break

                for member in members:
                    terms = member.get("terms", {}).get("item", [])
                    current_term = terms[0] if terms else {}

                    all_members.append({
                        "bioguide_id": member.get("bioguideId", ""),
                        "name": member.get("name", ""),
                        "direct_name": member.get("directOrderName", ""),
                        "state": member.get("state", ""),
                        "district": member.get("district"),
                        "party": member.get("partyName", ""),
                        "chamber": current_term.get("chamber", ""),
                    })

                offset += page_size
                total = data.get("pagination", {}).get("count", 0)
                if offset >= total:
                    break

                # Rate limit
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Error fetching Congress members: {e}")
                break

    logger.info(f"Fetched {len(all_members)} Congress members")
    return all_members


def fetch_politicians_without_bioguide(supabase: Client, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Fetch politicians that don't have a bioguide_id."""
    try:
        query = (
            supabase.table("politicians")
            .select("id,full_name,first_name,last_name,party,state_or_country,chamber,role")
            .is_("bioguide_id", "null")
        )

        if limit:
            query = query.limit(limit)
        else:
            query = query.limit(1000)

        response = query.execute()
        return response.data if response.data else []

    except Exception as e:
        logger.error(f"Error fetching politicians: {e}")
        return []


def update_politician_bioguide(supabase: Client, politician_id: str, bioguide_id: str) -> bool:
    """Update a politician's bioguide_id."""
    try:
        response = (
            supabase.table("politicians")
            .update({"bioguide_id": bioguide_id})
            .eq("id", politician_id)
            .execute()
        )
        return True
    except Exception as e:
        logger.error(f"Error updating politician {politician_id}: {e}")
        return False


def match_politicians(
    app_politicians: List[Dict[str, Any]],
    congress_members: List[Dict[str, Any]]
) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """Match app politicians to Congress members by name."""
    # Build lookup tables
    congress_by_name = {}
    congress_by_direct_name = {}

    for member in congress_members:
        norm_name = normalize_name(member["name"])
        norm_direct = normalize_name(member["direct_name"])
        if norm_name:
            congress_by_name[norm_name] = member
        if norm_direct:
            congress_by_direct_name[norm_direct] = member

    matches = []

    for pol in app_politicians:
        full_name = pol.get("full_name", "")
        first_name = pol.get("first_name", "")
        last_name = pol.get("last_name", "")

        # Try different name formats
        names_to_try = [
            normalize_name(full_name),
            normalize_name(f"{first_name} {last_name}"),
            normalize_name(f"{last_name}, {first_name}"),
        ]

        for name in names_to_try:
            if name in congress_by_name:
                matches.append((pol, congress_by_name[name]))
                break
            if name in congress_by_direct_name:
                matches.append((pol, congress_by_direct_name[name]))
                break

    return matches


async def run_bioguide_enrichment(
    job_id: str,
    limit: Optional[int] = None,
) -> None:
    """
    Run the bioguide enrichment job.

    1. Fetch current Congress members from Congress.gov API
    2. Fetch politicians without bioguide_id from Supabase
    3. Match by name
    4. Update bioguide_id in Supabase
    """
    JOB_STATUS[job_id]["status"] = "running"
    JOB_STATUS[job_id]["message"] = "Fetching Congress members..."

    try:
        # Get Supabase client
        try:
            supabase = get_supabase_client()
        except ValueError as e:
            JOB_STATUS[job_id]["status"] = "failed"
            JOB_STATUS[job_id]["message"] = str(e)
            return

        # Step 1: Fetch Congress members
        congress_members = await fetch_congress_members()
        if not congress_members:
            JOB_STATUS[job_id]["status"] = "failed"
            JOB_STATUS[job_id]["message"] = "Failed to fetch Congress members (check CONGRESS_API_KEY)"
            return

        JOB_STATUS[job_id]["message"] = f"Fetched {len(congress_members)} Congress members. Finding politicians to enrich..."

        # Step 2: Fetch politicians without bioguide_id
        politicians = fetch_politicians_without_bioguide(supabase, limit)
        logger.info(f"Found {len(politicians)} politicians without bioguide_id")

        if not politicians:
            JOB_STATUS[job_id]["status"] = "completed"
            JOB_STATUS[job_id]["message"] = "No politicians need enrichment"
            JOB_STATUS[job_id]["completed_at"] = datetime.utcnow().isoformat()
            return

        JOB_STATUS[job_id]["total"] = len(politicians)

        # Step 3: Match politicians
        JOB_STATUS[job_id]["message"] = "Matching politicians to Congress members..."
        matches = match_politicians(politicians, congress_members)
        logger.info(f"Found {len(matches)} matches")

        if not matches:
            JOB_STATUS[job_id]["status"] = "completed"
            JOB_STATUS[job_id]["message"] = f"No matches found for {len(politicians)} politicians"
            JOB_STATUS[job_id]["completed_at"] = datetime.utcnow().isoformat()
            return

        # Step 4: Update bioguide_ids
        JOB_STATUS[job_id]["message"] = f"Updating {len(matches)} politicians..."
        updated = 0
        failed = 0

        for i, (pol, congress) in enumerate(matches):
            JOB_STATUS[job_id]["progress"] = i + 1

            if update_politician_bioguide(supabase, pol["id"], congress["bioguide_id"]):
                updated += 1
                logger.info(f"Updated {pol['full_name']} -> {congress['bioguide_id']}")
            else:
                failed += 1

        # Complete
        JOB_STATUS[job_id]["status"] = "completed"
        JOB_STATUS[job_id]["completed_at"] = datetime.utcnow().isoformat()
        JOB_STATUS[job_id]["message"] = (
            f"Enrichment complete: {updated} updated, {failed} failed, "
            f"{len(politicians) - len(matches)} unmatched"
        )

        logger.info(
            f"[BioguideEnrichment] Complete: {updated} updated, {failed} failed, "
            f"{len(politicians) - len(matches)} unmatched"
        )

    except Exception as e:
        logger.exception(f"[BioguideEnrichment] Failed: {e}")
        JOB_STATUS[job_id]["status"] = "failed"
        JOB_STATUS[job_id]["message"] = str(e)
        JOB_STATUS[job_id]["completed_at"] = datetime.utcnow().isoformat()
