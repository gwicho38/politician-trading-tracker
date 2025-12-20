import { useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Loader2 } from 'lucide-react';
import { useChartData, useChartYears, ChartTimeRange } from '@/hooks/useSupabaseData';
import { formatCurrency } from '@/lib/mockData';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const VolumeChart = () => {
  const [timeRange, setTimeRange] = useState<ChartTimeRange>('trailing12');
  const { data: chartData, isLoading } = useChartData(timeRange);
  const { data: availableYears } = useChartYears();

  const handleTimeRangeChange = (value: string) => {
    if (value === 'trailing12' || value === 'trailing24' || value === 'all') {
      setTimeRange(value);
    } else {
      setTimeRange(parseInt(value, 10));
    }
  };

  return (
    <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-foreground">Trade Volume</h3>
          <p className="text-sm text-muted-foreground">Total disclosed trading volume by month</p>
        </div>
        <Select
          value={typeof timeRange === 'number' ? String(timeRange) : timeRange}
          onValueChange={handleTimeRangeChange}
        >
          <SelectTrigger className="w-[140px] h-8 text-xs">
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
      </div>
      
      <div className="h-72">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : chartData && chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="volumeGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid 
                strokeDasharray="3 3" 
                stroke="hsl(var(--border))" 
                vertical={false}
              />
              <XAxis 
                dataKey="month" 
                stroke="hsl(var(--muted-foreground))"
                tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                axisLine={{ stroke: 'hsl(var(--border))' }}
              />
              <YAxis 
                stroke="hsl(var(--muted-foreground))"
                tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                axisLine={{ stroke: 'hsl(var(--border))' }}
                tickFormatter={(value) => formatCurrency(value)}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                }}
                labelStyle={{ color: 'hsl(var(--foreground))' }}
                formatter={(value: number) => [formatCurrency(value), 'Volume']}
              />
              <Area 
                type="monotone" 
                dataKey="volume" 
                stroke="hsl(var(--primary))" 
                strokeWidth={2}
                fill="url(#volumeGradient)" 
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
            No volume data available
          </div>
        )}
      </div>
    </div>
  );
};

export default VolumeChart;
