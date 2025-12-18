-- Clean Migration - drops and recreates all frontend tables
-- Run in Supabase SQL Editor

-- Drop existing tables (in reverse dependency order)
DROP TABLE IF EXISTS trading_orders CASCADE;
DROP TABLE IF EXISTS trading_signals CASCADE;
DROP TABLE IF EXISTS sync_logs CASCADE;
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS user_roles CASCADE;
DROP TABLE IF EXISTS profiles CASCADE;
DROP TABLE IF EXISTS dashboard_stats CASCADE;
DROP TABLE IF EXISTS chart_data CASCADE;
DROP TABLE IF EXISTS trades CASCADE;
DROP TABLE IF EXISTS jurisdictions CASCADE;

-- Create tables fresh

CREATE TABLE jurisdictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    code VARCHAR(50),
    region VARCHAR(50),
    country VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    politician_id UUID,
    politician_name VARCHAR(200),
    transaction_date TIMESTAMPTZ NOT NULL,
    disclosure_date TIMESTAMPTZ,
    ticker VARCHAR(20),
    asset_description VARCHAR(500),
    asset_type VARCHAR(100),
    transaction_type VARCHAR(50) NOT NULL,
    amount VARCHAR(100),
    amount_min DECIMAL(15,2),
    amount_max DECIMAL(15,2),
    price DECIMAL(15,2),
    party VARCHAR(50),
    state VARCHAR(100),
    chamber VARCHAR(50),
    source VARCHAR(100),
    source_url TEXT,
    raw_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE chart_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    total_trades INTEGER DEFAULT 0,
    buy_count INTEGER DEFAULT 0,
    sell_count INTEGER DEFAULT 0,
    total_volume DECIMAL(20,2) DEFAULT 0,
    unique_politicians INTEGER DEFAULT 0,
    top_tickers JSONB,
    party_breakdown JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE dashboard_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    total_trades INTEGER DEFAULT 0,
    total_politicians INTEGER DEFAULT 0,
    total_volume DECIMAL(20,2) DEFAULT 0,
    trades_this_month INTEGER DEFAULT 0,
    top_traded_stock VARCHAR(20),
    most_active_politician VARCHAR(200),
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    stats_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE profiles (
    id UUID PRIMARY KEY,
    email VARCHAR(255),
    full_name VARCHAR(200),
    avatar_url TEXT,
    subscription_tier VARCHAR(50) DEFAULT 'free',
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, role)
);

CREATE TABLE trading_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(20) NOT NULL,
    signal_type VARCHAR(50) NOT NULL,
    strength DECIMAL(5,2),
    confidence DECIMAL(5,2),
    source VARCHAR(100),
    politician_id UUID,
    politician_name VARCHAR(200),
    trade_id UUID,
    analysis JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    title VARCHAR(200) NOT NULL,
    message TEXT,
    type VARCHAR(50) DEFAULT 'info',
    is_read BOOLEAN DEFAULT FALSE,
    action_url TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE sync_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    records_found INTEGER DEFAULT 0,
    records_processed INTEGER DEFAULT 0,
    records_new INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_message TEXT,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE trading_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    ticker VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(15,4) NOT NULL,
    order_type VARCHAR(20) NOT NULL,
    limit_price DECIMAL(15,2),
    stop_price DECIMAL(15,2),
    status VARCHAR(50) DEFAULT 'pending',
    filled_quantity DECIMAL(15,4) DEFAULT 0,
    filled_avg_price DECIMAL(15,2),
    signal_id UUID,
    external_order_id VARCHAR(100),
    broker VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add missing columns to politicians (don't drop - has data)
ALTER TABLE politicians ADD COLUMN IF NOT EXISTS name VARCHAR(200);
ALTER TABLE politicians ADD COLUMN IF NOT EXISTS state VARCHAR(100);
ALTER TABLE politicians ADD COLUMN IF NOT EXISTS chamber VARCHAR(50);
ALTER TABLE politicians ADD COLUMN IF NOT EXISTS position VARCHAR(100);
ALTER TABLE politicians ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE politicians ADD COLUMN IF NOT EXISTS image_url TEXT;
ALTER TABLE politicians ADD COLUMN IF NOT EXISTS party VARCHAR(50);

-- Indexes
CREATE INDEX idx_trades_ticker ON trades(ticker);
CREATE INDEX idx_trades_date ON trades(transaction_date DESC);
CREATE INDEX idx_signals_ticker ON trading_signals(ticker);
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_orders_user ON trading_orders(user_id);

-- Enable RLS on all tables
ALTER TABLE jurisdictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE chart_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE trading_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE trading_orders ENABLE ROW LEVEL SECURITY;

-- Simple public read policies
CREATE POLICY "read_jurisdictions" ON jurisdictions FOR SELECT USING (true);
CREATE POLICY "read_trades" ON trades FOR SELECT USING (true);
CREATE POLICY "read_chart_data" ON chart_data FOR SELECT USING (true);
CREATE POLICY "read_dashboard_stats" ON dashboard_stats FOR SELECT USING (true);
CREATE POLICY "read_trading_signals" ON trading_signals FOR SELECT USING (true);
CREATE POLICY "read_politicians" ON politicians FOR SELECT USING (true);

-- User-specific policies
CREATE POLICY "profiles_policy" ON profiles FOR ALL USING (auth.uid() = id);
CREATE POLICY "user_roles_policy" ON user_roles FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "notifications_policy" ON notifications FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "orders_policy" ON trading_orders FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "sync_logs_policy" ON sync_logs FOR ALL USING (true);

-- Seed data
INSERT INTO jurisdictions (name, code, region, country) VALUES
    ('US House of Representatives', 'us_house', 'North America', 'United States'),
    ('US Senate', 'us_senate', 'North America', 'United States'),
    ('UK Parliament', 'uk_parliament', 'Europe', 'United Kingdom'),
    ('EU Parliament', 'eu_parliament', 'Europe', 'European Union');

INSERT INTO dashboard_stats (total_trades, total_politicians, total_volume, trades_this_month)
VALUES (0, 0, 0, 0);

-- Grants
GRANT SELECT ON jurisdictions TO anon, authenticated;
GRANT SELECT ON politicians TO anon, authenticated;
GRANT SELECT ON trades TO anon, authenticated;
GRANT SELECT ON chart_data TO anon, authenticated;
GRANT SELECT ON dashboard_stats TO anon, authenticated;
GRANT SELECT ON trading_signals TO anon, authenticated;
GRANT ALL ON profiles TO authenticated;
GRANT SELECT ON user_roles TO authenticated;
GRANT ALL ON notifications TO authenticated;
GRANT ALL ON trading_orders TO authenticated;
GRANT ALL ON sync_logs TO authenticated;

SELECT 'Migration complete!' as result;
