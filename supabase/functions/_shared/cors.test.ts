/**
 * Tests for cors.ts CORS configuration utilities
 *
 * Tests cover:
 * - Origin validation (allowlist)
 * - Dev mode handling
 * - Localhost patterns
 * - CORS headers generation
 * - Preflight request handling
 * - Response helpers
 * - Legacy exports
 */

import {
  assertEquals,
  assertStringIncludes,
} from "https://deno.land/std@0.208.0/assert/mod.ts";

import {
  isOriginAllowed,
  getCorsHeaders,
  handleCorsPreflightRequest,
  corsJsonResponse,
  corsErrorResponse,
  createCorsHeaders,
  corsHeaders,
} from "./cors.ts";

// =============================================================================
// Test Environment Setup
// =============================================================================

const originalAllowedOrigins = Deno.env.get("ALLOWED_ORIGINS");
const originalDevMode = Deno.env.get("CORS_DEV_MODE");
const originalAllowLocalhost = Deno.env.get("ALLOW_LOCALHOST");

function setEnv(key: string, value: string | null) {
  if (value === null) {
    Deno.env.delete(key);
  } else {
    Deno.env.set(key, value);
  }
}

function restoreEnv() {
  if (originalAllowedOrigins !== undefined) {
    Deno.env.set("ALLOWED_ORIGINS", originalAllowedOrigins);
  } else {
    Deno.env.delete("ALLOWED_ORIGINS");
  }
  if (originalDevMode !== undefined) {
    Deno.env.set("CORS_DEV_MODE", originalDevMode);
  } else {
    Deno.env.delete("CORS_DEV_MODE");
  }
  if (originalAllowLocalhost !== undefined) {
    Deno.env.set("ALLOW_LOCALHOST", originalAllowLocalhost);
  } else {
    Deno.env.delete("ALLOW_LOCALHOST");
  }
}

function resetEnv() {
  Deno.env.delete("ALLOWED_ORIGINS");
  Deno.env.delete("CORS_DEV_MODE");
  Deno.env.delete("ALLOW_LOCALHOST");
}

// =============================================================================
// isOriginAllowed Tests
// =============================================================================

Deno.test("isOriginAllowed - returns false for null origin", () => {
  resetEnv();
  try {
    assertEquals(isOriginAllowed(null), false);
  } finally {
    restoreEnv();
  }
});

Deno.test("isOriginAllowed - returns true for default production origins", () => {
  resetEnv();
  try {
    assertEquals(isOriginAllowed("https://govmarket.trade"), true);
    assertEquals(isOriginAllowed("https://www.govmarket.trade"), true);
  } finally {
    restoreEnv();
  }
});

Deno.test("isOriginAllowed - returns false for non-allowed origin", () => {
  resetEnv();
  try {
    assertEquals(isOriginAllowed("https://evil.com"), false);
    assertEquals(isOriginAllowed("https://example.com"), false);
  } finally {
    restoreEnv();
  }
});

Deno.test("isOriginAllowed - uses custom ALLOWED_ORIGINS", () => {
  resetEnv();
  setEnv("ALLOWED_ORIGINS", "https://custom.com,https://another.com");
  try {
    assertEquals(isOriginAllowed("https://custom.com"), true);
    assertEquals(isOriginAllowed("https://another.com"), true);
    assertEquals(isOriginAllowed("https://govmarket.trade"), false); // Not in custom list
  } finally {
    restoreEnv();
  }
});

Deno.test("isOriginAllowed - trims whitespace from ALLOWED_ORIGINS", () => {
  resetEnv();
  setEnv("ALLOWED_ORIGINS", " https://custom.com , https://another.com ");
  try {
    assertEquals(isOriginAllowed("https://custom.com"), true);
    assertEquals(isOriginAllowed("https://another.com"), true);
  } finally {
    restoreEnv();
  }
});

Deno.test("isOriginAllowed - returns true for any origin in dev mode", () => {
  resetEnv();
  setEnv("CORS_DEV_MODE", "true");
  try {
    assertEquals(isOriginAllowed("https://any-origin.com"), true);
    assertEquals(isOriginAllowed("https://evil.com"), true);
    assertEquals(isOriginAllowed("http://localhost:3000"), true);
  } finally {
    restoreEnv();
  }
});

