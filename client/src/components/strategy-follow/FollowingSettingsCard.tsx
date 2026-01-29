import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Target,
  Play,
  Pause,
  RefreshCw,
  Loader2,
  Clock,
  TrendingUp,
  TrendingDown,
  CheckCircle2,
  XCircle,
  AlertTriangle,
} from 'lucide-react';
import { formatDistanceToNow, format } from 'date-fns';
import { toast } from 'sonner';
import { useStrategyFollow } from '@/hooks/useStrategyFollow';

interface FollowingSettingsCardProps {
  tradingMode: 'paper' | 'live';
}

export function FollowingSettingsCard({ tradingMode }: FollowingSettingsCardProps) {
  const {
    subscription,
    isFollowing,
    followingName,
    isLoading,
    recentTrades,
    unsubscribe,
    syncNow,
    isUnsubscribing,
    isSyncing,
    isLoadingTrades,
    isAuthenticated,
  } = useStrategyFollow();

  // Only show if following a strategy in this trading mode
  if (!isAuthenticated) {
    return null;
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6 flex items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin" />
        </CardContent>
      </Card>
    );
  }

  if (!isFollowing || !subscription || subscription.trading_mode !== tradingMode) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            Strategy Following
          </CardTitle>
          <CardDescription>
            You're not following any strategy in {tradingMode} mode
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Alert>
            <AlertDescription>
              To follow a strategy, visit the Reference Strategy page or Strategy
              Showcase and click "Apply Strategy".
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  const handleSync = async () => {
    try {
      const result = await syncNow();
      toast.success('Sync completed', {
        description: result.message,
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
    } catch (error) {
      toast.error('Failed to unfollow', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'filled':
      case 'submitted':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'skipped':
        return <AlertTriangle className="h-4 w-4 text-muted-foreground" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5" />
              Strategy Following
              <Badge
                variant={tradingMode === 'live' ? 'destructive' : 'secondary'}
              >
                {tradingMode}
              </Badge>
            </CardTitle>
            <CardDescription>
              Automatically mirroring {followingName}
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Strategy Info */}
        <div className="grid grid-cols-2 gap-4">
          <div className="p-3 bg-muted rounded-lg">
            <p className="text-sm text-muted-foreground">Strategy</p>
            <p className="font-medium">{followingName}</p>
          </div>
          <div className="p-3 bg-muted rounded-lg">
            <p className="text-sm text-muted-foreground">Last Synced</p>
            <p className="font-medium">
              {subscription.last_synced_at
                ? formatDistanceToNow(new Date(subscription.last_synced_at), {
                    addSuffix: true,
                  })
                : 'Never'}
            </p>
          </div>
        </div>

        {/* Recent Trades */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium flex items-center gap-2">
            <Clock className="h-4 w-4" />
            Recent Strategy Trades
          </h4>

          {isLoadingTrades ? (
            <div className="flex items-center justify-center p-4">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : recentTrades.length === 0 ? (
            <p className="text-sm text-muted-foreground p-3 bg-muted rounded-lg">
              No trades executed yet
            </p>
          ) : (
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {recentTrades.slice(0, 5).map((trade) => (
                <div
                  key={trade.id}
                  className="flex items-center justify-between p-2 rounded border bg-card text-sm"
                >
                  <div className="flex items-center gap-2">
                    {getStatusIcon(trade.status)}
                    <span className="font-medium">{trade.ticker}</span>
                    <Badge
                      variant="outline"
                      className={
                        trade.side === 'buy'
                          ? 'text-green-600 border-green-600'
                          : 'text-red-600 border-red-600'
                      }
                    >
                      {trade.side === 'buy' ? (
                        <TrendingUp className="h-3 w-3 mr-1" />
                      ) : (
                        <TrendingDown className="h-3 w-3 mr-1" />
                      )}
                      {trade.side.toUpperCase()}
                    </Badge>
                    <span className="text-muted-foreground">
                      {trade.quantity} shares
                    </span>
                  </div>
                  <span className="text-muted-foreground text-xs">
                    {trade.created_at &&
                      format(new Date(trade.created_at), 'MMM d, h:mm a')}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-2 border-t">
          <Button
            variant="outline"
            onClick={handleSync}
            disabled={isSyncing}
            className="flex-1"
          >
            {isSyncing ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            Sync Now
          </Button>
          <Button
            variant="ghost"
            onClick={handleUnfollow}
            disabled={isUnsubscribing}
          >
            {isUnsubscribing ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Pause className="h-4 w-4 mr-2" />
            )}
            Unfollow
          </Button>
        </div>

        {/* Live Trading Warning */}
        {tradingMode === 'live' && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Live trading is active. Trades will be executed with real money.
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

export default FollowingSettingsCard;
