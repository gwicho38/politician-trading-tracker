-- ML Feedback Loop Configuration
-- Adds dynamic blend weight and widens trading_mode constraint

-- 1. Add ml_blend_weight to reference_portfolio_config
ALTER TABLE public.reference_portfolio_config
  ADD COLUMN IF NOT EXISTS ml_blend_weight DECIMAL(3,2) NOT NULL DEFAULT 0.20;

-- 2. Widen trading_mode constraint to allow 'live'
DO $$
BEGIN
  ALTER TABLE public.reference_portfolio_config
    DROP CONSTRAINT IF EXISTS reference_portfolio_config_trading_mode_check;
EXCEPTION WHEN undefined_object THEN
  NULL;
END $$;

ALTER TABLE public.reference_portfolio_config
  ADD CONSTRAINT reference_portfolio_config_trading_mode_check
  CHECK (trading_mode IN ('paper', 'live'));

-- 3. Add 'candidate' to ml_models status
DO $$
BEGIN
  ALTER TABLE public.ml_models
    DROP CONSTRAINT IF EXISTS ml_models_status_check;
EXCEPTION WHEN undefined_object THEN
  NULL;
END $$;

ALTER TABLE public.ml_models
  ADD CONSTRAINT ml_models_status_check
  CHECK (status IN ('pending', 'training', 'active', 'archived', 'failed', 'candidate'));

COMMENT ON COLUMN public.reference_portfolio_config.ml_blend_weight IS
  'ML model weight in blended signals (0.1-0.7). Auto-adjusted by signal-feedback evaluation.';
COMMENT ON COLUMN public.reference_portfolio_config.trading_mode IS
  'paper = Alpaca paper trading, live = real money. Requires manual switch.';
