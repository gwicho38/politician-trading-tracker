import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';

interface AlpacaPosition {
  asset_id: string;
  symbol: string;
  exchange: string;
  asset_class: string;
  avg_entry_price: number;
  qty: number;
  side: 'long' | 'short';
  market_value: number;
  cost_basis: number;
  unrealized_pl: number;
  unrealized_plpc: number;
  unrealized_intraday_pl: number;
  unrealized_intraday_plpc: number;
  current_price: number;
  lastday_price: number;
  change_today: number;
}

interface PositionsResponse {
  success: boolean;
  positions?: AlpacaPosition[];
  tradingMode?: 'paper' | 'live';
  error?: string;
}

export function useAlpacaPositions(tradingMode: 'paper' | 'live') {
  const { user, authReady } = useAuth();

  return useQuery({
    queryKey: ['alpaca-positions', tradingMode, user?.email],
    queryFn: async (): Promise<AlpacaPosition[]> => {
      if (!user) return [];

      const { data, error } = await supabase.functions.invoke<PositionsResponse>('alpaca-account', {
        body: {
          action: 'get-positions',
          tradingMode,
        },
      });

      if (error) {
        console.error('Error fetching positions:', error);
        throw new Error(error.message);
      }

      if (!data?.success) {
        // If no credentials, return empty array
        if (data?.error?.includes('No Alpaca credentials')) {
          return [];
        }
        throw new Error(data?.error || 'Failed to fetch positions');
      }

      return data.positions || [];
    },
    // Only run when auth is fully ready (not just localStorage hydrated)
    enabled: !!user && authReady,
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Refresh every minute
    retry: 1,
  });
}

// Calculate total position metrics
export function calculatePositionMetrics(positions: AlpacaPosition[]) {
  return positions.reduce(
    (acc, pos) => ({
      totalValue: acc.totalValue + pos.market_value,
      totalCost: acc.totalCost + pos.cost_basis,
      totalPnL: acc.totalPnL + pos.unrealized_pl,
      totalIntradayPnL: acc.totalIntradayPnL + pos.unrealized_intraday_pl,
      positionCount: acc.positionCount + 1,
    }),
    { totalValue: 0, totalCost: 0, totalPnL: 0, totalIntradayPnL: 0, positionCount: 0 }
  );
}
