"""
Error Report Processor Service

Uses Ollama LLM to interpret user error reports and apply corrections.

Workflow:
1. Fetch pending error reports from user_error_reports table
2. Use Ollama to interpret user descriptions and determine corrections
3. Apply high-confidence corrections automatically
4. Flag low-confidence corrections for human review
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import httpx
from supabase import Client

from app.lib.database import get_supabase

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "https://ollama.lefv.info")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
DEFAULT_MODEL = "llama3.1:8b"


@dataclass
class CorrectionProposal:
    """A proposed correction from the LLM."""
    field: str
    old_value: any
    new_value: any
    confidence: float
    reasoning: str


@dataclass
class ProcessingResult:
    """Result of processing a single error report."""
    report_id: str
    status: str  # 'fixed', 'needs_review', 'invalid', 'error'
    corrections: list[CorrectionProposal]
    admin_notes: str


class ErrorReportProcessor:
    """
    Processes user error reports using Ollama LLM.

    High-confidence corrections (>= 80%) are applied automatically.
    Low-confidence corrections are flagged for human review.
    """

    CONFIDENCE_THRESHOLD = 0.8

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.supabase = self._get_supabase()
        self.ollama_client = self._get_ollama_client()

    def _get_supabase(self) -> Optional[Client]:
        """Get Supabase client."""
        return get_supabase() 

    def _get_ollama_client(self) -> httpx.Client:
        """Create Ollama HTTP client with auth."""
        headers = {}
        if OLLAMA_API_KEY:
            headers["Authorization"] = f"Bearer {OLLAMA_API_KEY}"
        return httpx.Client(base_url=OLLAMA_BASE_URL, timeout=120.0, headers=headers)

    def test_connection(self) -> bool:
        """Test connection to Ollama."""
        try:
            response = self.ollama_client.get("/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama connection test failed: {e}")
            return False

    def get_pending_reports(self, limit: int = 10) -> list[dict]:
        """Fetch pending error reports from database."""
        if not self.supabase:
            return []

        try:
            response = (
                self.supabase.table("user_error_reports")
                .select("*")
                .eq("status", "pending")
                .order("created_at", desc=False)
                .limit(limit)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error fetching reports: {e}")
            return []

    def interpret_corrections(self, report: dict) -> list[CorrectionProposal]:
        """Use Ollama to interpret what corrections the user is requesting."""
        prompt = self._build_prompt(report)

        try:
            response = self.ollama_client.post(
                "/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 1024,
                    }
                }
            )

            if response.status_code != 200:
                print(f"Ollama error: {response.status_code} - {response.text}")
                return []

            result = response.json()
            text = result.get("response", "")

            # Parse JSON response
            parsed = json.loads(text)
            corrections = []

            for c in parsed.get("corrections", []):
                corrections.append(CorrectionProposal(
                    field=c.get("field", ""),
                    old_value=c.get("old_value"),
                    new_value=c.get("new_value"),
                    confidence=float(c.get("confidence", 0.0)),
                    reasoning=c.get("reasoning", "")
                ))

            return corrections

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return []
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            return []

    def _build_prompt(self, report: dict) -> str:
        """Build the prompt for Ollama."""
        snapshot = report.get("disclosure_snapshot", {})

        return f"""You are analyzing a user-submitted error report for a financial disclosure database record.

ERROR REPORT:
- Error Type: {report.get('error_type', 'unknown')}
- User Description: "{report.get('description', '')}"

CURRENT DISCLOSURE DATA:
{json.dumps(snapshot, indent=2)}

TASK:
Based on the user's description, determine what field(s) need to be corrected and what the new value(s) should be.

FIELD MAPPING:
- wrong_amount → amount_range_min and/or amount_range_max (numeric values in dollars, no commas)
- wrong_date → transaction_date or disclosure_date (ISO 8601 format: YYYY-MM-DD)
- wrong_ticker → asset_ticker (uppercase stock symbol)
- wrong_politician → politician_name or politician_party
- other → any field

RESPONSE FORMAT (JSON only):
{{
  "corrections": [
    {{
      "field": "field_name",
      "old_value": <current value from snapshot>,
      "new_value": <corrected value>,
      "confidence": <0.0 to 1.0>,
      "reasoning": "brief explanation"
    }}
  ]
}}

RULES:
1. Parse dollar amounts like "$5,000,001 - $25,000,000" into numeric min/max values
2. Confidence should be 0.9+ only if the user clearly states the correct value
3. Confidence should be 0.5-0.8 if you're inferring the correction
4. Return empty corrections array if you cannot determine what to fix
5. For amount ranges, always provide BOTH amount_range_min and amount_range_max

