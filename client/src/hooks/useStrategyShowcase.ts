/**
 * useStrategyShowcase Hook
 * Fetches public strategies with likes and provides like/unlike functionality
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase, supabasePublic } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';
import type { ShowcaseStrategy } from '@/types/signal-playground';

const SHOWCASE_QUERY_KEY = ['strategyShowcase'];

export type SortOption = 'recent' | 'popular';

/**
 * Fetch public strategies using the database function
 */
async function fetchShowcaseStrategies(
  sortBy: SortOption,
  userId: string | undefined
): Promise<ShowcaseStrategy[]> {
  // Use public client for fetching - won't block on auth
  const { data, error } = await supabasePublic.rpc('get_public_strategies', {
    sort_by: sortBy,
    user_id_param: userId || null,
  });

  if (error) {
    throw new Error(error.message || 'Failed to fetch strategies');
  }

  return (data || []) as ShowcaseStrategy[];
}

/**
 * Like a strategy
 */
async function likeStrategy(presetId: string, userId: string): Promise<void> {
  const { error } = await supabase.from('strategy_likes').insert({
    user_id: userId,
    preset_id: presetId,
  });

  if (error) {
    // Ignore duplicate errors (already liked)
    if (error.code === '23505') return;
    throw new Error(error.message || 'Failed to like strategy');
  }
}

/**
 * Unlike a strategy
 */
async function unlikeStrategy(presetId: string, userId: string): Promise<void> {
  const { error } = await supabase
    .from('strategy_likes')
    .delete()
    .eq('user_id', userId)
    .eq('preset_id', presetId);

  if (error) {
    throw new Error(error.message || 'Failed to unlike strategy');
  }
}

export function useStrategyShowcase(sortBy: SortOption = 'recent') {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const userId = user?.id;

  // Fetch strategies query
  const {
    data: strategies = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: [...SHOWCASE_QUERY_KEY, sortBy, userId],
    queryFn: () => fetchShowcaseStrategies(sortBy, userId),
    staleTime: 30 * 1000, // 30 seconds
  });

  // Like mutation with optimistic updates
  const likeMutation = useMutation({
    mutationFn: (presetId: string) => {
      if (!userId) throw new Error('Must be logged in to like');
      return likeStrategy(presetId, userId);
    },
    onMutate: async (presetId) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: SHOWCASE_QUERY_KEY });

      // Snapshot previous value
      const previousStrategies = queryClient.getQueryData<ShowcaseStrategy[]>([
        ...SHOWCASE_QUERY_KEY,
        sortBy,
        userId,
      ]);

      // Optimistically update
      queryClient.setQueryData<ShowcaseStrategy[]>(
        [...SHOWCASE_QUERY_KEY, sortBy, userId],
        (old) =>
          old?.map((s) =>
            s.id === presetId
              ? { ...s, likes_count: s.likes_count + 1, user_has_liked: true }
              : s
          )
      );

      return { previousStrategies };
    },
    onError: (_err, _presetId, context) => {
      // Rollback on error
      if (context?.previousStrategies) {
        queryClient.setQueryData(
          [...SHOWCASE_QUERY_KEY, sortBy, userId],
          context.previousStrategies
        );
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: SHOWCASE_QUERY_KEY });
    },
  });

  // Unlike mutation with optimistic updates
  const unlikeMutation = useMutation({
    mutationFn: (presetId: string) => {
      if (!userId) throw new Error('Must be logged in to unlike');
      return unlikeStrategy(presetId, userId);
    },
    onMutate: async (presetId) => {
      await queryClient.cancelQueries({ queryKey: SHOWCASE_QUERY_KEY });

      const previousStrategies = queryClient.getQueryData<ShowcaseStrategy[]>([
        ...SHOWCASE_QUERY_KEY,
        sortBy,
        userId,
      ]);

      queryClient.setQueryData<ShowcaseStrategy[]>(
        [...SHOWCASE_QUERY_KEY, sortBy, userId],
        (old) =>
          old?.map((s) =>
            s.id === presetId
              ? { ...s, likes_count: Math.max(0, s.likes_count - 1), user_has_liked: false }
              : s
          )
      );

      return { previousStrategies };
    },
    onError: (_err, _presetId, context) => {
      if (context?.previousStrategies) {
        queryClient.setQueryData(
          [...SHOWCASE_QUERY_KEY, sortBy, userId],
          context.previousStrategies
        );
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: SHOWCASE_QUERY_KEY });
    },
  });

  // Toggle like helper
  const toggleLike = (presetId: string, isCurrentlyLiked: boolean) => {
    if (isCurrentlyLiked) {
      unlikeMutation.mutate(presetId);
    } else {
      likeMutation.mutate(presetId);
    }
  };

  return {
    // Data
    strategies,

    // Loading states
    isLoading,
    error,
    refetch,

    // Auth state
    isAuthenticated: !!userId,
    userId,

    // Like actions
    toggleLike,
    isLiking: likeMutation.isPending,
    isUnliking: unlikeMutation.isPending,
    likeError: likeMutation.error || unlikeMutation.error,
  };
}

export default useStrategyShowcase;
