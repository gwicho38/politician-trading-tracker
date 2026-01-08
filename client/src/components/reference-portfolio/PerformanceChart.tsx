import { useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Loader2 } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  useReferencePortfolioPerformance,
  Timeframe,
  ReferencePortfolioSnapshot,
} from '@/hooks/useReferencePortfolio';

interface ChartDataPoint {
  date: string;
  portfolioValue: number;
  benchmarkValue: number | null;
  dayReturn: number | null;
  cumulativeReturnPct: number | null;
}

const TIMEFRAME_OPTIONS: { value: Timeframe; label: string }[] = [
  { value: '1d', label: '1 Day' },
  { value: '1w', label: '1 Week' },
  { value: '1m', label: '1 Month' },
  { value: '3m', label: '3 Months' },
  { value: 'ytd', label: 'YTD' },
  { value: '1y', label: '1 Year' },
];

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
};

const formatPercent = (value: number | null) => {
  if (value === null) return 'N/A';
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload as ChartDataPoint;
    return (
      <div className="bg-popover/95 backdrop-blur-sm border border-border rounded-lg p-3 shadow-lg">
        <p className="text-sm font-medium text-foreground mb-2">{data.date}</p>
        <div className="space-y-1 text-xs">
          <div className="flex justify-between gap-4">
            <span className="text-muted-foreground">Portfolio:</span>
            <span className="font-medium text-primary">{formatCurrency(data.portfolioValue)}</span>
          </div>
          {data.benchmarkValue && (
            <div className="flex justify-between gap-4">
              <span className="text-muted-foreground">S&P 500:</span>
              <span className="font-medium text-muted-foreground">${data.benchmarkValue.toFixed(2)}</span>
            </div>
          )}
          <div className="flex justify-between gap-4">
            <span className="text-muted-foreground">Return:</span>
            <span className={`font-medium ${(data.cumulativeReturnPct || 0) >= 0 ? 'text-success' : 'text-destructive'}`}>
              {formatPercent(data.cumulativeReturnPct)}
            </span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

export function PerformanceChart() {
  const [timeframe, setTimeframe] = useState<Timeframe>('1m');
  const { data: snapshots, isLoading, error } = useReferencePortfolioPerformance(timeframe);

  // Transform snapshots to chart data
  const chartData: ChartDataPoint[] = (snapshots || []).map((snapshot: ReferencePortfolioSnapshot) => ({
    date: new Date(snapshot.snapshot_date).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    }),
    portfolioValue: snapshot.portfolio_value,
    benchmarkValue: snapshot.benchmark_value,
    dayReturn: snapshot.day_return,
    cumulativeReturnPct: snapshot.cumulative_return_pct,
  }));

  // Calculate min/max for Y-axis domain
  const values = chartData.map((d) => d.portfolioValue);
  const minValue = values.length > 0 ? Math.min(...values) * 0.98 : 95000;
  const maxValue = values.length > 0 ? Math.max(...values) * 1.02 : 105000;

  return (
    <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-foreground">Portfolio Performance</h3>
          <p className="text-sm text-muted-foreground">
            Reference strategy vs. S&P 500 benchmark
          </p>
        </div>
        <Select value={timeframe} onValueChange={(v) => setTimeframe(v as Timeframe)}>
          <SelectTrigger className="w-[120px] h-8 text-xs">
            <SelectValue placeholder="Timeframe" />
          </SelectTrigger>
          <SelectContent>
            {TIMEFRAME_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="h-72">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            Failed to load performance data
          </div>
        ) : chartData.length === 0 ? (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            No performance data available yet
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="portfolioGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border/50" />
              <XAxis
                dataKey="date"
                tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                domain={[minValue, maxValue]}
                tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
                tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                tickLine={false}
                axisLine={false}
                width={50}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ paddingTop: '10px' }}
                formatter={(value) => <span className="text-xs text-muted-foreground">{value}</span>}
              />
              <Area
                type="monotone"
                dataKey="portfolioValue"
                name="Portfolio Value"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                fill="url(#portfolioGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Summary stats below chart */}
      {chartData.length > 0 && (
        <div className="mt-4 pt-4 border-t border-border/50 grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-xs text-muted-foreground">Current Value</p>
            <p className="text-sm font-semibold text-foreground">
              {formatCurrency(chartData[chartData.length - 1]?.portfolioValue || 0)}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Period Return</p>
            <p className={`text-sm font-semibold ${(chartData[chartData.length - 1]?.cumulativeReturnPct ?? 0) >= 0 ? 'text-success' : 'text-destructive'}`}>
              {formatPercent(chartData[chartData.length - 1]?.cumulativeReturnPct ?? 0)}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Data Points</p>
            <p className="text-sm font-semibold text-foreground">{chartData.length}</p>
          </div>
        </div>
      )}
    </div>
  );
}
