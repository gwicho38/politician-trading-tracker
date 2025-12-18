-- Create positions table for tracking portfolio positions
CREATE TABLE IF NOT EXISTS public.positions (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  asset_name TEXT,
  quantity NUMERIC NOT NULL DEFAULT 0,
  side TEXT NOT NULL DEFAULT 'long', -- 'long' or 'short'
  avg_entry_price NUMERIC NOT NULL DEFAULT 0,
  current_price NUMERIC DEFAULT 0,
  market_value NUMERIC DEFAULT 0,
  unrealized_pl NUMERIC DEFAULT 0,
  unrealized_pl_pct NUMERIC DEFAULT 0,
  stop_loss NUMERIC,
  take_profit NUMERIC,
  is_open BOOLEAN NOT NULL DEFAULT true,
  trading_mode TEXT NOT NULL DEFAULT 'paper', -- 'paper' or 'live'
  alpaca_asset_id TEXT,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Create trading_orders table for order history
CREATE TABLE IF NOT EXISTS public.trading_orders (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  side TEXT NOT NULL, -- 'buy' or 'sell'
  quantity NUMERIC NOT NULL,
  order_type TEXT NOT NULL DEFAULT 'market', -- 'market', 'limit', 'stop', 'stop_limit'
  limit_price NUMERIC,
  stop_price NUMERIC,
  status TEXT NOT NULL DEFAULT 'new', -- 'new', 'accepted', 'pending_new', 'partially_filled', 'filled', 'canceled', 'rejected', 'expired'
  filled_qty NUMERIC DEFAULT 0,
  filled_avg_price NUMERIC,
  trading_mode TEXT NOT NULL DEFAULT 'paper', -- 'paper' or 'live'
  alpaca_order_id TEXT,
  signal_id UUID, -- Reference to trading signal that triggered this order
  submitted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  filled_at TIMESTAMP WITH TIME ZONE,
  canceled_at TIMESTAMP WITH TIME ZONE,
  expired_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trading_orders ENABLE ROW LEVEL SECURITY;

-- Positions policies - users can only see their own positions
CREATE POLICY "Users can view own positions"
ON public.positions
FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own positions"
ON public.positions
FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own positions"
ON public.positions
FOR UPDATE
USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own positions"
ON public.positions
FOR DELETE
USING (auth.uid() = user_id);

-- Trading orders policies - users can only see their own orders
CREATE POLICY "Users can view own orders"
ON public.trading_orders
FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own orders"
ON public.trading_orders
FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own orders"
ON public.trading_orders
FOR UPDATE
USING (auth.uid() = user_id);

-- Create indexes for performance
CREATE INDEX idx_positions_user_id ON public.positions(user_id);
CREATE INDEX idx_positions_is_open ON public.positions(is_open);
CREATE INDEX idx_positions_ticker ON public.positions(ticker);

CREATE INDEX idx_trading_orders_user_id ON public.trading_orders(user_id);
CREATE INDEX idx_trading_orders_status ON public.trading_orders(status);
CREATE INDEX idx_trading_orders_submitted_at ON public.trading_orders(submitted_at DESC);
CREATE INDEX idx_trading_orders_trading_mode ON public.trading_orders(trading_mode);
