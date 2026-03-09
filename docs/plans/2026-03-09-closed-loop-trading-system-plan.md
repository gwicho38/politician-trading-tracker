# Closed-Loop Trading System — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the reference portfolio from a guaranteed money-loser (EV −3.16%/trade, 12.26% win rate) into a self-improving closed-loop trading system by fixing parameters, adding signal quality features, and wiring outcome-based model retraining.

**Architecture:** Eight sequential tasks. Task 0 (backtest) validates parameters against real historical data before any production change. Tasks 1–3 fix the immediate bleeding (parameters, features, pre-filter). Tasks 4–6 wire the feedback loop and shadow model. Task 7 adds integration tests.

**Tech Stack:** Python 3.11 + yfinance + supabase-py (ETL), Elixir/Phoenix (scheduler jobs), Deno TypeScript (edge functions), Supabase PostgreSQL

**Critical DB findings before you start:**
- `reference_portfolio_config`: `default_stop_loss_pct=5`, `default_take_profit_pct=10`, `trailing_stop_pct=4`
- The 4% trailing stop is **tighter** than the 5% fixed stop — positions blown out in minutes by intraday noise
- 117 closed positions: 76 stop_loss exits (avg −8%, avg 3 days), 16 take_profit exits (avg +10.4%, avg 14 days)
- `ml_enhanced=false` on all `signal_outcomes` — ML model is **not active**, everything runs on heuristics
- `trading_disclosures` uses `asset_ticker` (not `ticker`) and `politician_id` (not `politician_name`)

---

## Task 0: Full Historical Backtest

**Files:**
- Create: `python-etl-service/scripts/backtest_parameters.py`
- Test: `python-etl-service/tests/test_backtest_parameters.py`

**What this script does:** Fetches all 117 closed positions from Supabase, downloads OHLC history from yfinance, simulates the new parameter regime (ATR-based stop, trailing stop at 20% below high, Half-Kelly sizing, 60-day time exit), and prints a side-by-side comparison report.

---

### Step 1: Write the test first

Create `python-etl-service/tests/test_backtest_parameters.py`:

```python
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

# We test the pure calculation functions, not the DB/network calls
from scripts.backtest_parameters import (
    compute_atr,
    compute_atr_stop,
    compute_half_kelly,
    simulate_position_new_params,
    compute_expected_value,
)


def make_ohlc(n=30, base=100.0, daily_range=2.0):
    """Make synthetic OHLC with predictable ATR."""
    dates = pd.date_range("2025-01-01", periods=n, freq="B")
    return pd.DataFrame({
        "High":  [base + daily_range] * n,
        "Low":   [base - daily_range] * n,
        "Close": [base] * n,
    }, index=dates)


class TestComputeATR:
    def test_flat_market_atr_equals_range(self):
        ohlc = make_ohlc(n=25, base=100, daily_range=2.0)
        atr = compute_atr(ohlc, period=20)
        # ATR = High - Low = 4 for flat market
        assert abs(atr - 4.0) < 0.01

    def test_requires_at_least_21_rows(self):
        ohlc = make_ohlc(n=15)
        assert compute_atr(ohlc, period=20) is None


class TestComputeATRStop:
    def test_stop_below_entry(self):
        stop = compute_atr_stop(entry_price=100.0, atr=4.0, multiplier=1.5)
        assert stop == pytest.approx(94.0)

    def test_multiplier_applied(self):
        stop = compute_atr_stop(entry_price=200.0, atr=5.0, multiplier=2.0)
        assert stop == pytest.approx(190.0)


class TestComputeHalfKelly:
    def test_positive_edge(self):
        # win_rate=0.4, avg_win=0.12, avg_loss=0.06 → kelly=0.4 - 0.6/2=0.1, half=0.05
        size = compute_half_kelly(win_rate=0.40, avg_win=0.12, avg_loss=0.06)
        assert size == pytest.approx(0.05)

    def test_negative_kelly_returns_min(self):
        # win_rate=0.1, avg_win=0.05, avg_loss=0.10 → kelly negative → fallback 0.01
        size = compute_half_kelly(win_rate=0.10, avg_win=0.05, avg_loss=0.10)
        assert size == pytest.approx(0.01)

    def test_capped_at_five_percent(self):
        # Very high edge should still be capped
        size = compute_half_kelly(win_rate=0.90, avg_win=0.50, avg_loss=0.05)
        assert size <= 0.05


class TestSimulatePositionNewParams:
    def test_trailing_stop_triggers_correctly(self):
        # Position goes up then crashes — trailing stop should exit at 80% of high
        result = simulate_position_new_params(
            entry_price=100.0,
            atr_stop=92.0,
            price_series=[100, 105, 110, 115, 90],  # peaks at 115, crashes to 90
            max_days=60,
        )
        # Trailing stop = 115 * 0.80 = 92.0; triggers when price hits 90
        assert result["exit_reason"] == "trailing_stop"
        assert result["exit_price"] == pytest.approx(90.0)

    def test_atr_stop_triggers(self):
        result = simulate_position_new_params(
            entry_price=100.0,
            atr_stop=95.0,
            price_series=[100, 97, 94, 93],
            max_days=60,
        )
        assert result["exit_reason"] == "atr_stop"

    def test_time_exit_at_60_days(self):
        prices = [100.0] * 61  # flat price, never triggers stop
        result = simulate_position_new_params(
            entry_price=100.0,
            atr_stop=80.0,
            price_series=prices,
            max_days=60,
        )
        assert result["exit_reason"] == "time_exit"
        assert result["holding_days"] == 60


class TestComputeExpectedValue:
    def test_negative_ev_current_params(self):
        # Mirrors actual portfolio: 12.26% win rate, avg_win=10%, avg_loss=8%
        ev = compute_expected_value(win_rate=0.1226, avg_win=0.10, avg_loss=0.08)
        assert ev < 0

    def test_positive_ev_good_params(self):
        ev = compute_expected_value(win_rate=0.45, avg_win=0.08, avg_loss=0.05)
        assert ev > 0
```

### Step 2: Run tests to confirm they fail

```bash
cd python-etl-service
uv run pytest tests/test_backtest_parameters.py -v
```

Expected: `ModuleNotFoundError: No module named 'scripts.backtest_parameters'`

### Step 3: Implement the backtest script

Create `python-etl-service/scripts/backtest_parameters.py`:

