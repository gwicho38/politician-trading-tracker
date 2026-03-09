"""
Historical backtest: all politician purchase disclosures 2014–2025.

This is a large-scale event-study backtest — NOT limited to the reference
portfolio positions. It replays every disclosure where a politician purchased
a stock, applying two exit strategies and comparing performance.

Entry timing (no look-ahead bias):
    disclosure_date + 1 business day (can only trade after filing is public).
    Falls back to transaction_date + 30d if disclosure_date is missing.

Strategies compared:
    A (old): 5% fixed stop-loss, 15% take-profit, 60-day time exit
    B (new): ATR×1.5 hard stop, 20% trailing stop (armed after +5% gain),
             60-day time exit

Run from politician-trading-tracker/:
    uv run python python-etl-service/scripts/backtest_historical_disclosures.py
    uv run python python-etl-service/scripts/backtest_historical_disclosures.py --year 2022
    uv run python python-etl-service/scripts/backtest_historical_disclosures.py --limit 500
"""

import argparse
import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Make `app` importable
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
# Pure simulation functions
# ============================================================

def simulate_old_strategy(
    entry_price: float,
    price_series: list[float],
    stop_loss_pct: float = 0.05,
    take_profit_pct: float = 0.15,
    max_days: int = 60,
) -> dict:
    """Simulate Strategy A: fixed % stop-loss, fixed % take-profit, time exit."""
    if not price_series:
        return {
            "exit_price": entry_price,
            "exit_reason": "time_exit",
            "holding_days": 0,
            "return_pct": 0.0,
        }

    stop_price = entry_price * (1 - stop_loss_pct)
    tp_price = entry_price * (1 + take_profit_pct)
    days = min(len(price_series), max_days)

    for i in range(days):
        p = price_series[i]
        if p <= stop_price:
            return {
                "exit_price": float(p),
                "exit_reason": "stop_loss",
                "holding_days": i,
                "return_pct": (p - entry_price) / entry_price,
            }
        if p >= tp_price:
            return {
                "exit_price": float(p),
                "exit_reason": "take_profit",
                "holding_days": i,
                "return_pct": (p - entry_price) / entry_price,
            }

    exit_price = float(price_series[days - 1])
    return {
        "exit_price": exit_price,
        "exit_reason": "time_exit",
        "holding_days": days - 1,
        "return_pct": (exit_price - entry_price) / entry_price,
    }


def simulate_new_strategy(
    entry_price: float,
    atr_stop: float,
    price_series: list[float],
    max_days: int = 60,
    trailing_pct: float = 0.20,
) -> dict:
    """Simulate Strategy B: ATR hard stop, trailing stop (armed at +5%), time exit."""
    if not price_series:
        return {
            "exit_price": entry_price,
            "exit_reason": "time_exit",
            "holding_days": 0,
            "return_pct": 0.0,
            "highest_price": entry_price,
        }

    highest = entry_price
    trailing_armed = False
    days = min(len(price_series), max_days)

    for i in range(days):
        p = price_series[i]
        if p > highest:
            highest = p
        if not trailing_armed and highest > entry_price * 1.05:
            trailing_armed = True

        if p <= atr_stop:
            return {
                "exit_price": float(p),
                "exit_reason": "atr_stop",
                "holding_days": i,
                "return_pct": (p - entry_price) / entry_price,
                "highest_price": highest,
            }

        if trailing_armed and p <= highest * (1 - trailing_pct):
            return {
                "exit_price": float(p),
                "exit_reason": "trailing_stop",
                "holding_days": i,
                "return_pct": (p - entry_price) / entry_price,
                "highest_price": highest,
            }

    exit_price = float(price_series[days - 1])
    return {
        "exit_price": exit_price,
        "exit_reason": "time_exit",
        "holding_days": days - 1,
        "return_pct": (exit_price - entry_price) / entry_price,
        "highest_price": highest,
    }


def compute_atr(ohlc: pd.DataFrame, period: int = 20) -> Optional[float]:
    """ATR over the last `period` bars (SMA of true range)."""
    if len(ohlc) <= period:
        return None
    high = ohlc["High"].values
    low = ohlc["Low"].values
    close = ohlc["Close"].values
    tr = [max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
          for i in range(1, len(ohlc))]
    return float(np.mean(tr[-period:]))


