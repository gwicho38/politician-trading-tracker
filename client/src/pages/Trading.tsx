import { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useAlpacaCredentials } from '@/hooks/useAlpacaCredentials';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Wallet, TrendingUp, ClipboardList, ArrowLeft, Loader2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import Header from '@/components/Header';
import { AlpacaConnectionCard } from '@/components/trading/AlpacaConnectionCard';
import { AccountDashboard } from '@/components/trading/AccountDashboard';
import { PositionsTable } from '@/components/trading/PositionsTable';
import { OrderHistory } from '@/components/trading/OrderHistory';

const Trading = () => {
  const { user, isLoading: authLoading } = useAuth();
  const [tradingMode, setTradingMode] = useState<'paper' | 'live'>('paper');
  const { isConnected, isLoading: credentialsLoading } = useAlpacaCredentials();
  const connected = isConnected(tradingMode);

  if (authLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="container mx-auto px-4 py-6 max-w-7xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Link to="/">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
            </Link>
            <div>
              <div className="flex items-center gap-3">
                <Wallet className="h-6 w-6 text-primary" />
                <h1 className="text-2xl font-bold">Trading</h1>
                <Badge
                  variant={tradingMode === 'paper' ? 'secondary' : 'destructive'}
                  className="ml-2"
                >
                  {tradingMode === 'paper' ? '📄 Paper Trading' : '💰 Live Trading'}
                </Badge>
              </div>
              <p className="text-muted-foreground mt-1">
                Execute trades based on politician trading signals
              </p>
            </div>
          </div>
        </div>

        {/* Auth Check */}
        {!user ? (
          <Card>
            <CardContent className="pt-6">
              <Alert>
                <AlertDescription className="flex items-center justify-between">
                  <span>Please sign in to access trading features.</span>
                  <Link to="/auth">
                    <Button size="sm">Sign In</Button>
                  </Link>
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        ) : (
          <Tabs defaultValue="overview" className="space-y-6">
            <TabsList className="grid w-full grid-cols-3 lg:w-[400px]">
              <TabsTrigger value="overview" className="flex items-center gap-2">
                <Wallet className="h-4 w-4" />
                Overview
              </TabsTrigger>
              <TabsTrigger value="signals" className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4" />
                Signals
              </TabsTrigger>
              <TabsTrigger value="orders" className="flex items-center gap-2">
                <ClipboardList className="h-4 w-4" />
                Orders
              </TabsTrigger>
            </TabsList>

            {/* Overview Tab */}
            <TabsContent value="overview" className="space-y-6">
              <div className="grid gap-6 md:grid-cols-2">
                {/* Trading Mode Card */}
                <Card>
                  <CardHeader>
                    <CardTitle>Trading Mode</CardTitle>
                    <CardDescription>
                      Select paper or live trading
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <Button
                          variant={tradingMode === 'paper' ? 'default' : 'outline'}
                          onClick={() => setTradingMode('paper')}
                          className="h-20 flex-col"
                        >
                          <span className="text-2xl mb-1">📄</span>
                          <span>Paper Trading</span>
                          {isConnected('paper') && (
                            <Badge variant="secondary" className="mt-1 text-xs">Connected</Badge>
                          )}
                        </Button>
                        <Button
                          variant={tradingMode === 'live' ? 'destructive' : 'outline'}
                          onClick={() => setTradingMode('live')}
                          className="h-20 flex-col"
                        >
                          <span className="text-2xl mb-1">💰</span>
                          <span>Live Trading</span>
                          {isConnected('live') && (
                            <Badge variant="secondary" className="mt-1 text-xs">Connected</Badge>
                          )}
                        </Button>
                      </div>
                      {tradingMode === 'live' && (
                        <Alert variant="destructive">
                          <AlertDescription>
                            Live trading uses real money. Make sure you understand the risks.
                          </AlertDescription>
                        </Alert>
                      )}
                    </div>
                  </CardContent>
                </Card>

                {/* Alpaca Connection Card */}
                <AlpacaConnectionCard tradingMode={tradingMode} />
              </div>

              {/* Account Dashboard */}
              {connected && (
                <>
                  <AccountDashboard tradingMode={tradingMode} />
                  <PositionsTable tradingMode={tradingMode} />
                </>
              )}
            </TabsContent>

            {/* Signals Tab */}
            <TabsContent value="signals" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Trading Signals</CardTitle>
                  <CardDescription>
                    AI-powered signals based on politician trading activity
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-center py-8">
                    <p className="text-muted-foreground mb-4">
                      View the full signals page for detailed analysis and trading cart.
                    </p>
                    <Link to="/trading-signals">
                      <Button>
                        <TrendingUp className="h-4 w-4 mr-2" />
                        Open Trading Signals
                      </Button>
                    </Link>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Orders Tab */}
            <TabsContent value="orders" className="space-y-6">
              {connected ? (
                <OrderHistory tradingMode={tradingMode} />
              ) : (
                <Card>
                  <CardHeader>
                    <CardTitle>Order History</CardTitle>
                    <CardDescription>
                      View and manage your trading orders
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="text-center py-8 text-muted-foreground">
                      <ClipboardList className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>Connect your Alpaca account to view order history</p>
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>
          </Tabs>
        )}
      </main>
    </div>
  );
};

export default Trading;
