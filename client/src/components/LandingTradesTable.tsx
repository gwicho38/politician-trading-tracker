import { useState } from 'react';
import { ExternalLink, ArrowUpRight, ArrowDownRight, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/lib/utils';
import { useTradingDisclosures } from '@/hooks/useSupabaseData';
import { getPartyColor, getPartyBg } from '@/lib/mockData';

const ROWS_PER_PAGE = 15;

const LandingTradesTable = () => {
  const [page, setPage] = useState(0);
  const offset = page * ROWS_PER_PAGE;

  const { data, isLoading } = useTradingDisclosures({
    limit: ROWS_PER_PAGE,
    offset,
  });

  const disclosures = data?.disclosures || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / ROWS_PER_PAGE);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const formatAmount = (min: number | null, max: number | null) => {
    if (min === null && max === null) return 'Not disclosed';
    if (min === null) return `Up to $${max?.toLocaleString()}`;
    if (max === null) return `$${min.toLocaleString()}+`;
    if (min === max) return `$${min.toLocaleString()}`;
    return `$${min.toLocaleString()} - $${max.toLocaleString()}`;
  };

  const getTransactionBadge = (type: string) => {
    const isBuy = type === 'purchase';
    const isSell = type === 'sale';

    return (
      <Badge
        variant={isBuy ? 'buy' : isSell ? 'sell' : 'outline'}
        className="gap-1"
      >
        {isBuy && <ArrowUpRight className="h-3 w-3" />}
        {isSell && <ArrowDownRight className="h-3 w-3" />}
        {type.charAt(0).toUpperCase() + type.slice(1)}
      </Badge>
    );
  };

  return (
    <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl">
      {/* Header */}
      <div className="p-6 border-b border-border/50">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-foreground">
              Politician Trading Disclosures
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              Real-time tracking of congressional stock trades. Data sourced from{' '}
              <a
                href="https://www.capitoltrades.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline inline-flex items-center gap-1"
              >
                Capitol Trades
                <ExternalLink className="h-3 w-3" />
              </a>
            </p>
          </div>
          <div className="text-sm text-muted-foreground">
            {total.toLocaleString()} total disclosures
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-[180px]">Politician</TableHead>
              <TableHead>Asset</TableHead>
              <TableHead className="w-[100px]">Type</TableHead>
              <TableHead className="w-[160px]">Amount</TableHead>
              <TableHead className="w-[120px]">Transaction</TableHead>
              <TableHead className="w-[120px]">Disclosed</TableHead>
              <TableHead className="w-[60px]">Source</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="h-32 text-center">
                  <Loader2 className="h-6 w-6 animate-spin mx-auto text-muted-foreground" />
                </TableCell>
              </TableRow>
            ) : disclosures.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="h-32 text-center text-muted-foreground">
                  No trading disclosures found
                </TableCell>
              </TableRow>
            ) : (
              disclosures.map((disclosure) => {
                const politician = disclosure.politician;
                const party = (politician?.party || 'Unknown') as 'D' | 'R' | 'I' | 'Other';

                return (
                  <TableRow key={disclosure.id} className="group">
                    {/* Politician */}
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-foreground">
                          {politician?.name || 'Unknown'}
                        </span>
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-xs px-1.5 py-0",
                            getPartyBg(party),
                            getPartyColor(party)
                          )}
                        >
                          {party}
                        </Badge>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {politician?.role || 'Unknown'}{politician?.state_or_country ? ` - ${politician.state_or_country}` : ''}
                      </div>
                    </TableCell>

                    {/* Asset */}
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {disclosure.asset_ticker && (
                          <span className="font-mono text-sm font-semibold text-primary">
                            {disclosure.asset_ticker}
                          </span>
                        )}
                        <span className="text-sm text-muted-foreground truncate max-w-[200px]">
                          {disclosure.asset_name}
                        </span>
                      </div>
                      {disclosure.asset_type && (
                        <div className="text-xs text-muted-foreground">
                          {disclosure.asset_type}
                        </div>
                      )}
                    </TableCell>

                    {/* Transaction Type */}
                    <TableCell>
                      {getTransactionBadge(disclosure.transaction_type)}
                    </TableCell>

                    {/* Amount */}
                    <TableCell className="font-medium">
                      {formatAmount(disclosure.amount_range_min, disclosure.amount_range_max)}
                    </TableCell>

                    {/* Transaction Date */}
                    <TableCell className="text-muted-foreground">
                      {formatDate(disclosure.transaction_date)}
                    </TableCell>

                    {/* Disclosure Date */}
                    <TableCell className="text-muted-foreground">
                      {formatDate(disclosure.disclosure_date)}
                    </TableCell>

                    {/* Source Link */}
                    <TableCell>
                      {disclosure.source_url ? (
                        <a
                          href={disclosure.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center justify-center rounded-lg p-2 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
                          title="View original disclosure"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      ) : (
                        <span className="text-muted-foreground/50">-</span>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-6 py-4 border-t border-border/50">
          <div className="text-sm text-muted-foreground">
            Showing {offset + 1} - {Math.min(offset + ROWS_PER_PAGE, total)} of {total.toLocaleString()}
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <span className="text-sm text-muted-foreground px-2">
              Page {page + 1} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Attribution Footer */}
      <div className="px-6 py-3 border-t border-border/50 bg-muted/30">
        <p className="text-xs text-muted-foreground text-center">
          This is a free public resource. Data is collected from public STOCK Act disclosures and{' '}
          <a
            href="https://www.capitoltrades.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:underline"
          >
            Capitol Trades
          </a>
          . For the most accurate and complete data, please verify with official sources.
        </p>
      </div>
    </div>
  );
};

export default LandingTradesTable;