def compute_ev(win_rate: float, avg_win: float, avg_loss: float) -> float:
    return win_rate * avg_win - (1 - win_rate) * avg_loss


def compute_profit_factor(returns: list[float]) -> float:
    gross_profit = sum(r for r in returns if r > 0)
    gross_loss = abs(sum(r for r in returns if r < 0)) or 1e-9
    return gross_profit / gross_loss


def regime_stats(returns: list[float]) -> dict:
    if not returns:
        return {"n": 0, "win_rate": 0, "avg_win": 0, "avg_loss": 0, "ev": 0, "pf": 0}
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    win_rate = len(wins) / len(returns)
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = float(abs(np.mean(losses))) if losses else 0.0
    return {
        "n": len(returns),
        "n_wins": len(wins),
        "n_losses": len(losses),
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "ev": compute_ev(win_rate, avg_win, avg_loss),
        "pf": compute_profit_factor(returns),
        "total_return": float(np.sum(returns)),
        "median_return": float(np.median(returns)),
    }


# ============================================================
# Date helpers
# ============================================================

def parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def next_business_day(dt: date) -> date:
    """First weekday strictly after dt."""
    next_dt = dt + timedelta(days=1)
    while next_dt.weekday() >= 5:
        next_dt += timedelta(days=1)
    return next_dt


def get_entry_date(row: dict) -> Optional[date]:
    """
    Entry = disclosure_date + 1 business day (no look-ahead bias).
    Fallback: transaction_date + 30d if disclosure_date is missing.
    """
    disc = parse_date(row.get("disclosure_date"))
    if disc:
        return next_business_day(disc)
    txn = parse_date(row.get("transaction_date"))
    if txn:
        return next_business_day(txn + timedelta(days=30))
    return None


# ============================================================
# Data fetching
# ============================================================

def fetch_disclosures(supabase, year_filter: Optional[int] = None, limit: Optional[int] = None) -> list[dict]:
    """Pull all purchase disclosures with valid tickers from Supabase."""
    logger.info("Fetching purchase disclosures from Supabase...")

    PAGE = 1000
    all_rows = []
    offset = 0

    while True:
        q = (
            supabase.table("trading_disclosures")
            .select(
                "id, politician_id, transaction_date, disclosure_date, "
                "asset_ticker, amount_range_min, amount_range_max"
            )
            .eq("transaction_type", "purchase")
            .not_.is_("asset_ticker", "null")
            .not_.is_("transaction_date", "null")
        )

        if year_filter:
            q = (
                q.gte("transaction_date", f"{year_filter}-01-01")
                .lt("transaction_date", f"{year_filter + 1}-01-01")
            )

        result = q.range(offset, offset + PAGE - 1).execute()
        batch = result.data or []
        all_rows.extend(batch)

        if len(batch) < PAGE:
            break
        offset += PAGE

        if limit and len(all_rows) >= limit:
            break

    if limit:
        all_rows = all_rows[:limit]

    # Filter out junk tickers (too long, contain numbers or special chars)
    valid = []
    for r in all_rows:
        t = (r.get("asset_ticker") or "").strip().upper()
        if 1 <= len(t) <= 5 and t.isalpha():
            r["asset_ticker"] = t
            entry_dt = get_entry_date(r)
            if entry_dt and entry_dt >= date(2014, 1, 1):
                r["_entry_date"] = entry_dt
                valid.append(r)

    logger.info("Fetched %d valid purchase disclosures (after ticker/date filter)", len(valid))
    return valid


def download_ticker_prices(ticker: str, start: date, end: date) -> Optional[pd.DataFrame]:
    """Download OHLCV for one ticker. Returns None on failure."""
    import yfinance as yf

    try:
        df = yf.download(
            ticker,
            start=start,
            end=end + timedelta(days=1),  # end is exclusive in yfinance
            progress=False,
            auto_adjust=True,
        )
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Open", "High", "Low", "Close"]].dropna()
        df.index = pd.to_datetime(df.index).date
        return df
    except Exception as exc:
        logger.debug("yfinance error for %s: %s", ticker, exc)
        return None


