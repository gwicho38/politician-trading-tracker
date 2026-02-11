"""
Data Quality Routes

Endpoints for validating data quality:
- /quality/validate-tickers - Check tickers against exchange data
- /quality/audit-sources - Re-fetch and compare sample records
- /quality/freshness-report - Get sync status per source
"""

import os
import random
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from app.lib.database import get_supabase
from app.services.politician_normalizer import PoliticianNormalizer

router = APIRouter()


def get_polygon_api_key() -> str:
    """Get Polygon API key."""
    return os.getenv("POLYGON_API_KEY", "")


# ============================================================================
# Request/Response Models
# ============================================================================


class TickerValidationRequest(BaseModel):
    """Request for ticker validation."""

    days_back: int = Field(default=7, ge=1, le=90)
    confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    limit: int = Field(default=100, ge=1, le=1000)


class TickerValidationResponse(BaseModel):
    """Response from ticker validation."""

    invalid_tickers: list
    low_confidence: list
    total_checked: int
    validation_time_ms: int


class AuditSourceRequest(BaseModel):
    """Request for source audit."""

    sample_size: int = Field(default=50, ge=10, le=200)
    source: Optional[str] = Field(default=None)
    days_back: int = Field(default=30, ge=1, le=365)


class AuditSourceResponse(BaseModel):
    """Response from source audit."""

    records_sampled: int
    mismatches_found: int
    accuracy_rate: float
    mismatches: list
    audit_time_ms: int


class FreshnessReport(BaseModel):
    """Freshness report response."""

    sources: list
    overall_health: str
    last_updated: str


class NormalizePoliticiansRequest(BaseModel):
    """Request for politician normalization."""

    dry_run: bool = Field(default=True, description="Preview changes without applying")
    limit: int = Field(default=500, ge=1, le=5000)
    steps: list = Field(
        default=["roles", "names", "state_backfill"],
        description="Which normalization steps to run",
    )


# ============================================================================
# Ticker Validation
# ============================================================================

# Known ticker mappings for common rebrands/splits
TICKER_MAPPINGS = {
    "FB": "META",
    "TWTR": "X",
    "GOOGL": "GOOG",  # Both valid, but normalize
}

# Common invalid patterns
INVALID_TICKER_PATTERNS = [
    "N/A",
    "NA",
    "NONE",
    "--",
    "UNKNOWN",
    "TBD",
    "VARIOUS",
    "MULTIPLE",
]


