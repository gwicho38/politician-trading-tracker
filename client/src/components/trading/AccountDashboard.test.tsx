import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AccountDashboard } from './AccountDashboard';

// Mock the useAlpacaAccount hook
const mockRefetch = vi.fn();
const mockUseAlpacaAccount = vi.fn();
const mockCalculateDailyPnL = vi.fn();

vi.mock('@/hooks/useAlpacaAccount', () => ({
  useAlpacaAccount: (mode: 'paper' | 'live') => mockUseAlpacaAccount(mode),
  calculateDailyPnL: (account: unknown) => mockCalculateDailyPnL(account),
}));

// Mock formatters
vi.mock('@/lib/formatters', () => ({
  formatCurrencyFull: (value: number) => `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
}));

// Mock account data
const mockAccount = {
  portfolio_value: 100000,
  cash: 25000,
  buying_power: 50000,
  equity: 100000,
  last_equity: 95000,
  long_market_value: 75000,
  short_market_value: 0,
  status: 'ACTIVE',
  currency: 'USD',
  pattern_day_trader: false,
  trading_blocked: false,
  transfers_blocked: false,
  account_blocked: false,
};

const mockAccountWithBlocks = {
  ...mockAccount,
  trading_blocked: true,
  account_blocked: true,
  pattern_day_trader: true,
};

const mockNegativePnLAccount = {
  ...mockAccount,
  equity: 90000,
  last_equity: 100000,
};

describe('AccountDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCalculateDailyPnL.mockReturnValue({ value: 5000, percent: 5.26 });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // Loading state tests
  describe('Loading state', () => {
    it('should show loading spinner when loading', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });

      render(<AccountDashboard tradingMode="paper" />);

      // Should have loading spinner
      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });

    it('should not show account content when loading', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });

      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.queryByText('Account Overview')).not.toBeInTheDocument();
    });
  });

  // Error state tests
  describe('Error state', () => {
    it('should show error message when fetch fails', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error('Network error'),
        refetch: mockRefetch,
        isRefetching: false,
      });

      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('Failed to load account data')).toBeInTheDocument();
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });

    it('should show retry button on error', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error('Network error'),
        refetch: mockRefetch,
        isRefetching: false,
      });

      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument();
    });

    it('should call refetch on retry button click', async () => {
      const user = userEvent.setup();
      mockUseAlpacaAccount.mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error('Network error'),
        refetch: mockRefetch,
        isRefetching: false,
      });

      render(<AccountDashboard tradingMode="paper" />);

      const retryButton = screen.getByRole('button', { name: /Retry/i });
      await user.click(retryButton);

      expect(mockRefetch).toHaveBeenCalled();
    });
  });

  // Empty state tests
  describe('Empty state (no account)', () => {
    it('should show connect message when account is null', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });

      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('Connect your Alpaca account to view your portfolio')).toBeInTheDocument();
    });

    it('should show wallet icon for empty state', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: null,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });

      render(<AccountDashboard tradingMode="paper" />);

      // Check for wallet icon class
      expect(document.querySelector('.lucide-wallet')).toBeInTheDocument();
    });
  });

  // Header tests
  describe('Header display', () => {
    beforeEach(() => {
      mockUseAlpacaAccount.mockReturnValue({
        data: mockAccount,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });
    });

    it('should display Account Overview title', () => {
      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('Account Overview')).toBeInTheDocument();
    });

    it('should display Paper badge for paper trading mode', () => {
      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('Paper')).toBeInTheDocument();
    });

    it('should display Live badge for live trading mode', () => {
      render(<AccountDashboard tradingMode="live" />);

      expect(screen.getByText('Live')).toBeInTheDocument();
    });

    it('should display active status description', () => {
      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('Account is active and ready to trade')).toBeInTheDocument();
    });

    it('should display non-active status', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: { ...mockAccount, status: 'SUSPENDED' },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });

      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('Status: SUSPENDED')).toBeInTheDocument();
    });

    it('should have refresh button', () => {
      render(<AccountDashboard tradingMode="paper" />);

      // Find refresh button by the refresh icon
      const refreshButtons = document.querySelectorAll('.lucide-refresh-cw');
      expect(refreshButtons.length).toBeGreaterThan(0);
    });

    it('should call refetch when refresh button clicked', async () => {
      const user = userEvent.setup();
      render(<AccountDashboard tradingMode="paper" />);

      // Find the ghost button with RefreshCw icon (header refresh button)
      const buttons = screen.getAllByRole('button');
      const refreshButton = buttons.find(btn => btn.querySelector('.lucide-refresh-cw'));

      if (refreshButton) {
        await user.click(refreshButton);
        expect(mockRefetch).toHaveBeenCalled();
      }
    });

    it('should disable refresh button when refetching', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: mockAccount,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: true,
      });

      render(<AccountDashboard tradingMode="paper" />);

      const buttons = screen.getAllByRole('button');
      const refreshButton = buttons.find(btn => btn.querySelector('.lucide-refresh-cw'));

      expect(refreshButton).toBeDisabled();
    });

    it('should animate refresh icon when refetching', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: mockAccount,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: true,
      });

      render(<AccountDashboard tradingMode="paper" />);

      const refreshIcons = document.querySelectorAll('.lucide-refresh-cw');
      const animatingIcon = Array.from(refreshIcons).find(icon => icon.classList.contains('animate-spin'));
      expect(animatingIcon).toBeInTheDocument();
    });
  });

  // Warning badges tests
  describe('Warning badges', () => {
    it('should show Trading Blocked badge when trading is blocked', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: { ...mockAccount, trading_blocked: true },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });

      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('Trading Blocked')).toBeInTheDocument();
    });

    it('should show Account Blocked badge when account is blocked', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: { ...mockAccount, account_blocked: true },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });

      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('Account Blocked')).toBeInTheDocument();
    });

    it('should show Pattern Day Trader badge when PDT', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: { ...mockAccount, trading_blocked: true, pattern_day_trader: true },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });

      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('Pattern Day Trader')).toBeInTheDocument();
    });

    it('should show multiple badges when multiple conditions', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: mockAccountWithBlocks,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });

      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('Trading Blocked')).toBeInTheDocument();
      expect(screen.getByText('Account Blocked')).toBeInTheDocument();
      expect(screen.getByText('Pattern Day Trader')).toBeInTheDocument();
    });

    it('should not show warning badges when no blocks', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: mockAccount,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });

      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.queryByText('Trading Blocked')).not.toBeInTheDocument();
      expect(screen.queryByText('Account Blocked')).not.toBeInTheDocument();
    });
  });

  // Main metrics tests
  describe('Main metrics', () => {
    beforeEach(() => {
      mockUseAlpacaAccount.mockReturnValue({
        data: mockAccount,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });
    });

    it('should display Portfolio Value label', () => {
      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('Portfolio Value')).toBeInTheDocument();
    });

    it('should display formatted portfolio value', () => {
      render(<AccountDashboard tradingMode="paper" />);

      // Portfolio value and equity are both $100,000.00, so check for multiple
      expect(screen.getAllByText('$100,000.00').length).toBeGreaterThan(0);
    });

    it('should display Today\'s P&L label', () => {
      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText("Today's P&L")).toBeInTheDocument();
    });

    it('should display formatted daily P&L value', () => {
      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('$5,000.00')).toBeInTheDocument();
    });

    it('should display P&L percentage', () => {
      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('+5.26%')).toBeInTheDocument();
    });

    it('should display Cash label', () => {
      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('Cash')).toBeInTheDocument();
    });

    it('should display formatted cash value', () => {
      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('$25,000.00')).toBeInTheDocument();
    });

    it('should display Buying Power label', () => {
      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('Buying Power')).toBeInTheDocument();
    });

    it('should display formatted buying power value', () => {
      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('$50,000.00')).toBeInTheDocument();
    });
  });

  // P&L styling tests
  describe('P&L styling', () => {
    it('should show green styling for positive P&L', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: mockAccount,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });
      mockCalculateDailyPnL.mockReturnValue({ value: 5000, percent: 5.26 });

      render(<AccountDashboard tradingMode="paper" />);

      const pnlValue = screen.getByText('$5,000.00');
      expect(pnlValue).toHaveClass('text-green-600');
    });

    it('should show red styling for negative P&L', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: mockNegativePnLAccount,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });
      mockCalculateDailyPnL.mockReturnValue({ value: -10000, percent: -10 });

      render(<AccountDashboard tradingMode="paper" />);

      const pnlValue = screen.getByText('$-10,000.00');
      expect(pnlValue).toHaveClass('text-red-600');
    });

    it('should show green TrendingUp icon for positive P&L', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: mockAccount,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });
      mockCalculateDailyPnL.mockReturnValue({ value: 5000, percent: 5.26 });

      render(<AccountDashboard tradingMode="paper" />);

      expect(document.querySelector('.lucide-trending-up')).toBeInTheDocument();
    });

    it('should show red TrendingDown icon for negative P&L', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: mockNegativePnLAccount,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });
      mockCalculateDailyPnL.mockReturnValue({ value: -10000, percent: -10 });

      render(<AccountDashboard tradingMode="paper" />);

      expect(document.querySelector('.lucide-trending-down')).toBeInTheDocument();
    });

    it('should show negative percent formatting', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: mockNegativePnLAccount,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });
      mockCalculateDailyPnL.mockReturnValue({ value: -10000, percent: -10 });

      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('-10.00%')).toBeInTheDocument();
    });
  });

  // Secondary metrics tests
  describe('Secondary metrics', () => {
    beforeEach(() => {
      mockUseAlpacaAccount.mockReturnValue({
        data: mockAccount,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });
    });

    it('should display Equity label', () => {
      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('Equity')).toBeInTheDocument();
    });

    it('should display formatted equity value', () => {
      render(<AccountDashboard tradingMode="paper" />);

      // Equity is $100,000.00 - same as portfolio_value, so check multiple elements exist
      expect(screen.getAllByText('$100,000.00').length).toBeGreaterThan(0);
    });

    it('should display Long Market Value label', () => {
      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('Long Market Value')).toBeInTheDocument();
    });

    it('should display formatted long market value', () => {
      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('$75,000.00')).toBeInTheDocument();
    });

    it('should display Short Market Value label', () => {
      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('Short Market Value')).toBeInTheDocument();
    });

    it('should display formatted short market value', () => {
      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('$0.00')).toBeInTheDocument();
    });

    it('should display Last Close Equity label', () => {
      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('Last Close Equity')).toBeInTheDocument();
    });

    it('should display formatted last equity value', () => {
      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('$95,000.00')).toBeInTheDocument();
    });
  });

  // Trading mode tests
  describe('Trading mode', () => {
    it('should call useAlpacaAccount with paper mode', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: mockAccount,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });

      render(<AccountDashboard tradingMode="paper" />);

      expect(mockUseAlpacaAccount).toHaveBeenCalledWith('paper');
    });

    it('should call useAlpacaAccount with live mode', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: mockAccount,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });

      render(<AccountDashboard tradingMode="live" />);

      expect(mockUseAlpacaAccount).toHaveBeenCalledWith('live');
    });
  });

  // Calculate daily P&L integration tests
  describe('calculateDailyPnL integration', () => {
    it('should call calculateDailyPnL with account data', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: mockAccount,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });

      render(<AccountDashboard tradingMode="paper" />);

      expect(mockCalculateDailyPnL).toHaveBeenCalledWith(mockAccount);
    });

    it('should handle zero P&L', () => {
      mockUseAlpacaAccount.mockReturnValue({
        data: mockAccount,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });
      mockCalculateDailyPnL.mockReturnValue({ value: 0, percent: 0 });

      render(<AccountDashboard tradingMode="paper" />);

      expect(screen.getByText('+0.00%')).toBeInTheDocument();
    });
  });

  // Edge cases
  describe('Edge cases', () => {
    it('should handle undefined values gracefully', () => {
      const incompleteAccount = {
        ...mockAccount,
        portfolio_value: undefined,
        cash: undefined,
      };

      mockUseAlpacaAccount.mockReturnValue({
        data: incompleteAccount as unknown as typeof mockAccount,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });

      render(<AccountDashboard tradingMode="paper" />);

      // Should not crash and should render with $0.00 for undefined values
      expect(screen.getByText('Account Overview')).toBeInTheDocument();
    });

    it('should handle NaN values gracefully', () => {
      const nanAccount = {
        ...mockAccount,
        portfolio_value: NaN,
        cash: NaN,
      };

      mockUseAlpacaAccount.mockReturnValue({
        data: nanAccount,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      });

      render(<AccountDashboard tradingMode="paper" />);

      // Should not crash
      expect(screen.getByText('Account Overview')).toBeInTheDocument();
    });
  });
});
