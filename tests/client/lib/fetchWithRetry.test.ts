import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fetchWithRetry, FetchRetryError } from '../../../client/src/lib/fetchWithRetry';

describe('fetchWithRetry', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  describe('successful requests', () => {
    it('should return response on first successful attempt', async () => {
      const mockResponse = new Response(JSON.stringify({ data: 'test' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
      vi.spyOn(global, 'fetch').mockResolvedValueOnce(mockResponse);

      const response = await fetchWithRetry('https://api.example.com/data');

      expect(response.ok).toBe(true);
      expect(fetch).toHaveBeenCalledTimes(1);
    });

    it('should pass through request options', async () => {
      const mockResponse = new Response('', { status: 200 });
      vi.spyOn(global, 'fetch').mockResolvedValueOnce(mockResponse);

      await fetchWithRetry('https://api.example.com/data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: 'value' }),
      });

      expect(fetch).toHaveBeenCalledWith('https://api.example.com/data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: 'value' }),
      });
    });
  });

  describe('retry behavior', () => {
    it('should retry on 500 server error', async () => {
      const errorResponse = new Response('', { status: 500, statusText: 'Internal Server Error' });
      const successResponse = new Response('', { status: 200 });

      vi.spyOn(global, 'fetch')
        .mockResolvedValueOnce(errorResponse)
        .mockResolvedValueOnce(successResponse);

      const fetchPromise = fetchWithRetry('https://api.example.com/data', { maxRetries: 3 });

      // Advance timer for first retry delay
      await vi.advanceTimersByTimeAsync(2000);

      const response = await fetchPromise;

      expect(response.ok).toBe(true);
      expect(fetch).toHaveBeenCalledTimes(2);
    });

    it('should retry on 503 service unavailable', async () => {
      const errorResponse = new Response('', { status: 503, statusText: 'Service Unavailable' });
      const successResponse = new Response('', { status: 200 });

      vi.spyOn(global, 'fetch')
        .mockResolvedValueOnce(errorResponse)
        .mockResolvedValueOnce(successResponse);

      const fetchPromise = fetchWithRetry('https://api.example.com/data', { maxRetries: 3 });
      await vi.advanceTimersByTimeAsync(2000);

      const response = await fetchPromise;

      expect(response.ok).toBe(true);
      expect(fetch).toHaveBeenCalledTimes(2);
    });

    it('should retry on 429 rate limit', async () => {
      const rateLimitResponse = new Response('', { status: 429, statusText: 'Too Many Requests' });
      const successResponse = new Response('', { status: 200 });

      vi.spyOn(global, 'fetch')
        .mockResolvedValueOnce(rateLimitResponse)
        .mockResolvedValueOnce(successResponse);

      const fetchPromise = fetchWithRetry('https://api.example.com/data', { maxRetries: 3 });
      await vi.advanceTimersByTimeAsync(2000);

      const response = await fetchPromise;

      expect(response.ok).toBe(true);
      expect(fetch).toHaveBeenCalledTimes(2);
    });

    it('should retry on 408 request timeout', async () => {
      const timeoutResponse = new Response('', { status: 408, statusText: 'Request Timeout' });
      const successResponse = new Response('', { status: 200 });

      vi.spyOn(global, 'fetch')
        .mockResolvedValueOnce(timeoutResponse)
        .mockResolvedValueOnce(successResponse);

      const fetchPromise = fetchWithRetry('https://api.example.com/data', { maxRetries: 3 });
      await vi.advanceTimersByTimeAsync(2000);

      const response = await fetchPromise;

      expect(response.ok).toBe(true);
      expect(fetch).toHaveBeenCalledTimes(2);
    });

    it('should retry on network error', async () => {
      const networkError = new Error('Network error');
      const successResponse = new Response('', { status: 200 });

      vi.spyOn(global, 'fetch')
        .mockRejectedValueOnce(networkError)
        .mockResolvedValueOnce(successResponse);

      const fetchPromise = fetchWithRetry('https://api.example.com/data', { maxRetries: 3 });
      await vi.advanceTimersByTimeAsync(2000);

      const response = await fetchPromise;

      expect(response.ok).toBe(true);
      expect(fetch).toHaveBeenCalledTimes(2);
    });

    it('should call onRetry callback when retrying', async () => {
      const onRetry = vi.fn();
      const errorResponse = new Response('', { status: 500, statusText: 'Internal Server Error' });
      const successResponse = new Response('', { status: 200 });

      vi.spyOn(global, 'fetch')
        .mockResolvedValueOnce(errorResponse)
        .mockResolvedValueOnce(successResponse);

      const fetchPromise = fetchWithRetry('https://api.example.com/data', {
        maxRetries: 3,
        onRetry,
      });
      await vi.advanceTimersByTimeAsync(2000);

      await fetchPromise;

      expect(onRetry).toHaveBeenCalledTimes(1);
      expect(onRetry).toHaveBeenCalledWith(1, expect.any(Error), expect.any(Number));
    });
  });

  describe('no retry scenarios', () => {
    it('should NOT retry on 401 unauthorized', async () => {
      const unauthorizedResponse = new Response('', { status: 401, statusText: 'Unauthorized' });

      vi.spyOn(global, 'fetch').mockResolvedValueOnce(unauthorizedResponse);

      const response = await fetchWithRetry('https://api.example.com/data', { maxRetries: 3 });

      // Should return the 401 response without retrying
      expect(response.status).toBe(401);
      expect(fetch).toHaveBeenCalledTimes(1);
    });

    it('should NOT retry on 403 forbidden', async () => {
      const forbiddenResponse = new Response('', { status: 403, statusText: 'Forbidden' });

      vi.spyOn(global, 'fetch').mockResolvedValueOnce(forbiddenResponse);

      const response = await fetchWithRetry('https://api.example.com/data', { maxRetries: 3 });

      expect(response.status).toBe(403);
      expect(fetch).toHaveBeenCalledTimes(1);
    });

    it('should NOT retry on 404 not found', async () => {
      const notFoundResponse = new Response('', { status: 404, statusText: 'Not Found' });

      vi.spyOn(global, 'fetch').mockResolvedValueOnce(notFoundResponse);

      const response = await fetchWithRetry('https://api.example.com/data', { maxRetries: 3 });

      expect(response.status).toBe(404);
      expect(fetch).toHaveBeenCalledTimes(1);
    });

    it('should NOT retry on 400 bad request', async () => {
      const badRequestResponse = new Response('', { status: 400, statusText: 'Bad Request' });

      vi.spyOn(global, 'fetch').mockResolvedValueOnce(badRequestResponse);

      const response = await fetchWithRetry('https://api.example.com/data', { maxRetries: 3 });

      expect(response.status).toBe(400);
      expect(fetch).toHaveBeenCalledTimes(1);
    });

    it('should NOT retry on AbortError', async () => {
      const abortError = new DOMException('Aborted', 'AbortError');

      vi.spyOn(global, 'fetch').mockRejectedValueOnce(abortError);

      await expect(
        fetchWithRetry('https://api.example.com/data', { maxRetries: 3 })
      ).rejects.toThrow('Aborted');

      expect(fetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('max retries exceeded', () => {
    it('should throw FetchRetryError after max retries', async () => {
      vi.useRealTimers(); // Use real timers for this test

      const errorResponse = new Response('', { status: 500, statusText: 'Internal Server Error' });
      vi.spyOn(global, 'fetch').mockResolvedValue(errorResponse);

      await expect(
        fetchWithRetry('https://api.example.com/data', {
          maxRetries: 2,
          baseDelay: 1, // Very short delay for testing
          maxDelay: 10,
        })
      ).rejects.toThrow(FetchRetryError);

      expect(fetch).toHaveBeenCalledTimes(3); // 1 initial + 2 retries
    });

    it('should include attempt count in error', async () => {
      vi.useRealTimers(); // Use real timers for this test

      const errorResponse = new Response('', { status: 500, statusText: 'Internal Server Error' });
      vi.spyOn(global, 'fetch').mockResolvedValue(errorResponse);

      try {
        await fetchWithRetry('https://api.example.com/data', {
          maxRetries: 2,
          baseDelay: 1,
          maxDelay: 10,
        });
        expect.fail('Should have thrown');
      } catch (error) {
        expect(error).toBeInstanceOf(FetchRetryError);
        expect((error as FetchRetryError).attempts).toBe(3);
        expect((error as FetchRetryError).status).toBe(500);
      }
    });
  });

  describe('exponential backoff', () => {
    it('should use increasing delays for retries', async () => {
      const errorResponse = new Response('', { status: 500, statusText: 'Internal Server Error' });
      const successResponse = new Response('', { status: 200 });

      vi.spyOn(global, 'fetch')
        .mockResolvedValueOnce(errorResponse)
        .mockResolvedValueOnce(errorResponse)
        .mockResolvedValueOnce(successResponse);

      const fetchPromise = fetchWithRetry('https://api.example.com/data', {
        maxRetries: 3,
        baseDelay: 1000,
        maxDelay: 30000,
      });

      // First retry should happen after ~1000ms (with jitter)
      await vi.advanceTimersByTimeAsync(1500);
      expect(fetch).toHaveBeenCalledTimes(2);

      // Second retry should happen after ~2000ms (with jitter)
      await vi.advanceTimersByTimeAsync(3000);
      expect(fetch).toHaveBeenCalledTimes(3);

      await fetchPromise;
    });
  });

  describe('default options', () => {
    it('should use default maxRetries of 3', async () => {
      vi.useRealTimers(); // Use real timers for this test

      const errorResponse = new Response('', { status: 500, statusText: 'Internal Server Error' });
      vi.spyOn(global, 'fetch').mockResolvedValue(errorResponse);

      await expect(
        fetchWithRetry('https://api.example.com/data', {
          baseDelay: 1, // Override delay for fast testing
          maxDelay: 10,
        })
      ).rejects.toThrow(FetchRetryError);

      expect(fetch).toHaveBeenCalledTimes(4); // 1 initial + 3 retries (default)
    });
  });
});
