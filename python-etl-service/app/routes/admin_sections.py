"""
Expanded Admin Dashboard Routes

Additional admin sections beyond the core validation dashboard:
- Overview: System-wide health summary
- ETL Jobs: Trigger and monitor House/Senate ETL pipelines
- ML Models: View models, trigger training, activate
- Data Quality: Ticker validation, source audit, freshness
- Enrichment: Trigger and monitor enrichment jobs
- Error Reports: View and process user-submitted error reports
- Audit Log: Unified event timeline

Authentication: Requires ETL_ADMIN_API_KEY via query param or header.
"""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.lib.database import get_supabase
from app.routes.admin import require_admin_for_dashboard, templates

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Overview Page
# ============================================================================


@router.get("/overview", response_class=HTMLResponse)
async def admin_overview(
    request: Request,
    api_key: str = Depends(require_admin_for_dashboard),
):
    """System-wide overview with health indicators for all subsystems."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    stats = {}

    # Trading disclosures count
    try:
        resp = supabase.table("trading_disclosures").select("id", count="exact").execute()
        stats["total_disclosures"] = resp.count if resp.count is not None else len(resp.data or [])
    except Exception:
        stats["total_disclosures"] = 0

    # Politicians count
    try:
        resp = supabase.table("politicians").select("id", count="exact").execute()
        stats["total_politicians"] = resp.count if resp.count is not None else len(resp.data or [])
    except Exception:
        stats["total_politicians"] = 0

    # ML models
    try:
        resp = supabase.table("ml_models").select("id,status").execute()
        models = resp.data or []
        stats["total_models"] = len(models)
        stats["active_models"] = sum(1 for m in models if m.get("status") == "active")
    except Exception:
        stats["total_models"] = 0
        stats["active_models"] = 0

    # ML training jobs (recent)
    try:
        resp = (
            supabase.table("ml_training_jobs")
            .select("id,status")
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        jobs = resp.data or []
        stats["running_jobs"] = sum(1 for j in jobs if j.get("status") in ("running", "pending"))
        stats["recent_jobs"] = len(jobs)
    except Exception:
        stats["running_jobs"] = 0
        stats["recent_jobs"] = 0

    # Error reports
    try:
        resp = (
            supabase.table("user_error_reports")
            .select("id,status")
            .execute()
        )
        reports = resp.data or []
        stats["total_error_reports"] = len(reports)
        stats["pending_error_reports"] = sum(
            1 for r in reports if r.get("status") in ("pending", "open")
        )
    except Exception:
        stats["total_error_reports"] = 0
        stats["pending_error_reports"] = 0

    # Validation results
    try:
        resp = supabase.table("trade_validation_results").select("id", count="exact").execute()
        stats["total_validations"] = resp.count if resp.count is not None else 0
        resp = supabase.table("trade_validation_results").select("id", count="exact").eq("validation_status", "mismatch").execute()
        stats["validation_mismatches"] = resp.count if resp.count is not None else 0
    except Exception:
        stats["total_validations"] = 0
        stats["validation_mismatches"] = 0

    # Recent disclosures (last 24h)
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        resp = (
            supabase.table("trading_disclosures")
            .select("id", count="exact")
            .gte("created_at", cutoff)
            .execute()
        )
        stats["disclosures_24h"] = resp.count if resp.count is not None else len(resp.data or [])
    except Exception:
        stats["disclosures_24h"] = 0

    return templates.TemplateResponse(
        "admin/overview.html",
        {
            "request": request,
            "api_key": api_key,
            "stats": stats,
            "active_section": "overview",
        },
    )


# ============================================================================
# ETL Jobs Page
# ============================================================================


@router.get("/etl", response_class=HTMLResponse)
async def admin_etl(
    request: Request,
    api_key: str = Depends(require_admin_for_dashboard),
):
    """ETL pipeline management - trigger and monitor House/Senate jobs."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    # Get recent disclosures stats using server-side counting
    stats = {"house_count": 0, "senate_count": 0, "eu_count": 0, "total_count": 0, "recent_24h": 0}

    # Total disclosures
    try:
        resp = supabase.table("trading_disclosures").select("id", count="exact").execute()
        stats["total_count"] = resp.count if resp.count is not None else 0
    except Exception as e:
        logger.error(f"Failed to get total disclosures count: {e}")

    # Chamber breakdown from politicians table (chamber lives there, not on disclosures)
    try:
        resp = supabase.table("politicians").select("id", count="exact").eq("chamber", "house").execute()
        stats["house_count"] = resp.count if resp.count is not None else 0
        resp = supabase.table("politicians").select("id", count="exact").eq("chamber", "senate").execute()
        stats["senate_count"] = resp.count if resp.count is not None else 0
        resp = supabase.table("politicians").select("id", count="exact").eq("chamber", "eu_parliament").execute()
        stats["eu_count"] = resp.count if resp.count is not None else 0
    except Exception as e:
        logger.error(f"Failed to get chamber counts: {e}")

    # Recent (last 24h)
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        resp = supabase.table("trading_disclosures").select("id", count="exact").gte("created_at", cutoff).execute()
        stats["recent_24h"] = resp.count if resp.count is not None else 0
    except Exception as e:
        logger.error(f"Failed to get recent disclosures count: {e}")

    return templates.TemplateResponse(
        "admin/etl_jobs.html",
        {
            "request": request,
            "api_key": api_key,
            "stats": stats,
            "active_section": "etl",
        },
    )


