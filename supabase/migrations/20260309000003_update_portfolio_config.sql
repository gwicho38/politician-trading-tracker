-- Fix portfolio parameters based on backtest findings:
-- 1. trailing_stop_pct: 4 → 20 (was tighter than the fixed stop, causing day-1 wipeouts)
-- 2. default_stop_loss_pct: 5 → 10 (wider fixed backstop; ATR-based is primary)
-- 3. default_take_profit_pct unchanged; trailing stop replaces fixed TP
-- Note: ATR-based stop is computed dynamically at execution time; this is the fallback.
UPDATE public.reference_portfolio_config
SET
  trailing_stop_pct     = 20,
  default_stop_loss_pct = 10,
  updated_at            = now()
WHERE id IS NOT NULL;
