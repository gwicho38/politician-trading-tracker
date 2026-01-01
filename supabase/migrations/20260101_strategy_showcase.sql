-- Strategy Showcase: Likes table and author display name
-- Enables public strategy sharing with likes functionality

-- Likes table for strategies
CREATE TABLE IF NOT EXISTS public.strategy_likes (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  preset_id UUID REFERENCES signal_weight_presets(id) ON DELETE CASCADE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, preset_id)
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_strategy_likes_preset ON strategy_likes(preset_id);
CREATE INDEX IF NOT EXISTS idx_strategy_likes_user ON strategy_likes(user_id);

-- RLS policies
ALTER TABLE strategy_likes ENABLE ROW LEVEL SECURITY;

-- Anyone can view likes (needed for count aggregation)
CREATE POLICY "Anyone can view likes"
  ON strategy_likes FOR SELECT
  USING (true);

-- Users can only insert their own likes
CREATE POLICY "Users can like strategies"
  ON strategy_likes FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can only delete their own likes
CREATE POLICY "Users can unlike strategies"
  ON strategy_likes FOR DELETE
  USING (auth.uid() = user_id);

-- Add author display name column to presets (optional override for display)
ALTER TABLE signal_weight_presets
  ADD COLUMN IF NOT EXISTS author_name TEXT;

-- Create a database function to get public strategies with likes count
-- This avoids complex joins in the client and handles auth.users access
CREATE OR REPLACE FUNCTION get_public_strategies(
  sort_by TEXT DEFAULT 'recent',
  user_id_param UUID DEFAULT NULL
)
RETURNS TABLE (
  id UUID,
  name TEXT,
  description TEXT,
  user_id UUID,
  author_name TEXT,
  author_email TEXT,
  is_public BOOLEAN,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ,
  base_confidence NUMERIC,
  politician_count_5_plus NUMERIC,
  politician_count_3_4 NUMERIC,
  politician_count_2 NUMERIC,
  recent_activity_5_plus NUMERIC,
  recent_activity_2_4 NUMERIC,
  bipartisan_bonus NUMERIC,
  volume_1m_plus NUMERIC,
  volume_100k_plus NUMERIC,
  strong_signal_bonus NUMERIC,
  moderate_signal_bonus NUMERIC,
  strong_buy_threshold NUMERIC,
  buy_threshold NUMERIC,
  strong_sell_threshold NUMERIC,
  sell_threshold NUMERIC,
  likes_count BIGINT,
  user_has_liked BOOLEAN
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT
    p.id,
    p.name,
    p.description,
    p.user_id,
    p.author_name,
    COALESCE(p.author_name, u.email) as author_email,
    p.is_public,
    p.created_at,
    p.updated_at,
    p.base_confidence,
    p.politician_count_5_plus,
    p.politician_count_3_4,
    p.politician_count_2,
    p.recent_activity_5_plus,
    p.recent_activity_2_4,
    p.bipartisan_bonus,
    p.volume_1m_plus,
    p.volume_100k_plus,
    p.strong_signal_bonus,
    p.moderate_signal_bonus,
    p.strong_buy_threshold,
    p.buy_threshold,
    p.strong_sell_threshold,
    p.sell_threshold,
    COALESCE((
      SELECT COUNT(*)::BIGINT
      FROM strategy_likes l
      WHERE l.preset_id = p.id
    ), 0) as likes_count,
    CASE
      WHEN user_id_param IS NULL THEN FALSE
      ELSE EXISTS (
        SELECT 1 FROM strategy_likes l
        WHERE l.preset_id = p.id AND l.user_id = user_id_param
      )
    END as user_has_liked
  FROM signal_weight_presets p
  LEFT JOIN auth.users u ON u.id = p.user_id
  WHERE p.is_public = true AND p.user_id IS NOT NULL
  ORDER BY
    CASE WHEN sort_by = 'popular' THEN (
      SELECT COUNT(*) FROM strategy_likes l WHERE l.preset_id = p.id
    ) END DESC NULLS LAST,
    CASE WHEN sort_by = 'recent' OR sort_by IS NULL THEN p.created_at END DESC NULLS LAST,
    p.created_at DESC;
END;
$$;

-- Grant execute permission to authenticated and anon users
GRANT EXECUTE ON FUNCTION get_public_strategies TO authenticated;
GRANT EXECUTE ON FUNCTION get_public_strategies TO anon;

COMMENT ON FUNCTION get_public_strategies IS 'Get public strategies with likes count and user like status for showcase page';
