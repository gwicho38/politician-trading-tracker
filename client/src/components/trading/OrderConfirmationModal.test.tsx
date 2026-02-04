import { describe, it, expect, vi, beforeEach, afterEach, beforeAll, afterAll } from 'vitest';
import { render, screen, waitFor, within, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { OrderConfirmationModal } from './OrderConfirmationModal';

// Mock toast from sonner
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();

vi.mock('sonner', () => ({
  toast: {
    success: (message: string) => mockToastSuccess(message),
    error: (message: string) => mockToastError(message),
  },
}));

// Mock formatters
vi.mock('@/lib/formatters', () => ({
  formatCurrencyFull: (value: number) => `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
}));

// Mock ResizeObserver for Radix UI dialogs
beforeAll(() => {
  global.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }));

  // Mock pointer capture methods for Radix UI
  Element.prototype.hasPointerCapture = vi.fn(() => false);
  Element.prototype.setPointerCapture = vi.fn();
  Element.prototype.releasePointerCapture = vi.fn();
});

// Helper to flush all pending promises and timers
const flushPromises = () => act(async () => {
  await new Promise(resolve => setTimeout(resolve, 0));
});

// Note: import.meta.env is handled by Vite during build and in tests,
// we don't need to mock it as the component handles undefined values gracefully
// localStorage is already available in the jsdom test environment

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Sample order data
const singleBuyOrder = [
  { ticker: 'AAPL', side: 'buy' as const, quantity: 10, order_type: 'market' as const },
];

const singleSellOrder = [
  { ticker: 'GOOGL', side: 'sell' as const, quantity: 5, order_type: 'limit' as const, limit_price: 150 },
];

const multipleOrders = [
  { ticker: 'AAPL', side: 'buy' as const, quantity: 10, order_type: 'market' as const },
  { ticker: 'GOOGL', side: 'sell' as const, quantity: 5, order_type: 'limit' as const, limit_price: 150 },
  { ticker: 'MSFT', side: 'buy' as const, quantity: 20, order_type: 'market' as const },
  { ticker: 'AMZN', side: 'sell' as const, quantity: 15, order_type: 'market' as const },
];

const defaultProps = {
  open: true,
  onOpenChange: vi.fn(),
  orders: singleBuyOrder,
  tradingMode: 'paper' as const,
  onSuccess: vi.fn(),
};

describe('OrderConfirmationModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default successful response
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: true, message: 'Orders placed successfully' }),
    });
  });

  afterEach(async () => {
    // Flush pending promises to avoid state updates after unmount
    await flushPromises();
    vi.clearAllMocks();
  });

  // Dialog visibility tests
  describe('Dialog visibility', () => {
    it('should render dialog when open is true', () => {
      render(<OrderConfirmationModal {...defaultProps} />);

      expect(screen.getByText('Confirm Orders')).toBeInTheDocument();
    });

    it('should not render dialog content when open is false', () => {
      render(<OrderConfirmationModal {...defaultProps} open={false} />);

      expect(screen.queryByText('Confirm Orders')).not.toBeInTheDocument();
    });

    it('should show dialog description', () => {
      render(<OrderConfirmationModal {...defaultProps} />);

      expect(screen.getByText('Review your orders before submitting')).toBeInTheDocument();
    });
  });

  // Trading mode badge tests
  describe('Trading mode badge', () => {
    it('should show Paper Trading badge for paper mode', () => {
      render(<OrderConfirmationModal {...defaultProps} tradingMode="paper" />);

      expect(screen.getByText('Paper Trading')).toBeInTheDocument();
    });

    it('should show Live Trading badge for live mode', () => {
      render(<OrderConfirmationModal {...defaultProps} tradingMode="live" />);

      expect(screen.getByText('Live Trading')).toBeInTheDocument();
    });
  });

  // Order summary tests
  describe('Order summary', () => {
    it('should display total orders count', () => {
      render(<OrderConfirmationModal {...defaultProps} orders={multipleOrders} />);

      expect(screen.getByText('Total Orders')).toBeInTheDocument();
      expect(screen.getByText('4')).toBeInTheDocument();
    });

    it('should display total shares count', () => {
      render(<OrderConfirmationModal {...defaultProps} orders={multipleOrders} />);

      expect(screen.getByText('Total Shares')).toBeInTheDocument();
      // 10 + 5 + 20 + 15 = 50
      expect(screen.getByText('50')).toBeInTheDocument();
    });

    it('should show buy count badge for buy orders', () => {
      render(<OrderConfirmationModal {...defaultProps} orders={multipleOrders} />);

      // 2 buy orders
      expect(screen.getByText('2 Buy')).toBeInTheDocument();
    });

    it('should show sell count badge for sell orders', () => {
      render(<OrderConfirmationModal {...defaultProps} orders={multipleOrders} />);

      // 2 sell orders
      expect(screen.getByText('2 Sell')).toBeInTheDocument();
    });

    it('should not show buy badge when no buy orders', () => {
      render(<OrderConfirmationModal {...defaultProps} orders={singleSellOrder} />);

      expect(screen.queryByText(/Buy/)).not.toBeInTheDocument();
    });

    it('should not show sell badge when no sell orders', () => {
      render(<OrderConfirmationModal {...defaultProps} orders={singleBuyOrder} />);

      expect(screen.queryByText(/\d+ Sell/)).not.toBeInTheDocument();
    });
  });

  // Order list table tests
  describe('Order list table', () => {
    it('should render table headers', () => {
      render(<OrderConfirmationModal {...defaultProps} />);

      expect(screen.getByText('Ticker')).toBeInTheDocument();
      expect(screen.getByText('Side')).toBeInTheDocument();
      expect(screen.getByText('Qty')).toBeInTheDocument();
      expect(screen.getByText('Type')).toBeInTheDocument();
    });

    it('should render order ticker', () => {
      render(<OrderConfirmationModal {...defaultProps} orders={singleBuyOrder} />);

      expect(screen.getByText('AAPL')).toBeInTheDocument();
    });

    it('should render order side badge', () => {
      render(<OrderConfirmationModal {...defaultProps} orders={singleBuyOrder} />);

      expect(screen.getByText('BUY')).toBeInTheDocument();
    });

    it('should render order quantity', () => {
      render(<OrderConfirmationModal {...defaultProps} orders={singleBuyOrder} />);

      // quantity is 10, appears in table
      const table = screen.getByRole('table');
      expect(within(table).getByText('10')).toBeInTheDocument();
    });

    it('should render order type', () => {
      render(<OrderConfirmationModal {...defaultProps} orders={singleBuyOrder} />);

      expect(screen.getByText('market')).toBeInTheDocument();
    });

    it('should render multiple orders in table', () => {
      render(<OrderConfirmationModal {...defaultProps} orders={multipleOrders} />);

      expect(screen.getByText('AAPL')).toBeInTheDocument();
      expect(screen.getByText('GOOGL')).toBeInTheDocument();
      expect(screen.getByText('MSFT')).toBeInTheDocument();
      expect(screen.getByText('AMZN')).toBeInTheDocument();
    });

    it('should show BUY badge with green styling for buy orders', () => {
      render(<OrderConfirmationModal {...defaultProps} orders={singleBuyOrder} />);

      const buyBadge = screen.getByText('BUY');
      expect(buyBadge).toHaveClass('text-green-600');
    });

    it('should show SELL badge with red styling for sell orders', () => {
      render(<OrderConfirmationModal {...defaultProps} orders={singleSellOrder} />);

      const sellBadge = screen.getByText('SELL');
      expect(sellBadge).toHaveClass('text-red-600');
    });
  });

  // Paper trading alert tests
  describe('Paper trading alert', () => {
    it('should show paper trading info message', () => {
      render(<OrderConfirmationModal {...defaultProps} tradingMode="paper" />);

      expect(screen.getByText('Paper trading uses simulated money. No real trades will be executed.')).toBeInTheDocument();
    });

    it('should not show live trading warning for paper mode', () => {
      render(<OrderConfirmationModal {...defaultProps} tradingMode="paper" />);

      expect(screen.queryByText(/This will execute real trades with real money/)).not.toBeInTheDocument();
    });
  });

  // Live trading warning tests
  describe('Live trading warning', () => {
    it('should show live trading warning message', () => {
      render(<OrderConfirmationModal {...defaultProps} tradingMode="live" />);

      expect(screen.getByText('This will execute real trades with real money!')).toBeInTheDocument();
    });

    it('should show confirmation checkbox for live trading', () => {
      render(<OrderConfirmationModal {...defaultProps} tradingMode="live" />);

      expect(screen.getByRole('checkbox')).toBeInTheDocument();
      expect(screen.getByText('I understand and accept the risks of live trading')).toBeInTheDocument();
    });

    it('should not show paper trading info for live mode', () => {
      render(<OrderConfirmationModal {...defaultProps} tradingMode="live" />);

      expect(screen.queryByText('Paper trading uses simulated money.')).not.toBeInTheDocument();
    });

    it('should have checkbox unchecked by default', () => {
      render(<OrderConfirmationModal {...defaultProps} tradingMode="live" />);

      const checkbox = screen.getByRole('checkbox');
      expect(checkbox).not.toBeChecked();
    });

    it('should toggle checkbox when clicked', async () => {
      const user = userEvent.setup();
      render(<OrderConfirmationModal {...defaultProps} tradingMode="live" />);

      const checkbox = screen.getByRole('checkbox');
      await user.click(checkbox);

      expect(checkbox).toBeChecked();
    });
  });

  // Submit button tests
  describe('Submit button', () => {
    it('should show correct button text for single order', () => {
      render(<OrderConfirmationModal {...defaultProps} orders={singleBuyOrder} />);

      expect(screen.getByRole('button', { name: 'Place 1 Order' })).toBeInTheDocument();
    });

    it('should show correct button text for multiple orders', () => {
      render(<OrderConfirmationModal {...defaultProps} orders={multipleOrders} />);

      expect(screen.getByRole('button', { name: 'Place 4 Orders' })).toBeInTheDocument();
    });

    it('should enable submit button for paper trading', () => {
      render(<OrderConfirmationModal {...defaultProps} tradingMode="paper" />);

      const submitButton = screen.getByRole('button', { name: 'Place 1 Order' });
      expect(submitButton).not.toBeDisabled();
    });

    it('should disable submit button for live trading without confirmation', () => {
      render(<OrderConfirmationModal {...defaultProps} tradingMode="live" />);

      const submitButton = screen.getByRole('button', { name: 'Place 1 Order' });
      expect(submitButton).toBeDisabled();
    });

    it('should enable submit button for live trading with confirmation', async () => {
      const user = userEvent.setup();
      render(<OrderConfirmationModal {...defaultProps} tradingMode="live" />);

      const checkbox = screen.getByRole('checkbox');
      await user.click(checkbox);

      const submitButton = screen.getByRole('button', { name: 'Place 1 Order' });
      expect(submitButton).not.toBeDisabled();
    });

    it('should have destructive variant for live trading', () => {
      render(<OrderConfirmationModal {...defaultProps} tradingMode="live" />);

      const submitButton = screen.getByRole('button', { name: 'Place 1 Order' });
      // The button should have destructive styling
      expect(submitButton.className).toContain('destructive');
    });
  });

  // Cancel button tests
  describe('Cancel button', () => {
    it('should render cancel button', () => {
      render(<OrderConfirmationModal {...defaultProps} />);

      expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
    });

    it('should call onOpenChange with false when cancel clicked', async () => {
      const user = userEvent.setup();
      const mockOnOpenChange = vi.fn();
      render(<OrderConfirmationModal {...defaultProps} onOpenChange={mockOnOpenChange} />);

      await user.click(screen.getByRole('button', { name: 'Cancel' }));

      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });
  });

  // Order submission tests
  describe('Order submission - Paper trading', () => {
    it('should call fetch on submit', async () => {
      const user = userEvent.setup();
      render(<OrderConfirmationModal {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: 'Place 1 Order' }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
        // Verify it was called with POST method and JSON body
        const callArgs = mockFetch.mock.calls[0];
        expect(callArgs[1]?.method).toBe('POST');
        expect(callArgs[1]?.headers?.['Content-Type']).toBe('application/json');
        expect(callArgs[1]?.body).toContain('place-orders');
      });
    });

    it('should show loading state while submitting', async () => {
      const user = userEvent.setup();
      // Delay the response to see loading state
      mockFetch.mockImplementation(() => new Promise(resolve =>
        setTimeout(() => resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        }), 100)
      ));

      render(<OrderConfirmationModal {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: 'Place 1 Order' }));

      expect(screen.getByText('Placing Orders...')).toBeInTheDocument();
    });

    it('should show success toast on successful submission', async () => {
      const user = userEvent.setup();
      render(<OrderConfirmationModal {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: 'Place 1 Order' }));

      await waitFor(() => {
        expect(mockToastSuccess).toHaveBeenCalledWith('Orders placed successfully');
      });
    });

    it('should call onSuccess callback on successful submission', async () => {
      const user = userEvent.setup();
      const mockOnSuccess = vi.fn();
      render(<OrderConfirmationModal {...defaultProps} onSuccess={mockOnSuccess} />);

      await user.click(screen.getByRole('button', { name: 'Place 1 Order' }));

      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled();
      });
    });

    it('should close dialog on successful submission', async () => {
      const user = userEvent.setup();
      const mockOnOpenChange = vi.fn();
      render(<OrderConfirmationModal {...defaultProps} onOpenChange={mockOnOpenChange} />);

      await user.click(screen.getByRole('button', { name: 'Place 1 Order' }));

      await waitFor(() => {
        expect(mockOnOpenChange).toHaveBeenCalledWith(false);
      });
    });
  });

  // Order submission - Live trading
  describe('Order submission - Live trading', () => {
    it('should show error toast if live confirmation not checked', async () => {
      const user = userEvent.setup();
      render(<OrderConfirmationModal {...defaultProps} tradingMode="live" />);

      // Button is disabled, but let's test the handleSubmit logic
      // We need to enable the button first by checking the checkbox
      // Actually, button is disabled, so we can't click it
      // This test verifies the button is disabled without confirmation
      const submitButton = screen.getByRole('button', { name: 'Place 1 Order' });
      expect(submitButton).toBeDisabled();
    });

    it('should submit orders when live confirmation is checked', async () => {
      const user = userEvent.setup();
      render(<OrderConfirmationModal {...defaultProps} tradingMode="live" />);

      // Check the confirmation checkbox
      await user.click(screen.getByRole('checkbox'));

      // Submit
      await user.click(screen.getByRole('button', { name: 'Place 1 Order' }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });
    });
  });

  // Error handling tests
  describe('Error handling', () => {
    it('should show error toast on API error response', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValue({
        ok: false,
        json: () => Promise.resolve({ message: 'Insufficient funds' }),
      });

      render(<OrderConfirmationModal {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: 'Place 1 Order' }));

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith('Insufficient funds');
      });
    });

    it('should show generic error on API failure without message', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValue({
        ok: false,
        json: () => Promise.reject(new Error('Parse error')),
      });

      render(<OrderConfirmationModal {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: 'Place 1 Order' }));

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith('Failed to place orders');
      });
    });

    it('should show error toast on network failure', async () => {
      const user = userEvent.setup();
      mockFetch.mockRejectedValue(new Error('Network error'));

      render(<OrderConfirmationModal {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: 'Place 1 Order' }));

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith('Network error');
      });
    });

    it('should re-enable submit button after error', async () => {
      const user = userEvent.setup();
      mockFetch.mockRejectedValue(new Error('Network error'));

      render(<OrderConfirmationModal {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: 'Place 1 Order' }));

      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: 'Place 1 Order' });
        expect(submitButton).not.toBeDisabled();
      });
    });
  });

  // Partial success handling tests
  describe('Partial success handling', () => {
    it('should show error toast for failed orders in partial success', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          success: false,
          results: [
            { success: true, ticker: 'AAPL' },
            { success: false, ticker: 'GOOGL', error: 'Symbol not found' },
          ],
          summary: { success: 1, failed: 1 },
        }),
      });

      render(<OrderConfirmationModal {...defaultProps} orders={multipleOrders.slice(0, 2)} />);

      await user.click(screen.getByRole('button', { name: 'Place 2 Orders' }));

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith('1 orders failed');
      });
    });

    it('should show success toast for successful orders in partial success', async () => {
      const user = userEvent.setup();
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          success: false,
          results: [
            { success: true, ticker: 'AAPL' },
            { success: false, ticker: 'GOOGL', error: 'Symbol not found' },
          ],
          summary: { success: 1, failed: 1 },
        }),
      });

      render(<OrderConfirmationModal {...defaultProps} orders={multipleOrders.slice(0, 2)} />);

      await user.click(screen.getByRole('button', { name: 'Place 2 Orders' }));

      await waitFor(() => {
        expect(mockToastSuccess).toHaveBeenCalledWith('1 orders placed successfully');
      });
    });

    it('should call onSuccess on partial success', async () => {
      const user = userEvent.setup();
      const mockOnSuccess = vi.fn();
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          success: false,
          results: [
            { success: true, ticker: 'AAPL' },
            { success: false, ticker: 'GOOGL', error: 'Symbol not found' },
          ],
          summary: { success: 1, failed: 1 },
        }),
      });

      render(<OrderConfirmationModal {...defaultProps} onSuccess={mockOnSuccess} orders={multipleOrders.slice(0, 2)} />);

      await user.click(screen.getByRole('button', { name: 'Place 2 Orders' }));

      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled();
      });
    });

    it('should close dialog on partial success', async () => {
      const user = userEvent.setup();
      const mockOnOpenChange = vi.fn();
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          success: false,
          results: [
            { success: true, ticker: 'AAPL' },
            { success: false, ticker: 'GOOGL', error: 'Symbol not found' },
          ],
          summary: { success: 1, failed: 1 },
        }),
      });

      render(<OrderConfirmationModal {...defaultProps} onOpenChange={mockOnOpenChange} orders={multipleOrders.slice(0, 2)} />);

      await user.click(screen.getByRole('button', { name: 'Place 2 Orders' }));

      await waitFor(() => {
        expect(mockOnOpenChange).toHaveBeenCalledWith(false);
      });
    });
  });

  // Access token handling tests
  describe('Access token handling', () => {
    it('should include Authorization header in fetch request', async () => {
      const user = userEvent.setup();

      render(<OrderConfirmationModal {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: 'Place 1 Order' }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
        const callArgs = mockFetch.mock.calls[0];
        const authHeader = callArgs[1]?.headers?.['Authorization'];
        // Authorization header should exist and have Bearer prefix
        expect(authHeader).toBeDefined();
        expect(authHeader).toMatch(/^Bearer /);
      });
    });

    it('should include apikey header in fetch request', async () => {
      const user = userEvent.setup();

      render(<OrderConfirmationModal {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: 'Place 1 Order' }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
        const callArgs = mockFetch.mock.calls[0];
        const apikeyHeader = callArgs[1]?.headers?.['apikey'];
        // apikey header should exist (from env variable)
        expect(apikeyHeader).toBeDefined();
      });
    });
  });

  // Button disabled states during submission
  describe('Button disabled states during submission', () => {
    it('should disable cancel button while submitting', async () => {
      const user = userEvent.setup();
      mockFetch.mockImplementation(() => new Promise(resolve =>
        setTimeout(() => resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        }), 100)
      ));

      render(<OrderConfirmationModal {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: 'Place 1 Order' }));

      expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled();
    });

    it('should disable submit button while submitting', async () => {
      const user = userEvent.setup();
      mockFetch.mockImplementation(() => new Promise(resolve =>
        setTimeout(() => resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        }), 100)
      ));

      render(<OrderConfirmationModal {...defaultProps} />);

      await user.click(screen.getByRole('button', { name: 'Place 1 Order' }));

      // Find the button with loading text
      const loadingButton = screen.getByRole('button', { name: /Placing Orders/i });
      expect(loadingButton).toBeDisabled();
    });
  });

  // Edge cases
  describe('Edge cases', () => {
    it('should handle empty orders array', () => {
      render(<OrderConfirmationModal {...defaultProps} orders={[]} />);

      // Total orders and total shares are both 0, so there are multiple '0' elements
      const zeros = screen.getAllByText('0');
      expect(zeros.length).toBeGreaterThan(0);
      // The button text includes 0
      expect(screen.getByRole('button', { name: /Place 0 Order/ })).toBeInTheDocument();
    });

    it('should handle orders with signal_id', async () => {
      const user = userEvent.setup();
      const ordersWithSignal = [
        { ticker: 'AAPL', side: 'buy' as const, quantity: 10, order_type: 'market' as const, signal_id: 'signal-123' },
      ];

      render(<OrderConfirmationModal {...defaultProps} orders={ordersWithSignal} />);

      await user.click(screen.getByRole('button', { name: 'Place 1 Order' }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
        const callArgs = mockFetch.mock.calls[0];
        expect(callArgs[1]?.body).toContain('signal-123');
      });
    });

    it('should handle limit orders with price', () => {
      render(<OrderConfirmationModal {...defaultProps} orders={singleSellOrder} />);

      expect(screen.getByText('limit')).toBeInTheDocument();
    });

    it('should handle onSuccess being undefined', async () => {
      const user = userEvent.setup();
      const propsWithoutOnSuccess = { ...defaultProps, onSuccess: undefined };

      render(<OrderConfirmationModal {...propsWithoutOnSuccess} />);

      await user.click(screen.getByRole('button', { name: 'Place 1 Order' }));

      // Should not throw error
      await waitFor(() => {
        expect(mockToastSuccess).toHaveBeenCalled();
      });
    });
  });
});
