/**
 * Shared CORS configuration for Edge Functions
 *
 * Security: Uses allowlist instead of wildcard (*) for production.
 * Configure via environment variables:
 * - ALLOWED_ORIGINS: Comma-separated list of allowed origins
 *   Default: "https://govmarket.trade,https://www.govmarket.trade"
 * - CORS_DEV_MODE: Set to "true" to allow all origins (for local development)
 */

// Default allowed origins for production
const DEFAULT_ALLOWED_ORIGINS = [
  'https://govmarket.trade',
  'https://www.govmarket.trade',
];

// Get allowed origins from environment or use defaults
function getAllowedOrigins(): string[] {
  const envOrigins = Deno.env.get('ALLOWED_ORIGINS');
  if (envOrigins) {
    return envOrigins.split(',').map(origin => origin.trim());
  }
  return DEFAULT_ALLOWED_ORIGINS;
}

// Check if we're in dev mode (allows all origins)
function isDevMode(): boolean {
  return Deno.env.get('CORS_DEV_MODE') === 'true';
}

/**
 * Check if an origin is allowed
 */
export function isOriginAllowed(origin: string | null): boolean {
  if (!origin) return false;
  if (isDevMode()) return true;

  const allowedOrigins = getAllowedOrigins();

  // Check exact match
  if (allowedOrigins.includes(origin)) return true;

  // Check localhost patterns for development
  if (origin.startsWith('http://localhost:') || origin.startsWith('http://127.0.0.1:')) {
    // Allow localhost in dev mode or when explicitly configured
    const localDevEnabled = Deno.env.get('ALLOW_LOCALHOST') === 'true';
    return localDevEnabled || isDevMode();
  }

  return false;
}

/**
 * Get CORS headers for a request
 * Returns appropriate Access-Control-Allow-Origin based on request origin
 */
export function getCorsHeaders(requestOrigin: string | null): Record<string, string> {
  const headers: Record<string, string> = {
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, x-correlation-id',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Max-Age': '86400', // 24 hours
  };

  if (isDevMode()) {
    // Dev mode: allow all origins
    headers['Access-Control-Allow-Origin'] = '*';
  } else if (requestOrigin && isOriginAllowed(requestOrigin)) {
    // Production: reflect the allowed origin
    headers['Access-Control-Allow-Origin'] = requestOrigin;
    headers['Vary'] = 'Origin';
  } else {
    // Deny: use first allowed origin as fallback (will cause CORS error in browser)
    const allowedOrigins = getAllowedOrigins();
    headers['Access-Control-Allow-Origin'] = allowedOrigins[0] || 'https://govmarket.trade';
    headers['Vary'] = 'Origin';
  }

  return headers;
}

/**
 * Handle CORS preflight OPTIONS request
 */
export function handleCorsPreflightRequest(request: Request): Response {
  const origin = request.headers.get('Origin');
  return new Response(null, {
    status: 204,
    headers: getCorsHeaders(origin),
  });
}

/**
 * Create a JSON response with CORS headers
 */
export function corsJsonResponse(
  body: unknown,
  requestOrigin: string | null,
  status: number = 200
): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...getCorsHeaders(requestOrigin),
    },
  });
}

/**
 * Create an error response with CORS headers
 */
export function corsErrorResponse(
  message: string,
  requestOrigin: string | null,
  status: number = 400
): Response {
  return new Response(JSON.stringify({ error: message }), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...getCorsHeaders(requestOrigin),
    },
  });
}

/**
 * Get CORS headers with origin from request
 * Use this wrapper function for backwards compatibility
 * When no origin is provided, uses environment-based defaults
 */
export function createCorsHeaders(origin?: string | null): Record<string, string> {
  return getCorsHeaders(origin || null);
}

// Legacy export for backwards compatibility
// In production, this will use the first allowed origin from ALLOWED_ORIGINS env var
// In dev mode (CORS_DEV_MODE=true), this will use '*'
export const corsHeaders = (() => {
  const devMode = typeof Deno !== 'undefined' && Deno.env?.get?.('CORS_DEV_MODE') === 'true';

  return {
    'Access-Control-Allow-Origin': devMode ? '*' : (
      typeof Deno !== 'undefined'
        ? (Deno.env?.get?.('ALLOWED_ORIGINS')?.split(',')[0]?.trim() || 'https://govmarket.trade')
        : 'https://govmarket.trade'
    ),
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, x-correlation-id',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Max-Age': '86400',
  };
})();
