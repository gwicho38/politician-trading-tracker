/**
 * useTickerSearch Hook
 * Searches for tickers for autocomplete functionality
 */

import { useQuery } from '@tanstack/react-query';
import { supabasePublic as supabase } from '@/integrations/supabase/client';

export interface TickerResult {
  ticker: string;
  name: string | null;
  tradeCount: number;
}

export const useTickerSearch = (query: string, enabled: boolean = true) => {
  return useQuery({
    queryKey: ['tickerSearch', query],
    queryFn: async (): Promise<TickerResult[]> => {
      if (!query || query.length < 1) return [];

      const searchTerm = query.trim().toUpperCase();
      const results: TickerResult[] = [];

      // Search tickers using top_tickers view (has trade counts)
      const { data: tickers } = await supabase
        .from('top_tickers')
        .select('ticker, name, trade_count')
        .ilike('ticker', `${searchTerm}%`)  // Prefix match for better UX
        .order('trade_count', { ascending: false })
        .limit(8);

      if (tickers && tickers.length > 0) {
        tickers.forEach((t) => {
          results.push({
            ticker: t.ticker,
            name: t.name,
            tradeCount: t.trade_count,
          });
        });
      }

      // If no results from top_tickers, try trading_disclosures
      if (results.length === 0) {
        const { data: disclosureTickers } = await supabase
          .from('trading_disclosures')
          .select('asset_ticker, asset_name')
          .ilike('asset_ticker', `${searchTerm}%`)
          .eq('status', 'active')
          .limit(20);

        if (disclosureTickers) {
          const seen = new Set<string>();
          disclosureTickers.forEach((d) => {
            if (d.asset_ticker && !seen.has(d.asset_ticker.toUpperCase())) {
              seen.add(d.asset_ticker.toUpperCase());
              results.push({
                ticker: d.asset_ticker.toUpperCase(),
                name: d.asset_name,
                tradeCount: 0,
              });
            }
          });
        }
      }

      return results.slice(0, 8);
    },
    enabled: enabled && query.length >= 1,
    staleTime: 60 * 1000, // Cache for 1 minute
  });
};

export default useTickerSearch;
