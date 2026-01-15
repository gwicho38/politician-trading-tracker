/**
 * useDrops Hook
 * Fetches drops with likes, provides CRUD and like/unlike functionality
 * Follows the useStrategyShowcase pattern
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase, supabasePublic } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';
import type { Drop, FeedType, CreateDropRequest } from '@/types/drops';

export const DROPS_QUERY_KEY = ['drops'];

/**
 * Fetch drops using the database function
 */
async function fetchDrops(
  feedType: FeedType,
  userId: string | undefined,
  limit: number = 50,
  offset: number = 0
): Promise<Drop[]> {
  const { data, error } = await supabasePublic.rpc('get_drops_feed', {
    feed_type: feedType,
    user_id_param: userId || null,
    limit_count: limit,
    offset_count: offset,
  });

  if (error) {
    throw new Error(error.message || 'Failed to fetch drops');
  }

  return (data || []) as Drop[];
}

/**
 * Create a new drop
 */
async function createDrop(
  content: string,
  userId: string,
  isPublic: boolean = true
): Promise<Drop> {
  const { data, error } = await supabase
    .from('drops')
    .insert({
      user_id: userId,
      content: content.trim(),
      is_public: isPublic,
    })
    .select()
    .single();

  if (error) {
    throw new Error(error.message || 'Failed to create drop');
  }

  return data as Drop;
}

/**
 * Delete a drop
 */
async function deleteDrop(dropId: string, userId: string): Promise<void> {
  const { error } = await supabase
    .from('drops')
    .delete()
    .eq('id', dropId)
    .eq('user_id', userId);

  if (error) {
    throw new Error(error.message || 'Failed to delete drop');
  }
}

/**
 * Like a drop
 */
async function likeDrop(dropId: string, userId: string): Promise<void> {
  const { error } = await supabase.from('drop_likes').insert({
    user_id: userId,
    drop_id: dropId,
  });

  if (error) {
    // Ignore duplicate errors (already liked)
    if (error.code === '23505') return;
    throw new Error(error.message || 'Failed to like drop');
  }
}

/**
 * Unlike a drop
 */
async function unlikeDrop(dropId: string, userId: string): Promise<void> {
  const { error } = await supabase
    .from('drop_likes')
    .delete()
    .eq('user_id', userId)
    .eq('drop_id', dropId);

  if (error) {
    throw new Error(error.message || 'Failed to unlike drop');
  }
}

export function useDrops(feedType: FeedType = 'live') {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const userId = user?.id;

  // Fetch drops query
  const {
    data: drops = [],
    isLoading,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: [...DROPS_QUERY_KEY, feedType, userId],
    queryFn: () => fetchDrops(feedType, userId),
    staleTime: 10 * 1000, // 10 seconds for real-time feel
  });

  // Create drop mutation
  const createMutation = useMutation({
    mutationFn: (request: CreateDropRequest) => {
      if (!userId) throw new Error('Must be logged in to post');
      return createDrop(request.content, userId, request.is_public ?? true);
    },
    onSuccess: () => {
      // Invalidate both feeds
      queryClient.invalidateQueries({ queryKey: DROPS_QUERY_KEY });
    },
  });

  // Delete drop mutation with optimistic update
  const deleteMutation = useMutation({
    mutationFn: (dropId: string) => {
      if (!userId) throw new Error('Must be logged in to delete');
      return deleteDrop(dropId, userId);
    },
    onMutate: async (dropId) => {
      await queryClient.cancelQueries({ queryKey: DROPS_QUERY_KEY });

      const previousDrops = queryClient.getQueryData<Drop[]>([
        ...DROPS_QUERY_KEY,
        feedType,
        userId,
      ]);

      // Optimistically remove the drop
      queryClient.setQueryData<Drop[]>(
        [...DROPS_QUERY_KEY, feedType, userId],
        (old) => old?.filter((d) => d.id !== dropId)
      );

      return { previousDrops };
    },
    onError: (_err, _dropId, context) => {
      if (context?.previousDrops) {
        queryClient.setQueryData(
          [...DROPS_QUERY_KEY, feedType, userId],
          context.previousDrops
        );
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: DROPS_QUERY_KEY });
    },
  });

  // Like mutation with optimistic updates
  const likeMutation = useMutation({
    mutationFn: (dropId: string) => {
      if (!userId) throw new Error('Must be logged in to like');
      return likeDrop(dropId, userId);
    },
    onMutate: async (dropId) => {
      await queryClient.cancelQueries({ queryKey: DROPS_QUERY_KEY });

      const previousDrops = queryClient.getQueryData<Drop[]>([
        ...DROPS_QUERY_KEY,
        feedType,
        userId,
      ]);

      // Optimistically update
      queryClient.setQueryData<Drop[]>(
        [...DROPS_QUERY_KEY, feedType, userId],
        (old) =>
          old?.map((d) =>
            d.id === dropId
              ? { ...d, likes_count: d.likes_count + 1, user_has_liked: true }
              : d
          )
      );

      return { previousDrops };
    },
    onError: (_err, _dropId, context) => {
      if (context?.previousDrops) {
        queryClient.setQueryData(
          [...DROPS_QUERY_KEY, feedType, userId],
          context.previousDrops
        );
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: DROPS_QUERY_KEY });
    },
  });

  // Unlike mutation with optimistic updates
  const unlikeMutation = useMutation({
    mutationFn: (dropId: string) => {
      if (!userId) throw new Error('Must be logged in to unlike');
      return unlikeDrop(dropId, userId);
    },
    onMutate: async (dropId) => {
      await queryClient.cancelQueries({ queryKey: DROPS_QUERY_KEY });

      const previousDrops = queryClient.getQueryData<Drop[]>([
        ...DROPS_QUERY_KEY,
        feedType,
        userId,
      ]);

      queryClient.setQueryData<Drop[]>(
        [...DROPS_QUERY_KEY, feedType, userId],
        (old) =>
          old?.map((d) =>
            d.id === dropId
              ? { ...d, likes_count: Math.max(0, d.likes_count - 1), user_has_liked: false }
              : d
          )
      );

      return { previousDrops };
    },
    onError: (_err, _dropId, context) => {
      if (context?.previousDrops) {
        queryClient.setQueryData(
          [...DROPS_QUERY_KEY, feedType, userId],
          context.previousDrops
        );
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: DROPS_QUERY_KEY });
    },
  });

  // Toggle like helper
  const toggleLike = (dropId: string, isCurrentlyLiked: boolean) => {
    if (isCurrentlyLiked) {
      unlikeMutation.mutate(dropId);
    } else {
      likeMutation.mutate(dropId);
    }
  };

  return {
    // Data
    drops,

    // Loading states
    isLoading,
    isFetching,
    error,
    refetch,

    // Auth state
    isAuthenticated: !!userId,
    userId,

    // Create actions
    createDrop: createMutation.mutate,
    createDropAsync: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    createError: createMutation.error,

    // Delete actions
    deleteDrop: deleteMutation.mutate,
    isDeleting: deleteMutation.isPending,
    deleteError: deleteMutation.error,

    // Like actions
    toggleLike,
    isLiking: likeMutation.isPending,
    isUnliking: unlikeMutation.isPending,
    likeError: likeMutation.error || unlikeMutation.error,
  };
}

export default useDrops;
