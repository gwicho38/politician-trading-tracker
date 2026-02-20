"""
Politician Trading ETL Service

FastAPI service that extracts real disclosure data from government PDFs
and uploads to Supabase.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.responses import Response

from app.routes import health, etl, enrichment, ml, quality, error_reports, dedup, signals, admin
from app.routes import admin_sections
from app.routes import llm_pipeline
from app.lib.logging_config import configure_logging, get_logger
from app.middleware.correlation import CorrelationMiddleware
from app.middleware.auth import AuthMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

# Configure structured logging before anything else
log_level = logging.DEBUG if os.getenv("DEBUG") else logging.INFO
json_logs = os.getenv("JSON_LOGS", "true").lower() == "true"
configure_logging(level=log_level, service_name="politician-etl", json_format=json_logs)

logger = get_logger(__name__)


# OpenAPI tag descriptions for better documentation
OPENAPI_TAGS = [
    {
        "name": "health",
        "description": "Service health checks for monitoring and load balancers.",
    },
    {
        "name": "etl",
        "description": """
ETL (Extract, Transform, Load) operations for congressional trading disclosures.

**Data Sources:**
- **House**: Financial disclosure PDFs from disclosures-clerk.house.gov
- **Senate**: Electronic filings from efdsearch.senate.gov

**Workflow:**
1. Trigger ETL job with `POST /etl/trigger`
2. Monitor progress with `GET /etl/status/{job_id}`
3. Enrich data with `/enrichment` endpoints
4. Generate signals with `/signals` endpoints
""",
    },
    {
        "name": "enrichment",
        "description": """
Data enrichment services using AI (Ollama LLM) and external data sources.

**Available Enrichments:**
- **Party Enrichment**: Infer politician party affiliation (D/R/I)
- **Name Enrichment**: Extract structured names from raw disclosure text
- **Bioguide Enrichment**: Link to official Congress.gov bioguide IDs
""",
    },
    {
        "name": "ml",
        "description": """
Machine learning model management for trading signal prediction.

**Signal Types:**
- `-2`: Strong Sell
- `-1`: Sell
- `0`: Hold
- `1`: Buy
- `2`: Strong Buy

**Model Features:**
- politician_count, buy_sell_ratio, recent_activity_30d
- bipartisan, net_volume, volume_magnitude
- party_alignment, committee_relevance, disclosure_delay
- sentiment_score, market_momentum, sector_performance

⚠️ **Admin endpoints** (`/ml/train`, `/ml/models/{id}/activate`) require `X-Admin-Key` header.
""",
    },
    {
        "name": "quality",
        "description": """
Data quality monitoring and validation tools.

**Validation Checks:**
- Ticker symbol validation against known patterns and Polygon.io
- Source data auditing by re-fetching and comparing
- Data freshness monitoring per source
""",
    },
    {
        "name": "error-reports",
        "description": """
User-submitted error report processing using AI (Ollama LLM).

**Workflow:**
1. Users submit error reports via the web app
2. `POST /error-reports/process` analyzes reports with LLM
3. High-confidence corrections are auto-applied
4. Low-confidence corrections require manual review via `GET /error-reports/needs-review`
5. Admins can force-apply corrections with `POST /error-reports/force-apply`

⚠️ **Admin endpoints** (`/error-reports/force-apply`, `/error-reports/reanalyze`) require `X-Admin-Key` header.
""",
    },
    {
        "name": "deduplication",
        "description": """
Politician deduplication services using fuzzy name matching.

Identifies and merges duplicate politician records that may have been
created due to name variations (e.g., "Nancy Pelosi" vs "PELOSI, NANCY").
""",
    },
    {
        "name": "signals",
        "description": """
Custom signal transformation using sandboxed Python lambdas.

Allows users to write custom transformation logic that runs in a
restricted sandbox (no file I/O, no network, limited builtins).

**Example Lambda:**
```python
for s in signals:
    if s['confidence'] > 0.8:
        s['signal_type'] = 'strong_' + s['signal_type']
```
""",
    },
    {
        "name": "llm",
        "description": "LLM prompt pipeline for validation, anomaly detection, lineage audit, and feedback.",
    },
    {
        "name": "admin",
        "description": """
Admin dashboard for GovMarket.trade platform management.

**Sections:**
- **Overview** - System health summary
- **Validation** - QuiverQuant data validation management
- **ETL Jobs** - Trigger and monitor House/Senate ETL pipelines
- **ML Models** - View, train, and activate ML models
- **Data Quality** - Ticker validation, source audit, freshness
- **Enrichment** - Party, name, and BioGuide enrichment
- **Error Reports** - User-submitted error report processing
- **Audit Log** - Unified event timeline

**Access:**
Requires admin API key via `?key=YOUR_ADMIN_KEY` query parameter.

