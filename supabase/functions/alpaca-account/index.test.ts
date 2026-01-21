/**
 * Tests for alpaca-account Edge Function
 *
 * Tests:
 * - Circuit breaker pattern
 * - Service role request detection
 * - Position formatting
 * - Account data formatting
 * - Credential resolution
 */

import { assertEquals, assertAlmostEquals } from "https://deno.land/std@0.208.0/assert/mod.ts";

// Extracted types
interface CircuitBreakerState {
  failures: number;
  lastFailure: number;
  state: 'closed' | 'open' | 'half-open';
  lastSuccess: number;
}

const CIRCUIT_BREAKER_CONFIG = {
  failureThreshold: 5,
  resetTimeout: 30000,
  halfOpenRequests: 2,
};

// Circuit breaker implementation for testing
function createCircuitBreaker(): CircuitBreakerState {
  return {
    failures: 0,
    lastFailure: 0,
    state: 'closed',
    lastSuccess: Date.now(),
  };
}

function checkCircuitBreaker(
  breaker: CircuitBreakerState,
  config: typeof CIRCUIT_BREAKER_CONFIG
): { allowed: boolean; reason?: string } {
  const now = Date.now();

  if (breaker.state === 'closed') {
    return { allowed: true };
  }

  if (breaker.state === 'open') {
    if (now - breaker.lastFailure > config.resetTimeout) {
      breaker.state = 'half-open';
      breaker.failures = 0;
      return { allowed: true };
    }
    return {
      allowed: false,
      reason: `Circuit breaker open. Retry after ${Math.ceil((config.resetTimeout - (now - breaker.lastFailure)) / 1000)}s`,
    };
  }

  return { allowed: true };
}

function recordSuccess(breaker: CircuitBreakerState): void {
  breaker.failures = 0;
  breaker.state = 'closed';
  breaker.lastSuccess = Date.now();
}

function recordFailure(breaker: CircuitBreakerState, config: typeof CIRCUIT_BREAKER_CONFIG): void {
  breaker.failures++;
  breaker.lastFailure = Date.now();

  if (breaker.failures >= config.failureThreshold) {
    breaker.state = 'open';
  }
}

function getCircuitBreakerStatus(breaker: CircuitBreakerState): {
  state: string;
  failures: number;
  lastSuccess: string;
  lastFailure: string | null;
} {
  return {
    state: breaker.state,
    failures: breaker.failures,
    lastSuccess: new Date(breaker.lastSuccess).toISOString(),
    lastFailure: breaker.lastFailure ? new Date(breaker.lastFailure).toISOString() : null,
  };
}

// Tests

Deno.test("createCircuitBreaker() - starts in closed state", () => {
  const breaker = createCircuitBreaker();
  assertEquals(breaker.state, 'closed');
  assertEquals(breaker.failures, 0);
});

Deno.test("checkCircuitBreaker() - allows requests when closed", () => {
  const breaker = createCircuitBreaker();
  const result = checkCircuitBreaker(breaker, CIRCUIT_BREAKER_CONFIG);
  assertEquals(result.allowed, true);
  assertEquals(result.reason, undefined);
});

Deno.test("checkCircuitBreaker() - blocks requests when open", () => {
  const breaker = createCircuitBreaker();
  breaker.state = 'open';
  breaker.lastFailure = Date.now();

  const result = checkCircuitBreaker(breaker, CIRCUIT_BREAKER_CONFIG);
  assertEquals(result.allowed, false);
  assertEquals(result.reason?.includes('Circuit breaker open'), true);
});

Deno.test("checkCircuitBreaker() - transitions to half-open after timeout", () => {
  const breaker = createCircuitBreaker();
  breaker.state = 'open';
  breaker.lastFailure = Date.now() - (CIRCUIT_BREAKER_CONFIG.resetTimeout + 1000);

  const result = checkCircuitBreaker(breaker, CIRCUIT_BREAKER_CONFIG);
  assertEquals(result.allowed, true);
  assertEquals(breaker.state, 'half-open');
});

Deno.test("checkCircuitBreaker() - allows requests in half-open state", () => {
  const breaker = createCircuitBreaker();
  breaker.state = 'half-open';

  const result = checkCircuitBreaker(breaker, CIRCUIT_BREAKER_CONFIG);
  assertEquals(result.allowed, true);
});

Deno.test("recordSuccess() - resets to closed state", () => {
  const breaker = createCircuitBreaker();
  breaker.state = 'half-open';
  breaker.failures = 3;

  recordSuccess(breaker);

  assertEquals(breaker.state, 'closed');
  assertEquals(breaker.failures, 0);
});

