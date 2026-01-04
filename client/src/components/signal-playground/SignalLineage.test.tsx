import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { SignalLineage } from './SignalLineage';

// Mock Supabase
const mockSupabaseFrom = vi.fn();

vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    from: (...args: any[]) => mockSupabaseFrom(...args),
  },
}));

// Sample test data
const mockSignal = {
  id: 'signal-123',
  ticker: 'AAPL',
  signal_type: 'buy',
  confidence_score: 0.85,
  generated_at: '2024-01-15T10:00:00Z',
  model_id: 'model-456',
  model_version: 'v2.1.0',
  generation_context: { lookbackDays: 90, minConfidence: 0.6 },
  reproducibility_hash: 'abc123def456',
};

const mockModel = {
  id: 'model-456',
  model_name: 'xgboost-signals',
  model_version: 'v2.1.0',
  model_type: 'xgboost',
  status: 'active',
  training_completed_at: '2024-01-10T08:00:00Z',
  metrics: { accuracy: 0.82, f1_weighted: 0.79 },
  feature_importance: {
    buy_sell_ratio: 0.25,
    politician_count: 0.20,
    recent_activity: 0.15,
  },
};

const mockAuditTrail = [
  {
    id: 'audit-1',
    event_type: 'created',
    event_timestamp: '2024-01-15T10:00:00Z',
    signal_snapshot: { ticker: 'AAPL', confidence: 0.85 },
    model_version: 'v2.1.0',
    source_system: 'edge_function',
    triggered_by: 'scheduler',
  },
];

const mockLifecycle = [
  {
    id: 'lifecycle-1',
    previous_state: null,
    current_state: 'generated',
    transition_reason: 'Signal generated from model prediction',
    transitioned_at: '2024-01-15T10:00:00Z',
    transitioned_by: 'system',
  },
  {
    id: 'lifecycle-2',
    previous_state: 'generated',
    current_state: 'in_cart',
    transition_reason: 'Added to cart by user',
    transitioned_at: '2024-01-15T11:00:00Z',
    transitioned_by: 'user',
  },
];

// Test wrapper
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

// Helper to setup Supabase mock responses
const setupSupabaseMocks = (options: {
  signal?: typeof mockSignal | null;
  model?: typeof mockModel | null;
  auditTrail?: typeof mockAuditTrail;
  lifecycle?: typeof mockLifecycle;
  signalError?: boolean;
  modelError?: boolean;
}) => {
  mockSupabaseFrom.mockImplementation((table: string) => {
    const createChain = (data: any, error: any = null) => ({
      select: vi.fn().mockReturnThis(),
      eq: vi.fn().mockReturnThis(),
      order: vi.fn().mockReturnThis(),
      single: vi.fn().mockResolvedValue({ data, error }),
    });

    switch (table) {
      case 'trading_signals':
        return createChain(
          options.signalError ? null : options.signal,
          options.signalError ? { message: 'Signal error' } : null
        );
      case 'ml_models':
        return createChain(
          options.modelError ? null : options.model,
          options.modelError ? { message: 'Model error' } : null
        );
      case 'signal_audit_trail':
        return {
          select: vi.fn().mockReturnThis(),
          eq: vi.fn().mockReturnThis(),
          order: vi.fn().mockResolvedValue({
            data: options.auditTrail || [],
            error: null,
          }),
        };
      case 'signal_lifecycle':
        return {
          select: vi.fn().mockReturnThis(),
          eq: vi.fn().mockReturnThis(),
          order: vi.fn().mockResolvedValue({
            data: options.lifecycle || [],
            error: null,
          }),
        };
      default:
        return createChain(null, null);
    }
  });
};

