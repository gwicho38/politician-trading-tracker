/**
 * Tests for hooks/useAlpacaAccount.ts and useAlpacaPositions.ts
 *
 * Tests:
 * - useAlpacaAccount() - Fetches Alpaca account data from edge function
 * - calculateDailyPnL() - Daily P&L calculation helper
 * - useAlpacaPositions() - Fetches Alpaca positions from edge function
 * - calculatePositionMetrics() - Position metrics calculation helper
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock environment variables
vi.stubEnv('VITE_SUPABASE_URL', 'https://test.supabase.co');
vi.stubEnv('VITE_SUPABASE_PUBLISHABLE_KEY', 'test-anon-key');

// Mock useAuth
const mockUseAuth = vi.fn();
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => mockUseAuth(),
}));

// Mock Supabase client
vi.mock('@/integrations/supabase/client', () => ({
  supabase: { from: vi.fn() },
  supabasePublic: { from: vi.fn() },
}));

// Mock logger
vi.mock('@/lib/logger', () => ({
  logError: vi.fn(),
}));

import { useAlpacaAccount, calculateDailyPnL } from './useAlpacaAccount';
import { useAlpacaPositions, calculatePositionMetrics } from './useAlpacaPositions';

const mockFetch = vi.fn();

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe('useAlpacaAccount()', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = mockFetch;
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('is disabled when user is null', () => {
    mockUseAuth.mockReturnValue({ user: null, authReady: true });

    const { result } = renderHook(() => useAlpacaAccount('paper'), { wrapper: createWrapper() });
    expect(result.current.isFetching).toBe(false);
  });

  it('is disabled when auth is not ready', () => {
    mockUseAuth.mockReturnValue({ user: { email: 'test@test.com' }, authReady: false });

    const { result } = renderHook(() => useAlpacaAccount('paper'), { wrapper: createWrapper() });
    expect(result.current.isFetching).toBe(false);
  });

  it('fetches account data when authenticated', async () => {
    mockUseAuth.mockReturnValue({ user: { email: 'test@test.com' }, authReady: true });

    const mockToken = JSON.stringify({ access_token: 'test-token' });
    localStorage.setItem('sb-test-auth-token', mockToken);

    const mockAccount = {
      success: true,
      account: {
        portfolio_value: 100000,
        cash: 25000,
        equity: 100000,
        last_equity: 99000,
        status: 'ACTIVE',
      },
    };
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockAccount),
    });

    const { result } = renderHook(() => useAlpacaAccount('paper'), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.portfolio_value).toBe(100000);

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toContain('/functions/v1/alpaca-account');
    const body = JSON.parse(options.body);
    expect(body.action).toBe('get-account');
    expect(body.tradingMode).toBe('paper');
  });

  it('returns null when no credentials configured', async () => {
    mockUseAuth.mockReturnValue({ user: { email: 'test@test.com' }, authReady: true });

    const mockToken = JSON.stringify({ access_token: 'test-token' });
    localStorage.setItem('sb-test-auth-token', mockToken);

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        success: false,
        error: 'No Alpaca credentials found',
      }),
    });

    const { result } = renderHook(() => useAlpacaAccount('paper'), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBeNull();
  });

  it('throws on non-credential errors', async () => {
    mockUseAuth.mockReturnValue({ user: { email: 'test@test.com' }, authReady: true });

    const mockToken = JSON.stringify({ access_token: 'test-token' });
    localStorage.setItem('sb-test-auth-token', mockToken);

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: false, error: 'Server error' }),
    });

    const { result } = renderHook(() => useAlpacaAccount('paper'), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
  });
});

describe('calculateDailyPnL()', () => {
  it('returns zero for null account', () => {
    expect(calculateDailyPnL(null)).toEqual({ value: 0, percent: 0 });
  });

  it('calculates positive P&L', () => {
    const account = { equity: 105000, last_equity: 100000 } as Parameters<typeof calculateDailyPnL>[0];
    const result = calculateDailyPnL(account);
    expect(result.value).toBe(5000);
    expect(result.percent).toBeCloseTo(5.0);
  });

  it('calculates negative P&L', () => {
    const account = { equity: 95000, last_equity: 100000 } as Parameters<typeof calculateDailyPnL>[0];
    const result = calculateDailyPnL(account);
    expect(result.value).toBe(-5000);
    expect(result.percent).toBeCloseTo(-5.0);
  });

  it('handles zero last_equity', () => {
    const account = { equity: 1000, last_equity: 0 } as Parameters<typeof calculateDailyPnL>[0];
    const result = calculateDailyPnL(account);
    expect(result.percent).toBe(0);
  });

  it('handles string values', () => {
    const account = { equity: '105000', last_equity: '100000' } as unknown as Parameters<typeof calculateDailyPnL>[0];
    const result = calculateDailyPnL(account);
    expect(result.value).toBe(5000);
  });
});

describe('useAlpacaPositions()', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = mockFetch;
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('is disabled when user is null', () => {
    mockUseAuth.mockReturnValue({ user: null, authReady: true });

    const { result } = renderHook(() => useAlpacaPositions('paper'), { wrapper: createWrapper() });
    expect(result.current.isFetching).toBe(false);
  });

  it('fetches positions when authenticated', async () => {
    mockUseAuth.mockReturnValue({ user: { email: 'test@test.com' }, authReady: true });

    const mockToken = JSON.stringify({ access_token: 'test-token' });
    localStorage.setItem('sb-test-auth-token', mockToken);

    const mockPositions = {
      success: true,
      positions: [
        { symbol: 'AAPL', qty: 10, market_value: 1500, unrealized_pl: 200 },
        { symbol: 'MSFT', qty: 5, market_value: 2000, unrealized_pl: -50 },
      ],
    };
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockPositions),
    });

    const { result } = renderHook(() => useAlpacaPositions('paper'), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(2);
  });

  it('returns empty array when no credentials', async () => {
    mockUseAuth.mockReturnValue({ user: { email: 'test@test.com' }, authReady: true });

    const mockToken = JSON.stringify({ access_token: 'test-token' });
    localStorage.setItem('sb-test-auth-token', mockToken);

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        success: false,
        error: 'No Alpaca credentials found',
      }),
    });

    const { result } = renderHook(() => useAlpacaPositions('paper'), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([]);
  });
});

describe('calculatePositionMetrics()', () => {
  it('calculates aggregate metrics', () => {
    const positions = [
      { market_value: 5000, cost_basis: 4500, unrealized_pl: 500, unrealized_intraday_pl: 50 },
      { market_value: 3000, cost_basis: 3200, unrealized_pl: -200, unrealized_intraday_pl: -30 },
    ] as Parameters<typeof calculatePositionMetrics>[0];

    const result = calculatePositionMetrics(positions);
    expect(result.totalValue).toBe(8000);
    expect(result.totalCost).toBe(7700);
    expect(result.totalPnL).toBe(300);
    expect(result.totalIntradayPnL).toBe(20);
    expect(result.positionCount).toBe(2);
  });

  it('returns zeros for empty array', () => {
    const result = calculatePositionMetrics([]);
    expect(result.totalValue).toBe(0);
    expect(result.positionCount).toBe(0);
  });
});
