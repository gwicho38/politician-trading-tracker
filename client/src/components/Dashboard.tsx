import { TrendingUp, Users, FileText, DollarSign, Loader2 } from 'lucide-react';
import StatsCard from '@/components/StatsCard';
import TradeChart from '@/components/TradeChart';
import VolumeChart from '@/components/VolumeChart';
import TopTraders from '@/components/TopTraders';
import TopTickers from '@/components/TopTickers';
import LandingTradesTable from '@/components/LandingTradesTable';
import { useDashboardStats } from '@/hooks/useSupabaseData';
import { formatCurrency } from '@/lib/mockData';

interface DashboardProps {
  jurisdictionId?: string;
  initialTickerSearch?: string;
  onTickerSearchClear?: () => void;
}

const Dashboard = ({ jurisdictionId, initialTickerSearch, onTickerSearchClear }: DashboardProps) => {
  const { data: stats, isLoading } = useDashboardStats();

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
              change={`Tracked across ${stats?.jurisdictions_tracked || 0} jurisdictions`}
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

      {/* Main Trades Table */}
      <LandingTradesTable
        initialSearchQuery={initialTickerSearch}
        onSearchClear={onTickerSearchClear}
      />

      {/* Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        <TradeChart />
        <VolumeChart />
      </div>

      {/* Top Traders & Top Tickers */}
      <div className="grid gap-6 lg:grid-cols-2">
        <TopTraders />
        <TopTickers />
      </div>
    </div>
  );
};

export default Dashboard;