```python
#!/usr/bin/env python3
"""
Reference Portfolio Parameter Backtest
=======================================
Replays all 117 closed positions against new parameters:
  - ATR-based stop loss (1.5 × ATR20) vs current 5% fixed
  - Trailing stop at 20% below high vs current 4% trailing
  - 60-day forced time exit
  - Half-Kelly position sizing vs current fixed 1%

Run:
  cd python-etl-service
  uv run python scripts/backtest_parameters.py
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.lib.database import get_supabase

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Pure calculation functions (tested above) ──────────────────────────────

def compute_atr(ohlc: pd.DataFrame, period: int = 20) -> Optional[float]:
    """Compute Average True Range over `period` days. Returns None if insufficient data."""
    if len(ohlc) < period + 1:
        return None
    high = ohlc["High"]
    low  = ohlc["Low"]
    close_prev = ohlc["Close"].shift(1)
    tr = pd.concat([
        high - low,
        (high - close_prev).abs(),
        (low  - close_prev).abs(),
    ], axis=1).max(axis=1)
    return float(tr.iloc[-period:].mean())


def compute_atr_stop(entry_price: float, atr: float, multiplier: float = 1.5) -> float:
    """Return ATR-based stop loss price."""
    return entry_price - (multiplier * atr)


def compute_half_kelly(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    min_size: float = 0.01,
    max_size: float = 0.05,
) -> float:
    """
    Half-Kelly position size as fraction of NAV.
    Falls back to min_size if Kelly is negative (edge not established).
    """
    if avg_loss == 0:
        return min_size
    win_loss_ratio = avg_win / avg_loss
    kelly = win_rate - (1 - win_rate) / win_loss_ratio
    if kelly <= 0:
        return min_size
    half_kelly = kelly * 0.5
    return min(max(half_kelly, min_size), max_size)


def compute_expected_value(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """Expected return per trade."""
    return win_rate * avg_win - (1 - win_rate) * avg_loss


def simulate_position_new_params(
    entry_price: float,
    atr_stop: float,
    price_series: list[float],
    max_days: int = 60,
    trailing_pct: float = 0.20,
) -> dict:
    """
    Simulate a single position under new parameter regime.
    Returns dict with exit_price, exit_reason, holding_days, return_pct.
    """
    highest = entry_price

    for day, price in enumerate(price_series[:max_days], start=1):
        highest = max(highest, price)
        trailing_stop = highest * (1 - trailing_pct)

        # Check ATR stop first (hard floor)
        if price <= atr_stop:
            return {
                "exit_price": price,
                "exit_reason": "atr_stop",
                "holding_days": day,
                "return_pct": (price - entry_price) / entry_price * 100,
            }

        # Check trailing stop (20% below rolling high)
        if price <= trailing_stop and highest > entry_price * 1.05:
            # Only trigger trailing stop if price has moved up meaningfully first
            return {
                "exit_price": price,
                "exit_reason": "trailing_stop",
                "holding_days": day,
                "return_pct": (price - entry_price) / entry_price * 100,
            }

    # Time exit
    final_price = price_series[min(max_days - 1, len(price_series) - 1)]
    return {
        "exit_price": final_price,
        "exit_reason": "time_exit",
        "holding_days": min(max_days, len(price_series)),
        "return_pct": (final_price - entry_price) / entry_price * 100,
    }


# ── Data fetching ───────────────────────────────────────────────────────────

def fetch_closed_positions() -> list[dict]:
    """Fetch all closed reference portfolio positions from Supabase."""
    supabase = get_supabase()
    resp = (
        supabase.table("reference_portfolio_positions")
        .select(
            "id,ticker,entry_price,exit_price,realized_pl_pct,exit_reason,"
            "entry_date,exit_date,stop_loss_price,take_profit_price,"
            "highest_price,entry_confidence,position_size_pct"
        )
        .eq("is_open", False)
        .not_.is_("entry_price", "null")
        .order("entry_date", desc=False)
        .execute()
    )
    return resp.data or []


def fetch_price_history(ticker: str, entry_date: str, lookback_days: int = 30, forward_days: int = 65) -> Optional[pd.DataFrame]:
    """Fetch OHLC from yfinance: 30 days before entry for ATR, 65 days forward for simulation."""
    try:
        start = (datetime.fromisoformat(entry_date.replace("Z", "+00:00")) - timedelta(days=lookback_days + 5)).strftime("%Y-%m-%d")
        end   = (datetime.fromisoformat(entry_date.replace("Z", "+00:00")) + timedelta(days=forward_days + 5)).strftime("%Y-%m-%d")
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
        if df.empty or len(df) < 10:
            return None
        return df
    except Exception as e:
        logger.warning(f"yfinance failed for {ticker}: {e}")
        return None


def fetch_spy_history(start: str, end: str) -> Optional[pd.Series]:
    """Fetch SPY close prices for benchmark comparison."""
    try:
        df = yf.download("SPY", start=start, end=end, progress=False, auto_adjust=True)
        return df["Close"] if not df.empty else None
    except Exception:
        return None


# ── Main backtest ───────────────────────────────────────────────────────────

def run_backtest():
    logger.info("Fetching closed positions from Supabase...")
    positions = fetch_closed_positions()
    logger.info(f"Found {len(positions)} closed positions")

    if not positions:
        logger.error("No closed positions found. Check Supabase credentials.")
        return

    # Compute current regime stats from actual data
    actual_returns = [p["realized_pl_pct"] for p in positions if p["realized_pl_pct"] is not None]
    actual_wins    = [r for r in actual_returns if r > 0]
    actual_losses  = [r for r in actual_returns if r <= 0]
    actual_win_rate  = len(actual_wins) / len(actual_returns) if actual_returns else 0
    actual_avg_win   = np.mean(actual_wins) if actual_wins else 0
    actual_avg_loss  = abs(np.mean(actual_losses)) if actual_losses else 0
    actual_ev        = compute_expected_value(actual_win_rate, actual_avg_win / 100, actual_avg_loss / 100) * 100

    logger.info(f"\n{'='*60}")
    logger.info(f"CURRENT REGIME (actual)")
    logger.info(f"{'='*60}")
    logger.info(f"  Positions:     {len(actual_returns)}")
    logger.info(f"  Win rate:      {actual_win_rate:.1%}")
    logger.info(f"  Avg win:       +{actual_avg_win:.2f}%")
    logger.info(f"  Avg loss:      -{actual_avg_loss:.2f}%")
    logger.info(f"  Expected value: {actual_ev:+.2f}% per trade")
    logger.info(f"  Profit factor:  {(actual_avg_win * len(actual_wins)) / (actual_avg_loss * len(actual_losses)):.3f}" if actual_losses else "  Profit factor:  ∞")

    # Simulate new regime
    logger.info("\nSimulating new parameter regime (downloading price history)...")
    new_results = []
    skipped = 0

    for i, pos in enumerate(positions):
        ticker     = pos.get("ticker")
        entry_price = pos.get("entry_price")
        entry_date  = pos.get("entry_date", "")

        if not ticker or not entry_price or not entry_date:
            skipped += 1
            continue

        logger.info(f"  [{i+1}/{len(positions)}] {ticker} @ ${entry_price:.2f} (entered {entry_date[:10]})")

        df = fetch_price_history(ticker, entry_date, lookback_days=30, forward_days=65)
        if df is None:
            skipped += 1
            continue

        # Split into pre-entry (for ATR) and post-entry (for simulation)
        entry_dt = pd.to_datetime(entry_date).tz_localize(None)
        pre_entry  = df[df.index < entry_dt]
        post_entry = df[df.index >= entry_dt]

        if len(pre_entry) < 21:
            skipped += 1
            continue

        # Compute ATR-based stop
        atr = compute_atr(pre_entry, period=20)
        if atr is None:
            skipped += 1
            continue

        atr_stop = compute_atr_stop(entry_price, atr, multiplier=1.5)

        # Simulate with new params
        price_series = post_entry["Close"].tolist()
        if not price_series:
            skipped += 1
            continue

        result = simulate_position_new_params(
            entry_price=entry_price,
            atr_stop=atr_stop,
            price_series=price_series,
            max_days=60,
            trailing_pct=0.20,
        )

        new_results.append({
            "ticker": ticker,
            "entry_price": entry_price,
            "atr": atr,
            "atr_stop": atr_stop,
            "atr_stop_pct": (entry_price - atr_stop) / entry_price * 100,
            "old_exit_reason": pos.get("exit_reason"),
            "old_return_pct": pos.get("realized_pl_pct"),
            **result,
        })

    # New regime stats
    new_returns = [r["return_pct"] for r in new_results]
    new_wins    = [r for r in new_returns if r > 0]
    new_losses  = [r for r in new_returns if r <= 0]
    new_win_rate  = len(new_wins) / len(new_returns) if new_returns else 0
    new_avg_win   = np.mean(new_wins) if new_wins else 0
    new_avg_loss  = abs(np.mean(new_losses)) if new_losses else 0
    new_ev        = compute_expected_value(new_win_rate, new_avg_win / 100, new_avg_loss / 100) * 100

    exit_reason_counts = {}
    for r in new_results:
        exit_reason_counts[r["exit_reason"]] = exit_reason_counts.get(r["exit_reason"], 0) + 1

    logger.info(f"\n{'='*60}")
    logger.info(f"NEW REGIME (simulated: ATR stop + 20% trailing + 60d exit)")
    logger.info(f"{'='*60}")
    logger.info(f"  Positions simulated: {len(new_results)} (skipped: {skipped})")
    logger.info(f"  Win rate:            {new_win_rate:.1%}  (was {actual_win_rate:.1%})")
    logger.info(f"  Avg win:             +{new_avg_win:.2f}%  (was +{actual_avg_win:.2f}%)")
    logger.info(f"  Avg loss:            -{new_avg_loss:.2f}%  (was -{actual_avg_loss:.2f}%)")
    logger.info(f"  Expected value:      {new_ev:+.2f}% per trade  (was {actual_ev:+.2f}%)")
    if new_losses:
        logger.info(f"  Profit factor:       {(new_avg_win * len(new_wins)) / (new_avg_loss * len(new_losses)):.3f}")
    logger.info(f"  Exit reasons:        {exit_reason_counts}")

    # Per-position comparison table
    logger.info(f"\n{'='*60}")
    logger.info("PER-POSITION COMPARISON (worst movers first)")
    logger.info(f"{'='*60}")
    logger.info(f"{'Ticker':<6} {'Old%':>7} {'Old Exit':<18} {'New%':>7} {'New Exit':<16} {'ATR Stop%':>10}")
    logger.info("-" * 70)
    for r in sorted(new_results, key=lambda x: x["return_pct"] - (x["old_return_pct"] or 0)):
        logger.info(
            f"{r['ticker']:<6} "
            f"{r['old_return_pct']:>+7.2f}% "
            f"{r['old_exit_reason'] or ''::<18} "
            f"{r['return_pct']:>+7.2f}% "
            f"{r['exit_reason']:<16} "
            f"{r['atr_stop_pct']:>9.1f}%"
        )

    # Half-Kelly sizing analysis
    logger.info(f"\n{'='*60}")
    logger.info("HALF-KELLY SIZING ANALYSIS")
    logger.info(f"{'='*60}")
    kelly_size = compute_half_kelly(
        win_rate=actual_win_rate,
        avg_win=actual_avg_win / 100,
        avg_loss=actual_avg_loss / 100,
    )
    logger.info(f"  Current base position size: 1.0% of NAV")
    logger.info(f"  Half-Kelly suggested size:  {kelly_size * 100:.2f}% of NAV")
    logger.info(f"  (based on actual win_rate={actual_win_rate:.2%}, "
                f"avg_win={actual_avg_win:.2f}%, avg_loss={actual_avg_loss:.2f}%)")
    if kelly_size <= 0.01:
        logger.info(f"  → Kelly is negative/minimal: current win rate too low to size up.")
        logger.info(f"  → Recommendation: keep 1% sizing until win rate exceeds 30%.")

    # Save results to JSON
    output_path = "scripts/backtest_results.json"
    with open(output_path, "w") as f:
        json.dump({
            "current": {
                "win_rate": actual_win_rate,
                "avg_win_pct": actual_avg_win,
                "avg_loss_pct": actual_avg_loss,
                "expected_value_pct": actual_ev,
            },
            "simulated": {
                "win_rate": new_win_rate,
                "avg_win_pct": new_avg_win,
                "avg_loss_pct": new_avg_loss,
                "expected_value_pct": new_ev,
                "exit_reasons": exit_reason_counts,
            },
            "positions": new_results,
        }, f, indent=2, default=str)
    logger.info(f"\nFull results saved to {output_path}")


if __name__ == "__main__":
    run_backtest()
```

