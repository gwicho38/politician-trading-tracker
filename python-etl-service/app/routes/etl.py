"""ETL trigger and status endpoints."""

import os
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.services.house_etl import run_house_etl, JOB_STATUS
from app.services.ticker_backfill import run_ticker_backfill, run_transaction_type_backfill

router = APIRouter()


class ETLTriggerRequest(BaseModel):
    """Request body for triggering ETL."""
    source: str = "house"
    year: int = 2025
    limit: Optional[int] = None  # Optional limit for testing; None = process all


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


@router.post("/trigger", response_model=ETLTriggerResponse)
async def trigger_etl(
    request: ETLTriggerRequest,
    background_tasks: BackgroundTasks,
):
    """
    Trigger an ETL job for a specific data source.

    Currently supported sources:
    - house: US House of Representatives disclosures
    """
    if request.source != "house":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported source: {request.source}. Currently only 'house' is supported.",
        )

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Initialize job status
    JOB_STATUS[job_id] = {
        "status": "queued",
        "progress": 0,
        "total": request.limit,  # Will be updated once we know total
        "message": "Job queued",
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
    }

    # Add ETL task to background
    background_tasks.add_task(
        run_house_etl,
        job_id=job_id,
        year=request.year,
        limit=request.limit,
    )

    limit_msg = f"up to {request.limit}" if request.limit else "all"
    return ETLTriggerResponse(
        job_id=job_id,
        status="started",
        message=f"ETL job started for {request.source} ({request.year}), processing {limit_msg} PDFs",
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
        "started_at": datetime.utcnow().isoformat(),
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
        "started_at": datetime.utcnow().isoformat(),
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
