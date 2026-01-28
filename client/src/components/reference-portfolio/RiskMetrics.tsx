import { AlertTriangle, TrendingDown, BarChart3, Scale } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { useReferencePortfolioState } from '@/hooks/useReferencePortfolio';

interface RiskGaugeProps {
  label: string;
  value: number | null;
  maxValue?: number;
  format?: 'percent' | 'ratio' | 'currency';
  description: string;
  icon: React.ReactNode;
  invertColor?: boolean;
  isLoading?: boolean;
}

function RiskGauge({
  label,
  value,
  maxValue = 100,
  format = 'percent',
  description,
  icon,
  invertColor = false,
  isLoading = false,
}: RiskGaugeProps) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-12" />
        </div>
        <Skeleton className="h-2 w-full" />
        <Skeleton className="h-3 w-32" />
      </div>
    );
  }

  const displayValue = value ?? 0;
  const percentage = Math.min(100, Math.max(0, (Math.abs(displayValue) / maxValue) * 100));

  const formatValue = () => {
    if (value === null || value === undefined) return 'N/A';
    switch (format) {
      case 'percent':
        return `${value.toFixed(2)}%`;
      case 'ratio':
        return value.toFixed(2);
      case 'currency':
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: 'USD',
          minimumFractionDigits: 0,
        }).format(value);
      default:
        return value.toString();
    }
  };

  // Color logic: green is good for most metrics, but for drawdown, lower is better
  const getColorClass = () => {
    if (invertColor) {
      // Lower is better (e.g., drawdown)
      if (percentage <= 25) return 'bg-success';
      if (percentage <= 50) return 'bg-yellow-500';
      return 'bg-destructive';
    }
    // Higher is better (e.g., Sharpe ratio, win rate)
    if (percentage >= 75) return 'bg-success';
    if (percentage >= 50) return 'bg-yellow-500';
    return 'bg-destructive';
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-sm font-medium text-foreground">{label}</span>
        </div>
        <span className="text-sm font-semibold text-foreground">{formatValue()}</span>
      </div>
      <Progress value={percentage} className={`h-2 ${getColorClass()}`} />
      <p className="text-xs text-muted-foreground">{description}</p>
    </div>
  );
}

export function RiskMetrics() {
  const { data: state, isLoading, error } = useReferencePortfolioState();

  if (error) {
    return (
      <Card className="bg-card/60 backdrop-blur-xl border-border/50">
        <CardHeader>
          <CardTitle className="text-lg">Risk Metrics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-muted-foreground text-sm">Failed to load risk metrics</div>
        </CardContent>
      </Card>
    );
  }

  // Calculate concentration metrics
  const positionConcentration = state?.open_positions
    ? Math.min(100, (state.open_positions / (state.config?.max_portfolio_positions || 20)) * 100)
    : 0;

  // Capital utilization: use absolute value to handle negative positions_value bug
  // and clamp to reasonable range (0-100%)
  const capitalUtilization = state?.positions_value && state?.portfolio_value && state.portfolio_value > 0
    ? Math.max(0, Math.min(100, (Math.abs(state.positions_value) / state.portfolio_value) * 100))
    : 0;

  return (
    <Card className="bg-card/60 backdrop-blur-xl border-border/50">
      <CardHeader className="pb-4">
        <CardTitle className="text-lg flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-primary" />
          Risk Metrics
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <RiskGauge
          label="Max Drawdown"
          value={state?.max_drawdown || 0}
          maxValue={30}
          format="percent"
          description="Peak-to-trough decline. Below 10% is excellent."
          icon={<TrendingDown className="h-4 w-4 text-muted-foreground" />}
          invertColor={true}
          isLoading={isLoading}
        />

        <RiskGauge
          label="Current Drawdown"
          value={state?.current_drawdown || 0}
          maxValue={30}
          format="percent"
          description="Current decline from peak portfolio value."
          icon={<TrendingDown className="h-4 w-4 text-muted-foreground" />}
          invertColor={true}
          isLoading={isLoading}
        />

        <RiskGauge
          label="Sharpe Ratio"
          value={state?.sharpe_ratio || 0}
          maxValue={3}
          format="ratio"
          description="Risk-adjusted return. Above 1.0 is good, above 2.0 is excellent."
          icon={<Scale className="h-4 w-4 text-muted-foreground" />}
          invertColor={false}
          isLoading={isLoading}
        />

        <RiskGauge
          label="Win Rate"
          value={state?.win_rate || 0}
          maxValue={100}
          format="percent"
          description="Percentage of profitable trades. Above 50% is profitable."
          icon={<BarChart3 className="h-4 w-4 text-muted-foreground" />}
          invertColor={false}
          isLoading={isLoading}
        />

        <RiskGauge
          label="Position Concentration"
          value={positionConcentration}
          maxValue={100}
          format="percent"
          description={`${state?.open_positions || 0} of ${state?.config?.max_portfolio_positions || 20} max positions used.`}
          icon={<BarChart3 className="h-4 w-4 text-muted-foreground" />}
          invertColor={true}
          isLoading={isLoading}
        />

        <RiskGauge
          label="Capital Utilization"
          value={capitalUtilization}
          maxValue={100}
          format="percent"
          description="Percentage of portfolio invested in positions."
          icon={<BarChart3 className="h-4 w-4 text-muted-foreground" />}
          invertColor={false}
          isLoading={isLoading}
        />

        {/* Additional Info */}
        {state?.profit_factor && (
          <div className="pt-4 border-t border-border/50">
            <div className="flex justify-between items-center text-sm">
              <span className="text-muted-foreground">Profit Factor</span>
              <span className={`font-semibold ${state.profit_factor >= 1 ? 'text-success' : 'text-destructive'}`}>
                {state.profit_factor.toFixed(2)}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Ratio of gross profits to gross losses. Above 1.0 means profitable.
            </p>
          </div>
        )}

        {/* Average Win/Loss */}
        <div className="pt-4 border-t border-border/50 grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-muted-foreground">Avg Win</p>
            <p className="text-sm font-semibold text-success">
              {state?.avg_win ? `$${state.avg_win.toFixed(2)}` : 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Avg Loss</p>
            <p className="text-sm font-semibold text-destructive">
              {state?.avg_loss ? `$${Math.abs(state.avg_loss).toFixed(2)}` : 'N/A'}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
