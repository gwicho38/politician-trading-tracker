import { useState } from 'react';
import { Filter, ArrowUpRight, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import TradeCard from '@/components/TradeCard';
import { useTrades, useJurisdictions } from '@/hooks/useSupabaseData';

const RecentTrades = () => {
  const [filterJurisdiction, setFilterJurisdiction] = useState<string | undefined>(undefined);
  const { data: trades, isLoading: tradesLoading } = useTrades(10, filterJurisdiction);
  const { data: jurisdictions, isLoading: jurisdictionsLoading } = useJurisdictions();

  const isLoading = tradesLoading || jurisdictionsLoading;

  return (
    <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-6">
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-foreground">Recent Trades</h3>
          <p className="text-sm text-muted-foreground">Latest disclosed trading activity</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="gap-2">
            <Filter className="h-4 w-4" />
            Filter
          </Button>
          <Button 
            variant="ghost" 
            size="sm" 
            className="gap-1 text-primary"
            onClick={() => window.dispatchEvent(new CustomEvent('navigate-section', { detail: 'trades' }))}
          >
            View all <ArrowUpRight className="h-3 w-3" />
          </Button>
        </div>
      </div>

      {/* Jurisdiction filters */}
      <div className="mb-4 flex flex-wrap gap-2">
        <Badge 
          variant="jurisdiction" 
          className={`cursor-pointer transition-colors ${!filterJurisdiction ? 'bg-primary/20 text-primary border-primary/30' : ''}`}
          onClick={() => setFilterJurisdiction(undefined)}
        >
          All
        </Badge>
        {jurisdictions?.slice(0, 4).map((j) => (
          <Badge 
            key={j.id} 
            variant="jurisdiction"
            className={`cursor-pointer transition-colors ${filterJurisdiction === j.id ? 'bg-primary/20 text-primary border-primary/30' : ''}`}
            onClick={() => setFilterJurisdiction(j.id)}
          >
            {j.flag} {j.name}
          </Badge>
        ))}
      </div>

      {/* Trade list */}
      <div className="space-y-3">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : trades && trades.length > 0 ? (
          trades.map((trade, index) => (
            <TradeCard
              key={trade.id}
              trade={{
                id: trade.id,
                politicianId: trade.politician_id,
                politicianName: trade.politician?.name || 'Unknown',
                party: (trade.politician?.party as 'D' | 'R' | 'I' | 'Other') || 'Other',
                jurisdiction: trade.politician?.jurisdiction_id || '',
                ticker: trade.ticker || trade.asset_ticker || '',
                company: trade.company || trade.asset_name || '',
                type: (trade.trade_type === 'buy' || trade.trade_type === 'sell' ? trade.trade_type : 'buy') as 'buy' | 'sell',
                amount: trade.amount_range,
                estimatedValue: trade.estimated_value,
                filingDate: trade.filing_date || trade.disclosure_date,
                transactionDate: trade.transaction_date,
                sourceUrl: trade.source_url || undefined,
                sourceDocumentId: trade.source_document_id || undefined,
              }}
              delay={index * 50}
            />
          ))
        ) : (
          <p className="text-sm text-muted-foreground text-center py-8">
            No trades recorded yet
          </p>
        )}
      </div>
    </div>
  );
};

export default RecentTrades;
