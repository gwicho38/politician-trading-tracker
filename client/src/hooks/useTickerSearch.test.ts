/**
 * Tests for hooks/useTickerSearch.ts
 *
 * Tests:
 * - useTickerSearch() - Ticker search autocomplete
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

import { useTickerSearch } from './useTickerSearch';
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

describe('useTickerSearch()', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns empty array for empty query', async () => {
    const { result } = renderHook(() => useTickerSearch(''), {
      wrapper: createWrapper(),
    });

    // Query should not be enabled for empty string
    expect(result.current.data).toBeUndefined();
    expect(result.current.isFetching).toBe(false);
  });

  it('is disabled when enabled=false', () => {
    const { result } = renderHook(() => useTickerSearch('AAPL', false), {
      wrapper: createWrapper(),
    });

    expect(result.current.isFetching).toBe(false);
  });

  it('searches for tickers with valid query', async () => {
    const mockData = [
      { ticker: 'AAPL', name: 'Apple Inc.', trade_count: 150 },
      { ticker: 'AAPD', name: 'Direxion Daily AAPL', trade_count: 10 },
    ];

    const mockSelect = vi.fn().mockReturnValue({
      ilike: vi.fn().mockReturnValue({
        order: vi.fn().mockReturnValue({
          limit: vi.fn().mockResolvedValue({ data: mockData, error: null }),
        }),
      }),
    });

    (supabasePublic.from as ReturnType<typeof vi.fn>).mockReturnValue({
      select: mockSelect,
    });

    const { result } = renderHook(() => useTickerSearch('AAP'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(2);
    expect(result.current.data?.[0].ticker).toBe('AAPL');
    expect(result.current.data?.[0].tradeCount).toBe(150);
  });

  it('converts query to uppercase', async () => {
    const mockSelect = vi.fn().mockReturnValue({
      ilike: vi.fn().mockReturnValue({
        order: vi.fn().mockReturnValue({
          limit: vi.fn().mockResolvedValue({ data: [], error: null }),
        }),
      }),
    });

    (supabasePublic.from as ReturnType<typeof vi.fn>).mockReturnValue({
      select: mockSelect,
    });

    renderHook(() => useTickerSearch('aapl'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(mockSelect).toHaveBeenCalled();
    });

    // The ilike should be called with uppercase pattern
    const ilikeMock = mockSelect.mock.results[0].value.ilike;
    expect(ilikeMock).toHaveBeenCalledWith('ticker', 'AAPL%');
  });

  it('falls back to trading_disclosures when top_tickers is empty', async () => {
    const mockDisclosureData = [
      { asset_ticker: 'RARE', asset_name: 'Rare Stock' },
    ];

    // First call returns empty (top_tickers)
    const mockTopTickers = {
      select: vi.fn().mockReturnValue({
        ilike: vi.fn().mockReturnValue({
          order: vi.fn().mockReturnValue({
            limit: vi.fn().mockResolvedValue({ data: [], error: null }),
          }),
        }),
      }),
    };

    // Second call returns data (trading_disclosures)
    const mockDisclosures = {
      select: vi.fn().mockReturnValue({
        ilike: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            limit: vi.fn().mockResolvedValue({ data: mockDisclosureData, error: null }),
          }),
        }),
      }),
    };

    let callCount = 0;
    (supabasePublic.from as ReturnType<typeof vi.fn>).mockImplementation((table: string) => {
      callCount++;
      if (table === 'top_tickers') return mockTopTickers;
      return mockDisclosures;
    });

    const { result } = renderHook(() => useTickerSearch('RARE'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0].ticker).toBe('RARE');
    expect(result.current.data?.[0].tradeCount).toBe(0);
  });

  it('limits results to 8', async () => {
    const mockData = Array.from({ length: 15 }, (_, i) => ({
      ticker: `TKR${i}`,
      name: `Ticker ${i}`,
      trade_count: 100 - i,
    }));

    const mockSelect = vi.fn().mockReturnValue({
      ilike: vi.fn().mockReturnValue({
        order: vi.fn().mockReturnValue({
          limit: vi.fn().mockResolvedValue({ data: mockData.slice(0, 8), error: null }),
        }),
      }),
    });

    (supabasePublic.from as ReturnType<typeof vi.fn>).mockReturnValue({
      select: mockSelect,
    });

    const { result } = renderHook(() => useTickerSearch('TKR'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.length).toBeLessThanOrEqual(8);
  });

  it('deduplicates tickers from disclosures', async () => {
    const mockDisclosureData = [
      { asset_ticker: 'DUP', asset_name: 'Duplicate Stock' },
      { asset_ticker: 'dup', asset_name: 'Duplicate Stock Lowercase' },
      { asset_ticker: 'DUP', asset_name: 'Same Ticker Again' },
    ];

    const mockTopTickers = {
      select: vi.fn().mockReturnValue({
        ilike: vi.fn().mockReturnValue({
          order: vi.fn().mockReturnValue({
            limit: vi.fn().mockResolvedValue({ data: [], error: null }),
          }),
        }),
      }),
    };

    const mockDisclosures = {
      select: vi.fn().mockReturnValue({
        ilike: vi.fn().mockReturnValue({
          eq: vi.fn().mockReturnValue({
            limit: vi.fn().mockResolvedValue({ data: mockDisclosureData, error: null }),
          }),
        }),
      }),
    };

    (supabasePublic.from as ReturnType<typeof vi.fn>).mockImplementation((table: string) => {
      if (table === 'top_tickers') return mockTopTickers;
      return mockDisclosures;
    });

    const { result } = renderHook(() => useTickerSearch('DUP'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Should only have 1 result after deduplication
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0].ticker).toBe('DUP');
  });
});
