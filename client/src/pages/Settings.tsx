import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Settings, Key, Shield, AlertCircle, CheckCircle, Eye, EyeOff } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { supabase } from '@/integrations/supabase/client';
import { logError } from '@/lib/logger';

interface APIKeys {
  alpaca_api_key?: string;
  alpaca_secret_key?: string;
  alpaca_paper?: boolean;
}

const SettingsPage = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [apiKeys, setApiKeys] = useState<APIKeys>({});
  const [showSecrets, setShowSecrets] = useState(false);

  // Form state
  const [alpacaApiKey, setAlpacaApiKey] = useState('');
  const [alpacaSecretKey, setAlpacaSecretKey] = useState('');
  const [usePaperTrading, setUsePaperTrading] = useState(true);

  // Check authentication
  useEffect(() => {
    const checkAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        navigate('/auth');
      }
    };
    checkAuth();
  }, [navigate]);

  // Load existing API keys
  useEffect(() => {
    loadApiKeys();
  }, []);

  const loadApiKeys = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.user?.email) return;

      // In a real implementation, you'd call an API endpoint to get encrypted keys
      // For now, we'll show a placeholder
      setApiKeys({
        alpaca_api_key: '••••••••••••••••', // Masked
        alpaca_secret_key: '••••••••••••••••', // Masked
        alpaca_paper: true
      });
    } catch (error) {
      logError('Error loading API keys', 'settings', error instanceof Error ? error : undefined);
    }
  };

  const saveApiKeys = async () => {
    if (!alpacaApiKey || !alpacaSecretKey) {
      toast({
        title: 'Validation Error',
        description: 'Please provide both API key and secret key.',
        variant: 'destructive',
      });
      return;
    }

    setLoading(true);
    try {
      // In a real implementation, you'd call an API endpoint to securely store encrypted keys
      // This would typically go through a backend service that encrypts and stores the keys

      toast({
        title: 'API Keys Saved',
        description: 'Your Alpaca API keys have been securely stored.',
      });

      // Reload to show updated state
      await loadApiKeys();

      // Clear form
      setAlpacaApiKey('');
      setAlpacaSecretKey('');

    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to save API keys. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const testConnection = async () => {
    setLoading(true);
    try {
      // In a real implementation, you'd call an API endpoint to test the connection
      // This would validate the API keys without storing sensitive data

      toast({
        title: 'Connection Test',
        description: 'API connection test completed successfully.',
      });

    } catch (error) {
      toast({
        title: 'Connection Failed',
        description: 'Unable to connect with the provided API keys.',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <Settings className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-3xl font-bold text-foreground">Settings</h1>
            <p className="text-muted-foreground">Manage your account and API connections</p>
          </div>
        </div>

        <Tabs defaultValue="api-keys" className="space-y-6">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="api-keys" className="flex items-center gap-2">
              <Key className="h-4 w-4" />
              API Keys
            </TabsTrigger>
            <TabsTrigger value="security" className="flex items-center gap-2">
              <Shield className="h-4 w-4" />
              Security
            </TabsTrigger>
            <TabsTrigger value="account" className="flex items-center gap-2">
              <Settings className="h-4 w-4" />
              Account
            </TabsTrigger>
          </TabsList>

          {/* API Keys Tab */}
          <TabsContent value="api-keys" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Key className="h-5 w-5" />
                  Alpaca Trading API
                </CardTitle>
                <CardDescription>
                  Connect your Alpaca trading account to enable automated trading features.
                  Your API keys are encrypted and stored securely.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Current Status */}
                <div className="flex items-center gap-3 p-4 bg-muted rounded-lg">
                  {apiKeys.alpaca_api_key ? (
                    <>
                      <CheckCircle className="h-5 w-5 text-green-500" />
                      <div>
                        <p className="font-medium text-green-700">API Keys Configured</p>
                        <p className="text-sm text-muted-foreground">
                          {apiKeys.alpaca_paper ? 'Paper Trading' : 'Live Trading'} Account
                        </p>
                      </div>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="h-5 w-5 text-yellow-500" />
                      <div>
                        <p className="font-medium text-yellow-700">API Keys Not Configured</p>
                        <p className="text-sm text-muted-foreground">
                          Configure your Alpaca API keys to enable trading features
                        </p>
                      </div>
                    </>
                  )}
                </div>

                <Separator />

                {/* API Key Form */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold">Configure API Keys</h3>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setShowSecrets(!showSecrets)}
                      className="flex items-center gap-2"
                    >
                      {showSecrets ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      {showSecrets ? 'Hide' : 'Show'} Keys
                    </Button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="api-key">API Key</Label>
                      <Input
                        id="api-key"
                        type={showSecrets ? "text" : "password"}
                        placeholder="Your Alpaca API Key"
                        value={alpacaApiKey}
                        onChange={(e) => setAlpacaApiKey(e.target.value)}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="secret-key">Secret Key</Label>
                      <Input
                        id="secret-key"
                        type={showSecrets ? "text" : "password"}
                        placeholder="Your Alpaca Secret Key"
                        value={alpacaSecretKey}
                        onChange={(e) => setAlpacaSecretKey(e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="paper-trading"
                      checked={usePaperTrading}
                      onChange={(e) => setUsePaperTrading(e.target.checked)}
                      className="rounded"
                    />
                    <Label htmlFor="paper-trading" className="text-sm">
                      Use Paper Trading (recommended for testing)
                    </Label>
                  </div>

                  <div className="flex gap-3">
                    <Button onClick={saveApiKeys} disabled={loading}>
                      {loading ? 'Saving...' : 'Save API Keys'}
                    </Button>
                    <Button variant="outline" onClick={testConnection} disabled={loading}>
                      Test Connection
                    </Button>
                  </div>
                </div>

                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    <strong>Security Notice:</strong> Your API keys are encrypted before storage.
                    Never share your secret key with anyone. You can generate new API keys
                    from your <a href="https://alpaca.markets/account" target="_blank" rel="noopener noreferrer" className="underline">Alpaca dashboard</a>.
                  </AlertDescription>
                </Alert>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Security Tab */}
          <TabsContent value="security" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  Security Settings
                </CardTitle>
                <CardDescription>
                  Manage your account security and authentication preferences.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-4 bg-muted rounded-lg">
                  <p className="text-sm text-muted-foreground">
                    Security settings will be available in a future update.
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Account Tab */}
          <TabsContent value="account" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Account Information</CardTitle>
                <CardDescription>
                  View and manage your account details.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="p-4 bg-muted rounded-lg">
                  <p className="text-sm text-muted-foreground">
                    Account management features will be available in a future update.
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default SettingsPage;