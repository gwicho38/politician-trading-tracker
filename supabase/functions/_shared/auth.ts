/**
 * Shared authentication utilities for Edge Functions
 *
 * Security: Uses constant-time comparison to prevent timing attacks
 * on service role key validation.
 */

/**
 * Constant-time string comparison to prevent timing attacks.
 *
 * Standard string comparison (===) can leak information about how many
 * characters match through timing differences. This function always takes
 * the same amount of time regardless of where strings differ.
 *
 * @param a First string to compare
 * @param b Second string to compare
 * @returns true if strings are equal, false otherwise
 */
export function constantTimeCompare(a: string, b: string): boolean {
  // If lengths differ, we still need to do a comparison to avoid
  // leaking length information through timing
  const aBytes = new TextEncoder().encode(a);
  const bBytes = new TextEncoder().encode(b);

  // Use the longer length to ensure we always compare the same number of bytes
  const maxLength = Math.max(aBytes.length, bBytes.length);

  let result = aBytes.length === bBytes.length ? 1 : 0;

  for (let i = 0; i < maxLength; i++) {
    // Use 0 for out-of-bounds access to maintain constant time
    const aByte = i < aBytes.length ? aBytes[i] : 0;
    const bByte = i < bBytes.length ? bBytes[i] : 0;

    // XOR the bytes and OR into result (any difference sets result to 0)
    result &= (aByte ^ bByte) === 0 ? 1 : 0;
  }

  return result === 1;
}

/**
 * Validate a token against the service role key using constant-time comparison.
 *
 * @param token The token to validate
 * @returns true if token matches service role key, false otherwise
 */
export function validateServiceRoleKey(token: string): boolean {
  const serviceRoleKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') || '';

  // Empty service role key should never validate
  if (!serviceRoleKey) {
    return false;
  }

  return constantTimeCompare(token, serviceRoleKey);
}

/**
 * Check if a request is using the service role key for authentication.
 * Used for scheduled jobs and internal service-to-service calls.
 *
 * @param req The incoming request
 * @returns true if request has valid service role authentication
 */
export function isServiceRoleRequest(req: Request): boolean {
  const authHeader = req.headers.get('authorization');
  if (!authHeader) return false;

  const token = authHeader.replace('Bearer ', '');
  return validateServiceRoleKey(token);
}

/**
 * Extract the bearer token from an authorization header.
 *
 * @param authHeader The Authorization header value
 * @returns The token without the Bearer prefix, or null if invalid
 */
export function extractBearerToken(authHeader: string | null): string | null {
  if (!authHeader) return null;

  if (authHeader.startsWith('Bearer ')) {
    return authHeader.substring(7);
  }

  return null;
}
