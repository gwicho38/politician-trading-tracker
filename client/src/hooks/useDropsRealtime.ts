/**
 * useDropsRealtime Hook
 * Subscribes to real-time updates on the drops table
 * Invalidates React Query cache when changes occur
 */

import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { supabasePublic } from '@/integrations/supabase/client';
import { DROPS_QUERY_KEY } from './useDrops';

/**
 * Subscribe to real-time updates for the drops table
 * Call this in components that need live updates (e.g., Live Drops tab)
 */
export function useDropsRealtime() {
  const queryClient = useQueryClient();

  useEffect(() => {
    // Subscribe to drops table changes
    const channel = supabasePublic
      .channel('drops-realtime')
      .on(
        'postgres_changes',
        {
          event: '*', // INSERT, UPDATE, DELETE
          schema: 'public',
          table: 'drops',
          filter: 'is_public=eq.true', // Only listen to public drops
        },
        (payload) => {
          // Invalidate drops queries to trigger refetch
          // This keeps the feed in sync without complex state management
          queryClient.invalidateQueries({ queryKey: DROPS_QUERY_KEY });
        }
      )
      .subscribe();

    // Cleanup subscription on unmount
    return () => {
      supabasePublic.removeChannel(channel);
    };
  }, [queryClient]);
}

export default useDropsRealtime;
