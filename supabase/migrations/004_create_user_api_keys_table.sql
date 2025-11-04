-- User API Keys Table
-- Stores encrypted API keys for each user to access their own services
-- Multi-tenancy: Each user has isolated data and credentials

CREATE TABLE IF NOT EXISTS user_api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_email VARCHAR(255) NOT NULL UNIQUE,
    user_name VARCHAR(255),

    -- Alpaca Trading API (Paper trading credentials)
    paper_api_key TEXT,
    paper_secret_key TEXT,
    paper_validated_at TIMESTAMPTZ,

    -- Alpaca Trading API (Live trading credentials - requires subscription)
    live_api_key TEXT,
    live_secret_key TEXT,
    live_validated_at TIMESTAMPTZ,

    -- Supabase Database (User's own Supabase instance)
    supabase_url TEXT,
    supabase_anon_key TEXT,
    supabase_service_role_key TEXT,
    supabase_validated_at TIMESTAMPTZ,

    -- QuiverQuant API (Enhanced Congress trading data)
    quiverquant_api_key TEXT,
    quiverquant_validated_at TIMESTAMPTZ,

    -- Future: Other data sources
    -- polygon_api_key TEXT,
    -- alpha_vantage_api_key TEXT,
    -- finnhub_api_key TEXT,

    -- Subscription info
    subscription_tier VARCHAR(20) DEFAULT 'free',
    subscription_status VARCHAR(20) DEFAULT 'active',
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_api_keys_email ON user_api_keys(user_email);
CREATE INDEX IF NOT EXISTS idx_user_api_keys_subscription ON user_api_keys(subscription_tier, subscription_status);

-- Updated at trigger
DROP TRIGGER IF EXISTS update_user_api_keys_updated_at ON user_api_keys;
CREATE TRIGGER update_user_api_keys_updated_at
    BEFORE UPDATE ON user_api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS (Row Level Security) policies
ALTER TABLE user_api_keys ENABLE ROW LEVEL SECURITY;

-- Users can only see and modify their own API keys
CREATE POLICY "Users can view their own API keys" ON user_api_keys
    FOR SELECT USING (user_email = current_setting('request.jwt.claims', true)::json->>'email');

CREATE POLICY "Users can insert their own API keys" ON user_api_keys
    FOR INSERT WITH CHECK (user_email = current_setting('request.jwt.claims', true)::json->>'email');

CREATE POLICY "Users can update their own API keys" ON user_api_keys
    FOR UPDATE USING (user_email = current_setting('request.jwt.claims', true)::json->>'email');

-- Comments
COMMENT ON TABLE user_api_keys IS 'Stores user-specific API credentials for all services (multi-tenancy model)';
COMMENT ON COLUMN user_api_keys.paper_api_key IS 'Encrypted Alpaca paper trading API key';
COMMENT ON COLUMN user_api_keys.paper_secret_key IS 'Encrypted Alpaca paper trading secret key';
COMMENT ON COLUMN user_api_keys.live_api_key IS 'Encrypted Alpaca live trading API key (requires paid subscription)';
COMMENT ON COLUMN user_api_keys.live_secret_key IS 'Encrypted Alpaca live trading secret key (requires paid subscription)';
COMMENT ON COLUMN user_api_keys.supabase_url IS 'Encrypted user Supabase instance URL';
COMMENT ON COLUMN user_api_keys.supabase_anon_key IS 'Encrypted user Supabase anonymous key';
COMMENT ON COLUMN user_api_keys.supabase_service_role_key IS 'Encrypted user Supabase service role key (admin access)';
COMMENT ON COLUMN user_api_keys.quiverquant_api_key IS 'Encrypted QuiverQuant API key for enhanced Congress data';
COMMENT ON COLUMN user_api_keys.subscription_tier IS 'free, basic, or pro';
COMMENT ON COLUMN user_api_keys.subscription_status IS 'active, canceled, or past_due';
