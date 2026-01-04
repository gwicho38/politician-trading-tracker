"""
Politician Trading ETL Service

FastAPI service that extracts real disclosure data from government PDFs
and uploads to Supabase.
"""

import os
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.routes import health, etl, enrichment, ml, quality, error_reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("Starting Politician Trading ETL Service...")
    yield
    # Shutdown
    print("Shutting down ETL Service...")


app = FastAPI(
    title="Politician Trading ETL Service",
    description="Extracts trading disclosures from government PDFs",
    version="1.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(etl.router, prefix="/etl", tags=["etl"])
app.include_router(enrichment.router, prefix="/enrichment", tags=["enrichment"])
app.include_router(ml.router, prefix="/ml", tags=["ml"])
app.include_router(quality.router, prefix="/quality", tags=["quality"])
app.include_router(error_reports.router, prefix="/error-reports", tags=["error-reports"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "politician-trading-etl",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "trigger_etl": "POST /etl/trigger",
            "etl_status": "GET /etl/status/{job_id}",
            "trigger_enrichment": "POST /enrichment/trigger",
            "enrichment_status": "GET /enrichment/status/{job_id}",
            "enrichment_preview": "GET /enrichment/preview",
            "ml_predict": "POST /ml/predict",
            "ml_batch_predict": "POST /ml/batch-predict",
            "ml_train": "POST /ml/train",
            "ml_models": "GET /ml/models",
            "ml_health": "GET /ml/health",
            "quality_validate_tickers": "POST /quality/validate-tickers",
            "quality_audit_sources": "POST /quality/audit-sources",
            "quality_freshness": "GET /quality/freshness-report",
            "error_reports_process": "POST /error-reports/process",
            "error_reports_process_one": "POST /error-reports/process-one",
            "error_reports_stats": "GET /error-reports/stats",
            "error_reports_health": "GET /error-reports/health",
        },
    }
