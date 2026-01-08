-- Add ml_enhanced column to trading_signals table
-- This column tracks whether a signal was enhanced by ML predictions

ALTER TABLE trading_signals
ADD COLUMN IF NOT EXISTS ml_enhanced BOOLEAN DEFAULT false;

-- Add index for filtering ML-enhanced signals
CREATE INDEX IF NOT EXISTS idx_trading_signals_ml_enhanced ON trading_signals(ml_enhanced);

COMMENT ON COLUMN trading_signals.ml_enhanced IS 'Whether this signal was enhanced by ML model predictions';
