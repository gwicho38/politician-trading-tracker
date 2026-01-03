import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Loader2, RefreshCw, TrendingUp, TrendingDown, Wallet, DollarSign, PiggyBank, AlertTriangle } from 'lucide-react';
import { useAlpacaAccount, calculateDailyPnL } from '@/hooks/useAlpacaAccount';
import { cn } from '@/lib/utils';

interface AccountDashboardProps {
  tradingMode: 'paper' | 'live';
}

function formatCurrency(value: number | undefined | null): string {
  // Handle NaN, undefined, null gracefully
  const safeValue = typeof value === 'number' && !isNaN(value) ? value : 0;
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(safeValue);
}

function formatPercent(value: number | undefined | null): string {
  // Handle NaN, undefined, null gracefully
  const safeValue = typeof value === 'number' && !isNaN(value) ? value : 0;
  const sign = safeValue >= 0 ? '+' : '';
  return `${sign}${safeValue.toFixed(2)}%`;
}

export function AccountDashboard({ tradingMode }: AccountDashboardProps) {
  const { data: account, isLoading, error, refetch, isRefetching } = useAlpacaAccount(tradingMode);
  const dailyPnL = calculateDailyPnL(account);

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
            <AlertTriangle className="h-12 w-12 mx-auto mb-4" />
            <p>Failed to load account data</p>
            <p className="text-sm text-muted-foreground mt-2">{error.message}</p>
            <Button variant="outline" onClick={() => refetch()} className="mt-4">
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!account) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center py-8 text-muted-foreground">
            <Wallet className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>Connect your Alpaca account to view your portfolio</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div>
          <CardTitle className="flex items-center gap-2">
            Account Overview
            <Badge variant={tradingMode === 'paper' ? 'secondary' : 'destructive'}>
              {tradingMode === 'paper' ? 'Paper' : 'Live'}
            </Badge>
          </CardTitle>
          <CardDescription>
            {account.status === 'ACTIVE' ? 'Account is active and ready to trade' : `Status: ${account.status}`}
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
        {/* Warning badges */}
        {(account.trading_blocked || account.account_blocked) && (
          <div className="mb-4 flex gap-2 flex-wrap">
            {account.trading_blocked && (
              <Badge variant="destructive">Trading Blocked</Badge>
            )}
            {account.account_blocked && (
              <Badge variant="destructive">Account Blocked</Badge>
            )}
            {account.pattern_day_trader && (
              <Badge variant="outline">Pattern Day Trader</Badge>
            )}
          </div>
        )}

        {/* Main metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Portfolio Value */}
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground flex items-center gap-1">
              <Wallet className="h-3 w-3" />
              Portfolio Value
            </p>
            <p className="text-2xl font-bold">{formatCurrency(account.portfolio_value)}</p>
          </div>

          {/* Daily P&L */}
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground flex items-center gap-1">
              {dailyPnL.value >= 0 ? (
                <TrendingUp className="h-3 w-3 text-green-600" />
              ) : (
                <TrendingDown className="h-3 w-3 text-red-600" />
              )}
              Today's P&L
            </p>
            <p className={cn(
              "text-2xl font-bold",
              dailyPnL.value >= 0 ? "text-green-600" : "text-red-600"
            )}>
              {formatCurrency(dailyPnL.value)}
            </p>
            <p className={cn(
              "text-xs",
              dailyPnL.value >= 0 ? "text-green-600" : "text-red-600"
            )}>
              {formatPercent(dailyPnL.percent)}
            </p>
          </div>

          {/* Cash */}
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground flex items-center gap-1">
              <DollarSign className="h-3 w-3" />
              Cash
            </p>
            <p className="text-2xl font-bold">{formatCurrency(account.cash)}</p>
          </div>

          {/* Buying Power */}
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground flex items-center gap-1">
              <PiggyBank className="h-3 w-3" />
              Buying Power
            </p>
            <p className="text-2xl font-bold">{formatCurrency(account.buying_power)}</p>
          </div>
        </div>

        {/* Secondary metrics */}
        <div className="mt-4 pt-4 border-t grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">Equity</p>
            <p className="font-medium">{formatCurrency(account.equity)}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Long Market Value</p>
            <p className="font-medium">{formatCurrency(account.long_market_value)}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Short Market Value</p>
            <p className="font-medium">{formatCurrency(account.short_market_value)}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Last Close Equity</p>
            <p className="font-medium">{formatCurrency(account.last_equity)}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
