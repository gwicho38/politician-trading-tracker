"""
EU Parliament Financial Declarations ETL Service

Fetches MEP (Member of European Parliament) financial interest declarations
and uploads them to the trading_disclosures table.

EU declarations are NOT individual stock trades. They are periodic
Declaration of Private Interests (DPI) forms with sections covering:
  A - Previous occupations (3yr before office)
  B - Remunerated outside activities (>5k EUR/yr)
  C - Board memberships & outside activities
  D - Shareholdings & financial interests
  E - Third-party financial support
  F - Other private interests

We map these as "holding" or "income" transaction types.

Pipeline:
  1. Fetch MEP list from XML endpoint
  2. Upsert MEPs to politicians table (chamber="eu_parliament")
  3. For each MEP, scrape declarations page for DPI PDF URLs
  4. Download + parse PDFs with pdfplumber
  5. Extract financial interests from sections B, C, D
  6. Map to trading_disclosures schema and upload
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.lib.base_etl import BaseETLService, ETLResult
from app.lib.database import get_supabase
from app.lib.pdf_utils import extract_text_from_pdf
from app.lib.politician import find_or_create_politician
from app.lib.registry import ETLRegistry
from app.services.eu_parliament_client import EUParliamentClient

logger = logging.getLogger(__name__)

# Section header patterns in DPI PDFs
# Real PDF format uses "(A) " parenthesized letters; also handle "A. " period format
SECTION_PATTERN = re.compile(
    r"^\(?([A-G])\)?[.\s]+[-–—\"']*\s*(.+?)$",
    re.MULTILINE,
)

# Map DPI sections to asset types
SECTION_ASSET_TYPES: Dict[str, str] = {
    "A": "Previous Occupation",
    "B": "Outside Employment",
    "C": "Board Membership",
    "D": "Shareholding",
    "E": "Third-Party Support",
    "F": "Other Interest",
}

# Sections we extract financial interests from
EXTRACTABLE_SECTIONS = {"B", "C", "D"}

# Lines to skip during extraction
SKIP_PATTERNS = [
    re.compile(r"^\s*$"),
    re.compile(r"^page\s+\d+", re.IGNORECASE),
    re.compile(r"^declaration\s+of\s+", re.IGNORECASE),
    re.compile(r"^private\s+interests", re.IGNORECASE),
    re.compile(r"^member\s+of\s+the\s+european", re.IGNORECASE),
    re.compile(r"^signature", re.IGNORECASE),
    re.compile(r"^date\s*:", re.IGNORECASE),
    re.compile(r"^name\s*:", re.IGNORECASE),
    re.compile(r"^none\b", re.IGNORECASE),
    re.compile(r"^n/?a\s*\.?\s*$", re.IGNORECASE),
    re.compile(r"^not\s+applicable", re.IGNORECASE),
    re.compile(r"^-+\s*$"),
    # DPI PDF boilerplate: section description text and column headers
    re.compile(r"pursuant\s+to\s+article", re.IGNORECASE),
    re.compile(r"code\s+of\s+conduct", re.IGNORECASE),
    re.compile(r"generated\s+income", re.IGNORECASE),
    re.compile(r"^income\s+amount", re.IGNORECASE),
    re.compile(r"^nature\s+of\s+the\b", re.IGNORECASE),
    re.compile(r"^periodicity\s*$", re.IGNORECASE),
    re.compile(r"benefit\s+\(if\s+it", re.IGNORECASE),
    re.compile(r"generate\s+income\)", re.IGNORECASE),
    re.compile(r"field\s+and\s+nature\s+of\s+the\s+activity", re.IGNORECASE),
    re.compile(r"^occupation\s+or\s+membership", re.IGNORECASE),
    re.compile(r"^membership\s+or\s+activity", re.IGNORECASE),
    re.compile(r"^holding\s+or\s+partnership", re.IGNORECASE),
    re.compile(r"policy\s+implications", re.IGNORECASE),
    re.compile(r"significant\s+influence", re.IGNORECASE),
    re.compile(r"remunerated\s+activity", re.IGNORECASE),
    re.compile(r"governmental\s+organisations", re.IGNORECASE),
    re.compile(r"associations\s+or\s+other\s+bodies", re.IGNORECASE),
    re.compile(r"outside\s+activit", re.IGNORECASE),
    re.compile(r"exceeds\s+eur\s+5", re.IGNORECASE),
    re.compile(r"financial\s+or\s+in\s+terms\s+of", re.IGNORECASE),
    re.compile(r"political\s+activities\s+by\s+third", re.IGNORECASE),
    re.compile(r"identity\s+of\s+the\s+third\s+party", re.IGNORECASE),
    re.compile(r"unofficial\s+grouping", re.IGNORECASE),
    re.compile(r"^\(\*?\)\s*$"),
    re.compile(r"^EN\s*$"),
    re.compile(r"^with\s+the\s+parliament", re.IGNORECASE),
    re.compile(r"boards\s+or\s+committees\s+of\s+companies", re.IGNORECASE),
    re.compile(r"previous\s+mandate\s+as\s+mep", re.IGNORECASE),
    re.compile(r"specification\s+of\s+the\s+income", re.IGNORECASE),
    re.compile(r"calendar\s+year", re.IGNORECASE),
    re.compile(r"^including\s+the\s+name", re.IGNORECASE),
    re.compile(r"total\s+remuneration\s+of\s+all", re.IGNORECASE),
    re.compile(r"influence\s+over\s+the\s+affairs", re.IGNORECASE),
    re.compile(r"direct\s+or\s+indirect\s+private", re.IGNORECASE),
    re.compile(r"^to\s+above\s*:?\s*$", re.IGNORECASE),
    re.compile(r"additional\s+information\s+i\s+wish", re.IGNORECASE),
    re.compile(r"^holding\s+which\s+gives", re.IGNORECASE),
    re.compile(r"^with\s+potential\s+public", re.IGNORECASE),
]

# Batch size for MEP processing
MEP_BATCH_SIZE = 50


@ETLRegistry.register
class EUParliamentETLService(BaseETLService):
    """
    EU Parliament financial declarations ETL service.

    Fetches MEP DPI (Declaration of Private Interests) PDFs,
    parses financial interest sections, and uploads to the
    trading_disclosures table.
    """

    source_id = "eu_parliament"
    source_name = "EU Parliament Declarations"

    async def fetch_disclosures(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch EU Parliament financial interest declarations.

        Kwargs:
            limit_meps: Max number of MEPs to process (for testing)
            include_former: Include outgoing/former MEPs for historical data (default: True)
            year_start: Earliest year to include declarations from (default: 2015)

        Returns:
            List of parsed financial interest records ready for upload.
        """
        limit_meps = kwargs.get("limit_meps") or kwargs.get("limit")
        include_former = kwargs.get("include_former", True)
        year_start = kwargs.get("year_start", 2015)
        all_records: List[Dict[str, Any]] = []

        supabase = get_supabase()
        if not supabase:
            self.logger.error("Supabase client not available")
            return []

        async with EUParliamentClient() as client:
            # Step 1: Fetch MEP list
            self.logger.info("Fetching MEP list from EU Parliament XML...")
            meps = await client.fetch_mep_list()
            if not meps:
                self.logger.warning("No MEPs fetched from XML endpoint")
                return []

            self.logger.info(f"Found {len(meps)} current MEPs")

            # Optionally fetch former MEPs for historical backfill (2015+)
            if include_former:
                self.logger.info("Fetching outgoing/former MEPs for historical data...")
                former_meps = await client.fetch_outgoing_meps()
                if former_meps:
                    # Deduplicate by mep_id (some may have re-entered)
                    existing_ids = {m["mep_id"] for m in meps}
                    new_former = [m for m in former_meps if m["mep_id"] not in existing_ids]
                    meps.extend(new_former)
                    self.logger.info(
                        f"Added {len(new_former)} former MEPs "
                        f"(total: {len(meps)})"
                    )

            if limit_meps:
                meps = meps[:limit_meps]
                self.logger.info(f"Limited to {limit_meps} MEPs for processing")

            # Step 2: Upsert MEPs and fetch their declarations
            politician_cache: Dict[str, str] = {}

            for i, mep in enumerate(meps):
                mep_id = mep["mep_id"]
                full_name = mep["full_name"]

                self.logger.info(
                    f"Processing MEP {i + 1}/{len(meps)}: {full_name}"
                )

                # Upsert politician
                first_name, last_name = _split_mep_name(full_name)
                politician_id = find_or_create_politician(
                    supabase,
                    name=full_name,
                    first_name=first_name,
                    last_name=last_name,
                    chamber="eu_parliament",
                    state=mep.get("country"),
                    party=mep.get("political_group") or None,
                )

                if not politician_id:
                    self.logger.warning(f"Failed to upsert MEP: {full_name}")
                    continue

                politician_cache[mep_id] = politician_id

                # Step 3: Fetch declarations page
                declarations = await client.fetch_declarations_page(
                    mep_id, full_name
                )

                if not declarations:
                    self.logger.info(f"No declarations found for MEP {full_name}")
                    continue

                self.logger.info(
                    f"Found {len(declarations)} declarations for {full_name}"
                )

                # Step 4: Download and parse each DPI PDF
                for decl in declarations:
                    # Skip declarations before the start year
                    decl_date = decl.get("date", "")
                    if decl_date and year_start:
                        try:
                            decl_year = int(decl_date[:4])
                            if decl_year < year_start:
                                self.logger.info(
                                    f"Skipping {decl_date} declaration (before {year_start})"
                                )
                                continue
                        except (ValueError, IndexError):
                            pass  # Can't parse year, include it

                    pdf_url = decl["pdf_url"]
                    self.logger.info(f"Downloading PDF: {pdf_url}")
                    pdf_bytes = await client.download_pdf(pdf_url)
                    if not pdf_bytes:
                        self.logger.warning(f"Failed to download PDF: {pdf_url}")
                        continue

                    # Parse PDF text
                    text = extract_text_from_pdf(pdf_bytes)
                    if not text:
                        self.logger.warning(
                            f"No text extracted from PDF: {pdf_url}"
                        )
                        continue

                    # Extract financial interests
                    interests = extract_financial_interests(text)
                    self.logger.info(
                        f"Extracted {len(interests)} interests from {pdf_url}"
                    )

                    declaration_date = decl.get("date") or datetime.now(
                        timezone.utc
                    ).strftime("%Y-%m-%d")

                    for interest in interests:
                        record = {
                            "politician_name": full_name,
                            "first_name": first_name,
                            "last_name": last_name,
                            "politician_id": politician_id,
                            "chamber": "eu_parliament",
                            "state": mep.get("country"),
                            "asset_name": interest["entity"][:200],
                            "asset_type": interest["asset_type"],
                            "transaction_type": interest["transaction_type"],
                            "transaction_date": declaration_date,
                            "filing_date": declaration_date,
                            "notification_date": declaration_date,
                            "value_low": interest.get("value_low"),
                            "value_high": interest.get("value_high"),
                            "source": "eu_parliament",
                            "source_url": pdf_url,
                            "doc_id": f"DPI-{mep_id}-{declaration_date}",
                            "raw_row": interest.get("raw_lines", []),
                            "section": interest["section"],
                        }
                        all_records.append(record)

        self.logger.info(
            f"Extracted {len(all_records)} financial interest records "
            f"from {len(meps)} MEPs"
        )
        return all_records

    async def parse_disclosure(
        self, raw: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Map a raw EU financial interest record to the standard schema.

        The record is already mostly in the right shape from
        fetch_disclosures(); this method normalizes it for
        upload_disclosure().
        """
        asset_name = raw.get("asset_name", "")
        if not asset_name or len(asset_name.strip()) < 2:
            return None

        return {
            "politician_name": raw.get("politician_name"),
            "first_name": raw.get("first_name"),
            "last_name": raw.get("last_name"),
            "chamber": "eu_parliament",
            "state": raw.get("state"),
            "asset_name": asset_name,
            "asset_type": raw.get("asset_type", "Other Interest"),
            "transaction_type": raw.get("transaction_type", "holding"),
            "transaction_date": raw.get("transaction_date"),
            "filing_date": raw.get("filing_date"),
            "notification_date": raw.get("notification_date"),
            "value_low": raw.get("value_low"),
            "value_high": raw.get("value_high"),
            "source_url": raw.get("source_url"),
            "doc_id": raw.get("doc_id"),
            "source": "eu_parliament",
            "raw_row": raw.get("raw_row", []),
        }


# ---------------------------------------------------------------------------
# PDF parsing helpers
# ---------------------------------------------------------------------------


def split_sections(text: str) -> Dict[str, str]:
    """
    Split DPI PDF text into sections A-F.

    Returns a dict mapping section letter to section body text.
    """
    sections: Dict[str, str] = {}

    # Find all section headers
    matches = list(SECTION_PATTERN.finditer(text))

    if not matches:
        return sections

    for i, match in enumerate(matches):
        letter = match.group(1).upper()
        # First match for each section wins (avoids spurious footer matches)
        if letter in sections:
            continue
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections[letter] = body

    return sections


def extract_financial_interests(text: str) -> List[Dict[str, Any]]:
    """
    Extract financial interest entries from DPI PDF text.

    Focuses on sections B (outside employment), C (board memberships),
    and D (shareholdings).

    Returns:
        List of dicts with keys: entity, section, asset_type,
        transaction_type, value_low, value_high, raw_lines
    """
    sections = split_sections(text)
    interests: List[Dict[str, Any]] = []

    for section_letter in EXTRACTABLE_SECTIONS:
        body = sections.get(section_letter)
        if not body:
            continue

        asset_type = SECTION_ASSET_TYPES.get(section_letter, "Other Interest")
        transaction_type = "income" if section_letter == "B" else "holding"

        entries = _parse_section_entries(body, section_letter)

        for entry in entries:
            value_low, value_high = _extract_income_range(entry["text"])

            interests.append(
                {
                    "entity": entry["entity"],
                    "section": section_letter,
                    "asset_type": asset_type,
                    "transaction_type": transaction_type,
                    "value_low": value_low,
                    "value_high": value_high,
                    "raw_lines": entry["raw_lines"],
                }
            )

    return interests


def _parse_section_entries(
    body: str, section: str
) -> List[Dict[str, Any]]:
    """
    Parse individual entries from a section body.

    Entries are typically separated by:
    - Numbered items (1., 2., etc.)
    - Dash/bullet separators
    - Double newlines (paragraph breaks)

    Returns list of dicts with entity name and raw lines.
    """
    entries: List[Dict[str, Any]] = []
    lines = body.split("\n")

    # Filter out skip-pattern lines
    meaningful_lines: List[str] = []
    for line in lines:
        stripped = line.strip()
        if any(p.search(stripped) for p in SKIP_PATTERNS):
            continue
        if stripped:
            meaningful_lines.append(stripped)

    if not meaningful_lines:
        return entries

    # Try numbered item splitting first
    numbered_pattern = re.compile(r"^(\d+)\.\s+(.+)")
    current_entry_lines: List[str] = []
    current_entity: Optional[str] = None
    found_numbered = False

    for line in meaningful_lines:
        num_match = numbered_pattern.match(line)
        if num_match:
            found_numbered = True
            # Save previous entry (only if it was also a numbered item)
            if current_entity and found_numbered:
                entries.append(
                    {
                        "entity": current_entity,
                        "text": " ".join(current_entry_lines),
                        "raw_lines": current_entry_lines.copy(),
                    }
                )
            current_entity = num_match.group(2).strip()
            current_entry_lines = [line]
        elif current_entity and found_numbered:
            # Continuation line after a numbered item
            current_entry_lines.append(line)
            if len(current_entry_lines) == 2:
                current_entity = f"{current_entity} - {line}"
        # Lines before first numbered item are description text — skip them

    # Don't forget the last entry
    if current_entity and found_numbered:
        entries.append(
            {
                "entity": current_entity,
                "text": " ".join(current_entry_lines),
                "raw_lines": current_entry_lines.copy(),
            }
        )

    # If no numbered items were found, try treating meaningful lines
    # as individual entries (for sections without numbered lists)
    if not entries and meaningful_lines:
        # Only include lines that look like actual entity names (short, no colons)
        for line in meaningful_lines:
            if len(line) < 150 and ":" not in line:
                entries.append(
                    {
                        "entity": line[:200],
                        "text": line,
                        "raw_lines": [line],
                    }
        )

    return entries


def _extract_income_range(text: str) -> tuple:
    """
    Try to extract income category from EU DPI text.

    EU income categories for Section B:
    - Category 1: EUR 1 - EUR 499
    - Category 2: EUR 500 - EUR 999
    - Category 3: EUR 1,000 - EUR 4,999
    - Category 4: EUR 5,000 - EUR 9,999
    - Category 5: EUR 10,000 or more

    Returns:
        (value_low, value_high) or (None, None)
    """
    text_lower = text.lower()

    # Direct EUR range patterns
    eur_range = re.search(
        r"(?:eur|€)\s*([\d,.]+)\s*[-–—to]+\s*(?:eur|€)?\s*([\d,.]+)",
        text_lower,
    )
    if eur_range:
        try:
            low = float(eur_range.group(1).replace(",", "").replace(".", ""))
            high = float(eur_range.group(2).replace(",", "").replace(".", ""))
            return (low, high)
        except ValueError:
            pass

    # Category-based patterns
    category_ranges = [
        (r"category\s*1\b", 1, 499),
        (r"category\s*2\b", 500, 999),
        (r"category\s*3\b", 1000, 4999),
        (r"category\s*4\b", 5000, 9999),
        (r"category\s*5\b", 10000, None),
    ]
    for pattern, low, high in category_ranges:
        if re.search(pattern, text_lower):
            return (float(low), float(high) if high else None)

    return (None, None)


def _split_mep_name(full_name: str) -> tuple:
    """
    Split an MEP name into first and last name.

    EU Parliament names are typically in 'FirstName LASTNAME' format
    where the last name is in ALL CAPS.

    Examples:
        'Mika AALTOLA' -> ('Mika', 'AALTOLA')
        'María Teresa GIMÉNEZ BARBAT' -> ('María Teresa', 'GIMÉNEZ BARBAT')
        'Bas EICKHOUT' -> ('Bas', 'EICKHOUT')
    """
    if not full_name:
        return ("", "")

    parts = full_name.strip().split()
    if len(parts) <= 1:
        return (full_name, "")

    # Find the boundary where uppercase-only words start
    first_parts: List[str] = []
    last_parts: List[str] = []
    found_upper = False

    for part in parts:
        # A word is considered a "last name part" if it's all uppercase
        # (ignoring accented chars and hyphens)
        clean = re.sub(r"[^a-zA-ZÀ-ÿ]", "", part)
        if clean and clean == clean.upper() and not found_upper and first_parts:
            found_upper = True

        if found_upper:
            last_parts.append(part)
        else:
            first_parts.append(part)

    if not first_parts:
        first_parts = [parts[0]]
        last_parts = parts[1:]
    elif not last_parts:
        last_parts = [first_parts.pop()] if len(first_parts) > 1 else [""]

    return (" ".join(first_parts), " ".join(last_parts))
