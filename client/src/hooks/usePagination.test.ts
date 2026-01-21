/**
 * Tests for hooks/usePagination.ts
 *
 * Tests:
 * - usePagination() - Pagination state management
 */

import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { usePagination } from './usePagination';

describe('usePagination()', () => {
  describe('initialization', () => {
    it('returns default values with no options', () => {
      const { result } = renderHook(() => usePagination());

      expect(result.current.currentPage).toBe(1);
      expect(result.current.totalItems).toBe(0);
      expect(result.current.totalPages).toBe(1);
    });

    it('accepts initial page', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 3, totalItems: 100 })
      );

      expect(result.current.currentPage).toBe(3);
    });

    it('accepts initial page size', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPageSize: 25 })
      );

      expect(result.current.pageSize).toBe(25);
    });

    it('accepts initial total items', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100 })
      );

      expect(result.current.totalItems).toBe(100);
    });
  });

  describe('totalPages calculation', () => {
    it('calculates total pages correctly', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100, initialPageSize: 10 })
      );

      expect(result.current.totalPages).toBe(10);
    });

    it('rounds up for partial pages', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 25, initialPageSize: 10 })
      );

      expect(result.current.totalPages).toBe(3);
    });

    it('returns 1 for empty data', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 0 })
      );

      expect(result.current.totalPages).toBe(1);
    });
  });

  describe('computed indices', () => {
    it('calculates startIndex correctly', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 2, initialPageSize: 10, totalItems: 100 })
      );

      expect(result.current.startIndex).toBe(10);
    });

    it('calculates endIndex correctly', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 2, initialPageSize: 10, totalItems: 100 })
      );

      expect(result.current.endIndex).toBe(20);
    });

    it('clamps endIndex to totalItems', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 3, initialPageSize: 10, totalItems: 25 })
      );

      expect(result.current.endIndex).toBe(25);
    });
  });

  describe('display values', () => {
    it('calculates showingFrom correctly', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 2, initialPageSize: 10, totalItems: 100 })
      );

      expect(result.current.showingFrom).toBe(11);
    });

    it('calculates showingTo correctly', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 2, initialPageSize: 10, totalItems: 100 })
      );

      expect(result.current.showingTo).toBe(20);
    });

    it('returns 0 for showingFrom when empty', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 0 })
      );

      expect(result.current.showingFrom).toBe(0);
    });
  });

  describe('setPage()', () => {
    it('updates current page', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100, initialPageSize: 10 })
      );

      act(() => {
        result.current.setPage(5);
      });

      expect(result.current.currentPage).toBe(5);
    });

    it('clamps to minimum of 1', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100, initialPageSize: 10 })
      );

      act(() => {
        result.current.setPage(-1);
      });

      expect(result.current.currentPage).toBe(1);
    });

    it('clamps to maximum of totalPages', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100, initialPageSize: 10 })
      );

      act(() => {
        result.current.setPage(999);
      });

      expect(result.current.currentPage).toBe(10);
    });
  });

  describe('setPageSize()', () => {
    it('updates page size', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100, initialPageSize: 10 })
      );

      act(() => {
        result.current.setPageSize(25);
      });

      expect(result.current.pageSize).toBe(25);
    });

    it('resets to page 1', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 5, totalItems: 100, initialPageSize: 10 })
      );

      act(() => {
        result.current.setPageSize(25);
      });

      expect(result.current.currentPage).toBe(1);
    });
  });

  describe('setTotalItems()', () => {
    it('updates total items', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100 })
      );

      act(() => {
        result.current.setTotalItems(200);
      });

      expect(result.current.totalItems).toBe(200);
    });

    it('adjusts current page if exceeds new total', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 10, totalItems: 100, initialPageSize: 10 })
      );

      act(() => {
        result.current.setTotalItems(25);
      });

      // New total pages is 3, so current page should be 3
      expect(result.current.currentPage).toBe(3);
    });
  });

  describe('navigation actions', () => {
    it('goToFirst() goes to page 1', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 5, totalItems: 100 })
      );

      act(() => {
        result.current.goToFirst();
      });

      expect(result.current.currentPage).toBe(1);
    });

    it('goToLast() goes to last page', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100, initialPageSize: 10 })
      );

      act(() => {
        result.current.goToLast();
      });

      expect(result.current.currentPage).toBe(10);
    });

    it('goToNext() increments page', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100, initialPageSize: 10 })
      );

      act(() => {
        result.current.goToNext();
      });

      expect(result.current.currentPage).toBe(2);
    });

    it('goToPrevious() decrements page', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 5, initialPageSize: 10, totalItems: 100 })
      );

      act(() => {
        result.current.goToPrevious();
      });

      expect(result.current.currentPage).toBe(4);
    });
  });

  describe('predicates', () => {
    it('canGoNext is true when not on last page', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100, initialPageSize: 10 })
      );

      expect(result.current.canGoNext).toBe(true);
    });

    it('canGoNext is false on last page', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 10, totalItems: 100, initialPageSize: 10 })
      );

      expect(result.current.canGoNext).toBe(false);
    });

    it('canGoPrevious is false on first page', () => {
      const { result } = renderHook(() =>
        usePagination({ totalItems: 100 })
      );

      expect(result.current.canGoPrevious).toBe(false);
    });

    it('canGoPrevious is true when not on first page', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 2, totalItems: 100 })
      );

      expect(result.current.canGoPrevious).toBe(true);
    });
  });

  describe('paginationParams', () => {
    it('returns limit and offset for server-side pagination', () => {
      const { result } = renderHook(() =>
        usePagination({ initialPage: 3, initialPageSize: 10, totalItems: 100 })
      );

      expect(result.current.paginationParams).toEqual({
        limit: 10,
        offset: 20,
      });
    });
  });
});
