import { TrendingUp, Users, FileText, DollarSign, Loader2, ArrowUpRight, ArrowDownRight, Wallet } from 'lucide-react';
import StatsCard from '@/components/StatsCard';
import TradeChart from '@/components/TradeChart';
import VolumeChart from '@/components/VolumeChart';
import TopTraders from '@/components/TopTraders';
import TopTickers from '@/components/TopTickers';
import PartyBreakdown from '@/components/PartyBreakdown';
import LandingTradesTable from '@/components/LandingTradesTable';
import { useDashboardStats, useChartData } from '@/hooks/useSupabaseData';
import { formatCurrency } from '@/lib/mockData';
import { Badge } from '@/components/ui/badge';
import { ErrorBoundary } from '@/components/ErrorBoundary';

interface DashboardProps {
  initialTickerSearch?: string;
  onTickerSearchClear?: () => void;
}

const Dashboard = ({ initialTickerSearch, onTickerSearchClear }: DashboardProps) => {
  const { data: stats, isLoading } = useDashboardStats();
  const { data: chartData } = useChartData('all');

  // Calculate transaction type totals from chart data
  const transactionTotals = chartData?.reduce(
    (acc, month) => ({
      buys: acc.buys + (month.buys || 0),
      sells: acc.sells + (month.sells || 0),
    }),
    { buys: 0, sells: 0 }
  ) || { buys: 0, sells: 0 };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2">
        <h2 className="text-2xl font-bold text-foreground">
          Politician Stock Trading Tracker
        </h2>
        <p className="text-muted-foreground">
          A free public resource tracking congressional stock trades and disclosures
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {isLoading ? (
          <>
            {[...Array(4)].map((_, i) => (
              <div key={i} className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-6 flex items-center justify-center h-32">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ))}
          </>
        ) : (
          <>
            <StatsCard
              title="Total Trades"
              value={stats?.total_trades?.toLocaleString() || '0'}
              change={`Avg ${formatCurrency(stats?.average_trade_size || 0)} per trade`}
              changeType="neutral"
              icon={TrendingUp}
              delay={0}
            />
            <StatsCard
              title="Total Volume"
              value={formatCurrency(stats?.total_volume || 0)}
              change="Disclosed trading value"
              changeType="neutral"
              icon={DollarSign}
              delay={100}
            />
            <StatsCard
              title="Active Politicians"
              value={(stats?.active_politicians || 0).toString()}
              change="US Congress members"
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

      {/* Transaction Type Summary */}
      {transactionTotals.buys > 0 || transactionTotals.sells > 0 ? (
        <div className="flex items-center gap-4 flex-wrap">
          <span className="text-sm text-muted-foreground">Transaction breakdown:</span>
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
        />
      </ErrorBoundary>

      {/* Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        <ErrorBoundary name="Trade Chart" minimal>
          <TradeChart />
        </ErrorBoundary>
        <ErrorBoundary name="Volume Chart" minimal>
          <VolumeChart />
        </ErrorBoundary>
      </div>

      {/* Top Traders, Top Tickers & Party Breakdown */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <ErrorBoundary name="Top Traders" minimal>
          <TopTraders />
        </ErrorBoundary>
        <ErrorBoundary name="Top Tickers" minimal>
          <TopTickers />
        </ErrorBoundary>
        <ErrorBoundary name="Party Breakdown" minimal>
          <PartyBreakdown />
        </ErrorBoundary>
      </div>
    </div>
  );
};

export default Dashboard;
