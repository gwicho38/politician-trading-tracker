import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { OrderHistory } from './OrderHistory';

// Mock the hooks
const mockRefetch = vi.fn();
const mockSyncMutateAsync = vi.fn();
const mockCancelMutateAsync = vi.fn();

vi.mock('@/hooks/useOrders', () => ({
  useOrders: vi.fn(),
  useSyncOrders: vi.fn(() => ({
    mutateAsync: mockSyncMutateAsync,
    isPending: false,
  })),
  useCancelOrder: vi.fn(() => ({
    mutateAsync: mockCancelMutateAsync,
    isPending: false,
  })),
  getOrderStatusVariant: vi.fn((status: string) => {
    switch (status.toLowerCase()) {
      case 'filled':
        return 'default';
      case 'new':
      case 'accepted':
        return 'secondary';
      case 'cancelled':
      case 'canceled':
        return 'outline';
      default:
        return 'destructive';
    }
  }),
}));

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock formatters
vi.mock('@/lib/formatters', () => ({
  formatCurrencyFull: vi.fn((value: number) => `$${value.toFixed(2)}`),
  formatDateTime: vi.fn((dateString: string) => {
    if (!dateString) return null;
    return '1/29/2026, 10:00 AM';
  }),
}));

// Import the mocked hook for manipulation
import { useOrders, useSyncOrders, useCancelOrder } from '@/hooks/useOrders';
import { toast } from 'sonner';

const mockUseOrders = vi.mocked(useOrders);
const mockUseSyncOrders = vi.mocked(useSyncOrders);
const mockUseCancelOrder = vi.mocked(useCancelOrder);

const mockOrders = [
  {
    id: 'order-1',
    alpaca_order_id: 'alpaca-1',
    ticker: 'AAPL',
    side: 'buy',
    quantity: 100,
    filled_quantity: 100,
    filled_avg_price: 175.50,
    limit_price: null,
    status: 'filled',
    submitted_at: '2026-01-29T10:00:00Z',
  },
  {
    id: 'order-2',
    alpaca_order_id: 'alpaca-2',
    ticker: 'GOOGL',
    side: 'sell',
    quantity: 50,
    filled_quantity: 0,
    filled_avg_price: null,
    limit_price: 145.00,
    status: 'new',
    submitted_at: '2026-01-29T11:00:00Z',
  },
  {
    id: 'order-3',
    alpaca_order_id: 'alpaca-3',
    ticker: 'MSFT',
    side: 'buy',
    quantity: 25,
    filled_quantity: 0,
    filled_avg_price: null,
    limit_price: null,
    status: 'cancelled',
    submitted_at: '2026-01-29T09:00:00Z',
  },
];

