"""
Tests for backtest_parameters.py — pure calculation functions only.

Tests cover:
- compute_atr()
- compute_atr_stop()
- compute_half_kelly()
- compute_expected_value()
- simulate_position_new_params()
"""

import sys
import os
import pytest
import pandas as pd
import numpy as np

# Make scripts/ importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from backtest_parameters import (
    compute_atr,
    compute_atr_stop,
    compute_half_kelly,
    compute_expected_value,
    simulate_position_new_params,
)


# ============================================================
# Helpers
# ============================================================

def _make_ohlc(n: int, open_=100.0, high=102.0, low=98.0, close=100.0) -> pd.DataFrame:
    """Return a simple flat OHLC DataFrame with n rows."""
    return pd.DataFrame(
        {
            "Open": [open_] * n,
            "High": [high] * n,
            "Low": [low] * n,
            "Close": [close] * n,
        }
    )


# ============================================================
# TestComputeATR
# ============================================================

class TestComputeATR:
    def test_flat_market_atr_equals_range(self):
        """For a flat market with daily high=102, low=98 (range=4), ATR ≈ 4.0."""
        df = _make_ohlc(30, open_=100.0, high=102.0, low=98.0, close=100.0)
        result = compute_atr(df, period=20)
        assert result is not None
        # With flat OHLC the true range each day equals high-low=4; ATR = 4.0
        assert abs(result - 4.0) < 0.5, f"Expected ATR ≈ 4.0, got {result}"

    def test_requires_at_least_21_rows(self):
        """Returns None when fewer than period+1 rows are provided."""
        df = _make_ohlc(20)  # exactly 20 rows (period=20 needs 21)
        result = compute_atr(df, period=20)
        assert result is None

    def test_returns_float_for_sufficient_rows(self):
        """Returns a float when enough rows are provided."""
        df = _make_ohlc(25)
        result = compute_atr(df, period=20)
        assert isinstance(result, float)
        assert result > 0


# ============================================================
# TestComputeATRStop
# ============================================================

class TestComputeATRStop:
    def test_stop_below_entry(self):
        """entry=100, atr=4, mult=1.5 → stop = 100 - 1.5*4 = 94.0"""
        result = compute_atr_stop(entry_price=100.0, atr=4.0, multiplier=1.5)
        assert result == pytest.approx(94.0)

    def test_multiplier_applied(self):
        """entry=200, atr=5, mult=2.0 → stop = 200 - 2.0*5 = 190.0"""
        result = compute_atr_stop(entry_price=200.0, atr=5.0, multiplier=2.0)
        assert result == pytest.approx(190.0)

    def test_default_multiplier(self):
        """Default multiplier=1.5; entry=50, atr=2 → stop = 50 - 3 = 47.0"""
        result = compute_atr_stop(entry_price=50.0, atr=2.0)
        assert result == pytest.approx(47.0)


# ============================================================
# TestComputeHalfKelly
# ============================================================

class TestComputeHalfKelly:
    def test_positive_edge_capped(self):
        """
        win_rate=0.4, avg_win=0.12, avg_loss=0.06
        kelly = 0.4 - 0.6/(0.12/0.06) = 0.4 - 0.3 = 0.1
        half_kelly = 0.05 → capped at max_size=0.05
        """
        result = compute_half_kelly(
            win_rate=0.4, avg_win=0.12, avg_loss=0.06, max_size=0.05
        )
        assert result == pytest.approx(0.05)

    def test_negative_kelly_returns_min(self):
        """win_rate=0.1, avg_win=0.06, avg_loss=0.08 → Kelly negative → return min_size=0.01"""
        result = compute_half_kelly(
            win_rate=0.1, avg_win=0.06, avg_loss=0.08, min_size=0.01
        )
        assert result == pytest.approx(0.01)

    def test_capped_at_five_percent(self):
        """Very high edge: Kelly >> 0.1 → still capped at 0.05"""
        result = compute_half_kelly(
            win_rate=0.9, avg_win=0.20, avg_loss=0.02, max_size=0.05
        )
        assert result == pytest.approx(0.05)

    def test_moderate_positive_kelly(self):
        """
        win_rate=0.5, avg_win=0.10, avg_loss=0.05
        win_loss = 10/5 = 2.0
        kelly = 0.5 - 0.5/2.0 = 0.5 - 0.25 = 0.25
        half_kelly = 0.125 → capped at 0.05
        """
        result = compute_half_kelly(
            win_rate=0.5, avg_win=0.10, avg_loss=0.05, max_size=0.05
        )
        assert result == pytest.approx(0.05)


# ============================================================
# TestComputeExpectedValue
# ============================================================

