import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, User, TrendingUp, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useGlobalSearch, type SearchResult } from '@/hooks/useGlobalSearch';
import { getPartyColor, getPartyBg } from '@/lib/mockData';
import { toParty, getPartyLabel } from '@/lib/typeGuards';
import { cn } from '@/lib/utils';

interface GlobalSearchProps {
  onSelectPolitician?: (id: string) => void;
  onSelectTicker?: (ticker: string) => void;
  /** If true, uses full width styling for mobile dialogs */
  fullWidth?: boolean;
  /** Called when a result is selected - useful for closing mobile dialogs */
  onResultSelect?: () => void;
}

export function GlobalSearch({ onSelectPolitician, onSelectTicker, fullWidth, onResultSelect }: GlobalSearchProps) {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data: results, isLoading } = useGlobalSearch(query);

  // Reset selection when results change
  useEffect(() => {
    setSelectedIndex(0);
  }, [results]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || !results || results.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => (prev + 1) % results.length);
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => (prev - 1 + results.length) % results.length);
        break;
      case 'Enter':
        e.preventDefault();
        handleSelect(results[selectedIndex]);
        break;
      case 'Escape':
        setIsOpen(false);
        inputRef.current?.blur();
        break;
    }
  };

  const handleSelect = (result: SearchResult) => {
    setQuery('');
    setIsOpen(false);

    if (result.type === 'politician') {
      // Navigate to politicians view and trigger selection
      if (onSelectPolitician) {
        onSelectPolitician(result.id);
      } else {
        // Navigate to politicians view with politician query param
        navigate(`/?view=politicians&politician=${result.id}`);
      }
    } else if (result.type === 'ticker') {
      // Navigate to dashboard with ticker filter (trades table has search)
      if (onSelectTicker) {
        onSelectTicker(result.id);
      } else {
        navigate(`/?ticker=${result.id}`);
      }
    }

    // Notify parent (useful for closing mobile dialogs)
    onResultSelect?.();
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
    setIsOpen(e.target.value.length >= 2);
  };

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          ref={inputRef}
          type="search"
          placeholder="Search politicians, tickers..."
          value={query}
          onChange={handleInputChange}
          onFocus={() => query.length >= 2 && setIsOpen(true)}
          onKeyDown={handleKeyDown}
          className={cn(
            "pl-9 bg-secondary/50 border-border/50 focus:border-primary/50",
            fullWidth ? "w-full" : "w-64"
          )}
        />
        {isLoading && (
          <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground animate-spin" />
        )}
      </div>

      {/* Results Dropdown */}
      {isOpen && query.length >= 2 && (
        <div className="absolute top-full left-0 right-0 mt-2 rounded-lg border border-border bg-popover shadow-lg overflow-hidden z-50">
          {isLoading ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : results && results.length > 0 ? (
            <div className="max-h-80 overflow-y-auto">
              {results.map((result, index) => (
                <button
                  key={`${result.type}-${result.id}`}
                  className={cn(
                    'w-full flex items-center gap-3 px-4 py-3 text-left transition-colors',
                    selectedIndex === index
                      ? 'bg-secondary'
                      : 'hover:bg-secondary/50'
                  )}
                  onClick={() => handleSelect(result)}
                  onMouseEnter={() => setSelectedIndex(index)}
                >
                  {/* Icon */}
                  <div className={cn(
                    'flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center',
                    result.type === 'politician' ? 'bg-primary/10' : 'bg-success/10'
                  )}>
                    {result.type === 'politician' ? (
                      <User className="h-4 w-4 text-primary" />
                    ) : (
                      <TrendingUp className="h-4 w-4 text-success" />
                    )}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={cn(
                        'font-medium truncate',
                        result.type === 'ticker' && 'font-mono'
                      )}>
                        {result.label}
                      </span>
                      {result.type === 'politician' && result.meta?.party && (
                        <Badge
                          variant="outline"
                          className={cn(
                            'text-xs px-1.5 py-0',
                            getPartyBg(result.meta.party),
                            getPartyColor(result.meta.party)
                          )}
                        >
                          {getPartyLabel(toParty(result.meta.party))}
                        </Badge>
                      )}
                    </div>
                    {result.sublabel && (
                      <p className="text-xs text-muted-foreground truncate">
                        {result.sublabel}
                      </p>
                    )}
                  </div>

                  {/* Trade count */}
                  {result.meta?.tradeCount !== undefined && (
                    <span className="text-xs text-muted-foreground">
                      {result.meta.tradeCount} trades
                    </span>
                  )}
                </button>
              ))}
            </div>
          ) : (
            <div className="py-6 text-center text-sm text-muted-foreground">
              No results found for "{query}"
            </div>
          )}
        </div>
      )}
    </div>
  );
}
