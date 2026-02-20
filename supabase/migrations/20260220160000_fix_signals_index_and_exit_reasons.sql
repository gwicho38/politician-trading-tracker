-- Fix trading_signals timeout: add composite partial index for the primary query pattern
-- WHERE is_active = true ORDER BY created_at DESC
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trading_signals_active_created
  ON trading_signals(created_at DESC)
  WHERE is_active = true;

-- Fix exit_reason CHECK constraint: add 'position_not_found' and 'alpaca_closed'
-- These are needed by handleUpdatePositions() and handleCheckExits() for reconciliation
-- when Alpaca has closed a position but the DB still has it as open.
-- The original constraint only allowed: signal, stop_loss, take_profit, manual, rebalance
ALTER TABLE reference_portfolio_positions
  DROP CONSTRAINT IF EXISTS reference_portfolio_positions_exit_reason_check;

ALTER TABLE reference_portfolio_positions
  ADD CONSTRAINT reference_portfolio_positions_exit_reason_check
  CHECK (exit_reason IN ('signal', 'stop_loss', 'take_profit', 'manual', 'rebalance', 'position_not_found', 'alpaca_closed', 'trailing_stop', 'timeout'));
