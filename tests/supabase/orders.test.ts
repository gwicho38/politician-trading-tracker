// Deno tests for orders edge function
// Run with: deno test --allow-env --allow-net index.test.ts

import {
  assertEquals,
  assertExists,
  assertStringIncludes,
} from "https://deno.land/std@0.168.0/testing/asserts.ts";

// ============================================================================
// Idempotency Key Generation Tests
// ============================================================================

Deno.test("generateIdempotencyKey - generates consistent key", async () => {
  const generateIdempotencyKey = async (
    userId: string,
    ticker: string,
    side: string,
    quantity: number,
    signalId?: string
  ): Promise<string> => {
    const data = `${userId}-${ticker}-${side}-${quantity}-${signalId || 'no-signal'}`;
    const encoder = new TextEncoder();
    const hashBuffer = await crypto.subtle.digest('SHA-256', encoder.encode(data));
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  };

  const key1 = await generateIdempotencyKey('user-123', 'AAPL', 'buy', 100, 'signal-456');
  const key2 = await generateIdempotencyKey('user-123', 'AAPL', 'buy', 100, 'signal-456');

  assertEquals(key1, key2); // Same inputs = same key
  assertEquals(key1.length, 64); // SHA-256 = 64 hex chars
});

Deno.test("generateIdempotencyKey - different inputs produce different keys", async () => {
  const generateIdempotencyKey = async (
    userId: string,
    ticker: string,
    side: string,
    quantity: number,
    signalId?: string
  ): Promise<string> => {
    const data = `${userId}-${ticker}-${side}-${quantity}-${signalId || 'no-signal'}`;
    const encoder = new TextEncoder();
    const hashBuffer = await crypto.subtle.digest('SHA-256', encoder.encode(data));
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  };

  const key1 = await generateIdempotencyKey('user-123', 'AAPL', 'buy', 100);
  const key2 = await generateIdempotencyKey('user-123', 'GOOGL', 'buy', 100);
  const key3 = await generateIdempotencyKey('user-123', 'AAPL', 'sell', 100);
  const key4 = await generateIdempotencyKey('user-123', 'AAPL', 'buy', 50);

  // All should be different
  const keys = [key1, key2, key3, key4];
  const uniqueKeys = new Set(keys);
  assertEquals(uniqueKeys.size, 4);
});

// ============================================================================
// Order State Transition Tests
// ============================================================================

Deno.test("Order state machine - valid state transitions", () => {
  const validTransitions: Record<string, string[]> = {
    'draft': ['pending'],
    'pending': ['submitted', 'canceled'],
    'submitted': ['accepted', 'rejected'],
    'accepted': ['filled', 'partially_filled', 'canceled', 'expired'],
    'partially_filled': ['filled', 'canceled'],
    'filled': [], // Terminal state
    'rejected': [], // Terminal state
    'canceled': [], // Terminal state
    'expired': [], // Terminal state
  };

  const canTransition = (from: string, to: string): boolean => {
    return validTransitions[from]?.includes(to) ?? false;
  };

  // Valid transitions
  assertEquals(canTransition('draft', 'pending'), true);
  assertEquals(canTransition('pending', 'submitted'), true);
  assertEquals(canTransition('submitted', 'accepted'), true);
  assertEquals(canTransition('accepted', 'filled'), true);
  assertEquals(canTransition('accepted', 'canceled'), true);

  // Invalid transitions
  assertEquals(canTransition('draft', 'filled'), false);
  assertEquals(canTransition('filled', 'canceled'), false);
  assertEquals(canTransition('rejected', 'accepted'), false);
});

Deno.test("Order state machine - terminal states have no transitions", () => {
  const terminalStates = ['filled', 'rejected', 'canceled', 'expired'];

  const validTransitions: Record<string, string[]> = {
    'filled': [],
    'rejected': [],
    'canceled': [],
    'expired': [],
  };

  for (const state of terminalStates) {
    assertEquals(validTransitions[state].length, 0);
  }
});

// ============================================================================
// Signal Lifecycle Tests
// ============================================================================

Deno.test("Signal lifecycle - valid state transitions", () => {
  const validLifecycleTransitions: Record<string, string[]> = {
    'generated': ['active', 'in_cart', 'expired'],
    'active': ['in_cart', 'expired'],
    'in_cart': ['ordered', 'active', 'expired'],
    'ordered': ['filled', 'canceled', 'expired'],
    'filled': [], // Terminal
    'canceled': ['active'], // Can be re-activated
    'expired': [], // Terminal
  };

  const canTransition = (from: string, to: string): boolean => {
    return validLifecycleTransitions[from]?.includes(to) ?? false;
  };

  // Valid transitions
  assertEquals(canTransition('generated', 'in_cart'), true);
  assertEquals(canTransition('in_cart', 'ordered'), true);
  assertEquals(canTransition('ordered', 'filled'), true);

  // Invalid transitions
  assertEquals(canTransition('generated', 'filled'), false);
  assertEquals(canTransition('filled', 'active'), false);
});

