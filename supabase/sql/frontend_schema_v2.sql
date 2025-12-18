-- Frontend Schema Migration v2
-- Run this in Supabase SQL Editor: https://app.supabase.com/project/uljsqvwkomdrlnofmlad/sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- STEP 1: Create base tables first (no foreign keys to user_roles)
-- ============================================================================

-- JURISDICTIONS
CREATE TABLE IF NOT EXISTS jurisdictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    code VARCHAR(50),
    region VARCHAR(50),
    country VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- TRADES
CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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

-- CHART_DATA
CREATE TABLE IF NOT EXISTS chart_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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

-- DASHBOARD_STATS
CREATE TABLE IF NOT EXISTS dashboard_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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

-- PROFILES
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY,
    email VARCHAR(255),
    full_name VARCHAR(200),
    avatar_url TEXT,
    subscription_tier VARCHAR(50) DEFAULT 'free',
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- USER_ROLES (fresh table with correct schema)
DROP TABLE IF EXISTS user_roles CASCADE;
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, role)
);

-- TRADING_SIGNALS
CREATE TABLE IF NOT EXISTS trading_signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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

-- NOTIFICATIONS
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,
    title VARCHAR(200) NOT NULL,
    message TEXT,
    type VARCHAR(50) DEFAULT 'info',
    is_read BOOLEAN DEFAULT FALSE,
    action_url TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- SYNC_LOGS
CREATE TABLE IF NOT EXISTS sync_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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

-- TRADING_ORDERS
CREATE TABLE IF NOT EXISTS trading_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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

-- ============================================================================
-- STEP 2: Add missing columns to politicians table
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'politicians' AND column_name = 'name') THEN
        ALTER TABLE politicians ADD COLUMN name VARCHAR(200);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'politicians' AND column_name = 'state') THEN
        ALTER TABLE politicians ADD COLUMN state VARCHAR(100);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'politicians' AND column_name = 'chamber') THEN
        ALTER TABLE politicians ADD COLUMN chamber VARCHAR(50);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'politicians' AND column_name = 'position') THEN
        ALTER TABLE politicians ADD COLUMN position VARCHAR(100);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'politicians' AND column_name = 'is_active') THEN
        ALTER TABLE politicians ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'politicians' AND column_name = 'image_url') THEN
        ALTER TABLE politicians ADD COLUMN image_url TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'politicians' AND column_name = 'party') THEN
        ALTER TABLE politicians ADD COLUMN party VARCHAR(50);
    END IF;
END $$;

-- Populate name from existing columns
UPDATE politicians
SET name = COALESCE(full_name, CONCAT(first_name, ' ', last_name))
WHERE name IS NULL;

-- Populate state from state_or_country if exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'politicians' AND column_name = 'state_or_country') THEN
        UPDATE politicians SET state = state_or_country WHERE state IS NULL;
    END IF;
END $$;

-- ============================================================================
-- STEP 3: Indexes
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_trades_ticker ON trades(ticker);
CREATE INDEX IF NOT EXISTS idx_trades_transaction_date ON trades(transaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_trades_created ON trades(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trading_signals_ticker ON trading_signals(ticker);
CREATE INDEX IF NOT EXISTS idx_trading_signals_active ON trading_signals(is_active);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_sync_logs_source ON sync_logs(source);
CREATE INDEX IF NOT EXISTS idx_trading_orders_user ON trading_orders(user_id);

-- ============================================================================
-- STEP 4: Enable RLS
-- ============================================================================
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

-- ============================================================================
-- STEP 5: Simple public read policies (no admin checks yet)
-- ============================================================================
DROP POLICY IF EXISTS "anon_read_jurisdictions" ON jurisdictions;
CREATE POLICY "anon_read_jurisdictions" ON jurisdictions FOR SELECT USING (true);

DROP POLICY IF EXISTS "anon_read_trades" ON trades;
CREATE POLICY "anon_read_trades" ON trades FOR SELECT USING (true);

DROP POLICY IF EXISTS "anon_read_chart_data" ON chart_data;
CREATE POLICY "anon_read_chart_data" ON chart_data FOR SELECT USING (true);

DROP POLICY IF EXISTS "anon_read_dashboard_stats" ON dashboard_stats;
CREATE POLICY "anon_read_dashboard_stats" ON dashboard_stats FOR SELECT USING (true);

DROP POLICY IF EXISTS "anon_read_trading_signals" ON trading_signals;
CREATE POLICY "anon_read_trading_signals" ON trading_signals FOR SELECT USING (true);

-- User policies
DROP POLICY IF EXISTS "user_read_profile" ON profiles;
CREATE POLICY "user_read_profile" ON profiles FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "user_write_profile" ON profiles;
CREATE POLICY "user_write_profile" ON profiles FOR ALL USING (auth.uid() = id);

DROP POLICY IF EXISTS "user_read_roles" ON user_roles;
CREATE POLICY "user_read_roles" ON user_roles FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "user_read_notifications" ON notifications;
CREATE POLICY "user_read_notifications" ON notifications FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "user_update_notifications" ON notifications;
CREATE POLICY "user_update_notifications" ON notifications FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "user_manage_orders" ON trading_orders;
CREATE POLICY "user_manage_orders" ON trading_orders FOR ALL USING (auth.uid() = user_id);

-- Service role full access
DROP POLICY IF EXISTS "service_full_access_sync_logs" ON sync_logs;
CREATE POLICY "service_full_access_sync_logs" ON sync_logs FOR ALL USING (true);

-- ============================================================================
-- STEP 6: Seed data
-- ============================================================================
INSERT INTO jurisdictions (name, code, region, country) VALUES
    ('US House of Representatives', 'us_house', 'North America', 'United States'),
    ('US Senate', 'us_senate', 'North America', 'United States'),
    ('UK Parliament', 'uk_parliament', 'Europe', 'United Kingdom'),
    ('EU Parliament', 'eu_parliament', 'Europe', 'European Union')
ON CONFLICT DO NOTHING;

INSERT INTO dashboard_stats (total_trades, total_politicians, total_volume, trades_this_month)
SELECT 0, 0, 0, 0 WHERE NOT EXISTS (SELECT 1 FROM dashboard_stats LIMIT 1);

-- ============================================================================
-- STEP 7: Grants
-- ============================================================================
GRANT SELECT ON jurisdictions TO anon, authenticated;
GRANT SELECT ON trades TO anon, authenticated;
GRANT SELECT ON chart_data TO anon, authenticated;
GRANT SELECT ON dashboard_stats TO anon, authenticated;
GRANT SELECT ON trading_signals TO anon, authenticated;
GRANT ALL ON profiles TO authenticated;
GRANT SELECT ON user_roles TO authenticated;
GRANT ALL ON notifications TO authenticated;
GRANT ALL ON trading_orders TO authenticated;
GRANT ALL ON sync_logs TO authenticated;

-- Done!
SELECT 'Migration completed successfully!' as status;
