"""
Senate PTR Historical Backfill Service (2012-2026)

Year-by-year orchestrator that backfills historical Periodic Transaction Reports
from the Senate EFD system. Uses Playwright for data retrieval since the Akamai
WAF blocks HTTP requests to the DataTables API.

Design:
- Dedup by source_url (always populated, unlike source_document_id)
- Per-year log_job_execution() for resumability
- Mutable existing_urls set grows as each year completes
- Reuses process_disclosures_playwright() for browser lifecycle
- 5s cooldown between years for GC on 256MB Fly.io
"""

import asyncio
import gc
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from supabase import Client

from app.lib.database import get_supabase
from app.lib.job_logger import log_job_execution
from app.services.house_etl import JOB_STATUS
from app.services.senate_etl import (
    _match_disclosures_to_senators,
    fetch_senators_from_xml,
    process_disclosures_playwright,
    search_all_ptr_disclosures_playwright,
    upsert_senator_to_db,
)

logger = logging.getLogger(__name__)

# Constants
BACKFILL_START_YEAR = 2012  # STOCK Act enacted
BACKFILL_END_YEAR = 2026
BACKFILL_JOB_ID = "politician-trading-senate-backfill"
YEAR_COOLDOWN_SECONDS = 5


def get_existing_senate_source_urls(supabase: Client) -> Set[str]:
    """
    Fetch all source_urls matching efdsearch.senate.gov to skip at discovery.

    Paginates through all records since there could be thousands.
    Returns a set for O(1) lookup during dedup.
    """
    urls: Set[str] = set()
    batch_size = 1000
    offset = 0

    while True:
        response = (
            supabase.table("trading_disclosures")
            .select("source_url")
            .like("source_url", "%efdsearch.senate%")
            .range(offset, offset + batch_size - 1)
            .execute()
        )

        if not response.data:
            break

        for row in response.data:
            url = row.get("source_url")
            if url:
                urls.add(url)

        if len(response.data) < batch_size:
            break

        offset += batch_size

    logger.info(f"Found {len(urls)} existing Senate source URLs for dedup")
    return urls


def get_completed_backfill_years(supabase: Client) -> Set[int]:
    """
    Check job_executions for successfully completed backfill years.

    Looks for entries with job_id='politician-trading-senate-backfill'
    and status='success' that have a year in their metadata.
    """
    years: Set[int] = set()

    try:
        response = (
            supabase.table("job_executions")
            .select("metadata")
            .eq("job_id", BACKFILL_JOB_ID)
            .eq("status", "success")
            .execute()
        )

        if response.data:
            for row in response.data:
                metadata = row.get("metadata", {})
                if isinstance(metadata, dict):
                    year = metadata.get("year")
                    if year is not None:
                        years.add(int(year))

    except Exception as e:
        logger.warning(f"Error fetching completed backfill years: {e}")

    logger.info(f"Previously completed backfill years: {sorted(years) if years else 'none'}")
    return years


async def backfill_year(
    year: int,
    senators: List[Dict[str, Any]],
    supabase: Client,
    existing_urls: Set[str],
    job_id: str,
    idx: int,
    total: int,
) -> Dict[str, Any]:
    """
    Backfill one year of Senate PTR disclosures.

    Steps:
    1. Search EFD via Playwright with date range for the year
    2. Filter out already-imported disclosures (by source_url)
    3. Match disclosures to senators
    4. Filter paper filings
    5. Process electronic disclosures via Playwright
    6. Update existing_urls set with newly imported URLs
    """
    start_date = f"01/01/{year}"
    end_date = f"12/31/{year}"
    year_started = datetime.now(timezone.utc)

    stats = {
        "year": year,
        "discovered": 0,
        "skipped_existing": 0,
        "skipped_paper": 0,
        "processed": 0,
        "transactions": 0,
        "errors": 0,
    }

    logger.info(f"[Backfill {idx}/{total}] Year {year}: searching {start_date} - {end_date}")

    JOB_STATUS[job_id]["message"] = (
        f"Year {year} ({idx}/{total}): searching disclosures..."
    )

    # Step 1: Search for disclosures in this year
    raw_disclosures = await search_all_ptr_disclosures_playwright(
        start_date=start_date,
        end_date=end_date,
    )
    stats["discovered"] = len(raw_disclosures)

    logger.info(f"[Backfill] Year {year}: discovered {len(raw_disclosures)} PTR disclosures")

    if not raw_disclosures:
        return stats

    # Step 2: Filter out already-imported
    new_disclosures = []
    for d in raw_disclosures:
        url = d.get("source_url", "")
        if url and url not in existing_urls:
            new_disclosures.append(d)
        else:
            stats["skipped_existing"] += 1

    logger.info(
        f"[Backfill] Year {year}: {len(new_disclosures)} new, "
        f"{stats['skipped_existing']} already imported"
    )

    if not new_disclosures:
        return stats

    # Step 3: Match to senators
    matched = _match_disclosures_to_senators(new_disclosures, senators)

    # Step 4: Filter paper filings
    electronic = [d for d in matched if not d.get("is_paper")]
    stats["skipped_paper"] = len(matched) - len(electronic)

    if not electronic:
        return stats

    stats["processed"] = len(electronic)

    JOB_STATUS[job_id]["message"] = (
        f"Year {year} ({idx}/{total}): processing {len(electronic)} disclosures..."
    )

    # Step 5: Process disclosures
    transactions, errors = await process_disclosures_playwright(electronic, supabase)
    stats["transactions"] = transactions
    stats["errors"] = errors

    # Step 6: Update existing_urls with newly imported
    for d in electronic:
        url = d.get("source_url")
        if url:
            existing_urls.add(url)

    # Log per-year execution
    year_completed = datetime.now(timezone.utc)
    log_job_execution(
        supabase,
        job_id=BACKFILL_JOB_ID,
        status="success",
        started_at=year_started,
        completed_at=year_completed,
        metadata={
            "year": year,
            "etl_job_id": job_id,
            **stats,
        },
    )

    logger.info(
        f"[Backfill] Year {year} complete: {stats['discovered']} discovered, "
        f"{stats['transactions']} transactions, {stats['errors']} errors"
    )

    return stats


