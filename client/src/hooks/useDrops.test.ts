/**
 * Tests for hooks/useDrops.ts and useDropsRealtime.ts
 *
 * Tests:
 * - useDrops() - Fetches drops feed, CRUD mutations, like/unlike with optimistic updates
 * - useDropsRealtime() - Subscribes to realtime changes
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock Supabase client
const mockRpc = vi.fn();
const mockChannel = vi.fn();
const mockRemoveChannel = vi.fn();
vi.mock('@/integrations/supabase/client', () => ({
  supabasePublic: {
    rpc: (...args: unknown[]) => mockRpc(...args),
    channel: (...args: unknown[]) => mockChannel(...args),
    removeChannel: (...args: unknown[]) => mockRemoveChannel(...args),
  },
  supabase: {
    rpc: (...args: unknown[]) => mockRpc(...args),
    channel: (...args: unknown[]) => mockChannel(...args),
    removeChannel: (...args: unknown[]) => mockRemoveChannel(...args),
  },
}));

// Mock useAuth
const mockUseAuth = vi.fn();
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => mockUseAuth(),
}));

// Mock logger
vi.mock('@/lib/logger', () => ({
  logDebug: vi.fn(),
  logError: vi.fn(),
}));

// Mock environment variables
vi.stubEnv('VITE_SUPABASE_URL', 'https://test.supabase.co');
vi.stubEnv('VITE_SUPABASE_PUBLISHABLE_KEY', 'test-anon-key');

import { useDrops } from './useDrops';
import { useDropsRealtime } from './useDropsRealtime';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

const mockFetch = vi.fn();

describe('useDrops()', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = mockFetch;
    mockUseAuth.mockReturnValue({ user: { id: 'user-1' } });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches drops feed via RPC', async () => {
    const mockDrops = [
      { id: 'd1', content: 'First drop', likes_count: 3, user_has_liked: false },
      { id: 'd2', content: 'Second drop', likes_count: 1, user_has_liked: true },
    ];
    mockRpc.mockResolvedValue({ data: mockDrops, error: null });

    const { result } = renderHook(() => useDrops('live'), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(mockRpc).toHaveBeenCalledWith('get_drops_feed', {
      feed_type: 'live',
      user_id_param: 'user-1',
      limit_count: 50,
      offset_count: 0,
    });
    expect(result.current.drops).toHaveLength(2);
  });

  it('returns empty drops when RPC returns null', async () => {
    mockRpc.mockResolvedValue({ data: null, error: null });

    const { result } = renderHook(() => useDrops(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.drops).toEqual([]);
  });

  it('throws on RPC error', async () => {
    mockRpc.mockResolvedValue({ data: null, error: { message: 'Function failed' } });

    const { result } = renderHook(() => useDrops(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.error).toBeTruthy());
  });

  it('returns isAuthenticated based on user', () => {
    mockUseAuth.mockReturnValue({ user: null });
    mockRpc.mockResolvedValue({ data: [], error: null });

    const { result } = renderHook(() => useDrops(), { wrapper: createWrapper() });
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.userId).toBeUndefined();
  });

  it('has correct initial mutation states', async () => {
    mockRpc.mockResolvedValue({ data: [], error: null });

    const { result } = renderHook(() => useDrops(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.isCreating).toBe(false);
    expect(result.current.isDeleting).toBe(false);
    expect(result.current.isLiking).toBe(false);
    expect(result.current.isUnliking).toBe(false);
  });

  it('creates a drop via fetch', async () => {
    mockRpc.mockResolvedValue({ data: [], error: null });

    // Mock localStorage for access token
    const mockToken = JSON.stringify({ access_token: 'test-token' });
    localStorage.setItem('sb-test-auth-token', mockToken);

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([{ id: 'new-drop', content: 'Hello' }]),
    });

    const { result } = renderHook(() => useDrops(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      result.current.createDrop({ content: 'Hello', is_public: true });
    });

    await waitFor(() => expect(mockFetch).toHaveBeenCalled());

    const [url, options] = mockFetch.mock.calls.find(
      (call: unknown[]) => typeof call[0] === 'string' && (call[0] as string).includes('/rest/v1/drops'),
    ) || [];
    expect(url).toContain('/rest/v1/drops');
    expect(options.method).toBe('POST');

    localStorage.removeItem('sb-test-auth-token');
  });

  it('toggleLike calls like when not currently liked', async () => {
    const mockDrops = [
      { id: 'd1', content: 'Test', likes_count: 0, user_has_liked: false },
    ];
    mockRpc.mockResolvedValue({ data: mockDrops, error: null });

    const mockToken = JSON.stringify({ access_token: 'test-token' });
    localStorage.setItem('sb-test-auth-token', mockToken);
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });

    const { result } = renderHook(() => useDrops(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.toggleLike('d1', false);
    });

    await waitFor(() => {
      const likeCall = mockFetch.mock.calls.find(
        (call: unknown[]) => typeof call[0] === 'string' && (call[0] as string).includes('/rest/v1/drop_likes'),
      );
      expect(likeCall).toBeTruthy();
    });

    localStorage.removeItem('sb-test-auth-token');
  });
});

describe('useDropsRealtime()', () => {
  beforeEach(() => vi.clearAllMocks());

  it('subscribes to drops table changes', () => {
    const mockSubscribe = vi.fn().mockReturnValue({});
    const mockOn = vi.fn().mockReturnValue({ subscribe: mockSubscribe });
    mockChannel.mockReturnValue({ on: mockOn });

    renderHook(() => useDropsRealtime(), { wrapper: createWrapper() });

    expect(mockChannel).toHaveBeenCalledWith('drops-realtime');
    expect(mockOn).toHaveBeenCalledWith(
      'postgres_changes',
      expect.objectContaining({
        event: '*',
        schema: 'public',
        table: 'drops',
      }),
      expect.any(Function),
    );
    expect(mockSubscribe).toHaveBeenCalled();
  });

  it('removes channel on unmount', () => {
    const channel = {};
    const mockSubscribe = vi.fn().mockReturnValue(channel);
    const mockOn = vi.fn().mockReturnValue({ subscribe: mockSubscribe });
    mockChannel.mockReturnValue({ on: mockOn });

    const { unmount } = renderHook(() => useDropsRealtime(), { wrapper: createWrapper() });
    unmount();

    expect(mockRemoveChannel).toHaveBeenCalled();
  });
});
