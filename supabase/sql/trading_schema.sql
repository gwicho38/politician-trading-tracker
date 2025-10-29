-- Trading signals, orders, portfolios, and positions tables
-- This extends the politician trading tracker with automated trading capabilities

-- =============================================================================
-- Trading Signals Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS trading_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker TEXT NOT NULL,
    asset_name TEXT NOT NULL,

    -- Signal details
    signal_type TEXT NOT NULL CHECK (signal_type IN ('buy', 'sell', 'hold', 'strong_buy', 'strong_sell')),
    signal_strength TEXT NOT NULL CHECK (signal_strength IN ('very_weak', 'weak', 'moderate', 'strong', 'very_strong')),
    confidence_score DECIMAL(5,4) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),

    -- Price targets
    target_price DECIMAL(12,2),
    stop_loss DECIMAL(12,2),
    take_profit DECIMAL(12,2),

    -- Signal generation info
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMP WITH TIME ZONE,
    model_version TEXT NOT NULL,

    -- Supporting data
    politician_activity_count INTEGER DEFAULT 0,
    total_transaction_volume DECIMAL(15,2),
    buy_sell_ratio DECIMAL(8,4),
    avg_politician_return DECIMAL(8,4),

    -- Feature data (JSON)
    features JSONB,

    -- Related disclosures
    disclosure_ids TEXT[],

    -- Status
    is_active BOOLEAN DEFAULT true,
    notes TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for trading_signals
