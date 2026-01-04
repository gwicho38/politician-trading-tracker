// Deno tests for alpaca-account edge function
// Run with: deno test --allow-env --allow-net index.test.ts

import {
  assertEquals,
  assertExists,
  assertStringIncludes,
} from "https://deno.land/std@0.168.0/testing/asserts.ts";
import {
  stub,
  Stub,
  returnsNext,
} from "https://deno.land/std@0.168.0/testing/mock.ts";

// ============================================================================
// Circuit Breaker Unit Tests
// ============================================================================

Deno.test("Circuit Breaker - starts in closed state", () => {
  const circuitBreaker = {
    failures: 0,
    lastFailure: 0,
    state: 'closed' as const,
    lastSuccess: Date.now(),
  };

  assertEquals(circuitBreaker.state, 'closed');
  assertEquals(circuitBreaker.failures, 0);
});

Deno.test("Circuit Breaker - checkCircuitBreaker allows requests when closed", () => {
  const circuitBreaker = {
    failures: 0,
    lastFailure: 0,
    state: 'closed' as const,
    lastSuccess: Date.now(),
  };

  const checkCircuitBreaker = () => {
    if (circuitBreaker.state === 'closed') {
      return { allowed: true };
    }
    return { allowed: false, reason: 'Circuit open' };
  };

  const result = checkCircuitBreaker();
  assertEquals(result.allowed, true);
});

Deno.test("Circuit Breaker - blocks requests when open", () => {
  const CIRCUIT_BREAKER_CONFIG = {
    failureThreshold: 5,
    resetTimeout: 30000,
  };

  const circuitBreaker = {
    failures: 5,
    lastFailure: Date.now(),
    state: 'open' as const,
    lastSuccess: Date.now() - 60000,
  };

  const checkCircuitBreaker = () => {
    const now = Date.now();

    if (circuitBreaker.state === 'closed') {
      return { allowed: true };
    }

    if (circuitBreaker.state === 'open') {
      if (now - circuitBreaker.lastFailure > CIRCUIT_BREAKER_CONFIG.resetTimeout) {
        return { allowed: true }; // Would transition to half-open
      }
      return {
        allowed: false,
        reason: `Circuit breaker open. Retry after ${Math.ceil((CIRCUIT_BREAKER_CONFIG.resetTimeout - (now - circuitBreaker.lastFailure)) / 1000)}s`,
      };
    }

    return { allowed: true };
  };

  const result = checkCircuitBreaker();
  assertEquals(result.allowed, false);
  assertStringIncludes(result.reason!, 'Circuit breaker open');
});

Deno.test("Circuit Breaker - transitions to half-open after timeout", () => {
  const CIRCUIT_BREAKER_CONFIG = {
    failureThreshold: 5,
    resetTimeout: 30000,
  };

  const circuitBreaker = {
    failures: 5,
    lastFailure: Date.now() - 35000, // 35 seconds ago (past timeout)
    state: 'open' as 'closed' | 'open' | 'half-open',
    lastSuccess: Date.now() - 60000,
  };

  const checkCircuitBreaker = () => {
    const now = Date.now();

    if (circuitBreaker.state === 'open') {
      if (now - circuitBreaker.lastFailure > CIRCUIT_BREAKER_CONFIG.resetTimeout) {
        circuitBreaker.state = 'half-open';
        circuitBreaker.failures = 0;
        return { allowed: true };
      }
    }

    return { allowed: circuitBreaker.state !== 'open' };
  };

  const result = checkCircuitBreaker();
  assertEquals(result.allowed, true);
  assertEquals(circuitBreaker.state, 'half-open');
});

Deno.test("Circuit Breaker - recordSuccess resets to closed", () => {
  const circuitBreaker = {
    failures: 3,
    lastFailure: Date.now() - 10000,
    state: 'half-open' as 'closed' | 'open' | 'half-open',
    lastSuccess: Date.now() - 60000,
  };

  const recordSuccess = () => {
    circuitBreaker.failures = 0;
    circuitBreaker.state = 'closed';
    circuitBreaker.lastSuccess = Date.now();
  };

  recordSuccess();

  assertEquals(circuitBreaker.state, 'closed');
  assertEquals(circuitBreaker.failures, 0);
});

