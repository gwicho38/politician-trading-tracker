import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Activity,
  Clock,
  Zap,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

/**
 * Get access token from localStorage
 */
function getAccessToken(): string | null {
  try {
    const keys = Object.keys(localStorage).filter(k => k.startsWith('sb-') && k.endsWith('-auth-token'));
    if (keys.length === 0) return null;
    const sessionData = localStorage.getItem(keys[0]);
    if (!sessionData) return null;
    const parsed = JSON.parse(sessionData);
    return parsed?.access_token || null;
  } catch {
    return null;
  }
}

interface ConnectionStatusResponse {
  success: boolean;
  status: 'connected' | 'degraded' | 'disconnected';
  circuitBreaker: {
    state: 'closed' | 'open' | 'half-open';
    failures: number;
    lastSuccess: string;
    lastFailure: string | null;
  };
  statistics: {
    recentChecks: number;
    healthyChecks: number;
    healthRate: string;
    avgLatencyMs: number | null;
  };
  recentLogs: Array<{
    status: string;
    latencyMs: number;
    responseCode: number;
    createdAt: string;
  }>;
  timestamp: string;
  error?: string;
}

interface HealthCheckResponse {
  success: boolean;
  healthy: boolean;
  latency: number;
  status: number;
  tradingMode: string;
  circuitBreaker: {
    state: string;
    failures: number;
  };
  timestamp: string;
  error?: string;
}

interface AlpacaConnectionStatusProps {
  tradingMode: 'paper' | 'live';
}

