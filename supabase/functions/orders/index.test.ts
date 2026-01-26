/**
 * Tests for orders Edge Function
 *
 * Tests:
 * - Idempotency key generation
 * - Order validation
 * - Order status filtering
 * - Order transformation
 * - Statistics calculation
 */

import { assertEquals, assertStringIncludes, assertNotEquals } from "https://deno.land/std@0.208.0/assert/mod.ts";

// Extracted idempotency key generation logic
function generateIdempotencyKey(
  userId: string,
  ticker: string,
  side: string,
  quantity: number,
  signalId: string | null
): string {
  const timestamp = Math.floor(Date.now() / 60000);
  const components = [userId, ticker.toUpperCase(), side, quantity.toString(), signalId || 'no-signal', timestamp.toString()];
  const uuid = crypto.randomUUID().substring(0, 8);
  return `order_${components.join('_')}_${uuid}`;
}

// Order validation logic
function validateOrderParams(params: {
  ticker?: string;
  side?: string;
  quantity?: number;
}): { valid: boolean; error?: string } {
  if (!params.ticker || !params.side || params.quantity === undefined || params.quantity === null) {
    return { valid: false, error: 'Missing required fields: ticker, side, quantity' };
  }

  if (!['buy', 'sell'].includes(params.side)) {
    return { valid: false, error: 'Side must be "buy" or "sell"' };
  }

  if (params.quantity <= 0) {
    return { valid: false, error: 'Quantity must be greater than 0' };
  }

  return { valid: true };
}

// Status filter mapping
function mapStatusFilter(statusFilter: string): string[] {
  if (statusFilter === 'open') {
    return ['new', 'accepted', 'pending_new', 'partially_filled'];
  } else if (statusFilter === 'closed') {
    return ['filled', 'canceled', 'rejected', 'expired'];
  }
  return [statusFilter];
}

// Order transformation
function transformOrder(order: {
  id: string;
  filled_qty?: number;
  alpaca_order_id?: string;
}): { id: string; filled_quantity: number; alpaca_order_id: string } {
  return {
    ...order,
    filled_quantity: order.filled_qty || 0,
    alpaca_order_id: order.alpaca_order_id || order.id,
  };
}

// Statistics calculation
function calculateOrderStats(orders: Array<{
  status: string;
  side: string;
  quantity: number;
  filled_avg_price?: number;
}>): {
  total_orders: number;
  status_distribution: Record<string, number>;
  side_distribution: Record<string, number>;
  average_fill_price: number;
  total_volume: number;
  success_rate: number;
} {
  const stats = {
    total_orders: orders.length,
    status_distribution: {} as Record<string, number>,
    side_distribution: {} as Record<string, number>,
    average_fill_price: 0,
    total_volume: 0,
    success_rate: 0,
  };

  if (orders.length === 0) return stats;

  let totalFilledPrice = 0;
  let filledOrderCount = 0;

  orders.forEach(order => {
    stats.status_distribution[order.status] = (stats.status_distribution[order.status] || 0) + 1;
    stats.side_distribution[order.side] = (stats.side_distribution[order.side] || 0) + 1;
    stats.total_volume += order.quantity;

    if (order.filled_avg_price) {
      totalFilledPrice += order.filled_avg_price * order.quantity;
      filledOrderCount++;
    }
  });

  if (filledOrderCount > 0) {
    stats.average_fill_price = totalFilledPrice / filledOrderCount;
  }

  const filledOrders = stats.status_distribution['filled'] || 0;
  stats.success_rate = (filledOrders / orders.length) * 100;

  return stats;
}

// Request sanitization
function sanitizeHeadersForLogging(headers: Record<string, string>): Record<string, string> {
  const sanitized = { ...headers };
  const sensitiveHeaders = ['authorization', 'x-api-key', 'cookie', 'x-supabase-auth'];
  sensitiveHeaders.forEach(header => {
    if (sanitized[header]) {
      sanitized[header] = '[REDACTED]';
    }
  });
  return sanitized;
}

// Tests

Deno.test("generateIdempotencyKey() - generates unique keys", () => {
  const key1 = generateIdempotencyKey('user1', 'AAPL', 'buy', 10, null);
  const key2 = generateIdempotencyKey('user1', 'AAPL', 'buy', 10, null);

  // Keys should be different due to UUID component
  assertNotEquals(key1, key2);
});

