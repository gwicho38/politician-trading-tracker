import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { AlertProvider, useAlerts, useAddAlert } from './AlertContext';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

// Mock Supabase
const mockSupabaseAuth = {
  getSession: vi.fn(),
  onAuthStateChange: vi.fn(() => ({
    data: { subscription: { unsubscribe: vi.fn() } },
  })),
};

vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    auth: mockSupabaseAuth,
  },
}));

// Mock sonner toast
const mockToast = {
  error: vi.fn(),
  warning: vi.fn(),
  success: vi.fn(),
  info: vi.fn(),
};

vi.mock('sonner', () => ({
  toast: mockToast,
}));

// Mock fetch for connection health check
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <AlertProvider>{children}</AlertProvider>
    </QueryClientProvider>
  );
};

describe('AlertContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    // Default: no auth session
    mockSupabaseAuth.getSession.mockResolvedValue({
      data: { session: null },
    });

    mockSupabaseAuth.onAuthStateChange.mockImplementation(() => ({
      data: { subscription: { unsubscribe: vi.fn() } },
    }));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('Alert Management', () => {
    it('should start with empty alerts', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useAlerts(), { wrapper });

      expect(result.current.alerts).toEqual([]);
      expect(result.current.getUndismissedCount()).toBe(0);
    });

    it('should add an alert', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useAlerts(), { wrapper });

      act(() => {
        result.current.addAlert({
          category: 'system',
          severity: 'error',
          title: 'Test Error',
          message: 'Something went wrong',
        });
      });

      expect(result.current.alerts).toHaveLength(1);
      expect(result.current.alerts[0].title).toBe('Test Error');
      expect(result.current.alerts[0].category).toBe('system');
      expect(result.current.alerts[0].severity).toBe('error');
      expect(result.current.alerts[0].dismissed).toBe(false);
    });

    it('should show toast notification based on severity', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useAlerts(), { wrapper });

      act(() => {
        result.current.addAlert({
          category: 'connection',
          severity: 'error',
          title: 'Connection Error',
          message: 'Failed to connect',
        });
      });

      expect(mockToast.error).toHaveBeenCalledWith('Connection Error', {
        description: 'Failed to connect',
        duration: 8000,
      });
    });

    it('should show warning toast', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useAlerts(), { wrapper });

      act(() => {
        result.current.addAlert({
          category: 'connection',
          severity: 'warning',
          title: 'Connection Degraded',
          message: 'Experiencing issues',
        });
      });

      expect(mockToast.warning).toHaveBeenCalledWith('Connection Degraded', {
        description: 'Experiencing issues',
        duration: 6000,
      });
    });

    it('should show success toast', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useAlerts(), { wrapper });

      act(() => {
        result.current.addAlert({
          category: 'order',
          severity: 'success',
          title: 'Order Placed',
          message: 'Order submitted successfully',
        });
      });

      expect(mockToast.success).toHaveBeenCalledWith('Order Placed', {
        description: 'Order submitted successfully',
        duration: 4000,
      });
    });

    it('should show info toast', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useAlerts(), { wrapper });

      act(() => {
        result.current.addAlert({
          category: 'auth',
          severity: 'info',
          title: 'Session Info',
          message: 'Your session will expire soon',
        });
      });

      expect(mockToast.info).toHaveBeenCalledWith('Session Info', {
        description: 'Your session will expire soon',
        duration: 5000,
      });
    });

    it('should dismiss an alert', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useAlerts(), { wrapper });

      act(() => {
        result.current.addAlert({
          category: 'system',
          severity: 'error',
          title: 'Test Error',
          message: 'Something went wrong',
        });
      });

      const alertId = result.current.alerts[0].id;

      act(() => {
        result.current.dismissAlert(alertId);
      });

      expect(result.current.alerts[0].dismissed).toBe(true);
      expect(result.current.getUndismissedCount()).toBe(0);
    });

    it('should dismiss all alerts', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useAlerts(), { wrapper });

      act(() => {
        result.current.addAlert({
          category: 'system',
          severity: 'error',
          title: 'Error 1',
          message: 'Message 1',
        });
        result.current.addAlert({
          category: 'connection',
          severity: 'warning',
          title: 'Warning 1',
          message: 'Message 2',
        });
      });

      expect(result.current.getUndismissedCount()).toBe(2);

      act(() => {
        result.current.dismissAllAlerts();
      });

      expect(result.current.getUndismissedCount()).toBe(0);
      expect(result.current.alerts.every((a) => a.dismissed)).toBe(true);
    });

    it('should get alerts by category', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useAlerts(), { wrapper });

      act(() => {
        result.current.addAlert({
          category: 'connection',
          severity: 'error',
          title: 'Connection Error',
          message: 'Message 1',
        });
        result.current.addAlert({
          category: 'order',
          severity: 'warning',
          title: 'Order Warning',
          message: 'Message 2',
        });
        result.current.addAlert({
          category: 'connection',
          severity: 'warning',
          title: 'Connection Warning',
          message: 'Message 3',
        });
      });

      const connectionAlerts = result.current.getAlertsByCategory('connection');
      expect(connectionAlerts).toHaveLength(2);

      const orderAlerts = result.current.getAlertsByCategory('order');
      expect(orderAlerts).toHaveLength(1);

      const signalAlerts = result.current.getAlertsByCategory('signal');
      expect(signalAlerts).toHaveLength(0);
    });
  });

  describe('Alert Deduplication', () => {
    it('should deduplicate alerts within window', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useAlerts(), { wrapper });

      act(() => {
        result.current.addAlert({
          category: 'system',
          severity: 'error',
          title: 'Same Error',
          message: 'Message 1',
        });
      });

      act(() => {
        result.current.addAlert({
          category: 'system',
          severity: 'error',
          title: 'Same Error',
          message: 'Message 2', // Different message, same category+title
        });
      });

      // Should only have 1 alert due to deduplication
      expect(result.current.alerts).toHaveLength(1);
    });

    it('should allow duplicate alerts after window expires', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useAlerts(), { wrapper });

      act(() => {
        result.current.addAlert({
          category: 'system',
          severity: 'error',
          title: 'Same Error',
          message: 'Message 1',
        });
      });

      // Advance time past dedup window (5 seconds)
      act(() => {
        vi.advanceTimersByTime(6000);
      });

      act(() => {
        result.current.addAlert({
          category: 'system',
          severity: 'error',
          title: 'Same Error',
          message: 'Message 2',
        });
      });

      // Should have 2 alerts now
      expect(result.current.alerts).toHaveLength(2);
    });

    it('should allow different alerts at same time', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useAlerts(), { wrapper });

      act(() => {
        result.current.addAlert({
          category: 'system',
          severity: 'error',
          title: 'Error A',
          message: 'Message 1',
        });
        result.current.addAlert({
          category: 'connection',
          severity: 'error',
          title: 'Error B',
          message: 'Message 2',
        });
      });

      expect(result.current.alerts).toHaveLength(2);
    });
  });

  describe('Alert Limit', () => {
    it('should limit alerts to MAX_ALERTS (50)', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useAlerts(), { wrapper });

      // Add 60 alerts with different titles to avoid deduplication
      for (let i = 0; i < 60; i++) {
        act(() => {
          result.current.addAlert({
            category: 'system',
            severity: 'info',
            title: `Alert ${i}`,
            message: `Message ${i}`,
          });
        });
      }

      expect(result.current.alerts.length).toBeLessThanOrEqual(50);
    });
  });

  describe('Connection Health', () => {
    it('should start with unknown connection health', () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useAlerts(), { wrapper });

      expect(result.current.connectionHealth).toBe('unknown');
      expect(result.current.lastConnectionCheck).toBeNull();
    });
  });
});

describe('useAlerts hook', () => {
  it('should throw error when used outside AlertProvider', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      renderHook(() => useAlerts());
    }).toThrow('useAlerts must be used within an AlertProvider');

    consoleSpy.mockRestore();
  });
});

describe('useAddAlert hook', () => {
  it('should return addAlert function', () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useAddAlert(), { wrapper });

    expect(typeof result.current).toBe('function');

    act(() => {
      result.current({
        category: 'system',
        severity: 'info',
        title: 'Test',
        message: 'Test message',
      });
    });

    // Verify it worked by checking toast was called
    expect(mockToast.info).toHaveBeenCalled();
  });
});
