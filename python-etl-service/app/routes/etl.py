"""ETL trigger and status endpoints."""

import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

import httpx

# Legacy imports for backward compatibility
from app.services.house_etl import (
    run_house_etl,
    JOB_STATUS,
    HouseDisclosureScraper,
    extract_tables_from_pdf,
    parse_transaction_from_row,
    get_supabase,
    find_or_create_politician,
    upload_transaction_to_supabase,
)
from app.services.senate_etl import (
    run_senate_etl,
    fetch_senators_from_xml,
    get_supabase as get_senate_supabase_client,
)
from app.services.ticker_backfill import run_ticker_backfill, run_transaction_type_backfill
from app.services.bioguide_enrichment import run_bioguide_enrichment

# New framework imports
from app.lib import ETLRegistry

# Register services (import triggers registration)
import app.services.etl_services  # noqa: F401

router = APIRouter()


class ETLTriggerRequest(BaseModel):
    """Request body for triggering ETL."""
    source: str = "house"  # "house" or "senate"
    year: int = 2025
    lookback_days: int = 30  # For senate, how many days back to search
    limit: Optional[int] = None  # Optional limit for testing; None = process all
    update_mode: bool = False  # If true, upsert instead of insert (re-parse existing records)


class ETLTriggerResponse(BaseModel):
    """Response from triggering ETL."""
    job_id: str
    status: str
    message: str


class ETLStatusResponse(BaseModel):
    """Response for job status check."""
    job_id: str
    status: str
    progress: Optional[int] = None
    total: Optional[int] = None
    message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class SourceInfo(BaseModel):
    """Information about an ETL source."""
    source_id: str
    source_name: str
    class_name: str


class SourcesResponse(BaseModel):
    """Response listing available ETL sources."""
    sources: List[SourceInfo]


@router.get("/sources", response_model=SourcesResponse)
async def list_sources():
    """
    List all available ETL data sources.

    Returns registered sources from the ETL registry.
    """
    sources = [
        SourceInfo(
            source_id=info["source_id"],
            source_name=info["source_name"],
            class_name=info["class"],
        )
        for info in ETLRegistry.get_all_info()
    ]
    return SourcesResponse(sources=sources)


@router.post("/trigger", response_model=ETLTriggerResponse)
async def trigger_etl(
    request: ETLTriggerRequest,
    background_tasks: BackgroundTasks,
):
    """
    Trigger an ETL job for a specific data source.

    Supported sources can be listed via GET /etl/sources.
    Currently registered:
    - house: US House of Representatives disclosures
    - senate: US Senate disclosures
    """
    # Validate source using registry
    if not ETLRegistry.is_registered(request.source):
        available = ETLRegistry.list_sources()
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported source: {request.source}. Available: {available}",
        )

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Initialize job status
    JOB_STATUS[job_id] = {
        "status": "queued",
        "progress": 0,
        "total": request.limit,  # Will be updated once we know total
        "message": "Job queued",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
    }

    # Add ETL task to background based on source
    if request.source == "house":
        background_tasks.add_task(
            run_house_etl,
            job_id=job_id,
            year=request.year,
            limit=request.limit,
            update_mode=request.update_mode,
        )
    elif request.source == "senate":
        background_tasks.add_task(
            run_senate_etl,
            job_id=job_id,
            lookback_days=request.lookback_days,
            limit=request.limit,
            update_mode=request.update_mode,
        )

    limit_msg = f"up to {request.limit}" if request.limit else "all"
    mode_msg = " (UPDATE MODE)" if request.update_mode else ""
    return ETLTriggerResponse(
        job_id=job_id,
        status="started",
        message=f"ETL job started for {request.source} ({request.year}), processing {limit_msg} PDFs{mode_msg}",
    )


@router.get("/status/{job_id}", response_model=ETLStatusResponse)
async def get_job_status(job_id: str):
    """Get the status of an ETL job."""
    if job_id not in JOB_STATUS:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found",
        )

    status = JOB_STATUS[job_id]
    return ETLStatusResponse(
        job_id=job_id,
        status=status["status"],
        progress=status.get("progress"),
        total=status.get("total"),
        message=status.get("message"),
        started_at=status.get("started_at"),
        completed_at=status.get("completed_at"),
    )


class BackfillRequest(BaseModel):
    """Request body for ticker backfill."""
    limit: Optional[int] = None  # Optional limit for testing