**URLs:**
- `GET /admin/overview` - System overview
- `GET /admin` - Validation dashboard
- `GET /admin/etl` - ETL management
- `GET /admin/ml` - ML model management
- `GET /admin/quality` - Data quality
- `GET /admin/enrichment` - Enrichment management
- `GET /admin/errors` - Error reports
- `GET /admin/audit-log` - Audit log
""",
    },
]


API_DESCRIPTION = """
# Politician Trading ETL Service

Extracts, transforms, and loads congressional trading disclosures from official government sources.

## Authentication

Most endpoints require API key authentication:

| Header | Description |
|--------|-------------|
| `X-API-Key` | Standard API key for read/write operations |
| `X-Admin-Key` | Admin API key for sensitive operations (train, activate, force-apply) |

**Public Endpoints** (no auth required):
- `GET /` - Service info
- `GET /health` - Health check
- `GET /docs` - This documentation
- `GET /openapi.json` - OpenAPI schema

## Rate Limiting

Requests are rate-limited based on IP address:

| Endpoint Pattern | Limit |
|-----------------|-------|
| `/ml/train` | 5 requests/hour |
| `/etl/trigger` | 10 requests/minute |
| All other endpoints | 100 requests/minute |

Rate limit headers:
- `X-RateLimit-Remaining`: Requests remaining in window
- `Retry-After`: Seconds to wait (on 429 response)

## Request Tracing

All requests include correlation IDs for tracing:
- Send `X-Correlation-ID` header to set your own
- Response includes `X-Correlation-ID` header
- Logs include `correlation_id` field for debugging

## Error Responses

All errors follow this format:
```json
{
  "detail": "Human-readable error message"
}
```

Common HTTP status codes:
- `400` - Invalid request parameters
- `401` - Missing API key
- `403` - Invalid API key or insufficient permissions
- `404` - Resource not found
- `422` - Validation error (check detail for field errors)
- `429` - Rate limit exceeded
- `500` - Internal server error
- `503` - Service unavailable (database or external service down)
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Politician Trading ETL Service...", extra={"version": "1.0.0"})
    yield
    # Shutdown
    logger.info("Shutting down ETL Service...")


app = FastAPI(
    title="Politician Trading ETL Service",
    description=API_DESCRIPTION,
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    contact={
        "name": "GovMarket.trade Support",
        "url": "https://govmarket.trade",
    },
)

# Add middleware (order matters - first added = outermost)
# 1. Correlation ID middleware for request tracing
app.add_middleware(CorrelationMiddleware)
# 2. API key authentication middleware
app.add_middleware(AuthMiddleware)
# 3. Rate limiting middleware (innermost - runs after auth)
app.add_middleware(RateLimitMiddleware)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(etl.router, prefix="/etl", tags=["etl"])
app.include_router(enrichment.router, prefix="/enrichment", tags=["enrichment"])
app.include_router(ml.router, prefix="/ml", tags=["ml"])
app.include_router(quality.router, prefix="/quality", tags=["quality"])
app.include_router(error_reports.router, prefix="/error-reports", tags=["error-reports"])
app.include_router(dedup.router, tags=["deduplication"])
app.include_router(signals.router, prefix="/signals", tags=["signals"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(admin_sections.router, prefix="/admin", tags=["admin"])
app.include_router(llm_pipeline.router, prefix="/llm", tags=["llm"])


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Return 204 No Content for favicon requests to avoid 401 errors in browser."""
    return Response(status_code=204)


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
            "dedup_preview": "GET /dedup/preview",
            "dedup_process": "POST /dedup/process",
            "signals_apply_lambda": "POST /signals/apply-lambda",
            "signals_validate_lambda": "POST /signals/validate-lambda",
            "signals_lambda_help": "GET /signals/lambda-help",
            "admin_overview": "GET /admin/overview?key=YOUR_ADMIN_KEY",
            "admin_validation": "GET /admin?key=YOUR_ADMIN_KEY",
            "admin_detail": "GET /admin/detail/{id}?key=YOUR_ADMIN_KEY",
            "admin_etl": "GET /admin/etl?key=YOUR_ADMIN_KEY",
            "admin_ml": "GET /admin/ml?key=YOUR_ADMIN_KEY",
            "admin_quality": "GET /admin/quality?key=YOUR_ADMIN_KEY",
            "admin_enrichment": "GET /admin/enrichment?key=YOUR_ADMIN_KEY",
            "admin_errors": "GET /admin/errors?key=YOUR_ADMIN_KEY",
            "admin_audit_log": "GET /admin/audit-log?key=YOUR_ADMIN_KEY",
            "llm_validate_batch": "POST /llm/validate-batch",
            "llm_detect_anomalies": "POST /llm/detect-anomalies",
            "llm_audit_lineage": "POST /llm/audit-lineage",
            "llm_run_feedback": "POST /llm/run-feedback",
            "llm_audit_trail": "GET /llm/audit-trail",
            "llm_health": "GET /llm/health",
        },
    }
