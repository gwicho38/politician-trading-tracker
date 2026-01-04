-- Migration: Server-side cart persistence
-- This migration creates the user_carts table for persisting shopping cart data

-- Create the user_carts table
CREATE TABLE IF NOT EXISTS user_carts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    signal_id TEXT NOT NULL, -- Can be signal UUID or ticker for preview signals
    ticker TEXT NOT NULL,
    asset_name TEXT,
    signal_type TEXT NOT NULL CHECK (signal_type IN ('strong_buy', 'buy', 'hold', 'sell', 'strong_sell')),
    confidence_score DECIMAL NOT NULL,
    politician_activity_count INTEGER NOT NULL DEFAULT 0,
    buy_sell_ratio DECIMAL,
    target_price DECIMAL,
    source TEXT NOT NULL CHECK (source IN ('trading_signals', 'playground')),
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    total_transaction_volume DECIMAL,
    bipartisan BOOLEAN,
    signal_strength TEXT,
    generated_at TIMESTAMPTZ,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, ticker) -- One entry per ticker per user
);

-- Create indexes
CREATE INDEX idx_user_carts_user_id ON user_carts(user_id);
CREATE INDEX idx_user_carts_ticker ON user_carts(ticker);
CREATE INDEX idx_user_carts_added_at ON user_carts(added_at);

-- Enable RLS
ALTER TABLE user_carts ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Users can only access their own cart items
CREATE POLICY "Users can view own cart items"
    ON user_carts FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own cart items"
    ON user_carts FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own cart items"
    ON user_carts FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own cart items"
    ON user_carts FOR DELETE
    USING (auth.uid() = user_id);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_user_carts_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_user_carts_updated_at
    BEFORE UPDATE ON user_carts
    FOR EACH ROW
    EXECUTE FUNCTION update_user_carts_updated_at();

-- Comments
COMMENT ON TABLE user_carts IS 'Persisted shopping cart items for authenticated users';
COMMENT ON COLUMN user_carts.signal_id IS 'Signal ID (UUID) or ticker for playground signals';
COMMENT ON COLUMN user_carts.source IS 'Origin of the signal: trading_signals table or playground preview';
COMMENT ON COLUMN user_carts.quantity IS 'Number of shares to buy/sell';
