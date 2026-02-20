"""
LineageAuditService -- Verify the provenance chain of custody for trading
disclosure records using LLM analysis (Prompt 3 in the LLM Prompt Pipeline).

Fetches a single trading_disclosure record by ID, computes a SHA-256 hash
chain from the source filing through every transformation to the current state,
renders the lineage_audit prompt template, sends it to the configured LLM,
and returns a structured provenance report.

Usage:
    from app.services.llm.lineage_auditor import LineageAuditService

    service = LineageAuditService(llm_client=client, supabase=supabase)
    result = await service.audit("disclosure-uuid-123")
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from app.prompts import render_template
from app.services.llm.audit_logger import LLMAuditLogger
from app.services.llm.client import LLMClient

logger = logging.getLogger(__name__)

# Default chain integrity classifications
CHAIN_INTEGRITY_VALUES = {"valid", "broken", "partial"}


class LineageAuditService:
    """Verify provenance chain of custody for trading disclosure records."""

    def __init__(self, llm_client: LLMClient, supabase):
        self.llm_client = llm_client
        self.supabase = supabase
        self.model = os.getenv("LLM_AUDIT_MODEL", "deepseek-r1:7b")
        self.audit_logger = LLMAuditLogger()

    # --------------------------------------------------------------------- #
    #  Public API                                                            #
    # --------------------------------------------------------------------- #

    async def audit(self, disclosure_id: str) -> dict:
        """Main entry point: fetch record, compute hash chain, audit via LLM.

        Args:
            disclosure_id: UUID of the trading_disclosures record to audit.

        Returns:
            Dict with trust_score, chain_integrity, verification_questions,
            and provenance_report keys.
        """
        empty_result = {
            "trust_score": 0,
            "chain_integrity": "broken",
            "verification_questions": [],
            "provenance_report": "",
        }

        # 1. Fetch the record and its metadata
        record, metadata = await self._fetch_record_and_metadata(disclosure_id)
        if not record:
            logger.warning("No record found for disclosure_id=%s", disclosure_id)
            return empty_result

        # 2. Compute the hash chain
        hash_chain = self._compute_hash_chain(record)

        # 3. Render the prompt
        prompt = self._render_prompt(record, metadata, hash_chain)

        # 4. Send to LLM
        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                model=self.model,
            )
        except Exception as exc:
            logger.error("LLM call failed for lineage audit of %s: %s", disclosure_id, exc)
            return empty_result

        # 5. Parse and return structured result
        try:
            parsed = json.loads(response.text)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("Malformed LLM response for lineage audit: %s", exc)
            # Log the parse failure
            try:
                await self.audit_logger.log(
                    service_name="lineage_audit",
                    prompt_version="v1.0",
                    prompt_hash="",
                    model_used=self.model,
                    response=response,
                    parse_success=False,
                    error_message=f"JSON parse error: {exc}",
                )
            except Exception:
                pass
            return empty_result

        # Extract the structured fields
        trust_score = parsed.get("overall_trust_score", 0)
        chain_integrity_data = parsed.get("chain_integrity", {})
        verification_questions = parsed.get("verification_questions", [])
        provenance_report = parsed.get("audit_narrative", "")

        # Determine chain_integrity status from the chain_integrity sub-object
        chain_integrity = _classify_chain_integrity(chain_integrity_data)

        # Extract just the question strings for the simplified return
        question_strings = [
            q.get("question", "") if isinstance(q, dict) else str(q)
            for q in verification_questions
        ]

        result = {
            "trust_score": trust_score,
            "chain_integrity": chain_integrity,
            "verification_questions": question_strings,
            "provenance_report": provenance_report,
        }

        # Log the successful audit
        try:
            await self.audit_logger.log(
                service_name="lineage_audit",
                prompt_version="v1.0",
                prompt_hash=LLMAuditLogger.compute_prompt_hash(prompt),
                model_used=self.model,
                response=response,
                request_context={"disclosure_id": disclosure_id},
                parsed_output=parsed,
                parse_success=True,
            )
        except Exception as log_err:
            logger.warning("Audit logging failed for lineage audit: %s", log_err)

        return result

    # --------------------------------------------------------------------- #
    #  Data fetching                                                         #
    # --------------------------------------------------------------------- #

    async def _fetch_record_and_metadata(
        self, disclosure_id: str
    ) -> tuple[Optional[dict], dict]:
        """Fetch a trading_disclosures record and extract pipeline metadata.

        Args:
            disclosure_id: UUID of the disclosure record.

        Returns:
            Tuple of (record_dict, metadata_dict). record_dict is None if
            the record is not found.
        """
        try:
            response = (
                self.supabase.table("trading_disclosures")
                .select("*")
                .eq("id", disclosure_id)
                .limit(1)
                .execute()
            )

            records = response.data or []
            if not records:
                return None, {}

            record = records[0]

            # Extract metadata from raw_data
            raw_data = record.get("raw_data") or {}
            if isinstance(raw_data, str):
                try:
                    raw_data = json.loads(raw_data)
                except (json.JSONDecodeError, TypeError):
                    raw_data = {}

            metadata = {
                "source_url": raw_data.get("source_url", ""),
                "extraction_ts": raw_data.get("extraction_ts", ""),
                "method": raw_data.get("method", raw_data.get("source", "unknown")),
                "transform_chain": raw_data.get("transform_chain", []),
            }

            return record, metadata

        except Exception as exc:
            logger.error("Failed to fetch record %s: %s", disclosure_id, exc)
            return None, {}

    # --------------------------------------------------------------------- #
    #  Hash chain computation                                                #
    # --------------------------------------------------------------------- #

    def _compute_hash_chain(self, record: dict) -> dict:
        """Compute SHA-256 hash chain from source to current record state.

        Produces hashes at each logical transform step:
        1. source_hash: hash of the raw source data
        2. transform hashes: hash after each recorded transform step
        3. current_hash: hash of the current record state

        Args:
            record: The full trading_disclosure record dict.

        Returns:
            Dict with source_hash, current_hash, and transform_chain_json keys.
        """
        raw_data = record.get("raw_data") or {}
        if isinstance(raw_data, str):
            try:
                raw_data = json.loads(raw_data)
            except (json.JSONDecodeError, TypeError):
                raw_data = {}

        # Source hash: hash of the raw_data content
        source_content = json.dumps(raw_data, sort_keys=True, default=str)
        source_hash = hashlib.sha256(source_content.encode("utf-8")).hexdigest()

        # Build transform chain with hashes
        transform_chain = raw_data.get("transform_chain", [])
        chain_with_hashes = []
        previous_hash = source_hash

        for step in transform_chain:
            step_content = json.dumps(step, sort_keys=True, default=str)
            input_hash = previous_hash
            output_hash = hashlib.sha256(
                (input_hash + step_content).encode("utf-8")
            ).hexdigest()

            chain_with_hashes.append({
                "step": step.get("step", "unknown"),
                "ts": step.get("ts", ""),
                "version": step.get("version", ""),
                "input_hash": input_hash,
                "output_hash": output_hash,
            })

            previous_hash = output_hash

        # Current hash: hash of the full record as it stands now
        # Exclude volatile fields that change after insertion
        hashable_fields = {
            k: v
            for k, v in record.items()
            if k not in ("created_at", "updated_at", "llm_validation_status", "llm_validated_at")
        }
        current_content = json.dumps(hashable_fields, sort_keys=True, default=str)
        current_hash = hashlib.sha256(current_content.encode("utf-8")).hexdigest()

        return {
            "source_hash": source_hash,
            "current_hash": current_hash,
            "transform_chain": chain_with_hashes,
            "transform_chain_json": json.dumps(chain_with_hashes, indent=2),
        }

    # --------------------------------------------------------------------- #
    #  Prompt rendering                                                      #
    # --------------------------------------------------------------------- #

    def _render_prompt(self, record: dict, metadata: dict, hash_chain: dict) -> str:
        """Render the lineage_audit prompt template with all variables.

        Args:
            record: The trading_disclosure record dict.
            metadata: Extracted pipeline metadata.
            hash_chain: Computed hash chain from _compute_hash_chain.

        Returns:
            Rendered prompt string with all placeholders filled.
        """
        return render_template(
            "lineage_audit",
            record_json=json.dumps(record, indent=2, default=str),
            source_url=metadata.get("source_url", ""),
            source_hash=hash_chain["source_hash"],
            method=metadata.get("method", "unknown"),
            extraction_ts=metadata.get("extraction_ts", ""),
            transform_chain_json=hash_chain["transform_chain_json"],
            current_hash=hash_chain["current_hash"],
        )


# --------------------------------------------------------------------------- #
#  Module-level helpers                                                       #
# --------------------------------------------------------------------------- #


def _classify_chain_integrity(chain_integrity_data: dict) -> str:
    """Classify chain integrity as valid, broken, or partial.

    Args:
        chain_integrity_data: The chain_integrity sub-object from the LLM response.

    Returns:
        One of "valid", "broken", or "partial".
    """
    if not chain_integrity_data or not isinstance(chain_integrity_data, dict):
        return "broken"

    hash_valid = chain_integrity_data.get("hash_chain_valid", False)
    temporal_valid = chain_integrity_data.get("temporal_ordering_valid", False)
    transforms_approved = chain_integrity_data.get("all_transforms_approved", False)
    gaps = chain_integrity_data.get("gaps_detected", 0)

    if hash_valid and temporal_valid and transforms_approved and gaps == 0:
        return "valid"
    elif not hash_valid or gaps > 2:
        return "broken"
    else:
        return "partial"
