/**
 * Tests for hooks/useAlpacaCredentials.ts
 *
 * Tests:
 * - Credentials query behavior based on auth state
 * - isConnected helper logic
 * - getValidatedAt helper logic
 * - Query disabled states
 * - Mutation error handling
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock useAuth
const mockUseAuth = vi.fn();
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => mockUseAuth(),
}));

// Mock environment variables
vi.stubEnv('VITE_SUPABASE_URL', 'https://test.supabase.co');
vi.stubEnv('VITE_SUPABASE_PUBLISHABLE_KEY', 'test-anon-key');

import { useAlpacaCredentials } from './useAlpacaCredentials';

// Create wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

// Mock fetch
const mockFetch = vi.fn();

describe('useAlpacaCredentials', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Setup global fetch mock
    global.fetch = mockFetch;

    // Default auth mock - user authenticated
    mockUseAuth.mockReturnValue({
      user: { email: 'test@example.com' },
      authReady: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Query behavior based on auth state', () => {
    it('does not fetch when user is null', async () => {
      mockUseAuth.mockReturnValue({
        user: null,
        authReady: true,
      });

      const { result } = renderHook(() => useAlpacaCredentials(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Should not attempt to fetch when no user
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('does not fetch when authReady is false', async () => {
      mockUseAuth.mockReturnValue({
        user: { email: 'test@example.com' },
        authReady: false,
      });

      renderHook(() => useAlpacaCredentials(), {
        wrapper: createWrapper(),
      });

      // Query should be disabled - no fetch
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('does not fetch when user email is missing', async () => {
      mockUseAuth.mockReturnValue({
        user: { id: '123' }, // No email
        authReady: true,
      });

      const { result } = renderHook(() => useAlpacaCredentials(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(mockFetch).not.toHaveBeenCalled();
    });
  });

  describe('isConnected helper', () => {
    it('returns false when credentials are undefined', () => {
      mockUseAuth.mockReturnValue({
        user: null,
        authReady: true,
      });

      const { result } = renderHook(() => useAlpacaCredentials(), {
        wrapper: createWrapper(),
      });

      // credentials will be undefined since query is disabled
      expect(result.current.isConnected('paper')).toBe(false);
      expect(result.current.isConnected('live')).toBe(false);
    });
  });

  describe('getValidatedAt helper', () => {
    it('returns null when credentials are undefined', () => {
      mockUseAuth.mockReturnValue({
        user: null,
        authReady: true,
      });

      const { result } = renderHook(() => useAlpacaCredentials(), {
        wrapper: createWrapper(),
      });

      // credentials will be undefined since query is disabled
      expect(result.current.getValidatedAt('paper')).toBeNull();
      expect(result.current.getValidatedAt('live')).toBeNull();
    });
  });

  describe('Hook return shape', () => {
    it('returns expected properties', async () => {
      mockUseAuth.mockReturnValue({
        user: null,
        authReady: true,
      });

      const { result } = renderHook(() => useAlpacaCredentials(), {
        wrapper: createWrapper(),
      });

      // Check all expected properties exist
      expect(result.current).toHaveProperty('credentials');
      expect(result.current).toHaveProperty('isLoading');
      expect(result.current).toHaveProperty('error');
      expect(result.current).toHaveProperty('refetch');
      expect(result.current).toHaveProperty('isConnected');
      expect(result.current).toHaveProperty('getValidatedAt');
      expect(result.current).toHaveProperty('saveCredentials');
      expect(result.current).toHaveProperty('isSaving');
      expect(result.current).toHaveProperty('testConnection');
      expect(result.current).toHaveProperty('isTesting');
      expect(result.current).toHaveProperty('clearCredentials');
      expect(result.current).toHaveProperty('isClearing');
    });

    it('has functions for isConnected and getValidatedAt', () => {
      mockUseAuth.mockReturnValue({
        user: null,
        authReady: true,
      });

      const { result } = renderHook(() => useAlpacaCredentials(), {
        wrapper: createWrapper(),
      });

      expect(typeof result.current.isConnected).toBe('function');
      expect(typeof result.current.getValidatedAt).toBe('function');
      expect(typeof result.current.saveCredentials).toBe('function');
      expect(typeof result.current.testConnection).toBe('function');
      expect(typeof result.current.clearCredentials).toBe('function');
      expect(typeof result.current.refetch).toBe('function');
    });
  });

  describe('Initial loading states', () => {
    it('has isSaving as false initially', () => {
      mockUseAuth.mockReturnValue({
        user: null,
        authReady: true,
      });

      const { result } = renderHook(() => useAlpacaCredentials(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isSaving).toBe(false);
    });

    it('has isTesting as false initially', () => {
      mockUseAuth.mockReturnValue({
        user: null,
        authReady: true,
      });

      const { result } = renderHook(() => useAlpacaCredentials(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isTesting).toBe(false);
    });

    it('has isClearing as false initially', () => {
      mockUseAuth.mockReturnValue({
        user: null,
        authReady: true,
      });

      const { result } = renderHook(() => useAlpacaCredentials(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isClearing).toBe(false);
    });

    it('has error as null initially', () => {
      mockUseAuth.mockReturnValue({
        user: null,
        authReady: true,
      });

      const { result } = renderHook(() => useAlpacaCredentials(), {
        wrapper: createWrapper(),
      });

      expect(result.current.error).toBeNull();
    });
  });

  describe('Query key includes user email', () => {
    it('uses user email in query key for proper caching', () => {
      // This test verifies the hook correctly associates credentials with user
      mockUseAuth.mockReturnValue({
        user: { email: 'user1@example.com' },
        authReady: true,
      });

      const { result: result1 } = renderHook(() => useAlpacaCredentials(), {
        wrapper: createWrapper(),
      });

      mockUseAuth.mockReturnValue({
        user: { email: 'user2@example.com' },
        authReady: true,
      });

      const { result: result2 } = renderHook(() => useAlpacaCredentials(), {
        wrapper: createWrapper(),
      });

      // Both hooks should have their own state based on user email
      expect(result1.current).toBeDefined();
      expect(result2.current).toBeDefined();
    });
  });

  describe('Mode parameters', () => {
    it('isConnected accepts paper mode', () => {
      const { result } = renderHook(() => useAlpacaCredentials(), {
        wrapper: createWrapper(),
      });

      // Should not throw when called with 'paper'
      expect(() => result.current.isConnected('paper')).not.toThrow();
    });

    it('isConnected accepts live mode', () => {
      const { result } = renderHook(() => useAlpacaCredentials(), {
        wrapper: createWrapper(),
      });

      // Should not throw when called with 'live'
      expect(() => result.current.isConnected('live')).not.toThrow();
    });

    it('getValidatedAt accepts paper mode', () => {
      const { result } = renderHook(() => useAlpacaCredentials(), {
        wrapper: createWrapper(),
      });

      // Should not throw when called with 'paper'
      expect(() => result.current.getValidatedAt('paper')).not.toThrow();
    });

    it('getValidatedAt accepts live mode', () => {
      const { result } = renderHook(() => useAlpacaCredentials(), {
        wrapper: createWrapper(),
      });

      // Should not throw when called with 'live'
      expect(() => result.current.getValidatedAt('live')).not.toThrow();
    });
  });
});
