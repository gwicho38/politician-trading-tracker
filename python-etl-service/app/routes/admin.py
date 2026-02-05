"""
Admin Dashboard Routes

Server-rendered admin interface for QuiverQuant validation management.
Uses Jinja2 templates with HTMX for interactivity.

Authentication: Requires ETL_ADMIN_API_KEY via query param or header.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.lib.database import get_supabase
from app.middleware.auth import get_api_key, validate_api_key

logger = logging.getLogger(__name__)

router = APIRouter()

# Set up Jinja2 templates
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


async def require_admin_for_dashboard(
    request: Request,
    key: Optional[str] = Query(None, alias="key"),
) -> str:
    """
    Check admin API key for dashboard access.
    Accepts key via query param (for browser URLs) or header.
    """
    # Try query param first (for browser navigation)
    api_key = key

    # Fall back to header
    if not api_key:
        api_key = await get_api_key(
            request.headers.get("X-API-Key"),
            request.headers.get("Authorization"),
            None,
        )

    if not api_key or not validate_api_key(api_key, require_admin=True):
        raise HTTPException(
            status_code=401,
            detail="Admin API key required. Add ?key=YOUR_ADMIN_KEY to URL.",
        )

    return api_key


# ============================================================================
# Dashboard Pages (HTML)
# ============================================================================


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    api_key: str = Depends(require_admin_for_dashboard),
):
    """
    Main admin dashboard showing validation overview.
    """
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    # Get validation stats
    stats = await get_validation_stats(supabase)

    # Get recent validation results (first page, unresolved by default)
    results = await get_validation_results(
        supabase,
        page=1,
        status=None,
        severity=None,
        resolved=False,
        search=None,
        root_cause=None,
    )

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "api_key": api_key,
            "stats": stats,
            "results": results,
            "filters": {"resolved": "false"},
            "page": 1,
        },
    )


@router.get("/detail/{result_id}", response_class=HTMLResponse)
async def admin_detail(
    request: Request,
    result_id: str,
    api_key: str = Depends(require_admin_for_dashboard),
):
    """
    Detail view for a single validation result.
    Shows side-by-side comparison and fix options.
    """
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")

    # Get the validation result
    try:
        response = (
            supabase.table("trade_validation_results")
            .select("*")
            .eq("id", result_id)
            .single()
            .execute()
        )
        result = response.data
    except Exception as e:
        logger.error(f"Failed to fetch validation result: {e}")
        raise HTTPException(status_code=404, detail="Validation result not found")

    if not result:
        raise HTTPException(status_code=404, detail="Validation result not found")

    # Build comparison fields
    comparison_fields = build_comparison_fields(result)

    # Get fix history
    fix_history = await get_fix_history(supabase, result_id)

    return templates.TemplateResponse(
        "admin/detail.html",
        {
            "request": request,
            "api_key": api_key,
            "result": result,
            "comparison_fields": comparison_fields,
            "fix_history": fix_history,
        },
    )


# ============================================================================
# API Endpoints (JSON/HTML partials for HTMX)
# ============================================================================


@router.get("/api/results", response_class=HTMLResponse)
async def api_get_results(
    request: Request,
    key: str = Query(...),
    page: int = Query(1, ge=1),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    resolved: Optional[str] = Query("false"),
    search: Optional[str] = Query(None),
    root_cause: Optional[str] = Query(None),
):
    """
    Get filtered validation results as HTML partial (for HTMX).
    """
    if not validate_api_key(key, require_admin=True):
        return HTMLResponse(
            '<div class="text-red-600 p-4">Invalid API key</div>',
            status_code=401,
        )

    supabase = get_supabase()
    if not supabase:
        return HTMLResponse(
            '<div class="text-red-600 p-4">Database error</div>',
            status_code=500,
        )

    # Parse resolved filter
    resolved_bool = None
    if resolved == "true":
        resolved_bool = True
    elif resolved == "false":
        resolved_bool = False

    results = await get_validation_results(
        supabase,
        page=page,
        status=status if status else None,
        severity=severity if severity else None,
        resolved=resolved_bool,
        search=search if search else None,
        root_cause=root_cause if root_cause else None,
    )

    return templates.TemplateResponse(
        "admin/partials/results_table.html",
        {
            "request": request,
            "api_key": key,
            "results": results,
            "page": page,
        },
    )


@router.post("/api/audit", response_class=HTMLResponse)
async def api_run_audit(
    request: Request,
    key: Optional[str] = Query(None),
    limit: int = Query(100, ge=10, le=1000),
):
    """
    Trigger a validation audit and return results as HTML partial.

    Accepts key from either query param or form body (for HTMX compatibility).
    """
    # HTMX sends hx-vals in body as form-urlencoded
    if not key:
        try:
            form_data = await request.form()
            key = form_data.get("key")
            limit_str = form_data.get("limit")
            if limit_str:
                limit = int(limit_str)
            logger.info(f"Parsed form data: key={key[:10] if key else None}..., limit={limit}")
        except Exception as e:
            logger.warning(f"Failed to parse form data: {e}")
            # Try JSON body as fallback
            try:
                body = await request.json()
                key = body.get("key")
                limit = body.get("limit", limit)
                logger.info(f"Parsed JSON body: key={key[:10] if key else None}...")
            except Exception as e2:
                logger.warning(f"Failed to parse JSON body: {e2}")

    if not key or not validate_api_key(key, require_admin=True):
        logger.warning(f"Auth failed: key={'present' if key else 'missing'}")
        return HTMLResponse(
            '<div class="text-red-600 p-4">Invalid API key</div>',
            status_code=401,
        )

    supabase = get_supabase()
    if not supabase:
        return HTMLResponse(
            '<div class="text-red-600 p-4">Database error</div>',
            status_code=500,
        )

    # Import and run the validation audit
    try:
        from app.services.quiver_validation import QuiverValidationService

        service = QuiverValidationService()
        audit_results = await service.run_audit(limit=limit)

        # Refresh the results view
        results = await get_validation_results(
            supabase,
            page=1,
            status=None,
            severity=None,
            resolved=False,
            search=None,
            root_cause=None,
        )

        return templates.TemplateResponse(
            "admin/partials/results_table.html",
            {
                "request": request,
                "api_key": key,
                "results": results,
                "page": 1,
                "audit_message": f"Audit complete: {audit_results.get('validated', 0)} trades validated",
            },
        )
    except ImportError:
        return HTMLResponse(
            '<div class="text-yellow-600 p-4">Validation service not available. Run CLI: mcli run etl quiver audit</div>',
            status_code=200,
        )
    except Exception as e:
        logger.exception("Audit failed")
        return HTMLResponse(
            f'<div class="text-red-600 p-4">Audit failed: {str(e)}</div>',
            status_code=500,
        )


@router.post("/api/fix/{result_id}", response_class=HTMLResponse)
async def api_apply_fix(
    request: Request,
    result_id: str,
    key: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    field: Optional[str] = Query(None),
    value: Optional[str] = Query(None),
):
    """
    Apply a fix to a validation result.

    Actions:
    - accept_all_qq: Replace all app values with QuiverQuant values
    - field_update: Update a single field
    - mark_resolved: Mark as resolved without changes
    - delete_trade: Soft-delete the trade

    Accepts params from either query string or form body (for HTMX compatibility).
    """
    # HTMX sends hx-vals in body, so check both query and form
    if not key or not action:
        try:
            form_data = await request.form()
            key = key or form_data.get("key")
            action = action or form_data.get("action")
            field = field or form_data.get("field")
            value = value or form_data.get("value")
        except Exception:
            pass

    if not key or not validate_api_key(key, require_admin=True):
        return HTMLResponse(
            '<div class="text-red-600 p-4">Invalid API key</div>',
            status_code=401,
        )

    if not action:
        return HTMLResponse(
            '<div class="text-red-600 p-4">Action is required</div>',
            status_code=400,
        )

    supabase = get_supabase()
    if not supabase:
        return HTMLResponse(
            '<div class="text-red-600 p-4">Database error</div>',
            status_code=500,
        )

    try:
        # Get the validation result
        result_resp = (
            supabase.table("trade_validation_results")
            .select("*")
            .eq("id", result_id)
            .single()
            .execute()
        )
        result = result_resp.data

        if not result:
            return HTMLResponse(
                '<div class="text-red-600 p-4">Validation result not found</div>',
                status_code=404,
            )

        # Apply the fix based on action type
        if action == "accept_all_qq":
            await apply_accept_all_qq(supabase, result)
            message = "Applied all QuiverQuant values"

        elif action == "field_update":
            if not field or value is None:
                return HTMLResponse(
                    '<div class="text-red-600 p-4">Field and value required</div>',
                    status_code=400,
                )
            await apply_field_update(supabase, result, field, value)
            message = f"Updated {field}"

        elif action == "mark_resolved":
            await mark_resolved(supabase, result_id)
            message = "Marked as resolved"

        elif action == "delete_trade":
            await soft_delete_trade(supabase, result)
            message = "Trade deleted (soft)"

        else:
            return HTMLResponse(
                f'<div class="text-red-600 p-4">Unknown action: {action}</div>',
                status_code=400,
            )

        return HTMLResponse(
            f'<div class="bg-green-100 text-green-800 p-4 rounded">{message}. <a href="/admin/detail/{result_id}?key={key}" class="underline">Refresh page</a></div>',
            status_code=200,
        )

    except Exception as e:
        logger.exception(f"Fix failed: {e}")
        return HTMLResponse(
            f'<div class="text-red-600 p-4">Fix failed: {str(e)}</div>',
            status_code=500,
        )


# ============================================================================
# Helper Functions
# ============================================================================


async def get_validation_stats(supabase) -> dict:
    """Get validation statistics for the dashboard."""
    try:
        # Get counts by status
        response = (
            supabase.table("trade_validation_results")
            .select("validation_status", count="exact")
            .execute()
        )

        total = len(response.data) if response.data else 0

        # Count by status
        match_count = 0
        mismatch_count = 0
        app_only_count = 0
        quiver_only_count = 0

        for row in response.data or []:
            status = row.get("validation_status")
            if status == "match":
                match_count += 1
            elif status == "mismatch":
                mismatch_count += 1
            elif status == "app_only":
                app_only_count += 1
            elif status == "quiver_only":
                quiver_only_count += 1

        return {
            "total": total,
            "match": match_count,
            "mismatch": mismatch_count,
            "app_only": app_only_count,
            "quiver_only": quiver_only_count,
            "match_pct": (match_count / total * 100) if total > 0 else 0,
            "mismatch_pct": (mismatch_count / total * 100) if total > 0 else 0,
        }
    except Exception as e:
        logger.error(f"Failed to get validation stats: {e}")
        return {
            "total": 0,
            "match": 0,
            "mismatch": 0,
            "app_only": 0,
            "quiver_only": 0,
            "match_pct": 0,
            "mismatch_pct": 0,
        }


async def get_validation_results(
    supabase,
    page: int,
    status: Optional[str],
    severity: Optional[str],
    resolved: Optional[bool],
    search: Optional[str],
    root_cause: Optional[str],
    page_size: int = 50,
) -> list:
    """Get paginated validation results with filters."""
    try:
        query = (
            supabase.table("trade_validation_results")
            .select("*")
            .order("created_at", desc=True)
        )

        # Apply filters
        if status:
            query = query.eq("validation_status", status)

        if severity:
            query = query.eq("severity", severity)

        if resolved is not None:
            if resolved:
                query = query.not_.is_("resolved_at", "null")
            else:
                query = query.is_("resolved_at", "null")

        if root_cause:
            query = query.eq("root_cause", root_cause)

        if search:
            # Search in politician name or ticker
            query = query.or_(
                f"politician_name.ilike.%{search}%,ticker.ilike.%{search}%"
            )

        # Pagination
        offset = (page - 1) * page_size
        query = query.range(offset, offset + page_size - 1)

        response = query.execute()
        return response.data or []

    except Exception as e:
        logger.error(f"Failed to get validation results: {e}")
        return []


def build_comparison_fields(result: dict) -> list:
    """Build field-by-field comparison from validation result."""
    app_snapshot = result.get("app_snapshot") or {}
    qq_snapshot = result.get("quiver_snapshot") or {}

    # Handle JSON strings
    if isinstance(app_snapshot, str):
        try:
            app_snapshot = json.loads(app_snapshot)
        except json.JSONDecodeError:
            app_snapshot = {}

    if isinstance(qq_snapshot, str):
        try:
            qq_snapshot = json.loads(qq_snapshot)
        except json.JSONDecodeError:
            qq_snapshot = {}

    fields = [
        ("politician_name", "Politician Name"),
        ("ticker", "Ticker"),
        ("transaction_date", "Transaction Date"),
        ("transaction_type", "Transaction Type"),
        ("amount_range_min", "Amount Min"),
        ("amount_range_max", "Amount Max"),
        ("asset_name", "Asset Name"),
    ]

    comparison = []
    for field_name, label in fields:
        app_value = app_snapshot.get(field_name)
        qq_value = qq_snapshot.get(field_name)

        # Normalize for comparison
        app_str = str(app_value) if app_value is not None else ""
        qq_str = str(qq_value) if qq_value is not None else ""

        differs = app_str.lower().strip() != qq_str.lower().strip()

        comparison.append({
            "name": field_name,
            "label": label,
            "app_value": app_value,
            "qq_value": qq_value,
            "differs": differs,
        })

    return comparison


async def get_fix_history(supabase, result_id: str) -> list:
    """Get fix history for a validation result."""
    try:
        response = (
            supabase.table("validation_fix_log")
            .select("*")
            .eq("validation_result_id", result_id)
            .order("performed_at", desc=True)
            .limit(20)
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get fix history: {e}")
        return []


async def apply_accept_all_qq(supabase, result: dict):
    """Apply all QuiverQuant values to the trading disclosure."""
    qq_snapshot = result.get("quiver_snapshot") or {}
    if isinstance(qq_snapshot, str):
        qq_snapshot = json.loads(qq_snapshot)

    trading_disclosure_id = result.get("trading_disclosure_id")
    if not trading_disclosure_id:
        raise ValueError("No trading disclosure linked to this result")

    # Get current values for audit log
    current = (
        supabase.table("trading_disclosures")
        .select("*")
        .eq("id", trading_disclosure_id)
        .single()
        .execute()
    ).data

    # Build update
    update_fields = {}
    fields_to_update = [
        "politician_name", "asset_ticker", "transaction_date",
        "transaction_type", "amount_range_min", "amount_range_max",
    ]

    for field in fields_to_update:
        qq_field = field.replace("asset_ticker", "ticker")
        if qq_field in qq_snapshot and qq_snapshot[qq_field] is not None:
            update_fields[field] = qq_snapshot[qq_field]

    if update_fields:
        # Update trading disclosure
        supabase.table("trading_disclosures").update(update_fields).eq(
            "id", trading_disclosure_id
        ).execute()

        # Log the fix
        supabase.table("validation_fix_log").insert({
            "validation_result_id": result["id"],
            "trading_disclosure_id": trading_disclosure_id,
            "action_type": "accept_all_qq",
            "old_value": json.dumps({k: current.get(k) for k in update_fields.keys()}),
            "new_value": json.dumps(update_fields),
            "performed_by": "admin",
        }).execute()

    # Mark as resolved
    await mark_resolved(supabase, result["id"])


async def apply_field_update(supabase, result: dict, field: str, value: str):
    """Update a single field in the trading disclosure."""
    trading_disclosure_id = result.get("trading_disclosure_id")
    if not trading_disclosure_id:
        raise ValueError("No trading disclosure linked to this result")

    # Map field names
    db_field = field
    if field == "ticker":
        db_field = "asset_ticker"

    # Get current value
    current = (
        supabase.table("trading_disclosures")
        .select(db_field)
        .eq("id", trading_disclosure_id)
        .single()
        .execute()
    ).data

    old_value = current.get(db_field) if current else None

    # Update
    supabase.table("trading_disclosures").update({
        db_field: value
    }).eq("id", trading_disclosure_id).execute()

    # Log the fix
    supabase.table("validation_fix_log").insert({
        "validation_result_id": result["id"],
        "trading_disclosure_id": trading_disclosure_id,
        "action_type": "field_update",
        "field_changed": db_field,
        "old_value": str(old_value) if old_value is not None else None,
        "new_value": value,
        "performed_by": "admin",
    }).execute()


async def mark_resolved(supabase, result_id: str):
    """Mark a validation result as resolved."""
    supabase.table("trade_validation_results").update({
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", result_id).execute()

    # Log
    supabase.table("validation_fix_log").insert({
        "validation_result_id": result_id,
        "action_type": "mark_resolved",
        "performed_by": "admin",
    }).execute()


async def soft_delete_trade(supabase, result: dict):
    """Soft-delete a trading disclosure."""
    trading_disclosure_id = result.get("trading_disclosure_id")
    if not trading_disclosure_id:
        raise ValueError("No trading disclosure linked to this result")

    # Soft delete
    supabase.table("trading_disclosures").update({
        "deleted_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", trading_disclosure_id).execute()

    # Mark validation result as resolved
    await mark_resolved(supabase, result["id"])

    # Log
    supabase.table("validation_fix_log").insert({
        "validation_result_id": result["id"],
        "trading_disclosure_id": trading_disclosure_id,
        "action_type": "delete_trade",
        "performed_by": "admin",
    }).execute()
