-- Add foreign key relationships for PostgREST joins
-- Run in Supabase SQL Editor

-- Add foreign key from trades to politicians
ALTER TABLE trades
DROP CONSTRAINT IF EXISTS trades_politician_id_fkey;

ALTER TABLE trades
ADD CONSTRAINT trades_politician_id_fkey
FOREIGN KEY (politician_id) REFERENCES politicians(id) ON DELETE SET NULL;

-- Add foreign key from politicians to jurisdictions
ALTER TABLE politicians
DROP CONSTRAINT IF EXISTS politicians_jurisdiction_id_fkey;

ALTER TABLE politicians
ADD CONSTRAINT politicians_jurisdiction_id_fkey
FOREIGN KEY (jurisdiction_id) REFERENCES jurisdictions(id) ON DELETE SET NULL;

-- Add foreign key from trading_signals to trades
ALTER TABLE trading_signals
DROP CONSTRAINT IF EXISTS trading_signals_trade_id_fkey;

ALTER TABLE trading_signals
ADD CONSTRAINT trading_signals_trade_id_fkey
FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE SET NULL;

-- Add foreign key from trading_signals to politicians
ALTER TABLE trading_signals
DROP CONSTRAINT IF EXISTS trading_signals_politician_id_fkey;

ALTER TABLE trading_signals
ADD CONSTRAINT trading_signals_politician_id_fkey
FOREIGN KEY (politician_id) REFERENCES politicians(id) ON DELETE SET NULL;

SELECT 'Foreign keys added!' as status;
