import { useEffect, useState } from 'react';
import { Loader2, ChevronRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { usePoliticians, type Politician } from '@/hooks/useSupabaseData';
import { usePagination } from '@/hooks/usePagination';
import { PaginationControls } from '@/components/PaginationControls';
import { formatCurrency, getPartyColor, getPartyBg } from '@/lib/mockData';
import { cn } from '@/lib/utils';
import { PoliticianProfileModal } from '@/components/detail-modals';

interface PoliticiansViewProps {
  jurisdictionId?: string;
  initialPoliticianId?: string | null;
  onPoliticianSelected?: () => void;
}

const PoliticiansView = ({ jurisdictionId, initialPoliticianId, onPoliticianSelected }: PoliticiansViewProps) => {
  const { data: politicians, isLoading, error } = usePoliticians(jurisdictionId);
  const pagination = usePagination();
  const [selectedPolitician, setSelectedPolitician] = useState<Politician | null>(null);

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

  // Handle initial politician selection from search
  useEffect(() => {
    if (initialPoliticianId && politicians) {
      const politician = politicians.find(p => p.id === initialPoliticianId);
      if (politician) {
        setSelectedPolitician(politician);
        onPoliticianSelected?.();
      }
    }
  }, [initialPoliticianId, politicians, onPoliticianSelected]);

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

      <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <p className="text-sm text-muted-foreground text-center py-12">
            No data available yet
          </p>
        ) : politicians?.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-12">
            No politicians tracked yet
          </p>
        ) : (
          <>
            {/* Table Header */}
            <div className="grid grid-cols-12 gap-4 px-4 py-3 border-b border-border/50 text-xs font-medium text-muted-foreground uppercase tracking-wide">
              <div className="col-span-5 sm:col-span-4">Politician</div>
              <div className="col-span-2 hidden sm:block">Chamber</div>
              <div className="col-span-3 sm:col-span-2 text-right">Volume</div>
              <div className="col-span-3 sm:col-span-2 text-right">Trades</div>
              <div className="col-span-1 sm:col-span-2"></div>
            </div>

            {/* Table Body */}
            <div className="divide-y divide-border/30">
              {paginatedPoliticians?.map((politician) => (
                <div
                  key={politician.id}
                  onClick={() => setSelectedPolitician(politician)}
                  className="grid grid-cols-12 gap-4 px-4 py-3 items-center cursor-pointer transition-all duration-200 hover:bg-secondary/50 group"
                >
                  {/* Politician Info */}
                  <div className="col-span-5 sm:col-span-4 flex items-center gap-3 min-w-0">
                    <div className="flex-shrink-0 h-9 w-9 rounded-full bg-secondary flex items-center justify-center text-sm font-bold text-muted-foreground">
                      {politician.name?.split(' ').map(n => n[0]).join('').slice(0, 2) || '??'}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-foreground truncate group-hover:text-primary transition-colors">
                          {politician.name || 'Unknown'}
                        </span>
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-xs px-1.5 py-0 flex-shrink-0",
                            getPartyBg(politician.party),
                            getPartyColor(politician.party)
                          )}
                        >
                          {politician.party}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground truncate sm:hidden">
                        {politician.chamber || 'Unknown'}
                      </p>
                    </div>
                  </div>

                  {/* Chamber & State */}
                  <div className="col-span-2 hidden sm:block text-sm text-muted-foreground">
                    <p className="truncate">{politician.chamber || 'Unknown'}</p>
                    <p className="text-xs truncate">{politician.state || politician.jurisdiction_id || ''}</p>
                  </div>

                  {/* Volume */}
                  <div className="col-span-3 sm:col-span-2 text-right">
                    <p className="font-mono text-sm font-semibold text-foreground">
                      {formatCurrency(politician.total_volume)}
                    </p>
                  </div>

                  {/* Trades */}
                  <div className="col-span-3 sm:col-span-2 text-right">
                    <p className="font-mono text-sm text-muted-foreground">
                      {politician.total_trades}
                    </p>
                  </div>

                  {/* Arrow */}
                  <div className="col-span-1 sm:col-span-2 flex justify-end">
                    <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* Pagination Controls */}
        {politicians && politicians.length > 0 && (
          <div className="border-t border-border/50 p-4">
            <PaginationControls pagination={pagination} itemLabel="politicians" />
          </div>
        )}
      </div>

      {/* Profile Modal */}
      <PoliticianProfileModal
        politician={selectedPolitician}
        open={!!selectedPolitician}
        onOpenChange={(open) => !open && setSelectedPolitician(null)}
      />
    </div>
  );
};

export default PoliticiansView;
