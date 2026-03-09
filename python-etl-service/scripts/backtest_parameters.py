"""
Backtest script: evaluate proposed trading parameters against 117 historical
closed positions in reference_portfolio_positions.

Run from python-etl-service/:
    uv run python scripts/backtest_parameters.py

Proposed parameter changes vs current config:
  Current:  stop_loss_pct=5%, take_profit_pct=10%, trailing_stop_pct=4%
  Proposed: ATR-based stop (1.5×ATR), trailing_stop_pct=20%

The current trailing stop (4%) fires almost immediately after entry, which
explains the 4 trailing_stop exits with avg -9.9% return (contradicts a
trailing stop's purpose of locking in gains).
"""

import sys
import os
import json
import logging
from datetime import datetime, timedelta, date
from typing import Optional

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Make `app` importable when running as a standalone script
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ETL_ROOT = os.path.dirname(_SCRIPT_DIR)
if _ETL_ROOT not in sys.path:
    sys.path.insert(0, _ETL_ROOT)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================
# Pure calculation functions (unit-tested)
# ============================================================

def compute_atr(ohlc: pd.DataFrame, period: int = 20) -> Optional[float]:
    """Compute Average True Range over `period` bars.

    Args:
        ohlc: DataFrame with columns Open, High, Low, Close (chronological).
        period: ATR period.

    Returns:
        ATR value as a float, or None if insufficient rows (<= period).
    """
    if len(ohlc) <= period:
        return None

    high = ohlc["High"].values
    low = ohlc["Low"].values
    close = ohlc["Close"].values

    tr_list = []
    for i in range(1, len(ohlc)):
        hl = high[i] - low[i]
        hpc = abs(high[i] - close[i - 1])
        lpc = abs(low[i] - close[i - 1])
        tr_list.append(max(hl, hpc, lpc))

    tr = np.array(tr_list)
    # Use the last `period` true-range values (simple average for first ATR, then EMA)
    if len(tr) < period:
        return None
    return float(np.mean(tr[-period:]))


def compute_atr_stop(entry_price: float, atr: float, multiplier: float = 1.5) -> float:
    """Compute ATR-based stop-loss price.

    Args:
        entry_price: Price at which the position was opened.
        atr: ATR value computed before entry.
        multiplier: How many ATRs below entry to set the stop.

    Returns:
        Stop-loss price = entry_price - multiplier * atr.
    """
    return entry_price - multiplier * atr


def compute_half_kelly(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    min_size: float = 0.01,
    max_size: float = 0.05,
) -> float:
    """Compute Half-Kelly position size as a fraction of portfolio.

    Kelly formula: f = win_rate - (1 - win_rate) / (avg_win / avg_loss)
    Half-Kelly:    f* = f / 2

    Args:
        win_rate: Fraction of trades that are winners [0, 1].
        avg_win: Average return on winning trades (positive decimal).
        avg_loss: Average loss on losing trades (positive decimal).
        min_size: Floor position size when Kelly <= 0.
        max_size: Ceiling position size.

    Returns:
        Half-Kelly position size clamped to [min_size, max_size].
    """
    if avg_loss == 0 or avg_win == 0:
        return min_size

    win_loss_ratio = avg_win / avg_loss
    kelly = win_rate - (1 - win_rate) / win_loss_ratio
    half_kelly = kelly * 0.5

    if half_kelly <= 0:
        return min_size
    return min(half_kelly, max_size)