@router.post("/api/trigger-etl", response_class=HTMLResponse)
async def api_trigger_etl(
    request: Request,
    background_tasks: BackgroundTasks,
    key: Optional[str] = Query(None),
):
    """Trigger an ETL job via HTMX."""
    if not key:
        try:
            form_data = await request.form()
            key = form_data.get("key")
            source = form_data.get("source", "house")
            year = int(form_data.get("year", 2025))
        except Exception:
            source = "house"
            year = 2025

    from app.middleware.auth import validate_api_key
    if not key or not validate_api_key(key, require_admin=True):
        return HTMLResponse('<div class="text-red-600 p-3">Invalid API key</div>', status_code=401)

    try:
        if source == "house":
            from app.services.house_etl import run_house_etl, JOB_STATUS
            import uuid
            job_id = str(uuid.uuid4())
            JOB_STATUS[job_id] = {"status": "running", "started_at": datetime.now(timezone.utc).isoformat()}
            background_tasks.add_task(run_house_etl, job_id, year)
            return HTMLResponse(
                f'<div class="bg-green-100 text-green-800 p-3 rounded">'
                f'House ETL started for {year}. Job ID: <code class="text-xs">{job_id[:8]}...</code>'
                f'</div>'
            )
        elif source == "senate":
            from app.services.senate_etl import run_senate_etl
            import uuid
            job_id = str(uuid.uuid4())
            background_tasks.add_task(run_senate_etl, job_id, 30)
            return HTMLResponse(
                f'<div class="bg-green-100 text-green-800 p-3 rounded">'
                f'Senate ETL started (30-day lookback). Job ID: <code class="text-xs">{job_id[:8]}...</code>'
                f'</div>'
            )
        elif source == "eu_parliament":
            from app.lib.registry import ETLRegistry
            import uuid
            job_id = str(uuid.uuid4())

            async def _run_eu_etl(jid: str):
                service = ETLRegistry.create_instance("eu_parliament")
                await service.run(job_id=jid)

            background_tasks.add_task(_run_eu_etl, job_id)
            return HTMLResponse(
                f'<div class="bg-green-100 text-green-800 p-3 rounded">'
                f'EU Parliament ETL started (2015+ backfill). Job ID: <code class="text-xs">{job_id[:8]}...</code>'
                f'</div>'
            )
        else:
            return HTMLResponse(f'<div class="text-red-600 p-3">Unknown source: {source}</div>')
    except Exception as e:
        logger.exception("ETL trigger failed")
        return HTMLResponse(f'<div class="text-red-600 p-3">ETL failed: {str(e)}</div>', status_code=500)


# ============================================================================
# ML Models Page
# ============================================================================