Deno.test("isOriginAllowed - localhost not allowed by default", () => {
  resetEnv();
  try {
    assertEquals(isOriginAllowed("http://localhost:3000"), false);
    assertEquals(isOriginAllowed("http://localhost:5173"), false);
    assertEquals(isOriginAllowed("http://127.0.0.1:3000"), false);
  } finally {
    restoreEnv();
  }
});

Deno.test("isOriginAllowed - localhost allowed when ALLOW_LOCALHOST=true", () => {
  resetEnv();
  setEnv("ALLOW_LOCALHOST", "true");
  try {
    assertEquals(isOriginAllowed("http://localhost:3000"), true);
    assertEquals(isOriginAllowed("http://localhost:5173"), true);
    assertEquals(isOriginAllowed("http://127.0.0.1:8080"), true);
  } finally {
    restoreEnv();
  }
});

Deno.test("isOriginAllowed - localhost allowed in dev mode", () => {
  resetEnv();
  setEnv("CORS_DEV_MODE", "true");
  try {
    assertEquals(isOriginAllowed("http://localhost:3000"), true);
    assertEquals(isOriginAllowed("http://127.0.0.1:5173"), true);
  } finally {
    restoreEnv();
  }
});

// =============================================================================
// getCorsHeaders Tests
// =============================================================================

Deno.test("getCorsHeaders - includes required headers", () => {
  resetEnv();
  try {
    const headers = getCorsHeaders("https://govmarket.trade");
    assertEquals(headers["Access-Control-Allow-Methods"], "GET, POST, PUT, DELETE, OPTIONS");
    assertStringIncludes(headers["Access-Control-Allow-Headers"], "authorization");
    assertStringIncludes(headers["Access-Control-Allow-Headers"], "content-type");
    assertEquals(headers["Access-Control-Max-Age"], "86400");
  } finally {
    restoreEnv();
  }
});

Deno.test("getCorsHeaders - reflects allowed origin", () => {
  resetEnv();
  try {
    const headers = getCorsHeaders("https://govmarket.trade");
    assertEquals(headers["Access-Control-Allow-Origin"], "https://govmarket.trade");
    assertEquals(headers["Vary"], "Origin");
  } finally {
    restoreEnv();
  }
});

Deno.test("getCorsHeaders - uses fallback for disallowed origin", () => {
  resetEnv();
  try {
    const headers = getCorsHeaders("https://evil.com");
    assertEquals(headers["Access-Control-Allow-Origin"], "https://govmarket.trade");
    assertEquals(headers["Vary"], "Origin");
  } finally {
    restoreEnv();
  }
});

Deno.test("getCorsHeaders - uses wildcard in dev mode", () => {
  resetEnv();
  setEnv("CORS_DEV_MODE", "true");
  try {
    const headers = getCorsHeaders("https://any-origin.com");
    assertEquals(headers["Access-Control-Allow-Origin"], "*");
    assertEquals(headers["Vary"], undefined);
  } finally {
    restoreEnv();
  }
});

Deno.test("getCorsHeaders - handles null origin", () => {
  resetEnv();
  try {
    const headers = getCorsHeaders(null);
    // Should use fallback
    assertEquals(headers["Access-Control-Allow-Origin"], "https://govmarket.trade");
  } finally {
    restoreEnv();
  }
});

Deno.test("getCorsHeaders - uses first ALLOWED_ORIGINS as fallback", () => {
  resetEnv();
  setEnv("ALLOWED_ORIGINS", "https://first.com,https://second.com");
  try {
    const headers = getCorsHeaders("https://disallowed.com");
    assertEquals(headers["Access-Control-Allow-Origin"], "https://first.com");
  } finally {
    restoreEnv();
  }
});

// =============================================================================
// handleCorsPreflightRequest Tests
// =============================================================================

Deno.test("handleCorsPreflightRequest - returns 204 status", () => {
  resetEnv();
  try {
    const req = new Request("https://api.example.com/endpoint", {
      method: "OPTIONS",
      headers: { "Origin": "https://govmarket.trade" },
    });
    const response = handleCorsPreflightRequest(req);
    assertEquals(response.status, 204);
  } finally {
    restoreEnv();
  }
});

