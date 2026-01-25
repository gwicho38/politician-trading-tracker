-- Backfill sell transactions from closed positions
-- This creates sell transaction records for all positions that were closed but don't have a corresponding sell transaction

INSERT INTO reference_portfolio_transactions (
  position_id,
  ticker,
  transaction_type,
  quantity,
  price,
  total_value,
  executed_at,
  alpaca_order_id,
  exit_reason,
  realized_pl,
  realized_pl_pct,
  signal_id,
  status
)
SELECT
  p.id as position_id,
  p.ticker,
  'sell' as transaction_type,
  p.quantity,
  p.exit_price as price,
  p.exit_price * p.quantity as total_value,
  p.exit_date as executed_at,
  p.exit_order_id as alpaca_order_id,
  p.exit_reason,
  p.realized_pl,
  p.realized_pl_pct,
  p.exit_signal_id as signal_id,
  'executed' as status
FROM reference_portfolio_positions p
WHERE p.is_open = false
  AND p.exit_date IS NOT NULL
  AND p.exit_price IS NOT NULL
  -- Exclude test positions
  AND p.ticker NOT LIKE 'TEST%'
  -- Only insert if no sell transaction exists for this position
  AND NOT EXISTS (
    SELECT 1
    FROM reference_portfolio_transactions t
    WHERE t.position_id = p.id
      AND t.transaction_type = 'sell'
  );
