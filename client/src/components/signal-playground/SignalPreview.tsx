/**
 * SignalPreview Component
 * Right panel showing signal preview results with charts and tables
 */

import { useMemo, useState } from 'react';
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  AlertCircle,
  Loader2,
  Maximize2,
  Minimize2,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  ShoppingCart,
  X,
} from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Legend, ResponsiveContainer } from 'recharts';
import { SIGNAL_TYPE_CONFIG } from '@/lib/signal-weights';
import { useCart } from '@/contexts/CartContext';
import type { CartSignal } from '@/types/cart';
import type {
  PreviewSignal,
  PreviewStats,
  SignalType,
} from '@/types/signal-playground';

interface SignalPreviewProps {
  signals: PreviewSignal[];
  stats?: PreviewStats;
  isLoading?: boolean;
  isUpdating?: boolean;
  error?: Error | null;
}

const PAGE_SIZE_OPTIONS = [10, 20, 50, 100];

/**
 * Pagination controls component
 */
function TablePagination({
  currentPage,
  totalPages,
  pageSize,
  totalItems,
  onPageChange,
  onPageSizeChange,
}: {
  currentPage: number;
  totalPages: number;
  pageSize: number;
  totalItems: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
}) {
  const startItem = (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalItems);

  return (
    <div className="flex items-center justify-between px-2 py-3 border-t">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span>Rows per page:</span>
        <Select
          value={String(pageSize)}
          onValueChange={(value) => onPageSizeChange(Number(value))}
        >
          <SelectTrigger className="h-8 w-[70px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PAGE_SIZE_OPTIONS.map((size) => (
              <SelectItem key={size} value={String(size)}>
                {size}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">
          {startItem}-{endItem} of {totalItems}
        </span>
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => onPageChange(1)}
            disabled={currentPage === 1}
          >
            <ChevronsLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage === 1}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => onPageChange(totalPages)}
            disabled={currentPage === totalPages}
          >
            <ChevronsRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

/**
 * Stats cards showing key metrics
 */
