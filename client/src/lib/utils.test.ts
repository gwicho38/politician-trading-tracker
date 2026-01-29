/**
 * Tests for lib/utils.ts
 *
 * Tests:
 * - cn() - Class name utility function
 */

import { describe, it, expect } from 'vitest';
import { cn } from './utils';

describe('cn()', () => {
  it('merges class names', () => {
    const result = cn('foo', 'bar');
    expect(result).toBe('foo bar');
  });

  it('handles conditional classes', () => {
    const isEnabled = false;
    const result = cn('foo', isEnabled && 'bar', 'baz');
    expect(result).toBe('foo baz');
  });

  it('handles undefined values', () => {
    const result = cn('foo', undefined, 'bar');
    expect(result).toBe('foo bar');
  });

  it('handles null values', () => {
    const result = cn('foo', null, 'bar');
    expect(result).toBe('foo bar');
  });

  it('merges tailwind classes correctly', () => {
    // twMerge should handle conflicting tailwind classes
    const result = cn('px-2', 'px-4');
    expect(result).toBe('px-4');
  });

  it('handles array inputs', () => {
    const result = cn(['foo', 'bar']);
    expect(result).toBe('foo bar');
  });

  it('handles object inputs for conditional classes', () => {
    const result = cn({ foo: true, bar: false, baz: true });
    expect(result).toBe('foo baz');
  });

  it('returns empty string for no inputs', () => {
    const result = cn();
    expect(result).toBe('');
  });

  it('handles mixed inputs', () => {
    const result = cn('foo', { bar: true }, ['baz', 'qux']);
    expect(result).toBe('foo bar baz qux');
  });

  it('handles tailwind responsive classes', () => {
    const result = cn('text-sm', 'md:text-base', 'lg:text-lg');
    expect(result).toBe('text-sm md:text-base lg:text-lg');
  });

  it('handles tailwind hover classes', () => {
    const result = cn('bg-blue-500', 'hover:bg-blue-600');
    expect(result).toBe('bg-blue-500 hover:bg-blue-600');
  });
});
