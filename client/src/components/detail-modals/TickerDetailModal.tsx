import { TrendingUp, TrendingDown, Wallet, ExternalLink, Loader2, Users } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { useTickerDetail } from '@/hooks/useSupabaseData';
import { formatCurrency, getPartyColor, getPartyBg } from '@/lib/mockData';
import { cn } from '@/lib/utils';

interface TickerDetailModalProps {
  ticker: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function TickerDetailModal({
  ticker,
  open,
  onOpenChange,
}: TickerDetailModalProps) {
  const { data: detail, isLoading } = useTickerDetail(ticker);

  if (!ticker) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader className="pb-4 border-b">
          <div>
            <DialogTitle className="text-xl font-mono">
              {ticker.toUpperCase()}
            </DialogTitle>
            {detail && (
              <p className="text-sm text-muted-foreground mt-1">
                {detail.name}
              </p>
            )}
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
                <p className="text-xl font-bold">{detail.totalTrades}</p>
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
                {formatCurrency(detail.totalVolume)}
              </p>
            </div>

            {/* Top Politicians */}
            {detail.topPoliticians.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                  <Users className="h-4 w-4" />
                  Top Politicians Trading This Stock
                </h4>
                <div className="space-y-2">
                  {detail.topPoliticians.map((p, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between rounded-lg bg-secondary/30 p-3"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-muted-foreground text-sm">#{idx + 1}</span>
                        <span className="font-medium">{p.name}</span>
                        <Badge
                          variant="outline"
                          className={cn(
                            'text-xs',
                            getPartyBg(p.party),
                            getPartyColor(p.party)
                          )}
                        >
                          {p.party}
                        </Badge>
                      </div>
                      <span className="text-sm text-muted-foreground">
                        {p.count} trades
                      </span>
                    </div>
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
                          <span className="font-medium">
                            {trade.politician?.name || 'Unknown'}
                          </span>
                          {trade.politician?.party && (
                            <Badge
                              variant="outline"
                              className={cn(
                                'text-xs ml-2',
                                getPartyBg(trade.politician.party),
                                getPartyColor(trade.politician.party)
                              )}
                            >
                              {trade.politician.party}
                            </Badge>
                          )}
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
            No trading data available for {ticker}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
