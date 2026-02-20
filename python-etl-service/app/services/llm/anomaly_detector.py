"""
AnomalyDetectionService -- Detect anomalous trading patterns using rolling
time windows and LLM analysis (Prompt 2 in the LLM Prompt Pipeline).

Fetches politician trading disclosures for a date window, computes per-filer
baseline statistics from the prior 12 months, renders the anomaly_detection
prompt template, sends it to the configured LLM, and stores the resulting
anomaly signals into Supabase.

Usage:
    from app.services.llm.anomaly_detector import AnomalyDetectionService

    service = AnomalyDetectionService(llm_client=client, supabase=supabase)
    result = await service.detect("2026-01-01", "2026-01-31", filer="ALL")
"""

import json
import logging
import os
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.prompts import render_template
from app.services.llm.audit_logger import LLMAuditLogger
from app.services.llm.client import LLMClient

logger = logging.getLogger(__name__)

# Signal classifications recognised by the pipeline
SIGNAL_CLASSIFICATIONS = {
    "FREQUENCY_SPIKE",
    "SECTOR_CLUSTER",
    "TIMING_ANOMALY",
    "AMOUNT_ANOMALY",
    "COORDINATED_PATTERN",
}

# Minimum confidence to also emit a trading_signals row
HIGH_CONFIDENCE_THRESHOLD = 7

# Amount-range index lookup (mid-point of common STOCK Act ranges)
AMOUNT_RANGE_INDEX = {
    (0, 1000): 1,
    (1001, 15000): 2,
    (15001, 50000): 3,
    (50001, 100000): 4,
    (100001, 250000): 5,
    (250001, 500000): 6,
    (500001, 1000000): 7,
    (1000001, 5000000): 8,
    (5000001, 25000000): 9,
    (25000001, 50000000): 10,
}

# Map LLM direction to trading_signals signal_type
DIRECTION_TO_SIGNAL_TYPE = {
    "long": "buy",
    "short": "sell",
    "neutral": "hold",
}


