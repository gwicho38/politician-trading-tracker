-- Signal Weight Presets Table
-- Stores user-defined weight configurations for signal generation playground

CREATE TABLE IF NOT EXISTS public.signal_weight_presets (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  is_public BOOLEAN DEFAULT FALSE,

  -- Base confidence weight
  base_confidence NUMERIC NOT NULL DEFAULT 0.50,

  -- Politician count weights
  politician_count_5_plus NUMERIC NOT NULL DEFAULT 0.15,
  politician_count_3_4 NUMERIC NOT NULL DEFAULT 0.10,
  politician_count_2 NUMERIC NOT NULL DEFAULT 0.05,

  -- Recent activity weights (last 30 days)
  recent_activity_5_plus NUMERIC NOT NULL DEFAULT 0.10,
  recent_activity_2_4 NUMERIC NOT NULL DEFAULT 0.05,

  -- Bipartisan bonus
  bipartisan_bonus NUMERIC NOT NULL DEFAULT 0.10,

  -- Volume magnitude weights
  volume_1m_plus NUMERIC NOT NULL DEFAULT 0.10,
  volume_100k_plus NUMERIC NOT NULL DEFAULT 0.05,

  -- Signal type bonuses
  strong_signal_bonus NUMERIC NOT NULL DEFAULT 0.15,
  moderate_signal_bonus NUMERIC NOT NULL DEFAULT 0.10,

  -- Signal type thresholds (buy/sell ratios)
  strong_buy_threshold NUMERIC NOT NULL DEFAULT 3.0,
  buy_threshold NUMERIC NOT NULL DEFAULT 2.0,
  strong_sell_threshold NUMERIC NOT NULL DEFAULT 0.33,
  sell_threshold NUMERIC NOT NULL DEFAULT 0.5,

  -- Metadata
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Enable Row Level Security
ALTER TABLE public.signal_weight_presets ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (idempotent)
DROP POLICY IF EXISTS "Users can view own and public presets" ON public.signal_weight_presets;
DROP POLICY IF EXISTS "Users can insert own presets" ON public.signal_weight_presets;
DROP POLICY IF EXISTS "Users can update own presets" ON public.signal_weight_presets;
DROP POLICY IF EXISTS "Users can delete own presets" ON public.signal_weight_presets;

-- Users can view their own presets and public presets
CREATE POLICY "Users can view own and public presets"
ON public.signal_weight_presets
FOR SELECT
USING (auth.uid() = user_id OR is_public = true);

-- Users can insert their own presets
CREATE POLICY "Users can insert own presets"
ON public.signal_weight_presets
FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Users can update their own presets
CREATE POLICY "Users can update own presets"
ON public.signal_weight_presets
FOR UPDATE
USING (auth.uid() = user_id);

-- Users can delete their own presets
CREATE POLICY "Users can delete own presets"
ON public.signal_weight_presets
FOR DELETE
USING (auth.uid() = user_id);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_signal_weight_presets_user_id
ON public.signal_weight_presets(user_id);

CREATE INDEX IF NOT EXISTS idx_signal_weight_presets_public
ON public.signal_weight_presets(is_public)
WHERE is_public = true;

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_signal_weight_presets_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_signal_weight_presets_updated_at ON public.signal_weight_presets;
CREATE TRIGGER trigger_update_signal_weight_presets_updated_at
BEFORE UPDATE ON public.signal_weight_presets
FOR EACH ROW
EXECUTE FUNCTION update_signal_weight_presets_updated_at();

-- Delete existing system presets and re-insert (idempotent)
DELETE FROM public.signal_weight_presets WHERE user_id IS NULL AND is_public = true;

-- Insert default system presets (public, no user)
INSERT INTO public.signal_weight_presets (
  user_id, name, description, is_public,
  base_confidence,
  politician_count_5_plus, politician_count_3_4, politician_count_2,
  recent_activity_5_plus, recent_activity_2_4,
  bipartisan_bonus,
  volume_1m_plus, volume_100k_plus,
  strong_signal_bonus, moderate_signal_bonus,
  strong_buy_threshold, buy_threshold, strong_sell_threshold, sell_threshold
) VALUES
-- Default balanced preset
(NULL, 'Balanced (Default)', 'Default weights balancing all factors equally', true,
 0.50, 0.15, 0.10, 0.05, 0.10, 0.05, 0.10, 0.10, 0.05, 0.15, 0.10, 3.0, 2.0, 0.33, 0.5),

-- High conviction preset (requires more evidence)
(NULL, 'High Conviction', 'Higher thresholds requiring stronger signals', true,
 0.40, 0.20, 0.15, 0.10, 0.15, 0.10, 0.15, 0.10, 0.05, 0.20, 0.15, 4.0, 2.5, 0.25, 0.4),

-- Momentum preset (favors recent activity)
(NULL, 'Momentum', 'Emphasizes recent trading activity', true,
 0.45, 0.10, 0.08, 0.05, 0.20, 0.15, 0.10, 0.15, 0.10, 0.15, 0.10, 2.5, 1.8, 0.40, 0.55),

-- Bipartisan consensus preset
(NULL, 'Bipartisan Consensus', 'Higher weight on cross-party agreement', true,
 0.45, 0.12, 0.10, 0.05, 0.10, 0.05, 0.25, 0.10, 0.05, 0.15, 0.10, 2.5, 1.8, 0.40, 0.55);