describe('SignalLineage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Full View', () => {
    it('should render loading state initially', () => {
      setupSupabaseMocks({ signal: mockSignal, model: mockModel });

      render(
        <SignalLineage signalId="signal-123" ticker="AAPL" />,
        { wrapper: createWrapper() }
      );

      // Should show loading indicator
      expect(screen.getByRole('heading', { name: /signal lineage/i })).toBeInTheDocument();
    });

    it('should display signal not found when signal is null', async () => {
      setupSupabaseMocks({ signal: null });

      render(
        <SignalLineage signalId="non-existent" ticker="AAPL" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText(/signal not found/i)).toBeInTheDocument();
      });
    });

    it('should display lineage flow when data loads', async () => {
      setupSupabaseMocks({
        signal: mockSignal,
        model: mockModel,
        auditTrail: mockAuditTrail,
        lifecycle: mockLifecycle,
      });

      render(
        <SignalLineage signalId="signal-123" ticker="AAPL" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        // Should show model name
        expect(screen.getByText('xgboost-signals')).toBeInTheDocument();
        // Should show ticker
        expect(screen.getByText('AAPL')).toBeInTheDocument();
        // Should show confidence
        expect(screen.getByText(/85%/)).toBeInTheDocument();
      });
    });

    it('should display model details section', async () => {
      setupSupabaseMocks({
        signal: mockSignal,
        model: mockModel,
        auditTrail: [],
        lifecycle: [],
      });

      render(
        <SignalLineage signalId="signal-123" ticker="AAPL" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText(/model details/i)).toBeInTheDocument();
        expect(screen.getByText('xgboost')).toBeInTheDocument();
        expect(screen.getByText('active')).toBeInTheDocument();
      });
    });

    it('should display feature weights', async () => {
      setupSupabaseMocks({
        signal: mockSignal,
        model: mockModel,
        auditTrail: [],
        lifecycle: [],
      });

      render(
        <SignalLineage signalId="signal-123" ticker="AAPL" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText(/feature weights used/i)).toBeInTheDocument();
        expect(screen.getByText('buy_sell_ratio')).toBeInTheDocument();
        expect(screen.getByText('25.0%')).toBeInTheDocument();
      });
    });

    it('should display reproducibility hash', async () => {
      setupSupabaseMocks({
        signal: mockSignal,
        model: mockModel,
        auditTrail: [],
        lifecycle: [],
      });

      render(
        <SignalLineage signalId="signal-123" ticker="AAPL" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText(/reproducibility hash/i)).toBeInTheDocument();
        expect(screen.getByText('abc123def456')).toBeInTheDocument();
      });
    });

    it('should display lifecycle entries', async () => {
      setupSupabaseMocks({
        signal: mockSignal,
        model: mockModel,
        auditTrail: [],
        lifecycle: mockLifecycle,
      });

      render(
        <SignalLineage signalId="signal-123" ticker="AAPL" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText(/lifecycle/i)).toBeInTheDocument();
        expect(screen.getByText('generated')).toBeInTheDocument();
        expect(screen.getByText('in_cart')).toBeInTheDocument();
      });
    });

    it('should display audit trail entries', async () => {
      setupSupabaseMocks({
        signal: mockSignal,
        model: mockModel,
        auditTrail: mockAuditTrail,
        lifecycle: [],
      });

      render(
        <SignalLineage signalId="signal-123" ticker="AAPL" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText(/audit trail/i)).toBeInTheDocument();
        expect(screen.getByText('created')).toBeInTheDocument();
        expect(screen.getByText(/edge_function/i)).toBeInTheDocument();
      });
    });

    it('should display generation context', async () => {
      setupSupabaseMocks({
        signal: mockSignal,
        model: mockModel,
        auditTrail: [],
        lifecycle: [],
      });

      render(
        <SignalLineage signalId="signal-123" ticker="AAPL" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText(/generation context/i)).toBeInTheDocument();
        expect(screen.getByText(/lookbackDays/)).toBeInTheDocument();
      });
    });

    it('should show heuristic when no model', async () => {
      setupSupabaseMocks({
        signal: { ...mockSignal, model_id: null },
        model: null,
        auditTrail: [],
        lifecycle: [],
      });

      render(
        <SignalLineage signalId="signal-123" ticker="AAPL" />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByText('Heuristic')).toBeInTheDocument();
      });
    });
  });

  describe('Compact View', () => {
    it('should render compact button', () => {
      setupSupabaseMocks({ signal: mockSignal, model: mockModel });

      render(
        <SignalLineage signalId="signal-123" ticker="AAPL" compact />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByRole('button', { name: /lineage/i })).toBeInTheDocument();
    });

    it('should open dialog when button clicked', async () => {
      const user = userEvent.setup();
      setupSupabaseMocks({
        signal: mockSignal,
        model: mockModel,
        auditTrail: [],
        lifecycle: [],
      });

      render(
        <SignalLineage signalId="signal-123" ticker="AAPL" compact />,
        { wrapper: createWrapper() }
      );

      const button = screen.getByRole('button', { name: /lineage/i });
      await user.click(button);

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
        expect(screen.getByText(/signal lineage: aapl/i)).toBeInTheDocument();
      });
    });
  });
});