@router.post("/backfill-tickers", response_model=ETLTriggerResponse)
async def trigger_backfill(
    request: BackfillRequest,
    background_tasks: BackgroundTasks,
):
    """
    Trigger ticker backfill job.

    Finds all disclosures with missing tickers and attempts to extract
    tickers from the asset_name field.
    """
    job_id = str(uuid.uuid4())

    JOB_STATUS[job_id] = {
        "status": "queued",
        "progress": 0,
        "total": None,
        "message": "Job queued",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
    }

    background_tasks.add_task(
        run_ticker_backfill,
        job_id=job_id,
        limit=request.limit,
    )

    limit_msg = f"up to {request.limit}" if request.limit else "all"
    return ETLTriggerResponse(
        job_id=job_id,
        status="started",
        message=f"Ticker backfill job started, processing {limit_msg} disclosures",
    )


@router.post("/backfill-transaction-types", response_model=ETLTriggerResponse)
async def trigger_transaction_type_backfill(
    request: BackfillRequest,
    background_tasks: BackgroundTasks,
):
    """
    Trigger transaction type backfill job.

    Finds all disclosures with 'unknown' transaction_type and attempts to
    extract purchase/sale from the raw_data.
    """
    job_id = str(uuid.uuid4())

    JOB_STATUS[job_id] = {
        "status": "queued",
        "progress": 0,
        "total": None,
        "message": "Job queued",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
    }

    background_tasks.add_task(
        run_transaction_type_backfill,
        job_id=job_id,
        limit=request.limit,
    )

    limit_msg = f"up to {request.limit}" if request.limit else "all"
    return ETLTriggerResponse(
        job_id=job_id,
        status="started",
        message=f"Transaction type backfill job started, processing {limit_msg} disclosures",
    )


@router.post("/enrich-bioguide", response_model=ETLTriggerResponse)
async def trigger_bioguide_enrichment(
    request: BackfillRequest,
    background_tasks: BackgroundTasks,
):
    """
    Trigger bioguide ID enrichment job.

    Fetches current Congress members from Congress.gov API and matches them
    to politicians in our database by name. Updates the bioguide_id column
    for matched politicians.

    Requires CONGRESS_API_KEY environment variable.
    """
    job_id = str(uuid.uuid4())

    JOB_STATUS[job_id] = {
        "status": "queued",
        "progress": 0,
        "total": None,
        "message": "Job queued",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
    }

    background_tasks.add_task(
        run_bioguide_enrichment,
        job_id=job_id,
        limit=request.limit,
    )

    limit_msg = f"up to {request.limit}" if request.limit else "all"
    return ETLTriggerResponse(
        job_id=job_id,
        status="started",
        message=f"BioGuide enrichment job started, processing {limit_msg} politicians",
    )


# =============================================================================
# Single File Ingest
# =============================================================================


class IngestUrlRequest(BaseModel):
    """Request body for single URL ingest."""
    url: str
    politician_name: Optional[str] = None  # Override politician name
    dry_run: bool = False  # If true, parse but don't upload


class IngestUrlResponse(BaseModel):
    """Response from single URL ingest."""
    url: str
    doc_id: str
    year: int
    politician_name: Optional[str]
    politician_id: Optional[str]
    transactions_found: int
    transactions_uploaded: int
    transactions: List[Dict[str, Any]]
    dry_run: bool


def parse_pdf_url(url: str) -> tuple[int, str, str]:
    """
    Parse a House disclosure PDF URL to extract year, doc_id, and filing type.

    Supports:
    - PTR PDFs: https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2025/20033576.pdf
    - FD PDFs: https://disclosures-clerk.house.gov/public_disc/financial-pdfs/2024/12345678.pdf

    Returns: (year, doc_id, filing_type)
    """
    # PTR pattern: /ptr-pdfs/{year}/{doc_id}.pdf
    ptr_match = re.search(r"/ptr-pdfs/(\d{4})/(\d+)\.pdf", url)
    if ptr_match:
        return int(ptr_match.group(1)), ptr_match.group(2), "P"

    # FD pattern: /financial-pdfs/{year}/{doc_id}.pdf
    fd_match = re.search(r"/financial-pdfs/(\d{4})/(\d+)\.pdf", url)
    if fd_match:
        return int(fd_match.group(1)), fd_match.group(2), "F"

    raise ValueError(f"Could not parse PDF URL: {url}")


