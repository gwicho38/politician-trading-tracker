-- Reference Portfolio Feature Migration
-- Creates tables for application-level automated trading portfolio
-- This portfolio automatically executes trades based on high-confidence signals

-- ============================================================================
-- 1. Reference Portfolio Configuration (Singleton)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.reference_portfolio_config (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Basic Info
  name TEXT NOT NULL DEFAULT 'Reference Strategy',
  description TEXT DEFAULT 'Automated paper trading based on politician activity signals',

  -- Capital & Trading Parameters
  initial_capital DECIMAL(15,2) NOT NULL DEFAULT 100000.00,
  min_confidence_threshold DECIMAL(5,4) NOT NULL DEFAULT 0.70,
  max_position_size_pct DECIMAL(5,2) NOT NULL DEFAULT 5.00,
  max_portfolio_positions INTEGER NOT NULL DEFAULT 20,

  -- Risk Management
  max_single_trade_pct DECIMAL(5,2) NOT NULL DEFAULT 2.00,
  max_daily_trades INTEGER NOT NULL DEFAULT 10,
  default_stop_loss_pct DECIMAL(5,2) DEFAULT 5.00,
  default_take_profit_pct DECIMAL(5,2) DEFAULT 15.00,

  -- Position Sizing (Confidence-Weighted)
  base_position_size_pct DECIMAL(5,2) NOT NULL DEFAULT 1.00,
  confidence_multiplier DECIMAL(5,2) NOT NULL DEFAULT 3.00,

  -- Status
  is_active BOOLEAN DEFAULT true,
  trading_mode TEXT NOT NULL DEFAULT 'paper' CHECK (trading_mode = 'paper'),

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Ensure only one config row exists (singleton pattern)
CREATE UNIQUE INDEX IF NOT EXISTS idx_reference_portfolio_config_singleton
  ON public.reference_portfolio_config((true));

-- ============================================================================
-- 2. Reference Portfolio State (Real-time Metrics)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.reference_portfolio_state (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  config_id UUID REFERENCES public.reference_portfolio_config(id) ON DELETE CASCADE,

  -- Current Portfolio Values
  cash DECIMAL(15,2) NOT NULL DEFAULT 100000.00,
  portfolio_value DECIMAL(15,2) NOT NULL DEFAULT 100000.00,
  positions_value DECIMAL(15,2) DEFAULT 0,
  buying_power DECIMAL(15,2) NOT NULL DEFAULT 100000.00,

  -- Performance Metrics
  total_return DECIMAL(15,2) DEFAULT 0,
  total_return_pct DECIMAL(8,4) DEFAULT 0,
  day_return DECIMAL(15,2) DEFAULT 0,
  day_return_pct DECIMAL(8,4) DEFAULT 0,

  -- Risk Metrics
  max_drawdown DECIMAL(8,4) DEFAULT 0,
  current_drawdown DECIMAL(8,4) DEFAULT 0,
  sharpe_ratio DECIMAL(8,4),
  sortino_ratio DECIMAL(8,4),
  volatility DECIMAL(8,4),

  -- Trade Statistics
  total_trades INTEGER DEFAULT 0,
  trades_today INTEGER DEFAULT 0,
  winning_trades INTEGER DEFAULT 0,
  losing_trades INTEGER DEFAULT 0,
  win_rate DECIMAL(5,2) DEFAULT 0,
  avg_win DECIMAL(15,2) DEFAULT 0,
  avg_loss DECIMAL(15,2) DEFAULT 0,
  profit_factor DECIMAL(8,4),

  -- Position Info
  open_positions INTEGER DEFAULT 0,
  peak_portfolio_value DECIMAL(15,2) DEFAULT 100000.00,

  -- Benchmark Tracking
  benchmark_value DECIMAL(15,2),
  benchmark_return_pct DECIMAL(8,4),
  alpha DECIMAL(8,4),

  -- Status Timestamps
  last_trade_at TIMESTAMPTZ,
  last_sync_at TIMESTAMPTZ,

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Ensure only one state row exists
CREATE UNIQUE INDEX IF NOT EXISTS idx_reference_portfolio_state_singleton
  ON public.reference_portfolio_state((true));

-- ============================================================================
-- 3. Reference Portfolio Positions
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.reference_portfolio_positions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Position Details
  ticker TEXT NOT NULL,
  asset_name TEXT,
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  side TEXT NOT NULL CHECK (side IN ('long', 'short')) DEFAULT 'long',

  -- Entry Information
  entry_price DECIMAL(12,4) NOT NULL,
  entry_date TIMESTAMPTZ NOT NULL DEFAULT now(),
  entry_signal_id UUID REFERENCES public.trading_signals(id),
  entry_confidence DECIMAL(5,4),
  entry_order_id TEXT,

  -- Current Values (updated on sync)
  current_price DECIMAL(12,4),
  market_value DECIMAL(15,2),
  unrealized_pl DECIMAL(15,2) DEFAULT 0,
  unrealized_pl_pct DECIMAL(8,4) DEFAULT 0,

  -- Exit Information (for closed positions)
  exit_price DECIMAL(12,4),
  exit_date TIMESTAMPTZ,
  exit_signal_id UUID REFERENCES public.trading_signals(id),
  exit_order_id TEXT,
  exit_reason TEXT CHECK (exit_reason IN ('signal', 'stop_loss', 'take_profit', 'manual', 'rebalance')),
  realized_pl DECIMAL(15,2),
  realized_pl_pct DECIMAL(8,4),

  -- Risk Management
  stop_loss_price DECIMAL(12,4),
  take_profit_price DECIMAL(12,4),

  -- Position Sizing Info
  position_size_pct DECIMAL(5,2),
  confidence_weight DECIMAL(5,2),

  -- Status
  is_open BOOLEAN DEFAULT true,

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ref_positions_ticker ON public.reference_portfolio_positions(ticker);
CREATE INDEX IF NOT EXISTS idx_ref_positions_is_open ON public.reference_portfolio_positions(is_open);
CREATE INDEX IF NOT EXISTS idx_ref_positions_entry_date ON public.reference_portfolio_positions(entry_date DESC);
CREATE INDEX IF NOT EXISTS idx_ref_positions_signal ON public.reference_portfolio_positions(entry_signal_id);

-- ============================================================================
-- 4. Reference Portfolio Transactions (Trade History)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.reference_portfolio_transactions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  position_id UUID REFERENCES public.reference_portfolio_positions(id),

  -- Transaction Details
  ticker TEXT NOT NULL,
  transaction_type TEXT NOT NULL CHECK (transaction_type IN ('buy', 'sell')),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  price DECIMAL(12,4) NOT NULL,
  total_value DECIMAL(15,2) NOT NULL,

  -- Signal Reference
  signal_id UUID REFERENCES public.trading_signals(id),
  signal_confidence DECIMAL(5,4),
  signal_type TEXT,

  -- Execution Details
  executed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  alpaca_order_id TEXT,
  alpaca_client_order_id TEXT,

  -- Position Sizing Info
  position_size_pct DECIMAL(5,2),
  confidence_weight DECIMAL(5,2),
  portfolio_value_at_trade DECIMAL(15,2),

  -- Status
  status TEXT NOT NULL DEFAULT 'executed' CHECK (status IN ('pending', 'submitted', 'executed', 'failed', 'canceled')),
  error_message TEXT,

  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ref_transactions_ticker ON public.reference_portfolio_transactions(ticker);
CREATE INDEX IF NOT EXISTS idx_ref_transactions_executed_at ON public.reference_portfolio_transactions(executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_ref_transactions_signal ON public.reference_portfolio_transactions(signal_id);
CREATE INDEX IF NOT EXISTS idx_ref_transactions_position ON public.reference_portfolio_transactions(position_id);

-- ============================================================================
-- 5. Reference Portfolio Snapshots (Performance Time-Series)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.reference_portfolio_snapshots (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Snapshot Timing
  snapshot_date DATE NOT NULL,
  snapshot_time TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Portfolio Values
  portfolio_value DECIMAL(15,2) NOT NULL,
  cash DECIMAL(15,2) NOT NULL,
  positions_value DECIMAL(15,2) NOT NULL,

  -- Daily Returns
  day_return DECIMAL(15,2),
  day_return_pct DECIMAL(8,4),

  -- Cumulative Returns
  cumulative_return DECIMAL(15,2),
  cumulative_return_pct DECIMAL(8,4),

  -- Metrics at Snapshot Time
  open_positions INTEGER,
  total_trades INTEGER,
  sharpe_ratio DECIMAL(8,4),
  max_drawdown DECIMAL(8,4),
  current_drawdown DECIMAL(8,4),
  win_rate DECIMAL(5,2),

  -- Benchmark Comparison (S&P 500 / SPY)
  benchmark_value DECIMAL(15,2),
  benchmark_return DECIMAL(15,2),
  benchmark_return_pct DECIMAL(8,4),
  alpha DECIMAL(8,4),

  created_at TIMESTAMPTZ DEFAULT now(),

  UNIQUE(snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_ref_snapshots_date ON public.reference_portfolio_snapshots(snapshot_date DESC);

-- ============================================================================
-- 6. Signal Queue for Reference Portfolio Processing
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.reference_portfolio_signal_queue (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  signal_id UUID NOT NULL REFERENCES public.trading_signals(id),

  -- Processing Status
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'executed', 'skipped', 'failed')),

  -- Processing Details
  skip_reason TEXT,
  error_message TEXT,

  -- Execution Result
  transaction_id UUID REFERENCES public.reference_portfolio_transactions(id),

  created_at TIMESTAMPTZ DEFAULT now(),
  processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ref_signal_queue_status ON public.reference_portfolio_signal_queue(status);
CREATE INDEX IF NOT EXISTS idx_ref_signal_queue_created ON public.reference_portfolio_signal_queue(created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ref_signal_queue_signal ON public.reference_portfolio_signal_queue(signal_id);

-- ============================================================================
-- 7. Row Level Security Policies
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE public.reference_portfolio_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reference_portfolio_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reference_portfolio_positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reference_portfolio_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reference_portfolio_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reference_portfolio_signal_queue ENABLE ROW LEVEL SECURITY;

-- Public READ access for all reference portfolio tables (transparency)
DROP POLICY IF EXISTS "public_read_ref_config" ON public.reference_portfolio_config;
CREATE POLICY "public_read_ref_config" ON public.reference_portfolio_config
  FOR SELECT USING (true);

DROP POLICY IF EXISTS "public_read_ref_state" ON public.reference_portfolio_state;
CREATE POLICY "public_read_ref_state" ON public.reference_portfolio_state
  FOR SELECT USING (true);

DROP POLICY IF EXISTS "public_read_ref_positions" ON public.reference_portfolio_positions;
CREATE POLICY "public_read_ref_positions" ON public.reference_portfolio_positions
  FOR SELECT USING (true);

DROP POLICY IF EXISTS "public_read_ref_transactions" ON public.reference_portfolio_transactions;
CREATE POLICY "public_read_ref_transactions" ON public.reference_portfolio_transactions
  FOR SELECT USING (true);

DROP POLICY IF EXISTS "public_read_ref_snapshots" ON public.reference_portfolio_snapshots;
CREATE POLICY "public_read_ref_snapshots" ON public.reference_portfolio_snapshots
  FOR SELECT USING (true);

-- Signal queue is internal only - service role access
DROP POLICY IF EXISTS "service_read_signal_queue" ON public.reference_portfolio_signal_queue;
CREATE POLICY "service_read_signal_queue" ON public.reference_portfolio_signal_queue
  FOR SELECT USING (auth.role() = 'service_role');

-- Service role WRITE access for all tables (automated trading)
DROP POLICY IF EXISTS "service_write_ref_config" ON public.reference_portfolio_config;
CREATE POLICY "service_write_ref_config" ON public.reference_portfolio_config
  FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "service_write_ref_state" ON public.reference_portfolio_state;
CREATE POLICY "service_write_ref_state" ON public.reference_portfolio_state
  FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "service_write_ref_positions" ON public.reference_portfolio_positions;
CREATE POLICY "service_write_ref_positions" ON public.reference_portfolio_positions
  FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "service_write_ref_transactions" ON public.reference_portfolio_transactions;
CREATE POLICY "service_write_ref_transactions" ON public.reference_portfolio_transactions
  FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "service_write_ref_snapshots" ON public.reference_portfolio_snapshots;
CREATE POLICY "service_write_ref_snapshots" ON public.reference_portfolio_snapshots
  FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "service_write_signal_queue" ON public.reference_portfolio_signal_queue;
CREATE POLICY "service_write_signal_queue" ON public.reference_portfolio_signal_queue
  FOR ALL USING (auth.role() = 'service_role');

-- ============================================================================
-- 8. Updated At Triggers
-- ============================================================================

-- Trigger function for updated_at
CREATE OR REPLACE FUNCTION public.update_reference_portfolio_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers
CREATE TRIGGER update_ref_config_updated_at
  BEFORE UPDATE ON public.reference_portfolio_config
  FOR EACH ROW EXECUTE FUNCTION public.update_reference_portfolio_updated_at();

CREATE TRIGGER update_ref_state_updated_at
  BEFORE UPDATE ON public.reference_portfolio_state
  FOR EACH ROW EXECUTE FUNCTION public.update_reference_portfolio_updated_at();

CREATE TRIGGER update_ref_positions_updated_at
  BEFORE UPDATE ON public.reference_portfolio_positions
  FOR EACH ROW EXECUTE FUNCTION public.update_reference_portfolio_updated_at();

-- ============================================================================
-- 9. Initialize Default Configuration and State
-- ============================================================================

-- Insert default config
INSERT INTO public.reference_portfolio_config (
  name,
  description,
  initial_capital,
  min_confidence_threshold,
  max_position_size_pct,
  max_portfolio_positions,
  max_single_trade_pct,
  max_daily_trades,
  default_stop_loss_pct,
  default_take_profit_pct,
  base_position_size_pct,
  confidence_multiplier,
  is_active,
  trading_mode
) VALUES (
  'Reference Strategy',
  'Automated paper trading portfolio demonstrating signal performance. Trades are executed automatically based on high-confidence politician trading signals.',
  100000.00,
  0.70,
  5.00,
  20,
  2.00,
  10,
  5.00,
  15.00,
  1.00,
  3.00,
  true,
  'paper'
) ON CONFLICT DO NOTHING;

-- Insert initial state (linked to config)
INSERT INTO public.reference_portfolio_state (
  config_id,
  cash,
  portfolio_value,
  positions_value,
  buying_power,
  total_return,
  total_return_pct,
  peak_portfolio_value
)
SELECT
  id,
  100000.00,
  100000.00,
  0,
  100000.00,
  0,
  0,
  100000.00
FROM public.reference_portfolio_config
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 10. Helper Functions
-- ============================================================================

-- Function to calculate position size based on confidence
CREATE OR REPLACE FUNCTION public.calculate_reference_position_size(
  p_portfolio_value DECIMAL,
  p_confidence DECIMAL,
  p_current_price DECIMAL
) RETURNS INTEGER AS $$
DECLARE
  v_config reference_portfolio_config%ROWTYPE;
  v_base_size DECIMAL;
  v_confidence_range DECIMAL;
  v_normalized_confidence DECIMAL;
  v_multiplier DECIMAL;
  v_position_value DECIMAL;
  v_max_position DECIMAL;
  v_max_trade DECIMAL;
  v_shares INTEGER;
BEGIN
  -- Get config
  SELECT * INTO v_config FROM public.reference_portfolio_config LIMIT 1;

  -- Calculate base position size
  v_base_size := p_portfolio_value * (v_config.base_position_size_pct / 100);

  -- Calculate confidence multiplier (1x to max based on confidence)
  v_confidence_range := 1.0 - v_config.min_confidence_threshold;
  v_normalized_confidence := (p_confidence - v_config.min_confidence_threshold) / v_confidence_range;
  v_normalized_confidence := GREATEST(0, LEAST(1, v_normalized_confidence)); -- Clamp to 0-1
  v_multiplier := 1 + (v_normalized_confidence * (v_config.confidence_multiplier - 1));

  -- Apply multiplier
  v_position_value := v_base_size * v_multiplier;

  -- Cap at max position size
  v_max_position := p_portfolio_value * (v_config.max_position_size_pct / 100);
  v_position_value := LEAST(v_position_value, v_max_position);

  -- Cap at max single trade size
  v_max_trade := p_portfolio_value * (v_config.max_single_trade_pct / 100);
  v_position_value := LEAST(v_position_value, v_max_trade);

  -- Calculate shares
  v_shares := FLOOR(v_position_value / p_current_price);

  RETURN v_shares;
END;
$$ LANGUAGE plpgsql;

-- Function to check if we can execute more trades today
CREATE OR REPLACE FUNCTION public.can_execute_reference_trade()
RETURNS BOOLEAN AS $$
DECLARE
  v_config reference_portfolio_config%ROWTYPE;
  v_state reference_portfolio_state%ROWTYPE;
BEGIN
  SELECT * INTO v_config FROM public.reference_portfolio_config LIMIT 1;
  SELECT * INTO v_state FROM public.reference_portfolio_state LIMIT 1;

  -- Check if trading is active
  IF NOT v_config.is_active THEN
    RETURN FALSE;
  END IF;

  -- Check daily trade limit
  IF v_state.trades_today >= v_config.max_daily_trades THEN
    RETURN FALSE;
  END IF;

  -- Check max positions
  IF v_state.open_positions >= v_config.max_portfolio_positions THEN
    RETURN FALSE;
  END IF;

  RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Function to reset daily trade count (called at market open)
CREATE OR REPLACE FUNCTION public.reset_reference_daily_trades()
RETURNS VOID AS $$
BEGIN
  UPDATE public.reference_portfolio_state
  SET trades_today = 0,
      updated_at = now();
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 11. Comments for Documentation
-- ============================================================================

COMMENT ON TABLE public.reference_portfolio_config IS 'Singleton configuration for the application-level reference portfolio';
COMMENT ON TABLE public.reference_portfolio_state IS 'Real-time state and metrics for the reference portfolio';
COMMENT ON TABLE public.reference_portfolio_positions IS 'All positions (open and closed) for the reference portfolio';
COMMENT ON TABLE public.reference_portfolio_transactions IS 'Complete trade history for the reference portfolio';
COMMENT ON TABLE public.reference_portfolio_snapshots IS 'Daily performance snapshots for charting and analysis';
COMMENT ON TABLE public.reference_portfolio_signal_queue IS 'Queue for processing high-confidence signals into trades';

COMMENT ON FUNCTION public.calculate_reference_position_size IS 'Calculate confidence-weighted position size for a trade';
COMMENT ON FUNCTION public.can_execute_reference_trade IS 'Check if trading constraints allow another trade';
COMMENT ON FUNCTION public.reset_reference_daily_trades IS 'Reset daily trade counter at market open';