class TestComputeExpectedValue:
    def test_negative_ev_current_params(self):
        """
        Current regime stats: win_rate=0.1226, avg_win=0.104, avg_loss=0.080
        EV = 0.1226*0.104 - 0.8774*0.080 = 0.01275 - 0.07019 = -0.0574 (negative)
        """
        ev = compute_expected_value(
            win_rate=0.1226, avg_win=0.104, avg_loss=0.080
        )
        assert ev < 0, f"Expected negative EV for current params, got {ev}"

    def test_positive_ev_good_params(self):
        """
        win_rate=0.45, avg_win=0.08, avg_loss=0.05
        EV = 0.45*0.08 - 0.55*0.05 = 0.036 - 0.0275 = +0.0085 (positive)
        """
        ev = compute_expected_value(
            win_rate=0.45, avg_win=0.08, avg_loss=0.05
        )
        assert ev > 0, f"Expected positive EV for good params, got {ev}"

    def test_breakeven_ev(self):
        """win_rate=0.5, avg_win=0.05, avg_loss=0.05 → EV = 0.0"""
        ev = compute_expected_value(win_rate=0.5, avg_win=0.05, avg_loss=0.05)
        assert ev == pytest.approx(0.0)


# ============================================================
# TestSimulatePositionNewParams
# ============================================================

class TestSimulatePositionNewParams:
    def test_trailing_stop_triggers_correctly(self):
        """
        prices=[100, 105, 110, 115, 90]
        entry=100, peaks at 115 (>5% move), trailing_stop = 115 * 0.80 = 92.0
        When price drops to 90 < 92, trailing stop triggers.
        """
        prices = [100.0, 105.0, 110.0, 115.0, 90.0]
        result = simulate_position_new_params(
            entry_price=100.0,
            atr_stop=70.0,  # very low, won't trigger
            price_series=prices,
            max_days=60,
            trailing_pct=0.20,
        )
        assert result["exit_reason"] == "trailing_stop"
        assert result["exit_price"] == pytest.approx(90.0)
        assert result["holding_days"] == 4  # exits on day index 4 (0-indexed)

    def test_trailing_stop_does_not_trigger_before_5pct_move(self):
        """
        Trailing stop must NOT trigger before price moves up >5%.
        prices=[100, 102, 101, 99, 98, 97, 96, 95] — price falls but never rose >5%
        atr_stop=90 (low), so atr_stop won't fire either.
        Should be time_exit (or hit all 8 prices as time_exit if max_days=7).
        """
        prices = [100.0, 102.0, 101.0, 99.0, 98.0, 97.0, 96.0, 95.0]
        result = simulate_position_new_params(
            entry_price=100.0,
            atr_stop=80.0,  # very low, won't trigger
            price_series=prices,
            max_days=60,
            trailing_pct=0.20,
        )
        # price never exceeded 5% above entry (105), so trailing stop never armed
        assert result["exit_reason"] in ("time_exit",)

    def test_atr_stop_triggers(self):
        """
        prices=[100, 97, 94, 93], atr_stop=95
        Day 2: price=94 < atr_stop=95 → exit_reason='atr_stop'
        """
        prices = [100.0, 97.0, 94.0, 93.0]
        result = simulate_position_new_params(
            entry_price=100.0,
            atr_stop=95.0,
            price_series=prices,
            max_days=60,
            trailing_pct=0.20,
        )
        assert result["exit_reason"] == "atr_stop"
        assert result["exit_price"] == pytest.approx(94.0)

    def test_time_exit_at_60_days(self):
        """
        61 flat prices at 100, atr_stop=80, max_days=60.
        days_to_simulate = min(61, 60) = 60.
        Loop runs indices 0..59; exits on index 59 → holding_days=59.
        """
        prices = [100.0] * 61
        result = simulate_position_new_params(
            entry_price=100.0,
            atr_stop=80.0,
            price_series=prices,
            max_days=60,
            trailing_pct=0.20,
        )
        assert result["exit_reason"] == "time_exit"
        assert result["holding_days"] == 59  # 0-indexed last bar = index 59

    def test_return_pct_computed_correctly(self):
        """
        60 prices: first 59 at 100, last one at 110.
        max_days=60 → days_to_simulate=60, exit_idx=59, exit_price=110 → return=0.10
        """
        prices = [100.0] * 59 + [110.0]  # 60 prices; index 59 = 110
        result = simulate_position_new_params(
            entry_price=100.0,
            atr_stop=80.0,
            price_series=prices,
            max_days=60,
            trailing_pct=0.20,
        )
        assert result["exit_reason"] == "time_exit"
        assert result["return_pct"] == pytest.approx(0.10)

    def test_atr_stop_takes_priority_over_trailing(self):
        """
        Both ATR stop and trailing stop could fire; ATR stop should fire first
        since it is checked before trailing.
        prices=[100, 108, 107, 106, 105, 104, 103, 90]
        atr_stop=95; trailing_pct=0.05 → trailing armed at 108 (>5%), trailing_stop=108*0.95=102.6
        Day 7: price=90 < atr_stop=95 AND < trailing 102.6 → ATR stop wins (checked first)
        """
        prices = [100.0, 108.0, 107.0, 106.0, 105.0, 104.0, 103.0, 90.0]
        result = simulate_position_new_params(
            entry_price=100.0,
            atr_stop=95.0,
            price_series=prices,
            max_days=60,
            trailing_pct=0.05,
        )
        assert result["exit_reason"] == "atr_stop"
