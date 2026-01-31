"""
Party Enrichment Service

Uses Ollama LLM to determine political party affiliation for politicians
with missing party data.
"""

import os
import re
import asyncio
import logging
import httpx
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from app.lib.database import get_supabase

logger = logging.getLogger(__name__)

# Configuration
OLLAMA_URL = os.environ.get("OLLAMA_URL", "https://ollama.lefv.info")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")  # Available: gpt-oss:20b, llama3.1:8b
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

# Rate limiting
REQUEST_DELAY = 0.5  # seconds between Ollama requests
BATCH_SIZE = 50  # politicians per batch


async def query_ollama_for_party(
    client: httpx.AsyncClient,
    name: str,
    state: Optional[str] = None,
    chamber: Optional[str] = None,
) -> Optional[str]:
    """
    Query Ollama to determine a politician's party affiliation.

    Uses OpenAI-compatible chat completions API.
    Returns: 'D', 'R', 'I', or None if unable to determine.
    """
    context_parts = []
    if state:
        context_parts.append(f"from {state}")
    if chamber:
        context_parts.append(f"serving in the {chamber}")
    context = " ".join(context_parts) if context_parts else ""

    user_message = f"""What is the political party affiliation of US politician {name} {context}?

Answer with ONLY one of these options:
- D (Democrat)
- R (Republican)
- I (Independent)
- UNKNOWN (if you cannot determine)

Your answer (just the letter or UNKNOWN):"""

    try:
        headers = {"Content-Type": "application/json"}
        if OLLAMA_API_KEY:
            headers["Authorization"] = f"Bearer {OLLAMA_API_KEY}"

        response = await client.post(
            f"{OLLAMA_URL}/v1/chat/completions",
            headers=headers,
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that provides factual information about US politicians. Answer concisely with just the letter code."},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.1,
                "max_tokens": 20,
            },
            timeout=60.0
        )
        response.raise_for_status()

        result = response.json()
        answer = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip().upper()

        # Extract party from response
        if "DEMOCRAT" in answer or answer.startswith("D"):
            return "D"
        elif "REPUBLICAN" in answer or answer.startswith("R"):
            return "R"
        elif "INDEPENDENT" in answer or answer.startswith("I"):
            return "I"
        else:
            logger.warning(f"Could not parse party from response for {name}: {answer}")
            return None

    except httpx.HTTPError as e:
        logger.error(f"Ollama request failed for {name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error querying Ollama for {name}: {e}")
        return None


class PartyEnrichmentJob:
    """Background job for enriching politician party data."""

    def __init__(self, job_id: str, limit: Optional[int] = None) -> None:
        self.job_id = job_id
        self.limit = limit
        self.status: str = "pending"
        self.progress: int = 0
        self.total: int = 0
        self.updated: int = 0
        self.skipped: int = 0
        self.errors: int = 0
        self.message: str = ""
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert job state to dictionary."""
        return {
            "job_id": self.job_id,
            "status": self.status,
            "progress": self.progress,
            "total": self.total,
            "updated": self.updated,
            "skipped": self.skipped,
            "errors": self.errors,
            "message": self.message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    async def run(self) -> None:
        """Execute the party enrichment job."""
        self.status = "running"
        self.started_at = datetime.now(timezone.utc)
        self.message = "Fetching politicians with missing party data..."

        try:
            supabase = get_supabase()

            # Fetch politicians with NULL party using pagination
            # Supabase has a default limit of 1000 rows per request
            target_limit = self.limit or 5000  # Safety limit
            politicians = []
            page_size = 1000  # Max per Supabase request
            offset = 0

            while len(politicians) < target_limit:
                fetch_count = min(page_size, target_limit - len(politicians))

                result = supabase.table("politicians").select(
                    "id, full_name, state, chamber"
                ).is_("party", "null").range(offset, offset + fetch_count - 1).execute()

                if not result.data:
                    break  # No more data

                politicians.extend(result.data)
                offset += len(result.data)

                if len(result.data) < fetch_count:
                    break  # Last page

                logger.info(f"[{self.job_id}] Fetched {len(politicians)} politicians so far...")

            self.total = len(politicians)

            if self.total == 0:
                self.status = "completed"
                self.message = "No politicians need party enrichment"
                self.completed_at = datetime.now(timezone.utc)
                return

            self.message = f"Processing {self.total} politicians..."
            logger.info(f"[{self.job_id}] Starting enrichment for {self.total} politicians")

            # Process in batches with rate limiting
            async with httpx.AsyncClient() as client:
                for i, politician in enumerate(politicians):
                    self.progress = i + 1

                    name = politician["full_name"]
                    state = politician.get("state")
                    chamber = politician.get("chamber")

                    # Query Ollama for party
                    party = await query_ollama_for_party(client, name, state, chamber)

                    if party:
                        # Update politician record
                        try:
                            supabase.table("politicians").update({
                                "party": party
                            }).eq("id", politician["id"]).execute()

                            self.updated += 1
                            logger.info(f"[{self.job_id}] Updated {name}: party={party}")
                        except Exception as e:
                            self.errors += 1
                            logger.error(f"[{self.job_id}] Failed to update {name}: {e}")
                    else:
                        self.skipped += 1
                        logger.info(f"[{self.job_id}] Skipped {name}: could not determine party")

                    # Rate limiting
                    await asyncio.sleep(REQUEST_DELAY)

                    # Update message periodically
                    if (i + 1) % 10 == 0:
                        self.message = f"Processed {i + 1}/{self.total} (updated: {self.updated}, skipped: {self.skipped})"

            self.status = "completed"
            self.message = f"Completed: {self.updated} updated, {self.skipped} skipped, {self.errors} errors"
            self.completed_at = datetime.now(timezone.utc)
            logger.info(f"[{self.job_id}] {self.message}")

        except Exception as e:
            self.status = "failed"
            self.message = f"Job failed: {str(e)}"
            self.completed_at = datetime.now(timezone.utc)
            logger.error(f"[{self.job_id}] {self.message}")


# Global job registry
_jobs: Dict[str, PartyEnrichmentJob] = {}


def get_job(job_id: str) -> Optional[PartyEnrichmentJob]:
    """Get a job by ID."""
    return _jobs.get(job_id)


def create_job(limit: Optional[int] = None) -> PartyEnrichmentJob:
    """Create a new party enrichment job."""
    import uuid
    job_id = str(uuid.uuid4())[:8]
    job = PartyEnrichmentJob(job_id, limit)
    _jobs[job_id] = job
    return job


async def run_job_in_background(job: PartyEnrichmentJob) -> None:
    """Run a job in the background."""
    await job.run()