function StatsCards({ stats, signals }: { stats?: PreviewStats; signals: PreviewSignal[] }) {
  // Calculate unique tickers from actual signals, not source data
  const uniqueTickerCount = useMemo(() => {
    const tickers = new Set(signals.map((s) => s.ticker));
    return tickers.size;
  }, [signals]);

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Total Signals
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{signals.length}</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Unique Tickers
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{uniqueTickerCount}</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1">
            <TrendingUp className="h-4 w-4 text-green-500" />
            Buy Signals
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-green-600">
            {(stats?.signalTypeDistribution?.strong_buy || 0) +
              (stats?.signalTypeDistribution?.buy || 0)}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1">
            <TrendingDown className="h-4 w-4 text-red-500" />
            Sell Signals
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-red-600">
            {(stats?.signalTypeDistribution?.strong_sell || 0) +
              (stats?.signalTypeDistribution?.sell || 0)}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * Map label back to SignalType
 */
const labelToSignalType: Record<string, SignalType> = {
  'Strong Buy': 'strong_buy',
  'Buy': 'buy',
  'Hold': 'hold',
  'Sell': 'sell',
  'Strong Sell': 'strong_sell',
};

/**
 * Interactive pie chart showing signal type distribution with legend
 * Clicking a segment filters to show those signals
 */
type PieTableSortField = 'ticker' | 'confidence_score' | 'total_transaction_volume' | 'politician_activity_count';

function SignalDistributionChart({
  stats,
  signals,
  selectedType,
  onSelectType,
}: {
  stats?: PreviewStats;
  signals: PreviewSignal[];
  selectedType: SignalType | null;
  onSelectType: (type: SignalType | null) => void;
}) {
  // State for maximizing the signals table
  const [isMaximized, setIsMaximized] = useState(false);

  // Sort state for the filtered signals table
  const [tableSortField, setTableSortField] = useState<PieTableSortField>('confidence_score');
  const [tableSortDirection, setTableSortDirection] = useState<SortDirection>('desc');

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const handleTableSort = (field: PieTableSortField) => {
    if (field === tableSortField) {
      setTableSortDirection(tableSortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setTableSortField(field);
      setTableSortDirection('desc');
    }
    setCurrentPage(1); // Reset to first page on sort change
  };

  const handlePageSizeChange = (size: number) => {
    setPageSize(size);
    setCurrentPage(1);
  };

  // Order signal types logically: strong buy -> buy -> hold -> sell -> strong sell
  const signalOrder: SignalType[] = ['strong_buy', 'buy', 'hold', 'sell', 'strong_sell'];

  const data = useMemo(() => {
    if (!stats?.signalTypeDistribution) return [];

    return signalOrder
      .filter((type) => (stats.signalTypeDistribution[type] || 0) > 0)
      .map((type) => ({
        name: SIGNAL_TYPE_CONFIG[type].label,
        type,
        value: stats.signalTypeDistribution[type] || 0,
        fill: SIGNAL_TYPE_CONFIG[type].color,
      }));
  }, [stats]);

  // Filter and sort signals by selected type
  const sortedFilteredSignals = useMemo(() => {
    if (!selectedType) return [];
    const filtered = signals.filter((s) => s.signal_type === selectedType);

    return filtered.sort((a, b) => {
      const aVal = a[tableSortField];
      const bVal = b[tableSortField];

      if (typeof aVal === 'string') {
        return tableSortDirection === 'asc'
          ? aVal.localeCompare(bVal as string)
          : (bVal as string).localeCompare(aVal);
      }

      return tableSortDirection === 'asc'
        ? (aVal as number) - (bVal as number)
        : (bVal as number) - (aVal as number);
    });
  }, [signals, selectedType, tableSortField, tableSortDirection]);

  // Paginated signals for display
  const totalPages = Math.ceil(sortedFilteredSignals.length / pageSize);
  const paginatedSignals = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    return sortedFilteredSignals.slice(startIndex, startIndex + pageSize);
  }, [sortedFilteredSignals, currentPage, pageSize]);

  // Reset page when selection changes
  useMemo(() => {
    setCurrentPage(1);
  }, [selectedType]);

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-[250px] text-muted-foreground">
        No signal data
      </div>
    );
  }

  const handlePieClick = (data: any) => {
    if (data && data.type) {
      // Toggle selection
      onSelectType(selectedType === data.type ? null : data.type);
    }
  };

  return (
    <div className={`h-full flex flex-col ${isMaximized ? '' : 'space-y-4'}`}>
      {/* Hide pie chart when maximized */}
      {!isMaximized && (
      <div className="flex-1 min-h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="45%"
              outerRadius={90}
              innerRadius={40}
              onClick={handlePieClick}
              cursor="pointer"
            >
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.fill}
                  opacity={selectedType && selectedType !== entry.type ? 0.3 : 1}
                  stroke={selectedType === entry.type ? '#fff' : 'transparent'}
                  strokeWidth={selectedType === entry.type ? 2 : 0}
                />
              ))}
            </Pie>
            <Legend
              layout="horizontal"
              verticalAlign="bottom"
              align="center"
              onClick={(e) => {
                const type = labelToSignalType[e.value];
                if (type) onSelectType(selectedType === type ? null : type);
              }}
              formatter={(value, entry: any) => {
                const item = data.find((d) => d.name === value);
                const isSelected = selectedType === item?.type;
                return (
                  <span
                    style={{
                      color: entry.color,
                      opacity: selectedType && !isSelected ? 0.5 : 1,
                      cursor: 'pointer',
                      textDecoration: isSelected ? 'underline' : 'none',
                    }}
                  >
                    {value}: {item?.value || 0}
                  </span>
                );
              }}
            />
            <ChartTooltip
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null;
                const item = payload[0];
                return (
                  <div className="bg-background border rounded-lg shadow-lg p-2 text-sm">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: item.payload.fill }}
                      />
                      <span className="font-medium">{item.name}</span>
                    </div>
                    <div className="text-muted-foreground">
                      {item.value} signals ({((item.value as number / data.reduce((a, b) => a + b.value, 0)) * 100).toFixed(1)}%)
                    </div>
                    <div className="text-xs text-primary mt-1">Click to view tickers</div>
                  </div>
                );
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      )}

      {/* Selected type signals table */}
      {selectedType && sortedFilteredSignals.length > 0 && (
        <div className={`border rounded-lg p-3 flex flex-col ${isMaximized ? 'flex-1 bg-background' : 'bg-secondary/30'}`}>
          <div className="flex items-center justify-between mb-2 shrink-0">
            <div className="flex items-center gap-2">
              <SignalTypeBadge type={selectedType} />
              <span className="text-sm text-muted-foreground">
                {sortedFilteredSignals.length} tickers
              </span>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsMaximized(!isMaximized)}
                className="text-xs h-6 px-2"
              >
                {isMaximized ? (
                  <Minimize2 className="h-3 w-3" />
                ) : (
                  <Maximize2 className="h-3 w-3" />
                )}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  onSelectType(null);
                  setIsMaximized(false);
                }}
                className="text-xs h-6"
              >
                Clear
              </Button>
            </div>
          </div>
          <div className={isMaximized ? 'flex-1 overflow-y-auto' : 'max-h-[200px] overflow-y-auto'}>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-20">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="-ml-3 h-8 hover:bg-transparent"
                      onClick={() => handleTableSort('ticker')}
                    >
                      Ticker
                      {tableSortField === 'ticker' ? (
                        tableSortDirection === 'asc' ? <ArrowUp className="ml-1 h-3 w-3" /> : <ArrowDown className="ml-1 h-3 w-3" />
                      ) : (
                        <ArrowUpDown className="ml-1 h-3 w-3 opacity-50" />
                      )}
                    </Button>
                  </TableHead>
                  <TableHead className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 hover:bg-transparent"
                      onClick={() => handleTableSort('confidence_score')}
                    >
                      Confidence
                      {tableSortField === 'confidence_score' ? (
                        tableSortDirection === 'asc' ? <ArrowUp className="ml-1 h-3 w-3" /> : <ArrowDown className="ml-1 h-3 w-3" />
                      ) : (
                        <ArrowUpDown className="ml-1 h-3 w-3 opacity-50" />
                      )}
                    </Button>
                  </TableHead>
                  <TableHead className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 hover:bg-transparent"
                      onClick={() => handleTableSort('total_transaction_volume')}
                    >
                      Volume
                      {tableSortField === 'total_transaction_volume' ? (
                        tableSortDirection === 'asc' ? <ArrowUp className="ml-1 h-3 w-3" /> : <ArrowDown className="ml-1 h-3 w-3" />
                      ) : (
                        <ArrowUpDown className="ml-1 h-3 w-3 opacity-50" />
                      )}
                    </Button>
                  </TableHead>
                  <TableHead className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 hover:bg-transparent"
                      onClick={() => handleTableSort('politician_activity_count')}
                    >
                      Politicians
                      {tableSortField === 'politician_activity_count' ? (
                        tableSortDirection === 'asc' ? <ArrowUp className="ml-1 h-3 w-3" /> : <ArrowDown className="ml-1 h-3 w-3" />
                      ) : (
                        <ArrowUpDown className="ml-1 h-3 w-3 opacity-50" />
                      )}
                    </Button>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedSignals.map((signal, idx) => (
                  <TableRow key={`${signal.ticker}-${idx}`}>
                    <TableCell className="font-mono font-medium">
                      {signal.ticker}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {Math.round(signal.confidence_score * 100)}%
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      ${(signal.total_transaction_volume / 1000).toFixed(0)}k
                    </TableCell>
                    <TableCell className="text-right">
                      {signal.politician_activity_count}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {/* Pagination */}
          <TablePagination
            currentPage={currentPage}
            totalPages={totalPages}
            pageSize={pageSize}
            totalItems={sortedFilteredSignals.length}
            onPageChange={setCurrentPage}
            onPageSizeChange={handlePageSizeChange}
          />
        </div>
      )}
    </div>
  );
}

