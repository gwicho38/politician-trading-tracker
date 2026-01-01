import { useState, useEffect } from 'react';
import { Globe, Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

const SERVER_URL = import.meta.env.VITE_SERVER_URL || 'https://politician-trading-server.fly.dev';

interface SyncStatusResponse {
  last_sync: string | null;
  jobs: Array<{
    job_id: string;
    job_name: string;
    last_successful_run: string | null;
  }>;
}

function useSyncStatus() {
  return useQuery<SyncStatusResponse>({
    queryKey: ['sync-status'],
    queryFn: async () => {
      const response = await fetch(`${SERVER_URL}/api/jobs/sync-status`);
      if (!response.ok) throw new Error('Failed to fetch sync status');
      return response.json();
    },
    refetchInterval: 60000, // Refetch every minute
    staleTime: 30000, // Consider data stale after 30 seconds
  });
}

function formatTimeAgo(date: Date): string {
  const diff = Math.floor((Date.now() - date.getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

// Compact sync status for header
export function HeaderSyncStatus() {
  const { data, isLoading, error } = useSyncStatus();
  const [timeAgo, setTimeAgo] = useState('--');

  useEffect(() => {
    if (!data?.last_sync) return;

    const lastSync = new Date(data.last_sync);
    setTimeAgo(formatTimeAgo(lastSync));

    const interval = setInterval(() => {
      setTimeAgo(formatTimeAgo(lastSync));
    }, 10000); // Update every 10 seconds

    return () => clearInterval(interval);
  }, [data?.last_sync]);

  if (isLoading) {
    return (
      <div className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground bg-secondary/50 rounded-lg px-3 py-1.5">
        <Loader2 className="h-3 w-3 animate-spin" />
        <span>Checking...</span>
      </div>
    );
  }

  if (error || !data?.last_sync) {
    return (
      <div className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground bg-secondary/50 rounded-lg px-3 py-1.5">
        <Globe className="h-3 w-3" />
        <span>Sync pending</span>
      </div>
    );
  }

  return (
    <div className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground bg-secondary/50 rounded-lg px-3 py-1.5">
      <Globe className="h-3 w-3" />
      <span>Synced {timeAgo}</span>
      <div className="h-2 w-2 rounded-full bg-success" />
    </div>
  );
}

// Fuller sync status for sidebar
export function SidebarSyncStatus() {
  const { data, isLoading, error } = useSyncStatus();
  const [timeAgo, setTimeAgo] = useState('--');

  useEffect(() => {
    if (!data?.last_sync) return;

    const lastSync = new Date(data.last_sync);
    setTimeAgo(formatTimeAgo(lastSync));

    const interval = setInterval(() => {
      setTimeAgo(formatTimeAgo(lastSync));
    }, 10000);

    return () => clearInterval(interval);
  }, [data?.last_sync]);

  if (isLoading) {
    return (
      <div className="mt-4 rounded-lg bg-secondary/50 p-3">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" />
          <span>Checking sync status...</span>
        </div>
      </div>
    );
  }

  if (error || !data?.last_sync) {
    return (
      <div className="mt-4 rounded-lg bg-secondary/50 p-3">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Globe className="h-3 w-3" />
          <span>Sync pending</span>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-4 rounded-lg bg-secondary/50 p-3">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Globe className="h-3 w-3" />
        <span>Last sync: {timeAgo}</span>
      </div>
      <div className="mt-1 h-1 w-full rounded-full bg-border">
        <div className="h-1 w-full rounded-full bg-success" />
      </div>
    </div>
  );
}
