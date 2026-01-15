/**
 * Drops Feature Types
 * Types for the Twitter-like social feed feature
 */

/**
 * A drop (post) returned from the get_drops_feed function
 */
export interface Drop {
  id: string;
  user_id: string;
  content: string;
  author_email: string | null;
  is_public: boolean;
  created_at: string;
  updated_at: string;
  likes_count: number;
  user_has_liked: boolean;
}

/**
 * Feed type for filtering drops
 */
export type FeedType = 'live' | 'my_drops';

/**
 * Request to create a new drop
 */
export interface CreateDropRequest {
  content: string;
  is_public?: boolean;
}

/**
 * Sort options for drops feed
 */
export type DropsSortOption = 'recent' | 'popular';
