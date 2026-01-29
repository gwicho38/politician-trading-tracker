/**
 * Tests for components/PoliticiansView.tsx
 *
 * Tests:
 * - Component rendering
 * - Loading state display
 * - Error state handling
 * - Empty state display
 * - Politician list rendering
 * - Sorting functionality
 * - Pagination
 * - Initial politician selection
 * - Modal interaction
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock PaginationControls component
vi.mock('@/components/PaginationControls', () => ({
  PaginationControls: ({ pagination, itemLabel }: { pagination: { page: number; totalPages: number }; itemLabel: string }) => (
    <div data-testid="pagination-controls">
      <span data-testid="pagination-page">{pagination.page}</span>
      <span data-testid="pagination-item-label">{itemLabel}</span>
    </div>
  ),
}));

// Mock PoliticianProfileModal component
vi.mock('@/components/detail-modals', () => ({
  PoliticianProfileModal: ({ politician, open, onOpenChange }: { politician: unknown; open: boolean; onOpenChange: (open: boolean) => void }) => (
    open ? (
      <div data-testid="politician-modal">
        <span data-testid="modal-politician-name">{(politician as { name?: string })?.name || 'Unknown'}</span>
        <button data-testid="modal-close" onClick={() => onOpenChange(false)}>Close</button>
      </div>
    ) : null
  ),
}));

// Mock hooks
const mockUsePoliticians = vi.fn();
const mockUsePagination = vi.fn();

vi.mock('@/hooks/useSupabaseData', () => ({
  usePoliticians: () => mockUsePoliticians(),
}));

vi.mock('@/hooks/usePagination', () => ({
  usePagination: () => mockUsePagination(),
}));

// Mock mockData
vi.mock('@/lib/mockData', () => ({
  formatCurrency: (value: number | undefined) => value ? `$${value.toLocaleString()}` : '$0',
  getPartyColor: (party: string) => party === 'D' ? 'text-blue-600' : party === 'R' ? 'text-red-600' : 'text-gray-600',
  getPartyBg: (party: string) => party === 'D' ? 'bg-blue-100' : party === 'R' ? 'bg-red-100' : 'bg-gray-100',
}));

import PoliticiansView from './PoliticiansView';

// Create wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

// Helper to create mock politician
const createMockPolitician = (overrides = {}) => ({
  id: '1',
  name: 'John Doe',
  party: 'D',
  chamber: 'House',
  state: 'CA',
  jurisdiction_id: 'us_house',
  total_volume: 5000000,
  total_trades: 45,
  ...overrides,
});

// Helper to create mock pagination
const createMockPagination = (overrides = {}) => ({
  page: 1,
  totalPages: 1,
  totalItems: 0,
  itemsPerPage: 10,
  startIndex: 0,
  endIndex: 10,
  setPage: vi.fn(),
  setTotalItems: vi.fn(),
  setItemsPerPage: vi.fn(),
  nextPage: vi.fn(),
  prevPage: vi.fn(),
  ...overrides,
});

describe('PoliticiansView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePoliticians.mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
    });
    mockUsePagination.mockReturnValue(createMockPagination());
  });

  describe('Header', () => {
    it('renders the title', () => {
      render(<PoliticiansView />, { wrapper: createWrapper() });

      expect(screen.getByText('Politicians')).toBeInTheDocument();
    });

    it('renders the description', () => {
      render(<PoliticiansView />, { wrapper: createWrapper() });

      expect(
        screen.getByText('All tracked politicians and their trading activity')
      ).toBeInTheDocument();
    });
  });

  describe('Loading State', () => {
    it('shows loading spinner when loading', () => {
      mockUsePoliticians.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
      });

      render(<PoliticiansView />, { wrapper: createWrapper() });

      expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });

    it('does not show spinner when loaded', () => {
      mockUsePoliticians.mockReturnValue({
        data: [createMockPolitician()],
        isLoading: false,
        error: null,
      });

      render(<PoliticiansView />, { wrapper: createWrapper() });

      expect(document.querySelector('.animate-spin')).not.toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('shows error message when error occurs', () => {
      mockUsePoliticians.mockReturnValue({
        data: null,
        isLoading: false,
        error: new Error('Database error'),
      });

      render(<PoliticiansView />, { wrapper: createWrapper() });

      expect(screen.getByText('No data available yet')).toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('shows empty message when no politicians', () => {
      mockUsePoliticians.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
      });

      render(<PoliticiansView />, { wrapper: createWrapper() });

      expect(screen.getByText('No politicians tracked yet')).toBeInTheDocument();
    });
  });

  describe('Politician List', () => {
    it('renders politician names', () => {
      mockUsePoliticians.mockReturnValue({
        data: [
          createMockPolitician({ id: '1', name: 'John Doe' }),
          createMockPolitician({ id: '2', name: 'Jane Smith' }),
        ],
        isLoading: false,
        error: null,
      });

      render(<PoliticiansView />, { wrapper: createWrapper() });

      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('Jane Smith')).toBeInTheDocument();
    });

    it('renders party badges', () => {
      mockUsePoliticians.mockReturnValue({
        data: [
          createMockPolitician({ id: '1', party: 'D' }),
          createMockPolitician({ id: '2', party: 'R' }),
        ],
        isLoading: false,
        error: null,
      });

      render(<PoliticiansView />, { wrapper: createWrapper() });

      expect(screen.getByText('D')).toBeInTheDocument();
      expect(screen.getByText('R')).toBeInTheDocument();
    });

    it('renders total volume formatted', () => {
      mockUsePoliticians.mockReturnValue({
        data: [createMockPolitician({ total_volume: 5000000 })],
        isLoading: false,
        error: null,
      });

      render(<PoliticiansView />, { wrapper: createWrapper() });

      expect(screen.getByText('$5,000,000')).toBeInTheDocument();
    });

    it('renders total trades', () => {
      mockUsePoliticians.mockReturnValue({
        data: [createMockPolitician({ total_trades: 45 })],
        isLoading: false,
        error: null,
      });

      render(<PoliticiansView />, { wrapper: createWrapper() });

      expect(screen.getByText('45')).toBeInTheDocument();
    });

    it('renders initials avatar', () => {
      mockUsePoliticians.mockReturnValue({
        data: [createMockPolitician({ name: 'John Doe' })],
        isLoading: false,
        error: null,
      });

      render(<PoliticiansView />, { wrapper: createWrapper() });

      expect(screen.getByText('JD')).toBeInTheDocument();
    });

    it('handles missing name gracefully', () => {
      mockUsePoliticians.mockReturnValue({
        data: [createMockPolitician({ name: undefined })],
        isLoading: false,
        error: null,
      });

      render(<PoliticiansView />, { wrapper: createWrapper() });

      expect(screen.getByText('Unknown')).toBeInTheDocument();
      expect(screen.getByText('??')).toBeInTheDocument();
    });
  });

  describe('Table Headers and Sorting', () => {
    beforeEach(() => {
      mockUsePoliticians.mockReturnValue({
        data: [
          createMockPolitician({ id: '1', name: 'Alice', total_volume: 1000000, total_trades: 10 }),
          createMockPolitician({ id: '2', name: 'Bob', total_volume: 5000000, total_trades: 50 }),
          createMockPolitician({ id: '3', name: 'Charlie', total_volume: 2000000, total_trades: 20 }),
        ],
        isLoading: false,
        error: null,
      });
    });

    it('renders table headers', () => {
      render(<PoliticiansView />, { wrapper: createWrapper() });

      expect(screen.getByText('Politician')).toBeInTheDocument();
      expect(screen.getByText('Chamber')).toBeInTheDocument();
      expect(screen.getByText('Volume')).toBeInTheDocument();
      expect(screen.getByText('Trades')).toBeInTheDocument();
    });

    it('sorts by name when clicking header', async () => {
      const setPageMock = vi.fn();
      mockUsePagination.mockReturnValue(createMockPagination({ setPage: setPageMock }));

      render(<PoliticiansView />, { wrapper: createWrapper() });

      const nameHeader = screen.getByText('Politician');
      fireEvent.click(nameHeader);

      // Should reset to page 1
      expect(setPageMock).toHaveBeenCalledWith(1);
    });

    it('sorts by volume when clicking header', () => {
      const setPageMock = vi.fn();
      mockUsePagination.mockReturnValue(createMockPagination({ setPage: setPageMock }));

      render(<PoliticiansView />, { wrapper: createWrapper() });

      const volumeHeader = screen.getByText('Volume');
      fireEvent.click(volumeHeader);

      expect(setPageMock).toHaveBeenCalledWith(1);
    });

    it('toggles sort direction when clicking same header twice', () => {
      const setPageMock = vi.fn();
      mockUsePagination.mockReturnValue(createMockPagination({ setPage: setPageMock }));

      render(<PoliticiansView />, { wrapper: createWrapper() });

      const volumeHeader = screen.getByText('Volume');

      // Click once
      fireEvent.click(volumeHeader);
      // Click again to toggle direction
      fireEvent.click(volumeHeader);

      expect(setPageMock).toHaveBeenCalledTimes(2);
    });
  });

  describe('Pagination', () => {
    it('shows pagination controls when politicians exist', () => {
      mockUsePoliticians.mockReturnValue({
        data: [createMockPolitician()],
        isLoading: false,
        error: null,
      });

      render(<PoliticiansView />, { wrapper: createWrapper() });

      expect(screen.getByTestId('pagination-controls')).toBeInTheDocument();
    });

    it('passes correct itemLabel to pagination', () => {
      mockUsePoliticians.mockReturnValue({
        data: [createMockPolitician()],
        isLoading: false,
        error: null,
      });

      render(<PoliticiansView />, { wrapper: createWrapper() });

      expect(screen.getByTestId('pagination-item-label')).toHaveTextContent('politicians');
    });

    it('calls setTotalItems when politicians change', () => {
      const setTotalItemsMock = vi.fn();
      mockUsePagination.mockReturnValue(createMockPagination({ setTotalItems: setTotalItemsMock }));
      mockUsePoliticians.mockReturnValue({
        data: [
          createMockPolitician({ id: '1' }),
          createMockPolitician({ id: '2' }),
        ],
        isLoading: false,
        error: null,
      });

      render(<PoliticiansView />, { wrapper: createWrapper() });

      expect(setTotalItemsMock).toHaveBeenCalledWith(2);
    });

    it('paginates results correctly', () => {
      mockUsePagination.mockReturnValue(createMockPagination({
        startIndex: 0,
        endIndex: 1,
      }));
      mockUsePoliticians.mockReturnValue({
        data: [
          createMockPolitician({ id: '1', name: 'First' }),
          createMockPolitician({ id: '2', name: 'Second' }),
        ],
        isLoading: false,
        error: null,
      });

      render(<PoliticiansView />, { wrapper: createWrapper() });

      // Only first politician should be shown
      expect(screen.getByText('First')).toBeInTheDocument();
      expect(screen.queryByText('Second')).not.toBeInTheDocument();
    });
  });

  describe('Modal Interaction', () => {
    it('opens modal when clicking on politician row', () => {
      mockUsePoliticians.mockReturnValue({
        data: [createMockPolitician({ name: 'John Doe' })],
        isLoading: false,
        error: null,
      });

      render(<PoliticiansView />, { wrapper: createWrapper() });

      const politicianRow = screen.getByText('John Doe').closest('div[class*="cursor-pointer"]');
      if (politicianRow) {
        fireEvent.click(politicianRow);
      }

      expect(screen.getByTestId('politician-modal')).toBeInTheDocument();
      expect(screen.getByTestId('modal-politician-name')).toHaveTextContent('John Doe');
    });

    it('closes modal when close button clicked', async () => {
      mockUsePoliticians.mockReturnValue({
        data: [createMockPolitician({ name: 'John Doe' })],
        isLoading: false,
        error: null,
      });

      render(<PoliticiansView />, { wrapper: createWrapper() });

      // Open modal
      const politicianRow = screen.getByText('John Doe').closest('div[class*="cursor-pointer"]');
      if (politicianRow) {
        fireEvent.click(politicianRow);
      }

      // Close modal
      const closeButton = screen.getByTestId('modal-close');
      fireEvent.click(closeButton);

      await waitFor(() => {
        expect(screen.queryByTestId('politician-modal')).not.toBeInTheDocument();
      });
    });
  });

  describe('Initial Politician Selection', () => {
    it('opens modal for initialPoliticianId when found', () => {
      const onPoliticianSelectedMock = vi.fn();
      mockUsePoliticians.mockReturnValue({
        data: [
          createMockPolitician({ id: 'pol1', name: 'Target Politician' }),
          createMockPolitician({ id: 'pol2', name: 'Other Politician' }),
        ],
        isLoading: false,
        error: null,
      });

      render(
        <PoliticiansView
          initialPoliticianId="pol1"
          onPoliticianSelected={onPoliticianSelectedMock}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByTestId('politician-modal')).toBeInTheDocument();
      expect(screen.getByTestId('modal-politician-name')).toHaveTextContent('Target Politician');
      expect(onPoliticianSelectedMock).toHaveBeenCalled();
    });

    it('does not open modal when initialPoliticianId not found', () => {
      const onPoliticianSelectedMock = vi.fn();
      mockUsePoliticians.mockReturnValue({
        data: [createMockPolitician({ id: 'pol1', name: 'Some Politician' })],
        isLoading: false,
        error: null,
      });

      render(
        <PoliticiansView
          initialPoliticianId="nonexistent"
          onPoliticianSelected={onPoliticianSelectedMock}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.queryByTestId('politician-modal')).not.toBeInTheDocument();
      expect(onPoliticianSelectedMock).not.toHaveBeenCalled();
    });

    it('does not open modal when initialPoliticianId is null', () => {
      mockUsePoliticians.mockReturnValue({
        data: [createMockPolitician()],
        isLoading: false,
        error: null,
      });

      render(
        <PoliticiansView initialPoliticianId={null} />,
        { wrapper: createWrapper() }
      );

      expect(screen.queryByTestId('politician-modal')).not.toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles undefined chamber gracefully', () => {
      mockUsePoliticians.mockReturnValue({
        data: [createMockPolitician({ chamber: undefined })],
        isLoading: false,
        error: null,
      });

      render(<PoliticiansView />, { wrapper: createWrapper() });

      // Should show "Unknown" for chamber in mobile view
      expect(screen.getAllByText('Unknown').length).toBeGreaterThan(0);
    });

    it('handles undefined state with jurisdiction_id fallback', () => {
      mockUsePoliticians.mockReturnValue({
        data: [createMockPolitician({ state: undefined, jurisdiction_id: 'us_house' })],
        isLoading: false,
        error: null,
      });

      render(<PoliticiansView />, { wrapper: createWrapper() });

      expect(screen.getByText('us_house')).toBeInTheDocument();
    });

    it('handles zero volume and trades', () => {
      mockUsePoliticians.mockReturnValue({
        data: [createMockPolitician({ total_volume: 0, total_trades: 0 })],
        isLoading: false,
        error: null,
      });

      render(<PoliticiansView />, { wrapper: createWrapper() });

      expect(screen.getByText('$0')).toBeInTheDocument();
      expect(screen.getByText('0')).toBeInTheDocument();
    });

    it('handles undefined total_volume and total_trades', () => {
      mockUsePoliticians.mockReturnValue({
        data: [createMockPolitician({ total_volume: undefined, total_trades: undefined })],
        isLoading: false,
        error: null,
      });

      render(<PoliticiansView />, { wrapper: createWrapper() });

      // formatCurrency should handle undefined
      expect(screen.getByText('$0')).toBeInTheDocument();
    });
  });
});
