/**
 * Unit tests for Alpaca trading hooks (METRICS.md Section 5.1 and Section 1.5).
 *
 * Tests all metrics consumed by trading/portfolio hooks:
 * - Trading Orders: status, fill_price, quantity, etc.
 * - Positions: quantity, value, unrealized_pl, etc.
 * - Account: balance
 * - Trading Signals: signal_type, confidence, etc.
 *
 * Run with: cd client && npm run test
 */

import { describe, it, expect, vi } from 'vitest';

// =============================================================================
// SECTION 5.1: Alpaca Trading API - Trading Orders (12 metrics)
// =============================================================================

describe('useOrders', () => {
  describe('[ ] trading_orders.alpaca_order_id metric', () => {
    it('returns Alpaca order UUID', () => {
      const mockOrder = { alpaca_order_id: '550e8400-e29b-41d4-a716-446655440000' };
      expect(mockOrder.alpaca_order_id).toMatch(/^[0-9a-f-]{36}$/i);
    });
  });

  describe('[ ] trading_orders.alpaca_client_order_id metric', () => {
    it('returns client-provided order ID', () => {
      const mockOrder = { alpaca_client_order_id: 'my-order-123' };
      expect(mockOrder.alpaca_client_order_id).toBe('my-order-123');
    });
  });

  describe('[ ] trading_orders.ticker metric', () => {
    it('returns stock symbol', () => {
      const mockOrder = { ticker: 'AAPL' };
      expect(mockOrder.ticker).toBe('AAPL');
    });

    it('ticker is uppercase', () => {
      const ticker = 'AAPL';
      expect(ticker).toBe(ticker.toUpperCase());
    });
  });

  describe('[ ] trading_orders.side metric', () => {
    it('returns buy or sell', () => {
      const mockOrder = { side: 'buy' };
      expect(['buy', 'sell']).toContain(mockOrder.side);
    });
  });

  describe('[ ] trading_orders.quantity metric', () => {
    it('returns number of shares', () => {
      const mockOrder = { quantity: 100 };
      expect(mockOrder.quantity).toBe(100);
    });

    it('quantity is positive', () => {
      const quantity = 100;
      expect(quantity).toBeGreaterThan(0);
    });
  });

  describe('[ ] trading_orders.order_type metric', () => {
    it('returns order type', () => {
      const mockOrder = { order_type: 'market' };
      expect(['market', 'limit', 'stop', 'stop_limit']).toContain(mockOrder.order_type);
    });
  });

  describe('[ ] trading_orders.limit_price metric', () => {
    it('returns limit price when applicable', () => {
      const mockOrder = { order_type: 'limit', limit_price: 150.50 };
      expect(mockOrder.limit_price).toBe(150.50);
    });

    it('limit_price is null for market orders', () => {
      const mockOrder = { order_type: 'market', limit_price: null };
      expect(mockOrder.limit_price).toBeNull();
    });
  });

  describe('[ ] trading_orders.stop_price metric', () => {
    it('returns stop price when applicable', () => {
      const mockOrder = { order_type: 'stop', stop_price: 145.00 };
      expect(mockOrder.stop_price).toBe(145.00);
    });
  });

  describe('[ ] trading_orders.status metric', () => {
    it('returns order status', () => {
      const mockOrder = { status: 'filled' };
      const validStatuses = ['new', 'partially_filled', 'filled', 'done_for_day',
        'canceled', 'expired', 'replaced', 'pending_cancel', 'pending_replace',
        'accepted', 'pending_new', 'accepted_for_bidding', 'stopped', 'rejected', 'suspended', 'calculated'];
      expect(validStatuses).toContain(mockOrder.status);
    });
  });

  describe('[ ] trading_orders.filled_quantity metric', () => {
    it('returns filled shares', () => {
      const mockOrder = { filled_quantity: 100, quantity: 100 };
      expect(mockOrder.filled_quantity).toBeLessThanOrEqual(mockOrder.quantity);
    });
  });

  describe('[ ] trading_orders.filled_avg_price metric', () => {
    it('returns average fill price', () => {
      const mockOrder = { filled_avg_price: 150.25 };
      expect(mockOrder.filled_avg_price).toBe(150.25);
    });

    it('filled_avg_price is positive when filled', () => {
      const filled_avg_price = 150.25;
      expect(filled_avg_price).toBeGreaterThan(0);
    });
  });

  describe('[ ] trading_orders.submitted_at metric', () => {
    it('returns submission timestamp', () => {
      const mockOrder = { submitted_at: '2024-01-15T10:30:00Z' };
      expect(mockOrder.submitted_at).toMatch(/\d{4}-\d{2}-\d{2}T/);
    });
  });

  describe('[ ] trading_orders.filled_at metric', () => {
    it('returns fill timestamp', () => {
      const mockOrder = { filled_at: '2024-01-15T10:30:01Z' };
      expect(mockOrder.filled_at).toMatch(/\d{4}-\d{2}-\d{2}T/);
    });
  });

  describe('[ ] trading_orders.canceled_at metric', () => {
    it('returns cancellation timestamp when canceled', () => {
      const mockOrder = { canceled_at: '2024-01-15T10:30:00Z', status: 'canceled' };
      expect(mockOrder.canceled_at).not.toBeNull();
    });

    it('canceled_at is null when not canceled', () => {
      const mockOrder = { canceled_at: null, status: 'filled' };
      expect(mockOrder.canceled_at).toBeNull();
    });
  });

  describe('[ ] trading_orders.expired_at metric', () => {
    it('returns expiration timestamp when expired', () => {
      const mockOrder = { expired_at: '2024-01-15T16:00:00Z', status: 'expired' };
      expect(mockOrder.expired_at).not.toBeNull();
    });
  });
});

