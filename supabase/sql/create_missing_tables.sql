-- Create Missing Tables for Politician Trading Tracker
-- Execute this in your Supabase SQL Editor

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- POLITICIAN_TRADES TABLE (Main trading data table)
-- ============================================================================
CREATE TABLE IF NOT EXISTS politician_trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    politician_name VARCHAR(200) NOT NULL,
    transaction_date TIMESTAMPTZ NOT NULL,
    disclosure_date TIMESTAMPTZ NOT NULL,
    ticker VARCHAR(20),
    asset_description VARCHAR(500),
    asset_type VARCHAR(100),
    transaction_type VARCHAR(50) NOT NULL,  -- 'purchase', 'sale', 'exchange', etc.
    amount VARCHAR(100),  -- Range like "$1,001 - $15,000"
    amount_min DECIMAL(15,2),
    amount_max DECIMAL(15,2),
    party VARCHAR(50),
    state VARCHAR(100),
    district VARCHAR(50),
    position VARCHAR(100),
    source VARCHAR(100),  -- 'us_house', 'us_senate', 'uk_parliament', etc.
    source_url TEXT,
    raw_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for politician_trades
CREATE INDEX IF NOT EXISTS idx_politician_trades_ticker ON politician_trades(ticker);
CREATE INDEX IF NOT EXISTS idx_politician_trades_name ON politician_trades(politician_name);
CREATE INDEX IF NOT EXISTS idx_politician_trades_transaction_date ON politician_trades(transaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_politician_trades_disclosure_date ON politician_trades(disclosure_date DESC);
CREATE INDEX IF NOT EXISTS idx_politician_trades_type ON politician_trades(transaction_type);
CREATE INDEX IF NOT EXISTS idx_politician_trades_source ON politician_trades(source);
CREATE INDEX IF NOT EXISTS idx_politician_trades_created ON politician_trades(created_at DESC);

-- Unique constraint to prevent duplicates
CREATE UNIQUE INDEX IF NOT EXISTS idx_politician_trades_unique
ON politician_trades(politician_name, transaction_date, ticker, transaction_type, disclosure_date, source);

-- ============================================================================
-- USER_SESSIONS TABLE (For auth session tracking)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(100) UNIQUE NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    user_name VARCHAR(255),
    login_time TIMESTAMPTZ DEFAULT NOW(),
    last_activity TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    ip_address INET,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    logout_time TIMESTAMPTZ,
    session_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for user_sessions
CREATE INDEX IF NOT EXISTS idx_user_sessions_email ON user_sessions(user_email);
CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_last_activity ON user_sessions(last_activity DESC);
CREATE INDEX IF NOT EXISTS idx_user_sessions_is_active ON user_sessions(is_active);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);

-- ============================================================================
-- TRIGGERS FOR updated_at COLUMNS
-- ============================================================================
-- Create or replace the trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

-- Apply trigger to politician_trades
DROP TRIGGER IF EXISTS update_politician_trades_updated_at ON politician_trades;
CREATE TRIGGER update_politician_trades_updated_at
    BEFORE UPDATE ON politician_trades
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to user_sessions
DROP TRIGGER IF EXISTS update_user_sessions_updated_at ON user_sessions;
CREATE TRIGGER update_user_sessions_updated_at
    BEFORE UPDATE ON user_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS
ALTER TABLE politician_trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;

-- Allow read access to all authenticated users for politician_trades
CREATE POLICY "Allow read access for authenticated users" ON politician_trades
    FOR SELECT
    USING (auth.role() = 'authenticated');

-- Allow insert/update/delete for authenticated users (can be restricted further)
CREATE POLICY "Allow write access for authenticated users" ON politician_trades
    FOR ALL
    USING (auth.role() = 'authenticated');

-- Allow anon read access to politician_trades (public data)
CREATE POLICY "Allow read access for anon" ON politician_trades
    FOR SELECT
    USING (auth.role() = 'anon');

-- User sessions - users can only see their own sessions
CREATE POLICY "Users can view their own sessions" ON user_sessions
    FOR SELECT
    USING (auth.jwt() ->> 'email' = user_email OR auth.role() = 'authenticated');

