/**
 * Tests for hooks/useSupabaseData.ts
 *
 * Tests all network-dependent hooks:
 * - useJurisdictions, usePoliticians, useTrades, useTradingDisclosures
 * - useChartData, useChartYears, useTopTickers, useDashboardStats
 * - usePoliticianDetail, useTickerDetail, useMonthDetail
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock Supabase client
const mockFrom = vi.fn();
vi.mock('@/integrations/supabase/client', () => ({
  supabasePublic: { from: (...args: unknown[]) => mockFrom(...args) },
  supabase: { from: (...args: unknown[]) => mockFrom(...args) },
}));

import {
  useJurisdictions,
  usePoliticians,
  useTrades,
  useTradingDisclosures,
  useChartData,
  useChartYears,
  useTopTickers,
  useDashboardStats,
  usePoliticianDetail,
  useTickerDetail,
  useMonthDetail,
} from './useSupabaseData';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

// Helper to build chainable mock returning data
function chainMock(data: unknown, opts?: { count?: number }) {
  const terminal = {
    data,
    error: null,
    count: opts?.count ?? null,
  };
  const chain: Record<string, ReturnType<typeof vi.fn>> = {};
  // Each method returns `chain` so chaining works in any order,
  // except terminal methods return the resolved value.
  const terminalFn = vi.fn().mockResolvedValue(terminal);
  const self = () =>
    new Proxy(
      {},
      {
        get(_target, prop: string) {
          if (['maybeSingle', 'single'].includes(prop)) return terminalFn;
          if (!chain[prop]) {
            chain[prop] = vi.fn().mockReturnValue(self());
          }
          return chain[prop];
        },
      },
    );

  // The outer select also needs to resolve when awaited
  const root = self();
  // Make the root promise-like so `const { data } = await query` works
  (root as Record<string, unknown>).then = (resolve: (val: unknown) => void) =>
    Promise.resolve(terminal).then(resolve);
  return root;
}

// Simpler helper for terminal-chain patterns
function tableChain(data: unknown, opts?: { count?: number }) {
  const terminal = { data, error: null, count: opts?.count ?? null };
  const handler: ProxyHandler<object> = {
    get(_target, prop: string) {
      if (prop === 'then') {
        return (resolve: (v: unknown) => void) => Promise.resolve(terminal).then(resolve);
      }
      return vi.fn().mockReturnValue(new Proxy({}, handler));
    },
  };
  return new Proxy({}, handler);
}

describe('useJurisdictions()', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches jurisdictions ordered by name', async () => {
    const mockData = [
      { id: '1', code: 'us', name: 'United States', flag: 'US' },
      { id: '2', code: 'uk', name: 'United Kingdom', flag: 'GB' },
    ];
    mockFrom.mockReturnValue(tableChain(mockData));

    const { result } = renderHook(() => useJurisdictions(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockFrom).toHaveBeenCalledWith('jurisdictions');
    expect(result.current.data).toHaveLength(2);
    expect(result.current.data?.[0].code).toBe('us');
  });

  it('throws on Supabase error', async () => {
    const errorTerminal = { data: null, error: { message: 'DB error' }, count: null };
    const handler: ProxyHandler<object> = {
      get(_target, prop: string) {
        if (prop === 'then')
          return (resolve: (v: unknown) => void) => Promise.resolve(errorTerminal).then(resolve);
        return vi.fn().mockReturnValue(new Proxy({}, handler));
      },
    };
    mockFrom.mockReturnValue(new Proxy({}, handler));

    const { result } = renderHook(() => useJurisdictions(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe('usePoliticians()', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches all politicians when no jurisdiction specified', async () => {
    const mockData = [
      {
        id: 'p1', first_name: 'John', last_name: 'Doe', full_name: 'John Doe',
        party: 'D', role: 'Senator', state_or_country: 'NY', district: null,
        total_volume: 100000,
      },
    ];
    mockFrom.mockReturnValue(tableChain(mockData));

    const { result } = renderHook(() => usePoliticians(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockFrom).toHaveBeenCalledWith('politicians');
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0].name).toBe('John Doe');
    expect(result.current.data?.[0].chamber).toBe('Senator');
  });

  it('transforms politician data with fallback name', async () => {
    const mockData = [
      {
        id: 'p2', first_name: 'Jane', last_name: 'Smith', full_name: null,
        party: null, role: null, state_or_country: null, state: null, district: 'CA-12',
        total_volume: 50000,
      },
    ];
    mockFrom.mockReturnValue(tableChain(mockData));

    const { result } = renderHook(() => usePoliticians(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.[0].name).toBe('Jane Smith');
    expect(result.current.data?.[0].chamber).toBe('Unknown');
    expect(result.current.data?.[0].party).toBe('Unknown');
  });

  it('maps jurisdiction_id from role correctly', async () => {
    const mockData = [
      { id: 'p1', full_name: 'MEP User', role: 'MEP', party: 'EPP', state_or_country: null, first_name: 'M', last_name: 'U', total_volume: 0, district: null },
    ];
    mockFrom.mockReturnValue(tableChain(mockData));

    const { result } = renderHook(() => usePoliticians(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.[0].jurisdiction_id).toBe('eu_parliament');
  });
});

describe('useTrades()', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches recent trades with politician join', async () => {
    const mockData = [
      {
        id: 't1', asset_ticker: 'AAPL', asset_name: 'Apple Inc.',
        transaction_type: 'purchase', amount_range_min: 1000, amount_range_max: 15000,
        disclosure_date: '2025-01-15', status: 'active',
        politician: {
          id: 'p1', full_name: 'John Doe', first_name: 'John', last_name: 'Doe',
          party: 'D', role: 'Senator', state_or_country: 'NY',
        },
      },
    ];
    mockFrom.mockReturnValue(tableChain(mockData));

    const { result } = renderHook(() => useTrades(10), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockFrom).toHaveBeenCalledWith('trading_disclosures');
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0].ticker).toBe('AAPL');
    expect(result.current.data?.[0].trade_type).toBe('buy');
    expect(result.current.data?.[0].estimated_value).toBe(8000);
  });

  it('maps sale transaction_type to sell', async () => {
    const mockData = [
      {
        id: 't2', asset_ticker: 'MSFT', asset_name: 'Microsoft',
        transaction_type: 'sale', amount_range_min: 0, amount_range_max: 0,
        disclosure_date: '2025-01-10', status: 'active', politician: null,
      },
    ];
    mockFrom.mockReturnValue(tableChain(mockData));

    const { result } = renderHook(() => useTrades(5), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.[0].trade_type).toBe('sell');
  });

  it('handles null politician gracefully', async () => {
    const mockData = [
      {
        id: 't3', asset_ticker: null, asset_name: 'Unknown', transaction_type: 'other',
        amount_range_min: null, amount_range_max: null, disclosure_date: '2025-01-05',
        status: 'active', politician: null,
      },
    ];
    mockFrom.mockReturnValue(tableChain(mockData));

    const { result } = renderHook(() => useTrades(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.[0].ticker).toBe('');
    expect(result.current.data?.[0].politician).toBeUndefined();
  });
});

describe('useTradingDisclosures()', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches disclosures with default options', async () => {
    const mockData = [
      {
        id: 'd1', asset_ticker: 'GOOG', asset_name: 'Alphabet',
        transaction_type: 'purchase', status: 'active',
        politician: { id: 'p1', full_name: 'A B', first_name: 'A', last_name: 'B' },
      },
    ];
    mockFrom.mockReturnValue(tableChain(mockData, { count: 1 }));

    const { result } = renderHook(() => useTradingDisclosures(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.disclosures).toHaveLength(1);
    expect(result.current.data?.total).toBe(1);
  });

  it('pre-queries politicians for jurisdiction filter', async () => {
    // First call: politicians query for pre-filtering
    const politiciansData = [{ id: 'p1' }, { id: 'p2' }];
    // Second call: disclosures query
    const disclosuresData = [
      {
        id: 'd1', asset_ticker: 'AAPL', status: 'active', transaction_type: 'purchase',
        politician: { id: 'p1', full_name: 'Rep User', first_name: 'Rep', last_name: 'User' },
      },
    ];

    let callCount = 0;
    mockFrom.mockImplementation(() => {
      callCount++;
      if (callCount === 1) return tableChain(politiciansData);
      return tableChain(disclosuresData, { count: 1 });
    });

    const { result } = renderHook(
      () => useTradingDisclosures({ jurisdiction: 'us' }),
      { wrapper: createWrapper() },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Should call from('politicians') first, then from('trading_disclosures')
    expect(mockFrom).toHaveBeenCalledWith('politicians');
    expect(mockFrom).toHaveBeenCalledWith('trading_disclosures');
  });

  it('short-circuits when no politicians match jurisdiction', async () => {
    // Politicians query returns empty
    mockFrom.mockReturnValue(tableChain([]));

    const { result } = renderHook(
      () => useTradingDisclosures({ jurisdiction: 'uk' }),
      { wrapper: createWrapper() },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.disclosures).toHaveLength(0);
    expect(result.current.data?.total).toBe(0);
  });

  it('constructs politician name from first_name + last_name fallback', async () => {
    const mockData = [
      {
        id: 'd1', status: 'active', transaction_type: 'purchase',
        politician: { id: 'p1', full_name: null, first_name: 'Jane', last_name: 'Doe' },
      },
    ];
    mockFrom.mockReturnValue(tableChain(mockData, { count: 1 }));

    const { result } = renderHook(() => useTradingDisclosures(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.disclosures[0].politician?.name).toBe('Jane Doe');
  });
});

describe('useChartData()', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches chart data with trailing12 default', async () => {
    const mockData = [
      { id: '1', month: 1, year: 2025, buys: 100, sells: 50, volume: 1000000 },
      { id: '2', month: 2, year: 2025, buys: 120, sells: 60, volume: 1200000 },
    ];
    mockFrom.mockReturnValue(tableChain(mockData));

    const { result } = renderHook(() => useChartData(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockFrom).toHaveBeenCalledWith('chart_data');
    expect(result.current.data).toHaveLength(2);
    expect(result.current.data?.[0].month).toContain("Jan '25");
  });

  it('formats month labels correctly', async () => {
    const mockData = [
      { id: '1', month: 12, year: 2024, buys: 50, sells: 25, volume: 500000 },
    ];
    mockFrom.mockReturnValue(tableChain(mockData));

    const { result } = renderHook(() => useChartData('all'), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.[0].month).toBe("Dec '24");
  });
});

describe('useChartYears()', () => {
  beforeEach(() => vi.clearAllMocks());

  it('returns unique years from chart data', async () => {
    const mockData = [
      { year: 2025 }, { year: 2025 }, { year: 2024 }, { year: 2024 }, { year: 2023 },
    ];
    mockFrom.mockReturnValue(tableChain(mockData));

    const { result } = renderHook(() => useChartYears(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([2025, 2024, 2023]);
  });
});

describe('useTopTickers()', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches top tickers from view', async () => {
    const mockData = [
      { ticker: 'AAPL', name: 'Apple Inc.', trade_count: 200, total_volume: 5000000 },
      { ticker: 'MSFT', name: null, trade_count: 150, total_volume: 3000000 },
    ];
    mockFrom.mockReturnValue(tableChain(mockData));

    const { result } = renderHook(() => useTopTickers(5), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockFrom).toHaveBeenCalledWith('top_tickers');
    expect(result.current.data).toHaveLength(2);
    expect(result.current.data?.[0].ticker).toBe('AAPL');
    expect(result.current.data?.[0].count).toBe(200);
    // Falls back to ticker when name is null
    expect(result.current.data?.[1].name).toBe('MSFT');
  });
});

describe('useDashboardStats()', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches dashboard stats by fixed ID', async () => {
    const mockStats = {
      id: '00000000-0000-0000-0000-000000000001',
      total_trades: 5000, total_volume: 100000000,
      active_politicians: 300, jurisdictions_tracked: 4,
      average_trade_size: 20000, recent_filings: 150,
    };

    // First call returns data via maybeSingle
    const terminal = { data: mockStats, error: null };
    const handler: ProxyHandler<object> = {
      get(_target, prop: string) {
        if (prop === 'maybeSingle') return vi.fn().mockResolvedValue(terminal);
        return vi.fn().mockReturnValue(new Proxy({}, handler));
      },
    };
    mockFrom.mockReturnValue(new Proxy({}, handler));

    const { result } = renderHook(() => useDashboardStats(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockFrom).toHaveBeenCalledWith('dashboard_stats');
    expect(result.current.data?.total_trades).toBe(5000);
  });

  it('falls back to most recent row when fixed ID not found', async () => {
    const mockStats = {
      id: 'other-id', total_trades: 3000, total_volume: 50000000,
    };

    // First maybeSingle returns null, second returns data
    let callCount = 0;
    const handler: ProxyHandler<object> = {
      get(_target, prop: string) {
        if (prop === 'maybeSingle') {
          callCount++;
          if (callCount === 1) return vi.fn().mockResolvedValue({ data: null, error: null });
          return vi.fn().mockResolvedValue({ data: mockStats, error: null });
        }
        return vi.fn().mockReturnValue(new Proxy({}, handler));
      },
    };
    mockFrom.mockReturnValue(new Proxy({}, handler));

    const { result } = renderHook(() => useDashboardStats(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.total_trades).toBe(3000);
  });
});

describe('usePoliticianDetail()', () => {
  beforeEach(() => vi.clearAllMocks());

  it('is disabled when politicianId is null', () => {
    const { result } = renderHook(() => usePoliticianDetail(null), { wrapper: createWrapper() });
    expect(result.current.isFetching).toBe(false);
  });

  it('fetches politician with trade stats', async () => {
    const mockPolitician = {
      id: 'p1', first_name: 'John', last_name: 'Doe', full_name: 'John Doe',
      party: 'D', role: 'Senator', state_or_country: 'NY', district: null,
    };
    const mockTrades = [
      { id: 't1', transaction_type: 'purchase', asset_ticker: 'AAPL', amount_range_min: 1000, amount_range_max: 5000, status: 'active' },
      { id: 't2', transaction_type: 'sale', asset_ticker: 'AAPL', amount_range_min: 2000, amount_range_max: 10000, status: 'active' },
      { id: 't3', transaction_type: 'purchase', asset_ticker: 'MSFT', amount_range_min: null, amount_range_max: null, status: 'active' },
      { id: 't4', transaction_type: 'holding', asset_ticker: 'GOOG', amount_range_min: 500, amount_range_max: 1000, status: 'active' },
      { id: 't5', transaction_type: 'gift', asset_ticker: null, amount_range_min: 0, amount_range_max: 0, status: 'active' },
    ];

    let callCount = 0;
    mockFrom.mockImplementation(() => {
      callCount++;
      if (callCount === 1) {
        // politicians query with .single()
        const singleFn = vi.fn().mockResolvedValue({ data: mockPolitician, error: null });
        const handler: ProxyHandler<object> = {
          get(_target, prop: string) {
            if (prop === 'single') return singleFn;
            return vi.fn().mockReturnValue(new Proxy({}, handler));
          },
        };
        return new Proxy({}, handler);
      }
      // trading_disclosures query
      return tableChain(mockTrades);
    });

    const { result } = renderHook(() => usePoliticianDetail('p1'), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.name).toBe('John Doe');
    expect(result.current.data?.buyCount).toBe(2);
    expect(result.current.data?.sellCount).toBe(1);
    expect(result.current.data?.holdingCount).toBe(1);
    expect(result.current.data?.otherCount).toBe(1); // gift
    expect(result.current.data?.total_trades).toBe(5);
    // Top tickers: AAPL (2 trades), MSFT (1), GOOG (1)
    expect(result.current.data?.topTickers[0].ticker).toBe('AAPL');
    expect(result.current.data?.topTickers[0].count).toBe(2);
  });
});

describe('useTickerDetail()', () => {
  beforeEach(() => vi.clearAllMocks());

  it('is disabled when ticker is null', () => {
    const { result } = renderHook(() => useTickerDetail(null), { wrapper: createWrapper() });
    expect(result.current.isFetching).toBe(false);
  });

  it('fetches ticker details with politician aggregation', async () => {
    const mockTrades = [
      {
        id: 't1', asset_ticker: 'AAPL', asset_name: 'Apple Inc.',
        transaction_type: 'purchase', amount_range_min: 1000, amount_range_max: 5000,
        disclosure_date: '2025-01-15', status: 'active',
        politician: { id: 'p1', full_name: 'John Doe', first_name: 'J', last_name: 'D', party: 'D' },
      },
      {
        id: 't2', asset_ticker: 'AAPL', asset_name: 'Apple Inc.',
        transaction_type: 'sale', amount_range_min: 2000, amount_range_max: 10000,
        disclosure_date: '2025-01-10', status: 'active',
        politician: { id: 'p1', full_name: 'John Doe', first_name: 'J', last_name: 'D', party: 'D' },
      },
      {
        id: 't3', asset_ticker: 'AAPL', asset_name: 'Apple Inc.',
        transaction_type: 'purchase', amount_range_min: 500, amount_range_max: 1000,
        disclosure_date: '2025-01-05', status: 'active',
        politician: { id: 'p2', full_name: 'Jane Smith', first_name: 'J', last_name: 'S', party: 'R' },
      },
    ];
    mockFrom.mockReturnValue(tableChain(mockTrades));

    const { result } = renderHook(() => useTickerDetail('AAPL'), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.ticker).toBe('AAPL');
    expect(result.current.data?.name).toBe('Apple Inc.');
    expect(result.current.data?.totalTrades).toBe(3);
    expect(result.current.data?.buyCount).toBe(2);
    expect(result.current.data?.sellCount).toBe(1);
    // Top politicians: John Doe (2 trades), Jane Smith (1)
    expect(result.current.data?.topPoliticians[0].name).toBe('John Doe');
    expect(result.current.data?.topPoliticians[0].count).toBe(2);
  });

  it('returns null for empty results', async () => {
    mockFrom.mockReturnValue(tableChain([]));

    const { result } = renderHook(() => useTickerDetail('ZZZZ'), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBeNull();
  });
});

describe('useMonthDetail()', () => {
  beforeEach(() => vi.clearAllMocks());

  it('is disabled when month or year is null', () => {
    const { result: r1 } = renderHook(() => useMonthDetail(null, 2025), { wrapper: createWrapper() });
    expect(r1.current.isFetching).toBe(false);

    const { result: r2 } = renderHook(() => useMonthDetail(1, null), { wrapper: createWrapper() });
    expect(r2.current.isFetching).toBe(false);
  });

  it('fetches trades for a specific month', async () => {
    const mockTrades = [
      {
        id: 't1', transaction_type: 'purchase', asset_ticker: 'AAPL', asset_name: 'Apple',
        amount_range_min: 1000, amount_range_max: 5000, disclosure_date: '2025-01-15',
        status: 'active',
        politician: { id: 'p1', full_name: 'John Doe', first_name: 'J', last_name: 'D', party: 'D' },
      },
      {
        id: 't2', transaction_type: 'sale', asset_ticker: 'MSFT', asset_name: 'Microsoft',
        amount_range_min: 2000, amount_range_max: 10000, disclosure_date: '2025-01-20',
        status: 'active',
        politician: { id: 'p1', full_name: 'John Doe', first_name: 'J', last_name: 'D', party: 'D' },
      },
    ];
    mockFrom.mockReturnValue(tableChain(mockTrades));

    const { result } = renderHook(() => useMonthDetail(1, 2025), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.month).toBe(1);
    expect(result.current.data?.year).toBe(2025);
    expect(result.current.data?.label).toBe('Jan 2025');
    expect(result.current.data?.totalTrades).toBe(2);
    expect(result.current.data?.buyCount).toBe(1);
    expect(result.current.data?.sellCount).toBe(1);
    expect(result.current.data?.topTickers).toHaveLength(2);
    expect(result.current.data?.topPoliticians).toHaveLength(1);
    expect(result.current.data?.topPoliticians[0].count).toBe(2);
  });
});
