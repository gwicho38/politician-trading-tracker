import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AlpacaConnectionStatus } from './AlpacaConnectionStatus';

// Mock formatDistanceToNow
vi.mock('date-fns', () => ({
  formatDistanceToNow: vi.fn(() => '5 minutes ago'),
}));

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock localStorage
const mockLocalStorage: Record<string, string> = {};
const localStorageMock = {
  getItem: vi.fn((key: string) => mockLocalStorage[key] || null),
  setItem: vi.fn((key: string, value: string) => {
    mockLocalStorage[key] = value;
  }),
  removeItem: vi.fn((key: string) => {
    delete mockLocalStorage[key];
  }),
  clear: vi.fn(() => {
    Object.keys(mockLocalStorage).forEach(key => delete mockLocalStorage[key]);
  }),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock Object.keys for localStorage
const originalObjectKeys = Object.keys;

// Mock env vars
vi.stubEnv('VITE_SUPABASE_URL', 'https://test.supabase.co');
vi.stubEnv('VITE_SUPABASE_PUBLISHABLE_KEY', 'test-anon-key');

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
      },
    },
  });
}

function renderWithProviders(component: React.ReactElement) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  );
}

const mockConnectionStatus = {
  success: true,
  status: 'connected',
  circuitBreaker: {
    state: 'closed',
    failures: 0,
    lastSuccess: '2026-01-29T12:00:00Z',
    lastFailure: null,
  },
  statistics: {
    recentChecks: 10,
    healthyChecks: 9,
    healthRate: '90%',
    avgLatencyMs: 150,
  },
  recentLogs: [
    {
      status: 'healthy',
      latencyMs: 120,
      responseCode: 200,
      createdAt: '2026-01-29T12:00:00Z',
    },
    {
      status: 'healthy',
      latencyMs: 180,
      responseCode: 200,
      createdAt: '2026-01-29T11:55:00Z',
    },
  ],
  timestamp: '2026-01-29T12:00:00Z',
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
  timestamp: '2026-01-29T12:01:00Z',
};

