/**
 * Tests for hooks/useAuth.tsx
 *
 * Tests:
 * - AuthProvider initialization from localStorage
 * - Auth state change handling
 * - useAuth hook returns correct context values
 * - useAuthReady backwards compatibility
 * - Loading states
 * - Timeout fallback for authReady
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, renderHook, waitFor, act } from '@testing-library/react';
import React from 'react';

// Mock Supabase client
const mockUnsubscribe = vi.fn();
const mockOnAuthStateChange = vi.fn();

vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    auth: {
      onAuthStateChange: (callback: (event: string, session: { user: object } | null) => void) => {
        mockOnAuthStateChange(callback);
        return {
          data: {
            subscription: {
              unsubscribe: mockUnsubscribe,
            },
          },
        };
      },
    },
  },
}));

import { AuthProvider, useAuth, useAuthReady } from './useAuth';

// Mock user for testing
const mockUser = {
  id: 'user-123',
  email: 'test@example.com',
  created_at: '2024-01-01T00:00:00.000Z',
  aud: 'authenticated',
  role: 'authenticated',
};

// Helper to create session data for localStorage
function createSessionData(user: object | null, expiresAt: number) {
  return JSON.stringify({
    user,
    expires_at: expiresAt,
    access_token: 'mock-access-token',
    refresh_token: 'mock-refresh-token',
  });
}

// Test component that displays auth state
function TestConsumer() {
  const { user, loading, isAuthenticated, authReady } = useAuth();
  return (
    <div>
      <span data-testid="user-email">{user?.email ?? 'no-user'}</span>
      <span data-testid="loading">{loading ? 'true' : 'false'}</span>
      <span data-testid="is-authenticated">{isAuthenticated ? 'true' : 'false'}</span>
      <span data-testid="auth-ready">{authReady ? 'true' : 'false'}</span>
    </div>
  );
}

describe('useAuth', () => {
  // Store original localStorage
  let originalLocalStorage: Storage;
  let mockStorage: Record<string, string>;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    // Mock localStorage
    originalLocalStorage = global.localStorage;
    mockStorage = {};

    Object.defineProperty(global, 'localStorage', {
      value: {
        getItem: vi.fn((key: string) => mockStorage[key] ?? null),
        setItem: vi.fn((key: string, value: string) => {
          mockStorage[key] = value;
        }),
        removeItem: vi.fn((key: string) => {
          delete mockStorage[key];
        }),
        clear: vi.fn(() => {
          mockStorage = {};
        }),
        key: vi.fn((index: number) => Object.keys(mockStorage)[index] ?? null),
        get length() {
          return Object.keys(mockStorage).length;
        },
      },
      writable: true,
      configurable: true,
    });

    // Override Object.keys for localStorage to return our mock keys
    const originalObjectKeys = Object.keys;
    vi.spyOn(Object, 'keys').mockImplementation((obj) => {
      if (obj === localStorage) {
        return originalObjectKeys(mockStorage);
      }
      return originalObjectKeys(obj);
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    Object.defineProperty(global, 'localStorage', {
      value: originalLocalStorage,
      writable: true,
      configurable: true,
    });
  });

  describe('AuthProvider', () => {
    it('renders children', () => {
      render(
        <AuthProvider>
          <div data-testid="child">Hello</div>
        </AuthProvider>
      );

      expect(screen.getByTestId('child')).toHaveTextContent('Hello');
    });

    it('provides default auth state when no stored user', () => {
      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      expect(screen.getByTestId('user-email')).toHaveTextContent('no-user');
      expect(screen.getByTestId('loading')).toHaveTextContent('true');
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
      expect(screen.getByTestId('auth-ready')).toHaveTextContent('false');
    });

    it('initializes from valid localStorage session', () => {
      // Set up valid session in localStorage
      const futureExpiry = Math.floor(Date.now() / 1000) + 3600; // 1 hour from now
      mockStorage['sb-test-auth-token'] = createSessionData(mockUser, futureExpiry);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      expect(screen.getByTestId('user-email')).toHaveTextContent('test@example.com');
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true');
    });

    it('does not use expired session from localStorage', () => {
      // Set up expired session
      const pastExpiry = Math.floor(Date.now() / 1000) - 3600; // 1 hour ago
      mockStorage['sb-test-auth-token'] = createSessionData(mockUser, pastExpiry);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      expect(screen.getByTestId('user-email')).toHaveTextContent('no-user');
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
    });

    it('handles invalid JSON in localStorage gracefully', () => {
      mockStorage['sb-test-auth-token'] = 'invalid-json';

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      expect(screen.getByTestId('user-email')).toHaveTextContent('no-user');
    });

    it('sets up auth state change listener on mount', () => {
      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      expect(mockOnAuthStateChange).toHaveBeenCalledTimes(1);
      expect(mockOnAuthStateChange).toHaveBeenCalledWith(expect.any(Function));
    });

    it('unsubscribes from auth changes on unmount', () => {
      const { unmount } = render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      unmount();

      expect(mockUnsubscribe).toHaveBeenCalledTimes(1);
    });

    it('updates user on auth state change', async () => {
      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      // Get the callback that was passed to onAuthStateChange
      const authCallback = mockOnAuthStateChange.mock.calls[0][0];

      // Simulate auth change event
      act(() => {
        authCallback('SIGNED_IN', { user: mockUser });
      });

      expect(screen.getByTestId('user-email')).toHaveTextContent('test@example.com');
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true');
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
      expect(screen.getByTestId('auth-ready')).toHaveTextContent('true');
    });

    it('clears user on sign out', async () => {
      // Start with a stored user
      const futureExpiry = Math.floor(Date.now() / 1000) + 3600;
      mockStorage['sb-test-auth-token'] = createSessionData(mockUser, futureExpiry);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      expect(screen.getByTestId('user-email')).toHaveTextContent('test@example.com');

      // Simulate sign out
      const authCallback = mockOnAuthStateChange.mock.calls[0][0];
      act(() => {
        authCallback('SIGNED_OUT', null);
      });

      expect(screen.getByTestId('user-email')).toHaveTextContent('no-user');
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
    });

    it('sets authReady to true after 2 second timeout', async () => {
      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      expect(screen.getByTestId('auth-ready')).toHaveTextContent('false');

      // Advance past the 2 second timeout
      act(() => {
        vi.advanceTimersByTime(2001);
      });

      expect(screen.getByTestId('auth-ready')).toHaveTextContent('true');
    });

    it('clears timeout on unmount', () => {
      const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout');

      const { unmount } = render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      unmount();

      expect(clearTimeoutSpy).toHaveBeenCalled();
    });
  });

  describe('useAuth hook', () => {
    it('returns auth state from context', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AuthProvider>{children}</AuthProvider>
      );

      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current).toHaveProperty('user');
      expect(result.current).toHaveProperty('loading');
      expect(result.current).toHaveProperty('isAuthenticated');
      expect(result.current).toHaveProperty('authReady');
    });

    it('returns default values outside of provider', () => {
      // This tests the default context value
      const { result } = renderHook(() => useAuth());

      expect(result.current.user).toBeNull();
      expect(result.current.loading).toBe(true);
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.authReady).toBe(false);
    });
  });

  describe('useAuthReady hook', () => {
    it('returns authReady from context', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AuthProvider>{children}</AuthProvider>
      );

      const { result } = renderHook(() => useAuthReady(), { wrapper });

      expect(typeof result.current).toBe('boolean');
    });

    it('returns false initially', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AuthProvider>{children}</AuthProvider>
      );

      const { result } = renderHook(() => useAuthReady(), { wrapper });

      expect(result.current).toBe(false);
    });

    it('returns true after auth state change', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AuthProvider>{children}</AuthProvider>
      );

      const { result } = renderHook(() => useAuthReady(), { wrapper });

      // Simulate auth change
      const authCallback = mockOnAuthStateChange.mock.calls[0][0];
      act(() => {
        authCallback('INITIAL_SESSION', null);
      });

      expect(result.current).toBe(true);
    });
  });

  describe('isAuthenticated computed property', () => {
    it('is true when user exists', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AuthProvider>{children}</AuthProvider>
      );

      const { result } = renderHook(() => useAuth(), { wrapper });

      // Simulate sign in
      const authCallback = mockOnAuthStateChange.mock.calls[0][0];
      act(() => {
        authCallback('SIGNED_IN', { user: mockUser });
      });

      expect(result.current.isAuthenticated).toBe(true);
    });

    it('is false when user is null', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AuthProvider>{children}</AuthProvider>
      );

      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current.isAuthenticated).toBe(false);
    });
  });

  describe('loading state', () => {
    it('starts as true when no stored user', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AuthProvider>{children}</AuthProvider>
      );

      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current.loading).toBe(true);
    });

    it('starts as false when stored user exists', () => {
      const futureExpiry = Math.floor(Date.now() / 1000) + 3600;
      mockStorage['sb-test-auth-token'] = createSessionData(mockUser, futureExpiry);

      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AuthProvider>{children}</AuthProvider>
      );

      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current.loading).toBe(false);
    });

    it('becomes false after auth state change', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <AuthProvider>{children}</AuthProvider>
      );

      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current.loading).toBe(true);

      // Simulate auth change
      const authCallback = mockOnAuthStateChange.mock.calls[0][0];
      act(() => {
        authCallback('INITIAL_SESSION', null);
      });

      expect(result.current.loading).toBe(false);
    });
  });

  describe('localStorage key detection', () => {
    it('finds session with standard supabase key format', () => {
      const futureExpiry = Math.floor(Date.now() / 1000) + 3600;
      mockStorage['sb-projectid-auth-token'] = createSessionData(mockUser, futureExpiry);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      expect(screen.getByTestId('user-email')).toHaveTextContent('test@example.com');
    });

    it('ignores non-supabase keys', () => {
      const futureExpiry = Math.floor(Date.now() / 1000) + 3600;
      mockStorage['other-key'] = createSessionData(mockUser, futureExpiry);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      expect(screen.getByTestId('user-email')).toHaveTextContent('no-user');
    });

    it('ignores keys that do not end with auth-token', () => {
      const futureExpiry = Math.floor(Date.now() / 1000) + 3600;
      mockStorage['sb-test-other'] = createSessionData(mockUser, futureExpiry);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      expect(screen.getByTestId('user-email')).toHaveTextContent('no-user');
    });
  });

  describe('session validation', () => {
    it('validates session has user property', () => {
      const futureExpiry = Math.floor(Date.now() / 1000) + 3600;
      mockStorage['sb-test-auth-token'] = JSON.stringify({
        expires_at: futureExpiry,
        // No user property
      });

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      expect(screen.getByTestId('user-email')).toHaveTextContent('no-user');
    });
  });
});
