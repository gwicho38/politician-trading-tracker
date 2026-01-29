"""
Politician Deduplication API Routes

Endpoints for identifying and merging duplicate politician records.

Duplicates occur when the same politician appears with different name
variations (e.g., "Nancy Pelosi" vs "PELOSI, NANCY" vs "Hon. Nancy Pelosi").
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from ..services.politician_dedup import PoliticianDeduplicator

router = APIRouter(prefix="/dedup", tags=["deduplication"])


# ============================================================================
# Request/Response Models
# ============================================================================

class ProcessRequest(BaseModel):
    """Request body for deduplication processing."""
    limit: int = Field(default=50, ge=1, le=500, description="Maximum number of duplicate groups to process")
    dry_run: bool = Field(default=False, description="If true, show what would be merged without making changes")


class PoliticianRecord(BaseModel):
    """A politician record within a duplicate group."""
    id: str
    full_name: str
    party: Optional[str] = None
    state: Optional[str] = None
    is_winner: bool = Field(..., description="Whether this is the winner record (most complete)")


class DuplicateGroup(BaseModel):
    """A group of duplicate politician records."""
    normalized_name: str = Field(..., description="Normalized name used for matching")
    records: List[PoliticianRecord] = Field(..., description="Politician records in this group")
    disclosures_to_update: int = Field(..., description="Number of disclosures that will be reassigned")


class PreviewResponse(BaseModel):
    """Response for preview endpoint."""
    duplicate_groups: int = Field(..., description="Number of duplicate groups found")
    total_duplicates: int = Field(..., description="Total number of duplicate records")
    groups: List[DuplicateGroup] = Field(..., description="Details of each duplicate group")


class ProcessResponse(BaseModel):
    """Response for process endpoint."""
    processed: int = Field(..., description="Number of groups processed")
    merged: int = Field(..., description="Number of successful merges")
    disclosures_updated: int = Field(default=0, description="Number of disclosures reassigned")
    errors: int = Field(..., description="Number of merge failures")
    dry_run: bool
    results: Optional[List[dict]] = Field(None, description="Details of each merge operation")


class DedupHealthResponse(BaseModel):
    """Response for health check."""
    status: str = Field(..., description="healthy | degraded")
    database_connected: bool


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/preview", response_model=PreviewResponse)
async def preview_duplicates(limit: int = 20):
    """
    Preview duplicate politician groups without merging.

    **Matching Algorithm:**
    1. Names are normalized (lowercased, punctuation removed, whitespace trimmed)
    2. Common prefixes removed (Hon., Rep., Sen., etc.)
    3. Groups with 2+ records sharing the same normalized name are duplicates

    **Review the Preview Before Processing:**
    - Check that grouped politicians are truly the same person
    - Different politicians can have similar names (e.g., John Smith)
    - Use `dry_run=true` in `/process` for additional safety
    """
    dedup = PoliticianDeduplicator()
    return dedup.preview(limit)


@router.post("/process", response_model=ProcessResponse)
async def process_duplicates(request: ProcessRequest):
    """
    Process and merge duplicate politicians.

    **Merge Logic:**
    1. Selects the "winner" record (most complete data, most disclosures)
    2. Updates all disclosures from "loser" records to point to winner
    3. Merges any missing fields from losers into winner
    4. Soft-deletes loser records (marked as `merged_into`)

    **Safety:**
    - Use `dry_run=true` first to see what would happen
    - Merges are logged in `politician_merge_audit` table
    - Soft-deleted records can be recovered if needed

    **Performance:**
    - Process in batches of 50-100 groups
    - Large merges may take several seconds per group
    """
    dedup = PoliticianDeduplicator()
    return dedup.process_all(request.limit, request.dry_run)


@router.get("/health", response_model=DedupHealthResponse)
async def dedup_health():
    """
    Check deduplication service health.

    **Health Status:**
    - `healthy`: Database connected, ready to process
    - `degraded`: Database unavailable, operations will fail
    """
    dedup = PoliticianDeduplicator()
    has_db = dedup.supabase is not None
    return {
        "status": "healthy" if has_db else "degraded",
        "database_connected": has_db
    }
