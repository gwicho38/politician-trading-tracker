/**
 * useDrops Hook
 * Fetches drops with likes, provides CRUD and like/unlike functionality
 * Follows the useStrategyShowcase pattern
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabasePublic } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';
import { logDebug, logError } from '@/lib/logger';
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
 * Get access token from localStorage
 */
function getAccessToken(): string | null {
  try {
    const keys = Object.keys(localStorage).filter(k => k.startsWith('sb-') && k.endsWith('-auth-token'));
    if (keys.length === 0) return null;
    const sessionData = localStorage.getItem(keys[0]);
    if (!sessionData) return null;
    const parsed = JSON.parse(sessionData);
    return parsed?.access_token || null;
  } catch {
    return null;
  }
}

/**
 * Create a new drop using direct fetch to avoid Supabase client blocking
 */
async function createDrop(
  content: string,
  userId: string,
  isPublic: boolean = true
): Promise<Drop> {
  logDebug('Starting insert', 'drops', { userId });

  const accessToken = getAccessToken();
  logDebug('Access token check', 'drops', { hasToken: !!accessToken });

  if (!accessToken) {
    throw new Error('No access token found. Please sign in again.');
  }

  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
  const anonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

  logDebug('Making fetch request', 'drops');

  const response = await fetch(`${supabaseUrl}/rest/v1/drops`, {
    method: 'POST',
    headers: {
      'apikey': anonKey,
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
      'Prefer': 'return=representation',
    },
    body: JSON.stringify({
      user_id: userId,
      content: content.trim(),
      is_public: isPublic,
    }),
  });

  logDebug('Response received', 'drops', { status: response.status });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    logError('Create drop failed', 'drops', undefined, { errorData, status: response.status });

    if (response.status === 401 || errorData.code === '42501') {
      throw new Error('Session expired. Please sign in again.');
    }
    throw new Error(errorData.message || `Failed to create drop (${response.status})`);
  }

  const data = await response.json();
  logDebug('Create drop success', 'drops', { id: Array.isArray(data) ? data[0]?.id : data?.id });

  // Response is an array, get the first item
  return Array.isArray(data) ? data[0] : data;
}

/**
 * Delete a drop using direct fetch
 */
async function deleteDrop(dropId: string, userId: string): Promise<void> {
  logDebug('Deleting drop', 'drops', { dropId, userId });

  const accessToken = getAccessToken();
  if (!accessToken) {
    throw new Error('No access token found. Please sign in again.');
  }

  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
  const anonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

  const response = await fetch(
    `${supabaseUrl}/rest/v1/drops?id=eq.${dropId}&user_id=eq.${userId}`,
    {
      method: 'DELETE',
      headers: {
        'apikey': anonKey,
        'Authorization': `Bearer ${accessToken}`,
      },
    }
  );

  logDebug('Delete response', 'drops', { status: response.status });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    logError('Delete drop failed', 'drops', undefined, { errorData });
    throw new Error(errorData.message || 'Failed to delete drop');
  }

  logDebug('Delete drop success', 'drops', { dropId });
}

/**
 * Like a drop using direct fetch
 */
async function likeDrop(dropId: string, userId: string): Promise<void> {
  logDebug('Liking drop', 'drops', { dropId });

  const accessToken = getAccessToken();
  if (!accessToken) {
    throw new Error('No access token found. Please sign in again.');
  }

  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
  const anonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

  const response = await fetch(`${supabaseUrl}/rest/v1/drop_likes`, {
    method: 'POST',
    headers: {
      'apikey': anonKey,
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_id: userId,
      drop_id: dropId,
    }),
  });

  // Ignore 409 Conflict (already liked - duplicate)
  if (response.status === 409) {
    logDebug('Already liked', 'drops', { dropId });
    return;
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    logError('Like drop failed', 'drops', undefined, { errorData });
    throw new Error(errorData.message || 'Failed to like drop');
  }

  logDebug('Like drop success', 'drops', { dropId });
}

/**
 * Unlike a drop using direct fetch
 */
async function unlikeDrop(dropId: string, userId: string): Promise<void> {
  logDebug('Unliking drop', 'drops', { dropId });

  const accessToken = getAccessToken();
  if (!accessToken) {
    throw new Error('No access token found. Please sign in again.');
  }

  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
  const anonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

  const response = await fetch(
    `${supabaseUrl}/rest/v1/drop_likes?user_id=eq.${userId}&drop_id=eq.${dropId}`,
    {
      method: 'DELETE',
      headers: {
        'apikey': anonKey,
        'Authorization': `Bearer ${accessToken}`,
      },
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    logError('Unlike drop failed', 'drops', undefined, { errorData });
    throw new Error(errorData.message || 'Failed to unlike drop');
  }

  logDebug('Unlike drop success', 'drops', { dropId });
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
      logDebug('Create mutation called', 'drops', { content: request.content.substring(0, 50), userId });
      if (!userId) throw new Error('Must be logged in to post');
      return createDrop(request.content, userId, request.is_public ?? true);
    },
    onMutate: (variables) => {
      logDebug('Create mutation starting', 'drops', { isPublic: variables.is_public });
    },
    onSuccess: (data) => {
      logDebug('Create mutation success', 'drops', { id: data.id });
      // Invalidate both feeds
      queryClient.invalidateQueries({ queryKey: DROPS_QUERY_KEY });
    },
    onError: (error) => {
      logError('Create mutation failed', 'drops', error instanceof Error ? error : undefined);
    },
    onSettled: () => {
      logDebug('Create mutation settled', 'drops');
    },
  });

  // Delete drop mutation with optimistic update
  const deleteMutation = useMutation({
    mutationFn: (dropId: string) => {
      logDebug('Delete mutation called', 'drops', { dropId });
      if (!userId) throw new Error('Must be logged in to delete');
      return deleteDrop(dropId, userId);
    },
    onMutate: async (dropId) => {
      logDebug('Delete mutation - optimistic update', 'drops', { dropId });
      await queryClient.cancelQueries({ queryKey: DROPS_QUERY_KEY });

      // Get previous data for rollback
      const previousDrops = queryClient.getQueryData<Drop[]>([
        ...DROPS_QUERY_KEY,
        feedType,
        userId,
      ]);

      // Optimistically remove from ALL cached queries (both feeds)
      queryClient.setQueriesData<Drop[]>(
        { queryKey: DROPS_QUERY_KEY },
        (old) => old?.filter((d) => d.id !== dropId)
      );

      return { previousDrops };
    },
    onError: (err, _dropId, context) => {
      logError('Delete mutation failed', 'drops', err instanceof Error ? err : undefined);
      if (context?.previousDrops) {
        queryClient.setQueryData(
          [...DROPS_QUERY_KEY, feedType, userId],
          context.previousDrops
        );
      }
    },
    onSuccess: () => {
      logDebug('Delete mutation success', 'drops');
    },
    onSettled: () => {
      logDebug('Delete mutation settled', 'drops');
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
