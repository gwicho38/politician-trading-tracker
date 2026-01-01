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
  first_name: string;
  last_name: string;
  full_name: string;
  name: string; // alias for full_name for compatibility
  party: string;
  role: string;
  chamber: string; // alias for role for compatibility
  state_or_country: string | null;
  state: string | null; // alias for state_or_country
  district: string | null;
  jurisdiction_id: string;
  avatar_url: string | null;
  total_trades: number;
  total_volume: number;
  is_active: boolean;
}

// Trading disclosure from the trading_disclosures table (actual ETL data)
export interface TradingDisclosure {
  id: string;
  politician_id: string;
  transaction_date: string;
  disclosure_date: string;
  transaction_type: string; // 'purchase', 'sale', 'exchange', 'unknown'
  asset_name: string;
  asset_ticker: string | null;
  asset_type: string | null;
  amount_range_min: number | null;
  amount_range_max: number | null;
  source_url: string | null; // Link to the original PDF disclosure
  source_document_id: string | null;
  raw_data: Record<string, unknown> | null;
  status: string;
  created_at: string;
  updated_at: string;
  politician?: Politician;
}

// Alias for backwards compatibility
export interface Trade extends TradingDisclosure {
  ticker: string; // alias for asset_ticker
  company: string; // alias for asset_name
  trade_type: string; // alias for transaction_type
  amount_range: string; // computed from min/max
  estimated_value: number; // computed from min/max midpoint
  filing_date: string; // alias for disclosure_date
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
        .eq('is_active', true)
        .order('total_volume', { ascending: false });

      if (jurisdictionId) {
        // Map jurisdiction IDs to state/country filters
        const jurisdictionMap: Record<string, string> = {
          'us-house': 'Representative',
          'us-senate': 'Senate',
          'eu-parliament': 'EU',
          'uk-parliament': 'UK',
        };
        const role = jurisdictionMap[jurisdictionId];
        if (role) {
          query = query.eq('role', role);
        }
      }

      const { data, error } = await query;
      if (error) throw error;

      // Transform data to match expected interface
      return (data || []).map(p => ({
        ...p,
        name: p.full_name || `${p.first_name} ${p.last_name}`,
        chamber: p.role || 'Unknown',
        state: p.state_or_country || p.district,
        party: p.party || 'Unknown',
        jurisdiction_id: p.role === 'Representative' ? 'us-house' :
                         p.role === 'Senate' ? 'us-senate' : 'unknown',
      })) as Politician[];
    },
  });
};

// Helper to format amount range
const formatAmountRange = (min: number | null, max: number | null): string => {
  if (min === null && max === null) return 'Unknown';
  if (min === null) return `Up to $${max?.toLocaleString()}`;
  if (max === null) return `$${min.toLocaleString()}+`;
  return `$${min.toLocaleString()} - $${max.toLocaleString()}`;
};

// Fetch recent trading disclosures (from trading_disclosures table)
export const useTrades = (limit = 10, jurisdictionId?: string) => {
  return useQuery({
    queryKey: ['trades', limit, jurisdictionId],
    queryFn: async () => {
      // Query the actual trading_disclosures table with politician join
      let query = supabase
        .from('trading_disclosures')
        .select(`
          *,
          politician:politicians(*)
        `)
        .eq('status', 'active')
        .order('disclosure_date', { ascending: false })
        .limit(limit);

      const { data, error } = await query;
      if (error) throw error;

      // Transform to match expected Trade interface
      return (data || []).map(d => {
        const politician = d.politician as Politician | null;
        const minVal = d.amount_range_min || 0;
        const maxVal = d.amount_range_max || 0;

        return {
          ...d,
          // Computed aliases for backwards compatibility
          ticker: d.asset_ticker || '',
          company: d.asset_name || '',
          trade_type: d.transaction_type === 'purchase' ? 'buy' :
                      d.transaction_type === 'sale' ? 'sell' : d.transaction_type,
          amount_range: formatAmountRange(d.amount_range_min, d.amount_range_max),
          estimated_value: (minVal + maxVal) / 2,
          filing_date: d.disclosure_date,
          // Transform politician data
          politician: politician ? {
            ...politician,
            name: politician.full_name || `${politician.first_name} ${politician.last_name}`,
            chamber: politician.role || 'Unknown',
            state: politician.state_or_country || politician.district,
            party: politician.party || 'Unknown',
            jurisdiction_id: politician.role === 'Representative' ? 'us-house' :
                             politician.role === 'Senate' ? 'us-senate' : 'unknown',
          } : undefined,
        };
      }) as Trade[];
    },
  });
};

// Sort configuration type
export type SortField = 'disclosure_date' | 'transaction_date' | 'amount_range_max' | 'asset_ticker' | 'transaction_type';
export type SortDirection = 'asc' | 'desc';

