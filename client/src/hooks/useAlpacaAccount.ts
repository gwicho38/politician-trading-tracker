import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';

interface AlpacaAccount {
  portfolio_value: number;
  cash: number;
  buying_power: number;
  equity: number;
  last_equity: number;
  long_market_value: number;
  short_market_value: number;
  status: string;
  currency: string;
  pattern_day_trader: boolean;
  trading_blocked: boolean;
  transfers_blocked: boolean;
  account_blocked: boolean;
}

interface AccountResponse {
  success: boolean;
  account?: AlpacaAccount;
  tradingMode?: 'paper' | 'live';
  error?: string;
}

export function useAlpacaAccount(tradingMode: 'paper' | 'live') {
  const { user, authReady } = useAuth();

  return useQuery({
    queryKey: ['alpaca-account', tradingMode, user?.email],
    queryFn: async (): Promise<AlpacaAccount | null> => {
      if (!user) return null;

      const { data, error } = await supabase.functions.invoke<AccountResponse>('alpaca-account', {
        body: {
          action: 'get-account',
          tradingMode,
        },
      });

      if (error) {
        console.error('Error fetching account:', error);
        throw new Error(error.message);
      }

      if (!data?.success) {
        // If credentials not configured, return null (not an error)
        if (data?.error?.includes('No Alpaca credentials')) {
          return null;
        }
        throw new Error(data?.error || 'Failed to fetch account');
      }

      return data.account || null;
    },
    // Only run when auth is fully ready (not just localStorage hydrated)
    enabled: !!user && authReady,
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Refresh every minute
    retry: 1,
  });
}

// Helper to safely convert to number
function safeNumber(value: unknown): number {
  if (typeof value === 'number' && !isNaN(value)) return value;
  if (typeof value === 'string') {
    const parsed = parseFloat(value);
    return isNaN(parsed) ? 0 : parsed;
  }
  return 0;
}

// Calculate daily P&L
export function calculateDailyPnL(account: AlpacaAccount | null) {
  if (!account) return { value: 0, percent: 0 };

  const equity = safeNumber(account.equity);
  const lastEquity = safeNumber(account.last_equity);

  const pnl = equity - lastEquity;
  const pnlPercent = lastEquity > 0
    ? (pnl / lastEquity) * 100
    : 0;

  return { value: pnl, percent: pnlPercent };
}