@router.post("/validate-tickers", response_model=TickerValidationResponse)
async def validate_tickers(request: TickerValidationRequest):
    """
    Validate tickers against known patterns and optionally Polygon.io.

    Checks:
    - Known invalid patterns (N/A, --, etc.)
    - Ticker format validation (1-5 uppercase letters)
    - Known rebrands/mappings
    - Optional: Polygon.io exchange validation
    """
    import time

    start_time = time.time()

    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    # Get recent tickers from disclosures
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=request.days_back)).isoformat()

    try:
        response = (
            supabase.table("trading_disclosures")
            .select("asset_ticker")
            .gte("created_at", cutoff_date)
            .not_.is_("asset_ticker", "null")
            .limit(request.limit * 10)  # Get more, then dedupe
            .execute()
        )

        # Get unique tickers
        tickers = list(
            set(
                r["asset_ticker"].upper().strip()
                for r in response.data
                if r.get("asset_ticker")
            )
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tickers: {e}")

    invalid_tickers = []
    low_confidence = []

    for ticker in tickers[: request.limit]:
        # Check invalid patterns
        if ticker in INVALID_TICKER_PATTERNS or not ticker:
            invalid_tickers.append(
                {"ticker": ticker, "reason": "Invalid pattern", "affected_count": 1}
            )
            continue

        # Check format (1-5 uppercase letters, optionally with numbers for some ETFs)
        import re

        if not re.match(r"^[A-Z]{1,5}$", ticker) and not re.match(
            r"^[A-Z]{2,4}[0-9]{1,2}$", ticker
        ):
            # Could be valid (like BRK.A) but flag as low confidence
            low_confidence.append(
                {"ticker": ticker, "confidence": 0.5, "reason": "Unusual format"}
            )
            continue

        # Check known mappings
        if ticker in TICKER_MAPPINGS:
            low_confidence.append(
                {
                    "ticker": ticker,
                    "confidence": 0.7,
                    "reason": f"Outdated ticker, now {TICKER_MAPPINGS[ticker]}",
                }
            )
            continue

        # Optional Polygon.io validation
        polygon_key = get_polygon_api_key()
        if polygon_key:
            is_valid, confidence = await validate_ticker_polygon(ticker)
            if not is_valid:
                invalid_tickers.append(
                    {"ticker": ticker, "reason": "Not found on exchange"}
                )
            elif confidence < request.confidence_threshold:
                low_confidence.append(
                    {
                        "ticker": ticker,
                        "confidence": confidence,
                        "reason": "Low exchange confidence",
                    }
                )

    elapsed_ms = int((time.time() - start_time) * 1000)

    return TickerValidationResponse(
        invalid_tickers=invalid_tickers,
        low_confidence=low_confidence,
        total_checked=len(tickers),
        validation_time_ms=elapsed_ms,
    )


async def validate_ticker_polygon(ticker: str) -> tuple[bool, float]:
    """
    Validate ticker against Polygon.io API.

    Returns (is_valid, confidence_score).
    """
    import httpx

    polygon_key = get_polygon_api_key()
    if not polygon_key:
        return True, 1.0  # Skip if no API key

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.polygon.io/v3/reference/tickers/{ticker}",
                params={"apiKey": polygon_key},
                timeout=5.0,
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", {})
                # Check if active
                if results.get("active", False):
                    return True, 1.0
                else:
                    return True, 0.5  # Exists but not active
            elif response.status_code == 404:
                return False, 0.0
            else:
                # API error, assume valid to avoid false negatives
                return True, 0.8

    except Exception:
        # Network error, assume valid
        return True, 0.8


# ============================================================================
# Source Audit
# ============================================================================


@router.post("/audit-sources", response_model=AuditSourceResponse)
async def audit_sources(request: AuditSourceRequest):
    """
    Audit source data by re-fetching samples and comparing.

    This endpoint:
    1. Randomly samples records from the last N days
    2. Re-parses the original source (where possible)
    3. Compares parsed values to stored values
    4. Reports discrepancies

    Note: Currently performs validation checks on stored data rather than
    re-fetching sources (which would require access to original PDFs).
    """
    import time

    start_time = time.time()

    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=request.days_back)).isoformat()

    try:
        # Build query
        query = (
            supabase.table("trading_disclosures")
            .select(
                "id, politician_id, asset_name, asset_ticker, transaction_type, "
                "transaction_date, amount_range_min, amount_range_max, disclosure_date, "
                "source_url, created_at"
            )
            .gte("created_at", cutoff_date)
        )

        if request.source:
            query = query.ilike("source_url", f"%{request.source}%")

        response = query.limit(500).execute()

        # Random sample
        records = response.data
        if len(records) > request.sample_size:
            records = random.sample(records, request.sample_size)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch records: {e}")

    mismatches = []

    for record in records:
        issues = validate_record_integrity(record)
        if issues:
            mismatches.append(
                {
                    "record_id": record["id"],
                    "issues": issues,
                    "record": {
                        "ticker": record.get("asset_ticker"),
                        "transaction_date": record.get("transaction_date"),
                        "politician_id": record.get("politician_id"),
                    },
                }
            )

    elapsed_ms = int((time.time() - start_time) * 1000)
    accuracy_rate = 1.0 - (len(mismatches) / max(len(records), 1))

    return AuditSourceResponse(
        records_sampled=len(records),
        mismatches_found=len(mismatches),
        accuracy_rate=accuracy_rate,
        mismatches=mismatches[:50],  # Limit response size
        audit_time_ms=elapsed_ms,
    )


def validate_record_integrity(record: dict) -> list:
    """
    Validate a record's internal integrity.

    Checks:
    - Date consistency (transaction_date <= disclosure_date)
    - Amount range validity (min <= max)
    - Required fields present
    - No future dates
    """
    issues = []
    today = datetime.now(timezone.utc).date()

    # Check transaction date
    if transaction_date := record.get("transaction_date"):
        try:
            tx_date = datetime.fromisoformat(transaction_date.replace("Z", "")).date()
            if tx_date > today:
                issues.append(
                    {"field": "transaction_date", "issue": "Future date", "value": transaction_date}
                )
        except (ValueError, AttributeError):
            issues.append(
                {
                    "field": "transaction_date",
                    "issue": "Invalid format",
                    "value": transaction_date,
                }
            )

    # Check disclosure date
    if disclosure_date := record.get("disclosure_date"):
        try:
            disc_date = datetime.fromisoformat(disclosure_date.replace("Z", "")).date()
            if disc_date > today:
                issues.append(
                    {
                        "field": "disclosure_date",
                        "issue": "Future date",
                        "value": disclosure_date,
                    }
                )

            # Transaction should be before disclosure
            if transaction_date:
                tx_date = datetime.fromisoformat(
                    transaction_date.replace("Z", "")
                ).date()
                if tx_date > disc_date:
                    issues.append(
                        {
                            "field": "transaction_date",
                            "issue": "Transaction after disclosure",
                            "value": f"{transaction_date} > {disclosure_date}",
                        }
                    )
        except (ValueError, AttributeError):
            pass

    # Check amount range
    amount_min = record.get("amount_range_min")
    amount_max = record.get("amount_range_max")
    if amount_min is not None and amount_max is not None:
        if amount_min > amount_max:
            issues.append(
                {
                    "field": "amount_range",
                    "issue": "Min > Max",
                    "value": f"{amount_min} > {amount_max}",
                }
            )

    # Check required fields
    if not record.get("politician_id"):
        issues.append({"field": "politician_id", "issue": "Missing required field"})

    return issues


