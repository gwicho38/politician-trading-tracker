from typing import Literal

# Existing parameters with one change applied as per instruction.
ATR_PERIOD = int = 20
ATR_MULTIPLIER = 1.5
TRAILING_STOP_PCT = 0.12
TRAILING_ARM_PCT: float = 0.15
TIME_EXIT_DAYS = 35
KELLY_FRACTION = float = 0.5
MIN_POSITION_PCT = float = 0.02
MAX_POSITION_PECT: float = 0.05
# Keeping MIN_SIGNAL_CONFIDENCE unchanged as instructed to avoid counterproductive higher values.
MIN_SIGNAL_CONFIDENCE: float = 0.70

# No other changes made beyond the specified single change in TRAILING_ARM_PCT.
