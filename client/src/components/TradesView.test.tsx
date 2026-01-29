/**
 * Tests for components/TradesView.tsx
 *
 * Tests:
 * - Component rendering
 * - Loading state display
 * - Jurisdiction filter functionality
 * - Search query filtering
 * - Pagination handling
 * - Empty states
 * - Trade data transformation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock TradeCard component
vi.mock('@/components/TradeCard', () => ({
  default: ({ trade }: { trade: { politicianName: string; ticker: string; type: string } }) => (
    <div data-testid={`trade-card-${trade.ticker}`}>
      <span data-testid="politician-name">{trade.politicianName}</span>
      <span data-testid="ticker">{trade.ticker}</span>
      <span data-testid="type">{trade.type}</span>
    </div>
  ),
}));

// Mock PaginationControls component
vi.mock('@/components/PaginationControls', () => ({
  PaginationControls: ({ pagination, itemLabel }: { pagination: { page: number; totalPages: number }; itemLabel: string }) => (
    <div data-testid="pagination-controls">
      <span data-testid="pagination-page">{pagination.page}</span>
      <span data-testid="pagination-total-pages">{pagination.totalPages}</span>
      <span data-testid="pagination-item-label">{itemLabel}</span>
    </div>
  ),
}));

// Mock hooks
const mockUseTrades = vi.fn();
const mockUseJurisdictions = vi.fn();
const mockUsePagination = vi.fn();

vi.mock('@/hooks/useSupabaseData', () => ({
  useTrades: (...args: unknown[]) => mockUseTrades(...args),
  useJurisdictions: () => mockUseJurisdictions(),
}));

vi.mock('@/hooks/usePagination', () => ({
  usePagination: () => mockUsePagination(),
}));

// Mock type guards (they're already tested separately)
vi.mock('@/lib/typeGuards', () => ({
  toParty: (value: unknown) => value || 'Other',
  toDisplayTransactionType: (value: unknown) => {
    if (value === 'purchase') return 'buy';
    if (value === 'sale') return 'sell';
    return value || 'unknown';
  },
}));

import TradesView from './TradesView';

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

// Helper to create mock pagination
const createMockPagination = (overrides = {}) => ({
  page: 1,
  totalPages: 1,
  totalItems: 0,
  itemsPerPage: 10,
  startIndex: 0,
  endIndex: 10,
  setPage: vi.fn(),
  setTotalItems: vi.fn(),
  setItemsPerPage: vi.fn(),
  nextPage: vi.fn(),
  prevPage: vi.fn(),
  ...overrides,
});

// Helper to create mock trade
const createMockTrade = (overrides = {}) => ({
  id: '1',
  politician_id: 'pol1',
  ticker: 'AAPL',
  asset_ticker: 'AAPL',
  company: 'Apple Inc.',
  asset_name: 'Apple Inc.',
  trade_type: 'buy',
  amount_range: '$15,001 - $50,000',
  estimated_value: 32500,
  filing_date: '2026-01-15',
  disclosure_date: '2026-01-15',
  transaction_date: '2026-01-10',
  source_url: 'https://example.com/disclosure.pdf',
  source_document_id: 'doc123',
  politician: {
    id: 'pol1',
    name: 'John Doe',
    party: 'D',
    jurisdiction_id: 'us_house',
  },
  ...overrides,
});

// Helper to create mock jurisdiction
const createMockJurisdiction = (overrides = {}) => ({
  id: 'us_house',
  code: 'US_HOUSE',
  name: 'US House',
  flag: '🇺🇸',
  ...overrides,
});

describe('TradesView', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock return values
    mockUseTrades.mockReturnValue({
      data: null,
      isLoading: false,
    });

    mockUseJurisdictions.mockReturnValue({
      data: null,
      isLoading: false,
    });

    mockUsePagination.mockReturnValue(createMockPagination());
  });

  describe('Header', () => {
    it('renders the title', () => {
      render(<TradesView />, { wrapper: createWrapper() });

      expect(screen.getByText('Recent Trades')).toBeInTheDocument();
    });

    it('renders the description', () => {
      render(<TradesView />, { wrapper: createWrapper() });

      expect(
        screen.getByText('All disclosed trading activity from tracked politicians')
      ).toBeInTheDocument();
    });

    it('renders the Filter button', () => {
      render(<TradesView />, { wrapper: createWrapper() });

      expect(screen.getByRole('button', { name: /filter/i })).toBeInTheDocument();
    });
  });

  describe('Loading State', () => {
    it('shows loading spinner when trades are loading', () => {
      mockUseTrades.mockReturnValue({
        data: null,
        isLoading: true,
      });

      render(<TradesView />, { wrapper: createWrapper() });

      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });

    it('shows loading spinner when jurisdictions are loading', () => {
      mockUseJurisdictions.mockReturnValue({
        data: null,
        isLoading: true,
      });

      render(<TradesView />, { wrapper: createWrapper() });

      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });

    it('does not show spinner when both are loaded', () => {
      mockUseTrades.mockReturnValue({
        data: [],
        isLoading: false,
      });
      mockUseJurisdictions.mockReturnValue({
        data: [],
        isLoading: false,
      });

      render(<TradesView />, { wrapper: createWrapper() });

      expect(document.querySelector('.animate-spin')).not.toBeInTheDocument();
    });
  });

  describe('Jurisdiction Filters', () => {
    const mockJurisdictions = [
      createMockJurisdiction({ id: 'us_house', name: 'US House', flag: '🇺🇸' }),
      createMockJurisdiction({ id: 'us_senate', name: 'US Senate', flag: '🇺🇸' }),
    ];

    beforeEach(() => {
      mockUseJurisdictions.mockReturnValue({
        data: mockJurisdictions,
        isLoading: false,
      });
      mockUseTrades.mockReturnValue({
        data: [],
        isLoading: false,
      });
    });

    it('renders "All" filter badge', () => {
      render(<TradesView />, { wrapper: createWrapper() });

      expect(screen.getByText('All')).toBeInTheDocument();
    });

    it('renders jurisdiction filter badges', () => {
      render(<TradesView />, { wrapper: createWrapper() });

      expect(screen.getByText('🇺🇸 US House')).toBeInTheDocument();
      expect(screen.getByText('🇺🇸 US Senate')).toBeInTheDocument();
    });

    it('"All" badge is highlighted by default', () => {
      render(<TradesView />, { wrapper: createWrapper() });

      const allBadge = screen.getByText('All');
      expect(allBadge).toHaveClass('bg-primary/20');
    });

    it('clicking jurisdiction badge updates filter', async () => {
      render(<TradesView />, { wrapper: createWrapper() });

      const houseBadge = screen.getByText('🇺🇸 US House');
      fireEvent.click(houseBadge);

      await waitFor(() => {
        expect(houseBadge).toHaveClass('bg-primary/20');
      });
    });

    it('clicking "All" clears jurisdiction filter', async () => {
      render(<TradesView jurisdictionId="us_house" />, { wrapper: createWrapper() });

      const allBadge = screen.getByText('All');
      fireEvent.click(allBadge);

      await waitFor(() => {
        expect(allBadge).toHaveClass('bg-primary/20');
      });
    });
  });

  describe('Trade List', () => {
    it('renders trade cards when data exists', () => {
      const mockTrades = [
        createMockTrade({ id: '1', ticker: 'AAPL' }),
        createMockTrade({ id: '2', ticker: 'GOOGL' }),
      ];

      mockUseTrades.mockReturnValue({
        data: mockTrades,
        isLoading: false,
      });
      mockUsePagination.mockReturnValue(createMockPagination({
        totalItems: 2,
        endIndex: 10,
      }));

      render(<TradesView />, { wrapper: createWrapper() });

      expect(screen.getByTestId('trade-card-AAPL')).toBeInTheDocument();
      expect(screen.getByTestId('trade-card-GOOGL')).toBeInTheDocument();
    });

    it('shows empty state when no trades', () => {
      mockUseTrades.mockReturnValue({
        data: [],
        isLoading: false,
      });

      render(<TradesView />, { wrapper: createWrapper() });

      expect(screen.getByText('No trades recorded yet')).toBeInTheDocument();
    });

    it('shows search-specific empty state when searching', () => {
      mockUseTrades.mockReturnValue({
        data: [],
        isLoading: false,
      });

      render(<TradesView searchQuery="INVALID" />, { wrapper: createWrapper() });

      expect(screen.getByText('No trades found for "INVALID"')).toBeInTheDocument();
    });

    it('transforms trade data correctly for TradeCard', () => {
      const mockTrade = createMockTrade({
        ticker: 'TSLA',
        politician: {
          id: 'pol1',
          name: 'Jane Smith',
          party: 'R',
          jurisdiction_id: 'us_senate',
        },
      });

      mockUseTrades.mockReturnValue({
        data: [mockTrade],
        isLoading: false,
      });
      mockUsePagination.mockReturnValue(createMockPagination({
        totalItems: 1,
        endIndex: 10,
      }));

      render(<TradesView />, { wrapper: createWrapper() });

      const tradeCard = screen.getByTestId('trade-card-TSLA');
      expect(tradeCard).toBeInTheDocument();
      expect(screen.getByTestId('politician-name')).toHaveTextContent('Jane Smith');
    });
  });

  describe('Search Query Filtering', () => {
    const mockTrades = [
      createMockTrade({ id: '1', ticker: 'AAPL', company: 'Apple Inc.', politician: { id: 'pol1', name: 'John Doe', party: 'D', jurisdiction_id: 'us_house' } }),
      createMockTrade({ id: '2', ticker: 'GOOGL', company: 'Alphabet Inc.', politician: { id: 'pol2', name: 'Jane Smith', party: 'R', jurisdiction_id: 'us_senate' } }),
      createMockTrade({ id: '3', ticker: 'MSFT', company: 'Microsoft Corp', politician: { id: 'pol3', name: 'Apple Johnson', party: 'I', jurisdiction_id: 'us_house' } }),
    ];

    beforeEach(() => {
      mockUseTrades.mockReturnValue({
        data: mockTrades,
        isLoading: false,
      });
    });

    it('filters by ticker', () => {
      mockUsePagination.mockReturnValue(createMockPagination({
        totalItems: 1,
        endIndex: 10,
      }));

      render(<TradesView searchQuery="AAPL" />, { wrapper: createWrapper() });

      expect(screen.getByTestId('trade-card-AAPL')).toBeInTheDocument();
      expect(screen.queryByTestId('trade-card-GOOGL')).not.toBeInTheDocument();
    });

    it('filters by company name', () => {
      mockUsePagination.mockReturnValue(createMockPagination({
        totalItems: 1,
        endIndex: 10,
      }));

      render(<TradesView searchQuery="Alphabet" />, { wrapper: createWrapper() });

      expect(screen.getByTestId('trade-card-GOOGL')).toBeInTheDocument();
      expect(screen.queryByTestId('trade-card-AAPL')).not.toBeInTheDocument();
    });

    it('filters by politician name', () => {
      mockUsePagination.mockReturnValue(createMockPagination({
        totalItems: 2,
        endIndex: 10,
      }));

      render(<TradesView searchQuery="Apple" />, { wrapper: createWrapper() });

      // Should match both "Apple Inc." company and "Apple Johnson" politician
      expect(screen.getByTestId('trade-card-AAPL')).toBeInTheDocument();
      expect(screen.getByTestId('trade-card-MSFT')).toBeInTheDocument();
    });

    it('search is case-insensitive', () => {
      mockUsePagination.mockReturnValue(createMockPagination({
        totalItems: 1,
        endIndex: 10,
      }));

      render(<TradesView searchQuery="aapl" />, { wrapper: createWrapper() });

      expect(screen.getByTestId('trade-card-AAPL')).toBeInTheDocument();
    });

    it('shows all trades when searchQuery is empty', () => {
      mockUsePagination.mockReturnValue(createMockPagination({
        totalItems: 3,
        endIndex: 10,
      }));

      render(<TradesView searchQuery="" />, { wrapper: createWrapper() });

      expect(screen.getByTestId('trade-card-AAPL')).toBeInTheDocument();
      expect(screen.getByTestId('trade-card-GOOGL')).toBeInTheDocument();
      expect(screen.getByTestId('trade-card-MSFT')).toBeInTheDocument();
    });
  });

  describe('Pagination', () => {
    it('shows pagination controls when trades exist', () => {
      mockUseTrades.mockReturnValue({
        data: [createMockTrade()],
        isLoading: false,
      });
      mockUsePagination.mockReturnValue(createMockPagination({
        totalItems: 1,
      }));

      render(<TradesView />, { wrapper: createWrapper() });

      expect(screen.getByTestId('pagination-controls')).toBeInTheDocument();
    });

    it('hides pagination controls when no trades', () => {
      mockUseTrades.mockReturnValue({
        data: [],
        isLoading: false,
      });

      render(<TradesView />, { wrapper: createWrapper() });

      expect(screen.queryByTestId('pagination-controls')).not.toBeInTheDocument();
    });

    it('passes correct itemLabel to pagination', () => {
      mockUseTrades.mockReturnValue({
        data: [createMockTrade()],
        isLoading: false,
      });
      mockUsePagination.mockReturnValue(createMockPagination({
        totalItems: 1,
      }));

      render(<TradesView />, { wrapper: createWrapper() });

      expect(screen.getByTestId('pagination-item-label')).toHaveTextContent('trades');
    });

    it('calls setTotalItems when trades change', () => {
      const setTotalItemsMock = vi.fn();
      mockUseTrades.mockReturnValue({
        data: [createMockTrade(), createMockTrade({ id: '2' })],
        isLoading: false,
      });
      mockUsePagination.mockReturnValue(createMockPagination({
        setTotalItems: setTotalItemsMock,
      }));

      render(<TradesView />, { wrapper: createWrapper() });

      expect(setTotalItemsMock).toHaveBeenCalledWith(2);
    });
  });

  describe('Props Handling', () => {
    it('passes jurisdictionId to useTrades hook', () => {
      render(<TradesView jurisdictionId="us_house" />, { wrapper: createWrapper() });

      expect(mockUseTrades).toHaveBeenCalledWith(500, 'us_house');
    });

    it('uses undefined jurisdiction when not provided', () => {
      render(<TradesView />, { wrapper: createWrapper() });

      expect(mockUseTrades).toHaveBeenCalledWith(500, undefined);
    });

    it('uses initial jurisdictionId for filter state', () => {
      mockUseJurisdictions.mockReturnValue({
        data: [createMockJurisdiction({ id: 'us_house', name: 'US House', flag: '🇺🇸' })],
        isLoading: false,
      });

      render(<TradesView jurisdictionId="us_house" />, { wrapper: createWrapper() });

      const houseBadge = screen.getByText('🇺🇸 US House');
      expect(houseBadge).toHaveClass('bg-primary/20');
    });

    it('resets page when jurisdiction filter changes', () => {
      const setPageMock = vi.fn();
      mockUsePagination.mockReturnValue(createMockPagination({
        setPage: setPageMock,
      }));
      mockUseJurisdictions.mockReturnValue({
        data: [createMockJurisdiction()],
        isLoading: false,
      });
      mockUseTrades.mockReturnValue({
        data: [],
        isLoading: false,
      });

      render(<TradesView />, { wrapper: createWrapper() });

      // Click jurisdiction filter
      const houseBadge = screen.getByText('🇺🇸 US House');
      fireEvent.click(houseBadge);

      expect(setPageMock).toHaveBeenCalledWith(1);
    });
  });

  describe('Edge Cases', () => {
    it('handles null politician gracefully', () => {
      const tradeWithNullPolitician = createMockTrade({
        politician: null,
      });

      mockUseTrades.mockReturnValue({
        data: [tradeWithNullPolitician],
        isLoading: false,
      });
      mockUsePagination.mockReturnValue(createMockPagination({
        totalItems: 1,
        endIndex: 10,
      }));

      render(<TradesView />, { wrapper: createWrapper() });

      // Should render with "Unknown" politician name
      expect(screen.getByTestId('politician-name')).toHaveTextContent('Unknown');
    });

    it('handles missing ticker fields gracefully', () => {
      const tradeWithMissingTicker = createMockTrade({
        ticker: '',
        asset_ticker: 'NVDA',
      });

      mockUseTrades.mockReturnValue({
        data: [tradeWithMissingTicker],
        isLoading: false,
      });
      mockUsePagination.mockReturnValue(createMockPagination({
        totalItems: 1,
        endIndex: 10,
      }));

      render(<TradesView />, { wrapper: createWrapper() });

      // Should fall back to asset_ticker
      expect(screen.getByTestId('trade-card-NVDA')).toBeInTheDocument();
    });

    it('handles undefined trades data', () => {
      mockUseTrades.mockReturnValue({
        data: undefined,
        isLoading: false,
      });

      render(<TradesView />, { wrapper: createWrapper() });

      expect(screen.getByText('No trades recorded yet')).toBeInTheDocument();
    });

    it('handles empty jurisdictions array', () => {
      mockUseJurisdictions.mockReturnValue({
        data: [],
        isLoading: false,
      });

      render(<TradesView />, { wrapper: createWrapper() });

      // Should still show "All" badge
      expect(screen.getByText('All')).toBeInTheDocument();
    });
  });
});
