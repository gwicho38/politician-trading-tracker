import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Loader2, RefreshCw, X, ClipboardList, TrendingUp, TrendingDown } from 'lucide-react';
import { useOrders, useSyncOrders, useCancelOrder, getOrderStatusVariant } from '@/hooks/useOrders';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { formatCurrencyFull, formatDateTime } from '@/lib/formatters';

interface OrderHistoryProps {
  tradingMode: 'paper' | 'live';
}

// Use centralized formatters from '@/lib/formatters'
const formatCurrency = formatCurrencyFull;
const formatDate = (dateString: string) => formatDateTime(dateString) || '-';

export function OrderHistory({ tradingMode }: OrderHistoryProps) {
  const [statusFilter, setStatusFilter] = useState<'all' | 'open' | 'closed'>('all');
  const [cancelOrderId, setCancelOrderId] = useState<string | null>(null);

  const { data, isLoading, error, refetch, isRefetching } = useOrders(tradingMode, {
    status: statusFilter,
    limit: 50,
  });

  const syncMutation = useSyncOrders(tradingMode);
  const cancelMutation = useCancelOrder(tradingMode);

  const handleSync = async () => {
    try {
      const result = await syncMutation.mutateAsync();
      toast.success(result.message);
    } catch (error: any) {
      toast.error(error.message || 'Failed to sync orders');
    }
  };

  const handleCancelOrder = async () => {
    if (!cancelOrderId) return;

    try {
      const result = await cancelMutation.mutateAsync(cancelOrderId);
      toast.success(result.message);
    } catch (error: any) {
      toast.error(error.message || 'Failed to cancel order');
    } finally {
      setCancelOrderId(null);
    }
  };

  const canCancelOrder = (status: string): boolean => {
    const openStatuses = ['new', 'accepted', 'pending_new', 'partially_filled'];
    return openStatuses.includes(status.toLowerCase());
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6 flex items-center justify-center h-48">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center py-8 text-destructive">
            <p>Failed to load orders</p>
            <Button variant="outline" onClick={() => refetch()} className="mt-4">
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const orders = data?.orders || [];

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <div>
            <CardTitle className="flex items-center gap-2">
              Order History
              <Badge variant={tradingMode === 'paper' ? 'secondary' : 'destructive'}>
                {tradingMode === 'paper' ? 'Paper' : 'Live'}
              </Badge>
            </CardTitle>
            <CardDescription>
              {data?.total || 0} orders total
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Select
              value={statusFilter}
              onValueChange={(value: 'all' | 'open' | 'closed') => setStatusFilter(value)}
            >
              <SelectTrigger className="w-[130px]">
                <SelectValue placeholder="Filter" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Orders</SelectItem>
                <SelectItem value="open">Open</SelectItem>
                <SelectItem value="closed">Closed</SelectItem>
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              size="sm"
              onClick={handleSync}
              disabled={syncMutation.isPending}
            >
              {syncMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              <span className="ml-2 hidden sm:inline">Sync</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => refetch()}
              disabled={isRefetching}
            >
              <RefreshCw className={cn('h-4 w-4', isRefetching && 'animate-spin')} />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {orders.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <ClipboardList className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No orders found</p>
              <p className="text-sm mt-2">
                {statusFilter !== 'all'
                  ? `Try selecting "All Orders" to see more`
                  : 'Place your first trade to see it here'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b text-left text-sm text-muted-foreground">
                    <th className="pb-2 font-medium">Symbol</th>
                    <th className="pb-2 font-medium">Side</th>
                    <th className="pb-2 font-medium text-right">Qty</th>
                    <th className="pb-2 font-medium text-right">Filled</th>
                    <th className="pb-2 font-medium text-right">Price</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium">Date</th>
                    <th className="pb-2 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((order) => (
                    <tr key={order.id} className="border-b hover:bg-muted/50">
                      <td className="py-3 font-medium">{order.ticker}</td>
                      <td className="py-3">
                        <div className="flex items-center gap-1">
                          {order.side === 'buy' ? (
                            <TrendingUp className="h-3 w-3 text-green-600" />
                          ) : (
                            <TrendingDown className="h-3 w-3 text-red-600" />
                          )}
                          <span
                            className={cn(
                              'capitalize',
                              order.side === 'buy' ? 'text-green-600' : 'text-red-600'
                            )}
                          >
                            {order.side}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 text-right font-mono">{order.quantity}</td>
                      <td className="py-3 text-right font-mono">
                        {order.filled_quantity || 0}
                      </td>
                      <td className="py-3 text-right font-mono">
                        {order.filled_avg_price
                          ? formatCurrency(order.filled_avg_price)
                          : order.limit_price
                          ? formatCurrency(order.limit_price)
                          : 'Market'}
                      </td>
                      <td className="py-3">
                        <Badge variant={getOrderStatusVariant(order.status)}>
                          {order.status}
                        </Badge>
                      </td>
                      <td className="py-3 text-sm text-muted-foreground">
                        {formatDate(order.submitted_at)}
                      </td>
                      <td className="py-3 text-right">
                        {canCancelOrder(order.status) && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setCancelOrderId(order.alpaca_order_id)}
                            disabled={cancelMutation.isPending}
                            className="text-destructive hover:text-destructive"
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Cancel Order Confirmation Dialog */}
      <AlertDialog open={!!cancelOrderId} onOpenChange={() => setCancelOrderId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cancel Order</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to cancel this order? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep Order</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleCancelOrder}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {cancelMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Canceling...
                </>
              ) : (
                'Cancel Order'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