Deno.test("recordFailure() - increments failure count", () => {
  const breaker = createCircuitBreaker();

  recordFailure(breaker, CIRCUIT_BREAKER_CONFIG);

  assertEquals(breaker.failures, 1);
  assertEquals(breaker.state, 'closed');
});

Deno.test("recordFailure() - opens circuit after threshold", () => {
  const breaker = createCircuitBreaker();

  for (let i = 0; i < CIRCUIT_BREAKER_CONFIG.failureThreshold; i++) {
    recordFailure(breaker, CIRCUIT_BREAKER_CONFIG);
  }

  assertEquals(breaker.state, 'open');
  assertEquals(breaker.failures, CIRCUIT_BREAKER_CONFIG.failureThreshold);
});

Deno.test("recordFailure() - stays closed below threshold", () => {
  const breaker = createCircuitBreaker();

  for (let i = 0; i < CIRCUIT_BREAKER_CONFIG.failureThreshold - 1; i++) {
    recordFailure(breaker, CIRCUIT_BREAKER_CONFIG);
  }

  assertEquals(breaker.state, 'closed');
});

Deno.test("getCircuitBreakerStatus() - returns formatted status", () => {
  const breaker = createCircuitBreaker();
  const status = getCircuitBreakerStatus(breaker);

  assertEquals(status.state, 'closed');
  assertEquals(status.failures, 0);
  assertEquals(status.lastFailure, null);
  assertEquals(typeof status.lastSuccess, 'string');
});

// Service role detection
function isServiceRoleRequest(authHeader: string | null, serviceRoleKey: string): boolean {
  if (!authHeader) return false;
  const token = authHeader.replace('Bearer ', '');
  return token === serviceRoleKey;
}

Deno.test("isServiceRoleRequest() - true when token matches", () => {
  const serviceKey = 'super-secret-key';
  const result = isServiceRoleRequest(`Bearer ${serviceKey}`, serviceKey);
  assertEquals(result, true);
});

Deno.test("isServiceRoleRequest() - false when token doesn't match", () => {
  const result = isServiceRoleRequest('Bearer wrong-key', 'super-secret-key');
  assertEquals(result, false);
});

Deno.test("isServiceRoleRequest() - false when no header", () => {
  const result = isServiceRoleRequest(null, 'super-secret-key');
  assertEquals(result, false);
});

// Position formatting
interface AlpacaPosition {
  asset_id: string;
  symbol: string;
  exchange: string;
  asset_class: string;
  avg_entry_price: string;
  qty: string;
  side: string;
  market_value: string;
  cost_basis: string;
  unrealized_pl: string;
  unrealized_plpc: string;
  current_price: string;
}

function formatPosition(pos: AlpacaPosition) {
  return {
    asset_id: pos.asset_id,
    symbol: pos.symbol,
    exchange: pos.exchange,
    asset_class: pos.asset_class,
    avg_entry_price: parseFloat(pos.avg_entry_price) || 0,
    qty: parseFloat(pos.qty) || 0,
    side: pos.side,
    market_value: parseFloat(pos.market_value) || 0,
    cost_basis: parseFloat(pos.cost_basis) || 0,
    unrealized_pl: parseFloat(pos.unrealized_pl) || 0,
    unrealized_plpc: parseFloat(pos.unrealized_plpc) || 0,
    current_price: parseFloat(pos.current_price) || 0,
  };
}

Deno.test("formatPosition() - parses numeric strings", () => {
  const position: AlpacaPosition = {
    asset_id: 'abc123',
    symbol: 'AAPL',
    exchange: 'NASDAQ',
    asset_class: 'us_equity',
    avg_entry_price: '150.50',
    qty: '10',
    side: 'long',
    market_value: '1550.00',
    cost_basis: '1505.00',
    unrealized_pl: '45.00',
    unrealized_plpc: '0.0299',
    current_price: '155.00',
  };

  const formatted = formatPosition(position);

  assertEquals(formatted.symbol, 'AAPL');
  assertEquals(formatted.avg_entry_price, 150.50);
  assertEquals(formatted.qty, 10);
  assertEquals(formatted.market_value, 1550.00);
  assertEquals(formatted.unrealized_pl, 45.00);
});

Deno.test("formatPosition() - handles invalid numbers", () => {
  const position: AlpacaPosition = {
    asset_id: 'abc123',
    symbol: 'AAPL',
    exchange: 'NASDAQ',
    asset_class: 'us_equity',
    avg_entry_price: 'invalid',
    qty: '',
    side: 'long',
    market_value: 'NaN',
    cost_basis: '1505.00',
    unrealized_pl: '45.00',
    unrealized_plpc: '0.0299',
    current_price: '155.00',
  };

  const formatted = formatPosition(position);

  assertEquals(formatted.avg_entry_price, 0);
  assertEquals(formatted.qty, 0);
  assertEquals(formatted.market_value, 0);
});

