-- Migration: Add crypto and extended hours trading support
-- Adds asset_type columns, changes quantity to DECIMAL for fractional crypto,
-- and adds configuration columns for extended hours and crypto trading.

-- 1. Add asset_type to trading_signals
ALTER TABLE trading_signals
  ADD COLUMN IF NOT EXISTS asset_type TEXT NOT NULL DEFAULT 'stock';

-- 2. Add asset_type to reference_portfolio_positions
ALTER TABLE reference_portfolio_positions
  ADD COLUMN IF NOT EXISTS asset_type TEXT NOT NULL DEFAULT 'stock';

-- 3. Change quantity from INTEGER to DECIMAL in positions (for fractional crypto)
ALTER TABLE reference_portfolio_positions
  ALTER COLUMN quantity TYPE DECIMAL(18,8);

-- 4. Add asset_type to reference_portfolio_transactions
ALTER TABLE reference_portfolio_transactions
  ADD COLUMN IF NOT EXISTS asset_type TEXT NOT NULL DEFAULT 'stock';

-- 5. Change quantity from INTEGER to DECIMAL in transactions (for fractional crypto)
ALTER TABLE reference_portfolio_transactions
  ALTER COLUMN quantity TYPE DECIMAL(18,8);

-- 6. Add extended hours + crypto config to reference_portfolio_config
ALTER TABLE reference_portfolio_config
  ADD COLUMN IF NOT EXISTS extended_hours_enabled BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS extended_hours_limit_buffer_pct DECIMAL(5,2) NOT NULL DEFAULT 0.50,
  ADD COLUMN IF NOT EXISTS crypto_enabled BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS crypto_base_position_size_pct DECIMAL(5,2) NOT NULL DEFAULT 0.50,
  ADD COLUMN IF NOT EXISTS crypto_max_positions INTEGER NOT NULL DEFAULT 5,
  ADD COLUMN IF NOT EXISTS crypto_stop_loss_pct DECIMAL(5,2) NOT NULL DEFAULT 15.00,
  ADD COLUMN IF NOT EXISTS crypto_take_profit_pct DECIMAL(5,2) NOT NULL DEFAULT 25.00;

-- 7. Indexes for efficient filtering by asset type
CREATE INDEX IF NOT EXISTS idx_trading_signals_asset_type ON trading_signals(asset_type);
CREATE INDEX IF NOT EXISTS idx_rp_positions_asset_type ON reference_portfolio_positions(asset_type);
