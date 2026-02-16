"""
Party Registry — auto-creates parties in the `parties` table.

When the ETL encounters a party code not yet in the database,
this module creates it with a generated hex color (hash-based).
"""

import hashlib
import logging
import re
from typing import Optional, Set

from supabase import Client

logger = logging.getLogger(__name__)

# In-memory cache to avoid repeated DB lookups within the same ETL run
_known_parties: Set[str] = set()

# Known EU group abbreviations (moved from eu_parliament_client.py)
_EU_GROUP_ABBREVIATIONS = {
    "european people's party": "EPP",
    "progressive alliance": "S&D",
    "renew europe": "Renew",
    "greens": "Greens/EFA",
    "european free alliance": "Greens/EFA",
    "conservatives and reformists": "ECR",
    "identity and democracy": "ID",
    "the left group": "GUE/NGL",
    "gue/ngl": "GUE/NGL",
    "non-attached": "NI",
    "patriots for europe": "PfE",
    "europe of sovereign nations": "ESN",
}


def abbreviate_group_name(full_name: Optional[str]) -> str:
    """Convert an EU Parliament group name to its standard abbreviation.

    Checks known patterns first, then generates initials from significant words.
    """
    if not full_name:
        return ""

    lower = full_name.lower().strip()

    # Check known abbreviations
    for pattern, abbrev in _EU_GROUP_ABBREVIATIONS.items():
        if pattern in lower:
            return abbrev

    # Generate initials from significant words (skip articles/prepositions)
    skip_words = {"of", "the", "and", "in", "for", "group", "a", "an"}
    words = re.findall(r"[A-Z][a-z]*|[A-Z]+", full_name)
    if not words:
        words = [w for w in full_name.split() if w.lower() not in skip_words]
    initials = "".join(w[0].upper() for w in words if w.lower() not in skip_words)
    return initials[:20] if initials else full_name[:20]


def generate_party_color(party_name: str) -> str:
    """Generate a hex color for a political party.

    Uses a deterministic hash to produce a visually distinct, saturated color.
    Avoids very dark or very light colors for readability on dark backgrounds.
    """
    h = hashlib.md5(party_name.encode()).hexdigest()
    # Use first 6 hex chars but ensure saturation by mixing channels
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)

    # Boost saturation: push channels apart from the mean
    mean = (r + g + b) // 3
    r = min(255, max(60, r + (r - mean) // 2))
    g = min(255, max(60, g + (g - mean) // 2))
    b = min(255, max(60, b + (b - mean) // 2))

    return f"#{r:02X}{g:02X}{b:02X}"


def ensure_party_exists(
    supabase: Client,
    code: str,
    full_name: Optional[str] = None,
    jurisdiction: str = "US",
) -> str:
    """Ensure a party exists in the parties table. Auto-creates if missing.

    Args:
        supabase: Supabase client
        code: Short party code (e.g., 'D', 'EPP', 'PfE')
        full_name: Full party name (used when creating)
        jurisdiction: 'US' or 'EU'

    Returns:
        The party code (always returns the input code).
    """
    global _known_parties

    if not code:
        return code

    # Check in-memory cache first
    if code in _known_parties:
        return code

    try:
        existing = (
            supabase.table("parties")
            .select("code")
            .eq("code", code)
            .limit(1)
            .execute()
        )
        if existing.data:
            _known_parties.add(code)
            return code
    except Exception as e:
        logger.debug(f"Error checking party {code}: {e}")
        return code

    # Party not found — create it
    name = full_name or code
    short_name = code if len(code) <= 20 else code[:20]
    color = generate_party_color(name)

    try:
        supabase.table("parties").insert({
            "code": code,
            "name": name,
            "short_name": short_name,
            "jurisdiction": jurisdiction,
            "color": color,
        }).execute()
        _known_parties.add(code)
        logger.info(f"Auto-registered party: {code} ({name}) color={color}")
    except Exception as e:
        # Likely a unique constraint race condition — safe to ignore
        logger.debug(f"Error creating party {code}: {e}")
        _known_parties.add(code)

    return code


def reset_cache():
    """Clear the in-memory party cache (useful for testing)."""
    global _known_parties
    _known_parties = set()
