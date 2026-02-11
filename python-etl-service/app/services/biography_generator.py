"""
Biography Generator Service

Generates politician biographies using Ollama LLM with template fallback.
Stores bios in the database to avoid re-generating on every UI modal open.
"""

import os
import re
import asyncio
import logging
import uuid
import httpx
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from app.lib.database import get_supabase

logger = logging.getLogger(__name__)

# Configuration (reuses same Ollama config as party_enrichment)
OLLAMA_URL = os.environ.get("OLLAMA_URL", "https://ollama.lefv.info")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY")

# Rate limiting
REQUEST_DELAY = 0.5  # seconds between Ollama requests
BATCH_SIZE = 100


def generate_fallback_bio(politician: Dict[str, Any], stats: Dict[str, Any]) -> str:
    """
    Generate a template-based biography when Ollama is unavailable.

    Mirrors the generateFallbackBio() logic from the Edge Function.
    """
    name = politician.get("full_name", "Unknown")
    party = politician.get("party")
    role = politician.get("role", "")
    state = politician.get("state_or_country") or politician.get("state", "")

    party_full = {
        "D": "Democratic",
        "R": "Republican",
        "I": "Independent",
    }.get(party or "", party or "Unknown party")

    if "rep" in (role or "").lower():
        chamber_full = "Representative"
    elif "sen" in (role or "").lower():
        chamber_full = "Senator"
    elif "mep" in (role or "").lower():
        chamber_full = "Member of the European Parliament"
    else:
        chamber_full = "Member of Congress"

    total_trades = stats.get("total_trades", 0)
    total_volume = stats.get("total_volume", 0)
    top_tickers = stats.get("top_tickers", [])

    volume_str = f"${total_volume:,.0f}" if total_volume else "$0"

    bio = (
        f"{name} is a {party_full} {chamber_full}"
        f"{f' from {state}' if state else ''}. "
        f"According to public financial disclosure filings, they have reported "
        f"{total_trades} trade{'s' if total_trades != 1 else ''} "
        f"with an estimated trading volume of {volume_str}."
    )

    if top_tickers:
        tickers_str = ", ".join(top_tickers[:3])
        bio += f" Their most frequently traded securities include {tickers_str}."

    return bio


def build_ollama_prompt(politician: Dict[str, Any], stats: Dict[str, Any]) -> str:
    """Build the prompt for Ollama biography generation."""
    name = politician.get("full_name", "Unknown")
    party = politician.get("party", "Unknown")
    role = politician.get("role", "Unknown")
    state = politician.get("state_or_country") or politician.get("state", "Unknown")
    total_trades = stats.get("total_trades", 0)
    total_volume = stats.get("total_volume", 0)
    top_tickers = stats.get("top_tickers", [])

    tickers_str = ", ".join(top_tickers[:5]) if top_tickers else "N/A"

    return f"""Write a brief, factual 2-3 sentence biography for the following US politician,
focusing on their political career and notable trading activity.

Name: {name}
Party: {party}
Role: {role}
State: {state}
Total Trades: {total_trades}
Trading Volume: ${total_volume:,.0f}
Top Traded Tickers: {tickers_str}

Write ONLY the biography text, no headers or labels. Keep it factual and concise."""


def clean_llm_response(text: str) -> str:
    """
    Clean LLM response by stripping common preamble patterns.

    Mirrors the cleaning logic from the Edge Function.
    """
    if not text:
        return text

    # Strip common LLM preamble patterns
    preamble_patterns = [
        r"^(?:Here(?:'s| is) (?:a |the )?(?:brief |short )?(?:biography|bio|profile).*?:\s*)",
        r"^(?:Sure[,!]?\s*(?:here(?:'s| is).*?:\s*)?)",
        r"^(?:Based on (?:the |this )?(?:provided |available )?(?:information|data).*?:\s*)",
    ]

    cleaned = text.strip()
    for pattern in preamble_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    # Remove surrounding quotes if present
    if cleaned.startswith('"') and cleaned.endswith('"'):
        cleaned = cleaned[1:-1]

    return cleaned.strip()


