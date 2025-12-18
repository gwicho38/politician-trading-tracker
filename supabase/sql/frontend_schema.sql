-- Frontend Schema for Politician Trading Tracker
-- Creates all tables required by the React frontend
-- Execute this in your Supabase SQL Editor (https://app.supabase.com/project/uljsqvwkomdrlnofmlad/sql)

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- JURISDICTIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS jurisdictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL UNIQUE,
    code VARCHAR(50),
    region VARCHAR(50),
    country VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- POLITICIANS TABLE (matching frontend expectations)
-- ============================================================================
CREATE TABLE IF NOT EXISTS politicians (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    party VARCHAR(50),
    state VARCHAR(100),
    district VARCHAR(50),
    chamber VARCHAR(50),
    position VARCHAR(100),
    jurisdiction_id UUID REFERENCES jurisdictions(id),
    bioguide_id VARCHAR(20),
    image_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- TRADES TABLE (matching frontend expectations)
-- ============================================================================
CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    politician_id UUID REFERENCES politicians(id),
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

-- ============================================================================
-- CHART_DATA TABLE (for dashboard visualizations)
-- ============================================================================
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
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(year, month)
);

-- ============================================================================
-- DASHBOARD_STATS TABLE (for dashboard summary)
-- ============================================================================
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

-- ============================================================================
-- PROFILES TABLE (user profiles)
-- ============================================================================
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email VARCHAR(255),
    full_name VARCHAR(200),
    avatar_url TEXT,
    subscription_tier VARCHAR(50) DEFAULT 'free',
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- USER_ROLES TABLE (for role-based access)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('admin', 'user', 'premium')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, role)
);

-- ============================================================================
-- TRADING_SIGNALS TABLE (for trading signals feature)
-- ============================================================================
CREATE TABLE IF NOT EXISTS trading_signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker VARCHAR(20) NOT NULL,
    signal_type VARCHAR(50) NOT NULL,
    strength DECIMAL(5,2),
    confidence DECIMAL(5,2),
    source VARCHAR(100),
    politician_id UUID REFERENCES politicians(id),
    politician_name VARCHAR(200),
    trade_id UUID REFERENCES trades(id),
    analysis JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- NOTIFICATIONS TABLE (for user notifications)
-- ============================================================================
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    message TEXT,
    type VARCHAR(50) DEFAULT 'info',
    is_read BOOLEAN DEFAULT FALSE,
    action_url TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- SYNC_LOGS TABLE (for admin sync status)
-- ============================================================================
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

-- ============================================================================
-- TRADING_ORDERS TABLE (for paper/live trading)
-- ============================================================================
CREATE TABLE IF NOT EXISTS trading_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    ticker VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('buy', 'sell')),
    quantity DECIMAL(15,4) NOT NULL,
    order_type VARCHAR(20) NOT NULL,
    limit_price DECIMAL(15,2),
    stop_price DECIMAL(15,2),
    status VARCHAR(50) DEFAULT 'pending',
    filled_quantity DECIMAL(15,4) DEFAULT 0,
    filled_avg_price DECIMAL(15,2),
    signal_id UUID REFERENCES trading_signals(id),
    external_order_id VARCHAR(100),
    broker VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_politicians_name ON politicians(name);
CREATE INDEX IF NOT EXISTS idx_politicians_party ON politicians(party);
CREATE INDEX IF NOT EXISTS idx_politicians_state ON politicians(state);
CREATE INDEX IF NOT EXISTS idx_politicians_jurisdiction ON politicians(jurisdiction_id);

