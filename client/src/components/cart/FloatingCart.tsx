/**
 * FloatingCart Component
 * A floating cart button and panel that persists across all pages
 */

import { useState } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';
import { useCart } from '@/contexts/CartContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  ShoppingCart,
  X,
  Loader2,
  TrendingUp,
  TrendingDown,
  Minus,
  Trash2,
} from 'lucide-react';
import { toast } from 'sonner';

function getSignalIcon(signalType: string) {
  switch (signalType) {
    case 'buy':
    case 'strong_buy':
      return <TrendingUp className="h-4 w-4 text-green-600" />;
    case 'sell':
    case 'strong_sell':
      return <TrendingDown className="h-4 w-4 text-red-600" />;
    default:
      return <Minus className="h-4 w-4 text-gray-600" />;
  }
}

function getSignalColor(signalType: string) {
  switch (signalType) {
    case 'buy':
    case 'strong_buy':
      return 'bg-green-100 text-green-800 border-green-200';
    case 'sell':
    case 'strong_sell':
      return 'bg-red-100 text-red-800 border-red-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
}

export function FloatingCart() {
  const { user } = useAuth();
  const {
    items,
    isOpen,
    toggleCart,
    closeCart,
    removeFromCart,
    updateQuantity,
    clearCart,
    totalItems,
    totalShares,
  } = useCart();

  const [placingOrders, setPlacingOrders] = useState(false);

  const placeOrders = async () => {
    if (!user) {
      toast.error('Please log in to place orders');
      return;
    }

    if (items.length === 0) {
      toast.error('Cart is empty');
      return;
    }

    setPlacingOrders(true);

    try {
      // Convert cart items to order format
      const orders = items.map((item) => ({
        ticker: item.signal.ticker,
        side: item.signal.signal_type.includes('buy') ? 'buy' : 'sell',
        quantity: item.quantity,
        order_type: 'market',
        signal_id: item.signal.source === 'trading_signals' ? item.signal.id : undefined,
      }));

      // Call the orders edge function
      const { data, error } = await supabase.functions.invoke('orders', {
        body: {
          action: 'place-orders',
          orders,
        },
      });

      if (error) {
        throw new Error(error.message || 'Failed to place orders');
      }

      if (data.success) {
        toast.success(data.message || `${data.summary?.success || 0} orders placed successfully`);
        clearCart(); // Clear cart after successful orders
        closeCart();
      } else {
        // Show results summary
        const failedOrders = data.results?.filter((r: any) => !r.success) || [];
        if (failedOrders.length > 0) {
          toast.error(
            `${failedOrders.length} orders failed: ${failedOrders.map((o: any) => o.ticker).join(', ')}`
          );
        }
        if (data.summary?.success > 0) {
          toast.success(`${data.summary.success} orders placed successfully`);
          // Remove successful orders from cart
          const successTickers =
            data.results?.filter((r: any) => r.success).map((r: any) => r.ticker) || [];
          successTickers.forEach((ticker: string) => removeFromCart(ticker));
        }
      }
    } catch (error: any) {
      console.error('Error placing orders:', error);
      toast.error(error.message || 'Failed to place orders');
    } finally {
      setPlacingOrders(false);
    }
  };

  return (
    <>
      {/* Floating Cart Button */}
      <Button
        onClick={toggleCart}
        className="fixed bottom-6 right-6 z-40 h-14 w-14 rounded-full shadow-lg"
        size="icon"
      >
        <ShoppingCart className="h-6 w-6" />
        {totalItems > 0 && (
          <Badge className="absolute -top-2 -right-2 h-6 w-6 rounded-full p-0 flex items-center justify-center text-xs">
            {totalItems}
          </Badge>
        )}
      </Button>

      {/* Cart Panel Overlay */}
      {isOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <Card className="w-full max-w-lg max-h-[80vh] overflow-hidden flex flex-col">
            <CardHeader className="flex flex-row items-center justify-between shrink-0">
              <CardTitle className="flex items-center gap-2">
                <ShoppingCart className="h-5 w-5" />
                Cart ({totalItems} {totalItems === 1 ? 'signal' : 'signals'})
              </CardTitle>
              <Button variant="ghost" size="sm" onClick={closeCart}>
                <X className="h-4 w-4" />
              </Button>
            </CardHeader>

            <CardContent className="overflow-y-auto flex-1">
              {items.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <ShoppingCart className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Your cart is empty</p>
                  <p className="text-sm">Add some trading signals to get started</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {items.map((item) => (
                    <div
                      key={item.signal.ticker}
                      className="flex items-center justify-between p-3 border rounded-lg"
                    >
                      <div className="flex items-center gap-3 flex-1">
                        {getSignalIcon(item.signal.signal_type)}
                        <div className="flex-1">
                          <p className="font-medium">{item.signal.ticker}</p>
                          <p className="text-sm text-muted-foreground">
                            {item.signal.asset_name || 'Unknown asset'}
                          </p>
                          <div className="flex items-center gap-2 mt-1">
                            <Badge
                              className={`${getSignalColor(item.signal.signal_type)} text-xs`}
                            >
                              {item.signal.signal_type.replace('_', ' ').toUpperCase()}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              {Math.round(item.signal.confidence_score * 100)}% conf.
                            </span>
                            {item.signal.source === 'playground' && (
                              <Badge variant="outline" className="text-xs">
                                Preview
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex items-center gap-1">
                          <Label
                            htmlFor={`qty-${item.signal.ticker}`}
                            className="text-xs text-muted-foreground"
                          >
                            Qty:
                          </Label>
                          <Input
                            id={`qty-${item.signal.ticker}`}
                            type="number"
                            min={1}
                            value={item.quantity}
                            onChange={(e) =>
                              updateQuantity(item.signal.ticker, parseInt(e.target.value) || 1)
                            }
                            className="w-16 h-8 text-center"
                          />
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeFromCart(item.signal.ticker)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>

            {items.length > 0 && (
              <div className="p-4 border-t space-y-3 shrink-0">
                {!user && (
                  <Alert>
                    <AlertDescription>Please log in to place orders</AlertDescription>
                  </Alert>
                )}
                <div className="text-sm text-muted-foreground">Total shares: {totalShares}</div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    className="flex-1"
                    onClick={clearCart}
                    disabled={placingOrders}
                  >
                    Clear All
                  </Button>
                  <Button
                    className="flex-1"
                    onClick={placeOrders}
                    disabled={!user || placingOrders}
                  >
                    {placingOrders ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Placing Orders...
                      </>
                    ) : (
                      <>
                        Place {totalItems} Order{totalItems > 1 ? 's' : ''}
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}
          </Card>
        </div>
      )}
    </>
  );
}

export default FloatingCart;
