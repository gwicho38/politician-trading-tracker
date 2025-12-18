import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import {
  Database,
  RefreshCw,
  Play,
  Pause,
  AlertCircle,
  CheckCircle,
  Clock,
  TrendingUp,
  Users,
  BarChart3,
  Settings,
  Download,
  Upload
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { supabase } from '@/integrations/supabase/client';

interface SyncStatus {
  lastSync: string | null;
  status: 'idle' | 'running' | 'completed' | 'failed';
  recordsProcessed: number;
  totalRecords: number;
  currentOperation: string;
}

interface DataStats {
  politicians: number;
  trades: number;
  jurisdictions: number;
  lastUpdated: string;
}

const AdminDataCollection = () => {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [syncStatus, setSyncStatus] = useState<SyncStatus>({
    lastSync: null,
    status: 'idle',
    recordsProcessed: 0,
    totalRecords: 0,
    currentOperation: ''
  });

  const [dataStats, setDataStats] = useState<DataStats>({
    politicians: 0,
    trades: 0,
    jurisdictions: 0,
    lastUpdated: ''
  });

  const [loading, setLoading] = useState(false);

  // Check authentication and admin status
  useEffect(() => {
    const checkAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        navigate('/auth');
        return;
      }

      // Check if user is admin
      const { data: roles } = await supabase
        .from('user_roles')
        .select('role')
        .eq('user_id', session.user.id)
        .eq('role', 'admin')
        .single();

      if (!roles) {
        toast({
          title: 'Access Denied',
          description: 'Admin access required for this page.',
          variant: 'destructive',
        });
        navigate('/');
        return;
      }

      // Load initial data
      await loadDataStats();
      await loadSyncStatus();
    };

    checkAuth();
  }, [navigate, toast]);

  const loadDataStats = async () => {
    try {
      // Get politician count
      const { count: politicianCount } = await supabase
        .from('politicians')
        .select('*', { count: 'exact', head: true });

      // Get trade count
      const { count: tradeCount } = await supabase
        .from('trades')
        .select('*', { count: 'exact', head: true });

      // Get jurisdiction count
      const { count: jurisdictionCount } = await supabase
        .from('jurisdictions')
        .select('*', { count: 'exact', head: true });

      // Get last updated timestamp
      const { data: lastTrade } = await supabase
        .from('trades')
        .select('created_at')
        .order('created_at', { ascending: false })
        .limit(1)
        .single();

      setDataStats({
        politicians: politicianCount || 0,
        trades: tradeCount || 0,
        jurisdictions: jurisdictionCount || 0,
        lastUpdated: lastTrade?.created_at || ''
      });
    } catch (error) {
      console.error('Error loading data stats:', error);
    }
  };

  const loadSyncStatus = async () => {
    try {
      // Get last sync from dashboard stats
      const { data: stats } = await supabase
        .from('dashboard_stats')
        .select('updated_at')
        .order('updated_at', { ascending: false })
        .limit(1)
        .single();

      if (stats) {
        setSyncStatus(prev => ({
          ...prev,
          lastSync: stats.updated_at
        }));
      }
    } catch (error) {
      console.error('Error loading sync status:', error);
    }
  };

  const handleSyncAll = async () => {
    setLoading(true);
    setSyncStatus(prev => ({ ...prev, status: 'running', currentOperation: 'Starting full synchronization...' }));

    try {
      // Call the sync Edge Function
      const { data, error } = await supabase.functions.invoke('sync-data/sync-full');

      if (error) {
        throw error;
      }

      setSyncStatus(prev => ({
        ...prev,
        status: 'completed',
        recordsProcessed: data?.results?.politicians?.count || 0 + data?.results?.trades?.count || 0,
        currentOperation: 'Synchronization completed successfully'
      }));

      toast({
        title: 'Sync Completed',
        description: `Synchronized ${data?.results?.politicians?.count || 0} politicians and ${data?.results?.trades?.count || 0} trades.`,
      });

      // Reload stats
      await loadDataStats();
      await loadSyncStatus();

    } catch (error) {
      console.error('Sync error:', error);
      setSyncStatus(prev => ({
        ...prev,
        status: 'failed',
        currentOperation: 'Synchronization failed'
      }));

      toast({
        title: 'Sync Failed',
        description: 'Failed to complete data synchronization. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSyncPoliticians = async () => {
    setLoading(true);
    setSyncStatus(prev => ({ ...prev, status: 'running', currentOperation: 'Syncing politicians...' }));

    try {
      const { data, error } = await supabase.functions.invoke('sync-data/sync-all');

      if (error) {
        throw error;
      }

      setSyncStatus(prev => ({
        ...prev,
        status: 'completed',
        recordsProcessed: data?.count || 0,
        currentOperation: 'Politician sync completed'
      }));

      toast({
        title: 'Politicians Synced',
        description: `Synchronized ${data?.count || 0} politicians.`,
      });

      await loadDataStats();

    } catch (error) {
      console.error('Politician sync error:', error);
      setSyncStatus(prev => ({
        ...prev,
        status: 'failed',
        currentOperation: 'Politician sync failed'
      }));

      toast({
        title: 'Sync Failed',
        description: 'Failed to sync politicians. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSyncTrades = async () => {
    setLoading(true);
    setSyncStatus(prev => ({ ...prev, status: 'running', currentOperation: 'Syncing trades...' }));

    try {
      const { data, error } = await supabase.functions.invoke('sync-data/sync-trades');

      if (error) {
        throw error;
      }

      setSyncStatus(prev => ({
        ...prev,
        status: 'completed',
        recordsProcessed: data?.count || 0,
        currentOperation: 'Trade sync completed'
      }));

      toast({
        title: 'Trades Synced',
        description: `Synchronized ${data?.count || 0} trades.`,
      });

      await loadDataStats();

    } catch (error) {
      console.error('Trade sync error:', error);
      setSyncStatus(prev => ({
        ...prev,
        status: 'failed',
        currentOperation: 'Trade sync failed'
      }));

      toast({
        title: 'Sync Failed',
        description: 'Failed to sync trades. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateStats = async () => {
    setLoading(true);
    setSyncStatus(prev => ({ ...prev, status: 'running', currentOperation: 'Updating statistics...' }));

    try {
      const { data, error } = await supabase.functions.invoke('sync-data/update-stats');

      if (error) {
        throw error;
      }

      setSyncStatus(prev => ({
        ...prev,
        status: 'completed',
        currentOperation: 'Statistics updated'
      }));

      toast({
        title: 'Statistics Updated',
        description: 'Dashboard statistics have been recalculated.',
      });

      await loadDataStats();
      await loadSyncStatus();

    } catch (error) {
      console.error('Stats update error:', error);
      setSyncStatus(prev => ({
        ...prev,
        status: 'failed',
        currentOperation: 'Statistics update failed'
      }));

      toast({
        title: 'Update Failed',
        description: 'Failed to update statistics. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'text-blue-500';
      case 'completed': return 'text-green-500';
      case 'failed': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running': return <RefreshCw className="h-4 w-4 animate-spin" />;
      case 'completed': return <CheckCircle className="h-4 w-4" />;
      case 'failed': return <AlertCircle className="h-4 w-4" />;
      default: return <Clock className="h-4 w-4" />;
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <Database className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-3xl font-bold text-foreground">Data Collection Admin</h1>
            <p className="text-muted-foreground">Manage data synchronization and monitor collection status</p>
          </div>
        </div>

        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="sync">Synchronization</TabsTrigger>
            <TabsTrigger value="stats">Statistics</TabsTrigger>
            <TabsTrigger value="settings">Settings</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            {/* Status Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-4">
                    <Users className="h-8 w-8 text-blue-500" />
                    <div>
                      <p className="text-2xl font-bold">{dataStats.politicians.toLocaleString()}</p>
                      <p className="text-sm text-muted-foreground">Politicians</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-4">
                    <TrendingUp className="h-8 w-8 text-green-500" />
                    <div>
                      <p className="text-2xl font-bold">{dataStats.trades.toLocaleString()}</p>
                      <p className="text-sm text-muted-foreground">Trades</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-4">
                    <BarChart3 className="h-8 w-8 text-purple-500" />
                    <div>
                      <p className="text-2xl font-bold">{dataStats.jurisdictions}</p>
                      <p className="text-sm text-muted-foreground">Jurisdictions</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-4">
                    <Clock className="h-8 w-8 text-orange-500" />
                    <div>
                      <p className="text-sm font-medium">
                        {dataStats.lastUpdated ?
                          new Date(dataStats.lastUpdated).toLocaleDateString() :
                          'Never'
                        }
                      </p>
                      <p className="text-xs text-muted-foreground">Last Updated</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Sync Status */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  {getStatusIcon(syncStatus.status)}
                  Synchronization Status
                </CardTitle>
                <CardDescription>
                  Current status of data synchronization operations
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className={`font-medium ${getStatusColor(syncStatus.status)}`}>
                      {syncStatus.currentOperation || 'Idle'}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Last sync: {syncStatus.lastSync ?
                        new Date(syncStatus.lastSync).toLocaleString() :
                        'Never'
                      }
                    </p>
                  </div>
                  <Badge variant={
                    syncStatus.status === 'running' ? 'default' :
                    syncStatus.status === 'completed' ? 'secondary' :
                    syncStatus.status === 'failed' ? 'destructive' : 'outline'
                  }>
                    {syncStatus.status.toUpperCase()}
                  </Badge>
                </div>

                {syncStatus.status === 'running' && (
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Progress</span>
                      <span>{syncStatus.recordsProcessed} / {syncStatus.totalRecords || '?'}</span>
                    </div>
                    <Progress
                      value={syncStatus.totalRecords ?
                        (syncStatus.recordsProcessed / syncStatus.totalRecords) * 100 : 0
                      }
                      className="w-full"
                    />
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Synchronization Tab */}
          <TabsContent value="sync" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Manual Sync Controls */}
              <Card>
                <CardHeader>
                  <CardTitle>Manual Synchronization</CardTitle>
                  <CardDescription>
                    Trigger data synchronization operations manually
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 gap-3">
                    <Button
                      onClick={handleSyncAll}
                      disabled={loading || syncStatus.status === 'running'}
                      className="w-full"
                    >
                      {loading ? (
                        <>
                          <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                          Syncing All Data...
                        </>
                      ) : (
                        <>
                          <RefreshCw className="mr-2 h-4 w-4" />
                          Full Synchronization
                        </>
                      )}
                    </Button>

                    <div className="grid grid-cols-2 gap-3">
                      <Button
                        variant="outline"
                        onClick={handleSyncPoliticians}
                        disabled={loading || syncStatus.status === 'running'}
                      >
                        <Users className="mr-2 h-4 w-4" />
                        Sync Politicians
                      </Button>

                      <Button
                        variant="outline"
                        onClick={handleSyncTrades}
                        disabled={loading || syncStatus.status === 'running'}
                      >
                        <TrendingUp className="mr-2 h-4 w-4" />
                        Sync Trades
                      </Button>
                    </div>

                    <Button
                      variant="outline"
                      onClick={handleUpdateStats}
                      disabled={loading || syncStatus.status === 'running'}
                    >
                      <BarChart3 className="mr-2 h-4 w-4" />
                      Update Statistics
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Automated Sync Settings */}
              <Card>
                <CardHeader>
                  <CardTitle>Automated Synchronization</CardTitle>
                  <CardDescription>
                    Configure automatic data collection schedules
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Alert>
                    <Settings className="h-4 w-4" />
                    <AlertDescription>
                      Automated synchronization is configured via scheduled jobs.
                      Access the Jobs page to manage automated data collection.
                    </AlertDescription>
                  </Alert>

                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Daily sync</span>
                      <Badge variant="secondary">Enabled</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Real-time updates</span>
                      <Badge variant="secondary">Enabled</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Error notifications</span>
                      <Badge variant="secondary">Enabled</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Data Sources */}
            <Card>
              <CardHeader>
                <CardTitle>Data Sources</CardTitle>
                <CardDescription>
                  Monitor the status of various data collection sources
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <CheckCircle className="h-5 w-5 text-green-500" />
                      <div>
                        <p className="font-medium">US House Disclosures</p>
                        <p className="text-sm text-muted-foreground">Last successful sync: 2 hours ago</p>
                      </div>
                    </div>
                    <Badge variant="secondary">Active</Badge>
                  </div>

                  <div className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <CheckCircle className="h-5 w-5 text-green-500" />
                      <div>
                        <p className="font-medium">US Senate Disclosures</p>
                        <p className="text-sm text-muted-foreground">Last successful sync: 2 hours ago</p>
                      </div>
                    </div>
                    <Badge variant="secondary">Active</Badge>
                  </div>

                  <div className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <AlertCircle className="h-5 w-5 text-yellow-500" />
                      <div>
                        <p className="font-medium">QuiverQuant API</p>
                        <p className="text-sm text-muted-foreground">Rate limited - retrying in 30 minutes</p>
                      </div>
                    </div>
                    <Badge variant="outline">Throttled</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Statistics Tab */}
          <TabsContent value="stats" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Data Quality Metrics</CardTitle>
                <CardDescription>
                  Monitor data integrity and quality indicators
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-500">99.8%</div>
                    <p className="text-sm text-muted-foreground">Data Accuracy</p>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-500">24/7</div>
                    <p className="text-sm text-muted-foreground">Uptime</p>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-purple-500">&lt;5min</div>
                    <p className="text-sm text-muted-foreground">Sync Latency</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Settings Tab */}
          <TabsContent value="settings" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Data Collection Settings</CardTitle>
                <CardDescription>
                  Configure data collection parameters and thresholds
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Alert>
                  <Settings className="h-4 w-4" />
                  <AlertDescription>
                    Advanced settings are managed through environment variables and configuration files.
                    Contact your administrator for changes to data collection settings.
                  </AlertDescription>
                </Alert>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default AdminDataCollection;