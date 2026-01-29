import { useState, useMemo, useEffect } from 'react';
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
  Copy,
  Check,
  Download,
  Calendar,
  Flag,
} from 'lucide-react';
import { formatDate, formatAmountRange } from '@/lib/formatters';
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/lib/utils';
import { useTradingDisclosures, SortField, SortDirection, TradingDisclosure } from '@/hooks/useSupabaseData';
import { ReportErrorModal } from '@/components/ReportErrorModal';
import { PoliticianProfileModal } from '@/components/detail-modals/PoliticianProfileModal';
import { getPartyColor, getPartyBg } from '@/lib/mockData';
import { toParty } from '@/lib/typeGuards';
import type { Politician } from '@/hooks/useSupabaseData';

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

interface LandingTradesTableProps {
  initialSearchQuery?: string;
  onSearchClear?: () => void;
}

const LandingTradesTable = ({ initialSearchQuery, onSearchClear }: LandingTradesTableProps = {}) => {
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
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  // Copy ticker state
  const [copiedTicker, setCopiedTicker] = useState<string | null>(null);

  // Report error modal state
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [selectedDisclosure, setSelectedDisclosure] = useState<TradingDisclosure | null>(null);

  // Mobile filter dialog state
  const [mobileFilterOpen, setMobileFilterOpen] = useState(false);

  // Politician profile modal state
  const [selectedPoliticianForProfile, setSelectedPoliticianForProfile] = useState<Politician | null>(null);

  const handleReportClick = (disclosure: TradingDisclosure) => {
    setSelectedDisclosure(disclosure);
    setReportModalOpen(true);
  };

  // Handle initial search query from props
  useEffect(() => {
    if (initialSearchQuery) {
      setSearchQuery(initialSearchQuery);
      setDebouncedSearch(initialSearchQuery);
      setPage(0);
      onSearchClear?.();
    }
  }, [initialSearchQuery, onSearchClear]);

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
  const { data, isLoading, error } = useTradingDisclosures({
    limit: ROWS_PER_PAGE,
    offset,
    searchQuery: debouncedSearch || undefined,
    transactionType: transactionType || undefined,
    party: party || undefined,
    dateFrom: dateFrom || undefined,
    dateTo: dateTo || undefined,
    sortField,
    sortDirection,
  });

  const disclosures = data?.disclosures || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / ROWS_PER_PAGE);

  // Check if any filters are active
  const hasActiveFilters = debouncedSearch || transactionType || party || dateFrom || dateTo;

  // Clear all filters
  const clearFilters = () => {
    setSearchQuery('');
    setDebouncedSearch('');
    setTransactionType('');
    setParty('');
    setDateFrom('');
    setDateTo('');
    setPage(0);
  };

  // Copy ticker to clipboard
  const copyTicker = async (ticker: string) => {
    try {
      await navigator.clipboard.writeText(ticker);
      setCopiedTicker(ticker);
      setTimeout(() => setCopiedTicker(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // Export to CSV
  const exportToCSV = () => {
    if (!disclosures.length) return;

    const headers = ['Politician', 'Party', 'Ticker', 'Asset Name', 'Type', 'Amount Min', 'Amount Max', 'Transaction Date', 'Disclosure Date'];
    const rows = disclosures.map(d => [
      d.politician?.name || 'Unknown',
      d.politician?.party || 'Unknown',
      d.asset_ticker || '',
      d.asset_name || '',
      d.transaction_type || '',
      d.amount_range_min || '',
      d.amount_range_max || '',
      d.transaction_date || '',
      d.disclosure_date || '',
    ]);

    const csvContent = [headers, ...rows]
      .map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
      .join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `politician-trades-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);
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

  // formatDate and formatAmountRange are now imported from '@/lib/formatters'
  // Alias formatAmountRange to formatAmount for backwards compatibility in this file
  const formatAmount = (min: number | null, max: number | null) => {
    if (min === null && max === null) return 'Not disclosed';
    return formatAmountRange(min, max);
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
            </div>
            <div className="text-sm text-muted-foreground">
              {total.toLocaleString()} {hasActiveFilters ? 'matching' : 'total'} disclosures
            </div>
          </div>

          {/* Search and Filters Row */}
          <div className="flex flex-col gap-3">
            {/* Search Input - Full width on mobile */}
            <div className="relative w-full sm:max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search ticker or company..."
                value={searchQuery}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="pl-9 bg-background/50"
              />
              {searchQuery && (
                <button
                  onClick={() => handleSearchChange('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  aria-label="Clear search"
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                </button>
              )}
            </div>

            {/* Filters Row */}
            <div className="flex flex-wrap gap-2 items-center">
              {/* Transaction Type Filter */}
              <Select value={transactionType || 'all'} onValueChange={(v) => { setTransactionType(v === 'all' ? '' : v); setPage(0); }}>
                <SelectTrigger className="w-[110px] sm:w-[130px] bg-background/50">
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
              <Select value={party || 'all'} onValueChange={(v) => { setParty(v === 'all' ? '' : v); setPage(0); }}>
                <SelectTrigger className="w-[110px] sm:w-[130px] bg-background/50">
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

              {/* Mobile Date Filter Button */}
              <Dialog open={mobileFilterOpen} onOpenChange={setMobileFilterOpen}>
                <DialogTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    className="sm:hidden gap-1"
                  >
                    <Calendar className="h-4 w-4" />
                    Dates
                    {(dateFrom || dateTo) && (
                      <Badge variant="secondary" className="h-4 w-4 p-0 flex items-center justify-center text-[10px]">
                        {(dateFrom ? 1 : 0) + (dateTo ? 1 : 0)}
                      </Badge>
                    )}
                  </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-md">
                  <DialogHeader>
                    <DialogTitle>Filter by Date</DialogTitle>
                  </DialogHeader>
                  <div className="flex flex-col gap-4 py-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">From Date</label>
                      <Input
                        type="date"
                        value={dateFrom}
                        onChange={(e) => { setDateFrom(e.target.value); setPage(0); }}
                        className="bg-background/50"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">To Date</label>
                      <Input
                        type="date"
                        value={dateTo}
                        onChange={(e) => { setDateTo(e.target.value); setPage(0); }}
                        className="bg-background/50"
                      />
                    </div>
                    {(dateFrom || dateTo) && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => { setDateFrom(''); setDateTo(''); setPage(0); }}
                        className="w-full"
                      >
                        Clear Dates
                      </Button>
                    )}
                    <Button
                      onClick={() => setMobileFilterOpen(false)}
                      className="w-full"
                    >
                      Apply
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>

              {/* Date Filters - Hidden on mobile */}
              <div className="hidden sm:flex gap-2">
                {/* Date From */}
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                  <Input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => { setDateFrom(e.target.value); setPage(0); }}
                    className="pl-9 w-[150px] bg-background/50"
                    title="From date"
                  />
                </div>

                {/* Date To */}
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                  <Input
                    type="date"
                    value={dateTo}
                    onChange={(e) => { setDateTo(e.target.value); setPage(0); }}
                    className="pl-9 w-[150px] bg-background/50"
                    title="To date"
                  />
                </div>
              </div>

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

              {/* Export CSV */}
              <Button
                variant="outline"
                size="sm"
                onClick={exportToCSV}
                disabled={disclosures.length === 0}
                className="gap-1 ml-auto"
              >
                <Download className="h-4 w-4" />
                Export
              </Button>
            </div>
          </div>

          {/* Active Filters Display */}
          {hasActiveFilters && (
            <div className="flex flex-wrap gap-2 items-center">
              <Filter className="h-4 w-4 text-muted-foreground" />
              {debouncedSearch && (
                <Badge variant="secondary" className="gap-1">
                  Search: "{debouncedSearch}"
                  <button onClick={() => handleSearchChange('')} aria-label="Clear search filter">
                    <X className="h-3 w-3" aria-hidden="true" />
                  </button>
                </Badge>
              )}
              {transactionType && (
                <Badge variant="secondary" className="gap-1">
                  Type: {transactionType}
                  <button onClick={() => { setTransactionType(''); setPage(0); }} aria-label="Clear transaction type filter">
                    <X className="h-3 w-3" aria-hidden="true" />
                  </button>
                </Badge>
              )}
              {party && (
                <Badge variant="secondary" className="gap-1">
                  Party: {party}
                  <button onClick={() => { setParty(''); setPage(0); }} aria-label="Clear party filter">
                    <X className="h-3 w-3" aria-hidden="true" />
                  </button>
                </Badge>
              )}
              {dateFrom && (
                <Badge variant="secondary" className="gap-1">
                  From: {dateFrom}
                  <button onClick={() => { setDateFrom(''); setPage(0); }} aria-label="Clear start date filter">
                    <X className="h-3 w-3" aria-hidden="true" />
                  </button>
                </Badge>
              )}
              {dateTo && (
                <Badge variant="secondary" className="gap-1">
                  To: {dateTo}
                  <button onClick={() => { setDateTo(''); setPage(0); }} aria-label="Clear end date filter">
                    <X className="h-3 w-3" aria-hidden="true" />
                  </button>
                </Badge>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Mobile Card View */}
      <div className="sm:hidden">
        {error ? (
          <div className="py-12 px-4 text-center">
            <div className="text-destructive font-semibold mb-2">Failed to load data</div>
            <div className="text-sm text-muted-foreground">
              There was an error loading trading disclosures. Please try again later.
            </div>
            {error instanceof Error && (
              <div className="text-xs text-muted-foreground mt-2 font-mono">
                {error.message}
              </div>
            )}
          </div>
        ) : isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : disclosures.length === 0 ? (
          <div className="py-12 text-center text-muted-foreground">
            {hasActiveFilters
              ? 'No disclosures match your filters'
              : 'No trading disclosures found'}
          </div>
        ) : (
          <div className="grid grid-cols-1 xs:grid-cols-2 gap-3 p-3 sm:p-4">
            {disclosures.map((disclosure) => {
              const politician = disclosure.politician;
              const partyValue = toParty(politician?.party);
              const isBuy = disclosure.transaction_type === 'purchase';
              const isSell = disclosure.transaction_type === 'sale';

              return (
                <div
                  key={disclosure.id}
                  className={cn(
                    "relative rounded-xl border p-3 flex flex-col gap-2",
                    isBuy && "border-success/30 bg-success/5",
                    isSell && "border-destructive/30 bg-destructive/5",
                    !isBuy && !isSell && "border-border/50 bg-card/60"
                  )}
                >
                  {/* Transaction Type Indicator */}
                  <div className="flex items-center justify-between">
                    <Badge
                      variant={isBuy ? 'buy' : isSell ? 'sell' : 'outline'}
                      className="text-[10px] px-1.5 py-0 gap-0.5"
                    >
                      {isBuy && <ArrowUpRight className="h-2.5 w-2.5" />}
                      {isSell && <ArrowDownRight className="h-2.5 w-2.5" />}
                      {disclosure.transaction_type.charAt(0).toUpperCase() + disclosure.transaction_type.slice(1)}
                    </Badge>
                    {disclosure.source_url && (
                      <a
                        href={disclosure.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-muted-foreground hover:text-foreground"
                        aria-label="View original disclosure document"
                      >
                        <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                      </a>
                    )}
                  </div>

                  {/* Ticker - Prominent */}
                  <div className="flex items-center gap-1.5">
                    {disclosure.asset_ticker && (
                      <span className="font-mono text-lg font-bold text-primary">
                        {disclosure.asset_ticker}
                      </span>
                    )}
                    <Badge
                      variant="outline"
                      className={cn(
                        "text-[9px] px-1 py-0",
                        getPartyBg(partyValue),
                        getPartyColor(partyValue)
                      )}
                    >
                      {partyValue}
                    </Badge>
                  </div>

                  {/* Amount - Most Prominent */}
                  <div className={cn(
                    "text-xl font-bold",
                    isBuy && "text-success",
                    isSell && "text-destructive",
                    !isBuy && !isSell && "text-foreground"
                  )}>
                    {formatAmount(disclosure.amount_range_min, disclosure.amount_range_max)}
                  </div>

                  {/* Politician Name */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (politician) setSelectedPoliticianForProfile(politician);
                    }}
                    className="text-xs text-muted-foreground truncate hover:text-primary hover:underline transition-colors text-left"
                  >
                    {politician?.name || 'Unknown'}
                  </button>

                  {/* Date */}
                  <div className="text-[10px] text-muted-foreground/70">
                    {formatDate(disclosure.disclosure_date)}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Desktop Table View */}
      <div className="hidden sm:block overflow-x-auto">
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
              <TableHead className="w-[100px] hidden sm:table-cell">
                <button
                  className="flex items-center hover:text-foreground transition-colors"
                  onClick={() => handleSort('transaction_type')}
                >
                  Type
                  {getSortIcon('transaction_type')}
                </button>
              </TableHead>
              <TableHead className="w-[160px] hidden md:table-cell">
                <button
                  className="flex items-center hover:text-foreground transition-colors"
                  onClick={() => handleSort('amount_range_max')}
                >
                  Amount
                  {getSortIcon('amount_range_max')}
                </button>
              </TableHead>
              <TableHead className="w-[120px] hidden lg:table-cell">
                <button
                  className="flex items-center hover:text-foreground transition-colors"
                  onClick={() => handleSort('transaction_date')}
                >
                  Transaction
                  {getSortIcon('transaction_date')}
                </button>
              </TableHead>
              <TableHead className="w-[120px] hidden sm:table-cell">
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
            {error ? (
              <TableRow>
                <TableCell colSpan={7} className="h-32 text-center">
                  <div className="text-destructive font-semibold mb-2">Failed to load data</div>
                  <div className="text-sm text-muted-foreground">
                    There was an error loading trading disclosures. Please try again later.
                  </div>
                  {error instanceof Error && (
                    <div className="text-xs text-muted-foreground mt-2 font-mono">
                      {error.message}
                    </div>
                  )}
                </TableCell>
              </TableRow>
            ) : isLoading ? (
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
                const partyValue = toParty(politician?.party);

                return (
                  <TableRow key={disclosure.id} className="group">
                    {/* Politician */}
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            if (politician) setSelectedPoliticianForProfile(politician);
                          }}
                          className="font-medium text-foreground hover:text-primary hover:underline transition-colors text-left"
                        >
                          {politician?.name || 'Unknown'}
                        </button>
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
                          <div className="flex items-center gap-1">
                            <span className="font-mono text-sm font-semibold text-primary">
                              {disclosure.asset_ticker}
                            </span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                copyTicker(disclosure.asset_ticker!);
                              }}
                              className="p-1 rounded hover:bg-secondary transition-colors opacity-0 group-hover:opacity-100"
                              aria-label={`Copy ticker ${disclosure.asset_ticker}`}
                            >
                              {copiedTicker === disclosure.asset_ticker ? (
                                <Check className="h-3 w-3 text-success" aria-hidden="true" />
                              ) : (
                                <Copy className="h-3 w-3 text-muted-foreground" aria-hidden="true" />
                              )}
                            </button>
                          </div>
                        )}
                        <span className="text-sm text-muted-foreground truncate max-w-[180px]">
                          {disclosure.asset_name}
                        </span>
                      </div>
                      {disclosure.asset_type && (
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 mt-1 font-normal">
                          {disclosure.asset_type}
                        </Badge>
                      )}
                    </TableCell>

                    {/* Transaction Type */}
                    <TableCell className="hidden sm:table-cell">
                      {getTransactionBadge(disclosure.transaction_type)}
                    </TableCell>

                    {/* Amount */}
                    <TableCell className="font-medium hidden md:table-cell">
                      {formatAmount(disclosure.amount_range_min, disclosure.amount_range_max)}
                    </TableCell>

                    {/* Transaction Date */}
                    <TableCell className="text-muted-foreground hidden lg:table-cell">
                      {formatDate(disclosure.transaction_date)}
                    </TableCell>

                    {/* Disclosure Date */}
                    <TableCell className="text-muted-foreground hidden sm:table-cell">
                      {formatDate(disclosure.disclosure_date)}
                    </TableCell>

                    {/* Source Link & Report */}
                    <TableCell>
                      <div className="flex items-center gap-1">
                        {disclosure.source_url ? (
                          <a
                            href={disclosure.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center justify-center rounded-lg p-2 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
                            aria-label="View original disclosure document"
                          >
                            <ExternalLink className="h-4 w-4" aria-hidden="true" />
                          </a>
                        ) : (
                          <span className="text-muted-foreground/50 p-2">-</span>
                        )}
                        <button
                          onClick={() => handleReportClick(disclosure)}
                          className="inline-flex items-center justify-center rounded-lg p-2 text-muted-foreground hover:bg-warning/10 hover:text-warning transition-colors opacity-0 group-hover:opacity-100"
                          aria-label="Report data error"
                        >
                          <Flag className="h-4 w-4" aria-hidden="true" />
                        </button>
                      </div>
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
        <div className="flex items-center justify-between px-4 sm:px-6 py-4 border-t border-border/50">
          <div className="text-xs sm:text-sm text-muted-foreground">
            <span className="hidden sm:inline">Showing </span>
            {offset + 1}-{Math.min(offset + ROWS_PER_PAGE, total)}
            <span className="hidden sm:inline"> of {total.toLocaleString()}</span>
          </div>
          <div className="flex items-center gap-1 sm:gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-2 sm:px-3"
            >
              <ChevronLeft className="h-4 w-4" />
              <span className="hidden sm:inline ml-1">Previous</span>
            </Button>
            <span className="text-xs sm:text-sm text-muted-foreground px-1 sm:px-2">
              {page + 1}/{totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="px-2 sm:px-3"
            >
              <span className="hidden sm:inline mr-1">Next</span>
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
            href="https://www.govmarket.trade"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:underline"
          >
            GovMarket
          </a>
          . For the most accurate and complete data, please verify with official sources.
        </p>
      </div>

      {/* Report Error Modal */}
      <ReportErrorModal
        disclosure={selectedDisclosure}
        open={reportModalOpen}
        onOpenChange={setReportModalOpen}
      />

      {/* Politician Profile Modal */}
      <PoliticianProfileModal
        politician={selectedPoliticianForProfile}
        open={!!selectedPoliticianForProfile}
        onOpenChange={(open) => !open && setSelectedPoliticianForProfile(null)}
      />
    </div>
  );
};

export default LandingTradesTable;
