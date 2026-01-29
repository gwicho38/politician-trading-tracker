import { useState } from 'react';
import { Loader2, TrendingUp, TrendingDown, ChevronDown, ChevronUp } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  useReferencePortfolioPositions,
  ReferencePortfolioPosition,
} from '@/hooks/useReferencePortfolio';
import { formatCurrencyFull } from '@/lib/formatters';

// Use centralized formatter with null safety wrapper
const formatCurrency = (value: number | null) => {
  if (value === null || value === undefined) return '-';
  return formatCurrencyFull(value);
};

const formatPercent = (value: number | null) => {
  if (value === null || value === undefined) return '-';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
};

interface SortConfig {
  key: keyof ReferencePortfolioPosition | 'ticker';
  direction: 'asc' | 'desc';
}

export function HoldingsTable() {
  const { data: positions, isLoading, error } = useReferencePortfolioPositions(false);
  const [sortConfig, setSortConfig] = useState<SortConfig>({ key: 'market_value', direction: 'desc' });

  const handleSort = (key: SortConfig['key']) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc',
    }));
  };

  const sortedPositions = [...(positions || [])].sort((a, b) => {
    const aValue = a[sortConfig.key as keyof ReferencePortfolioPosition];
    const bValue = b[sortConfig.key as keyof ReferencePortfolioPosition];

    if (aValue === null || aValue === undefined) return 1;
    if (bValue === null || bValue === undefined) return -1;

    if (typeof aValue === 'string' && typeof bValue === 'string') {
      return sortConfig.direction === 'asc'
        ? aValue.localeCompare(bValue)
        : bValue.localeCompare(aValue);
    }

    if (typeof aValue === 'number' && typeof bValue === 'number') {
      return sortConfig.direction === 'asc' ? aValue - bValue : bValue - aValue;
    }

    return 0;
  });

  const SortIcon = ({ columnKey }: { columnKey: SortConfig['key'] }) => {
    if (sortConfig.key !== columnKey) return null;
    return sortConfig.direction === 'asc' ? (
      <ChevronUp className="h-3 w-3 inline ml-1" />
    ) : (
      <ChevronDown className="h-3 w-3 inline ml-1" />
    );
  };

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-6">
        <h3 className="text-lg font-semibold text-foreground mb-4">Current Holdings</h3>
        <div className="flex items-center justify-center h-40">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-6">
        <h3 className="text-lg font-semibold text-foreground mb-4">Current Holdings</h3>
        <div className="flex items-center justify-center h-40 text-muted-foreground">
          Failed to load positions
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border/50 bg-card/60 backdrop-blur-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-foreground">Current Holdings</h3>
          <p className="text-sm text-muted-foreground">
            {positions?.length || 0} open position{positions?.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>

      {sortedPositions.length === 0 ? (
        <div className="flex items-center justify-center h-40 text-muted-foreground">
          No open positions
        </div>
      ) : (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-auto p-0 font-medium text-xs"
                    onClick={() => handleSort('ticker')}
                  >
                    Ticker <SortIcon columnKey="ticker" />
                  </Button>
                </TableHead>
                <TableHead className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-auto p-0 font-medium text-xs"
                    onClick={() => handleSort('quantity')}
                  >
                    Shares <SortIcon columnKey="quantity" />
                  </Button>
                </TableHead>
                <TableHead className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-auto p-0 font-medium text-xs"
                    onClick={() => handleSort('entry_price')}
                  >
                    Entry <SortIcon columnKey="entry_price" />
                  </Button>
                </TableHead>
                <TableHead className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-auto p-0 font-medium text-xs"
                    onClick={() => handleSort('current_price')}
                  >
                    Current <SortIcon columnKey="current_price" />
                  </Button>
                </TableHead>
                <TableHead className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-auto p-0 font-medium text-xs"
                    onClick={() => handleSort('market_value')}
                  >
                    Value <SortIcon columnKey="market_value" />
                  </Button>
                </TableHead>
                <TableHead className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-auto p-0 font-medium text-xs"
                    onClick={() => handleSort('unrealized_pl')}
                  >
                    P&L <SortIcon columnKey="unrealized_pl" />
                  </Button>
                </TableHead>
                <TableHead className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-auto p-0 font-medium text-xs"
                    onClick={() => handleSort('entry_confidence')}
                  >
                    Confidence <SortIcon columnKey="entry_confidence" />
                  </Button>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedPositions.map((position) => {
                const isProfit = (position.unrealized_pl || 0) >= 0;
                return (
                  <TableRow key={position.id} className="hover:bg-muted/30">
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-foreground">{position.ticker}</span>
                        <Badge variant="outline" className="text-xs">
                          {position.side}
                        </Badge>
                      </div>
                      {position.asset_name && (
                        <p className="text-xs text-muted-foreground truncate max-w-[150px]">
                          {position.asset_name}
                        </p>
                      )}
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {position.quantity}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCurrency(position.entry_price)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatCurrency(position.current_price)}
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {formatCurrency(position.market_value)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        {isProfit ? (
                          <TrendingUp className="h-3 w-3 text-success" />
                        ) : (
                          <TrendingDown className="h-3 w-3 text-destructive" />
                        )}
                        <span className={isProfit ? 'text-success' : 'text-destructive'}>
                          {formatCurrency(position.unrealized_pl)}
                        </span>
                      </div>
                      <p className={`text-xs ${isProfit ? 'text-success' : 'text-destructive'}`}>
                        {formatPercent(position.unrealized_pl_pct)}
                      </p>
                    </TableCell>
                    <TableCell className="text-right">
                      <Badge
                        variant={
                          (position.entry_confidence || 0) >= 0.85
                            ? 'default'
                            : (position.entry_confidence || 0) >= 0.75
                            ? 'secondary'
                            : 'outline'
                        }
                        className="text-xs"
                      >
                        {((position.entry_confidence || 0) * 100).toFixed(0)}%
                      </Badge>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