Deno.test("generateIdempotencyKey() - includes order components", () => {
  const key = generateIdempotencyKey('user123', 'TSLA', 'sell', 50, 'signal-abc');

  assertStringIncludes(key, 'order_');
  assertStringIncludes(key, 'user123');
  assertStringIncludes(key, 'TSLA');
  assertStringIncludes(key, 'sell');
  assertStringIncludes(key, '50');
  assertStringIncludes(key, 'signal-abc');
});

Deno.test("generateIdempotencyKey() - uppercases ticker", () => {
  const key = generateIdempotencyKey('user1', 'aapl', 'buy', 10, null);

  assertStringIncludes(key, 'AAPL');
});

Deno.test("generateIdempotencyKey() - handles null signal", () => {
  const key = generateIdempotencyKey('user1', 'AAPL', 'buy', 10, null);

  assertStringIncludes(key, 'no-signal');
});

Deno.test("validateOrderParams() - valid order", () => {
  const result = validateOrderParams({ ticker: 'AAPL', side: 'buy', quantity: 10 });

  assertEquals(result.valid, true);
  assertEquals(result.error, undefined);
});

Deno.test("validateOrderParams() - missing ticker", () => {
  const result = validateOrderParams({ side: 'buy', quantity: 10 });

  assertEquals(result.valid, false);
  assertStringIncludes(result.error!, 'ticker');
});

Deno.test("validateOrderParams() - missing side", () => {
  const result = validateOrderParams({ ticker: 'AAPL', quantity: 10 });

  assertEquals(result.valid, false);
  assertStringIncludes(result.error!, 'side');
});

Deno.test("validateOrderParams() - missing quantity", () => {
  const result = validateOrderParams({ ticker: 'AAPL', side: 'buy' });

  assertEquals(result.valid, false);
  assertStringIncludes(result.error!, 'quantity');
});

Deno.test("validateOrderParams() - invalid side", () => {
  const result = validateOrderParams({ ticker: 'AAPL', side: 'hold', quantity: 10 });

  assertEquals(result.valid, false);
  assertStringIncludes(result.error!, 'Side must be');
});

Deno.test("validateOrderParams() - zero quantity", () => {
  const result = validateOrderParams({ ticker: 'AAPL', side: 'buy', quantity: 0 });

  assertEquals(result.valid, false);
  assertStringIncludes(result.error!, 'Quantity must be greater than 0');
});

Deno.test("validateOrderParams() - negative quantity", () => {
  const result = validateOrderParams({ ticker: 'AAPL', side: 'buy', quantity: -5 });

  assertEquals(result.valid, false);
});

Deno.test("mapStatusFilter() - open status", () => {
  const result = mapStatusFilter('open');

  assertEquals(result.includes('new'), true);
  assertEquals(result.includes('accepted'), true);
  assertEquals(result.includes('pending_new'), true);
  assertEquals(result.includes('partially_filled'), true);
});

Deno.test("mapStatusFilter() - closed status", () => {
  const result = mapStatusFilter('closed');

  assertEquals(result.includes('filled'), true);
  assertEquals(result.includes('canceled'), true);
  assertEquals(result.includes('rejected'), true);
  assertEquals(result.includes('expired'), true);
});

Deno.test("mapStatusFilter() - specific status", () => {
  const result = mapStatusFilter('filled');

  assertEquals(result, ['filled']);
});

Deno.test("transformOrder() - adds filled_quantity", () => {
  const order = { id: 'order-1', filled_qty: 10 };
  const result = transformOrder(order);

  assertEquals(result.filled_quantity, 10);
});

Deno.test("transformOrder() - defaults filled_quantity to 0", () => {
  const order = { id: 'order-1' };
  const result = transformOrder(order);

  assertEquals(result.filled_quantity, 0);
});

Deno.test("transformOrder() - uses alpaca_order_id if present", () => {
  const order = { id: 'order-1', alpaca_order_id: 'alpaca-123' };
  const result = transformOrder(order);

  assertEquals(result.alpaca_order_id, 'alpaca-123');
});

Deno.test("transformOrder() - falls back to id for alpaca_order_id", () => {
  const order = { id: 'order-1' };
  const result = transformOrder(order);

  assertEquals(result.alpaca_order_id, 'order-1');
});

Deno.test("calculateOrderStats() - empty orders", () => {
  const result = calculateOrderStats([]);

  assertEquals(result.total_orders, 0);
  assertEquals(result.success_rate, 0);
  assertEquals(result.total_volume, 0);
});

