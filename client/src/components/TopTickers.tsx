import { useState } from 'react';
import { TrendingUp, Loader2 } from 'lucide-react';
import { useTopTickers } from '@/hooks/useSupabaseData';
import { formatCurrency } from '@/lib/mockData';
import { TickerDetailModal } from '@/components/detail-modals';

const TopTickers = () => {
  const { data: tickers, isLoading, error } = useTopTickers(5);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  return (
    <>
      <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-6">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-foreground">Most Traded Tickers</h3>
            <p className="text-sm text-muted-foreground">By number of transactions</p>
          </div>
          <TrendingUp className="h-5 w-5 text-muted-foreground" />
        </div>

        <div className="space-y-3">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : error ? (
            <div className="text-center py-8">
              <p className="text-sm text-destructive font-semibold mb-1">Failed to load data</p>
              <p className="text-xs text-muted-foreground">
                {error instanceof Error ? error.message : 'Please try again later'}
              </p>
            </div>
          ) : !tickers || tickers.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No tickers tracked yet
            </p>
          ) : (
            tickers.map((ticker, index) => (
              <div
                key={ticker.ticker}
                onClick={() => setSelectedTicker(ticker.ticker)}
                className="group flex items-center justify-between rounded-lg p-3 transition-all duration-200 hover:bg-secondary/50 cursor-pointer"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary font-mono text-sm font-bold text-muted-foreground">
                    #{index + 1}
                  </div>
                  <div>
                    <span className="font-mono font-semibold text-foreground group-hover:text-primary transition-colors">
                      {ticker.ticker}
                    </span>
                    <p className="text-xs text-muted-foreground truncate max-w-[180px]">
                      {ticker.name}
                    </p>
                  </div>
                </div>

                <div className="text-right">
                  <p className="font-mono text-sm font-semibold text-foreground">
                    {ticker.count} trades
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {formatCurrency(ticker.totalVolume)}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <TickerDetailModal
        ticker={selectedTicker}
        open={!!selectedTicker}
        onOpenChange={(open) => !open && setSelectedTicker(null)}
      />
    </>
  );
};

export default TopTickers;
