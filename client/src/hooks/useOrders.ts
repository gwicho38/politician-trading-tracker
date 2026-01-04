import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import { fetchWithRetry } from '@/lib/fetchWithRetry';

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
  const status = options?.status || 'all';
  const limit = options?.limit || 50;
  const offset = options?.offset || 0;

  return useQuery({
    queryKey: ['orders', tradingMode, status, limit, offset],
    queryFn: async (): Promise<OrdersResponse> => {
      const { data, error } = await supabase.functions.invoke('orders', {
        body: {
          action: 'get-orders',
          trading_mode: tradingMode,
          status,
          limit,
          offset,
        },
      });

      if (error) {
        throw new Error(error.message);
      }

      return data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
    staleTime: 10000, // Consider data stale after 10 seconds
  });
}

export function useSyncOrders(tradingMode: 'paper' | 'live') {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (): Promise<SyncResponse> => {
      const { data, error } = await supabase.functions.invoke('orders', {
        body: {
          action: 'sync-orders',
          tradingMode,
          status: 'all',
          limit: 100,
        },
      });

      if (error) {
        throw new Error(error.message);
      }

      return data;
    },
    onSuccess: () => {
      // Invalidate orders query to refetch with new data
      queryClient.invalidateQueries({ queryKey: ['orders', tradingMode] });
    },
  });
}

export function useCancelOrder(tradingMode: 'paper' | 'live') {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (orderId: string): Promise<{ success: boolean; message: string }> => {
      // Get the user's Alpaca credentials
      const { data: { user } } = await supabase.auth.getUser();
      if (!user?.email) {
        throw new Error('User not authenticated');
      }

      // Get credentials from user_api_keys
      const { data: credentials } = await supabase
        .from('user_api_keys')
        .select('paper_api_key, paper_secret_key, live_api_key, live_secret_key')
        .eq('user_email', user.email)
        .maybeSingle();

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
      await supabase
        .from('trading_orders')
        .update({ status: 'canceled', canceled_at: new Date().toISOString() })
        .eq('alpaca_order_id', orderId);

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
