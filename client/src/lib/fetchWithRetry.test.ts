/**
 * Tests for lib/fetchWithRetry.ts
 *
 * Tests:
 * - fetchWithRetry() - Fetch with exponential backoff
 * - FetchRetryError - Custom error class
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fetchWithRetry, FetchRetryError } from './fetchWithRetry';

describe('fetchWithRetry()', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  describe('successful requests', () => {
    it('returns response on successful fetch', async () => {
      const mockResponse = new Response('{"success": true}', { status: 200 });
      vi.spyOn(global, 'fetch').mockResolvedValueOnce(mockResponse);

      const response = await fetchWithRetry('/api/test');

      expect(response.ok).toBe(true);
      expect(fetch).toHaveBeenCalledTimes(1);
    });

    it('passes fetch options through', async () => {
      const mockResponse = new Response('{}', { status: 200 });
      vi.spyOn(global, 'fetch').mockResolvedValueOnce(mockResponse);

      await fetchWithRetry('/api/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data: 'test' }),
      });

      expect(fetch).toHaveBeenCalledWith('/api/test', expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{"data":"test"}',
      }));
    });
  });

  describe('retry logic', () => {
    it('retries on 500 server error', async () => {
      const errorResponse = new Response('Server Error', { status: 500, statusText: 'Internal Server Error' });
      const successResponse = new Response('{}', { status: 200 });

      vi.spyOn(global, 'fetch')
        .mockResolvedValueOnce(errorResponse)
        .mockResolvedValueOnce(successResponse);

      const responsePromise = fetchWithRetry('/api/test', { maxRetries: 1, baseDelay: 100 });

      // Advance timers to trigger retry
      await vi.advanceTimersByTimeAsync(200);

      const response = await responsePromise;
      expect(response.ok).toBe(true);
      expect(fetch).toHaveBeenCalledTimes(2);
    });

    it('retries on 429 rate limit', async () => {
      const rateLimitResponse = new Response('Rate Limited', { status: 429, statusText: 'Too Many Requests' });
      const successResponse = new Response('{}', { status: 200 });

      vi.spyOn(global, 'fetch')
        .mockResolvedValueOnce(rateLimitResponse)
        .mockResolvedValueOnce(successResponse);

      const responsePromise = fetchWithRetry('/api/test', { maxRetries: 1, baseDelay: 100 });
      await vi.advanceTimersByTimeAsync(200);

      const response = await responsePromise;
      expect(response.ok).toBe(true);
    });

    it('retries on 408 timeout', async () => {
      const timeoutResponse = new Response('Timeout', { status: 408, statusText: 'Request Timeout' });
      const successResponse = new Response('{}', { status: 200 });

      vi.spyOn(global, 'fetch')
        .mockResolvedValueOnce(timeoutResponse)
        .mockResolvedValueOnce(successResponse);

      const responsePromise = fetchWithRetry('/api/test', { maxRetries: 1, baseDelay: 100 });
      await vi.advanceTimersByTimeAsync(200);

      const response = await responsePromise;
      expect(response.ok).toBe(true);
    });

    it('calls onRetry callback on retry', async () => {
      const errorResponse = new Response('Server Error', { status: 500, statusText: 'Internal Server Error' });
      const successResponse = new Response('{}', { status: 200 });
      const onRetry = vi.fn();

      vi.spyOn(global, 'fetch')
        .mockResolvedValueOnce(errorResponse)
        .mockResolvedValueOnce(successResponse);

      const responsePromise = fetchWithRetry('/api/test', {
        maxRetries: 1,
        baseDelay: 100,
        onRetry,
      });

      await vi.advanceTimersByTimeAsync(200);
      await responsePromise;

      expect(onRetry).toHaveBeenCalledTimes(1);
      expect(onRetry).toHaveBeenCalledWith(1, expect.any(Error), expect.any(Number));
    });
  });

  describe('non-retryable errors', () => {
    it('does not retry on 400 bad request', async () => {
      const badRequestResponse = new Response('Bad Request', { status: 400, statusText: 'Bad Request' });
      vi.spyOn(global, 'fetch').mockResolvedValueOnce(badRequestResponse);

      const response = await fetchWithRetry('/api/test', { maxRetries: 3 });

      expect(response.status).toBe(400);
      expect(fetch).toHaveBeenCalledTimes(1);
    });

    it('does not retry on 401 unauthorized', async () => {
      const unauthorizedResponse = new Response('Unauthorized', { status: 401, statusText: 'Unauthorized' });
      vi.spyOn(global, 'fetch').mockResolvedValueOnce(unauthorizedResponse);

      const response = await fetchWithRetry('/api/test', { maxRetries: 3 });

      expect(response.status).toBe(401);
      expect(fetch).toHaveBeenCalledTimes(1);
    });

    it('does not retry on 403 forbidden', async () => {
      const forbiddenResponse = new Response('Forbidden', { status: 403, statusText: 'Forbidden' });
      vi.spyOn(global, 'fetch').mockResolvedValueOnce(forbiddenResponse);

      const response = await fetchWithRetry('/api/test', { maxRetries: 3 });

      expect(response.status).toBe(403);
      expect(fetch).toHaveBeenCalledTimes(1);
    });

    it('does not retry on 404 not found', async () => {
      const notFoundResponse = new Response('Not Found', { status: 404, statusText: 'Not Found' });
      vi.spyOn(global, 'fetch').mockResolvedValueOnce(notFoundResponse);

      const response = await fetchWithRetry('/api/test', { maxRetries: 3 });

      expect(response.status).toBe(404);
      expect(fetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('max retries exceeded', () => {
    it('throws FetchRetryError after max retries', async () => {
      vi.useRealTimers(); // Use real timers to avoid complexity
      const errorResponse = new Response('Server Error', { status: 500, statusText: 'Internal Server Error' });
      vi.spyOn(global, 'fetch').mockResolvedValue(errorResponse);

      try {
        await fetchWithRetry('/api/test', { maxRetries: 1, baseDelay: 1, maxDelay: 1 });
        expect.fail('Should have thrown');
      } catch (error) {
        expect(error).toBeInstanceOf(FetchRetryError);
        expect((error as FetchRetryError).attempts).toBe(2);
      }
      expect(fetch).toHaveBeenCalledTimes(2); // Initial + 1 retry
      vi.useFakeTimers(); // Restore fake timers
    });
  });

  describe('network errors', () => {
    it('retries on network failure', async () => {
      const networkError = new Error('Network error');
      const successResponse = new Response('{}', { status: 200 });

      vi.spyOn(global, 'fetch')
        .mockRejectedValueOnce(networkError)
        .mockResolvedValueOnce(successResponse);

      const responsePromise = fetchWithRetry('/api/test', { maxRetries: 1, baseDelay: 100 });
      await vi.advanceTimersByTimeAsync(200);

      const response = await responsePromise;
      expect(response.ok).toBe(true);
    });

    it('does not retry on AbortError', async () => {
      const abortError = new DOMException('Aborted', 'AbortError');
      vi.spyOn(global, 'fetch').mockRejectedValueOnce(abortError);

      await expect(fetchWithRetry('/api/test', { maxRetries: 3 })).rejects.toThrow('Aborted');
      expect(fetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('default options', () => {
    it('uses default maxRetries of 3', async () => {
      vi.useRealTimers(); // Use real timers to avoid complexity
      const errorResponse = new Response('Server Error', { status: 500, statusText: 'Internal Server Error' });
      vi.spyOn(global, 'fetch').mockResolvedValue(errorResponse);

      try {
        await fetchWithRetry('/api/test', { baseDelay: 1, maxDelay: 1 }); // Fast delays
        expect.fail('Should have thrown');
      } catch (error) {
        expect(error).toBeInstanceOf(FetchRetryError);
        expect((error as FetchRetryError).attempts).toBe(4); // Initial + 3 retries
      }
      expect(fetch).toHaveBeenCalledTimes(4);
      vi.useFakeTimers(); // Restore fake timers
    });
  });
});

describe('FetchRetryError', () => {
  it('has correct name', () => {
    const error = new FetchRetryError('Test error', 500, 3, new Error('Original'));

    expect(error.name).toBe('FetchRetryError');
  });

  it('stores status', () => {
    const error = new FetchRetryError('Test error', 500, 3, new Error('Original'));

    expect(error.status).toBe(500);
  });

  it('stores attempts', () => {
    const error = new FetchRetryError('Test error', 500, 3, new Error('Original'));

    expect(error.attempts).toBe(3);
  });

  it('stores lastError', () => {
    const originalError = new Error('Original');
    const error = new FetchRetryError('Test error', 500, 3, originalError);

    expect(error.lastError).toBe(originalError);
  });

  it('handles undefined status', () => {
    const error = new FetchRetryError('Test error', undefined, 3, new Error('Original'));

    expect(error.status).toBeUndefined();
  });
});
