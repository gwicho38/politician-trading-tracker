import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import { usePagination } from '@/hooks/usePagination';
import { PaginationControls } from '@/components/PaginationControls';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { RefreshCw, CheckCircle, XCircle, Clock, Activity, Play } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { toast } from 'sonner';

interface SyncLog {
  id: string;
  sync_type: string;
  status: string;
  records_processed: number;
  records_created: number;
  records_updated: number;
  error_message: string | null;
  metadata: Record<string, unknown>;
  started_at: string;
  completed_at: string | null;
  created_at: string;
}

const statusConfig: Record<string, { icon: React.ReactNode; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  pending: { icon: <Clock className="h-3 w-3" />, variant: 'secondary' },
  running: { icon: <RefreshCw className="h-3 w-3 animate-spin" />, variant: 'default' },
  success: { icon: <CheckCircle className="h-3 w-3" />, variant: 'outline' },
  failed: { icon: <XCircle className="h-3 w-3" />, variant: 'destructive' },
};

const syncTypeLabels: Record<string, string> = {
  filing: 'Filing Sync',
  politician: 'Politician',
  trade: 'Trade',
  full_sync: 'Full Sync',
  chart_data: 'Chart Data',
  dashboard_stats: 'Dashboard Stats',
};

const AdminSyncStatus = () => {
  const [isSyncing, setIsSyncing] = useState(false);
  const queryClient = useQueryClient();
  const pagination = usePagination();

  const { data: syncLogs, isLoading } = useQuery({
    queryKey: ['sync-logs'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('sync_logs')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(200);

      if (error) throw error;
      return data as SyncLog[];
    },
    refetchInterval: 10000,
  });

  // Update pagination when logs change
  useEffect(() => {
    pagination.setTotalItems(syncLogs?.length || 0);
  }, [syncLogs?.length]);

  // Paginate logs
  const paginatedLogs = syncLogs?.slice(pagination.startIndex, pagination.endIndex);

  const handleRunFullSync = async () => {
    setIsSyncing(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        toast.error('You must be logged in to run sync');
        return;
      }

      const response = await supabase.functions.invoke('run-full-sync', {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });

      if (response.error) {
        throw new Error(response.error.message || 'Sync failed');
      }

      toast.success('Full sync completed successfully');
      queryClient.invalidateQueries({ queryKey: ['sync-logs'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] });
      queryClient.invalidateQueries({ queryKey: ['politicians'] });
      queryClient.invalidateQueries({ queryKey: ['chart-data'] });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Sync failed';
      toast.error(message);
    } finally {
      setIsSyncing(false);
    }
  };

  const latestByType = syncLogs?.reduce((acc, log) => {
    if (!acc[log.sync_type] || new Date(log.created_at) > new Date(acc[log.sync_type].created_at)) {
      acc[log.sync_type] = log;
    }
    return acc;
  }, {} as Record<string, SyncLog>);

  const stats = syncLogs ? {
    total: syncLogs.length,
    success: syncLogs.filter(l => l.status === 'success').length,
    failed: syncLogs.filter(l => l.status === 'failed').length,
    running: syncLogs.filter(l => l.status === 'running').length,
  } : { total: 0, success: 0, failed: 0, running: 0 };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48">
        <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Manual Sync Trigger */}
      <Card className="glass border-primary/20">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Manual Sync</CardTitle>
              <CardDescription>Recalculate all derived data from trades</CardDescription>
            </div>
            <Button 
              onClick={handleRunFullSync} 
              disabled={isSyncing}
              className="gap-2"
            >
              {isSyncing ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              {isSyncing ? 'Running...' : 'Run Full Sync'}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            This will recalculate politician totals, chart data, and dashboard statistics from the trades table. 
            Use this after bulk importing data or to fix any data inconsistencies.
          </p>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="glass">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Syncs</p>
                <p className="text-2xl font-bold">{stats.total}</p>
              </div>
              <Activity className="h-8 w-8 text-primary/50" />
            </div>
          </CardContent>
        </Card>
        <Card className="glass">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Successful</p>
                <p className="text-2xl font-bold text-green-500">{stats.success}</p>
              </div>
              <CheckCircle className="h-8 w-8 text-green-500/50" />
            </div>
          </CardContent>
        </Card>
        <Card className="glass">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Failed</p>
                <p className="text-2xl font-bold text-destructive">{stats.failed}</p>
              </div>
              <XCircle className="h-8 w-8 text-destructive/50" />
            </div>
          </CardContent>
        </Card>
        <Card className="glass">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Running</p>
                <p className="text-2xl font-bold text-primary">{stats.running}</p>
              </div>
              <RefreshCw className={`h-8 w-8 text-primary/50 ${stats.running > 0 ? 'animate-spin' : ''}`} />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Latest Status by Type */}
      <Card className="glass">
        <CardHeader>
          <CardTitle>Latest Sync Status</CardTitle>
          <CardDescription>Most recent sync operation for each type</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {Object.entries(latestByType || {}).map(([type, log]) => {
              const config = statusConfig[log.status] || statusConfig.pending;
              return (
                <div key={type} className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                  <div>
                    <p className="font-medium text-sm">{syncTypeLabels[type] || type}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
                    </p>
                  </div>
                  <Badge variant={config.variant} className="gap-1">
                    {config.icon}
                    {log.status}
                  </Badge>
                </div>
              );
            })}
            {Object.keys(latestByType || {}).length === 0 && (
              <p className="text-muted-foreground col-span-full text-center py-4">
                No sync operations recorded yet
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Sync History Table */}
      <Card className="glass">
        <CardHeader>
          <CardTitle>Sync History</CardTitle>
          <CardDescription>Recent sync operations from Python backend</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="hidden md:table-cell">Processed</TableHead>
                <TableHead className="hidden md:table-cell">Created</TableHead>
                <TableHead className="hidden md:table-cell">Updated</TableHead>
                <TableHead>Time</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedLogs?.map((log) => {
                const config = statusConfig[log.status] || statusConfig.pending;
                return (
                  <TableRow key={log.id}>
                    <TableCell className="font-medium">
                      {syncTypeLabels[log.sync_type] || log.sync_type}
                    </TableCell>
                    <TableCell>
                      <Badge variant={config.variant} className="gap-1">
                        {config.icon}
                        {log.status}
                      </Badge>
                      {log.error_message && (
                        <p className="text-xs text-destructive mt-1 max-w-[200px] truncate" title={log.error_message}>
                          {log.error_message}
                        </p>
                      )}
                    </TableCell>
                    <TableCell className="hidden md:table-cell">{log.records_processed}</TableCell>
                    <TableCell className="hidden md:table-cell">{log.records_created}</TableCell>
                    <TableCell className="hidden md:table-cell">{log.records_updated}</TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
                    </TableCell>
                  </TableRow>
                );
              })}
              {(!paginatedLogs || paginatedLogs.length === 0) && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                    No sync logs yet. Run a sync from your Python application.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>

          {/* Pagination Controls */}
          {syncLogs && syncLogs.length > 0 && (
            <PaginationControls pagination={pagination} itemLabel="sync logs" />
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default AdminSyncStatus;
