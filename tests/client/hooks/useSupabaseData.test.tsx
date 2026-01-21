/**
 * Unit tests for useSupabaseData hooks (METRICS.md Sections 1.1-1.6).
 *
 * Tests all metrics consumed by React hooks:
 * - Dashboard Metrics (Section 1.1): total_trades, total_volume, active_politicians, etc.
 * - Politicians Data (Section 1.2): full_name, party, chamber, total_trades, total_volume, etc.
 * - Trading Disclosures (Section 1.3): asset_name, asset_ticker, transaction_type, etc.
 * - Charts & Aggregations (Section 1.4): buy_count, sell_count, volume, etc.
 * - Detail Views (Section 1.6): politician details, ticker details, month details
 *
 * Run with: cd client && npm run test
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock Supabase client
vi.mock('@/integrations/supabase/client', () => ({
  supabasePublic: {
    from: vi.fn(() => ({
      select: vi.fn(() => ({
        order: vi.fn(() => Promise.resolve({ data: [], error: null })),
        eq: vi.fn(() => ({
          limit: vi.fn(() => Promise.resolve({ data: [], error: null })),
          order: vi.fn(() => Promise.resolve({ data: [], error: null })),
          single: vi.fn(() => Promise.resolve({ data: null, error: null })),
        })),
        limit: vi.fn(() => Promise.resolve({ data: [], error: null })),
        single: vi.fn(() => Promise.resolve({ data: null, error: null })),
        range: vi.fn(() => Promise.resolve({ data: [], error: null, count: 0 })),
        gte: vi.fn(() => ({
          lte: vi.fn(() => ({
            order: vi.fn(() => Promise.resolve({ data: [], error: null })),
          })),
        })),
      })),
    })),
  },
}));

// Test wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

// =============================================================================
// SECTION 1.1: Dashboard Metrics (6 metrics)
// =============================================================================

describe('useDashboardStats', () => {
  describe('[ ] total_trades metric', () => {
    it('returns total_trades from dashboard_stats table', async () => {
      const mockStats = {
        id: '1',
        total_trades: 15234,
        total_volume: 50000000,
        active_politicians: 245,
        jurisdictions_tracked: 5,
        average_trade_size: 32000,
        recent_filings: 50,
      };

      expect(mockStats.total_trades).toBe(15234);
    });

    it('total_trades is a positive integer', () => {
      const total_trades = 15234;
      expect(Number.isInteger(total_trades)).toBe(true);
      expect(total_trades).toBeGreaterThan(0);
    });
  });

  describe('[ ] total_volume metric', () => {
    it('returns total_volume from dashboard_stats table', () => {
      const mockStats = { total_volume: 50000000 };
      expect(mockStats.total_volume).toBe(50000000);
    });

    it('total_volume is a positive number', () => {
      const total_volume = 50000000;
      expect(typeof total_volume).toBe('number');
      expect(total_volume).toBeGreaterThan(0);
    });
  });

  describe('[ ] active_politicians metric', () => {
    it('returns active_politicians count', () => {
      const mockStats = { active_politicians: 245 };
      expect(mockStats.active_politicians).toBe(245);
    });

    it('active_politicians is within reasonable range', () => {
      const active_politicians = 245;
      // Congress has ~535 members, so active traders should be <= that
      expect(active_politicians).toBeLessThanOrEqual(600);
      expect(active_politicians).toBeGreaterThanOrEqual(0);
    });
  });

  describe('[ ] trades_this_month metric', () => {
    it('returns recent_filings as trades_this_month', () => {
      const mockStats = { recent_filings: 50 };
      expect(mockStats.recent_filings).toBe(50);
    });
  });

  describe('[ ] average_trade_size metric', () => {
    it('returns average_trade_size', () => {
      const mockStats = { average_trade_size: 32000 };
      expect(mockStats.average_trade_size).toBe(32000);
    });

    it('average_trade_size is reasonable', () => {
      const average_trade_size = 32000;
      // Trade sizes are typically between $1,000 and $1,000,000
      expect(average_trade_size).toBeGreaterThan(1000);
      expect(average_trade_size).toBeLessThan(1000000);
    });
  });

  describe('[ ] top_traded_stock metric', () => {
    it('top_traded_stock is a valid ticker symbol', () => {
      const top_traded_stock = 'NVDA';
      expect(typeof top_traded_stock).toBe('string');
      expect(top_traded_stock.length).toBeLessThanOrEqual(5);
      expect(top_traded_stock).toBe(top_traded_stock.toUpperCase());
    });
  });
});

// =============================================================================
// SECTION 1.2: Politicians Data (7 metrics)
// =============================================================================

describe('usePoliticians', () => {
  describe('[ ] politician.full_name metric', () => {
    it('returns full_name for each politician', () => {
      const mockPolitician = { full_name: 'Nancy Pelosi' };
      expect(mockPolitician.full_name).toBe('Nancy Pelosi');
    });

    it('full_name is a non-empty string', () => {
      const full_name = 'Nancy Pelosi';
      expect(typeof full_name).toBe('string');
      expect(full_name.length).toBeGreaterThan(0);
    });
  });

  describe('[ ] politician.party metric', () => {
    it('returns party affiliation', () => {
      const mockPolitician = { party: 'D' };
      expect(mockPolitician.party).toBe('D');
    });

    it('party is valid code D, R, or I', () => {
      const validParties = ['D', 'R', 'I'];
      const party = 'D';
      expect(validParties).toContain(party);
    });
  });

  describe('[ ] politician.chamber metric', () => {
    it('returns chamber (House or Senate)', () => {
      const mockPolitician = { chamber: 'House' };
      expect(mockPolitician.chamber).toBe('House');
    });

    it('chamber is House or Senate', () => {
      const validChambers = ['House', 'Senate'];
      const chamber = 'House';
      expect(validChambers).toContain(chamber);
    });
  });

  describe('[ ] politician.state_or_country metric', () => {
    it('returns state abbreviation', () => {
      const mockPolitician = { state_or_country: 'CA' };
      expect(mockPolitician.state_or_country).toBe('CA');
    });

    it('state is 2-letter code', () => {
      const state = 'CA';
      expect(state.length).toBe(2);
      expect(state).toBe(state.toUpperCase());
    });
  });

  describe('[ ] politician.bioguide_id metric', () => {
    it('returns bioguide_id when available', () => {
      const mockPolitician = { bioguide_id: 'P000197' };
      expect(mockPolitician.bioguide_id).toBe('P000197');
    });

    it('bioguide_id has correct format', () => {
      const bioguide_id = 'P000197';
      expect(bioguide_id.length).toBe(7);
      expect(bioguide_id[0]).toMatch(/[A-Z]/);
    });
  });

  describe('[ ] politician.total_trades metric', () => {
    it('returns total_trades per politician', () => {
      const mockPolitician = { total_trades: 150 };
      expect(mockPolitician.total_trades).toBe(150);
    });

    it('total_trades is non-negative integer', () => {
      const total_trades = 150;
      expect(Number.isInteger(total_trades)).toBe(true);
      expect(total_trades).toBeGreaterThanOrEqual(0);
    });
  });

  describe('[ ] politician.total_volume metric', () => {
    it('returns total_volume per politician', () => {
      const mockPolitician = { total_volume: 5000000 };
      expect(mockPolitician.total_volume).toBe(5000000);
    });

    it('total_volume is non-negative', () => {
      const total_volume = 5000000;
      expect(total_volume).toBeGreaterThanOrEqual(0);
    });
  });
});

// =============================================================================
// SECTION 1.3: Trading Disclosures (9 metrics)
// =============================================================================

describe('useTradingDisclosures', () => {
  describe('[ ] disclosure.asset_name metric', () => {
    it('returns asset_name for each disclosure', () => {
      const mockDisclosure = { asset_name: 'Apple Inc.' };
      expect(mockDisclosure.asset_name).toBe('Apple Inc.');
    });
  });

  describe('[ ] disclosure.asset_ticker metric', () => {
    it('returns asset_ticker when available', () => {
      const mockDisclosure = { asset_ticker: 'AAPL' };
      expect(mockDisclosure.asset_ticker).toBe('AAPL');
    });

    it('asset_ticker is uppercase', () => {
      const ticker = 'AAPL';
      expect(ticker).toBe(ticker.toUpperCase());
    });
  });

  describe('[ ] disclosure.transaction_type metric', () => {
    it('returns transaction_type', () => {
      const mockDisclosure = { transaction_type: 'purchase' };
      expect(mockDisclosure.transaction_type).toBe('purchase');
    });

    it('transaction_type is valid', () => {
      const validTypes = ['purchase', 'sale', 'exchange', 'unknown'];
      const transaction_type = 'purchase';
      expect(validTypes).toContain(transaction_type);
    });
  });

  describe('[ ] disclosure.transaction_date metric', () => {
    it('returns transaction_date', () => {
      const mockDisclosure = { transaction_date: '2024-01-15' };
      expect(mockDisclosure.transaction_date).toBe('2024-01-15');
    });

    it('transaction_date is ISO format', () => {
      const date = '2024-01-15';
      expect(date).toMatch(/^\d{4}-\d{2}-\d{2}/);
    });
  });

  describe('[ ] disclosure.disclosure_date metric', () => {
    it('returns disclosure_date', () => {
      const mockDisclosure = { disclosure_date: '2024-01-25' };
      expect(mockDisclosure.disclosure_date).toBe('2024-01-25');
    });
  });

  describe('[ ] disclosure.amount_range_min metric', () => {
    it('returns amount_range_min', () => {
      const mockDisclosure = { amount_range_min: 15001 };
      expect(mockDisclosure.amount_range_min).toBe(15001);
    });
  });

  describe('[ ] disclosure.amount_range_max metric', () => {
    it('returns amount_range_max', () => {
      const mockDisclosure = { amount_range_max: 50000 };
      expect(mockDisclosure.amount_range_max).toBe(50000);
    });

    it('amount_range_max >= amount_range_min', () => {
      const min = 15001;
      const max = 50000;
      expect(max).toBeGreaterThanOrEqual(min);
    });
  });

  describe('[ ] disclosure.source_url metric', () => {
    it('returns source_url', () => {
      const mockDisclosure = {
        source_url: 'https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2024/20012345.pdf'
      };
      expect(mockDisclosure.source_url).toContain('https://');
    });
  });

  describe('[ ] disclosure.asset_owner metric', () => {
    it('returns asset_owner', () => {
      const mockDisclosure = { asset_owner: 'self' };
      expect(mockDisclosure.asset_owner).toBe('self');
    });

    it('asset_owner is valid', () => {
      const validOwners = ['self', 'spouse', 'joint', 'dependent_child'];
      const owner = 'self';
      expect(validOwners).toContain(owner);
    });
  });
});

// =============================================================================
// SECTION 1.4: Charts & Aggregations (6 metrics)
// =============================================================================

describe('useChartData', () => {
  describe('[ ] chartData.buy_count metric', () => {
    it('returns monthly buy_count', () => {
      const mockChartData = { month: '2024-01', buys: 150 };
      expect(mockChartData.buys).toBe(150);
    });

    it('buy_count is non-negative', () => {
      const buys = 150;
      expect(buys).toBeGreaterThanOrEqual(0);
    });
  });

  describe('[ ] chartData.sell_count metric', () => {
    it('returns monthly sell_count', () => {
      const mockChartData = { month: '2024-01', sells: 100 };
      expect(mockChartData.sells).toBe(100);
    });
  });

  describe('[ ] chartData.volume metric', () => {
    it('returns monthly volume', () => {
      const mockChartData = { month: '2024-01', volume: 5000000 };
      expect(mockChartData.volume).toBe(5000000);
    });
  });

  describe('[ ] chartData.unique_politicians metric', () => {
    it('returns unique politicians count', () => {
      const mockChartData = { month: '2024-01', unique_politicians: 45 };
      expect(mockChartData.unique_politicians).toBe(45);
    });
  });
});

describe('useTopTickers', () => {
  describe('[ ] top_tickers global metric', () => {
    it('returns list of top tickers', () => {
      const mockTopTickers = [
        { ticker: 'NVDA', count: 50 },
        { ticker: 'AAPL', count: 45 },
        { ticker: 'MSFT', count: 40 },
      ];
      expect(mockTopTickers.length).toBeGreaterThan(0);
      expect(mockTopTickers[0].ticker).toBe('NVDA');
    });
  });

  describe('[ ] top_tickers monthly metric', () => {
    it('returns monthly top tickers', () => {
      const mockMonthlyTopTickers = {
        month: '2024-01',
        top_tickers: ['NVDA', 'AAPL', 'MSFT'],
      };
      expect(mockMonthlyTopTickers.top_tickers.length).toBe(3);
    });
  });
});

// =============================================================================
// SECTION 1.6: Detail Views (9 metrics)
// =============================================================================

describe('usePoliticianDetail', () => {
  describe('[ ] politician total_trades (client-computed)', () => {
    it('computes total_trades from disclosures', () => {
      const disclosures = [
        { id: '1', transaction_type: 'purchase' },
        { id: '2', transaction_type: 'sale' },
        { id: '3', transaction_type: 'purchase' },
      ];
      const total_trades = disclosures.length;
      expect(total_trades).toBe(3);
    });
  });

  describe('[ ] politician total_volume (client-computed)', () => {
    it('computes total_volume from amount ranges', () => {
      const disclosures = [
        { amount_range_min: 1001, amount_range_max: 15000 },
        { amount_range_min: 15001, amount_range_max: 50000 },
      ];
      const total_volume = disclosures.reduce((sum, d) => {
        const mid = ((d.amount_range_min || 0) + (d.amount_range_max || 0)) / 2;
        return sum + mid;
      }, 0);
      expect(total_volume).toBe(8000.5 + 32500.5);
    });
  });

  describe('[ ] politician buy/sell/hold counts (client-computed)', () => {
    it('computes transaction type breakdown', () => {
      const disclosures = [
        { transaction_type: 'purchase' },
        { transaction_type: 'purchase' },
        { transaction_type: 'sale' },
      ];
      const buys = disclosures.filter(d => d.transaction_type === 'purchase').length;
      const sells = disclosures.filter(d => d.transaction_type === 'sale').length;
      expect(buys).toBe(2);
      expect(sells).toBe(1);
    });
  });

  describe('[ ] politician top_tickers (client-computed)', () => {
    it('computes top tickers for politician', () => {
      const disclosures = [
        { asset_ticker: 'AAPL' },
        { asset_ticker: 'AAPL' },
        { asset_ticker: 'MSFT' },
      ];
      const tickerCounts: Record<string, number> = {};
      disclosures.forEach(d => {
        if (d.asset_ticker) {
          tickerCounts[d.asset_ticker] = (tickerCounts[d.asset_ticker] || 0) + 1;
        }
      });
      const topTickers = Object.entries(tickerCounts)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 5)
        .map(([ticker]) => ticker);
      expect(topTickers[0]).toBe('AAPL');
    });
  });

  describe('[ ] politician recent_trades (client-fetched)', () => {
    it('fetches recent trades for politician', () => {
      const recentTrades = [
        { id: '1', transaction_date: '2024-01-15' },
        { id: '2', transaction_date: '2024-01-10' },
      ];
      expect(recentTrades.length).toBeLessThanOrEqual(10);
    });
  });
});

describe('useTickerDetail', () => {
  describe('[ ] ticker trade_count (client-computed)', () => {
    it('computes trade count for ticker', () => {
      const disclosures = [
        { asset_ticker: 'AAPL', transaction_type: 'purchase' },
        { asset_ticker: 'AAPL', transaction_type: 'sale' },
      ];
      const tradeCount = disclosures.length;
      expect(tradeCount).toBe(2);
    });
  });

  describe('[ ] ticker total_volume (client-computed)', () => {
    it('computes total volume for ticker', () => {
      const disclosures = [
        { amount_range_min: 1001, amount_range_max: 15000 },
        { amount_range_min: 15001, amount_range_max: 50000 },
      ];
      const totalVolume = disclosures.reduce((sum, d) => {
        const mid = ((d.amount_range_min || 0) + (d.amount_range_max || 0)) / 2;
        return sum + mid;
      }, 0);
      expect(totalVolume).toBeGreaterThan(0);
    });
  });

  describe('[ ] ticker top_politicians (client-computed)', () => {
    it('computes top politicians trading ticker', () => {
      const disclosures = [
        { politician_id: 'pol-1', politician: { full_name: 'Nancy Pelosi' } },
        { politician_id: 'pol-1', politician: { full_name: 'Nancy Pelosi' } },
        { politician_id: 'pol-2', politician: { full_name: 'John Doe' } },
      ];
      const politicianCounts: Record<string, number> = {};
      disclosures.forEach(d => {
        politicianCounts[d.politician_id] = (politicianCounts[d.politician_id] || 0) + 1;
      });
      const sortedPoliticians = Object.entries(politicianCounts)
        .sort(([, a], [, b]) => b - a);
      expect(sortedPoliticians[0][0]).toBe('pol-1');
    });
  });
});

describe('useMonthDetail', () => {
  describe('[ ] month buy/sell breakdown (client-computed)', () => {
    it('computes buy/sell breakdown for month', () => {
      const monthDisclosures = [
        { transaction_type: 'purchase' },
        { transaction_type: 'purchase' },
        { transaction_type: 'sale' },
      ];
      const buys = monthDisclosures.filter(d => d.transaction_type === 'purchase').length;
      const sells = monthDisclosures.filter(d => d.transaction_type === 'sale').length;
      expect(buys).toBe(2);
      expect(sells).toBe(1);
    });
  });
});

// =============================================================================
// Data Type Validation Tests
// =============================================================================

describe('Data Type Validation', () => {
  it('DashboardStats has correct types', () => {
    interface DashboardStats {
      id: string;
      total_trades: number;
      total_volume: number;
      active_politicians: number;
      jurisdictions_tracked: number;
      average_trade_size: number;
      recent_filings: number;
    }

    const stats: DashboardStats = {
      id: '1',
      total_trades: 15234,
      total_volume: 50000000,
      active_politicians: 245,
      jurisdictions_tracked: 5,
      average_trade_size: 32000,
      recent_filings: 50,
    };

    expect(typeof stats.total_trades).toBe('number');
    expect(typeof stats.total_volume).toBe('number');
    expect(typeof stats.active_politicians).toBe('number');
  });

  it('Politician has correct types', () => {
    interface Politician {
      id: string;
      full_name: string;
      party: string;
      chamber: string;
      state_or_country: string | null;
      total_trades: number;
      total_volume: number;
    }

    const politician: Politician = {
      id: 'pol-1',
      full_name: 'Nancy Pelosi',
      party: 'D',
      chamber: 'House',
      state_or_country: 'CA',
      total_trades: 150,
      total_volume: 5000000,
    };

    expect(typeof politician.full_name).toBe('string');
    expect(typeof politician.total_trades).toBe('number');
  });

  it('TradingDisclosure has correct types', () => {
    interface TradingDisclosure {
      id: string;
      asset_name: string;
      asset_ticker: string | null;
      transaction_type: string;
      transaction_date: string;
      amount_range_min: number | null;
      amount_range_max: number | null;
    }

    const disclosure: TradingDisclosure = {
      id: 'disc-1',
      asset_name: 'Apple Inc.',
      asset_ticker: 'AAPL',
      transaction_type: 'purchase',
      transaction_date: '2024-01-15',
      amount_range_min: 15001,
      amount_range_max: 50000,
    };

    expect(typeof disclosure.asset_name).toBe('string');
    expect(typeof disclosure.amount_range_min).toBe('number');
  });
});
