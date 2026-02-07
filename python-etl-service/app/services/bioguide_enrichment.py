"""
BioGuide ID Enrichment Service

Fetches bioguide_id from Congress.gov API for politicians that don't have one.
This enables cross-referencing with official Congress data and other data sources.

Enrichment sources (in order of priority):
1. Congress.gov API - Official source, includes historical members
2. QuiverQuant API - Fallback source for politicians not in Congress.gov
"""

import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from supabase import Client
from thefuzz import fuzz

from app.lib.database import get_supabase
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

# QuiverQuant API configuration (fallback source)
QUIVER_API_URL = "https://api.quiverquant.com/beta"
QUIVER_API_KEY = os.environ.get("QUIVER_API_KEY")

# Fuzzy matching configuration
FUZZY_MATCH_THRESHOLD = 85  # Minimum score (0-100) for a name match
FUZZY_MATCH_HIGH_CONFIDENCE = 95  # Score for high-confidence matches


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


async def fetch_congress_members(current_only: bool = False) -> List[Dict[str, Any]]:
    """Fetch Congress members from Congress.gov API.

    Args:
        current_only: If True, only fetch current members. If False, fetch all
                      historical members (slower but more complete).

    Returns:
        List of member dictionaries with bioguide_id, name, party, state, etc.
    """
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
            }
            # Only add currentMember filter if explicitly requested
            if current_only:
                params["currentMember"] = "true"

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


def update_politician_from_congress(
    supabase: Client,
    politician_id: str,
    congress_data: Dict[str, Any],
    current_data: Dict[str, Any]
) -> bool:
    """
    Update a politician with data from Congress.gov.

    Updates bioguide_id and optionally fills in missing:
    - full_name (from direct_name or parsed name)
    - party (D/R/I from partyName)
    - state
    - chamber

    Only overwrites full_name if current name looks like a placeholder.
    """
    try:
        update_data = {"bioguide_id": congress_data["bioguide_id"]}

        # Check if current name is a placeholder
        current_name = current_data.get("full_name", "")
        is_placeholder = any(p in current_name.lower() for p in [
            "placeholder", "member (", "house_member", "senate_member",
            "congress_member", "unknown", "mep ("
        ])

        # Update full_name if placeholder or missing
        if is_placeholder or not current_name:
            # Prefer direct_name (First Last format), fall back to name (Last, First)
            new_name = congress_data.get("direct_name") or congress_data.get("name", "")
            if new_name and new_name != current_name:
                update_data["full_name"] = new_name
                # Also update first/last name
                parts = new_name.split()
                if len(parts) >= 2:
                    update_data["first_name"] = parts[0]
                    update_data["last_name"] = " ".join(parts[1:])

        # Fill in missing party (normalize to D/R/I)
        if not current_data.get("party"):
            party_name = congress_data.get("party", "").lower()
            if "democrat" in party_name:
                update_data["party"] = "D"
            elif "republican" in party_name:
                update_data["party"] = "R"
            elif "independent" in party_name:
                update_data["party"] = "I"

        # Fill in missing state
        if not current_data.get("state") and not current_data.get("state_or_country"):
            state = congress_data.get("state")
            if state:
                update_data["state"] = state
                update_data["state_or_country"] = state

        # Fill in missing chamber
        if not current_data.get("chamber"):
            chamber = congress_data.get("chamber")
            if chamber:
                update_data["chamber"] = chamber

        # Fill in district if available
        district = congress_data.get("district")
        if district and not current_data.get("district"):
            update_data["district"] = str(district)

        response = (
            supabase.table("politicians")
            .update(update_data)
            .eq("id", politician_id)
            .execute()
        )
        return True
    except Exception as e:
        logger.error(f"Error updating politician {politician_id}: {e}")
        return False


def fuzzy_match_name(name1: str, name2: str) -> int:
    """Calculate fuzzy match score between two names.

    Uses token_sort_ratio which handles word order differences well:
    - "Richard W. Allen" vs "Allen, Richard W." -> high score
    - "April McClain Delaney" vs "April Mcclain-Delaney" -> high score

    Returns:
        Score from 0-100, where 100 is a perfect match.
    """
    if not name1 or not name2:
        return 0
    # Normalize both names before comparison
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)
    # token_sort_ratio handles word order and is good for names
    return fuzz.token_sort_ratio(n1, n2)


