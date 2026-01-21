/**
 * Tests for hooks/useDebounce.ts
 *
 * Tests:
 * - useDebounce() - Debounces value updates
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useDebounce } from './useDebounce';

describe('useDebounce()', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns initial value immediately', () => {
    const { result } = renderHook(() => useDebounce('initial', 500));

    expect(result.current).toBe('initial');
  });

  it('debounces value updates', () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: 'initial', delay: 500 } }
    );

    // Update the value
    rerender({ value: 'updated', delay: 500 });

    // Value should not change immediately
    expect(result.current).toBe('initial');

    // Advance time past the delay
    act(() => {
      vi.advanceTimersByTime(500);
    });

    // Now the value should be updated
    expect(result.current).toBe('updated');
  });

  it('resets timer on value change', () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: 'initial', delay: 500 } }
    );

    // Update value
    rerender({ value: 'first', delay: 500 });

    // Advance partial time
    act(() => {
      vi.advanceTimersByTime(300);
    });

    // Update value again (should reset timer)
    rerender({ value: 'second', delay: 500 });

    // Advance partial time again
    act(() => {
      vi.advanceTimersByTime(300);
    });

    // Value should still be initial (timer reset)
    expect(result.current).toBe('initial');

    // Advance remaining time
    act(() => {
      vi.advanceTimersByTime(200);
    });

    // Now value should be 'second'
    expect(result.current).toBe('second');
  });

  it('handles different delay values', () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: 'initial', delay: 100 } }
    );

    rerender({ value: 'updated', delay: 100 });

    act(() => {
      vi.advanceTimersByTime(100);
    });

    expect(result.current).toBe('updated');
  });

  it('works with number values', () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: 0, delay: 500 } }
    );

    rerender({ value: 42, delay: 500 });

    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(result.current).toBe(42);
  });

  it('works with object values', () => {
    const initialObj = { foo: 'bar' };
    const updatedObj = { foo: 'baz' };

    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: initialObj, delay: 500 } }
    );

    rerender({ value: updatedObj, delay: 500 });

    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(result.current).toEqual(updatedObj);
  });

  it('cleans up timer on unmount', () => {
    const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout');

    const { unmount, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: 'initial', delay: 500 } }
    );

    rerender({ value: 'updated', delay: 500 });
    unmount();

    expect(clearTimeoutSpy).toHaveBeenCalled();
    clearTimeoutSpy.mockRestore();
  });

  it('handles zero delay', () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: 'initial', delay: 0 } }
    );

    rerender({ value: 'updated', delay: 0 });

    act(() => {
      vi.advanceTimersByTime(0);
    });

    expect(result.current).toBe('updated');
  });
});
