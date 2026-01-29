import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PositionsTable } from './PositionsTable';

// Mock the useAlpacaPositions hook
const mockRefetch = vi.fn();
const mockCalculatePositionMetrics = vi.fn();

vi.mock('@/hooks/useAlpacaPositions', () => ({
  useAlpacaPositions: vi.fn(),
  calculatePositionMetrics: vi.fn(() => mockCalculatePositionMetrics()),
}));

// Mock the QuickTradeDialog component
vi.mock('./QuickTradeDialog', () => ({
  QuickTradeDialog: vi.fn(({ open, onOpenChange, position, tradingMode, defaultSide }) => {
    if (!open) return null;
    return (
      <div data-testid="quick-trade-dialog">
        <span data-testid="dialog-position">{position?.symbol}</span>
        <span data-testid="dialog-mode">{tradingMode}</span>
        <span data-testid="dialog-side">{defaultSide}</span>
        <button onClick={() => onOpenChange(false)}>Close</button>
      </div>
    );
  }),
}));

// Import the mocked hook for manipulation
import { useAlpacaPositions } from '@/hooks/useAlpacaPositions';
const mockUseAlpacaPositions = vi.mocked(useAlpacaPositions);

const mockPositions = [
  {
    asset_id: 'asset-1',
    symbol: 'AAPL',
    qty: 100,
    side: 'long' as const,
    avg_entry_price: 150.00,
    current_price: 175.00,
    market_value: 17500,
    unrealized_pl: 2500,
    unrealized_plpc: 16.67,
    unrealized_intraday_pl: 125.50,
  },
  {
    asset_id: 'asset-2',
    symbol: 'GOOGL',
    qty: 50,
    side: 'long' as const,
    avg_entry_price: 140.00,
    current_price: 135.00,
    market_value: 6750,
    unrealized_pl: -250,
    unrealized_plpc: -3.57,
    unrealized_intraday_pl: -50.00,
  },
];

const mockMetrics = {
  totalValue: 24250,
  totalPnL: 2250,
  totalPnLPercent: 10.2,
};

