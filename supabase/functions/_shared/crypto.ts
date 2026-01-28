/**
 * Encryption utilities for sensitive data at rest.
 *
 * Uses AES-256-GCM encryption with Web Crypto API for:
 * - Encrypting API keys before storage in database
 * - Decrypting API keys on retrieval
 *
 * Security features:
 * - AES-256-GCM provides authenticated encryption (confidentiality + integrity)
 * - Random IV for each encryption (prevents pattern analysis)
 * - Key derivation from environment variable using PBKDF2
 * - Base64 encoding for safe storage in text fields
 */

// Salt for key derivation (fixed, but encryption uses random IV per operation)
const KEY_DERIVATION_SALT = 'govmarket-api-encryption-v1';

/**
 * Derive an AES-256 key from the master secret using PBKDF2.
 *
 * @param masterSecret The encryption key from environment variable
 * @returns CryptoKey suitable for AES-GCM operations
 */
async function deriveKey(masterSecret: string): Promise<CryptoKey> {
  const encoder = new TextEncoder();

  // Import the master secret as raw key material
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    encoder.encode(masterSecret),
    'PBKDF2',
    false,
    ['deriveBits', 'deriveKey']
  );

  // Derive a 256-bit AES-GCM key
  return crypto.subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt: encoder.encode(KEY_DERIVATION_SALT),
      iterations: 100000,
      hash: 'SHA-256',
    },
    keyMaterial,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt']
  );
}

/**
 * Get the encryption key from environment.
 * Returns null if not configured (encryption disabled).
 */
function getEncryptionSecret(): string | null {
  return Deno.env.get('API_ENCRYPTION_KEY') || null;
}

/**
 * Check if encryption is enabled (key is configured).
 */
export function isEncryptionEnabled(): boolean {
  return !!getEncryptionSecret();
}

/**
 * Encrypt a plaintext string using AES-256-GCM.
 *
 * @param plaintext The text to encrypt (e.g., API key)
 * @returns Base64-encoded ciphertext (IV:ciphertext format), or original text if encryption disabled
 */
export async function encrypt(plaintext: string): Promise<string> {
  const secret = getEncryptionSecret();

  // If no encryption key configured, return plaintext (backwards compatibility)
  if (!secret) {
    console.warn('[crypto] API_ENCRYPTION_KEY not set - storing credentials unencrypted');
    return plaintext;
  }

  try {
    const encoder = new TextEncoder();
    const key = await deriveKey(secret);

    // Generate random 12-byte IV (recommended for AES-GCM)
    const iv = crypto.getRandomValues(new Uint8Array(12));

    // Encrypt the plaintext
    const ciphertext = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv },
      key,
      encoder.encode(plaintext)
    );

    // Combine IV and ciphertext, then base64 encode
    const combined = new Uint8Array(iv.length + new Uint8Array(ciphertext).length);
    combined.set(iv);
    combined.set(new Uint8Array(ciphertext), iv.length);

    // Prefix with 'enc:' to identify encrypted values
    return 'enc:' + btoa(String.fromCharCode(...combined));
  } catch (error) {
    console.error('[crypto] Encryption failed:', error);
    throw new Error('Failed to encrypt credential');
  }
}

/**
 * Decrypt a ciphertext string encrypted with AES-256-GCM.
 *
 * @param ciphertext Base64-encoded ciphertext (from encrypt())
 * @returns Original plaintext, or input unchanged if not encrypted
 */
export async function decrypt(ciphertext: string): Promise<string> {
  // Check if this is an encrypted value (has 'enc:' prefix)
  if (!ciphertext.startsWith('enc:')) {
    // Not encrypted - return as-is (backwards compatibility with existing unencrypted data)
    return ciphertext;
  }

  const secret = getEncryptionSecret();

  if (!secret) {
    console.error('[crypto] Cannot decrypt: API_ENCRYPTION_KEY not configured');
    throw new Error('Encryption key not configured - cannot decrypt credentials');
  }

  try {
    // Remove 'enc:' prefix and decode base64
    const combined = Uint8Array.from(
      atob(ciphertext.slice(4)),
      (c) => c.charCodeAt(0)
    );

    // Extract IV (first 12 bytes) and ciphertext (rest)
    const iv = combined.slice(0, 12);
    const encryptedData = combined.slice(12);

    const key = await deriveKey(secret);

    // Decrypt
    const decrypted = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv },
      key,
      encryptedData
    );

    return new TextDecoder().decode(decrypted);
  } catch (error) {
    console.error('[crypto] Decryption failed:', error);
    throw new Error('Failed to decrypt credential - key may have changed');
  }
}

/**
 * Encrypt an object's sensitive fields.
 * Only encrypts fields that are truthy (non-null, non-empty).
 *
 * @param obj Object containing fields to encrypt
 * @param fields Array of field names to encrypt
 * @returns New object with specified fields encrypted
 */
export async function encryptFields<T extends Record<string, any>>(
  obj: T,
  fields: (keyof T)[]
): Promise<T> {
  const result = { ...obj };

  for (const field of fields) {
    const value = obj[field];
    if (value && typeof value === 'string') {
      (result as any)[field] = await encrypt(value);
    }
  }

  return result;
}

/**
 * Decrypt an object's encrypted fields.
 *
 * @param obj Object containing fields to decrypt
 * @param fields Array of field names to decrypt
 * @returns New object with specified fields decrypted
 */
export async function decryptFields<T extends Record<string, any>>(
  obj: T,
  fields: (keyof T)[]
): Promise<T> {
  const result = { ...obj };

  for (const field of fields) {
    const value = obj[field];
    if (value && typeof value === 'string') {
      (result as any)[field] = await decrypt(value);
    }
  }

  return result;
}

/**
 * Generate a secure random encryption key (for initial setup).
 * This should be called once to generate the API_ENCRYPTION_KEY value.
 *
 * @returns Base64-encoded 32-byte random key
 */
export function generateEncryptionKey(): string {
  const key = crypto.getRandomValues(new Uint8Array(32));
  return btoa(String.fromCharCode(...key));
}
