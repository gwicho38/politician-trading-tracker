-- Fix existing trading schema by adding missing columns
-- Run this if you get "column does not exist" errors

-- =============================================================================
-- Fix Trading Signals Table
-- =============================================================================

-- Add missing columns to trading_signals if they don't exist
DO $$
BEGIN
    -- Add ticker column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_signals' AND column_name='ticker') THEN
        ALTER TABLE trading_signals ADD COLUMN ticker TEXT NOT NULL DEFAULT '';
    END IF;

    -- Add asset_name column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_signals' AND column_name='asset_name') THEN
        ALTER TABLE trading_signals ADD COLUMN asset_name TEXT NOT NULL DEFAULT '';
    END IF;

    -- Add signal_type column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_signals' AND column_name='signal_type') THEN
        ALTER TABLE trading_signals ADD COLUMN signal_type TEXT NOT NULL DEFAULT 'hold';
        ALTER TABLE trading_signals ADD CONSTRAINT trading_signals_signal_type_check
            CHECK (signal_type IN ('buy', 'sell', 'hold', 'strong_buy', 'strong_sell'));
    END IF;

    -- Add signal_strength column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_signals' AND column_name='signal_strength') THEN
        ALTER TABLE trading_signals ADD COLUMN signal_strength TEXT NOT NULL DEFAULT 'moderate';
        ALTER TABLE trading_signals ADD CONSTRAINT trading_signals_signal_strength_check
            CHECK (signal_strength IN ('very_weak', 'weak', 'moderate', 'strong', 'very_strong'));
    END IF;

    -- Add confidence_score column (THIS IS THE KEY ONE!)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_signals' AND column_name='confidence_score') THEN
        ALTER TABLE trading_signals ADD COLUMN confidence_score DECIMAL(5,4) NOT NULL DEFAULT 0.5;
        ALTER TABLE trading_signals ADD CONSTRAINT trading_signals_confidence_score_check
            CHECK (confidence_score >= 0 AND confidence_score <= 1);
    END IF;

    -- Add price target columns
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_signals' AND column_name='target_price') THEN
        ALTER TABLE trading_signals ADD COLUMN target_price DECIMAL(12,2);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_signals' AND column_name='stop_loss') THEN
        ALTER TABLE trading_signals ADD COLUMN stop_loss DECIMAL(12,2);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_signals' AND column_name='take_profit') THEN
        ALTER TABLE trading_signals ADD COLUMN take_profit DECIMAL(12,2);
    END IF;

    -- Add signal generation info
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_signals' AND column_name='generated_at') THEN
        ALTER TABLE trading_signals ADD COLUMN generated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW();
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_signals' AND column_name='valid_until') THEN
        ALTER TABLE trading_signals ADD COLUMN valid_until TIMESTAMP WITH TIME ZONE;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_signals' AND column_name='model_version') THEN
        ALTER TABLE trading_signals ADD COLUMN model_version TEXT NOT NULL DEFAULT 'v1.0';
    END IF;

    -- Add supporting data columns
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_signals' AND column_name='politician_activity_count') THEN
        ALTER TABLE trading_signals ADD COLUMN politician_activity_count INTEGER DEFAULT 0;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_signals' AND column_name='total_transaction_volume') THEN
        ALTER TABLE trading_signals ADD COLUMN total_transaction_volume DECIMAL(15,2);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_signals' AND column_name='buy_sell_ratio') THEN
        ALTER TABLE trading_signals ADD COLUMN buy_sell_ratio DECIMAL(8,4);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_signals' AND column_name='avg_politician_return') THEN
        ALTER TABLE trading_signals ADD COLUMN avg_politician_return DECIMAL(8,4);
    END IF;

    -- Add feature data
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_signals' AND column_name='features') THEN
        ALTER TABLE trading_signals ADD COLUMN features JSONB;
    END IF;

    -- Add disclosure_ids
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_signals' AND column_name='disclosure_ids') THEN
        ALTER TABLE trading_signals ADD COLUMN disclosure_ids TEXT[];
    END IF;

    -- Add status columns
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_signals' AND column_name='is_active') THEN
        ALTER TABLE trading_signals ADD COLUMN is_active BOOLEAN DEFAULT true;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_signals' AND column_name='notes') THEN
        ALTER TABLE trading_signals ADD COLUMN notes TEXT;
    END IF;
END $$;

-- =============================================================================
-- Fix Trading Orders Table
-- =============================================================================

