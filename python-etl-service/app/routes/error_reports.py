"""
Error Reports API Routes

Endpoints for processing user-submitted error reports.

Sensitive endpoints (force-apply, reanalyze) require admin API key
for authorization as they can modify trading disclosure data.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.error_report_processor import ErrorReportProcessor
from app.middleware.auth import require_api_key, require_admin_key
from app.lib.audit_log import log_audit_event, AuditAction, AuditContext

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
async def process_pending_reports(request: ProcessRequest) -> dict:
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
async def force_apply_correction(
    request: ForceApplyRequest,
    _admin_key: str = Depends(require_admin_key),
):
    """
    Force-apply corrections to a report regardless of confidence.

    **Requires admin API key.**

    Use this for manual review of low-confidence suggestions.
    Provide the corrections you want to apply.
    """
    with AuditContext(
        AuditAction.ERROR_REPORT_APPLY,
        resource_type="error_report",
        resource_id=request.report_id,
    ) as audit:
        audit.details["corrections_count"] = len(request.corrections)
        audit.details["fields"] = [c["field"] for c in request.corrections]

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
            audit.details["disclosure_id"] = disclosure_id

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

            audit.details["corrections_applied"] = len(corrections)
            audit.details["correction_summary"] = correction_summary

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
async def reanalyze_report(
    request: ReanalyzeRequest,
    _admin_key: str = Depends(require_admin_key),
):
    """
    Reanalyze a report with a lower confidence threshold.

    **Requires admin API key.**

    Useful for reports that were flagged for review - you can
    re-run the analysis with a lower threshold to auto-apply.
    """
    with AuditContext(
        AuditAction.ERROR_REPORT_REANALYZE,
        resource_type="error_report",
        resource_id=request.report_id,
    ) as audit:
        audit.details["model"] = request.model
        audit.details["confidence_threshold"] = request.confidence_threshold
        audit.details["dry_run"] = request.dry_run

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

            audit.details["result_status"] = result.status
            audit.details["corrections_count"] = len(result.corrections)

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


class GenerateSuggestionRequest(BaseModel):
    """Request to generate a suggestion for a report using Ollama."""
    report_id: str
    model: str = "llama3.1:8b"


@router.post("/generate-suggestion")
async def generate_suggestion(request: GenerateSuggestionRequest):
    """
    Force Ollama to analyze a report and generate suggested corrections.

    This is useful for:
    - Generating suggestions for reports that haven't been processed yet
    - Re-generating suggestions with a different model
    - Testing Ollama's interpretation of a specific report

    Returns the suggested corrections WITHOUT applying them.
    """
    processor = ErrorReportProcessor(model=request.model)

    if not processor.test_connection():
        raise HTTPException(status_code=503, detail="Cannot connect to Ollama service")

    if not processor.supabase:
        raise HTTPException(status_code=503, detail="Database not configured")

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

        report = response.data

        # Call Ollama to interpret corrections
        corrections = processor.interpret_corrections(report)

        if not corrections:
            return {
                "report_id": request.report_id,
                "model": request.model,
                "status": "no_corrections",
                "message": "Ollama could not determine any corrections for this report",
                "report_summary": {
                    "error_type": report.get("error_type"),
                    "description": report.get("description"),
                    "politician": report.get("disclosure_snapshot", {}).get("politician_name"),
                    "asset": report.get("disclosure_snapshot", {}).get("asset_name"),
                },
                "corrections": []
            }

        # Format corrections for response
        formatted_corrections = [
            {
                "field": c.field,
                "old_value": c.old_value,
                "new_value": c.new_value,
                "confidence": c.confidence,
                "confidence_pct": f"{c.confidence * 100:.0f}%",
                "reasoning": c.reasoning,
                "would_auto_apply": c.confidence >= processor.CONFIDENCE_THRESHOLD
            }
            for c in corrections
        ]

        # Determine overall status
        high_confidence = [c for c in corrections if c.confidence >= processor.CONFIDENCE_THRESHOLD]
        low_confidence = [c for c in corrections if c.confidence < processor.CONFIDENCE_THRESHOLD]

        return {
            "report_id": request.report_id,
            "model": request.model,
            "status": "suggestions_generated",
            "report_summary": {
                "error_type": report.get("error_type"),
                "description": report.get("description"),
                "politician": report.get("disclosure_snapshot", {}).get("politician_name"),
                "asset": report.get("disclosure_snapshot", {}).get("asset_name"),
                "current_status": report.get("status"),
            },
            "corrections": formatted_corrections,
            "summary": {
                "total_suggestions": len(corrections),
                "high_confidence": len(high_confidence),
                "low_confidence": len(low_confidence),
                "confidence_threshold": f"{processor.CONFIDENCE_THRESHOLD * 100:.0f}%"
            },
            "next_steps": {
                "to_apply_all": f"POST /error-reports/reanalyze with report_id={request.report_id}",
                "to_apply_manual": f"POST /error-reports/force-apply with specific corrections"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