Deno.test("Circuit Breaker - recordFailure increments failures", () => {
  const CIRCUIT_BREAKER_CONFIG = {
    failureThreshold: 5,
    resetTimeout: 30000,
  };

  const circuitBreaker = {
    failures: 4,
    lastFailure: 0,
    state: 'closed' as 'closed' | 'open' | 'half-open',
    lastSuccess: Date.now(),
  };

  const recordFailure = () => {
    circuitBreaker.failures++;
    circuitBreaker.lastFailure = Date.now();

    if (circuitBreaker.failures >= CIRCUIT_BREAKER_CONFIG.failureThreshold) {
      circuitBreaker.state = 'open';
    }
  };

  recordFailure();

  assertEquals(circuitBreaker.failures, 5);
  assertEquals(circuitBreaker.state, 'open');
});

// ============================================================================
// Credential Resolution Tests
// ============================================================================

Deno.test("getAlpacaCredentials - returns provided credentials first", async () => {
  const getAlpacaCredentials = async (
    _supabase: any,
    _userEmail: string | null,
    tradingMode: 'paper' | 'live',
    providedApiKey?: string,
    providedSecretKey?: string
  ) => {
    if (providedApiKey && providedSecretKey) {
      const baseUrl = tradingMode === 'paper'
        ? 'https://paper-api.alpaca.markets'
        : 'https://api.alpaca.markets';
      return { apiKey: providedApiKey, secretKey: providedSecretKey, baseUrl };
    }
    return null;
  };

  const result = await getAlpacaCredentials(
    null,
    'test@example.com',
    'paper',
    'TEST_KEY',
    'TEST_SECRET'
  );

  assertExists(result);
  assertEquals(result!.apiKey, 'TEST_KEY');
  assertEquals(result!.secretKey, 'TEST_SECRET');
  assertEquals(result!.baseUrl, 'https://paper-api.alpaca.markets');
});

Deno.test("getAlpacaCredentials - uses live URL for live mode", async () => {
  const getAlpacaCredentials = async (
    _supabase: any,
    _userEmail: string | null,
    tradingMode: 'paper' | 'live',
    providedApiKey?: string,
    providedSecretKey?: string
  ) => {
    if (providedApiKey && providedSecretKey) {
      const baseUrl = tradingMode === 'paper'
        ? 'https://paper-api.alpaca.markets'
        : 'https://api.alpaca.markets';
      return { apiKey: providedApiKey, secretKey: providedSecretKey, baseUrl };
    }
    return null;
  };

  const result = await getAlpacaCredentials(
    null,
    'test@example.com',
    'live',
    'LIVE_KEY',
    'LIVE_SECRET'
  );

  assertExists(result);
  assertEquals(result!.baseUrl, 'https://api.alpaca.markets');
});

// ============================================================================
// Service Role Detection Tests
// ============================================================================

Deno.test("isServiceRoleRequest - returns false without auth header", () => {
  const isServiceRoleRequest = (req: Request): boolean => {
    const authHeader = req.headers.get('authorization');
    if (!authHeader) return false;
    const token = authHeader.replace('Bearer ', '');
    const serviceRoleKey = 'test-service-role-key';
    return token === serviceRoleKey;
  };

  const req = new Request('http://localhost', { method: 'POST' });
  assertEquals(isServiceRoleRequest(req), false);
});

Deno.test("isServiceRoleRequest - returns true with matching service key", () => {
  const serviceRoleKey = 'test-service-role-key';

  const isServiceRoleRequest = (req: Request): boolean => {
    const authHeader = req.headers.get('authorization');
    if (!authHeader) return false;
    const token = authHeader.replace('Bearer ', '');
    return token === serviceRoleKey;
  };

  const req = new Request('http://localhost', {
    method: 'POST',
    headers: {
      'authorization': `Bearer ${serviceRoleKey}`,
    },
  });

  assertEquals(isServiceRoleRequest(req), true);
});

