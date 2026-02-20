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
    DEFAULT_FEATURE_NAMES,
    SIGNAL_LABELS,
    get_signal_labels,
    get_feature_names,
)
from app.services.feature_pipeline import (
    get_training_job,
    create_training_job,
    run_training_job_in_background,
    get_supabase,
)
from app.models.training_config import TrainingConfig, FeatureToggles
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
    vix_level: float = Field(default=0.5, ge=0, description="VIX level normalized by /30")
    market_return_20d: float = Field(default=0.0, description="SPY 20-day return")
    market_breadth: float = Field(default=0.5, ge=0, le=1, description="Fraction of sectors with positive 20d returns")


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
    prediction_window_days: int = Field(default=7, description="Forward return window: 7, 14, or 30")
    num_classes: int = Field(default=5, description="3 (buy/hold/sell) or 5 (strong_buy/.../strong_sell)")
    enable_sector: bool = Field(default=True, description="Include sector features")
    enable_market_regime: bool = Field(default=True, description="Include VIX/SPY/breadth features")
    enable_sentiment: bool = Field(default=False, description="Include LLM sentiment (slow)")
    triggered_by: str = Field(
        default="api",
        description="Source that triggered the training: api, scheduler, batch_retraining, manual"
    )
    use_outcomes: bool = Field(default=False, description="Use signal_outcomes for training labels")
    outcome_weight: float = Field(default=2.0, ge=0.1, le=10.0, description="Weight multiplier for outcome-labeled data")
    fine_tune: bool = Field(default=False, description="Fine-tune existing model instead of training from scratch")
    base_model_id: Optional[str] = Field(default=None, description="Model ID to fine-tune from (required if fine_tune=True)")


class ModelInfo(BaseModel):
    """Model information stored in ml_models table."""
    model_config = {"extra": "allow"}  # Allow extra fields from database

    id: str
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    model_type: Optional[str] = None
    status: str
    metrics: Optional[dict] = None
    feature_importance: Optional[dict] = None
    training_completed_at: Optional[str] = None
    created_at: Optional[str] = None


class TrainJobResponse(BaseModel):
    """Response for training job trigger."""
    job_id: str
    status: str
    triggered_by: str
    message: str


class TrainJobStatusResponse(BaseModel):
    """Response for training job status."""
    job_id: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    model_id: Optional[str] = None
    metrics: Optional[dict] = None


class ModelsListResponse(BaseModel):
    """Response for listing all models."""
    models: List[dict]
    count: int


class ModelActivateResponse(BaseModel):
    """Response for model activation."""
    message: str
    status: str


class FeatureImportanceResponse(BaseModel):
    """Response for feature importance query."""
    model_id: str
    model_name: Optional[str]
    model_version: Optional[str]
    feature_importance: dict
    feature_names: List[str]


