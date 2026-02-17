/**
 * Tests for hooks/useSignalPlayground.ts
 *
 * Tests:
 * - useSignalPlayground() - Signal generation playground with debounced API calls
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock environment variables
vi.stubEnv('VITE_SUPABASE_URL', 'https://test.supabase.co');
vi.stubEnv('VITE_SUPABASE_PUBLISHABLE_KEY', 'test-anon-key');

// Mock Supabase client (needed by transitive imports)
vi.mock('@/integrations/supabase/client', () => ({
  supabasePublic: { from: vi.fn() },
  supabase: { from: vi.fn() },
}));

import { useSignalPlayground } from './useSignalPlayground';

const mockFetch = vi.fn();

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe('useSignalPlayground()', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = mockFetch;
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        signals: [
          { ticker: 'AAPL', signal_type: 'buy', confidence_score: 0.75 },
        ],
        stats: { totalSignals: 1, buyCount: 1, holdCount: 0, mlEnhancedCount: 0 },
      }),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns default weights initially', () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useSignalPlayground(), { wrapper: createWrapper() });

    expect(result.current.weights).toBeDefined();
    expect(result.current.hasChanges).toBe(false);
    expect(result.current.modifiedCount).toBe(0);
    vi.useRealTimers();
  });

  it('accepts initial weights that differ from defaults', () => {
    vi.useFakeTimers();
    const { result } = renderHook(
      () => useSignalPlayground({ initialWeights: { baseConfidence: 0.9 } }),
      { wrapper: createWrapper() },
    );

    expect(result.current.weights.baseConfidence).toBe(0.9);
    expect(result.current.hasChanges).toBe(true);
    expect(result.current.modifiedCount).toBeGreaterThan(0);
    vi.useRealTimers();
  });

  it('updates a single weight from defaults', () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useSignalPlayground(), { wrapper: createWrapper() });

    act(() => {
      result.current.updateWeight('baseConfidence', 0.9);
    });

    expect(result.current.weights.baseConfidence).toBe(0.9);
    expect(result.current.hasChanges).toBe(true);
    vi.useRealTimers();
  });

  it('updates multiple weights at once', () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useSignalPlayground(), { wrapper: createWrapper() });

    act(() => {
      result.current.updateWeights({ baseConfidence: 0.9, bipartisanBonus: 0.3 });
    });

    expect(result.current.weights.baseConfidence).toBe(0.9);
    expect(result.current.weights.bipartisanBonus).toBe(0.3);
    vi.useRealTimers();
  });

  it('resets to defaults', () => {
    vi.useFakeTimers();
    const { result } = renderHook(
      () => useSignalPlayground({ initialWeights: { baseConfidence: 0.9 } }),
      { wrapper: createWrapper() },
    );

    expect(result.current.hasChanges).toBe(true);

    act(() => {
      result.current.resetToDefaults();
    });

    expect(result.current.hasChanges).toBe(false);
    vi.useRealTimers();
  });

  it('sets lookback days', () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useSignalPlayground(), { wrapper: createWrapper() });

    act(() => {
      result.current.setLookbackDays(30);
    });

    expect(result.current.lookbackDays).toBe(30);
    vi.useRealTimers();
  });

  it('sets user lambda', () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useSignalPlayground(), { wrapper: createWrapper() });

    act(() => {
      result.current.setUserLambda('return signal;');
    });

    expect(result.current.userLambda).toBe('return signal;');
    vi.useRealTimers();
  });

  it('tracks debouncing state', () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useSignalPlayground(), { wrapper: createWrapper() });

    act(() => {
      result.current.updateWeight('baseConfidence', 0.8);
    });

    expect(result.current.isDebouncing).toBe(true);

    act(() => {
      vi.advanceTimersByTime(600);
    });

    expect(result.current.isDebouncing).toBe(false);
    vi.useRealTimers();
  });

  it('has mlEnabled always true', () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useSignalPlayground(), { wrapper: createWrapper() });
    expect(result.current.mlEnabled).toBe(true);
    vi.useRealTimers();
  });

  it('returns signals from preview response', async () => {
    // Use real timers for async test so waitFor works
    const { result } = renderHook(() => useSignalPlayground(), { wrapper: createWrapper() });

    // Wait for debounce (500ms) + fetch + query state update
    await vi.waitFor(() => {
      expect(result.current.signals.length).toBeGreaterThan(0);
    }, { timeout: 3000 });

    expect(result.current.signals[0].ticker).toBe('AAPL');
  });

  it('calls edge function with correct URL', async () => {
    const { result } = renderHook(() => useSignalPlayground(), { wrapper: createWrapper() });

    await vi.waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    }, { timeout: 2000 });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('/functions/v1/trading-signals/preview-signals');
    expect(result.current.error).toBeNull();
  });
});