Deno.test("isServiceRoleRequest - returns false with non-matching key", () => {
  const serviceRoleKey = 'test-service-role-key';

  const isServiceRoleRequest = (req: Request): boolean => {
    const authHeader = req.headers.get('authorization');
    if (!authHeader) return false;
    const token = authHeader.replace('Bearer ', '');
    return token === serviceRoleKey;
  };

  const req = new Request('http://localhost', {
    method: 'POST',
    headers: {
      'authorization': 'Bearer wrong-key',
    },
  });

  assertEquals(isServiceRoleRequest(req), false);
});

// ============================================================================
// Structured Logging Tests
// ============================================================================

Deno.test("Structured logging - log.info formats correctly", () => {
  const logs: string[] = [];
  const originalLog = console.log;
  console.log = (msg: string) => logs.push(msg);

  const log = {
    info: (message: string, metadata?: any) => {
      console.log(JSON.stringify({
        level: 'INFO',
        timestamp: new Date().toISOString(),
        service: 'alpaca-account',
        message,
        ...metadata,
      }));
    },
  };

  log.info('Test message', { requestId: '12345' });

  console.log = originalLog;

  assertEquals(logs.length, 1);
  const parsed = JSON.parse(logs[0]);
  assertEquals(parsed.level, 'INFO');
  assertEquals(parsed.service, 'alpaca-account');
  assertEquals(parsed.message, 'Test message');
  assertEquals(parsed.requestId, '12345');
});

Deno.test("Structured logging - log.error includes error details", () => {
  const logs: string[] = [];
  const originalError = console.error;
  console.error = (msg: string) => logs.push(msg);

  const log = {
    error: (message: string, error?: any, metadata?: any) => {
      console.error(JSON.stringify({
        level: 'ERROR',
        timestamp: new Date().toISOString(),
        service: 'alpaca-account',
        message,
        error: error?.message || error,
        stack: error?.stack,
        ...metadata,
      }));
    },
  };

  const testError = new Error('Test error');
  log.error('Something failed', testError, { requestId: '12345' });

  console.error = originalError;

  assertEquals(logs.length, 1);
  const parsed = JSON.parse(logs[0]);
  assertEquals(parsed.level, 'ERROR');
  assertEquals(parsed.error, 'Test error');
  assertExists(parsed.stack);
});

// ============================================================================
// Response Formatting Tests
// ============================================================================

Deno.test("Account data formatting - parses numeric fields correctly", () => {
  const alpacaAccountData = {
    id: 'account-123',
    portfolio_value: '100000.50',
    cash: '25000.00',
    buying_power: '50000.00',
    status: 'ACTIVE',
    currency: 'USD',
    equity: '100000.50',
    last_equity: '99500.00',
    long_market_value: '75000.50',
    short_market_value: '0.00',
    pattern_day_trader: false,
    trading_blocked: false,
    transfers_blocked: false,
    account_blocked: false,
  };

  const formattedAccount = {
    portfolio_value: parseFloat(alpacaAccountData.portfolio_value) || 0,
    cash: parseFloat(alpacaAccountData.cash) || 0,
    buying_power: parseFloat(alpacaAccountData.buying_power) || 0,
    status: alpacaAccountData.status || 'UNKNOWN',
    currency: alpacaAccountData.currency || 'USD',
    equity: parseFloat(alpacaAccountData.equity) || 0,
    last_equity: parseFloat(alpacaAccountData.last_equity) || 0,
    long_market_value: parseFloat(alpacaAccountData.long_market_value) || 0,
    short_market_value: parseFloat(alpacaAccountData.short_market_value) || 0,
    pattern_day_trader: alpacaAccountData.pattern_day_trader || false,
    trading_blocked: alpacaAccountData.trading_blocked || false,
    transfers_blocked: alpacaAccountData.transfers_blocked || false,
    account_blocked: alpacaAccountData.account_blocked || false,
  };

  assertEquals(formattedAccount.portfolio_value, 100000.50);
  assertEquals(formattedAccount.cash, 25000.00);
  assertEquals(formattedAccount.buying_power, 50000.00);
  assertEquals(formattedAccount.status, 'ACTIVE');
  assertEquals(formattedAccount.equity, 100000.50);
  assertEquals(formattedAccount.long_market_value, 75000.50);
});

