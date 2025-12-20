import { useEffect } from 'react';
import { FileText, Loader2, ExternalLink } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { useTrades } from '@/hooks/useSupabaseData';
import { usePagination } from '@/hooks/usePagination';
import { PaginationControls } from '@/components/PaginationControls';
import { formatCurrency } from '@/lib/mockData';
import { format } from 'date-fns';

interface FilingsViewProps {
  jurisdictionId?: string;
}

const FilingsView = ({ jurisdictionId }: FilingsViewProps) => {
  const { data: trades, isLoading } = useTrades(500, jurisdictionId);
  const pagination = usePagination();

  // Group trades by filing date
  const filingsByDate = trades?.reduce((acc, trade) => {
    const date = trade.filing_date;
    if (!acc[date]) {
      acc[date] = [];
    }
    acc[date].push(trade);
    return acc;
  }, {} as Record<string, typeof trades>);

  const sortedDates = Object.keys(filingsByDate || {}).sort((a, b) =>
    new Date(b).getTime() - new Date(a).getTime()
  );

  // Update pagination when dates change
  useEffect(() => {
    pagination.setTotalItems(sortedDates.length);
  }, [sortedDates.length]);

  // Reset to page 1 when jurisdiction changes
  useEffect(() => {
    pagination.setPage(1);
  }, [jurisdictionId]);

  // Paginate the dates (not individual trades)
  const paginatedDates = sortedDates.slice(pagination.startIndex, pagination.endIndex);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <h2 className="text-2xl font-bold text-foreground">Filings</h2>
        <p className="text-muted-foreground">
          Official disclosure filings grouped by date
        </p>
      </div>

      <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : sortedDates.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            No filings recorded yet
          </p>
        ) : (
          <div className="space-y-6">
            {paginatedDates.map((date) => (
              <div key={date} className="border-b border-border/50 pb-6 last:border-0 last:pb-0">
                <div className="flex items-center gap-3 mb-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/20">
                    <FileText className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-foreground">
                      {format(new Date(date), 'MMMM d, yyyy')}
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      {filingsByDate?.[date]?.length} trades filed
                    </p>
                  </div>
                </div>

                <div className="ml-13 space-y-2">
                  {filingsByDate?.[date]?.map((trade) => (
                    <div 
                      key={trade.id}
                      className="flex items-center justify-between rounded-lg bg-secondary/30 p-3 hover:bg-secondary/50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <Badge variant={trade.trade_type === 'buy' ? 'default' : 'destructive'} className="text-xs">
                          {trade.trade_type.toUpperCase()}
                        </Badge>
                        <div>
                          <p className="font-medium text-sm text-foreground">
                            {trade.politician?.name || 'Unknown'} - {trade.ticker}
                          </p>
                          <p className="text-xs text-muted-foreground">{trade.company}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-mono text-sm font-semibold text-foreground">
                          {formatCurrency(trade.estimated_value)}
                        </p>
                        <p className="text-xs text-muted-foreground">{trade.amount_range}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination Controls */}
        {sortedDates.length > 0 && (
          <PaginationControls pagination={pagination} itemLabel="filing dates" />
        )}
      </div>
    </div>
  );
};

export default FilingsView;