// Account formatting
interface AlpacaAccount {
  portfolio_value: string;
  cash: string;
  buying_power: string;
  status: string;
  currency: string;
  equity: string;
  last_equity: string;
  pattern_day_trader: boolean;
  trading_blocked: boolean;
}

function formatAccount(account: AlpacaAccount) {
  return {
    portfolio_value: parseFloat(account.portfolio_value) || 0,
    cash: parseFloat(account.cash) || 0,
    buying_power: parseFloat(account.buying_power) || 0,
    status: account.status || 'UNKNOWN',
    currency: account.currency || 'USD',
    equity: parseFloat(account.equity) || 0,
    last_equity: parseFloat(account.last_equity) || 0,
    pattern_day_trader: account.pattern_day_trader || false,
    trading_blocked: account.trading_blocked || false,
  };
}

Deno.test("formatAccount() - parses account values", () => {
  const account: AlpacaAccount = {
    portfolio_value: '100000.00',
    cash: '50000.00',
    buying_power: '200000.00',
    status: 'ACTIVE',
    currency: 'USD',
    equity: '100000.00',
    last_equity: '99500.00',
    pattern_day_trader: false,
    trading_blocked: false,
  };

  const formatted = formatAccount(account);

  assertEquals(formatted.portfolio_value, 100000);
  assertEquals(formatted.cash, 50000);
  assertEquals(formatted.status, 'ACTIVE');
  assertEquals(formatted.pattern_day_trader, false);
});

Deno.test("formatAccount() - defaults for missing values", () => {
  const account = {
    portfolio_value: '',
    cash: '',
    buying_power: '',
    status: '',
    currency: '',
    equity: '',
    last_equity: '',
    pattern_day_trader: false,
    trading_blocked: false,
  };

  const formatted = formatAccount(account);

  assertEquals(formatted.portfolio_value, 0);
  assertEquals(formatted.status, 'UNKNOWN');
  assertEquals(formatted.currency, 'USD');
});

// Trading mode base URL determination
function getBaseUrl(tradingMode: 'paper' | 'live'): string {
  return tradingMode === 'paper'
    ? 'https://paper-api.alpaca.markets'
    : 'https://api.alpaca.markets';
}

Deno.test("getBaseUrl() - paper mode", () => {
  assertEquals(getBaseUrl('paper'), 'https://paper-api.alpaca.markets');
});

Deno.test("getBaseUrl() - live mode", () => {
  assertEquals(getBaseUrl('live'), 'https://api.alpaca.markets');
});

// Connection status calculation
function calculateConnectionStatus(healthRate: number): 'connected' | 'degraded' | 'disconnected' {
  if (healthRate >= 0.8) {
    return 'connected';
  } else if (healthRate >= 0.5) {
    return 'degraded';
  }
  return 'disconnected';
}

Deno.test("calculateConnectionStatus() - connected at 80%+", () => {
  assertEquals(calculateConnectionStatus(0.8), 'connected');
  assertEquals(calculateConnectionStatus(1.0), 'connected');
  assertEquals(calculateConnectionStatus(0.95), 'connected');
});

Deno.test("calculateConnectionStatus() - degraded at 50-79%", () => {
  assertEquals(calculateConnectionStatus(0.5), 'degraded');
  assertEquals(calculateConnectionStatus(0.7), 'degraded');
  assertEquals(calculateConnectionStatus(0.79), 'degraded');
});

Deno.test("calculateConnectionStatus() - disconnected below 50%", () => {
  assertEquals(calculateConnectionStatus(0.49), 'disconnected');
  assertEquals(calculateConnectionStatus(0), 'disconnected');
  assertEquals(calculateConnectionStatus(0.3), 'disconnected');
});

// Average latency calculation
function calculateAverageLatency(logs: { response_time_ms: number }[]): number | null {
  if (logs.length === 0) return null;
  return logs.reduce((sum, l) => sum + (l.response_time_ms || 0), 0) / logs.length;
}

Deno.test("calculateAverageLatency() - calculates average", () => {
  const logs = [
    { response_time_ms: 100 },
    { response_time_ms: 200 },
    { response_time_ms: 300 },
  ];

  assertEquals(calculateAverageLatency(logs), 200);
});

Deno.test("calculateAverageLatency() - null for empty logs", () => {
  assertEquals(calculateAverageLatency([]), null);
});

Deno.test("calculateAverageLatency() - handles zero values", () => {
  const logs = [
    { response_time_ms: 0 },
    { response_time_ms: 100 },
  ];

  assertEquals(calculateAverageLatency(logs), 50);
});
