import { TrendingUp, TrendingDown, Wallet, ExternalLink, Loader2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { usePoliticianDetail, type Politician } from '@/hooks/useSupabaseData';
import { formatCurrency, getPartyColor, getPartyBg } from '@/lib/mockData';
import { cn, formatChamber } from '@/lib/utils';

interface PoliticianDetailModalProps {
  politician: Politician | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function PoliticianDetailModal({
  politician,
  open,
  onOpenChange,
}: PoliticianDetailModalProps) {
  const { data: detail, isLoading } = usePoliticianDetail(politician?.id ?? null);

  if (!politician) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader className="pb-4 border-b">
          <div className="flex items-start justify-between">
            <div>
              <DialogTitle className="text-xl flex items-center gap-2">
                {politician.name}
                <Badge
                  variant="outline"
                  className={cn(
                    'text-xs',
                    getPartyBg(politician.party),
                    getPartyColor(politician.party)
                  )}
                >
                  {politician.party}
                </Badge>
              </DialogTitle>
              <p className="text-sm text-muted-foreground mt-1">
                {formatChamber(politician.chamber)} {politician.state && `• ${politician.state}`}
              </p>
            </div>
          </div>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : detail ? (
          <div className="flex-1 overflow-y-auto space-y-6 py-4">
            {/* Trading Stats */}
            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-lg bg-secondary/50 p-3 text-center">
                <p className="text-xl font-bold">{detail.total_trades}</p>
                <p className="text-xs text-muted-foreground">Total</p>
              </div>
              <div className="rounded-lg bg-success/10 p-3 text-center">
                <div className="flex items-center justify-center gap-1">
                  <TrendingUp className="h-3 w-3 text-success" />
                  <p className="text-xl font-bold text-success">{detail.buyCount}</p>
                </div>
                <p className="text-xs text-muted-foreground">Buys</p>
              </div>
              <div className="rounded-lg bg-destructive/10 p-3 text-center">
                <div className="flex items-center justify-center gap-1">
                  <TrendingDown className="h-3 w-3 text-destructive" />
                  <p className="text-xl font-bold text-destructive">{detail.sellCount}</p>
                </div>
                <p className="text-xs text-muted-foreground">Sells</p>
              </div>
              <div className="rounded-lg bg-primary/10 p-3 text-center">
                <div className="flex items-center justify-center gap-1">
                  <Wallet className="h-3 w-3 text-primary" />
                  <p className="text-xl font-bold text-primary">{detail.holdingCount}</p>
                </div>
                <p className="text-xs text-muted-foreground">Holdings</p>
              </div>
            </div>

            {/* Total Volume */}
            <div className="rounded-lg border p-4">
              <p className="text-sm text-muted-foreground">Total Trading Volume</p>
              <p className="text-2xl font-bold font-mono">
                {formatCurrency(detail.total_volume)}
              </p>
            </div>

            {/* Top Tickers */}
            {detail.topTickers.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold mb-3">Most Traded Tickers</h4>
                <div className="flex flex-wrap gap-2">
                  {detail.topTickers.map((t) => (
                    <Badge key={t.ticker} variant="secondary" className="font-mono">
                      {t.ticker}
                      <span className="ml-1 text-muted-foreground">({t.count})</span>
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Recent Trades */}
            {detail.recentTrades.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold mb-3">Recent Trades</h4>
                <div className="space-y-2">
                  {detail.recentTrades.map((trade) => (
                    <div
                      key={trade.id}
                      className="flex items-center justify-between rounded-lg border p-3 text-sm"
                    >
                      <div className="flex items-center gap-3">
                        <Badge
                          variant="outline"
                          className={cn(
                            'text-xs',
                            trade.transaction_type === 'purchase' && 'bg-success/10 text-success border-success/30',
                            trade.transaction_type === 'sale' && 'bg-destructive/10 text-destructive border-destructive/30',
                            trade.transaction_type === 'holding' && 'bg-primary/10 text-primary border-primary/30',
                            !['purchase', 'sale', 'holding'].includes(trade.transaction_type || '') && 'bg-muted/10 text-muted-foreground border-muted'
                          )}
                        >
                          {trade.transaction_type === 'purchase' ? 'BUY' :
                           trade.transaction_type === 'sale' ? 'SELL' :
                           trade.transaction_type === 'holding' ? 'HOLD' :
                           trade.transaction_type?.toUpperCase() || 'N/A'}
                        </Badge>
                        <div>
                          <span className="font-mono font-semibold">
                            {trade.asset_ticker || 'N/A'}
                          </span>
                          <span className="text-muted-foreground ml-2 text-xs">
                            {trade.asset_name?.slice(0, 30)}
                            {(trade.asset_name?.length || 0) > 30 ? '...' : ''}
                          </span>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-muted-foreground">
                          {new Date(trade.disclosure_date).toLocaleDateString()}
                        </p>
                        {trade.source_url && (
                          <a
                            href={trade.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-primary hover:underline inline-flex items-center gap-1"
                          >
                            Source <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="py-12 text-center text-muted-foreground">
            No trading data available
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
