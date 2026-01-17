/**
 * LambdaTrace Component
 * Displays execution trace and console output from lambda execution
 * Provides observability for user-defined signal transforms
 */

import { Terminal, Clock, Activity, AlertTriangle, ArrowRight, CheckCircle } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { cn } from '@/lib/utils';
import type { ExecutionTrace } from '@/types/signal-playground';

interface LambdaTraceProps {
  trace: ExecutionTrace | null;
  isLoading?: boolean;
}

export function LambdaTrace({ trace, isLoading }: LambdaTraceProps) {
  if (isLoading) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-4">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Terminal className="h-4 w-4 animate-pulse" />
            <span className="text-sm">Running lambda...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!trace) {
    return null;
  }

  const hasConsoleOutput = trace.console_output.length > 0;
  const hasErrors = trace.errors.length > 0;
  const hasSampleTransformations = trace.sample_transformations.length > 0;

  return (
    <Card className="border-green-500/20 bg-green-500/5">
      <CardHeader className="py-3 pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            <CheckCircle className="h-4 w-4 text-green-500" />
            Lambda Executed Successfully
          </CardTitle>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {trace.execution_time_ms.toFixed(1)}ms
            </span>
            <span className="flex items-center gap-1">
              <Activity className="h-3 w-3" />
              {trace.signals_modified}/{trace.signals_processed} modified
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 pt-0">
        {/* Console Output */}
        {hasConsoleOutput && (
          <Collapsible defaultOpen={true}>
            <CollapsibleTrigger className="flex items-center gap-2 text-xs font-medium hover:text-foreground text-muted-foreground w-full">
              <Terminal className="h-3 w-3" />
              Console Output ({trace.console_output.length} lines)
            </CollapsibleTrigger>
            <CollapsibleContent>
              <ScrollArea className="mt-2 h-32 rounded-md border bg-black/90 p-3">
                <pre className="text-xs font-mono text-green-400">
                  {trace.console_output.map((line, i) => (
                    <div key={i} className="leading-relaxed">
                      <span className="text-muted-foreground select-none mr-2">{i + 1}</span>
                      {line}
                    </div>
                  ))}
                </pre>
              </ScrollArea>
            </CollapsibleContent>
          </Collapsible>
        )}

        {/* No Console Output Message */}
        {!hasConsoleOutput && (
          <div className="text-xs text-muted-foreground flex items-center gap-2 py-2">
            <Terminal className="h-3 w-3" />
            <span>No console output. Add <code className="bg-muted px-1 rounded">print()</code> statements to see output here.</span>
          </div>
        )}

        {/* Sample Transformations */}
        {hasSampleTransformations && (
          <Collapsible defaultOpen={true}>
            <CollapsibleTrigger className="flex items-center gap-2 text-xs font-medium hover:text-foreground text-muted-foreground w-full">
              <ArrowRight className="h-3 w-3" />
              Sample Transformations ({trace.sample_transformations.length})
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="mt-2 space-y-2">
                {trace.sample_transformations.map((sample, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3 text-xs rounded-md border bg-muted/50 p-2"
                  >
                    <Badge variant="outline" className="font-mono shrink-0">
                      {sample.ticker}
                    </Badge>
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <span className={cn(
                        "shrink-0",
                        sample.before.signal_type.includes('buy') && "text-green-600",
                        sample.before.signal_type.includes('sell') && "text-red-600"
                      )}>
                        {sample.before.signal_type}
                      </span>
                      <span className="text-muted-foreground">
                        ({(sample.before.confidence_score * 100).toFixed(0)}%)
                      </span>
                      <ArrowRight className="h-3 w-3 text-muted-foreground shrink-0" />
                      <span className={cn(
                        "shrink-0",
                        sample.after.signal_type.includes('buy') && "text-green-600",
                        sample.after.signal_type.includes('sell') && "text-red-600"
                      )}>
                        {sample.after.signal_type}
                      </span>
                      <span className="text-muted-foreground">
                        ({(sample.after.confidence_score * 100).toFixed(0)}%)
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}

        {/* Errors */}
        {hasErrors && (
          <Collapsible defaultOpen={true}>
            <CollapsibleTrigger className="flex items-center gap-2 text-xs font-medium hover:text-foreground text-amber-600 w-full">
              <AlertTriangle className="h-3 w-3" />
              Errors ({trace.errors.length})
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="mt-2 space-y-1">
                {trace.errors.map((error, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 text-xs rounded-md border border-amber-500/30 bg-amber-500/10 p-2"
                  >
                    <Badge variant="outline" className="font-mono shrink-0 border-amber-500/50">
                      {error.ticker}
                    </Badge>
                    <span className="text-amber-600 truncate">{error.error}</span>
                  </div>
                ))}
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}
      </CardContent>
    </Card>
  );
}

export default LambdaTrace;
