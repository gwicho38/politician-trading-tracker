/**
 * Tests for portfolio Edge Function
 *
 * Tests:
 * - Position drift detection
 * - Position synchronization logic
 * - Request sanitization
 * - Response formatting
 */

import { assertEquals, assertAlmostEquals } from "https://deno.land/std@0.208.0/assert/mod.ts";

// Position drift detection
interface PositionDrift {
  ticker: string;
  field: string;
  localValue: number;
  alpacaValue: number;
  difference: number;
}

function detectQuantityDrift(
  ticker: string,
  localQty: number,
  alpacaQty: number,
  threshold: number = 0.001
): PositionDrift | null {
  const diff = alpacaQty - localQty;
  if (Math.abs(diff) > threshold) {
    return {
      ticker,
      field: 'quantity',
      localValue: localQty,
      alpacaValue: alpacaQty,
      difference: diff,
    };
  }
  return null;
}

function detectPriceDrift(
  ticker: string,
  localPrice: number,
  alpacaPrice: number,
  threshold: number = 0.01
): PositionDrift | null {
  const diff = alpacaPrice - localPrice;
  if (Math.abs(diff) > threshold) {
    return {
      ticker,
      field: 'avg_entry_price',
      localValue: localPrice,
      alpacaValue: alpacaPrice,
      difference: diff,
    };
  }
  return null;
}

function detectMarketValueDrift(
  ticker: string,
  localValue: number,
  alpacaValue: number,
  threshold: number = 1
): PositionDrift | null {
  const diff = alpacaValue - localValue;
  if (Math.abs(diff) > threshold) {
    return {
      ticker,
      field: 'market_value',
      localValue: localValue,
      alpacaValue: alpacaValue,
      difference: diff,
    };
  }
  return null;
}

// Position record building
interface PositionRecord {
  user_id: string | null;
  ticker: string;
  quantity: number;
  avg_entry_price: number;
  market_value: number;
  cost_basis: number;
  unrealized_pl: number;
  unrealized_plpc: number;
  current_price: number;
  side: string;
  trading_mode: 'paper' | 'live';
  is_open: boolean;
  alpaca_asset_id: string;
  last_synced_at: string;
}

function buildPositionRecord(
  userId: string | null,
  alpacaPosition: {
    symbol: string;
    qty: string;
    avg_entry_price: string;
    market_value: string;
    cost_basis: string;
    unrealized_pl: string;
    unrealized_plpc: string;
    current_price: string;
    side: string;
    asset_id: string;
  },
  tradingMode: 'paper' | 'live'
): PositionRecord {
  return {
    user_id: userId,
    ticker: alpacaPosition.symbol,
    quantity: parseFloat(alpacaPosition.qty) || 0,
    avg_entry_price: parseFloat(alpacaPosition.avg_entry_price) || 0,
    market_value: parseFloat(alpacaPosition.market_value) || 0,
    cost_basis: parseFloat(alpacaPosition.cost_basis) || 0,
    unrealized_pl: parseFloat(alpacaPosition.unrealized_pl) || 0,
    unrealized_plpc: parseFloat(alpacaPosition.unrealized_plpc) || 0,
    current_price: parseFloat(alpacaPosition.current_price) || 0,
    side: alpacaPosition.side,
    trading_mode: tradingMode,
    is_open: true,
    alpaca_asset_id: alpacaPosition.asset_id,
    last_synced_at: new Date().toISOString(),
  };
}

// Health status determination
function determineHealthStatus(
  driftCount: number,
  missingLocalCount: number,
  missingAlpacaCount: number
): 'healthy' | 'degraded' {
  if (driftCount === 0 && missingLocalCount === 0 && missingAlpacaCount === 0) {
    return 'healthy';
  }
  return 'degraded';
}

// Response sanitization
function sanitizeResponseBody(body: unknown, maxLength: number = 500): string {
  const str = JSON.stringify(body);
  if (str.length > maxLength) {
    return str.substring(0, maxLength) + '...';
  }
  return str;
}

// Tests

Deno.test("detectQuantityDrift() - detects drift above threshold", () => {
  const result = detectQuantityDrift('AAPL', 10, 15, 0.001);

  assertEquals(result?.ticker, 'AAPL');
  assertEquals(result?.field, 'quantity');
  assertEquals(result?.localValue, 10);
  assertEquals(result?.alpacaValue, 15);
  assertEquals(result?.difference, 5);
});

Deno.test("detectQuantityDrift() - no drift within threshold", () => {
  const result = detectQuantityDrift('AAPL', 10, 10.0001, 0.001);

  assertEquals(result, null);
});