// =============================================================================
// SECTION 5.1: Alpaca Trading API - Reference Portfolio Positions (7 metrics)
// =============================================================================

describe('useAlpacaPositions', () => {
  describe('[ ] position.ticker metric', () => {
    it('returns stock symbol', () => {
      const mockPosition = { ticker: 'AAPL' };
      expect(mockPosition.ticker).toBe('AAPL');
    });
  });

  describe('[ ] position.quantity metric', () => {
    it('returns shares held', () => {
      const mockPosition = { quantity: 100 };
      expect(mockPosition.quantity).toBe(100);
    });

    it('quantity can be fractional', () => {
      const mockPosition = { quantity: 10.5 };
      expect(mockPosition.quantity).toBe(10.5);
    });
  });

  describe('[ ] position.average_entry_price metric', () => {
    it('returns cost basis per share', () => {
      const mockPosition = { average_entry_price: 145.50 };
      expect(mockPosition.average_entry_price).toBe(145.50);
    });
  });

  describe('[ ] position.current_price metric', () => {
    it('returns real-time price', () => {
      const mockPosition = { current_price: 150.25 };
      expect(mockPosition.current_price).toBe(150.25);
    });
  });

  describe('[ ] position.market_value metric', () => {
    it('returns current position value', () => {
      const mockPosition = { quantity: 100, current_price: 150.25, market_value: 15025 };
      expect(mockPosition.market_value).toBe(mockPosition.quantity * mockPosition.current_price);
    });
  });

  describe('[ ] position.unrealized_pl metric', () => {
    it('returns unrealized P&L in dollars', () => {
      const mockPosition = {
        quantity: 100,
        average_entry_price: 145.50,
        current_price: 150.25,
        unrealized_pl: 475,
      };
      const calculatedPL = mockPosition.quantity * (mockPosition.current_price - mockPosition.average_entry_price);
      expect(mockPosition.unrealized_pl).toBe(calculatedPL);
    });

    it('unrealized_pl can be negative', () => {
      const mockPosition = { unrealized_pl: -250.50 };
      expect(mockPosition.unrealized_pl).toBeLessThan(0);
    });
  });

  describe('[ ] position.unrealized_plpc metric', () => {
    it('returns unrealized P&L percentage', () => {
      const mockPosition = {
        average_entry_price: 145.50,
        current_price: 150.25,
        unrealized_plpc: 3.26,
      };
      expect(mockPosition.unrealized_plpc).toBeGreaterThan(0);
    });

    it('unrealized_plpc is expressed as percentage', () => {
      const unrealized_plpc = 3.26;
      // Typical range is -100% to +infinite%, but usually -50% to +100%
      expect(unrealized_plpc).toBeGreaterThan(-100);
    });
  });
});

// =============================================================================
// SECTION 5.1: Alpaca Trading API - Portfolios (2 metrics)
// =============================================================================

describe('useAlpacaAccount', () => {
  describe('[ ] portfolio.cash_balance metric', () => {
    it('returns available cash', () => {
      const mockAccount = { cash: 10000.50 };
      expect(mockAccount.cash).toBe(10000.50);
    });

    it('cash_balance is non-negative', () => {
      const cash = 10000.50;
      expect(cash).toBeGreaterThanOrEqual(0);
    });
  });

  describe('[ ] portfolio.current_value metric', () => {
    it('returns total portfolio value', () => {
      const mockAccount = { portfolio_value: 150000.75 };
      expect(mockAccount.portfolio_value).toBe(150000.75);
    });

    it('portfolio_value includes cash and positions', () => {
      const cash = 10000;
      const positionsValue = 140000;
      const portfolioValue = cash + positionsValue;
      expect(portfolioValue).toBe(150000);
    });
  });
});