# ============================================================================
# Freshness Report
# ============================================================================


@router.get("/freshness-report", response_model=FreshnessReport)
async def get_freshness_report():
    """
    Get data freshness status per source.

    Returns last sync time and record counts per source.
    """
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        # Get latest records per source type
        # House disclosures
        house_response = (
            supabase.table("trading_disclosures")
            .select("created_at, source_url")
            .ilike("source_url", "%house%")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        # Senate disclosures
        senate_response = (
            supabase.table("trading_disclosures")
            .select("created_at, source_url")
            .ilike("source_url", "%senate%")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        # Get scheduled jobs status
        jobs_response = (
            supabase.table("scheduled_jobs")
            .select("job_name, last_run_at, last_successful_run, enabled")
            .execute()
        )

        sources = []

        # House source
        if house_response.data:
            last_sync = house_response.data[0]["created_at"]
            hours_ago = (
                datetime.now(timezone.utc)
                - datetime.fromisoformat(last_sync.replace("Z", "+00:00"))
            ).total_seconds() / 3600
            sources.append(
                {
                    "name": "House Disclosures",
                    "last_sync": last_sync,
                    "hours_since_sync": round(hours_ago, 1),
                    "status": "healthy" if hours_ago < 48 else "stale",
                }
            )
        else:
            sources.append(
                {
                    "name": "House Disclosures",
                    "last_sync": None,
                    "hours_since_sync": None,
                    "status": "no_data",
                }
            )

        # Senate source
        if senate_response.data:
            last_sync = senate_response.data[0]["created_at"]
            hours_ago = (
                datetime.now(timezone.utc)
                - datetime.fromisoformat(last_sync.replace("Z", "+00:00"))
            ).total_seconds() / 3600
            sources.append(
                {
                    "name": "Senate Disclosures",
                    "last_sync": last_sync,
                    "hours_since_sync": round(hours_ago, 1),
                    "status": "healthy" if hours_ago < 48 else "stale",
                }
            )
        else:
            sources.append(
                {
                    "name": "Senate Disclosures",
                    "last_sync": None,
                    "hours_since_sync": None,
                    "status": "no_data",
                }
            )

        # Job statuses
        for job in jobs_response.data:
            job_status = "healthy"
            if not job.get("enabled"):
                job_status = "disabled"
            elif not job.get("last_successful_run"):
                job_status = "never_run"
            elif job.get("last_run_at") != job.get("last_successful_run"):
                job_status = "failed"

            sources.append(
                {
                    "name": f"Job: {job['job_name']}",
                    "last_sync": job.get("last_successful_run"),
                    "status": job_status,
                }
            )

        # Determine overall health
        statuses = [s["status"] for s in sources]
        if "failed" in statuses or "stale" in statuses:
            overall_health = "degraded"
        elif "no_data" in statuses or "never_run" in statuses:
            overall_health = "incomplete"
        else:
            overall_health = "healthy"

        return FreshnessReport(
            sources=sources,
            overall_health=overall_health,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {e}")


# ============================================================================
# Politician Normalization
# ============================================================================


@router.post("/normalize-politicians")
async def normalize_politicians(request: NormalizePoliticiansRequest):
    """
    Normalize politician data for consistency.

    Runs selected normalization steps:
    - roles: Map deprecated role values to canonical (Representative, Senator, MEP)
    - names: Strip honorific prefixes and fix whitespace
    - state_backfill: Fill empty state_or_country from district data

    Use dry_run=true to preview changes without applying.
    """
    import time

    start_time = time.time()
    normalizer = PoliticianNormalizer()

    results = {}
    total_corrections = 0
    total_errors = 0

    step_methods = {
        "roles": normalizer.normalize_roles,
        "names": normalizer.standardize_names,
        "state_backfill": normalizer.backfill_state_country,
    }

    for step in request.steps:
        if step not in step_methods:
            continue
        result = step_methods[step](dry_run=request.dry_run, limit=request.limit)
        results[step] = result
        total_corrections += result.get("corrections", 0)
        total_errors += result.get("errors", 0)

    elapsed_ms = int((time.time() - start_time) * 1000)

    return {
        "dry_run": request.dry_run,
        "steps_completed": list(results.keys()),
        "total_corrections": total_corrections,
        "total_errors": total_errors,
        "results": results,
        "duration_ms": elapsed_ms,
    }