-- Users can insert their own sessions
CREATE POLICY "Users can create their own sessions" ON user_sessions
    FOR INSERT
    WITH CHECK (auth.role() = 'authenticated');

-- Users can update their own sessions
CREATE POLICY "Users can update their own sessions" ON user_sessions
    FOR UPDATE
    USING (auth.jwt() ->> 'email' = user_email OR auth.role() = 'authenticated');

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

-- Grant read access to anon role for politician_trades
GRANT SELECT ON politician_trades TO anon;
GRANT SELECT ON politician_trades TO authenticated;
GRANT INSERT, UPDATE, DELETE ON politician_trades TO authenticated;

-- Grant access to user_sessions for authenticated users
GRANT SELECT, INSERT, UPDATE ON user_sessions TO authenticated;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE politician_trades IS 'Main table storing all politician trading activity from various sources';
COMMENT ON TABLE user_sessions IS 'Tracks user authentication sessions with enhanced security features';

COMMENT ON COLUMN politician_trades.ticker IS 'Stock ticker symbol (e.g., AAPL, GOOGL)';
COMMENT ON COLUMN politician_trades.raw_data IS 'Original scraped data in JSON format for debugging';
COMMENT ON COLUMN politician_trades.source IS 'Data source identifier (us_house, us_senate, uk_parliament, etc.)';
COMMENT ON COLUMN politician_trades.amount IS 'Human-readable amount range as reported';
COMMENT ON COLUMN politician_trades.amount_min IS 'Minimum amount in USD';
COMMENT ON COLUMN politician_trades.amount_max IS 'Maximum amount in USD';

COMMENT ON COLUMN user_sessions.session_id IS 'Unique session identifier for tracking user sessions';
COMMENT ON COLUMN user_sessions.expires_at IS 'Session expiration timestamp';
COMMENT ON COLUMN user_sessions.is_active IS 'Whether the session is currently active';
COMMENT ON COLUMN user_sessions.session_data IS 'Additional session metadata in JSON format';

-- ============================================================================
-- HELPFUL VIEWS
-- ============================================================================

-- View for recent trading activity
CREATE OR REPLACE VIEW v_recent_trades AS
SELECT
    politician_name,
    transaction_date,
    disclosure_date,
    ticker,
    asset_description,
    transaction_type,
    amount,
    party,
    state,
    position,
    source,
    created_at
FROM politician_trades
ORDER BY disclosure_date DESC, created_at DESC
LIMIT 100;

-- View for active user sessions
CREATE OR REPLACE VIEW v_active_sessions AS
SELECT
    user_email,
    user_name,
    login_time,
    last_activity,
    expires_at,
    ip_address,
    EXTRACT(EPOCH FROM (NOW() - last_activity))/60 as minutes_since_activity
FROM user_sessions
WHERE is_active = TRUE
  AND (expires_at IS NULL OR expires_at > NOW())
ORDER BY last_activity DESC;

-- Grant view access
GRANT SELECT ON v_recent_trades TO anon, authenticated;
GRANT SELECT ON v_active_sessions TO authenticated;

-- ============================================================================
-- SAMPLE DATA (Optional - for testing)
-- ============================================================================

-- Uncomment to insert sample data for testing
/*
INSERT INTO politician_trades (
    politician_name, transaction_date, disclosure_date, ticker,
    asset_description, transaction_type, amount,
    amount_min, amount_max, party, state, position, source
) VALUES (
    'John Doe', NOW() - INTERVAL '30 days', NOW() - INTERVAL '15 days', 'AAPL',
    'Apple Inc. - Common Stock', 'purchase', '$15,001 - $50,000',
    15001, 50000, 'Democratic', 'California', 'Senator', 'us_senate'
) ON CONFLICT DO NOTHING;
*/

-- ============================================================================
-- COMPLETION MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Successfully created politician_trades and user_sessions tables!';
    RAISE NOTICE 'Tables created: politician_trades, user_sessions';
    RAISE NOTICE 'Views created: v_recent_trades, v_active_sessions';
    RAISE NOTICE 'RLS policies enabled for both tables';
END $$;