// Fetch trading disclosures with search/filter/sort support
export const useTradingDisclosures = (options: {
  limit?: number;
  offset?: number;
  ticker?: string;
  politicianId?: string;
  transactionType?: string;
  party?: string;
  searchQuery?: string;
  sortField?: SortField;
  sortDirection?: SortDirection;
  dateFrom?: string;
  dateTo?: string;
} = {}) => {
  const {
    limit = 50,
    offset = 0,
    ticker,
    politicianId,
    transactionType,
    party,
    searchQuery,
    sortField = 'disclosure_date',
    sortDirection = 'desc',
    dateFrom,
    dateTo,
  } = options;

  return useQuery({
    queryKey: ['tradingDisclosures', limit, offset, ticker, politicianId, transactionType, party, searchQuery, sortField, sortDirection, dateFrom, dateTo],
    queryFn: async () => {
      // Use inner join when filtering by party to enable server-side filtering
      const selectQuery = party
        ? `*, politician:politicians!inner(*)`
        : `*, politician:politicians(*)`;

      let query = supabase
        .from('trading_disclosures')
        .select(selectQuery, { count: 'exact' })
        .eq('status', 'active')
        .order(sortField, { ascending: sortDirection === 'asc' })
        .range(offset, offset + limit - 1);

      if (ticker) {
        query = query.ilike('asset_ticker', `%${ticker}%`);
      }
      if (politicianId) {
        query = query.eq('politician_id', politicianId);
      }
      if (transactionType) {
        query = query.eq('transaction_type', transactionType);
      }
      // Search: use ilike on asset_ticker only (simpler, faster, avoids 500 errors)
      // For more comprehensive search, search asset_name separately
      if (searchQuery) {
        // Use a simpler approach: search ticker first, fallback to name
        // The or() with multiple ilike can cause timeout on large tables
        query = query.ilike('asset_ticker', `%${searchQuery}%`);
      }
      if (dateFrom) {
        query = query.gte('disclosure_date', dateFrom);
      }
      if (dateTo) {
        query = query.lte('disclosure_date', dateTo);
      }
      // Filter by party server-side using the inner join
      if (party) {
        query = query.eq('politician.party', party);
      }

      const { data, error, count } = await query;
      if (error) throw error;

      return {
        disclosures: (data || []).map(d => ({
          ...d,
          politician: d.politician ? {
            ...d.politician,
            name: d.politician.full_name || `${d.politician.first_name} ${d.politician.last_name}`,
          } : undefined,
        })) as TradingDisclosure[],
        total: count || 0,
      };
    },
    staleTime: 5 * 60 * 1000, // Cache paginated results for 5 minutes
  });
};

// Month names for chart display
const MONTH_NAMES = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

// Time range options for chart filtering
export type ChartTimeRange = 'trailing12' | 'trailing24' | 'all' | number; // number = specific year

// Fetch chart data with time range filtering
export const useChartData = (timeRange: ChartTimeRange = 'trailing12') => {
  return useQuery({
    queryKey: ['chartData', timeRange],
    queryFn: async () => {
      let query = supabase
        .from('chart_data')
        .select('*')
        .order('year', { ascending: true })
        .order('month', { ascending: true });

      // Apply time range filter
      if (typeof timeRange === 'number') {
        // Specific year
        query = query.eq('year', timeRange);
      } else if (timeRange === 'trailing12' || timeRange === 'trailing24') {
        // Trailing months filter
        const monthsBack = timeRange === 'trailing12' ? 12 : 24;
        const now = new Date();
        const startDate = new Date(now.getFullYear(), now.getMonth() - monthsBack, 1);
        const startYear = startDate.getFullYear();
        const startMonth = startDate.getMonth() + 1; // 1-indexed

        // We need to filter where (year > startYear) OR (year = startYear AND month >= startMonth)
        query = query.or(
          `year.gt.${startYear},and(year.eq.${startYear},month.gte.${startMonth})`
        );
      }
      // 'all' = no filter

      const { data, error } = await query;
      if (error) throw error;

      // Transform to include display label with year
      return (data || []).map((row: { id: string; month: number; year: number; buys: number; sells: number; volume: number }) => ({
        ...row,
        // Keep original month for internal use
        monthNum: row.month,
        // Display label includes abbreviated year (e.g., "Jan '24")
        month: `${MONTH_NAMES[row.month]} '${String(row.year).slice(-2)}`,
      })) as ChartData[];
    },
  });
};

// Get available years from chart data
export const useChartYears = () => {
  return useQuery({
    queryKey: ['chartYears'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('chart_data')
        .select('year')
        .order('year', { ascending: false });

      if (error) throw error;

      // Get unique years
      const years = [...new Set((data || []).map(r => r.year))];
      return years;
    },
  });
};

// Fetch top tickers by trade count (uses database view for performance)
export const useTopTickers = (limit = 5) => {
  return useQuery({
    queryKey: ['topTickers', limit],
    queryFn: async () => {
      // Query from pre-aggregated view instead of all disclosures
      const { data, error } = await supabase
        .from('top_tickers')
        .select('ticker, name, trade_count, total_volume')
        .limit(limit);

      if (error) throw error;

      return (data || []).map(d => ({
        ticker: d.ticker,
        name: d.name || d.ticker,
        count: d.trade_count,
        totalVolume: d.total_volume,
      }));
    },
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });
};

// Fixed ID for singleton dashboard stats row
const DASHBOARD_STATS_ID = '00000000-0000-0000-0000-000000000001';

// Fetch dashboard stats
export const useDashboardStats = () => {
  return useQuery({
    queryKey: ['dashboardStats'],
    queryFn: async () => {
      // First try to get by fixed ID
      let { data, error } = await supabase
        .from('dashboard_stats')
        .select('*')
        .eq('id', DASHBOARD_STATS_ID)
        .maybeSingle();

      // Fallback: get the most recent row if fixed ID doesn't exist
      if (!data) {
        const result = await supabase
          .from('dashboard_stats')
          .select('*')
          .order('updated_at', { ascending: false })
          .limit(1)
          .maybeSingle();
        data = result.data;
        error = result.error;
      }

      if (error) throw error;
      return data as DashboardStats;
    },
  });
};
