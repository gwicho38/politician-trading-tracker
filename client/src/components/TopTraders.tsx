import { ArrowUpRight, Loader2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { usePoliticians } from '@/hooks/useSupabaseData';
import { formatCurrency, getPartyColor, getPartyBg } from '@/lib/mockData';
import { cn } from '@/lib/utils';

const TopTraders = () => {
  const { data: politicians, isLoading, error } = usePoliticians();

  const sortedPoliticians = politicians?.slice(0, 5) || [];

  return (
    <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-foreground">Top Traders</h3>
          <p className="text-sm text-muted-foreground">By total trading volume</p>
        </div>
        {/* COMMENTED OUT FOR MINIMAL BUILD - Uncomment when ready */}
        {/* <button
          onClick={() => window.dispatchEvent(new CustomEvent('navigate-section', { detail: 'politicians' }))}
          className="text-sm text-primary hover:underline flex items-center gap-1"
        >
          View all <ArrowUpRight className="h-3 w-3" />
        </button> */}
      </div>

      <div className="space-y-3">
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
          sortedPoliticians.map((politician, index) => (
            <div
              key={politician.id}
              className="group flex items-center justify-between rounded-lg p-3 transition-all duration-200 hover:bg-secondary/50"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary font-mono text-sm font-bold text-muted-foreground">
                  #{index + 1}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-foreground">{politician.name}</span>
                    <Badge 
                      variant="outline" 
                      className={cn("text-xs px-1.5 py-0", getPartyBg(politician.party), getPartyColor(politician.party))}
                    >
                      {politician.party}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {politician.chamber} • {politician.state || politician.jurisdiction_id}
                  </p>
                </div>
              </div>

              <div className="text-right">
                <p className="font-mono text-sm font-semibold text-foreground">
                  {formatCurrency(politician.total_volume)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {politician.total_trades} trades
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default TopTraders;
