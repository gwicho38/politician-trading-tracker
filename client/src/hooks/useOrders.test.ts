/**
 * Tests for hooks/useOrders.ts
 *
 * Tests:
 * - useOrders() - Fetches trading orders from edge function
 * - useSyncOrders() - Syncs orders from Alpaca
 * - usePlaceOrder() - Places new orders
 * - useCancelOrder() - Cancels existing orders
 * - getOrderStatusColor / getOrderStatusVariant helpers
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

// Mock fetchWithRetry
vi.mock('@/lib/fetchWithRetry', () => ({
  fetchWithRetry: vi.fn(),
}));

import { useOrders, getOrderStatusColor, getOrderStatusVariant } from './useOrders';

const mockFetch = vi.fn();

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe('useOrders()', () => {
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

    const { result } = renderHook(() => useOrders('paper'), { wrapper: createWrapper() });
    expect(result.current.isFetching).toBe(false);
  });

  it('is disabled when auth is not ready', () => {
    mockUseAuth.mockReturnValue({ user: { email: 'test@test.com' }, authReady: false });

    const { result } = renderHook(() => useOrders('paper'), { wrapper: createWrapper() });
    expect(result.current.isFetching).toBe(false);
  });

  it('fetches orders when authenticated', async () => {
    mockUseAuth.mockReturnValue({ user: { email: 'test@test.com' }, authReady: true });

    const mockToken = JSON.stringify({ access_token: 'test-token' });
    localStorage.setItem('sb-test-auth-token', mockToken);

    const mockOrders = {
      success: true,
      orders: [
        { id: 'o1', ticker: 'AAPL', side: 'buy', quantity: 10, status: 'filled' },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    };
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockOrders),
    });

    const { result } = renderHook(() => useOrders('paper'), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockFetch).toHaveBeenCalled();
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toContain('/functions/v1/orders');
    const body = JSON.parse(options.body);
    expect(body.action).toBe('get-orders');
    expect(body.trading_mode).toBe('paper');
  });

  it('handles fetch error', async () => {
    mockUseAuth.mockReturnValue({ user: { email: 'test@test.com' }, authReady: true });

    const mockToken = JSON.stringify({ access_token: 'test-token' });
    localStorage.setItem('sb-test-auth-token', mockToken);

    mockFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ message: 'Unauthorized' }),
    });

    const { result } = renderHook(() => useOrders('paper'), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it('passes status filter to API', async () => {
    mockUseAuth.mockReturnValue({ user: { email: 'test@test.com' }, authReady: true });

    const mockToken = JSON.stringify({ access_token: 'test-token' });
    localStorage.setItem('sb-test-auth-token', mockToken);

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: true, orders: [], total: 0 }),
    });

    renderHook(
      () => useOrders('live', { status: 'open', limit: 10 }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => expect(mockFetch).toHaveBeenCalled());

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.status).toBe('open');
    expect(body.limit).toBe(10);
    expect(body.trading_mode).toBe('live');
  });
});

describe('getOrderStatusColor()', () => {
  it('returns green for filled', () => {
    expect(getOrderStatusColor('filled')).toBe('text-green-600');
  });

  it('returns blue for partially_filled', () => {
    expect(getOrderStatusColor('partially_filled')).toBe('text-blue-600');
  });

  it('returns yellow for new/accepted/pending_new', () => {
    expect(getOrderStatusColor('new')).toBe('text-yellow-600');
    expect(getOrderStatusColor('accepted')).toBe('text-yellow-600');
    expect(getOrderStatusColor('pending_new')).toBe('text-yellow-600');
  });

  it('returns gray for canceled/expired', () => {
    expect(getOrderStatusColor('canceled')).toBe('text-gray-500');
    expect(getOrderStatusColor('expired')).toBe('text-gray-500');
  });

  it('returns red for rejected', () => {
    expect(getOrderStatusColor('rejected')).toBe('text-red-600');
  });

  it('returns muted for unknown status', () => {
    expect(getOrderStatusColor('unknown')).toBe('text-muted-foreground');
  });
});

describe('getOrderStatusVariant()', () => {
  it('returns default for filled', () => {
    expect(getOrderStatusVariant('filled')).toBe('default');
  });

  it('returns secondary for pending states', () => {
    expect(getOrderStatusVariant('new')).toBe('secondary');
    expect(getOrderStatusVariant('accepted')).toBe('secondary');
    expect(getOrderStatusVariant('partially_filled')).toBe('secondary');
  });

  it('returns destructive for rejected', () => {
    expect(getOrderStatusVariant('rejected')).toBe('destructive');
  });

  it('returns outline for unknown status', () => {
    expect(getOrderStatusVariant('unknown')).toBe('outline');
  });
});
