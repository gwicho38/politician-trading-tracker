/**
 * Tests for auth.ts authentication utilities
 *
 * Tests cover:
 * - Constant-time comparison for timing attack resistance
 * - Service role key validation
 * - Bearer token extraction
 * - Service role request detection
 */

import {
  assertEquals,
} from "https://deno.land/std@0.208.0/assert/mod.ts";

import {
  constantTimeCompare,
  validateServiceRoleKey,
  isServiceRoleRequest,
  extractBearerToken,
} from "./auth.ts";

// =============================================================================
// Test Environment Setup
// =============================================================================

const originalKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");

function setServiceRoleKey(key: string | null) {
  if (key === null) {
    Deno.env.delete("SUPABASE_SERVICE_ROLE_KEY");
  } else {
    Deno.env.set("SUPABASE_SERVICE_ROLE_KEY", key);
  }
}

function restoreEnv() {
  if (originalKey) {
    Deno.env.set("SUPABASE_SERVICE_ROLE_KEY", originalKey);
  } else {
    Deno.env.delete("SUPABASE_SERVICE_ROLE_KEY");
  }
}

// =============================================================================
// constantTimeCompare Tests
// =============================================================================

Deno.test("constantTimeCompare - returns true for equal strings", () => {
  assertEquals(constantTimeCompare("hello", "hello"), true);
});

Deno.test("constantTimeCompare - returns false for different strings", () => {
  assertEquals(constantTimeCompare("hello", "world"), false);
});

Deno.test("constantTimeCompare - returns false for different length strings", () => {
  assertEquals(constantTimeCompare("short", "longer string"), false);
});

Deno.test("constantTimeCompare - returns true for empty strings", () => {
  assertEquals(constantTimeCompare("", ""), true);
});

Deno.test("constantTimeCompare - returns false for empty vs non-empty", () => {
  assertEquals(constantTimeCompare("", "something"), false);
  assertEquals(constantTimeCompare("something", ""), false);
});

Deno.test("constantTimeCompare - handles unicode correctly", () => {
  assertEquals(constantTimeCompare("你好", "你好"), true);
  assertEquals(constantTimeCompare("你好", "世界"), false);
});

Deno.test("constantTimeCompare - handles special characters", () => {
  assertEquals(constantTimeCompare("!@#$%^&*()", "!@#$%^&*()"), true);
  assertEquals(constantTimeCompare("!@#$%", "!@#$^"), false);
});

Deno.test("constantTimeCompare - handles long strings", () => {
  const long1 = "a".repeat(10000);
  const long2 = "a".repeat(10000);
  const long3 = "a".repeat(9999) + "b";
  assertEquals(constantTimeCompare(long1, long2), true);
  assertEquals(constantTimeCompare(long1, long3), false);
});

Deno.test("constantTimeCompare - handles typical API keys", () => {
  const key1 = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0";
  const key2 = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0";
  const key3 = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5ODc2NTQzMjEwIn0";
  assertEquals(constantTimeCompare(key1, key2), true);
  assertEquals(constantTimeCompare(key1, key3), false);
});

// =============================================================================
// validateServiceRoleKey Tests
// =============================================================================

Deno.test("validateServiceRoleKey - returns false when key not configured", () => {
  setServiceRoleKey(null);
  try {
    assertEquals(validateServiceRoleKey("any-token"), false);
  } finally {
    restoreEnv();
  }
});

Deno.test("validateServiceRoleKey - returns false when key is empty string", () => {
  setServiceRoleKey("");
  try {
    assertEquals(validateServiceRoleKey("any-token"), false);
  } finally {
    restoreEnv();
  }
});

Deno.test("validateServiceRoleKey - returns true for matching token", () => {
  setServiceRoleKey("secret-service-role-key");
  try {
    assertEquals(validateServiceRoleKey("secret-service-role-key"), true);
  } finally {
    restoreEnv();
  }
});

Deno.test("validateServiceRoleKey - returns false for non-matching token", () => {
  setServiceRoleKey("secret-service-role-key");
  try {
    assertEquals(validateServiceRoleKey("wrong-key"), false);
  } finally {
    restoreEnv();
  }
});

Deno.test("validateServiceRoleKey - returns false for partial match", () => {
  setServiceRoleKey("secret-service-role-key");
  try {
    assertEquals(validateServiceRoleKey("secret"), false);
    assertEquals(validateServiceRoleKey("secret-service-role-key-extra"), false);
  } finally {
    restoreEnv();
  }
});

Deno.test("validateServiceRoleKey - returns false for empty token", () => {
  setServiceRoleKey("secret-service-role-key");
  try {
    assertEquals(validateServiceRoleKey(""), false);
  } finally {
    restoreEnv();
  }
});

// =============================================================================
// extractBearerToken Tests
// =============================================================================

