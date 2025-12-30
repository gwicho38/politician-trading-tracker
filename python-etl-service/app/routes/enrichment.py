"""
Party Enrichment API Routes

Endpoints for triggering and monitoring party enrichment jobs.
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

    # Get count
    count_result = supabase.table("politicians").select(
        "id", count="exact"
    ).is_("party", "null").limit(0).execute()

    # Get sample
    sample_result = supabase.table("politicians").select(
        "id, full_name, state, chamber"
    ).is_("party", "null").limit(10).execute()

    return {
        "total_missing_party": count_result.count,
        "sample": sample_result.data,
    }
