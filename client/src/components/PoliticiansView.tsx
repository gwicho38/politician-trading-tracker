import { useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { usePoliticians } from '@/hooks/useSupabaseData';
import { usePagination } from '@/hooks/usePagination';
import { PaginationControls } from '@/components/PaginationControls';
import { formatCurrency, getPartyColor, getPartyBg } from '@/lib/mockData';
import { cn } from '@/lib/utils';

interface PoliticiansViewProps {
  jurisdictionId?: string;
}

const PoliticiansView = ({ jurisdictionId }: PoliticiansViewProps) => {
  const { data: politicians, isLoading, error } = usePoliticians(jurisdictionId);
  const pagination = usePagination();

  // Update total items when politicians data changes
  useEffect(() => {
    if (politicians) {
      pagination.setTotalItems(politicians.length);
    }
  }, [politicians]);

  // Reset to page 1 when jurisdiction changes
  useEffect(() => {
    pagination.setPage(1);
  }, [jurisdictionId]);

  // Get paginated politicians
  const paginatedPoliticians = politicians?.slice(pagination.startIndex, pagination.endIndex);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <h2 className="text-2xl font-bold text-foreground">Politicians</h2>
        <p className="text-muted-foreground">
          All tracked politicians and their trading activity
        </p>
      </div>

      <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            No data available yet
          </p>
        ) : politicians?.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            No politicians tracked yet
          </p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {paginatedPoliticians?.map((politician, index) => (
              <div
                key={politician.id}
                className="group rounded-lg border border-border/50 p-4 transition-all duration-200 hover:bg-secondary/50"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary text-sm font-bold text-muted-foreground">
                      {politician.name?.split(' ').map(n => n[0]).join('').slice(0, 2) || '??'}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-foreground">{politician.name || 'Unknown'}</span>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {politician.chamber || 'Unknown'} • {politician.state || politician.jurisdiction_id || 'Unknown'}
                      </p>
                    </div>
                  </div>
                  <Badge 
                    variant="outline" 
                    className={cn("text-xs px-1.5 py-0", getPartyBg(politician.party), getPartyColor(politician.party))}
                  >
                    {politician.party}
                  </Badge>
                </div>

                <div className="mt-4 flex items-center justify-between border-t border-border/50 pt-3">
                  <div>
                    <p className="text-xs text-muted-foreground">Total Volume</p>
                    <p className="font-mono text-sm font-semibold text-foreground">
                      {formatCurrency(politician.total_volume)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-muted-foreground">Trades</p>
                    <p className="font-mono text-sm font-semibold text-foreground">
                      {politician.total_trades}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination Controls */}
        {politicians && politicians.length > 0 && (
          <PaginationControls pagination={pagination} itemLabel="politicians" />
        )}
      </div>
    </div>
  );
};

export default PoliticiansView;
