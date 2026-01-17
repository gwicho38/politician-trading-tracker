/**
 * useStrategyFollow Hook
 * Manages user strategy subscriptions for automated trading
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from './useAuth';
import type { SignalWeights } from '@/types/signal-playground';

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

export interface StrategySubscription {
  id: string;
  user_email: string;
  strategy_type: 'reference' | 'preset' | 'custom';
  preset_id: string | null;
  preset_name: string | null;
  custom_weights: SignalWeights | null;
  trading_mode: 'paper' | 'live';
  is_active: boolean;
  sync_existing_positions: boolean;
  created_at: string;
  updated_at: string;
  last_synced_at: string | null;
}

export interface StrategyTrade {
  id: string;
  ticker: string;
  side: 'buy' | 'sell';
  quantity: number;
  signal_type: string | null;
  confidence_score: number | null;
  status: 'pending' | 'submitted' | 'filled' | 'failed' | 'skipped';
  alpaca_order_id: string | null;
  error_message: string | null;
  created_at: string;
  executed_at: string | null;
}

interface SubscribeParams {
  strategyType: 'reference' | 'preset' | 'custom';
  presetId?: string;
  customWeights?: SignalWeights;
  tradingMode: 'paper' | 'live';
  syncExistingPositions: boolean;
}

interface SyncResult {
  success: boolean;
  message: string;
  summary: {
    tradesPlanned: number;
    executed: number;
    failed: number;
  };
  results: Array<{
    ticker: string;
    side: 'buy' | 'sell';
    quantity: number;
    success: boolean;
    orderId?: string;
    error?: string;
  }>;
}

export function useStrategyFollow() {
  const { user, authReady } = useAuth();
  const queryClient = useQueryClient();

  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
  const anonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

  // Fetch current subscription
  const {
    data: subscriptionData,
    isLoading: isLoadingSubscription,
    error: subscriptionError,
    refetch: refetchSubscription
  } = useQuery({
    queryKey: ['strategy-subscription', user?.email],
    queryFn: async () => {
      const accessToken = getAccessToken();
      if (!accessToken) throw new Error('Not authenticated');

      const response = await fetch(`${supabaseUrl}/functions/v1/strategy-follow`, {
        method: 'POST',
        headers: {
          'apikey': anonKey,
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: 'get-subscription' }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to fetch subscription');
      }

      return response.json();
    },
    enabled: !!user && authReady,
    staleTime: 30000, // 30 seconds
    refetchOnWindowFocus: true,
  });

  // Fetch recent trades
  const {
    data: tradesData,
    isLoading: isLoadingTrades,
    refetch: refetchTrades
  } = useQuery({
    queryKey: ['strategy-trades', user?.email],
    queryFn: async () => {
      const accessToken = getAccessToken();
      if (!accessToken) throw new Error('Not authenticated');

      const response = await fetch(`${supabaseUrl}/functions/v1/strategy-follow`, {
        method: 'POST',
        headers: {
          'apikey': anonKey,
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: 'get-trades', limit: 20 }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to fetch trades');
      }

      return response.json();
    },
    enabled: !!user && authReady && !!subscriptionData?.subscription,
    staleTime: 60000, // 1 minute
  });

  // Subscribe to a strategy
  const subscribeMutation = useMutation({
    mutationFn: async (params: SubscribeParams) => {
      const accessToken = getAccessToken();
      if (!accessToken) throw new Error('Not authenticated');

      const response = await fetch(`${supabaseUrl}/functions/v1/strategy-follow`, {
        method: 'POST',
        headers: {
          'apikey': anonKey,
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'subscribe',
          ...params,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to subscribe');
      }

      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategy-subscription'] });
    },
  });

  // Unsubscribe from current strategy
  const unsubscribeMutation = useMutation({
    mutationFn: async () => {
      const accessToken = getAccessToken();
      if (!accessToken) throw new Error('Not authenticated');

      const response = await fetch(`${supabaseUrl}/functions/v1/strategy-follow`, {
        method: 'POST',
        headers: {
          'apikey': anonKey,
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: 'unsubscribe' }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to unsubscribe');
      }

      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategy-subscription'] });
    },
  });

  // Manual sync
  const syncNowMutation = useMutation({
    mutationFn: async (): Promise<SyncResult> => {
      const accessToken = getAccessToken();
      if (!accessToken) throw new Error('Not authenticated');

      const response = await fetch(`${supabaseUrl}/functions/v1/strategy-follow`, {
        method: 'POST',
        headers: {
          'apikey': anonKey,
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: 'sync-now' }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to sync');
      }

      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategy-subscription'] });
      queryClient.invalidateQueries({ queryKey: ['strategy-trades'] });
      queryClient.invalidateQueries({ queryKey: ['alpaca-positions'] });
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    },
  });

  // Computed values
  const subscription = subscriptionData?.subscription as StrategySubscription | null;
  const isFollowing = subscriptionData?.isFollowing || false;
  const recentTrades = (tradesData?.trades || []) as StrategyTrade[];

  // Get strategy display name
  const getStrategyName = () => {
    if (!subscription) return null;

    switch (subscription.strategy_type) {
      case 'reference':
        return 'Reference Strategy';
      case 'preset':
        return subscription.preset_name || 'Custom Preset';
      case 'custom':
        return 'Custom Weights';
      default:
        return 'Unknown Strategy';
    }
  };

  return {
    // Subscription state
    subscription,
    isFollowing,
    followingName: getStrategyName(),

    // Loading states
    isLoading: isLoadingSubscription,
    isLoadingTrades,

    // Error state
    error: subscriptionError,

    // Trade history
    recentTrades,

    // Actions
    subscribe: subscribeMutation.mutateAsync,
    unsubscribe: unsubscribeMutation.mutateAsync,
    syncNow: syncNowMutation.mutateAsync,

    // Mutation states
    isSubscribing: subscribeMutation.isPending,
    isUnsubscribing: unsubscribeMutation.isPending,
    isSyncing: syncNowMutation.isPending,

    // Refetch functions
    refetchSubscription,
    refetchTrades,

    // Check if user is authenticated
    isAuthenticated: !!user && authReady,
  };
}

export default useStrategyFollow;