describe('AlpacaConnectionStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();

    // Set up authenticated session in localStorage
    mockLocalStorage['sb-test-auth-token'] = JSON.stringify({
      access_token: 'test-token',
    });

    // Mock Object.keys to return our localStorage keys
    vi.spyOn(Object, 'keys').mockImplementation((obj) => {
      if (obj === localStorage) {
        return Object.keys(mockLocalStorage);
      }
      return originalObjectKeys(obj);
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Loading state', () => {
    it('shows loading spinner while fetching', () => {
      mockFetch.mockImplementation(() => new Promise(() => {})); // Never resolves

      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      // Check for the Loader2 icon which has animate-spin class
      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });
  });

  describe('Error state', () => {
    it('shows error message when fetch fails', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(screen.getByText(/Failed to fetch connection status/)).toBeInTheDocument();
      });
    });

    it('shows error when not authenticated', async () => {
      // Clear localStorage to simulate unauthenticated state
      Object.keys(mockLocalStorage).forEach(key => delete mockLocalStorage[key]);

      mockFetch.mockRejectedValueOnce(new Error('Not authenticated'));

      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(screen.getByText(/Not authenticated/)).toBeInTheDocument();
      });
    });
  });

  describe('Connected state', () => {
    beforeEach(() => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockConnectionStatus),
      });
    });

    it('displays connection status title', async () => {
      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(screen.getByText('Connection Status')).toBeInTheDocument();
      });
    });

    it('displays trading mode badge', async () => {
      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(screen.getByText('Paper')).toBeInTheDocument();
      });
    });

    it('displays live trading mode badge', async () => {
      renderWithProviders(<AlpacaConnectionStatus tradingMode="live" />);

      await waitFor(() => {
        expect(screen.getByText('Live')).toBeInTheDocument();
      });
    });

    it('displays connected status', async () => {
      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(screen.getByText('connected')).toBeInTheDocument();
      });
    });

    it('displays circuit breaker state', async () => {
      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(screen.getByText('Closed')).toBeInTheDocument();
      });
    });

    it('displays health rate statistic', async () => {
      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(screen.getByText('90%')).toBeInTheDocument();
        expect(screen.getByText('Health Rate')).toBeInTheDocument();
      });
    });

    it('displays average latency', async () => {
      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(screen.getByText('150ms')).toBeInTheDocument();
        expect(screen.getByText('Avg Latency')).toBeInTheDocument();
      });
    });

    it('displays healthy/total checks', async () => {
      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(screen.getByText('9/10')).toBeInTheDocument();
        expect(screen.getByText('Healthy/Total')).toBeInTheDocument();
      });
    });

    it('displays recent health checks section', async () => {
      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(screen.getByText('Recent Health Checks')).toBeInTheDocument();
      });
    });

    it('displays recent health check logs with latency', async () => {
      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(screen.getByText('120ms')).toBeInTheDocument();
        expect(screen.getByText('180ms')).toBeInTheDocument();
      });
    });

    it('displays refresh button', async () => {
      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Refresh/ })).toBeInTheDocument();
      });
    });

    it('displays health check button', async () => {
      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Run Health Check/ })).toBeInTheDocument();
      });
    });
  });

  describe('Degraded state', () => {
    it('displays degraded status with correct styling', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          ...mockConnectionStatus,
          status: 'degraded',
        }),
      });

      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(screen.getByText('degraded')).toBeInTheDocument();
      });
    });
  });

  describe('Disconnected state', () => {
    it('displays disconnected status', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          ...mockConnectionStatus,
          status: 'disconnected',
        }),
      });

      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(screen.getByText('disconnected')).toBeInTheDocument();
      });
    });
  });

  describe('Circuit breaker states', () => {
    it('displays open circuit breaker with warning', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          ...mockConnectionStatus,
          circuitBreaker: {
            ...mockConnectionStatus.circuitBreaker,
            state: 'open',
            failures: 5,
          },
        }),
      });

      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(screen.getByText('Open')).toBeInTheDocument();
        expect(screen.getByText(/Circuit breaker is open/)).toBeInTheDocument();
        expect(screen.getByText('(5 failures)')).toBeInTheDocument();
      });
    });

    it('displays half-open circuit breaker with info', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          ...mockConnectionStatus,
          circuitBreaker: {
            ...mockConnectionStatus.circuitBreaker,
            state: 'half-open',
            failures: 3,
          },
        }),
      });

      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(screen.getByText('Half-Open')).toBeInTheDocument();
        expect(screen.getByText(/Circuit breaker is in half-open state/)).toBeInTheDocument();
      });
    });
  });

  describe('Health check functionality', () => {
    it('runs health check on button click', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockConnectionStatus),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockHealthCheckResponse),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockConnectionStatus),
        });

      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Run Health Check/ })).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: /Run Health Check/ }));

      await waitFor(() => {
        expect(screen.getByText('Healthy')).toBeInTheDocument();
        expect(screen.getByText('(125ms)')).toBeInTheDocument();
      });
    });

    it('displays unhealthy health check result', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockConnectionStatus),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({
            ...mockHealthCheckResponse,
            healthy: false,
            error: 'Connection timeout',
          }),
        });

      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Run Health Check/ })).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: /Run Health Check/ }));

      await waitFor(() => {
        expect(screen.getByText('Unhealthy')).toBeInTheDocument();
        expect(screen.getByText('Connection timeout')).toBeInTheDocument();
      });
    });
  });

  describe('Refresh functionality', () => {
    it('refetches data on refresh button click', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockConnectionStatus),
      });

      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Refresh/ })).toBeInTheDocument();
      });

      const initialCallCount = mockFetch.mock.calls.length;

      fireEvent.click(screen.getByRole('button', { name: /Refresh/ }));

      await waitFor(() => {
        expect(mockFetch.mock.calls.length).toBeGreaterThan(initialCallCount);
      });
    });
  });

  describe('Statistics with N/A values', () => {
    it('displays N/A when avgLatencyMs is null', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          ...mockConnectionStatus,
          statistics: {
            ...mockConnectionStatus.statistics,
            avgLatencyMs: null,
          },
        }),
      });

      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(screen.getByText('N/A')).toBeInTheDocument();
      });
    });
  });

  describe('Empty recent logs', () => {
    it('does not show recent checks section when logs are empty', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          ...mockConnectionStatus,
          recentLogs: [],
        }),
      });

      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      // Wait for health rate statistic to appear (indicates data loaded)
      await waitFor(() => {
        expect(screen.getByText('90%')).toBeInTheDocument();
      });

      // Recent Health Checks section should not be shown when logs are empty
      expect(screen.queryByText('Recent Health Checks')).not.toBeInTheDocument();
    });
  });

  describe('API request construction', () => {
    it('sends correct request body for paper trading', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockConnectionStatus),
      });

      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/functions/v1/alpaca-account'),
          expect.objectContaining({
            method: 'POST',
            body: JSON.stringify({
              action: 'connection-status',
              tradingMode: 'paper',
            }),
          })
        );
      });
    });

    it('sends correct request body for live trading', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockConnectionStatus),
      });

      renderWithProviders(<AlpacaConnectionStatus tradingMode="live" />);

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/functions/v1/alpaca-account'),
          expect.objectContaining({
            method: 'POST',
            body: JSON.stringify({
              action: 'connection-status',
              tradingMode: 'live',
            }),
          })
        );
      });
    });

    it('includes authorization header', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockConnectionStatus),
      });

      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            headers: expect.objectContaining({
              'Authorization': 'Bearer test-token',
            }),
          })
        );
      });
    });
  });

  describe('HTTP error handling', () => {
    it('handles HTTP error response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      renderWithProviders(<AlpacaConnectionStatus tradingMode="paper" />);

      await waitFor(() => {
        expect(screen.getByText(/HTTP 500/)).toBeInTheDocument();
      });
    });
  });
});