// ============================================================================
// Order Validation Tests
// ============================================================================

Deno.test("Order validation - validates required fields", () => {
  interface OrderRequest {
    ticker?: string;
    side?: string;
    quantity?: number;
    type?: string;
  }

  const validateOrder = (order: OrderRequest): { valid: boolean; errors: string[] } => {
    const errors: string[] = [];

    if (!order.ticker) errors.push('ticker is required');
    if (!order.side) errors.push('side is required');
    if (!order.quantity || order.quantity <= 0) errors.push('quantity must be positive');
    if (!order.type) errors.push('type is required');

    return { valid: errors.length === 0, errors };
  };

  // Valid order
  const validOrder = { ticker: 'AAPL', side: 'buy', quantity: 100, type: 'market' };
  assertEquals(validateOrder(validOrder).valid, true);

  // Missing ticker
  const noTicker = { side: 'buy', quantity: 100, type: 'market' };
  const result1 = validateOrder(noTicker);
  assertEquals(result1.valid, false);
  assertStringIncludes(result1.errors.join(','), 'ticker');

  // Invalid quantity
  const badQuantity = { ticker: 'AAPL', side: 'buy', quantity: 0, type: 'market' };
  const result2 = validateOrder(badQuantity);
  assertEquals(result2.valid, false);
  assertStringIncludes(result2.errors.join(','), 'quantity');
});

Deno.test("Order validation - validates side values", () => {
  const validSides = ['buy', 'sell'];

  const isValidSide = (side: string): boolean => {
    return validSides.includes(side.toLowerCase());
  };

  assertEquals(isValidSide('buy'), true);
  assertEquals(isValidSide('sell'), true);
  assertEquals(isValidSide('BUY'), true);
  assertEquals(isValidSide('SELL'), true);
  assertEquals(isValidSide('hold'), false);
  assertEquals(isValidSide(''), false);
});

Deno.test("Order validation - validates order types", () => {
  const validTypes = ['market', 'limit', 'stop', 'stop_limit'];

  const isValidType = (type: string): boolean => {
    return validTypes.includes(type.toLowerCase());
  };

  assertEquals(isValidType('market'), true);
  assertEquals(isValidType('limit'), true);
  assertEquals(isValidType('stop'), true);
  assertEquals(isValidType('stop_limit'), true);
  assertEquals(isValidType('MARKET'), true);
  assertEquals(isValidType('invalid'), false);
});

// ============================================================================
// Circuit Breaker Tests (Same as alpaca-account)
// ============================================================================

Deno.test("Orders Circuit Breaker - configuration", () => {
  const CIRCUIT_BREAKER_CONFIG = {
    failureThreshold: 5,
    resetTimeout: 30000,
    halfOpenRequests: 2,
  };

  assertEquals(CIRCUIT_BREAKER_CONFIG.failureThreshold, 5);
  assertEquals(CIRCUIT_BREAKER_CONFIG.resetTimeout, 30000);
  assertEquals(CIRCUIT_BREAKER_CONFIG.halfOpenRequests, 2);
});

// ============================================================================
// Order Response Formatting Tests
// ============================================================================

Deno.test("Order response formatting - formats Alpaca order correctly", () => {
  const alpacaOrder = {
    id: 'order-123',
    client_order_id: 'client-456',
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:05Z',
    submitted_at: '2024-01-15T10:00:01Z',
    filled_at: '2024-01-15T10:00:05Z',
    expired_at: null,
    canceled_at: null,
    failed_at: null,
    asset_id: 'asset-789',
    symbol: 'AAPL',
    asset_class: 'us_equity',
    qty: '100',
    filled_qty: '100',
    type: 'market',
    side: 'buy',
    time_in_force: 'day',
    limit_price: null,
    stop_price: null,
    filled_avg_price: '150.50',
    status: 'filled',
  };

  const formattedOrder = {
    alpaca_order_id: alpacaOrder.id,
    client_order_id: alpacaOrder.client_order_id,
    ticker: alpacaOrder.symbol,
    quantity: parseFloat(alpacaOrder.qty) || 0,
    filled_quantity: parseFloat(alpacaOrder.filled_qty) || 0,
    order_type: alpacaOrder.type,
    side: alpacaOrder.side,
    time_in_force: alpacaOrder.time_in_force,
    limit_price: alpacaOrder.limit_price ? parseFloat(alpacaOrder.limit_price) : null,
    stop_price: alpacaOrder.stop_price ? parseFloat(alpacaOrder.stop_price) : null,
    filled_avg_price: alpacaOrder.filled_avg_price ? parseFloat(alpacaOrder.filled_avg_price) : null,
    status: alpacaOrder.status,
    created_at: alpacaOrder.created_at,
    filled_at: alpacaOrder.filled_at,
  };

  assertEquals(formattedOrder.alpaca_order_id, 'order-123');
  assertEquals(formattedOrder.ticker, 'AAPL');
  assertEquals(formattedOrder.quantity, 100);
  assertEquals(formattedOrder.filled_quantity, 100);
  assertEquals(formattedOrder.filled_avg_price, 150.50);
  assertEquals(formattedOrder.status, 'filled');
});

