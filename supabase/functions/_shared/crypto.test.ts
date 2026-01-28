/**
 * Tests for crypto.ts encryption utilities
 *
 * Tests cover:
 * - Key derivation
 * - Encryption/decryption roundtrip
 * - Backwards compatibility with unencrypted data
 * - Error handling for missing keys
 * - Field encryption helpers
 * - Key generation
 */

import {
  assertEquals,
  assertNotEquals,
  assertRejects,
} from "https://deno.land/std@0.208.0/assert/mod.ts";

// Import functions to test
import {
  encrypt,
  decrypt,
  isEncryptionEnabled,
  encryptFields,
  decryptFields,
  generateEncryptionKey,
} from "./crypto.ts";

// =============================================================================
// Test Environment Setup
// =============================================================================

// Store original env value
const originalKey = Deno.env.get("API_ENCRYPTION_KEY");

function setEncryptionKey(key: string | null) {
  if (key === null) {
    Deno.env.delete("API_ENCRYPTION_KEY");
  } else {
    Deno.env.set("API_ENCRYPTION_KEY", key);
  }
}

function restoreEnv() {
  if (originalKey) {
    Deno.env.set("API_ENCRYPTION_KEY", originalKey);
  } else {
    Deno.env.delete("API_ENCRYPTION_KEY");
  }
}

// =============================================================================
// isEncryptionEnabled Tests
// =============================================================================

Deno.test("isEncryptionEnabled - returns false when key not set", () => {
  setEncryptionKey(null);
  try {
    assertEquals(isEncryptionEnabled(), false);
  } finally {
    restoreEnv();
  }
});

Deno.test("isEncryptionEnabled - returns true when key is set", () => {
  setEncryptionKey("test-encryption-key-32-bytes-long!");
  try {
    assertEquals(isEncryptionEnabled(), true);
  } finally {
    restoreEnv();
  }
});

// =============================================================================
// encrypt Tests
// =============================================================================

Deno.test("encrypt - returns plaintext when encryption disabled", async () => {
  setEncryptionKey(null);
  try {
    const plaintext = "my-secret-api-key";
    const result = await encrypt(plaintext);
    assertEquals(result, plaintext);
  } finally {
    restoreEnv();
  }
});

Deno.test("encrypt - returns encrypted value with enc: prefix", async () => {
  setEncryptionKey("test-encryption-key-32-bytes-long!");
  try {
    const plaintext = "my-secret-api-key";
    const result = await encrypt(plaintext);
    assertEquals(result.startsWith("enc:"), true);
    assertNotEquals(result, plaintext);
  } finally {
    restoreEnv();
  }
});

Deno.test("encrypt - produces different ciphertext each time (random IV)", async () => {
  setEncryptionKey("test-encryption-key-32-bytes-long!");
  try {
    const plaintext = "my-secret-api-key";
    const result1 = await encrypt(plaintext);
    const result2 = await encrypt(plaintext);
    // Both should be encrypted
    assertEquals(result1.startsWith("enc:"), true);
    assertEquals(result2.startsWith("enc:"), true);
    // But different due to random IV
    assertNotEquals(result1, result2);
  } finally {
    restoreEnv();
  }
});

// =============================================================================
// decrypt Tests
// =============================================================================

Deno.test("decrypt - returns unencrypted value unchanged", async () => {
  setEncryptionKey("test-encryption-key-32-bytes-long!");
  try {
    const plaintext = "not-encrypted-value";
    const result = await decrypt(plaintext);
    assertEquals(result, plaintext);
  } finally {
    restoreEnv();
  }
});

Deno.test("decrypt - throws when key not configured for encrypted value", async () => {
  // First encrypt with key
  setEncryptionKey("test-encryption-key-32-bytes-long!");
  let encrypted: string;
  try {
    encrypted = await encrypt("my-secret");
  } finally {
    setEncryptionKey(null);
  }

  // Try to decrypt without key
  try {
    await assertRejects(
      async () => await decrypt(encrypted),
      Error,
      "Encryption key not configured"
    );
  } finally {
    restoreEnv();
  }
});

Deno.test("decrypt - throws on invalid ciphertext", async () => {
  setEncryptionKey("test-encryption-key-32-bytes-long!");
  try {
    // Invalid base64 after enc:
    await assertRejects(
      async () => await decrypt("enc:not-valid-base64!!!"),
      Error
    );
  } finally {
    restoreEnv();
  }
});

