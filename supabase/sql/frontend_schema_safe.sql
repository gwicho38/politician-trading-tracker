-- Safe Frontend Schema Migration for Politician Trading Tracker
-- Handles existing tables by adding missing columns
-- Execute this in your Supabase SQL Editor

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- JURISDICTIONS TABLE (create if not exists)
-- ============================================================================
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

-- Add unique constraint if not exists
DO $$ BEGIN
    ALTER TABLE jurisdictions ADD CONSTRAINT jurisdictions_name_key UNIQUE (name);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================================
-- POLITICIANS TABLE - Add missing columns to existing table
-- ============================================================================
DO $$ BEGIN
    -- Add 'name' column if it doesn't exist (computed from first_name + last_name or full_name)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'politicians' AND column_name = 'name') THEN
        ALTER TABLE politicians ADD COLUMN name VARCHAR(200);
        -- Populate from existing data
        UPDATE politicians SET name = COALESCE(full_name, first_name || ' ' || last_name) WHERE name IS NULL;
    END IF;

    -- Add other potentially missing columns
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'politicians' AND column_name = 'chamber') THEN
        ALTER TABLE politicians ADD COLUMN chamber VARCHAR(50);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'politicians' AND column_name = 'position') THEN
        ALTER TABLE politicians ADD COLUMN position VARCHAR(100);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'politicians' AND column_name = 'jurisdiction_id') THEN
        ALTER TABLE politicians ADD COLUMN jurisdiction_id UUID REFERENCES jurisdictions(id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'politicians' AND column_name = 'image_url') THEN
        ALTER TABLE politicians ADD COLUMN image_url TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'politicians' AND column_name = 'is_active') THEN
        ALTER TABLE politicians ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'politicians' AND column_name = 'state') THEN
        ALTER TABLE politicians ADD COLUMN state VARCHAR(100);
        -- Populate from state_or_country if exists
        UPDATE politicians SET state = state_or_country WHERE state IS NULL AND state_or_country IS NOT NULL;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'politicians' AND column_name = 'party') THEN
        ALTER TABLE politicians ADD COLUMN party VARCHAR(50);
    END IF;
END $$;

-- ============================================================================
-- TRADES TABLE (create if not exists)
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
-- CHART_DATA TABLE
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
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add unique constraint if not exists
DO $$ BEGIN
    ALTER TABLE chart_data ADD CONSTRAINT chart_data_year_month_key UNIQUE (year, month);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================================
-- DASHBOARD_STATS TABLE
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
-- PROFILES TABLE
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
-- USER_ROLES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add unique constraint if not exists
DO $$ BEGIN
    ALTER TABLE user_roles ADD CONSTRAINT user_roles_user_id_role_key UNIQUE (user_id, role);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================================
-- TRADING_SIGNALS TABLE
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
-- NOTIFICATIONS TABLE
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
-- SYNC_LOGS TABLE
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
-- TRADING_ORDERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS trading_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    ticker VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
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
-- INDEXES (create if not exists)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_politicians_name ON politicians(name);
CREATE INDEX IF NOT EXISTS idx_politicians_party ON politicians(party);
CREATE INDEX IF NOT EXISTS idx_politicians_state ON politicians(state);