Deno.test("extractBearerToken - extracts token from valid Bearer header", () => {
  assertEquals(extractBearerToken("Bearer my-token-123"), "my-token-123");
});

Deno.test("extractBearerToken - returns null for null header", () => {
  assertEquals(extractBearerToken(null), null);
});

Deno.test("extractBearerToken - returns null for non-Bearer header", () => {
  assertEquals(extractBearerToken("Basic dXNlcjpwYXNz"), null);
});

Deno.test("extractBearerToken - returns null for malformed Bearer", () => {
  assertEquals(extractBearerToken("bearer token"), null); // lowercase
  assertEquals(extractBearerToken("BearerToken"), null); // no space
});

Deno.test("extractBearerToken - handles empty token after Bearer", () => {
  assertEquals(extractBearerToken("Bearer "), "");
});

Deno.test("extractBearerToken - handles token with spaces", () => {
  assertEquals(extractBearerToken("Bearer token with spaces"), "token with spaces");
});

Deno.test("extractBearerToken - handles JWT token format", () => {
  const jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature";
  assertEquals(extractBearerToken(`Bearer ${jwt}`), jwt);
});

// =============================================================================
// isServiceRoleRequest Tests
// =============================================================================

Deno.test("isServiceRoleRequest - returns false for request without auth header", () => {
  setServiceRoleKey("secret-key");
  try {
    const req = new Request("https://example.com/api");
    assertEquals(isServiceRoleRequest(req), false);
  } finally {
    restoreEnv();
  }
});

Deno.test("isServiceRoleRequest - returns true for valid service role request", () => {
  setServiceRoleKey("secret-key");
  try {
    const req = new Request("https://example.com/api", {
      headers: {
        "Authorization": "Bearer secret-key",
      },
    });
    assertEquals(isServiceRoleRequest(req), true);
  } finally {
    restoreEnv();
  }
});

Deno.test("isServiceRoleRequest - returns false for invalid service role key", () => {
  setServiceRoleKey("secret-key");
  try {
    const req = new Request("https://example.com/api", {
      headers: {
        "Authorization": "Bearer wrong-key",
      },
    });
    assertEquals(isServiceRoleRequest(req), false);
  } finally {
    restoreEnv();
  }
});

Deno.test("isServiceRoleRequest - returns false when service role key not configured", () => {
  setServiceRoleKey(null);
  try {
    const req = new Request("https://example.com/api", {
      headers: {
        "Authorization": "Bearer any-key",
      },
    });
    assertEquals(isServiceRoleRequest(req), false);
  } finally {
    restoreEnv();
  }
});

Deno.test("isServiceRoleRequest - handles authorization header without Bearer prefix", () => {
  setServiceRoleKey("secret-key");
  try {
    const req = new Request("https://example.com/api", {
      headers: {
        "Authorization": "secret-key", // No Bearer prefix
      },
    });
    // Should still work because the code does replace('Bearer ', '')
    // which leaves 'secret-key' if no prefix
    assertEquals(isServiceRoleRequest(req), true);
  } finally {
    restoreEnv();
  }
});

Deno.test("isServiceRoleRequest - handles lowercase authorization header", () => {
  setServiceRoleKey("secret-key");
  try {
    // Headers are case-insensitive in HTTP
    const req = new Request("https://example.com/api", {
      headers: {
        "authorization": "Bearer secret-key",
      },
    });
    assertEquals(isServiceRoleRequest(req), true);
  } finally {
    restoreEnv();
  }
});

// =============================================================================
// Security Property Tests
// =============================================================================

Deno.test("security - comparison timing should be consistent", async () => {
  // This is a basic sanity check - real timing attack tests need statistical analysis
  const key = "a".repeat(1000);
  const match = key;
  const mismatchFirst = "b" + "a".repeat(999);
  const mismatchLast = "a".repeat(999) + "b";

  // Run each comparison multiple times
  const iterations = 100;

  const timeMatch = performance.now();
  for (let i = 0; i < iterations; i++) {
    constantTimeCompare(key, match);
  }
  const matchDuration = performance.now() - timeMatch;

  const timeMismatchFirst = performance.now();
  for (let i = 0; i < iterations; i++) {
    constantTimeCompare(key, mismatchFirst);
  }
  const mismatchFirstDuration = performance.now() - timeMismatchFirst;

  const timeMismatchLast = performance.now();
  for (let i = 0; i < iterations; i++) {
    constantTimeCompare(key, mismatchLast);
  }
  const mismatchLastDuration = performance.now() - timeMismatchLast;

  // All three should take roughly the same time
  // We allow 100% variance since this is a basic sanity check
  const maxDuration = Math.max(matchDuration, mismatchFirstDuration, mismatchLastDuration);
  const minDuration = Math.min(matchDuration, mismatchFirstDuration, mismatchLastDuration);

  // Ensure no timing difference greater than 2x (very lenient for basic test)
  assertEquals(maxDuration / minDuration < 2, true);
});