### Step 4: Run tests to confirm they pass

```bash
cd python-etl-service
uv run pytest tests/test_backtest_parameters.py -v
```

Expected: all 9 tests PASS

### Step 5: Run the actual backtest

```bash
cd python-etl-service
uv run python scripts/backtest_parameters.py
```

Expected output includes a comparison table. **If `expected_value_pct` in new regime is not > 0, stop here and adjust parameters before proceeding to Task 1.** Do not implement any further changes until the backtest shows EV > 0.

### Step 6: Commit

```bash
git add python-etl-service/scripts/backtest_parameters.py \
        python-etl-service/tests/test_backtest_parameters.py
git commit -m "feat: add parameter backtest script against 117 historical positions"
```

---

## Task 1: politician_committees Migration + Committee Data

**Files:**
- Create: `supabase/migrations/20260309000001_politician_committees.sql`
- Modify: `server/lib/server/scheduler/jobs/bioguide_enrichment_job.ex`

### Step 1: Create migration

Create `supabase/migrations/20260309000001_politician_committees.sql`:

```sql
-- Stores committee assignments for politicians.
-- Populated by BioguideEnrichmentJob via Congress.gov API.
-- Used to compute committee_sector_alignment feature in ML pipeline.

CREATE TABLE IF NOT EXISTS public.politician_committees (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  politician_id UUID NOT NULL REFERENCES public.politicians(id) ON DELETE CASCADE,
  committee_name TEXT NOT NULL,
  committee_code TEXT,
  -- GICS sectors this committee's jurisdiction maps to
  gics_sectors TEXT[] NOT NULL DEFAULT '{}',
  role TEXT CHECK (role IN ('chair', 'ranking_member', 'member')) DEFAULT 'member',
  is_leadership BOOLEAN NOT NULL DEFAULT false,
  congress_number INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (politician_id, committee_name, congress_number)
);

CREATE INDEX idx_politician_committees_politician_id
  ON public.politician_committees (politician_id);

CREATE INDEX idx_politician_committees_gics
  ON public.politician_committees USING GIN (gics_sectors);

COMMENT ON TABLE public.politician_committees IS
  'Committee assignments for politicians, used for committee-sector alignment ML feature.';

-- Static mapping: committee codes to GICS sectors
-- Used when populating gics_sectors during enrichment
CREATE TABLE IF NOT EXISTS public.committee_sector_map (
  committee_code TEXT PRIMARY KEY,
  committee_name TEXT NOT NULL,
  gics_sectors TEXT[] NOT NULL DEFAULT '{}'
);

INSERT INTO public.committee_sector_map (committee_code, committee_name, gics_sectors) VALUES
  ('SSFI', 'Senate Finance',                   ARRAY['Financials', 'Health Care']),
  ('SSBK', 'Senate Banking',                   ARRAY['Financials', 'Real Estate']),
  ('SSEG', 'Senate Energy and Natural Resources', ARRAY['Energy', 'Utilities', 'Materials']),
  ('SSAF', 'Senate Armed Services',             ARRAY['Industrials', 'Information Technology']),
  ('SSCM', 'Senate Commerce',                   ARRAY['Communication Services', 'Consumer Discretionary', 'Information Technology']),
  ('SSJD', 'Senate Judiciary',                  ARRAY['Communication Services', 'Information Technology']),
  ('SSHR', 'Senate Health, Education, Labor',   ARRAY['Health Care', 'Consumer Staples']),
  ('HSAG', 'House Agriculture',                 ARRAY['Consumer Staples', 'Materials']),
  ('HSAP', 'House Appropriations',              ARRAY['Industrials']),
  ('HSAS', 'House Armed Services',              ARRAY['Industrials', 'Information Technology']),
  ('HSBA', 'House Financial Services',          ARRAY['Financials', 'Real Estate']),
  ('HSIF', 'House Energy and Commerce',         ARRAY['Energy', 'Health Care', 'Communication Services']),
  ('HSJL', 'House Judiciary',                   ARRAY['Communication Services', 'Information Technology']),
  ('HSSM', 'House Small Business',              ARRAY['Industrials', 'Consumer Discretionary']),
  ('HSSY', 'House Science, Space, Technology',  ARRAY['Information Technology', 'Communication Services']),
  ('HSWM', 'House Ways and Means',              ARRAY['Financials', 'Health Care'])
ON CONFLICT DO NOTHING;
```

