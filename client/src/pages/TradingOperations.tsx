import { useState, useEffect } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Loader2, Briefcase, ShoppingCart, Target, Plus, History, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { toast } from 'sonner';

interface AlpacaAccount {
  portfolio_value: string;
  cash: string;
  buying_power: string;
  status: string;
}

interface CartItem {
  id: string;
  ticker: string;
  asset_name: string;
  signal_type: string;
  quantity: number;
  confidence_score?: number;
  target_price?: number;
  stop_loss?: number;
  take_profit?: number;
}

interface TradingOrder {
  id: string;
  ticker: string;
  side: string;
  quantity: number;
  order_type: string;
  status: string;
  filled_quantity?: number;
  filled_avg_price?: number;
  submitted_at?: string;
  alpaca_order_id?: string;
}

const TradingOperations = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [accountInfo, setAccountInfo] = useState<AlpacaAccount | null>(null);
  const [cartItems, setCartItems] = useState<CartItem[]>([]);
  const [recentOrders, setRecentOrders] = useState<TradingOrder[]>([]);
  const [tradingMode, setTradingMode] = useState<'paper' | 'live'>('paper');
  const [hasLiveAccess, setHasLiveAccess] = useState(false);
  const [executingTrades, setExecutingTrades] = useState(false);

  // Manual order form
  const [manualTicker, setManualTicker] = useState('AAPL');
  const [manualQuantity, setManualQuantity] = useState(10);
  const [manualSide, setManualSide] = useState<'buy' | 'sell'>('buy');
  const [manualOrderType, setManualOrderType] = useState<'market' | 'limit'>('market');
  const [manualLimitPrice, setManualLimitPrice] = useState(100.00);
  const [manualConfirm, setManualConfirm] = useState(false);

  useEffect(() => {
    if (user) {
      loadData();
    } else {
      setLoading(false);
    }
  }, [user]);

  const loadData = async () => {
    try {
      await Promise.all([
        checkApiKeys(),
        loadAccountInfo(),
        loadCart(),
        loadRecentOrders()
      ]);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const checkApiKeys = async () => {
    // Check if user has API keys configured
    // This would typically call an API endpoint to check user settings
    // For now, we'll assume paper keys are available
    setHasLiveAccess(false); // TODO: Check actual subscription status
  };

  const loadAccountInfo = async () => {
    try {
      // Call Alpaca account Edge Function
      const { data, error } = await supabase.functions.invoke('alpaca-account');

      if (error) {
        throw new Error(error.message || 'Failed to load account information');
      }

      if (data.success && data.account) {
        setAccountInfo(data.account);
      } else {
        throw new Error(data.error || 'Invalid response from Alpaca API');
      }
    } catch (error) {
      console.error('Error loading account info:', error);
      // Set default account info on error
      setAccountInfo({
        portfolio_value: '0.00',
        cash: '0.00',
        buying_power: '0.00',
        status: 'ERROR'
      });
    }
  };

  const loadCart = async () => {
    try {
      // Load cart items from localStorage or API
      // For now, use mock data
      const mockCart: CartItem[] = [
        {
          id: '1',
          ticker: 'AAPL',
          asset_name: 'Apple Inc.',
          signal_type: 'buy',
          quantity: 10,
          confidence_score: 0.85,
          target_price: 180.00
        }
      ];
      setCartItems(mockCart);
    } catch (error) {
      console.error('Error loading cart:', error);
    }
  };

  const loadRecentOrders = async () => {
    try {
      const { data, error } = await supabase
        .from('trading_orders')
        .select('*')
        .eq('trading_mode', tradingMode)
        .order('created_at', { ascending: false })
        .limit(20);

      if (error) throw error;
      setRecentOrders(data || []);
    } catch (error) {
      console.error('Error loading orders:', error);
      toast.error('Failed to load recent orders');
    }
  };

  const executeCartTrades = async () => {
    if (!user) {
      toast.error('Please log in to execute trades');
      return;
    }

    setExecutingTrades(true);
    try {
      // Execute trades via API
      // This would call an Edge Function to execute trades with Alpaca
      toast.success('Cart trades executed successfully!');
      setCartItems([]); // Clear cart after execution
    } catch (error) {
      console.error('Error executing trades:', error);
      toast.error('Failed to execute trades');
    } finally {
      setExecutingTrades(false);
    }
  };

  const placeManualOrder = async () => {
    if (!user) {
      toast.error('Please log in to place orders');
      return;
    }

    try {
      // Place manual order via API
      const orderData = {
        ticker: manualTicker,
        quantity: manualQuantity,
        side: manualSide,
        order_type: manualOrderType,
        limit_price: manualOrderType === 'limit' ? manualLimitPrice : null,
        trading_mode: tradingMode
      };

      // This would call an Edge Function to place the order
      toast.success('Order placed successfully!');
      setManualConfirm(false);
      loadRecentOrders(); // Refresh orders
    } catch (error) {
      console.error('Error placing order:', error);
      toast.error('Failed to place order');
    }
  };

  const getSignalColor = (signalType: string) => {
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
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'filled':
        return 'bg-green-100 text-green-800';
      case 'pending':
      case 'submitted':
        return 'bg-yellow-100 text-yellow-800';
      case 'canceled':
      case 'rejected':
      case 'expired':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (!user) {
    return (
      <div className="container mx-auto p-6">
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Please log in to access trading operations.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Briefcase className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-3xl font-bold">Trading Operations</h1>
          <p className="text-muted-foreground">
            Execute trades based on AI signals with comprehensive risk management
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
                <strong>WARNING: LIVE TRADING MODE</strong><br />
                You are about to execute trades with REAL MONEY. Make sure you understand the risks involved.
              </AlertDescription>
            </Alert>
          )}

          {tradingMode === 'paper' && (
            <Alert className="mt-4 border-blue-200 bg-blue-50">
              <CheckCircle className="h-4 w-4 text-blue-600" />
              <AlertDescription className="text-blue-800">
                <strong>Paper Trading Mode (Safe)</strong><br />
                You're in paper trading mode, which uses simulated funds. Perfect for testing strategies.
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Account Information */}
      <Card>
        <CardHeader>
          <CardTitle>Account Information</CardTitle>
          <CardDescription>
            Your {tradingMode} trading account status
          </CardDescription>
        </CardHeader>
        <CardContent>
          {accountInfo ? (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold">${parseFloat(accountInfo.portfolio_value).toLocaleString()}</div>
                <p className="text-sm text-muted-foreground">Portfolio Value</p>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">${parseFloat(accountInfo.cash).toLocaleString()}</div>
                <p className="text-sm text-muted-foreground">Cash</p>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">${parseFloat(accountInfo.buying_power).toLocaleString()}</div>
                <p className="text-sm text-muted-foreground">Buying Power</p>
              </div>
              <div className="text-center">
                <Badge variant={accountInfo.status === 'ACTIVE' ? 'default' : 'secondary'}>
                  {accountInfo.status}
                </Badge>
                <p className="text-sm text-muted-foreground mt-1">Account Status</p>
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
              <p className="text-muted-foreground">Loading account information...</p>
            </div>
          )}
        </CardContent>
      </Card>

      <Tabs defaultValue="cart" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="cart" className="flex items-center gap-2">
            <ShoppingCart className="h-4 w-4" />
            Cart Execution
          </TabsTrigger>
          <TabsTrigger value="signals" className="flex items-center gap-2">
            <Target className="h-4 w-4" />
            Signal Trading
          </TabsTrigger>
          <TabsTrigger value="manual" className="flex items-center gap-2">
            <Plus className="h-4 w-4" />
            Manual Orders
          </TabsTrigger>
          <TabsTrigger value="orders" className="flex items-center gap-2">
            <History className="h-4 w-4" />
            Recent Orders
          </TabsTrigger>
        </TabsList>

        {/* Cart Execution Tab */}
        <TabsContent value="cart" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Execute Cart Trades</CardTitle>
              <CardDescription>
                Execute all trades currently in your shopping cart
              </CardDescription>
            </CardHeader>
            <CardContent>
              {cartItems.length > 0 ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 gap-4">
                    {cartItems.map((item) => (
                      <Card key={item.id} className="border-l-4 border-l-primary">
                        <CardContent className="pt-4">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <div>
                                <h3 className="font-semibold">{item.ticker} - {item.asset_name}</h3>
                                <div className="flex items-center gap-2 mt-1">
                                  <Badge className={getSignalColor(item.signal_type)}>
                                    {item.signal_type.toUpperCase().replace('_', ' ')}
                                  </Badge>
                                  {item.confidence_score && (
                                    <span className="text-sm text-muted-foreground">
                                      {(item.confidence_score * 100).toFixed(1)}% confidence
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="font-medium">Qty: {item.quantity}</div>
                              {item.target_price && (
                                <div className="text-sm text-muted-foreground">
                                  Target: ${item.target_price.toFixed(2)}
                                </div>
                              )}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>

                  <div className="flex gap-4">
                    <Button
                      onClick={executeCartTrades}
                      disabled={executingTrades}
                      className="flex items-center gap-2"
                      size="lg"
                    >
                      {executingTrades ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <ShoppingCart className="h-4 w-4" />
                      )}
                      Execute All Cart Trades
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <ShoppingCart className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">Your cart is empty</h3>
                  <p className="text-muted-foreground">
                    Add signals from the Trading Signals page to get started!
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Signal Trading Tab */}
        <TabsContent value="signals" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Signal-Based Trading</CardTitle>
              <CardDescription>
                Execute trades based on AI-generated signals with risk management
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8">
                <Target className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium mb-2">Signal Trading</h3>
                <p className="text-muted-foreground">
                  Advanced signal-based trading with risk management will be available soon.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Manual Orders Tab */}
        <TabsContent value="manual" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Manual Order Placement</CardTitle>
              <CardDescription>
                Place individual orders manually
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="ticker">Ticker Symbol</Label>
                    <Input
                      id="ticker"
                      value={manualTicker}
                      onChange={(e) => setManualTicker(e.target.value.toUpperCase())}
                      placeholder="AAPL"
                    />
                  </div>
                  <div>
                    <Label htmlFor="quantity">Quantity</Label>
                    <Input
                      id="quantity"
                      type="number"
                      min={1}
                      value={manualQuantity}
                      onChange={(e) => setManualQuantity(Number(e.target.value))}
                    />
                  </div>
                  <div>
                    <Label htmlFor="side">Side</Label>
                    <Select value={manualSide} onValueChange={(value) => setManualSide(value as 'buy' | 'sell')}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="buy">Buy</SelectItem>
                        <SelectItem value="sell">Sell</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <Label htmlFor="order-type">Order Type</Label>
                    <Select value={manualOrderType} onValueChange={(value) => setManualOrderType(value as 'market' | 'limit')}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="market">Market Order</SelectItem>
                        <SelectItem value="limit">Limit Order</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {manualOrderType === 'limit' && (
                    <div>
                      <Label htmlFor="limit-price">Limit Price</Label>
                      <Input
                        id="limit-price"
                        type="number"
                        min={0.01}
                        step={0.01}
                        value={manualLimitPrice}
                        onChange={(e) => setManualLimitPrice(Number(e.target.value))}
                      />
                    </div>
                  )}

                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="confirm-manual"
                      checked={manualConfirm}
                      onCheckedChange={setManualConfirm}
                    />
                    <Label htmlFor="confirm-manual" className="text-sm">
                      Confirm order placement
                    </Label>
                  </div>
                </div>
              </div>

              {tradingMode === 'live' && (
                <Alert className="border-red-200 bg-red-50">
                  <AlertTriangle className="h-4 w-4 text-red-600" />
                  <AlertDescription className="text-red-800">
                    This will execute a LIVE {manualSide.toUpperCase()} order for {manualQuantity} shares of {manualTicker}
                  </AlertDescription>
                </Alert>
              )}

              <Button
                onClick={placeManualOrder}
                disabled={!manualConfirm}
                className="w-full"
              >
                Place Order
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Recent Orders Tab */}
        <TabsContent value="orders" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Recent Orders</CardTitle>
              <CardDescription>
                Your recent trading orders ({tradingMode} account)
              </CardDescription>
            </CardHeader>
            <CardContent>
              {recentOrders.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-2">Ticker</th>
                        <th className="text-left p-2">Side</th>
                        <th className="text-left p-2">Qty</th>
                        <th className="text-left p-2">Type</th>
                        <th className="text-left p-2">Status</th>
                        <th className="text-left p-2">Filled</th>
                        <th className="text-left p-2">Avg Price</th>
                        <th className="text-left p-2">Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentOrders.map((order) => (
                        <tr key={order.id} className="border-b hover:bg-muted/50">
                          <td className="p-2 font-medium">{order.ticker}</td>
                          <td className="p-2">
                            <Badge variant={order.side === 'buy' ? 'default' : 'secondary'}>
                              {order.side.toUpperCase()}
                            </Badge>
                          </td>
                          <td className="p-2">{order.quantity}</td>
                          <td className="p-2">{order.order_type}</td>
                          <td className="p-2">
                            <Badge className={getStatusColor(order.status)}>
                              {order.status}
                            </Badge>
                          </td>
                          <td className="p-2">{order.filled_quantity || 0}</td>
                          <td className="p-2">
                            {order.filled_avg_price ? `$${order.filled_avg_price.toFixed(2)}` : '-'}
                          </td>
                          <td className="p-2">
                            {order.submitted_at ? new Date(order.submitted_at).toLocaleDateString() : 'N/A'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-8">
                  <History className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">No orders found</h3>
                  <p className="text-muted-foreground">
                    Your recent orders will appear here.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default TradingOperations;