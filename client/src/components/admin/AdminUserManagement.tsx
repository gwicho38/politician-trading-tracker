import { useState, useEffect } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { usePagination } from '@/hooks/usePagination';
import { PaginationControls } from '@/components/PaginationControls';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import { Users, Shield, UserCheck } from 'lucide-react';
import type { Database } from '@/integrations/supabase/types';
import { logError } from '@/lib/logger';

type AppRole = Database['public']['Enums']['app_role'];

interface UserWithRole {
  id: string;
  email: string | null;
  wallet_address: string | null;
  display_name: string | null;
  created_at: string;
  role: AppRole | null;
}

const AdminUserManagement = () => {
  const [users, setUsers] = useState<UserWithRole[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { toast } = useToast();
  const pagination = usePagination();

  // Update pagination when users change
  useEffect(() => {
    pagination.setTotalItems(users.length);
  }, [users.length]);

  // Paginate users
  const paginatedUsers = users.slice(pagination.startIndex, pagination.endIndex);

  const fetchUsers = async () => {
    setIsLoading(true);
    try {
      // Fetch profiles with their roles
      const { data: profiles, error: profilesError } = await supabase
        .from('profiles')
        .select('id, wallet_address, display_name, created_at');

      if (profilesError) throw profilesError;

      // Fetch all roles
      const { data: roles, error: rolesError } = await supabase
        .from('user_roles')
        .select('user_id, role');

      if (rolesError) throw rolesError;

      // Map roles to users
      const roleMap = new Map(roles?.map(r => [r.user_id, r.role]) || []);

      const usersWithRoles: UserWithRole[] = (profiles || []).map(profile => ({
        id: profile.id,
        email: null, // Email not stored in profiles
        wallet_address: profile.wallet_address,
        display_name: profile.display_name,
        created_at: profile.created_at,
        role: roleMap.get(profile.id) || null,
      }));

      setUsers(usersWithRoles);
    } catch (error) {
      logError('Error fetching users', 'admin', error instanceof Error ? error : undefined);
      toast({
        title: 'Error',
        description: 'Failed to fetch users',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const updateUserRole = async (userId: string, newRole: AppRole | 'none') => {
    try {
      if (newRole === 'none') {
        // Remove role
        const { error } = await supabase
          .from('user_roles')
          .delete()
          .eq('user_id', userId);
        
        if (error) throw error;
      } else {
        // Check if user has a role
        const existingRole = users.find(u => u.id === userId)?.role;
        
        if (existingRole) {
          // Update existing role
          const { error } = await supabase
            .from('user_roles')
            .update({ role: newRole })
            .eq('user_id', userId);
          
          if (error) throw error;
        } else {
          // Insert new role
          const { error } = await supabase
            .from('user_roles')
            .insert({ user_id: userId, role: newRole });
          
          if (error) throw error;
        }
      }

      toast({
        title: 'Success',
        description: 'User role updated successfully',
      });
      
      fetchUsers();
    } catch (error) {
      logError('Error updating role', 'admin', error instanceof Error ? error : undefined);
      toast({
        title: 'Error',
        description: 'Failed to update user role',
        variant: 'destructive',
      });
    }
  };

  const getRoleBadgeVariant = (role: AppRole | null) => {
    switch (role) {
      case 'admin':
        return 'destructive';
      case 'moderator':
        return 'default';
      case 'user':
        return 'secondary';
      default:
        return 'outline';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getDisplayIdentifier = (user: UserWithRole) => {
    if (user.display_name) return user.display_name;
    if (user.wallet_address) return `${user.wallet_address.slice(0, 6)}...${user.wallet_address.slice(-4)}`;
    return user.id.slice(0, 8) + '...';
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="glass">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Users</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{users.length}</div>
          </CardContent>
        </Card>

        <Card className="glass">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Admins</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {users.filter(u => u.role === 'admin').length}
            </div>
          </CardContent>
        </Card>

        <Card className="glass">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Moderators</CardTitle>
            <UserCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {users.filter(u => u.role === 'moderator').length}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="glass">
        <CardHeader>
          <CardTitle>User Management</CardTitle>
          <CardDescription>Manage user accounts and roles</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : (
            <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Wallet</TableHead>
                  <TableHead>Joined</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedUsers.map(user => (
                  <TableRow key={user.id}>
                    <TableCell className="font-medium">
                      {getDisplayIdentifier(user)}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {user.wallet_address 
                        ? `${user.wallet_address.slice(0, 6)}...${user.wallet_address.slice(-4)}`
                        : '-'
                      }
                    </TableCell>
                    <TableCell>{formatDate(user.created_at)}</TableCell>
                    <TableCell>
                      <Badge variant={getRoleBadgeVariant(user.role)}>
                        {user.role || 'No role'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Select
                        value={user.role || 'none'}
                        onValueChange={(value) => updateUserRole(user.id, value as AppRole | 'none')}
                      >
                        <SelectTrigger className="w-32">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">No role</SelectItem>
                          <SelectItem value="user">User</SelectItem>
                          <SelectItem value="moderator">Moderator</SelectItem>
                          <SelectItem value="admin">Admin</SelectItem>
                        </SelectContent>
                      </Select>
                    </TableCell>
                  </TableRow>
                ))}
                {paginatedUsers.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                      No users found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>

            {/* Pagination Controls */}
            {users.length > 0 && (
              <PaginationControls pagination={pagination} itemLabel="users" />
            )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default AdminUserManagement;
