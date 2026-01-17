-- Add missing columns for sell transactions in reference portfolio
-- These columns store exit reason and realized P&L for sell trades

ALTER TABLE reference_portfolio_transactions
ADD COLUMN IF NOT EXISTS exit_reason TEXT,
ADD COLUMN IF NOT EXISTS realized_pl NUMERIC(12, 2),
ADD COLUMN IF NOT EXISTS realized_pl_pct NUMERIC(8, 4);

-- Add comment for documentation
COMMENT ON COLUMN reference_portfolio_transactions.exit_reason IS 'Reason for exit: stop_loss, take_profit, signal_sell, manual, etc.';
COMMENT ON COLUMN reference_portfolio_transactions.realized_pl IS 'Realized profit/loss in dollars for sell transactions';
COMMENT ON COLUMN reference_portfolio_transactions.realized_pl_pct IS 'Realized profit/loss percentage for sell transactions';
