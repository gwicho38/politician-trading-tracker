"""
LLM Prompt Pipeline API Routes

Endpoints for the 4-stage LLM prompt pipeline:
1. Validation Gate - Post-ingestion semantic validation
2. Anomaly Detection - Detect anomalous trading patterns
3. Lineage Audit - Verify provenance chain of custody
4. Feedback Loop - Evaluate signal quality and recommend prompt improvements

Also provides audit trail querying and Ollama health checks.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.lib.database import get_supabase
from app.services.llm.client import LLMClient

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request Models
# ============================================================================

class ValidateBatchRequest(BaseModel):
    """Request body for batch validation."""
    model: Optional[str] = Field(
        default=None,
        description="Ollama model override (default: LLM_VALIDATION_MODEL env var or qwen3:8b)",
    )


class DetectAnomaliesRequest(BaseModel):
    """Request body for anomaly detection."""
    start_date: str = Field(..., description="ISO date string (inclusive) for window start")
    end_date: str = Field(..., description="ISO date string (inclusive) for window end")
    filer: str = Field(default="ALL", description="Filer name to filter on, or 'ALL' for all filers")


class AuditLineageRequest(BaseModel):
    """Request body for lineage audit."""
    disclosure_id: str = Field(..., description="UUID of the trading_disclosures record to audit")


class RunFeedbackRequest(BaseModel):
    """Request body for feedback loop analysis."""
    start_date: str = Field(..., description="ISO date string (inclusive) for window start")
    end_date: str = Field(..., description="ISO date string (inclusive) for window end")


# ============================================================================
# Response Models
# ============================================================================

class BackgroundTaskResponse(BaseModel):
    """Response for endpoints that launch background tasks."""
    status: str = Field(..., description="Task status (e.g., 'accepted')")
    message: str = Field(..., description="Human-readable status message")


class ValidationResultResponse(BaseModel):
    """Response for validation gate results."""
    total_records: int = Field(default=0, description="Total records processed")
    passed: int = Field(default=0, description="Records that passed validation")
    flagged: int = Field(default=0, description="Records flagged for review")
    rejected: int = Field(default=0, description="Records rejected")
    batches_processed: int = Field(default=0, description="Number of batches processed")


class AnomalyDetectionResponse(BaseModel):
    """Response for anomaly detection results."""
    model_config = {"extra": "allow"}

    anomalies_detected: int = Field(default=0, description="Number of anomalies detected")
    signals: List[dict] = Field(default_factory=list, description="Detected anomaly signals")
    analysis_window: dict = Field(default_factory=dict, description="Start/end dates analyzed")
    signals_stored: Optional[int] = Field(default=None, description="Signals stored in DB")


class LineageAuditResponse(BaseModel):
    """Response for lineage audit results."""
    trust_score: int = Field(default=0, description="Overall trust score (0-100)")
    chain_integrity: str = Field(default="broken", description="Chain integrity: valid, partial, or broken")
    verification_questions: List[str] = Field(default_factory=list, description="Questions to verify provenance")
    provenance_report: str = Field(default="", description="Narrative provenance report")


class FeedbackLoopResponse(BaseModel):
    """Response for feedback loop results."""
    model_config = {"extra": "allow"}

    scorecard: dict = Field(default_factory=dict, description="Performance scorecard")
    recommendations: List[dict] = Field(default_factory=list, description="Prompt improvement recommendations")
    threshold_adjustments: List[dict] = Field(default_factory=list, description="Suggested threshold adjustments")
    feedback_id: Optional[str] = Field(default=None, description="Feedback analysis ID")


class AuditTrailEntry(BaseModel):
    """Single audit trail entry."""
    model_config = {"extra": "allow"}

    id: Optional[str] = None
    service_name: Optional[str] = None
    prompt_version: Optional[str] = None
    model_used: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    parse_success: Optional[bool] = None
    created_at: Optional[str] = None


class AuditTrailResponse(BaseModel):
    """Response for audit trail query."""
    count: int = Field(..., description="Number of entries returned")
    entries: List[dict] = Field(default_factory=list, description="Audit trail entries")


class ProviderStatus(BaseModel):
    """Status of a single LLM provider."""
    name: str = Field(..., description="Provider name")
    connected: bool = Field(..., description="Whether provider is reachable")
    base_url: str = Field(..., description="Provider base URL")


class LLMHealthResponse(BaseModel):
    """Response for LLM health check."""
    providers: List[ProviderStatus] = Field(..., description="Status of each provider")
    any_connected: bool = Field(..., description="Whether at least one provider is reachable")


# ============================================================================
# Background task runners
# ============================================================================

async def _run_validation(model_override: Optional[str] = None) -> None:
    """Background task: run validation gate on recent pending records."""
    try:
        supabase = get_supabase()
        if not supabase:
            logger.error("Supabase client unavailable for validation background task")
            return

        from app.services.llm.validation_gate import ValidationGateService

        client = LLMClient()
        gate = ValidationGateService(llm_client=client, supabase=supabase)
        result = await gate.validate_recent()
        logger.info("Validation background task complete: %s", result)
    except Exception as exc:
        logger.error("Validation background task failed: %s", exc)


async def _run_feedback(start_date: str, end_date: str) -> None:
    """Background task: run feedback loop analysis."""
    try:
        supabase = get_supabase()
        if not supabase:
            logger.error("Supabase client unavailable for feedback background task")
            return

        from app.services.llm.feedback_loop import FeedbackLoopService

        client = LLMClient()
        service = FeedbackLoopService(llm_client=client, supabase=supabase)
        result = await service.analyze(start_date, end_date)
        logger.info("Feedback background task complete: %s", result)
    except Exception as exc:
        logger.error("Feedback background task failed: %s", exc)


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/validate-batch", response_model=BackgroundTaskResponse, status_code=202)
async def validate_batch(
    request: ValidateBatchRequest,
    background_tasks: BackgroundTasks,
):
    """
    Trigger batch validation of recently-ingested trading disclosures.

    Launches a background task that:
    1. Fetches records with llm_validation_status='pending' from the last 2 hours
    2. Sends them in batches to the LLM for semantic validation
    3. Updates each record's status (pass/flag/reject) and creates quality issues

    Returns immediately with HTTP 202 Accepted.
    """
    background_tasks.add_task(_run_validation, request.model)
    return BackgroundTaskResponse(
        status="accepted",
        message="Batch validation task has been queued.",
    )


@router.post("/detect-anomalies", response_model=AnomalyDetectionResponse)
async def detect_anomalies(request: DetectAnomaliesRequest):
    """
    Detect anomalous trading patterns within a date window.

    Fetches trading disclosures for the specified date range, computes
    per-filer baseline statistics from the prior 12 months, and sends
    the data to the LLM for anomaly analysis.

    High-confidence anomalies are also emitted as trading signals.
    """
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database not configured")

    from app.services.llm.anomaly_detector import AnomalyDetectionService

    client = LLMClient()
    service = AnomalyDetectionService(llm_client=client, supabase=supabase)

    try:
        result = await service.detect(
            start_date=request.start_date,
            end_date=request.end_date,
            filer=request.filer,
        )
        return result
    except Exception as exc:
        logger.error("Anomaly detection failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Anomaly detection failed: {exc}")


@router.post("/audit-lineage", response_model=LineageAuditResponse)
async def audit_lineage(request: AuditLineageRequest):
    """
    Audit the provenance chain of custody for a single trading disclosure.

    Computes a SHA-256 hash chain from the source filing through every
    transformation to the current state, sends the data to the LLM,
    and returns a structured provenance report with trust score.
    """
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database not configured")

    from app.services.llm.lineage_auditor import LineageAuditService

    client = LLMClient()
    service = LineageAuditService(llm_client=client, supabase=supabase)

    try:
        result = await service.audit(disclosure_id=request.disclosure_id)
        return result
    except Exception as exc:
        logger.error("Lineage audit failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Lineage audit failed: {exc}")


@router.post("/run-feedback", response_model=BackgroundTaskResponse, status_code=202)
async def run_feedback(
    request: RunFeedbackRequest,
    background_tasks: BackgroundTasks,
):
    """
    Trigger feedback loop analysis for a date window.

    Launches a background task that:
    1. Fetches trading signals with their position outcomes
    2. Computes a performance scorecard (hit_rate, alpha_rate, etc.)
    3. Sends the data to the LLM for meta-analysis
    4. Stores improvement recommendations in llm_prompt_recommendations

    Returns immediately with HTTP 202 Accepted.
    """
    background_tasks.add_task(_run_feedback, request.start_date, request.end_date)
    return BackgroundTaskResponse(
        status="accepted",
        message="Feedback loop analysis task has been queued.",
    )


@router.get("/audit-trail", response_model=AuditTrailResponse)
async def get_audit_trail(
    service_name: Optional[str] = None,
    limit: int = 50,
):
    """
    Query the LLM audit trail.

    Returns recent entries from the llm_audit_trail table, optionally
    filtered by service_name (e.g., 'validation_gate', 'anomaly_detection',
    'lineage_audit', 'feedback_loop').
    """
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database not configured")

    try:
        query = (
            supabase.table("llm_audit_trail")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
        )

        if service_name:
            query = query.eq("service_name", service_name)

        response = query.execute()
        entries = response.data or []

        return AuditTrailResponse(
            count=len(entries),
            entries=entries,
        )

    except Exception as exc:
        logger.error("Failed to query audit trail: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to query audit trail: {exc}")


@router.get("/health", response_model=LLMHealthResponse)
async def check_llm_health():
    """
    Test connectivity to all configured LLM providers.

    Returns per-provider status and whether at least one provider
    is reachable.
    """
    client = LLMClient()
    statuses = await client.test_connections()
    providers = [
        ProviderStatus(
            name=p.name,
            connected=statuses.get(p.name, False),
            base_url=p.base_url,
        )
        for p in client.providers
    ]
    return LLMHealthResponse(
        providers=providers,
        any_connected=any(s.connected for s in providers),
    )
