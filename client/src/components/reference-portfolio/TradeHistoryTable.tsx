import { useState } from 'react';
import { Loader2, ArrowUpRight, ArrowDownRight, ExternalLink } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  useReferencePortfolioTrades,
  ReferencePortfolioTransaction,
} from '@/hooks/useReferencePortfolio';

const formatCurrency = (value: number | null) => {
  if (value === null || value === undefined) return '-';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

const formatDate = (dateString: string) => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
};

interface TradeHistoryTableProps {
  limit?: number;
}

export function TradeHistoryTable({ limit = 20 }: TradeHistoryTableProps) {
  const [page, setPage] = useState(0);
  const { data, isLoading, error } = useReferencePortfolioTrades(limit, page * limit);

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-6">
        <h3 className="text-lg font-semibold text-foreground mb-4">Trade History</h3>
        <div className="flex items-center justify-center h-40">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-6">
        <h3 className="text-lg font-semibold text-foreground mb-4">Trade History</h3>
        <div className="flex items-center justify-center h-40 text-muted-foreground">
          Failed to load trade history
        </div>
      </div>
    );
  }

  const { trades, total } = data || { trades: [], total: 0 };
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-foreground">Trade History</h3>
          <p className="text-sm text-muted-foreground">
            {total} total trade{total !== 1 ? 's' : ''} executed
          </p>
        </div>
      </div>

      {trades.length === 0 ? (
        <div className="flex items-center justify-center h-40 text-muted-foreground">
          No trades executed yet
        </div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="text-xs font-medium">Date</TableHead>
                  <TableHead className="text-xs font-medium">Ticker</TableHead>
                  <TableHead className="text-xs font-medium">Type</TableHead>
                  <TableHead className="text-right text-xs font-medium">Shares</TableHead>
                  <TableHead className="text-right text-xs font-medium">Price</TableHead>
                  <TableHead className="text-right text-xs font-medium">Total</TableHead>
                  <TableHead className="text-right text-xs font-medium">Signal</TableHead>
                  <TableHead className="text-xs font-medium">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {trades.map((trade: ReferencePortfolioTransaction) => {
                  const isBuy = trade.transaction_type === 'buy';
                  return (
                    <TableRow key={trade.id} className="hover:bg-muted/30">
                      <TableCell className="text-xs text-muted-foreground">
                        {formatDate(trade.executed_at)}
                      </TableCell>
                      <TableCell>
                        <span className="font-semibold text-foreground">{trade.ticker}</span>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          {isBuy ? (
                            <ArrowUpRight className="h-3 w-3 text-success" />
                          ) : (
                            <ArrowDownRight className="h-3 w-3 text-destructive" />
                          )}
                          <Badge
                            variant={isBuy ? 'default' : 'destructive'}
                            className="text-xs"
                          >
                            {trade.transaction_type.toUpperCase()}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {trade.quantity}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(trade.price)}
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {formatCurrency(trade.total_value)}
                      </TableCell>
                      <TableCell className="text-right">
                        {isBuy ? (
                          // Show signal info for buys
                          trade.signal_confidence ? (
                            <div className="flex flex-col items-end">
                              <Badge variant="outline" className="text-xs">
                                {(trade.signal_confidence * 100).toFixed(0)}%
                              </Badge>
                              {trade.signal_type && (
                                <span className="text-[10px] text-muted-foreground mt-0.5">
                                  {trade.signal_type.replace('_', ' ')}
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )
                        ) : (
                          // Show exit reason and P/L for sells
                          <div className="flex flex-col items-end">
                            {trade.exit_reason && (
                              <Badge
                                variant="outline"
                                className={`text-xs ${
                                  trade.exit_reason === 'take_profit'
                                    ? 'border-success text-success'
                                    : trade.exit_reason === 'stop_loss'
                                    ? 'border-destructive text-destructive'
                                    : ''
                                }`}
                              >
                                {trade.exit_reason.replace('_', ' ')}
                              </Badge>
                            )}
                            {trade.realized_pl !== null && (
                              <span className={`text-[10px] mt-0.5 ${
                                trade.realized_pl >= 0 ? 'text-success' : 'text-destructive'
                              }`}>
                                {trade.realized_pl >= 0 ? '+' : ''}
                                {formatCurrency(trade.realized_pl)}
                              </span>
                            )}
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            trade.status === 'executed'
                              ? 'default'
                              : trade.status === 'failed'
                              ? 'destructive'
                              : 'secondary'
                          }
                          className="text-xs"
                        >
                          {trade.status}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4 pt-4 border-t border-border/50">
              <p className="text-xs text-muted-foreground">
                Showing {page * limit + 1}-{Math.min((page + 1) * limit, total)} of {total}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                  disabled={page >= totalPages - 1}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
