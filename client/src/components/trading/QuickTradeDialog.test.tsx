import { describe, it, expect, vi, beforeEach, afterEach, beforeAll } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QuickTradeDialog } from './QuickTradeDialog';

// Mock ResizeObserver for Radix UI components
beforeAll(() => {
  global.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }));
  Element.prototype.hasPointerCapture = vi.fn(() => false);
  Element.prototype.setPointerCapture = vi.fn();
  Element.prototype.releasePointerCapture = vi.fn();
});

// Mock the usePlaceOrder hook
const mockMutateAsync = vi.fn();
const mockUsePlaceOrder = vi.fn(() => ({
  mutateAsync: mockMutateAsync,
  isPending: false,
}));

vi.mock('@/hooks/useOrders', () => ({
  usePlaceOrder: (mode: 'paper' | 'live') => mockUsePlaceOrder(mode),
}));

// Mock toast
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    success: (msg: string) => mockToastSuccess(msg),
    error: (msg: string) => mockToastError(msg),
  },
}));

// Mock formatters
vi.mock('@/lib/formatters', () => ({
  formatCurrencyFull: (value: number) => `$${value.toFixed(2)}`,
}));

// Mock position data
const mockPosition = {
  asset_id: 'asset-123',
  symbol: 'AAPL',
  qty: 100,
  side: 'long' as const,
  avg_entry_price: 150.0,
  current_price: 175.5,
  market_value: 17550,
  unrealized_pl: 2550,
};

const mockNegativePLPosition = {
  ...mockPosition,
  current_price: 140.0,
  market_value: 14000,
  unrealized_pl: -1000,
};

const mockShortPosition = {
  ...mockPosition,
  side: 'short' as const,
  qty: -50,
};

