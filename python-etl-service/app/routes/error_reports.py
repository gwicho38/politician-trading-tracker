"""
Error Reports API Routes

Endpoints for processing user-submitted error reports.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.error_report_processor import ErrorReportProcessor

router = APIRouter()


class ProcessRequest(BaseModel):
    """Request body for processing error reports."""
    limit: int = 10
    model: str = "llama3.1:8b"
    dry_run: bool = False


class ProcessOneRequest(BaseModel):
    """Request body for processing a single report."""
    report_id: str
    model: str = "llama3.1:8b"
    dry_run: bool = False


@router.post("/process")
async def process_pending_reports(request: ProcessRequest):
    """
    Process pending error reports using Ollama LLM.

    High-confidence corrections are applied automatically.
    Low-confidence corrections are flagged for human review.
    """
    processor = ErrorReportProcessor(model=request.model)

    # Test Ollama connection
    if not processor.test_connection():
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to Ollama service"
        )

    result = processor.process_all_pending(
        limit=request.limit,
        dry_run=request.dry_run
    )

    return result


@router.post("/process-one")
async def process_single_report(request: ProcessOneRequest):
    """Process a single error report by ID."""
    processor = ErrorReportProcessor(model=request.model)

    if not processor.test_connection():
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to Ollama service"
        )

    # Fetch the specific report
    if not processor.supabase:
        raise HTTPException(
            status_code=503,
            detail="Database not configured"
        )

    try:
        response = (
            processor.supabase.table("user_error_reports")
            .select("*")
            .eq("id", request.report_id)
            .single()
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )

        report = response.data
        result = processor.process_report(report, dry_run=request.dry_run)

        return {
            "success": True,
            "report_id": result.report_id,
            "status": result.status,
            "corrections": [
                {
                    "field": c.field,
                    "old_value": c.old_value,
                    "new_value": c.new_value,
                    "confidence": c.confidence,
                    "reasoning": c.reasoning
                }
                for c in result.corrections
            ],
            "admin_notes": result.admin_notes,
            "dry_run": request.dry_run
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing report: {str(e)}"
        )


@router.get("/stats")
async def get_error_report_stats():
    """Get statistics about error reports."""
    processor = ErrorReportProcessor()

    if not processor.supabase:
        raise HTTPException(
            status_code=503,
            detail="Database not configured"
        )

    try:
        # Get counts by status
        statuses = ["pending", "reviewed", "fixed", "invalid"]
        stats = {}

        for status in statuses:
            response = (
                processor.supabase.table("user_error_reports")
                .select("id", count="exact")
                .eq("status", status)
                .execute()
            )
            stats[status] = response.count or 0

        # Get counts by error type
        error_types = ["wrong_amount", "wrong_date", "wrong_ticker", "wrong_politician", "other"]
        by_type = {}

        for error_type in error_types:
            response = (
                processor.supabase.table("user_error_reports")
                .select("id", count="exact")
                .eq("error_type", error_type)
                .execute()
            )
            by_type[error_type] = response.count or 0

        return {
            "by_status": stats,
            "by_type": by_type,
            "total": sum(stats.values())
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching stats: {str(e)}"
        )


@router.get("/health")
async def check_ollama_health():
    """Check if Ollama service is available."""
    processor = ErrorReportProcessor()

    connected = processor.test_connection()

    return {
        "ollama_connected": connected,
        "ollama_url": processor.ollama_client.base_url,
        "model": processor.model
    }