Respond with ONLY the JSON object, no other text."""

    def process_report(self, report: dict, dry_run: bool = False) -> ProcessingResult:
        """Process a single error report."""
        report_id = report.get("id", "unknown")

        # Get corrections from LLM
        corrections = self.interpret_corrections(report)

        if not corrections:
            # Couldn't determine what to fix
            if not dry_run:
                self._update_report_status(
                    report_id, "reviewed",
                    "Could not automatically determine correction from description"
                )
            return ProcessingResult(
                report_id=report_id,
                status="needs_review",
                corrections=[],
                admin_notes="Could not automatically determine correction from description"
            )

        # Check if all corrections have high confidence
        all_high_confidence = all(c.confidence >= self.CONFIDENCE_THRESHOLD for c in corrections)

        if not all_high_confidence:
            # Mark for human review
            notes = "; ".join([
                f"{c.field}: {c.old_value} → {c.new_value} ({int(c.confidence * 100)}%)"
                for c in corrections
            ])
            if not dry_run:
                self._update_report_status(
                    report_id, "reviewed",
                    f"Low confidence corrections suggested: {notes}"
                )
            return ProcessingResult(
                report_id=report_id,
                status="needs_review",
                corrections=corrections,
                admin_notes=f"Suggested corrections need human review due to low confidence"
            )

        # Apply corrections
        if not dry_run:
            success = self._apply_corrections(report.get("disclosure_id"), corrections)
            if not success:
                return ProcessingResult(
                    report_id=report_id,
                    status="error",
                    corrections=corrections,
                    admin_notes="Failed to apply corrections to database"
                )

            # Mark report as fixed
            correction_summary = "; ".join([
                f"{c.field}: {c.old_value} → {c.new_value}"
                for c in corrections
            ])
            self._update_report_status(report_id, "fixed", f"Auto-corrected: {correction_summary}")

        return ProcessingResult(
            report_id=report_id,
            status="fixed",
            corrections=corrections,
            admin_notes=f"Applied {len(corrections)} correction(s)"
        )

    # Fields that belong to politicians table (not trading_disclosures)
    POLITICIAN_FIELDS = {"politician_party", "politician_name", "state", "chamber"}

    def _apply_corrections(self, disclosure_id: str, corrections: list[CorrectionProposal]) -> bool:
        """Apply corrections to the appropriate table(s)."""
        if not self.supabase or not disclosure_id:
            return False

        try:
            # Separate corrections by target table
            disclosure_updates = {}
            politician_updates = {}

            for c in corrections:
                # Map correction field to actual database field
                field = c.field
                value = c.new_value

                # Handle politician_party -> party mapping
                if field == "politician_party":
                    # Convert full name to abbreviation if needed
                    if isinstance(value, str):
                        value = self._normalize_party(value)
                    politician_updates["party"] = value
                elif field in self.POLITICIAN_FIELDS:
                    politician_updates[field] = value
                else:
                    disclosure_updates[field] = value

            # Apply disclosure updates
            if disclosure_updates:
                disclosure_updates["updated_at"] = datetime.utcnow().isoformat()
                self.supabase.table("trading_disclosures").update(
                    disclosure_updates
                ).eq("id", disclosure_id).execute()

            # Apply politician updates (need to get politician_id first)
            if politician_updates:
                # Get politician_id from the disclosure
                disclosure = self.supabase.table("trading_disclosures").select(
                    "politician_id"
                ).eq("id", disclosure_id).single().execute()

                if disclosure.data and disclosure.data.get("politician_id"):
                    politician_id = disclosure.data["politician_id"]
                    politician_updates["updated_at"] = datetime.utcnow().isoformat()
                    self.supabase.table("politicians").update(
                        politician_updates
                    ).eq("id", politician_id).execute()
                else:
                    logger.warning(f"No politician_id found for disclosure {disclosure_id}")
                    return False

            return True
        except Exception as e:
            logger.error(f"Failed to apply corrections: {e}")
            return False

    def _normalize_party(self, party: str) -> str:
        """Normalize party name to abbreviation."""
        party_lower = party.lower().strip()
        if party_lower in ("democrat", "democratic", "dem", "d"):
            return "D"
        elif party_lower in ("republican", "gop", "rep", "r"):
            return "R"
        elif party_lower in ("independent", "ind", "i"):
            return "I"
        return party  # Return as-is if not recognized

    def _update_report_status(self, report_id: str, status: str, admin_notes: str):
        """Update error report status."""
        if not self.supabase:
            return

        try:
            self.supabase.table("user_error_reports").update({
                "status": status,
                "admin_notes": admin_notes,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", report_id).execute()
        except Exception as e:
            logger.error(f"Failed to update report status: {e}")

    def process_all_pending(
        self, limit: int = 10, dry_run: bool = False
    ) -> dict:
        """
        Process all pending error reports.

        Returns:
            Summary dict with processed, fixed, needs_review counts
        """
        reports = self.get_pending_reports(limit)

        if not reports:
            return {
                "processed": 0,
                "fixed": 0,
                "needs_review": 0,
                "errors": 0,
                "results": []
            }

        results = []
        fixed = 0
        needs_review = 0
        errors = 0

        for report in reports:
            try:
                result = self.process_report(report, dry_run)
                results.append({
                    "report_id": result.report_id,
                    "status": result.status,
                    "corrections": [
                        {
                            "field": c.field,
                            "old_value": c.old_value,
                            "new_value": c.new_value,
                            "confidence": c.confidence,
                            "reasoning": c.reasoning
                        }
                        for c in result.corrections
                    ],
                    "admin_notes": result.admin_notes
                })

                if result.status == "fixed":
                    fixed += 1
                elif result.status == "needs_review":
                    needs_review += 1
                else:
                    errors += 1

            except Exception as e:
                print(f"Error processing report {report.get('id')}: {e}")
                errors += 1
                results.append({
                    "report_id": report.get("id"),
                    "status": "error",
                    "corrections": [],
                    "admin_notes": str(e)
                })

        return {
            "processed": len(reports),
            "fixed": fixed,
            "needs_review": needs_review,
            "errors": errors,
            "results": results,
            "dry_run": dry_run
        }