class MLHealthResponse(BaseModel):
    """Response for ML service health check."""
    status: str
    model_loaded: bool
    model_version: Optional[str]
    feature_count: int


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
                signal_type=SIGNAL_LABELS.get(cached['prediction'], 'hold'),  # cache doesn't store num_classes, use 5-class
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

        labels = get_signal_labels(model.num_classes)
        return PredictResponse(
            ticker=ticker,
            prediction=prediction,
            signal_type=labels.get(prediction, 'hold'),
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
            labels = get_signal_labels(model.num_classes)

            results.append(PredictResponse(
                ticker=ticker,
                prediction=prediction,
                signal_type=labels.get(prediction, 'hold'),
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

@router.post("/train", response_model=TrainJobResponse)
async def trigger_training(
    request: TrainRequest,
    background_tasks: BackgroundTasks,
    _admin_key: str = Depends(require_admin_key),
):
    """
    Trigger model training job.

    **Requires admin API key** (`X-Admin-Key` header).

    This is a long-running operation that runs in the background.
    Returns a job ID to check progress via `GET /ml/train/{job_id}`.

    **Training Sources** (`triggered_by` field):
    - `api` (default): Direct API call
    - `scheduler`: Weekly scheduled training (MlTrainingJob)
    - `batch_retraining`: Threshold-based batch retraining (BatchRetrainingJob)
    - `manual`: Manual trigger via admin/CLI

    **Training Process:**
    1. Fetches disclosures from the last `lookback_days`
    2. Extracts features using FeaturePipeline
    3. Trains XGBoost/LightGBM model
    4. Uploads model artifact to Supabase storage
    5. Records model metadata in `ml_models` table
    """
    config = TrainingConfig(
        lookback_days=request.lookback_days,
        model_type=request.model_type,
        prediction_window_days=request.prediction_window_days,
        num_classes=request.num_classes,
        features=FeatureToggles(
            enable_sector=request.enable_sector,
            enable_market_regime=request.enable_market_regime,
            enable_sentiment=request.enable_sentiment,
        ),
        triggered_by=request.triggered_by,
        use_outcomes=request.use_outcomes,
        outcome_weight=request.outcome_weight,
        fine_tune=request.fine_tune,
        base_model_id=request.base_model_id,
    )

    job = create_training_job(config=config)

    logger.info(f"Training triggered by: {request.triggered_by}, config: {config.num_classes}-class, {config.prediction_window_days}d window")

    # Log the training trigger
    log_audit_event(
        action=AuditAction.MODEL_TRAIN,
        resource_type="ml_training_job",
        resource_id=job.job_id,
        details=config.to_hyperparameters_dict(),
    )

    # Run in background
    background_tasks.add_task(run_training_job_in_background, job)

    return {
        "job_id": job.job_id,
        "status": job.status,
        "triggered_by": request.triggered_by,
        "message": "Training job started. Use GET /ml/train/{job_id} to check progress.",
    }


@router.get("/train/{job_id}", response_model=TrainJobStatusResponse)
async def get_training_status(job_id: str):
    """
    Get training job status.

    **Job Statuses:**
    - `pending`: Job created, waiting to start
    - `running`: Training in progress
    - `completed`: Training finished successfully
    - `failed`: Training failed (check `error` field)

    Poll this endpoint to monitor long-running training jobs.
    """
    job = get_training_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Training job {job_id} not found")

    return job.to_dict()


# ============================================================================
# Model Management Endpoints
# ============================================================================

@router.get("/models", response_model=ModelsListResponse)
async def list_models():
    """
    List all trained models with their metrics.

    Returns the 20 most recent models ordered by creation date.

    **Model Statuses:**
    - `active`: Currently used for predictions
    - `archived`: Previously active, now replaced
    - `training`: Training in progress
    - `failed`: Training failed
    """
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


@router.get("/models/active", response_model=ModelInfo)
async def get_active_model_info():
    """
    Get information about the currently active model.

    The active model is used for all `/ml/predict` and `/ml/batch-predict` requests.

    Returns 404 if no model has been trained yet.
    """
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


@router.get("/models/{model_id}/feature-importance", response_model=FeatureImportanceResponse)
async def get_feature_importance(model_id: str):
    """
    Get feature importance for a specific model.

    Useful for explainability and understanding model behavior.

    **Feature Importance Interpretation:**
    - Higher values indicate greater influence on predictions
    - Values are normalized (0-1 scale, sum to 1)
    - Based on XGBoost/LightGBM gain-based importance
    """
    try:
        supabase = get_supabase()
        result = supabase.table('ml_models').select(
            'feature_importance, model_name, model_version'
        ).eq('id', model_id).limit(1).execute()

        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

        data = result.data[0]
        # Feature names from hyperparameters if available, else defaults
        hyper = data.get('hyperparameters') or {}
        feature_names = hyper.get('feature_names', DEFAULT_FEATURE_NAMES)
        return {
            "model_id": model_id,
            "model_name": data.get('model_name'),
            "model_version": data.get('model_version'),
            "feature_importance": data.get('feature_importance', {}),
            "feature_names": feature_names,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get feature importance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/{model_id}/activate", response_model=ModelActivateResponse)
async def activate_model(
    model_id: str,
    _admin_key: str = Depends(require_admin_key),
):
    """
    Activate a specific model for predictions.

    **Requires admin API key** (`X-Admin-Key` header).

    **Side Effects:**
    - Archives the currently active model (status: `active` → `archived`)
    - Sets the specified model's status to `active`
    - Reloads the model into memory for predictions

    Use this to roll back to a previous model or activate a newly trained model.
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

@router.get("/health", response_model=MLHealthResponse)
async def ml_health():
    """
    ML service health check.

    **Health Indicators:**
    - `model_loaded`: Whether a trained model is loaded in memory
    - `model_version`: Version string of the loaded model
    - `feature_count`: Number of features the model expects

    If `model_loaded` is `false`, predictions will fail until a model is trained.
    """
    model = get_active_model()

    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "model_version": model.model_version if model else None,
        "feature_count": len(model.feature_names) if model else len(DEFAULT_FEATURE_NAMES),
    }
