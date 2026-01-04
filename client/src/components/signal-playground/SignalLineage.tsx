/**
 * SignalLineage Component
 * Displays the full lineage of a trading signal: signal → model → weights
 * Shows audit trail, model version, and feature weights used for prediction
 */

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  GitBranch,
  Brain,
  Scale,
  Clock,
  ChevronRight,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Loader2,
  Info,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { supabase } from '@/integrations/supabase/client';
import { formatDistanceToNow, format } from 'date-fns';

interface SignalLineageProps {
  signalId: string;
  ticker: string;
  compact?: boolean;
}

interface SignalData {
  id: string;
  ticker: string;
  signal_type: string;
  confidence_score: number;
  generated_at: string;
  model_id: string | null;
  model_version: string;
  generation_context: any;
  reproducibility_hash: string | null;
}

interface ModelData {
  id: string;
  model_name: string;
  model_version: string;
  model_type: string;
  status: string;
  training_completed_at: string;
  metrics: any;
  feature_importance: any;
}

interface AuditEntry {
  id: string;
  event_type: string;
  event_timestamp: string;
  signal_snapshot: any;
  model_version: string;
  source_system: string;
  triggered_by: string;
}

interface LifecycleEntry {
  id: string;
  previous_state: string | null;
  current_state: string;
  transition_reason: string;
  transitioned_at: string;
  transitioned_by: string;
}

export function SignalLineage({ signalId, ticker, compact = false }: SignalLineageProps) {
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  // Fetch signal data
  const { data: signal, isLoading: signalLoading } = useQuery<SignalData | null>({
    queryKey: ['signal-lineage', signalId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('trading_signals')
        .select('id, ticker, signal_type, confidence_score, generated_at, model_id, model_version, generation_context, reproducibility_hash')
        .eq('id', signalId)
        .single();

      if (error) throw error;
      return data;
    },
    enabled: !!signalId,
  });

  // Fetch model data if signal has model_id
  const { data: model, isLoading: modelLoading } = useQuery<ModelData | null>({
    queryKey: ['signal-model', signal?.model_id],
    queryFn: async () => {
      if (!signal?.model_id) return null;
      const { data, error } = await supabase
        .from('ml_models')
        .select('id, model_name, model_version, model_type, status, training_completed_at, metrics, feature_importance')
        .eq('id', signal.model_id)
        .single();

      if (error) throw error;
      return data;
    },
    enabled: !!signal?.model_id,
  });

  // Fetch audit trail
  const { data: auditTrail, isLoading: auditLoading } = useQuery<AuditEntry[]>({
    queryKey: ['signal-audit', signalId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('signal_audit_trail')
        .select('id, event_type, event_timestamp, signal_snapshot, model_version, source_system, triggered_by')
        .eq('signal_id', signalId)
        .order('event_timestamp', { ascending: true });

      if (error) throw error;
      return data || [];
    },
    enabled: !!signalId,
  });

  // Fetch lifecycle
  const { data: lifecycle, isLoading: lifecycleLoading } = useQuery<LifecycleEntry[]>({
    queryKey: ['signal-lifecycle', signalId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('signal_lifecycle')
        .select('id, previous_state, current_state, transition_reason, transitioned_at, transitioned_by')
        .eq('signal_id', signalId)
        .order('transitioned_at', { ascending: true });

      if (error) throw error;
      return data || [];
    },
    enabled: !!signalId,
  });

  const isLoading = signalLoading || modelLoading || auditLoading || lifecycleLoading;

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'created':
        return <CheckCircle2 className="h-3 w-3 text-green-500" />;
      case 'updated':
        return <Clock className="h-3 w-3 text-blue-500" />;
      case 'executed':
        return <CheckCircle2 className="h-3 w-3 text-emerald-500" />;
      case 'expired':
        return <XCircle className="h-3 w-3 text-gray-500" />;
      case 'invalidated':
        return <XCircle className="h-3 w-3 text-red-500" />;
      default:
        return <AlertCircle className="h-3 w-3 text-yellow-500" />;
    }
  };

  const getStateColor = (state: string) => {
    switch (state) {
      case 'generated':
        return 'bg-blue-500/10 text-blue-600';
      case 'active':
        return 'bg-green-500/10 text-green-600';
      case 'in_cart':
        return 'bg-purple-500/10 text-purple-600';
      case 'ordered':
        return 'bg-orange-500/10 text-orange-600';
      case 'filled':
        return 'bg-emerald-500/10 text-emerald-600';
      case 'expired':
        return 'bg-gray-500/10 text-gray-600';
      case 'canceled':
        return 'bg-red-500/10 text-red-600';
      default:
        return 'bg-gray-500/10 text-gray-600';
    }
  };

  // Compact view - just shows a badge with lineage info
  if (compact) {
    return (
      <TooltipProvider>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button variant="ghost" size="sm" className="h-6 px-2 text-xs gap-1">
              <GitBranch className="h-3 w-3" />
              Lineage
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <GitBranch className="h-5 w-5" />
                Signal Lineage: {ticker}
              </DialogTitle>
              <DialogDescription>
                Full audit trail and model lineage for this trading signal
              </DialogDescription>
            </DialogHeader>
            <SignalLineageContent
              signal={signal}
              model={model}
              auditTrail={auditTrail}
              lifecycle={lifecycle}
              isLoading={isLoading}
              getEventIcon={getEventIcon}
              getStateColor={getStateColor}
            />
          </DialogContent>
        </Dialog>
      </TooltipProvider>
    );
  }

  // Full view
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <GitBranch className="h-5 w-5" />
          Signal Lineage
        </CardTitle>
      </CardHeader>
      <CardContent>
        <SignalLineageContent
          signal={signal}
          model={model}
          auditTrail={auditTrail}
          lifecycle={lifecycle}
          isLoading={isLoading}
          getEventIcon={getEventIcon}
          getStateColor={getStateColor}
        />
      </CardContent>
    </Card>
  );
}