Deno.test("decrypt - throws when wrong key used", async () => {
  // Encrypt with one key
  setEncryptionKey("first-encryption-key-32-bytes!!!");
  let encrypted: string;
  try {
    encrypted = await encrypt("my-secret");
  } finally {
    // Try to decrypt with different key
    setEncryptionKey("different-key-32-bytes-long!!!!");
  }

  try {
    await assertRejects(
      async () => await decrypt(encrypted),
      Error,
      "Failed to decrypt"
    );
  } finally {
    restoreEnv();
  }
});

// =============================================================================
// Roundtrip Tests
// =============================================================================

Deno.test("encrypt/decrypt - roundtrip preserves plaintext", async () => {
  setEncryptionKey("test-encryption-key-32-bytes-long!");
  try {
    const plaintext = "my-super-secret-api-key-12345";
    const encrypted = await encrypt(plaintext);
    const decrypted = await decrypt(encrypted);
    assertEquals(decrypted, plaintext);
  } finally {
    restoreEnv();
  }
});

Deno.test("encrypt/decrypt - roundtrip works with special characters", async () => {
  setEncryptionKey("test-encryption-key-32-bytes-long!");
  try {
    const plaintext = "key-with-special-chars!@#$%^&*()_+-=[]{}|;':\",./<>?";
    const encrypted = await encrypt(plaintext);
    const decrypted = await decrypt(encrypted);
    assertEquals(decrypted, plaintext);
  } finally {
    restoreEnv();
  }
});

Deno.test("encrypt/decrypt - roundtrip works with unicode", async () => {
  setEncryptionKey("test-encryption-key-32-bytes-long!");
  try {
    const plaintext = "API密钥🔐";
    const encrypted = await encrypt(plaintext);
    const decrypted = await decrypt(encrypted);
    assertEquals(decrypted, plaintext);
  } finally {
    restoreEnv();
  }
});

Deno.test("encrypt/decrypt - roundtrip works with empty string", async () => {
  setEncryptionKey("test-encryption-key-32-bytes-long!");
  try {
    const plaintext = "";
    const encrypted = await encrypt(plaintext);
    const decrypted = await decrypt(encrypted);
    assertEquals(decrypted, plaintext);
  } finally {
    restoreEnv();
  }
});

Deno.test("encrypt/decrypt - roundtrip works with long string", async () => {
  setEncryptionKey("test-encryption-key-32-bytes-long!");
  try {
    const plaintext = "x".repeat(10000); // 10KB string
    const encrypted = await encrypt(plaintext);
    const decrypted = await decrypt(encrypted);
    assertEquals(decrypted, plaintext);
  } finally {
    restoreEnv();
  }
});

// =============================================================================
// encryptFields Tests
// =============================================================================

Deno.test("encryptFields - encrypts specified fields", async () => {
  setEncryptionKey("test-encryption-key-32-bytes-long!");
  try {
    const obj = {
      api_key: "secret-key",
      api_secret: "secret-secret",
      name: "not-sensitive",
    };

    const result = await encryptFields(obj, ["api_key", "api_secret"]);

    assertEquals(result.api_key.startsWith("enc:"), true);
    assertEquals(result.api_secret.startsWith("enc:"), true);
    assertEquals(result.name, "not-sensitive"); // Unchanged
  } finally {
    restoreEnv();
  }
});

Deno.test("encryptFields - skips null/undefined fields", async () => {
  setEncryptionKey("test-encryption-key-32-bytes-long!");
  try {
    const obj = {
      api_key: "secret-key",
      api_secret: null as string | null,
      missing: undefined as string | undefined,
    };

    const result = await encryptFields(obj, ["api_key", "api_secret", "missing"]);

    assertEquals(result.api_key.startsWith("enc:"), true);
    assertEquals(result.api_secret, null);
    assertEquals(result.missing, undefined);
  } finally {
    restoreEnv();
  }
});

Deno.test("encryptFields - skips non-string fields", async () => {
  setEncryptionKey("test-encryption-key-32-bytes-long!");
  try {
    const obj = {
      api_key: "secret-key",
      count: 42,
      active: true,
    };

    const result = await encryptFields(obj, ["api_key", "count" as any, "active" as any]);

    assertEquals(result.api_key.startsWith("enc:"), true);
    assertEquals(result.count, 42);
    assertEquals(result.active, true);
  } finally {
    restoreEnv();
  }
});

