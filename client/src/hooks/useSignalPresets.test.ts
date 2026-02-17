/**
 * Tests for hooks/useSignalPresets.ts
 *
 * Tests:
 * - useSignalPresets() - CRUD operations on signal weight presets
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock environment variables
vi.stubEnv('VITE_SUPABASE_URL', 'https://test.supabase.co');
vi.stubEnv('VITE_SUPABASE_PUBLISHABLE_KEY', 'test-anon-key');

// Mock Supabase client
const mockFrom = vi.fn();
vi.mock('@/integrations/supabase/client', () => ({
  supabasePublic: { from: (...args: unknown[]) => mockFrom(...args) },
  supabase: { from: (...args: unknown[]) => mockFrom(...args) },
}));

// Mock logger
vi.mock('@/lib/logger', () => ({
  logDebug: vi.fn(),
  logError: vi.fn(),
}));

import { useSignalPresets } from './useSignalPresets';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

function tableChain(data: unknown) {
  const terminal = { data, error: null };
  const handler: ProxyHandler<object> = {
    get(_target, prop: string) {
      if (prop === 'then')
        return (resolve: (v: unknown) => void) => Promise.resolve(terminal).then(resolve);
      return vi.fn().mockReturnValue(new Proxy({}, handler));
    },
  };
  return new Proxy({}, handler);
}

describe('useSignalPresets()', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Clear localStorage
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('fetches presets from signal_weight_presets table', async () => {
    const mockPresets = [
      { id: 'p1', name: 'Aggressive', user_id: 'u1', is_public: false, created_at: '2025-01-01' },
      { id: 'p2', name: 'Conservative', user_id: null, is_public: true, created_at: '2025-01-02' },
    ];
    mockFrom.mockReturnValue(tableChain(mockPresets));

    const { result } = renderHook(() => useSignalPresets(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(mockFrom).toHaveBeenCalledWith('signal_weight_presets');
    expect(result.current.presets).toHaveLength(2);
  });

  it('separates user and system presets', async () => {
    const mockPresets = [
      { id: 'p1', name: 'My Preset', user_id: 'u1', is_public: false },
      { id: 'p2', name: 'System Preset', user_id: null, is_public: true },
      { id: 'p3', name: 'Another User', user_id: 'u2', is_public: true },
    ];
    mockFrom.mockReturnValue(tableChain(mockPresets));

    const { result } = renderHook(() => useSignalPresets(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.userPresets).toHaveLength(2); // u1 and u2 presets
    expect(result.current.systemPresets).toHaveLength(1); // null user_id + public
  });

  it('returns empty presets on null data', async () => {
    mockFrom.mockReturnValue(tableChain(null));

    const { result } = renderHook(() => useSignalPresets(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.presets).toEqual([]);
  });

  it('has correct initial mutation states', async () => {
    mockFrom.mockReturnValue(tableChain([]));

    const { result } = renderHook(() => useSignalPresets(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.isCreating).toBe(false);
    expect(result.current.isUpdating).toBe(false);
    expect(result.current.isDeleting).toBe(false);
    expect(result.current.createError).toBeNull();
    expect(result.current.updateError).toBeNull();
    expect(result.current.deleteError).toBeNull();
  });

  it('exposes refetch function', async () => {
    mockFrom.mockReturnValue(tableChain([]));

    const { result } = renderHook(() => useSignalPresets(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(typeof result.current.refetch).toBe('function');
  });
});
