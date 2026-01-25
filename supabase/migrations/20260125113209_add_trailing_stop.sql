-- Migration: Add Trailing Stop Configuration
-- 
-- Rationale: Trailing stops lock in profits as the stock rises while allowing upside
-- to continue running. When a position gains 10%, the trailing stop follows 8% behind,
-- protecting gains while avoiding premature exits.
--
-- Changes:
-- - Add trailing_stop_pct to config (default: 8%)
-- - Add highest_price and trailing_stop_price to positions table
-- - These will be updated dynamically by the exit check job

-- Add trailing stop configuration
ALTER TABLE public.reference_portfolio_config
ADD COLUMN IF NOT EXISTS trailing_stop_pct DECIMAL(5,2) DEFAULT 8.00;

-- Set default for existing config
UPDATE public.reference_portfolio_config
SET trailing_stop_pct = 8.00
WHERE trailing_stop_pct IS NULL;

COMMENT ON COLUMN public.reference_portfolio_config.trailing_stop_pct IS 
  'Trailing stop percentage - locks in profits as price rises. Default 8% below highest price since entry.';

-- Add tracking columns to positions table
ALTER TABLE public.reference_portfolio_positions
ADD COLUMN IF NOT EXISTS highest_price DECIMAL(15,4),
ADD COLUMN IF NOT EXISTS trailing_stop_price DECIMAL(15,4);

-- Initialize highest_price for existing open positions (use entry_price as baseline)
UPDATE public.reference_portfolio_positions
SET highest_price = GREATEST(entry_price, COALESCE(current_price, entry_price))
WHERE is_open = true
  AND highest_price IS NULL;

-- Initialize trailing_stop_price for existing open positions
UPDATE public.reference_portfolio_positions p
SET trailing_stop_price = p.highest_price * (1 - (c.trailing_stop_pct / 100))
FROM public.reference_portfolio_config c
WHERE p.is_open = true
  AND p.trailing_stop_price IS NULL
  AND p.highest_price IS NOT NULL;

COMMENT ON COLUMN public.reference_portfolio_positions.highest_price IS 
  'Highest price reached since position entry - used to calculate trailing stop';

COMMENT ON COLUMN public.reference_portfolio_positions.trailing_stop_price IS 
  'Trailing stop price - dynamically adjusted as highest_price increases. Exit if current_price <= trailing_stop_price';

-- Create index for efficient trailing stop queries
CREATE INDEX IF NOT EXISTS idx_positions_trailing_stop 
ON public.reference_portfolio_positions(trailing_stop_price, is_open, current_price) 
WHERE is_open = true AND trailing_stop_price IS NOT NULL;

COMMENT ON INDEX idx_positions_trailing_stop IS 
  'Optimize queries for checking trailing stop triggers';
