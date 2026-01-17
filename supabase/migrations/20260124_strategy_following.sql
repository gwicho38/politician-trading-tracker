-- Strategy Following: Allow users to follow and mirror trading strategies
-- Users can follow the Reference Strategy, a public preset, or custom weights

-- User Strategy Subscriptions table
CREATE TABLE IF NOT EXISTS public.user_strategy_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_email TEXT NOT NULL,

  -- What they're following (one of these will be set)
  strategy_type TEXT NOT NULL CHECK (strategy_type IN ('reference', 'preset', 'custom')),
  preset_id UUID REFERENCES signal_weight_presets(id) ON DELETE CASCADE,
  custom_weights JSONB, -- For "Apply These Weights" from playground

  -- Trading settings
  trading_mode TEXT NOT NULL CHECK (trading_mode IN ('paper', 'live')) DEFAULT 'paper',
  is_active BOOLEAN DEFAULT TRUE,
  sync_existing_positions BOOLEAN DEFAULT FALSE, -- Initial sync toggle

  -- Tracking
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  last_synced_at TIMESTAMPTZ,

  -- One subscription per user
  UNIQUE(user_email)
);

-- User Strategy Trades table (trade log)
CREATE TABLE IF NOT EXISTS public.user_strategy_trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subscription_id UUID NOT NULL REFERENCES user_strategy_subscriptions(id) ON DELETE CASCADE,
  user_email TEXT NOT NULL,

  -- Trade details
  ticker TEXT NOT NULL,
  side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
  quantity INTEGER NOT NULL,
  signal_type TEXT, -- strong_buy, buy, sell, strong_sell
  confidence_score NUMERIC(4,3),

  -- Source signal info
  source_signal_id UUID, -- From trading_signals if reference
  source_preset_id UUID, -- From signal_weight_presets if preset

  -- Execution
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'submitted', 'filled', 'failed', 'skipped')),
  alpaca_order_id TEXT,
  error_message TEXT,

  created_at TIMESTAMPTZ DEFAULT NOW(),
  executed_at TIMESTAMPTZ
);

-- Indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_user_strategy_subscriptions_email ON user_strategy_subscriptions(user_email);
CREATE INDEX IF NOT EXISTS idx_user_strategy_subscriptions_active ON user_strategy_subscriptions(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_user_strategy_trades_subscription ON user_strategy_trades(subscription_id);
CREATE INDEX IF NOT EXISTS idx_user_strategy_trades_status ON user_strategy_trades(status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_user_strategy_trades_email ON user_strategy_trades(user_email);

-- Updated at trigger for subscriptions
DROP TRIGGER IF EXISTS update_user_strategy_subscriptions_updated_at ON user_strategy_subscriptions;
CREATE TRIGGER update_user_strategy_subscriptions_updated_at
    BEFORE UPDATE ON user_strategy_subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS (Row Level Security) policies for subscriptions
ALTER TABLE user_strategy_subscriptions ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (for idempotent migration)
DROP POLICY IF EXISTS "Users can view their own subscription" ON user_strategy_subscriptions;
DROP POLICY IF EXISTS "Users can insert their own subscription" ON user_strategy_subscriptions;
DROP POLICY IF EXISTS "Users can update their own subscription" ON user_strategy_subscriptions;
DROP POLICY IF EXISTS "Users can delete their own subscription" ON user_strategy_subscriptions;

-- Users can only see and modify their own subscriptions
CREATE POLICY "Users can view their own subscription" ON user_strategy_subscriptions
    FOR SELECT USING (user_email = current_setting('request.jwt.claims', true)::json->>'email');

CREATE POLICY "Users can insert their own subscription" ON user_strategy_subscriptions
    FOR INSERT WITH CHECK (user_email = current_setting('request.jwt.claims', true)::json->>'email');

CREATE POLICY "Users can update their own subscription" ON user_strategy_subscriptions
    FOR UPDATE USING (user_email = current_setting('request.jwt.claims', true)::json->>'email');

CREATE POLICY "Users can delete their own subscription" ON user_strategy_subscriptions
    FOR DELETE USING (user_email = current_setting('request.jwt.claims', true)::json->>'email');

-- RLS policies for trades
ALTER TABLE user_strategy_trades ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their own strategy trades" ON user_strategy_trades;
DROP POLICY IF EXISTS "Users can insert their own strategy trades" ON user_strategy_trades;

CREATE POLICY "Users can view their own strategy trades" ON user_strategy_trades
    FOR SELECT USING (user_email = current_setting('request.jwt.claims', true)::json->>'email');

-- Only the system (service role) should insert trades, but we allow users to see their own
CREATE POLICY "Users can insert their own strategy trades" ON user_strategy_trades
    FOR INSERT WITH CHECK (user_email = current_setting('request.jwt.claims', true)::json->>'email');

-- Function to get user's current subscription with strategy name
CREATE OR REPLACE FUNCTION get_user_subscription(user_email_param TEXT)
RETURNS TABLE (
  id UUID,
  user_email TEXT,
  strategy_type TEXT,
  preset_id UUID,
  preset_name TEXT,
  custom_weights JSONB,
  trading_mode TEXT,
  is_active BOOLEAN,
  sync_existing_positions BOOLEAN,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ,
  last_synced_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT
    s.id,
    s.user_email,
    s.strategy_type,
    s.preset_id,
    p.name as preset_name,
    s.custom_weights,
    s.trading_mode,
    s.is_active,
    s.sync_existing_positions,
    s.created_at,
    s.updated_at,
    s.last_synced_at
  FROM user_strategy_subscriptions s
  LEFT JOIN signal_weight_presets p ON p.id = s.preset_id
  WHERE s.user_email = user_email_param;
END;
$$;

GRANT EXECUTE ON FUNCTION get_user_subscription TO authenticated;

-- Function to get recent strategy trades for a user
CREATE OR REPLACE FUNCTION get_recent_strategy_trades(
  user_email_param TEXT,
  limit_param INTEGER DEFAULT 20
)
RETURNS TABLE (
  id UUID,
  ticker TEXT,
  side TEXT,
  quantity INTEGER,
  signal_type TEXT,
  confidence_score NUMERIC(4,3),
  status TEXT,
  alpaca_order_id TEXT,
  error_message TEXT,
  created_at TIMESTAMPTZ,
  executed_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT
    t.id,
    t.ticker,
    t.side,
    t.quantity,
    t.signal_type,
    t.confidence_score,
    t.status,
    t.alpaca_order_id,
    t.error_message,
    t.created_at,
    t.executed_at
  FROM user_strategy_trades t
  WHERE t.user_email = user_email_param
  ORDER BY t.created_at DESC
  LIMIT limit_param;
END;
$$;

GRANT EXECUTE ON FUNCTION get_recent_strategy_trades TO authenticated;

-- Comments
COMMENT ON TABLE user_strategy_subscriptions IS 'User subscriptions to follow trading strategies';
COMMENT ON COLUMN user_strategy_subscriptions.strategy_type IS 'reference = follow reference portfolio, preset = follow a public strategy, custom = follow custom weights';
COMMENT ON COLUMN user_strategy_subscriptions.custom_weights IS 'JSON object with signal weights when strategy_type is custom';
COMMENT ON COLUMN user_strategy_subscriptions.sync_existing_positions IS 'Whether to sync existing positions when subscribing';

COMMENT ON TABLE user_strategy_trades IS 'Log of trades executed by strategy following system';
COMMENT ON COLUMN user_strategy_trades.status IS 'pending = awaiting execution, submitted = sent to Alpaca, filled = completed, failed = error occurred, skipped = intentionally not executed';