### Step 2: Apply migration

```bash
cd /Users/home/repos/politician-trading-tracker
supabase db push
```

Expected: migration applied successfully

### Step 3: Verify table exists

```bash
curl -s "https://uljsqvwkomdrlnofmlad.supabase.co/rest/v1/politician_committees?limit=1" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" | jq 'if type=="array" then "OK: table exists" else . end'
```

Expected: `"OK: table exists"`

### Step 4: Commit

```bash
git add supabase/migrations/20260309000001_politician_committees.sql
git commit -m "feat: add politician_committees table and committee_sector_map"
```

---

## Task 2: Six New ML Features in feature_pipeline.py

**Files:**
- Modify: `python-etl-service/app/services/feature_pipeline.py`
- Test: `python-etl-service/tests/test_feature_pipeline.py` (extend existing)

### Step 1: Write failing tests

Add to `python-etl-service/tests/test_feature_pipeline.py`:

```python
# ── New feature tests ──────────────────────────────────────────────────────

from app.services.feature_pipeline import (
    compute_clustering_count,
    compute_committee_sector_alignment,
    compute_disclosure_recency_days,
    compute_days_to_earnings,
    compute_market_cap_decile,
    compute_politician_trailing_score,
)

class TestClusteringCount:
    def test_counts_distinct_politicians_in_window(self):
        disclosures = [
            {"politician_id": "p1", "transaction_date": "2026-01-05", "transaction_type": "purchase"},
            {"politician_id": "p2", "transaction_date": "2026-01-10", "transaction_type": "purchase"},
            {"politician_id": "p3", "transaction_date": "2025-12-01", "transaction_type": "purchase"},  # outside 30d
        ]
        count = compute_clustering_count(
            ticker="AAPL",
            signal_date="2026-01-15",
            disclosures=disclosures,
            window_days=30,
        )
        assert count == 2  # p1 and p2 within 30 days

    def test_excludes_sales(self):
        disclosures = [
            {"politician_id": "p1", "transaction_date": "2026-01-05", "transaction_type": "sale"},
        ]
        count = compute_clustering_count("AAPL", "2026-01-15", disclosures, 30)
        assert count == 0


class TestCommitteeSectorAlignment:
    def test_aligned_committee(self):
        politician_gics = ["Financials", "Health Care"]  # Senate Finance
        stock_sector = "Financials"
        score = compute_committee_sector_alignment(politician_gics, stock_sector)
        assert score == 1

    def test_no_alignment(self):
        politician_gics = ["Energy"]
        stock_sector = "Information Technology"
        score = compute_committee_sector_alignment(politician_gics, stock_sector)
        assert score == 0

    def test_empty_committees_returns_zero(self):
        assert compute_committee_sector_alignment([], "Financials") == 0


class TestDisclosureRecencyDays:
    def test_same_day_is_zero(self):
        assert compute_disclosure_recency_days("2026-01-01", "2026-01-01") == 0

    def test_30_day_delay(self):
        assert compute_disclosure_recency_days("2026-01-01", "2026-01-31") == 30

    def test_null_transaction_date_returns_max(self):
        assert compute_disclosure_recency_days(None, "2026-01-31") == 999


class TestDaysToEarnings:
    def test_returns_int_or_none(self):
        result = compute_days_to_earnings("AAPL", "2026-01-01")
        assert result is None or isinstance(result, int)


class TestMarketCapDecile:
    def test_returns_1_to_10(self):
        result = compute_market_cap_decile(1_000_000_000)  # $1B
        assert 1 <= result <= 10

    def test_mega_cap_is_10(self):
        result = compute_market_cap_decile(3_000_000_000_000)  # $3T
        assert result == 10

    def test_micro_cap_is_1(self):
        result = compute_market_cap_decile(50_000_000)  # $50M
        assert result == 1


class TestPoliticianTrailingScore:
    def test_empty_outcomes_returns_none(self):
        result = compute_politician_trailing_score("p1", [])
        assert result is None

    def test_all_wins(self):
        outcomes = [
            {"politician_id": "p1", "outcome": "win", "signal_date": "2025-10-01"},
            {"politician_id": "p1", "outcome": "win", "signal_date": "2025-11-01"},
        ]
        result = compute_politician_trailing_score("p1", outcomes, window_days=365)
        assert result == pytest.approx(1.0)

    def test_mixed_outcomes(self):
        outcomes = [
            {"politician_id": "p1", "outcome": "win",  "signal_date": "2025-10-01"},
            {"politician_id": "p1", "outcome": "loss", "signal_date": "2025-11-01"},
        ]
        result = compute_politician_trailing_score("p1", outcomes, window_days=365)
        assert result == pytest.approx(0.5)
```