// Internal component for lineage content
function SignalLineageContent({
  signal,
  model,
  auditTrail,
  lifecycle,
  isLoading,
  getEventIcon,
  getStateColor,
}: {
  signal: SignalData | null | undefined;
  model: ModelData | null | undefined;
  auditTrail: AuditEntry[] | undefined;
  lifecycle: LifecycleEntry[] | undefined;
  isLoading: boolean;
  getEventIcon: (type: string) => JSX.Element;
  getStateColor: (state: string) => string;
}) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  }

  if (!signal) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <AlertCircle className="h-8 w-8 mx-auto mb-2" />
        <p>Signal not found</p>
      </div>
    );
  }

  return (
    <ScrollArea className="max-h-[60vh]">
      <div className="space-y-6">
        {/* Lineage Flow */}
        <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-full bg-blue-500/10">
              <Brain className="h-4 w-4 text-blue-500" />
            </div>
            <div>
              <div className="text-sm font-medium">
                {model?.model_name || 'Heuristic'}
              </div>
              <div className="text-xs text-muted-foreground">
                v{signal.model_version}
              </div>
            </div>
          </div>
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-full bg-purple-500/10">
              <Scale className="h-4 w-4 text-purple-500" />
            </div>
            <div>
              <div className="text-sm font-medium">Feature Weights</div>
              <div className="text-xs text-muted-foreground">
                {model?.model_type || 'Rule-based'}
              </div>
            </div>
          </div>
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-full bg-green-500/10">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            </div>
            <div>
              <div className="text-sm font-medium">{signal.ticker}</div>
              <div className="text-xs text-muted-foreground">
                {Math.round(signal.confidence_score * 100)}% confidence
              </div>
            </div>
          </div>
        </div>

        {/* Model Details */}
        {model && (
          <>
            <Separator />
            <div>
              <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                <Brain className="h-4 w-4" />
                Model Details
              </h4>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Type:</span>{' '}
                  <Badge variant="outline">{model.model_type}</Badge>
                </div>
                <div>
                  <span className="text-muted-foreground">Status:</span>{' '}
                  <Badge
                    variant={model.status === 'active' ? 'default' : 'secondary'}
                    className={model.status === 'active' ? 'bg-green-600' : ''}
                  >
                    {model.status}
                  </Badge>
                </div>
                <div className="col-span-2">
                  <span className="text-muted-foreground">Trained:</span>{' '}
                  {model.training_completed_at &&
                    formatDistanceToNow(new Date(model.training_completed_at), {
                      addSuffix: true,
                    })}
                </div>
                {model.metrics?.accuracy && (
                  <div>
                    <span className="text-muted-foreground">Accuracy:</span>{' '}
                    {Math.round(model.metrics.accuracy * 100)}%
                  </div>
                )}
                {model.metrics?.f1_weighted && (
                  <div>
                    <span className="text-muted-foreground">F1 Score:</span>{' '}
                    {Math.round(model.metrics.f1_weighted * 100)}%
                  </div>
                )}
              </div>
            </div>
          </>
        )}

        {/* Feature Weights */}
        {model?.feature_importance && (
          <>
            <Separator />
            <div>
              <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                <Scale className="h-4 w-4" />
                Feature Weights Used
              </h4>
              <div className="grid grid-cols-2 gap-2 text-xs">
                {Object.entries(model.feature_importance)
                  .sort(([, a], [, b]) => (b as number) - (a as number))
                  .slice(0, 6)
                  .map(([key, value]) => (
                    <div
                      key={key}
                      className="flex items-center justify-between p-2 bg-muted/30 rounded"
                    >
                      <span className="text-muted-foreground">{key}</span>
                      <span className="font-mono">{((value as number) * 100).toFixed(1)}%</span>
                    </div>
                  ))}
              </div>
            </div>
          </>
        )}

        {/* Reproducibility Hash */}
        {signal.reproducibility_hash && (
          <>
            <Separator />
            <div>
              <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                <Info className="h-4 w-4" />
                Reproducibility Hash
              </h4>
              <code className="text-xs bg-muted p-2 rounded block break-all">
                {signal.reproducibility_hash}
              </code>
              <p className="text-xs text-muted-foreground mt-1">
                This hash ensures the signal can be reproduced with the same inputs
              </p>
            </div>
          </>
        )}

        {/* Lifecycle */}
        {lifecycle && lifecycle.length > 0 && (
          <>
            <Separator />
            <div>
              <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                <Clock className="h-4 w-4" />
                Lifecycle
              </h4>
              <div className="space-y-2">
                {lifecycle.map((entry, index) => (
                  <div
                    key={entry.id}
                    className="flex items-center gap-3 text-xs"
                  >
                    <div className="w-20 shrink-0">
                      {entry.previous_state && (
                        <Badge variant="outline" className={`text-[10px] ${getStateColor(entry.previous_state)}`}>
                          {entry.previous_state}
                        </Badge>
                      )}
                    </div>
                    <ChevronRight className="h-3 w-3 text-muted-foreground shrink-0" />
                    <Badge variant="outline" className={`text-[10px] ${getStateColor(entry.current_state)}`}>
                      {entry.current_state}
                    </Badge>
                    <span className="text-muted-foreground truncate flex-1">
                      {entry.transition_reason}
                    </span>
                    <span className="text-muted-foreground shrink-0">
                      {formatDistanceToNow(new Date(entry.transitioned_at), { addSuffix: true })}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Audit Trail */}
        {auditTrail && auditTrail.length > 0 && (
          <>
            <Separator />
            <div>
              <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                <GitBranch className="h-4 w-4" />
                Audit Trail
              </h4>
              <div className="space-y-2">
                {auditTrail.map((entry) => (
                  <div
                    key={entry.id}
                    className="flex items-center gap-3 p-2 bg-muted/30 rounded text-xs"
                  >
                    {getEventIcon(entry.event_type)}
                    <Badge variant="outline" className="text-[10px]">
                      {entry.event_type}
                    </Badge>
                    <span className="text-muted-foreground">
                      via {entry.source_system}
                    </span>
                    <span className="text-muted-foreground ml-auto">
                      {format(new Date(entry.event_timestamp), 'MMM d, HH:mm:ss')}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Generation Context */}
        {signal.generation_context && (
          <>
            <Separator />
            <div>
              <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                <Info className="h-4 w-4" />
                Generation Context
              </h4>
              <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                {JSON.stringify(signal.generation_context, null, 2)}
              </pre>
            </div>
          </>
        )}
      </div>
    </ScrollArea>
  );
}

export default SignalLineage;
