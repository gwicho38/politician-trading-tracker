import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAdmin } from '@/hooks/useAdmin';
import { Users, FileText, BarChart3, Shield, Bell, RefreshCw } from 'lucide-react';
import AdminUserManagement from '@/components/admin/AdminUserManagement';
import AdminContentManagement from '@/components/admin/AdminContentManagement';
import AdminAnalytics from '@/components/admin/AdminAnalytics';
import AdminNotifications from '@/components/admin/AdminNotifications';
import AdminSyncStatus from '@/components/admin/AdminSyncStatus';

const Admin = () => {
  const navigate = useNavigate();
  const { isAdmin, isLoading } = useAdmin();

  useEffect(() => {
    if (!isLoading && !isAdmin) {
      navigate('/');
    }
  }, [isAdmin, isLoading, navigate]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!isAdmin) {
    return null;
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 w-full border-b border-border/50 bg-background/80 backdrop-blur-xl">
        <div className="container flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-primary/20 flex items-center justify-center border border-primary/30">
              <Shield className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">
                <span className="text-gradient">Admin</span>
                <span className="text-foreground"> Dashboard</span>
              </h1>
              <p className="text-xs text-muted-foreground -mt-0.5">
                Manage your platform
              </p>
            </div>
          </div>
          <a
            href="/"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            ← Back to Site
          </a>
        </div>
      </header>

      <main className="container py-8 px-4">
        <Tabs defaultValue="users" className="space-y-6">
          <TabsList className="glass">
            <TabsTrigger value="users" className="gap-2">
              <Users className="h-4 w-4" />
              <span className="hidden sm:inline">Users</span>
            </TabsTrigger>
            <TabsTrigger value="content" className="gap-2">
              <FileText className="h-4 w-4" />
              <span className="hidden sm:inline">Content</span>
            </TabsTrigger>
            <TabsTrigger value="notifications" className="gap-2">
              <Bell className="h-4 w-4" />
              <span className="hidden sm:inline">Notifications</span>
            </TabsTrigger>
            <TabsTrigger value="sync" className="gap-2">
              <RefreshCw className="h-4 w-4" />
              <span className="hidden sm:inline">Sync Status</span>
            </TabsTrigger>
            <TabsTrigger value="analytics" className="gap-2">
              <BarChart3 className="h-4 w-4" />
              <span className="hidden sm:inline">Analytics</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="users" className="space-y-6">
            <AdminUserManagement />
          </TabsContent>

          <TabsContent value="content" className="space-y-6">
            <AdminContentManagement />
          </TabsContent>

          <TabsContent value="notifications" className="space-y-6">
            <AdminNotifications />
          </TabsContent>

          <TabsContent value="sync" className="space-y-6">
            <AdminSyncStatus />
          </TabsContent>

          <TabsContent value="analytics" className="space-y-6">
            <AdminAnalytics />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

export default Admin;