def build_price_cache(disclosures: list[dict]) -> dict[str, Optional[pd.DataFrame]]:
    """
    Group disclosures by ticker and download one combined price range per ticker.

    Pre-entry window: 40 days before earliest entry (for ATR calculation)
    Post-entry window: 75 days after latest entry (covers 60-day simulation + buffer)
    """
    # Group by ticker → collect entry dates
    by_ticker: dict[str, list[date]] = defaultdict(list)
    for row in disclosures:
        by_ticker[row["asset_ticker"]].append(row["_entry_date"])

    tickers = list(by_ticker.keys())
    logger.info("Downloading price history for %d unique tickers...", len(tickers))

    cache: dict[str, Optional[pd.DataFrame]] = {}
    for i, ticker in enumerate(tickers):
        dates = by_ticker[ticker]
        dl_start = min(dates) - timedelta(days=40)
        dl_end = max(dates) + timedelta(days=75)
        df = download_ticker_prices(ticker, dl_start, dl_end)
        cache[ticker] = df

        if (i + 1) % 50 == 0:
            logger.info("  Downloaded %d / %d tickers", i + 1, len(tickers))
            time.sleep(0.5)  # brief pause to avoid rate limiting

    downloaded = sum(1 for v in cache.values() if v is not None)
    logger.info("Price data available for %d / %d tickers", downloaded, len(tickers))
    return cache


# ============================================================
# Main backtest
# ============================================================

