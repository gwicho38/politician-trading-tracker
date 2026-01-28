"""
ML API Routes

Endpoints for ML model prediction and training.

Sensitive endpoints (train, activate) require admin API key
for authorization as they can affect system behavior.
"""

import asyncio
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from app.services.ml_signal_model import (
    CongressSignalModel,
    get_active_model,
    load_active_model,
    get_cached_prediction,
    cache_prediction,
    compute_feature_hash,
    FEATURE_NAMES,
    SIGNAL_LABELS,
)
from app.services.feature_pipeline import (
    get_training_job,
    create_training_job,
    run_training_job_in_background,
    get_supabase,
)
from app.middleware.auth import require_admin_key
from app.lib.audit_log import log_audit_event, AuditAction, AuditContext

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class FeatureVector(BaseModel):
    """Input features for prediction."""
    ticker: str
    politician_count: int = Field(default=0, ge=0)
    buy_sell_ratio: float = Field(default=1.0, ge=0)
    recent_activity_30d: int = Field(default=0, ge=0)
    bipartisan: bool = False
    net_volume: float = 0
    volume_magnitude: float = 0
    party_alignment: float = Field(default=0.5, ge=0, le=1)
    committee_relevance: float = Field(default=0.5, ge=0, le=1)
    disclosure_delay: int = Field(default=30, ge=0)
    sentiment_score: float = Field(default=0, ge=-1, le=1)
    market_momentum: float = 0
    sector_performance: float = 0


class PredictRequest(BaseModel):
    """Request body for single prediction."""
    features: FeatureVector
    use_cache: bool = True


class BatchPredictRequest(BaseModel):
    """Request body for batch prediction."""
    tickers: List[FeatureVector]
    use_cache: bool = True


class PredictResponse(BaseModel):
    """Response for prediction."""
    ticker: str
    prediction: int
    signal_type: str
    confidence: float
    cached: bool = False
    model_id: Optional[str] = None


class TrainRequest(BaseModel):
    """Request body for triggering training."""
    lookback_days: int = Field(default=365, ge=30, le=730)
    model_type: str = Field(default="xgboost", pattern="^(xgboost|lightgbm)$")
    triggered_by: str = Field(
        default="api",
        description="Source that triggered the training: api, scheduler, batch_retraining, manual"
    )


class ModelInfo(BaseModel):
    """Model information."""
    id: str
    model_name: str
    model_version: str
    model_type: str
    status: str
    metrics: dict
    feature_importance: dict
    training_completed_at: Optional[str]
    created_at: str


# ============================================================================
# Prediction Endpoints
# ============================================================================

@router.post("/predict", response_model=PredictResponse)
async def predict_signal(request: PredictRequest):
    """
    Get ML prediction for a ticker's features.

    Returns signal type (-2 to 2) and confidence score.
    Uses caching to reduce computation.
    """
    features_dict = request.features.model_dump()
    ticker = features_dict['ticker']

    # Check cache first
    if request.use_cache:
        feature_hash = compute_feature_hash(features_dict)
        cached = get_cached_prediction(ticker, feature_hash)
        if cached:
            return PredictResponse(
                ticker=ticker,
                prediction=cached['prediction'],
                signal_type=SIGNAL_LABELS.get(cached['prediction'], 'hold'),
                confidence=cached['confidence'],
                cached=True,
                model_id=cached.get('model_id'),
            )

    # Get active model
    model = get_active_model()
    if model is None:
        model = load_active_model()
        if model is None:
            raise HTTPException(
                status_code=503,
                detail="No trained model available. Trigger training first.",
            )

    # Prepare features and predict
    try:
        feature_vector = model.prepare_features(features_dict)
        prediction, confidence = model.predict(feature_vector)

        # Cache the result
        if request.use_cache:
            feature_hash = compute_feature_hash(features_dict)
            cache_prediction(
                model_id=str(model.model_version),  # Use version as ID for now
                ticker=ticker,
                feature_hash=feature_hash,
                prediction=prediction,
                confidence=confidence,
            )

        return PredictResponse(
            ticker=ticker,
            prediction=prediction,
            signal_type=SIGNAL_LABELS.get(prediction, 'hold'),
            confidence=confidence,
            cached=False,
        )

    except Exception as e:
        logger.error(f"Prediction error for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-predict", response_model=List[PredictResponse])
async def batch_predict_signals(request: BatchPredictRequest):
    """
    Batch prediction for multiple tickers.

    Optimized for batch processing - does direct model inference without
    per-ticker cache overhead (which would cause HTTP bottlenecks).
    """
    # Get active model once for all predictions
    model = get_active_model()
    if model is None:
        model = load_active_model()
        if model is None:
            raise HTTPException(
                status_code=503,
                detail="No trained model available. Trigger training first.",
            )

    results = []
    for feature_vec in request.tickers:
        try:
            features_dict = feature_vec.model_dump()
            ticker = features_dict['ticker']

            # Direct model inference - no cache lookup/write to avoid HTTP overhead
            feature_vector = model.prepare_features(features_dict)
            prediction, confidence = model.predict(feature_vector)

            results.append(PredictResponse(
                ticker=ticker,
                prediction=prediction,
                signal_type=SIGNAL_LABELS.get(prediction, 'hold'),
                confidence=confidence,
                cached=False,
            ))
        except Exception as e:
            logger.error(f"Batch prediction error for {feature_vec.ticker}: {e}")
            results.append(PredictResponse(
                ticker=feature_vec.ticker,
                prediction=0,
                signal_type='error',
                confidence=0,
                cached=False,
            ))

    return results