/**
 * Bar chart showing confidence distribution
 */
function ConfidenceDistributionChart({ signals }: { signals: PreviewSignal[] }) {
  const data = useMemo(() => {
    const ranges = [
      { range: '0-20%', min: 0, max: 0.2, count: 0 },
      { range: '20-40%', min: 0.2, max: 0.4, count: 0 },
      { range: '40-60%', min: 0.4, max: 0.6, count: 0 },
      { range: '60-80%', min: 0.6, max: 0.8, count: 0 },
      { range: '80-100%', min: 0.8, max: 1.0, count: 0 },
    ];

    signals.forEach((signal) => {
      const conf = signal.confidence_score;
      const range = ranges.find((r) => conf >= r.min && conf < r.max);
      if (range) range.count++;
    });

    return ranges.map(({ range, count }) => ({ range, count }));
  }, [signals]);

  if (signals.length === 0) {
    return (
      <div className="flex items-center justify-center h-[200px] text-muted-foreground">
        No signal data
      </div>
    );
  }

  const chartConfig = {
    count: { label: 'Signals', color: 'hsl(var(--primary))' },
  };

  return (
    <ChartContainer config={chartConfig} className="h-[200px]">
      <BarChart data={data}>
        <XAxis dataKey="range" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Bar dataKey="count" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
        <ChartTooltip content={<ChartTooltipContent />} />
      </BarChart>
    </ChartContainer>
  );
}

