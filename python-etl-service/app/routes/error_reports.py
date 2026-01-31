"""
Error Reports API Routes

Endpoints for processing user-submitted error reports.

Sensitive endpoints (force-apply, reanalyze) require admin API key
for authorization as they can modify trading disclosure data.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from enum import Enum

from app.services.error_report_processor import ErrorReportProcessor
from app.middleware.auth import require_api_key, require_admin_key
from app.lib.audit_log import log_audit_event, AuditAction, AuditContext

router = APIRouter()


# ============================================================================
# Enums for OpenAPI Documentation
# ============================================================================

class ErrorType(str, Enum):
    """Types of errors users can report."""
    wrong_amount = "wrong_amount"
    wrong_date = "wrong_date"
    wrong_ticker = "wrong_ticker"
    wrong_politician = "wrong_politician"
    other = "other"


class ReportStatus(str, Enum):
    """Status of an error report."""
    pending = "pending"
    reviewed = "reviewed"
    fixed = "fixed"
    invalid = "invalid"


# ============================================================================
# Request Models
# ============================================================================

class ProcessRequest(BaseModel):
    """Request body for processing error reports."""
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of reports to process")
    model: str = Field(default="llama3.1:8b", description="Ollama model to use for analysis")
    dry_run: bool = Field(default=False, description="If true, analyze but don't apply corrections")


class ProcessOneRequest(BaseModel):
    """Request body for processing a single report."""
    report_id: str = Field(..., description="UUID of the error report to process")
    model: str = Field(default="llama3.1:8b", description="Ollama model to use for analysis")
    dry_run: bool = Field(default=False, description="If true, analyze but don't apply corrections")


# ============================================================================
# Response Models
# ============================================================================

class CorrectionDetail(BaseModel):
    """Details of a proposed or applied correction."""
    field: str = Field(..., description="Field being corrected (e.g., amount, ticker)")
    old_value: Optional[str] = Field(None, description="Original value")
    new_value: str = Field(..., description="Corrected value")
    confidence: float = Field(..., ge=0, le=1, description="LLM confidence score (0-1)")
    reasoning: Optional[str] = Field(None, description="LLM explanation for the correction")


class ProcessResponse(BaseModel):
    """Response for batch processing."""
    model_config = {"extra": "allow"}  # Allow extra fields from service

    processed: int = Field(..., description="Number of reports processed")
    fixed: int = Field(default=0, description="Number of corrections applied (high confidence)")
    needs_review: int = Field(default=0, description="Number flagged for human review (low confidence)")
    errors: int = Field(default=0, description="Number of processing errors")
    results: Optional[List[dict]] = Field(default=None, description="Per-report results")


class ProcessOneResponse(BaseModel):
    """Response for single report processing."""
    success: bool
    report_id: str
    status: str
    corrections: List[CorrectionDetail]
    admin_notes: Optional[str]
    dry_run: bool


class StatsResponse(BaseModel):
    """Response for error report statistics."""
    by_status: Dict[str, int] = Field(..., description="Counts per status (pending, reviewed, fixed, invalid)")
    by_type: Dict[str, int] = Field(..., description="Counts per error type")
    total: int = Field(..., description="Total number of reports")


class NeedsReviewResponse(BaseModel):
    """Response for reports needing review."""
    count: int
    reports: List[Dict[str, Any]] = Field(..., description="List of report objects needing review")


class ForceApplyResponse(BaseModel):
    """Response for force-apply operation."""
    success: bool
    report_id: str
    corrections_applied: int
    admin_notes: str


class ReanalyzeResponse(BaseModel):
    """Response for reanalyze operation."""
    report_id: str
    status: str
    confidence_threshold: float
    corrections: List[CorrectionDetail]
    admin_notes: Optional[str]
    dry_run: bool


class SuggestionResponse(BaseModel):
    """Response for generate-suggestion operation."""
    report_id: str
    model: str
    status: str = Field(..., description="no_corrections | suggestions_generated")
    message: Optional[str] = None
    report_summary: Dict[str, Any]
    corrections: List[Dict[str, Any]]
    summary: Optional[Dict[str, Any]] = None
    next_steps: Optional[Dict[str, Any]] = None


class OllamaHealthResponse(BaseModel):
    """Response for Ollama health check."""
    ollama_connected: bool
    ollama_url: str
    model: str


@router.post("/process", response_model=ProcessResponse)
async def process_pending_reports(request: ProcessRequest):
    """
    Process pending error reports using Ollama LLM.

    **Processing Flow:**
    1. Fetches up to `limit` pending reports
    2. Analyzes each report with the specified Ollama model
    3. High-confidence corrections (≥70%) are applied automatically
    4. Low-confidence corrections are flagged for human review

    **Returns:**
    - `processed`: Total reports analyzed
    - `applied`: Corrections applied automatically
    - `flagged_for_review`: Reports needing manual review
    - `errors`: Processing failures (check logs)
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


@router.post("/process-one", response_model=ProcessOneResponse)
async def process_single_report(request: ProcessOneRequest):
    """
    Process a single error report by ID.

    Useful for testing the LLM analysis on a specific report
    before processing in batch.

    Use `dry_run=true` to see what corrections would be applied
    without making changes.
    """
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


