import { TrendingUp, TrendingDown, DollarSign, Target, Activity, Award } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useReferencePortfolioState } from '@/hooks/useReferencePortfolio';

interface MetricCardProps {
  label: string;
  value: string | number;
  subValue?: string;
  icon: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  isLoading?: boolean;
}

function MetricCard({ label, value, subValue, icon, trend, isLoading }: MetricCardProps) {
  if (isLoading) {
    return (
      <Card className="bg-card/60 backdrop-blur-xl border-border/50">
        <CardContent className="p-4">
          <div className="flex items-start justify-between">
            <div className="space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-7 w-32" />
              <Skeleton className="h-3 w-20" />
            </div>
            <Skeleton className="h-10 w-10 rounded-lg" />
          </div>
        </CardContent>
      </Card>
    );
  }

  const trendColor = trend === 'up' ? 'text-success' : trend === 'down' ? 'text-destructive' : 'text-muted-foreground';

  return (
    <Card className="bg-card/60 backdrop-blur-xl border-border/50 hover:border-primary/30 transition-colors">
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground font-medium">{label}</p>
            <p className={`text-2xl font-bold ${trendColor}`}>{value}</p>
            {subValue && <p className="text-xs text-muted-foreground">{subValue}</p>}
          </div>
          <div className="p-2 rounded-lg bg-primary/10">
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
};

const formatPercent = (value: number | null, showSign = true) => {
  if (value === null || value === undefined) return 'N/A';
  const sign = showSign && value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
};

export function MetricsCards() {
  const { data: state, isLoading, error } = useReferencePortfolioState();

  if (error) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {[...Array(6)].map((_, i) => (
          <Card key={i} className="bg-card/60 backdrop-blur-xl border-border/50">
            <CardContent className="p-4 text-center text-muted-foreground text-sm">
              Error loading
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const totalReturnTrend = (state?.total_return_pct || 0) >= 0 ? 'up' : 'down';
  const dayReturnTrend = (state?.day_return_pct || 0) >= 0 ? 'up' : 'down';

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      <MetricCard
        label="Portfolio Value"
        value={formatCurrency(state?.portfolio_value || 100000)}
        subValue={`Cash: ${formatCurrency(state?.cash || 100000)}`}
        icon={<DollarSign className="h-5 w-5 text-primary" />}
        isLoading={isLoading}
      />

      <MetricCard
        label="Total Return"
        value={formatPercent(state?.total_return_pct || 0)}
        subValue={formatCurrency(state?.total_return || 0)}
        icon={totalReturnTrend === 'up' ?
          <TrendingUp className="h-5 w-5 text-success" /> :
          <TrendingDown className="h-5 w-5 text-destructive" />
        }
        trend={totalReturnTrend}
        isLoading={isLoading}
      />

      <MetricCard
        label="Day Return"
        value={formatPercent(state?.day_return_pct || 0)}
        subValue={formatCurrency(state?.day_return || 0)}
        icon={dayReturnTrend === 'up' ?
          <TrendingUp className="h-5 w-5 text-success" /> :
          <TrendingDown className="h-5 w-5 text-destructive" />
        }
        trend={dayReturnTrend}
        isLoading={isLoading}
      />

      <MetricCard
        label="Win Rate"
        value={formatPercent(state?.win_rate || 0, false)}
        subValue={`${state?.winning_trades || 0}W / ${state?.losing_trades || 0}L`}
        icon={<Target className="h-5 w-5 text-primary" />}
        trend={(state?.win_rate || 0) >= 50 ? 'up' : 'down'}
        isLoading={isLoading}
      />

      <MetricCard
        label="Sharpe Ratio"
        value={state?.sharpe_ratio?.toFixed(2) || 'N/A'}
        subValue="Risk-adjusted return"
        icon={<Award className="h-5 w-5 text-primary" />}
        trend={(state?.sharpe_ratio || 0) >= 1 ? 'up' : 'neutral'}
        isLoading={isLoading}
      />

      <MetricCard
        label="Open Positions"
        value={state?.open_positions || 0}
        subValue={`${state?.total_trades || 0} total trades`}
        icon={<Activity className="h-5 w-5 text-primary" />}
        isLoading={isLoading}
      />
    </div>
  );
}