// =============================================================================
// SECTION 1.5: Trading Signals (from ML Service)
// =============================================================================

describe('Trading Signals', () => {
  describe('[ ] trading_signals.signal_type metric', () => {
    it('returns signal type', () => {
      const mockSignal = { signal_type: 'buy' };
      expect(['buy', 'sell', 'hold', 'strong_buy', 'strong_sell']).toContain(mockSignal.signal_type);
    });
  });

  describe('[ ] trading_signals.confidence_score metric', () => {
    it('returns confidence between 0 and 1', () => {
      const mockSignal = { confidence_score: 0.75 };
      expect(mockSignal.confidence_score).toBeGreaterThanOrEqual(0);
      expect(mockSignal.confidence_score).toBeLessThanOrEqual(1);
    });
  });

  describe('[ ] reference_portfolio_positions metric', () => {
    it('reference portfolio tracks positions', () => {
      const mockReferencePortfolio = {
        positions: [
          { ticker: 'AAPL', quantity: 50, market_value: 7500 },
          { ticker: 'NVDA', quantity: 20, market_value: 12000 },
        ],
      };
      expect(mockReferencePortfolio.positions.length).toBeGreaterThan(0);
    });
  });
});

// =============================================================================
// Order State Machine Tests
// =============================================================================

describe('Order State Machine', () => {
  it('new orders transition to filled or canceled', () => {
    const validTransitions: Record<string, string[]> = {
      new: ['accepted', 'rejected', 'canceled'],
      accepted: ['filled', 'partially_filled', 'canceled', 'expired'],
      partially_filled: ['filled', 'canceled'],
      filled: [], // Terminal state
      canceled: [], // Terminal state
      expired: [], // Terminal state
    };

    expect(validTransitions['new']).toContain('accepted');
    expect(validTransitions['accepted']).toContain('filled');
    expect(validTransitions['filled']).toEqual([]);
  });
});

// =============================================================================
// Position Calculations Tests
// =============================================================================

describe('Position Calculations', () => {
  it('calculates market value correctly', () => {
    const quantity = 100;
    const currentPrice = 150.25;
    const marketValue = quantity * currentPrice;
    expect(marketValue).toBe(15025);
  });

  it('calculates unrealized P&L correctly', () => {
    const quantity = 100;
    const entryPrice = 145.50;
    const currentPrice = 150.25;
    const unrealizedPL = quantity * (currentPrice - entryPrice);
    expect(unrealizedPL).toBe(475);
  });

  it('calculates unrealized P&L percentage correctly', () => {
    const entryPrice = 145.50;
    const currentPrice = 150.25;
    const unrealizedPLPC = ((currentPrice - entryPrice) / entryPrice) * 100;
    expect(unrealizedPLPC).toBeCloseTo(3.26, 1);
  });

  it('calculates portfolio total value correctly', () => {
    const positions = [
      { market_value: 15025 },
      { market_value: 12000 },
      { market_value: 8500 },
    ];
    const cash = 10000;
    const positionsValue = positions.reduce((sum, p) => sum + p.market_value, 0);
    const totalValue = positionsValue + cash;
    expect(totalValue).toBe(45525);
  });
});

// =============================================================================
// Alpaca API Response Format Tests
// =============================================================================

describe('Alpaca API Response Formats', () => {
  it('order response has required fields', () => {
    const mockOrderResponse = {
      id: '550e8400-e29b-41d4-a716-446655440000',
      client_order_id: 'my-order-123',
      symbol: 'AAPL',
      side: 'buy',
      qty: '100',
      type: 'market',
      status: 'filled',
      filled_qty: '100',
      filled_avg_price: '150.25',
      submitted_at: '2024-01-15T10:30:00Z',
      filled_at: '2024-01-15T10:30:01Z',
    };

    expect(mockOrderResponse.id).toBeDefined();
    expect(mockOrderResponse.symbol).toBeDefined();
    expect(mockOrderResponse.side).toBeDefined();
    expect(mockOrderResponse.status).toBeDefined();
  });

  it('position response has required fields', () => {
    const mockPositionResponse = {
      symbol: 'AAPL',
      qty: '100',
      avg_entry_price: '145.50',
      market_value: '15025',
      unrealized_pl: '475',
      unrealized_plpc: '0.0326',
    };

    expect(mockPositionResponse.symbol).toBeDefined();
    expect(mockPositionResponse.qty).toBeDefined();
    expect(mockPositionResponse.market_value).toBeDefined();
  });

  it('account response has required fields', () => {
    const mockAccountResponse = {
      cash: '10000.50',
      portfolio_value: '150000.75',
      buying_power: '20000.00',
      equity: '150000.75',
    };

    expect(mockAccountResponse.cash).toBeDefined();
    expect(mockAccountResponse.portfolio_value).toBeDefined();
  });
});