async def run_senate_backfill(
    job_id: str,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    limit: Optional[int] = None,
    skip_completed: bool = True,
) -> None:
    """
    Main entry point for Senate PTR historical backfill.

    Iterates year-by-year from start_year to end_year, backfilling
    PTR disclosures via Playwright. Resumable: skips years that
    already completed successfully.

    Args:
        job_id: Unique job identifier for status tracking
        start_year: First year to backfill (default: 2012)
        end_year: Last year to backfill (default: 2026)
        limit: Max disclosures to process per year (for testing)
        skip_completed: If True, skip years already completed
    """
    start_yr = start_year or BACKFILL_START_YEAR
    end_yr = end_year or BACKFILL_END_YEAR

    JOB_STATUS[job_id]["status"] = "running"
    JOB_STATUS[job_id]["message"] = f"Starting Senate backfill {start_yr}-{end_yr}..."

    total_stats = {
        "years_processed": 0,
        "years_skipped": 0,
        "years_failed": 0,
        "total_discovered": 0,
        "total_transactions": 0,
        "total_errors": 0,
    }

    try:
        supabase = get_supabase()

        # Step 1: Fetch & upsert senators
        JOB_STATUS[job_id]["message"] = "Fetching senators..."
        senators = await fetch_senators_from_xml()
        if not senators:
            JOB_STATUS[job_id]["status"] = "error"
            JOB_STATUS[job_id]["message"] = "Failed to fetch senators list"
            return

        for senator in senators:
            politician_id = upsert_senator_to_db(supabase, senator)
            if politician_id:
                senator["politician_id"] = politician_id

        logger.info(f"[Backfill] Upserted {len(senators)} senators")

        # Step 2: Get existing source_urls for dedup
        JOB_STATUS[job_id]["message"] = "Loading existing URLs for dedup..."
        existing_urls = get_existing_senate_source_urls(supabase)

        # Step 3: Get completed years for resumability
        completed_years: Set[int] = set()
        if skip_completed:
            completed_years = get_completed_backfill_years(supabase)

        # Build year list
        years = list(range(start_yr, end_yr + 1))
        total_years = len(years)

        JOB_STATUS[job_id]["total"] = total_years

        # Step 4: Loop years
        for idx, year in enumerate(years, 1):
            if year in completed_years:
                logger.info(f"[Backfill] Skipping year {year} (already completed)")
                total_stats["years_skipped"] += 1
                JOB_STATUS[job_id]["progress"] = idx
                continue

            try:
                stats = await backfill_year(
                    year=year,
                    senators=senators,
                    supabase=supabase,
                    existing_urls=existing_urls,
                    job_id=job_id,
                    idx=idx,
                    total=total_years,
                )

                total_stats["years_processed"] += 1
                total_stats["total_discovered"] += stats["discovered"]
                total_stats["total_transactions"] += stats["transactions"]
                total_stats["total_errors"] += stats["errors"]

            except Exception as e:
                logger.error(f"[Backfill] Year {year} failed: {e}", exc_info=True)
                total_stats["years_failed"] += 1

                # Log failed year
                log_job_execution(
                    supabase,
                    job_id=BACKFILL_JOB_ID,
                    status="failed",
                    started_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                    error_message=str(e),
                    metadata={"year": year, "etl_job_id": job_id},
                )

            JOB_STATUS[job_id]["progress"] = idx

            # Step 5: Cooldown between years for GC
            if idx < total_years:
                gc.collect()
                await asyncio.sleep(YEAR_COOLDOWN_SECONDS)

        # Final status
        completed_at = datetime.now(timezone.utc)
        JOB_STATUS[job_id]["status"] = "completed"
        JOB_STATUS[job_id]["completed_at"] = completed_at.isoformat()
        JOB_STATUS[job_id]["message"] = (
            f"Backfill complete: {total_stats['years_processed']} years processed, "
            f"{total_stats['years_skipped']} skipped, "
            f"{total_stats['years_failed']} failed, "
            f"{total_stats['total_transactions']} transactions"
        )

        logger.info(f"[Backfill] Final stats: {total_stats}")

    except Exception as e:
        completed_at = datetime.now(timezone.utc)
        JOB_STATUS[job_id]["status"] = "error"
        JOB_STATUS[job_id]["message"] = f"Backfill failed: {str(e)}"
        JOB_STATUS[job_id]["completed_at"] = completed_at.isoformat()
        logger.error(f"[Backfill] Fatal error: {e}", exc_info=True)
        raise