def run_backtest(year_filter: Optional[int] = None, limit: Optional[int] = None) -> None:
    from dotenv import load_dotenv

    _project_root = os.path.dirname(_ETL_ROOT)
    env_path = os.path.join(_project_root, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)

    from supabase import create_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    supabase = create_client(url, key)

    # -----------------------------------------------------------------------
    # 1. Fetch disclosures
    # -----------------------------------------------------------------------
    disclosures = fetch_disclosures(supabase, year_filter=year_filter, limit=limit)
    if not disclosures:
        logger.error("No disclosures found.")
        return

    # -----------------------------------------------------------------------
    # 2. Build price cache (one download per ticker)
    # -----------------------------------------------------------------------
    price_cache = build_price_cache(disclosures)

    # -----------------------------------------------------------------------
    # 3. Simulate both strategies
    # -----------------------------------------------------------------------
    ATR_PERIOD = 20
    ATR_MULT = 1.5
    TRAILING_PCT = 0.20
    MAX_DAYS = 60
    OLD_STOP = 0.05
    OLD_TP = 0.15

    results_a: list[float] = []
    results_b: list[float] = []
    by_year_a: dict[int, list[float]] = defaultdict(list)
    by_year_b: dict[int, list[float]] = defaultdict(list)
    exit_counts_a: dict[str, int] = defaultdict(int)
    exit_counts_b: dict[str, int] = defaultdict(int)
    ticker_results: list[dict] = []
    skipped = 0

    logger.info("Simulating %d disclosures...", len(disclosures))

    for row in disclosures:
        ticker = row["asset_ticker"]
        entry_dt = row["_entry_date"]
        txn_year = (parse_date(row.get("transaction_date")) or entry_dt).year

        df = price_cache.get(ticker)
        if df is None or df.empty:
            skipped += 1
            continue

        # Split into pre/post entry
        pre_entry = df[df.index < entry_dt]
        post_entry = df[df.index >= entry_dt]

        if post_entry.empty:
            skipped += 1
            continue

        price_series = post_entry["Close"].tolist()
        entry_price = price_series[0]

        # ---- Strategy A (old: fixed stop/TP) ----
        sim_a = simulate_old_strategy(
            entry_price=entry_price,
            price_series=price_series,
            stop_loss_pct=OLD_STOP,
            take_profit_pct=OLD_TP,
            max_days=MAX_DAYS,
        )

        # ---- Strategy B (new: ATR stop + trailing) ----
        atr = compute_atr(pre_entry, period=ATR_PERIOD) if len(pre_entry) > ATR_PERIOD else None
        atr_stop = (entry_price - ATR_MULT * atr) if atr else entry_price * (1 - OLD_STOP)

        sim_b = simulate_new_strategy(
            entry_price=entry_price,
            atr_stop=atr_stop,
            price_series=price_series,
            max_days=MAX_DAYS,
            trailing_pct=TRAILING_PCT,
        )

        results_a.append(sim_a["return_pct"])
        results_b.append(sim_b["return_pct"])
        by_year_a[txn_year].append(sim_a["return_pct"])
        by_year_b[txn_year].append(sim_b["return_pct"])
        exit_counts_a[sim_a["exit_reason"]] += 1
        exit_counts_b[sim_b["exit_reason"]] += 1

        ticker_results.append({
            "ticker": ticker,
            "entry_date": entry_dt.isoformat(),
            "entry_price": round(entry_price, 4),
            "year": txn_year,
            "return_a": round(sim_a["return_pct"], 4),
            "return_b": round(sim_b["return_pct"], 4),
            "exit_a": sim_a["exit_reason"],
            "exit_b": sim_b["exit_reason"],
            "atr_available": atr is not None,
            "improvement": round(sim_b["return_pct"] - sim_a["return_pct"], 4),
        })

    logger.info("Simulated %d, skipped %d", len(results_a), skipped)

    if not results_a:
        logger.error("No simulations completed.")
        return

    # -----------------------------------------------------------------------
    # 4. Compute stats
    # -----------------------------------------------------------------------
    stats_a = regime_stats(results_a)
    stats_b = regime_stats(results_b)

    # -----------------------------------------------------------------------
    # 5. Print report
    # -----------------------------------------------------------------------
    label = f"Year {year_filter}" if year_filter else "All years (2014–2025)"
    print(f"\n{'='*72}")
    print(f"HISTORICAL DISCLOSURE BACKTEST  —  {label}")
    print(f"Total disclosures simulated: {len(results_a):,}  |  Skipped: {skipped:,}")
    print(f"{'='*72}")

    def pct(v): return f"{v:+.2%}"
    def flt(v): return f"{v:.4f}"

    print(f"\n{'Metric':<28} {'Strategy A (old)':>16} {'Strategy B (new)':>16} {'Delta':>10}")
    print(f"  {'-'*28} {'-'*16} {'-'*16} {'-'*10}")
    metrics = [
        ("Win rate",         f"{stats_a['win_rate']:.1%}", f"{stats_b['win_rate']:.1%}",
         f"{stats_b['win_rate']-stats_a['win_rate']:+.1%}"),
        ("Avg win",          pct(stats_a['avg_win']),       pct(stats_b['avg_win']),
         f"{stats_b['avg_win']-stats_a['avg_win']:+.2%}"),
        ("Avg loss",         pct(stats_a['avg_loss']),      pct(stats_b['avg_loss']),
         f"{stats_b['avg_loss']-stats_a['avg_loss']:+.2%}"),
        ("Expected value",   flt(stats_a['ev']),            flt(stats_b['ev']),
         f"{stats_b['ev']-stats_a['ev']:+.4f}"),
        ("Profit factor",    f"{stats_a['pf']:.3f}",        f"{stats_b['pf']:.3f}",
         f"{stats_b['pf']-stats_a['pf']:+.3f}"),
        ("Total return",     pct(stats_a['total_return']),  pct(stats_b['total_return']),
         f"{stats_b['total_return']-stats_a['total_return']:+.2%}"),
        ("Median return",    pct(stats_a['median_return']), pct(stats_b['median_return']),
         f"{stats_b['median_return']-stats_a['median_return']:+.2%}"),
        ("N wins",           str(stats_a['n_wins']),        str(stats_b['n_wins']),
         f"{stats_b['n_wins']-stats_a['n_wins']:+d}"),
        ("N losses",         str(stats_a['n_losses']),      str(stats_b['n_losses']),
         f"{stats_b['n_losses']-stats_a['n_losses']:+d}"),
    ]
    for name, va, vb, delta in metrics:
        print(f"  {name:<28} {va:>16} {vb:>16} {delta:>10}")

    print(f"\n  Exit reasons (A): {dict(exit_counts_a)}")
    print(f"  Exit reasons (B): {dict(exit_counts_b)}")

    # Year-by-year breakdown
    print(f"\n{'='*72}")
    print("YEAR-BY-YEAR BREAKDOWN")
    print(f"{'='*72}")
    print(f"  {'Year':<6} {'N':>6} {'WinR-A':>8} {'WinR-B':>8} {'EV-A':>10} {'EV-B':>10} {'Delta-EV':>10}")
    print(f"  {'-'*6} {'-'*6} {'-'*8} {'-'*8} {'-'*10} {'-'*10} {'-'*10}")
    for yr in sorted(set(by_year_a.keys())):
        ra = by_year_a[yr]
        rb = by_year_b[yr]
        if len(ra) < 5:
            continue
        sa = regime_stats(ra)
        sb = regime_stats(rb)
        print(
            f"  {yr:<6} {sa['n']:>6} "
            f"{sa['win_rate']:>7.1%} {sb['win_rate']:>7.1%} "
            f"{sa['ev']:>+10.4f} {sb['ev']:>+10.4f} "
            f"{sb['ev']-sa['ev']:>+10.4f}"
        )

    # Best and worst performers
    ticker_results.sort(key=lambda x: x["return_b"], reverse=True)
    print(f"\n{'='*72}")
    print("TOP 15 PERFORMERS (Strategy B)")
    print(f"{'='*72}")
    print(f"  {'Ticker':<8} {'Entry':>12} {'Ret-A':>8} {'Ret-B':>8} {'Exit-B':<16} {'Yr':>4}")
    print(f"  {'-'*8} {'-'*12} {'-'*8} {'-'*8} {'-'*16} {'-'*4}")
    for r in ticker_results[:15]:
        print(
            f"  {r['ticker']:<8} {r['entry_date']:>12} "
            f"{r['return_a']:>+7.2%} {r['return_b']:>+7.2%} "
            f"{r['exit_b']:<16} {r['year']:>4}"
        )

    ticker_results.sort(key=lambda x: x["return_b"])
    print(f"\n{'='*72}")
    print("BOTTOM 15 PERFORMERS (Strategy B)")
    print(f"{'='*72}")
    print(f"  {'Ticker':<8} {'Entry':>12} {'Ret-A':>8} {'Ret-B':>8} {'Exit-B':<16} {'Yr':>4}")
    print(f"  {'-'*8} {'-'*12} {'-'*8} {'-'*8} {'-'*16} {'-'*4}")
    for r in ticker_results[:15]:
        print(
            f"  {r['ticker']:<8} {r['entry_date']:>12} "
            f"{r['return_a']:>+7.2%} {r['return_b']:>+7.2%} "
            f"{r['exit_b']:<16} {r['year']:>4}"
        )

    # Summary verdict
    print(f"\n{'='*72}")
    ev_a = stats_a["ev"]
    ev_b = stats_b["ev"]
    if ev_b > ev_a and ev_b > 0:
        verdict = "POSITIVE EV with new strategy"
        detail = f"New strategy beats old by {ev_b - ev_a:+.4f} per trade, EV is POSITIVE."
    elif ev_b > ev_a:
        verdict = "IMPROVED but still negative EV"
        detail = f"New strategy beats old by {ev_b - ev_a:+.4f} per trade, but EV is still negative."
    else:
        verdict = "Old strategy wins on aggregate EV"
        detail = f"New strategy EV {ev_b:+.4f} < old {ev_a:+.4f}."
    print(f"VERDICT: {verdict}")
    print(f"  {detail}")
    print(f"  Win rate: {stats_a['win_rate']:.1%} → {stats_b['win_rate']:.1%}")
    print(f"  Avg win:  {stats_a['avg_win']:.2%} → {stats_b['avg_win']:.2%}")
    print(f"{'='*72}")

    # Save JSON output
    output = {
        "run_timestamp": datetime.utcnow().isoformat() + "Z",
        "filter": {"year": year_filter, "limit": limit},
        "config": {
            "atr_period": ATR_PERIOD,
            "atr_multiplier": ATR_MULT,
            "trailing_pct": TRAILING_PCT,
            "max_days": MAX_DAYS,
            "old_stop_pct": OLD_STOP,
            "old_tp_pct": OLD_TP,
        },
        "total_simulated": len(results_a),
        "skipped": skipped,
        "strategy_a": stats_a,
        "strategy_b": stats_b,
        "exit_counts_a": dict(exit_counts_a),
        "exit_counts_b": dict(exit_counts_b),
        "by_year": {
            str(yr): {
                "a": regime_stats(by_year_a[yr]),
                "b": regime_stats(by_year_b[yr]),
            }
            for yr in sorted(by_year_a.keys())
            if len(by_year_a[yr]) >= 5
        },
    }
    out_path = os.path.join(_SCRIPT_DIR, "backtest_historical_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    logger.info("Results saved to %s", out_path)
    print(f"\nFull JSON results saved to: {out_path}")


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Historical disclosure backtest")
    parser.add_argument(
        "--year", type=int, default=None,
        help="Restrict to a single transaction year (e.g. 2022)"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Max number of disclosures to process (for quick testing)"
    )
    args = parser.parse_args()
    run_backtest(year_filter=args.year, limit=args.limit)
