import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';
import { fetchWithRetry } from '@/lib/fetchWithRetry';

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
 * Get user email from localStorage
 */
function getUserEmail(): string | null {
  try {
    const keys = Object.keys(localStorage).filter(k => k.startsWith('sb-') && k.endsWith('-auth-token'));
    if (keys.length === 0) return null;
    const sessionData = localStorage.getItem(keys[0]);
    if (!sessionData) return null;
    const parsed = JSON.parse(sessionData);
    return parsed?.user?.email || null;
  } catch {
    return null;
  }
}

export interface Order {
  id: string;
  alpaca_order_id: string;
  ticker: string;
  side: 'buy' | 'sell';
  quantity: number;
  order_type: 'market' | 'limit' | 'stop' | 'stop_limit';
  limit_price: number | null;
  status: string;
  trading_mode: 'paper' | 'live';
  submitted_at: string;
  filled_quantity: number;
  filled_avg_price: number | null;
  filled_at: string | null;
  canceled_at: string | null;
  signal_id: string | null;
}

interface OrdersResponse {
  success: boolean;
  orders: Order[];
  total: number;
  limit: number;
  offset: number;
}

interface SyncResponse {
  success: boolean;
  message: string;
  summary: {
    total: number;
    synced: number;
    updated: number;
    errors: number;
  };
}

export function useOrders(
  tradingMode: 'paper' | 'live',
  options?: {
    status?: 'all' | 'open' | 'closed';
    limit?: number;
    offset?: number;
  }
) {
  const { user, authReady } = useAuth();
  const status = options?.status || 'all';
  const limit = options?.limit || 50;
  const offset = options?.offset || 0;

  return useQuery({
    queryKey: ['orders', tradingMode, status, limit, offset, user?.email],
    queryFn: async (): Promise<OrdersResponse> => {
      const accessToken = getAccessToken();
      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
      const anonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

      const response = await fetch(`${supabaseUrl}/functions/v1/orders`, {
        method: 'POST',
        headers: {
          'apikey': anonKey,
          'Authorization': `Bearer ${accessToken || anonKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'get-orders',
          trading_mode: tradingMode,
          status,
          limit,
          offset,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || 'Failed to fetch orders');
      }

      return response.json();
    },
    // Only run when auth is fully ready (not just localStorage hydrated)
    enabled: !!user && authReady,
    refetchInterval: 30000, // Refresh every 30 seconds
    staleTime: 10000, // Consider data stale after 10 seconds
  });
}

export function useSyncOrders(tradingMode: 'paper' | 'live') {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (): Promise<SyncResponse> => {
      const accessToken = getAccessToken();
      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
      const anonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

      const response = await fetch(`${supabaseUrl}/functions/v1/orders`, {
        method: 'POST',
        headers: {
          'apikey': anonKey,
          'Authorization': `Bearer ${accessToken || anonKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'sync-orders',
          tradingMode,
          status: 'all',
          limit: 100,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || 'Failed to sync orders');
      }

      return response.json();
    },
    onSuccess: () => {
      // Invalidate orders query to refetch with new data
      queryClient.invalidateQueries({ queryKey: ['orders', tradingMode] });
    },
  });
}

export interface PlaceOrderParams {
  ticker: string;
  side: 'buy' | 'sell';
  quantity: number;
  order_type?: 'market' | 'limit';
  limit_price?: number;
  signal_id?: string;
}

export function usePlaceOrder(tradingMode: 'paper' | 'live') {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: PlaceOrderParams): Promise<{ success: boolean; order?: TradingOrder; error?: string }> => {
      const accessToken = getAccessToken();
      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
      const anonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

      const response = await fetch(`${supabaseUrl}/functions/v1/orders`, {
        method: 'POST',
        headers: {
          'apikey': anonKey,
          'Authorization': `Bearer ${accessToken || anonKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'place-order',
          tradingMode,
          ...params,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || 'Failed to place order');
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Failed to place order');
      }

      return data;
    },
    onSuccess: () => {
      // Invalidate orders and positions queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['orders', tradingMode] });
      queryClient.invalidateQueries({ queryKey: ['alpaca-positions', tradingMode] });
    },
  });
}

export function useCancelOrder(tradingMode: 'paper' | 'live') {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (orderId: string): Promise<{ success: boolean; message: string }> => {
      const accessToken = getAccessToken();
      const userEmail = getUserEmail();
      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
      const anonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

      if (!userEmail || !accessToken) {
        throw new Error('User not authenticated');
      }

      // Get credentials from user_api_keys
      const credResponse = await fetch(
        `${supabaseUrl}/rest/v1/user_api_keys?user_email=eq.${encodeURIComponent(userEmail)}&select=paper_api_key,paper_secret_key,live_api_key,live_secret_key`,
        {
          headers: {
            'apikey': anonKey,
            'Authorization': `Bearer ${accessToken}`,
          },
        }
      );

      const credData = await credResponse.json();
      const credentials = credData.length > 0 ? credData[0] : null;

      if (!credentials) {
        throw new Error('No Alpaca credentials found');
      }

      const apiKey = tradingMode === 'paper' ? credentials.paper_api_key : credentials.live_api_key;
      const secretKey = tradingMode === 'paper' ? credentials.paper_secret_key : credentials.live_secret_key;
      const baseUrl = tradingMode === 'paper'
        ? 'https://paper-api.alpaca.markets'
        : 'https://api.alpaca.markets';

      if (!apiKey || !secretKey) {
        throw new Error(`No ${tradingMode} trading credentials found`);
      }

      // Cancel order via Alpaca API (with retry for network issues)
      const response = await fetchWithRetry(`${baseUrl}/v2/orders/${orderId}`, {
        method: 'DELETE',
        headers: {
          'APCA-API-KEY-ID': apiKey,
          'APCA-API-SECRET-KEY': secretKey,
        },
        maxRetries: 2,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `Failed to cancel order (${response.status})`);
      }

      // Update local database
      await fetch(
        `${supabaseUrl}/rest/v1/trading_orders?alpaca_order_id=eq.${orderId}`,
        {
          method: 'PATCH',
          headers: {
            'apikey': anonKey,
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ status: 'canceled', canceled_at: new Date().toISOString() }),
        }
      );

      return { success: true, message: 'Order canceled successfully' };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders', tradingMode] });
    },
  });
}

// Helper to get order status color
export function getOrderStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'filled':
      return 'text-green-600';
    case 'partially_filled':
      return 'text-blue-600';
    case 'new':
    case 'accepted':
    case 'pending_new':
      return 'text-yellow-600';
    case 'canceled':
    case 'expired':
      return 'text-gray-500';
    case 'rejected':
      return 'text-red-600';
    default:
      return 'text-muted-foreground';
  }
}

// Helper to get order status badge variant
export function getOrderStatusVariant(status: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status.toLowerCase()) {
    case 'filled':
      return 'default';
    case 'new':
    case 'accepted':
    case 'pending_new':
    case 'partially_filled':
      return 'secondary';
    case 'rejected':
      return 'destructive';
    default:
      return 'outline';
  }
}
