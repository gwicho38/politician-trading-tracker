"""
Politician Name Enrichment Service

Uses Ollama LLM to extract and normalize politician names from raw data.
This is the PREFERRED method for name enrichment before falling back to
Congress.gov API via BioGuide ID.

Priority order:
1. Ollama (this service) - Extract names from raw_data, normalize placeholders
2. Congress.gov API - Use BioGuide ID to get official name
3. Placeholder - Only if nothing else works
"""

import os
import re
import asyncio
import logging
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Configuration
OLLAMA_URL = os.environ.get("OLLAMA_URL", "https://ollama.lefv.info")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

# Rate limiting
REQUEST_DELAY = 0.5  # seconds between Ollama requests
BATCH_SIZE = 50


def get_supabase() -> Client:
    """Get Supabase client."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


async def extract_politician_name_with_ollama(
    client: httpx.AsyncClient,
    raw_data: Dict[str, Any],
    current_name: str,
) -> Optional[Dict[str, str]]:
    """
    Use Ollama to extract a proper politician name from raw disclosure data.

    Returns dict with:
    - full_name: The extracted full name
    - first_name: First name
    - last_name: Last name
    - party: Party if detected (D/R/I)
    - state: State if detected
    - confidence: high/medium/low

    Returns None if unable to extract.
    """
    # Build context from raw_data
    context_parts = []

    # Look for any name-like fields in raw_data
    for key in ["representative", "senator", "member", "filer", "name", "politician"]:
        if key in raw_data:
            context_parts.append(f"{key}: {raw_data[key]}")

    # Include source URL if it might contain name info
    source_url = raw_data.get("source_url", raw_data.get("url", ""))
    if source_url:
        context_parts.append(f"source: {source_url}")

    # Include any text content that might contain names
    for key in ["text", "content", "description", "title", "html_row"]:
        if key in raw_data and raw_data[key]:
            text = str(raw_data[key])[:500]  # Limit length
            context_parts.append(f"{key}: {text}")

    if not context_parts:
        return None

    context = "\n".join(context_parts)

    user_message = f"""I need to extract a US politician's name from this disclosure data.
Current placeholder name: {current_name}

Raw data:
{context}

Please extract:
1. The politician's full name (First Middle Last format preferred)
2. Their party (D for Democrat, R for Republican, I for Independent) if mentioned
3. Their state (2-letter code) if mentioned

Respond in this exact format:
NAME: [full name]
PARTY: [D/R/I or UNKNOWN]
STATE: [XX or UNKNOWN]
CONFIDENCE: [HIGH/MEDIUM/LOW]

