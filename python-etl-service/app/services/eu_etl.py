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

from app.lib.base_etl import BaseETLService, ETLResult, JobStatus
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
EXTRACTABLE_SECTIONS = {"A", "B", "C", "D"}

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
    re.compile(r"^(?:EN|NL|FR|DE|ES|IT|PT|PL|RO|HU|EL|CS|DA|SV|FI|SK|BG|HR|LT|LV|ET|SL|GA|MT)\s*$"),
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
    # Dutch boilerplate
    re.compile(r"overeenkomstig\s+artikel", re.IGNORECASE),
    re.compile(r"gedragscode", re.IGNORECASE),
    re.compile(r"^geen\s*$", re.IGNORECASE),
    re.compile(r"^bedrag\s+inkomsten", re.IGNORECASE),
    re.compile(r"^aard\s+van\s+het", re.IGNORECASE),
    re.compile(r"^periodiciteit\s*$", re.IGNORECASE),
    re.compile(r"gegenereerde\s+inkomsten", re.IGNORECASE),
    re.compile(r"^gebied\s+en\s+aard", re.IGNORECASE),
    re.compile(r"^deelname\s+of\s+werkzaamheid", re.IGNORECASE),
    re.compile(r"^deelname\s+in\s+een", re.IGNORECASE),
    re.compile(r"^deelname\s+met", re.IGNORECASE),
    re.compile(r"^onderneming", re.IGNORECASE),
    re.compile(r"^voordeel\s*\(", re.IGNORECASE),
    re.compile(r"^zie\s+hierboven", re.IGNORECASE),
    # French boilerplate
    re.compile(r"^montant\s+des\s+revenus", re.IGNORECASE),
    re.compile(r"^nature\s+de\s+l", re.IGNORECASE),
    re.compile(r"^périodicité", re.IGNORECASE),
    re.compile(r"^néant\s*$", re.IGNORECASE),
    re.compile(r"^aucun\s*$", re.IGNORECASE),
    re.compile(r"^domaine\s+et\s+nature", re.IGNORECASE),
    re.compile(r"^voir\s+ci-dessus", re.IGNORECASE),
    # German boilerplate
    re.compile(r"^betrag\s+der\s+einkünfte", re.IGNORECASE),
    re.compile(r"^art\s+des\s+vorteils", re.IGNORECASE),
    re.compile(r"^regelmäßigkeit", re.IGNORECASE),
    re.compile(r"^keine\s*$", re.IGNORECASE),
    re.compile(r"^siehe\s+oben", re.IGNORECASE),
    # Slovenian boilerplate
    re.compile(r"^znesek\s+prihodkov", re.IGNORECASE),
    re.compile(r"^narava\s+ugodnosti", re.IGNORECASE),
    re.compile(r"^periodi[čc]nost\s*$", re.IGNORECASE),
    re.compile(r"^jih\s+ni\s*\.?\s*$", re.IGNORECASE),
    re.compile(r"ustvarjeni\s+prihodki", re.IGNORECASE),
    re.compile(r"poklic\s+ali\s+[čc]lanstvo", re.IGNORECASE),
    re.compile(r"\([čc]e\s+ne\s+ustvarja", re.IGNORECASE),
    re.compile(r"prihodkov\)\s*$", re.IGNORECASE),
    # Italian boilerplate
    re.compile(r"^importo\s+del\s+reddito", re.IGNORECASE),
    re.compile(r"^natura\s+del\s+beneficio", re.IGNORECASE),
    re.compile(r"^periodicit[àa]\s*$", re.IGNORECASE),
    re.compile(r"^nulla\s*$", re.IGNORECASE),
    re.compile(r"reddito\s+generato", re.IGNORECASE),
    re.compile(r"se\s+non\s+genera\s*$", re.IGNORECASE),
    re.compile(r"^reddito\)\s*$", re.IGNORECASE),
    re.compile(r"^attivit[àa]\s+o\s+partecipazione", re.IGNORECASE),
    re.compile(r"^partecipazione\s+o\s+attivit[àa]", re.IGNORECASE),
    re.compile(r"^settore\s+e\s+natura\s+dell", re.IGNORECASE),
    re.compile(r"^partecipazione\s+o\s+partenariato", re.IGNORECASE),
    re.compile(r"^stima\s*$", re.IGNORECASE),
    re.compile(r"^remunerazione\s*$", re.IGNORECASE),
    re.compile(r"^annuale\s*$", re.IGNORECASE),
    # Spanish boilerplate
    re.compile(r"^ninguno\b", re.IGNORECASE),
    re.compile(r"^importe\s+de\s+los", re.IGNORECASE),
    re.compile(r"^naturaleza\s+del", re.IGNORECASE),
    re.compile(r"^periodicidad\s*$", re.IGNORECASE),
    re.compile(r"ingresos\s+generados", re.IGNORECASE),
    re.compile(r"actividad\s+profesional\s+o\s+pertenencia", re.IGNORECASE),
    re.compile(r"genera\s+ingresos\)", re.IGNORECASE),
    re.compile(r"^beneficio\s*\(si\s+no", re.IGNORECASE),
    re.compile(r"^aproximado\s*$", re.IGNORECASE),
    re.compile(r"^pertenencia\s+o\s+actividad", re.IGNORECASE),
    re.compile(r"participaciones\s+en\s+empresas", re.IGNORECASE),
    re.compile(r"participaciones\s+que\s+otorguen", re.IGNORECASE),
    re.compile(r"influencia\s+importante\s*$", re.IGNORECASE),
    re.compile(r"implicaciones\s+pol[ií]ticas", re.IGNORECASE),
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

        Note: This method buffers all records in memory. For production use,
        prefer the overridden run() method which uploads incrementally per-MEP.
        """
        year_start = kwargs.get("year_start", 2015)
        all_records: List[Dict[str, Any]] = []

        supabase = get_supabase()
        if not supabase:
            self.logger.error("Supabase client not available")
            return []

        async with EUParliamentClient() as client:
            meps = await self._prepare_mep_list(client, **kwargs)
            if not meps:
                return []

            for i, mep in enumerate(meps):
                self.logger.info(
                    f"Processing MEP {i + 1}/{len(meps)}: {mep['full_name']}"
                )
                records = await self._fetch_mep_records(
                    client, supabase, mep, year_start
                )
                all_records.extend(records)

        self.logger.info(
            f"Extracted {len(all_records)} financial interest records "
            f"from {len(meps)} MEPs"
        )
        return all_records

    async def _prepare_mep_list(
        self, client: EUParliamentClient, **kwargs
    ) -> List[Dict[str, Any]]:
        """Fetch and prepare the deduplicated MEP list."""
        limit_meps = kwargs.get("limit_meps") or kwargs.get("limit")
        include_former = kwargs.get("include_former", True)

        self.logger.info("Fetching MEP list from EU Parliament XML...")
        meps = await client.fetch_mep_list()
        if not meps:
            self.logger.warning("No MEPs fetched from XML endpoint")
            return []

        self.logger.info(f"Found {len(meps)} current MEPs")

        if include_former:
            self.logger.info("Fetching outgoing/former MEPs for historical data...")
            former_meps = await client.fetch_outgoing_meps()
            if former_meps:
                existing_ids = {m["mep_id"] for m in meps}
                new_former = [m for m in former_meps if m["mep_id"] not in existing_ids]
                meps.extend(new_former)
                self.logger.info(
                    f"Added {len(new_former)} former MEPs (total: {len(meps)})"
                )

        if limit_meps:
            meps = meps[:limit_meps]
            self.logger.info(f"Limited to {limit_meps} MEPs for processing")

        return meps

    async def _fetch_mep_records(
        self,
        client: EUParliamentClient,
        supabase,
        mep: Dict[str, Any],
        year_start: int = 2015,
    ) -> List[Dict[str, Any]]:
        """
        Fetch and parse all financial interest records for a single MEP.

        Downloads DPI PDFs, extracts financial interests, and returns
        records ready for upload. Does NOT upload to database.
        """
        records: List[Dict[str, Any]] = []
        mep_id = mep["mep_id"]
        full_name = mep["full_name"]

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
            return records

        declarations = await client.fetch_declarations_page(mep_id, full_name)
        if not declarations:
            self.logger.info(f"No declarations found for MEP {full_name}")
            return records

        self.logger.info(
            f"Found {len(declarations)} declarations for {full_name}"
        )

        for decl in declarations:
            decl_date = decl.get("date", "")
            if decl_date and year_start:
                try:
                    if int(decl_date[:4]) < year_start:
                        self.logger.info(
                            f"Skipping {decl_date} declaration (before {year_start})"
                        )
                        continue
                except (ValueError, IndexError):
                    pass

            pdf_url = decl["pdf_url"]
            self.logger.info(f"Downloading PDF: {pdf_url}")
            pdf_bytes = await client.download_pdf(pdf_url)
            if not pdf_bytes:
                self.logger.warning(f"Failed to download PDF: {pdf_url}")
                continue

            text = extract_text_from_pdf(pdf_bytes)
            if not text:
                self.logger.warning(f"No text extracted from PDF: {pdf_url}")
                continue

            interests = extract_financial_interests(text)
            self.logger.info(
                f"Extracted {len(interests)} interests from {pdf_url}"
            )

            declaration_date = decl.get("date") or datetime.now(
                timezone.utc
            ).strftime("%Y-%m-%d")

            for interest in interests:
                records.append({
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
                })

        return records

    async def run(
        self,
        job_id: str,
        limit: Optional[int] = None,
        update_mode: bool = False,
        **kwargs,
    ) -> ETLResult:
        """
        Execute EU Parliament ETL with incremental per-MEP uploads.

        Overrides BaseETLService.run() to upload each MEP's records
        immediately after extraction. This ensures partial progress
        survives process restarts (Fly.io machine cycling) instead of
        losing ~60 minutes of work when all 736 MEPs are buffered.
        """
        result = ETLResult(started_at=datetime.now(timezone.utc))
        self._job_status[job_id] = JobStatus(
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
            message=f"Starting {self.source_name} ETL...",
        )

        try:
            await self.on_start(job_id, **kwargs)

            year_start = kwargs.get("year_start", 2015)

            supabase = get_supabase()
            if not supabase:
                result.add_error("Supabase client not available")
                result.completed_at = datetime.now(timezone.utc)
                self._job_status[job_id].status = "failed"
                self._job_status[job_id].message = "Supabase client not available"
                return result

            async with EUParliamentClient() as client:
                # Map run(limit=N) to limit_meps for EU ETL
                if limit and not kwargs.get("limit_meps"):
                    kwargs["limit_meps"] = limit

                self.update_job_status(job_id, message="Fetching MEP list...")
                meps = await self._prepare_mep_list(client, **kwargs)

                if not meps:
                    result.add_warning("No MEPs fetched from source")
                    self.update_job_status(
                        job_id, status="completed",
                        message="No MEPs to process",
                    )
                    result.completed_at = datetime.now(timezone.utc)
                    return result

                total_meps = len(meps)
                self.update_job_status(job_id, total=total_meps)
                self.logger.info(
                    f"Processing {total_meps} MEPs with incremental upload"
                )

                for i, mep in enumerate(meps):
                    mep_name = mep["full_name"]
                    self.update_job_status(
                        job_id, progress=i + 1,
                        message=(
                            f"MEP {i + 1}/{total_meps}: {mep_name} "
                            f"({result.records_inserted + result.records_updated} uploaded)"
                        ),
                    )

                    try:
                        records = await self._fetch_mep_records(
                            client, supabase, mep, year_start
                        )
                    except Exception as e:
                        result.records_failed += 1
                        result.add_error(
                            f"Failed to fetch MEP {mep_name}: {e}"
                        )
                        continue

                    # Upload this MEP's records immediately
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

                    if records:
                        self.logger.info(
                            f"MEP {i + 1}/{total_meps} {mep_name}: "
                            f"uploaded {len(records)} records "
                            f"(total: {result.records_inserted + result.records_updated})"
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
            self.logger.exception(f"ETL job {job_id} failed")

        return result

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
        if not asset_name or len(asset_name.strip()) < 5:
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
        transaction_type = "income" if section_letter in {"A", "B"} else "holding"

        entries = _parse_section_entries(body, section_letter)

        for entry in entries:
            value_low, value_high = _extract_income_range(entry["text"])
            entity = _clean_entity_name(entry["entity"])

            interests.append(
                {
                    "entity": entity,
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

    return entries


def _extract_income_range(text: str) -> tuple:
    """
    Try to extract income/amount from EU DPI text.

    Handles multiple formats found across 24 EU languages:
    - EUR ranges: "EUR 5,000 - EUR 9,999"
    - Single amounts (EUR before): "EUR 2,500" or "€2500"
    - Single amounts (EUR after): "2500 EUR" or "2 500 EUR" (common in Dutch/French/German PDFs)
    - EU income categories: "Category 1" through "Category 5"

    Returns:
        (value_low, value_high) or (None, None)
    """
    text_lower = text.lower()

    # Direct EUR range patterns (two amounts separated by dash)
    eur_range = re.search(
        r"(?:eur|€)\s*([\d,.\s]+?)\s*[-–—]+\s*(?:eur|€)?\s*([\d,.\s]+?)(?:\s|$|[a-z])",
        text_lower,
    )
    if eur_range:
        try:
            low = _parse_eur_number(eur_range.group(1))
            high = _parse_eur_number(eur_range.group(2))
            if low is not None and high is not None:
                return (low, high)
        except ValueError:
            pass

    # Single amount: "NUMBER EUR" format (e.g. "2500 EUR", "2 500 EUR")
    num_before_eur = re.search(
        r"([\d][\d,.\s]*)\s*(?:eur|€)", text_lower
    )
    if num_before_eur:
        val = _parse_eur_number(num_before_eur.group(1))
        if val is not None and val > 0:
            return (val, val)

    # Single amount: "EUR NUMBER" or "€NUMBER" format (e.g. "EUR 2500", "€2,500")
    eur_before_num = re.search(
        r"(?:eur|€)\s*([\d][\d,.\s]*?)(?:\s*(?:per|par|pro|/|$)|\s+[a-z]|$)",
        text_lower,
    )
    if eur_before_num:
        val = _parse_eur_number(eur_before_num.group(1))
        if val is not None and val > 0:
            return (val, val)

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


def _parse_eur_number(s: str) -> Optional[float]:
    """
    Parse a European-format number string to float.

    Handles: "2500", "2,500", "2.500", "2 500", "5,000.00"
    """
    cleaned = s.strip().replace(" ", "")
    if not cleaned:
        return None
    # If both , and . present, the last one is the decimal separator
    if "," in cleaned and "." in cleaned:
        if cleaned.rindex(",") > cleaned.rindex("."):
            # comma is decimal: 2.500,00
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            # period is decimal: 2,500.00
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        # Could be decimal (1,5) or thousands (1,000)
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) == 3:
            # Thousands separator: 2,500
            cleaned = cleaned.replace(",", "")
        else:
            # Decimal separator: 1,5
            cleaned = cleaned.replace(",", ".")
    elif "." in cleaned:
        parts = cleaned.split(".")
        if len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) >= 1:
            # Thousands separator (European style): 2.500
            cleaned = cleaned.replace(".", "")
        # else: decimal separator (English style): 2.5
    try:
        return float(cleaned)
    except ValueError:
        return None


# Pattern to strip EUR amounts and periodicity from entity names
_EUR_AMOUNT_PATTERN = re.compile(
    r"\s*[\d][\d,.\s]*\s*(?:eur|€)"
    r"(?:\s+(?:per|par|pro|promedio)\s+\w+(?:\s+aproximado)?"
    r"|\s+mese[čc]no|\s+mensile|\s+m[eě]s[ií][čc]n[eě]|\s+mensual"
    r"|\s+annuale|\s+trimestrale|\s+semestrale"
    r"|\s+stima(?:\s+remunerazione(?:\s+annuale)?)?"
    r")?\s*",
    re.IGNORECASE,
)
_EUR_PREFIX_PATTERN = re.compile(
    r"\s*(?:eur|€)\s*[\d][\d,.\s]*"
    r"(?:\s+(?:per|par|pro|promedio)\s+\w+(?:\s+aproximado)?"
    r"|\s+mese[čc]no|\s+mensile|\s+m[eě]s[ií][čc]n[eě]|\s+mensual"
    r"|\s+annuale|\s+trimestrale|\s+semestrale"
    r"|\s+stima(?:\s+remunerazione(?:\s+annuale)?)?"
    r")?\s*",
    re.IGNORECASE,
)


def _clean_entity_name(entity: str) -> str:
    """
    Remove EUR amount text from entity names.

    pdfplumber merges table columns, so amounts like "2500 EUR per maand"
    end up appended to entity names. Strip them out.

    Examples:
        "NBX 2500 EUR per maand" -> "NBX"
        "Uhasselt EUR 600" -> "Uhasselt"
        "Company X" -> "Company X"  (no amount, unchanged)
    """
    cleaned = _EUR_AMOUNT_PATTERN.sub(" ", entity)
    cleaned = _EUR_PREFIX_PATTERN.sub(" ", cleaned)
    # Strip standalone "aproximado" leftover from multi-line periodicity
    cleaned = re.sub(r"\s+aproximado\b", "", cleaned, flags=re.IGNORECASE)
    # Strip "X" markers (no-income indicator in DPI tables) — trailing or mid-string
    cleaned = re.sub(r",?\s+X\s*(?=-|$)", " ", cleaned)
    # Collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Strip trailing separators
    cleaned = cleaned.rstrip("- ")
    return cleaned if cleaned else entity


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
