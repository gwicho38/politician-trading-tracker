import { ReactNode, useEffect, useRef } from 'react';
import { WagmiProvider, useAccount, useReconnect } from 'wagmi';
import { RainbowKitProvider, darkTheme } from '@rainbow-me/rainbowkit';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { config, isWalletDemoMode, WALLET_SESSION_KEY } from '@/config/wallet';
import { logDebug, logError } from '@/lib/logger';
import '@rainbow-me/rainbowkit/styles.css';

/**
 * Exponential backoff with jitter for retry delays.
 * Base delay: 1000ms, doubles each attempt, max 30s.
 * Jitter adds ±25% randomization to prevent thundering herd.
 */
const calculateRetryDelay = (attemptIndex: number): number => {
  const baseDelay = 1000;
  const maxDelay = 30000;
  const exponentialDelay = Math.min(baseDelay * Math.pow(2, attemptIndex), maxDelay);
  // Add jitter: ±25% randomization
  const jitter = exponentialDelay * 0.25 * (Math.random() * 2 - 1);
  return Math.max(0, exponentialDelay + jitter);
};

/**
 * Determine if an error should trigger a retry.
 * Don't retry on auth errors (401/403) or client errors (4xx except 408/429).
 */
const shouldRetry = (failureCount: number, error: unknown): boolean => {
  if (failureCount >= 3) return false;

  // Check for HTTP status codes in error
  const status = (error as { status?: number })?.status
    || (error as { response?: { status?: number } })?.response?.status;

  if (status) {
    // Don't retry auth errors
    if (status === 401 || status === 403) return false;
    // Don't retry client errors except timeout (408) and rate limit (429)
    if (status >= 400 && status < 500 && status !== 408 && status !== 429) return false;
  }

  return true;
};

// Create query client with retry configuration
const wagmiQueryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: shouldRetry,
      retryDelay: calculateRetryDelay,
      staleTime: 1000 * 60, // 1 minute
      refetchOnWindowFocus: false, // Prevent aggressive refetching
    },
    mutations: {
      retry: shouldRetry,
      retryDelay: calculateRetryDelay,
    },
  },
});

/**
 * WalletSessionManager - handles session persistence and reconnection
 * Must be used inside WagmiProvider
 */
function WalletSessionManager({ children }: { children: ReactNode }) {
  const { address, isConnected, isDisconnected, status } = useAccount();
  const { reconnect, isPending: isReconnecting } = useReconnect();
  const reconnectAttemptedRef = useRef(false);
  const lastKnownAddressRef = useRef<string | null>(null);

  // Attempt reconnection on mount if there was a previous session
  useEffect(() => {
    if (reconnectAttemptedRef.current) return;

    const savedSession = localStorage.getItem(WALLET_SESSION_KEY);
    if (savedSession && !isConnected && status === 'disconnected') {
      reconnectAttemptedRef.current = true;
      try {
        const session = JSON.parse(savedSession);
        if (session.address) {
          logDebug('[WalletSession] Attempting to reconnect previous session', 'wallet');
          reconnect();
        }
      } catch (e) {
        logError('[WalletSession] Failed to parse saved session', 'wallet', e instanceof Error ? e : undefined);
        localStorage.removeItem(WALLET_SESSION_KEY);
      }
    }
  }, [isConnected, status, reconnect]);

  // Save session when connected
  useEffect(() => {
    if (isConnected && address) {
      const session = {
        address,
        connectedAt: new Date().toISOString(),
        lastActiveAt: new Date().toISOString(),
      };
      localStorage.setItem(WALLET_SESSION_KEY, JSON.stringify(session));
      lastKnownAddressRef.current = address;
      logDebug('[WalletSession] Session saved', 'wallet', { address });
    }
  }, [isConnected, address]);

  // Update last active time periodically when connected
  useEffect(() => {
    if (!isConnected || !address) return;

    const updateInterval = setInterval(() => {
      try {
        const savedSession = localStorage.getItem(WALLET_SESSION_KEY);
        if (savedSession) {
          const session = JSON.parse(savedSession);
          session.lastActiveAt = new Date().toISOString();
          localStorage.setItem(WALLET_SESSION_KEY, JSON.stringify(session));
        }
      } catch (e) {
        // Ignore errors in background update
      }
    }, 60000); // Update every minute

    return () => clearInterval(updateInterval);
  }, [isConnected, address]);

  // Handle disconnection - attempt reconnect if unexpected
  useEffect(() => {
    if (isDisconnected && lastKnownAddressRef.current && !isReconnecting) {
      // Unexpected disconnect - attempt to reconnect
      logDebug('[WalletSession] Unexpected disconnect, attempting reconnect', 'wallet');
      const timer = setTimeout(() => {
        reconnect();
      }, 2000); // Wait 2 seconds before attempting reconnect

      return () => clearTimeout(timer);
    }
  }, [isDisconnected, isReconnecting, reconnect]);

  // Clear session on intentional disconnect
  useEffect(() => {
    if (isDisconnected && !isReconnecting && reconnectAttemptedRef.current) {
      // After reconnect was attempted and still disconnected, clear session
      const timer = setTimeout(() => {
        if (!isConnected) {
          logDebug('[WalletSession] Clearing stale session', 'wallet');
          localStorage.removeItem(WALLET_SESSION_KEY);
          lastKnownAddressRef.current = null;
        }
      }, 5000); // Wait 5 seconds to ensure reconnect had time to complete

      return () => clearTimeout(timer);
    }
  }, [isDisconnected, isReconnecting, isConnected]);

  return <>{children}</>;
}

interface WalletProviderProps {
  children: ReactNode;
}

export const WalletProvider = ({ children }: WalletProviderProps) => {
  // Always provide WagmiProvider - hooks like useAccount need it even in demo mode
  // In demo mode, skip RainbowKitProvider to avoid WalletConnect API errors
  if (isWalletDemoMode) {
    return (
      <WagmiProvider config={config}>
        <QueryClientProvider client={wagmiQueryClient}>
          <WalletSessionManager>
            {children}
          </WalletSessionManager>
        </QueryClientProvider>
      </WagmiProvider>
    );
  }

  // Full wallet functionality when we have a real project ID
  return (
    <WagmiProvider config={config}>
      <QueryClientProvider client={wagmiQueryClient}>
        <RainbowKitProvider
          theme={darkTheme({
            accentColor: 'hsl(142, 76%, 36%)',
            accentColorForeground: 'white',
            borderRadius: 'medium',
            fontStack: 'system',
          })}
        >
          <WalletSessionManager>
            {children}
          </WalletSessionManager>
        </RainbowKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
};
