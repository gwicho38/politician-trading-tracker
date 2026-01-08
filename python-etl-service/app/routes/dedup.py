"""
Politician Deduplication API Routes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.politician_dedup import PoliticianDeduplicator

router = APIRouter(prefix="/dedup", tags=["deduplication"])


class ProcessRequest(BaseModel):
    limit: int = 50
    dry_run: bool = False


@router.get("/preview")
async def preview_duplicates(limit: int = 20):
    """
    Preview duplicate politician groups without merging.

    Returns groups of politicians that appear to be duplicates
    based on normalized name matching.
    """
    dedup = PoliticianDeduplicator()
    return dedup.preview(limit)


@router.post("/process")
async def process_duplicates(request: ProcessRequest):
    """
    Process and merge duplicate politicians.

    Set dry_run=True to see what would happen without making changes.
    """
    dedup = PoliticianDeduplicator()
    return dedup.process_all(request.limit, request.dry_run)


@router.get("/health")
async def dedup_health():
    """Check deduplication service health."""
    dedup = PoliticianDeduplicator()
    has_db = dedup.supabase is not None
    return {
        "status": "healthy" if has_db else "degraded",
        "database_connected": has_db
    }
