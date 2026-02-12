import { useQuery } from '@tanstack/react-query';
import { supabasePublic as supabase } from '@/integrations/supabase/client';

export interface SearchResult {
  type: 'politician' | 'ticker';
  id: string;
  label: string;
  sublabel?: string;
  meta?: {
    party?: string;
    chamber?: string;
    tradeCount?: number;
  };
}

export const useGlobalSearch = (query: string) => {
  return useQuery({
    queryKey: ['globalSearch', query],
    queryFn: async (): Promise<SearchResult[]> => {
      if (!query || query.length < 2) return [];

      const results: SearchResult[] = [];
      const searchTerm = query.trim();

      // Search politicians by name (partial match)
      const { data: politicians } = await supabase
        .from('politicians')
        .select('id, first_name, last_name, full_name, party, role, total_trades')
        .or(`full_name.ilike.%${searchTerm}%,first_name.ilike.%${searchTerm}%,last_name.ilike.%${searchTerm}%`)
        .order('total_trades', { ascending: false })
        .limit(5);

      if (politicians) {
        politicians.forEach(p => {
          results.push({
            type: 'politician',
            id: p.id,
            label: p.full_name || `${p.first_name} ${p.last_name}`,
            sublabel: p.role || 'Member',
            meta: {
              party: p.party,
              chamber: p.role,
              tradeCount: p.total_trades,
            },
          });
        });
      }

      // Search tickers - use the top_tickers view for better performance
      const { data: tickers } = await supabase
        .from('top_tickers')
        .select('ticker, name, trade_count')
        .ilike('ticker', `%${searchTerm}%`)
        .order('trade_count', { ascending: false })
        .limit(5);

      if (tickers) {
        tickers.forEach(t => {
          results.push({
            type: 'ticker',
            id: t.ticker,
            label: t.ticker,
            sublabel: t.name || undefined,
            meta: {
              tradeCount: t.trade_count,
            },
          });
        });
      }

      // If no ticker matches from view, search trading_disclosures directly
      if (!tickers || tickers.length === 0) {
        const { data: disclosureTickers } = await supabase
          .from('trading_disclosures')
          .select('asset_ticker, asset_name')
          .ilike('asset_ticker', `%${searchTerm}%`)
          .eq('status', 'active')
          .limit(10);

        if (disclosureTickers) {
          // Deduplicate by ticker
          const seen = new Set<string>();
          disclosureTickers.forEach(d => {
            if (d.asset_ticker && !seen.has(d.asset_ticker.toUpperCase())) {
              seen.add(d.asset_ticker.toUpperCase());
              results.push({
                type: 'ticker',
                id: d.asset_ticker.toUpperCase(),
                label: d.asset_ticker.toUpperCase(),
                sublabel: d.asset_name || undefined,
              });
            }
          });
        }
      }

      return results;
    },
    enabled: query.length >= 2,
    staleTime: 30 * 1000, // Cache for 30 seconds
  });
};
