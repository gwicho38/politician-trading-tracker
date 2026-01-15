-- Drops Feature: Twitter-like social feed for trading insights
-- Enables users to post short-form content with $TICKER mentions

-- Main drops table
CREATE TABLE IF NOT EXISTS public.drops (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  content TEXT NOT NULL,
  is_public BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,

  -- Character limit enforced at DB level (500 chars)
  CONSTRAINT drops_content_length CHECK (char_length(content) <= 500),
  CONSTRAINT drops_content_not_empty CHECK (char_length(trim(content)) > 0)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_drops_user_id ON drops(user_id);
CREATE INDEX IF NOT EXISTS idx_drops_created_at ON drops(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_drops_public ON drops(is_public) WHERE is_public = true;

-- RLS policies for drops
ALTER TABLE drops ENABLE ROW LEVEL SECURITY;

-- Anyone can view public drops
CREATE POLICY "Anyone can view public drops"
  ON drops FOR SELECT
  USING (is_public = true);

-- Users can view their own drops (including private)
CREATE POLICY "Users can view own drops"
  ON drops FOR SELECT
  USING (auth.uid() = user_id);

-- Users can create their own drops
CREATE POLICY "Users can create drops"
  ON drops FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can update their own drops
CREATE POLICY "Users can update own drops"
  ON drops FOR UPDATE
  USING (auth.uid() = user_id);

-- Users can delete their own drops
CREATE POLICY "Users can delete own drops"
  ON drops FOR DELETE
  USING (auth.uid() = user_id);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_drops_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_drops_updated_at ON drops;
CREATE TRIGGER trigger_update_drops_updated_at
BEFORE UPDATE ON drops
FOR EACH ROW
EXECUTE FUNCTION update_drops_updated_at();

-- Likes table for drops (follows strategy_likes pattern)
CREATE TABLE IF NOT EXISTS public.drop_likes (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  drop_id UUID REFERENCES drops(id) ON DELETE CASCADE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, drop_id)
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_drop_likes_drop ON drop_likes(drop_id);
CREATE INDEX IF NOT EXISTS idx_drop_likes_user ON drop_likes(user_id);

-- RLS policies for drop_likes
ALTER TABLE drop_likes ENABLE ROW LEVEL SECURITY;

-- Anyone can view likes (needed for count aggregation)
CREATE POLICY "Anyone can view drop likes"
  ON drop_likes FOR SELECT
  USING (true);

-- Users can only insert their own likes
CREATE POLICY "Users can like drops"
  ON drop_likes FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can only delete their own likes
CREATE POLICY "Users can unlike drops"
  ON drop_likes FOR DELETE
  USING (auth.uid() = user_id);

-- Function to get drops feed with likes count and user like status
-- Follows the get_public_strategies pattern
CREATE OR REPLACE FUNCTION get_drops_feed(
  feed_type TEXT DEFAULT 'live',  -- 'live' | 'my_drops'
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
    u.email::TEXT as author_email,  -- Cast to TEXT to match return type
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
      ELSE d.is_public = true  -- 'live' feed shows all public drops
    END
  ORDER BY d.created_at DESC
  LIMIT limit_count
  OFFSET offset_count;
END;
$$;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION get_drops_feed TO authenticated;
GRANT EXECUTE ON FUNCTION get_drops_feed TO anon;

COMMENT ON FUNCTION get_drops_feed IS 'Get drops feed with likes count and user like status';

-- Enable realtime for drops table (for live feed)
ALTER PUBLICATION supabase_realtime ADD TABLE drops;