CREATE INDEX IF NOT EXISTS idx_trades_politician ON trades(politician_id);
CREATE INDEX IF NOT EXISTS idx_trades_ticker ON trades(ticker);
CREATE INDEX IF NOT EXISTS idx_trades_transaction_date ON trades(transaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_trades_disclosure_date ON trades(disclosure_date DESC);
CREATE INDEX IF NOT EXISTS idx_trades_type ON trades(transaction_type);
CREATE INDEX IF NOT EXISTS idx_trades_created ON trades(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_trading_signals_ticker ON trading_signals(ticker);
CREATE INDEX IF NOT EXISTS idx_trading_signals_active ON trading_signals(is_active);
CREATE INDEX IF NOT EXISTS idx_trading_signals_created ON trading_signals(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(is_read);

CREATE INDEX IF NOT EXISTS idx_sync_logs_source ON sync_logs(source);
CREATE INDEX IF NOT EXISTS idx_sync_logs_status ON sync_logs(status);
CREATE INDEX IF NOT EXISTS idx_sync_logs_created ON sync_logs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_trading_orders_user ON trading_orders(user_id);
CREATE INDEX IF NOT EXISTS idx_trading_orders_status ON trading_orders(status);

-- ============================================================================
-- UPDATED_AT TRIGGER FUNCTION
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

-- Apply triggers
DO $$
DECLARE
    tbl TEXT;
    tables TEXT[] := ARRAY['jurisdictions', 'politicians', 'trades', 'chart_data',
                           'dashboard_stats', 'profiles', 'user_roles', 'trading_signals',
                           'trading_orders'];
BEGIN
    FOREACH tbl IN ARRAY tables LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS update_%s_updated_at ON %s', tbl, tbl);
        EXECUTE format('CREATE TRIGGER update_%s_updated_at BEFORE UPDATE ON %s FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()', tbl, tbl);
    END LOOP;
END $$;

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================
ALTER TABLE jurisdictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE politicians ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE chart_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE trading_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE trading_orders ENABLE ROW LEVEL SECURITY;

-- Public read access policies (anon + authenticated)
CREATE POLICY "Public read jurisdictions" ON jurisdictions FOR SELECT USING (true);
CREATE POLICY "Public read politicians" ON politicians FOR SELECT USING (true);
CREATE POLICY "Public read trades" ON trades FOR SELECT USING (true);
CREATE POLICY "Public read chart_data" ON chart_data FOR SELECT USING (true);
CREATE POLICY "Public read dashboard_stats" ON dashboard_stats FOR SELECT USING (true);
CREATE POLICY "Public read trading_signals" ON trading_signals FOR SELECT USING (true);

-- User-specific policies
CREATE POLICY "Users read own profile" ON profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users update own profile" ON profiles FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Users insert own profile" ON profiles FOR INSERT WITH CHECK (auth.uid() = id);

CREATE POLICY "Users read own roles" ON user_roles FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users read own notifications" ON notifications FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users update own notifications" ON notifications FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users read own orders" ON trading_orders FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users insert own orders" ON trading_orders FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users update own orders" ON trading_orders FOR UPDATE USING (auth.uid() = user_id);

-- Admin policies (check for admin role)
CREATE POLICY "Admins manage jurisdictions" ON jurisdictions FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
);
CREATE POLICY "Admins manage politicians" ON politicians FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
);
CREATE POLICY "Admins manage trades" ON trades FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
);
CREATE POLICY "Admins manage chart_data" ON chart_data FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
);
CREATE POLICY "Admins manage dashboard_stats" ON dashboard_stats FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
);
CREATE POLICY "Admins manage trading_signals" ON trading_signals FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
);
CREATE POLICY "Admins manage notifications" ON notifications FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
);
CREATE POLICY "Admins manage user_roles" ON user_roles FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role = 'admin')
);
CREATE POLICY "Admins read sync_logs" ON sync_logs FOR SELECT USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
);
CREATE POLICY "Service role sync_logs" ON sync_logs FOR ALL USING (auth.role() = 'service_role');

-- ============================================================================
-- SEED DATA - Jurisdictions
-- ============================================================================
INSERT INTO jurisdictions (name, code, region, country) VALUES
    ('US House of Representatives', 'us_house', 'North America', 'United States'),
    ('US Senate', 'us_senate', 'North America', 'United States'),
    ('UK Parliament', 'uk_parliament', 'Europe', 'United Kingdom'),
    ('EU Parliament', 'eu_parliament', 'Europe', 'European Union'),
    ('California State Legislature', 'ca_state', 'North America', 'United States'),
    ('Texas State Legislature', 'tx_state', 'North America', 'United States'),
    ('New York State Legislature', 'ny_state', 'North America', 'United States')
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- SEED DATA - Initial Dashboard Stats
-- ============================================================================
INSERT INTO dashboard_stats (total_trades, total_politicians, total_volume, trades_this_month)
VALUES (0, 0, 0, 0)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- GRANTS
-- ============================================================================
GRANT SELECT ON jurisdictions TO anon, authenticated;
GRANT SELECT ON politicians TO anon, authenticated;
GRANT SELECT ON trades TO anon, authenticated;
GRANT SELECT ON chart_data TO anon, authenticated;
GRANT SELECT ON dashboard_stats TO anon, authenticated;
GRANT SELECT ON trading_signals TO anon, authenticated;

GRANT SELECT, INSERT, UPDATE ON profiles TO authenticated;
GRANT SELECT ON user_roles TO authenticated;
GRANT SELECT, UPDATE ON notifications TO authenticated;
GRANT SELECT, INSERT, UPDATE ON trading_orders TO authenticated;

-- ============================================================================
-- COMPLETION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE 'Frontend schema created successfully!';
    RAISE NOTICE 'Tables: jurisdictions, politicians, trades, chart_data, dashboard_stats,';
    RAISE NOTICE '        profiles, user_roles, trading_signals, notifications, sync_logs, trading_orders';
END $$;
