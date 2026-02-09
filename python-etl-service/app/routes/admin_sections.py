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
        resp = supabase.table("trade_validation_results").select("id,validation_status").execute()
        results = resp.data or []
        stats["total_validations"] = len(results)
        stats["validation_mismatches"] = sum(
            1 for r in results if r.get("validation_status") == "mismatch"
        )
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

    # Get recent disclosures stats
    stats = {}
    try:
        # House disclosures count
        resp = (
            supabase.table("trading_disclosures")
            .select("id,chamber,created_at", count="exact")
            .execute()
        )
        all_disclosures = resp.data or []
        stats["house_count"] = sum(
            1 for d in all_disclosures if d.get("chamber", "").lower() == "house"
        )
        stats["senate_count"] = sum(
            1 for d in all_disclosures if d.get("chamber", "").lower() == "senate"
        )
        stats["total_count"] = len(all_disclosures)

        # Recent (last 24h)
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        stats["recent_24h"] = sum(
            1 for d in all_disclosures
            if d.get("created_at", "") >= cutoff
        )
    except Exception as e:
        logger.error(f"Failed to get ETL stats: {e}")
        stats = {"house_count": 0, "senate_count": 0, "total_count": 0, "recent_24h": 0}

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
    """Trigger ML model training via HTMX."""
    model_type = "xgboost"
    if not key:
        try:
            form_data = await request.form()
            key = form_data.get("key")
            model_type = form_data.get("model_type", "xgboost")
        except Exception:
            pass

    from app.middleware.auth import validate_api_key
    if not key or not validate_api_key(key, require_admin=True):
        return HTMLResponse('<div class="text-red-600 p-3">Invalid API key</div>', status_code=401)

    try:
        from app.services.feature_pipeline import create_training_job, run_training_job_in_background
        job = await create_training_job(
            model_type=model_type,
            lookback_days=365,
            triggered_by="admin_dashboard",
        )
        background_tasks.add_task(run_training_job_in_background, job["id"])
        return HTMLResponse(
            f'<div class="bg-green-100 text-green-800 p-3 rounded">'
            f'Training started ({model_type}). Job: <code class="text-xs">{job["id"][:8]}...</code>'
            f' <a href="/admin/ml?key={key}" class="underline">Refresh page</a></div>'
        )
    except Exception as e:
        logger.exception("Training trigger failed")
        return HTMLResponse(f'<div class="text-red-600 p-3">Training failed: {str(e)}</div>', status_code=500)


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

    # Get freshness info
    try:
        cutoff_7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

        resp = supabase.table("trading_disclosures").select("created_at,chamber").execute()
        all_records = resp.data or []

        stats["total_records"] = len(all_records)
        stats["records_7d"] = sum(1 for r in all_records if r.get("created_at", "") >= cutoff_7d)
        stats["records_24h"] = sum(1 for r in all_records if r.get("created_at", "") >= cutoff_24h)

        # Find most recent record
        if all_records:
            dates = [r.get("created_at", "") for r in all_records if r.get("created_at")]
            stats["newest_record"] = max(dates) if dates else "N/A"
        else:
            stats["newest_record"] = "N/A"
    except Exception as e:
        logger.error(f"Failed to get quality stats: {e}")
        stats = {"total_records": 0, "records_7d": 0, "records_24h": 0, "newest_record": "N/A"}

    # Validation results summary
    try:
        resp = supabase.table("trade_validation_results").select("validation_status").execute()
        validations = resp.data or []
        stats["validation_total"] = len(validations)
        stats["validation_match"] = sum(1 for v in validations if v.get("validation_status") == "match")
        stats["validation_mismatch"] = sum(1 for v in validations if v.get("validation_status") == "mismatch")
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
