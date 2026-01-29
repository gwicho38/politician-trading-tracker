import { useState, useEffect, useCallback } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';
import { usePagination } from '@/hooks/usePagination';
import { PaginationControls } from '@/components/PaginationControls';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Loader2, RefreshCw, Download, ExternalLink, Clock, CheckCircle, AlertTriangle, XCircle, Minus, CloudDownload } from 'lucide-react';
import { toast } from 'sonner';
import { logError } from '@/lib/logger';

interface TradingOrder {
  id: string;
  alpaca_order_id: string;
  ticker: string;
  order_type: string;
  side: string;
  quantity: number;
  filled_quantity?: number;
  status: string;
  limit_price?: number;
  stop_price?: number;
  filled_avg_price?: number;
  submitted_at?: string;
  filled_at?: string;
  canceled_at?: string;
  trading_mode: string;
}

const Orders = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [orders, setOrders] = useState<TradingOrder[]>([]);
  const [tradingMode, setTradingMode] = useState<'paper' | 'live'>('paper');
  const [hasLiveAccess, setHasLiveAccess] = useState(false);
  const pagination = usePagination();

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Reset to page 1 when filters change
  useEffect(() => {
    pagination.setPage(1);
  }, [tradingMode, statusFilter]);

  useEffect(() => {
    if (user) {
      checkApiKeys();
      loadOrders();
    } else {
      setLoading(false);
    }
  }, [user, tradingMode, statusFilter, pagination.currentPage, pagination.pageSize]);

  const checkApiKeys = async () => {
    try {
      // Check if user has API keys configured
      setHasLiveAccess(false); // TODO: Check actual subscription status
    } catch (error) {
      logError('Error checking API keys', 'orders', error instanceof Error ? error : undefined);
    }
  };

  const loadOrders = useCallback(async () => {
    if (!user) return;

    setLoading(true);
    try {
      // Call the orders Edge Function with proper auth
      const { data, error } = await supabase.functions.invoke('orders', {
        body: {
          action: 'get-orders',
          trading_mode: tradingMode,
          status: statusFilter,
          limit: pagination.pageSize,
          offset: pagination.offset
        }
      });

      if (error) {
        logError('Orders error', 'orders', undefined, { error: error.message });
        throw new Error(error.message || 'Failed to fetch orders');
      }

      if (data?.success) {
        setOrders(data.orders || []);
        pagination.setTotalItems(data.total || 0);
      } else {
        throw new Error(data?.error || 'Failed to fetch orders');
      }
    } catch (error) {
      logError('Error loading orders', 'orders', error instanceof Error ? error : undefined);
      toast.error('Failed to load orders');
    } finally {
      setLoading(false);
    }
  }, [user, tradingMode, statusFilter, pagination.pageSize, pagination.offset]);

  const refreshOrders = () => {
    loadOrders();
    toast.success('Orders refreshed');
  };

  const syncFromAlpaca = async () => {
    if (!user) return;

    setSyncing(true);
    try {
      const { data, error } = await supabase.functions.invoke('orders', {
        body: {
          action: 'sync-orders',
          status: 'all',
          limit: 100
        }
      });

      if (error) {
        logError('Sync error', 'orders', undefined, { error: error.message });
        throw new Error(error.message || 'Failed to sync orders');
      }

      if (data?.success) {
        toast.success(`Synced ${data.synced || 0} orders from Alpaca`);
        // Reload orders after sync
        await loadOrders();
      } else {
        throw new Error(data?.error || 'Failed to sync orders');
      }
    } catch (error) {
      logError('Error syncing orders', 'orders', error instanceof Error ? error : undefined);
      toast.error('Failed to sync orders from Alpaca');
    } finally {
      setSyncing(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'filled':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'partially_filled':
        return <AlertTriangle className="h-4 w-4 text-blue-600" />;
      case 'pending':
      case 'new':
      case 'accepted':
      case 'pending_new':
        return <Clock className="h-4 w-4 text-yellow-600" />;
      case 'canceled':
        return <XCircle className="h-4 w-4 text-gray-600" />;
      case 'rejected':
        return <XCircle className="h-4 w-4 text-red-600" />;
      default:
        return <Minus className="h-4 w-4 text-gray-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'filled':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'partially_filled':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'pending':
      case 'new':
      case 'accepted':
      case 'pending_new':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'canceled':
        return 'bg-gray-100 text-gray-800 border-gray-200';
      case 'rejected':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getOrderSummary = () => {
    const pending = orders.filter(o => ['new', 'accepted', 'pending_new'].includes(o.status)).length;
    const filled = orders.filter(o => o.status === 'filled').length;
    const partial = orders.filter(o => o.status === 'partially_filled').length;
    const canceled = orders.filter(o => o.status === 'canceled').length;
    const rejected = orders.filter(o => o.status === 'rejected').length;

    return { pending, filled, partial, canceled, rejected };
  };

  const exportToCSV = () => {
    const csvData = orders.map(order => ({
      'Order ID': order.alpaca_order_id.substring(0, 8) + '...',
      'Ticker': order.ticker,
      'Type': order.order_type,
      'Side': order.side.toUpperCase(),
      'Quantity': order.quantity,
      'Filled': order.filled_quantity || 0,
      'Status': order.status,
      'Limit Price': order.limit_price ? `$${order.limit_price.toFixed(2)}` : 'N/A',
      'Filled Price': order.filled_avg_price ? `$${order.filled_avg_price.toFixed(2)}` : 'N/A',
      'Submitted': order.submitted_at ? new Date(order.submitted_at).toLocaleDateString() : 'N/A'
    }));

    const csvString = [
      Object.keys(csvData[0]).join(','),
      ...csvData.map(row => Object.values(row).join(','))
    ].join('\n');

    const blob = new Blob([csvString], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `orders_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const summary = getOrderSummary();

  if (!user) {
    return (
      <div className="container mx-auto p-6">
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Please log in to access your orders.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center gap-3">
        <RefreshCw className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-3xl font-bold">Order Tracking</h1>
          <p className="text-muted-foreground">
            Monitor all your trading orders and their execution status
          </p>
        </div>
      </div>

      {/* Trading Mode Selection */}
      <Card>
        <CardHeader>
          <CardTitle>Trading Mode</CardTitle>
          <CardDescription>
            Select your trading environment
          </CardDescription>
        </CardHeader>
        <CardContent>
          <RadioGroup
            value={tradingMode}
            onValueChange={(value) => setTradingMode(value as 'paper' | 'live')}
            className="flex gap-6"
          >
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="paper" id="paper" />
              <Label htmlFor="paper" className="cursor-pointer">
                Paper Trading (Safe)
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="live" id="live" disabled={!hasLiveAccess} />
              <Label htmlFor="live" className={`cursor-pointer ${!hasLiveAccess ? 'text-muted-foreground' : ''}`}>
                Live Trading (Real Money)
              </Label>
            </div>
          </RadioGroup>

          {tradingMode === 'live' && (
            <Alert className="mt-4 border-red-200 bg-red-50">
              <AlertTriangle className="h-4 w-4 text-red-600" />
              <AlertDescription className="text-red-800">
                Viewing LIVE trading orders with real money at risk.
              </AlertDescription>
            </Alert>
          )}

          {tradingMode === 'paper' && (
            <Alert className="mt-4 border-blue-200 bg-blue-50">
              <CheckCircle className="h-4 w-4 text-blue-600" />
              <AlertDescription className="text-blue-800">
                Viewing paper trading orders with simulated funds.
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Alpaca Dashboard Link */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium">Alpaca Dashboard</h3>
              <p className="text-sm text-muted-foreground">
                View detailed order information in your Alpaca dashboard
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                onClick={syncFromAlpaca}
                disabled={syncing}
                className="flex items-center gap-2"
              >
                {syncing ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CloudDownload className="h-4 w-4" />
                )}
                {syncing ? 'Syncing...' : 'Sync from Alpaca'}
              </Button>
              <Button variant="outline" asChild>
                <a
                  href={tradingMode === 'paper'
                    ? "https://app.alpaca.markets/paper/dashboard/overview"
                    : "https://app.alpaca.markets/live/dashboard/overview"
                  }
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2"
                >
                  <ExternalLink className="h-4 w-4" />
                  View Dashboard
                </a>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Order Summary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-yellow-600">{summary.pending}</div>
            <p className="text-xs text-muted-foreground">⏳ Pending</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-green-600">{summary.filled}</div>
            <p className="text-xs text-muted-foreground">✅ Filled</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-blue-600">{summary.partial}</div>
            <p className="text-xs text-muted-foreground">🔄 Partial</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-gray-600">{summary.canceled}</div>
            <p className="text-xs text-muted-foreground">❌ Canceled</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-red-600">{summary.rejected}</div>
            <p className="text-xs text-muted-foreground">🚫 Rejected</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Order History</CardTitle>
          <CardDescription>
            Filter and view your trading orders
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 mb-4">
            <div className="flex-1">
              <Label htmlFor="status-filter">Status Filter</Label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Orders</SelectItem>
                  <SelectItem value="open">Open Orders</SelectItem>
                  <SelectItem value="closed">Closed Orders</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-end">
              <Button onClick={refreshOrders} variant="outline" className="flex items-center gap-2">
                <RefreshCw className="h-4 w-4" />
                Refresh
              </Button>
            </div>
          </div>

          <div className="flex justify-between items-center">
            <p className="text-sm text-muted-foreground">
              {pagination.totalItems > 0
                ? `Showing ${pagination.showingFrom} to ${pagination.showingTo} of ${pagination.totalItems.toLocaleString()} orders`
                : 'No orders found'}
            </p>
            <Button onClick={exportToCSV} variant="outline" size="sm" className="flex items-center gap-2" disabled={orders.length === 0}>
              <Download className="h-4 w-4" />
              Export CSV
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Orders Table */}
      {loading ? (
        <Card>
          <CardContent className="pt-6 text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
            <p className="text-muted-foreground">Loading orders...</p>
          </CardContent>
        </Card>
      ) : orders.length > 0 ? (
        <Card>
          <CardContent className="pt-6">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-2">Order ID</th>
                    <th className="text-left p-2">Ticker</th>
                    <th className="text-left p-2">Type</th>
                    <th className="text-left p-2">Side</th>
                    <th className="text-left p-2">Quantity</th>
                    <th className="text-left p-2">Filled</th>
                    <th className="text-left p-2">Status</th>
                    <th className="text-left p-2">Filled Price</th>
                    <th className="text-left p-2">Submitted</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((order) => (
                    <tr key={order.id} className="border-b hover:bg-muted/50">
                      <td className="p-2 font-mono text-sm">
                        {order.alpaca_order_id.substring(0, 8)}...
                      </td>
                      <td className="p-2 font-medium">{order.ticker}</td>
                      <td className="p-2">{order.order_type}</td>
                      <td className="p-2">
                        <Badge variant={order.side === 'buy' ? 'default' : 'secondary'}>
                          {order.side.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="p-2">{order.quantity}</td>
                      <td className="p-2">{order.filled_quantity || 0}</td>
                      <td className="p-2">
                        <Badge className={getStatusColor(order.status)}>
                          <div className="flex items-center gap-1">
                            {getStatusIcon(order.status)}
                            {order.status.replace('_', ' ')}
                          </div>
                        </Badge>
                      </td>
                      <td className="p-2">
                        {order.filled_avg_price ? `$${order.filled_avg_price.toFixed(2)}` : 'N/A'}
                      </td>
                      <td className="p-2">
                        {order.submitted_at ? new Date(order.submitted_at).toLocaleDateString() : 'N/A'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            <PaginationControls
              pagination={pagination}
              itemLabel="orders"
              showPageSizeSelector={true}
            />
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="pt-6 text-center py-8">
            <RefreshCw className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium mb-2">No orders found</h3>
            <p className="text-muted-foreground">
              Place some trades to see them here!
            </p>
          </CardContent>
        </Card>
      )}

      {/* Order Details */}
      {orders.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Order Details</CardTitle>
            <CardDescription>
              Detailed information for recent orders
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {orders.slice(0, 10).map((order) => (
              <Card key={order.id} className="border-l-4 border-l-primary">
                <CardContent className="pt-4">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      {getStatusIcon(order.status)}
                      <div>
                        <h3 className="font-semibold">
                          {order.ticker} - {order.side.toUpperCase()} {order.quantity} shares
                        </h3>
                        <Badge className={getStatusColor(order.status)}>
                          {order.status.replace('_', ' ')}
                        </Badge>
                      </div>
                    </div>
                    <div className="text-sm text-muted-foreground font-mono">
                      {order.alpaca_order_id.substring(0, 16)}...
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <h4 className="font-medium mb-2">Order Info</h4>
                      <div className="space-y-1 text-sm">
                        <div>Type: {order.order_type}</div>
                        <div>Quantity: {order.quantity}</div>
                        <div>Filled: {order.filled_quantity || 0}</div>
                      </div>
                    </div>

                    <div>
                      <h4 className="font-medium mb-2">Prices</h4>
                      <div className="space-y-1 text-sm">
                        {order.limit_price && <div>Limit: ${order.limit_price.toFixed(2)}</div>}
                        {order.stop_price && <div>Stop: ${order.stop_price.toFixed(2)}</div>}
                        {order.filled_avg_price && <div>Fill Avg: ${order.filled_avg_price.toFixed(2)}</div>}
                      </div>
                    </div>

                    <div>
                      <h4 className="font-medium mb-2">Timestamps</h4>
                      <div className="space-y-1 text-sm">
                        {order.submitted_at && (
                          <div>Submitted: {new Date(order.submitted_at).toLocaleString()}</div>
                        )}
                        {order.filled_at && (
                          <div>Filled: {new Date(order.filled_at).toLocaleString()}</div>
                        )}
                        {order.canceled_at && (
                          <div>Canceled: {new Date(order.canceled_at).toLocaleString()}</div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Status-specific messages */}
                  {order.status === 'rejected' && (
                    <Alert className="mt-4 border-red-200 bg-red-50">
                      <XCircle className="h-4 w-4 text-red-600" />
                      <AlertDescription className="text-red-800">
                        This order was rejected. Common reasons: insufficient funds, market closed, invalid symbol.
                      </AlertDescription>
                    </Alert>
                  )}

                  {['new', 'accepted', 'pending_new'].includes(order.status) && (
                    <Alert className="mt-4 border-yellow-200 bg-yellow-50">
                      <Clock className="h-4 w-4 text-yellow-600" />
                      <AlertDescription className="text-yellow-800">
                        This order is pending execution. It will fill when market conditions are met.
                      </AlertDescription>
                    </Alert>
                  )}

                  {order.status === 'partially_filled' && (
                    <Alert className="mt-4 border-blue-200 bg-blue-50">
                      <AlertTriangle className="h-4 w-4 text-blue-600" />
                      <AlertDescription className="text-blue-800">
                        {order.filled_quantity}/{order.quantity} shares filled. Waiting for remaining shares.
                      </AlertDescription>
                    </Alert>
                  )}
                </CardContent>
              </Card>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Help Section */}
      <Card>
        <CardHeader>
          <CardTitle>Understanding Order Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium mb-3">Order States</h4>
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-yellow-600" />
                  <span><strong>Pending</strong> (new, accepted) - Order submitted, waiting to execute</span>
                </div>
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-blue-600" />
                  <span><strong>Partially Filled</strong> - Some shares filled, waiting for more</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <span><strong>Filled</strong> - Order completely executed</span>
                </div>
                <div className="flex items-center gap-2">
                  <XCircle className="h-4 w-4 text-gray-600" />
                  <span><strong>Canceled</strong> - Order was canceled before execution</span>
                </div>
                <div className="flex items-center gap-2">
                  <XCircle className="h-4 w-4 text-red-600" />
                  <span><strong>Rejected</strong> - Order rejected (insufficient funds, invalid symbol, etc.)</span>
                </div>
              </div>
            </div>

            <div>
              <h4 className="font-medium mb-3">Tips</h4>
              <div className="space-y-2 text-sm text-muted-foreground">
                <p>• Orders placed outside market hours (9:30 AM - 4:00 PM ET) will execute when market opens</p>
                <p>• Paper trading orders fill almost instantly during market hours</p>
                <p>• Check order status before assuming execution</p>
                <p>• Use limit orders for price control</p>
                <p>• Market orders execute immediately at current price</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Orders;