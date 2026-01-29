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
      <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-4 sm:p-6">
        <div className="mb-4 sm:mb-6 flex items-center justify-between">
          <div>
            <h3 className="text-base sm:text-lg font-semibold text-foreground">Most Traded Tickers</h3>
            <p className="text-xs sm:text-sm text-muted-foreground">By number of transactions</p>
          </div>
          <TrendingUp className="h-4 w-4 sm:h-5 sm:w-5 text-muted-foreground" aria-hidden="true" />
        </div>

        <div className="space-y-2 sm:space-y-3">
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
              <button
                key={ticker.ticker}
                type="button"
                onClick={() => setSelectedTicker(ticker.ticker)}
                className="group w-full flex items-center justify-between rounded-lg p-2 sm:p-3 transition-all duration-200 hover:bg-secondary/50 cursor-pointer gap-2 text-left"
                aria-label={`View details for ${ticker.ticker} - ${ticker.name}, ${ticker.count} trades, ${formatCurrency(ticker.totalVolume)} total volume`}
              >
                <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
                  <div className="flex h-6 w-6 sm:h-8 sm:w-8 items-center justify-center rounded-lg bg-secondary font-mono text-xs sm:text-sm font-bold text-muted-foreground flex-shrink-0" aria-hidden="true">
                    #{index + 1}
                  </div>
                  <div className="min-w-0 flex-1">
                    <span className="font-mono text-sm sm:text-base font-semibold text-foreground group-hover:text-primary transition-colors">
                      {ticker.ticker}
                    </span>
                    <p className="text-xs text-muted-foreground truncate">
                      {ticker.name}
                    </p>
                  </div>
                </div>

                <div className="text-right flex-shrink-0">
                  <p className="font-mono text-xs sm:text-sm font-semibold text-foreground">
                    {ticker.count} trades
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {formatCurrency(ticker.totalVolume)}
                  </p>
                </div>
              </button>
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