def match_politicians(
    app_politicians: List[Dict[str, Any]],
    congress_members: List[Dict[str, Any]],
    threshold: int = FUZZY_MATCH_THRESHOLD
) -> List[Tuple[Dict[str, Any], Dict[str, Any], int]]:
    """Match app politicians to Congress members by fuzzy name matching.

    Args:
        app_politicians: Politicians from our database
        congress_members: Members from Congress.gov
        threshold: Minimum fuzzy match score (0-100) to consider a match

    Returns:
        List of tuples: (app_politician, congress_member, match_score)
    """
    # Build list of normalized congress member names for matching
    congress_lookup = []
    for member in congress_members:
        congress_lookup.append({
            "member": member,
            "names": [
                normalize_name(member.get("name", "")),
                normalize_name(member.get("direct_name", "")),
            ]
        })

    matches = []
    matched_bioguides = set()  # Prevent duplicate matches

    for pol in app_politicians:
        full_name = pol.get("full_name", "")
        first_name = pol.get("first_name", "")
        last_name = pol.get("last_name", "")

        # Names to try matching against
        names_to_try = [
            full_name,
            f"{first_name} {last_name}",
            f"{last_name}, {first_name}",
        ]

        best_match = None
        best_score = 0

        for congress_entry in congress_lookup:
            member = congress_entry["member"]
            bioguide = member.get("bioguide_id", "")

            # Skip if already matched to another politician
            if bioguide in matched_bioguides:
                continue

            for pol_name in names_to_try:
                for congress_name in congress_entry["names"]:
                    if not pol_name or not congress_name:
                        continue

                    score = fuzzy_match_name(pol_name, congress_name)
                    if score > best_score and score >= threshold:
                        best_score = score
                        best_match = member

        if best_match:
            matches.append((pol, best_match, best_score))
            matched_bioguides.add(best_match.get("bioguide_id", ""))
            logger.debug(
                f"Matched '{full_name}' -> '{best_match.get('direct_name')}' "
                f"(score: {best_score}, bioguide: {best_match.get('bioguide_id')})"
            )

    return matches


async def fetch_quiver_members() -> List[Dict[str, Any]]:
    """Fetch Congress members from QuiverQuant API (fallback source).

    QuiverQuant tracks congressional trading and has bioguide_ids for
    politicians they've recorded trades for, including former members.

    Returns:
        List of member dictionaries with bioguide_id and name.
    """
    if not QUIVER_API_KEY:
        logger.warning("QUIVER_API_KEY not set - skipping QuiverQuant fallback")
        return []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Fetch recent trades to extract unique politicians
            headers = {"Authorization": f"Bearer {QUIVER_API_KEY}"}
            response = await client.get(
                f"{QUIVER_API_URL}/bulk/congresstrading",
                headers=headers,
            )

            if response.status_code != 200:
                logger.error(f"QuiverQuant API error: {response.status_code}")
                return []

            data = response.json()

            # Extract unique politicians with bioguide_ids
            seen_bioguides = set()
            members = []

            for trade in data:
                bioguide = trade.get("BioGuideID")
                name = trade.get("Representative")

                if bioguide and bioguide not in seen_bioguides:
                    seen_bioguides.add(bioguide)
                    members.append({
                        "bioguide_id": bioguide,
                        "name": name,
                        "direct_name": name,  # QuiverQuant uses "First Last" format
                        "party": trade.get("Party"),
                        "chamber": "House of Representatives" if trade.get("House") == "Representatives" else "Senate",
                    })

            logger.info(f"Fetched {len(members)} unique politicians from QuiverQuant")
            return members

    except Exception as e:
        logger.error(f"Error fetching QuiverQuant members: {e}")
        return []


