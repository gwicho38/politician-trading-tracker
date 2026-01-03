import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, CheckCircle2, XCircle, Eye, EyeOff, ExternalLink, Trash2 } from 'lucide-react';
import { useAlpacaCredentials } from '@/hooks/useAlpacaCredentials';
import { formatDistanceToNow } from 'date-fns';

interface AlpacaConnectionCardProps {
  tradingMode: 'paper' | 'live';
  onConnectionChange?: (connected: boolean) => void;
}

export function AlpacaConnectionCard({ tradingMode, onConnectionChange }: AlpacaConnectionCardProps) {
  const {
    isLoading,
    isConnected,
    getValidatedAt,
    saveCredentials,
    isSaving,
    testConnection,
    isTesting,
    clearCredentials,
    isClearing,
  } = useAlpacaCredentials();

  const [apiKey, setApiKey] = useState('');
  const [secretKey, setSecretKey] = useState('');
  const [showSecret, setShowSecret] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
    account?: { portfolio_value: number; cash: number; buying_power: number };
  } | null>(null);

  const connected = isConnected(tradingMode);
  const validatedAt = getValidatedAt(tradingMode);

  const handleTestConnection = async () => {
    if (!apiKey || !secretKey) {
      setTestResult({ success: false, message: 'Please enter both API key and secret key' });
      return;
    }

    setTestResult(null);

    const result = await testConnection({ tradingMode, apiKey, secretKey });

    if (result.success) {
      setTestResult({
        success: true,
        message: 'Connection successful!',
        account: result.account,
      });
    } else {
      setTestResult({
        success: false,
        message: result.error || 'Connection failed',
      });
    }
  };

  const handleSaveCredentials = async () => {
    if (!apiKey || !secretKey) {
      setTestResult({ success: false, message: 'Please enter both API key and secret key' });
      return;
    }

    // Test connection first
    const result = await testConnection({ tradingMode, apiKey, secretKey });

    if (!result.success) {
      setTestResult({
        success: false,
        message: result.error || 'Connection failed - credentials not saved',
      });
      return;
    }

    // Save if connection succeeded
    await saveCredentials({ tradingMode, apiKey, secretKey });
    setApiKey('');
    setSecretKey('');
    setTestResult(null);
    onConnectionChange?.(true);
  };

  const handleDisconnect = async () => {
    await clearCredentials(tradingMode);
    setTestResult(null);
    onConnectionChange?.(false);
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6 flex items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              Alpaca Connection
              <Badge variant={tradingMode === 'paper' ? 'secondary' : 'destructive'}>
                {tradingMode === 'paper' ? 'Paper' : 'Live'}
              </Badge>
            </CardTitle>
            <CardDescription>
              {tradingMode === 'paper'
                ? 'Connect your paper trading account to practice without risk'
                : 'Connect your live trading account (uses real money)'}
            </CardDescription>
          </div>
          {connected && (
            <Badge variant="outline" className="text-green-600 border-green-600">
              <CheckCircle2 className="h-3 w-3 mr-1" />
              Connected
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {connected ? (
          // Connected state
          <div className="space-y-4">
            <div className="p-4 bg-green-50 dark:bg-green-950 rounded-lg border border-green-200 dark:border-green-800">
              <div className="flex items-center gap-2 text-green-700 dark:text-green-300">
                <CheckCircle2 className="h-5 w-5" />
                <span className="font-medium">Account Connected</span>
              </div>
              {validatedAt && (
                <p className="text-sm text-green-600 dark:text-green-400 mt-1">
                  Last validated {formatDistanceToNow(new Date(validatedAt), { addSuffix: true })}
                </p>
              )}
            </div>

            <Button
              variant="outline"
              className="w-full text-destructive hover:text-destructive"
              onClick={handleDisconnect}
              disabled={isClearing}
            >
              {isClearing ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4 mr-2" />
              )}
              Disconnect Account
            </Button>
          </div>
        ) : (
          // Not connected state
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="api-key">API Key</Label>
              <Input
                id="api-key"
                type="text"
                placeholder={tradingMode === 'paper' ? 'PK...' : 'AK...'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="secret-key">Secret Key</Label>
              <div className="relative">
                <Input
                  id="secret-key"
                  type={showSecret ? 'text' : 'password'}
                  placeholder="Your secret key"
                  value={secretKey}
                  onChange={(e) => setSecretKey(e.target.value)}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                  onClick={() => setShowSecret(!showSecret)}
                >
                  {showSecret ? (
                    <EyeOff className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <Eye className="h-4 w-4 text-muted-foreground" />
                  )}
                </Button>
              </div>
            </div>

            {/* Test Result */}
            {testResult && (
              <Alert variant={testResult.success ? 'default' : 'destructive'}>
                <div className="flex items-start gap-2">
                  {testResult.success ? (
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                  ) : (
                    <XCircle className="h-4 w-4" />
                  )}
                  <div>
                    <AlertDescription>{testResult.message}</AlertDescription>
                    {testResult.account && (
                      <div className="mt-2 text-sm">
                        <p>Portfolio Value: ${testResult.account.portfolio_value.toLocaleString()}</p>
                        <p>Buying Power: ${testResult.account.buying_power.toLocaleString()}</p>
                      </div>
                    )}
                  </div>
                </div>
              </Alert>
            )}

            {/* Actions */}
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={handleTestConnection}
                disabled={isTesting || !apiKey || !secretKey}
                className="flex-1"
              >
                {isTesting ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : null}
                Test Connection
              </Button>
              <Button
                onClick={handleSaveCredentials}
                disabled={isSaving || isTesting || !apiKey || !secretKey}
                className="flex-1"
              >
                {isSaving ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : null}
                Connect & Save
              </Button>
            </div>

            {/* Help Link */}
            <a
              href="https://alpaca.markets/docs/trading/getting_started/"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-primary transition-colors"
            >
              <ExternalLink className="h-3 w-3" />
              Get your Alpaca API keys
            </a>
          </div>
        )}

        {/* Live Trading Warning */}
        {tradingMode === 'live' && !connected && (
          <Alert variant="destructive">
            <AlertDescription>
              Live trading uses real money. Only use live trading if you fully understand the risks
              and have tested your strategy with paper trading first.
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
