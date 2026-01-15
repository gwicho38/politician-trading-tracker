-- Fix get_drops_feed function type mismatch
-- Cast author_email to TEXT to match function return type

CREATE OR REPLACE FUNCTION get_drops_feed(
  feed_type TEXT DEFAULT 'live',
  user_id_param UUID DEFAULT NULL,
  limit_count INT DEFAULT 50,
  offset_count INT DEFAULT 0
)
RETURNS TABLE (
  id UUID,
  user_id UUID,
  content TEXT,
  author_email TEXT,
  is_public BOOLEAN,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ,
  likes_count BIGINT,
  user_has_liked BOOLEAN
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT
    d.id,
    d.user_id,
    d.content,
    u.email::TEXT as author_email,  -- Explicit cast to TEXT
    d.is_public,
    d.created_at,
    d.updated_at,
    COALESCE((
      SELECT COUNT(*)::BIGINT
      FROM drop_likes l
      WHERE l.drop_id = d.id
    ), 0) as likes_count,
    CASE
      WHEN user_id_param IS NULL THEN FALSE
      ELSE EXISTS (
        SELECT 1 FROM drop_likes l
        WHERE l.drop_id = d.id AND l.user_id = user_id_param
      )
    END as user_has_liked
  FROM drops d
  LEFT JOIN auth.users u ON u.id = d.user_id
  WHERE
    CASE
      WHEN feed_type = 'my_drops' THEN d.user_id = user_id_param
      ELSE d.is_public = true
    END
  ORDER BY d.created_at DESC
  LIMIT limit_count
  OFFSET offset_count;
END;
$$;

COMMENT ON FUNCTION get_drops_feed IS 'Get drops feed with likes count and user like status (fixed type mismatch)';
