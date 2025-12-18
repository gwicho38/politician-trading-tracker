import { useState, useEffect } from 'react';
import { Filter, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import TradeCard from '@/components/TradeCard';
import { useTrades, useJurisdictions } from '@/hooks/useSupabaseData';

interface TradesViewProps {
  jurisdictionId?: string;
  searchQuery?: string;
}

const TradesView = ({ jurisdictionId, searchQuery }: TradesViewProps) => {
  const [filterJurisdiction, setFilterJurisdiction] = useState<string | undefined>(jurisdictionId);
  const { data: trades, isLoading: tradesLoading } = useTrades(50, filterJurisdiction);
  const { data: jurisdictions, isLoading: jurisdictionsLoading } = useJurisdictions();

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
            <Button variant="outline" size="sm" className="gap-2">
              <Filter className="h-4 w-4" />
              Filter
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
          {jurisdictions?.map((j) => (
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
          ) : filteredTrades && filteredTrades.length > 0 ? (
            filteredTrades.map((trade, index) => (
              <TradeCard 
                key={trade.id} 
                trade={{
                  id: trade.id,
                  politicianId: trade.politician_id,
                  politicianName: trade.politician?.name || 'Unknown',
                  party: (trade.politician?.party as 'D' | 'R' | 'I' | 'Other') || 'Other',
                  jurisdiction: trade.politician?.jurisdiction_id || '',
                  ticker: trade.ticker,
                  company: trade.company,
                  type: trade.trade_type as 'buy' | 'sell',
                  amount: trade.amount_range,
                  estimatedValue: trade.estimated_value,
                  filingDate: trade.filing_date,
                  transactionDate: trade.transaction_date,
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
      </div>
    </div>
  );
};

export default TradesView;