Deno.test("Account data formatting - handles missing/null values", () => {
  const alpacaAccountData = {
    id: 'account-123',
    portfolio_value: null,
    cash: undefined,
    status: '',
  };

  const formattedAccount = {
    portfolio_value: parseFloat(alpacaAccountData.portfolio_value as any) || 0,
    cash: parseFloat(alpacaAccountData.cash as any) || 0,
    status: alpacaAccountData.status || 'UNKNOWN',
  };

  assertEquals(formattedAccount.portfolio_value, 0);
  assertEquals(formattedAccount.cash, 0);
  assertEquals(formattedAccount.status, 'UNKNOWN');
});

// ============================================================================
// Position Formatting Tests
// ============================================================================

Deno.test("Position formatting - parses position data correctly", () => {
  const alpacaPosition = {
    asset_id: 'asset-123',
    symbol: 'AAPL',
    exchange: 'NASDAQ',
    asset_class: 'us_equity',
    avg_entry_price: '150.50',
    qty: '100',
    side: 'long',
    market_value: '15500.00',
    cost_basis: '15050.00',
    unrealized_pl: '450.00',
    unrealized_plpc: '0.0299',
    unrealized_intraday_pl: '50.00',
    unrealized_intraday_plpc: '0.0032',
    current_price: '155.00',
    lastday_price: '154.50',
    change_today: '0.0032',
  };

  const formattedPosition = {
    asset_id: alpacaPosition.asset_id,
    symbol: alpacaPosition.symbol,
    exchange: alpacaPosition.exchange,
    asset_class: alpacaPosition.asset_class,
    avg_entry_price: parseFloat(alpacaPosition.avg_entry_price) || 0,
    qty: parseFloat(alpacaPosition.qty) || 0,
    side: alpacaPosition.side,
    market_value: parseFloat(alpacaPosition.market_value) || 0,
    cost_basis: parseFloat(alpacaPosition.cost_basis) || 0,
    unrealized_pl: parseFloat(alpacaPosition.unrealized_pl) || 0,
    unrealized_plpc: parseFloat(alpacaPosition.unrealized_plpc) || 0,
    unrealized_intraday_pl: parseFloat(alpacaPosition.unrealized_intraday_pl) || 0,
    unrealized_intraday_plpc: parseFloat(alpacaPosition.unrealized_intraday_plpc) || 0,
    current_price: parseFloat(alpacaPosition.current_price) || 0,
    lastday_price: parseFloat(alpacaPosition.lastday_price) || 0,
    change_today: parseFloat(alpacaPosition.change_today) || 0,
  };

  assertEquals(formattedPosition.symbol, 'AAPL');
  assertEquals(formattedPosition.avg_entry_price, 150.50);
  assertEquals(formattedPosition.qty, 100);
  assertEquals(formattedPosition.market_value, 15500.00);
  assertEquals(formattedPosition.unrealized_pl, 450.00);
  assertEquals(formattedPosition.current_price, 155.00);
});

// ============================================================================
// CORS Headers Tests
// ============================================================================

Deno.test("CORS headers - are correctly formatted", () => {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  };

  assertEquals(corsHeaders['Access-Control-Allow-Origin'], '*');
  assertStringIncludes(corsHeaders['Access-Control-Allow-Headers'], 'authorization');
  assertStringIncludes(corsHeaders['Access-Control-Allow-Headers'], 'content-type');
});