Deno.test("detectQuantityDrift() - negative drift", () => {
  const result = detectQuantityDrift('TSLA', 20, 15, 0.001);

  assertEquals(result?.difference, -5);
});

Deno.test("detectQuantityDrift() - exact match", () => {
  const result = detectQuantityDrift('MSFT', 100, 100, 0.001);

  assertEquals(result, null);
});

Deno.test("detectPriceDrift() - detects price difference", () => {
  const result = detectPriceDrift('AAPL', 150.00, 152.50, 0.01);

  assertEquals(result?.field, 'avg_entry_price');
  assertAlmostEquals(result?.difference || 0, 2.5, 0.001);
});

Deno.test("detectPriceDrift() - no drift within threshold", () => {
  const result = detectPriceDrift('AAPL', 150.00, 150.005, 0.01);

  assertEquals(result, null);
});

Deno.test("detectMarketValueDrift() - detects value difference", () => {
  const result = detectMarketValueDrift('NVDA', 10000, 10500, 1);

  assertEquals(result?.field, 'market_value');
  assertEquals(result?.difference, 500);
});

Deno.test("detectMarketValueDrift() - no drift within threshold", () => {
  const result = detectMarketValueDrift('NVDA', 10000, 10000.5, 1);

  assertEquals(result, null);
});

Deno.test("buildPositionRecord() - parses alpaca position", () => {
  const alpacaPos = {
    symbol: 'AAPL',
    qty: '10',
    avg_entry_price: '150.50',
    market_value: '1505.00',
    cost_basis: '1505.00',
    unrealized_pl: '50.00',
    unrealized_plpc: '0.0332',
    current_price: '155.50',
    side: 'long',
    asset_id: 'asset-123',
  };

  const result = buildPositionRecord('user-1', alpacaPos, 'paper');

  assertEquals(result.user_id, 'user-1');
  assertEquals(result.ticker, 'AAPL');
  assertEquals(result.quantity, 10);
  assertEquals(result.avg_entry_price, 150.50);
  assertEquals(result.market_value, 1505);
  assertEquals(result.unrealized_pl, 50);
  assertEquals(result.side, 'long');
  assertEquals(result.trading_mode, 'paper');
  assertEquals(result.is_open, true);
});

Deno.test("buildPositionRecord() - handles null user_id", () => {
  const alpacaPos = {
    symbol: 'TSLA',
    qty: '5',
    avg_entry_price: '200.00',
    market_value: '1000.00',
    cost_basis: '1000.00',
    unrealized_pl: '0.00',
    unrealized_plpc: '0',
    current_price: '200.00',
    side: 'long',
    asset_id: 'asset-456',
  };

  const result = buildPositionRecord(null, alpacaPos, 'live');

  assertEquals(result.user_id, null);
  assertEquals(result.trading_mode, 'live');
});

Deno.test("buildPositionRecord() - handles invalid numbers", () => {
  const alpacaPos = {
    symbol: 'INVALID',
    qty: 'not-a-number',
    avg_entry_price: '',
    market_value: 'NaN',
    cost_basis: '100.00',
    unrealized_pl: 'invalid',
    unrealized_plpc: '0',
    current_price: '50.00',
    side: 'long',
    asset_id: 'asset-789',
  };

  const result = buildPositionRecord('user-1', alpacaPos, 'paper');

  assertEquals(result.quantity, 0);
  assertEquals(result.avg_entry_price, 0);
  assertEquals(result.market_value, 0);
  assertEquals(result.unrealized_pl, 0);
  assertEquals(result.cost_basis, 100);
  assertEquals(result.current_price, 50);
});

Deno.test("determineHealthStatus() - healthy when no issues", () => {
  const result = determineHealthStatus(0, 0, 0);
  assertEquals(result, 'healthy');
});

Deno.test("determineHealthStatus() - degraded with drift", () => {
  const result = determineHealthStatus(1, 0, 0);
  assertEquals(result, 'degraded');
});

Deno.test("determineHealthStatus() - degraded with missing local", () => {
  const result = determineHealthStatus(0, 1, 0);
  assertEquals(result, 'degraded');
});

Deno.test("determineHealthStatus() - degraded with missing alpaca", () => {
  const result = determineHealthStatus(0, 0, 1);
  assertEquals(result, 'degraded');
});

Deno.test("determineHealthStatus() - degraded with multiple issues", () => {
  const result = determineHealthStatus(2, 3, 1);
  assertEquals(result, 'degraded');
});

