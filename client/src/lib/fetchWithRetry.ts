/**
 * Fetch wrapper with exponential backoff retry logic.
 *
 * Features:
 * - Exponential backoff with jitter
 * - Smart retry logic (no retry on 4xx except 408/429)
 * - Configurable retry count and delays
 * - AbortController support for cancellation
 */

export interface FetchRetryOptions extends RequestInit {
  /** Maximum number of retry attempts (default: 3) */
  maxRetries?: number;
  /** Base delay in ms (default: 1000) */
  baseDelay?: number;
  /** Maximum delay in ms (default: 30000) */
  maxDelay?: number;
  /** Callback when a retry occurs */
  onRetry?: (attempt: number, error: Error, delay: number) => void;
}

export class FetchRetryError extends Error {
  public readonly status?: number;
  public readonly attempts: number;
  public readonly lastError: Error;

  constructor(message: string, status: number | undefined, attempts: number, lastError: Error) {
    super(message);
    this.name = 'FetchRetryError';
    this.status = status;
    this.attempts = attempts;
    this.lastError = lastError;
  }
}

/**
 * Calculate retry delay with exponential backoff and jitter.
 */
const calculateDelay = (attemptIndex: number, baseDelay: number, maxDelay: number): number => {
  const exponentialDelay = Math.min(baseDelay * Math.pow(2, attemptIndex), maxDelay);
  // Add jitter: ±25% randomization to prevent thundering herd
  const jitter = exponentialDelay * 0.25 * (Math.random() * 2 - 1);
  return Math.max(0, exponentialDelay + jitter);
};

/**
 * Determine if an HTTP status code should trigger a retry.
 */
const shouldRetryStatus = (status: number): boolean => {
  // Don't retry successful responses
  if (status >= 200 && status < 300) return false;
  // Don't retry auth errors
  if (status === 401 || status === 403) return false;
  // Retry timeout (408) and rate limit (429)
  if (status === 408 || status === 429) return true;
  // Don't retry other client errors
  if (status >= 400 && status < 500) return false;
  // Retry server errors (5xx)
  return true;
};

/**
 * Sleep for a specified duration.
 */
const sleep = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Fetch with automatic retry using exponential backoff.
 *
 * @example
 * ```ts
 * const response = await fetchWithRetry('/api/data', {
 *   method: 'POST',
 *   body: JSON.stringify({ data }),
 *   maxRetries: 3,
 *   onRetry: (attempt, error, delay) => {
 *     console.log(`Retry ${attempt} after ${delay}ms: ${error.message}`);
 *   },
 * });
 * ```
 */
export const fetchWithRetry = async (
  url: string,
  options: FetchRetryOptions = {}
): Promise<Response> => {
  const {
    maxRetries = 3,
    baseDelay = 1000,
    maxDelay = 30000,
    onRetry,
    ...fetchOptions
  } = options;

  let lastError: Error = new Error('No attempts made');
  let lastStatus: number | undefined;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(url, fetchOptions);

      // Check if we should retry based on status
      if (!response.ok && shouldRetryStatus(response.status)) {
        lastStatus = response.status;
        const errorMessage = `HTTP ${response.status}: ${response.statusText}`;

        if (attempt < maxRetries) {
          const delay = calculateDelay(attempt, baseDelay, maxDelay);
          lastError = new Error(errorMessage);
          onRetry?.(attempt + 1, lastError, delay);
          await sleep(delay);
          continue;
        }

        // Last attempt failed
        throw new FetchRetryError(
          `Failed after ${maxRetries + 1} attempts: ${errorMessage}`,
          response.status,
          attempt + 1,
          new Error(errorMessage)
        );
      }

      // Success or non-retryable status
      return response;
    } catch (error) {
      // Network errors (fetch throws on network failure)
      if (error instanceof FetchRetryError) {
        throw error;
      }

      lastError = error instanceof Error ? error : new Error(String(error));

      // Check if it's an abort error (don't retry)
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw error;
      }

      if (attempt < maxRetries) {
        const delay = calculateDelay(attempt, baseDelay, maxDelay);
        onRetry?.(attempt + 1, lastError, delay);
        await sleep(delay);
        continue;
      }

      // Last attempt failed
      throw new FetchRetryError(
        `Failed after ${maxRetries + 1} attempts: ${lastError.message}`,
        lastStatus,
        attempt + 1,
        lastError
      );
    }
  }

  // Should never reach here, but TypeScript needs this
  throw new FetchRetryError(
    `Failed after ${maxRetries + 1} attempts`,
    lastStatus,
    maxRetries + 1,
    lastError
  );
};

export default fetchWithRetry;