class AnomalyDetectionService:
    """Detect anomalous trading patterns using rolling time windows."""

    def __init__(self, llm_client: LLMClient, supabase):
        self.llm_client = llm_client
        self.supabase = supabase
        self.model = os.getenv("LLM_ANOMALY_MODEL", "gemma3:12b-it-qat")
        self.audit_logger = LLMAuditLogger()

    # --------------------------------------------------------------------- #
    #  Public API                                                            #
    # --------------------------------------------------------------------- #

    async def detect(
        self,
        start_date: str,
        end_date: str,
        filer: str = "ALL",
    ) -> dict:
        """Main entry: fetch window, compute baselines, detect anomalies, store signals.

        Args:
            start_date: ISO date string (inclusive) for window start.
            end_date: ISO date string (inclusive) for window end.
            filer: Filer name to filter on, or "ALL" for all filers.

        Returns:
            Dict with anomalies_detected, signals, analysis_window, and signals_stored.
        """
        # 1. Fetch trading records for the window
        records = await self._fetch_trading_window(start_date, end_date, filer)
        if not records:
            return {
                "anomalies_detected": 0,
                "signals": [],
                "analysis_window": {"start": start_date, "end": end_date},
            }

        # 2. Get unique filers and compute baselines
        filers = list(set(r.get("filer_name", "") for r in records))
        baselines = {}
        for f in filers:
            baselines[f] = await self._compute_baseline_stats(f, start_date)

        # 3. Fetch legislative calendar events
        calendar = await self._fetch_calendar_events(start_date, end_date)

        # 4. Render prompt and send to LLM
        prompt = render_template(
            "anomaly_detection",
            start_date=start_date,
            end_date=end_date,
            filer_names_or_ALL=filer,
            calendar_events_json=json.dumps(calendar),
            trading_records_json=json.dumps(records),
            baseline_stats_json=json.dumps(baselines),
        )

        response = await self.llm_client.generate(prompt=prompt, model=self.model)

        # 5. Parse and store results
        try:
            parsed = json.loads(response.text)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("Malformed LLM response for anomaly detection: %s", exc)
            return {
                "anomalies_detected": 0,
                "signals": [],
                "analysis_window": {"start": start_date, "end": end_date},
                "error": f"Failed to parse LLM response: {exc}",
            }

        signals = parsed.get("signals", [])
        stored = await self._store_signals(signals, audit_id=None)

        return {
            "anomalies_detected": parsed.get("anomalies_detected", 0),
            "signals": signals,
            "analysis_window": {"start": start_date, "end": end_date},
            "signals_stored": stored,
        }

    # --------------------------------------------------------------------- #
    #  Data fetching                                                         #
    # --------------------------------------------------------------------- #

    async def _fetch_trading_window(
        self,
        start: str,
        end: str,
        filer: str,
    ) -> list[dict]:
        """Query trading_disclosures for the date range, optionally filtered by filer.

        Returns a list of dicts with: filer_name, transaction_date, ticker,
        asset_description, transaction_type, amount_range_min, amount_range_max, source.
        """
        try:
            query = (
                self.supabase.table("trading_disclosures")
                .select(
                    "id, transaction_date, asset_ticker, asset_name, "
                    "transaction_type, amount_range_min, amount_range_max, "
                    "raw_data, politicians(full_name)"
                )
                .gte("transaction_date", start)
                .lte("transaction_date", end)
            )

            if filer and filer != "ALL":
                query = query.ilike("politicians.full_name", f"%{filer}%")

            result = query.execute()
            rows = result.data or []

            records = []
            for row in rows:
                politician_data = row.get("politicians") or {}
                filer_name = ""
                if isinstance(politician_data, dict):
                    filer_name = politician_data.get("full_name", "")
                elif isinstance(politician_data, list) and politician_data:
                    filer_name = politician_data[0].get("full_name", "")

                raw_data = row.get("raw_data") or {}
                source = raw_data.get("source", "unknown") if isinstance(raw_data, dict) else "unknown"

                records.append({
                    "record_id": row.get("id", ""),
                    "filer_name": filer_name,
                    "transaction_date": row.get("transaction_date", ""),
                    "ticker": row.get("asset_ticker", ""),
                    "asset_description": row.get("asset_name", ""),
                    "transaction_type": row.get("transaction_type", ""),
                    "amount_range_min": row.get("amount_range_min"),
                    "amount_range_max": row.get("amount_range_max"),
                    "source": source,
                })

            return records

        except Exception as exc:
            logger.error("Failed to fetch trading window: %s", exc)
            return []

    async def _compute_baseline_stats(
        self,
        filer: str,
        before_date: str,
    ) -> dict:
        """Compute 12-month baseline stats for a filer.

        Returns a dict with: avg_trades_per_month, typical_sectors (top 3),
        avg_amount_range_index, trading_day_distribution.
        """
        empty = {
            "avg_trades_per_month": 0,
            "typical_sectors": [],
            "avg_amount_range_index": 0,
            "trading_day_distribution": {},
        }

        try:
            before_dt = datetime.fromisoformat(before_date)
            twelve_months_ago = (before_dt - timedelta(days=365)).strftime("%Y-%m-%d")

            result = (
                self.supabase.table("trading_disclosures")
                .select(
                    "transaction_date, asset_ticker, asset_name, "
                    "transaction_type, amount_range_min, amount_range_max"
                )
                .ilike("politicians.full_name", f"%{filer}%")
                .gte("transaction_date", twelve_months_ago)
                .lt("transaction_date", before_date)
                .execute()
            )

            rows = result.data or []
            if not rows:
                return empty

            # avg_trades_per_month
            total_trades = len(rows)
            avg_trades_per_month = round(total_trades / 12.0, 2)

            # typical_sectors (top 3 tickers as proxy for sectors)
            tickers = [r.get("asset_ticker", "") for r in rows if r.get("asset_ticker")]
            ticker_counts = Counter(tickers)
            typical_sectors = [t for t, _ in ticker_counts.most_common(3)]

            # avg_amount_range_index
            indices = []
            for row in rows:
                low = row.get("amount_range_min") or 0
                high = row.get("amount_range_max") or 0
                idx = _amount_range_to_index(low, high)
                if idx > 0:
                    indices.append(idx)
            avg_index = round(sum(indices) / len(indices), 2) if indices else 0

            # trading_day_distribution
            day_counts: dict[str, int] = {}
            for row in rows:
                td = row.get("transaction_date", "")
                if td:
                    try:
                        dt = datetime.fromisoformat(str(td).split("T")[0])
                        day_name = dt.strftime("%A")
                        day_counts[day_name] = day_counts.get(day_name, 0) + 1
                    except (ValueError, TypeError):
                        pass

            return {
                "avg_trades_per_month": avg_trades_per_month,
                "typical_sectors": typical_sectors,
                "avg_amount_range_index": avg_index,
                "trading_day_distribution": day_counts,
            }

        except Exception as exc:
            logger.error("Failed to compute baseline stats for %s: %s", filer, exc)
            return empty

    async def _fetch_calendar_events(
        self,
        start: str,
        end: str,
    ) -> list[dict]:
        """Fetch legislative calendar events for the window.

        Placeholder: returns an empty list until a calendar table is available.
        """
        return []

    # --------------------------------------------------------------------- #
    #  Signal storage                                                        #
    # --------------------------------------------------------------------- #

    async def _store_signals(
        self,
        signals: list[dict],
        audit_id: Optional[str] = None,
    ) -> int:
        """Insert detected anomaly signals into llm_anomaly_signals table.

        For signals with confidence >= HIGH_CONFIDENCE_THRESHOLD, also insert
        a row into trading_signals to feed the downstream trading pipeline.

        Returns the count of anomaly signals successfully stored.
        """
        stored = 0

        for signal in signals:
            try:
                signal_id = signal.get("signal_id") or str(uuid.uuid4())
                classification = signal.get("classification", "UNKNOWN")
                confidence = signal.get("confidence", 0)

                row = {
                    "signal_id": signal_id,
                    "filer": signal.get("filer", ""),
                    "classification": classification,
                    "severity": signal.get("severity", "low"),
                    "confidence": confidence,
                    "trades_involved": signal.get("trades_involved", []),
                    "legislative_context": signal.get("legislative_context"),
                    "statistical_evidence": signal.get("statistical_evidence"),
                    "reasoning": signal.get("reasoning", ""),
                    "trading_signal": signal.get("trading_signal"),
                    "self_verification_notes": signal.get("self_verification_notes", ""),
                }

                if audit_id:
                    row["audit_trail_id"] = audit_id

                self.supabase.table("llm_anomaly_signals").insert(row).execute()
                stored += 1

                # High-confidence signals also go to trading_signals
                if confidence >= HIGH_CONFIDENCE_THRESHOLD:
                    self._emit_trading_signal(signal)

            except Exception as exc:
                logger.error("Failed to store anomaly signal %s: %s", signal.get("signal_id"), exc)

        return stored

    def _emit_trading_signal(self, signal: dict) -> None:
        """Insert a high-confidence anomaly into the trading_signals table."""
        try:
            trading_sig = signal.get("trading_signal", {}) or {}
            direction = trading_sig.get("direction", "neutral")
            signal_type = DIRECTION_TO_SIGNAL_TYPE.get(direction, "hold")

            # Pick the first suggested ticker
            tickers = trading_sig.get("suggested_tickers", [])
            ticker = tickers[0] if tickers else ""

            if not ticker:
                # Fall back to first trade involved
                trades = signal.get("trades_involved", [])
                if trades:
                    ticker = trades[0].get("ticker", "")

            if not ticker:
                logger.warning("No ticker for trading signal from anomaly %s", signal.get("signal_id"))
                return

            confidence_score = min(signal.get("confidence", 0) / 10.0, 1.0)

            row = {
                "ticker": ticker,
                "signal_type": signal_type,
                "strength": confidence_score,
                "confidence": confidence_score,
                "source": "llm_anomaly_detection",
                "politician_name": signal.get("filer", ""),
                "analysis": {
                    "classification": signal.get("classification"),
                    "severity": signal.get("severity"),
                    "reasoning": signal.get("reasoning"),
                    "legislative_context": signal.get("legislative_context"),
                    "statistical_evidence": signal.get("statistical_evidence"),
                },
                "is_active": True,
            }

            self.supabase.table("trading_signals").insert(row).execute()

        except Exception as exc:
            logger.error("Failed to emit trading signal: %s", exc)


# --------------------------------------------------------------------------- #
#  Module-level helpers                                                       #
# --------------------------------------------------------------------------- #


def _amount_range_to_index(low: float, high: float) -> int:
    """Map an amount range to an ordinal index (1-10)."""
    if low <= 0 and high <= 0:
        return 0
    mid = (low + high) / 2.0
    for (lo, hi), idx in AMOUNT_RANGE_INDEX.items():
        if lo <= mid <= hi:
            return idx
    # If above all ranges, return the max index
    if mid > 25000001:
        return 10
    return 0