CREATE INDEX IF NOT EXISTS idx_trading_signals_ticker ON trading_signals(ticker);
CREATE INDEX IF NOT EXISTS idx_trading_signals_signal_type ON trading_signals(signal_type);
CREATE INDEX IF NOT EXISTS idx_trading_signals_confidence ON trading_signals(confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_trading_signals_generated_at ON trading_signals(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_trading_signals_is_active ON trading_signals(is_active);
CREATE INDEX IF NOT EXISTS idx_trading_signals_valid_until ON trading_signals(valid_until);

-- =============================================================================
-- Trading Orders Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS trading_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID REFERENCES trading_signals(id),

    -- Order details
    ticker TEXT NOT NULL,
    order_type TEXT NOT NULL CHECK (order_type IN ('market', 'limit', 'stop', 'stop_limit', 'trailing_stop')),
    side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    limit_price DECIMAL(12,2),
    stop_price DECIMAL(12,2),
    trailing_percent DECIMAL(5,2),

    -- Execution details
    status TEXT NOT NULL CHECK (status IN ('pending', 'submitted', 'filled', 'partially_filled', 'canceled', 'rejected', 'expired')),
    filled_quantity INTEGER DEFAULT 0,
    filled_avg_price DECIMAL(12,4),
    commission DECIMAL(10,4),

    -- Trading mode
    trading_mode TEXT NOT NULL CHECK (trading_mode IN ('paper', 'live')),

    -- Alpaca order info
    alpaca_order_id TEXT,
    alpaca_client_order_id TEXT,

    -- Timestamps
    submitted_at TIMESTAMP WITH TIME ZONE,
    filled_at TIMESTAMP WITH TIME ZONE,
    canceled_at TIMESTAMP WITH TIME ZONE,
    expired_at TIMESTAMP WITH TIME ZONE,

    -- Error information
    error_message TEXT,
    reject_reason TEXT,

    -- Additional metadata
    metadata JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for trading_orders
CREATE INDEX IF NOT EXISTS idx_trading_orders_ticker ON trading_orders(ticker);
CREATE INDEX IF NOT EXISTS idx_trading_orders_signal_id ON trading_orders(signal_id);
CREATE INDEX IF NOT EXISTS idx_trading_orders_status ON trading_orders(status);
CREATE INDEX IF NOT EXISTS idx_trading_orders_trading_mode ON trading_orders(trading_mode);
CREATE INDEX IF NOT EXISTS idx_trading_orders_alpaca_order_id ON trading_orders(alpaca_order_id);
CREATE INDEX IF NOT EXISTS idx_trading_orders_created_at ON trading_orders(created_at DESC);

-- =============================================================================
-- Portfolios Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS portfolios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    trading_mode TEXT NOT NULL CHECK (trading_mode IN ('paper', 'live')),

    -- Portfolio metrics
    cash DECIMAL(15,2) DEFAULT 0,
    portfolio_value DECIMAL(15,2) DEFAULT 0,
    buying_power DECIMAL(15,2) DEFAULT 0,

    -- Performance metrics
    total_return DECIMAL(15,2),
    total_return_pct DECIMAL(8,4),
    day_return DECIMAL(15,2),
    day_return_pct DECIMAL(8,4),

    -- Risk metrics
    max_drawdown DECIMAL(8,4),
    sharpe_ratio DECIMAL(8,4),
    win_rate DECIMAL(5,2),

    -- Position counts
    long_positions INTEGER DEFAULT 0,
    short_positions INTEGER DEFAULT 0,

    -- Alpaca account info
    alpaca_account_id TEXT,
    alpaca_account_status TEXT,

    -- Configuration
    max_position_size DECIMAL(15,2),
    max_portfolio_risk DECIMAL(5,2),
    is_active BOOLEAN DEFAULT true,

    -- Metadata
    metadata JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for portfolios
CREATE INDEX IF NOT EXISTS idx_portfolios_trading_mode ON portfolios(trading_mode);
CREATE INDEX IF NOT EXISTS idx_portfolios_is_active ON portfolios(is_active);
CREATE INDEX IF NOT EXISTS idx_portfolios_alpaca_account_id ON portfolios(alpaca_account_id);

-- =============================================================================
-- Positions Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID REFERENCES portfolios(id),

    -- Position details
    ticker TEXT NOT NULL,
    asset_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('long', 'short')),

    -- Cost basis
    avg_entry_price DECIMAL(12,4) DEFAULT 0,
    total_cost DECIMAL(15,2) DEFAULT 0,

    -- Current value
    current_price DECIMAL(12,4) DEFAULT 0,
    market_value DECIMAL(15,2) DEFAULT 0,
    unrealized_pl DECIMAL(15,2) DEFAULT 0,
    unrealized_pl_pct DECIMAL(8,4) DEFAULT 0,

    -- Realized P&L (for closed positions)
    realized_pl DECIMAL(15,2),
    realized_pl_pct DECIMAL(8,4),

    -- Entry/exit info
    opened_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE,

    -- Related signals and orders
    signal_ids TEXT[],
    order_ids TEXT[],

    -- Risk management
    stop_loss DECIMAL(12,2),
    take_profit DECIMAL(12,2),

    -- Status
    is_open BOOLEAN DEFAULT true,

    -- Metadata
    metadata JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for positions
CREATE INDEX IF NOT EXISTS idx_positions_portfolio_id ON positions(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_positions_ticker ON positions(ticker);
CREATE INDEX IF NOT EXISTS idx_positions_is_open ON positions(is_open);
CREATE INDEX IF NOT EXISTS idx_positions_opened_at ON positions(opened_at DESC);
CREATE INDEX IF NOT EXISTS idx_positions_closed_at ON positions(closed_at DESC);

-- =============================================================================
-- Triggers for updated_at
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_trading_signals_updated_at
    BEFORE UPDATE ON trading_signals
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trading_orders_updated_at
    BEFORE UPDATE ON trading_orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_portfolios_updated_at
    BEFORE UPDATE ON portfolios
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_positions_updated_at
    BEFORE UPDATE ON positions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Views
-- =============================================================================

-- Active signals view
CREATE OR REPLACE VIEW active_signals AS
SELECT
    ts.*,
    COUNT(DISTINCT td.id) as related_disclosures_count
FROM trading_signals ts
LEFT JOIN LATERAL unnest(ts.disclosure_ids) AS disclosure_id ON true
LEFT JOIN trading_disclosures td ON td.id::text = disclosure_id
WHERE ts.is_active = true
AND (ts.valid_until IS NULL OR ts.valid_until > NOW())
GROUP BY ts.id;

-- Open positions with P&L
CREATE OR REPLACE VIEW open_positions_summary AS
SELECT
    p.portfolio_id,
    p.ticker,
    p.quantity,
    p.side,
    p.avg_entry_price,
    p.current_price,
    p.market_value,
    p.unrealized_pl,
    p.unrealized_pl_pct,
    p.opened_at,
    EXTRACT(EPOCH FROM (NOW() - p.opened_at))/86400 as days_held,
    p.stop_loss,
    p.take_profit
FROM positions p
WHERE p.is_open = true
ORDER BY p.unrealized_pl DESC;

-- Portfolio performance view
CREATE OR REPLACE VIEW portfolio_performance AS
SELECT
    p.id as portfolio_id,
    p.name,
    p.trading_mode,
    p.portfolio_value,
    p.cash,
    p.total_return,
    p.total_return_pct,
    p.win_rate,
    COUNT(DISTINCT pos.id) FILTER (WHERE pos.is_open = true) as open_positions_count,
    SUM(pos.market_value) FILTER (WHERE pos.is_open = true) as total_exposure,
    SUM(pos.unrealized_pl) FILTER (WHERE pos.is_open = true) as total_unrealized_pl
FROM portfolios p
LEFT JOIN positions pos ON pos.portfolio_id = p.id
WHERE p.is_active = true
GROUP BY p.id;

-- Trading activity summary
CREATE OR REPLACE VIEW trading_activity_summary AS
SELECT
    DATE(to.created_at) as trade_date,
    to.trading_mode,
    COUNT(*) as total_orders,
    COUNT(*) FILTER (WHERE to.status = 'filled') as filled_orders,
    COUNT(*) FILTER (WHERE to.side = 'buy') as buy_orders,
    COUNT(*) FILTER (WHERE to.side = 'sell') as sell_orders,
    SUM(to.filled_quantity * to.filled_avg_price) FILTER (WHERE to.status = 'filled') as total_volume
FROM trading_orders to
GROUP BY DATE(to.created_at), to.trading_mode
ORDER BY trade_date DESC;

-- Signal performance tracking
CREATE OR REPLACE VIEW signal_performance AS
SELECT
    ts.ticker,
    ts.signal_type,
    ts.confidence_score,
    ts.generated_at,
    COUNT(DISTINCT to.id) as orders_placed,
    AVG(CASE
        WHEN to.status = 'filled' AND pos.unrealized_pl IS NOT NULL
        THEN pos.unrealized_pl
    END) as avg_pl,
    SUM(CASE
        WHEN to.status = 'filled' AND pos.unrealized_pl > 0
        THEN 1
        ELSE 0
    END)::DECIMAL / NULLIF(COUNT(DISTINCT to.id) FILTER (WHERE to.status = 'filled'), 0) as win_rate
FROM trading_signals ts
LEFT JOIN trading_orders to ON to.signal_id = ts.id
LEFT JOIN LATERAL (
    SELECT pos.*
    FROM positions pos
    WHERE pos.ticker = ts.ticker
    AND to.alpaca_order_id = ANY(pos.order_ids)
    LIMIT 1
) pos ON true
GROUP BY ts.id
ORDER BY ts.generated_at DESC;

-- =============================================================================
-- Row Level Security (RLS) Policies
-- =============================================================================

-- Enable RLS on all trading tables
ALTER TABLE trading_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE trading_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;
ALTER TABLE positions ENABLE ROW LEVEL SECURITY;

-- For now, allow all authenticated users to read/write
-- In production, you'd want more restrictive policies
CREATE POLICY "Allow all operations for authenticated users" ON trading_signals
    FOR ALL USING (true);

CREATE POLICY "Allow all operations for authenticated users" ON trading_orders
    FOR ALL USING (true);

CREATE POLICY "Allow all operations for authenticated users" ON portfolios
    FOR ALL USING (true);

CREATE POLICY "Allow all operations for authenticated users" ON positions
    FOR ALL USING (true);
