"""
LLMAuditLogger — Logs every LLM call to the llm_audit_trail Supabase table.

Fire-and-forget design: if logging fails, the error is logged but never
raised, so the main operation is never disrupted.

Usage:
    logger = LLMAuditLogger()
    await logger.log(
        service_name="validation_gate",
        prompt_version="v1.0",
        prompt_hash=LLMAuditLogger.compute_prompt_hash(template),
        model_used="llama3.1:8b",
        response=llm_response,
        request_context={"disclosure_id": "abc-123"},
        parsed_output={"result": "ok"},
    )
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class LLMAuditLogger:
    """
    Logs LLM calls to the llm_audit_trail table in Supabase.

    All logging is fire-and-forget: failures are logged but never raised.
    """

    def __init__(self):
        pass

    def _get_supabase(self):
        """Get Supabase client. Deferred import to avoid circular deps."""
        from app.lib.database import get_supabase

        return get_supabase()

    async def log(
        self,
        service_name: str,
        prompt_version: str,
        prompt_hash: str,
        model_used: str,
        response: object,
        request_context: dict = None,
        parsed_output: dict = None,
        parse_success: bool = True,
        error_message: str = None,
    ) -> None:
        """
        Log an LLM call to the llm_audit_trail table.

        Args:
            service_name: Which prompt service made the call
                          (e.g., "validation_gate", "anomaly_detection").
            prompt_version: Version tag of the prompt template (e.g., "v1.0").
            prompt_hash: SHA-256 hash of the prompt template text.
            model_used: Ollama model name used for the call.
            response: LLMResponse object from LLMClient.generate().
            request_context: Optional dict with contextual info (e.g., disclosure_id).
            parsed_output: Optional dict of the parsed LLM output.
            parse_success: Whether the LLM output was successfully parsed.
            error_message: Optional error message if something failed.
        """
        try:
            supabase = self._get_supabase()
            if supabase is None:
                logger.warning("Supabase client unavailable; skipping LLM audit log")
                return

            row = {
                "service_name": service_name,
                "prompt_version": prompt_version,
                "prompt_hash": prompt_hash,
                "model_used": model_used,
                "input_tokens": getattr(response, "input_tokens", 0),
                "output_tokens": getattr(response, "output_tokens", 0),
                "latency_ms": getattr(response, "latency_ms", 0),
                "raw_response": getattr(response, "text", ""),
                "parsed_output": parsed_output,
                "parse_success": parse_success,
                "error_message": error_message,
                "request_context": request_context,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            supabase.table("llm_audit_trail").insert(row).execute()

        except Exception as e:
            logger.error(f"Failed to log LLM audit trail: {e}")
            # Fire-and-forget: never raise from audit logging

    @staticmethod
    def compute_prompt_hash(template_text: str) -> str:
        """
        Compute a SHA-256 hex digest of a prompt template.

        Used to track which exact prompt version produced a given output,
        enabling prompt drift detection and A/B testing.

        Args:
            template_text: The full prompt template string.

        Returns:
            64-character hex string (SHA-256 digest).
        """
        return hashlib.sha256(template_text.encode("utf-8")).hexdigest()
