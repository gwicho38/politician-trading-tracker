import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, CheckCircle2, XCircle, Eye, EyeOff, ExternalLink, Trash2, HelpCircle, ChevronDown, ChevronUp } from 'lucide-react';
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
  const [showGuide, setShowGuide] = useState(false);
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

            {/* Setup Guide */}
            <div className="border rounded-lg overflow-hidden">
              <button
                onClick={() => setShowGuide(!showGuide)}
                className="w-full flex items-center justify-between p-3 text-sm text-left hover:bg-muted/50 transition-colors"
              >
                <span className="flex items-center gap-2 font-medium">
                  <HelpCircle className="h-4 w-4 text-primary" />
                  How to get your Alpaca API keys
                </span>
                {showGuide ? (
                  <ChevronUp className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                )}
              </button>

              {showGuide && (
                <div className="p-4 pt-0 space-y-4 text-sm">
                  <div className="space-y-3">
                    <div className="flex gap-3">
                      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/20 text-primary text-xs font-bold flex items-center justify-center">
                        1
                      </div>
                      <div>
                        <p className="font-medium">Create a free Alpaca account</p>
                        <p className="text-muted-foreground mt-0.5">
                          Go to{' '}
                          <a
                            href="https://app.alpaca.markets/signup"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline inline-flex items-center gap-1"
                          >
                            alpaca.markets/signup <ExternalLink className="h-3 w-3" />
                          </a>
                        </p>
                      </div>
                    </div>

                    <div className="flex gap-3">
                      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/20 text-primary text-xs font-bold flex items-center justify-center">
                        2
                      </div>
                      <div>
                        <p className="font-medium">Go to API Keys page</p>
                        <p className="text-muted-foreground mt-0.5">
                          After signing in, click the menu icon (☰) and select{' '}
                          <span className="font-medium text-foreground">"API Keys"</span>
                        </p>
                      </div>
                    </div>

                    <div className="flex gap-3">
                      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/20 text-primary text-xs font-bold flex items-center justify-center">
                        3
                      </div>
                      <div>
                        <p className="font-medium">Generate new keys</p>
                        <p className="text-muted-foreground mt-0.5">
                          Click <span className="font-medium text-foreground">"Generate New Key"</span>.
                          {tradingMode === 'paper' ? (
                            <> Make sure you're in <Badge variant="secondary" className="mx-1 text-xs">Paper Trading</Badge> mode.</>
                          ) : (
                            <> Make sure you're in <Badge variant="destructive" className="mx-1 text-xs">Live Trading</Badge> mode.</>
                          )}
                        </p>
                      </div>
                    </div>

                    <div className="flex gap-3">
                      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/20 text-primary text-xs font-bold flex items-center justify-center">
                        4
                      </div>
                      <div>
                        <p className="font-medium">Copy both keys</p>
                        <p className="text-muted-foreground mt-0.5">
                          Copy the <span className="font-medium text-foreground">API Key</span> (starts with PK or AK)
                          and <span className="font-medium text-foreground">Secret Key</span> (only shown once!)
                        </p>
                      </div>
                    </div>

                    <div className="flex gap-3">
                      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/20 text-primary text-xs font-bold flex items-center justify-center">
                        5
                      </div>
                      <div>
                        <p className="font-medium">Paste keys above</p>
                        <p className="text-muted-foreground mt-0.5">
                          Enter both keys in the fields above and click{' '}
                          <span className="font-medium text-foreground">"Connect & Save"</span>
                        </p>
                      </div>
                    </div>
                  </div>

                  <Alert>
                    <HelpCircle className="h-4 w-4" />
                    <AlertDescription>
                      <span className="font-medium">Tip:</span> Start with Paper Trading to practice without risking real money.
                      Your paper account comes with $100,000 in virtual funds!
                    </AlertDescription>
                  </Alert>
                </div>
              )}
            </div>
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