@router.get("/stats", response_model=StatsResponse)
async def get_error_report_stats():
    """
    Get statistics about error reports.

    **Status Definitions:**
    - `pending`: Not yet processed
    - `reviewed`: Processed, but corrections need manual review
    - `fixed`: Corrections applied successfully
    - `invalid`: Report determined to be invalid/duplicate

    **Error Types:**
    - `wrong_amount`: Incorrect transaction amount
    - `wrong_date`: Incorrect transaction or disclosure date
    - `wrong_ticker`: Incorrect stock ticker symbol
    - `wrong_politician`: Wrong politician attribution
    - `other`: Other data quality issues
    """
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


@router.get("/needs-review", response_model=NeedsReviewResponse)
async def get_reports_needing_review():
    """
    Get error reports that need human review.

    Returns reports with status `reviewed` that have suggested corrections
    but weren't auto-applied due to low confidence (<70%).

    **Next Steps for Reviewers:**
    1. Review the `admin_notes` field for LLM suggestions
    2. Use `POST /error-reports/force-apply` to apply corrections
    3. Or use `POST /error-reports/reanalyze` with lower threshold
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


class ForceApplyCorrection(BaseModel):
    """A single correction to force-apply."""
    field: str = Field(..., description="Field to correct (e.g., amount, ticker, politician_name)")
    new_value: str | int | float = Field(..., description="New value to apply")
    old_value: Optional[str | int | float] = Field(None, description="Original value (for audit trail)")


class ForceApplyRequest(BaseModel):
    """Request to force-apply corrections."""
    report_id: str = Field(..., description="UUID of the error report")
    corrections: List[ForceApplyCorrection] = Field(..., description="List of corrections to apply")


@router.post("/force-apply", response_model=ForceApplyResponse)
async def force_apply_correction(
    request: ForceApplyRequest,
    _admin_key: str = Depends(require_admin_key),
):
    """
    Force-apply corrections to a report regardless of confidence.

    **Requires admin API key** (`X-Admin-Key` header).

    Use this after manually reviewing low-confidence suggestions
    from `GET /error-reports/needs-review`.

    **Example Request:**
    ```json
    {
      "report_id": "uuid-here",
      "corrections": [
        {"field": "ticker", "new_value": "AAPL", "old_value": "APPL"}
      ]
    }
    ```

    All corrections are applied with 100% confidence and marked as
    "Manually applied by admin" in the audit trail.
    """
    with AuditContext(
        AuditAction.ERROR_REPORT_APPLY,
        resource_type="error_report",
        resource_id=request.report_id,
    ) as audit:
        audit.details["corrections_count"] = len(request.corrections)
        audit.details["fields"] = [c.field for c in request.corrections]

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
                    field=c.field,
                    old_value=c.old_value,
                    new_value=c.new_value,
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
    report_id: str = Field(..., description="UUID of the error report")
    model: str = Field(default="llama3.1:8b", description="Ollama model to use")
    confidence_threshold: float = Field(
        default=0.5,
        ge=0.1,
        le=1.0,
        description="Minimum confidence to auto-apply (default 70% lowered to 50%)"
    )
    dry_run: bool = Field(default=False, description="If true, analyze but don't apply")


@router.post("/reanalyze", response_model=ReanalyzeResponse)
async def reanalyze_report(
    request: ReanalyzeRequest,
    _admin_key: str = Depends(require_admin_key),
):
    """
    Reanalyze a report with a lower confidence threshold.

    **Requires admin API key** (`X-Admin-Key` header).

    Useful for reports that were flagged for review - you can
    re-run the analysis with a lower threshold to auto-apply
    corrections that the default threshold (70%) rejected.

    **Use Case:**
    When a report has sensible suggestions but confidence was 60%,
    set `confidence_threshold=0.5` to auto-apply them.
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
    report_id: str = Field(..., description="UUID of the error report")
    model: str = Field(default="llama3.1:8b", description="Ollama model to use")


@router.post("/generate-suggestion", response_model=SuggestionResponse)
async def generate_suggestion(request: GenerateSuggestionRequest):
    """
    Force Ollama to analyze a report and generate suggested corrections.

    **Use Cases:**
    - Preview suggestions for reports that haven't been processed yet
    - Re-generate suggestions with a different model
    - Test Ollama's interpretation before applying changes
    - Debug LLM behavior on specific reports

    Returns the suggested corrections **WITHOUT applying them**.

    **Response Fields:**
    - `status`: `no_corrections` if LLM couldn't determine fixes, `suggestions_generated` otherwise
    - `corrections[].would_auto_apply`: Whether this correction meets the confidence threshold
    - `next_steps`: API endpoints to apply the suggestions
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


@router.get("/health", response_model=OllamaHealthResponse)
async def check_ollama_health():
    """
    Check if Ollama service is available.

    **Health Indicators:**
    - `ollama_connected`: Whether the Ollama API is reachable
    - `ollama_url`: Base URL being used for Ollama
    - `model`: Default model for analysis

    If `ollama_connected=false`, error report processing will fail.
    Ensure Ollama is running and accessible.
    """
    processor = ErrorReportProcessor()

    connected = processor.test_connection()

    return {
        "ollama_connected": connected,
        "ollama_url": processor.ollama_client.base_url,
        "model": processor.model
    }