async def query_ollama_for_bio(
    client: httpx.AsyncClient,
    politician: Dict[str, Any],
    stats: Dict[str, Any],
) -> Optional[str]:
    """
    Query Ollama to generate a politician biography.

    Returns the generated bio text, or None on failure.
    """
    prompt = build_ollama_prompt(politician, stats)

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
                    {
                        "role": "system",
                        "content": (
                            "You are a political analyst writing concise, factual "
                            "politician biographies. Focus on their public service "
                            "and disclosed trading activity. Be objective and "
                            "informative."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 300,
            },
            timeout=60.0,
        )
        response.raise_for_status()

        result = response.json()
        answer = (
            result.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

        if not answer:
            return None

        return clean_llm_response(answer)

    except httpx.HTTPError as e:
        name = politician.get("full_name", "Unknown")
        logger.error(f"Ollama request failed for {name}: {e}")
        return None
    except Exception as e:
        name = politician.get("full_name", "Unknown")
        logger.error(f"Unexpected error querying Ollama for {name}: {e}")
        return None


def _fetch_trading_stats(supabase, politician_id: str) -> Dict[str, Any]:
    """Fetch trading stats for a politician from Supabase."""
    result = (
        supabase.table("trading_disclosures")
        .select("asset_ticker, amount_range_min, amount_range_max")
        .eq("politician_id", politician_id)
        .eq("status", "active")
        .execute()
    )

    trades = result.data or []
    total_trades = len(trades)

    # Calculate volume (handle None values from DB)
    total_volume = sum(
        ((t.get("amount_range_min") or 0) + (t.get("amount_range_max") or 0)) / 2
        for t in trades
    )

    # Top tickers by frequency
    ticker_counts: Dict[str, int] = {}
    for t in trades:
        ticker = t.get("asset_ticker")
        if ticker:
            ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1

    top_tickers = sorted(ticker_counts, key=ticker_counts.get, reverse=True)[:5]

    return {
        "total_trades": total_trades,
        "total_volume": total_volume,
        "top_tickers": top_tickers,
    }


class BiographyJob:
    """Background job for generating politician biographies."""

    def __init__(
        self,
        job_id: str,
        limit: Optional[int] = None,
        force: bool = False,
    ) -> None:
        self.job_id = job_id
        self.limit = limit
        self.force = force
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
        """Execute the biography generation job."""
        self.status = "running"
        self.started_at = datetime.now(timezone.utc)
        self.message = "Fetching politicians for biography generation..."

        try:
            supabase = get_supabase()

            # Build query based on force flag
            target_limit = self.limit or 200
            politicians = []
            page_size = 1000
            offset = 0

            while len(politicians) < target_limit:
                fetch_count = min(page_size, target_limit - len(politicians))

                query = supabase.table("politicians").select(
                    "id, full_name, party, role, state, state_or_country, chamber"
                )

                if not self.force:
                    # Only process politicians without biographies
                    query = query.is_("biography", "null")

                # Skip placeholder politicians
                query = query.not_.ilike("full_name", "%Placeholder%")

                result = query.range(offset, offset + fetch_count - 1).execute()

                if not result.data:
                    break

                politicians.extend(result.data)
                offset += len(result.data)

                if len(result.data) < fetch_count:
                    break

            self.total = len(politicians)

            if self.total == 0:
                self.status = "completed"
                self.message = "No politicians need biography generation"
                self.completed_at = datetime.now(timezone.utc)
                return

            self.message = f"Processing {self.total} politicians..."
            logger.info(
                f"[{self.job_id}] Starting biography generation for {self.total} politicians"
            )

            async with httpx.AsyncClient() as client:
                for i, politician in enumerate(politicians):
                    self.progress = i + 1
                    name = politician["full_name"]
                    pol_id = politician["id"]

                    # Fetch trading stats
                    stats = _fetch_trading_stats(supabase, pol_id)

                    # Try Ollama first
                    bio = await query_ollama_for_bio(client, politician, stats)
                    source = "ollama"

                    if not bio:
                        # Fall back to template
                        bio = generate_fallback_bio(politician, stats)
                        source = "fallback"

                    if bio:
                        try:
                            supabase.table("politicians").update(
                                {
                                    "biography": bio,
                                    "biography_updated_at": datetime.now(
                                        timezone.utc
                                    ).isoformat(),
                                }
                            ).eq("id", pol_id).execute()

                            self.updated += 1
                            logger.info(
                                f"[{self.job_id}] Updated {name}: bio generated ({source})"
                            )
                        except Exception as e:
                            self.errors += 1
                            logger.error(
                                f"[{self.job_id}] Failed to update {name}: {e}"
                            )
                    else:
                        self.skipped += 1

                    # Rate limiting
                    await asyncio.sleep(REQUEST_DELAY)

                    # Update message periodically
                    if (i + 1) % 10 == 0:
                        self.message = (
                            f"Processed {i + 1}/{self.total} "
                            f"(updated: {self.updated}, skipped: {self.skipped})"
                        )

            self.status = "completed"
            self.message = (
                f"Completed: {self.updated} updated, "
                f"{self.skipped} skipped, {self.errors} errors"
            )
            self.completed_at = datetime.now(timezone.utc)
            logger.info(f"[{self.job_id}] {self.message}")

        except Exception as e:
            self.status = "failed"
            self.message = f"Job failed: {str(e)}"
            self.completed_at = datetime.now(timezone.utc)
            logger.error(f"[{self.job_id}] {self.message}")


# Global job registry
_jobs: Dict[str, BiographyJob] = {}


def get_bio_job(job_id: str) -> Optional[BiographyJob]:
    """Get a biography job by ID."""
    return _jobs.get(job_id)


def create_bio_job(
    limit: Optional[int] = None,
    force: bool = False,
) -> BiographyJob:
    """Create a new biography generation job."""
    job_id = str(uuid.uuid4())[:8]
    job = BiographyJob(job_id, limit, force)
    _jobs[job_id] = job
    return job


async def run_bio_job_in_background(job: BiographyJob) -> None:
    """Run a biography job in the background."""
    await job.run()
