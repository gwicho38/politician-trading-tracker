"""
Enrichment API Routes

Endpoints for triggering and monitoring enrichment jobs:
- Party enrichment (Ollama)
- Name enrichment (Ollama) - PREFERRED for placeholder names
- Biography generation (Ollama + template fallback)
- BioGuide enrichment (Congress.gov) - Fallback for name/party/state
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.services.party_enrichment import (
    create_job,
    get_job,
    run_job_in_background,
)
from app.services.name_enrichment import (
    create_name_job,
    get_name_job,
    run_name_job_in_background,
)
from app.services.biography_generator import (
    create_bio_job,
    get_bio_job,
    run_bio_job_in_background,
)

router = APIRouter()


class EnrichmentTriggerRequest(BaseModel):
    """Request body for triggering enrichment."""
    limit: Optional[int] = None  # Limit number of politicians to process


class EnrichmentTriggerResponse(BaseModel):
    """Response for enrichment trigger."""
    job_id: str
    message: str
    status: str


class EnrichmentStatusResponse(BaseModel):
    """Response for enrichment status."""
    job_id: str
    status: str
    progress: int
    total: int
    updated: int
    skipped: int
    errors: int
    message: str
    started_at: Optional[str]
    completed_at: Optional[str]


@router.post("/trigger", response_model=EnrichmentTriggerResponse)
async def trigger_enrichment(
    request: EnrichmentTriggerRequest,
    background_tasks: BackgroundTasks,
):
    """
    Trigger a party enrichment job.

    This will query the Ollama LLM to determine party affiliation
    for politicians with missing party data.
    """
    job = create_job(limit=request.limit)

    # Run job in background
    background_tasks.add_task(run_job_in_background, job)

    return EnrichmentTriggerResponse(
        job_id=job.job_id,
        message=f"Party enrichment job started (limit: {request.limit or 'none'})",
        status="started",
    )


@router.get("/status/{job_id}", response_model=EnrichmentStatusResponse)
async def get_enrichment_status(job_id: str):
    """Get the status of a party enrichment job."""
    job = get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = job.to_dict()
    return EnrichmentStatusResponse(**state)


@router.get("/preview")
async def preview_enrichment():
    """
    Preview politicians that would be enriched.

    Returns a sample of politicians with missing party data.
    """
    from app.services.party_enrichment import get_supabase

    supabase = get_supabase()

    # Get count (NULL or "Unknown" party)
    count_result = supabase.table("politicians").select(
        "id", count="exact"
    ).or_("party.is.null,party.eq.Unknown").limit(0).execute()

    # Get sample
    sample_result = supabase.table("politicians").select(
        "id, full_name, state, chamber, party"
    ).or_("party.is.null,party.eq.Unknown").limit(10).execute()

    return {
        "total_missing_party": count_result.count,
        "sample": sample_result.data,
    }


# =============================================================================
# Name Enrichment Endpoints (Ollama-based - PREFERRED)
# =============================================================================

@router.post("/name/trigger", response_model=EnrichmentTriggerResponse)
async def trigger_name_enrichment(
    request: EnrichmentTriggerRequest,
    background_tasks: BackgroundTasks,
):
    """
    Trigger a name enrichment job using Ollama.

    This will use the LLM to extract proper politician names from raw
    disclosure data, replacing placeholder names like "House Member (Placeholder)".

    This is the PREFERRED method - run this before bioguide enrichment.
    """
    job = create_name_job(limit=request.limit)

    # Run job in background
    background_tasks.add_task(run_name_job_in_background, job)

    return EnrichmentTriggerResponse(
        job_id=job.job_id,
        message=f"Name enrichment job started (limit: {request.limit or 'none'})",
        status="started",
    )


@router.get("/name/status/{job_id}", response_model=EnrichmentStatusResponse)
async def get_name_enrichment_status(job_id: str):
    """Get the status of a name enrichment job."""
    job = get_name_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = job.to_dict()
    return EnrichmentStatusResponse(**state)


@router.get("/name/preview")
async def preview_name_enrichment():
    """
    Preview politicians with placeholder names that would be enriched.

    Returns a sample of politicians with placeholder-like names.
    """
    from app.services.party_enrichment import get_supabase

    supabase = get_supabase()

    placeholder_patterns = [
        "Placeholder",
        "Member (",
        "house_member",
        "senate_member",
        "Unknown",
    ]

    all_politicians = []
    for pattern in placeholder_patterns:
        result = supabase.table("politicians").select(
            "id, full_name, party, state, chamber"
        ).ilike("full_name", f"%{pattern}%").limit(20).execute()

        if result.data:
            all_politicians.extend(result.data)

    # Dedupe
    seen = set()
    unique = []
    for p in all_politicians:
        if p["id"] not in seen:
            seen.add(p["id"])
            unique.append(p)

    return {
        "total_placeholder_names": len(unique),
        "sample": unique[:10],
        "note": "Run 'name/trigger' to replace these with proper names using Ollama"
    }


# =============================================================================
# Biography Generation Endpoints (Ollama + template fallback)
# =============================================================================

class BiographyTriggerRequest(BaseModel):
    """Request body for triggering biography generation."""
    limit: Optional[int] = None
    force: bool = False  # If True, regenerate all bios (weekly refresh)


@router.post("/biography/trigger", response_model=EnrichmentTriggerResponse)
async def trigger_biography_generation(
    request: BiographyTriggerRequest,
    background_tasks: BackgroundTasks,
):
    """
    Trigger a biography generation job.

    Generates biographies for politicians using Ollama LLM with template fallback.
    Set force=True to regenerate all biographies (for weekly refresh).
    """
    job = create_bio_job(limit=request.limit, force=request.force)

    background_tasks.add_task(run_bio_job_in_background, job)

    mode = "force refresh" if request.force else "missing only"
    return EnrichmentTriggerResponse(
        job_id=job.job_id,
        message=f"Biography generation job started ({mode}, limit: {request.limit or 'none'})",
        status="started",
    )


@router.get("/biography/status/{job_id}", response_model=EnrichmentStatusResponse)
async def get_biography_status(job_id: str):
    """Get the status of a biography generation job."""
    job = get_bio_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = job.to_dict()
    return EnrichmentStatusResponse(**state)
