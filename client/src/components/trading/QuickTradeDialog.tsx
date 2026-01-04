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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Loader2, TrendingUp, TrendingDown } from 'lucide-react';
import { usePlaceOrder } from '@/hooks/useOrders';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

interface Position {
  asset_id: string;
  symbol: string;
  qty: number;
  side: 'long' | 'short';
  avg_entry_price: number;
  current_price: number;
  market_value: number;
  unrealized_pl: number;
}

interface QuickTradeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  position: Position | null;
  tradingMode: 'paper' | 'live';
  defaultSide?: 'buy' | 'sell';
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function QuickTradeDialog({
  open,
  onOpenChange,
  position,
  tradingMode,
  defaultSide = 'sell',
}: QuickTradeDialogProps) {
  const [side, setSide] = useState<'buy' | 'sell'>(defaultSide);
  const [quantity, setQuantity] = useState<string>('');
  const [orderType, setOrderType] = useState<'market' | 'limit'>('market');
  const [limitPrice, setLimitPrice] = useState<string>('');

  const placeOrder = usePlaceOrder(tradingMode);

  // Reset form when dialog opens with new position
  const handleOpenChange = (newOpen: boolean) => {
    if (newOpen && position) {
      setSide(defaultSide);
      setQuantity(position.side === 'long' && defaultSide === 'sell' ? String(Math.abs(position.qty)) : '');
      setOrderType('market');
      setLimitPrice(position.current_price.toFixed(2));
    }
    onOpenChange(newOpen);
  };

  const handleSubmit = async () => {
    if (!position) return;

    const qty = parseFloat(quantity);
    if (isNaN(qty) || qty <= 0) {
      toast.error('Please enter a valid quantity');
      return;
    }

    // Validate limit price for limit orders
    if (orderType === 'limit') {
      const price = parseFloat(limitPrice);
      if (isNaN(price) || price <= 0) {
        toast.error('Please enter a valid limit price');
        return;
      }
    }

    try {
      await placeOrder.mutateAsync({
        ticker: position.symbol,
        side,
        quantity: qty,
        order_type: orderType,
        limit_price: orderType === 'limit' ? parseFloat(limitPrice) : undefined,
      });

      toast.success(`${side.toUpperCase()} order placed for ${qty} shares of ${position.symbol}`);
      onOpenChange(false);
    } catch (error: any) {
      toast.error(error.message || 'Failed to place order');
    }
  };

  const estimatedValue = position
    ? parseFloat(quantity || '0') * position.current_price
    : 0;

  if (!position) return null;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Trade {position.symbol}
            <Badge variant="outline" className="text-xs">
              {tradingMode === 'paper' ? 'Paper' : 'Live'}
            </Badge>
          </DialogTitle>
          <DialogDescription>
            Current position: {Math.abs(position.qty)} shares ({position.side})
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          {/* Position Summary */}
          <div className="grid grid-cols-2 gap-4 p-3 bg-muted rounded-lg">
            <div>
              <p className="text-xs text-muted-foreground">Current Price</p>
              <p className="font-mono font-medium">{formatCurrency(position.current_price)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Unrealized P&L</p>
              <p className={cn(
                "font-mono font-medium flex items-center gap-1",
                position.unrealized_pl >= 0 ? "text-green-600" : "text-red-600"
              )}>
                {position.unrealized_pl >= 0 ? (
                  <TrendingUp className="h-3 w-3" />
                ) : (
                  <TrendingDown className="h-3 w-3" />
                )}
                {formatCurrency(position.unrealized_pl)}
              </p>
            </div>
          </div>

          {/* Order Side */}
          <div className="grid gap-2">
            <Label>Side</Label>
            <div className="flex gap-2">
              <Button
                type="button"
                variant={side === 'buy' ? 'default' : 'outline'}
                className={cn(
                  "flex-1",
                  side === 'buy' && "bg-green-600 hover:bg-green-700"
                )}
                onClick={() => setSide('buy')}
              >
                <TrendingUp className="h-4 w-4 mr-2" />
                Buy
              </Button>
              <Button
                type="button"
                variant={side === 'sell' ? 'default' : 'outline'}
                className={cn(
                  "flex-1",
                  side === 'sell' && "bg-red-600 hover:bg-red-700"
                )}
                onClick={() => setSide('sell')}
              >
                <TrendingDown className="h-4 w-4 mr-2" />
                Sell
              </Button>
            </div>
          </div>

          {/* Quantity */}
          <div className="grid gap-2">
            <Label htmlFor="quantity">Quantity</Label>
            <div className="flex gap-2">
              <Input
                id="quantity"
                type="number"
                min="1"
                step="1"
                placeholder="Enter quantity"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className="flex-1"
              />
              {side === 'sell' && position.side === 'long' && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setQuantity(String(Math.abs(position.qty)))}
                >
                  Sell All
                </Button>
              )}
            </div>
          </div>

          {/* Order Type */}
          <div className="grid gap-2">
            <Label htmlFor="order-type">Order Type</Label>
            <Select value={orderType} onValueChange={(v) => setOrderType(v as 'market' | 'limit')}>
              <SelectTrigger id="order-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="market">Market</SelectItem>
                <SelectItem value="limit">Limit</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Limit Price (conditional) */}
          {orderType === 'limit' && (
            <div className="grid gap-2">
              <Label htmlFor="limit-price">Limit Price</Label>
              <Input
                id="limit-price"
                type="number"
                min="0.01"
                step="0.01"
                placeholder="Enter limit price"
                value={limitPrice}
                onChange={(e) => setLimitPrice(e.target.value)}
              />
            </div>
          )}

          {/* Estimated Value */}
          {quantity && parseFloat(quantity) > 0 && (
            <div className="p-3 bg-muted rounded-lg">
              <p className="text-xs text-muted-foreground">Estimated Value</p>
              <p className="font-mono text-lg font-medium">
                {formatCurrency(estimatedValue)}
              </p>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={placeOrder.isPending || !quantity || parseFloat(quantity) <= 0}
            className={cn(
              side === 'buy' ? "bg-green-600 hover:bg-green-700" : "bg-red-600 hover:bg-red-700"
            )}
          >
            {placeOrder.isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Placing Order...
              </>
            ) : (
              <>
                {side === 'buy' ? 'Buy' : 'Sell'} {quantity || 0} shares
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