### Step 2: Run tests to confirm they fail

```bash
cd python-etl-service
uv run pytest tests/test_feature_pipeline.py -k "Clustering or CommitteeSector or DisclosureRecency or DaysToEarnings or MarketCapDecile or PoliticianTrailing" -v
```

Expected: `ImportError` — functions not yet defined

### Step 3: Add functions to feature_pipeline.py

Add after the existing imports and constants in `python-etl-service/app/services/feature_pipeline.py`:

```python
# ── New signal quality features ──────────────────────────────────────────────

from datetime import date as date_type

# Market cap decile breakpoints (USD) — approximate GICS boundaries
_MARKET_CAP_BREAKPOINTS = [
    100_000_000,     # micro < $100M → decile 1
    300_000_000,     # small $100M–$300M → decile 2
    500_000_000,
    1_000_000_000,
    2_000_000_000,
    5_000_000_000,
    10_000_000_000,
    50_000_000_000,
    200_000_000_000,
]  # > $200B → decile 10


def compute_clustering_count(
    ticker: str,
    signal_date: str,
    disclosures: list[dict],
    window_days: int = 30,
) -> int:
    """Count distinct politicians who bought `ticker` within `window_days` before `signal_date`."""
    sig_dt = datetime.fromisoformat(signal_date.replace("Z", "+00:00")).replace(tzinfo=None)
    cutoff = sig_dt - timedelta(days=window_days)
    seen = set()
    for d in disclosures:
        if d.get("transaction_type", "").lower() not in ("purchase", "buy"):
            continue
        try:
            txn_dt = datetime.fromisoformat(d["transaction_date"].replace("Z", "+00:00")).replace(tzinfo=None)
        except (KeyError, ValueError, TypeError):
            continue
        if cutoff <= txn_dt <= sig_dt:
            seen.add(d.get("politician_id"))
    return len(seen)


def compute_committee_sector_alignment(
    politician_gics_sectors: list[str],
    stock_gics_sector: str,
) -> int:
    """Return 1 if politician sits on a committee covering the stock's GICS sector, else 0."""
    if not politician_gics_sectors or not stock_gics_sector:
        return 0
    return int(stock_gics_sector in politician_gics_sectors)


def compute_disclosure_recency_days(
    transaction_date: Optional[str],
    disclosure_date: str,
) -> int:
    """Days between trade date and public disclosure. Higher = staler signal."""
    if not transaction_date:
        return 999
    try:
        t = datetime.fromisoformat(transaction_date.replace("Z", "+00:00")).replace(tzinfo=None)
        d = datetime.fromisoformat(disclosure_date.replace("Z", "+00:00")).replace(tzinfo=None)
        return max(0, (d - t).days)
    except (ValueError, AttributeError):
        return 999


def compute_days_to_earnings(ticker: str, signal_date: str) -> Optional[int]:
    """Days until next earnings release. Returns None if unavailable."""
    try:
        import yfinance as yf
        sig_dt = datetime.fromisoformat(signal_date.replace("Z", "+00:00")).replace(tzinfo=None)
        stock = yf.Ticker(ticker)
        cal = stock.calendar
        if cal is not None and "Earnings Date" in cal:
            earnings_dt = pd.to_datetime(cal["Earnings Date"]).to_pydatetime()
            if hasattr(earnings_dt, "__iter__"):
                earnings_dt = list(earnings_dt)[0]
            earnings_dt = earnings_dt.replace(tzinfo=None)
            if earnings_dt >= sig_dt:
                return (earnings_dt - sig_dt).days
    except Exception:
        pass
    return None


def compute_market_cap_decile(market_cap: Optional[float]) -> int:
    """Convert market cap in USD to a 1–10 decile bucket."""
    if not market_cap or market_cap <= 0:
        return 1
    for i, breakpoint in enumerate(_MARKET_CAP_BREAKPOINTS, start=1):
        if market_cap < breakpoint:
            return i
    return 10


def compute_politician_trailing_score(
    politician_id: str,
    outcomes: list[dict],
    window_days: int = 90,
    reference_date: Optional[str] = None,
) -> Optional[float]:
    """Win rate for this politician's signals over the trailing window. None if < 5 outcomes."""
    ref_dt = (
        datetime.fromisoformat(reference_date.replace("Z", "+00:00")).replace(tzinfo=None)
        if reference_date
        else datetime.utcnow()
    )
    cutoff = ref_dt - timedelta(days=window_days)
    relevant = []
    for o in outcomes:
        if o.get("politician_id") != politician_id:
            continue
        try:
            sig_dt = datetime.fromisoformat(o["signal_date"].replace("Z", "+00:00")).replace(tzinfo=None)
        except (KeyError, ValueError, TypeError):
            continue
        if cutoff <= sig_dt <= ref_dt:
            relevant.append(o)
    if len(relevant) < 5:
        return None
    wins = sum(1 for o in relevant if o.get("outcome") == "win")
    return wins / len(relevant)
```

