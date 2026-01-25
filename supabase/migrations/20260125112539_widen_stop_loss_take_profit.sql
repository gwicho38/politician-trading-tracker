-- Migration: Widen Stop-Loss and Take-Profit Levels
-- 
-- Rationale: Current 5% stop-loss is too tight for politician trades with 30-90 day
-- information lag. Stocks need more room to breathe. Increasing take-profit to 25%
-- allows winners to run further.
--
-- Changes:
-- - default_stop_loss_pct: 5.00 -> 10.00
-- - default_take_profit_pct: 15.00 -> 25.00

-- Update the reference portfolio config
UPDATE public.reference_portfolio_config
SET 
  default_stop_loss_pct = 10.00,
  default_take_profit_pct = 25.00,
  updated_at = now()
WHERE id IS NOT NULL;

-- Update any existing open positions with new stop-loss and take-profit levels
-- This ensures existing positions benefit from the new risk parameters
UPDATE public.reference_portfolio_positions
SET
  stop_loss_price = entry_price * (1 - 0.10),  -- 10% stop loss
  take_profit_price = entry_price * (1 + 0.25),  -- 25% take profit
  updated_at = now()
WHERE is_open = true
  AND stop_loss_price IS NOT NULL  -- Only update if stop loss was previously set
  AND take_profit_price IS NOT NULL;

-- Log the change
COMMENT ON TABLE public.reference_portfolio_config IS 
  'Reference portfolio configuration - Updated 2026-01-25: Widened stop-loss to 10% and take-profit to 25% to account for disclosure lag in politician trades';
