import { useQuery } from '@tanstack/react-query';
import { supabasePublic as supabase } from '@/integrations/supabase/client';
import { logError } from '@/lib/logger';

// Types for reference portfolio data
export interface ReferencePortfolioConfig {
  id: string;
  name: string;
  description: string;
  initial_capital: number;
  min_confidence_threshold: number;
  max_position_size_pct: number;
  max_portfolio_positions: number;
  max_single_trade_pct: number;
  max_daily_trades: number;
  default_stop_loss_pct: number;
  default_take_profit_pct: number;
  base_position_size_pct: number;
  confidence_multiplier: number;
  is_active: boolean;
  trading_mode: string;
  created_at: string;
  updated_at: string;
}

export interface ReferencePortfolioState {
  id: string;
  config_id: string;
  cash: number;
  portfolio_value: number;
  positions_value: number;
  buying_power: number;
  total_return: number;
  total_return_pct: number;
  day_return: number;
  day_return_pct: number;
  max_drawdown: number;
  current_drawdown: number;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  volatility: number | null;
  total_trades: number;
  trades_today: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number | null;
  open_positions: number;
  peak_portfolio_value: number;
  benchmark_value: number | null;
  benchmark_return_pct: number | null;
  alpha: number | null;
  last_trade_at: string | null;
  last_sync_at: string | null;
  created_at: string;
  updated_at: string;
  config?: ReferencePortfolioConfig;
}

export interface ReferencePortfolioPosition {
  id: string;
  ticker: string;
  asset_name: string | null;
  quantity: number;
  side: 'long' | 'short';
  entry_price: number;
  entry_date: string;
  entry_signal_id: string | null;
  entry_confidence: number | null;
  entry_order_id: string | null;
  current_price: number | null;
  market_value: number | null;
  unrealized_pl: number;
  unrealized_pl_pct: number;
  exit_price: number | null;
  exit_date: string | null;
  exit_signal_id: string | null;
  exit_order_id: string | null;
  exit_reason: string | null;
  realized_pl: number | null;
  realized_pl_pct: number | null;
  stop_loss_price: number | null;
  take_profit_price: number | null;
  position_size_pct: number | null;
  confidence_weight: number | null;
  is_open: boolean;
  created_at: string;
  updated_at: string;
}

export interface ReferencePortfolioTransaction {
  id: string;
  position_id: string | null;
  ticker: string;
  transaction_type: 'buy' | 'sell';
  quantity: number;
  price: number;
  total_value: number;
  signal_id: string | null;
  signal_confidence: number | null;
  signal_type: string | null;
  executed_at: string;
  alpaca_order_id: string | null;
  alpaca_client_order_id: string | null;
  position_size_pct: number | null;
  confidence_weight: number | null;
  portfolio_value_at_trade: number | null;
  status: string;
  error_message: string | null;
  created_at: string;
  // Sell-specific fields
  exit_reason: string | null;
  realized_pl: number | null;
  realized_pl_pct: number | null;
}

export interface ReferencePortfolioSnapshot {
  id: string;
  snapshot_date: string;
  snapshot_time: string;
  portfolio_value: number;
  cash: number;
  positions_value: number;
  day_return: number | null;
  day_return_pct: number | null;
  cumulative_return: number | null;
  cumulative_return_pct: number | null;
  open_positions: number | null;
  total_trades: number | null;
  sharpe_ratio: number | null;
  max_drawdown: number | null;
  current_drawdown: number | null;
  win_rate: number | null;
  benchmark_value: number | null;
  benchmark_return: number | null;
  benchmark_return_pct: number | null;
  alpha: number | null;
  created_at: string;
}

export type Timeframe = '1d' | '1w' | '1m' | '3m' | 'ytd' | '1y';

// Get start date for a given timeframe
function getStartDateForTimeframe(timeframe: Timeframe): string {
  const now = new Date();
  let startDate: Date;

  switch (timeframe) {
    case '1d':
      startDate = new Date(now.getTime() - 24 * 60 * 60 * 1000);
      break;
    case '1w':
      startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      break;
    case '1m':
      startDate = new Date(now);
      startDate.setMonth(startDate.getMonth() - 1);
      break;
    case '3m':
      startDate = new Date(now);
      startDate.setMonth(startDate.getMonth() - 3);
      break;
    case 'ytd':
      startDate = new Date(now.getFullYear(), 0, 1);
      break;
    case '1y':
      startDate = new Date(now);
      startDate.setFullYear(startDate.getFullYear() - 1);
      break;
    default:
      startDate = new Date(now);
      startDate.setMonth(startDate.getMonth() - 1);
  }

  return startDate.toISOString().split('T')[0];
}

/**
 * Hook to fetch the reference portfolio state with configuration
 * Refetches every 60 seconds to keep metrics current
 */
export function useReferencePortfolioState() {
  return useQuery({
    queryKey: ['reference-portfolio', 'state'],
    queryFn: async (): Promise<ReferencePortfolioState | null> => {
      const { data, error } = await supabase
        .from('reference_portfolio_state')
        .select(`
          *,
          config:reference_portfolio_config(*)
        `)
        .single();

      if (error) {
        logError('Failed to fetch reference portfolio state', 'portfolio', undefined, { error: error.message });
        throw error;
      }

      return data as ReferencePortfolioState;
    },
    refetchInterval: 60000, // Refresh every minute
  });
}