If you cannot determine a real name, respond with:
NAME: UNKNOWN"""

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
                        "content": "You are a data extraction assistant. Extract politician information from raw disclosure data accurately. Only provide real names, not placeholders."
                    },
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.1,
                "max_tokens": 150,
            },
            timeout=60.0
        )
        response.raise_for_status()

        result = response.json()
        answer = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

        # Parse response
        extracted = parse_ollama_name_response(answer)

        if extracted and extracted.get("full_name") and extracted["full_name"] != "UNKNOWN":
            return extracted

        return None

    except httpx.HTTPError as e:
        logger.error(f"Ollama request failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error querying Ollama: {e}")
        return None


def parse_ollama_name_response(response: str) -> Optional[Dict[str, str]]:
    """Parse the structured response from Ollama."""
    result = {}

    # Extract NAME
    name_match = re.search(r"NAME:\s*(.+?)(?:\n|$)", response, re.IGNORECASE)
    if name_match:
        name = name_match.group(1).strip()
        if name and name.upper() != "UNKNOWN":
            result["full_name"] = name
            # Split into first/last
            parts = name.split()
            if len(parts) >= 2:
                result["first_name"] = parts[0]
                result["last_name"] = " ".join(parts[1:])
            elif len(parts) == 1:
                result["first_name"] = parts[0]
                result["last_name"] = parts[0]

    # Extract PARTY
    party_match = re.search(r"PARTY:\s*(\w+)", response, re.IGNORECASE)
    if party_match:
        party = party_match.group(1).strip().upper()
        if party in ["D", "R", "I"]:
            result["party"] = party
        elif "DEMOCRAT" in party:
            result["party"] = "D"
        elif "REPUBLICAN" in party:
            result["party"] = "R"
        elif "INDEPENDENT" in party:
            result["party"] = "I"

    # Extract STATE
    state_match = re.search(r"STATE:\s*([A-Z]{2})", response, re.IGNORECASE)
    if state_match:
        state = state_match.group(1).strip().upper()
        if len(state) == 2:
            result["state"] = state

    # Extract CONFIDENCE
    conf_match = re.search(r"CONFIDENCE:\s*(\w+)", response, re.IGNORECASE)
    if conf_match:
        result["confidence"] = conf_match.group(1).strip().lower()

    return result if result.get("full_name") else None


class NameEnrichmentJob:
    """Background job for enriching politician names using Ollama."""

    def __init__(self, job_id: str, limit: Optional[int] = None):
        self.job_id = job_id
        self.limit = limit
        self.status = "pending"
        self.progress = 0
        self.total = 0
        self.updated = 0
        self.skipped = 0
        self.errors = 0
        self.message = ""
        self.started_at = None
        self.completed_at = None

    def to_dict(self) -> dict:
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

    async def run(self):
        """Execute the name enrichment job."""
        self.status = "running"
        self.started_at = datetime.utcnow()
        self.message = "Fetching politicians with placeholder names..."

        try:
            supabase = get_supabase()

            # Fetch politicians with placeholder-like names
            placeholder_patterns = [
                "Placeholder",
                "Member (",
                "house_member",
                "senate_member",
                "congress_member",
                "Unknown",
                "MEP ("
            ]

            # Build OR query for placeholder names
            all_politicians = []
            for pattern in placeholder_patterns:
                result = supabase.table("politicians").select(
                    "id, full_name, first_name, last_name, party, state, chamber"
                ).ilike("full_name", f"%{pattern}%").execute()

                if result.data:
                    all_politicians.extend(result.data)

            # Dedupe by ID
            seen_ids = set()
            politicians = []
            for p in all_politicians:
                if p["id"] not in seen_ids:
                    seen_ids.add(p["id"])
                    politicians.append(p)

            if self.limit:
                politicians = politicians[:self.limit]

            self.total = len(politicians)

            if self.total == 0:
                self.status = "completed"
                self.message = "No politicians with placeholder names found"
                self.completed_at = datetime.utcnow()
                return

            self.message = f"Processing {self.total} politicians with Ollama..."
            logger.info(f"[{self.job_id}] Starting name enrichment for {self.total} politicians")

            # For each politician, try to find raw_data from their disclosures
            async with httpx.AsyncClient() as client:
                for i, politician in enumerate(politicians):
                    self.progress = i + 1

                    # Get raw_data from one of their disclosures
                    disc_result = supabase.table("trading_disclosures").select(
                        "raw_data"
                    ).eq("politician_id", politician["id"]).limit(1).execute()

                    raw_data = {}
                    if disc_result.data and disc_result.data[0].get("raw_data"):
                        raw_data = disc_result.data[0]["raw_data"]

                    if not raw_data:
                        self.skipped += 1
                        logger.info(f"[{self.job_id}] Skipped {politician['full_name']}: no raw_data")
                        continue

                    # Query Ollama for name extraction
                    extracted = await extract_politician_name_with_ollama(
                        client,
                        raw_data,
                        politician["full_name"]
                    )

                    if extracted and extracted.get("full_name"):
                        # Update politician record
                        try:
                            update_data = {"full_name": extracted["full_name"]}

                            if extracted.get("first_name"):
                                update_data["first_name"] = extracted["first_name"]
                            if extracted.get("last_name"):
                                update_data["last_name"] = extracted["last_name"]

                            # Only update party/state if we don't have them
                            if not politician.get("party") and extracted.get("party"):
                                update_data["party"] = extracted["party"]
                            if not politician.get("state") and extracted.get("state"):
                                update_data["state"] = extracted["state"]

                            supabase.table("politicians").update(
                                update_data
                            ).eq("id", politician["id"]).execute()

                            self.updated += 1
                            logger.info(
                                f"[{self.job_id}] Updated {politician['full_name']} -> "
                                f"{extracted['full_name']} (confidence: {extracted.get('confidence', 'unknown')})"
                            )
                        except Exception as e:
                            self.errors += 1
                            logger.error(f"[{self.job_id}] Failed to update {politician['full_name']}: {e}")
                    else:
                        self.skipped += 1
                        logger.info(f"[{self.job_id}] Skipped {politician['full_name']}: could not extract name")

                    # Rate limiting
                    await asyncio.sleep(REQUEST_DELAY)

                    # Update message periodically
                    if (i + 1) % 10 == 0:
                        self.message = f"Processed {i + 1}/{self.total} (updated: {self.updated}, skipped: {self.skipped})"

            self.status = "completed"
            self.message = f"Completed: {self.updated} updated, {self.skipped} skipped, {self.errors} errors"
            self.completed_at = datetime.utcnow()
            logger.info(f"[{self.job_id}] {self.message}")

        except Exception as e:
            self.status = "failed"
            self.message = f"Job failed: {str(e)}"
            self.completed_at = datetime.utcnow()
            logger.error(f"[{self.job_id}] {self.message}")


# Global job registry
_name_jobs: dict[str, NameEnrichmentJob] = {}


def get_name_job(job_id: str) -> Optional[NameEnrichmentJob]:
    """Get a job by ID."""
    return _name_jobs.get(job_id)


def create_name_job(limit: Optional[int] = None) -> NameEnrichmentJob:
    """Create a new name enrichment job."""
    import uuid
    job_id = str(uuid.uuid4())[:8]
    job = NameEnrichmentJob(job_id, limit)
    _name_jobs[job_id] = job
    return job


async def run_name_job_in_background(job: NameEnrichmentJob):
    """Run a job in the background."""
    await job.run()