@router.get("/ml", response_class=HTMLResponse)
async def admin_ml(
    request: Request,
    api_key: str = Depends(require_admin_for_dashboard),
):
    """ML model management - view, train, activate."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    models = []
    jobs = []
    try:
        resp = (
            supabase.table("ml_models")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        models = resp.data or []
    except Exception as e:
        logger.error(f"Failed to fetch ML models: {e}")

    try:
        resp = (
            supabase.table("ml_training_jobs")
            .select("*")
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        jobs = resp.data or []
    except Exception as e:
        logger.error(f"Failed to fetch training jobs: {e}")

    active_models = [m for m in models if m.get("status") == "active"]
    running_jobs = [j for j in jobs if j.get("status") in ("running", "pending")]

    return templates.TemplateResponse(
        "admin/ml_models.html",
        {
            "request": request,
            "api_key": api_key,
            "models": models,
            "jobs": jobs,
            "active_models": active_models,
            "running_jobs": running_jobs,
            "active_section": "ml",
        },
    )


@router.post("/api/trigger-training", response_class=HTMLResponse)
async def api_trigger_training(
    request: Request,
    background_tasks: BackgroundTasks,
    key: Optional[str] = Query(None),
):
    """Trigger ML model training via HTMX with full TrainingConfig support."""
    model_type = "xgboost"
    lookback_days = 365
    prediction_window = 7
    num_classes = 5
    enable_sector = True
    enable_market_regime = True
    enable_sentiment = False

    if not key:
        try:
            form_data = await request.form()
            key = form_data.get("key")
            model_type = form_data.get("model_type", "xgboost")
            lookback_days = int(form_data.get("lookback_days", 365))
            prediction_window = int(form_data.get("prediction_window", 7))
            num_classes = int(form_data.get("num_classes", 5))
            enable_sector = form_data.get("enable_sector", "on") == "on"
            enable_market_regime = form_data.get("enable_market_regime", "on") == "on"
            enable_sentiment = form_data.get("enable_sentiment") == "on"
        except Exception:
            pass

    from app.middleware.auth import validate_api_key
    if not key or not validate_api_key(key, require_admin=True):
        return HTMLResponse('<div class="text-red-600 p-3">Invalid API key</div>', status_code=401)

    try:
        from app.services.feature_pipeline import create_training_job, run_training_job_in_background
        from app.models.training_config import TrainingConfig, FeatureToggles

        config = TrainingConfig(
            lookback_days=lookback_days,
            model_type=model_type,
            prediction_window_days=prediction_window,
            num_classes=num_classes,
            features=FeatureToggles(
                enable_sector=enable_sector,
                enable_market_regime=enable_market_regime,
                enable_sentiment=enable_sentiment,
            ),
            triggered_by="admin_dashboard",
        )

        job = create_training_job(config=config)
        background_tasks.add_task(run_training_job_in_background, job)
        desc = f"{model_type}, {num_classes}-class, {prediction_window}d window"
        return HTMLResponse(
            f'<div class="bg-green-100 text-green-800 p-3 rounded">'
            f'Training started ({desc}). Job: <code class="text-xs">{job.job_id}</code>'
            f' <a href="/admin/ml?key={key}" class="underline">Refresh page</a></div>'
        )
    except Exception as e:
        logger.exception("Training trigger failed")
        return HTMLResponse(f'<div class="text-red-600 p-3">Training failed: {str(e)}</div>', status_code=500)


@router.get("/ml/{model_id}", response_class=HTMLResponse)
async def admin_ml_detail(
    request: Request,
    model_id: str,
    api_key: str = Depends(require_admin_for_dashboard),
):
    """Detail view for a single ML model - view metrics, edit metadata, delete."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    try:
        resp = (
            supabase.table("ml_models")
            .select("*")
            .eq("id", model_id)
            .single()
            .execute()
        )
        model = resp.data
    except Exception as e:
        logger.error(f"Failed to fetch model {model_id}: {e}")
        raise HTTPException(status_code=404, detail="Model not found")

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Get training jobs linked to this model
    jobs = []
    try:
        resp = (
            supabase.table("ml_training_jobs")
            .select("*")
            .eq("model_id", model_id)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        jobs = resp.data or []
    except Exception as e:
        logger.error(f"Failed to fetch training jobs for model {model_id}: {e}")

    # Get prediction count from cache
    prediction_count = 0
    try:
        resp = (
            supabase.table("ml_predictions_cache")
            .select("id", count="exact")
            .eq("model_id", model_id)
            .execute()
        )
        prediction_count = resp.count if resp.count is not None else 0
    except Exception:
        pass

    return templates.TemplateResponse(
        "admin/ml_model_detail.html",
        {
            "request": request,
            "api_key": api_key,
            "model": model,
            "jobs": jobs,
            "prediction_count": prediction_count,
            "active_section": "ml",
        },
    )


@router.post("/api/update-model", response_class=HTMLResponse)
async def api_update_model(
    request: Request,
    key: Optional[str] = Query(None),
):
    """Update ML model metadata via HTMX."""
    model_id = None
    updates = {}
    if not key:
        try:
            form_data = await request.form()
            key = form_data.get("key")
            model_id = form_data.get("model_id")
            # Collect editable fields
            for field in ("model_name", "model_version", "status"):
                val = form_data.get(field)
                if val is not None and val != "":
                    updates[field] = val
        except Exception:
            pass

    from app.middleware.auth import validate_api_key
    if not key or not validate_api_key(key, require_admin=True):
        return HTMLResponse('<div class="text-red-600 p-3">Invalid API key</div>', status_code=401)

    if not model_id:
        return HTMLResponse('<div class="text-red-600 p-3">Model ID required</div>', status_code=400)

    if not updates:
        return HTMLResponse('<div class="text-yellow-600 p-3">No changes provided</div>', status_code=400)

    # Validate status value
    valid_statuses = ("pending", "training", "active", "archived", "failed")
    if "status" in updates and updates["status"] not in valid_statuses:
        return HTMLResponse(
            f'<div class="text-red-600 p-3">Invalid status. Must be one of: {", ".join(valid_statuses)}</div>',
            status_code=400,
        )

    supabase = get_supabase()
    if not supabase:
        return HTMLResponse('<div class="text-red-600 p-3">Database error</div>', status_code=500)

    try:
        # If activating, deactivate others first
        if updates.get("status") == "active":
            supabase.table("ml_models").update({"status": "archived"}).eq("status", "active").execute()

        supabase.table("ml_models").update(updates).eq("id", model_id).execute()
        updated_fields = ", ".join(f"{k}={v}" for k, v in updates.items())
        return HTMLResponse(
            f'<div class="bg-green-100 text-green-800 p-3 rounded">'
            f'Model updated: {updated_fields}.'
            f' <a href="/admin/ml/{model_id}?key={key}" class="underline">Refresh</a></div>'
        )
    except Exception as e:
        logger.exception("Model update failed")
        return HTMLResponse(f'<div class="text-red-600 p-3">Update failed: {str(e)}</div>', status_code=500)


@router.post("/api/delete-model", response_class=HTMLResponse)
async def api_delete_model(
    request: Request,
    key: Optional[str] = Query(None),
):
    """Delete an ML model via HTMX."""
    model_id = None
    if not key:
        try:
            form_data = await request.form()
            key = form_data.get("key")
            model_id = form_data.get("model_id")
        except Exception:
            pass

    from app.middleware.auth import validate_api_key
    if not key or not validate_api_key(key, require_admin=True):
        return HTMLResponse('<div class="text-red-600 p-3">Invalid API key</div>', status_code=401)

    if not model_id:
        return HTMLResponse('<div class="text-red-600 p-3">Model ID required</div>', status_code=400)

    supabase = get_supabase()
    if not supabase:
        return HTMLResponse('<div class="text-red-600 p-3">Database error</div>', status_code=500)

    try:
        # Check the model exists and isn't active
        resp = supabase.table("ml_models").select("id,status").eq("id", model_id).single().execute()
        model = resp.data
        if not model:
            return HTMLResponse('<div class="text-red-600 p-3">Model not found</div>', status_code=404)
        if model.get("status") == "active":
            return HTMLResponse(
                '<div class="text-red-600 p-3">Cannot delete the active model. Activate another model first.</div>',
                status_code=400,
            )

        # Delete associated predictions cache
        supabase.table("ml_predictions_cache").delete().eq("model_id", model_id).execute()
        # Delete the model
        supabase.table("ml_models").delete().eq("id", model_id).execute()

        return HTMLResponse(
            f'<div class="bg-green-100 text-green-800 p-3 rounded">'
            f'Model deleted. <a href="/admin/ml?key={key}" class="underline">Back to models</a></div>'
        )
    except Exception as e:
        logger.exception("Model deletion failed")
        return HTMLResponse(f'<div class="text-red-600 p-3">Delete failed: {str(e)}</div>', status_code=500)


@router.post("/api/activate-model", response_class=HTMLResponse)
async def api_activate_model(
    request: Request,
    key: Optional[str] = Query(None),
):
    """Activate an ML model via HTMX."""
    model_id = None
    if not key:
        try:
            form_data = await request.form()
            key = form_data.get("key")
            model_id = form_data.get("model_id")
        except Exception:
            pass

    from app.middleware.auth import validate_api_key
    if not key or not validate_api_key(key, require_admin=True):
        return HTMLResponse('<div class="text-red-600 p-3">Invalid API key</div>', status_code=401)

    if not model_id:
        return HTMLResponse('<div class="text-red-600 p-3">Model ID required</div>', status_code=400)

    supabase = get_supabase()
    if not supabase:
        return HTMLResponse('<div class="text-red-600 p-3">Database error</div>', status_code=500)

    try:
        # Deactivate current active models
        supabase.table("ml_models").update({"status": "inactive"}).eq("status", "active").execute()
        # Activate the selected model
        supabase.table("ml_models").update({"status": "active"}).eq("id", model_id).execute()
        return HTMLResponse(
            f'<div class="bg-green-100 text-green-800 p-3 rounded">'
            f'Model activated. <a href="/admin/ml?key={key}" class="underline">Refresh page</a></div>'
        )
    except Exception as e:
        logger.exception("Model activation failed")
        return HTMLResponse(f'<div class="text-red-600 p-3">Activation failed: {str(e)}</div>', status_code=500)


# ============================================================================
# Data Quality Page
# ============================================================================


@router.get("/quality", response_class=HTMLResponse)
async def admin_quality(
    request: Request,
    api_key: str = Depends(require_admin_for_dashboard),
):
    """Data quality monitoring - ticker validation, freshness, source audit."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    stats = {}

    # Get freshness info using server-side counting
    try:
        cutoff_7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

        # Total records
        resp = supabase.table("trading_disclosures").select("id", count="exact").execute()
        stats["total_records"] = resp.count if resp.count is not None else 0

        # Records in last 7 days
        resp = supabase.table("trading_disclosures").select("id", count="exact").gte("created_at", cutoff_7d).execute()
        stats["records_7d"] = resp.count if resp.count is not None else 0

        # Records in last 24h
        resp = supabase.table("trading_disclosures").select("id", count="exact").gte("created_at", cutoff_24h).execute()
        stats["records_24h"] = resp.count if resp.count is not None else 0

        # Find most recent record
        resp = supabase.table("trading_disclosures").select("created_at").order("created_at", desc=True).limit(1).execute()
        if resp.data:
            stats["newest_record"] = resp.data[0].get("created_at", "N/A")
        else:
            stats["newest_record"] = "N/A"
    except Exception as e:
        logger.error(f"Failed to get quality stats: {e}")
        stats = {"total_records": 0, "records_7d": 0, "records_24h": 0, "newest_record": "N/A"}

    # Validation results summary using server-side counting
    try:
        resp = supabase.table("trade_validation_results").select("id", count="exact").execute()
        stats["validation_total"] = resp.count if resp.count is not None else 0
        resp = supabase.table("trade_validation_results").select("id", count="exact").eq("validation_status", "match").execute()
        stats["validation_match"] = resp.count if resp.count is not None else 0
        resp = supabase.table("trade_validation_results").select("id", count="exact").eq("validation_status", "mismatch").execute()
        stats["validation_mismatch"] = resp.count if resp.count is not None else 0
    except Exception:
        stats["validation_total"] = 0
        stats["validation_match"] = 0
        stats["validation_mismatch"] = 0

    return templates.TemplateResponse(
        "admin/data_quality.html",
        {
            "request": request,
            "api_key": api_key,
            "stats": stats,
            "active_section": "quality",
        },
    )


@router.post("/api/validate-tickers", response_class=HTMLResponse)
async def api_validate_tickers_html(
    request: Request,
    key: Optional[str] = Query(None),
):
    """Run ticker validation and return HTML results."""
    if not key:
        try:
            form_data = await request.form()
            key = form_data.get("key")
        except Exception:
            pass

    from app.middleware.auth import validate_api_key
    if not key or not validate_api_key(key, require_admin=True):
        return HTMLResponse('<div class="text-red-600 p-3">Invalid API key</div>', status_code=401)

    try:
        from app.routes.quality import validate_tickers, TickerValidationRequest
        req = TickerValidationRequest(days_back=30, limit=200)
        result = await validate_tickers(req)

        invalid_count = len(result.invalid_tickers)
        low_conf_count = len(result.low_confidence)

        html = f'''
        <div class="bg-white rounded p-4">
            <div class="grid grid-cols-3 gap-4 mb-4">
                <div class="text-center p-3 bg-gray-50 rounded">
                    <div class="text-xl font-bold">{result.total_checked}</div>
                    <div class="text-xs text-gray-500">Checked</div>
                </div>
                <div class="text-center p-3 bg-red-50 rounded">
                    <div class="text-xl font-bold text-red-600">{invalid_count}</div>
                    <div class="text-xs text-gray-500">Invalid</div>
                </div>
                <div class="text-center p-3 bg-yellow-50 rounded">
                    <div class="text-xl font-bold text-yellow-600">{low_conf_count}</div>
                    <div class="text-xs text-gray-500">Low Confidence</div>
                </div>
            </div>
            <p class="text-xs text-gray-500">Completed in {result.validation_time_ms}ms</p>
        '''

        if result.invalid_tickers:
            html += '<h4 class="font-medium mt-3 mb-2 text-red-700">Invalid Tickers</h4>'
            html += '<div class="border rounded overflow-hidden"><table class="w-full text-sm">'
            html += '<thead class="bg-gray-50"><tr><th class="px-3 py-2 text-left">Ticker</th><th class="px-3 py-2 text-left">Reason</th></tr></thead><tbody>'
            for t in result.invalid_tickers[:20]:
                html += f'<tr class="border-t"><td class="px-3 py-2 font-mono">{t.get("ticker", "?")}</td><td class="px-3 py-2 text-red-600">{t.get("reason", "?")}</td></tr>'
            html += '</tbody></table></div>'

        if result.low_confidence:
            html += '<h4 class="font-medium mt-3 mb-2 text-yellow-700">Low Confidence</h4>'
            html += '<div class="border rounded overflow-hidden"><table class="w-full text-sm">'
            html += '<thead class="bg-gray-50"><tr><th class="px-3 py-2 text-left">Ticker</th><th class="px-3 py-2 text-left">Reason</th><th class="px-3 py-2 text-right">Confidence</th></tr></thead><tbody>'
            for t in result.low_confidence[:20]:
                conf = int(t.get("confidence", 0) * 100)
                html += f'<tr class="border-t"><td class="px-3 py-2 font-mono">{t.get("ticker", "?")}</td><td class="px-3 py-2">{t.get("reason", "?")}</td><td class="px-3 py-2 text-right">{conf}%</td></tr>'
            html += '</tbody></table></div>'

        html += '</div>'
        return HTMLResponse(html)
    except Exception as e:
        logger.exception("Ticker validation failed")
        return HTMLResponse(f'<div class="text-red-600 p-3">Validation failed: {str(e)}</div>', status_code=500)


# ============================================================================
# Enrichment Page
# ============================================================================


@router.get("/enrichment", response_class=HTMLResponse)
async def admin_enrichment(
    request: Request,
    api_key: str = Depends(require_admin_for_dashboard),
):
    """Enrichment job management - party, name, bioguide enrichment."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    stats = {}
    try:
        # Politicians with/without party
        resp = supabase.table("politicians").select("id,party,bioguide_id").execute()
        politicians = resp.data or []
        stats["total_politicians"] = len(politicians)
        stats["with_party"] = sum(1 for p in politicians if p.get("party"))
        stats["without_party"] = stats["total_politicians"] - stats["with_party"]
        stats["with_bioguide"] = sum(1 for p in politicians if p.get("bioguide_id"))
        stats["without_bioguide"] = stats["total_politicians"] - stats["with_bioguide"]
    except Exception as e:
        logger.error(f"Failed to get enrichment stats: {e}")
        stats = {
            "total_politicians": 0, "with_party": 0, "without_party": 0,
            "with_bioguide": 0, "without_bioguide": 0,
        }

    return templates.TemplateResponse(
        "admin/enrichment.html",
        {
            "request": request,
            "api_key": api_key,
            "stats": stats,
            "active_section": "enrichment",
        },
    )


@router.post("/api/trigger-enrichment", response_class=HTMLResponse)
async def api_trigger_enrichment(
    request: Request,
    background_tasks: BackgroundTasks,
    key: Optional[str] = Query(None),
):
    """Trigger enrichment via HTMX."""
    enrichment_type = "party"
    limit = 50
    if not key:
        try:
            form_data = await request.form()
            key = form_data.get("key")
            enrichment_type = form_data.get("type", "party")
            limit = int(form_data.get("limit", 50))
        except Exception:
            pass

    from app.middleware.auth import validate_api_key
    if not key or not validate_api_key(key, require_admin=True):
        return HTMLResponse('<div class="text-red-600 p-3">Invalid API key</div>', status_code=401)

    try:
        if enrichment_type == "party":
            from app.services.party_enrichment import create_job, run_job_in_background
            job = create_job(limit=limit)
            background_tasks.add_task(run_job_in_background, job["id"])
            return HTMLResponse(
                f'<div class="bg-green-100 text-green-800 p-3 rounded">'
                f'Party enrichment started (limit: {limit}). Job: <code class="text-xs">{job["id"][:8]}...</code></div>'
            )
        elif enrichment_type == "name":
            from app.services.name_enrichment import create_name_job, run_name_job_in_background
            job = create_name_job(limit=limit)
            background_tasks.add_task(run_name_job_in_background, job["id"])
            return HTMLResponse(
                f'<div class="bg-green-100 text-green-800 p-3 rounded">'
                f'Name enrichment started (limit: {limit}). Job: <code class="text-xs">{job["id"][:8]}...</code></div>'
            )
        elif enrichment_type == "bioguide":
            from app.services.bioguide_enrichment import run_bioguide_enrichment
            background_tasks.add_task(run_bioguide_enrichment, limit)
            return HTMLResponse(
                f'<div class="bg-green-100 text-green-800 p-3 rounded">'
                f'BioGuide enrichment started (limit: {limit}).</div>'
            )
        else:
            return HTMLResponse(f'<div class="text-red-600 p-3">Unknown type: {enrichment_type}</div>')
    except Exception as e:
        logger.exception("Enrichment trigger failed")
        return HTMLResponse(f'<div class="text-red-600 p-3">Enrichment failed: {str(e)}</div>', status_code=500)


# ============================================================================
# Error Reports Page
# ============================================================================


@router.get("/errors", response_class=HTMLResponse)
async def admin_errors(
    request: Request,
    api_key: str = Depends(require_admin_for_dashboard),
):
    """Error report management - view and process user reports."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    reports = []
    stats = {}
    try:
        resp = (
            supabase.table("user_error_reports")
            .select("*")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        reports = resp.data or []
        stats["total"] = len(reports)
        stats["pending"] = sum(1 for r in reports if r.get("status") in ("pending", "open"))
        stats["fixed"] = sum(1 for r in reports if r.get("status") == "fixed")
        stats["reviewed"] = sum(1 for r in reports if r.get("status") == "reviewed")
    except Exception as e:
        logger.error(f"Failed to fetch error reports: {e}")
        stats = {"total": 0, "pending": 0, "fixed": 0, "reviewed": 0}

    return templates.TemplateResponse(
        "admin/error_reports.html",
        {
            "request": request,
            "api_key": api_key,
            "reports": reports,
            "stats": stats,
            "active_section": "errors",
        },
    )


@router.post("/api/process-reports", response_class=HTMLResponse)
async def api_process_reports(
    request: Request,
    background_tasks: BackgroundTasks,
    key: Optional[str] = Query(None),
):
    """Process error reports via HTMX."""
    limit = 10
    if not key:
        try:
            form_data = await request.form()
            key = form_data.get("key")
            limit = int(form_data.get("limit", 10))
        except Exception:
            pass

    from app.middleware.auth import validate_api_key
    if not key or not validate_api_key(key, require_admin=True):
        return HTMLResponse('<div class="text-red-600 p-3">Invalid API key</div>', status_code=401)

    try:
        from app.services.error_report_processor import ErrorReportProcessor
        processor = ErrorReportProcessor()
        result = await processor.process_batch(limit=limit)
        processed = result.get("processed", 0)
        fixed = result.get("fixed", 0)
        needs_review = result.get("needs_review", 0)
        return HTMLResponse(
            f'<div class="bg-green-100 text-green-800 p-3 rounded">'
            f'Processed {processed} reports: {fixed} auto-fixed, {needs_review} need review.'
            f' <a href="/admin/errors?key={key}" class="underline">Refresh</a></div>'
        )
    except Exception as e:
        logger.exception("Report processing failed")
        return HTMLResponse(f'<div class="text-red-600 p-3">Processing failed: {str(e)}</div>', status_code=500)


@router.post("/api/resolve-report", response_class=HTMLResponse)
async def api_resolve_report(
    request: Request,
    key: Optional[str] = Query(None),
):
    """Resolve a single error report."""
    report_id = None
    resolution = "reviewed"
    if not key:
        try:
            form_data = await request.form()
            key = form_data.get("key")
            report_id = form_data.get("report_id")
            resolution = form_data.get("resolution", "reviewed")
        except Exception:
            pass

    from app.middleware.auth import validate_api_key
    if not key or not validate_api_key(key, require_admin=True):
        return HTMLResponse('<div class="text-red-600 p-3">Invalid API key</div>', status_code=401)

    if not report_id:
        return HTMLResponse('<div class="text-red-600 p-3">Report ID required</div>', status_code=400)

    supabase = get_supabase()
    if not supabase:
        return HTMLResponse('<div class="text-red-600 p-3">Database error</div>', status_code=500)

    try:
        supabase.table("user_error_reports").update({
            "status": resolution,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", report_id).execute()
        return HTMLResponse(
            f'<div class="bg-green-100 text-green-800 p-3 rounded">Report marked as {resolution}.</div>'
        )
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-600 p-3">Failed: {str(e)}</div>', status_code=500)


# ============================================================================
# Audit Log Page
# ============================================================================


@router.get("/audit-log", response_class=HTMLResponse)
async def admin_audit_log(
    request: Request,
    api_key: str = Depends(require_admin_for_dashboard),
):
    """Unified audit log - validation fixes, model changes, ETL events."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    fix_log = []
    try:
        resp = (
            supabase.table("validation_fix_log")
            .select("*")
            .order("performed_at", desc=True)
            .limit(100)
            .execute()
        )
        fix_log = resp.data or []
    except Exception as e:
        logger.error(f"Failed to fetch fix log: {e}")

    return templates.TemplateResponse(
        "admin/audit_log.html",
        {
            "request": request,
            "api_key": api_key,
            "fix_log": fix_log,
            "active_section": "audit",
        },
    )