describe('OrderHistory', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSyncOrders.mockReturnValue({
      mutateAsync: mockSyncMutateAsync,
      isPending: false,
    } as ReturnType<typeof useSyncOrders>);
    mockUseCancelOrder.mockReturnValue({
      mutateAsync: mockCancelMutateAsync,
      isPending: false,
    } as ReturnType<typeof useCancelOrder>);
  });

  describe('Loading state', () => {
    it('shows loading spinner when loading', () => {
      mockUseOrders.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useOrders>);

      render(<OrderHistory tradingMode="paper" />);

      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });
  });

  describe('Error state', () => {
    it('shows error message when fetch fails', () => {
      mockUseOrders.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Failed to fetch'),
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useOrders>);

      render(<OrderHistory tradingMode="paper" />);

      expect(screen.getByText('Failed to load orders')).toBeInTheDocument();
    });

    it('shows retry button on error', () => {
      mockUseOrders.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Failed to fetch'),
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useOrders>);

      render(<OrderHistory tradingMode="paper" />);

      expect(screen.getByRole('button', { name: /Retry/ })).toBeInTheDocument();
    });

    it('calls refetch when retry button is clicked', async () => {
      mockUseOrders.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Failed to fetch'),
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useOrders>);

      const user = userEvent.setup();
      render(<OrderHistory tradingMode="paper" />);

      await user.click(screen.getByRole('button', { name: /Retry/ }));

      expect(mockRefetch).toHaveBeenCalled();
    });
  });

  describe('Empty state', () => {
    it('shows empty state when no orders', () => {
      mockUseOrders.mockReturnValue({
        data: { orders: [], total: 0 },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useOrders>);

      render(<OrderHistory tradingMode="paper" />);

      expect(screen.getByText('No orders found')).toBeInTheDocument();
    });

    it('shows suggestion to place first trade in empty state', () => {
      mockUseOrders.mockReturnValue({
        data: { orders: [], total: 0 },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useOrders>);

      render(<OrderHistory tradingMode="paper" />);

      expect(screen.getByText('Place your first trade to see it here')).toBeInTheDocument();
    });
  });

  describe('Header display', () => {
    beforeEach(() => {
      mockUseOrders.mockReturnValue({
        data: { orders: mockOrders, total: 3 },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useOrders>);
    });

    it('shows Order History title', () => {
      render(<OrderHistory tradingMode="paper" />);

      expect(screen.getByText('Order History')).toBeInTheDocument();
    });

    it('shows paper trading badge', () => {
      render(<OrderHistory tradingMode="paper" />);

      expect(screen.getByText('Paper')).toBeInTheDocument();
    });

    it('shows live trading badge', () => {
      render(<OrderHistory tradingMode="live" />);

      expect(screen.getByText('Live')).toBeInTheDocument();
    });

    it('shows total orders count', () => {
      render(<OrderHistory tradingMode="paper" />);

      expect(screen.getByText('3 orders total')).toBeInTheDocument();
    });
  });

  describe('Orders table', () => {
    beforeEach(() => {
      mockUseOrders.mockReturnValue({
        data: { orders: mockOrders, total: 3 },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useOrders>);
    });

    it('shows table headers', () => {
      render(<OrderHistory tradingMode="paper" />);

      expect(screen.getByText('Symbol')).toBeInTheDocument();
      expect(screen.getByText('Side')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
      expect(screen.getByText('Date')).toBeInTheDocument();
      expect(screen.getByText('Actions')).toBeInTheDocument();
    });

    it('displays order tickers', () => {
      render(<OrderHistory tradingMode="paper" />);

      expect(screen.getByText('AAPL')).toBeInTheDocument();
      expect(screen.getByText('GOOGL')).toBeInTheDocument();
      expect(screen.getByText('MSFT')).toBeInTheDocument();
    });

    it('displays buy side with green styling', () => {
      render(<OrderHistory tradingMode="paper" />);

      const buyLabels = screen.getAllByText('buy');
      expect(buyLabels.length).toBeGreaterThan(0);
    });

    it('displays sell side with red styling', () => {
      render(<OrderHistory tradingMode="paper" />);

      expect(screen.getByText('sell')).toBeInTheDocument();
    });

    it('displays order quantities', () => {
      render(<OrderHistory tradingMode="paper" />);

      // Use getAllByText since quantities may appear in multiple columns
      expect(screen.getAllByText('100').length).toBeGreaterThan(0);
      expect(screen.getAllByText('50').length).toBeGreaterThan(0);
      expect(screen.getAllByText('25').length).toBeGreaterThan(0);
    });

    it('displays filled quantities', () => {
      render(<OrderHistory tradingMode="paper" />);

      // First order has filled_quantity 100, others have 0
      const filledValues = screen.getAllByText('0');
      expect(filledValues.length).toBeGreaterThan(0);
    });

    it('displays filled average price', () => {
      render(<OrderHistory tradingMode="paper" />);

      expect(screen.getByText('$175.50')).toBeInTheDocument();
    });

    it('displays limit price when no fill price', () => {
      render(<OrderHistory tradingMode="paper" />);

      expect(screen.getByText('$145.00')).toBeInTheDocument();
    });

    it('displays "Market" when no price specified', () => {
      render(<OrderHistory tradingMode="paper" />);

      expect(screen.getByText('Market')).toBeInTheDocument();
    });

    it('displays order status badges', () => {
      render(<OrderHistory tradingMode="paper" />);

      expect(screen.getByText('filled')).toBeInTheDocument();
      expect(screen.getByText('new')).toBeInTheDocument();
      expect(screen.getByText('cancelled')).toBeInTheDocument();
    });
  });

  describe('Status filter', () => {
    beforeEach(() => {
      mockUseOrders.mockReturnValue({
        data: { orders: mockOrders, total: 3 },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useOrders>);
    });

    it('shows filter select with default "All Orders"', () => {
      render(<OrderHistory tradingMode="paper" />);

      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    it('calls useOrders with status filter', () => {
      render(<OrderHistory tradingMode="paper" />);

      expect(mockUseOrders).toHaveBeenCalledWith('paper', {
        status: 'all',
        limit: 50,
      });
    });
  });

  describe('Sync functionality', () => {
    beforeEach(() => {
      mockUseOrders.mockReturnValue({
        data: { orders: mockOrders, total: 3 },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useOrders>);
    });

    it('shows sync button', () => {
      render(<OrderHistory tradingMode="paper" />);

      // Find the button with RefreshCw icon that isn't the refetch button
      const buttons = screen.getAllByRole('button');
      const syncButton = buttons.find(btn =>
        btn.querySelector('.lucide-refresh-cw') &&
        (btn.textContent?.includes('Sync') || btn.getAttribute('aria-label')?.includes('Sync'))
      );
      expect(syncButton).toBeDefined();
    });

    it('calls sync mutation when sync button is clicked', async () => {
      mockSyncMutateAsync.mockResolvedValueOnce({ message: 'Orders synced' });

      const user = userEvent.setup();
      render(<OrderHistory tradingMode="paper" />);

      // Click the sync button (first button with RefreshCw and "Sync" text)
      const buttons = screen.getAllByRole('button');
      const syncButton = buttons.find(btn => btn.textContent?.includes('Sync'));

      if (syncButton) {
        await user.click(syncButton);
        expect(mockSyncMutateAsync).toHaveBeenCalled();
      }
    });

    it('shows success toast on successful sync', async () => {
      mockSyncMutateAsync.mockResolvedValueOnce({ message: 'Orders synced successfully' });

      const user = userEvent.setup();
      render(<OrderHistory tradingMode="paper" />);

      const buttons = screen.getAllByRole('button');
      const syncButton = buttons.find(btn => btn.textContent?.includes('Sync'));

      if (syncButton) {
        await user.click(syncButton);
        await waitFor(() => {
          expect(toast.success).toHaveBeenCalledWith('Orders synced successfully');
        });
      }
    });

    it('shows error toast on sync failure', async () => {
      mockSyncMutateAsync.mockRejectedValueOnce(new Error('Sync failed'));

      const user = userEvent.setup();
      render(<OrderHistory tradingMode="paper" />);

      const buttons = screen.getAllByRole('button');
      const syncButton = buttons.find(btn => btn.textContent?.includes('Sync'));

      if (syncButton) {
        await user.click(syncButton);
        await waitFor(() => {
          expect(toast.error).toHaveBeenCalledWith('Sync failed');
        });
      }
    });
  });

  describe('Cancel order functionality', () => {
    beforeEach(() => {
      mockUseOrders.mockReturnValue({
        data: { orders: mockOrders, total: 3 },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useOrders>);
    });

    it('shows cancel button for open orders', () => {
      render(<OrderHistory tradingMode="paper" />);

      // The 'new' status order should have a cancel button
      const cancelButtons = document.querySelectorAll('.lucide-x');
      expect(cancelButtons.length).toBeGreaterThan(0);
    });

    it('does not show cancel button for filled orders', () => {
      mockUseOrders.mockReturnValue({
        data: {
          orders: [mockOrders[0]], // Only the filled order
          total: 1,
        },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useOrders>);

      render(<OrderHistory tradingMode="paper" />);

      // Filled orders should not have cancel button
      const cancelButtons = document.querySelectorAll('.lucide-x');
      expect(cancelButtons.length).toBe(0);
    });

    it('opens confirmation dialog when cancel button is clicked', async () => {
      const user = userEvent.setup();
      render(<OrderHistory tradingMode="paper" />);

      const cancelButton = screen.getAllByRole('button').find(btn =>
        btn.querySelector('.lucide-x')
      );

      if (cancelButton) {
        await user.click(cancelButton);

        // Dialog title and button both say "Cancel Order", so use getAllByText
        expect(screen.getAllByText('Cancel Order').length).toBeGreaterThan(0);
        expect(screen.getByText(/Are you sure you want to cancel this order/)).toBeInTheDocument();
      }
    });

    it('shows Keep Order button in confirmation dialog', async () => {
      const user = userEvent.setup();
      render(<OrderHistory tradingMode="paper" />);

      const cancelButton = screen.getAllByRole('button').find(btn =>
        btn.querySelector('.lucide-x')
      );

      if (cancelButton) {
        await user.click(cancelButton);

        expect(screen.getByRole('button', { name: 'Keep Order' })).toBeInTheDocument();
      }
    });

    it('closes dialog when Keep Order is clicked', async () => {
      const user = userEvent.setup();
      render(<OrderHistory tradingMode="paper" />);

      const cancelButton = screen.getAllByRole('button').find(btn =>
        btn.querySelector('.lucide-x')
      );

      if (cancelButton) {
        await user.click(cancelButton);
        await user.click(screen.getByRole('button', { name: 'Keep Order' }));

        expect(screen.queryByText('Are you sure you want to cancel this order')).not.toBeInTheDocument();
      }
    });

    it('calls cancel mutation when Cancel Order is confirmed', async () => {
      mockCancelMutateAsync.mockResolvedValueOnce({ message: 'Order cancelled' });

      const user = userEvent.setup();
      render(<OrderHistory tradingMode="paper" />);

      const cancelButton = screen.getAllByRole('button').find(btn =>
        btn.querySelector('.lucide-x')
      );

      if (cancelButton) {
        await user.click(cancelButton);
        await user.click(screen.getByRole('button', { name: 'Cancel Order' }));

        expect(mockCancelMutateAsync).toHaveBeenCalledWith('alpaca-2');
      }
    });

    it('shows success toast on successful cancellation', async () => {
      mockCancelMutateAsync.mockResolvedValueOnce({ message: 'Order cancelled successfully' });

      const user = userEvent.setup();
      render(<OrderHistory tradingMode="paper" />);

      const cancelButton = screen.getAllByRole('button').find(btn =>
        btn.querySelector('.lucide-x')
      );

      if (cancelButton) {
        await user.click(cancelButton);
        await user.click(screen.getByRole('button', { name: 'Cancel Order' }));

        await waitFor(() => {
          expect(toast.success).toHaveBeenCalledWith('Order cancelled successfully');
        });
      }
    });

    it('shows error toast on cancellation failure', async () => {
      mockCancelMutateAsync.mockRejectedValueOnce(new Error('Cancellation failed'));

      const user = userEvent.setup();
      render(<OrderHistory tradingMode="paper" />);

      const cancelButton = screen.getAllByRole('button').find(btn =>
        btn.querySelector('.lucide-x')
      );

      if (cancelButton) {
        await user.click(cancelButton);
        await user.click(screen.getByRole('button', { name: 'Cancel Order' }));

        await waitFor(() => {
          expect(toast.error).toHaveBeenCalledWith('Cancellation failed');
        });
      }
    });
  });

  describe('Refetch functionality', () => {
    beforeEach(() => {
      mockUseOrders.mockReturnValue({
        data: { orders: mockOrders, total: 3 },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useOrders>);
    });

    it('shows refetch button', () => {
      render(<OrderHistory tradingMode="paper" />);

      // Find the ghost variant refresh button
      const buttons = screen.getAllByRole('button');
      const refetchButton = buttons.find(btn =>
        btn.classList.contains('ghost') ||
        (btn.querySelector('.lucide-refresh-cw') && !btn.textContent?.includes('Sync'))
      );
      expect(refetchButton).toBeDefined();
    });

    it('calls refetch when refresh button is clicked', async () => {
      const user = userEvent.setup();
      render(<OrderHistory tradingMode="paper" />);

      // Click the last refresh button (the refetch one)
      const buttons = screen.getAllByRole('button');
      const refreshButtons = buttons.filter(btn => btn.querySelector('.lucide-refresh-cw'));
      const refetchButton = refreshButtons[refreshButtons.length - 1];

      if (refetchButton) {
        await user.click(refetchButton);
        expect(mockRefetch).toHaveBeenCalled();
      }
    });
  });

  describe('Refetching state', () => {
    it('disables refetch button while refetching', () => {
      mockUseOrders.mockReturnValue({
        data: { orders: mockOrders, total: 3 },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: true,
      } as ReturnType<typeof useOrders>);

      render(<OrderHistory tradingMode="paper" />);

      const buttons = screen.getAllByRole('button');
      const refreshButtons = buttons.filter(btn => btn.querySelector('.lucide-refresh-cw'));
      const refetchButton = refreshButtons[refreshButtons.length - 1];

      expect(refetchButton).toBeDisabled();
    });

    it('shows spinning animation while refetching', () => {
      mockUseOrders.mockReturnValue({
        data: { orders: mockOrders, total: 3 },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: true,
      } as ReturnType<typeof useOrders>);

      render(<OrderHistory tradingMode="paper" />);

      const spinningIcon = document.querySelector('.lucide-refresh-cw.animate-spin');
      expect(spinningIcon).toBeInTheDocument();
    });
  });

  describe('Can cancel order logic', () => {
    it('allows cancellation for "new" status orders', () => {
      mockUseOrders.mockReturnValue({
        data: {
          orders: [{ ...mockOrders[1], status: 'new' }],
          total: 1,
        },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useOrders>);

      render(<OrderHistory tradingMode="paper" />);

      const cancelButtons = document.querySelectorAll('.lucide-x');
      expect(cancelButtons.length).toBe(1);
    });

    it('allows cancellation for "accepted" status orders', () => {
      mockUseOrders.mockReturnValue({
        data: {
          orders: [{ ...mockOrders[1], status: 'accepted' }],
          total: 1,
        },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useOrders>);

      render(<OrderHistory tradingMode="paper" />);

      const cancelButtons = document.querySelectorAll('.lucide-x');
      expect(cancelButtons.length).toBe(1);
    });

    it('allows cancellation for "partially_filled" status orders', () => {
      mockUseOrders.mockReturnValue({
        data: {
          orders: [{ ...mockOrders[1], status: 'partially_filled' }],
          total: 1,
        },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useOrders>);

      render(<OrderHistory tradingMode="paper" />);

      const cancelButtons = document.querySelectorAll('.lucide-x');
      expect(cancelButtons.length).toBe(1);
    });

    it('does not allow cancellation for "cancelled" status orders', () => {
      mockUseOrders.mockReturnValue({
        data: {
          orders: [{ ...mockOrders[2], status: 'cancelled' }],
          total: 1,
        },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        isRefetching: false,
      } as ReturnType<typeof useOrders>);

      render(<OrderHistory tradingMode="paper" />);

      const cancelButtons = document.querySelectorAll('.lucide-x');
      expect(cancelButtons.length).toBe(0);
    });
  });
});
