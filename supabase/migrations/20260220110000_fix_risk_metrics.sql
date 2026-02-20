-- Fix Risk Metrics Migration
-- Addresses data integrity issues:
-- 1. winning_trades/losing_trades counters drifted from actual closed positions
-- 2. Negative market_value on positions created by unintended short sells
-- 3. profit_factor, win_rate, avg_win, avg_loss out of sync

-- ============================================================================
-- 1. Fix positions with negative market_value
-- These were created when sell orders were placed against non-existent Alpaca
-- positions, causing Alpaca to open short positions with negative values.
-- ============================================================================
UPDATE reference_portfolio_positions
SET market_value = ABS(quantity * COALESCE(current_price, entry_price)),
    updated_at = NOW()
WHERE market_value < 0
  AND is_open = true;

-- ============================================================================
-- 2. Recalculate portfolio state from ground truth (closed positions)
-- Uses the existing recalculate_portfolio_state() function from migration
-- 20260128133800_fix_portfolio_state_sync.sql
-- ============================================================================
SELECT public.recalculate_portfolio_state();
