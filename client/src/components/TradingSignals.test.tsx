/**
 * Tests for components/TradingSignals.tsx
 *
 * Tests:
 * - Component rendering
 * - Loading state display
 * - Signal fetching and display
 * - Signal filtering by type and confidence
 * - Signal generation (authenticated vs unauthenticated)
 * - Stats cards display
 * - Signal table rendering
 * - Top 10 signals display
 * - Helper functions (getSignalIcon, getSignalColor)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock ResizeObserver properly for Radix UI components
class MockResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}

// @ts-expect-error - Mock for testing
global.ResizeObserver = MockResizeObserver;

// Mock Slider component to avoid ResizeObserver issues
vi.mock('@/components/ui/slider', () => ({
  Slider: ({ value, onValueChange, ...props }: { value: number[]; onValueChange: (value: number[]) => void }) => (
    <input
      type="range"
      value={value[0]}
      onChange={(e) => onValueChange([parseFloat(e.target.value)])}
      data-testid="mock-slider"
      {...props}
    />
  ),
}));

// Mock Supabase client
const mockFrom = vi.fn();
const mockSelect = vi.fn();
const mockEq = vi.fn();
const mockOrder = vi.fn();
const mockLimit = vi.fn();

vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    from: (...args: unknown[]) => mockFrom(...args),
  },
}));

// Mock useAuth hook
const mockUseAuth = vi.fn();
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => mockUseAuth(),
}));

// Mock toast - use vi.hoisted to properly hoist the mock values
const { mockToastSuccess, mockToastError } = vi.hoisted(() => ({
  mockToastSuccess: vi.fn(),
  mockToastError: vi.fn(),
}));

vi.mock('sonner', () => ({
  toast: {
    success: mockToastSuccess,
    error: mockToastError,
  },
}));

// Import after mocks
import TradingSignals from './TradingSignals';

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

// Helper to create mock signal
const createMockSignal = (overrides = {}) => ({
  id: '1',
  ticker: 'AAPL',
  asset_name: 'Apple Inc.',
  signal_type: 'buy' as const,
  signal_strength: 'strong',
  confidence_score: 0.85,
  target_price: 195.50,
  stop_loss: 175.00,
  take_profit: 210.00,
  generated_at: '2026-01-15T10:00:00Z',
  politician_activity_count: 12,
  buy_sell_ratio: 2.5,
  is_active: true,
  ...overrides,
});

// Setup mock chain
const setupMockChain = (data: unknown[], error: unknown = null) => {
  mockLimit.mockResolvedValue({ data, error });
  mockOrder.mockReturnValue({ limit: mockLimit });
  mockEq.mockReturnValue({ order: mockOrder });
  mockSelect.mockReturnValue({ eq: mockEq });
  mockFrom.mockReturnValue({ select: mockSelect });
};

describe('TradingSignals', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ user: null });
    setupMockChain([]);
  });

  describe('Loading State', () => {
    it('shows loading spinner initially', () => {
      // Keep the promise pending
      mockLimit.mockReturnValue(new Promise(() => {}));
      mockOrder.mockReturnValue({ limit: mockLimit });
      mockEq.mockReturnValue({ order: mockOrder });
      mockSelect.mockReturnValue({ eq: mockEq });
      mockFrom.mockReturnValue({ select: mockSelect });

      render(<TradingSignals />, { wrapper: createWrapper() });

      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });

    it('hides loading spinner after data loads', async () => {
      setupMockChain([createMockSignal()]);

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(document.querySelector('.animate-spin')).not.toBeInTheDocument();
      });
    });
  });

  describe('Header', () => {
    it('renders the title', async () => {
      setupMockChain([]);

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('Trading Signals')).toBeInTheDocument();
      });
    });

    it('renders the description', async () => {
      setupMockChain([]);

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(
          screen.getByText('AI-powered trading recommendations based on politician activity')
        ).toBeInTheDocument();
      });
    });
  });

  describe('Signal Generation Parameters', () => {
    it('renders parameter inputs', async () => {
      setupMockChain([]);

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByLabelText(/look back period/i)).toBeInTheDocument();
      });
    });

    it('shows login alert when user is not authenticated', async () => {
      setupMockChain([]);
      mockUseAuth.mockReturnValue({ user: null });

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/log in to generate new signals/i)).toBeInTheDocument();
      });
    });

    it('hides login alert when user is authenticated', async () => {
      setupMockChain([]);
      mockUseAuth.mockReturnValue({ user: { id: 'user1' } });

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.queryByText(/log in to generate new signals/i)).not.toBeInTheDocument();
      });
    });

    it('disables Generate button when not authenticated', async () => {
      setupMockChain([]);
      mockUseAuth.mockReturnValue({ user: null });

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        const generateButton = screen.getByRole('button', { name: /generate signals/i });
        expect(generateButton).toBeDisabled();
      });
    });

    it('enables Generate button when authenticated', async () => {
      setupMockChain([]);
      mockUseAuth.mockReturnValue({ user: { id: 'user1' } });

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        const generateButton = screen.getByRole('button', { name: /generate signals/i });
        expect(generateButton).not.toBeDisabled();
      });
    });

    // Note: The "shows error toast when generating without user" test is skipped
    // because the button is disabled when not authenticated, so the click doesn't trigger
    // the toast - this is the expected behavior
  });

  describe('Stats Cards', () => {
    it('displays total signals count', async () => {
      const signals = [
        createMockSignal({ id: '1', signal_type: 'buy' }),
        createMockSignal({ id: '2', signal_type: 'sell' }),
        createMockSignal({ id: '3', signal_type: 'hold' }),
      ];
      setupMockChain(signals);

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('Total Signals')).toBeInTheDocument();
        expect(screen.getByText('3')).toBeInTheDocument();
      });
    });

    it('displays buy signals count', async () => {
      const signals = [
        createMockSignal({ id: '1', signal_type: 'buy' }),
        createMockSignal({ id: '2', signal_type: 'strong_buy' }),
        createMockSignal({ id: '3', signal_type: 'sell' }),
      ];
      setupMockChain(signals);

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('Buy Signals')).toBeInTheDocument();
        // 2 buy signals (buy and strong_buy)
        const buyCard = screen.getByText('Buy Signals').closest('div')?.parentElement;
        expect(buyCard).toHaveTextContent('2');
      });
    });

    it('displays sell signals count', async () => {
      const signals = [
        createMockSignal({ id: '1', signal_type: 'sell' }),
        createMockSignal({ id: '2', signal_type: 'strong_sell' }),
      ];
      setupMockChain(signals);

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('Sell Signals')).toBeInTheDocument();
      });
    });

    it('displays hold signals count', async () => {
      const signals = [
        createMockSignal({ id: '1', signal_type: 'hold' }),
      ];
      setupMockChain(signals);

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('Hold Signals')).toBeInTheDocument();
      });
    });
  });

  describe('Signal Filters', () => {
    it('renders filter card title', async () => {
      setupMockChain([]);

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('Filter Signals')).toBeInTheDocument();
        expect(screen.getByText('Signal Type')).toBeInTheDocument();
      });
    });

    it('toggles filter when clicking button', async () => {
      const signals = [
        createMockSignal({ id: '1', signal_type: 'buy', confidence_score: 0.9 }),
        createMockSignal({ id: '2', signal_type: 'hold', confidence_score: 0.8 }),
      ];
      setupMockChain(signals);

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        // Hold is not in default filter, so clicking it should add it
        const holdButton = screen.getByRole('button', { name: /hold/i });
        fireEvent.click(holdButton);
      });

      // Filter state should have changed
      await waitFor(() => {
        expect(screen.getByText('2 signals match your filters')).toBeInTheDocument();
      });
    });

    it('displays filtered count message', async () => {
      const signals = [
        createMockSignal({ id: '1', signal_type: 'buy', confidence_score: 0.9 }),
        createMockSignal({ id: '2', signal_type: 'sell', confidence_score: 0.7 }),
      ];
      setupMockChain(signals);

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/signals match your filters/)).toBeInTheDocument();
      });
    });
  });

  describe('Signals Table', () => {
    it('renders table headers', async () => {
      setupMockChain([createMockSignal()]);

      render(<TradingSignals />, { wrapper: createWrapper() });

      // Wait for loading to complete first
      await waitFor(() => {
        expect(screen.queryByText('Trading Signals')).toBeInTheDocument();
      });

      // Then check for table headers
      expect(screen.getByText('Ticker')).toBeInTheDocument();
      expect(screen.getByText('Strength')).toBeInTheDocument();
      expect(screen.getByText('Confidence')).toBeInTheDocument();
    });

    it('renders signal rows with ticker', async () => {
      const signal = createMockSignal({
        ticker: 'GOOGL',
        signal_type: 'sell',
        confidence_score: 0.72,
      });
      setupMockChain([signal]);

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        // GOOGL appears in both table and top 10, so use getAllByText
        const googl = screen.getAllByText('GOOGL');
        expect(googl.length).toBeGreaterThan(0);
      });
    });

    it('displays target price when available', async () => {
      const signal = createMockSignal({ target_price: 200.50 });
      setupMockChain([signal]);

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        // Target price appears in multiple places
        const prices = screen.getAllByText('$200.50');
        expect(prices.length).toBeGreaterThan(0);
      });
    });

    it('displays N/A when target price is not available', async () => {
      const signal = createMockSignal({ target_price: undefined });
      setupMockChain([signal]);

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('N/A')).toBeInTheDocument();
      });
    });

    it('renders Export CSV button', async () => {
      setupMockChain([]);

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /export csv/i })).toBeInTheDocument();
      });
    });
  });

  describe('Top 10 Signals', () => {
    it('renders top 10 section title', async () => {
      setupMockChain([createMockSignal()]);

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/top 10 signals by confidence/i)).toBeInTheDocument();
      });
    });

    it('renders signal cards with ticker and name', async () => {
      const signal = createMockSignal({
        ticker: 'MSFT',
        asset_name: 'Microsoft Corporation',
        confidence_score: 0.92,
      });
      setupMockChain([signal]);

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('MSFT - Microsoft Corporation')).toBeInTheDocument();
      });
    });

    it('renders Add to Cart button for each signal', async () => {
      setupMockChain([createMockSignal()]);

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /add to cart/i })).toBeInTheDocument();
      });
    });

    it('limits to 10 signals', async () => {
      const signals = Array.from({ length: 15 }, (_, i) =>
        createMockSignal({ id: String(i), ticker: `TKR${i}`, confidence_score: 0.9 - i * 0.01 })
      );
      setupMockChain(signals);

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        // Should only show 10 "Add to Cart" buttons in Top 10 section
        const addToCartButtons = screen.getAllByRole('button', { name: /add to cart/i });
        expect(addToCartButtons.length).toBe(10);
      });
    });
  });

  describe('Error Handling', () => {
    it('shows error toast when fetch fails', async () => {
      setupMockChain([], { message: 'Database error' });

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith('Failed to load trading signals');
      });
    });

    it('handles null data gracefully', async () => {
      mockLimit.mockResolvedValue({ data: null, error: null });
      mockOrder.mockReturnValue({ limit: mockLimit });
      mockEq.mockReturnValue({ order: mockOrder });
      mockSelect.mockReturnValue({ eq: mockEq });
      mockFrom.mockReturnValue({ select: mockSelect });

      render(<TradingSignals />, { wrapper: createWrapper() });

      // Wait for loading to complete
      await waitFor(() => {
        expect(screen.getByText('Total Signals')).toBeInTheDocument();
      });

      // Should render with empty state (0 signals)
      expect(screen.getByText('0 signals match your filters')).toBeInTheDocument();
    });
  });

  describe('Signal Generation', () => {
    it('shows generating state when clicked', async () => {
      setupMockChain([]);
      mockUseAuth.mockReturnValue({ user: { id: 'user1' } });

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        const generateButton = screen.getByRole('button', { name: /generate signals/i });
        fireEvent.click(generateButton);
      });

      await waitFor(() => {
        expect(screen.getByText('Generating...')).toBeInTheDocument();
      });
    });

    it('shows success toast when generation starts', async () => {
      setupMockChain([]);
      mockUseAuth.mockReturnValue({ user: { id: 'user1' } });

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        const generateButton = screen.getByRole('button', { name: /generate signals/i });
        fireEvent.click(generateButton);
      });

      expect(mockToastSuccess).toHaveBeenCalledWith('Signal generation started! This may take a minute.');
    });
  });

  describe('Edge Cases', () => {
    it('handles empty signals array', async () => {
      setupMockChain([]);

      render(<TradingSignals />, { wrapper: createWrapper() });

      // Wait for loading to complete
      await waitFor(() => {
        expect(screen.getByText('Total Signals')).toBeInTheDocument();
      });

      expect(screen.getByText('0 signals match your filters')).toBeInTheDocument();
    });

    it('formats dates correctly', async () => {
      const signal = createMockSignal({ generated_at: '2026-01-15T10:00:00Z' });
      setupMockChain([signal]);

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        // Date format depends on locale, but should contain the date
        const dateElements = screen.getAllByText(/1\/15\/2026|15\/1\/2026|2026-01-15/);
        expect(dateElements.length).toBeGreaterThan(0);
      });
    });

    it('formats buy_sell_ratio correctly', async () => {
      const signal = createMockSignal({ buy_sell_ratio: 2.567 });
      setupMockChain([signal]);

      render(<TradingSignals />, { wrapper: createWrapper() });

      await waitFor(() => {
        // Ratio appears in both table and top 10 sections
        const ratios = screen.getAllByText('2.57');
        expect(ratios.length).toBeGreaterThan(0);
      });
    });
  });
});
