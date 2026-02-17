/**
 * Tests for hooks/useAdmin.ts
 *
 * Tests:
 * - useAdmin() - Checks admin role via auth session + RPC
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';

// Mock Supabase client
const mockGetSession = vi.fn();
const mockRpc = vi.fn();
const mockOnAuthStateChange = vi.fn();
vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    auth: {
      getSession: () => mockGetSession(),
      onAuthStateChange: (cb: () => void) => {
        mockOnAuthStateChange(cb);
        return { data: { subscription: { unsubscribe: vi.fn() } } };
      },
    },
    rpc: (...args: unknown[]) => mockRpc(...args),
  },
  supabasePublic: {
    auth: { getSession: () => mockGetSession() },
    rpc: (...args: unknown[]) => mockRpc(...args),
  },
}));

// Mock logger
vi.mock('@/lib/logger', () => ({
  logError: vi.fn(),
}));

import { useAdmin } from './useAdmin';

describe('useAdmin()', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns isAdmin=false when no session', async () => {
    mockGetSession.mockResolvedValue({
      data: { session: null },
      error: null,
    });

    const { result } = renderHook(() => useAdmin());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.isAdmin).toBe(false);
  });

  it('returns isAdmin=false on session error', async () => {
    mockGetSession.mockResolvedValue({
      data: { session: null },
      error: { message: 'Session expired' },
    });

    const { result } = renderHook(() => useAdmin());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.isAdmin).toBe(false);
  });

  it('returns isAdmin=true when has_role RPC returns true', async () => {
    mockGetSession.mockResolvedValue({
      data: { session: { user: { id: 'user-123' } } },
      error: null,
    });
    mockRpc.mockResolvedValue({ data: true, error: null });

    const { result } = renderHook(() => useAdmin());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.isAdmin).toBe(true);
    expect(mockRpc).toHaveBeenCalledWith('has_role', {
      _user_id: 'user-123',
      _role: 'admin',
    });
  });

  it('returns isAdmin=false when has_role returns false', async () => {
    mockGetSession.mockResolvedValue({
      data: { session: { user: { id: 'user-456' } } },
      error: null,
    });
    mockRpc.mockResolvedValue({ data: false, error: null });

    const { result } = renderHook(() => useAdmin());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.isAdmin).toBe(false);
  });

  it('returns isAdmin=false when RPC errors', async () => {
    mockGetSession.mockResolvedValue({
      data: { session: { user: { id: 'user-789' } } },
      error: null,
    });
    mockRpc.mockResolvedValue({ data: null, error: { message: 'RPC failed' } });

    const { result } = renderHook(() => useAdmin());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.isAdmin).toBe(false);
  });

  it('starts in loading state', () => {
    mockGetSession.mockReturnValue(new Promise(() => {})); // never resolves

    const { result } = renderHook(() => useAdmin());
    expect(result.current.isLoading).toBe(true);
  });

  it('subscribes to auth state changes', async () => {
    mockGetSession.mockResolvedValue({
      data: { session: null },
      error: null,
    });

    renderHook(() => useAdmin());
    await waitFor(() => expect(mockOnAuthStateChange).toHaveBeenCalled());
  });
});
