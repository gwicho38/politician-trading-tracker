/**
 * Tests for hooks/useWalletAuth.ts
 *
 * Tests:
 * - useWalletAuth() - 3-step wallet auth flow (nonce -> sign -> verify)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

// Mock wagmi hooks
const mockUseAccount = vi.fn();
const mockSignMessageAsync = vi.fn();
vi.mock('wagmi', () => ({
  useAccount: () => mockUseAccount(),
  useSignMessage: () => ({ signMessageAsync: mockSignMessageAsync }),
}));

// Mock Supabase client
const mockVerifyOtp = vi.fn();
vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    auth: { verifyOtp: (...args: unknown[]) => mockVerifyOtp(...args) },
    from: vi.fn(),
  },
  supabasePublic: { from: vi.fn() },
}));

// Mock fetchWithRetry
const mockFetchWithRetry = vi.fn();
vi.mock('@/lib/fetchWithRetry', () => ({
  fetchWithRetry: (...args: unknown[]) => mockFetchWithRetry(...args),
}));

// Mock logger
vi.mock('@/lib/logger', () => ({
  logDebug: vi.fn(),
  logError: vi.fn(),
}));

import { useWalletAuth } from './useWalletAuth';

describe('useWalletAuth()', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAccount.mockReturnValue({ address: '0xabc123', isConnected: true });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns initial state', () => {
    const { result } = renderHook(() => useWalletAuth());

    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.isConnected).toBe(true);
    expect(result.current.address).toBe('0xabc123');
    expect(typeof result.current.authenticate).toBe('function');
  });

  it('returns disconnected state when wallet not connected', () => {
    mockUseAccount.mockReturnValue({ address: undefined, isConnected: false });

    const { result } = renderHook(() => useWalletAuth());
    expect(result.current.isConnected).toBe(false);
    expect(result.current.address).toBeUndefined();
  });

  it('returns error when wallet not connected on authenticate', async () => {
    mockUseAccount.mockReturnValue({ address: undefined, isConnected: false });

    const { result } = renderHook(() => useWalletAuth());

    let authResult: { success: boolean; error?: string };
    await act(async () => {
      authResult = await result.current.authenticate();
    });

    expect(authResult!.success).toBe(false);
    expect(authResult!.error).toBe('Wallet not connected');
  });

  it('completes full auth flow successfully', async () => {
    // Step 1: nonce response
    mockFetchWithRetry.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ message: 'Sign this message: nonce-123' }),
    });

    // Step 2: wallet signs
    mockSignMessageAsync.mockResolvedValue('0xsignature');

    // Step 3: verify response
    mockFetchWithRetry.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        token: 'magic-link-token',
        isNewUser: false,
        userId: 'user-1',
      }),
    });

    // Step 4: Supabase OTP verify
    mockVerifyOtp.mockResolvedValue({ error: null });

    const { result } = renderHook(() => useWalletAuth());

    let authResult: { success: boolean; isNewUser?: boolean; userId?: string };
    await act(async () => {
      authResult = await result.current.authenticate();
    });

    expect(authResult!.success).toBe(true);
    expect(authResult!.isNewUser).toBe(false);
    expect(authResult!.userId).toBe('user-1');
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();

    // Verify nonce request
    expect(mockFetchWithRetry).toHaveBeenCalledTimes(2);
    const [nonceUrl, nonceOpts] = mockFetchWithRetry.mock.calls[0];
    expect(nonceUrl).toContain('wallet-auth?action=nonce');
    expect(JSON.parse(nonceOpts.body)).toEqual({ wallet_address: '0xabc123' });

    // Verify sign was called with message
    expect(mockSignMessageAsync).toHaveBeenCalledWith({
      message: 'Sign this message: nonce-123',
      account: '0xabc123',
    });

    // Verify verify request
    const [verifyUrl, verifyOpts] = mockFetchWithRetry.mock.calls[1];
    expect(verifyUrl).toContain('wallet-auth?action=verify');
    const verifyBody = JSON.parse(verifyOpts.body);
    expect(verifyBody.wallet_address).toBe('0xabc123');
    expect(verifyBody.signature).toBe('0xsignature');
    expect(verifyBody.message).toBe('Sign this message: nonce-123');

    // Verify OTP
    expect(mockVerifyOtp).toHaveBeenCalledWith({
      token_hash: 'magic-link-token',
      type: 'magiclink',
    });
  });

  it('handles nonce request failure', async () => {
    mockFetchWithRetry.mockResolvedValueOnce({
      ok: false,
      json: () => Promise.resolve({ error: 'Rate limited' }),
    });

    const { result } = renderHook(() => useWalletAuth());

    let authResult: { success: boolean; error?: string };
    await act(async () => {
      authResult = await result.current.authenticate();
    });

    expect(authResult!.success).toBe(false);
    expect(authResult!.error).toBe('Rate limited');
    expect(result.current.error).toBe('Rate limited');
    expect(result.current.isLoading).toBe(false);
  });

  it('handles wallet signing rejection', async () => {
    mockFetchWithRetry.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ message: 'Sign this' }),
    });

    mockSignMessageAsync.mockRejectedValue(new Error('User rejected'));

    const { result } = renderHook(() => useWalletAuth());

    let authResult: { success: boolean; error?: string };
    await act(async () => {
      authResult = await result.current.authenticate();
    });

    expect(authResult!.success).toBe(false);
    expect(authResult!.error).toBe('User rejected');
    expect(result.current.error).toBe('User rejected');
  });

  it('handles verify request failure', async () => {
    mockFetchWithRetry
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ message: 'Sign this' }),
      })
      .mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ error: 'Invalid signature' }),
      });

    mockSignMessageAsync.mockResolvedValue('0xbad');

    const { result } = renderHook(() => useWalletAuth());

    let authResult: { success: boolean; error?: string };
    await act(async () => {
      authResult = await result.current.authenticate();
    });

    expect(authResult!.success).toBe(false);
    expect(authResult!.error).toBe('Invalid signature');
  });

  it('handles Supabase OTP sign-in error', async () => {
    mockFetchWithRetry
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ message: 'Sign this' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ token: 'tok', isNewUser: false, userId: 'u1' }),
      });

    mockSignMessageAsync.mockResolvedValue('0xsig');
    mockVerifyOtp.mockResolvedValue({ error: { message: 'Token expired' } });

    const { result } = renderHook(() => useWalletAuth());

    let authResult: { success: boolean; error?: string };
    await act(async () => {
      authResult = await result.current.authenticate();
    });

    expect(authResult!.success).toBe(false);
    expect(authResult!.error).toBe('Token expired');
  });

  it('skips OTP when no token in response', async () => {
    mockFetchWithRetry
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ message: 'Sign this' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ isNewUser: true, userId: 'u-new' }),
      });

    mockSignMessageAsync.mockResolvedValue('0xsig');

    const { result } = renderHook(() => useWalletAuth());

    let authResult: { success: boolean; isNewUser?: boolean };
    await act(async () => {
      authResult = await result.current.authenticate();
    });

    expect(authResult!.success).toBe(true);
    expect(authResult!.isNewUser).toBe(true);
    expect(mockVerifyOtp).not.toHaveBeenCalled();
  });

  it('sets isLoading during authenticate', async () => {
    let resolveNonce: (v: unknown) => void;
    mockFetchWithRetry.mockReturnValueOnce(
      new Promise((r) => { resolveNonce = r; })
    );

    const { result } = renderHook(() => useWalletAuth());

    let authPromise: Promise<unknown>;
    act(() => {
      authPromise = result.current.authenticate();
    });

    expect(result.current.isLoading).toBe(true);

    await act(async () => {
      resolveNonce!({
        ok: false,
        json: () => Promise.resolve({ error: 'fail' }),
      });
      await authPromise;
    });

    expect(result.current.isLoading).toBe(false);
  });

  it('handles non-Error throws gracefully', async () => {
    mockFetchWithRetry.mockRejectedValueOnce('string error');

    const { result } = renderHook(() => useWalletAuth());

    let authResult: { success: boolean; error?: string };
    await act(async () => {
      authResult = await result.current.authenticate();
    });

    expect(authResult!.success).toBe(false);
    expect(authResult!.error).toBe('Authentication failed');
  });
});
