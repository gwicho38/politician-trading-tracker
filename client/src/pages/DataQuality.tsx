import { useState, useEffect } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';
import { fetchWithRetry } from '@/lib/fetchWithRetry';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  Loader2, RefreshCw, CheckCircle, XCircle, AlertTriangle,
  Activity, Shield, Clock, Database, ChevronRight, Undo2
} from 'lucide-react';
import { toast } from 'sonner';
import { SidebarLayout } from '@/components/layouts/SidebarLayout';
import { logError } from '@/lib/logger';

interface QualityCheck {
  id: string;
  check_id: string;
  started_at: string;
  completed_at: string;
  status: 'passed' | 'failed' | 'warning' | 'error';
  records_checked: number;
  issues_found: number;
  duration_ms: number;
  summary?: string;
}

interface QualityIssue {
  id: string;
  severity: 'critical' | 'warning' | 'info';
  issue_type: string;
  table_name: string;
  field_name?: string;
  record_id?: string;
  description: string;
  status: 'open' | 'resolved' | 'ignored';
  created_at: string;
  resolved_at?: string;
}

interface QualityCorrection {
  id: string;
  record_id: string;
  table_name: string;
  field_name: string;
  old_value: string;
  new_value: string;
  correction_type: string;
  confidence_score: number;
  corrected_by: string;
  status: 'pending' | 'applied' | 'rolled_back';
  created_at: string;
}

interface QualityMetrics {
  totalChecks: number;
  passRate: number;
  criticalIssues: number;
  warningIssues: number;
  autoCorrections: number;
  lastCheckTime?: string;
}