describe('QuickTradeDialog', () => {
  const mockOnOpenChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePlaceOrder.mockReturnValue({
      mutateAsync: mockMutateAsync,
      isPending: false,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // Helper to get side buttons (not the submit button)
  const getSideButtons = () => {
    const buttons = screen.getAllByRole('button');
    const buyButton = buttons.find(btn => btn.textContent === 'Buy' || btn.textContent?.includes('Buy') && !btn.textContent?.includes('shares'));
    const sellButton = buttons.find(btn => btn.textContent === 'Sell' || btn.textContent?.includes('Sell') && !btn.textContent?.includes('shares'));
    return { buyButton, sellButton };
  };

  // Null position tests
  describe('Null position', () => {
    it('should return null when position is null', () => {
      const { container } = render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={null}
          tradingMode="paper"
        />
      );
      expect(container.firstChild).toBeNull();
    });

    it('should call usePlaceOrder even when position is null', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={null}
          tradingMode="paper"
        />
      );
      // Hook should still be called at component level
      expect(mockUsePlaceOrder).toHaveBeenCalledWith('paper');
    });
  });

  // Dialog behavior tests
  describe('Dialog behavior', () => {
    it('should show dialog when open is true', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('should display dialog title with symbol', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      expect(screen.getByText(/Trade AAPL/)).toBeInTheDocument();
    });

    it('should display paper badge for paper trading mode', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      expect(screen.getByText('Paper')).toBeInTheDocument();
    });

    it('should display live badge for live trading mode', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="live"
        />
      );
      expect(screen.getByText('Live')).toBeInTheDocument();
    });

    it('should display position description', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      expect(screen.getByText(/100 shares \(long\)/)).toBeInTheDocument();
    });
  });

  // Position summary tests
  describe('Position summary', () => {
    it('should display current price', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      expect(screen.getByText('$175.50')).toBeInTheDocument();
    });

    it('should display current price label', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      expect(screen.getByText('Current Price')).toBeInTheDocument();
    });

    it('should display unrealized P&L', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      expect(screen.getByText('$2550.00')).toBeInTheDocument();
    });

    it('should display unrealized P&L label', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      expect(screen.getByText('Unrealized P&L')).toBeInTheDocument();
    });

    it('should show green styling for positive P&L', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      const plElement = screen.getByText('$2550.00');
      expect(plElement.closest('p')).toHaveClass('text-green-600');
    });

    it('should show red styling for negative P&L', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockNegativePLPosition}
          tradingMode="paper"
        />
      );
      const plElement = screen.getByText('$-1000.00');
      expect(plElement.closest('p')).toHaveClass('text-red-600');
    });
  });

  // Side selection tests
  describe('Side selection', () => {
    it('should display side label', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      expect(screen.getByText('Side')).toBeInTheDocument();
    });

    it('should have buy and sell buttons', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      const { buyButton, sellButton } = getSideButtons();
      expect(buyButton).toBeInTheDocument();
      expect(sellButton).toBeInTheDocument();
    });

    it('should default to sell side when defaultSide not provided', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      const { sellButton } = getSideButtons();
      expect(sellButton).toHaveClass('bg-red-600');
    });

    it('should use defaultSide=buy when provided', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
          defaultSide="buy"
        />
      );
      const { buyButton } = getSideButtons();
      expect(buyButton).toHaveClass('bg-green-600');
    });

    it('should allow switching to buy side', async () => {
      const user = userEvent.setup();
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );

      const { buyButton } = getSideButtons();
      await user.click(buyButton!);

      expect(buyButton).toHaveClass('bg-green-600');
    });

    it('should allow switching to sell side', async () => {
      const user = userEvent.setup();
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
          defaultSide="buy"
        />
      );

      const { sellButton } = getSideButtons();
      await user.click(sellButton!);

      expect(sellButton).toHaveClass('bg-red-600');
    });
  });

  // Quantity input tests
  describe('Quantity input', () => {
    it('should have quantity label', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      expect(screen.getByText('Quantity')).toBeInTheDocument();
    });

    it('should have quantity input field', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      expect(screen.getByPlaceholderText('Enter quantity')).toBeInTheDocument();
    });

    it('should allow entering custom quantity', async () => {
      const user = userEvent.setup();
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );

      const quantityInput = screen.getByPlaceholderText('Enter quantity');
      await user.clear(quantityInput);
      await user.type(quantityInput, '50');

      expect(quantityInput).toHaveValue(50);
    });

    it('should show Sell All button for long position with sell side', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      expect(screen.getByRole('button', { name: 'Sell All' })).toBeInTheDocument();
    });

    it('should not show Sell All button for buy side', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
          defaultSide="buy"
        />
      );
      expect(screen.queryByRole('button', { name: 'Sell All' })).not.toBeInTheDocument();
    });

    it('should fill quantity on Sell All click', async () => {
      const user = userEvent.setup();
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );

      const sellAllButton = screen.getByRole('button', { name: 'Sell All' });
      await user.click(sellAllButton);

      const quantityInput = screen.getByPlaceholderText('Enter quantity');
      expect(quantityInput).toHaveValue(100);
    });
  });

  // Order type tests
  describe('Order type selection', () => {
    it('should have order type label', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      expect(screen.getByText('Order Type')).toBeInTheDocument();
    });

    it('should default to market order type', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      expect(screen.getByText('Market')).toBeInTheDocument();
    });

    it('should have order type select combobox', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    it('should hide limit price input for market orders', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      expect(screen.queryByPlaceholderText('Enter limit price')).not.toBeInTheDocument();
    });
  });

  // Estimated value tests
  describe('Estimated value', () => {
    it('should not show estimated value without quantity', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      expect(screen.queryByText('Estimated Value')).not.toBeInTheDocument();
    });

    it('should show estimated value when quantity entered', async () => {
      const user = userEvent.setup();
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );

      const quantityInput = screen.getByPlaceholderText('Enter quantity');
      await user.type(quantityInput, '10');

      expect(screen.getByText('Estimated Value')).toBeInTheDocument();
      // 10 * 175.5 = 1755
      expect(screen.getByText('$1755.00')).toBeInTheDocument();
    });
  });

  // Submit button tests
  describe('Submit button', () => {
    it('should be disabled without quantity', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      // Find the submit button by looking for text pattern
      const submitButton = screen.getByRole('button', { name: /\d+ shares$/ });
      expect(submitButton).toBeDisabled();
    });

    it('should be enabled with valid quantity', async () => {
      const user = userEvent.setup();
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );

      const quantityInput = screen.getByPlaceholderText('Enter quantity');
      await user.type(quantityInput, '10');

      const submitButton = screen.getByRole('button', { name: /Sell 10 shares/ });
      expect(submitButton).not.toBeDisabled();
    });

    it('should show buy text when buy side selected', async () => {
      const user = userEvent.setup();
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
          defaultSide="buy"
        />
      );

      const quantityInput = screen.getByPlaceholderText('Enter quantity');
      await user.type(quantityInput, '10');

      expect(screen.getByRole('button', { name: /Buy 10 shares/ })).toBeInTheDocument();
    });

    it('should show loading state when placing order', () => {
      mockUsePlaceOrder.mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: true,
      });

      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );

      expect(screen.getByText('Placing Order...')).toBeInTheDocument();
    });
  });

  // Order submission tests
  describe('Order submission', () => {
    it('should place market order successfully', async () => {
      const user = userEvent.setup();
      mockMutateAsync.mockResolvedValue({ success: true });

      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );

      const quantityInput = screen.getByPlaceholderText('Enter quantity');
      await user.type(quantityInput, '10');

      const submitButton = screen.getByRole('button', { name: /Sell 10 shares/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith({
          ticker: 'AAPL',
          side: 'sell',
          quantity: 10,
          order_type: 'market',
          limit_price: undefined,
        });
      });
    });

    it('should show success toast after order placed', async () => {
      const user = userEvent.setup();
      mockMutateAsync.mockResolvedValue({ success: true });

      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );

      const quantityInput = screen.getByPlaceholderText('Enter quantity');
      await user.type(quantityInput, '10');

      const submitButton = screen.getByRole('button', { name: /Sell 10 shares/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockToastSuccess).toHaveBeenCalledWith('SELL order placed for 10 shares of AAPL');
      });
    });

    it('should close dialog after successful order', async () => {
      const user = userEvent.setup();
      mockMutateAsync.mockResolvedValue({ success: true });

      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );

      const quantityInput = screen.getByPlaceholderText('Enter quantity');
      await user.type(quantityInput, '10');

      const submitButton = screen.getByRole('button', { name: /Sell 10 shares/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockOnOpenChange).toHaveBeenCalledWith(false);
      });
    });

    it('should show error toast on order failure', async () => {
      const user = userEvent.setup();
      mockMutateAsync.mockRejectedValue(new Error('Insufficient funds'));

      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );

      const quantityInput = screen.getByPlaceholderText('Enter quantity');
      await user.type(quantityInput, '10');

      const submitButton = screen.getByRole('button', { name: /Sell 10 shares/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith('Insufficient funds');
      });
    });

    it('should show default error message for non-Error exceptions', async () => {
      const user = userEvent.setup();
      mockMutateAsync.mockRejectedValue('Unknown error');

      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );

      const quantityInput = screen.getByPlaceholderText('Enter quantity');
      await user.type(quantityInput, '10');

      const submitButton = screen.getByRole('button', { name: /Sell 10 shares/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith('Failed to place order');
      });
    });

    it('should place buy order correctly', async () => {
      const user = userEvent.setup();
      mockMutateAsync.mockResolvedValue({ success: true });

      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
          defaultSide="buy"
        />
      );

      const quantityInput = screen.getByPlaceholderText('Enter quantity');
      await user.type(quantityInput, '5');

      const submitButton = screen.getByRole('button', { name: /Buy 5 shares/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith({
          ticker: 'AAPL',
          side: 'buy',
          quantity: 5,
          order_type: 'market',
          limit_price: undefined,
        });
      });
    });
  });

  // Cancel button tests
  describe('Cancel button', () => {
    it('should have cancel button', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
    });

    it('should close dialog on cancel click', async () => {
      const user = userEvent.setup();
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );

      const cancelButton = screen.getByRole('button', { name: 'Cancel' });
      await user.click(cancelButton);

      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });
  });

  // Trading mode tests
  describe('Trading mode', () => {
    it('should call usePlaceOrder with paper mode', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );
      expect(mockUsePlaceOrder).toHaveBeenCalledWith('paper');
    });

    it('should call usePlaceOrder with live mode', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="live"
        />
      );
      expect(mockUsePlaceOrder).toHaveBeenCalledWith('live');
    });
  });

  // Short position tests
  describe('Short position handling', () => {
    it('should display short position description', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockShortPosition}
          tradingMode="paper"
        />
      );
      expect(screen.getByText(/50 shares \(short\)/)).toBeInTheDocument();
    });

    it('should not show Sell All button for short position', () => {
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockShortPosition}
          tradingMode="paper"
        />
      );
      expect(screen.queryByRole('button', { name: 'Sell All' })).not.toBeInTheDocument();
    });
  });

  // Submit button styling tests
  describe('Submit button styling', () => {
    it('should have green background for buy orders', async () => {
      const user = userEvent.setup();
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
          defaultSide="buy"
        />
      );

      const quantityInput = screen.getByPlaceholderText('Enter quantity');
      await user.type(quantityInput, '10');

      const submitButton = screen.getByRole('button', { name: /Buy 10 shares/ });
      expect(submitButton).toHaveClass('bg-green-600');
    });

    it('should have red background for sell orders', async () => {
      const user = userEvent.setup();
      render(
        <QuickTradeDialog
          open={true}
          onOpenChange={mockOnOpenChange}
          position={mockPosition}
          tradingMode="paper"
        />
      );

      const quantityInput = screen.getByPlaceholderText('Enter quantity');
      await user.type(quantityInput, '10');

      const submitButton = screen.getByRole('button', { name: /Sell 10 shares/ });
      expect(submitButton).toHaveClass('bg-red-600');
    });
  });
});
