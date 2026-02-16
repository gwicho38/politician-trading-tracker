import { useEffect, useState, useMemo } from 'react';
import { Loader2, ChevronRight, ArrowUpDown, ArrowUp, ArrowDown, X, Search } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { usePoliticians, type Politician } from '@/hooks/useSupabaseData';
import { usePagination } from '@/hooks/usePagination';
import { PaginationControls } from '@/components/PaginationControls';
import { formatCurrency } from '@/lib/mockData';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { cn, formatChamber } from '@/lib/utils';
import { PoliticianProfileModal } from '@/components/detail-modals';
import { useParties } from '@/hooks/useParties';
import { buildPartyMap, getPartyLabel, partyColorStyle, partyBadgeStyle, buildPartyFilterOptions } from '@/lib/partyUtils';

// Chamber filter options (value matches politician.role in the database)
const CHAMBER_FILTER_OPTIONS = [
  { value: '', label: 'All Chambers' },
  { value: 'Representative', label: 'House' },
  { value: 'Senator', label: 'Senate' },
  { value: 'MEP', label: 'EU Parliament' },
];

// Party filter options are now built dynamically from the parties table via useParties()

// Sortable fields for politicians
type SortField = 'name' | 'party' | 'chamber' | 'state' | 'total_volume' | 'total_trades';
type SortDirection = 'asc' | 'desc';

interface PoliticiansViewProps {
  initialPoliticianId?: string | null;
  onPoliticianSelected?: () => void;
}

