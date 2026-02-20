"""
ValidationGateService — Post-ingestion semantic validation of trading disclosure records.

Fetches recently-inserted disclosures with llm_validation_status='pending',
sends them in batches to an LLM for semantic validation, and updates the DB
based on the LLM's verdict (pass / flag / reject).

Usage:
    from app.services.llm.validation_gate import ValidationGateService
    from app.services.llm.client import LLMClient
    from app.lib.database import get_supabase

    client = LLMClient()
    supabase = get_supabase()
    gate = ValidationGateService(llm_client=client, supabase=supabase)
    results = await gate.validate_recent()
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.prompts import load_template, render_template
from app.services.llm.audit_logger import LLMAuditLogger
from app.services.llm.client import LLMClient

logger = logging.getLogger(__name__)


class ValidationGateService:
    """Post-ingestion semantic validation of trading disclosure records."""

    BATCH_SIZE = 25
    LOOKBACK_HOURS = 2

    def __init__(self, llm_client: LLMClient, supabase: object):
        self.llm_client = llm_client
        self.supabase = supabase
        self.model = os.getenv("LLM_VALIDATION_MODEL", "qwen3:8b")
        self.audit_logger = LLMAuditLogger()

    async def validate_recent(self) -> dict:
        """Main entry point: fetch pending records, batch, validate, update statuses.

        Returns:
            Dict with total_records, passed, flagged, rejected, batches_processed counts.
        """
        records = await self._fetch_pending()
        if not records:
            return {
                "total_records": 0,
                "passed": 0,
                "flagged": 0,
                "rejected": 0,
                "batches_processed": 0,
            }

        batches = self._batch_records(records)
        results = {
            "total_records": len(records),
            "passed": 0,
            "flagged": 0,
            "rejected": 0,
            "batches_processed": 0,
        }

        for i, batch in enumerate(batches):
            batch_result = await self._validate_batch(batch, i)
            await self._apply_results(batch_result, batch)
            results["passed"] += batch_result.get("passed", 0)
            results["flagged"] += batch_result.get("flagged", 0)
            results["rejected"] += batch_result.get("rejected", 0)
            results["batches_processed"] += 1

        logger.info(
            f"Validation complete: {results['total_records']} records, "
            f"{results['passed']} passed, {results['flagged']} flagged, "
            f"{results['rejected']} rejected in {results['batches_processed']} batches"
        )

        return results

    async def _fetch_pending(self) -> list[dict]:
        """Query trading_disclosures where llm_validation_status='pending', last LOOKBACK_HOURS.

        Returns:
            List of disclosure record dicts from Supabase.
        """
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=self.LOOKBACK_HOURS)
            cutoff_iso = cutoff.isoformat()

            response = (
                self.supabase.table("trading_disclosures")
                .select("*")
                .eq("llm_validation_status", "pending")
                .gte("created_at", cutoff_iso)
                .order("created_at", desc=True)
                .limit(500)
                .execute()
            )

            records = response.data or []
            logger.info(f"Fetched {len(records)} pending records for validation")
            return records

        except Exception as e:
            logger.error(f"Failed to fetch pending records: {e}")
            return []

    def _batch_records(self, records: list[dict]) -> list[list[dict]]:
        """Split records into batches of BATCH_SIZE.

        Args:
            records: List of disclosure record dicts.

        Returns:
            List of batches, each a list of record dicts.
        """
        return [
            records[i : i + self.BATCH_SIZE]
            for i in range(0, len(records), self.BATCH_SIZE)
        ]

    async def _validate_batch(self, batch: list[dict], batch_index: int) -> dict:
        """Send one batch to the LLM for validation and parse the structured response.

        Args:
            batch: List of disclosure record dicts to validate.
            batch_index: Sequential index of this batch (for logging).

        Returns:
            Parsed dict with 'records', 'passed', 'flagged', 'rejected' keys.
            On error, returns a safe empty result dict.
        """
        empty_result = {
            "records": [],
            "passed": 0,
            "flagged": 0,
            "rejected": 0,
        }

        try:
            # Serialize batch to JSON for template injection
            batch_json = json.dumps(batch, indent=2, default=str)

            # Render the prompt template with the batch data
            rendered_prompt = render_template("validation_gate", batch_json=batch_json)

            # Extract SYSTEM: and USER: sections from the raw template
            raw_template = load_template("validation_gate")
            system_prompt, user_prompt = self._extract_prompt_sections(raw_template)

            # Compute prompt hash for audit trail
            prompt_hash = LLMAuditLogger.compute_prompt_hash(raw_template)

            # Call the LLM
            llm_response = await self.llm_client.generate(
                prompt=rendered_prompt,
                model=self.model,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=4096,
            )

            # Parse the JSON response
            parsed = json.loads(llm_response.text)

            # Log via audit logger
            try:
                await self.audit_logger.log(
                    service_name="validation_gate",
                    prompt_version="v1.0",
                    prompt_hash=prompt_hash,
                    model_used=self.model,
                    response=llm_response,
                    request_context={
                        "batch_index": batch_index,
                        "batch_size": len(batch),
                    },
                    parsed_output=parsed,
                    parse_success=True,
                )
            except Exception as log_err:
                logger.warning(f"Audit logging failed for batch {batch_index}: {log_err}")

            # Validate the parsed structure has expected keys
            records = parsed.get("records", [])
            if not records:
                logger.warning(
                    f"Batch {batch_index}: LLM response has no 'records' key or empty records"
                )
                return empty_result

            # Count verdicts
            result = {
                "records": records,
                "passed": sum(1 for r in records if r.get("status") == "pass"),
                "flagged": sum(1 for r in records if r.get("status") == "flag"),
                "rejected": sum(1 for r in records if r.get("status") == "reject"),
            }

            logger.info(
                f"Batch {batch_index}: {result['passed']} pass, "
                f"{result['flagged']} flag, {result['rejected']} reject"
            )

            return result

        except json.JSONDecodeError as e:
            logger.error(
                f"Batch {batch_index}: Failed to parse LLM response as JSON: {e}"
            )
            # Log the parse failure
            try:
                await self.audit_logger.log(
                    service_name="validation_gate",
                    prompt_version="v1.0",
                    prompt_hash="",
                    model_used=self.model,
                    response=llm_response,
                    parse_success=False,
                    error_message=f"JSON parse error: {e}",
                )
            except Exception:
                pass
            return empty_result

        except Exception as e:
            logger.error(f"Batch {batch_index}: Validation failed: {e}")
            return empty_result

    async def _apply_results(self, results: dict, original_batch: list[dict]) -> None:
        """Update DB for each record based on LLM verdict.

        Args:
            results: Parsed LLM output with 'records' array.
            original_batch: The original disclosure records that were validated.
        """
        llm_records = results.get("records", [])
        if not llm_records:
            return

        now_iso = datetime.now(timezone.utc).isoformat()

        for llm_record in llm_records:
            try:
                record_index = llm_record.get("record_index", -1)
                status = llm_record.get("status", "").lower()
                flags = llm_record.get("flags", [])
                confidence = llm_record.get("confidence", 0)

                # Match to original record by index
                if record_index < 0 or record_index >= len(original_batch):
                    logger.warning(
                        f"Record index {record_index} out of range for batch of "
                        f"{len(original_batch)} records"
                    )
                    continue

                original = original_batch[record_index]
                record_id = original.get("id")
                if not record_id:
                    logger.warning(f"Original record at index {record_index} has no 'id'")
                    continue

                if status == "pass":
                    await self._apply_pass(record_id, now_iso)

                elif status == "flag":
                    await self._apply_flag(record_id, original, flags, confidence, now_iso)

                elif status == "reject":
                    await self._apply_reject(record_id, original, flags, confidence, now_iso)

                else:
                    logger.warning(
                        f"Unknown status '{status}' for record {record_id}, skipping"
                    )

            except Exception as e:
                logger.error(
                    f"Failed to apply result for record index {llm_record.get('record_index')}: {e}"
                )

    async def _apply_pass(self, record_id: str, now_iso: str) -> None:
        """Apply pass verdict: update status and set validated timestamp."""
        self.supabase.table("trading_disclosures").update(
            {
                "llm_validation_status": "pass",
                "llm_validated_at": now_iso,
            }
        ).eq("id", record_id).execute()

    async def _apply_flag(
        self,
        record_id: str,
        original: dict,
        flags: list[dict],
        confidence: int,
        now_iso: str,
    ) -> None:
        """Apply flag verdict: update status and insert data_quality_issues."""
        # Update disclosure status
        self.supabase.table("trading_disclosures").update(
            {
                "llm_validation_status": "flag",
                "llm_validated_at": now_iso,
            }
        ).eq("id", record_id).execute()

        # Insert one data_quality_issues record per flag
        for flag in flags:
            try:
                self.supabase.table("data_quality_issues").insert(
                    {
                        "disclosure_id": record_id,
                        "severity": flag.get("severity", "warning"),
                        "source": "llm_validation",
                        "field_name": flag.get("field", ""),
                        "description": flag.get("description", ""),
                        "reasoning": flag.get("reasoning", ""),
                        "suggested_action": flag.get("suggested_action", "review"),
                        "validation_step": flag.get("step", ""),
                        "confidence": confidence,
                        "created_at": now_iso,
                    }
                ).execute()
            except Exception as e:
                logger.error(
                    f"Failed to insert data_quality_issues for record {record_id}: {e}"
                )

    async def _apply_reject(
        self,
        record_id: str,
        original: dict,
        flags: list[dict],
        confidence: int,
        now_iso: str,
    ) -> None:
        """Apply reject verdict: update status and insert into quarantine."""
        # Update disclosure status
        self.supabase.table("trading_disclosures").update(
            {
                "llm_validation_status": "reject",
                "llm_validated_at": now_iso,
            }
        ).eq("id", record_id).execute()

        # Build suggested corrections from flags
        suggested_corrections = [
            {
                "field": f.get("field", ""),
                "description": f.get("description", ""),
                "suggested_action": f.get("suggested_action", "reject"),
            }
            for f in flags
        ]

        # Insert into quarantine
        try:
            self.supabase.table("data_quality_quarantine").insert(
                {
                    "disclosure_id": record_id,
                    "original_data": original,
                    "suggested_corrections": suggested_corrections,
                    "rejection_reasons": [f.get("description", "") for f in flags],
                    "confidence": confidence,
                    "source": "llm_validation",
                    "created_at": now_iso,
                }
            ).execute()
        except Exception as e:
            logger.error(
                f"Failed to insert quarantine record for {record_id}: {e}"
            )

    @staticmethod
    def _extract_prompt_sections(template_text: str) -> tuple[Optional[str], Optional[str]]:
        """Extract SYSTEM: and USER: sections from a prompt template.

        Args:
            template_text: Raw prompt template text.

        Returns:
            Tuple of (system_prompt, user_prompt). Either may be None if not found.
        """
        system_prompt = None
        user_prompt = None

        if "SYSTEM:" in template_text and "USER:" in template_text:
            system_start = template_text.index("SYSTEM:") + len("SYSTEM:")
            user_start = template_text.index("USER:")
            system_prompt = template_text[system_start:user_start].strip()
            user_prompt = template_text[user_start + len("USER:"):].strip()
        elif "USER:" in template_text:
            user_start = template_text.index("USER:")
            user_prompt = template_text[user_start + len("USER:"):].strip()

        return system_prompt, user_prompt
