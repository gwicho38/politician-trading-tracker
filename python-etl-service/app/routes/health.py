"""Health check endpoints for service monitoring."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.

    Used by Fly.io to determine if the service is ready to receive traffic.
    Returns immediately without checking dependencies.

    For detailed health including database and ML model status, use:
    - `GET /ml/health` - ML model status
    - `GET /error-reports/health` - Ollama status
    - `GET /dedup/health` - Database status
    """
    return {"status": "healthy"}
