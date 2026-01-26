import { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Loader2 } from 'lucide-react';
import { useChartData, useChartYears, ChartTimeRange } from '@/hooks/useSupabaseData';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { MonthDetailModal } from '@/components/detail-modals';

interface ChartDataPoint {
  month: string;
  monthNum: number;
  year: number;
  buys: number;
  sells: number;
  volume: number;
}

// Custom tooltip component for better dark mode readability
const CustomChartTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload as ChartDataPoint;
    return (
      <div className="bg-popover/95 backdrop-blur-sm border border-border rounded-lg p-3 shadow-lg">
        <p className="text-sm font-medium text-foreground mb-2">{label}</p>
        <div className="space-y-1 text-xs">
          <div className="flex justify-between gap-4">
            <span className="text-muted-foreground">Buys:</span>
            <span className="font-medium text-success">{data.buys}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-muted-foreground">Sells:</span>
            <span className="font-medium text-destructive">{data.sells}</span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

const TradeChart = () => {
  const [timeRange, setTimeRange] = useState<ChartTimeRange>('trailing12');
  const { data: chartData, isLoading } = useChartData(timeRange);
  const { data: availableYears } = useChartYears();

  // State for month detail modal
  const [selectedMonth, setSelectedMonth] = useState<{ month: number; year: number } | null>(null);

  const handleTimeRangeChange = (value: string) => {
    if (value === 'trailing12' || value === 'trailing24' || value === 'all') {
      setTimeRange(value);
    } else {
      setTimeRange(parseInt(value, 10));
    }
  };

  const handleBarClick = (data: ChartDataPoint) => {
    if (data && data.monthNum && data.year) {
      setSelectedMonth({ month: data.monthNum, year: data.year });
    }
  };

  return (
    <>
      <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-4 sm:p-6">
        <div className="mb-4 sm:mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-base sm:text-lg font-semibold text-foreground">Trading Activity</h3>
            <p className="text-xs sm:text-sm text-muted-foreground">
              Buy vs Sell transactions over time
              <span className="text-xs ml-2 text-primary/70 hidden sm:inline">• Click bars for details</span>
            </p>
          </div>
          <div className="flex items-center gap-2 sm:gap-4">
            <Select
              value={typeof timeRange === 'number' ? String(timeRange) : timeRange}
              onValueChange={handleTimeRangeChange}
            >
              <SelectTrigger className="w-[120px] sm:w-[140px] h-8 text-xs">
                <SelectValue placeholder="Time range" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="trailing12">Last 12 months</SelectItem>
                <SelectItem value="trailing24">Last 24 months</SelectItem>
                <SelectItem value="all">All time</SelectItem>
                {availableYears?.map((year) => (
                  <SelectItem key={year} value={String(year)}>
                    {year}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="flex items-center gap-2 sm:gap-3 text-sm">
              <div className="flex items-center gap-1">
                <div className="h-2 w-2 sm:h-2.5 sm:w-2.5 rounded-full bg-success" />
                <span className="text-muted-foreground text-xs">Buys</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="h-2 w-2 sm:h-2.5 sm:w-2.5 rounded-full bg-destructive" />
                <span className="text-muted-foreground text-xs">Sells</span>
              </div>
            </div>
          </div>
        </div>

        <div className="h-56 sm:h-72">
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : chartData && chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                barGap={4}
                onClick={(data) => {
                  if (data && data.activePayload && data.activePayload[0]) {
                    handleBarClick(data.activePayload[0].payload as ChartDataPoint);
                  }
                }}
                style={{ cursor: 'pointer' }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="hsl(var(--border))"
                  vertical={false}
                />
                <XAxis
                  dataKey="month"
                  stroke="hsl(var(--muted-foreground))"
                  tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }}
                  axisLine={{ stroke: 'hsl(var(--border))' }}
                  interval="preserveStartEnd"
                />
                <YAxis
                  stroke="hsl(var(--muted-foreground))"
                  tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }}
                  axisLine={{ stroke: 'hsl(var(--border))' }}
                  width={40}
                />
                <Tooltip
                  content={<CustomChartTooltip />}
                  cursor={{ fill: 'hsl(var(--muted)/0.2)' }}
                />
                <Bar
                  dataKey="buys"
                  fill="hsl(var(--success))"
                  radius={[4, 4, 0, 0]}
                  name="Buys"
                />
                <Bar
                  dataKey="sells"
                  fill="hsl(var(--destructive))"
                  radius={[4, 4, 0, 0]}
                  name="Sells"
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
              No chart data available
            </div>
          )}
        </div>

        {chartData && chartData.length > 0 && (
          <p className="text-xs text-muted-foreground text-center mt-2">
            Click on a bar to see detailed trades for that month
          </p>
        )}
      </div>

      <MonthDetailModal
        month={selectedMonth?.month ?? null}
        year={selectedMonth?.year ?? null}
        open={!!selectedMonth}
        onOpenChange={(open) => !open && setSelectedMonth(null)}
      />
    </>
  );
};

export default TradeChart;
