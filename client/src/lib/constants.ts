// Pagination configuration
export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 50,
  PAGE_SIZE_OPTIONS: [10, 25, 50, 100],
} as const;

// Type for page size options
export type PageSizeOption = (typeof PAGINATION.PAGE_SIZE_OPTIONS)[number];