/**
 * Signal type badge with appropriate styling
 */
function SignalTypeBadge({ type }: { type: SignalType }) {
  const config = SIGNAL_TYPE_CONFIG[type];
  return (
    <Badge
      variant="outline"
      style={{
        backgroundColor: config.bgColor,
        borderColor: config.color,
        color: config.color,
      }}
    >
      {config.label}
    </Badge>
  );
}

type SortField = 'ticker' | 'signal_type' | 'confidence_score' | 'politician_activity_count' | 'buy_sell_ratio' | 'total_transaction_volume';
type SortDirection = 'asc' | 'desc';

/**
 * Convert PreviewSignal to CartSignal for cart integration
 */
function toCartSignal(signal: PreviewSignal): CartSignal {
  return {
    id: signal.ticker, // Use ticker as ID for preview signals
    ticker: signal.ticker,
    signal_type: signal.signal_type,
    confidence_score: signal.confidence_score,
    politician_activity_count: signal.politician_activity_count,
    buy_sell_ratio: signal.buy_sell_ratio,
    source: 'playground',
    total_transaction_volume: signal.total_transaction_volume,
    bipartisan: signal.bipartisan,
  };
}

/**
 * Sortable column header
 */
function SortableHeader({
  label,
  field,
  currentField,
  direction,
  onSort,
  className,
}: {
  label: string;
  field: SortField;
  currentField: SortField;
  direction: SortDirection;
  onSort: (field: SortField) => void;
  className?: string;
}) {
  const isActive = currentField === field;
  return (
    <TableHead className={className}>
      <Button
        variant="ghost"
        size="sm"
        className="-ml-3 h-8 hover:bg-transparent"
        onClick={() => onSort(field)}
      >
        {label}
        {isActive ? (
          direction === 'asc' ? (
            <ArrowUp className="ml-1 h-3 w-3" />
          ) : (
            <ArrowDown className="ml-1 h-3 w-3" />
          )
        ) : (
          <ArrowUpDown className="ml-1 h-3 w-3 opacity-50" />
        )}
      </Button>
    </TableHead>
  );
}

/**
 * Table showing individual signals with sortable columns, pagination, and cart actions
 * Columns match the trading-signals page table for consistency
 */
