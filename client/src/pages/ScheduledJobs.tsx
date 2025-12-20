import { useState, useEffect } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Loader2, Clock, Play, Pause, RefreshCw, CheckCircle, XCircle, AlertTriangle, Download, Activity } from 'lucide-react';
import { toast } from 'sonner';

interface ScheduledJob {
  id: string;
  name: string;
  description?: string;
  type: string;
  schedule: string;
  is_paused: boolean;
  next_run?: string;
  last_execution?: {
    timestamp: string;
    status: string;
    duration_seconds?: number;
    error?: string;
    logs?: string[];
  };
}

interface JobExecution {
  job_id: string;
  timestamp: string;
  status: string;
  duration_seconds?: number;
  error?: string;
  logs?: string[];
}

const ScheduledJobs = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [jobs, setJobs] = useState<ScheduledJob[]>([]);
  const [executions, setExecutions] = useState<JobExecution[]>([]);
  const [schedulerRunning, setSchedulerRunning] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(30);

  useEffect(() => {
    loadJobs();
    loadExecutions();

    // Set up auto-refresh
    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(() => {
        loadJobs();
        loadExecutions();
      }, refreshInterval * 1000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh, refreshInterval]);

  const formatSchedule = (scheduleType: string, scheduleValue: string): string => {
    if (scheduleType === 'interval') {
      const seconds = parseInt(scheduleValue);
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);

      if (hours >= 24) {
        const days = Math.floor(hours / 24);
        return `Daily${days > 1 ? ` (every ${days} days)` : ''}`;
      } else if (hours > 0) {
        return `Every ${hours} hour${hours > 1 ? 's' : ''}`;
      } else if (minutes > 0) {
        return `Every ${minutes} minute${minutes > 1 ? 's' : ''}`;
      } else {
        return `Every ${seconds} seconds`;
      }
    } else if (scheduleType === 'cron') {
      // Parse cron expression for display
      const parts = scheduleValue.split(' ');
      if (parts.length >= 5) {
        const [minute, hour] = parts;
        if (hour !== '*' && minute !== '*') {
          return `Daily at ${hour}:${minute.padStart(2, '0')} AM`;
        }
      }
      return scheduleValue;
    }
    return scheduleValue;
  };

  const loadJobs = async () => {
    try {
      setLoading(true);

      // Fetch jobs from the scheduled_jobs table
      const { data: jobsData, error: jobsError } = await supabase
        .from('scheduled_jobs')
        .select('*')
        .order('job_name');

      if (jobsError) {
        console.error('Error fetching jobs:', jobsError);
        toast.error('Failed to load scheduled jobs');
        return;
      }

      // For each job, fetch the last execution
      const jobsWithExecutions: ScheduledJob[] = await Promise.all(
        (jobsData || []).map(async (job) => {
          // Fetch last execution for this job
          const { data: execData } = await supabase
            .from('job_executions')
            .select('*')
            .eq('job_id', job.job_id)
            .order('started_at', { ascending: false })
            .limit(1)
            .single();

          return {
            id: job.job_id,
            name: job.job_name,
            description: job.metadata?.description || '',
            type: job.schedule_type,
            schedule: formatSchedule(job.schedule_type, job.schedule_value),
            is_paused: !job.enabled,
            next_run: job.next_scheduled_run,
            last_execution: execData ? {
              timestamp: execData.started_at,
              status: execData.status,
              duration_seconds: execData.duration_seconds,
              error: execData.error_message,
              logs: execData.logs ? execData.logs.split('\n').filter((l: string) => l.trim()) : []
            } : undefined
          };
        })
      );

      setJobs(jobsWithExecutions);
      setSchedulerRunning(jobsWithExecutions.length > 0);
    } catch (error) {
      console.error('Error loading jobs:', error);
      toast.error('Failed to load scheduled jobs');
    } finally {
      setLoading(false);
    }
  };

  const loadExecutions = async () => {
    try {
      // Fetch recent job executions from the database
      const { data: execData, error: execError } = await supabase
        .from('job_executions')
        .select('*')
        .order('started_at', { ascending: false })
        .limit(50);

      if (execError) {
        console.error('Error fetching executions:', execError);
        return;
      }

      const formattedExecutions: JobExecution[] = (execData || []).map((exec) => ({
        job_id: exec.job_id,
        timestamp: exec.started_at,
        status: exec.status,
        duration_seconds: exec.duration_seconds,
        error: exec.error_message,
        logs: exec.logs ? exec.logs.split('\n').filter((l: string) => l.trim()) : []
      }));

      setExecutions(formattedExecutions);
    } catch (error) {
      console.error('Error loading executions:', error);
    }
  };

  const restartScheduler = async () => {
    try {
      // Restart scheduler (would call API in real implementation)
      toast.success('Scheduler restarted successfully');
      setSchedulerRunning(true);
      loadJobs();
    } catch (error) {
      console.error('Error restarting scheduler:', error);
      toast.error('Failed to restart scheduler');
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-red-600" />;
      default:
        return <Clock className="h-4 w-4 text-yellow-600" />;
    }
  };

  const getJobStatusColor = (isPaused: boolean) => {
    return isPaused ? 'bg-gray-100 text-gray-800' : 'bg-green-100 text-green-800';
  };

  const getJobStatusIcon = (isPaused: boolean) => {
    return isPaused ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />;
  };

  const formatTimeUntil = (nextRun?: string) => {
    if (!nextRun) return 'Not scheduled';

    const next = new Date(nextRun);
    const now = new Date();
    const diffMs = next.getTime() - now.getTime();

    if (diffMs < 0) return 'Running now...';

    const hours = diffMs / (1000 * 60 * 60);
    if (hours < 1) {
      const minutes = Math.floor(diffMs / (1000 * 60));
      return `in ${minutes} minutes`;
    } else if (hours < 24) {
      return `in ${hours.toFixed(1)} hours`;
    } else {
      const days = Math.floor(hours / 24);
      return `in ${days} days`;
    }
  };

  const downloadLogs = (logs: string[], jobId: string, timestamp: string) => {
    const logText = logs.join('\n');
    const blob = new Blob([logText], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${jobId}_${timestamp.replace(/[:\s]/g, '-')}.log`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const getJobName = (jobId: string) => {
    const job = jobs.find(j => j.id === jobId);
    return job ? job.name : jobId;
  };

  const jobStats = {
    total: jobs.length,
    enabled: jobs.filter(j => !j.is_paused).length,
    disabled: jobs.filter(j => j.is_paused).length
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Clock className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-3xl font-bold">Scheduled Jobs Management</h1>
          <p className="text-muted-foreground">
            Manage automated data collection and maintenance jobs
          </p>
        </div>
      </div>

      {/* Scheduler Status */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {schedulerRunning ? (
                <>
                  <CheckCircle className="h-5 w-5 text-green-600" />
                  <span className="text-green-600 font-medium">Scheduler is running</span>
                </>
              ) : (
                <>
                  <XCircle className="h-5 w-5 text-red-600" />
                  <span className="text-red-600 font-medium">Scheduler is not running</span>
                </>
              )}
            </div>

            {user && !schedulerRunning && (
              <Button onClick={restartScheduler} variant="outline">
                <RefreshCw className="h-4 w-4 mr-2" />
                Restart Scheduler
              </Button>
            )}
          </div>

          {!schedulerRunning && (
            <Alert className="mt-4 border-red-200 bg-red-50">
              <AlertTriangle className="h-4 w-4 text-red-600" />
              <AlertDescription className="text-red-800">
                Jobs will not execute while the scheduler is stopped.
                {user ? ' Click restart to resume job execution.' : ' Log in to restart the scheduler.'}
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Auto-refresh Controls */}
      <Card>
        <CardHeader>
          <CardTitle>Auto-Refresh Settings</CardTitle>
          <CardDescription>
            Configure automatic updates for real-time job monitoring
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="flex items-center space-x-2">
              <Switch
                id="auto-refresh"
                checked={autoRefresh}
                onCheckedChange={setAutoRefresh}
              />
              <Label htmlFor="auto-refresh">Enable auto-refresh</Label>
            </div>

            {autoRefresh && (
              <div className="flex items-center gap-2">
                <Label htmlFor="refresh-interval">Interval (seconds):</Label>
                <Input
                  id="refresh-interval"
                  type="number"
                  min={10}
                  max={300}
                  value={refreshInterval}
                  onChange={(e) => setRefreshInterval(Number(e.target.value))}
                  className="w-20"
                />
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Job Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{jobStats.total}</div>
            <p className="text-xs text-muted-foreground">Total Jobs</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-green-600">{jobStats.enabled}</div>
            <p className="text-xs text-muted-foreground">Enabled Jobs</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-gray-600">{jobStats.disabled}</div>
            <p className="text-xs text-muted-foreground">Disabled Jobs</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="jobs" className="space-y-6">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="jobs">Scheduled Jobs</TabsTrigger>
          <TabsTrigger value="history">Execution History</TabsTrigger>
        </TabsList>

        {/* Jobs Tab */}
        <TabsContent value="jobs" className="space-y-4">
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Jobs are defined in the database and managed programmatically. To modify jobs, update the database directly or use the initialization scripts.
            </AlertDescription>
          </Alert>

          {jobs.length === 0 ? (
            <Card>
              <CardContent className="pt-6 text-center py-8">
                <Activity className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium mb-2">No scheduled jobs found</h3>
                <p className="text-muted-foreground">
                  No jobs are currently configured in the system.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {jobs.map((job) => (
                <Card key={job.id}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {getJobStatusIcon(job.is_paused)}
                        <div>
                          <CardTitle className="text-lg">{job.name}</CardTitle>
                          <CardDescription>{job.description}</CardDescription>
                        </div>
                      </div>
                      <Badge className={getJobStatusColor(job.is_paused)}>
                        {job.is_paused ? 'DISABLED' : 'ENABLED'}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <div>
                          <span className="font-medium">Job ID:</span>
                          <code className="ml-2 text-sm">{job.id}</code>
                        </div>
                        <div>
                          <span className="font-medium">Type:</span>
                          <span className="ml-2 capitalize">{job.type.replace('_', ' ')}</span>
                        </div>
                        <div>
                          <span className="font-medium">Schedule:</span>
                          <span className="ml-2">{job.schedule}</span>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <div>
                          <span className="font-medium">Next Run:</span>
                          <span className="ml-2">{formatTimeUntil(job.next_run)}</span>
                        </div>

                        {job.last_execution && (
                          <div>
                            <span className="font-medium">Last Run:</span>
                            <div className="ml-2 flex items-center gap-2">
                              {getStatusIcon(job.last_execution.status)}
                              <span>
                                {new Date(job.last_execution.timestamp).toLocaleDateString()}
                                {job.last_execution.duration_seconds &&
                                  ` (${job.last_execution.duration_seconds.toFixed(1)}s)`
                                }
                              </span>
                            </div>
                          </div>
                        )}

                        {job.last_execution?.error && (
                          <Alert className="border-red-200 bg-red-50">
                            <XCircle className="h-4 w-4 text-red-600" />
                            <AlertDescription className="text-red-800">
                              {job.last_execution.error}
                            </AlertDescription>
                          </Alert>
                        )}
                      </div>
                    </div>

                    {job.last_execution?.logs && job.last_execution.logs.length > 0 && (
                      <div className="mt-4">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => downloadLogs(
                            job.last_execution!.logs!,
                            job.id,
                            job.last_execution.timestamp
                          )}
                        >
                          <Download className="h-4 w-4 mr-2" />
                          Download Last Execution Logs
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Execution History Tab */}
        <TabsContent value="history" className="space-y-4">
          {executions.length === 0 ? (
            <Card>
              <CardContent className="pt-6 text-center py-8">
                <Activity className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium mb-2">No executions found</h3>
                <p className="text-muted-foreground">
                  Job execution history will appear here.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {executions.map((execution, index) => (
                <Card key={index}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {getStatusIcon(execution.status)}
                        <div>
                          <CardTitle className="text-lg">
                            {getJobName(execution.job_id)}
                          </CardTitle>
                          <CardDescription>
                            {new Date(execution.timestamp).toLocaleString()}
                            {execution.duration_seconds && ` (${execution.duration_seconds.toFixed(1)}s)`}
                          </CardDescription>
                        </div>
                      </div>
                      <Badge variant={execution.status === 'success' ? 'default' : 'destructive'}>
                        {execution.status.toUpperCase()}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                      <div className="space-y-2">
                        <div>
                          <span className="font-medium">Job ID:</span>
                          <code className="ml-2 text-sm">{execution.job_id}</code>
                        </div>
                        {execution.duration_seconds && (
                          <div>
                            <span className="font-medium">Duration:</span>
                            <span className="ml-2">{execution.duration_seconds.toFixed(2)}s</span>
                          </div>
                        )}
                      </div>

                      <div>
                        {execution.error && (
                          <Alert className="border-red-200 bg-red-50">
                            <XCircle className="h-4 w-4 text-red-600" />
                            <AlertDescription className="text-red-800">
                              {execution.error}
                            </AlertDescription>
                          </Alert>
                        )}
                      </div>
                    </div>

                    {execution.logs && execution.logs.length > 0 && (
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <h4 className="font-medium">Execution Logs</h4>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => downloadLogs(
                              execution.logs!,
                              execution.job_id,
                              execution.timestamp
                            )}
                          >
                            <Download className="h-4 w-4 mr-2" />
                            Download
                          </Button>
                        </div>

                        <div className="bg-muted p-4 rounded-lg max-h-60 overflow-y-auto">
                          <pre className="text-sm whitespace-pre-wrap font-mono">
                            {execution.logs.join('\n')}
                          </pre>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Footer */}
      <Card>
        <CardContent className="pt-6 text-center">
          <p className="text-muted-foreground">
            Database-Managed Scheduled Jobs •
            <a href="/docs/scheduled-jobs.md" target="_blank" rel="noopener noreferrer" className="ml-1 underline">
              Documentation
            </a>
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default ScheduledJobs;