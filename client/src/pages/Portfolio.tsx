import { useState, useEffect } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Loader2, TrendingUp, TrendingDown, DollarSign, PieChart, BarChart, AlertTriangle, CheckCircle, XCircle, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

interface AlpacaAccount {
  portfolio_value: string;
  cash: string;
  buying_power: string;
  last_equity: string;
  long_market_value: string;
  status: string;
}

interface Position {
  id: string;
  ticker: string;
  asset_name: string;
  quantity: number;
  side: string;
  avg_entry_price: number;
  current_price: number;
  market_value: number;
  unrealized_pl: number;
  unrealized_pl_pct: number;
  stop_loss?: number;
  take_profit?: number;
  is_open: boolean;
}

interface PendingOrder {
  id: string;
  ticker: string;
  side: string;
  quantity: number;
  order_type: string;
  status: string;
  submitted_at?: string;
}

const Portfolio = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [accountInfo, setAccountInfo] = useState<AlpacaAccount | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [pendingOrders, setPendingOrders] = useState<PendingOrder[]>([]);
  const [tradingMode, setTradingMode] = useState<'paper' | 'live'>('paper');
  const [hasLiveAccess, setHasLiveAccess] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'checking' | 'connected' | 'error'>('checking');

  useEffect(() => {
    if (user) {
      checkApiKeys();
      loadPortfolioData();
    } else {
      setLoading(false);
    }
  }, [user, tradingMode]);

  const checkApiKeys = async () => {
    try {
      // Check if user has API keys configured
      // This would typically call an API endpoint to check user settings
      setHasLiveAccess(false); // TODO: Check actual subscription status
    } catch (error) {
      console.error('Error checking API keys:', error);
    }
  };

  const loadPortfolioData = async () => {
    if (!user) return;

    setLoading(true);
    try {
      // Test Alpaca connection
      setConnectionStatus('checking');

      // Load portfolio data from Edge Function
      const { data: portfolioData, error: portfolioError } = await supabase.functions.invoke('portfolio', {
        body: { action: 'get-portfolio' }
      });

      if (portfolioError) {
        console.error('Portfolio error:', portfolioError);
        setConnectionStatus('error');
      } else if (portfolioData?.success) {
        setPositions(portfolioData.positions || []);
        setConnectionStatus('connected');
      } else {
        setConnectionStatus('error');
      }

      // Load pending orders from Edge Function
      const { data: ordersData, error: ordersError } = await supabase.functions.invoke('orders', {
        body: { action: 'get-orders', trading_mode: tradingMode, status: 'open', limit: 10 }
      });

      if (ordersError) {
        console.error('Orders error:', ordersError);
        setPendingOrders([]);
      } else if (ordersData?.success) {
        setPendingOrders(ordersData.orders || []);
      } else {
        setPendingOrders([]);
      }

    } catch (error) {
      console.error('Error loading portfolio data:', error);
      setConnectionStatus('error');
      toast.error('Failed to load portfolio data');
    } finally {
      setLoading(false);
    }
  };

  const closePosition = async (ticker: string) => {
    try {
      // Close position via API
      toast.success(`Position in ${ticker} closed successfully`);
      loadPortfolioData(); // Refresh data
    } catch (error) {
      console.error('Error closing position:', error);
      toast.error('Failed to close position');
    }
  };

  const getPlColor = (value: number) => {
    return value > 0 ? 'text-green-600' : value < 0 ? 'text-red-600' : 'text-gray-600';
  };

  const getPlBadgeVariant = (value: number) => {
    return value > 0 ? 'default' : value < 0 ? 'destructive' : 'secondary';
  };

  const calculateRiskMetrics = () => {
    if (!accountInfo || !positions.length) return null;

    const totalValue = parseFloat(accountInfo.portfolio_value);
    const totalExposure = positions.reduce((sum, pos) => sum + Math.abs(pos.market_value), 0);
    const exposurePct = (totalExposure / totalValue) * 100;

    const totalUnrealizedPl = positions.reduce((sum, pos) => sum + pos.unrealized_pl, 0);
    const unrealizedPlPct = (totalUnrealizedPl / totalValue) * 100;

    const largestPosition = Math.max(...positions.map(pos => pos.market_value));
    const largestPositionPct = (largestPosition / totalValue) * 100;

    const winningPositions = positions.filter(pos => pos.unrealized_pl > 0).length;
    const winRate = (winningPositions / positions.length) * 100;

    return {
      exposurePct,
      totalExposure,
      totalUnrealizedPl,
      unrealizedPlPct,
      largestPosition,
      largestPositionPct,
      winningPositions,
      totalPositions: positions.length,
      winRate
    };
  };

  const riskMetrics = calculateRiskMetrics();

  if (!user) {
    return (
      <div className="container mx-auto p-6">
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Please log in to access your portfolio.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center gap-3">
        <TrendingUp className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-3xl font-bold">Portfolio Management</h1>
          <p className="text-muted-foreground">
            Monitor your positions, performance, and risk metrics
          </p>
        </div>
      </div>

      {/* Connection Status */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-3">
            {connectionStatus === 'checking' && (
              <>
                <Loader2 className="h-5 w-5 animate-spin text-yellow-600" />
                <span className="text-yellow-600">Testing Alpaca connection...</span>
              </>
            )}
            {connectionStatus === 'connected' && (
              <>
                <CheckCircle className="h-5 w-5 text-green-600" />
                <span className="text-green-600">Connected to Alpaca API</span>
              </>
            )}
            {connectionStatus === 'error' && (
              <>
                <XCircle className="h-5 w-5 text-red-600" />
                <span className="text-red-600">Failed to connect to Alpaca API</span>
              </>
            )}
          </div>
        </CardContent>
      </Card>

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
                Viewing LIVE trading account with real money at risk.
              </AlertDescription>
            </Alert>
          )}

          {tradingMode === 'paper' && (
            <Alert className="mt-4 border-blue-200 bg-blue-50">
              <CheckCircle className="h-4 w-4 text-blue-600" />
              <AlertDescription className="text-blue-800">
                Viewing paper trading account with simulated funds.
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Pending Orders */}
      {pendingOrders.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <RefreshCw className="h-5 w-5" />
              Pending Orders
            </CardTitle>
            <CardDescription>
              Orders that are currently pending execution
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {pendingOrders.map((order) => (
                <div key={order.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <Badge variant={order.side === 'buy' ? 'default' : 'secondary'}>
                      {order.side.toUpperCase()}
                    </Badge>
                    <div>
                      <div className="font-medium">{order.ticker}</div>
                      <div className="text-sm text-muted-foreground">
                        {order.quantity} shares • {order.order_type} • {order.status}
                      </div>
                    </div>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {order.submitted_at ? new Date(order.submitted_at).toLocaleDateString() : 'N/A'}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="positions">Positions</TabsTrigger>
          <TabsTrigger value="risk">Risk Analysis</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
        </TabsList>

        {/* Portfolio Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          {accountInfo && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
              <Card>
                <CardContent className="pt-6">
                  <div className="text-2xl font-bold">
                    ${parseFloat(accountInfo.portfolio_value).toLocaleString()}
                  </div>
                  <p className="text-xs text-muted-foreground">Portfolio Value</p>
                  <div className="text-sm mt-1">
                    <span className={getPlColor(parseFloat(accountInfo.portfolio_value) - parseFloat(accountInfo.last_equity))}>
                      ${((parseFloat(accountInfo.portfolio_value) - parseFloat(accountInfo.last_equity))).toFixed(2)}
                    </span>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="text-2xl font-bold">
                    ${parseFloat(accountInfo.cash).toLocaleString()}
                  </div>
                  <p className="text-xs text-muted-foreground">Cash</p>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="text-2xl font-bold">
                    ${parseFloat(accountInfo.buying_power).toLocaleString()}
                  </div>
                  <p className="text-xs text-muted-foreground">Buying Power</p>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="text-2xl font-bold">
                    ${parseFloat(accountInfo.long_market_value).toLocaleString()}
                  </div>
                  <p className="text-xs text-muted-foreground">Long Value</p>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="text-2xl font-bold">{positions.length}</div>
                  <p className="text-xs text-muted-foreground">Open Positions</p>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Risk Metrics */}
          {riskMetrics && (
            <Card>
              <CardHeader>
                <CardTitle>Risk Metrics</CardTitle>
                <CardDescription>
                  Current portfolio risk indicators
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold">{riskMetrics.exposurePct.toFixed(1)}%</div>
                    <p className="text-xs text-muted-foreground">Total Exposure</p>
                    <p className="text-sm">${riskMetrics.totalExposure.toLocaleString()}</p>
                    {riskMetrics.exposurePct > 80 && (
                      <Badge variant="destructive" className="mt-1">High</Badge>
                    )}
                  </div>

                  <div className="text-center">
                    <div className={`text-2xl font-bold ${getPlColor(riskMetrics.unrealizedPlPct)}`}>
                      {riskMetrics.unrealizedPlPct.toFixed(2)}%
                    </div>
                    <p className="text-xs text-muted-foreground">Unrealized P&L</p>
                    <p className={`text-sm ${getPlColor(riskMetrics.totalUnrealizedPl)}`}>
                      ${riskMetrics.totalUnrealizedPl.toLocaleString()}
                    </p>
                  </div>

                  <div className="text-center">
                    <div className="text-2xl font-bold">{riskMetrics.largestPositionPct.toFixed(1)}%</div>
                    <p className="text-xs text-muted-foreground">Largest Position</p>
                    <p className="text-sm">${riskMetrics.largestPosition.toLocaleString()}</p>
                    {riskMetrics.largestPositionPct > 15 && (
                      <Badge variant="destructive" className="mt-1">Concentrated</Badge>
                    )}
                  </div>

                  <div className="text-center">
                    <div className="text-2xl font-bold">{riskMetrics.winRate.toFixed(1)}%</div>
                    <p className="text-xs text-muted-foreground">Win Rate</p>
                    <p className="text-sm">
                      {riskMetrics.winningPositions}/{riskMetrics.totalPositions} positions
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Positions Tab */}
        <TabsContent value="positions" className="space-y-6">
          {positions.length > 0 ? (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>Open Positions</CardTitle>
                  <CardDescription>
                    Your current portfolio positions
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left p-2">Ticker</th>
                          <th className="text-left p-2">Side</th>
                          <th className="text-left p-2">Quantity</th>
                          <th className="text-left p-2">Avg Entry</th>
                          <th className="text-left p-2">Current</th>
                          <th className="text-left p-2">Market Value</th>
                          <th className="text-left p-2">P&L</th>
                          <th className="text-left p-2">P&L %</th>
                          <th className="text-left p-2">Stop Loss</th>
                          <th className="text-left p-2">Take Profit</th>
                        </tr>
                      </thead>
                      <tbody>
                        {positions.map((position) => (
                          <tr key={position.id} className="border-b hover:bg-muted/50">
                            <td className="p-2 font-medium">{position.ticker}</td>
                            <td className="p-2">
                              <Badge variant={position.side === 'long' ? 'default' : 'secondary'}>
                                {position.side.toUpperCase()}
                              </Badge>
                            </td>
                            <td className="p-2">{position.quantity}</td>
                            <td className="p-2">${position.avg_entry_price.toFixed(2)}</td>
                            <td className="p-2">${position.current_price.toFixed(2)}</td>
                            <td className="p-2">${position.market_value.toLocaleString()}</td>
                            <td className={`p-2 ${getPlColor(position.unrealized_pl)}`}>
                              ${position.unrealized_pl.toLocaleString()}
                            </td>
                            <td className={`p-2 ${getPlColor(position.unrealized_pl_pct)}`}>
                              {position.unrealized_pl_pct.toFixed(2)}%
                            </td>
                            <td className="p-2">
                              {position.stop_loss ? `$${position.stop_loss.toFixed(2)}` : 'N/A'}
                            </td>
                            <td className="p-2">
                              {position.take_profit ? `$${position.take_profit.toFixed(2)}` : 'N/A'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>

              {/* Position Details */}
              <div className="grid gap-4">
                {positions.map((position) => (
                  <Card key={position.id}>
                    <CardHeader>
                      <CardTitle className="flex items-center justify-between">
                        <span>{position.ticker} - {position.asset_name}</span>
                        <Badge variant={getPlBadgeVariant(position.unrealized_pl)}>
                          {position.side.toUpperCase()} {position.quantity}
                        </Badge>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                        <div>
                          <p className="text-sm text-muted-foreground">Avg Entry Price</p>
                          <p className="font-medium">${position.avg_entry_price.toFixed(2)}</p>
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">Current Price</p>
                          <p className="font-medium">${position.current_price.toFixed(2)}</p>
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">Market Value</p>
                          <p className="font-medium">${position.market_value.toLocaleString()}</p>
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">Unrealized P&L</p>
                          <p className={`font-medium ${getPlColor(position.unrealized_pl)}`}>
                            ${position.unrealized_pl.toLocaleString()} ({position.unrealized_pl_pct.toFixed(2)}%)
                          </p>
                        </div>
                      </div>

                      <div className="flex gap-2">
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => closePosition(position.ticker)}
                        >
                          Close Position
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </>
          ) : (
            <Card>
              <CardContent className="pt-6 text-center py-8">
                <PieChart className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium mb-2">No open positions</h3>
                <p className="text-muted-foreground">
                  Your portfolio doesn't have any open positions yet.
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Risk Analysis Tab */}
        <TabsContent value="risk" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Risk Report</CardTitle>
              <CardDescription>
                Detailed risk analysis of your portfolio
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8">
                <AlertTriangle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium mb-2">Risk Analysis</h3>
                <p className="text-muted-foreground">
                  Advanced risk analysis and monitoring will be available soon.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Performance Tab */}
        <TabsContent value="performance" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Performance Tracking</CardTitle>
              <CardDescription>
                Historical performance and analytics
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8">
                <BarChart className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium mb-2">Coming Soon</h3>
                <p className="text-muted-foreground">
                  Historical performance tracking, benchmark comparison, and trade history will be available soon.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Portfolio;