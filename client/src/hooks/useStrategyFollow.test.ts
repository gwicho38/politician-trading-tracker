/**
 * Tests for hooks/useStrategyFollow.ts
 *
 * Tests:
 * - useStrategyFollow() - Strategy subscription management
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock environment variables
vi.stubEnv('VITE_SUPABASE_URL', 'https://test.supabase.co');
vi.stubEnv('VITE_SUPABASE_PUBLISHABLE_KEY', 'test-anon-key');

// Mock useAuth
const mockUseAuth = vi.fn();
vi.mock('./useAuth', () => ({
  useAuth: () => mockUseAuth(),
}));

// Mock Supabase client
vi.mock('@/integrations/supabase/client', () => ({
  supabase: { from: vi.fn() },
  supabasePublic: { from: vi.fn() },
}));

import { useStrategyFollow } from './useStrategyFollow';

const mockFetch = vi.fn();

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe('useStrategyFollow()', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = mockFetch;
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('is disabled when user is null', () => {
    mockUseAuth.mockReturnValue({ user: null, authReady: true });

    const { result } = renderHook(() => useStrategyFollow(), { wrapper: createWrapper() });
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.isFollowing).toBe(false);
  });

  it('is disabled when auth is not ready', () => {
    mockUseAuth.mockReturnValue({ user: { email: 'test@test.com' }, authReady: false });

    const { result } = renderHook(() => useStrategyFollow(), { wrapper: createWrapper() });
    expect(result.current.isLoading).toBe(false);
  });

  it('fetches subscription when authenticated', async () => {
    mockUseAuth.mockReturnValue({ user: { email: 'test@test.com' }, authReady: true });

    const mockToken = JSON.stringify({ access_token: 'test-token' });
    localStorage.setItem('sb-test-auth-token', mockToken);

    const mockResponse = {
      isFollowing: true,
      subscription: {
        id: 's1',
        strategy_type: 'reference',
        trading_mode: 'paper',
        is_active: true,
      },
    };
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const { result } = renderHook(() => useStrategyFollow(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(mockFetch).toHaveBeenCalled();
    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.action).toBe('get-subscription');
    expect(result.current.isFollowing).toBe(true);
    expect(result.current.subscription?.strategy_type).toBe('reference');
  });

  it('returns strategy name for reference type', async () => {
    mockUseAuth.mockReturnValue({ user: { email: 'test@test.com' }, authReady: true });

    const mockToken = JSON.stringify({ access_token: 'test-token' });
    localStorage.setItem('sb-test-auth-token', mockToken);

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        isFollowing: true,
        subscription: { id: 's1', strategy_type: 'reference', is_active: true },
      }),
    });

    const { result } = renderHook(() => useStrategyFollow(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.followingName).toBe('Reference Strategy');
  });

  it('returns strategy name for preset type', async () => {
    mockUseAuth.mockReturnValue({ user: { email: 'test@test.com' }, authReady: true });

    const mockToken = JSON.stringify({ access_token: 'test-token' });
    localStorage.setItem('sb-test-auth-token', mockToken);

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        isFollowing: true,
        subscription: { id: 's1', strategy_type: 'preset', preset_name: 'Aggressive Growth' },
      }),
    });

    const { result } = renderHook(() => useStrategyFollow(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.followingName).toBe('Aggressive Growth');
  });

  it('returns null followingName when not following', () => {
    mockUseAuth.mockReturnValue({ user: null, authReady: true });

    const { result } = renderHook(() => useStrategyFollow(), { wrapper: createWrapper() });
    expect(result.current.followingName).toBeNull();
  });

  it('has correct initial mutation states', () => {
    mockUseAuth.mockReturnValue({ user: null, authReady: true });

    const { result } = renderHook(() => useStrategyFollow(), { wrapper: createWrapper() });
    expect(result.current.isSubscribing).toBe(false);
    expect(result.current.isUnsubscribing).toBe(false);
    expect(result.current.isSyncing).toBe(false);
  });

  it('handles fetch error', async () => {
    mockUseAuth.mockReturnValue({ user: { email: 'test@test.com' }, authReady: true });

    const mockToken = JSON.stringify({ access_token: 'test-token' });
    localStorage.setItem('sb-test-auth-token', mockToken);

    mockFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ error: 'Unauthorized' }),
    });

    const { result } = renderHook(() => useStrategyFollow(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.error).toBeTruthy());
  });
});
