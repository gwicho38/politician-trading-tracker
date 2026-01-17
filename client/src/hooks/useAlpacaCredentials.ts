import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';
import { toast } from 'sonner';

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

      const accessToken = getAccessToken();
      if (!accessToken) return null;

      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
      const anonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

      const response = await fetch(
        `${supabaseUrl}/rest/v1/user_api_keys?user_email=eq.${encodeURIComponent(user.email)}&select=paper_api_key,paper_secret_key,paper_validated_at,live_api_key,live_secret_key,live_validated_at`,
        {
          headers: {
            'apikey': anonKey,
            'Authorization': `Bearer ${accessToken}`,
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Error fetching credentials:', errorData);
        throw new Error(errorData.message || 'Failed to fetch credentials');
      }

      const data = await response.json();
      return data.length > 0 ? data[0] : null;
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

      const accessToken = getAccessToken();
      if (!accessToken) throw new Error('No access token');

      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
      const anonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

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
      const checkResponse = await fetch(
        `${supabaseUrl}/rest/v1/user_api_keys?user_email=eq.${encodeURIComponent(user.email)}&select=id`,
        {
          headers: {
            'apikey': anonKey,
            'Authorization': `Bearer ${accessToken}`,
          },
        }
      );

      const existingData = await checkResponse.json();
      const existing = existingData.length > 0 ? existingData[0] : null;

      if (existing) {
        const response = await fetch(
          `${supabaseUrl}/rest/v1/user_api_keys?user_email=eq.${encodeURIComponent(user.email)}`,
          {
            method: 'PATCH',
            headers: {
              'apikey': anonKey,
              'Authorization': `Bearer ${accessToken}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(updateData),
          }
        );

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.message || 'Failed to update credentials');
        }
      } else {
        const response = await fetch(
          `${supabaseUrl}/rest/v1/user_api_keys`,
          {
            method: 'POST',
            headers: {
              'apikey': anonKey,
              'Authorization': `Bearer ${accessToken}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              user_email: user.email,
              user_name: user.user_metadata?.full_name || user.email,
              ...updateData,
            }),
          }
        );

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.message || 'Failed to save credentials');
        }
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
      const accessToken = getAccessToken();
      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
      const anonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

      // Call the alpaca-account edge function with test credentials
      const response = await fetch(`${supabaseUrl}/functions/v1/alpaca-account`, {
        method: 'POST',
        headers: {
          'apikey': anonKey,
          'Authorization': `Bearer ${accessToken || anonKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'test-connection',
          apiKey,
          secretKey,
          tradingMode,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return { success: false, error: errorData.message || 'Connection test failed' };
      }

      const data = await response.json();

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

      const accessToken = getAccessToken();
      if (!accessToken) throw new Error('No access token');

      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
      const anonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

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

      const response = await fetch(
        `${supabaseUrl}/rest/v1/user_api_keys?user_email=eq.${encodeURIComponent(user.email)}`,
        {
          method: 'PATCH',
          headers: {
            'apikey': anonKey,
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(clearData),
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || 'Failed to clear credentials');
      }

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
