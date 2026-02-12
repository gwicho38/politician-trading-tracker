/**
 * Tests for components/detail-modals/PoliticianDetailModal.tsx
 *
 * Tests:
 * - Component rendering
 * - Null politician handling
 * - Loading state display
 * - Trading stats display (total, buys, sells, holdings)
 * - Total volume display
 * - Top tickers display
 * - Recent trades display
 * - Empty state handling
 * - Dialog open/close behavior
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock Dialog components
vi.mock('@/components/ui/dialog', () => ({
  Dialog: ({ open, children }: { open: boolean; children: React.ReactNode }) =>
    open ? <div data-testid="dialog">{children}</div> : null,
  DialogContent: ({ children }: { children: React.ReactNode }) =>
    <div data-testid="dialog-content">{children}</div>,
  DialogHeader: ({ children }: { children: React.ReactNode }) =>
    <div data-testid="dialog-header">{children}</div>,
  DialogTitle: ({ children }: { children: React.ReactNode }) =>
    <h2 data-testid="dialog-title">{children}</h2>,
}));

// Mock usePoliticianDetail hook
const mockUsePoliticianDetail = vi.fn();
vi.mock('@/hooks/useSupabaseData', () => ({
  usePoliticianDetail: (id: string | null) => mockUsePoliticianDetail(id),
}));

// Mock mockData
vi.mock('@/lib/mockData', () => ({
  formatCurrency: (value: number | undefined) => value ? `$${value.toLocaleString()}` : '$0',
  getPartyColor: (party: string) => party === 'D' ? 'text-blue-600' : party === 'R' ? 'text-red-600' : 'text-gray-600',
  getPartyBg: (party: string) => party === 'D' ? 'bg-blue-100' : party === 'R' ? 'bg-red-100' : 'bg-gray-100',
}));

import { PoliticianDetailModal } from './PoliticianDetailModal';

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

// Helper to create mock politician
const createMockPolitician = (overrides = {}) => ({
  id: 'pol1',
  name: 'John Doe',
  party: 'D',
  chamber: 'House',
  state: 'CA',
  jurisdiction_id: 'us_house',
  total_volume: 5000000,
  total_trades: 45,
  ...overrides,
});

// Helper to create mock detail
const createMockDetail = (overrides = {}) => ({
  total_trades: 45,
  total_volume: 5000000,
  buyCount: 25,
  sellCount: 15,
  holdingCount: 5,
  topTickers: [
    { ticker: 'AAPL', count: 10 },
    { ticker: 'GOOGL', count: 8 },
    { ticker: 'MSFT', count: 5 },
  ],
  recentTrades: [
    {
      id: 'trade1',
      asset_ticker: 'AAPL',
      asset_name: 'Apple Inc.',
      transaction_type: 'purchase',
      disclosure_date: '2026-01-15',
      source_url: 'https://example.com/disclosure1.pdf',
    },
    {
      id: 'trade2',
      asset_ticker: 'GOOGL',
      asset_name: 'Alphabet Inc.',
      transaction_type: 'sale',
      disclosure_date: '2026-01-10',
      source_url: null,
    },
  ],
  ...overrides,
});

describe('PoliticianDetailModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePoliticianDetail.mockReturnValue({
      data: null,
      isLoading: false,
    });
  });

  describe('Null Politician Handling', () => {
    it('returns null when politician is null', () => {
      const { container } = render(
        <PoliticianDetailModal
          politician={null}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(container).toBeEmptyDOMElement();
    });
  });

  describe('Dialog Behavior', () => {
    it('renders dialog when open is true', () => {
      mockUsePoliticianDetail.mockReturnValue({
        data: createMockDetail(),
        isLoading: false,
      });

      render(
        <PoliticianDetailModal
          politician={createMockPolitician()}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByTestId('dialog')).toBeInTheDocument();
    });

    it('does not render dialog when open is false', () => {
      render(
        <PoliticianDetailModal
          politician={createMockPolitician()}
          open={false}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.queryByTestId('dialog')).not.toBeInTheDocument();
    });
  });

  describe('Header', () => {
    beforeEach(() => {
      mockUsePoliticianDetail.mockReturnValue({
        data: createMockDetail(),
        isLoading: false,
      });
    });

    it('displays politician name', () => {
      render(
        <PoliticianDetailModal
          politician={createMockPolitician({ name: 'Jane Smith' })}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText('Jane Smith')).toBeInTheDocument();
    });

    it('displays party badge', () => {
      render(
        <PoliticianDetailModal
          politician={createMockPolitician({ party: 'R' })}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText('Republican')).toBeInTheDocument();
    });

    it('displays chamber and state', () => {
      render(
        <PoliticianDetailModal
          politician={createMockPolitician({ chamber: 'Senate', state: 'NY' })}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText(/Senate/)).toBeInTheDocument();
      expect(screen.getByText(/NY/)).toBeInTheDocument();
    });

    it('handles missing state gracefully', () => {
      render(
        <PoliticianDetailModal
          politician={createMockPolitician({ state: null })}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      // Should render without state
      expect(screen.getByText('House')).toBeInTheDocument();
    });
  });

  describe('Loading State', () => {
    it('shows loading spinner when loading', () => {
      mockUsePoliticianDetail.mockReturnValue({
        data: null,
        isLoading: true,
      });

      render(
        <PoliticianDetailModal
          politician={createMockPolitician()}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });

    it('does not show spinner when loaded', () => {
      mockUsePoliticianDetail.mockReturnValue({
        data: createMockDetail(),
        isLoading: false,
      });

      render(
        <PoliticianDetailModal
          politician={createMockPolitician()}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(document.querySelector('.animate-spin')).not.toBeInTheDocument();
    });
  });

  describe('Trading Stats', () => {
    beforeEach(() => {
      mockUsePoliticianDetail.mockReturnValue({
        data: createMockDetail({
          total_trades: 100,
          buyCount: 60,
          sellCount: 30,
          holdingCount: 10,
        }),
        isLoading: false,
      });
    });

    it('displays total trades', () => {
      render(
        <PoliticianDetailModal
          politician={createMockPolitician()}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText('100')).toBeInTheDocument();
      expect(screen.getByText('Total')).toBeInTheDocument();
    });

    it('displays buy count', () => {
      render(
        <PoliticianDetailModal
          politician={createMockPolitician()}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText('60')).toBeInTheDocument();
      expect(screen.getByText('Buys')).toBeInTheDocument();
    });

    it('displays sell count', () => {
      render(
        <PoliticianDetailModal
          politician={createMockPolitician()}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText('30')).toBeInTheDocument();
      expect(screen.getByText('Sells')).toBeInTheDocument();
    });

    it('displays holding count', () => {
      render(
        <PoliticianDetailModal
          politician={createMockPolitician()}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText('10')).toBeInTheDocument();
      expect(screen.getByText('Holdings')).toBeInTheDocument();
    });
  });

  describe('Total Volume', () => {
    it('displays formatted total volume', () => {
      mockUsePoliticianDetail.mockReturnValue({
        data: createMockDetail({ total_volume: 10000000 }),
        isLoading: false,
      });

      render(
        <PoliticianDetailModal
          politician={createMockPolitician()}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText('$10,000,000')).toBeInTheDocument();
      expect(screen.getByText('Total Trading Volume')).toBeInTheDocument();
    });
  });

  describe('Top Tickers', () => {
    it('displays top tickers section', () => {
      mockUsePoliticianDetail.mockReturnValue({
        data: createMockDetail({
          topTickers: [
            { ticker: 'NVDA', count: 15 },
            { ticker: 'TSLA', count: 10 },
          ],
          // Override recentTrades to avoid ticker conflicts
          recentTrades: [],
        }),
        isLoading: false,
      });

      render(
        <PoliticianDetailModal
          politician={createMockPolitician()}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText('Most Traded Tickers')).toBeInTheDocument();
      expect(screen.getByText('NVDA')).toBeInTheDocument();
      expect(screen.getByText('(15)')).toBeInTheDocument();
      expect(screen.getByText('TSLA')).toBeInTheDocument();
      expect(screen.getByText('(10)')).toBeInTheDocument();
    });

    it('does not show top tickers section when empty', () => {
      mockUsePoliticianDetail.mockReturnValue({
        data: createMockDetail({ topTickers: [] }),
        isLoading: false,
      });

      render(
        <PoliticianDetailModal
          politician={createMockPolitician()}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.queryByText('Most Traded Tickers')).not.toBeInTheDocument();
    });
  });

  describe('Recent Trades', () => {
    it('displays recent trades section', () => {
      mockUsePoliticianDetail.mockReturnValue({
        data: createMockDetail(),
        isLoading: false,
      });

      render(
        <PoliticianDetailModal
          politician={createMockPolitician()}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText('Recent Trades')).toBeInTheDocument();
    });

    it('displays trade with BUY badge for purchase', () => {
      mockUsePoliticianDetail.mockReturnValue({
        data: createMockDetail({
          recentTrades: [{
            id: 'trade1',
            asset_ticker: 'AAPL',
            asset_name: 'Apple Inc.',
            transaction_type: 'purchase',
            disclosure_date: '2026-01-15',
            source_url: null,
          }],
        }),
        isLoading: false,
      });

      render(
        <PoliticianDetailModal
          politician={createMockPolitician()}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText('BUY')).toBeInTheDocument();
    });

    it('displays trade with SELL badge for sale', () => {
      mockUsePoliticianDetail.mockReturnValue({
        data: createMockDetail({
          recentTrades: [{
            id: 'trade1',
            asset_ticker: 'GOOGL',
            asset_name: 'Alphabet Inc.',
            transaction_type: 'sale',
            disclosure_date: '2026-01-10',
            source_url: null,
          }],
        }),
        isLoading: false,
      });

      render(
        <PoliticianDetailModal
          politician={createMockPolitician()}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText('SELL')).toBeInTheDocument();
    });

    it('displays trade with HOLD badge for holding', () => {
      mockUsePoliticianDetail.mockReturnValue({
        data: createMockDetail({
          recentTrades: [{
            id: 'trade1',
            asset_ticker: 'MSFT',
            asset_name: 'Microsoft Corp',
            transaction_type: 'holding',
            disclosure_date: '2026-01-05',
            source_url: null,
          }],
        }),
        isLoading: false,
      });

      render(
        <PoliticianDetailModal
          politician={createMockPolitician()}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText('HOLD')).toBeInTheDocument();
    });

    it('displays source link when available', () => {
      mockUsePoliticianDetail.mockReturnValue({
        data: createMockDetail({
          recentTrades: [{
            id: 'trade1',
            asset_ticker: 'AAPL',
            asset_name: 'Apple Inc.',
            transaction_type: 'purchase',
            disclosure_date: '2026-01-15',
            source_url: 'https://example.com/disclosure.pdf',
          }],
        }),
        isLoading: false,
      });

      render(
        <PoliticianDetailModal
          politician={createMockPolitician()}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      const sourceLink = screen.getByText('Source');
      expect(sourceLink).toBeInTheDocument();
      expect(sourceLink.closest('a')).toHaveAttribute('href', 'https://example.com/disclosure.pdf');
    });

    it('does not show source link when not available', () => {
      mockUsePoliticianDetail.mockReturnValue({
        data: createMockDetail({
          recentTrades: [{
            id: 'trade1',
            asset_ticker: 'AAPL',
            asset_name: 'Apple Inc.',
            transaction_type: 'purchase',
            disclosure_date: '2026-01-15',
            source_url: null,
          }],
        }),
        isLoading: false,
      });

      render(
        <PoliticianDetailModal
          politician={createMockPolitician()}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.queryByText('Source')).not.toBeInTheDocument();
    });

    it('does not show recent trades section when empty', () => {
      mockUsePoliticianDetail.mockReturnValue({
        data: createMockDetail({ recentTrades: [] }),
        isLoading: false,
      });

      render(
        <PoliticianDetailModal
          politician={createMockPolitician()}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.queryByText('Recent Trades')).not.toBeInTheDocument();
    });

    it('truncates long asset names', () => {
      mockUsePoliticianDetail.mockReturnValue({
        data: createMockDetail({
          recentTrades: [{
            id: 'trade1',
            asset_ticker: 'LONG',
            asset_name: 'This Is A Very Long Company Name That Should Be Truncated',
            transaction_type: 'purchase',
            disclosure_date: '2026-01-15',
            source_url: null,
          }],
        }),
        isLoading: false,
      });

      render(
        <PoliticianDetailModal
          politician={createMockPolitician()}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      // Should truncate to 30 chars + ...
      expect(screen.getByText(/This Is A Very Long Company Na/)).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('shows empty message when no detail data', () => {
      mockUsePoliticianDetail.mockReturnValue({
        data: null,
        isLoading: false,
      });

      render(
        <PoliticianDetailModal
          politician={createMockPolitician()}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText('No trading data available')).toBeInTheDocument();
    });
  });

  describe('Hook Integration', () => {
    it('calls usePoliticianDetail with politician id', () => {
      mockUsePoliticianDetail.mockReturnValue({
        data: createMockDetail(),
        isLoading: false,
      });

      render(
        <PoliticianDetailModal
          politician={createMockPolitician({ id: 'test-pol-123' })}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      expect(mockUsePoliticianDetail).toHaveBeenCalledWith('test-pol-123');
    });

    it('calls usePoliticianDetail with null when politician is null', () => {
      render(
        <PoliticianDetailModal
          politician={null}
          open={true}
          onOpenChange={vi.fn()}
        />,
        { wrapper: createWrapper() }
      );

      // Component returns null before hook is called when politician is null
      // But we should verify it doesn't crash
      expect(mockUsePoliticianDetail).toHaveBeenCalledWith(null);
    });
  });
});
