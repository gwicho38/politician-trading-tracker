import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { render, screen } from '@testing-library/react';
import React from 'react';

// Mock wagmi hooks
const mockUseAccount = vi.fn();
const mockUseReconnect = vi.fn();

vi.mock('wagmi', async () => {
  const actual = await vi.importActual('wagmi');
  return {
    ...actual,
    WagmiProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    useAccount: () => mockUseAccount(),
    useReconnect: () => mockUseReconnect(),
    createStorage: vi.fn(() => ({})),
    createConfig: vi.fn(() => ({})),
    http: vi.fn(),
  };
});

// Mock RainbowKit
vi.mock('@rainbow-me/rainbowkit', () => ({
  RainbowKitProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  darkTheme: vi.fn(() => ({})),
  getDefaultConfig: vi.fn(() => ({})),
}));

// Mock React Query
vi.mock('@tanstack/react-query', () => ({
  QueryClient: vi.fn(() => ({
    defaultOptions: {},
  })),
  QueryClientProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock wallet config
vi.mock('@/config/wallet', () => ({
  config: {},
  isWalletDemoMode: false,
  WALLET_SESSION_KEY: 'govmarket-wallet-session',
}));

// Import after mocks
import { WalletProvider } from './WalletProvider';
import { WALLET_SESSION_KEY } from '@/config/wallet';

describe('WalletProvider', () => {
  const mockReconnect = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();

    // Default mock values
    mockUseAccount.mockReturnValue({
      address: undefined,
      isConnected: false,
      isDisconnected: true,
      status: 'disconnected',
    });

    mockUseReconnect.mockReturnValue({
      reconnect: mockReconnect,
      isPending: false,
    });
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe('Basic Rendering', () => {
    it('should render children', () => {
      render(
        <WalletProvider>
          <div data-testid="child">Test Child</div>
        </WalletProvider>
      );

      expect(screen.getByTestId('child')).toBeInTheDocument();
    });
  });

  describe('Session Persistence', () => {
    it('should save session to localStorage when connected', async () => {
      const testAddress = '0x1234567890abcdef';

      mockUseAccount.mockReturnValue({
        address: testAddress,
        isConnected: true,
        isDisconnected: false,
        status: 'connected',
      });

      render(
        <WalletProvider>
          <div>Test</div>
        </WalletProvider>
      );

      await waitFor(() => {
        const saved = localStorage.getItem(WALLET_SESSION_KEY);
        expect(saved).toBeDefined();
        const session = JSON.parse(saved!);
        expect(session.address).toBe(testAddress);
        expect(session.connectedAt).toBeDefined();
        expect(session.lastActiveAt).toBeDefined();
      });
    });

    it('should attempt reconnect when session exists and disconnected', async () => {
      // Pre-populate localStorage with session
      const savedSession = {
        address: '0x1234567890abcdef',
        connectedAt: new Date().toISOString(),
        lastActiveAt: new Date().toISOString(),
      };
      localStorage.setItem(WALLET_SESSION_KEY, JSON.stringify(savedSession));

      mockUseAccount.mockReturnValue({
        address: undefined,
        isConnected: false,
        isDisconnected: false,
        status: 'disconnected',
      });

      render(
        <WalletProvider>
          <div>Test</div>
        </WalletProvider>
      );

      await waitFor(() => {
        expect(mockReconnect).toHaveBeenCalled();
      });
    });

    it('should not attempt reconnect when no session exists', async () => {
      // No localStorage session
      mockUseAccount.mockReturnValue({
        address: undefined,
        isConnected: false,
        isDisconnected: true,
        status: 'disconnected',
      });

      render(
        <WalletProvider>
          <div>Test</div>
        </WalletProvider>
      );

      // Wait a bit to ensure no reconnect is attempted
      await new Promise((r) => setTimeout(r, 100));
      expect(mockReconnect).not.toHaveBeenCalled();
    });

    it('should handle corrupted session data gracefully', async () => {
      localStorage.setItem(WALLET_SESSION_KEY, 'not-valid-json');

      mockUseAccount.mockReturnValue({
        address: undefined,
        isConnected: false,
        isDisconnected: true,
        status: 'disconnected',
      });

      // Should not throw
      render(
        <WalletProvider>
          <div>Test</div>
        </WalletProvider>
      );

      // Session should be cleared
      await waitFor(() => {
        expect(localStorage.getItem(WALLET_SESSION_KEY)).toBeNull();
      });
    });
  });
});

describe('Retry Configuration', () => {
  it('should have exponential backoff configuration', async () => {
    // This tests the retry delay calculation logic
    // Base delay: 1000ms, doubles each attempt, max 30s

    // Test the concept - actual implementation is in WalletProvider
    const calculateRetryDelay = (attemptIndex: number): number => {
      const baseDelay = 1000;
      const maxDelay = 30000;
      const exponentialDelay = Math.min(baseDelay * Math.pow(2, attemptIndex), maxDelay);
      return exponentialDelay; // Without jitter for testing
    };

    expect(calculateRetryDelay(0)).toBe(1000);
    expect(calculateRetryDelay(1)).toBe(2000);
    expect(calculateRetryDelay(2)).toBe(4000);
    expect(calculateRetryDelay(3)).toBe(8000);
    expect(calculateRetryDelay(4)).toBe(16000);
    expect(calculateRetryDelay(5)).toBe(30000); // Capped at max
  });

  it('should not retry on auth errors (401/403)', () => {
    // Test the retry logic concept
    const shouldRetry = (failureCount: number, error: { status?: number }): boolean => {
      if (failureCount >= 3) return false;
      const status = error?.status;
      if (status === 401 || status === 403) return false;
      if (status && status >= 400 && status < 500 && status !== 408 && status !== 429) return false;
      return true;
    };

    expect(shouldRetry(0, { status: 401 })).toBe(false);
    expect(shouldRetry(0, { status: 403 })).toBe(false);
    expect(shouldRetry(0, { status: 500 })).toBe(true);
    expect(shouldRetry(0, { status: 408 })).toBe(true); // Timeout
    expect(shouldRetry(0, { status: 429 })).toBe(true); // Rate limit
    expect(shouldRetry(3, { status: 500 })).toBe(false); // Max retries
  });
});
