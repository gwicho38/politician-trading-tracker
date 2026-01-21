import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { AlpacaConnectionStatus } from '../../../client/src/components/trading/AlpacaConnectionStatus';

// Mock Supabase
const mockGetSession = vi.fn();

vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    auth: {
      getSession: () => mockGetSession(),
    },
  },
}));

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock React Query
const mockUseQuery = vi.fn();
const mockUseMutation = vi.fn();
const mockUseQueryClient = vi.fn();

vi.mock('@tanstack/react-query', () => ({
  QueryClient: vi.fn().mockImplementation(() => ({
    defaultOptions: {},
  })),
  QueryClientProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useQuery: (...args: any[]) => mockUseQuery(...args),
  useMutation: (...args: any[]) => mockUseMutation(...args),
  useQueryClient: () => mockUseQueryClient(),
}));

// Sample response data
const mockConnectionStatus = {
  success: true,
  status: 'connected',
  circuitBreaker: {
    state: 'closed',
    failures: 0,
    lastSuccess: '2024-01-15T10:00:00Z',
    lastFailure: null,
  },
  statistics: {
    recentChecks: 10,
    healthyChecks: 9,
    healthRate: '90.0%',
    avgLatencyMs: 150,
  },
  recentLogs: [
    {
      status: 'healthy',
      latencyMs: 120,
      responseCode: 200,
      createdAt: '2024-01-15T10:00:00Z',
    },
    {
      status: 'healthy',
      latencyMs: 180,
      responseCode: 200,
      createdAt: '2024-01-15T09:55:00Z',
    },
  ],
  timestamp: '2024-01-15T10:00:00Z',
};

const mockHealthCheckResponse = {
  success: true,
  healthy: true,
  latency: 125,
  status: 200,
  tradingMode: 'paper',
  circuitBreaker: {
    state: 'closed',
    failures: 0,
  },
  timestamp: '2024-01-15T10:05:00Z',
};

// Test wrapper
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('AlpacaConnectionStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default: authenticated session
    mockGetSession.mockResolvedValue({
      data: {
        session: {
          access_token: 'test-token',
        },
      },
    });

    // Default useQuery mock - loading state
    mockUseQuery.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    });

    mockUseMutation.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    });
  });

  describe('Loading State', () => {
    it('should show loading spinner initially', () => {
      mockUseQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      });

      render(<AlpacaConnectionStatus tradingMode="paper" />, {
        wrapper: createWrapper(),
      });

      // Should show loading spinner
      expect(screen.getByRole('status')).toBeInTheDocument();
    });
  });

      // Should show loading indicator in card
      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });
  });

  describe('Connected State', () => {
    it('should display connected status', async () => {
      mockUseQuery.mockReturnValue({
        data: mockConnectionStatus,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      render(<AlpacaConnectionStatus tradingMode="paper" />, {
        wrapper: createWrapper(),
      });

      expect(screen.getByText('Connected')).toBeInTheDocument();
    });

    it('should display circuit breaker status', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockConnectionStatus),
      });

      render(<AlpacaConnectionStatus tradingMode="paper" />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByText('Closed')).toBeInTheDocument();
      });
    });

    it('should display health statistics', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockConnectionStatus),
      });

      render(<AlpacaConnectionStatus tradingMode="paper" />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByText('90.0%')).toBeInTheDocument();
        expect(screen.getByText('150ms')).toBeInTheDocument();
        expect(screen.getByText('9/10')).toBeInTheDocument();
      });
    });

    it('should display recent health checks', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockConnectionStatus),
      });

      render(<AlpacaConnectionStatus tradingMode="paper" />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByText(/recent health checks/i)).toBeInTheDocument();
        expect(screen.getByText('120ms')).toBeInTheDocument();
        expect(screen.getByText('180ms')).toBeInTheDocument();
      });
    });

    it('should show Paper badge for paper mode', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockConnectionStatus),
      });

      render(<AlpacaConnectionStatus tradingMode="paper" />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByText('Paper')).toBeInTheDocument();
      });
    });

    it('should show Live badge for live mode', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockConnectionStatus),
      });

      render(<AlpacaConnectionStatus tradingMode="live" />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByText('Live')).toBeInTheDocument();
      });
    });
  });

  describe('Degraded State', () => {
    it('should display degraded status', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            ...mockConnectionStatus,
            status: 'degraded',
          }),
      });

      render(<AlpacaConnectionStatus tradingMode="paper" />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByText('Degraded')).toBeInTheDocument();
      });
    });
  });

  describe('Disconnected State', () => {
    it('should display disconnected status', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            ...mockConnectionStatus,
            status: 'disconnected',
          }),
      });

      render(<AlpacaConnectionStatus tradingMode="paper" />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByText('Disconnected')).toBeInTheDocument();
      });
    });
  });

  describe('Circuit Breaker States', () => {
    it('should show warning when circuit breaker is open', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            ...mockConnectionStatus,
            circuitBreaker: {
              ...mockConnectionStatus.circuitBreaker,
              state: 'open',
              failures: 5,
            },
          }),
      });

      render(<AlpacaConnectionStatus tradingMode="paper" />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByText('Open')).toBeInTheDocument();
        expect(screen.getByText(/circuit breaker is open/i)).toBeInTheDocument();
      });
    });

    it('should show warning when circuit breaker is half-open', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            ...mockConnectionStatus,
            circuitBreaker: {
              ...mockConnectionStatus.circuitBreaker,
              state: 'half-open',
            },
          }),
      });

      render(<AlpacaConnectionStatus tradingMode="paper" />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByText('Half-Open')).toBeInTheDocument();
        expect(screen.getByText(/half-open state/i)).toBeInTheDocument();
      });
    });
  });

  describe('Manual Health Check', () => {
    it('should have health check button', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockConnectionStatus),
      });

      render(<AlpacaConnectionStatus tradingMode="paper" />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /run health check/i })).toBeInTheDocument();
      });
    });

    it('should trigger health check on button click', async () => {
      const user = userEvent.setup();

      // First call returns status, second returns health check
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockConnectionStatus),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockHealthCheckResponse),
        });

      render(<AlpacaConnectionStatus tradingMode="paper" />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /run health check/i })).toBeInTheDocument();
      });

      const button = screen.getByRole('button', { name: /run health check/i });
      await user.click(button);

      await waitFor(() => {
        // Health check was called
        expect(mockFetch).toHaveBeenCalledTimes(2);
      });
    });

    it('should display health check result', async () => {
      const user = userEvent.setup();

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockConnectionStatus),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockHealthCheckResponse),
        });

      render(<AlpacaConnectionStatus tradingMode="paper" />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /run health check/i })).toBeInTheDocument();
      });

      const button = screen.getByRole('button', { name: /run health check/i });
      await user.click(button);

      await waitFor(() => {
        expect(screen.getByText('Healthy')).toBeInTheDocument();
        expect(screen.getByText('(125ms)')).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('should display error when fetch fails', async () => {
      mockFetch.mockRejectedValue(new Error('Network error'));

      render(<AlpacaConnectionStatus tradingMode="paper" />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByText(/failed to fetch connection status/i)).toBeInTheDocument();
      });
    });

    it('should display error when response is not ok', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
      });

      render(<AlpacaConnectionStatus tradingMode="paper" />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByText(/http 500/i)).toBeInTheDocument();
      });
    });
  });

  describe('Refresh', () => {
    it('should have refresh button', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockConnectionStatus),
      });

      render(<AlpacaConnectionStatus tradingMode="paper" />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument();
      });
    });
  });
});