def compute_expected_value(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """Compute expected value per trade.

    EV = win_rate * avg_win - (1 - win_rate) * avg_loss

    Args:
        win_rate: Fraction of trades that are winners.
        avg_win: Average return on winning trades (positive decimal).
        avg_loss: Average loss on losing trades (positive decimal, i.e. abs value).

    Returns:
        Expected value per trade as a decimal.
    """
    return win_rate * avg_win - (1 - win_rate) * avg_loss


def simulate_position_new_params(
    entry_price: float,
    atr_stop: float,
    price_series: list,
    max_days: int = 60,
    trailing_pct: float = 0.20,
) -> dict:
    """Simulate a position using ATR-based stop + trailing stop + time exit.

    Exit logic (priority order):
      1. ATR stop: if price <= atr_stop, exit immediately (hard floor).
      2. Trailing stop: only activates AFTER price has moved up >5% from entry.
         Trailing stop price = highest_price * (1 - trailing_pct).
         This prevents the stop from triggering on an immediate intraday dip.
      3. Time exit: exit after max_days days (use final price in series).

    Args:
        entry_price: Price at entry (day 0).
        atr_stop: Hard stop-loss price level (ATR-based).
        price_series: Sequence of daily close prices starting from entry day.
                      price_series[0] should equal (or be close to) entry_price.
        max_days: Maximum holding period in days.
        trailing_pct: Trailing stop as a fraction below the highest observed price.
                      e.g. 0.20 means stop = highest * 0.80.

    Returns:
        dict with keys:
            exit_price (float)
            exit_reason (str): 'atr_stop' | 'trailing_stop' | 'time_exit'
            holding_days (int): number of days held (1-based index of exit bar)
            return_pct (float): (exit_price - entry_price) / entry_price
    """
    highest_price = entry_price
    trailing_armed = False  # becomes True once price > entry * 1.05

    days_to_simulate = min(len(price_series), max_days)

    for day_idx in range(days_to_simulate):
        price = price_series[day_idx]

        # Update highest observed price
        if price > highest_price:
            highest_price = price

        # Arm trailing stop once price moves up more than 5% from entry
        if not trailing_armed and highest_price > entry_price * 1.05:
            trailing_armed = True

        # 1) ATR stop (hard floor — checked first)
        if price <= atr_stop:
            return {
                "exit_price": float(price),
                "exit_reason": "atr_stop",
                "holding_days": day_idx,
                "return_pct": (price - entry_price) / entry_price,
            }

        # 2) Trailing stop (only if armed)
        if trailing_armed:
            trailing_stop_price = highest_price * (1 - trailing_pct)
            if price <= trailing_stop_price:
                return {
                    "exit_price": float(price),
                    "exit_reason": "trailing_stop",
                    "holding_days": day_idx,
                    "return_pct": (price - entry_price) / entry_price,
                }

    # 3) Time exit — use last available price up to max_days
    exit_idx = days_to_simulate - 1
    exit_price = float(price_series[exit_idx])
    return {
        "exit_price": exit_price,
        "exit_reason": "time_exit",
        "holding_days": days_to_simulate - 1,
        "return_pct": (exit_price - entry_price) / entry_price,
    }


# ============================================================
# Data-fetching helpers
# ============================================================

def fetch_closed_positions() -> list[dict]:
    """Fetch all closed positions from reference_portfolio_positions."""
    from app.lib.database import get_supabase

    client = get_supabase()
    if not client:
        raise RuntimeError("Could not create Supabase client — check SUPABASE_URL and SUPABASE_SERVICE_KEY env vars")

    response = (
        client.table("reference_portfolio_positions")
        .select(
            "id, ticker, entry_price, entry_date, exit_price, exit_date, "
            "realized_pl_pct, exit_reason, is_open"
        )
        .eq("is_open", False)
        .execute()
    )
    positions = response.data or []
    logger.info("Fetched %d closed positions", len(positions))
    return positions


def _parse_entry_date(entry_date_str: str) -> Optional[date]:
    """Parse entry_date from various formats DB may return.

    Handles:
      - '2024-03-15'
      - '2026-01-08T15:00:05.598+00:00'   (ISO 8601 with timezone)
      - '2026-01-08T15:00:05.598Z'
      - '2026-01-08 15:00:05'
    """
    if not entry_date_str:
        return None
    # Normalize: strip everything after the date portion if it contains 'T' or space
    s = str(entry_date_str).strip()
    # Take just the date part (first 10 chars of an ISO string)
    date_part = s[:10]
    try:
        return datetime.strptime(date_part, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def fetch_price_history(ticker: str, entry_date_str: str) -> Optional[pd.DataFrame]:
    """Download OHLC price history for ATR calculation and simulation.

    Downloads:
      - 30 calendar days BEFORE entry_date → used for ATR calculation
      - 65 calendar days AFTER  entry_date → used for simulation (covers max_days=60)

    Args:
        ticker: Stock ticker symbol.
        entry_date_str: ISO date string of position entry (e.g. '2024-03-15' or
                        '2026-01-08T15:00:05.598+00:00').

    Returns:
        DataFrame with columns [Open, High, Low, Close] indexed by Date, or None on error.
    """
    import yfinance as yf

    entry_date = _parse_entry_date(entry_date_str)
    if entry_date is None:
        logger.warning("Invalid entry_date '%s' for %s", entry_date_str, ticker)
        return None

    start = entry_date - timedelta(days=35)   # extra buffer for weekends/holidays
    end = entry_date + timedelta(days=70)      # extra buffer for weekends/holidays

    try:
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
        if df.empty:
            logger.warning("No price data for %s", ticker)
            return None

        # yfinance may return multi-index columns for single ticker in some versions
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df[["Open", "High", "Low", "Close"]].dropna()
        df.index = pd.to_datetime(df.index).date
        return df

    except Exception as exc:
        logger.warning("Error fetching price data for %s: %s", ticker, exc)
        return None


# ============================================================
# Regime stats helpers
# ============================================================

def _compute_regime_stats(positions: list[dict]) -> dict:
    """Compute current regime win_rate, avg_win, avg_loss from realized P&L.

    realized_pl_pct is stored as percentage units (e.g. -6.91 = -6.91%).
    We convert to decimal fractions (÷100) for all calculations so that
    EV / Half-Kelly formulas work correctly with standard decimal inputs.
    """
    returns = []
    for p in positions:
        pnl = p.get("realized_pl_pct")
        if pnl is not None:
            try:
                # Convert from percentage to decimal fraction
                returns.append(float(pnl) / 100.0)
            except (ValueError, TypeError):
                pass

    if not returns:
        return {"win_rate": 0.0, "avg_win": 0.0, "avg_loss": 0.0, "n": 0}

    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]

    win_rate = len(wins) / len(returns) if returns else 0.0
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = float(abs(np.mean(losses))) if losses else 0.0

    return {
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "n": len(returns),
        "n_wins": len(wins),
        "n_losses": len(losses),
        "all_returns": returns,
    }


# ============================================================
# Main backtest runner
# ============================================================

def run_backtest() -> None:
    """Run full backtest: fetch positions, simulate new params, compare."""
    from dotenv import load_dotenv

    # Load .env from project root (two levels up from scripts/)
    _project_root = os.path.dirname(os.path.dirname(_ETL_ROOT))
    env_path = os.path.join(_project_root, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
        logger.info("Loaded .env from %s", env_path)
    else:
        load_dotenv()  # fallback to cwd or environment

    # ------------------------------------------------------------------
    # 1. Fetch closed positions
    # ------------------------------------------------------------------
    positions = fetch_closed_positions()
    if not positions:
        logger.error("No closed positions found.")
        return

    # ------------------------------------------------------------------
    # 2. Compute current regime stats from realized P&L
    # ------------------------------------------------------------------
    current_stats = _compute_regime_stats(positions)
    current_ev = compute_expected_value(
        current_stats["win_rate"], current_stats["avg_win"], current_stats["avg_loss"]
    )
    current_kelly = compute_half_kelly(
        current_stats["win_rate"], current_stats["avg_win"], current_stats["avg_loss"]
    )

    print("\n" + "=" * 70)
    print("CURRENT REGIME (actual realized P&L from 117 closed positions)")
    print("=" * 70)
    print(f"  Positions analysed : {current_stats['n']}")
    print(f"  Win rate           : {current_stats['win_rate']:.1%}  ({current_stats['n_wins']} wins / {current_stats['n_losses']} losses)")
    print(f"  Avg win            : {current_stats['avg_win']:.2%}")
    print(f"  Avg loss           : {current_stats['avg_loss']:.2%}")
    print(f"  Expected value (EV): {current_ev:+.4f}  ({'NEGATIVE ⚠' if current_ev < 0 else 'POSITIVE ✓'})")
    print(f"  Half-Kelly size    : {current_kelly:.2%}")

    # ------------------------------------------------------------------
    # 3. Simulate each position with new parameters
    # ------------------------------------------------------------------
    ATR_PERIOD = 20
    ATR_MULTIPLIER = 1.5
    NEW_TRAILING_PCT = 0.20
    MAX_DAYS = 60

    simulated_returns = []
    skipped = 0
    per_position_results = []

    logger.info("Simulating %d positions with new params (ATR×%.1f, trailing=%.0f%%)...",
                len(positions), ATR_MULTIPLIER, NEW_TRAILING_PCT * 100)

    for pos in positions:
        ticker = pos.get("ticker", "")
        entry_date_raw = pos.get("entry_date", "")
        entry_price_raw = pos.get("entry_price")
        actual_pnl = pos.get("realized_pl_pct")

        if not ticker or not entry_date_raw or entry_price_raw is None:
            skipped += 1
            continue

        # Parse entry date (handles full ISO timestamps)
        entry_dt = _parse_entry_date(entry_date_raw)
        if entry_dt is None:
            logger.debug("Skipping %s — unparseable entry_date: %s", ticker, entry_date_raw)
            skipped += 1
            continue

        # Use normalized date string for yfinance
        entry_date = entry_dt.isoformat()

        try:
            entry_price = float(entry_price_raw)
        except (ValueError, TypeError):
            skipped += 1
            continue

        # Fetch OHLC
        ohlc = fetch_price_history(ticker, entry_date)
        if ohlc is None or ohlc.empty:
            skipped += 1
            continue

        # Split: pre-entry rows for ATR, post-entry rows for simulation
        pre_entry = ohlc[ohlc.index < entry_dt]
        post_entry = ohlc[ohlc.index >= entry_dt]

        if len(pre_entry) < ATR_PERIOD + 1:
            skipped += 1
            continue

        atr = compute_atr(pre_entry, period=ATR_PERIOD)
        if atr is None:
            skipped += 1
            continue

        atr_stop = compute_atr_stop(entry_price, atr, multiplier=ATR_MULTIPLIER)

        if post_entry.empty:
            skipped += 1
            continue

        price_series = post_entry["Close"].tolist()
        sim = simulate_position_new_params(
            entry_price=entry_price,
            atr_stop=atr_stop,
            price_series=price_series,
            max_days=MAX_DAYS,
            trailing_pct=NEW_TRAILING_PCT,
        )

        simulated_returns.append(sim["return_pct"])

        # Record per-position comparison
        # realized_pl_pct is in percentage units (e.g. -25.16 = -25.16%)
        # convert to decimal fraction for consistency with sim_return_pct
        actual_pnl_decimal = float(actual_pnl) / 100.0 if actual_pnl is not None else 0.0
        improvement = sim["return_pct"] - actual_pnl_decimal
        per_position_results.append({
            "ticker": ticker,
            "entry_date": entry_date,
            "entry_price": entry_price,
            "atr": round(atr, 4),
            "atr_stop": round(atr_stop, 4),
            "actual_exit_reason": pos.get("exit_reason", "unknown"),
            "actual_return_pct": round(actual_pnl_decimal, 4),
            "sim_exit_reason": sim["exit_reason"],
            "sim_return_pct": round(sim["return_pct"], 4),
            "sim_holding_days": sim["holding_days"],
            "improvement": round(improvement, 4),
        })

    logger.info("Simulated %d positions, skipped %d", len(simulated_returns), skipped)

    if not simulated_returns:
        logger.error("No positions could be simulated — check data quality.")
        return

    # ------------------------------------------------------------------
    # 4. Compute simulated regime stats
    # ------------------------------------------------------------------
    sim_wins = [r for r in simulated_returns if r > 0]
    sim_losses = [r for r in simulated_returns if r <= 0]
    sim_n = len(simulated_returns)
    sim_win_rate = len(sim_wins) / sim_n
    sim_avg_win = float(np.mean(sim_wins)) if sim_wins else 0.0
    sim_avg_loss = float(abs(np.mean(sim_losses))) if sim_losses else 0.0
    sim_ev = compute_expected_value(sim_win_rate, sim_avg_win, sim_avg_loss)
    sim_kelly = compute_half_kelly(sim_win_rate, sim_avg_win, sim_avg_loss)

    # Profit factor
    total_profit = sum(r for r in simulated_returns if r > 0)
    total_loss = abs(sum(r for r in simulated_returns if r < 0)) or 1e-9
    sim_profit_factor = total_profit / total_loss

    cur_total_profit = sum(r for r in current_stats["all_returns"] if r > 0)
    cur_total_loss = abs(sum(r for r in current_stats["all_returns"] if r < 0)) or 1e-9
    cur_profit_factor = cur_total_profit / cur_total_loss

    # Exit reason breakdown for simulated
    exit_reason_counts: dict[str, int] = {}
    for r in per_position_results:
        k = r["sim_exit_reason"]
        exit_reason_counts[k] = exit_reason_counts.get(k, 0) + 1

    # ------------------------------------------------------------------
    # 5. Print comparison table
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("SIMULATED REGIME (ATR×1.5 stop, 20% trailing, 60-day time exit)")
    print("=" * 70)
    print(f"  Positions simulated: {sim_n}  (skipped {skipped})")
    print(f"  Win rate           : {sim_win_rate:.1%}  ({len(sim_wins)} wins / {len(sim_losses)} losses)")
    print(f"  Avg win            : {sim_avg_win:.2%}")
    print(f"  Avg loss           : {sim_avg_loss:.2%}")
    print(f"  Expected value (EV): {sim_ev:+.4f}  ({'NEGATIVE ⚠' if sim_ev < 0 else 'POSITIVE ✓'})")
    print(f"  Profit factor      : {sim_profit_factor:.3f}")
    print(f"  Half-Kelly size    : {sim_kelly:.2%}")
    print(f"  Exit reason breakdown: {exit_reason_counts}")

    print("\n" + "=" * 70)
    print("SIDE-BY-SIDE COMPARISON")
    print("=" * 70)
    print(f"  {'Metric':<25} {'Current':>12} {'Simulated':>12} {'Delta':>10}")
    print(f"  {'-'*25} {'-'*12} {'-'*12} {'-'*10}")
    print(f"  {'Win rate':<25} {current_stats['win_rate']:>11.1%} {sim_win_rate:>11.1%} {sim_win_rate - current_stats['win_rate']:>+10.1%}")
    print(f"  {'Avg win':<25} {current_stats['avg_win']:>11.2%} {sim_avg_win:>11.2%} {sim_avg_win - current_stats['avg_win']:>+10.2%}")
    print(f"  {'Avg loss':<25} {current_stats['avg_loss']:>11.2%} {sim_avg_loss:>11.2%} {sim_avg_loss - current_stats['avg_loss']:>+10.2%}")
    print(f"  {'Expected value':<25} {current_ev:>+11.4f} {sim_ev:>+11.4f} {sim_ev - current_ev:>+10.4f}")
    print(f"  {'Profit factor':<25} {cur_profit_factor:>12.3f} {sim_profit_factor:>12.3f} {sim_profit_factor - cur_profit_factor:>+10.3f}")

    # ------------------------------------------------------------------
    # 6. Per-position comparison sorted by improvement
    # ------------------------------------------------------------------
    per_position_results.sort(key=lambda x: x["improvement"], reverse=True)

    print("\n" + "=" * 70)
    print("TOP 10 MOST IMPROVED POSITIONS (simulated vs actual)")
    print("=" * 70)
    print(f"  {'Ticker':<8} {'Entry':>12} {'Actual%':>9} {'Sim%':>9} {'Delta':>8} {'SimReason':<16}")
    print(f"  {'-'*8} {'-'*12} {'-'*9} {'-'*9} {'-'*8} {'-'*16}")
    for r in per_position_results[:10]:
        print(
            f"  {r['ticker']:<8} {r['entry_date']:>12} "
            f"{r['actual_return_pct']:>+8.2%} {r['sim_return_pct']:>+8.2%} "
            f"{r['improvement']:>+7.2%} {r['sim_exit_reason']:<16}"
        )

    print("\n" + "=" * 70)
    print("BOTTOM 10 MOST DEGRADED POSITIONS")
    print("=" * 70)
    print(f"  {'Ticker':<8} {'Entry':>12} {'Actual%':>9} {'Sim%':>9} {'Delta':>8} {'SimReason':<16}")
    print(f"  {'-'*8} {'-'*12} {'-'*9} {'-'*9} {'-'*8} {'-'*16}")
    for r in per_position_results[-10:]:
        print(
            f"  {r['ticker']:<8} {r['entry_date']:>12} "
            f"{r['actual_return_pct']:>+8.2%} {r['sim_return_pct']:>+8.2%} "
            f"{r['improvement']:>+7.2%} {r['sim_exit_reason']:<16}"
        )

    # ------------------------------------------------------------------
    # 7. Half-Kelly analysis
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("HALF-KELLY POSITION SIZING ANALYSIS")
    print("=" * 70)
    print(f"  Current Half-Kelly  : {current_kelly:.2%} of portfolio per trade")
    print(f"  Simulated Half-Kelly: {sim_kelly:.2%} of portfolio per trade")
    print()
    print("  Note: With a negative EV, any position size compounds losses.")
    print("  Target: EV > 0 before deploying capital aggressively.")

    # ------------------------------------------------------------------
    # 8. EV warning
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    if sim_ev <= 0:
        print("WARNING: SIMULATED EV IS STILL NEGATIVE")
        print("  The proposed ATR stop + 20% trailing stop does NOT yet produce")
        print("  a positive expected value against these 117 historical positions.")
        print("  Recommended actions:")
        print("  - Improve signal quality (add ML pre-filter)")
        print("  - Widen take-profit target (current 10% may be too tight)")
        print("  - Add entry quality gate (only trade high-confidence signals)")
    else:
        print("SIMULATED EV IS POSITIVE")
        print(f"  EV improved from {current_ev:+.4f} (current) to {sim_ev:+.4f} (simulated)")
        print("  The proposed parameter changes show a measurable improvement.")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 9. Save results JSON
    # ------------------------------------------------------------------
    results = {
        "run_timestamp": datetime.utcnow().isoformat() + "Z",
        "config": {
            "atr_period": ATR_PERIOD,
            "atr_multiplier": ATR_MULTIPLIER,
            "new_trailing_pct": NEW_TRAILING_PCT,
            "max_days": MAX_DAYS,
        },
        "current_regime": {
            "n": current_stats["n"],
            "win_rate": current_stats["win_rate"],
            "avg_win": current_stats["avg_win"],
            "avg_loss": current_stats["avg_loss"],
            "expected_value": current_ev,
            "profit_factor": cur_profit_factor,
            "half_kelly": current_kelly,
        },
        "simulated_regime": {
            "n": sim_n,
            "skipped": skipped,
            "win_rate": sim_win_rate,
            "avg_win": sim_avg_win,
            "avg_loss": sim_avg_loss,
            "expected_value": sim_ev,
            "profit_factor": sim_profit_factor,
            "half_kelly": sim_kelly,
            "exit_reason_counts": exit_reason_counts,
        },
        "ev_improved": sim_ev > current_ev,
        "ev_positive": sim_ev > 0,
        "per_position": per_position_results,
    }

    output_path = os.path.join(_SCRIPT_DIR, "backtest_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info("Results saved to %s", output_path)
    print(f"\nFull results saved to: {output_path}")


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    run_backtest()
