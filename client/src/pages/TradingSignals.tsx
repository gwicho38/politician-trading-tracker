import { useState, useEffect } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';
import { useCart } from '@/contexts/CartContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Target, TrendingUp, TrendingDown, Minus, Download, ShoppingCart, X } from 'lucide-react';
import { toast } from 'sonner';
import type { CartSignal } from '@/types/cart';

interface TradingSignal {
  id: string;
  ticker: string;
  asset_name: string;
  signal_type: 'buy' | 'sell' | 'hold' | 'strong_buy' | 'strong_sell';
  signal_strength: string;
  confidence_score: number;
  target_price?: number;
  stop_loss?: number;
  take_profit?: number;
  generated_at: string;
  politician_activity_count: number;
  buy_sell_ratio: number;
  is_active: boolean;
}

const TradingSignals = () => {
  const { user } = useAuth();
  const { addToCart, removeFromCart, isInCart, openCart, totalItems } = useCart();
  const [signals, setSignals] = useState<TradingSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  // Signal generation parameters
  const [lookbackDays, setLookbackDays] = useState(30);
  const [minConfidence, setMinConfidence] = useState(0.65);
  const [fetchMarketData, setFetchMarketData] = useState(true);

  // Filters
  const [signalTypeFilter, setSignalTypeFilter] = useState<string[]>(['buy', 'strong_buy', 'sell', 'strong_sell']);
  const [minConfidenceDisplay, setMinConfidenceDisplay] = useState(0.0);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  useEffect(() => {
    fetchSignals();
  }, []);

  const fetchSignals = async () => {
    try {
      const { data: signals, error } = await supabase
        .from('trading_signals')
        .select('*')
        .eq('is_active', true)
        .order('created_at', { ascending: false })
        .limit(100);

      if (error) {
        throw new Error(`Database error: ${error.message}`);
      }

      setSignals(signals || []);
    } catch (error) {
      console.error('Error fetching signals:', error);
      toast.error('Failed to load trading signals');
    } finally {
      setLoading(false);
    }
  };

  const generateSignals = async () => {
    if (!user) {
      toast.error('Please log in to generate signals');
      return;
    }

    setGenerating(true);
    try {
      const { data, error } = await supabase.functions.invoke('trading-signals/generate-signals', {
        body: {
          lookbackDays,
          minConfidence,
          fetchMarketData
        }
      });

      if (error) {
        throw new Error(error.message || 'Failed to generate signals');
      }

      if (data.success) {
        toast.success(`Generated ${data.signals?.length || 0} trading signals`);
        fetchSignals();
      } else {
        throw new Error(data.error || 'Failed to generate signals');
      }
    } catch (error) {
      console.error('Error generating signals:', error);
      toast.error('Failed to generate signals');
    } finally {
      setGenerating(false);
    }
  };

  const getSignalIcon = (signalType: string) => {
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

  // Convert TradingSignal to CartSignal
  const toCartSignal = (signal: TradingSignal): CartSignal => ({
    id: signal.id,
    ticker: signal.ticker,
    asset_name: signal.asset_name,
    signal_type: signal.signal_type,
    confidence_score: signal.confidence_score,
    politician_activity_count: signal.politician_activity_count,
    buy_sell_ratio: signal.buy_sell_ratio,
    target_price: signal.target_price,
    source: 'trading_signals',
    signal_strength: signal.signal_strength,
    generated_at: signal.generated_at,
  });

  const handleCartAction = (signal: TradingSignal) => {
    if (isInCart(signal.ticker)) {
      removeFromCart(signal.ticker);
    } else {
      addToCart(toCartSignal(signal));
    }
  };

  const filteredSignals = signals.filter(signal =>
    signalTypeFilter.includes(signal.signal_type) &&
    signal.confidence_score >= minConfidenceDisplay
  );

  // Pagination
  const totalPages = Math.ceil(filteredSignals.length / pageSize);
  const paginatedSignals = filteredSignals.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  const topSignals = signals.slice(0, 10);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Target className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-3xl font-bold">Trading Signals</h1>
            <p className="text-muted-foreground">
              AI-powered trading recommendations based on politician activity
            </p>
          </div>
        </div>

        <Button
          variant="outline"
          onClick={openCart}
          className="relative"
        >
          <ShoppingCart className="h-4 w-4 mr-2" />
          Cart
          {totalItems > 0 && (
            <Badge className="absolute -top-2 -right-2 h-5 w-5 rounded-full p-0 flex items-center justify-center text-xs">
              {totalItems}
            </Badge>
          )}
        </Button>
      </div>

      {/* Signal Generation Parameters */}
      <Card>
        <CardHeader>
          <CardTitle>Signal Generation Parameters</CardTitle>
          <CardDescription>
            Configure parameters for generating new trading signals
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="lookback">Look back period (days)</Label>
              <Input
                id="lookback"
                type="number"
                min={7}
                max={1825}
                value={lookbackDays}
                onChange={(e) => setLookbackDays(Number(e.target.value))}
              />
            </div>

            <div className="space-y-2">
              <Label>Minimum confidence: {minConfidence.toFixed(2)}</Label>
              <Slider
                value={[minConfidence]}
                onValueChange={(value) => setMinConfidence(value[0])}
                min={0}
                max={1}
                step={0.05}
                className="w-full"
              />
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                id="market-data"
                checked={fetchMarketData}
                onCheckedChange={setFetchMarketData}
              />
              <Label htmlFor="market-data">Fetch market data</Label>
            </div>
          </div>

          <div className="flex gap-4">
            <Button
              onClick={generateSignals}
              disabled={generating || !user}
              className="flex items-center gap-2"
            >
              {generating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Target className="h-4 w-4" />
              )}
              {generating ? 'Generating...' : 'Generate Signals'}
            </Button>

            {!user && (
              <Alert className="flex-1">
                <AlertDescription>
                  Log in to generate new signals. You can view existing signals below.
                </AlertDescription>
              </Alert>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Active Signals Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{signals.length}</div>
            <p className="text-xs text-muted-foreground">Total Signals</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-green-600">
              {signals.filter(s => s.signal_type.includes('buy')).length}
            </div>
            <p className="text-xs text-muted-foreground">Buy Signals</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-red-600">
              {signals.filter(s => s.signal_type.includes('sell')).length}
            </div>
            <p className="text-xs text-muted-foreground">Sell Signals</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-gray-600">
              {signals.filter(s => s.signal_type === 'hold').length}
            </div>
            <p className="text-xs text-muted-foreground">Hold Signals</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Filter Signals</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Signal Type</Label>
              <div className="flex flex-wrap gap-2">
                {['buy', 'strong_buy', 'sell', 'strong_sell', 'hold'].map(type => (
                  <Button
                    key={type}
                    variant={signalTypeFilter.includes(type) ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => {
                      if (signalTypeFilter.includes(type)) {
                        setSignalTypeFilter(signalTypeFilter.filter(t => t !== type));
                      } else {
                        setSignalTypeFilter([...signalTypeFilter, type]);
                      }
                    }}
                  >
                    {type.replace('_', ' ').toUpperCase()}
                  </Button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <Label>Minimum Confidence: {minConfidenceDisplay.toFixed(2)}</Label>
              <Slider
                value={[minConfidenceDisplay]}
                onValueChange={(value) => setMinConfidenceDisplay(value[0])}
                min={0}
                max={1}
                step={0.05}
                className="w-full"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Signals Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Active Trading Signals</CardTitle>
             <CardDescription>
               {filteredSignals.length} signals match your filters - Page {currentPage} of {totalPages || 1}
             </CardDescription>
          </div>
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </Button>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-2">Ticker</th>
                  <th className="text-left p-2">Signal</th>
                  <th className="text-left p-2">Strength</th>
                  <th className="text-left p-2">Confidence</th>
                  <th className="text-left p-2">Politicians</th>
                  <th className="text-left p-2">B/S Ratio</th>
                  <th className="text-left p-2">Target</th>
                  <th className="text-left p-2">Generated</th>
                  <th className="text-left p-2">Action</th>
                </tr>
              </thead>
               <tbody>
                 {paginatedSignals.map(signal => (
                   <tr key={signal.id} className="border-b hover:bg-muted/50">
                     <td className="p-2 font-medium">{signal.ticker}</td>
                     <td className="p-2">
                       <Badge className={getSignalColor(signal.signal_type)}>
                         <div className="flex items-center gap-1">
                           {getSignalIcon(signal.signal_type)}
                           {signal.signal_type.replace('_', ' ').toUpperCase()}
                         </div>
                       </Badge>
                     </td>
                     <td className="p-2">{signal.signal_strength}</td>
                     <td className="p-2">{(signal.confidence_score * 100).toFixed(1)}%</td>
                     <td className="p-2">{signal.politician_activity_count}</td>
                     <td className="p-2">{signal.buy_sell_ratio.toFixed(2)}</td>
                     <td className="p-2">
                       {signal.target_price ? `$${signal.target_price.toFixed(2)}` : 'N/A'}
                     </td>
                     <td className="p-2">
                       {new Date(signal.generated_at).toLocaleDateString()}
                     </td>
                     <td className="p-2">
                       <Button
                         variant={isInCart(signal.ticker) ? "default" : "outline"}
                         size="sm"
                         onClick={() => handleCartAction(signal)}
                       >
                         {isInCart(signal.ticker) ? (
                           <X className="h-3 w-3" />
                         ) : (
                           <ShoppingCart className="h-3 w-3" />
                         )}
                       </Button>
                     </td>
                   </tr>
                 ))}
               </tbody>
            </table>
          </div>
        </CardContent>

        {/* Pagination Controls */}
        {filteredSignals.length > pageSize && (
          <div className="flex items-center justify-between px-6 py-4 border-t">
            <div className="flex items-center gap-2">
              <Label htmlFor="page-size">Show:</Label>
              <select
                id="page-size"
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setCurrentPage(1);
                }}
                className="px-2 py-1 border rounded"
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
              <span className="text-sm text-muted-foreground">
                Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, filteredSignals.length)} of {filteredSignals.length} signals
              </span>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
              >
                Previous
              </Button>

              <span className="text-sm">
                Page {currentPage} of {totalPages}
              </span>

              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Top 10 Signals */}
      <Card>
        <CardHeader>
          <CardTitle>Top 10 Signals by Confidence</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {topSignals.map(signal => (
            <Card key={signal.id} className="border-l-4 border-l-primary">
              <CardContent className="pt-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {getSignalIcon(signal.signal_type)}
                    <div>
                      <h3 className="font-semibold">{signal.ticker} - {signal.asset_name}</h3>
                      <p className="text-sm text-muted-foreground">
                        {signal.signal_type.replace('_', ' ').toUpperCase()} - {(signal.confidence_score * 100).toFixed(1)}% confidence
                      </p>
                    </div>
                   </div>
                   <Button
                     variant={isInCart(signal.ticker) ? "default" : "outline"}
                     size="sm"
                     onClick={() => handleCartAction(signal)}
                   >
                     {isInCart(signal.ticker) ? "Remove from Cart" : "Add to Cart"}
                   </Button>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Politicians</p>
                    <p className="font-medium">{signal.politician_activity_count}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">B/S Ratio</p>
                    <p className="font-medium">{signal.buy_sell_ratio.toFixed(2)}</p>
                  </div>
                  {signal.target_price && (
                    <div>
                      <p className="text-muted-foreground">Target Price</p>
                      <p className="font-medium">${signal.target_price.toFixed(2)}</p>
                    </div>
                  )}
                  <div>
                    <p className="text-muted-foreground">Generated</p>
                    <p className="font-medium">{new Date(signal.generated_at).toLocaleDateString()}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </CardContent>
      </Card>
    </div>
  );
};

export default TradingSignals;
