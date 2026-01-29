/**
 * Tests for pages/ReferencePortfolio.tsx
 *
 * Tests:
 * - Page header rendering
 * - Market status indicator
 * - Trading status badge
 * - Last sync time display
 * - Info alert content
 * - Strategy configuration display
 * - Child component rendering
 * - Loading states
 * - Edge cases with missing data
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock SidebarLayout
vi.mock('@/components/layouts/SidebarLayout', () => ({
  SidebarLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="sidebar-layout">{children}</div>
  ),
}));

// Mock child components from reference-portfolio
vi.mock('@/components/reference-portfolio', () => ({
  MetricsCards: () => <div data-testid="metrics-cards">Metrics Cards</div>,
  PerformanceChart: () => <div data-testid="performance-chart">Performance Chart</div>,
  HoldingsTable: () => <div data-testid="holdings-table">Holdings Table</div>,
  TradeHistoryTable: ({ limit }: { limit: number }) => (
    <div data-testid="trade-history-table">Trade History (limit: {limit})</div>
  ),
  RiskMetrics: () => <div data-testid="risk-metrics">Risk Metrics</div>,
}));

// Mock strategy-follow components
vi.mock('@/components/strategy-follow', () => ({
  ApplyStrategyButton: ({ strategyType }: { strategyType: string }) => (
    <button data-testid="apply-strategy-button">Apply {strategyType}</button>
  ),
  FollowingStatusBadge: () => <div data-testid="following-status-badge">Following Status</div>,
}));

// Mock UI components
vi.mock('@/components/ui/alert', () => ({
  Alert: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div data-testid="alert" className={className}>{children}</div>
  ),
  AlertDescription: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="alert-description">{children}</div>
  ),
}));

vi.mock('@/components/ui/badge', () => ({
  Badge: ({ children, variant }: { children: React.ReactNode; variant?: string }) => (
    <span data-testid="badge" data-variant={variant}>{children}</span>
  ),
}));

vi.mock('@/components/ui/separator', () => ({
  Separator: () => <hr data-testid="separator" />,
}));

// Mock hooks
const mockUseReferencePortfolioState = vi.fn();
const mockUseMarketStatus = vi.fn();

vi.mock('@/hooks/useReferencePortfolio', () => ({
  useReferencePortfolioState: () => mockUseReferencePortfolioState(),
  useMarketStatus: () => mockUseMarketStatus(),
}));

import ReferencePortfolio from './ReferencePortfolio';

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

// Helper to create mock state
const createMockState = (overrides = {}) => ({
  id: 'state-1',
  config_id: 'config-1',
  cash: 75000,
  portfolio_value: 125000,
  positions_value: 50000,
  buying_power: 75000,
  total_return: 25000,
  total_return_pct: 25,
  day_return: 500,
  day_return_pct: 0.4,
  max_drawdown: 5,
  current_drawdown: 2,
  sharpe_ratio: 1.5,
  sortino_ratio: 2.0,
  volatility: 15,
  total_trades: 100,
  trades_today: 3,
  winning_trades: 60,
  losing_trades: 40,
  win_rate: 60,
  avg_win: 500,
  avg_loss: 300,
  profit_factor: 1.5,
  open_positions: 8,
  peak_portfolio_value: 130000,
  benchmark_value: 120000,
  benchmark_return_pct: 20,
  alpha: 5,
  last_trade_at: '2026-01-29T14:30:00Z',
  last_sync_at: '2026-01-29T15:00:00Z',
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2026-01-29T15:00:00Z',
  config: {
    id: 'config-1',
    name: 'Reference Strategy',
    description: 'Automated paper trading based on signals',
    initial_capital: 100000,
    min_confidence_threshold: 0.7,
    max_position_size_pct: 5,
    max_portfolio_positions: 20,
    max_single_trade_pct: 2,
    max_daily_trades: 10,
    default_stop_loss_pct: 5,
    default_take_profit_pct: 15,
    base_position_size_pct: 1,
    confidence_multiplier: 3,
    is_active: true,
    trading_mode: 'paper',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2026-01-29T00:00:00Z',
  },
  ...overrides,
});

// Helper to create mock market status
const createMockMarketStatus = (overrides = {}) => ({
  isOpen: true,
  nextOpen: null,
  ...overrides,
});

describe('ReferencePortfolio', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseReferencePortfolioState.mockReturnValue({
      data: createMockState(),
      isLoading: false,
      error: null,
    });
    mockUseMarketStatus.mockReturnValue({
      data: createMockMarketStatus(),
      isLoading: false,
      error: null,
    });
  });

  describe('Page Header', () => {
    it('renders page title', () => {
      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText('Reference Strategy')).toBeInTheDocument();
    });

    it('renders page description', () => {
      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText('Automated paper trading based on politician activity signals')).toBeInTheDocument();
    });

    it('renders within SidebarLayout', () => {
      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByTestId('sidebar-layout')).toBeInTheDocument();
    });
  });

  describe('Market Status', () => {
    it('displays market open status when market is open', () => {
      mockUseMarketStatus.mockReturnValue({
        data: createMockMarketStatus({ isOpen: true }),
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText('Market Open')).toBeInTheDocument();
    });

    it('displays market closed status when market is closed', () => {
      mockUseMarketStatus.mockReturnValue({
        data: createMockMarketStatus({ isOpen: false }),
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText('Market Closed')).toBeInTheDocument();
    });

    it('handles null market status gracefully', () => {
      mockUseMarketStatus.mockReturnValue({
        data: null,
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText('Market Closed')).toBeInTheDocument();
    });
  });

  describe('Trading Status', () => {
    it('displays Trading Active badge when is_active is true', () => {
      mockUseReferencePortfolioState.mockReturnValue({
        data: createMockState({ config: { ...createMockState().config, is_active: true } }),
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText(/Trading Active/)).toBeInTheDocument();
    });

    it('displays Trading Paused badge when is_active is false', () => {
      mockUseReferencePortfolioState.mockReturnValue({
        data: createMockState({ config: { ...createMockState().config, is_active: false } }),
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText('Trading Paused')).toBeInTheDocument();
    });

    it('displays Trading Paused when state is null', () => {
      mockUseReferencePortfolioState.mockReturnValue({
        data: null,
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText('Trading Paused')).toBeInTheDocument();
    });
  });

  describe('Last Sync Time', () => {
    it('displays last sync time when available', () => {
      mockUseReferencePortfolioState.mockReturnValue({
        data: createMockState({ last_sync_at: '2026-01-29T15:00:00Z' }),
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      // Check for "Updated" text - actual time depends on timezone
      expect(screen.getByText(/Updated/)).toBeInTheDocument();
    });

    it('does not display sync time when null', () => {
      mockUseReferencePortfolioState.mockReturnValue({
        data: createMockState({ last_sync_at: null }),
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.queryByText(/Updated/)).not.toBeInTheDocument();
    });
  });

  describe('Info Alert', () => {
    it('displays info alert with confidence threshold', () => {
      mockUseReferencePortfolioState.mockReturnValue({
        data: createMockState({ config: { ...createMockState().config, min_confidence_threshold: 0.7 } }),
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText('70% confidence')).toBeInTheDocument();
    });

    it('displays last trade time in alert when available', () => {
      mockUseReferencePortfolioState.mockReturnValue({
        data: createMockState({ last_trade_at: '2026-01-29T14:30:00Z' }),
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText(/Last trade:/)).toBeInTheDocument();
    });

    it('does not display last trade time when null', () => {
      mockUseReferencePortfolioState.mockReturnValue({
        data: createMockState({ last_trade_at: null }),
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.queryByText(/Last trade:/)).not.toBeInTheDocument();
    });

    it('uses default 70% when confidence threshold is not set', () => {
      mockUseReferencePortfolioState.mockReturnValue({
        data: createMockState({ config: { ...createMockState().config, min_confidence_threshold: undefined } }),
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText('70% confidence')).toBeInTheDocument();
    });
  });

  describe('Child Components', () => {
    it('renders MetricsCards component', () => {
      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByTestId('metrics-cards')).toBeInTheDocument();
    });

    it('renders PerformanceChart component', () => {
      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByTestId('performance-chart')).toBeInTheDocument();
    });

    it('renders HoldingsTable component', () => {
      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByTestId('holdings-table')).toBeInTheDocument();
    });

    it('renders RiskMetrics component', () => {
      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByTestId('risk-metrics')).toBeInTheDocument();
    });

    it('renders TradeHistoryTable with limit of 20', () => {
      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByTestId('trade-history-table')).toBeInTheDocument();
      expect(screen.getByText(/limit: 20/)).toBeInTheDocument();
    });

    it('renders FollowingStatusBadge component', () => {
      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByTestId('following-status-badge')).toBeInTheDocument();
    });

    it('renders ApplyStrategyButton with reference type', () => {
      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByTestId('apply-strategy-button')).toBeInTheDocument();
      expect(screen.getByText('Apply reference')).toBeInTheDocument();
    });
  });

  describe('Strategy Configuration', () => {
    it('displays strategy configuration section', () => {
      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText('Strategy Configuration')).toBeInTheDocument();
    });

    it('displays initial capital', () => {
      mockUseReferencePortfolioState.mockReturnValue({
        data: createMockState({ config: { ...createMockState().config, initial_capital: 100000 } }),
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText('Initial Capital')).toBeInTheDocument();
      expect(screen.getByText('$100k')).toBeInTheDocument();
    });

    it('displays minimum confidence threshold', () => {
      mockUseReferencePortfolioState.mockReturnValue({
        data: createMockState({ config: { ...createMockState().config, min_confidence_threshold: 0.7 } }),
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText('Min Confidence')).toBeInTheDocument();
      // 70% appears in both alert and config section
      expect(screen.getAllByText('70%').length).toBeGreaterThanOrEqual(1);
    });

    it('displays max position size', () => {
      mockUseReferencePortfolioState.mockReturnValue({
        data: createMockState({ config: { ...createMockState().config, max_position_size_pct: 8 } }),
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText('Max Position Size')).toBeInTheDocument();
      expect(screen.getByText('8%')).toBeInTheDocument();
    });

    it('displays max positions', () => {
      mockUseReferencePortfolioState.mockReturnValue({
        data: createMockState({ config: { ...createMockState().config, max_portfolio_positions: 20 } }),
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText('Max Positions')).toBeInTheDocument();
      expect(screen.getByText('20')).toBeInTheDocument();
    });

    it('displays max daily trades', () => {
      mockUseReferencePortfolioState.mockReturnValue({
        data: createMockState({ config: { ...createMockState().config, max_daily_trades: 10 } }),
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText('Max Daily Trades')).toBeInTheDocument();
      expect(screen.getByText('10')).toBeInTheDocument();
    });

    it('displays base position size', () => {
      mockUseReferencePortfolioState.mockReturnValue({
        data: createMockState({ config: { ...createMockState().config, base_position_size_pct: 1 } }),
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText('Base Position')).toBeInTheDocument();
      expect(screen.getByText('1%')).toBeInTheDocument();
    });

    it('displays confidence multiplier', () => {
      mockUseReferencePortfolioState.mockReturnValue({
        data: createMockState({ config: { ...createMockState().config, confidence_multiplier: 3 } }),
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText('Confidence Multiplier')).toBeInTheDocument();
      expect(screen.getByText('Up to 3x')).toBeInTheDocument();
    });

    it('displays default stop loss', () => {
      mockUseReferencePortfolioState.mockReturnValue({
        data: createMockState({ config: { ...createMockState().config, default_stop_loss_pct: 5 } }),
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText('Default Stop Loss')).toBeInTheDocument();
      // 5% appears in both max position size and stop loss
      expect(screen.getAllByText('5%').length).toBeGreaterThanOrEqual(1);
    });

    it('uses default values when config values are undefined', () => {
      mockUseReferencePortfolioState.mockReturnValue({
        data: createMockState({ config: {} }),
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      // Check that defaults are used
      expect(screen.getByText('$100k')).toBeInTheDocument(); // default 100000
      expect(screen.getByText('20')).toBeInTheDocument(); // default max positions
      expect(screen.getByText('10')).toBeInTheDocument(); // default max daily trades
    });
  });

  describe('Footer', () => {
    it('displays disclaimer about paper trading', () => {
      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText(/paper trading demonstration/)).toBeInTheDocument();
    });

    it('displays disclaimer about past performance', () => {
      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText(/Past performance does not guarantee future results/)).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles null state gracefully', () => {
      mockUseReferencePortfolioState.mockReturnValue({
        data: null,
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      // Should still render with defaults
      expect(screen.getByText('Reference Strategy')).toBeInTheDocument();
      expect(screen.getByText('Trading Paused')).toBeInTheDocument();
    });

    it('handles undefined config gracefully', () => {
      mockUseReferencePortfolioState.mockReturnValue({
        data: createMockState({ config: undefined }),
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.getByText('Trading Paused')).toBeInTheDocument();
    });

    it('handles loading state for market status', () => {
      mockUseMarketStatus.mockReturnValue({
        data: undefined,
        isLoading: true,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      // Should show closed when loading/undefined
      expect(screen.getByText('Market Closed')).toBeInTheDocument();
    });

    it('handles missing last_sync_at and last_trade_at', () => {
      mockUseReferencePortfolioState.mockReturnValue({
        data: createMockState({ last_sync_at: null, last_trade_at: null }),
        isLoading: false,
      });

      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(screen.queryByText(/Updated/)).not.toBeInTheDocument();
      expect(screen.queryByText(/Last trade:/)).not.toBeInTheDocument();
    });
  });

  describe('Hook Integration', () => {
    it('calls useReferencePortfolioState', () => {
      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(mockUseReferencePortfolioState).toHaveBeenCalled();
    });

    it('calls useMarketStatus', () => {
      render(<ReferencePortfolio />, { wrapper: createWrapper() });
      expect(mockUseMarketStatus).toHaveBeenCalled();
    });
  });
});
