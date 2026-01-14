/**
 * LambdaComparison Component
 * Shows before/after comparison of signals when lambda is applied
 */

import { ArrowUp, ArrowDown, Minus, TrendingUp, TrendingDown, Activity } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import type { SignalType } from '@/types/signal-playground';

interface SignalComparison {
  ticker: string;
  before: {
    signal_type: string;
    confidence_score: number;
  };
  after: {
    signal_type: string;
    confidence_score: number;
  };
  changes: {
    typeChanged: boolean;
    confidenceDelta: number;
    typeImproved: boolean;
    typeDegraded: boolean;
  };
}

interface ComparisonStats {
  totalSignals: number;
  modifiedCount: number;
  improvedCount: number;
  degradedCount: number;
  avgConfidenceDelta: number;
}

interface LambdaComparisonProps {
  comparisons: SignalComparison[];
  stats: ComparisonStats;
  isLoading?: boolean;
}

const SIGNAL_TYPE_COLORS: Record<string, string> = {
  strong_buy: 'bg-green-500/20 text-green-500 border-green-500/30',
  buy: 'bg-green-500/10 text-green-400 border-green-400/20',
  hold: 'bg-gray-500/10 text-gray-400 border-gray-400/20',
  sell: 'bg-red-500/10 text-red-400 border-red-400/20',
  strong_sell: 'bg-red-500/20 text-red-500 border-red-500/30',
};

function SignalTypeBadge({ type }: { type: string }) {
  const colorClass = SIGNAL_TYPE_COLORS[type] || SIGNAL_TYPE_COLORS.hold;
  const displayType = type.replace('_', ' ');

  return (
    <Badge variant="outline" className={cn('text-xs capitalize', colorClass)}>
      {displayType}
    </Badge>
  );
}

function ConfidenceChange({ delta }: { delta: number }) {
  if (Math.abs(delta) < 0.01) {
    return (
      <span className="text-muted-foreground flex items-center gap-1">
        <Minus className="h-3 w-3" />
        0%
      </span>
    );
  }

  const isPositive = delta > 0;
  const percentage = (delta * 100).toFixed(1);

  return (
    <span
      className={cn(
        'flex items-center gap-1 font-medium',
        isPositive ? 'text-green-500' : 'text-red-500'
      )}
    >
      {isPositive ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />}
      {isPositive ? '+' : ''}
      {percentage}%
    </span>
  );
}

export function LambdaComparison({
  comparisons,
  stats,
  isLoading,
}: LambdaComparisonProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground">
        <Activity className="h-5 w-5 animate-pulse mr-2" />
        Loading comparison data...
      </div>
    );
  }

  if (!comparisons.length) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground">
        No comparison data available. Apply a lambda to see changes.
      </div>
    );
  }

  // Filter to only show modified signals
  const modifiedComparisons = comparisons.filter(
    (c) => c.changes.typeChanged || Math.abs(c.changes.confidenceDelta) > 0.01
  );

  return (
    <div className="space-y-4">
      {/* Summary Stats */}
      <div className="grid grid-cols-4 gap-3">
        <Card className="bg-secondary/30">
          <CardContent className="p-3">
            <div className="text-2xl font-bold">{stats.modifiedCount}</div>
            <div className="text-xs text-muted-foreground">Modified</div>
          </CardContent>
        </Card>
        <Card className="bg-green-500/10 border-green-500/20">
          <CardContent className="p-3">
            <div className="text-2xl font-bold text-green-500 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              {stats.improvedCount}
            </div>
            <div className="text-xs text-muted-foreground">Improved</div>
          </CardContent>
        </Card>
        <Card className="bg-red-500/10 border-red-500/20">
          <CardContent className="p-3">
            <div className="text-2xl font-bold text-red-500 flex items-center gap-1">
              <TrendingDown className="h-4 w-4" />
              {stats.degradedCount}
            </div>
            <div className="text-xs text-muted-foreground">Degraded</div>
          </CardContent>
        </Card>
        <Card className="bg-secondary/30">
          <CardContent className="p-3">
            <div className={cn(
              'text-2xl font-bold',
              stats.avgConfidenceDelta > 0 ? 'text-green-500' : stats.avgConfidenceDelta < 0 ? 'text-red-500' : ''
            )}>
              {stats.avgConfidenceDelta > 0 ? '+' : ''}
              {(stats.avgConfidenceDelta * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-muted-foreground">Avg Change</div>
          </CardContent>
        </Card>
      </div>

      {/* Comparison Table */}
      {modifiedComparisons.length === 0 ? (
        <div className="flex items-center justify-center h-32 text-muted-foreground border rounded-lg">
          Lambda applied but no signals were modified.
        </div>
      ) : (
        <ScrollArea className="h-[400px] rounded-lg border">
          <Table>
            <TableHeader className="sticky top-0 bg-background">
              <TableRow>
                <TableHead className="w-20">Ticker</TableHead>
                <TableHead>Before</TableHead>
                <TableHead>After</TableHead>
                <TableHead className="text-right">Confidence Change</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {modifiedComparisons.map((comparison) => {
                const isImproved = comparison.changes.typeImproved || comparison.changes.confidenceDelta > 0.01;
                const isDegraded = comparison.changes.typeDegraded || comparison.changes.confidenceDelta < -0.01;

                return (
                  <TableRow
                    key={comparison.ticker}
                    className={cn(
                      isImproved && 'bg-green-500/5',
                      isDegraded && 'bg-red-500/5'
                    )}
                  >
                    <TableCell className="font-mono font-medium">
                      {comparison.ticker}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <SignalTypeBadge type={comparison.before.signal_type} />
                        <span className="text-xs text-muted-foreground">
                          {(comparison.before.confidence_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <SignalTypeBadge type={comparison.after.signal_type} />
                        <span className="text-xs text-muted-foreground">
                          {(comparison.after.confidence_score * 100).toFixed(0)}%
                        </span>
                        {comparison.changes.typeChanged && (
                          comparison.changes.typeImproved ? (
                            <ArrowUp className="h-3 w-3 text-green-500" />
                          ) : (
                            <ArrowDown className="h-3 w-3 text-red-500" />
                          )
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <ConfidenceChange delta={comparison.changes.confidenceDelta} />
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </ScrollArea>
      )}
    </div>
  );
}

export default LambdaComparison;
