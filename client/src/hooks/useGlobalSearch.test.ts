/**
 * Tests for hooks/useGlobalSearch.ts
 *
 * Tests:
 * - useGlobalSearch() - Global search across politicians and tickers
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock Supabase client
vi.mock('@/integrations/supabase/client', () => ({
  supabasePublic: {
    from: vi.fn(),
  },
}));

import { useGlobalSearch } from './useGlobalSearch';
import { supabasePublic } from '@/integrations/supabase/client';

// Create wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

// Helper to create politician mock chain: .select().eq().or().order().limit()
const createPoliticianMock = (data: unknown[]) => ({
  select: vi.fn().mockReturnValue({
    eq: vi.fn().mockReturnValue({
      or: vi.fn().mockReturnValue({
        order: vi.fn().mockReturnValue({
          limit: vi.fn().mockResolvedValue({ data, error: null }),
        }),
      }),
    }),
  }),
});

// Helper to create ticker mock chain: .select().ilike().order().limit()
const createTickerMock = (data: unknown[]) => ({
  select: vi.fn().mockReturnValue({
    ilike: vi.fn().mockReturnValue({
      order: vi.fn().mockReturnValue({
        limit: vi.fn().mockResolvedValue({ data, error: null }),
      }),
    }),
  }),
});

// Helper to create disclosure mock chain: .select().ilike().eq().limit()
const createDisclosureMock = (data: unknown[]) => ({
  select: vi.fn().mockReturnValue({
    ilike: vi.fn().mockReturnValue({
      eq: vi.fn().mockReturnValue({
        limit: vi.fn().mockResolvedValue({ data, error: null }),
      }),
    }),
  }),
});

describe('useGlobalSearch()', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns empty array for empty query', async () => {
    const { result } = renderHook(() => useGlobalSearch(''), {
      wrapper: createWrapper(),
    });

    // Query should not be enabled for empty string
    expect(result.current.data).toBeUndefined();
    expect(result.current.isFetching).toBe(false);
  });

  it('returns empty array for single character query', async () => {
    const { result } = renderHook(() => useGlobalSearch('a'), {
      wrapper: createWrapper(),
    });

    // Query should not be enabled for less than 2 characters
    expect(result.current.data).toBeUndefined();
    expect(result.current.isFetching).toBe(false);
  });

  it('searches for politicians when query is 2+ characters', async () => {
    const mockPoliticians = [
      {
        id: 'p1',
        first_name: 'John',
        last_name: 'Smith',
        full_name: 'John Smith',
        party: 'D',
        role: 'Senator',
        total_trades: 42,
      },
    ];

    (supabasePublic.from as ReturnType<typeof vi.fn>).mockImplementation((table: string) => {
      if (table === 'politicians') return createPoliticianMock(mockPoliticians);
      if (table === 'top_tickers') return createTickerMock([]);
      if (table === 'trading_disclosures') return createDisclosureMock([]);
      return { select: vi.fn() };
    });

    const { result } = renderHook(() => useGlobalSearch('john'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0].type).toBe('politician');
    expect(result.current.data?.[0].label).toBe('John Smith');
    expect(result.current.data?.[0].meta?.party).toBe('D');
    expect(result.current.data?.[0].meta?.tradeCount).toBe(42);
  });

  it('searches for tickers and returns them with results', async () => {
    const mockTickers = [
      { ticker: 'AAPL', name: 'Apple Inc.', trade_count: 150 },
      { ticker: 'AMZN', name: 'Amazon.com Inc.', trade_count: 120 },
    ];

    (supabasePublic.from as ReturnType<typeof vi.fn>).mockImplementation((table: string) => {
      if (table === 'politicians') return createPoliticianMock([]);
      if (table === 'top_tickers') return createTickerMock(mockTickers);
      return { select: vi.fn() };
    });

    const { result } = renderHook(() => useGlobalSearch('AA'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(2);
    expect(result.current.data?.[0].type).toBe('ticker');
    expect(result.current.data?.[0].label).toBe('AAPL');
    expect(result.current.data?.[0].sublabel).toBe('Apple Inc.');
  });

  it('combines politician and ticker results', async () => {
    const mockPoliticians = [
      {
        id: 'p1',
        first_name: 'Apple',
        last_name: 'Jones',
        full_name: 'Apple Jones',
        party: 'R',
        role: 'Representative',
        total_trades: 10,
      },
    ];

    const mockTickers = [
      { ticker: 'AAPL', name: 'Apple Inc.', trade_count: 150 },
    ];

    (supabasePublic.from as ReturnType<typeof vi.fn>).mockImplementation((table: string) => {
      if (table === 'politicians') return createPoliticianMock(mockPoliticians);
      if (table === 'top_tickers') return createTickerMock(mockTickers);
      return { select: vi.fn() };
    });

    const { result } = renderHook(() => useGlobalSearch('Apple'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Should have both politician and ticker results
    expect(result.current.data).toHaveLength(2);
    const types = result.current.data?.map(r => r.type);
    expect(types).toContain('politician');
    expect(types).toContain('ticker');
  });

  it('falls back to trading_disclosures when top_tickers returns empty', async () => {
    const mockDisclosures = [
      { asset_ticker: 'RARE', asset_name: 'Rare Company' },
      { asset_ticker: 'rare', asset_name: 'Rare Lowercase' },
    ];

    (supabasePublic.from as ReturnType<typeof vi.fn>).mockImplementation((table: string) => {
      if (table === 'politicians') return createPoliticianMock([]);
      if (table === 'top_tickers') return createTickerMock([]);
      if (table === 'trading_disclosures') return createDisclosureMock(mockDisclosures);
      return { select: vi.fn() };
    });

    const { result } = renderHook(() => useGlobalSearch('rare'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Should deduplicate tickers (RARE and rare are the same)
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0].type).toBe('ticker');
    expect(result.current.data?.[0].label).toBe('RARE');
  });

  it('constructs correct politician label with fallback', async () => {
    const mockPoliticians = [
      {
        id: 'p1',
        first_name: 'Jane',
        last_name: 'Doe',
        full_name: null,
        party: 'I',
        role: null,
        total_trades: 5,
      },
    ];

    (supabasePublic.from as ReturnType<typeof vi.fn>).mockImplementation((table: string) => {
      if (table === 'politicians') return createPoliticianMock(mockPoliticians);
      if (table === 'top_tickers') return createTickerMock([]);
      if (table === 'trading_disclosures') return createDisclosureMock([]);
      return { select: vi.fn() };
    });

    const { result } = renderHook(() => useGlobalSearch('Jane'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Should construct label from first_name + last_name when full_name is null
    expect(result.current.data?.[0].label).toBe('Jane Doe');
    // Should use 'Member' as default when role is null
    expect(result.current.data?.[0].sublabel).toBe('Member');
  });

  it('handles null ticker names gracefully', async () => {
    const mockTickers = [
      { ticker: 'XYZ', name: null, trade_count: 50 },
    ];

    (supabasePublic.from as ReturnType<typeof vi.fn>).mockImplementation((table: string) => {
      if (table === 'politicians') return createPoliticianMock([]);
      if (table === 'top_tickers') return createTickerMock(mockTickers);
      return { select: vi.fn() };
    });

    const { result } = renderHook(() => useGlobalSearch('XYZ'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.[0].sublabel).toBeUndefined();
  });

  it('limits politicians to 5 results', async () => {
    const mockPoliticians = Array.from({ length: 5 }, (_, i) => ({
      id: `p${i}`,
      first_name: 'Test',
      last_name: `Person${i}`,
      full_name: `Test Person${i}`,
      party: 'D',
      role: 'Senator',
      total_trades: 100 - i,
    }));

    (supabasePublic.from as ReturnType<typeof vi.fn>).mockImplementation((table: string) => {
      if (table === 'politicians') return createPoliticianMock(mockPoliticians);
      if (table === 'top_tickers') return createTickerMock([]);
      if (table === 'trading_disclosures') return createDisclosureMock([]);
      return { select: vi.fn() };
    });

    const { result } = renderHook(() => useGlobalSearch('Test'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Should have at most 5 politician results
    const politicianResults = result.current.data?.filter(r => r.type === 'politician');
    expect(politicianResults?.length).toBeLessThanOrEqual(5);
  });

  it('limits tickers to 5 results', async () => {
    const mockTickers = Array.from({ length: 5 }, (_, i) => ({
      ticker: `TKR${i}`,
      name: `Ticker ${i} Inc.`,
      trade_count: 100 - i,
    }));

    (supabasePublic.from as ReturnType<typeof vi.fn>).mockImplementation((table: string) => {
      if (table === 'politicians') return createPoliticianMock([]);
      if (table === 'top_tickers') return createTickerMock(mockTickers);
      return { select: vi.fn() };
    });

    const { result } = renderHook(() => useGlobalSearch('TKR'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Should have at most 5 ticker results
    const tickerResults = result.current.data?.filter(r => r.type === 'ticker');
    expect(tickerResults?.length).toBeLessThanOrEqual(5);
  });

  it('trims whitespace from query', async () => {
    const mockPoliticians = [
      {
        id: 'p1',
        first_name: 'Test',
        last_name: 'Trim',
        full_name: 'Test Trim',
        party: 'D',
        role: 'Senator',
        total_trades: 1,
      },
    ];

    (supabasePublic.from as ReturnType<typeof vi.fn>).mockImplementation((table: string) => {
      if (table === 'politicians') return createPoliticianMock(mockPoliticians);
      if (table === 'top_tickers') return createTickerMock([]);
      if (table === 'trading_disclosures') return createDisclosureMock([]);
      return { select: vi.fn() };
    });

    const { result } = renderHook(() => useGlobalSearch('  test  '), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Should still find results with trimmed query
    expect(result.current.data?.length).toBeGreaterThan(0);
  });

  it('uses 30 second stale time for caching', async () => {
    (supabasePublic.from as ReturnType<typeof vi.fn>).mockImplementation((table: string) => {
      if (table === 'politicians') return createPoliticianMock([]);
      if (table === 'top_tickers') return createTickerMock([]);
      if (table === 'trading_disclosures') return createDisclosureMock([]);
      return { select: vi.fn() };
    });

    const { result } = renderHook(() => useGlobalSearch('test'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Check that the query was not immediately refetched
    // (stale time prevents refetch)
    expect(result.current.isStale).toBe(false);
  });

  it('handles empty disclosure ticker gracefully', async () => {
    const mockDisclosures = [
      { asset_ticker: null, asset_name: 'No Ticker' },
      { asset_ticker: 'VALID', asset_name: 'Valid Ticker' },
    ];

    (supabasePublic.from as ReturnType<typeof vi.fn>).mockImplementation((table: string) => {
      if (table === 'politicians') return createPoliticianMock([]);
      if (table === 'top_tickers') return createTickerMock([]);
      if (table === 'trading_disclosures') return createDisclosureMock(mockDisclosures);
      return { select: vi.fn() };
    });

    const { result } = renderHook(() => useGlobalSearch('test'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Should only include VALID ticker, not the null one
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0].label).toBe('VALID');
  });
});
