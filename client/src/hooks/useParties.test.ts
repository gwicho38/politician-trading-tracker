/**
 * Tests for hooks/useParties.ts
 *
 * Tests:
 * - useParties() - Fetches party records from Supabase
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock Supabase client
const mockFrom = vi.fn();
vi.mock('@/integrations/supabase/client', () => ({
  supabasePublic: { from: (...args: unknown[]) => mockFrom(...args) },
  supabase: { from: (...args: unknown[]) => mockFrom(...args) },
}));

import { useParties } from './useParties';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
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

describe('useParties()', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches parties from the parties table', async () => {
    const mockData = [
      { id: '1', code: 'D', name: 'Democratic Party', short_name: 'D', jurisdiction: 'us', color: '#0000FF' },
      { id: '2', code: 'R', name: 'Republican Party', short_name: 'R', jurisdiction: 'us', color: '#FF0000' },
      { id: '3', code: 'LAB', name: 'Labour Party', short_name: 'Lab', jurisdiction: 'uk', color: '#E4003B' },
    ];
    mockFrom.mockReturnValue(tableChain(mockData));

    const { result } = renderHook(() => useParties(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockFrom).toHaveBeenCalledWith('parties');
    expect(result.current.data).toHaveLength(3);
    expect(result.current.data?.[0].code).toBe('D');
  });

  it('returns empty array when no parties exist', async () => {
    mockFrom.mockReturnValue(tableChain(null));

    const { result } = renderHook(() => useParties(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([]);
  });

  it('throws on Supabase error', async () => {
    const errorTerminal = { data: null, error: { message: 'Table not found' } };
    const handler: ProxyHandler<object> = {
      get(_target, prop: string) {
        if (prop === 'then')
          return (resolve: (v: unknown) => void) => Promise.resolve(errorTerminal).then(resolve);
        return vi.fn().mockReturnValue(new Proxy({}, handler));
      },
    };
    mockFrom.mockReturnValue(new Proxy({}, handler));

    const { result } = renderHook(() => useParties(), { wrapper: createWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
