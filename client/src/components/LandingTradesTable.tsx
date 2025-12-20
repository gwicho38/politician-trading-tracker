import { useState, useMemo } from 'react';
import {
  ExternalLink,
  ArrowUpRight,
  ArrowDownRight,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Search,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  X,
  Filter,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/lib/utils';
import { useTradingDisclosures, SortField, SortDirection } from '@/hooks/useSupabaseData';
import { getPartyColor, getPartyBg } from '@/lib/mockData';

const ROWS_PER_PAGE = 15;

// Transaction type options
const TRANSACTION_TYPES = [
  { value: '', label: 'All Types' },
  { value: 'purchase', label: 'Purchase' },
  { value: 'sale', label: 'Sale' },
  { value: 'exchange', label: 'Exchange' },
  { value: 'holding', label: 'Holding' },
];

// Party options
const PARTY_OPTIONS = [
  { value: '', label: 'All Parties' },
  { value: 'D', label: 'Democrat' },
  { value: 'R', label: 'Republican' },
  { value: 'I', label: 'Independent' },
];

// Sortable column configuration
interface SortableColumn {
  field: SortField;
  label: string;
}

const SORTABLE_COLUMNS: SortableColumn[] = [
  { field: 'disclosure_date', label: 'Disclosed' },
  { field: 'transaction_date', label: 'Transaction' },
  { field: 'amount_range_max', label: 'Amount' },
  { field: 'asset_ticker', label: 'Ticker' },
  { field: 'transaction_type', label: 'Type' },
];

const LandingTradesTable = () => {
  // Pagination
  const [page, setPage] = useState(0);

  // Sorting
  const [sortField, setSortField] = useState<SortField>('disclosure_date');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [transactionType, setTransactionType] = useState('');
  const [party, setParty] = useState('');

  // Debounce search
  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    // Simple debounce
    setTimeout(() => {
      setDebouncedSearch(value);
      setPage(0); // Reset to first page on search
    }, 300);
  };

  // Calculate offset
  const offset = page * ROWS_PER_PAGE;

  // Fetch data with all filters
  const { data, isLoading } = useTradingDisclosures({
    limit: ROWS_PER_PAGE,
    offset,
    searchQuery: debouncedSearch || undefined,
    transactionType: transactionType || undefined,
    party: party || undefined,
    sortField,
    sortDirection,
  });

  const disclosures = data?.disclosures || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / ROWS_PER_PAGE);

  // Check if any filters are active
  const hasActiveFilters = debouncedSearch || transactionType || party;

  // Clear all filters
  const clearFilters = () => {
    setSearchQuery('');
    setDebouncedSearch('');
    setTransactionType('');
    setParty('');
    setPage(0);
  };

  // Handle sort click
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      // Toggle direction if same field
      setSortDirection(prev => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      // New field, default to descending
      setSortField(field);
      setSortDirection('desc');
    }
    setPage(0); // Reset to first page on sort
  };

  // Get sort icon for a column
  const getSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <ArrowUpDown className="h-3 w-3 ml-1 opacity-50" />;
    }
    return sortDirection === 'asc' ? (
      <ArrowUp className="h-3 w-3 ml-1 text-primary" />
    ) : (
      <ArrowDown className="h-3 w-3 ml-1 text-primary" />
    );
  };

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
        <div className="flex flex-col gap-4">
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
              {total.toLocaleString()} {hasActiveFilters ? 'matching' : 'total'} disclosures
            </div>
          </div>

          {/* Search and Filters Row */}
          <div className="flex flex-col sm:flex-row gap-3">
            {/* Search Input */}
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by ticker (e.g., AAPL, MSFT)..."
                value={searchQuery}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="pl-9 bg-background/50"
              />
              {searchQuery && (
                <button
                  onClick={() => handleSearchChange('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>

            {/* Transaction Type Filter */}
            <Select value={transactionType} onValueChange={(v) => { setTransactionType(v); setPage(0); }}>
              <SelectTrigger className="w-[140px] bg-background/50">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                {TRANSACTION_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value || 'all'}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Party Filter */}
            <Select value={party} onValueChange={(v) => { setParty(v === 'all' ? '' : v); setPage(0); }}>
              <SelectTrigger className="w-[140px] bg-background/50">
                <SelectValue placeholder="Party" />
              </SelectTrigger>
              <SelectContent>
                {PARTY_OPTIONS.map((p) => (
                  <SelectItem key={p.value} value={p.value || 'all'}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Clear Filters */}
            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearFilters}
                className="gap-1 text-muted-foreground hover:text-foreground"
              >
                <X className="h-4 w-4" />
                Clear
              </Button>
            )}
          </div>

          {/* Active Filters Display */}
          {hasActiveFilters && (
            <div className="flex flex-wrap gap-2 items-center">
              <Filter className="h-4 w-4 text-muted-foreground" />
              {debouncedSearch && (
                <Badge variant="secondary" className="gap-1">
                  Search: "{debouncedSearch}"
                  <button onClick={() => handleSearchChange('')}>
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              )}
              {transactionType && (
                <Badge variant="secondary" className="gap-1">
                  Type: {transactionType}
                  <button onClick={() => { setTransactionType(''); setPage(0); }}>
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              )}
              {party && (
                <Badge variant="secondary" className="gap-1">
                  Party: {party}
                  <button onClick={() => { setParty(''); setPage(0); }}>
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-[180px]">Politician</TableHead>
              <TableHead>
                <button
                  className="flex items-center hover:text-foreground transition-colors"
                  onClick={() => handleSort('asset_ticker')}
                >
                  Asset
                  {getSortIcon('asset_ticker')}
                </button>
              </TableHead>
              <TableHead className="w-[100px]">
                <button
                  className="flex items-center hover:text-foreground transition-colors"
                  onClick={() => handleSort('transaction_type')}
                >
                  Type
                  {getSortIcon('transaction_type')}
                </button>
              </TableHead>
              <TableHead className="w-[160px]">
                <button
                  className="flex items-center hover:text-foreground transition-colors"
                  onClick={() => handleSort('amount_range_max')}
                >
                  Amount
                  {getSortIcon('amount_range_max')}
                </button>
              </TableHead>
              <TableHead className="w-[120px]">
                <button
                  className="flex items-center hover:text-foreground transition-colors"
                  onClick={() => handleSort('transaction_date')}
                >
                  Transaction
                  {getSortIcon('transaction_date')}
                </button>
              </TableHead>
              <TableHead className="w-[120px]">
                <button
                  className="flex items-center hover:text-foreground transition-colors"
                  onClick={() => handleSort('disclosure_date')}
                >
                  Disclosed
                  {getSortIcon('disclosure_date')}
                </button>
              </TableHead>
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
                  {hasActiveFilters
                    ? 'No disclosures match your filters'
                    : 'No trading disclosures found'}
                </TableCell>
              </TableRow>
            ) : (
              disclosures.map((disclosure) => {
                const politician = disclosure.politician;
                const partyValue = (politician?.party || 'Unknown') as 'D' | 'R' | 'I' | 'Other';

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
                            getPartyBg(partyValue),
                            getPartyColor(partyValue)
                          )}
                        >
                          {partyValue}
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
              Page {page + 1} of {totalPages.toLocaleString()}
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
