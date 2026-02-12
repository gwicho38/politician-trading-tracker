import { ArrowUpRight, ArrowDownRight, ExternalLink } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { Trade, formatCurrency, getPartyColor, getPartyBg } from '@/lib/mockData';
import { toParty, getPartyLabel } from '@/lib/typeGuards';

interface TradeCardProps {
  trade: Trade;
  delay?: number;
}

const TradeCard = ({ trade, delay = 0 }: TradeCardProps) => {
  const isBuy = trade.type === 'buy';

  return (
    <div
      className="group relative overflow-hidden rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-3 sm:p-4 transition-all duration-300 hover:border-primary/30 animate-fade-in"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-start justify-between gap-2 sm:gap-4">
        <div className="flex items-start gap-2 sm:gap-3 min-w-0 flex-1">
          {/* Trade type indicator */}
          <div className={cn(
            "mt-0.5 rounded-lg p-1.5 sm:p-2 flex-shrink-0",
            isBuy ? "bg-success/20 border border-success/30" : "bg-destructive/20 border border-destructive/30"
          )}>
            {isBuy ? (
              <ArrowUpRight className="h-3 w-3 sm:h-4 sm:w-4 text-success" />
            ) : (
              <ArrowDownRight className="h-3 w-3 sm:h-4 sm:w-4 text-destructive" />
            )}
          </div>

          <div className="space-y-1 min-w-0 flex-1">
            {/* Politician name and party */}
            <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap">
              <span className="font-semibold text-foreground text-sm sm:text-base truncate">
                {trade.politicianName}
              </span>
              <Badge
                variant="outline"
                className={cn("text-xs px-1 sm:px-1.5 py-0 flex-shrink-0", getPartyBg(trade.party), getPartyColor(trade.party))}
              >
                {getPartyLabel(toParty(trade.party))}
              </Badge>
            </div>

            {/* Ticker and company */}
            <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
              <span className="font-mono text-xs sm:text-sm font-semibold text-primary flex-shrink-0">
                {trade.ticker}
              </span>
              <span className="text-xs sm:text-sm text-muted-foreground truncate">
                {trade.company}
              </span>
            </div>

            {/* Amount */}
            <div className="flex items-center gap-1.5 sm:gap-2 text-xs sm:text-sm">
              <Badge variant={isBuy ? "buy" : "sell"} className="text-xs">
                {isBuy ? 'BUY' : 'SELL'}
              </Badge>
              <span className="text-muted-foreground truncate">{trade.amount}</span>
            </div>
          </div>
        </div>

        {/* Right side - date and link */}
        <div className="flex flex-col items-end gap-1 sm:gap-2 flex-shrink-0">
          <div className="text-right">
            <p className="text-xs text-muted-foreground">Filed</p>
            <p className="text-xs sm:text-sm font-medium text-foreground">
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
              className="rounded-lg p-1 sm:p-1.5 text-muted-foreground hover:bg-secondary hover:text-primary transition-colors sm:opacity-0 sm:group-hover:opacity-100"
              title="View original disclosure document"
              aria-label="View original disclosure document"
            >
              <ExternalLink className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            </a>
          )}
        </div>
      </div>
    </div>
  );
};

export default TradeCard;
