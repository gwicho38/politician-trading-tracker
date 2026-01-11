import { Activity, Info, Clock, CheckCircle2 } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  MetricsCards,
  PerformanceChart,
  HoldingsTable,
  TradeHistoryTable,
  RiskMetrics,
} from '@/components/reference-portfolio';
import { useReferencePortfolioState, useMarketStatus } from '@/hooks/useReferencePortfolio';
import { SidebarLayout } from '@/components/layouts/SidebarLayout';

export default function ReferencePortfolio() {
  const { data: state } = useReferencePortfolioState();
  const { data: marketStatus } = useMarketStatus();

  const lastSyncTime = state?.last_sync_at
    ? new Date(state.last_sync_at).toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
      })
    : null;

  const lastTradeTime = state?.last_trade_at
    ? new Date(state.last_trade_at).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      })
    : null;

  return (
    <SidebarLayout>
      {/* Page Header */}
      <div className="border-b border-border/50 bg-card/40 backdrop-blur-xl sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-primary/10">
                <Activity className="h-6 w-6 text-primary" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-foreground">Reference Strategy</h1>
                <p className="text-sm text-muted-foreground">
                  Automated paper trading based on politician activity signals
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {/* Market Status */}
              <div className="flex items-center gap-2">
                <div
                  className={`h-2 w-2 rounded-full ${
                    marketStatus?.isOpen ? 'bg-success animate-pulse' : 'bg-muted-foreground'
                  }`}
                />
                <span className="text-xs text-muted-foreground">
                  Market {marketStatus?.isOpen ? 'Open' : 'Closed'}
                </span>
              </div>

              {/* Trading Status */}
              <Badge
                variant={state?.config?.is_active ? 'default' : 'secondary'}
                className="gap-1"
              >
                {state?.config?.is_active ? (
                  <>
                    <CheckCircle2 className="h-3 w-3" />
                    Trading Active
                  </>
                ) : (
                  'Trading Paused'
                )}
              </Badge>

              {/* Last Sync */}
              {lastSyncTime && (
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  Updated {lastSyncTime}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6 space-y-6">
        {/* Info Alert */}
        <Alert className="bg-primary/5 border-primary/20">
          <Info className="h-4 w-4 text-primary" />
          <AlertDescription className="text-sm text-muted-foreground">
            This reference portfolio demonstrates the performance of our trading signals using paper
            trading. It automatically executes trades when signals exceed{' '}
            <span className="font-semibold text-foreground">
              {((state?.config?.min_confidence_threshold || 0.7) * 100).toFixed(0)}% confidence
            </span>
            . All users can view this portfolio's performance to evaluate our signal quality.
            {lastTradeTime && (
              <span className="block mt-1 text-xs">Last trade: {lastTradeTime}</span>
            )}
          </AlertDescription>
        </Alert>

        {/* Metrics Cards */}
        <section>
          <MetricsCards />
        </section>

        {/* Performance Chart */}
        <section>
          <PerformanceChart />
        </section>

        {/* Holdings and Risk Side by Side */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <HoldingsTable />
          </div>
          <div className="lg:col-span-1">
            <RiskMetrics />
          </div>
        </div>

        {/* Trade History */}
        <section>
          <TradeHistoryTable limit={20} />
        </section>

        {/* Strategy Details */}
        <section className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-6">
          <h3 className="text-lg font-semibold text-foreground mb-4">Strategy Configuration</h3>
          <Separator className="mb-4" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <p className="text-xs text-muted-foreground">Initial Capital</p>
              <p className="text-sm font-semibold text-foreground">
                ${((state?.config?.initial_capital || 100000) / 1000).toFixed(0)}k
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Min Confidence</p>
              <p className="text-sm font-semibold text-foreground">
                {((state?.config?.min_confidence_threshold || 0.7) * 100).toFixed(0)}%
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Max Position Size</p>
              <p className="text-sm font-semibold text-foreground">
                {state?.config?.max_position_size_pct || 5}%
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Max Positions</p>
              <p className="text-sm font-semibold text-foreground">
                {state?.config?.max_portfolio_positions || 20}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Max Daily Trades</p>
              <p className="text-sm font-semibold text-foreground">
                {state?.config?.max_daily_trades || 10}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Base Position</p>
              <p className="text-sm font-semibold text-foreground">
                {state?.config?.base_position_size_pct || 1}%
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Confidence Multiplier</p>
              <p className="text-sm font-semibold text-foreground">
                Up to {state?.config?.confidence_multiplier || 3}x
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Default Stop Loss</p>
              <p className="text-sm font-semibold text-foreground">
                {state?.config?.default_stop_loss_pct || 5}%
              </p>
            </div>
          </div>
        </section>

        {/* Footer Note */}
        <div className="text-center py-4 text-xs text-muted-foreground">
          <p>
            This is a paper trading demonstration. Past performance does not guarantee future results.
          </p>
          <p className="mt-1">
            Trades are executed automatically based on high-confidence trading signals from politician disclosures.
          </p>
        </div>
      </main>
    </SidebarLayout>
  );
}