export function AlpacaConnectionStatus({ tradingMode }: AlpacaConnectionStatusProps) {
  const queryClient = useQueryClient();
  const [lastHealthCheck, setLastHealthCheck] = useState<HealthCheckResponse | null>(null);

  // Fetch connection status
  const { data: connectionStatus, isLoading, error, refetch } = useQuery<ConnectionStatusResponse>({
    queryKey: ['alpaca-connection-status', tradingMode],
    queryFn: async () => {
      const accessToken = getAccessToken();
      const anonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

      if (!accessToken) throw new Error('Not authenticated');

      const response = await fetch(
        `${import.meta.env.VITE_SUPABASE_URL}/functions/v1/alpaca-account`,
        {
          method: 'POST',
          headers: {
            'apikey': anonKey,
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`,
          },
          body: JSON.stringify({
            action: 'connection-status',
            tradingMode,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return response.json();
    },
    refetchInterval: 60000, // Refresh every minute
  });

  // Health check mutation
  const healthCheckMutation = useMutation({
    mutationFn: async () => {
      const accessToken = getAccessToken();
      const anonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

      if (!accessToken) throw new Error('Not authenticated');

      const response = await fetch(
        `${import.meta.env.VITE_SUPABASE_URL}/functions/v1/alpaca-account`,
        {
          method: 'POST',
          headers: {
            'apikey': anonKey,
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`,
          },
          body: JSON.stringify({
            action: 'health-check',
            tradingMode,
          }),
        }
      );

      return response.json() as Promise<HealthCheckResponse>;
    },
    onSuccess: (data) => {
      setLastHealthCheck(data);
      // Refresh connection status after health check
      queryClient.invalidateQueries({ queryKey: ['alpaca-connection-status', tradingMode] });
    },
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected':
      case 'healthy':
        return 'text-green-600 dark:text-green-400';
      case 'degraded':
        return 'text-yellow-600 dark:text-yellow-400';
      case 'disconnected':
      case 'unhealthy':
      case 'error':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-muted-foreground';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
      case 'healthy':
        return <CheckCircle2 className="h-4 w-4" />;
      case 'degraded':
        return <AlertTriangle className="h-4 w-4" />;
      case 'disconnected':
      case 'unhealthy':
      case 'error':
        return <XCircle className="h-4 w-4" />;
      default:
        return <Activity className="h-4 w-4" />;
    }
  };

  const getCircuitBreakerBadge = (state: string) => {
    switch (state) {
      case 'closed':
        return <Badge variant="outline" className="border-green-500 text-green-600">Closed</Badge>;
      case 'open':
        return <Badge variant="destructive">Open</Badge>;
      case 'half-open':
        return <Badge variant="secondary" className="border-yellow-500 text-yellow-600">Half-Open</Badge>;
      default:
        return <Badge variant="outline">{state}</Badge>;
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6 flex items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Connection Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertDescription>
              Failed to fetch connection status: {(error as Error).message}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Connection Status
              <Badge variant={tradingMode === 'paper' ? 'secondary' : 'destructive'}>
                {tradingMode === 'paper' ? 'Paper' : 'Live'}
              </Badge>
            </CardTitle>
            <CardDescription>
              Real-time Alpaca API connection health and circuit breaker status
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Overall Status */}
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 rounded-lg border bg-card">
            <div className="text-sm text-muted-foreground mb-1">Connection Status</div>
            <div className={`flex items-center gap-2 text-lg font-semibold ${getStatusColor(connectionStatus?.status || 'disconnected')}`}>
              {getStatusIcon(connectionStatus?.status || 'disconnected')}
              <span className="capitalize">{connectionStatus?.status || 'Unknown'}</span>
            </div>
          </div>

          <div className="p-4 rounded-lg border bg-card">
            <div className="text-sm text-muted-foreground mb-1">Circuit Breaker</div>
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4" />
              {getCircuitBreakerBadge(connectionStatus?.circuitBreaker?.state || 'unknown')}
              {connectionStatus?.circuitBreaker?.failures ? (
                <span className="text-sm text-muted-foreground">
                  ({connectionStatus.circuitBreaker.failures} failures)
                </span>
              ) : null}
            </div>
          </div>
        </div>

        {/* Statistics */}
        {connectionStatus?.statistics && (
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-3 rounded-lg bg-muted/50">
              <div className="text-2xl font-bold">{connectionStatus.statistics.healthRate}</div>
              <div className="text-xs text-muted-foreground">Health Rate</div>
            </div>
            <div className="text-center p-3 rounded-lg bg-muted/50">
              <div className="text-2xl font-bold">
                {connectionStatus.statistics.avgLatencyMs
                  ? `${connectionStatus.statistics.avgLatencyMs}ms`
                  : 'N/A'}
              </div>
              <div className="text-xs text-muted-foreground">Avg Latency</div>
            </div>
            <div className="text-center p-3 rounded-lg bg-muted/50">
              <div className="text-2xl font-bold">
                {connectionStatus.statistics.healthyChecks}/{connectionStatus.statistics.recentChecks}
              </div>
              <div className="text-xs text-muted-foreground">Healthy/Total</div>
            </div>
          </div>
        )}

        {/* Recent Health Checks */}
        {connectionStatus?.recentLogs && connectionStatus.recentLogs.length > 0 && (
          <div>
            <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Recent Health Checks
            </h4>
            <div className="space-y-2">
              {connectionStatus.recentLogs.map((log, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-2 rounded border bg-card text-sm"
                >
                  <div className={`flex items-center gap-2 ${getStatusColor(log.status)}`}>
                    {getStatusIcon(log.status)}
                    <span className="capitalize">{log.status}</span>
                  </div>
                  <div className="flex items-center gap-4 text-muted-foreground">
                    <span>{log.latencyMs}ms</span>
                    <span>{formatDistanceToNow(new Date(log.createdAt), { addSuffix: true })}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Manual Health Check */}
        <div className="pt-2 border-t">
          <Button
            onClick={() => healthCheckMutation.mutate()}
            disabled={healthCheckMutation.isPending}
            variant="outline"
            className="w-full"
          >
            {healthCheckMutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Activity className="h-4 w-4 mr-2" />
            )}
            Run Health Check
          </Button>

          {lastHealthCheck && (
            <div className={`mt-3 p-3 rounded-lg border ${lastHealthCheck.healthy ? 'bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800' : 'bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800'}`}>
              <div className={`flex items-center gap-2 ${lastHealthCheck.healthy ? 'text-green-700 dark:text-green-300' : 'text-red-700 dark:text-red-300'}`}>
                {lastHealthCheck.healthy ? (
                  <CheckCircle2 className="h-4 w-4" />
                ) : (
                  <XCircle className="h-4 w-4" />
                )}
                <span className="font-medium">
                  {lastHealthCheck.healthy ? 'Healthy' : 'Unhealthy'}
                </span>
                <span className="text-sm">({lastHealthCheck.latency}ms)</span>
              </div>
              {lastHealthCheck.error && (
                <p className="text-sm mt-1 text-red-600 dark:text-red-400">
                  {lastHealthCheck.error}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Circuit Breaker Warning */}
        {connectionStatus?.circuitBreaker?.state === 'open' && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Circuit breaker is open due to repeated failures. API calls are temporarily blocked.
              The circuit will attempt to recover automatically.
            </AlertDescription>
          </Alert>
        )}

        {connectionStatus?.circuitBreaker?.state === 'half-open' && (
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Circuit breaker is in half-open state. Limited requests are being allowed to test
              if the API has recovered.
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