function SignalsTable({ signals }: { signals: PreviewSignal[] }) {
  const { addToCart, removeFromCart, isInCart } = useCart();
  const [sortField, setSortField] = useState<SortField>('confidence_score');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
    setCurrentPage(1); // Reset to first page on sort
  };

  const handlePageSizeChange = (size: number) => {
    setPageSize(size);
    setCurrentPage(1);
  };

  const handleCartAction = (signal: PreviewSignal) => {
    if (isInCart(signal.ticker)) {
      removeFromCart(signal.ticker);
    } else {
      addToCart(toCartSignal(signal));
    }
  };

  const sortedSignals = useMemo(() => {
    return [...signals].sort((a, b) => {
      const aVal: any = a[sortField];
      const bVal: any = b[sortField];

      if (typeof aVal === 'string') {
        return sortDirection === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }

      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
    });
  }, [signals, sortField, sortDirection]);

  // Pagination
  const totalPages = Math.ceil(sortedSignals.length / pageSize);
  const paginatedSignals = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    return sortedSignals.slice(startIndex, startIndex + pageSize);
  }, [sortedSignals, currentPage, pageSize]);

  if (signals.length === 0) {
    return (
      <div className="flex items-center justify-center h-[200px] text-muted-foreground">
        No signals generated
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      <div className="max-h-[350px] overflow-y-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <SortableHeader
              label="Ticker"
              field="ticker"
              currentField={sortField}
              direction={sortDirection}
              onSort={handleSort}
            />
            <SortableHeader
              label="Signal"
              field="signal_type"
              currentField={sortField}
              direction={sortDirection}
              onSort={handleSort}
            />
            <SortableHeader
              label="Confidence"
              field="confidence_score"
              currentField={sortField}
              direction={sortDirection}
              onSort={handleSort}
              className="text-right"
            />
            <SortableHeader
              label="Politicians"
              field="politician_activity_count"
              currentField={sortField}
              direction={sortDirection}
              onSort={handleSort}
              className="text-right"
            />
            <SortableHeader
              label="B/S Ratio"
              field="buy_sell_ratio"
              currentField={sortField}
              direction={sortDirection}
              onSort={handleSort}
              className="text-right"
            />
            <SortableHeader
              label="Volume"
              field="total_transaction_volume"
              currentField={sortField}
              direction={sortDirection}
              onSort={handleSort}
              className="text-right"
            />
            <TableHead className="text-center">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {paginatedSignals.map((signal, idx) => (
            <TableRow key={`${signal.ticker}-${idx}`}>
              <TableCell className="font-mono font-medium">
                {signal.ticker}
              </TableCell>
              <TableCell>
                <SignalTypeBadge type={signal.signal_type} />
              </TableCell>
              <TableCell className="text-right font-mono">
                {Math.round(signal.confidence_score * 100)}%
              </TableCell>
              <TableCell className="text-right">
                {signal.politician_activity_count}
              </TableCell>
              <TableCell className="text-right font-mono">
                {signal.buy_sell_ratio.toFixed(2)}
              </TableCell>
              <TableCell className="text-right font-mono">
                ${(signal.total_transaction_volume / 1000).toFixed(0)}k
              </TableCell>
              <TableCell className="text-center">
                <Button
                  variant={isInCart(signal.ticker) ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleCartAction(signal)}
                >
                  {isInCart(signal.ticker) ? (
                    <X className="h-3 w-3" />
                  ) : (
                    <ShoppingCart className="h-3 w-3" />
                  )}
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      </div>
      {/* Pagination */}
      <TablePagination
        currentPage={currentPage}
        totalPages={totalPages}
        pageSize={pageSize}
        totalItems={sortedSignals.length}
        onPageChange={setCurrentPage}
        onPageSizeChange={handlePageSizeChange}
      />
    </div>
  );
}

export function SignalPreview({
  signals,
  stats,
  isLoading,
  isUpdating,
  error,
}: SignalPreviewProps) {
  // State for selected signal type in distribution chart
  const [selectedSignalType, setSelectedSignalType] = useState<SignalType | null>(null);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <p className="text-muted-foreground">Loading signals...</p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-destructive">
        <AlertCircle className="h-8 w-8" />
        <p>Error loading signals: {error.message}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full p-4 space-y-4 overflow-y-auto">
      {/* Header with updating indicator */}
      <div className="flex items-center justify-between">
        <h3 className="font-semibold flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          Signal Preview
        </h3>
        {isUpdating && (
          <Badge variant="outline" className="animate-pulse">
            <Loader2 className="h-3 w-3 animate-spin mr-1" />
            Updating...
          </Badge>
        )}
      </div>

      {/* Stats cards */}
      <StatsCards stats={stats} signals={signals} />

      {/* Tabs for different views */}
      <Tabs defaultValue="distribution" className="flex-1 flex flex-col">
        <TabsList className="grid w-full grid-cols-3 shrink-0">
          <TabsTrigger value="distribution">Distribution</TabsTrigger>
          <TabsTrigger value="confidence">Confidence</TabsTrigger>
          <TabsTrigger value="signals">Signals</TabsTrigger>
        </TabsList>

        <TabsContent value="distribution" className="mt-4 flex-1">
          <Card className="h-full flex flex-col">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Signal Type Distribution</CardTitle>
              <p className="text-xs text-muted-foreground">
                Click a segment to see tickers
              </p>
            </CardHeader>
            <CardContent className="flex-1">
              <SignalDistributionChart
                stats={stats}
                signals={signals}
                selectedType={selectedSignalType}
                onSelectType={setSelectedSignalType}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="confidence" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Confidence Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <ConfidenceDistributionChart signals={signals} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="signals" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">
                Generated Signals ({signals.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <SignalsTable signals={signals} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default SignalPreview;