const DataQuality = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [checks, setChecks] = useState<QualityCheck[]>([]);
  const [issues, setIssues] = useState<QualityIssue[]>([]);
  const [corrections, setCorrections] = useState<QualityCorrection[]>([]);
  const [metrics, setMetrics] = useState<QualityMetrics>({
    totalChecks: 0,
    passRate: 0,
    criticalIssues: 0,
    warningIssues: 0,
    autoCorrections: 0,
  });
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    loadData();

    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(loadData, 60000); // Refresh every minute
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  const loadData = async () => {
    setLoading(true);
    await Promise.all([
      loadChecks(),
      loadIssues(),
      loadCorrections(),
    ]);
    setLoading(false);
  };

  const loadChecks = async () => {
    try {
      const { data, error } = await supabase
        .from('data_quality_results')
        .select('*')
        .order('started_at', { ascending: false })
        .limit(50);

      if (error) throw error;

      setChecks(data || []);

      // Calculate metrics
      const passed = data?.filter(c => c.status === 'passed').length || 0;
      const total = data?.length || 0;

      setMetrics(prev => ({
        ...prev,
        totalChecks: total,
        passRate: total > 0 ? (passed / total) * 100 : 0,
        lastCheckTime: data?.[0]?.completed_at,
      }));
    } catch (error) {
      logError('Error loading checks', 'data-quality', error instanceof Error ? error : undefined);
    }
  };

  const loadIssues = async () => {
    try {
      const { data, error } = await supabase
        .from('data_quality_issues')
        .select('*')
        .eq('status', 'open')
        .order('created_at', { ascending: false })
        .limit(100);

      if (error) throw error;

      setIssues(data || []);

      const critical = data?.filter(i => i.severity === 'critical').length || 0;
      const warnings = data?.filter(i => i.severity === 'warning').length || 0;

      setMetrics(prev => ({
        ...prev,
        criticalIssues: critical,
        warningIssues: warnings,
      }));
    } catch (error) {
      logError('Error loading issues', 'data-quality', error instanceof Error ? error : undefined);
    }
  };

  const loadCorrections = async () => {
    try {
      const { data, error } = await supabase
        .from('data_quality_corrections')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(100);

      if (error) throw error;

      setCorrections(data || []);

      const applied = data?.filter(c => c.status === 'applied').length || 0;
      setMetrics(prev => ({
        ...prev,
        autoCorrections: applied,
      }));
    } catch (error) {
      logError('Error loading corrections', 'data-quality', error instanceof Error ? error : undefined);
    }
  };

  const resolveIssue = async (issueId: string) => {
    try {
      const { error } = await supabase
        .from('data_quality_issues')
        .update({ status: 'resolved', resolved_at: new Date().toISOString() })
        .eq('id', issueId);

      if (error) throw error;

      toast.success('Issue marked as resolved');
      loadIssues();
    } catch (error) {
      logError('Error resolving issue', 'data-quality', error instanceof Error ? error : undefined);
      toast.error('Failed to resolve issue');
    }
  };

  const ignoreIssue = async (issueId: string) => {
    try {
      const { error } = await supabase
        .from('data_quality_issues')
        .update({ status: 'ignored' })
        .eq('id', issueId);

      if (error) throw error;

      toast.success('Issue ignored');
      loadIssues();
    } catch (error) {
      logError('Error ignoring issue', 'data-quality', error instanceof Error ? error : undefined);
      toast.error('Failed to ignore issue');
    }
  };

  const rollbackCorrection = async (correctionId: string) => {
    try {
      // Call the ETL service to rollback with retry
      const response = await fetchWithRetry(
        `${import.meta.env.VITE_ETL_URL || 'https://politician-trading-etl.fly.dev'}/quality/rollback/${correctionId}`,
        {
          method: 'POST',
          maxRetries: 2,
          onRetry: (attempt, err, delay) => {
            toast.info(`Retrying rollback (attempt ${attempt})...`);
          },
        }
      );

      if (!response.ok) throw new Error('Rollback failed');

      toast.success('Correction rolled back');
      loadCorrections();
    } catch (error) {
      logError('Error rolling back correction', 'data-quality', error instanceof Error ? error : undefined);
      toast.error('Failed to rollback correction');
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-500';
      case 'warning': return 'bg-yellow-500';
      case 'info': return 'bg-blue-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'passed':
        return <Badge className="bg-green-500"><CheckCircle className="w-3 h-3 mr-1" /> Passed</Badge>;
      case 'failed':
        return <Badge className="bg-red-500"><XCircle className="w-3 h-3 mr-1" /> Failed</Badge>;
      case 'warning':
        return <Badge className="bg-yellow-500"><AlertTriangle className="w-3 h-3 mr-1" /> Warning</Badge>;
      case 'error':
        return <Badge className="bg-red-700"><XCircle className="w-3 h-3 mr-1" /> Error</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  return (
    <SidebarLayout>
      <main className="flex-1 p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-3xl font-bold">Data Quality Dashboard</h1>
              <p className="text-muted-foreground">
                Monitor data quality checks, issues, and auto-corrections
              </p>
            </div>
            <div className="flex items-center gap-4">
              <Button
                variant="outline"
                onClick={loadData}
                disabled={loading}
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <RefreshCw className="w-4 h-4 mr-2" />
                )}
                Refresh
              </Button>
            </div>
          </div>

          {/* Metrics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Pass Rate</CardDescription>
                <CardTitle className="text-2xl flex items-center">
                  <Shield className="w-5 h-5 mr-2 text-green-500" />
                  {metrics.passRate.toFixed(1)}%
                </CardTitle>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Critical Issues</CardDescription>
                <CardTitle className="text-2xl flex items-center text-red-500">
                  <XCircle className="w-5 h-5 mr-2" />
                  {metrics.criticalIssues}
                </CardTitle>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Warnings</CardDescription>
                <CardTitle className="text-2xl flex items-center text-yellow-500">
                  <AlertTriangle className="w-5 h-5 mr-2" />
                  {metrics.warningIssues}
                </CardTitle>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Auto-Corrections</CardDescription>
                <CardTitle className="text-2xl flex items-center text-blue-500">
                  <Activity className="w-5 h-5 mr-2" />
                  {metrics.autoCorrections}
                </CardTitle>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Last Check</CardDescription>
                <CardTitle className="text-sm flex items-center">
                  <Clock className="w-4 h-4 mr-2" />
                  {metrics.lastCheckTime ? formatTime(metrics.lastCheckTime) : 'Never'}
                </CardTitle>
              </CardHeader>
            </Card>
          </div>

          {/* Critical Alert */}
          {metrics.criticalIssues > 0 && (
            <Alert className="mb-6 border-red-500 bg-red-50 dark:bg-red-950">
              <XCircle className="h-4 w-4 text-red-500" />
              <AlertDescription className="text-red-700 dark:text-red-300">
                <strong>{metrics.criticalIssues} critical issue(s)</strong> require immediate attention.
              </AlertDescription>
            </Alert>
          )}

          {/* Tabs */}
          <Tabs defaultValue="checks" className="space-y-4">
            <TabsList>
              <TabsTrigger value="checks">Recent Checks</TabsTrigger>
              <TabsTrigger value="issues">
                Open Issues
                {issues.length > 0 && (
                  <Badge variant="secondary" className="ml-2">{issues.length}</Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="corrections">
                Corrections
                {corrections.filter(c => c.status === 'applied').length > 0 && (
                  <Badge variant="secondary" className="ml-2">
                    {corrections.filter(c => c.status === 'applied').length}
                  </Badge>
                )}
              </TabsTrigger>
            </TabsList>

            {/* Recent Checks Tab */}
            <TabsContent value="checks">
              <Card>
                <CardHeader>
                  <CardTitle>Recent Quality Checks</CardTitle>
                  <CardDescription>
                    Results from automated data quality checks
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {loading ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="w-8 h-8 animate-spin" />
                    </div>
                  ) : checks.length === 0 ? (
                    <p className="text-center text-muted-foreground py-8">
                      No quality checks have run yet
                    </p>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Check</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Records</TableHead>
                          <TableHead>Issues</TableHead>
                          <TableHead>Duration</TableHead>
                          <TableHead>Time</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {checks.map((check) => (
                          <TableRow key={check.id}>
                            <TableCell className="font-medium">
                              {check.check_id}
                            </TableCell>
                            <TableCell>{getStatusBadge(check.status)}</TableCell>
                            <TableCell>{check.records_checked?.toLocaleString() || '-'}</TableCell>
                            <TableCell>
                              {check.issues_found > 0 ? (
                                <span className="text-yellow-600 font-medium">
                                  {check.issues_found}
                                </span>
                              ) : (
                                <span className="text-green-600">0</span>
                              )}
                            </TableCell>
                            <TableCell>{formatDuration(check.duration_ms)}</TableCell>
                            <TableCell className="text-muted-foreground text-sm">
                              {formatTime(check.completed_at)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Open Issues Tab */}
            <TabsContent value="issues">
              <Card>
                <CardHeader>
                  <CardTitle>Open Data Quality Issues</CardTitle>
                  <CardDescription>
                    Issues that need attention or review
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {loading ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="w-8 h-8 animate-spin" />
                    </div>
                  ) : issues.length === 0 ? (
                    <div className="text-center py-8">
                      <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
                      <p className="text-muted-foreground">No open issues!</p>
                    </div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Severity</TableHead>
                          <TableHead>Type</TableHead>
                          <TableHead>Table</TableHead>
                          <TableHead className="max-w-md">Description</TableHead>
                          <TableHead>Detected</TableHead>
                          <TableHead>Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {issues.map((issue) => (
                          <TableRow key={issue.id}>
                            <TableCell>
                              <Badge className={getSeverityColor(issue.severity)}>
                                {issue.severity}
                              </Badge>
                            </TableCell>
                            <TableCell className="font-medium">
                              {issue.issue_type}
                            </TableCell>
                            <TableCell>
                              <code className="text-sm bg-muted px-1 rounded">
                                {issue.table_name}
                              </code>
                            </TableCell>
                            <TableCell className="max-w-md truncate">
                              {issue.description}
                            </TableCell>
                            <TableCell className="text-muted-foreground text-sm">
                              {formatTime(issue.created_at)}
                            </TableCell>
                            <TableCell>
                              <div className="flex gap-2">
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => resolveIssue(issue.id)}
                                >
                                  <CheckCircle className="w-3 h-3 mr-1" />
                                  Resolve
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => ignoreIssue(issue.id)}
                                >
                                  Ignore
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Corrections Tab */}
            <TabsContent value="corrections">
              <Card>
                <CardHeader>
                  <CardTitle>Auto-Corrections Audit Trail</CardTitle>
                  <CardDescription>
                    History of automatic data corrections with rollback capability
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {loading ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="w-8 h-8 animate-spin" />
                    </div>
                  ) : corrections.length === 0 ? (
                    <p className="text-center text-muted-foreground py-8">
                      No auto-corrections have been made yet
                    </p>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Type</TableHead>
                          <TableHead>Table.Field</TableHead>
                          <TableHead>Old Value</TableHead>
                          <TableHead>New Value</TableHead>
                          <TableHead>Confidence</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {corrections.map((correction) => (
                          <TableRow key={correction.id}>
                            <TableCell className="font-medium">
                              {correction.correction_type}
                            </TableCell>
                            <TableCell>
                              <code className="text-sm bg-muted px-1 rounded">
                                {correction.table_name}.{correction.field_name}
                              </code>
                            </TableCell>
                            <TableCell className="text-red-600 font-mono text-sm">
                              {String(correction.old_value).substring(0, 30)}
                            </TableCell>
                            <TableCell className="text-green-600 font-mono text-sm">
                              {String(correction.new_value).substring(0, 30)}
                            </TableCell>
                            <TableCell>
                              <Badge variant={correction.confidence_score >= 0.9 ? "default" : "secondary"}>
                                {(correction.confidence_score * 100).toFixed(0)}%
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <Badge variant={
                                correction.status === 'applied' ? 'default' :
                                correction.status === 'rolled_back' ? 'destructive' :
                                'secondary'
                              }>
                                {correction.status}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              {correction.status === 'applied' && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => rollbackCorrection(correction.id)}
                                >
                                  <Undo2 className="w-3 h-3 mr-1" />
                                  Rollback
                                </Button>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
      </main>
    </SidebarLayout>
  );
};

export default DataQuality;