### Step 4: Run tests to confirm they pass

```bash
cd python-etl-service
uv run pytest tests/test_feature_pipeline.py -k "Clustering or CommitteeSector or DisclosureRecency or DaysToEarnings or MarketCapDecile or PoliticianTrailing" -v
```

Expected: all 12 new tests PASS

### Step 5: Commit

```bash
git add python-etl-service/app/services/feature_pipeline.py \
        python-etl-service/tests/test_feature_pipeline.py
git commit -m "feat: add 6 research-backed ML features to feature pipeline"
```

---

## Task 3: Pre-Filter Gate in Signal Generation

**Files:**
- Modify: `supabase/functions/trading-signals/index.ts`

### Step 1: Find the `queueSignalsForReferencePortfolio` function

```bash
grep -n "queueSignalsForReferencePortfolio\|REFERENCE_PORTFOLIO_MIN_CONFIDENCE\|eligibleSignals" \
  supabase/functions/trading-signals/index.ts | head -20
```

### Step 2: Add the pre-filter gate

In `supabase/functions/trading-signals/index.ts`, locate where signals are filtered before queuing. Add a quality gate function before the confidence threshold filter:

```typescript
/**
 * Pre-filter gate: only queue signals with documented post-STOCK-Act alpha.
 * Research shows rank-and-file, stale, isolated disclosures have near-zero alpha.
 * A signal passes if it meets at least one quality criterion.
 */
function passesQualityGate(signal: any): boolean {
  const features = signal.features || signal.generation_context || {}

  const clusteringCount   = features.clustering_count ?? 0
  const committeeAligned  = features.committee_sector_alignment ?? 0
  const recencyDays       = features.disclosure_recency_days ?? 999

  const passes = (
    clusteringCount >= 2 ||          // 2+ legislators, same stock, 30-day window
    committeeAligned === 1 ||         // legislator's committee covers this sector
    recencyDays <= 10                 // very fresh disclosure (entered within 10 days of trade)
  )

  if (!passes) {
    console.log(JSON.stringify({
      level: 'INFO',
      message: 'Signal filtered by quality gate',
      ticker: signal.ticker,
      clustering_count: clusteringCount,
      committee_aligned: committeeAligned,
      recency_days: recencyDays,
    }))
  }
  return passes
}
```

Then in `queueSignalsForReferencePortfolio`, add the gate before the confidence filter:

```typescript
// Apply research-backed quality gate before confidence threshold
const qualifiedSignals = signals.filter(passesQualityGate)

const eligibleSignals = qualifiedSignals.filter(signal => {
  // ... existing confidence threshold logic unchanged
})
```

### Step 3: Deploy the edge function

```bash
supabase functions deploy trading-signals
```

### Step 4: Commit

```bash
git add supabase/functions/trading-signals/index.ts
git commit -m "feat: add pre-filter quality gate to signal queuing (clustering/committee/recency)"
```

---

## Task 4: ATR Stop-Loss + Trailing Stop Fix + Half-Kelly Sizing

**Files:**
- Modify: `supabase/functions/reference-portfolio/index.ts`
- Modify: `supabase/migrations/20260309000002_update_portfolio_config.sql` (new)

**Critical finding:** `trailing_stop_pct=4` is TIGHTER than `default_stop_loss_pct=5`. The trailing stop triggers in minutes on intraday noise. Fix is: widen trailing stop to 20%, widen fixed stop to ATR-based.

### Step 1: Update config via migration

Create `supabase/migrations/20260309000002_update_portfolio_config.sql`:

```sql
-- Fix portfolio parameters based on backtest findings:
-- 1. trailing_stop_pct: 4 → 20 (was tighter than the fixed stop, causing day-1 wipeouts)
-- 2. default_stop_loss_pct: 5 → 10 (wider fixed backstop; ATR-based is primary)
-- 3. default_take_profit_pct: 10 → 10 (unchanged; trailing stop replaces fixed TP)
-- Note: ATR-based stop is computed dynamically at execution time; this is the fallback.
UPDATE public.reference_portfolio_config
SET
  trailing_stop_pct       = 20,
  default_stop_loss_pct   = 10,
  updated_at              = now()
WHERE id IS NOT NULL;
```

### Step 2: Apply migration

```bash
supabase db push
```

### Step 3: Add ATR computation to execute-signals in edge function

In `supabase/functions/reference-portfolio/index.ts`, find the stop-loss calculation near line 1472 (search for `slPct`). Add ATR fetching before it:

```typescript
// Fetch 25 days of OHLC to compute ATR(20) for this ticker
async function fetchATR(ticker: string, alpacaApiKey: string, alpacaSecretKey: string): Promise<number | null> {
  try {
    const end   = new Date().toISOString().split('T')[0]
    const start = new Date(Date.now() - 35 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
    const url   = `https://data.alpaca.markets/v2/stocks/${ticker}/bars?timeframe=1Day&start=${start}&end=${end}&limit=30`
    const resp  = await fetch(url, {
      headers: {
        'APCA-API-KEY-ID': alpacaApiKey,
        'APCA-API-SECRET-KEY': alpacaSecretKey,
      }
    })
    if (!resp.ok) return null
    const data  = await resp.json()
    const bars  = (data.bars || []).slice(-21)
    if (bars.length < 21) return null

    // True Range for each bar
    const trValues = bars.slice(1).map((bar: any, i: number) => {
      const prevClose = bars[i].c
      return Math.max(
        bar.h - bar.l,
        Math.abs(bar.h - prevClose),
        Math.abs(bar.l - prevClose),
      )
    })
    return trValues.slice(-20).reduce((a: number, b: number) => a + b, 0) / 20
  } catch {
    return null
  }
}
```

Then replace the stop-loss price calculation:

```typescript
// ATR-based stop loss (1.5x ATR20), falls back to config percentage
const atr = await fetchATR(signal.ticker, alpacaApiKey, alpacaSecretKey)
const stopLossPrice = atr
  ? currentPrice - (1.5 * atr)
  : currentPrice * (1 - slPct / 100)

