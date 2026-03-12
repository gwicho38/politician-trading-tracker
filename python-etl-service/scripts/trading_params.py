"""
Trading system parameters — the single file the research agent modifies.

This file is the autoresearch-style 'train.py' equivalent for the trading system.
The mcli 'trading research run' command modifies this file each iteration,
evaluates against backtest_parameters.py (fixed), and keeps or discards based on
profit_factor improvement.

METRIC TO OPTIMIZE: profit_factor (higher is better; > 1.0 = profitable)
FIXED EVALUATION:   backtest_parameters.py against all closed positions

CURRENT BASELINE (134 valid closed positions, junk tickers excluded):
  current_regime_profit_factor:  0.199  (actual realized P&L, no ATR)
  simulated_profit_factor:       0.627  (ATR×1.5, 20% trailing, 60-day)
  ev_per_trade:  -0.0161  (simulated)
  win_rate:       20.9%   (simulated)
  NOTE: profit_factor > 0.627 means improvement over ATR baseline
"""

# ============================================================
# Stop-loss parameters
# ============================================================

# ATR period for volatility estimation.
# Shorter periods (10–14) react faster to recent volatility.
# Longer periods (20–30) produce smoother, wider stops.
ATR_PERIOD: int = 20

# How many ATRs below entry to place the stop.
# 2.0 = stop at entry - 2.0 × ATR20
# Range to explore: [1.0, 3.0] — larger multiplier = wider stop = fewer premature stops
ATR_MULTIPLIER: float = 1.5

# ============================================================
# Trailing stop parameters
# ============================================================

# Trailing stop distance below the highest observed price.
# 0.12 = stop trails at 88% of peak.
# Tighter (0.10) locks in gains faster but exits strong trends early.
# Wider (0.25–0.30) lets winners run but gives back more.
TRAILING_STOP_PCT: float = 0.12

# Arm the trailing stop only after price exceeds entry by this fraction.
# 0.05 = arm once price is +5% above entry.
# Prevents the trailing stop from triggering on an opening-day dip.
# Range: [0.03, 0.10]
TRAILING_ARM_PCT: float = 0.05

# ============================================================
# Time exit
# ============================================================

# Maximum holding period in calendar days.
# After this many days, force-close the position at market.
# Range: [30, 90]
TIME_EXIT_DAYS: int = 45

# ============================================================
# Position sizing (Half-Kelly)
# ============================================================

# Fraction of the Kelly criterion to use.
# Full Kelly (1.0) maximises growth but has extreme volatility.
# Half-Kelly (0.5) is the standard conservative choice.
# Quarter-Kelly (0.25) for early-stage systems with uncertain edge.
# Range: [0.25, 0.75]
KELLY_FRACTION: float = 0.5

# Minimum position size as fraction of portfolio (floor when Kelly → 0).
# Range: [0.005, 0.02]
MIN_POSITION_PCT: float = 0.01

# Maximum position size as fraction of portfolio (cap, regardless of Kelly).
# Range: [0.03, 0.08]
MAX_POSITION_PCT: float = 0.05