/**
 * Hook to fetch reference portfolio positions
 * @param includeClosed - Whether to include closed positions (default: false)
 */
export function useReferencePortfolioPositions(includeClosed = false) {
  return useQuery({
    queryKey: ['reference-portfolio', 'positions', { includeClosed }],
    queryFn: async (): Promise<ReferencePortfolioPosition[]> => {
      let query = supabase
        .from('reference_portfolio_positions')
        .select('*')
        .order('entry_date', { ascending: false });

      if (!includeClosed) {
        query = query.eq('is_open', true);
      }

      const { data, error } = await query;

      if (error) {
        logError('Failed to fetch reference portfolio positions', 'portfolio', undefined, { error: error.message });
        throw error;
      }

      return (data || []) as ReferencePortfolioPosition[];
    },
    refetchInterval: 60000,
  });
}

/**
 * Hook to fetch reference portfolio trade history
 * @param limit - Maximum number of trades to fetch (default: 50)
 * @param offset - Offset for pagination (default: 0)
 */
export function useReferencePortfolioTrades(limit = 50, offset = 0) {
  return useQuery({
    queryKey: ['reference-portfolio', 'trades', { limit, offset }],
    queryFn: async (): Promise<{ trades: ReferencePortfolioTransaction[]; total: number }> => {
      const { data, error, count } = await supabase
        .from('reference_portfolio_transactions')
        .select('*', { count: 'exact' })
        .order('executed_at', { ascending: false })
        .range(offset, offset + limit - 1);

      if (error) {
        logError('Failed to fetch reference portfolio trades', 'portfolio', undefined, { error: error.message });
        throw error;
      }

      return {
        trades: (data || []) as ReferencePortfolioTransaction[],
        total: count || 0,
      };
    },
  });
}

/**
 * Hook to fetch reference portfolio performance from Alpaca's portfolio history API
 * @param timeframe - Time period to fetch data for
 */
export function useReferencePortfolioPerformance(timeframe: Timeframe = '1m') {
  return useQuery({
    queryKey: ['reference-portfolio', 'performance', timeframe],
    queryFn: async (): Promise<ReferencePortfolioSnapshot[]> => {
      // Call the edge function which fetches from Alpaca's portfolio history API
      const { data, error } = await supabase.functions.invoke('reference-portfolio', {
        body: { action: 'get-performance', timeframe }
      });

      if (error) {
        logError('Failed to fetch reference portfolio performance', 'portfolio', undefined, { error: error.message });
        throw error;
      }

      if (!data?.success) {
        throw new Error(data?.error || 'Failed to fetch performance data');
      }

      return (data.snapshots || []) as ReferencePortfolioSnapshot[];
    },
    // Alpaca data is real-time, refresh every 5 minutes during market hours
    refetchInterval: 5 * 60 * 1000,
  });
}

/**
 * Hook to fetch reference portfolio configuration only
 */
export function useReferencePortfolioConfig() {
  return useQuery({
    queryKey: ['reference-portfolio', 'config'],
    queryFn: async (): Promise<ReferencePortfolioConfig | null> => {
      const { data, error } = await supabase
        .from('reference_portfolio_config')
        .select('*')
        .single();

      if (error) {
        logError('Failed to fetch reference portfolio config', 'portfolio', undefined, { error: error.message });
        throw error;
      }

      return data as ReferencePortfolioConfig;
    },
    staleTime: 5 * 60 * 1000, // Config changes rarely, cache for 5 minutes
  });
}

/**
 * Hook to check if market is currently open (US Eastern Time)
 * This is a client-side approximation
 */
export function useMarketStatus() {
  return useQuery({
    queryKey: ['market-status'],
    queryFn: async (): Promise<{ isOpen: boolean; nextOpen: string | null }> => {
      const now = new Date();
      const utcHour = now.getUTCHours();
      const utcMinutes = now.getUTCMinutes();
      const dayOfWeek = now.getUTCDay();

      // Convert to ET (simplified - doesn't handle DST precisely)
      const etOffset = -5; // EST
      const etHour = (utcHour + etOffset + 24) % 24;

      // Market hours: 9:30 AM - 4:00 PM ET, Monday-Friday
      const isWeekday = dayOfWeek >= 1 && dayOfWeek <= 5;
      const afterOpen = etHour > 9 || (etHour === 9 && utcMinutes >= 30);
      const beforeClose = etHour < 16;
      const isOpen = isWeekday && afterOpen && beforeClose;

      return {
        isOpen,
        nextOpen: null, // Could calculate next market open
      };
    },
    refetchInterval: 60000, // Check every minute
  });
}

/**
 * Calculate summary metrics from portfolio state
 */
export function useReferencePortfolioSummary() {
  const { data: state, isLoading, error } = useReferencePortfolioState();

  const summary = state ? {
    portfolioValue: state.portfolio_value,
    totalReturn: state.total_return,
    totalReturnPct: state.total_return_pct,
    dayReturn: state.day_return,
    dayReturnPct: state.day_return_pct,
    winRate: state.win_rate,
    sharpeRatio: state.sharpe_ratio,
    maxDrawdown: state.max_drawdown,
    openPositions: state.open_positions,
    totalTrades: state.total_trades,
    isActive: state.config?.is_active ?? false,
    alpha: state.alpha,
  } : null;

  return { summary, isLoading, error };
}