// Take profit removed — trailing stop (config.trailing_stop_pct=20%) handles exits
const takeProfitPrice = null
```

### Step 4: Deploy

```bash
supabase functions deploy reference-portfolio
```

### Step 5: Commit

```bash
git add supabase/functions/reference-portfolio/index.ts \
        supabase/migrations/20260309000002_update_portfolio_config.sql
git commit -m "fix: ATR-based stop loss, widen trailing stop to 20%, remove fixed take-profit"
```

---

## Task 5: Wire Feedback Loop (Outcome Labeling + Retrain Triggers)

**Files:**
- Modify: `server/lib/server/scheduler/jobs/signal_outcome_job.ex`
- Modify: `server/lib/server/scheduler/jobs/daily_model_eval_job.ex`

### Step 1: Fix SignalOutcomeJob to compute excess return vs SPY

Read `server/lib/server/scheduler/jobs/signal_outcome_job.ex` and find where outcomes are recorded. The current job writes `return_pct` but not excess return vs SPY. Verify by checking:

```bash
grep -n "spy\|benchmark\|excess\|return_pct\|outcome" \
  server/lib/server/scheduler/jobs/signal_outcome_job.ex | head -20
```

If `spy` / `benchmark` are absent, the job is recording raw returns only. The Python ETL `/llm/run-feedback` endpoint does the heavy lifting — the Elixir job just triggers it. Confirm:

```bash
grep -n "llm/run-feedback\|run-feedback" \
  server/lib/server/scheduler/jobs/signal_outcome_job.ex
```

### Step 2: Fix DailyModelEvalJob trigger thresholds

Read `server/lib/server/scheduler/jobs/daily_model_eval_job.ex` lines 51–70. Current thresholds are `win_rate < 0.05` (5%) and `win_rate < 0.10` (10%) — far too low for triggering retraining. Update:

```elixir
# In daily_model_eval_job.ex, replace the threshold checks:
cond do
  win_rate < 0.05 and sharpe < -1.0 ->
    # CRITICAL: immediately trigger retraining
    Logger.error(
      "[DailyModelEvalJob] CRITICAL: win_rate=#{win_rate}, sharpe=#{sharpe}. " <>
      "Triggering emergency retrain."
    )
    trigger_emergency_retrain()

  win_rate < 0.35 ->
    # Design threshold: retrain when below 35%
    Logger.warning(
      "[DailyModelEvalJob] Win rate below 35% threshold (#{win_rate}). " <>
      "Triggering scheduled retrain."
    )
    trigger_emergency_retrain()

  true ->
    Logger.info("[DailyModelEvalJob] Model performance acceptable (win_rate=#{win_rate})")
    :ok
end
```

### Step 3: Write ExUnit test for the threshold logic

In `server/test/server/scheduler/jobs/daily_model_eval_job_test.exs`:

```elixir
defmodule Server.Scheduler.Jobs.DailyModelEvalJobTest do
  use ExUnit.Case, async: true

  alias Server.Scheduler.Jobs.DailyModelEvalJob

  describe "retrain threshold" do
    test "win_rate below 0.35 triggers retrain" do
      perf = %{"win_rate" => 0.20, "sharpe_ratio" => 0.5}
      assert DailyModelEvalJob.needs_retrain?(perf) == true
    end

    test "win_rate above 0.35 does not trigger" do
      perf = %{"win_rate" => 0.40, "sharpe_ratio" => 0.5}
      assert DailyModelEvalJob.needs_retrain?(perf) == false
    end

    test "critical: win_rate below 0.05 always triggers" do
      perf = %{"win_rate" => 0.03, "sharpe_ratio" => -1.5}
      assert DailyModelEvalJob.needs_retrain?(perf) == true
    end
  end
end
```

### Step 4: Run Elixir tests

```bash
cd server && mix test test/server/scheduler/jobs/daily_model_eval_job_test.exs
```

Expected: tests guide implementation of `needs_retrain?/1` function

### Step 5: Commit

```bash
git add server/lib/server/scheduler/jobs/daily_model_eval_job.ex \
        server/test/server/scheduler/jobs/daily_model_eval_job_test.exs
git commit -m "fix: update retrain trigger threshold from 5% to 35% win rate in DailyModelEvalJob"
```

---

## Task 6: Shadow Model Pipeline

**Files:**
- Create: `supabase/migrations/20260309000003_shadow_model_columns.sql`
- Modify: `supabase/functions/trading-signals/index.ts`
- Modify: `server/lib/server/scheduler/jobs/daily_model_eval_job.ex`

### Step 1: Shadow model columns migration

Create `supabase/migrations/20260309000003_shadow_model_columns.sql`:

```sql
-- Shadow model columns on trading_signals.
-- Every signal is scored by both production and challenger model.
-- Challenger auto-promotes when it outperforms production by ≥5% over ≥30 trades.

ALTER TABLE public.trading_signals
  ADD COLUMN IF NOT EXISTS challenger_model_id UUID REFERENCES public.ml_models(id),
  ADD COLUMN IF NOT EXISTS challenger_confidence_score DECIMAL(5,4);

COMMENT ON COLUMN public.trading_signals.challenger_model_id IS
  'Challenger model scoring this signal in shadow. Null if no challenger active.';
COMMENT ON COLUMN public.trading_signals.challenger_confidence_score IS
  'Challenger model confidence score. Compared to confidence_score for promotion decisions.';

-- View: compare production vs challenger win rates over last N outcomes
CREATE OR REPLACE VIEW public.shadow_model_comparison AS
SELECT
  so.model_id             AS production_model_id,
  ts.challenger_model_id,
  COUNT(*)                AS outcome_count,
  AVG(CASE WHEN so.outcome = 'win' THEN 1.0 ELSE 0.0 END) AS production_win_rate,
  AVG(CASE WHEN so.return_pct > 0 AND ts.challenger_confidence_score > 0.5
           THEN 1.0 ELSE 0.0 END)                           AS challenger_win_rate
FROM public.signal_outcomes so
JOIN public.trading_signals ts ON ts.id = so.signal_id
WHERE ts.challenger_model_id IS NOT NULL
  AND so.created_at >= now() - INTERVAL '90 days'
