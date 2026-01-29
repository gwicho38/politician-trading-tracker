/**
 * Safe localStorage utilities with error handling.
 *
 * localStorage can fail in various scenarios:
 * - Private/incognito browsing mode in some browsers
 * - Storage quota exceeded
 * - Browser security settings
 * - SSR environments
 *
 * These utilities provide graceful fallbacks for all cases.
 */

/**
 * Check if localStorage is available and working.
 */
export function isLocalStorageAvailable(): boolean {
  try {
    const testKey = '__storage_test__';
    window.localStorage.setItem(testKey, testKey);
    window.localStorage.removeItem(testKey);
    return true;
  } catch {
    return false;
  }
}

/**
 * Safely get an item from localStorage.
 *
 * @param key - The key to retrieve
 * @returns The value, or null if not found or error
 */
export function safeGetItem(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch (error) {
    console.warn(`[safeStorage] Failed to get item "${key}":`, error);
    return null;
  }
}

/**
 * Safely set an item in localStorage.
 *
 * @param key - The key to set
 * @param value - The value to store
 * @returns true if successful, false otherwise
 */
export function safeSetItem(key: string, value: string): boolean {
  try {
    window.localStorage.setItem(key, value);
    return true;
  } catch (error) {
    console.warn(`[safeStorage] Failed to set item "${key}":`, error);
    return false;
  }
}

/**
 * Safely remove an item from localStorage.
 *
 * @param key - The key to remove
 * @returns true if successful, false otherwise
 */
export function safeRemoveItem(key: string): boolean {
  try {
    window.localStorage.removeItem(key);
    return true;
  } catch (error) {
    console.warn(`[safeStorage] Failed to remove item "${key}":`, error);
    return false;
  }
}

/**
 * Safely get all localStorage keys.
 *
 * @returns Array of keys, or empty array on error
 */
export function safeGetKeys(): string[] {
  try {
    const keys: string[] = [];
    for (let i = 0; i < window.localStorage.length; i++) {
      const key = window.localStorage.key(i);
      if (key !== null) {
        keys.push(key);
      }
    }
    return keys;
  } catch (error) {
    console.warn('[safeStorage] Failed to get storage keys:', error);
    return [];
  }
}

/**
 * Safely clear localStorage keys matching a pattern.
 *
 * @param prefix - Prefix to filter keys (e.g., 'sb-' for Supabase)
 * @returns Number of keys removed, or 0 on error
 */
export function safeClearByPrefix(prefix: string): number {
  try {
    const keysToRemove: string[] = [];
    for (let i = 0; i < window.localStorage.length; i++) {
      const key = window.localStorage.key(i);
      if (key !== null && key.startsWith(prefix)) {
        keysToRemove.push(key);
      }
    }
    keysToRemove.forEach((key) => window.localStorage.removeItem(key));
    return keysToRemove.length;
  } catch (error) {
    console.warn(`[safeStorage] Failed to clear keys with prefix "${prefix}":`, error);
    return 0;
  }
}

/**
 * Safely get and parse JSON from localStorage.
 *
 * @param key - The key to retrieve
 * @returns Parsed value, or null if not found, invalid JSON, or error
 */
export function safeGetJSON<T>(key: string): T | null {
  try {
    const value = window.localStorage.getItem(key);
    if (value === null) return null;
    return JSON.parse(value) as T;
  } catch (error) {
    console.warn(`[safeStorage] Failed to parse JSON for "${key}":`, error);
    return null;
  }
}

/**
 * Safely stringify and set JSON in localStorage.
 *
 * @param key - The key to set
 * @param value - The value to store (will be JSON stringified)
 * @returns true if successful, false otherwise
 */
export function safeSetJSON<T>(key: string, value: T): boolean {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch (error) {
    console.warn(`[safeStorage] Failed to set JSON for "${key}":`, error);
    return false;
  }
}