// =============================================================================
// decryptFields Tests
// =============================================================================

Deno.test("decryptFields - decrypts specified fields", async () => {
  setEncryptionKey("test-encryption-key-32-bytes-long!");
  try {
    // First encrypt
    const encryptedKey = await encrypt("secret-key");
    const encryptedSecret = await encrypt("secret-secret");

    const obj = {
      api_key: encryptedKey,
      api_secret: encryptedSecret,
      name: "not-sensitive",
    };

    const result = await decryptFields(obj, ["api_key", "api_secret"]);

    assertEquals(result.api_key, "secret-key");
    assertEquals(result.api_secret, "secret-secret");
    assertEquals(result.name, "not-sensitive");
  } finally {
    restoreEnv();
  }
});

Deno.test("decryptFields - handles unencrypted fields gracefully", async () => {
  setEncryptionKey("test-encryption-key-32-bytes-long!");
  try {
    const obj = {
      api_key: "not-encrypted-key",
      api_secret: "not-encrypted-secret",
    };

    const result = await decryptFields(obj, ["api_key", "api_secret"]);

    // Should return unchanged since they don't have enc: prefix
    assertEquals(result.api_key, "not-encrypted-key");
    assertEquals(result.api_secret, "not-encrypted-secret");
  } finally {
    restoreEnv();
  }
});

Deno.test("decryptFields - skips null/undefined fields", async () => {
  setEncryptionKey("test-encryption-key-32-bytes-long!");
  try {
    const obj = {
      api_key: await encrypt("secret-key"),
      api_secret: null as string | null,
    };

    const result = await decryptFields(obj, ["api_key", "api_secret"]);

    assertEquals(result.api_key, "secret-key");
    assertEquals(result.api_secret, null);
  } finally {
    restoreEnv();
  }
});

// =============================================================================
// generateEncryptionKey Tests
// =============================================================================

Deno.test("generateEncryptionKey - returns base64 string", () => {
  const key = generateEncryptionKey();
  // Should be valid base64
  assertEquals(typeof key, "string");
  assertEquals(key.length > 0, true);
  // Base64 of 32 bytes = 44 characters
  assertEquals(key.length, 44);
});

Deno.test("generateEncryptionKey - produces unique keys", () => {
  const key1 = generateEncryptionKey();
  const key2 = generateEncryptionKey();
  assertNotEquals(key1, key2);
});

Deno.test("generateEncryptionKey - generated key can be used for encryption", async () => {
  const key = generateEncryptionKey();
  setEncryptionKey(key);
  try {
    const plaintext = "test-secret";
    const encrypted = await encrypt(plaintext);
    const decrypted = await decrypt(encrypted);
    assertEquals(decrypted, plaintext);
  } finally {
    restoreEnv();
  }
});

// =============================================================================
// Full Integration Test
// =============================================================================

Deno.test("integration - full credential lifecycle", async () => {
  // Generate a fresh key
  const encryptionKey = generateEncryptionKey();
  setEncryptionKey(encryptionKey);

  try {
    // Simulate storing API credentials
    const credentials = {
      user_id: "user-123",
      alpaca_api_key: "PKTEST123456789",
      alpaca_api_secret: "secretABC123xyz789",
      created_at: new Date().toISOString(),
    };

    // Encrypt sensitive fields before storage
    const encrypted = await encryptFields(credentials, [
      "alpaca_api_key",
      "alpaca_api_secret",
    ]);

    // Verify encryption
    assertEquals(encrypted.alpaca_api_key.startsWith("enc:"), true);
    assertEquals(encrypted.alpaca_api_secret.startsWith("enc:"), true);
    assertEquals(encrypted.user_id, "user-123"); // Not encrypted

    // Simulate retrieval and decryption
    const decrypted = await decryptFields(encrypted, [
      "alpaca_api_key",
      "alpaca_api_secret",
    ]);

    // Verify we get original values back
    assertEquals(decrypted.alpaca_api_key, "PKTEST123456789");
    assertEquals(decrypted.alpaca_api_secret, "secretABC123xyz789");
    assertEquals(decrypted.user_id, "user-123");
  } finally {
    restoreEnv();
  }
});
