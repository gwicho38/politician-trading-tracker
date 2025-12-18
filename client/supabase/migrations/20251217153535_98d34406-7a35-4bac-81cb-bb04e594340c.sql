-- Create notifications table
CREATE TABLE public.notifications (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  type TEXT NOT NULL DEFAULT 'info',
  read BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;

-- Users can see their own notifications or global ones
CREATE POLICY "Users can view their own notifications"
ON public.notifications FOR SELECT
USING (user_id IS NULL OR auth.uid() = user_id);

-- Users can mark their own notifications as read
CREATE POLICY "Users can update their own notifications"
ON public.notifications FOR UPDATE
USING (auth.uid() = user_id);

-- Admins can manage all notifications
CREATE POLICY "Admins can manage notifications"
ON public.notifications FOR ALL
USING (has_role(auth.uid(), 'admin'));

-- Insert sample politicians (party: D, R, I, Other)
INSERT INTO public.politicians (name, party, chamber, state, jurisdiction_id, total_trades, total_volume) VALUES
('Nancy Pelosi', 'D', 'House', 'CA', 'us-house', 89, 15500000),
('Tommy Tuberville', 'R', 'Senate', 'AL', 'us-senate', 132, 8200000),
('Dan Crenshaw', 'R', 'House', 'TX', 'us-house', 56, 4100000),
('Josh Gottheimer', 'D', 'House', 'NJ', 'us-house', 78, 6700000),
('Mark Green', 'R', 'House', 'TN', 'us-house', 45, 2900000),
('Michael McCaul', 'R', 'House', 'TX', 'us-house', 67, 9800000),
('Ro Khanna', 'D', 'House', 'CA', 'us-house', 34, 1800000),
('Pat Fallon', 'R', 'House', 'TX', 'us-house', 91, 5200000),
('Marjorie Taylor Greene', 'R', 'House', 'GA', 'us-house', 28, 980000),
('Earl Blumenauer', 'D', 'House', 'OR', 'us-house', 42, 3100000);

-- Insert sample trades (trade_type: buy, sell lowercase)
INSERT INTO public.trades (politician_id, ticker, company, trade_type, amount_range, estimated_value, transaction_date, filing_date)
SELECT 
  p.id,
  t.ticker,
  t.company,
  t.trade_type,
  t.amount_range,
  t.estimated_value,
  t.transaction_date::date,
  t.filing_date::date
FROM public.politicians p
CROSS JOIN (
  VALUES
    ('NVDA', 'NVIDIA Corporation', 'buy', '$500,001 - $1,000,000', 750000, '2025-11-15', '2025-12-01'),
    ('AAPL', 'Apple Inc.', 'buy', '$250,001 - $500,000', 375000, '2025-11-20', '2025-12-05'),
    ('MSFT', 'Microsoft Corporation', 'sell', '$100,001 - $250,000', 175000, '2025-11-22', '2025-12-08')
) AS t(ticker, company, trade_type, amount_range, estimated_value, transaction_date, filing_date)
WHERE p.name IN ('Nancy Pelosi', 'Tommy Tuberville', 'Dan Crenshaw', 'Josh Gottheimer', 'Michael McCaul');

-- Insert sample chart data
INSERT INTO public.chart_data (month, year, buys, sells, volume) VALUES
('Jan', 2025, 45, 32, 12500000),
('Feb', 2025, 52, 28, 15800000),
('Mar', 2025, 38, 41, 18200000),
('Apr', 2025, 61, 35, 21000000),
('May', 2025, 47, 52, 19500000),
('Jun', 2025, 55, 38, 23100000),
('Jul', 2025, 68, 42, 28900000),
('Aug', 2025, 43, 55, 22400000),
('Sep', 2025, 71, 39, 31200000),
('Oct', 2025, 58, 47, 26800000),
('Nov', 2025, 82, 51, 35600000),
('Dec', 2025, 65, 43, 29100000);

-- Insert sample notifications
INSERT INTO public.notifications (user_id, title, message, type) VALUES
(NULL, 'System Update', 'The platform will undergo maintenance tonight at 2 AM EST.', 'info'),
(NULL, 'New Feature', 'Real-time trade alerts are now available!', 'success'),
(NULL, 'Data Update', '500 new trades have been imported from recent filings.', 'info');