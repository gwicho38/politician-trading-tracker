import { ArrowUpRight, ArrowDownRight, ExternalLink } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { Trade, formatCurrency, getPartyColor, getPartyBg } from '@/lib/mockData';

interface TradeCardProps {
  trade: Trade;
  delay?: number;
}

const TradeCard = ({ trade, delay = 0 }: TradeCardProps) => {
  const isBuy = trade.type === 'buy';

  return (
    <div 
      className="group relative overflow-hidden rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-4 transition-all duration-300 hover:border-primary/30 animate-fade-in"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          {/* Trade type indicator */}
          <div className={cn(
            "mt-0.5 rounded-lg p-2",
            isBuy ? "bg-success/20 border border-success/30" : "bg-destructive/20 border border-destructive/30"
          )}>
            {isBuy ? (
              <ArrowUpRight className="h-4 w-4 text-success" />
            ) : (
              <ArrowDownRight className="h-4 w-4 text-destructive" />
            )}
          </div>
          
          <div className="space-y-1">
            {/* Politician name and party */}
            <div className="flex items-center gap-2">
              <span className="font-semibold text-foreground">
                {trade.politicianName}
              </span>
              <Badge 
                variant="outline" 
                className={cn("text-xs px-1.5 py-0", getPartyBg(trade.party), getPartyColor(trade.party))}
              >
                {trade.party}
              </Badge>
            </div>
            
            {/* Ticker and company */}
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-semibold text-primary">
                {trade.ticker}
              </span>
              <span className="text-sm text-muted-foreground truncate max-w-[180px]">
                {trade.company}
              </span>
            </div>
            
            {/* Amount */}
            <div className="flex items-center gap-2 text-sm">
              <Badge variant={isBuy ? "buy" : "sell"}>
                {isBuy ? 'BUY' : 'SELL'}
              </Badge>
              <span className="text-muted-foreground">{trade.amount}</span>
            </div>
          </div>
        </div>

        {/* Right side - date and link */}
        <div className="flex flex-col items-end gap-2">
          <div className="text-right">
            <p className="text-xs text-muted-foreground">Filed</p>
            <p className="text-sm font-medium text-foreground">
              {new Date(trade.filingDate).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric'
              })}
            </p>
          </div>
          {trade.sourceUrl && (
            <a
              href={trade.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg p-1.5 text-muted-foreground hover:bg-secondary hover:text-primary transition-colors opacity-0 group-hover:opacity-100"
              title="View original disclosure document"
            >
              <ExternalLink className="h-4 w-4" />
            </a>
          )}
        </div>
      </div>
    </div>
  );
};

export default TradeCard;
