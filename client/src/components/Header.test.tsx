/**
 * Tests for components/Header.tsx
 *
 * Tests:
 * - Header component rendering
 * - User authentication states (signed in vs signed out)
 * - Mobile menu button functionality
 * - Mobile search dialog
 * - Sign out functionality
 * - Display name formatting (email and wallet address)
 * - Navigation links
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import React from 'react';

// Mock child components
vi.mock('@/components/SyncStatus', () => ({
  HeaderSyncStatus: () => <div data-testid="sync-status">Sync Status</div>,
}));

vi.mock('@/components/GlobalSearch', () => ({
  GlobalSearch: ({ fullWidth, onResultSelect }: { fullWidth?: boolean; onResultSelect?: () => void }) => (
    <div data-testid="global-search" data-fullwidth={fullWidth}>
      Global Search
      {onResultSelect && (
        <button data-testid="search-result" onClick={onResultSelect}>
          Select Result
        </button>
      )}
    </div>
  ),
}));

// Mock hooks
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockUser = vi.fn();
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ user: mockUser() }),
}));

const mockIsAdmin = vi.fn();
vi.mock('@/hooks/useAdmin', () => ({
  useAdmin: () => ({ isAdmin: mockIsAdmin() }),
}));

// Mock supabase
const mockSignOut = vi.fn().mockResolvedValue({});
vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    auth: {
      signOut: () => mockSignOut(),
    },
  },
}));

// Mock safeStorage
vi.mock('@/lib/safeStorage', () => ({
  safeClearByPrefix: vi.fn(),
}));

// Mock logger
vi.mock('@/lib/logger', () => ({
  logError: vi.fn(),
}));

import Header from './Header';

describe('Header', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUser.mockReturnValue(null);
    mockIsAdmin.mockReturnValue(false);
    // Mock window.location.reload
    Object.defineProperty(window, 'location', {
      value: { reload: vi.fn() },
      writable: true,
    });
  });

  const renderHeader = (props = {}) => {
    return render(
      <MemoryRouter>
        <Header {...props} />
      </MemoryRouter>
    );
  };

  describe('Basic rendering', () => {
    it('renders the header with logo and title', () => {
      renderHeader();

      expect(screen.getByText('Gov')).toBeInTheDocument();
      expect(screen.getByText('Market')).toBeInTheDocument();
      expect(screen.getByText('Politician Trading Tracker')).toBeInTheDocument();
    });

    it('renders the sync status component', () => {
      renderHeader();

      expect(screen.getByTestId('sync-status')).toBeInTheDocument();
    });

    it('renders the desktop search component', () => {
      renderHeader();

      expect(screen.getByTestId('global-search')).toBeInTheDocument();
    });

    it('renders mobile search button', () => {
      renderHeader();

      expect(screen.getByLabelText('Search')).toBeInTheDocument();
    });
  });

  describe('Mobile menu', () => {
    it('renders menu button when onMenuClick is provided', () => {
      const onMenuClick = vi.fn();
      renderHeader({ onMenuClick });

      expect(screen.getByLabelText('Open menu')).toBeInTheDocument();
    });

    it('does not render menu button when onMenuClick is not provided', () => {
      renderHeader();

      expect(screen.queryByLabelText('Open menu')).not.toBeInTheDocument();
    });

    it('calls onMenuClick when menu button is clicked', async () => {
      const user = userEvent.setup();
      const onMenuClick = vi.fn();
      renderHeader({ onMenuClick });

      await user.click(screen.getByLabelText('Open menu'));

      expect(onMenuClick).toHaveBeenCalledTimes(1);
    });
  });

  describe('Mobile search dialog', () => {
    it('opens mobile search dialog when search button is clicked', async () => {
      const user = userEvent.setup();
      renderHeader();

      await user.click(screen.getByLabelText('Search'));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
        expect(screen.getByText('Search')).toBeInTheDocument();
      });
    });

    it('closes dialog when result is selected', async () => {
      const user = userEvent.setup();
      renderHeader();

      // Open dialog
      await user.click(screen.getByLabelText('Search'));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Click search result
      const searchResults = screen.getAllByTestId('search-result');
      await user.click(searchResults[searchResults.length - 1]);

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });
  });

  describe('Unauthenticated user', () => {
    beforeEach(() => {
      mockUser.mockReturnValue(null);
    });

    it('shows Sign In button when user is not authenticated', () => {
      renderHeader();

      expect(screen.getByText('Sign In')).toBeInTheDocument();
    });

    it('navigates to /auth when Sign In is clicked', async () => {
      const user = userEvent.setup();
      renderHeader();

      await user.click(screen.getByText('Sign In'));

      expect(mockNavigate).toHaveBeenCalledWith('/auth');
    });
  });

  describe('Authenticated user', () => {
    const testUser = {
      email: 'testuser@example.com',
      user_metadata: {},
    };

    beforeEach(() => {
      mockUser.mockReturnValue(testUser);
    });

    it('shows user dropdown when authenticated', () => {
      renderHeader();

      expect(screen.getByText('testuser')).toBeInTheDocument();
    });

    it('shows full email in dropdown menu', async () => {
      const user = userEvent.setup();
      renderHeader();

      await user.click(screen.getByText('testuser'));

      await waitFor(() => {
        expect(screen.getByText('testuser@example.com')).toBeInTheDocument();
      });
    });

    it('shows Sign out option in dropdown', async () => {
      const user = userEvent.setup();
      renderHeader();

      await user.click(screen.getByText('testuser'));

      await waitFor(() => {
        expect(screen.getByText('Sign out')).toBeInTheDocument();
      });
    });

    it('calls signOut and reloads when Sign out is clicked', async () => {
      const user = userEvent.setup();
      renderHeader();

      await user.click(screen.getByText('testuser'));

      await waitFor(() => {
        expect(screen.getByText('Sign out')).toBeInTheDocument();
      });

      await user.click(screen.getByText('Sign out'));

      expect(mockSignOut).toHaveBeenCalled();
      expect(mockNavigate).toHaveBeenCalledWith('/');
      expect(window.location.reload).toHaveBeenCalled();
    });
  });

  describe('Display name formatting', () => {
    it('shows truncated wallet address for wallet users', () => {
      mockUser.mockReturnValue({
        email: null,
        user_metadata: {
          wallet_address: '0x1234567890abcdef1234567890abcdef12345678',
        },
      });

      renderHeader();

      expect(screen.getByText('0x1234...5678')).toBeInTheDocument();
    });

    it('shows email username for email users', () => {
      mockUser.mockReturnValue({
        email: 'john.doe@company.com',
        user_metadata: {},
      });

      renderHeader();

      expect(screen.getByText('john.doe')).toBeInTheDocument();
    });

    it('shows "User" as fallback when no email or wallet', () => {
      mockUser.mockReturnValue({
        email: null,
        user_metadata: {},
      });

      renderHeader();

      expect(screen.getByText('User')).toBeInTheDocument();
    });
  });

  describe('Navigation', () => {
    it('logo links to home page', () => {
      renderHeader();

      const homeLink = screen.getByRole('link');
      expect(homeLink).toHaveAttribute('href', '/');
    });
  });

  describe('Accessibility', () => {
    it('has accessible menu button', () => {
      const onMenuClick = vi.fn();
      renderHeader({ onMenuClick });

      const menuButton = screen.getByLabelText('Open menu');
      expect(menuButton).toHaveAttribute('aria-label', 'Open menu');
    });

    it('has accessible search button', () => {
      renderHeader();

      const searchButton = screen.getByLabelText('Search');
      expect(searchButton).toHaveAttribute('aria-label', 'Search');
    });

    it('Sign In button has title attribute', () => {
      mockUser.mockReturnValue(null);
      renderHeader();

      const signInButton = screen.getByText('Sign In').closest('button');
      expect(signInButton).toHaveAttribute('title', 'Sign in to access all features');
    });
  });
});