DO $$
BEGIN
    -- Add trading_mode column (THIS IS THE KEY ONE!)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_orders' AND column_name='trading_mode') THEN
        ALTER TABLE trading_orders ADD COLUMN trading_mode TEXT NOT NULL DEFAULT 'paper';
        ALTER TABLE trading_orders ADD CONSTRAINT trading_orders_trading_mode_check
            CHECK (trading_mode IN ('paper', 'live'));
    END IF;

    -- Add other essential columns if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_orders' AND column_name='ticker') THEN
        ALTER TABLE trading_orders ADD COLUMN ticker TEXT NOT NULL DEFAULT '';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_orders' AND column_name='order_type') THEN
        ALTER TABLE trading_orders ADD COLUMN order_type TEXT NOT NULL DEFAULT 'market';
        ALTER TABLE trading_orders ADD CONSTRAINT trading_orders_order_type_check
            CHECK (order_type IN ('market', 'limit', 'stop', 'stop_limit', 'trailing_stop'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_orders' AND column_name='side') THEN
        ALTER TABLE trading_orders ADD COLUMN side TEXT NOT NULL DEFAULT 'buy';
        ALTER TABLE trading_orders ADD CONSTRAINT trading_orders_side_check
            CHECK (side IN ('buy', 'sell'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_orders' AND column_name='quantity') THEN
        ALTER TABLE trading_orders ADD COLUMN quantity INTEGER NOT NULL DEFAULT 1;
        ALTER TABLE trading_orders ADD CONSTRAINT trading_orders_quantity_check
            CHECK (quantity > 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_orders' AND column_name='status') THEN
        ALTER TABLE trading_orders ADD COLUMN status TEXT NOT NULL DEFAULT 'pending';
        ALTER TABLE trading_orders ADD CONSTRAINT trading_orders_status_check
            CHECK (status IN ('pending', 'submitted', 'filled', 'partially_filled', 'canceled', 'rejected', 'expired'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_orders' AND column_name='limit_price') THEN
        ALTER TABLE trading_orders ADD COLUMN limit_price DECIMAL(12,2);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_orders' AND column_name='stop_price') THEN
        ALTER TABLE trading_orders ADD COLUMN stop_price DECIMAL(12,2);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_orders' AND column_name='trailing_percent') THEN
        ALTER TABLE trading_orders ADD COLUMN trailing_percent DECIMAL(5,2);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_orders' AND column_name='filled_quantity') THEN
        ALTER TABLE trading_orders ADD COLUMN filled_quantity INTEGER DEFAULT 0;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_orders' AND column_name='filled_avg_price') THEN
        ALTER TABLE trading_orders ADD COLUMN filled_avg_price DECIMAL(12,4);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_orders' AND column_name='commission') THEN
        ALTER TABLE trading_orders ADD COLUMN commission DECIMAL(10,4);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_orders' AND column_name='alpaca_order_id') THEN
        ALTER TABLE trading_orders ADD COLUMN alpaca_order_id TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_orders' AND column_name='alpaca_client_order_id') THEN
        ALTER TABLE trading_orders ADD COLUMN alpaca_client_order_id TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_orders' AND column_name='submitted_at') THEN
        ALTER TABLE trading_orders ADD COLUMN submitted_at TIMESTAMP WITH TIME ZONE;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_orders' AND column_name='filled_at') THEN
        ALTER TABLE trading_orders ADD COLUMN filled_at TIMESTAMP WITH TIME ZONE;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_orders' AND column_name='canceled_at') THEN
        ALTER TABLE trading_orders ADD COLUMN canceled_at TIMESTAMP WITH TIME ZONE;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_orders' AND column_name='expired_at') THEN
        ALTER TABLE trading_orders ADD COLUMN expired_at TIMESTAMP WITH TIME ZONE;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_orders' AND column_name='error_message') THEN
        ALTER TABLE trading_orders ADD COLUMN error_message TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_orders' AND column_name='reject_reason') THEN
        ALTER TABLE trading_orders ADD COLUMN reject_reason TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_orders' AND column_name='metadata') THEN
        ALTER TABLE trading_orders ADD COLUMN metadata JSONB;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trading_orders' AND column_name='signal_id') THEN
        ALTER TABLE trading_orders ADD COLUMN signal_id UUID REFERENCES trading_signals(id);
    END IF;
END $$;

-- Create indexes if they don't exist
CREATE INDEX IF NOT EXISTS idx_trading_signals_ticker ON trading_signals(ticker);
CREATE INDEX IF NOT EXISTS idx_trading_signals_signal_type ON trading_signals(signal_type);
CREATE INDEX IF NOT EXISTS idx_trading_signals_confidence ON trading_signals(confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_trading_signals_generated_at ON trading_signals(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_trading_signals_is_active ON trading_signals(is_active);

CREATE INDEX IF NOT EXISTS idx_trading_orders_ticker ON trading_orders(ticker);
CREATE INDEX IF NOT EXISTS idx_trading_orders_status ON trading_orders(status);
CREATE INDEX IF NOT EXISTS idx_trading_orders_trading_mode ON trading_orders(trading_mode);
CREATE INDEX IF NOT EXISTS idx_trading_orders_alpaca_order_id ON trading_orders(alpaca_order_id);
CREATE INDEX IF NOT EXISTS idx_trading_orders_created_at ON trading_orders(created_at DESC);