Deno.test("handleCorsPreflightRequest - includes CORS headers", () => {
  resetEnv();
  try {
    const req = new Request("https://api.example.com/endpoint", {
      method: "OPTIONS",
      headers: { "Origin": "https://govmarket.trade" },
    });
    const response = handleCorsPreflightRequest(req);
    assertEquals(response.headers.get("Access-Control-Allow-Origin"), "https://govmarket.trade");
    assertEquals(response.headers.get("Access-Control-Allow-Methods"), "GET, POST, PUT, DELETE, OPTIONS");
  } finally {
    restoreEnv();
  }
});

Deno.test("handleCorsPreflightRequest - has null body", async () => {
  resetEnv();
  try {
    const req = new Request("https://api.example.com/endpoint", {
      method: "OPTIONS",
      headers: { "Origin": "https://govmarket.trade" },
    });
    const response = handleCorsPreflightRequest(req);
    const body = await response.text();
    assertEquals(body, "");
  } finally {
    restoreEnv();
  }
});

// =============================================================================
// corsJsonResponse Tests
// =============================================================================

Deno.test("corsJsonResponse - returns JSON with default 200 status", async () => {
  resetEnv();
  try {
    const data = { message: "success", count: 42 };
    const response = corsJsonResponse(data, "https://govmarket.trade");
    assertEquals(response.status, 200);
    assertEquals(response.headers.get("Content-Type"), "application/json");
    const body = await response.json();
    assertEquals(body.message, "success");
    assertEquals(body.count, 42);
  } finally {
    restoreEnv();
  }
});

Deno.test("corsJsonResponse - uses custom status", async () => {
  resetEnv();
  try {
    const data = { created: true };
    const response = corsJsonResponse(data, "https://govmarket.trade", 201);
    assertEquals(response.status, 201);
  } finally {
    restoreEnv();
  }
});

Deno.test("corsJsonResponse - includes CORS headers", () => {
  resetEnv();
  try {
    const response = corsJsonResponse({}, "https://govmarket.trade");
    assertEquals(response.headers.get("Access-Control-Allow-Origin"), "https://govmarket.trade");
  } finally {
    restoreEnv();
  }
});

Deno.test("corsJsonResponse - handles null origin", () => {
  resetEnv();
  try {
    const response = corsJsonResponse({}, null);
    // Should use fallback origin
    assertEquals(response.headers.get("Access-Control-Allow-Origin"), "https://govmarket.trade");
  } finally {
    restoreEnv();
  }
});

// =============================================================================
// corsErrorResponse Tests
// =============================================================================

Deno.test("corsErrorResponse - returns error JSON with default 400 status", async () => {
  resetEnv();
  try {
    const response = corsErrorResponse("Something went wrong", "https://govmarket.trade");
    assertEquals(response.status, 400);
    assertEquals(response.headers.get("Content-Type"), "application/json");
    const body = await response.json();
    assertEquals(body.error, "Something went wrong");
  } finally {
    restoreEnv();
  }
});

Deno.test("corsErrorResponse - uses custom status", () => {
  resetEnv();
  try {
    const response = corsErrorResponse("Not found", "https://govmarket.trade", 404);
    assertEquals(response.status, 404);
  } finally {
    restoreEnv();
  }
});

Deno.test("corsErrorResponse - uses 500 for server errors", async () => {
  resetEnv();
  try {
    const response = corsErrorResponse("Internal server error", "https://govmarket.trade", 500);
    assertEquals(response.status, 500);
    const body = await response.json();
    assertEquals(body.error, "Internal server error");
  } finally {
    restoreEnv();
  }
});

Deno.test("corsErrorResponse - includes CORS headers", () => {
  resetEnv();
  try {
    const response = corsErrorResponse("Error", "https://govmarket.trade");
    assertEquals(response.headers.get("Access-Control-Allow-Origin"), "https://govmarket.trade");
  } finally {
    restoreEnv();
  }
});

// =============================================================================
// createCorsHeaders Tests (Backwards Compatibility)
// =============================================================================

