import { useState, useMemo, useCallback } from 'react';
import { PAGINATION } from '@/lib/constants';

export interface UsePaginationOptions {
  initialPage?: number;
  initialPageSize?: number;
  totalItems?: number;
}

export interface UsePaginationReturn {
  // State
  currentPage: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;

  // Computed values for array slicing (0-based)
  startIndex: number;
  endIndex: number;
  offset: number; // For server-side pagination

  // Display values (1-based for UI)
  showingFrom: number;
  showingTo: number;

  // Actions
  setPage: (page: number) => void;
  setPageSize: (size: number) => void;
  setTotalItems: (total: number) => void;
  goToFirst: () => void;
  goToLast: () => void;
  goToNext: () => void;
  goToPrevious: () => void;

  // Predicates
  canGoNext: boolean;
  canGoPrevious: boolean;

  // For server-side pagination
  paginationParams: { limit: number; offset: number };
}

export function usePagination(options: UsePaginationOptions = {}): UsePaginationReturn {
  const {
    initialPage = 1,
    initialPageSize = PAGINATION.DEFAULT_PAGE_SIZE,
    totalItems: initialTotalItems = 0,
  } = options;

  const [currentPage, setCurrentPage] = useState(initialPage);
  const [pageSize, setPageSizeState] = useState(initialPageSize);
  const [totalItems, setTotalItemsState] = useState(initialTotalItems);

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(totalItems / pageSize)),
    [totalItems, pageSize]
  );

  // Computed indices for client-side slicing
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, totalItems);

  // Display values (1-based)
  const showingFrom = totalItems === 0 ? 0 : startIndex + 1;
  const showingTo = Math.min(currentPage * pageSize, totalItems);

  // For server-side pagination
  const offset = startIndex;

  const setPage = useCallback(
    (page: number) => {
      const validPage = Math.max(1, Math.min(page, totalPages));
      setCurrentPage(validPage);
    },
    [totalPages]
  );

  const setPageSize = useCallback((size: number) => {
    setPageSizeState(size);
    // Reset to page 1 when page size changes
    setCurrentPage(1);
  }, []);

  const setTotalItems = useCallback((total: number) => {
    setTotalItemsState(total);
    // Adjust current page if it exceeds new total pages
    const newTotalPages = Math.max(1, Math.ceil(total / pageSize));
    if (currentPage > newTotalPages) {
      setCurrentPage(newTotalPages);
    }
  }, [currentPage, pageSize]);

  const goToFirst = useCallback(() => setPage(1), [setPage]);
  const goToLast = useCallback(() => setPage(totalPages), [setPage, totalPages]);
  const goToNext = useCallback(() => setPage(currentPage + 1), [setPage, currentPage]);
  const goToPrevious = useCallback(() => setPage(currentPage - 1), [setPage, currentPage]);

  const canGoNext = currentPage < totalPages;
  const canGoPrevious = currentPage > 1;

  const paginationParams = useMemo(
    () => ({
      limit: pageSize,
      offset,
    }),
    [pageSize, offset]
  );

  return {
    currentPage,
    pageSize,
    totalItems,
    totalPages,
    startIndex,
    endIndex,
    offset,
    showingFrom,
    showingTo,
    setPage,
    setPageSize,
    setTotalItems,
    goToFirst,
    goToLast,
    goToNext,
    goToPrevious,
    canGoNext,
    canGoPrevious,
    paginationParams,
  };
}
