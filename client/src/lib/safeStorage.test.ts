import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import {
  isLocalStorageAvailable,
  safeGetItem,
  safeSetItem,
  safeRemoveItem,
  safeClearByPrefix,
  safeGetJSON,
  safeSetJSON,
} from './safeStorage';

describe('safeStorage utilities', () => {
  // Helper to clean up only test keys
  const clearTestKeys = () => {
    const keysToRemove: string[] = [];
    for (let i = 0; i < window.localStorage.length; i++) {
      const key = window.localStorage.key(i);
      if (key && (key.startsWith('test-') || key.startsWith('sb-') || key.startsWith('json-') || key.startsWith('array-') || key.startsWith('key') || key === 'other-key' || key === 'invalid-json' || key === 'non-existent' || key === 'circular-key')) {
        keysToRemove.push(key);
      }
    }
    keysToRemove.forEach(key => window.localStorage.removeItem(key));
  };

  beforeEach(() => {
    clearTestKeys();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearTestKeys();
  });

  describe('isLocalStorageAvailable', () => {
    it('returns true when localStorage is available', () => {
      expect(isLocalStorageAvailable()).toBe(true);
    });
  });

  describe('safeGetItem', () => {
    it('returns the value when key exists', () => {
      window.localStorage.setItem('test-key', 'test-value');
      expect(safeGetItem('test-key')).toBe('test-value');
    });

    it('returns null when key does not exist', () => {
      expect(safeGetItem('non-existent')).toBeNull();
    });
  });

  describe('safeSetItem', () => {
    it('sets the value and returns true', () => {
      expect(safeSetItem('test-key', 'test-value')).toBe(true);
      expect(window.localStorage.getItem('test-key')).toBe('test-value');
    });
  });

  describe('safeRemoveItem', () => {
    it('removes the item and returns true', () => {
      window.localStorage.setItem('test-key', 'test-value');
      expect(safeRemoveItem('test-key')).toBe(true);
      expect(window.localStorage.getItem('test-key')).toBeNull();
    });

    it('returns true even when key does not exist', () => {
      expect(safeRemoveItem('non-existent')).toBe(true);
    });
  });

  describe('safeClearByPrefix', () => {
    it('clears items with matching prefix', () => {
      window.localStorage.setItem('sb-auth-token', 'token123');
      window.localStorage.setItem('sb-refresh-token', 'refresh456');
      window.localStorage.setItem('other-key', 'value');

      const cleared = safeClearByPrefix('sb-');

      expect(cleared).toBe(2);
      expect(window.localStorage.getItem('sb-auth-token')).toBeNull();
      expect(window.localStorage.getItem('sb-refresh-token')).toBeNull();
      expect(window.localStorage.getItem('other-key')).toBe('value');
    });

    it('returns 0 when no keys match prefix', () => {
      window.localStorage.setItem('other-key', 'value');
      expect(safeClearByPrefix('sb-')).toBe(0);
    });
  });

  describe('safeGetJSON', () => {
    it('returns parsed object', () => {
      const data = { name: 'test', count: 42 };
      window.localStorage.setItem('json-key', JSON.stringify(data));

      expect(safeGetJSON('json-key')).toEqual(data);
    });

    it('returns parsed array', () => {
      const data = [1, 2, 3];
      window.localStorage.setItem('array-key', JSON.stringify(data));

      expect(safeGetJSON('array-key')).toEqual(data);
    });

    it('returns null when key does not exist', () => {
      expect(safeGetJSON('non-existent')).toBeNull();
    });

    it('returns null for invalid JSON', () => {
      window.localStorage.setItem('invalid-json', 'not valid json');

      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      expect(safeGetJSON('invalid-json')).toBeNull();
      expect(consoleSpy).toHaveBeenCalled();
    });
  });

  describe('safeSetJSON', () => {
    it('sets stringified object and returns true', () => {
      const data = { name: 'test', count: 42 };
      expect(safeSetJSON('json-key', data)).toBe(true);
      expect(window.localStorage.getItem('json-key')).toBe(JSON.stringify(data));
    });

    it('sets stringified array and returns true', () => {
      const data = [1, 2, 3];
      expect(safeSetJSON('array-key', data)).toBe(true);
      expect(window.localStorage.getItem('array-key')).toBe(JSON.stringify(data));
    });

    it('handles circular references gracefully', () => {
      const obj: Record<string, unknown> = {};
      obj.circular = obj;

      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      expect(safeSetJSON('circular-key', obj)).toBe(false);
      expect(consoleSpy).toHaveBeenCalled();
    });
  });
});