@router.post("/ingest-url", response_model=IngestUrlResponse)
async def ingest_single_url(request: IngestUrlRequest):
    """
    Ingest a single disclosure PDF by URL.

    This endpoint:
    1. Downloads the PDF from the provided URL
    2. Parses transactions from the PDF
    3. Uploads to Supabase (unless dry_run=true)

    Useful for testing ETL on specific filings.

    Example URL: https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2025/20033576.pdf
    """
    url = request.url.strip()

    # Parse URL to extract metadata
    try:
        year, doc_id, filing_type = parse_pdf_url(url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create disclosure metadata
    disclosure = {
        "doc_id": doc_id,
        "year": year,
        "filing_type": filing_type,
        "pdf_url": url,
        "politician_name": request.politician_name or "Unknown",
        "first_name": "",
        "last_name": request.politician_name or "Unknown",
        "state_district": "",
        "filing_date": None,
        "source": "us_house",
    }

    # Download PDF
    async with httpx.AsyncClient(
        timeout=60.0,
        headers={"User-Agent": "Mozilla/5.0 (compatible; PoliticianTradingETL/1.0)"}
    ) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            pdf_bytes = response.content
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to download PDF: {e}"
            )

    # Validate PDF
    if not pdf_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=400,
            detail="Downloaded content is not a valid PDF"
        )

    # Parse PDF
    tables = extract_tables_from_pdf(pdf_bytes)
    transactions = []

    for table in tables:
        for row in table:
            txn = parse_transaction_from_row(row, disclosure)
            if txn:
                transactions.append(txn)

    # If dry run, return without uploading
    if request.dry_run:
        return IngestUrlResponse(
            url=url,
            doc_id=doc_id,
            year=year,
            politician_name=request.politician_name,
            politician_id=None,
            transactions_found=len(transactions),
            transactions_uploaded=0,
            transactions=transactions,
            dry_run=True,
        )

    # Upload to Supabase
    try:
        supabase_client = get_supabase()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    politician_id = None
    transactions_uploaded = 0

    if transactions:
        # Get or create politician
        politician_id = find_or_create_politician(supabase_client, disclosure)

        if politician_id:
            for txn in transactions:
                disclosure_id = upload_transaction_to_supabase(
                    supabase_client, politician_id, txn, disclosure
                )
                if disclosure_id:
                    transactions_uploaded += 1

    return IngestUrlResponse(
        url=url,
        doc_id=doc_id,
        year=year,
        politician_name=request.politician_name,
        politician_id=politician_id,
        transactions_found=len(transactions),
        transactions_uploaded=transactions_uploaded,
        transactions=transactions,
        dry_run=False,
    )


# =============================================================================
# Senate Endpoints
# =============================================================================


class SenatorsResponse(BaseModel):
    """Response for senator list."""
    senators: List[Dict[str, Any]]
    with_disclosures: int
    total_disclosures: int


@router.get("/senators", response_model=SenatorsResponse)
async def get_senators(refresh: bool = False):
    """
    Get list of current senators with disclosure counts.

    Args:
        refresh: If true, fetch fresh list from Senate.gov XML
    """
    senators = await fetch_senators_from_xml()

    # Initialize counters before try block to avoid UnboundLocalError
    with_disclosures = 0
    total_disclosures = 0

    # Get disclosure counts from Supabase
    try:
        supabase = get_senate_supabase_client()

        for senator in senators:
            bioguide = senator.get("bioguide_id")
            if bioguide:
                # Find politician by bioguide
                result = supabase.table("politicians").select("id").eq(
                    "bioguide_id", bioguide
                ).limit(1).execute()

                if result.data:
                    pol_id = result.data[0]["id"]

                    # Count disclosures
                    disc_result = supabase.table("trading_disclosures").select(
                        "id", count="exact"
                    ).eq("politician_id", pol_id).limit(0).execute()

                    count = disc_result.count or 0
                    senator["disclosure_count"] = count

                    if count > 0:
                        with_disclosures += 1
                        total_disclosures += count

    except Exception as e:
        # If Supabase fails, just return senators without counts
        pass

    return SenatorsResponse(
        senators=senators,
        with_disclosures=with_disclosures,
        total_disclosures=total_disclosures,
    )


# =============================================================================
# Job Execution Cleanup
# =============================================================================


class CleanupRequest(BaseModel):
    """Request body for job execution cleanup."""
    days: int = 30  # Delete records older than this many days


class CleanupResponse(BaseModel):
    """Response from cleanup operation."""
    deleted: int
    message: str


@router.post("/cleanup-executions", response_model=CleanupResponse)
async def cleanup_job_executions(request: CleanupRequest):
    """
    Clean up old job execution records from the database.

    Deletes job_executions records older than the specified number of days.
    This should be called periodically (e.g., weekly) to prevent table bloat.

    Default: deletes records older than 30 days.
    """
    from app.lib.job_logger import cleanup_old_executions

    try:
        supabase_client = get_supabase()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    deleted = cleanup_old_executions(supabase_client, days=request.days)

    return CleanupResponse(
        deleted=deleted,
        message=f"Deleted {deleted} job execution records older than {request.days} days",
    )