Deno.test("createCorsHeaders - works with origin", () => {
  resetEnv();
  try {
    const headers = createCorsHeaders("https://govmarket.trade");
    assertEquals(headers["Access-Control-Allow-Origin"], "https://govmarket.trade");
  } finally {
    restoreEnv();
  }
});

Deno.test("createCorsHeaders - works with null origin", () => {
  resetEnv();
  try {
    const headers = createCorsHeaders(null);
    assertEquals(headers["Access-Control-Allow-Origin"], "https://govmarket.trade");
  } finally {
    restoreEnv();
  }
});

Deno.test("createCorsHeaders - works with undefined origin", () => {
  resetEnv();
  try {
    const headers = createCorsHeaders(undefined);
    assertEquals(headers["Access-Control-Allow-Origin"], "https://govmarket.trade");
  } finally {
    restoreEnv();
  }
});

Deno.test("createCorsHeaders - works without argument", () => {
  resetEnv();
  try {
    const headers = createCorsHeaders();
    assertEquals(headers["Access-Control-Allow-Origin"], "https://govmarket.trade");
  } finally {
    restoreEnv();
  }
});

// =============================================================================
// corsHeaders Legacy Export Tests
// =============================================================================

Deno.test("corsHeaders - is an object with required properties", () => {
  assertEquals(typeof corsHeaders, "object");
  assertEquals(typeof corsHeaders["Access-Control-Allow-Origin"], "string");
  assertEquals(typeof corsHeaders["Access-Control-Allow-Headers"], "string");
  assertEquals(typeof corsHeaders["Access-Control-Allow-Methods"], "string");
  assertEquals(typeof corsHeaders["Access-Control-Max-Age"], "string");
});

Deno.test("corsHeaders - includes authorization in allowed headers", () => {
  assertStringIncludes(corsHeaders["Access-Control-Allow-Headers"], "authorization");
});

Deno.test("corsHeaders - includes common methods", () => {
  assertStringIncludes(corsHeaders["Access-Control-Allow-Methods"], "GET");
  assertStringIncludes(corsHeaders["Access-Control-Allow-Methods"], "POST");
  assertStringIncludes(corsHeaders["Access-Control-Allow-Methods"], "OPTIONS");
});

// =============================================================================
// Edge Case Tests
// =============================================================================

Deno.test("handles empty ALLOWED_ORIGINS gracefully", () => {
  resetEnv();
  setEnv("ALLOWED_ORIGINS", "");
  try {
    // Empty string is falsy in JavaScript, so getAllowedOrigins() returns defaults
    // This means govmarket.trade IS allowed when ALLOWED_ORIGINS is empty string
    assertEquals(isOriginAllowed("https://govmarket.trade"), true);
    // Headers should use the allowed origin
    const headers = getCorsHeaders("https://govmarket.trade");
    assertEquals(headers["Access-Control-Allow-Origin"], "https://govmarket.trade");
  } finally {
    restoreEnv();
  }
});

Deno.test("handles single origin in ALLOWED_ORIGINS", () => {
  resetEnv();
  setEnv("ALLOWED_ORIGINS", "https://single.com");
  try {
    assertEquals(isOriginAllowed("https://single.com"), true);
    assertEquals(isOriginAllowed("https://other.com"), false);
  } finally {
    restoreEnv();
  }
});

Deno.test("CORS_DEV_MODE must be exactly 'true' to enable", () => {
  resetEnv();
  setEnv("CORS_DEV_MODE", "TRUE"); // uppercase
  try {
    assertEquals(isOriginAllowed("https://evil.com"), false);
  } finally {
    restoreEnv();
  }

  setEnv("CORS_DEV_MODE", "1");
  try {
    assertEquals(isOriginAllowed("https://evil.com"), false);
  } finally {
    restoreEnv();
  }

  setEnv("CORS_DEV_MODE", "yes");
  try {
    assertEquals(isOriginAllowed("https://evil.com"), false);
  } finally {
    restoreEnv();
  }
});

Deno.test("ALLOW_LOCALHOST must be exactly 'true' to enable", () => {
  resetEnv();
  setEnv("ALLOW_LOCALHOST", "TRUE"); // uppercase
  try {
    assertEquals(isOriginAllowed("http://localhost:3000"), false);
  } finally {
    restoreEnv();
  }
});
