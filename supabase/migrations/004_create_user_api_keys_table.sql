-- User API Keys Table
-- Stores encrypted API keys for each user to access their own Alpaca accounts

CREATE TABLE IF NOT EXISTS user_api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_email VARCHAR(255) NOT NULL UNIQUE,
    user_name VARCHAR(255),

    -- Paper trading credentials
    paper_api_key TEXT,
    paper_secret_key TEXT,
    paper_validated_at TIMESTAMPTZ,

    -- Live trading credentials (requires subscription)
    live_api_key TEXT,
    live_secret_key TEXT,
    live_validated_at TIMESTAMPTZ,

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
COMMENT ON TABLE user_api_keys IS 'Stores user-specific Alpaca API credentials and subscription info';
COMMENT ON COLUMN user_api_keys.paper_api_key IS 'Encrypted paper trading API key';
COMMENT ON COLUMN user_api_keys.paper_secret_key IS 'Encrypted paper trading secret key';
COMMENT ON COLUMN user_api_keys.live_api_key IS 'Encrypted live trading API key (requires paid subscription)';
COMMENT ON COLUMN user_api_keys.live_secret_key IS 'Encrypted live trading secret key (requires paid subscription)';
COMMENT ON COLUMN user_api_keys.subscription_tier IS 'free, basic, or pro';
COMMENT ON COLUMN user_api_keys.subscription_status IS 'active, canceled, or past_due';
