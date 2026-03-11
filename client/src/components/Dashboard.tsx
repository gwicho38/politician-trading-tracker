import { useState, useEffect, useCallback } from 'react';
import { TrendingUp, Users, FileText, DollarSign, Loader2, ArrowUpRight, ArrowDownRight, Wallet } from 'lucide-react';
import StatsCard from '@/components/StatsCard';
import TradeChart from '@/components/TradeChart';
import VolumeChart from '@/components/VolumeChart';
import TopTraders from '@/components/TopTraders';
import TopTickers from '@/components/TopTickers';
import LandingTradesTable from '@/components/LandingTradesTable';
import { useDashboardStats, useJurisdictionStats, useChartData } from '@/hooks/useSupabaseData';
import { formatCurrency } from '@/lib/mockData';
import { Badge } from '@/components/ui/badge';
import { ErrorBoundary } from '@/components/ErrorBoundary';

interface DashboardProps {
  initialTickerSearch?: string;
  onTickerSearchClear?: () => void;
  initialJurisdiction?: string;
}

const Dashboard = ({ initialTickerSearch, onTickerSearchClear, initialJurisdiction }: DashboardProps) => {
  const { data: globalStats, isLoading: globalLoading } = useDashboardStats();
  const { data: jurisdictionStats, isLoading: jurisdictionLoading } = useJurisdictionStats(initialJurisdiction);
  const { data: chartData } = useChartData('all');

  // total_trades is lifted from LandingTradesTable (reuses the working filtered count)
  const [jurisdictionTradeCount, setJurisdictionTradeCount] = useState<number | null>(null);

  // Reset count when jurisdiction changes to avoid showing stale data
  useEffect(() => {
    setJurisdictionTradeCount(null);
  }, [initialJurisdiction]);

  const handleTotalChange = useCallback((total: number) => {
    setJurisdictionTradeCount(total);
  }, []);

  // Use jurisdiction-specific stats when a jurisdiction is active, else global.
  // Merge in the lifted total_trades count (the RPC total_trades is null intentionally).
  const stats = initialJurisdiction
    ? { ...(jurisdictionStats ?? {}), total_trades: jurisdictionTradeCount ?? 0 }
    : globalStats;
  const isLoading = initialJurisdiction ? jurisdictionLoading : globalLoading;

  // Calculate transaction type totals from chart data
  const transactionTotals = chartData?.reduce(
    (acc, month) => ({
      buys: acc.buys + (month.buys || 0),
      sells: acc.sells + (month.sells || 0),
    }),
    { buys: 0, sells: 0 }
  ) || { buys: 0, sells: 0 };

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-1 sm:gap-2">
        <h2 className="text-xl sm:text-2xl font-bold text-foreground">
          Politician Stock Trading Tracker
        </h2>
        <p className="text-sm sm:text-base text-muted-foreground">
          A free public resource tracking politician stock trades and financial disclosures
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-3 sm:gap-4 grid-cols-2 lg:grid-cols-4">
        {isLoading ? (
          <>
            {[...Array(4)].map((_, i) => (
              <div key={i} className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-4 sm:p-6 flex items-center justify-center h-24 sm:h-32">
                <Loader2 className="h-5 w-5 sm:h-6 sm:w-6 animate-spin text-muted-foreground" />
              </div>
            ))}
          </>
        ) : (
          <>
            <StatsCard
              title="Total Trades"
              value={stats?.total_trades?.toLocaleString() || '0'}
              change={stats?.average_trade_size ? `Avg ${formatCurrency(stats.average_trade_size)} per trade` : 'Filtered trades'}
              changeType="neutral"
              icon={TrendingUp}
              delay={0}
            />
            <StatsCard
              title="Total Volume"
              value={stats?.total_volume != null ? formatCurrency(stats.total_volume) : '—'}
              change="Disclosed trading value"
              changeType="neutral"
              icon={DollarSign}
              delay={100}
            />
            <StatsCard
              title="Active Politicians"
              value={(stats?.active_politicians || 0).toString()}
              change="Tracked politicians"
              changeType="neutral"
              icon={Users}
              delay={200}
            />
            <StatsCard
              title="Recent Filings"
              value={(stats?.recent_filings || 0).toString()}
              change="Last 7 days"
              changeType="neutral"
              icon={FileText}
              delay={300}
            />
          </>
        )}
      </div>

      {/* Transaction Type Summary — hidden on jurisdiction views (chart data is global) */}
      {!initialJurisdiction && (transactionTotals.buys > 0 || transactionTotals.sells > 0) ? (
        <div className="flex items-center gap-2 sm:gap-4 flex-wrap">
          <span className="text-xs sm:text-sm text-muted-foreground">Transaction breakdown:</span>
          <Badge variant="outline" className="gap-1.5 bg-success/10 text-success border-success/30">
            <ArrowUpRight className="h-3 w-3" />
            {transactionTotals.buys.toLocaleString()} Buys
          </Badge>
          <Badge variant="outline" className="gap-1.5 bg-destructive/10 text-destructive border-destructive/30">
            <ArrowDownRight className="h-3 w-3" />
            {transactionTotals.sells.toLocaleString()} Sells
          </Badge>
          <Badge variant="outline" className="gap-1.5 bg-primary/10 text-primary border-primary/30">
            <Wallet className="h-3 w-3" />
            {((stats?.total_trades || 0) - transactionTotals.buys - transactionTotals.sells).toLocaleString()} Other
          </Badge>
        </div>
      ) : null}

      {/* Main Trades Table */}
      <ErrorBoundary name="Trades Table" minimal>
        <LandingTradesTable
          initialSearchQuery={initialTickerSearch}
          onSearchClear={onTickerSearchClear}
          initialJurisdiction={initialJurisdiction}
          onTotalChange={initialJurisdiction ? handleTotalChange : undefined}
        />
      </ErrorBoundary>

      {/* Charts Row — chart_data view has no jurisdiction breakdown, always global */}
      <div className="grid gap-4 sm:gap-6 lg:grid-cols-2">
        <ErrorBoundary name="Trade Chart" minimal>
          <TradeChart globalNote={initialJurisdiction ? 'Top financial activity' : undefined} />
        </ErrorBoundary>
        <ErrorBoundary name="Volume Chart" minimal>
          <VolumeChart globalNote={initialJurisdiction ? 'Top financial activity' : undefined} />
        </ErrorBoundary>
      </div>

      {/* Top Traders & Top Tickers */}
      <div className="grid gap-4 sm:gap-6 md:grid-cols-2">
        <ErrorBoundary name="Top Traders" minimal>
          <TopTraders jurisdiction={initialJurisdiction} />
        </ErrorBoundary>
        <ErrorBoundary name="Top Tickers" minimal>
          {/* top_tickers view is global — label it clearly when in a jurisdiction view */}
          <TopTickers globalNote={initialJurisdiction ? 'Top financial activity' : undefined} />
        </ErrorBoundary>
      </div>
    </div>
  );
};

export default Dashboard;