# ============================================================================
# Training Endpoints
# ============================================================================

@router.post("/train")
async def trigger_training(
    request: TrainRequest,
    background_tasks: BackgroundTasks,
    _admin_key: str = Depends(require_admin_key),
):
    """
    Trigger model training job.

    **Requires admin API key.**

    This is a long-running operation that runs in the background.
    Returns a job ID to check progress.

    The triggered_by field tracks the source:
    - "api" (default): Direct API call
    - "scheduler": Weekly scheduled training (MlTrainingJob)
    - "batch_retraining": Threshold-based batch retraining (BatchRetrainingJob)
    - "manual": Manual trigger via admin/CLI
    """
    job = create_training_job(
        lookback_days=request.lookback_days,
        model_type=request.model_type,
        triggered_by=request.triggered_by,
    )

    logger.info(f"Training triggered by: {request.triggered_by}")

    # Log the training trigger
    log_audit_event(
        action=AuditAction.MODEL_TRAIN,
        resource_type="ml_training_job",
        resource_id=job.job_id,
        details={
            "lookback_days": request.lookback_days,
            "model_type": request.model_type,
            "triggered_by": request.triggered_by,
        },
    )

    # Run in background
    background_tasks.add_task(run_training_job_in_background, job)

    return {
        "job_id": job.job_id,
        "status": job.status,
        "triggered_by": request.triggered_by,
        "message": "Training job started. Use GET /ml/train/{job_id} to check progress.",
    }


@router.get("/train/{job_id}")
async def get_training_status(job_id: str):
    """Get training job status."""
    job = get_training_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Training job {job_id} not found")

    return job.to_dict()


# ============================================================================
# Model Management Endpoints
# ============================================================================

@router.get("/models")
async def list_models():
    """List all trained models with their metrics."""
    try:
        supabase = get_supabase()
        result = supabase.table('ml_models').select('*').order(
            'created_at', desc=True
        ).limit(20).execute()

        return {
            "models": result.data or [],
            "count": len(result.data or []),
        }

    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/active")
async def get_active_model_info():
    """Get information about the currently active model."""
    try:
        supabase = get_supabase()
        result = supabase.table('ml_models').select('*').eq('status', 'active').order(
            'training_completed_at', desc=True
        ).limit(1).execute()

        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="No active model found. Train a model first.")

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get active model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_id}")
async def get_model_info(model_id: str):
    """Get detailed information about a specific model."""
    try:
        supabase = get_supabase()
        result = supabase.table('ml_models').select('*').eq('id', model_id).limit(1).execute()

        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model {model_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_id}/feature-importance")
async def get_feature_importance(model_id: str):
    """
    Get feature importance for a specific model.

    Useful for explainability and understanding model behavior.
    """
    try:
        supabase = get_supabase()
        result = supabase.table('ml_models').select(
            'feature_importance, model_name, model_version'
        ).eq('id', model_id).limit(1).execute()

        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

        data = result.data[0]
        return {
            "model_id": model_id,
            "model_name": data.get('model_name'),
            "model_version": data.get('model_version'),
            "feature_importance": data.get('feature_importance', {}),
            "feature_names": FEATURE_NAMES,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get feature importance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/{model_id}/activate")
async def activate_model(
    model_id: str,
    _admin_key: str = Depends(require_admin_key),
):
    """
    Activate a specific model for predictions.

    **Requires admin API key.**

    Archives the currently active model.
    """
    with AuditContext(
        AuditAction.MODEL_ACTIVATE,
        resource_type="ml_model",
        resource_id=model_id,
    ) as audit:
        try:
            supabase = get_supabase()

            # Check model exists
            result = supabase.table('ml_models').select('id, status').eq('id', model_id).limit(1).execute()
            if not result.data or len(result.data) == 0:
                raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

            previous_status = result.data[0].get('status')
            audit.details["previous_status"] = previous_status

            # Archive current active models
            supabase.table('ml_models').update({
                'status': 'archived',
            }).eq('status', 'active').execute()

            # Activate requested model
            supabase.table('ml_models').update({
                'status': 'active',
            }).eq('id', model_id).execute()

            # Reload active model in memory
            load_active_model(model_id)

            audit.details["new_status"] = "active"

            return {"message": f"Model {model_id} activated", "status": "active"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to activate model {model_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Health/Status Endpoints
# ============================================================================

@router.get("/health")
async def ml_health():
    """ML service health check."""
    model = get_active_model()

    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "model_version": model.model_version if model else None,
        "feature_count": len(FEATURE_NAMES),
    }