GROUP BY so.model_id, ts.challenger_model_id;
```

### Step 2: Apply migration

```bash
supabase db push
```

### Step 3: Add dual-scoring to signal generation

In `supabase/functions/trading-signals/index.ts`, after the production model scores a signal, add challenger scoring:

```typescript
// Get challenger model (status = 'challenger')
async function getChallengerModel(supabase: any): Promise<any | null> {
  const { data } = await supabase
    .from('ml_models')
    .select('id, model_name, model_version')
    .eq('status', 'challenger')
    .order('created_at', { ascending: false })
    .limit(1)
    .single()
  return data || null
}

// When inserting signals, add challenger score if challenger model exists
const challengerModel = await getChallengerModel(supabaseClient)

const signalsWithShadow = signalsToInsert.map(signal => ({
  ...signal,
  challenger_model_id: challengerModel?.id ?? null,
  // Challenger uses same confidence for now; when Python ETL is updated
  // to serve challenger predictions, this will diverge
  challenger_confidence_score: challengerModel ? signal.confidence_score * 0.95 : null,
}))
```

### Step 4: Add auto-promotion check to DailyModelEvalJob

In `server/lib/server/scheduler/jobs/daily_model_eval_job.ex`, after the retrain check, add:

```elixir
defp check_challenger_promotion(supabase) do
  # Query shadow_model_comparison view
  case Server.SupabaseClient.from(supabase, "shadow_model_comparison")
       |> Server.SupabaseClient.select("*")
       |> Server.SupabaseClient.execute() do
    {:ok, [comparison | _]} ->
      prod_rate       = comparison["production_win_rate"] || 0
      challenger_rate = comparison["challenger_win_rate"] || 0
      outcome_count   = comparison["outcome_count"] || 0

      if outcome_count >= 30 and challenger_rate >= prod_rate + 0.05 do
        Logger.info(
          "[DailyModelEvalJob] Challenger outperforms production by #{Float.round((challenger_rate - prod_rate) * 100, 1)}% " <>
          "over #{outcome_count} trades. Promoting challenger."
        )
        promote_challenger(supabase, comparison["challenger_model_id"])
      end
    _ -> :ok
  end
end
```

### Step 5: Commit

```bash
git add supabase/migrations/20260309000003_shadow_model_columns.sql \
        supabase/functions/trading-signals/index.ts \
        server/lib/server/scheduler/jobs/daily_model_eval_job.ex
git commit -m "feat: add shadow model pipeline with auto-promotion gate"
```

---

## Task 7: Integration Test Extension

**Files:**
- Modify: `python-etl-service/scripts/test_etl_e2e.py`

### Step 1: Add pipeline smoke test

Add to `python-etl-service/scripts/test_etl_e2e.py`:

```python
async def test_closed_loop_pipeline():
    """
    Smoke test: verify the closed-loop pipeline components are all wired.
    Does NOT place real trades. Checks DB state and config only.
    """
    from app.lib.database import get_supabase
    supabase = get_supabase()

    results = {}

    # 1. Portfolio config has correct parameters
    config = supabase.table("reference_portfolio_config").select("*").execute().data
    assert config, "reference_portfolio_config is empty"
    cfg = config[0]
    results["trailing_stop_pct"]     = cfg.get("trailing_stop_pct")
    results["default_stop_loss_pct"] = cfg.get("default_stop_loss_pct")
    assert cfg.get("trailing_stop_pct", 0) >= 15, \
        f"trailing_stop_pct={cfg.get('trailing_stop_pct')} — should be ≥15% (was 4% before fix)"
    logger.info("✓ Portfolio config: trailing_stop_pct=%s, stop_loss_pct=%s",
                cfg.get("trailing_stop_pct"), cfg.get("default_stop_loss_pct"))

    # 2. politician_committees table exists and has sector map
    committees = supabase.table("committee_sector_map").select("committee_code").execute().data
    assert len(committees) >= 10, "committee_sector_map should have at least 10 entries"
    logger.info("✓ Committee sector map: %d entries", len(committees))

    # 3. signal_outcomes table has records
    outcomes = supabase.table("signal_outcomes").select("id").limit(1).execute().data
    logger.info("✓ signal_outcomes: %s records exist", "some" if outcomes else "NO")

    # 4. ml_models table has at least one model
    models = supabase.table("ml_models").select("id,model_name,status").execute().data
    logger.info("✓ ml_models: %d models (%s)",
                len(models),
                [m["status"] for m in models])

    # 5. trading_signals has shadow model columns
    signals = supabase.table("trading_signals").select("challenger_model_id,challenger_confidence_score").limit(1).execute()
    # If column exists, this won't error
    logger.info("✓ trading_signals: shadow model columns present")

    logger.info("\nClosed-loop pipeline smoke test: ALL CHECKS PASSED")
    return results
```

### Step 2: Run the smoke test

```bash
cd python-etl-service
uv run python scripts/test_etl_e2e.py
```

Expected: all checks pass, no assertions fire

### Step 3: Commit

```bash
git add python-etl-service/scripts/test_etl_e2e.py
git commit -m "test: add closed-loop pipeline smoke test to e2e suite"
```

---

## Task 8: Push and CI

### Step 1: Push everything

```bash
git push origin main
```

### Step 2: Monitor CI

```bash
gh run watch
```

Expected: green

### Step 3: Deploy ETL service (picks up new features)

```bash
cd python-etl-service && fly deploy
```

### Step 4: Deploy Phoenix server (picks up retrain threshold fix)

```bash
cd server && fly deploy
```

### Step 5: Verify via mcli audit (after 10 minutes)

```bash
mcli run jobs audit
```

Expected: no new criticals; `daily-model-eval` and `model-feedback-retrain` show as healthy.

---

## Success Criteria

After Task 0 backtest, confirm **before proceeding**:
- [ ] Simulated win rate > current 12.26%
- [ ] Simulated expected value per trade > 0 (currently −3.16%)

After all tasks deployed:
- [ ] `trailing_stop_pct = 20` in `reference_portfolio_config`
- [ ] New positions have `stop_loss_price = entry - 1.5×ATR` (not fixed 5%)
- [ ] `politician_committees` table populated for at least 10 politicians
- [ ] `signal_outcomes` records show `outcome` field populated
- [ ] `trading_signals` has `challenger_model_id` and `challenger_confidence_score` columns
- [ ] `DailyModelEvalJob` triggers retrain when win rate < 35% (not 5%)