CREATE INDEX IF NOT EXISTS idx_trades_politician ON trades(politician_id);
CREATE INDEX IF NOT EXISTS idx_trades_ticker ON trades(ticker);
CREATE INDEX IF NOT EXISTS idx_trades_transaction_date ON trades(transaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_trades_created ON trades(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_trading_signals_ticker ON trading_signals(ticker);
CREATE INDEX IF NOT EXISTS idx_trading_signals_active ON trading_signals(is_active);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(is_read);

CREATE INDEX IF NOT EXISTS idx_sync_logs_source ON sync_logs(source);
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

-- ============================================================================
-- RLS POLICIES (drop and recreate to avoid conflicts)
-- ============================================================================

-- Public read access
DROP POLICY IF EXISTS "Public read jurisdictions" ON jurisdictions;
CREATE POLICY "Public read jurisdictions" ON jurisdictions FOR SELECT USING (true);

DROP POLICY IF EXISTS "Public read politicians" ON politicians;
CREATE POLICY "Public read politicians" ON politicians FOR SELECT USING (true);

DROP POLICY IF EXISTS "Public read trades" ON trades;
CREATE POLICY "Public read trades" ON trades FOR SELECT USING (true);

DROP POLICY IF EXISTS "Public read chart_data" ON chart_data;
CREATE POLICY "Public read chart_data" ON chart_data FOR SELECT USING (true);

DROP POLICY IF EXISTS "Public read dashboard_stats" ON dashboard_stats;
CREATE POLICY "Public read dashboard_stats" ON dashboard_stats FOR SELECT USING (true);

DROP POLICY IF EXISTS "Public read trading_signals" ON trading_signals;
CREATE POLICY "Public read trading_signals" ON trading_signals FOR SELECT USING (true);

-- User-specific policies
DROP POLICY IF EXISTS "Users read own profile" ON profiles;
CREATE POLICY "Users read own profile" ON profiles FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users update own profile" ON profiles;
CREATE POLICY "Users update own profile" ON profiles FOR UPDATE USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users insert own profile" ON profiles;
CREATE POLICY "Users insert own profile" ON profiles FOR INSERT WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "Users read own roles" ON user_roles;
CREATE POLICY "Users read own roles" ON user_roles FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users read own notifications" ON notifications;
CREATE POLICY "Users read own notifications" ON notifications FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users update own notifications" ON notifications;
CREATE POLICY "Users update own notifications" ON notifications FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users read own orders" ON trading_orders;
CREATE POLICY "Users read own orders" ON trading_orders FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users insert own orders" ON trading_orders;
CREATE POLICY "Users insert own orders" ON trading_orders FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users update own orders" ON trading_orders;
CREATE POLICY "Users update own orders" ON trading_orders FOR UPDATE USING (auth.uid() = user_id);

-- Admin policies
DROP POLICY IF EXISTS "Admins manage jurisdictions" ON jurisdictions;
CREATE POLICY "Admins manage jurisdictions" ON jurisdictions FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
);

DROP POLICY IF EXISTS "Admins manage politicians" ON politicians;
CREATE POLICY "Admins manage politicians" ON politicians FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
);

DROP POLICY IF EXISTS "Admins manage trades" ON trades;
CREATE POLICY "Admins manage trades" ON trades FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
);

DROP POLICY IF EXISTS "Admins manage chart_data" ON chart_data;
CREATE POLICY "Admins manage chart_data" ON chart_data FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
);

DROP POLICY IF EXISTS "Admins manage dashboard_stats" ON dashboard_stats;
CREATE POLICY "Admins manage dashboard_stats" ON dashboard_stats FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
);

DROP POLICY IF EXISTS "Admins manage trading_signals" ON trading_signals;
CREATE POLICY "Admins manage trading_signals" ON trading_signals FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
);

DROP POLICY IF EXISTS "Admins manage notifications" ON notifications;
CREATE POLICY "Admins manage notifications" ON notifications FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
);

DROP POLICY IF EXISTS "Admins manage user_roles" ON user_roles;
CREATE POLICY "Admins manage user_roles" ON user_roles FOR ALL USING (
    EXISTS (SELECT 1 FROM user_roles ur WHERE ur.user_id = auth.uid() AND ur.role = 'admin')
);

DROP POLICY IF EXISTS "Admins read sync_logs" ON sync_logs;
CREATE POLICY "Admins read sync_logs" ON sync_logs FOR SELECT USING (
    EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin')
);

DROP POLICY IF EXISTS "Service role sync_logs" ON sync_logs;
CREATE POLICY "Service role sync_logs" ON sync_logs FOR ALL USING (auth.role() = 'service_role');

-- ============================================================================
-- SEED DATA - Jurisdictions
-- ============================================================================
INSERT INTO jurisdictions (name, code, region, country) VALUES
    ('US House of Representatives', 'us_house', 'North America', 'United States'),
    ('US Senate', 'us_senate', 'North America', 'United States'),
    ('UK Parliament', 'uk_parliament', 'Europe', 'United Kingdom'),
    ('EU Parliament', 'eu_parliament', 'Europe', 'European Union')
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- SEED DATA - Initial Dashboard Stats (only if empty)
-- ============================================================================
INSERT INTO dashboard_stats (id, total_trades, total_politicians, total_volume, trades_this_month)
SELECT uuid_generate_v4(), 0, 0, 0, 0
WHERE NOT EXISTS (SELECT 1 FROM dashboard_stats LIMIT 1);

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
    RAISE NOTICE 'Frontend schema migration completed successfully!';
END $$;