const PoliticiansView = ({ initialPoliticianId, onPoliticianSelected }: PoliticiansViewProps) => {
  const { data: politicians, isLoading, error } = usePoliticians();
  const { data: parties = [] } = useParties();
  const partyMap = useMemo(() => buildPartyMap(parties), [parties]);
  const PARTY_FILTER_OPTIONS = useMemo(() => buildPartyFilterOptions(parties), [parties]);
  const pagination = usePagination();
  const [selectedPolitician, setSelectedPolitician] = useState<Politician | null>(null);
  const [sortField, setSortField] = useState<SortField>('total_volume');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [chamberFilter, setChamberFilter] = useState('');
  const [partyFilter, setPartyFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // Handle column header click for sorting
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      // Toggle direction if same field
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      // New field, default to descending for numeric, ascending for text
      setSortField(field);
      setSortDirection(['total_volume', 'total_trades'].includes(field) ? 'desc' : 'asc');
    }
    pagination.setPage(1); // Reset to first page on sort change
  };

  // Get sort icon for a column
  const getSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <ArrowUpDown className="h-3 w-3 ml-1 opacity-50" />;
    }
    return sortDirection === 'asc'
      ? <ArrowUp className="h-3 w-3 ml-1 text-primary" />
      : <ArrowDown className="h-3 w-3 ml-1 text-primary" />;
  };

  // Sort politicians client-side
  const sortedPoliticians = useMemo(() => {
    if (!politicians) return [];

    return [...politicians].sort((a, b) => {
      let comparison = 0;

      switch (sortField) {
        case 'name':
          comparison = (a.name || '').localeCompare(b.name || '');
          break;
        case 'party':
          comparison = (a.party || '').localeCompare(b.party || '');
          break;
        case 'chamber':
          comparison = (a.chamber || '').localeCompare(b.chamber || '');
          break;
        case 'state':
          comparison = (a.state || '').localeCompare(b.state || '');
          break;
        case 'total_volume':
          comparison = (a.total_volume || 0) - (b.total_volume || 0);
          break;
        case 'total_trades':
          comparison = (a.total_trades || 0) - (b.total_trades || 0);
          break;
      }

      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [politicians, sortField, sortDirection]);

  // Apply filters to sorted politicians
  const filteredPoliticians = useMemo(() => {
    let result = sortedPoliticians;
    if (chamberFilter) {
      result = result.filter(p => p.role === chamberFilter);
    }
    if (partyFilter) {
      result = result.filter(p => p.party === partyFilter);
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter(p =>
        (p.name || '').toLowerCase().includes(q) ||
        (p.state || '').toLowerCase().includes(q)
      );
    }
    return result;
  }, [sortedPoliticians, chamberFilter, partyFilter, searchQuery]);

  // Update total items when filtered data changes
  useEffect(() => {
    pagination.setTotalItems(filteredPoliticians.length);
  }, [filteredPoliticians]);

  const hasActiveFilters = chamberFilter || partyFilter || searchQuery;

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

  // Get paginated politicians from filtered list
  const paginatedPoliticians = filteredPoliticians.slice(pagination.startIndex, pagination.endIndex);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <h2 className="text-2xl font-bold text-foreground">Politicians</h2>
          <p className="text-muted-foreground">
            All tracked politicians and their trading activity
          </p>
        </div>

        {/* Search and Filters */}
        <div className="flex flex-wrap gap-2 items-center">
          <div className="relative w-full sm:max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by name or state..."
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); pagination.setPage(1); }}
              className="pl-9 bg-background/50"
            />
            {searchQuery && (
              <button
                onClick={() => { setSearchQuery(''); pagination.setPage(1); }}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                aria-label="Clear search"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            )}
          </div>

          <Select value={chamberFilter || 'all'} onValueChange={(v) => { setChamberFilter(v === 'all' ? '' : v); pagination.setPage(1); }}>
            <SelectTrigger className="w-[140px] bg-background/50">
              <SelectValue placeholder="Chamber" />
            </SelectTrigger>
            <SelectContent>
              {CHAMBER_FILTER_OPTIONS.map((c) => (
                <SelectItem key={c.value} value={c.value || 'all'}>
                  {c.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={partyFilter || 'all'} onValueChange={(v) => { setPartyFilter(v === 'all' ? '' : v); pagination.setPage(1); }}>
            <SelectTrigger className="w-[130px] bg-background/50">
              <SelectValue placeholder="Party" />
            </SelectTrigger>
            <SelectContent>
              {PARTY_FILTER_OPTIONS.map((p) => (
                <SelectItem key={p.value} value={p.value || 'all'}>
                  {p.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => { setChamberFilter(''); setPartyFilter(''); setSearchQuery(''); pagination.setPage(1); }}
              className="gap-1 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
              Clear
            </Button>
          )}

          <span className="text-sm text-muted-foreground ml-auto">
            {filteredPoliticians.length.toLocaleString()} {hasActiveFilters ? 'matching' : 'total'}
          </span>
        </div>
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
              <button
                onClick={() => handleSort('name')}
                className="col-span-5 sm:col-span-4 flex items-center hover:text-foreground transition-colors text-left"
              >
                Politician
                {getSortIcon('name')}
              </button>
              <button
                onClick={() => handleSort('chamber')}
                className="col-span-2 hidden sm:flex items-center hover:text-foreground transition-colors text-left"
              >
                Chamber
                {getSortIcon('chamber')}
              </button>
              <button
                onClick={() => handleSort('total_volume')}
                className="col-span-3 sm:col-span-2 flex items-center justify-end hover:text-foreground transition-colors"
              >
                Volume
                {getSortIcon('total_volume')}
              </button>
              <button
                onClick={() => handleSort('total_trades')}
                className="col-span-3 sm:col-span-2 flex items-center justify-end hover:text-foreground transition-colors"
              >
                Trades
                {getSortIcon('total_trades')}
              </button>
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
                          className="text-xs px-1.5 py-0 flex-shrink-0"
                          style={{...partyBadgeStyle(partyMap, politician.party), ...partyColorStyle(partyMap, politician.party)}}
                        >
                          {getPartyLabel(partyMap, politician.party)}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground truncate sm:hidden">
                        {formatChamber(politician.chamber)}
                      </p>
                    </div>
                  </div>

                  {/* Chamber & State */}
                  <div className="col-span-2 hidden sm:block text-sm text-muted-foreground">
                    <p className="truncate">{formatChamber(politician.chamber)}</p>
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
