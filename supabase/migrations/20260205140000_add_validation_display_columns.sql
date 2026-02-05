-- Add display columns to trade_validation_results
-- These columns store denormalized data for efficient dashboard display

-- =============================================================================
-- Add display columns
-- =============================================================================

ALTER TABLE trade_validation_results
ADD COLUMN IF NOT EXISTS politician_name TEXT,
ADD COLUMN IF NOT EXISTS ticker TEXT,
ADD COLUMN IF NOT EXISTS transaction_date DATE,
ADD COLUMN IF NOT EXISTS transaction_type TEXT;

-- =============================================================================
-- Create indexes for filtering/sorting
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_validation_politician_name
    ON trade_validation_results(politician_name);

CREATE INDEX IF NOT EXISTS idx_validation_ticker
    ON trade_validation_results(ticker);

CREATE INDEX IF NOT EXISTS idx_validation_transaction_date
    ON trade_validation_results(transaction_date DESC);

CREATE INDEX IF NOT EXISTS idx_validation_transaction_type
    ON trade_validation_results(transaction_type);

-- =============================================================================
-- Backfill existing records from trading_disclosures and politicians
-- =============================================================================

-- For records that have a trading_disclosure_id, backfill from the linked tables
UPDATE trade_validation_results v
SET
    politician_name = p.full_name,
    ticker = td.asset_ticker,
    transaction_date = td.transaction_date,
    transaction_type = td.transaction_type
FROM trading_disclosures td
LEFT JOIN politicians p ON td.politician_id = p.id
WHERE v.trading_disclosure_id = td.id
  AND v.politician_name IS NULL;

-- For quiver_only records, extract from quiver_record JSONB
UPDATE trade_validation_results v
SET
    politician_name = COALESCE(
        v.quiver_record->>'Representative',
        v.politician_name
    ),
    ticker = COALESCE(
        v.quiver_record->>'Ticker',
        v.ticker
    ),
    transaction_date = COALESCE(
        (v.quiver_record->>'TransactionDate')::date,
        v.transaction_date
    ),
    transaction_type = COALESCE(
        v.quiver_record->>'Transaction',
        v.transaction_type
    )
WHERE v.validation_status = 'quiver_only'
  AND v.quiver_record IS NOT NULL
  AND v.politician_name IS NULL;

-- =============================================================================
-- Comments
-- =============================================================================

COMMENT ON COLUMN trade_validation_results.politician_name IS
    'Denormalized politician name for display (from app or QuiverQuant)';

COMMENT ON COLUMN trade_validation_results.ticker IS
    'Denormalized ticker symbol for display';

COMMENT ON COLUMN trade_validation_results.transaction_date IS
    'Transaction date for display and filtering';

COMMENT ON COLUMN trade_validation_results.transaction_type IS
    'Transaction type (purchase, sale, etc.) for display';