Deno.test("sanitizeResponseBody() - short body unchanged", () => {
  const body = { success: true, data: 'test' };
  const result = sanitizeResponseBody(body);

  assertEquals(result, '{"success":true,"data":"test"}');
});

Deno.test("sanitizeResponseBody() - long body truncated", () => {
  const body = { data: 'x'.repeat(600) };
  const result = sanitizeResponseBody(body, 100);

  assertEquals(result.length, 103); // 100 + '...'
  assertEquals(result.endsWith('...'), true);
});

Deno.test("sanitizeResponseBody() - custom max length", () => {
  const body = { data: 'x'.repeat(100) };
  const result = sanitizeResponseBody(body, 50);

  assertEquals(result.length, 53); // 50 + '...'
});

// Order validation for place-order action
function validatePlaceOrderParams(params: {
  ticker?: string;
  quantity?: number;
  side?: string;
}): { valid: boolean; error?: string } {
  if (!params.ticker || !params.quantity || !params.side) {
    return { valid: false, error: 'Missing required fields: ticker, quantity, side' };
  }
  return { valid: true };
}

Deno.test("validatePlaceOrderParams() - valid params", () => {
  const result = validatePlaceOrderParams({
    ticker: 'AAPL',
    quantity: 10,
    side: 'buy',
  });

  assertEquals(result.valid, true);
});

Deno.test("validatePlaceOrderParams() - missing ticker", () => {
  const result = validatePlaceOrderParams({
    quantity: 10,
    side: 'buy',
  });

  assertEquals(result.valid, false);
});

// Position map building
function buildPositionMaps(
  alpacaPositions: Array<{ symbol: string }>,
  localPositions: Array<{ ticker: string }>
): { alpacaMap: Map<string, unknown>; localMap: Map<string, unknown> } {
  return {
    alpacaMap: new Map(alpacaPositions.map(p => [p.symbol, p])),
    localMap: new Map(localPositions.map(p => [p.ticker, p])),
  };
}

Deno.test("buildPositionMaps() - creates maps correctly", () => {
  const alpaca = [{ symbol: 'AAPL' }, { symbol: 'TSLA' }];
  const local = [{ ticker: 'AAPL' }, { ticker: 'MSFT' }];

  const { alpacaMap, localMap } = buildPositionMaps(alpaca, local);

  assertEquals(alpacaMap.size, 2);
  assertEquals(localMap.size, 2);
  assertEquals(alpacaMap.has('AAPL'), true);
  assertEquals(localMap.has('AAPL'), true);
  assertEquals(alpacaMap.has('MSFT'), false);
  assertEquals(localMap.has('TSLA'), false);
});

// Missing position detection
function findMissingPositions(
  alpacaSymbols: Set<string>,
  localTickers: Set<string>
): { missingLocal: string[]; missingAlpaca: string[] } {
  const missingLocal: string[] = [];
  const missingAlpaca: string[] = [];

  for (const symbol of alpacaSymbols) {
    if (!localTickers.has(symbol)) {
      missingLocal.push(symbol);
    }
  }

  for (const ticker of localTickers) {
    if (!alpacaSymbols.has(ticker)) {
      missingAlpaca.push(ticker);
    }
  }

  return { missingLocal, missingAlpaca };
}

Deno.test("findMissingPositions() - all synced", () => {
  const alpaca = new Set(['AAPL', 'TSLA']);
  const local = new Set(['AAPL', 'TSLA']);

  const result = findMissingPositions(alpaca, local);

  assertEquals(result.missingLocal.length, 0);
  assertEquals(result.missingAlpaca.length, 0);
});

Deno.test("findMissingPositions() - missing in local", () => {
  const alpaca = new Set(['AAPL', 'TSLA', 'NVDA']);
  const local = new Set(['AAPL', 'TSLA']);

  const result = findMissingPositions(alpaca, local);

  assertEquals(result.missingLocal, ['NVDA']);
  assertEquals(result.missingAlpaca.length, 0);
});

Deno.test("findMissingPositions() - missing in alpaca", () => {
  const alpaca = new Set(['AAPL']);
  const local = new Set(['AAPL', 'TSLA']);

  const result = findMissingPositions(alpaca, local);

  assertEquals(result.missingLocal.length, 0);
  assertEquals(result.missingAlpaca, ['TSLA']);
});

Deno.test("findMissingPositions() - mixed", () => {
  const alpaca = new Set(['AAPL', 'NVDA']);
  const local = new Set(['AAPL', 'TSLA']);

  const result = findMissingPositions(alpaca, local);

  assertEquals(result.missingLocal, ['NVDA']);
  assertEquals(result.missingAlpaca, ['TSLA']);
});
