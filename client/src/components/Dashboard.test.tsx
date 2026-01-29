/**
 * Tests for components/Dashboard.tsx
 *
 * Tests:
 * - Dashboard component rendering
 * - Loading state display
 * - Stats card rendering with data
 * - Transaction breakdown display
 * - Chart and component integration
 * - Props handling (initialTickerSearch, onTickerSearchClear)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock child components to isolate Dashboard testing
vi.mock('@/components/StatsCard', () => ({
  default: ({ title, value, change }: { title: string; value: string; change?: string }) => (
    <div data-testid={`stats-card-${title.toLowerCase().replace(/\s+/g, '-')}`}>
      <span data-testid="stats-title">{title}</span>
      <span data-testid="stats-value">{value}</span>
      {change && <span data-testid="stats-change">{change}</span>}
    </div>
  ),
}));

vi.mock('@/components/TradeChart', () => ({
  default: () => <div data-testid="trade-chart">Trade Chart</div>,
}));

vi.mock('@/components/VolumeChart', () => ({
  default: () => <div data-testid="volume-chart">Volume Chart</div>,
}));

vi.mock('@/components/TopTraders', () => ({
  default: () => <div data-testid="top-traders">Top Traders</div>,
}));

vi.mock('@/components/TopTickers', () => ({
  default: () => <div data-testid="top-tickers">Top Tickers</div>,
}));

vi.mock('@/components/LandingTradesTable', () => ({
  default: ({ initialSearchQuery, onSearchClear }: { initialSearchQuery?: string; onSearchClear?: () => void }) => (
    <div data-testid="landing-trades-table">
      {initialSearchQuery && <span data-testid="search-query">{initialSearchQuery}</span>}
      {onSearchClear && <button data-testid="clear-search" onClick={onSearchClear}>Clear</button>}
    </div>
  ),
}));

vi.mock('@/components/ErrorBoundary', () => ({
  ErrorBoundary: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock the hooks
const mockUseDashboardStats = vi.fn();
const mockUseChartData = vi.fn();

vi.mock('@/hooks/useSupabaseData', () => ({
  useDashboardStats: () => mockUseDashboardStats(),
  useChartData: () => mockUseChartData(),
}));

vi.mock('@/lib/mockData', () => ({
  formatCurrency: (value: number) => `$${value.toLocaleString()}`,
}));

import Dashboard from './Dashboard';

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

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock return values
    mockUseDashboardStats.mockReturnValue({
      data: null,
      isLoading: false,
    });
    mockUseChartData.mockReturnValue({
      data: null,
    });
  });

  describe('Header', () => {
    it('renders the main title', () => {
      render(<Dashboard />, { wrapper: createWrapper() });

      expect(screen.getByText('Politician Stock Trading Tracker')).toBeInTheDocument();
    });

    it('renders the description', () => {
      render(<Dashboard />, { wrapper: createWrapper() });

      expect(
        screen.getByText('A free public resource tracking congressional stock trades and disclosures')
      ).toBeInTheDocument();
    });
  });

  describe('Loading State', () => {
    it('shows loading spinners when data is loading', () => {
      mockUseDashboardStats.mockReturnValue({
        data: null,
        isLoading: true,
      });

      render(<Dashboard />, { wrapper: createWrapper() });

      // Should render 4 loading placeholders
      const loadingSpinners = document.querySelectorAll('.animate-spin');
      expect(loadingSpinners.length).toBe(4);
    });

    it('does not show stats cards when loading', () => {
      mockUseDashboardStats.mockReturnValue({
        data: null,
        isLoading: true,
      });

      render(<Dashboard />, { wrapper: createWrapper() });

      expect(screen.queryByTestId('stats-card-total-trades')).not.toBeInTheDocument();
    });
  });

  describe('Stats Cards', () => {
    const mockStats = {
      total_trades: 12500,
      total_volume: 5000000000,
      active_politicians: 535,
      recent_filings: 42,
      average_trade_size: 150000,
    };

    beforeEach(() => {
      mockUseDashboardStats.mockReturnValue({
        data: mockStats,
        isLoading: false,
      });
    });

    it('renders Total Trades stats card', () => {
      render(<Dashboard />, { wrapper: createWrapper() });

      const card = screen.getByTestId('stats-card-total-trades');
      expect(card).toBeInTheDocument();
      expect(card).toHaveTextContent('12,500');
    });

    it('renders Total Volume stats card', () => {
      render(<Dashboard />, { wrapper: createWrapper() });

      const card = screen.getByTestId('stats-card-total-volume');
      expect(card).toBeInTheDocument();
      expect(card).toHaveTextContent('$5,000,000,000');
    });

    it('renders Active Politicians stats card', () => {
      render(<Dashboard />, { wrapper: createWrapper() });

      const card = screen.getByTestId('stats-card-active-politicians');
      expect(card).toBeInTheDocument();
      expect(card).toHaveTextContent('535');
    });

    it('renders Recent Filings stats card', () => {
      render(<Dashboard />, { wrapper: createWrapper() });

      const card = screen.getByTestId('stats-card-recent-filings');
      expect(card).toBeInTheDocument();
      expect(card).toHaveTextContent('42');
    });

    it('shows average trade size in Total Trades card', () => {
      render(<Dashboard />, { wrapper: createWrapper() });

      const card = screen.getByTestId('stats-card-total-trades');
      expect(card).toHaveTextContent('Avg $150,000 per trade');
    });

    it('handles null/undefined stats gracefully', () => {
      mockUseDashboardStats.mockReturnValue({
        data: {},
        isLoading: false,
      });

      render(<Dashboard />, { wrapper: createWrapper() });

      // Should show 0 or default values
      const totalTradesCard = screen.getByTestId('stats-card-total-trades');
      expect(totalTradesCard).toHaveTextContent('0');
    });
  });

  describe('Transaction Breakdown', () => {
    const mockChartData = [
      { month: 'Jan', year: 2026, buys: 100, sells: 80, volume: 1000000 },
      { month: 'Feb', year: 2026, buys: 150, sells: 120, volume: 1500000 },
      { month: 'Mar', year: 2026, buys: 200, sells: 160, volume: 2000000 },
    ];

    const mockStats = {
      total_trades: 1000,
      total_volume: 5000000,
      active_politicians: 100,
      recent_filings: 20,
      average_trade_size: 5000,
    };

    beforeEach(() => {
      mockUseDashboardStats.mockReturnValue({
        data: mockStats,
        isLoading: false,
      });
      mockUseChartData.mockReturnValue({
        data: mockChartData,
      });
    });

    it('displays transaction breakdown when data exists', () => {
      render(<Dashboard />, { wrapper: createWrapper() });

      expect(screen.getByText('Transaction breakdown:')).toBeInTheDocument();
    });

    it('shows total buys count from chart data', () => {
      render(<Dashboard />, { wrapper: createWrapper() });

      // 100 + 150 + 200 = 450 buys
      expect(screen.getByText('450 Buys')).toBeInTheDocument();
    });

    it('shows total sells count from chart data', () => {
      render(<Dashboard />, { wrapper: createWrapper() });

      // 80 + 120 + 160 = 360 sells
      expect(screen.getByText('360 Sells')).toBeInTheDocument();
    });

    it('calculates "Other" transactions correctly', () => {
      render(<Dashboard />, { wrapper: createWrapper() });

      // total_trades (1000) - buys (450) - sells (360) = 190 other
      expect(screen.getByText('190 Other')).toBeInTheDocument();
    });

    it('does not show transaction breakdown when no chart data', () => {
      mockUseChartData.mockReturnValue({
        data: null,
      });

      render(<Dashboard />, { wrapper: createWrapper() });

      expect(screen.queryByText('Transaction breakdown:')).not.toBeInTheDocument();
    });

    it('does not show transaction breakdown when all zeros', () => {
      mockUseChartData.mockReturnValue({
        data: [{ month: 'Jan', year: 2026, buys: 0, sells: 0, volume: 0 }],
      });

      render(<Dashboard />, { wrapper: createWrapper() });

      expect(screen.queryByText('Transaction breakdown:')).not.toBeInTheDocument();
    });
  });

  describe('Child Components', () => {
    it('renders LandingTradesTable', () => {
      render(<Dashboard />, { wrapper: createWrapper() });

      expect(screen.getByTestId('landing-trades-table')).toBeInTheDocument();
    });

    it('renders TradeChart', () => {
      render(<Dashboard />, { wrapper: createWrapper() });

      expect(screen.getByTestId('trade-chart')).toBeInTheDocument();
    });

    it('renders VolumeChart', () => {
      render(<Dashboard />, { wrapper: createWrapper() });

      expect(screen.getByTestId('volume-chart')).toBeInTheDocument();
    });

    it('renders TopTraders', () => {
      render(<Dashboard />, { wrapper: createWrapper() });

      expect(screen.getByTestId('top-traders')).toBeInTheDocument();
    });

    it('renders TopTickers', () => {
      render(<Dashboard />, { wrapper: createWrapper() });

      expect(screen.getByTestId('top-tickers')).toBeInTheDocument();
    });
  });

  describe('Props Handling', () => {
    it('passes initialTickerSearch to LandingTradesTable', () => {
      render(<Dashboard initialTickerSearch="AAPL" />, { wrapper: createWrapper() });

      expect(screen.getByTestId('search-query')).toHaveTextContent('AAPL');
    });

    it('passes onTickerSearchClear to LandingTradesTable', () => {
      const mockClear = vi.fn();
      render(<Dashboard onTickerSearchClear={mockClear} />, { wrapper: createWrapper() });

      const clearButton = screen.getByTestId('clear-search');
      clearButton.click();

      expect(mockClear).toHaveBeenCalled();
    });

    it('renders without props', () => {
      render(<Dashboard />, { wrapper: createWrapper() });

      expect(screen.queryByTestId('search-query')).not.toBeInTheDocument();
    });
  });

  describe('Data Edge Cases', () => {
    it('handles empty chart data array', () => {
      mockUseChartData.mockReturnValue({
        data: [],
      });

      render(<Dashboard />, { wrapper: createWrapper() });

      // Should not crash and should not show transaction breakdown
      expect(screen.queryByText('Transaction breakdown:')).not.toBeInTheDocument();
    });

    it('handles chart data with null buys/sells', () => {
      mockUseChartData.mockReturnValue({
        data: [
          { month: 'Jan', year: 2026, buys: null, sells: null, volume: 1000 },
          { month: 'Feb', year: 2026, buys: 100, sells: 50, volume: 2000 },
        ],
      });

      render(<Dashboard />, { wrapper: createWrapper() });

      // Should handle nulls as 0
      expect(screen.getByText('100 Buys')).toBeInTheDocument();
      expect(screen.getByText('50 Sells')).toBeInTheDocument();
    });

    it('handles very large numbers', () => {
      mockUseDashboardStats.mockReturnValue({
        data: {
          total_trades: 999999999,
          total_volume: 999999999999,
          active_politicians: 1000,
          recent_filings: 10000,
          average_trade_size: 1000000000,
        },
        isLoading: false,
      });

      render(<Dashboard />, { wrapper: createWrapper() });

      const totalTradesCard = screen.getByTestId('stats-card-total-trades');
      expect(totalTradesCard).toHaveTextContent('999,999,999');
    });
  });
});
