import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Loader2, RefreshCw, TrendingUp, TrendingDown, Package } from 'lucide-react';
import { useAlpacaPositions, calculatePositionMetrics } from '@/hooks/useAlpacaPositions';
import { cn } from '@/lib/utils';
import { QuickTradeDialog } from './QuickTradeDialog';

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

interface Position {
  asset_id: string;
  symbol: string;
  qty: number;
  side: 'long' | 'short';
  avg_entry_price: number;
  current_price: number;
  market_value: number;
  unrealized_pl: number;
  unrealized_plpc: number;
  unrealized_intraday_pl: number;
}

export function PositionsTable({ tradingMode }: PositionsTableProps) {
  const { data: positions, isLoading, error, refetch, isRefetching } = useAlpacaPositions(tradingMode);
  const metrics = positions ? calculatePositionMetrics(positions) : null;

  const [tradeDialogOpen, setTradeDialogOpen] = useState(false);
  const [selectedPosition, setSelectedPosition] = useState<Position | null>(null);
  const [defaultTradeSide, setDefaultTradeSide] = useState<'buy' | 'sell'>('sell');

  const openTradeDialog = (position: Position, side: 'buy' | 'sell') => {
    setSelectedPosition(position);
    setDefaultTradeSide(side);
    setTradeDialogOpen(true);
  };

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
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 px-3 sm:px-6">
        <div className="min-w-0 flex-1">
          <CardTitle className="text-base sm:text-lg">Positions ({positions.length})</CardTitle>
          <CardDescription>
            {metrics && (
              <span className="flex flex-col xs:flex-row xs:items-center gap-1 xs:gap-4 mt-1 text-xs sm:text-sm">
                <span>Total: {formatCurrency(metrics.totalValue)}</span>
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
          className="flex-shrink-0"
        >
          <RefreshCw className={cn("h-4 w-4", isRefetching && "animate-spin")} />
        </Button>
      </CardHeader>
      <CardContent className="px-3 sm:px-6">
        {/* Mobile Card View */}
        <div className="sm:hidden space-y-3">
          {positions.map((position) => (
            <div
              key={position.asset_id}
              className={cn(
                "rounded-lg border p-3",
                position.unrealized_pl >= 0 ? "border-green-500/30 bg-green-500/5" : "border-red-500/30 bg-red-500/5"
              )}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-lg">{position.symbol}</span>
                  <Badge variant="outline" className="text-xs">
                    {position.side}
                  </Badge>
                </div>
                <div className={cn(
                  "flex items-center gap-1 text-sm font-medium",
                  position.unrealized_pl >= 0 ? "text-green-600" : "text-red-600"
                )}>
                  {position.unrealized_pl >= 0 ? (
                    <TrendingUp className="h-3 w-3" />
                  ) : (
                    <TrendingDown className="h-3 w-3" />
                  )}
                  {formatPercent(position.unrealized_plpc)}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-sm mb-3">
                <div>
                  <span className="text-muted-foreground text-xs">Qty</span>
                  <p className="font-mono">{position.qty.toLocaleString()}</p>
                </div>
                <div className="text-right">
                  <span className="text-muted-foreground text-xs">Value</span>
                  <p className="font-mono">{formatCurrency(position.market_value)}</p>
                </div>
                <div>
                  <span className="text-muted-foreground text-xs">Avg Entry</span>
                  <p className="font-mono">{formatCurrency(position.avg_entry_price)}</p>
                </div>
                <div className="text-right">
                  <span className="text-muted-foreground text-xs">Current</span>
                  <p className="font-mono">{formatCurrency(position.current_price)}</p>
                </div>
                <div>
                  <span className="text-muted-foreground text-xs">P&L</span>
                  <p className={cn("font-mono", position.unrealized_pl >= 0 ? "text-green-600" : "text-red-600")}>
                    {formatCurrency(position.unrealized_pl)}
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-muted-foreground text-xs">Today</span>
                  <p className={cn("font-mono", position.unrealized_intraday_pl >= 0 ? "text-green-600" : "text-red-600")}>
                    {formatCurrency(position.unrealized_intraday_pl)}
                  </p>
                </div>
              </div>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1 h-8 text-xs text-green-600 hover:text-green-700 hover:bg-green-50"
                  onClick={() => openTradeDialog(position as Position, 'buy')}
                >
                  <TrendingUp className="h-3 w-3 mr-1" />
                  Buy More
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1 h-8 text-xs text-red-600 hover:text-red-700 hover:bg-red-50"
                  onClick={() => openTradeDialog(position as Position, 'sell')}
                >
                  <TrendingDown className="h-3 w-3 mr-1" />
                  Sell
                </Button>
              </div>
            </div>
          ))}
        </div>

        {/* Desktop Table View */}
        <div className="hidden sm:block overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b text-left text-sm text-muted-foreground">
                <th className="pb-2 font-medium">Symbol</th>
                <th className="pb-2 font-medium text-right">Qty</th>
                <th className="pb-2 font-medium text-right hidden md:table-cell">Avg Price</th>
                <th className="pb-2 font-medium text-right hidden md:table-cell">Current</th>
                <th className="pb-2 font-medium text-right">Market Value</th>
                <th className="pb-2 font-medium text-right">P&L</th>
                <th className="pb-2 font-medium text-right hidden lg:table-cell">P&L %</th>
                <th className="pb-2 font-medium text-right hidden lg:table-cell">Today</th>
                <th className="pb-2 font-medium text-right">Actions</th>
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
                  <td className="py-3 text-right font-mono hidden md:table-cell">
                    {formatCurrency(position.avg_entry_price)}
                  </td>
                  <td className="py-3 text-right font-mono hidden md:table-cell">
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
                    "py-3 text-right font-mono text-sm hidden lg:table-cell",
                    position.unrealized_plpc >= 0 ? "text-green-600" : "text-red-600"
                  )}>
                    {formatPercent(position.unrealized_plpc)}
                  </td>
                  <td className={cn(
                    "py-3 text-right font-mono text-sm hidden lg:table-cell",
                    position.unrealized_intraday_pl >= 0 ? "text-green-600" : "text-red-600"
                  )}>
                    {formatCurrency(position.unrealized_intraday_pl)}
                  </td>
                  <td className="py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 px-2 text-xs text-green-600 hover:text-green-700 hover:bg-green-50"
                        onClick={() => openTradeDialog(position as Position, 'buy')}
                      >
                        <TrendingUp className="h-3 w-3 mr-1" />
                        Buy
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 px-2 text-xs text-red-600 hover:text-red-700 hover:bg-red-50"
                        onClick={() => openTradeDialog(position as Position, 'sell')}
                      >
                        <TrendingDown className="h-3 w-3 mr-1" />
                        Sell
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>

      <QuickTradeDialog
        open={tradeDialogOpen}
        onOpenChange={setTradeDialogOpen}
        position={selectedPosition}
        tradingMode={tradingMode}
        defaultSide={defaultTradeSide}
      />
    </Card>
  );
}
