import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Target,
  Play,
  Pause,
  RefreshCw,
  Loader2,
  Settings,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { toast } from 'sonner';
import { useStrategyFollow } from '@/hooks/useStrategyFollow';

interface FollowingStatusBadgeProps {
  showPopover?: boolean;
  className?: string;
}

export function FollowingStatusBadge({
  showPopover = true,
  className = '',
}: FollowingStatusBadgeProps) {
  const {
    subscription,
    isFollowing,
    followingName,
    isLoading,
    unsubscribe,
    syncNow,
    isUnsubscribing,
    isSyncing,
  } = useStrategyFollow();
  const [isOpen, setIsOpen] = useState(false);

  if (isLoading) {
    return (
      <Badge variant="secondary" className={`gap-1 ${className}`}>
        <Loader2 className="h-3 w-3 animate-spin" />
        Loading...
      </Badge>
    );
  }

  if (!isFollowing || !subscription) {
    return null;
  }

  const handleSync = async () => {
    try {
      const result = await syncNow();
      toast.success('Sync completed', {
        description: `${result.summary.executed} trades executed`,
      });
    } catch (error) {
      toast.error('Sync failed', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  const handleUnfollow = async () => {
    try {
      await unsubscribe();
      toast.success('Unfollowed strategy', {
        description: 'Your account will no longer track this strategy.',
      });
      setIsOpen(false);
    } catch (error) {
      toast.error('Failed to unfollow', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  const badge = (
    <Badge
      variant={subscription.trading_mode === 'live' ? 'destructive' : 'default'}
      className={`gap-1 cursor-pointer hover:opacity-80 ${className}`}
    >
      <Target className="h-3 w-3" />
      Following: {followingName}
      <span className="opacity-60 ml-1">
        ({subscription.trading_mode})
      </span>
    </Badge>
  );

  if (!showPopover) {
    return badge;
  }

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        {badge}
      </PopoverTrigger>
      <PopoverContent className="w-80" align="end">
        <div className="space-y-4">
          <div className="space-y-1">
            <h4 className="font-medium">Strategy Following</h4>
            <p className="text-sm text-muted-foreground">
              Your {subscription.trading_mode} account is tracking this strategy
            </p>
          </div>

          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Strategy</span>
              <span className="font-medium">{followingName}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Mode</span>
              <Badge
                variant={
                  subscription.trading_mode === 'live'
                    ? 'destructive'
                    : 'secondary'
                }
                className="capitalize"
              >
                {subscription.trading_mode}
              </Badge>
            </div>
            {subscription.last_synced_at && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Last Synced</span>
                <span>
                  {formatDistanceToNow(new Date(subscription.last_synced_at), {
                    addSuffix: true,
                  })}
                </span>
              </div>
            )}
          </div>

          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleSync}
              disabled={isSyncing}
              className="flex-1"
            >
              {isSyncing ? (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-1" />
              )}
              Sync Now
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleUnfollow}
              disabled={isUnsubscribing}
            >
              {isUnsubscribing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Pause className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}

export default FollowingStatusBadge;
