import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Loader2, RefreshCw, TrendingUp, TrendingDown, Package } from 'lucide-react';
import { useAlpacaPositions, calculatePositionMetrics } from '@/hooks/useAlpacaPositions';
import { cn } from '@/lib/utils';

interface PositionsTableProps {
  tradingMode: 'paper' | 'live';
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatPercent(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${(value * 100).toFixed(2)}%`;
}

export function PositionsTable({ tradingMode }: PositionsTableProps) {
  const { data: positions, isLoading, error, refetch, isRefetching } = useAlpacaPositions(tradingMode);
  const metrics = positions ? calculatePositionMetrics(positions) : null;

  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6 flex items-center justify-center h-48">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center py-8 text-destructive">
            <p>Failed to load positions</p>
            <Button variant="outline" onClick={() => refetch()} className="mt-4">
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!positions || positions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Positions</CardTitle>
          <CardDescription>Your current holdings</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <Package className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No open positions</p>
            <p className="text-sm mt-2">Start trading to build your portfolio</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div>
          <CardTitle>Positions ({positions.length})</CardTitle>
          <CardDescription>
            {metrics && (
              <span className="flex items-center gap-4 mt-1">
                <span>Total Value: {formatCurrency(metrics.totalValue)}</span>
                <span className={cn(
                  metrics.totalPnL >= 0 ? "text-green-600" : "text-red-600"
                )}>
                  P&L: {formatCurrency(metrics.totalPnL)}
                </span>
              </span>
            )}
          </CardDescription>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => refetch()}
          disabled={isRefetching}
        >
          <RefreshCw className={cn("h-4 w-4", isRefetching && "animate-spin")} />
        </Button>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b text-left text-sm text-muted-foreground">
                <th className="pb-2 font-medium">Symbol</th>
                <th className="pb-2 font-medium text-right">Qty</th>
                <th className="pb-2 font-medium text-right">Avg Price</th>
                <th className="pb-2 font-medium text-right">Current</th>
                <th className="pb-2 font-medium text-right">Market Value</th>
                <th className="pb-2 font-medium text-right">P&L</th>
                <th className="pb-2 font-medium text-right">P&L %</th>
                <th className="pb-2 font-medium text-right">Today</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((position) => (
                <tr key={position.asset_id} className="border-b hover:bg-muted/50">
                  <td className="py-3">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{position.symbol}</span>
                      <Badge variant="outline" className="text-xs">
                        {position.side}
                      </Badge>
                    </div>
                  </td>
                  <td className="py-3 text-right font-mono">
                    {position.qty.toLocaleString()}
                  </td>
                  <td className="py-3 text-right font-mono">
                    {formatCurrency(position.avg_entry_price)}
                  </td>
                  <td className="py-3 text-right font-mono">
                    {formatCurrency(position.current_price)}
                  </td>
                  <td className="py-3 text-right font-mono">
                    {formatCurrency(position.market_value)}
                  </td>
                  <td className={cn(
                    "py-3 text-right font-mono",
                    position.unrealized_pl >= 0 ? "text-green-600" : "text-red-600"
                  )}>
                    <div className="flex items-center justify-end gap-1">
                      {position.unrealized_pl >= 0 ? (
                        <TrendingUp className="h-3 w-3" />
                      ) : (
                        <TrendingDown className="h-3 w-3" />
                      )}
                      {formatCurrency(position.unrealized_pl)}
                    </div>
                  </td>
                  <td className={cn(
                    "py-3 text-right font-mono text-sm",
                    position.unrealized_plpc >= 0 ? "text-green-600" : "text-red-600"
                  )}>
                    {formatPercent(position.unrealized_plpc)}
                  </td>
                  <td className={cn(
                    "py-3 text-right font-mono text-sm",
                    position.unrealized_intraday_pl >= 0 ? "text-green-600" : "text-red-600"
                  )}>
                    {formatCurrency(position.unrealized_intraday_pl)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
