import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';
import { toast } from 'sonner';

interface AlpacaCredentials {
  paper_api_key: string | null;
  paper_secret_key: string | null;
  paper_validated_at: string | null;
  live_api_key: string | null;
  live_secret_key: string | null;
  live_validated_at: string | null;
}

interface ConnectionTestResult {
  success: boolean;
  account?: {
    portfolio_value: number;
    cash: number;
    buying_power: number;
    status: string;
  };
  error?: string;
}

export function useAlpacaCredentials() {
  const { user, authReady } = useAuth();
  const queryClient = useQueryClient();

  // Fetch existing credentials
  const {
    data: credentials,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['alpaca-credentials', user?.email],
    queryFn: async (): Promise<AlpacaCredentials | null> => {
      if (!user?.email) return null;

      const { data, error } = await supabase
        .from('user_api_keys')
        .select('paper_api_key, paper_secret_key, paper_validated_at, live_api_key, live_secret_key, live_validated_at')
        .eq('user_email', user.email)
        .maybeSingle();

      if (error) {
        console.error('Error fetching credentials:', error);
        throw error;
      }

      return data;
    },
    // Only run query when auth is fully ready (not just localStorage hydrated)
    enabled: !!user?.email && authReady,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Save credentials mutation
  const saveCredentialsMutation = useMutation({
    mutationFn: async ({
      tradingMode,
      apiKey,
      secretKey,
    }: {
      tradingMode: 'paper' | 'live';
      apiKey: string;
      secretKey: string;
    }) => {
      if (!user?.email) throw new Error('User not authenticated');

      const updateData: Record<string, string | null> = tradingMode === 'paper'
        ? {
            paper_api_key: apiKey,
            paper_secret_key: secretKey,
            paper_validated_at: new Date().toISOString(),
          }
        : {
            live_api_key: apiKey,
            live_secret_key: secretKey,
            live_validated_at: new Date().toISOString(),
          };

      // Try to update first, then insert if not exists
      const { data: existing } = await supabase
        .from('user_api_keys')
        .select('id')
        .eq('user_email', user.email)
        .maybeSingle();

      if (existing) {
        const { error } = await supabase
          .from('user_api_keys')
          .update(updateData)
          .eq('user_email', user.email);

        if (error) throw error;
      } else {
        const { error } = await supabase
          .from('user_api_keys')
          .insert({
            user_email: user.email,
            user_name: user.user_metadata?.full_name || user.email,
            ...updateData,
          });

        if (error) throw error;
      }

      return { success: true };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alpaca-credentials'] });
      toast.success('Credentials saved successfully');
    },
    onError: (error: Error) => {
      console.error('Error saving credentials:', error);
      toast.error('Failed to save credentials');
    },
  });

  // Test connection mutation
  const testConnectionMutation = useMutation({
    mutationFn: async ({
      tradingMode,
      apiKey,
      secretKey,
    }: {
      tradingMode: 'paper' | 'live';
      apiKey: string;
      secretKey: string;
    }): Promise<ConnectionTestResult> => {
      // Call the alpaca-account edge function with test credentials
      const { data, error } = await supabase.functions.invoke('alpaca-account', {
        body: {
          action: 'test-connection',
          apiKey,
          secretKey,
          tradingMode,
        },
      });

      if (error) {
        return { success: false, error: error.message };
      }

      if (!data.success) {
        return { success: false, error: data.error || 'Connection test failed' };
      }

      return {
        success: true,
        account: data.account,
      };
    },
  });

  // Clear credentials mutation
  const clearCredentialsMutation = useMutation({
    mutationFn: async (tradingMode: 'paper' | 'live') => {
      if (!user?.email) throw new Error('User not authenticated');

      const clearData: Record<string, null> = tradingMode === 'paper'
        ? {
            paper_api_key: null,
            paper_secret_key: null,
            paper_validated_at: null,
          }
        : {
            live_api_key: null,
            live_secret_key: null,
            live_validated_at: null,
          };

      const { error } = await supabase
        .from('user_api_keys')
        .update(clearData)
        .eq('user_email', user.email);

      if (error) throw error;
      return { success: true };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alpaca-credentials'] });
      toast.success('Credentials cleared');
    },
    onError: (error: Error) => {
      console.error('Error clearing credentials:', error);
      toast.error('Failed to clear credentials');
    },
  });

  // Check if connected for a specific mode
  const isConnected = (mode: 'paper' | 'live'): boolean => {
    if (!credentials) return false;
    if (mode === 'paper') {
      return !!(credentials.paper_api_key && credentials.paper_secret_key);
    }
    return !!(credentials.live_api_key && credentials.live_secret_key);
  };

  // Get validation timestamp for a mode
  const getValidatedAt = (mode: 'paper' | 'live'): string | null => {
    if (!credentials) return null;
    return mode === 'paper' ? credentials.paper_validated_at : credentials.live_validated_at;
  };

  return {
    credentials,
    isLoading,
    error,
    refetch,
    isConnected,
    getValidatedAt,
    saveCredentials: saveCredentialsMutation.mutateAsync,
    isSaving: saveCredentialsMutation.isPending,
    testConnection: testConnectionMutation.mutateAsync,
    isTesting: testConnectionMutation.isPending,
    clearCredentials: clearCredentialsMutation.mutateAsync,
    isClearing: clearCredentialsMutation.isPending,
  };
}
