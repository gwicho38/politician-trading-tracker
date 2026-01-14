-- Update get_public_strategies function to include user_lambda field
-- This allows the showcase to display which strategies include custom transforms

-- Drop the existing function first since we're changing the return type
DROP FUNCTION IF EXISTS get_public_strategies(TEXT, UUID);

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
  user_lambda TEXT,
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
    p.user_lambda,
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

-- Ensure permissions are maintained
GRANT EXECUTE ON FUNCTION get_public_strategies TO authenticated;
GRANT EXECUTE ON FUNCTION get_public_strategies TO anon;

COMMENT ON FUNCTION get_public_strategies IS 'Get public strategies with likes count, user_lambda, and user like status for showcase page';