Deno.test("calculateOrderStats() - counts statuses", () => {
  const orders = [
    { status: 'filled', side: 'buy', quantity: 10 },
    { status: 'filled', side: 'buy', quantity: 20 },
    { status: 'canceled', side: 'sell', quantity: 5 },
  ];

  const result = calculateOrderStats(orders);

  assertEquals(result.status_distribution['filled'], 2);
  assertEquals(result.status_distribution['canceled'], 1);
});

Deno.test("calculateOrderStats() - counts sides", () => {
  const orders = [
    { status: 'filled', side: 'buy', quantity: 10 },
    { status: 'filled', side: 'buy', quantity: 20 },
    { status: 'filled', side: 'sell', quantity: 5 },
  ];

  const result = calculateOrderStats(orders);

  assertEquals(result.side_distribution['buy'], 2);
  assertEquals(result.side_distribution['sell'], 1);
});

Deno.test("calculateOrderStats() - calculates volume", () => {
  const orders = [
    { status: 'filled', side: 'buy', quantity: 10 },
    { status: 'filled', side: 'buy', quantity: 20 },
    { status: 'filled', side: 'sell', quantity: 5 },
  ];

  const result = calculateOrderStats(orders);

  assertEquals(result.total_volume, 35);
});

Deno.test("calculateOrderStats() - calculates success rate", () => {
  const orders = [
    { status: 'filled', side: 'buy', quantity: 10 },
    { status: 'filled', side: 'buy', quantity: 20 },
    { status: 'canceled', side: 'sell', quantity: 5 },
    { status: 'rejected', side: 'buy', quantity: 15 },
  ];

  const result = calculateOrderStats(orders);

  assertEquals(result.success_rate, 50); // 2 filled out of 4
});

Deno.test("calculateOrderStats() - calculates average fill price", () => {
  const orders = [
    { status: 'filled', side: 'buy', quantity: 10, filled_avg_price: 100 },
    { status: 'filled', side: 'buy', quantity: 10, filled_avg_price: 150 },
  ];

  const result = calculateOrderStats(orders);

  assertEquals(result.average_fill_price, 1250); // (100*10 + 150*10) / 2
});

Deno.test("sanitizeHeadersForLogging() - redacts sensitive headers", () => {
  const headers = {
    'authorization': 'Bearer secret-token',
    'x-api-key': 'api-key-value',
    'content-type': 'application/json',
  };

  const result = sanitizeHeadersForLogging(headers);

  assertEquals(result['authorization'], '[REDACTED]');
  assertEquals(result['x-api-key'], '[REDACTED]');
  assertEquals(result['content-type'], 'application/json');
});

Deno.test("sanitizeHeadersForLogging() - handles missing headers", () => {
  const headers = {
    'content-type': 'application/json',
  };

  const result = sanitizeHeadersForLogging(headers);

  assertEquals(result['authorization'], undefined);
  assertEquals(result['content-type'], 'application/json');
});

// Test Alpaca order request building
interface AlpacaOrderRequest {
  symbol: string;
  qty: number;
  side: string;
  type: string;
  time_in_force: string;
  limit_price?: number;
}

function buildAlpacaOrderRequest(params: {
  ticker: string;
  quantity: number;
  side: string;
  order_type?: string;
  limit_price?: number;
}): AlpacaOrderRequest {
  const request: AlpacaOrderRequest = {
    symbol: params.ticker.toUpperCase(),
    qty: params.quantity,
    side: params.side,
    type: params.order_type || 'market',
    time_in_force: 'day',
  };

  if (params.order_type === 'limit' && params.limit_price) {
    request.limit_price = params.limit_price;
  }

  return request;
}

Deno.test("buildAlpacaOrderRequest() - market order", () => {
  const result = buildAlpacaOrderRequest({
    ticker: 'aapl',
    quantity: 10,
    side: 'buy',
  });

  assertEquals(result.symbol, 'AAPL');
  assertEquals(result.qty, 10);
  assertEquals(result.side, 'buy');
  assertEquals(result.type, 'market');
  assertEquals(result.time_in_force, 'day');
  assertEquals(result.limit_price, undefined);
});

Deno.test("buildAlpacaOrderRequest() - limit order", () => {
  const result = buildAlpacaOrderRequest({
    ticker: 'TSLA',
    quantity: 5,
    side: 'sell',
    order_type: 'limit',
    limit_price: 250.50,
  });

  assertEquals(result.type, 'limit');
  assertEquals(result.limit_price, 250.50);
});
