import { useState, useEffect } from 'react';
import { Filter, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import TradeCard from '@/components/TradeCard';
import { useTrades, useJurisdictions } from '@/hooks/useSupabaseData';
import { usePagination } from '@/hooks/usePagination';
import { PaginationControls } from '@/components/PaginationControls';
import { toParty, toDisplayTransactionType } from '@/lib/typeGuards';

interface TradesViewProps {
  jurisdictionId?: string;
  searchQuery?: string;
}

const TradesView = ({ jurisdictionId, searchQuery }: TradesViewProps) => {
  const [filterJurisdiction, setFilterJurisdiction] = useState<string | undefined>(jurisdictionId);
  const { data: trades, isLoading: tradesLoading } = useTrades(500, filterJurisdiction);
  const { data: jurisdictions, isLoading: jurisdictionsLoading } = useJurisdictions();
  const pagination = usePagination();

  const isLoading = tradesLoading || jurisdictionsLoading;

  // Filter trades by search query
  const filteredTrades = trades?.filter(trade => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      trade.ticker.toLowerCase().includes(query) ||
      trade.company.toLowerCase().includes(query) ||
      trade.politician?.name.toLowerCase().includes(query)
    );
  });

  // Update pagination when filtered trades change
  useEffect(() => {
    pagination.setTotalItems(filteredTrades?.length || 0);
  }, [filteredTrades?.length]);

  // Reset to page 1 when filters change
  useEffect(() => {
    pagination.setPage(1);
  }, [filterJurisdiction, searchQuery]);

  // Get paginated trades
  const paginatedTrades = filteredTrades?.slice(pagination.startIndex, pagination.endIndex);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <h2 className="text-2xl font-bold text-foreground">Recent Trades</h2>
        <p className="text-muted-foreground">
          All disclosed trading activity from tracked politicians
        </p>
      </div>

      <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-6">
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" className="gap-2" aria-label="Open trade filters">
              <Filter className="h-4 w-4" aria-hidden="true" />
              Filter
            </Button>
          </div>
        </div>

        {/* Jurisdiction filters */}
        <div className="mb-4 flex flex-wrap gap-2" role="group" aria-label="Filter by jurisdiction">
          <button
            type="button"
            className={`inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors cursor-pointer border-border/50 bg-card/50 text-foreground ${!filterJurisdiction ? 'bg-primary/20 text-primary border-primary/30' : ''}`}
            onClick={() => setFilterJurisdiction(undefined)}
            aria-pressed={!filterJurisdiction}
            aria-label="Show all jurisdictions"
          >
            All
          </button>
          {jurisdictions?.map((j) => (
            <button
              key={j.id}
              type="button"
              className={`inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors cursor-pointer border-border/50 bg-card/50 text-foreground ${filterJurisdiction === j.id ? 'bg-primary/20 text-primary border-primary/30' : ''}`}
              onClick={() => setFilterJurisdiction(j.id)}
              aria-pressed={filterJurisdiction === j.id}
              aria-label={`Filter by ${j.name}`}
            >
              <span aria-hidden="true">{j.flag}</span> {j.name}
            </button>
          ))}
        </div>

        {/* Trade list */}
        <div className="space-y-3">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : paginatedTrades && paginatedTrades.length > 0 ? (
            paginatedTrades.map((trade, index) => (
              <TradeCard
                key={trade.id}
                trade={{
                  id: trade.id,
                  politicianId: trade.politician_id,
                  politicianName: trade.politician?.name || 'Unknown',
                  party: toParty(trade.politician?.party),
                  jurisdiction: trade.politician?.jurisdiction_id || '',
                  ticker: trade.ticker || trade.asset_ticker || '',
                  company: trade.company || trade.asset_name || '',
                  type: toDisplayTransactionType(trade.trade_type) === 'buy' || toDisplayTransactionType(trade.trade_type) === 'sell' ? toDisplayTransactionType(trade.trade_type) : 'buy',
                  amount: trade.amount_range,
                  estimatedValue: trade.estimated_value,
                  filingDate: trade.filing_date || trade.disclosure_date,
                  transactionDate: trade.transaction_date,
                  sourceUrl: trade.source_url || undefined,
                  sourceDocumentId: trade.source_document_id || undefined,
                }}
                delay={index * 30}
              />
            ))
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              {searchQuery ? `No trades found for "${searchQuery}"` : 'No trades recorded yet'}
            </p>
          )}
        </div>

        {/* Pagination Controls */}
        {filteredTrades && filteredTrades.length > 0 && (
          <PaginationControls pagination={pagination} itemLabel="trades" />
        )}
      </div>
    </div>
  );
};

export default TradesView;
