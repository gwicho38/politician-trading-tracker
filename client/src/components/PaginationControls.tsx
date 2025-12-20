import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { PAGINATION } from '@/lib/constants';
import { UsePaginationReturn } from '@/hooks/usePagination';
import { cn } from '@/lib/utils';

interface PaginationControlsProps {
  pagination: UsePaginationReturn;
  showPageSizeSelector?: boolean;
  showItemCount?: boolean;
  itemLabel?: string;
  className?: string;
}

export function PaginationControls({
  pagination,
  showPageSizeSelector = true,
  showItemCount = true,
  itemLabel = 'items',
  className,
}: PaginationControlsProps) {
  const {
    currentPage,
    pageSize,
    totalPages,
    showingFrom,
    showingTo,
    totalItems,
    setPage,
    setPageSize,
    canGoNext,
    canGoPrevious,
  } = pagination;

  // Generate page numbers to display (max 5 visible pages)
  const getVisiblePages = (): (number | 'ellipsis-start' | 'ellipsis-end')[] => {
    if (totalPages <= 5) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }

    const pages: (number | 'ellipsis-start' | 'ellipsis-end')[] = [];

    if (currentPage <= 3) {
      pages.push(1, 2, 3, 4, 'ellipsis-end', totalPages);
    } else if (currentPage >= totalPages - 2) {
      pages.push(1, 'ellipsis-start', totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
    } else {
      pages.push(1, 'ellipsis-start', currentPage - 1, currentPage, currentPage + 1, 'ellipsis-end', totalPages);
    }

    return pages;
  };

  // Don't render if no items
  if (totalItems === 0) {
    return null;
  }

  return (
    <div className={cn('flex flex-col sm:flex-row items-center justify-between gap-4 pt-4', className)}>
      {/* Left: Item count and page size selector */}
      <div className="flex items-center gap-4 text-sm text-muted-foreground">
        {showItemCount && (
          <span>
            Showing {showingFrom} to {showingTo} of {totalItems.toLocaleString()} {itemLabel}
          </span>
        )}

        {showPageSizeSelector && (
          <div className="flex items-center gap-2">
            <span>Show:</span>
            <Select value={String(pageSize)} onValueChange={(value) => setPageSize(Number(value))}>
              <SelectTrigger className="w-20 h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PAGINATION.PAGE_SIZE_OPTIONS.map((size) => (
                  <SelectItem key={size} value={String(size)}>
                    {size}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      </div>

      {/* Right: Page navigation */}
      {totalPages > 1 && (
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                onClick={() => canGoPrevious && setPage(currentPage - 1)}
                className={cn(!canGoPrevious && 'pointer-events-none opacity-50')}
              />
            </PaginationItem>

            {getVisiblePages().map((page, index) =>
              typeof page === 'string' ? (
                <PaginationItem key={page}>
                  <PaginationEllipsis />
                </PaginationItem>
              ) : (
                <PaginationItem key={page}>
                  <PaginationLink onClick={() => setPage(page)} isActive={currentPage === page}>
                    {page}
                  </PaginationLink>
                </PaginationItem>
              )
            )}

            <PaginationItem>
              <PaginationNext
                onClick={() => canGoNext && setPage(currentPage + 1)}
                className={cn(!canGoNext && 'pointer-events-none opacity-50')}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}
    </div>
  );
}
