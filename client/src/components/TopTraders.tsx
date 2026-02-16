import { useState, useMemo } from 'react';
import { ArrowUpRight, Loader2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { usePoliticians, type Politician } from '@/hooks/useSupabaseData';
import { formatCurrency } from '@/lib/mockData';
import { formatChamber } from '@/lib/utils';
import { PoliticianDetailModal } from '@/components/detail-modals';
import { useParties } from '@/hooks/useParties';
import { buildPartyMap, getPartyLabel, partyColorStyle, partyBadgeStyle } from '@/lib/partyUtils';

const TopTraders = () => {
  const { data: politicians, isLoading, error } = usePoliticians();
  const { data: parties = [] } = useParties();
  const partyMap = useMemo(() => buildPartyMap(parties), [parties]);
  const [selectedPolitician, setSelectedPolitician] = useState<Politician | null>(null);

  const sortedPoliticians = politicians?.slice(0, 5) || [];

  return (
    <>
      <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-4 sm:p-6">
        <div className="mb-4 sm:mb-6 flex items-center justify-between">
          <div>
            <h3 className="text-base sm:text-lg font-semibold text-foreground">Top Traders</h3>
            <p className="text-xs sm:text-sm text-muted-foreground">By total trading volume</p>
          </div>
          <button
            type="button"
            onClick={() => window.dispatchEvent(new CustomEvent('navigate-section', { detail: 'politicians' }))}
            className="text-xs sm:text-sm text-primary hover:underline flex items-center gap-1"
            aria-label="View all politicians"
          >
            View all <ArrowUpRight className="h-3 w-3" aria-hidden="true" />
          </button>
        </div>

        <div className="space-y-2 sm:space-y-3">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : error ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No data available yet
            </p>
          ) : sortedPoliticians.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No politicians tracked yet
            </p>
          ) : (
            sortedPoliticians.map((politician, index) => {
              const party = politician.party || 'Unknown';
              return (
                <button
                  key={politician.id}
                  type="button"
                  onClick={() => setSelectedPolitician(politician)}
                  className="group w-full flex items-center justify-between rounded-lg p-2 sm:p-3 transition-all duration-200 hover:bg-secondary/50 cursor-pointer gap-2 text-left"
                  aria-label={`View details for ${politician.name}, ${getPartyLabel(partyMap, party)} party, ${formatChamber(politician.chamber)}, ${formatCurrency(politician.total_volume ?? 0)} total volume, ${politician.total_trades ?? 0} trades`}
                >
                  <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
                    <div className="flex h-6 w-6 sm:h-8 sm:w-8 items-center justify-center rounded-lg bg-secondary font-mono text-xs sm:text-sm font-bold text-muted-foreground flex-shrink-0" aria-hidden="true">
                      #{index + 1}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap">
                        <span className="font-medium text-sm sm:text-base text-foreground group-hover:text-primary transition-colors truncate">
                          {politician.name}
                        </span>
                        <Badge
                          variant="outline"
                          className="text-xs px-1 sm:px-1.5 py-0 flex-shrink-0"
                          style={{...partyBadgeStyle(partyMap, party), ...partyColorStyle(partyMap, party)}}
                        >
                          {getPartyLabel(partyMap, party)}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground truncate">
                        {formatChamber(politician.chamber)} • {politician.state || politician.jurisdiction_id || 'Unknown'}
                      </p>
                    </div>
                  </div>

                  <div className="text-right flex-shrink-0">
                    <p className="font-mono text-xs sm:text-sm font-semibold text-foreground">
                      {formatCurrency(politician.total_volume ?? 0)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {politician.total_trades ?? 0} trades
                    </p>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>

      <PoliticianDetailModal
        politician={selectedPolitician}
        open={!!selectedPolitician}
        onOpenChange={(open) => !open && setSelectedPolitician(null)}
      />
    </>
  );
};

export default TopTraders;
