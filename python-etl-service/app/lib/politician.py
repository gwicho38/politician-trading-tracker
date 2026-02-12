"""
Politician management utilities.

Consolidated from house_etl.py and senate_etl.py
"""

import logging
from typing import Any, Dict, Optional

from supabase import Client

logger = logging.getLogger(__name__)


def find_or_create_politician(
    supabase: Client,
    name: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    chamber: str = "house",
    state: Optional[str] = None,
    district: Optional[str] = None,
    bioguide_id: Optional[str] = None,
    disclosure: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Find existing politician or create a new one.

    This function handles both House and Senate politicians with a unified interface.
    You can pass either:
    - A `disclosure` dict with politician info (for backward compatibility)
    - Individual parameters (name, first_name, last_name, etc.)

    Lookup priority:
    1. bioguide_id (if provided) - Most reliable identifier
    2. first_name + last_name + role (for House)
    3. Fuzzy name match (for Senate or when first/last not available)

    Args:
        supabase: Supabase client instance
        name: Full name of the politician (used for Senate)
        first_name: First name (used for House)
        last_name: Last name (used for House)
        chamber: "house" or "senate"
        state: State abbreviation (e.g., "CA")
        district: District identifier (e.g., "CA12")
        bioguide_id: Official Congress bioguide ID (e.g., "A000123")
        disclosure: Dict with politician info (legacy support for House ETL)

    Returns:
        Politician UUID if found or created, None on error
    """
    # Handle legacy disclosure dict format (from house_etl)
    if disclosure:
        first_name = disclosure.get("first_name", "").strip()
        last_name = disclosure.get("last_name", "").strip()
        name = disclosure.get("politician_name", f"{first_name} {last_name}").strip()
        state_district = disclosure.get("state_district", "")
        state = state_district[:2] if len(state_district) >= 2 else None
        district = state_district
        chamber = "house"
        # Check if disclosure has bioguide_id
        if not bioguide_id:
            bioguide_id = disclosure.get("bioguide_id")

    # Build full name if not provided
    if not name and (first_name or last_name):
        name = f"{first_name or ''} {last_name or ''}".strip()

    if not name or name == "Unknown":
        return None

    # Clean the name - remove common prefixes
    clean_name = name.strip()
    for prefix in ["Sen.", "Senator", "Hon.", "Honorable", "Rep.", "Representative"]:
        clean_name = clean_name.replace(prefix, "").strip()

    # Determine role based on chamber
    chamber_role_map = {
        "senate": "Senator",
        "house": "Representative",
        "eu_parliament": "MEP",
        "california": "State Legislator",
    }
    role = chamber_role_map.get(chamber, "Representative")

    # Priority 1: Try to find by bioguide_id (most reliable)
    if bioguide_id:
        try:
            response = (
                supabase.table("politicians")
                .select("id")
                .eq("bioguide_id", bioguide_id)
                .limit(1)
                .execute()
            )
            if response.data and len(response.data) > 0:
                logger.debug(f"Found existing politician by bioguide_id: {bioguide_id}")
                return response.data[0]["id"]
        except Exception as e:
            logger.debug(f"Error finding politician by bioguide_id: {e}")

    # Priority 2: Try to find by name
    try:
        if first_name and last_name and chamber == "house":
            # House: match on first_name, last_name, and role
            response = (
                supabase.table("politicians")
                .select("id")
                .match({"first_name": first_name, "last_name": last_name, "role": role})
                .execute()
            )
        else:
            # Senate or name-only: fuzzy match on name
            response = (
                supabase.table("politicians")
                .select("id")
                .ilike("name", f"%{clean_name}%")
                .limit(1)
                .execute()
            )

        if response.data and len(response.data) > 0:
            logger.debug(f"Found existing politician: {name}")
            return response.data[0]["id"]

    except Exception as e:
        logger.debug(f"Error finding politician: {e}")

    # Create new politician
    try:
        # Split name into first and last if not provided
        if not first_name or not last_name:
            name_parts = clean_name.split()
            first_name = name_parts[0] if name_parts else clean_name
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        politician_data = {
            "name": clean_name,
            "full_name": clean_name,
            "first_name": first_name,
            "last_name": last_name,
            "chamber": chamber,
            "role": role,
            "party": None,
            "state": state,
        }

        # Add bioguide_id if provided
        if bioguide_id:
            politician_data["bioguide_id"] = bioguide_id

        # Add House-specific fields
        if chamber == "house" and district:
            politician_data["state_or_country"] = state
            politician_data["district"] = district

        response = supabase.table("politicians").insert(politician_data).execute()

        if response.data and len(response.data) > 0:
            logger.info(f"Created new politician: {clean_name} ({role})" +
                       (f" [bioguide: {bioguide_id}]" if bioguide_id else ""))
            return response.data[0]["id"]

    except Exception as e:
        logger.error(f"Error creating politician {name}: {e}")

    return None
