-- Jurisdictions table (for sidebar filters)
CREATE TABLE public.jurisdictions (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  flag TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Politicians table (for top traders)
CREATE TABLE public.politicians (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL,
  party TEXT NOT NULL CHECK (party IN ('D', 'R', 'I', 'Other')),
  chamber TEXT NOT NULL,
  jurisdiction_id TEXT REFERENCES public.jurisdictions(id),
  state TEXT,
  avatar_url TEXT,
  total_trades INTEGER NOT NULL DEFAULT 0,
  total_volume BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Trades table (for recent trades and charts)
CREATE TABLE public.trades (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  politician_id UUID REFERENCES public.politicians(id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  company TEXT NOT NULL,
  trade_type TEXT NOT NULL CHECK (trade_type IN ('buy', 'sell')),
  amount_range TEXT NOT NULL,
  estimated_value BIGINT NOT NULL,
  filing_date DATE NOT NULL,
  transaction_date DATE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Chart data table (for trade and volume charts)
CREATE TABLE public.chart_data (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  month TEXT NOT NULL,
  year INTEGER NOT NULL,
  buys INTEGER NOT NULL DEFAULT 0,
  sells INTEGER NOT NULL DEFAULT 0,
  volume BIGINT NOT NULL DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  UNIQUE(month, year)
);

-- Dashboard stats table (for stats cards)
CREATE TABLE public.dashboard_stats (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  total_trades INTEGER NOT NULL DEFAULT 0,
  total_volume BIGINT NOT NULL DEFAULT 0,
  active_politicians INTEGER NOT NULL DEFAULT 0,
  jurisdictions_tracked INTEGER NOT NULL DEFAULT 0,
  average_trade_size BIGINT NOT NULL DEFAULT 0,
  recent_filings INTEGER NOT NULL DEFAULT 0,
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Enable RLS on all tables
ALTER TABLE public.jurisdictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.politicians ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chart_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dashboard_stats ENABLE ROW LEVEL SECURITY;

-- Public read access for all tables (this is public disclosure data)
CREATE POLICY "Public read access for jurisdictions" ON public.jurisdictions FOR SELECT USING (true);
CREATE POLICY "Public read access for politicians" ON public.politicians FOR SELECT USING (true);
CREATE POLICY "Public read access for trades" ON public.trades FOR SELECT USING (true);
CREATE POLICY "Public read access for chart_data" ON public.chart_data FOR SELECT USING (true);
CREATE POLICY "Public read access for dashboard_stats" ON public.dashboard_stats FOR SELECT USING (true);

-- Admin write access (only admins can insert/update/delete)
CREATE POLICY "Admin write access for jurisdictions" ON public.jurisdictions FOR ALL USING (
  EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
);
CREATE POLICY "Admin write access for politicians" ON public.politicians FOR ALL USING (
  EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
);
CREATE POLICY "Admin write access for trades" ON public.trades FOR ALL USING (
  EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
);
CREATE POLICY "Admin write access for chart_data" ON public.chart_data FOR ALL USING (
  EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
);
CREATE POLICY "Admin write access for dashboard_stats" ON public.dashboard_stats FOR ALL USING (
  EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
);

-- Create indexes for better query performance
CREATE INDEX idx_politicians_jurisdiction ON public.politicians(jurisdiction_id);
CREATE INDEX idx_politicians_party ON public.politicians(party);
CREATE INDEX idx_trades_politician ON public.trades(politician_id);
CREATE INDEX idx_trades_filing_date ON public.trades(filing_date DESC);
CREATE INDEX idx_trades_type ON public.trades(trade_type);
CREATE INDEX idx_chart_data_year_month ON public.chart_data(year, month);

-- Update trigger for politicians
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SET search_path = public;

CREATE TRIGGER update_politicians_updated_at
  BEFORE UPDATE ON public.politicians
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_dashboard_stats_updated_at
  BEFORE UPDATE ON public.dashboard_stats
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

-- Seed jurisdictions data
INSERT INTO public.jurisdictions (id, name, flag) VALUES
  ('us-house', 'US House', '🇺🇸'),
  ('us-senate', 'US Senate', '🇺🇸'),
  ('eu-parliament', 'EU Parliament', '🇪🇺'),
  ('uk-parliament', 'UK Parliament', '🇬🇧'),
  ('california', 'California', '🌴'),
  ('texas', 'Texas', '⛳');

-- Seed initial dashboard stats
INSERT INTO public.dashboard_stats (total_trades, total_volume, active_politicians, jurisdictions_tracked, average_trade_size, recent_filings)
VALUES (1247, 156000000, 284, 6, 125000, 89);