async def run_bioguide_enrichment(
    job_id: str,
    limit: Optional[int] = None,
) -> None:
    """
    Run the bioguide enrichment job.

    Sources (in order of priority):
    1. Congress.gov API - Official source, includes all historical members
    2. QuiverQuant API - Fallback for politicians not in Congress.gov

    Process:
    1. Fetch all Congress members from Congress.gov API
    2. Fetch politicians without bioguide_id from Supabase
    3. Fuzzy match by name with confidence scoring
    4. Update bioguide_id in Supabase
    5. For unmatched, try QuiverQuant as fallback
    """
    JOB_STATUS[job_id]["status"] = "running"
    JOB_STATUS[job_id]["message"] = "Fetching Congress members (including historical)..."

    try:
        # Get Supabase client
        try:
            supabase = get_supabase()
        except ValueError as e:
            JOB_STATUS[job_id]["status"] = "failed"
            JOB_STATUS[job_id]["message"] = str(e)
            return

        # Step 1: Fetch Congress members (all, not just current)
        congress_members = await fetch_congress_members(current_only=False)
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
            JOB_STATUS[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
            return

        JOB_STATUS[job_id]["total"] = len(politicians)

        # Step 3: Fuzzy match politicians to Congress members
        JOB_STATUS[job_id]["message"] = "Fuzzy matching politicians to Congress members..."
        matches = match_politicians(politicians, congress_members)
        logger.info(f"Found {len(matches)} matches from Congress.gov")

        # Step 4: Update politicians with Congress.gov data
        updated = 0
        failed = 0
        high_confidence = 0
        matched_pol_ids = set()

        if matches:
            JOB_STATUS[job_id]["message"] = f"Updating {len(matches)} politicians with Congress.gov data..."

            for i, (pol, congress, score) in enumerate(matches):
                JOB_STATUS[job_id]["progress"] = i + 1
                matched_pol_ids.add(pol["id"])

                if score >= FUZZY_MATCH_HIGH_CONFIDENCE:
                    high_confidence += 1

                if update_politician_from_congress(supabase, pol["id"], congress, pol):
                    updated += 1
                    # Log what was updated
                    updates = [f"bioguide={congress['bioguide_id']}", f"score={score}"]
                    if any(p in pol.get("full_name", "").lower() for p in ["placeholder", "member ("]):
                        updates.append(f"name={congress.get('direct_name', congress.get('name', ''))}")
                    if not pol.get("party"):
                        updates.append(f"party={congress.get('party', '')}")
                    logger.info(f"Updated {pol['full_name']} -> {', '.join(updates)}")
                else:
                    failed += 1

        # Step 5: QuiverQuant fallback for unmatched politicians
        unmatched_politicians = [p for p in politicians if p["id"] not in matched_pol_ids]
        quiver_updated = 0

        if unmatched_politicians:
            JOB_STATUS[job_id]["message"] = f"Trying QuiverQuant fallback for {len(unmatched_politicians)} unmatched..."

            quiver_members = await fetch_quiver_members()
            if quiver_members:
                quiver_matches = match_politicians(unmatched_politicians, quiver_members)
                logger.info(f"Found {len(quiver_matches)} matches from QuiverQuant")

                for pol, quiver, score in quiver_matches:
                    if update_politician_from_congress(supabase, pol["id"], quiver, pol):
                        quiver_updated += 1
                        logger.info(
                            f"[QuiverQuant] Updated {pol['full_name']} -> "
                            f"bioguide={quiver['bioguide_id']}, score={score}"
                        )
                    else:
                        failed += 1

        # Complete
        total_updated = updated + quiver_updated
        final_unmatched = len(politicians) - len(matches) - quiver_updated
        JOB_STATUS[job_id]["status"] = "completed"
        JOB_STATUS[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
        JOB_STATUS[job_id]["message"] = (
            f"Enrichment complete: {total_updated} updated "
            f"({updated} Congress.gov, {quiver_updated} QuiverQuant), "
            f"{failed} failed, {final_unmatched} unmatched, "
            f"{high_confidence} high-confidence matches"
        )

        logger.info(
            f"[BioguideEnrichment] Complete: {total_updated} updated "
            f"({updated} Congress.gov, {quiver_updated} QuiverQuant), "
            f"{failed} failed, {final_unmatched} unmatched"
        )

    except Exception as e:
        logger.exception(f"[BioguideEnrichment] Failed: {e}")
        JOB_STATUS[job_id]["status"] = "failed"
        JOB_STATUS[job_id]["message"] = str(e)
        JOB_STATUS[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
