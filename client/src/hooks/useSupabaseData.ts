import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';

// Types matching database schema
export interface Jurisdiction {
  id: string;
  name: string;
  flag: string;
}

export interface Politician {
  id: string;
  name: string;
  party: 'D' | 'R' | 'I' | 'Other';
  chamber: string;
  jurisdiction_id: string;
  state: string | null;
  avatar_url: string | null;
  total_trades: number;
  total_volume: number;
}

export interface Trade {
  id: string;
  politician_id: string;
  ticker: string;
  company: string;
  trade_type: 'buy' | 'sell';
  amount_range: string;
  estimated_value: number;
  filing_date: string;
  transaction_date: string;
  politician?: Politician;
}

export interface ChartData {
  id: string;
  month: string;
  year: number;
  buys: number;
  sells: number;
  volume: number;
}

export interface DashboardStats {
  id: string;
  total_trades: number;
  total_volume: number;
  active_politicians: number;
  jurisdictions_tracked: number;
  average_trade_size: number;
  recent_filings: number;
}

// Fetch jurisdictions for sidebar
export const useJurisdictions = () => {
  return useQuery({
    queryKey: ['jurisdictions'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('jurisdictions')
        .select('*')
        .order('name');
      
      if (error) throw error;
      return data as Jurisdiction[];
    },
  });
};

// Fetch politicians for top traders
export const usePoliticians = (jurisdictionId?: string) => {
  return useQuery({
    queryKey: ['politicians', jurisdictionId],
    queryFn: async () => {
      let query = supabase
        .from('politicians')
        .select('*')
        .order('total_volume', { ascending: false });
      
      if (jurisdictionId) {
        query = query.eq('jurisdiction_id', jurisdictionId);
      }
      
      const { data, error } = await query;
      if (error) throw error;
      return data as Politician[];
    },
  });
};

// Fetch recent trades
export const useTrades = (limit = 10, jurisdictionId?: string) => {
  return useQuery({
    queryKey: ['trades', limit, jurisdictionId],
    queryFn: async () => {
      let query = supabase
        .from('trades')
        .select(`
          *,
          politician:politicians(*)
        `)
        .order('filing_date', { ascending: false })
        .limit(limit);
      
      if (jurisdictionId) {
        query = query.eq('politician.jurisdiction_id', jurisdictionId);
      }
      
      const { data, error } = await query;
      if (error) throw error;
      return data as (Trade & { politician: Politician })[];
    },
  });
};

// Fetch chart data
export const useChartData = (year?: number) => {
  return useQuery({
    queryKey: ['chartData', year],
    queryFn: async () => {
      let query = supabase
        .from('chart_data')
        .select('*')
        .order('year', { ascending: true })
        .order('month', { ascending: true });
      
      if (year) {
        query = query.eq('year', year);
      }
      
      const { data, error } = await query;
      if (error) throw error;
      return data as ChartData[];
    },
  });
};

// Fetch dashboard stats
export const useDashboardStats = () => {
  return useQuery({
    queryKey: ['dashboardStats'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('dashboard_stats')
        .select('*')
        .limit(1)
        .single();
      
      if (error) throw error;
      return data as DashboardStats;
    },
  });
};
