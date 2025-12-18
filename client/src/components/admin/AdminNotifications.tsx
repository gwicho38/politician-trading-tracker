import { useState, useEffect } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';
import { Bell, Plus, Trash2, RefreshCw } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

interface Notification {
  id: string;
  user_id: string | null;
  title: string;
  message: string;
  type: string;
  read: boolean;
  created_at: string;
}

const AdminNotifications = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newNotification, setNewNotification] = useState({
    title: '',
    message: '',
    type: 'info',
  });
  const { toast } = useToast();

  const fetchNotifications = async () => {
    setIsLoading(true);
    const { data, error } = await supabase
      .from('notifications')
      .select('*')
      .order('created_at', { ascending: false });

    if (error) {
      toast({ title: 'Error', description: 'Failed to fetch notifications', variant: 'destructive' });
    } else {
      setNotifications(data || []);
    }
    setIsLoading(false);
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  const createNotification = async () => {
    if (!newNotification.title || !newNotification.message) {
      toast({ title: 'Error', description: 'Please fill in all fields', variant: 'destructive' });
      return;
    }

    const { error } = await supabase.from('notifications').insert({
      title: newNotification.title,
      message: newNotification.message,
      type: newNotification.type,
      user_id: null, // Global notification
    });

    if (error) {
      toast({ title: 'Error', description: 'Failed to create notification', variant: 'destructive' });
    } else {
      toast({ title: 'Success', description: 'Notification created' });
      setNewNotification({ title: '', message: '', type: 'info' });
      setIsDialogOpen(false);
      fetchNotifications();
    }
  };

  const deleteNotification = async (id: string) => {
    const { error } = await supabase.from('notifications').delete().eq('id', id);
    if (error) {
      toast({ title: 'Error', description: 'Failed to delete notification', variant: 'destructive' });
    } else {
      toast({ title: 'Success', description: 'Notification deleted' });
      fetchNotifications();
    }
  };

  const getTypeBadgeVariant = (type: string) => {
    switch (type) {
      case 'success': return 'default';
      case 'warning': return 'secondary';
      case 'error': return 'destructive';
      default: return 'outline';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Notifications</h2>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={fetchNotifications} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Plus className="h-4 w-4 mr-2" />
                Create Notification
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create Global Notification</DialogTitle>
                <DialogDescription>Send a notification to all users</DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="title">Title</Label>
                  <Input
                    id="title"
                    value={newNotification.title}
                    onChange={(e) => setNewNotification(prev => ({ ...prev, title: e.target.value }))}
                    placeholder="Notification title"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="message">Message</Label>
                  <Textarea
                    id="message"
                    value={newNotification.message}
                    onChange={(e) => setNewNotification(prev => ({ ...prev, message: e.target.value }))}
                    placeholder="Notification message"
                    rows={3}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="type">Type</Label>
                  <Select
                    value={newNotification.type}
                    onValueChange={(value) => setNewNotification(prev => ({ ...prev, type: value }))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="info">Info</SelectItem>
                      <SelectItem value="success">Success</SelectItem>
                      <SelectItem value="warning">Warning</SelectItem>
                      <SelectItem value="error">Error</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsDialogOpen(false)}>Cancel</Button>
                <Button onClick={createNotification}>Create</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <Card className="glass">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Notifications</CardTitle>
          <Bell className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{notifications.length}</div>
        </CardContent>
      </Card>

      <Card className="glass">
        <CardHeader>
          <CardTitle>All Notifications</CardTitle>
          <CardDescription>Manage system notifications</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Message</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Scope</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {notifications.map(notification => (
                  <TableRow key={notification.id}>
                    <TableCell className="font-medium">{notification.title}</TableCell>
                    <TableCell className="max-w-xs truncate">{notification.message}</TableCell>
                    <TableCell>
                      <Badge variant={getTypeBadgeVariant(notification.type)}>
                        {notification.type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {notification.user_id ? 'User' : 'Global'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive hover:text-destructive"
                        onClick={() => deleteNotification(notification.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {notifications.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                      No notifications found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default AdminNotifications;
