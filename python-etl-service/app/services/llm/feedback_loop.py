"""
FeedbackLoopService -- Evaluate signal quality and recommend prompt improvements
(Prompt 4 in the LLM Prompt Pipeline).

Fetches trading_signals with their position outcomes for a date window, computes
a performance scorecard (hit_rate, alpha_rate, false_positive_rate, avg_confidence),
sends the data to an LLM for meta-analysis, and stores improvement recommendations
in the llm_prompt_recommendations table.

Usage:
    from app.services.llm.feedback_loop import FeedbackLoopService

    service = FeedbackLoopService(llm_client=client, supabase=supabase)
    result = await service.analyze("2026-01-01", "2026-01-31")
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.prompts import render_template
from app.services.llm.audit_logger import LLMAuditLogger
from app.services.llm.client import LLMClient

logger = logging.getLogger(__name__)

# Default prompt versions reported to the LLM for context
DEFAULT_VALIDATION_VERSION = "v1.0"
DEFAULT_ANOMALY_VERSION = "v1.0"

# Default thresholds the pipeline currently uses
DEFAULT_THRESHOLDS = {
    "high_confidence_threshold": 7,
    "z_score_threshold": 2.0,
    "frequency_spike_multiplier": 2.0,
    "min_trades_for_signal": 2,
}


class FeedbackLoopService:
    """Evaluate signal quality and recommend prompt improvements."""

    def __init__(self, llm_client: LLMClient, supabase: object):
        self.llm_client = llm_client
        self.supabase = supabase
        self.model = os.getenv("LLM_FEEDBACK_MODEL", "gemma3:12b-it-qat")
        self.audit_logger = LLMAuditLogger()

    # --------------------------------------------------------------------- #
    #  Public API                                                            #
    # --------------------------------------------------------------------- #

    async def analyze(self, start_date: str, end_date: str) -> dict:
        """Main entry: fetch signals with outcomes, compute scorecard, get LLM feedback.

        Args:
            start_date: ISO date string (inclusive) for window start.
            end_date: ISO date string (inclusive) for window end.

        Returns:
            Dict with scorecard, recommendations, threshold_adjustments, and feedback_id.
        """
        # 1. Fetch signals with position outcomes
        signals = await self._fetch_signals_with_outcomes(start_date, end_date)
        if not signals:
            return {
                "scorecard": self._empty_scorecard(),
                "recommendations": [],
                "threshold_adjustments": [],
                "feedback_id": None,
            }

        # 2. Compute performance scorecard
        scorecard = self._compute_scorecard(signals)

        # 3. Render prompt and send to LLM
        prompt = render_template(
            "feedback_loop",
            start_date=start_date,
            end_date=end_date,
            signals_with_outcomes_json=json.dumps(signals, default=str),
            validation_version=DEFAULT_VALIDATION_VERSION,
            anomaly_version=DEFAULT_ANOMALY_VERSION,
            thresholds_json=json.dumps(DEFAULT_THRESHOLDS),
        )

        response = await self.llm_client.generate(prompt=prompt, model=self.model)

        # 4. Parse response
        try:
            parsed = json.loads(response.text)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("Malformed LLM response for feedback loop: %s", exc)
            return {
                "scorecard": scorecard,
                "recommendations": [],
                "threshold_adjustments": [],
                "feedback_id": None,
                "error": f"Failed to parse LLM response: {exc}",
            }

        feedback_id = parsed.get("feedback_id", str(uuid.uuid4()))
        recommendations = parsed.get("prompt_recommendations", [])
        threshold_adjustments = parsed.get("threshold_adjustments", [])

        # 5. Log audit trail
        try:
            await self.audit_logger.log(
                service_name="feedback_loop",
                prompt_version="v1.0",
                prompt_hash=LLMAuditLogger.compute_prompt_hash(prompt),
                model_used=self.model,
                response=response,
                request_context={
                    "start_date": start_date,
                    "end_date": end_date,
                    "signals_count": len(signals),
                },
                parsed_output=parsed,
                parse_success=True,
            )
        except Exception as log_err:
            logger.warning("Audit logging failed for feedback loop: %s", log_err)

        # 6. Store recommendations
        await self._store_recommendations(recommendations, feedback_id)

        return {
            "scorecard": scorecard,
            "recommendations": recommendations,
            "threshold_adjustments": threshold_adjustments,
            "feedback_id": feedback_id,
        }

    # --------------------------------------------------------------------- #
    #  Data fetching                                                         #
    # --------------------------------------------------------------------- #

    async def _fetch_signals_with_outcomes(
        self,
        start: str,
        end: str,
    ) -> list[dict]:
        """Query trading_signals joined with positions for the date range.

        Returns a list of dicts with signal data and their position outcomes.
        """
        try:
            result = (
                self.supabase.table("trading_signals")
                .select("*")
                .gte("created_at", start)
                .lte("created_at", end)
                .execute()
            )

            signals = result.data or []
            if not signals:
                return []

            # For each signal, try to fetch associated position outcome
            enriched = []
            for signal in signals:
                ticker = signal.get("ticker", "")
                outcome = await self._fetch_position_outcome(ticker, start, end)
                enriched.append({
                    **signal,
                    "outcome": outcome,
                })

            return enriched

        except Exception as exc:
            logger.error("Failed to fetch signals with outcomes: %s", exc)
            return []

    async def _fetch_position_outcome(
        self,
        ticker: str,
        start: str,
        end: str,
    ) -> Optional[dict]:
        """Fetch position outcome for a ticker in the date range.

        Returns a dict with return_pct, benchmark_return_pct, alpha, etc., or None.
        """
        try:
            result = (
                self.supabase.table("positions")
                .select("*")
                .eq("ticker", ticker)
                .gte("created_at", start)
                .lte("created_at", end)
                .limit(1)
                .execute()
            )

            rows = result.data or []
            if not rows:
                return None

            pos = rows[0]
            return {
                "return_pct": pos.get("return_pct", 0),
                "benchmark_return_pct": pos.get("benchmark_return_pct", 0),
                "alpha": pos.get("alpha", 0),
                "max_drawdown_pct": pos.get("max_drawdown_pct", 0),
                "holding_period_days": pos.get("holding_period_days", 0),
            }

        except Exception as exc:
            logger.error("Failed to fetch position outcome for %s: %s", ticker, exc)
            return None

    # --------------------------------------------------------------------- #
    #  Scorecard computation                                                 #
    # --------------------------------------------------------------------- #

    def _compute_scorecard(self, signals: list[dict]) -> dict:
        """Calculate hit_rate, alpha_rate, false_positive_rate, avg_confidence.

        Args:
            signals: List of signal dicts, each with an 'outcome' key.

        Returns:
            Dict with total_signals, hit_rate, alpha_rate, false_positive_rate,
            avg_confidence.
        """
        if not signals:
            return self._empty_scorecard()

        total = len(signals)
        hits = 0
        alphas = 0
        false_positives = 0
        confidence_sum = 0.0
        signals_with_outcomes = 0

        for signal in signals:
            confidence = signal.get("confidence", 0)
            if isinstance(confidence, (int, float)):
                confidence_sum += confidence

            outcome = signal.get("outcome")
            if outcome is None:
                continue

            signals_with_outcomes += 1
            return_pct = outcome.get("return_pct", 0) or 0
            alpha = outcome.get("alpha", 0) or 0

            # Hit: signal direction was correct (positive return)
            if return_pct > 0:
                hits += 1

            # Alpha: beat benchmark
            if alpha > 0:
                alphas += 1

            # False positive: high confidence but lost money
            if isinstance(confidence, (int, float)) and confidence >= 7 and return_pct < 0:
                false_positives += 1

        denominator = signals_with_outcomes if signals_with_outcomes > 0 else 1
        high_confidence_count = sum(
            1 for s in signals
            if isinstance(s.get("confidence", 0), (int, float)) and s.get("confidence", 0) >= 7
        )
        high_confidence_denom = high_confidence_count if high_confidence_count > 0 else 1

        return {
            "total_signals": total,
            "hit_rate": round(hits / denominator, 4),
            "alpha_rate": round(alphas / denominator, 4),
            "false_positive_rate": round(false_positives / high_confidence_denom, 4),
            "avg_confidence": round(confidence_sum / total, 4) if total > 0 else 0,
        }

    @staticmethod
    def _empty_scorecard() -> dict:
        """Return a zero-valued scorecard."""
        return {
            "total_signals": 0,
            "hit_rate": 0,
            "alpha_rate": 0,
            "false_positive_rate": 0,
            "avg_confidence": 0,
        }

    # --------------------------------------------------------------------- #
    #  Recommendation storage                                                #
    # --------------------------------------------------------------------- #

    async def _store_recommendations(
        self,
        recommendations: list[dict],
        feedback_id: str,
    ) -> int:
        """Insert prompt recommendations into llm_prompt_recommendations table.

        Args:
            recommendations: List of recommendation dicts from LLM output.
            feedback_id: The feedback analysis ID to associate with.

        Returns:
            Count of recommendations successfully stored.
        """
        stored = 0
        now_iso = datetime.now(timezone.utc).isoformat()

        for rec in recommendations:
            try:
                row = {
                    "feedback_id": feedback_id,
                    "target_prompt": rec.get("target_prompt", ""),
                    "change_type": rec.get("change_type", ""),
                    "description": rec.get("description", ""),
                    "expected_impact": rec.get("expected_impact", ""),
                    "priority": rec.get("priority", "medium"),
                    "created_at": now_iso,
                }

                self.supabase.table("llm_prompt_recommendations").insert(row).execute()
                stored += 1

            except Exception as exc:
                logger.error(
                    "Failed to store recommendation for feedback %s: %s",
                    feedback_id,
                    exc,
                )

        return stored
