/**
 * Tests for hooks/useStrategyShowcase.ts
 *
 * Tests:
 * - useStrategyShowcase() - Public strategies with like/unlike optimistic updates
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock Supabase client
const mockRpc = vi.fn();
const mockInsert = vi.fn();
const mockDelete = vi.fn();
vi.mock('@/integrations/supabase/client', () => ({
  supabasePublic: {
    rpc: (...args: unknown[]) => mockRpc(...args),
    from: vi.fn(),
  },
  supabase: {
    from: (table: string) => {
      if (table === 'strategy_likes') {
        return {
          insert: mockInsert,
          delete: () => ({
            eq: () => ({
              eq: mockDelete,
            }),
          }),
        };
      }
      return {};
    },
  },
}));

// Mock useAuth
const mockUseAuth = vi.fn();
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => mockUseAuth(),
}));

import { useStrategyShowcase } from './useStrategyShowcase';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe('useStrategyShowcase()', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ user: { id: 'user-1' } });
  });

  it('fetches public strategies via RPC', async () => {
    const mockStrategies = [
      { id: 's1', name: 'Aggressive', likes_count: 10, user_has_liked: false },
      { id: 's2', name: 'Conservative', likes_count: 5, user_has_liked: true },
    ];
    mockRpc.mockResolvedValue({ data: mockStrategies, error: null });

    const { result } = renderHook(() => useStrategyShowcase('recent'), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(mockRpc).toHaveBeenCalledWith('get_public_strategies', {
      sort_by: 'recent',
      user_id_param: 'user-1',
    });
    expect(result.current.strategies).toHaveLength(2);
  });

  it('passes null user_id when not authenticated', async () => {
    mockUseAuth.mockReturnValue({ user: null });
    mockRpc.mockResolvedValue({ data: [], error: null });

    renderHook(() => useStrategyShowcase(), { wrapper: createWrapper() });
    await waitFor(() => expect(mockRpc).toHaveBeenCalled());

    expect(mockRpc).toHaveBeenCalledWith('get_public_strategies', {
      sort_by: 'recent',
      user_id_param: null,
    });
  });

  it('returns isAuthenticated based on user', () => {
    mockUseAuth.mockReturnValue({ user: null });
    mockRpc.mockResolvedValue({ data: [], error: null });

    const { result } = renderHook(() => useStrategyShowcase(), { wrapper: createWrapper() });
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('returns empty array on null data', async () => {
    mockRpc.mockResolvedValue({ data: null, error: null });

    const { result } = renderHook(() => useStrategyShowcase(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.strategies).toEqual([]);
  });

  it('handles RPC error', async () => {
    mockRpc.mockResolvedValue({ data: null, error: { message: 'Function failed' } });

    const { result } = renderHook(() => useStrategyShowcase(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.error).toBeTruthy());
  });

  it('has correct initial mutation states', async () => {
    mockRpc.mockResolvedValue({ data: [], error: null });

    const { result } = renderHook(() => useStrategyShowcase(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.isLiking).toBe(false);
    expect(result.current.isUnliking).toBe(false);
    expect(result.current.likeError).toBeNull();
  });

  it('supports popular sort option', async () => {
    mockRpc.mockResolvedValue({ data: [], error: null });

    renderHook(() => useStrategyShowcase('popular'), { wrapper: createWrapper() });
    await waitFor(() => expect(mockRpc).toHaveBeenCalled());

    expect(mockRpc).toHaveBeenCalledWith('get_public_strategies', {
      sort_by: 'popular',
      user_id_param: 'user-1',
    });
  });
});