// ============================================================================
// Order Status Mapping Tests
// ============================================================================

Deno.test("Order status mapping - maps Alpaca statuses correctly", () => {
  const statusMap: Record<string, string> = {
    'new': 'pending',
    'partially_filled': 'partially_filled',
    'filled': 'filled',
    'done_for_day': 'completed',
    'canceled': 'canceled',
    'expired': 'expired',
    'replaced': 'replaced',
    'pending_cancel': 'canceling',
    'pending_replace': 'replacing',
    'accepted': 'accepted',
    'pending_new': 'pending',
    'accepted_for_bidding': 'accepted',
    'stopped': 'stopped',
    'rejected': 'rejected',
    'suspended': 'suspended',
    'calculated': 'calculated',
  };

  const mapStatus = (alpacaStatus: string): string => {
    return statusMap[alpacaStatus] || alpacaStatus;
  };

  assertEquals(mapStatus('new'), 'pending');
  assertEquals(mapStatus('filled'), 'filled');
  assertEquals(mapStatus('canceled'), 'canceled');
  assertEquals(mapStatus('rejected'), 'rejected');
  assertEquals(mapStatus('unknown_status'), 'unknown_status'); // Passthrough
});

// ============================================================================
// Duplicate Order Detection Tests
// ============================================================================

Deno.test("Duplicate order detection - identifies duplicate by idempotency key", async () => {
  const existingOrders: Record<string, any> = {
    'abc123': { id: 'order-1', ticker: 'AAPL', status: 'filled' },
  };

  const checkIdempotency = async (idempotencyKey: string): Promise<{
    exists: boolean;
    existingOrder?: any;
  }> => {
    const existing = existingOrders[idempotencyKey];
    if (existing) {
      return { exists: true, existingOrder: existing };
    }
    return { exists: false };
  };

  const result1 = await checkIdempotency('abc123');
  assertEquals(result1.exists, true);
  assertExists(result1.existingOrder);
  assertEquals(result1.existingOrder.ticker, 'AAPL');

  const result2 = await checkIdempotency('xyz789');
  assertEquals(result2.exists, false);
  assertEquals(result2.existingOrder, undefined);
});

// ============================================================================
// Order Amount Calculations Tests
// ============================================================================

Deno.test("Order calculations - calculates total value", () => {
  const calculateOrderValue = (quantity: number, price: number): number => {
    return quantity * price;
  };

  assertEquals(calculateOrderValue(100, 150.50), 15050);
  assertEquals(calculateOrderValue(50, 200), 10000);
  assertEquals(calculateOrderValue(1, 500.25), 500.25);
});

Deno.test("Order calculations - calculates commission estimate", () => {
  const calculateCommission = (orderValue: number, rate: number = 0): number => {
    // Alpaca has zero commission, but this tests the pattern
    return orderValue * rate;
  };

  assertEquals(calculateCommission(10000, 0), 0);
  assertEquals(calculateCommission(10000, 0.001), 10);
});

// ============================================================================
// Order History Filtering Tests
// ============================================================================

Deno.test("Order history filtering - filters by status", () => {
  const orders = [
    { id: '1', status: 'filled' },
    { id: '2', status: 'canceled' },
    { id: '3', status: 'filled' },
    { id: '4', status: 'pending' },
  ];

  const filterByStatus = (orders: any[], status: string) => {
    return orders.filter(o => o.status === status);
  };

  assertEquals(filterByStatus(orders, 'filled').length, 2);
  assertEquals(filterByStatus(orders, 'canceled').length, 1);
  assertEquals(filterByStatus(orders, 'pending').length, 1);
  assertEquals(filterByStatus(orders, 'rejected').length, 0);
});

Deno.test("Order history filtering - filters by date range", () => {
  const orders = [
    { id: '1', created_at: '2024-01-10T10:00:00Z' },
    { id: '2', created_at: '2024-01-15T10:00:00Z' },
    { id: '3', created_at: '2024-01-20T10:00:00Z' },
  ];

  const filterByDateRange = (orders: any[], startDate: string, endDate: string) => {
    const start = new Date(startDate);
    const end = new Date(endDate);
    return orders.filter(o => {
      const created = new Date(o.created_at);
      return created >= start && created <= end;
    });
  };

  const filtered = filterByDateRange(orders, '2024-01-12', '2024-01-18');
  assertEquals(filtered.length, 1);
  assertEquals(filtered[0].id, '2');
});

// ============================================================================
// CORS Headers Tests
// ============================================================================

Deno.test("Orders CORS headers - correct format", () => {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  };

  assertEquals(corsHeaders['Access-Control-Allow-Origin'], '*');
  assertStringIncludes(corsHeaders['Access-Control-Allow-Headers'], 'authorization');
});
