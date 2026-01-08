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


@router.get("/needs-review")
async def get_reports_needing_review():
    """
    Get error reports that need human review.

    Returns reports with status 'reviewed' that have suggested corrections
    but weren't auto-applied due to low confidence.
    """
    processor = ErrorReportProcessor()

    if not processor.supabase:
        raise HTTPException(status_code=503, detail="Database not configured")

    try:
        response = (
            processor.supabase.table("user_error_reports")
            .select("*")
            .eq("status", "reviewed")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )

        return {
            "count": len(response.data or []),
            "reports": response.data or []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ForceApplyRequest(BaseModel):
    """Request to force-apply a correction."""
    report_id: str
    corrections: list[dict]  # [{field, new_value}, ...]


@router.post("/force-apply")
async def force_apply_correction(request: ForceApplyRequest):
    """
    Force-apply corrections to a report regardless of confidence.

    Use this for manual review of low-confidence suggestions.
    Provide the corrections you want to apply.
    """
    processor = ErrorReportProcessor()

    if not processor.supabase:
        raise HTTPException(status_code=503, detail="Database not configured")

    try:
        # Fetch the report
        report_response = (
            processor.supabase.table("user_error_reports")
            .select("*")
            .eq("id", request.report_id)
            .single()
            .execute()
        )

        if not report_response.data:
            raise HTTPException(status_code=404, detail="Report not found")

        report = report_response.data
        disclosure_id = report.get("disclosure_id")

        if not disclosure_id:
            raise HTTPException(status_code=400, detail="Report has no disclosure_id")

        # Build correction proposals with 100% confidence (force apply)
        from app.services.error_report_processor import CorrectionProposal
        corrections = [
            CorrectionProposal(
                field=c["field"],
                old_value=c.get("old_value"),
                new_value=c["new_value"],
                confidence=1.0,
                reasoning="Manually applied by admin"
            )
            for c in request.corrections
        ]

        # Apply the corrections
        success = processor._apply_corrections(disclosure_id, corrections)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to apply corrections")

        # Update report status
        correction_summary = "; ".join([
            f"{c.field}: {c.old_value} → {c.new_value}"
            for c in corrections
        ])
        processor._update_report_status(
            request.report_id,
            "fixed",
            f"Manually applied: {correction_summary}"
        )

        return {
            "success": True,
            "report_id": request.report_id,
            "corrections_applied": len(corrections),
            "admin_notes": f"Manually applied: {correction_summary}"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ReanalyzeRequest(BaseModel):
    """Request to reanalyze a report with lower confidence threshold."""
    report_id: str
    model: str = "llama3.1:8b"
    confidence_threshold: float = 0.5  # Lower threshold for manual review
    dry_run: bool = False


@router.post("/reanalyze")
async def reanalyze_report(request: ReanalyzeRequest):
    """
    Reanalyze a report with a lower confidence threshold.

    Useful for reports that were flagged for review - you can
    re-run the analysis with a lower threshold to auto-apply.
    """
    processor = ErrorReportProcessor(model=request.model)

    if not processor.test_connection():
        raise HTTPException(status_code=503, detail="Cannot connect to Ollama")

    if not processor.supabase:
        raise HTTPException(status_code=503, detail="Database not configured")

    # Temporarily lower the confidence threshold
    original_threshold = processor.CONFIDENCE_THRESHOLD
    processor.CONFIDENCE_THRESHOLD = request.confidence_threshold

    try:
        # Fetch the report
        response = (
            processor.supabase.table("user_error_reports")
            .select("*")
            .eq("id", request.report_id)
            .single()
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="Report not found")

        # Reset status to pending so it can be reprocessed
        if not request.dry_run:
            processor.supabase.table("user_error_reports").update({
                "status": "pending"
            }).eq("id", request.report_id).execute()

        report = response.data
        report["status"] = "pending"  # Override for processing

        result = processor.process_report(report, dry_run=request.dry_run)

        return {
            "report_id": result.report_id,
            "status": result.status,
            "confidence_threshold": request.confidence_threshold,
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

    finally:
        # Restore original threshold
        processor.CONFIDENCE_THRESHOLD = original_threshold


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
