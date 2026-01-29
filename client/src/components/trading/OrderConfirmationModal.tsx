import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, AlertTriangle, TrendingUp, TrendingDown } from 'lucide-react';
import { toast } from 'sonner';
import { formatCurrencyFull } from '@/lib/formatters';

/** Order result from the orders edge function */
interface OrderResult {
  success: boolean;
  ticker: string;
  error?: string;
}

/**
 * Get access token from localStorage
 */
function getAccessToken(): string | null {
  try {
    const keys = Object.keys(localStorage).filter(k => k.startsWith('sb-') && k.endsWith('-auth-token'));
    if (keys.length === 0) return null;
    const sessionData = localStorage.getItem(keys[0]);
    if (!sessionData) return null;
    const parsed = JSON.parse(sessionData);
    return parsed?.access_token || null;
  } catch {
    return null;
  }
}

interface OrderRequest {
  ticker: string;
  side: 'buy' | 'sell';
  quantity: number;
  order_type: 'market' | 'limit';
  limit_price?: number;
  signal_id?: string;
}

interface OrderConfirmationModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  orders: OrderRequest[];
  tradingMode: 'paper' | 'live';
  onSuccess?: () => void;
}

// formatCurrency uses the centralized formatter from '@/lib/formatters'
const formatCurrency = formatCurrencyFull;

export function OrderConfirmationModal({
  open,
  onOpenChange,
  orders,
  tradingMode,
  onSuccess,
}: OrderConfirmationModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [liveConfirmed, setLiveConfirmed] = useState(false);

  const totalShares = orders.reduce((sum, order) => sum + order.quantity, 0);
  const buyOrders = orders.filter((o) => o.side === 'buy');
  const sellOrders = orders.filter((o) => o.side === 'sell');

  const handleSubmit = async () => {
    if (tradingMode === 'live' && !liveConfirmed) {
      toast.error('Please confirm you understand the risks of live trading');
      return;
    }

    setIsSubmitting(true);

    try {
      const accessToken = getAccessToken();
      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
      const anonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

      // Call the orders edge function
      const response = await fetch(`${supabaseUrl}/functions/v1/orders`, {
        method: 'POST',
        headers: {
          'apikey': anonKey,
          'Authorization': `Bearer ${accessToken || anonKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'place-orders',
          orders,
          tradingMode,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || 'Failed to place orders');
      }

      const data = await response.json();

      if (data.success) {
        toast.success(data.message || 'Orders placed successfully');
        onSuccess?.();
        onOpenChange(false);
      } else {
        // Partial success or failure
        const results = (data.results || []) as OrderResult[];
        const failedOrders = results.filter((r) => !r.success);
        if (failedOrders.length > 0) {
          toast.error(`${failedOrders.length} orders failed`);
        }
        if (data.summary?.success > 0) {
          toast.success(`${data.summary.success} orders placed successfully`);
          onSuccess?.();
        }
        onOpenChange(false);
      }
    } catch (error) {
      console.error('Error placing orders:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to place orders');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Confirm Orders
            <Badge variant={tradingMode === 'paper' ? 'secondary' : 'destructive'}>
              {tradingMode === 'paper' ? 'Paper Trading' : 'Live Trading'}
            </Badge>
          </DialogTitle>
          <DialogDescription>
            Review your orders before submitting
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Order Summary */}
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Total Orders</span>
            <span className="font-medium">{orders.length}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Total Shares</span>
            <span className="font-medium">{totalShares.toLocaleString()}</span>
          </div>
          <div className="flex items-center gap-4 text-sm">
            {buyOrders.length > 0 && (
              <Badge variant="outline" className="text-green-600 border-green-600">
                <TrendingUp className="h-3 w-3 mr-1" />
                {buyOrders.length} Buy
              </Badge>
            )}
            {sellOrders.length > 0 && (
              <Badge variant="outline" className="text-red-600 border-red-600">
                <TrendingDown className="h-3 w-3 mr-1" />
                {sellOrders.length} Sell
              </Badge>
            )}
          </div>

          {/* Order List */}
          <div className="max-h-60 overflow-y-auto border rounded-lg">
            <table className="w-full text-sm">
              <thead className="bg-muted sticky top-0">
                <tr>
                  <th className="text-left p-2">Ticker</th>
                  <th className="text-left p-2">Side</th>
                  <th className="text-right p-2">Qty</th>
                  <th className="text-left p-2">Type</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order, idx) => (
                  <tr key={idx} className="border-t">
                    <td className="p-2 font-medium">{order.ticker}</td>
                    <td className="p-2">
                      <Badge
                        variant="outline"
                        className={
                          order.side === 'buy'
                            ? 'text-green-600 border-green-600'
                            : 'text-red-600 border-red-600'
                        }
                      >
                        {order.side.toUpperCase()}
                      </Badge>
                    </td>
                    <td className="p-2 text-right font-mono">{order.quantity}</td>
                    <td className="p-2">{order.order_type}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Live Trading Warning */}
          {tradingMode === 'live' && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <p className="font-medium mb-2">This will execute real trades with real money!</p>
                <div className="flex items-center gap-2">
                  <Checkbox
                    id="live-confirm"
                    checked={liveConfirmed}
                    onCheckedChange={(checked) => setLiveConfirmed(checked === true)}
                  />
                  <label htmlFor="live-confirm" className="text-sm cursor-pointer">
                    I understand and accept the risks of live trading
                  </label>
                </div>
              </AlertDescription>
            </Alert>
          )}

          {/* Paper Trading Info */}
          {tradingMode === 'paper' && (
            <Alert>
              <AlertDescription>
                Paper trading uses simulated money. No real trades will be executed.
              </AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || (tradingMode === 'live' && !liveConfirmed)}
            variant={tradingMode === 'live' ? 'destructive' : 'default'}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Placing Orders...
              </>
            ) : (
              `Place ${orders.length} Order${orders.length > 1 ? 's' : ''}`
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