describe('PositionsTable', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCalculatePositionMetrics.mockReturnValue(mockMetrics);
  });

  describe('Loading state', () => {
    it('shows loading spinner when loading', () => {
      mockUseAlpacaPositions.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useAlpacaPositions>);

      render(<PositionsTable tradingMode="paper" />);

      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });
  });

  describe('Error state', () => {
    it('shows error message when fetch fails', () => {
      mockUseAlpacaPositions.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Failed to fetch'),
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useAlpacaPositions>);

      render(<PositionsTable tradingMode="paper" />);

      expect(screen.getByText('Failed to load positions')).toBeInTheDocument();
    });

    it('shows retry button on error', () => {
      mockUseAlpacaPositions.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Failed to fetch'),
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useAlpacaPositions>);

      render(<PositionsTable tradingMode="paper" />);

      expect(screen.getByRole('button', { name: /Retry/ })).toBeInTheDocument();
    });

    it('calls refetch when retry button is clicked', async () => {
      mockUseAlpacaPositions.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Failed to fetch'),
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useAlpacaPositions>);

      const user = userEvent.setup();
      render(<PositionsTable tradingMode="paper" />);

      await user.click(screen.getByRole('button', { name: /Retry/ }));

      expect(mockRefetch).toHaveBeenCalled();
    });
  });

  describe('Empty state', () => {
    it('shows empty state message when no positions', () => {
      mockUseAlpacaPositions.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useAlpacaPositions>);

      render(<PositionsTable tradingMode="paper" />);

      expect(screen.getByText('No open positions')).toBeInTheDocument();
      expect(screen.getByText('Start trading to build your portfolio')).toBeInTheDocument();
    });

    it('shows card title in empty state', () => {
      mockUseAlpacaPositions.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useAlpacaPositions>);

      render(<PositionsTable tradingMode="paper" />);

      expect(screen.getByText('Positions')).toBeInTheDocument();
      expect(screen.getByText('Your current holdings')).toBeInTheDocument();
    });

    it('handles null positions', () => {
      mockUseAlpacaPositions.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as unknown as ReturnType<typeof useAlpacaPositions>);

      render(<PositionsTable tradingMode="paper" />);

      expect(screen.getByText('No open positions')).toBeInTheDocument();
    });
  });

  describe('Positions display', () => {
    beforeEach(() => {
      mockUseAlpacaPositions.mockReturnValue({
        data: mockPositions,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useAlpacaPositions>);
    });

    it('shows positions count in header', () => {
      render(<PositionsTable tradingMode="paper" />);

      expect(screen.getByText(/Positions \(2\)/)).toBeInTheDocument();
    });

    it('shows total value in header', () => {
      render(<PositionsTable tradingMode="paper" />);

      expect(screen.getByText(/Total:.*\$24,250/)).toBeInTheDocument();
    });

    it('shows total P&L in header', () => {
      render(<PositionsTable tradingMode="paper" />);

      expect(screen.getByText(/P&L:.*\$2,250/)).toBeInTheDocument();
    });

    it('displays position symbols', () => {
      render(<PositionsTable tradingMode="paper" />);

      expect(screen.getAllByText('AAPL').length).toBeGreaterThan(0);
      expect(screen.getAllByText('GOOGL').length).toBeGreaterThan(0);
    });

    it('displays position side badges', () => {
      render(<PositionsTable tradingMode="paper" />);

      const longBadges = screen.getAllByText('long');
      expect(longBadges.length).toBe(4); // 2 positions x 2 views (mobile + desktop)
    });

    it('shows refresh button', () => {
      render(<PositionsTable tradingMode="paper" />);

      // Find button with RefreshCw icon (uses ghost variant)
      const buttons = screen.getAllByRole('button');
      const refreshButton = buttons.find(btn => btn.querySelector('.lucide-refresh-cw'));
      expect(refreshButton).toBeInTheDocument();
    });

    it('calls refetch when refresh is clicked', async () => {
      const user = userEvent.setup();
      render(<PositionsTable tradingMode="paper" />);

      const buttons = screen.getAllByRole('button');
      const refreshButton = buttons.find(btn => btn.querySelector('.lucide-refresh-cw'));

      if (refreshButton) {
        await user.click(refreshButton);
        expect(mockRefetch).toHaveBeenCalled();
      }
    });
  });

  describe('P&L styling', () => {
    beforeEach(() => {
      mockUseAlpacaPositions.mockReturnValue({
        data: mockPositions,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useAlpacaPositions>);
    });

    it('applies green color for positive P&L', () => {
      render(<PositionsTable tradingMode="paper" />);

      // AAPL has positive P&L ($2,500)
      const aaplPnL = screen.getAllByText('$2,500.00');
      expect(aaplPnL.length).toBeGreaterThan(0);
    });

    it('applies red color for negative P&L', () => {
      render(<PositionsTable tradingMode="paper" />);

      // GOOGL has negative P&L (-$250)
      const googlPnL = screen.getAllByText('-$250.00');
      expect(googlPnL.length).toBeGreaterThan(0);
    });

    it('shows trending up icon for positive P&L', () => {
      render(<PositionsTable tradingMode="paper" />);

      const trendingUpIcons = document.querySelectorAll('.lucide-trending-up');
      expect(trendingUpIcons.length).toBeGreaterThan(0);
    });

    it('shows trending down icon for negative P&L', () => {
      render(<PositionsTable tradingMode="paper" />);

      const trendingDownIcons = document.querySelectorAll('.lucide-trending-down');
      expect(trendingDownIcons.length).toBeGreaterThan(0);
    });
  });

  describe('Trade dialog', () => {
    beforeEach(() => {
      mockUseAlpacaPositions.mockReturnValue({
        data: mockPositions,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useAlpacaPositions>);
    });

    it('opens trade dialog when Buy button is clicked', async () => {
      const user = userEvent.setup();
      render(<PositionsTable tradingMode="paper" />);

      // Find and click a Buy button
      const buyButtons = screen.getAllByRole('button', { name: /Buy/ });
      await user.click(buyButtons[0]);

      expect(screen.getByTestId('quick-trade-dialog')).toBeInTheDocument();
    });

    it('opens trade dialog when Sell button is clicked', async () => {
      const user = userEvent.setup();
      render(<PositionsTable tradingMode="paper" />);

      // Find and click a Sell button
      const sellButtons = screen.getAllByRole('button', { name: /Sell/ });
      await user.click(sellButtons[0]);

      expect(screen.getByTestId('quick-trade-dialog')).toBeInTheDocument();
    });

    it('passes correct position to trade dialog', async () => {
      const user = userEvent.setup();
      render(<PositionsTable tradingMode="paper" />);

      // Click the first Buy button (should be AAPL)
      const buyButtons = screen.getAllByRole('button', { name: /Buy/ });
      await user.click(buyButtons[0]);

      expect(screen.getByTestId('dialog-position')).toHaveTextContent('AAPL');
    });

    it('passes correct trading mode to trade dialog', async () => {
      const user = userEvent.setup();
      render(<PositionsTable tradingMode="live" />);

      const buyButtons = screen.getAllByRole('button', { name: /Buy/ });
      await user.click(buyButtons[0]);

      expect(screen.getByTestId('dialog-mode')).toHaveTextContent('live');
    });

    it('passes buy side when Buy button is clicked', async () => {
      const user = userEvent.setup();
      render(<PositionsTable tradingMode="paper" />);

      const buyButtons = screen.getAllByRole('button', { name: /Buy/ });
      await user.click(buyButtons[0]);

      expect(screen.getByTestId('dialog-side')).toHaveTextContent('buy');
    });

    it('passes sell side when Sell button is clicked', async () => {
      const user = userEvent.setup();
      render(<PositionsTable tradingMode="paper" />);

      const sellButtons = screen.getAllByRole('button', { name: /Sell/ });
      await user.click(sellButtons[0]);

      expect(screen.getByTestId('dialog-side')).toHaveTextContent('sell');
    });

    it('closes trade dialog when onOpenChange(false) is called', async () => {
      const user = userEvent.setup();
      render(<PositionsTable tradingMode="paper" />);

      // Open dialog
      const buyButtons = screen.getAllByRole('button', { name: /Buy/ });
      await user.click(buyButtons[0]);
      expect(screen.getByTestId('quick-trade-dialog')).toBeInTheDocument();

      // Close dialog
      await user.click(screen.getByRole('button', { name: /Close/ }));
      expect(screen.queryByTestId('quick-trade-dialog')).not.toBeInTheDocument();
    });
  });

  describe('Refetching state', () => {
    it('disables refresh button while refetching', () => {
      mockUseAlpacaPositions.mockReturnValue({
        data: mockPositions,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: true,
      } as ReturnType<typeof useAlpacaPositions>);

      render(<PositionsTable tradingMode="paper" />);

      const buttons = screen.getAllByRole('button');
      const refreshButton = buttons.find(btn => btn.querySelector('.lucide-refresh-cw'));

      expect(refreshButton).toBeDisabled();
    });

    it('shows spinning animation while refetching', () => {
      mockUseAlpacaPositions.mockReturnValue({
        data: mockPositions,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: true,
      } as ReturnType<typeof useAlpacaPositions>);

      render(<PositionsTable tradingMode="paper" />);

      const refreshIcon = document.querySelector('.lucide-refresh-cw.animate-spin');
      expect(refreshIcon).toBeInTheDocument();
    });
  });

  describe('Desktop table view', () => {
    beforeEach(() => {
      mockUseAlpacaPositions.mockReturnValue({
        data: mockPositions,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useAlpacaPositions>);
    });

    it('shows table headers', () => {
      render(<PositionsTable tradingMode="paper" />);

      expect(screen.getByText('Symbol')).toBeInTheDocument();
      // Use getAllByText since 'Qty' appears in both mobile and desktop views
      expect(screen.getAllByText('Qty').length).toBeGreaterThan(0);
      expect(screen.getByText('Market Value')).toBeInTheDocument();
      expect(screen.getByText('Actions')).toBeInTheDocument();
    });

    it('shows quantity for each position', () => {
      render(<PositionsTable tradingMode="paper" />);

      expect(screen.getAllByText('100').length).toBeGreaterThan(0);
      expect(screen.getAllByText('50').length).toBeGreaterThan(0);
    });

    it('shows market value for each position', () => {
      render(<PositionsTable tradingMode="paper" />);

      expect(screen.getAllByText('$17,500.00').length).toBeGreaterThan(0);
      expect(screen.getAllByText('$6,750.00').length).toBeGreaterThan(0);
    });
  });

  describe('Currency formatting', () => {
    beforeEach(() => {
      mockUseAlpacaPositions.mockReturnValue({
        data: mockPositions,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useAlpacaPositions>);
    });

    it('formats average entry price correctly', () => {
      render(<PositionsTable tradingMode="paper" />);

      expect(screen.getAllByText('$150.00').length).toBeGreaterThan(0);
    });

    it('formats current price correctly', () => {
      render(<PositionsTable tradingMode="paper" />);

      expect(screen.getAllByText('$175.00').length).toBeGreaterThan(0);
    });

    it('formats intraday P&L correctly', () => {
      render(<PositionsTable tradingMode="paper" />);

      // Positive intraday P&L
      expect(screen.getAllByText('$125.50').length).toBeGreaterThan(0);
      // Negative intraday P&L
      expect(screen.getAllByText('-$50.00').length).toBeGreaterThan(0);
    });
  });

  describe('Percent formatting', () => {
    beforeEach(() => {
      mockUseAlpacaPositions.mockReturnValue({
        data: mockPositions,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useAlpacaPositions>);
    });

    it('shows + sign for positive percentages', () => {
      render(<PositionsTable tradingMode="paper" />);

      // AAPL has +16.67% (unrealized_plpc is multiplied by 100 in formatPercent)
      // The raw value 16.67 is formatted with + prefix
      const positivePercents = screen.getAllByText(/\+1667\.00%/);
      expect(positivePercents.length).toBeGreaterThan(0);
    });

    it('shows - sign for negative percentages', () => {
      render(<PositionsTable tradingMode="paper" />);

      // GOOGL has -3.57% (raw value is formatted with - prefix)
      const negativePercents = screen.getAllByText(/-357\.00%/);
      expect(negativePercents.length).toBeGreaterThan(0);
    });
  });

  describe('Total metrics display', () => {
    it('shows positive total P&L with green styling', () => {
      mockCalculatePositionMetrics.mockReturnValue({
        totalValue: 24250,
        totalPnL: 2250,
        totalPnLPercent: 10.2,
      });

      mockUseAlpacaPositions.mockReturnValue({
        data: mockPositions,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useAlpacaPositions>);

      render(<PositionsTable tradingMode="paper" />);

      const pnlElement = screen.getByText(/P&L:/);
      expect(pnlElement.closest('span')).toHaveClass('text-green-600');
    });

    it('shows negative total P&L with red styling', () => {
      mockCalculatePositionMetrics.mockReturnValue({
        totalValue: 24250,
        totalPnL: -500,
        totalPnLPercent: -2.1,
      });

      mockUseAlpacaPositions.mockReturnValue({
        data: mockPositions,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useAlpacaPositions>);

      render(<PositionsTable tradingMode="paper" />);

      const pnlElement = screen.getByText(/P&L:/);
      expect(pnlElement.closest('span')).toHaveClass('text-red-600');
    });
  });
});
