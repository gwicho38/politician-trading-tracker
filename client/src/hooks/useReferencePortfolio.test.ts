/**
 * Tests for hooks/useReferencePortfolio.ts
 *
 * Tests:
 * - useReferencePortfolioState() - Portfolio state with config join
 * - useReferencePortfolioPositions() - Open/closed positions
 * - useReferencePortfolioTrades() - Trade history with pagination
 * - useReferencePortfolioPerformance() - Performance snapshots from edge function
 * - useReferencePortfolioConfig() - Portfolio configuration
 * - useMarketStatus() - Client-side market hours check
 * - useReferencePortfolioSummary() - Computed summary metrics
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock Supabase client
const mockFrom = vi.fn();
const mockFunctionsInvoke = vi.fn();
vi.mock('@/integrations/supabase/client', () => ({
  supabasePublic: {
    from: (...args: unknown[]) => mockFrom(...args),
    functions: { invoke: (...args: unknown[]) => mockFunctionsInvoke(...args) },
  },
  supabase: {
    from: (...args: unknown[]) => mockFrom(...args),
    functions: { invoke: (...args: unknown[]) => mockFunctionsInvoke(...args) },
  },
}));

// Mock logger
vi.mock('@/lib/logger', () => ({
  logError: vi.fn(),
}));

import {
  useReferencePortfolioState,
  useReferencePortfolioPositions,
  useReferencePortfolioTrades,
  useReferencePortfolioPerformance,
  useReferencePortfolioConfig,
  useMarketStatus,
  useReferencePortfolioSummary,
} from './useReferencePortfolio';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

function singleChain(data: unknown) {
  const terminal = { data, error: null };
  const handler: ProxyHandler<object> = {
    get(_target, prop: string) {
      if (prop === 'single') return vi.fn().mockResolvedValue(terminal);
      return vi.fn().mockReturnValue(new Proxy({}, handler));
    },
  };
  return new Proxy({}, handler);
}

function tableChain(data: unknown, opts?: { count?: number }) {
  const terminal = { data, error: null, count: opts?.count ?? null };
  const handler: ProxyHandler<object> = {
    get(_target, prop: string) {
      if (prop === 'then')
        return (resolve: (v: unknown) => void) => Promise.resolve(terminal).then(resolve);
      return vi.fn().mockReturnValue(new Proxy({}, handler));
    },
  };
  return new Proxy({}, handler);
}

describe('useReferencePortfolioState()', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches portfolio state with config join', async () => {
    const mockState = {
      id: 's1',
      portfolio_value: 100000,
      cash: 25000,
      total_return: 5000,
      total_return_pct: 5.0,
      day_return: 200,
      day_return_pct: 0.2,
      win_rate: 0.65,
      sharpe_ratio: 1.2,
      max_drawdown: -3.5,
      open_positions: 5,
      total_trades: 50,
      alpha: 2.3,
      config: { id: 'c1', is_active: true },
    };
    mockFrom.mockReturnValue(singleChain(mockState));

    const { result } = renderHook(() => useReferencePortfolioState(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockFrom).toHaveBeenCalledWith('reference_portfolio_state');
    expect(result.current.data?.portfolio_value).toBe(100000);
    expect(result.current.data?.config?.is_active).toBe(true);
  });

  it('handles error', async () => {
    const errorHandler: ProxyHandler<object> = {
      get(_target, prop: string) {
        if (prop === 'single')
          return vi.fn().mockResolvedValue({ data: null, error: { message: 'Not found' } });
        return vi.fn().mockReturnValue(new Proxy({}, errorHandler));
      },
    };
    mockFrom.mockReturnValue(new Proxy({}, errorHandler));

    const { result } = renderHook(() => useReferencePortfolioState(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useReferencePortfolioPositions()', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches open positions by default', async () => {
    const mockPositions = [
      { id: 'pos1', ticker: 'AAPL', quantity: 10, is_open: true, unrealized_pl: 500 },
      { id: 'pos2', ticker: 'MSFT', quantity: 5, is_open: true, unrealized_pl: -100 },
    ];
    mockFrom.mockReturnValue(tableChain(mockPositions));

    const { result } = renderHook(() => useReferencePortfolioPositions(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockFrom).toHaveBeenCalledWith('reference_portfolio_positions');
    expect(result.current.data).toHaveLength(2);
  });

  it('returns empty array on null data', async () => {
    mockFrom.mockReturnValue(tableChain(null));

    const { result } = renderHook(() => useReferencePortfolioPositions(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([]);
  });
});

describe('useReferencePortfolioTrades()', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches trades with pagination', async () => {
    const mockTrades = [
      { id: 'tx1', ticker: 'AAPL', transaction_type: 'buy', quantity: 10, price: 150 },
    ];
    const terminal = { data: mockTrades, error: null, count: 42 };
    const handler: ProxyHandler<object> = {
      get(_target, prop: string) {
        if (prop === 'then')
          return (resolve: (v: unknown) => void) => Promise.resolve(terminal).then(resolve);
        return vi.fn().mockReturnValue(new Proxy({}, handler));
      },
    };
    mockFrom.mockReturnValue(new Proxy({}, handler));

    const { result } = renderHook(() => useReferencePortfolioTrades(10, 0), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockFrom).toHaveBeenCalledWith('reference_portfolio_transactions');
    expect(result.current.data?.trades).toHaveLength(1);
    expect(result.current.data?.total).toBe(42);
  });
});

describe('useReferencePortfolioPerformance()', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches performance snapshots from edge function', async () => {
    const mockSnapshots = [
      { id: 'snap1', snapshot_date: '2025-01-15', portfolio_value: 100000 },
      { id: 'snap2', snapshot_date: '2025-01-16', portfolio_value: 101000 },
    ];
    mockFunctionsInvoke.mockResolvedValue({
      data: { success: true, snapshots: mockSnapshots },
      error: null,
    });

    const { result } = renderHook(() => useReferencePortfolioPerformance('1w'), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockFunctionsInvoke).toHaveBeenCalledWith('reference-portfolio', {
      body: { action: 'get-performance', timeframe: '1w' },
    });
    expect(result.current.data).toHaveLength(2);
  });

  it('throws on unsuccessful response', async () => {
    mockFunctionsInvoke.mockResolvedValue({
      data: { success: false, error: 'No data available' },
      error: null,
    });

    const { result } = renderHook(() => useReferencePortfolioPerformance(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('useReferencePortfolioConfig()', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches portfolio config', async () => {
    const mockConfig = {
      id: 'c1', name: 'Main', initial_capital: 100000, is_active: true,
    };
    mockFrom.mockReturnValue(singleChain(mockConfig));

    const { result } = renderHook(() => useReferencePortfolioConfig(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockFrom).toHaveBeenCalledWith('reference_portfolio_config');
    expect(result.current.data?.is_active).toBe(true);
  });
});

describe('useMarketStatus()', () => {
  beforeEach(() => vi.clearAllMocks());

  it('returns market status', async () => {
    const { result } = renderHook(() => useMarketStatus(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveProperty('isOpen');
    expect(typeof result.current.data?.isOpen).toBe('boolean');
  });
});

describe('useReferencePortfolioSummary()', () => {
  beforeEach(() => vi.clearAllMocks());

  it('computes summary from portfolio state', async () => {
    const mockState = {
      id: 's1', portfolio_value: 105000, total_return: 5000, total_return_pct: 5.0,
      day_return: 200, day_return_pct: 0.2, win_rate: 0.65, sharpe_ratio: 1.2,
      max_drawdown: -3.5, open_positions: 5, total_trades: 50, alpha: 2.3,
      config: { id: 'c1', is_active: true },
    };
    mockFrom.mockReturnValue(singleChain(mockState));

    const { result } = renderHook(() => useReferencePortfolioSummary(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.summary?.portfolioValue).toBe(105000);
    expect(result.current.summary?.totalReturnPct).toBe(5.0);
    expect(result.current.summary?.isActive).toBe(true);
    expect(result.current.summary?.alpha).toBe(2.3);
  });

  it('returns null summary when no state', async () => {
    mockFrom.mockReturnValue(singleChain(null));

    const { result } = renderHook(() => useReferencePortfolioSummary(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.summary).toBeNull();
  });
});
