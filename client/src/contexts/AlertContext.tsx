/**
 * AlertContext
 * Centralized alert system for monitoring and displaying failure notifications
 * Tracks connection health, order failures, and system errors
 */

import React, { createContext, useContext, useCallback, useEffect, useState, useRef } from 'react';
import { toast } from 'sonner';
import { supabase } from '@/integrations/supabase/client';
import { useQueryClient } from '@tanstack/react-query';

export type AlertSeverity = 'info' | 'warning' | 'error' | 'success';
export type AlertCategory = 'connection' | 'order' | 'signal' | 'cart' | 'auth' | 'system';

export interface Alert {
  id: string;
  category: AlertCategory;
  severity: AlertSeverity;
  title: string;
  message: string;
  timestamp: Date;
  dismissed: boolean;
  data?: any;
}

interface AlertContextValue {
  alerts: Alert[];
  addAlert: (alert: Omit<Alert, 'id' | 'timestamp' | 'dismissed'>) => void;
  dismissAlert: (id: string) => void;
  dismissAllAlerts: () => void;
  getAlertsByCategory: (category: AlertCategory) => Alert[];
  getUndismissedCount: () => number;
  connectionHealth: 'healthy' | 'degraded' | 'error' | 'unknown';
  lastConnectionCheck: Date | null;
}

const AlertContext = createContext<AlertContextValue | null>(null);

// Max alerts to keep in memory
const MAX_ALERTS = 50;

// Alert deduplication window (ms)
const DEDUP_WINDOW = 5000;

export function AlertProvider({ children }: { children: React.ReactNode }) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [connectionHealth, setConnectionHealth] = useState<'healthy' | 'degraded' | 'error' | 'unknown'>('unknown');
  const [lastConnectionCheck, setLastConnectionCheck] = useState<Date | null>(null);
  const recentAlertsRef = useRef<Map<string, number>>(new Map());
  const queryClient = useQueryClient();

  // Add a new alert
  const addAlert = useCallback((alertData: Omit<Alert, 'id' | 'timestamp' | 'dismissed'>) => {
    const alertKey = `${alertData.category}-${alertData.title}`;
    const now = Date.now();

    // Deduplicate alerts within window
    const lastAlertTime = recentAlertsRef.current.get(alertKey);
    if (lastAlertTime && now - lastAlertTime < DEDUP_WINDOW) {
      return; // Skip duplicate
    }
    recentAlertsRef.current.set(alertKey, now);

    const newAlert: Alert = {
      ...alertData,
      id: crypto.randomUUID(),
      timestamp: new Date(),
      dismissed: false,
    };

    setAlerts((prev) => {
      const updated = [newAlert, ...prev].slice(0, MAX_ALERTS);
      return updated;
    });

    // Show toast notification based on severity
    switch (alertData.severity) {
      case 'error':
        toast.error(alertData.title, {
          description: alertData.message,
          duration: 8000,
        });
        break;
      case 'warning':
        toast.warning(alertData.title, {
          description: alertData.message,
          duration: 6000,
        });
        break;
      case 'success':
        toast.success(alertData.title, {
          description: alertData.message,
          duration: 4000,
        });
        break;
      case 'info':
      default:
        toast.info(alertData.title, {
          description: alertData.message,
          duration: 5000,
        });
        break;
    }
  }, []);

  // Dismiss an alert
  const dismissAlert = useCallback((id: string) => {
    setAlerts((prev) =>
      prev.map((alert) =>
        alert.id === id ? { ...alert, dismissed: true } : alert
      )
    );
  }, []);

  // Dismiss all alerts
  const dismissAllAlerts = useCallback(() => {
    setAlerts((prev) => prev.map((alert) => ({ ...alert, dismissed: true })));
  }, []);

  // Get alerts by category
  const getAlertsByCategory = useCallback(
    (category: AlertCategory) => alerts.filter((alert) => alert.category === category),
    [alerts]
  );

  // Get count of undismissed alerts
  const getUndismissedCount = useCallback(
    () => alerts.filter((alert) => !alert.dismissed).length,
    [alerts]
  );

  // Monitor React Query for failures
  useEffect(() => {
    const unsubscribe = queryClient.getQueryCache().subscribe((event) => {
      if (event?.type === 'updated' && event?.query?.state?.status === 'error') {
        const error = event.query.state.error as Error;
        const queryKey = event.query.queryKey;

        // Categorize the error based on query key
        let category: AlertCategory = 'system';
        if (Array.isArray(queryKey)) {
          const keyStr = String(queryKey[0]);
          if (keyStr.includes('alpaca') || keyStr.includes('connection')) {
            category = 'connection';
          } else if (keyStr.includes('order')) {
            category = 'order';
          } else if (keyStr.includes('signal')) {
            category = 'signal';
          } else if (keyStr.includes('cart')) {
            category = 'cart';
          }
        }

        addAlert({
          category,
          severity: 'error',
          title: 'Request Failed',
          message: error?.message || 'An unexpected error occurred',
          data: { queryKey },
        });
      }
    });

    return () => {
      unsubscribe();
    };
  }, [queryClient, addAlert]);

  // Monitor auth state for failures
  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_OUT') {
        addAlert({
          category: 'auth',
          severity: 'info',
          title: 'Signed Out',
          message: 'You have been signed out',
        });
      } else if (event === 'TOKEN_REFRESHED') {
        // Session refreshed successfully - no alert needed
        console.log('[AlertContext] Token refreshed');
      } else if (event === 'USER_UPDATED') {
        addAlert({
          category: 'auth',
          severity: 'success',
          title: 'Account Updated',
          message: 'Your account has been updated',
        });
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [addAlert]);

  // Periodic connection health check
  useEffect(() => {
    const checkConnectionHealth = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session) {
          setConnectionHealth('unknown');
          return;
        }

        const response = await fetch(
          `${import.meta.env.VITE_SUPABASE_URL}/functions/v1/alpaca-account`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${session.access_token}`,
            },
            body: JSON.stringify({
              action: 'connection-status',
              tradingMode: 'paper',
            }),
          }
        );

        if (!response.ok) {
          setConnectionHealth('error');
          addAlert({
            category: 'connection',
            severity: 'error',
            title: 'Connection Check Failed',
            message: 'Unable to verify Alpaca connection status',
          });
          return;
        }

        const data = await response.json();
        setConnectionHealth(data.status || 'unknown');
        setLastConnectionCheck(new Date());

        // Alert if degraded or disconnected
        if (data.status === 'degraded') {
          addAlert({
            category: 'connection',
            severity: 'warning',
            title: 'Connection Degraded',
            message: 'Alpaca API connection is experiencing issues',
          });
        } else if (data.status === 'disconnected') {
          addAlert({
            category: 'connection',
            severity: 'error',
            title: 'Connection Lost',
            message: 'Alpaca API connection has been lost',
          });
        }

        // Alert if circuit breaker is open
        if (data.circuitBreaker?.state === 'open') {
          addAlert({
            category: 'connection',
            severity: 'error',
            title: 'Circuit Breaker Open',
            message: 'Trading API temporarily blocked due to repeated failures',
          });
        }
      } catch (error) {
        setConnectionHealth('error');
        console.error('[AlertContext] Connection check failed:', error);
      }
    };

    // Initial check after a short delay
    const initialTimeout = setTimeout(checkConnectionHealth, 5000);

    // Periodic check every 5 minutes
    const interval = setInterval(checkConnectionHealth, 5 * 60 * 1000);

    return () => {
      clearTimeout(initialTimeout);
      clearInterval(interval);
    };
  }, [addAlert]);

  // Clean up old dedup entries periodically
  useEffect(() => {
    const cleanup = setInterval(() => {
      const now = Date.now();
      recentAlertsRef.current.forEach((time, key) => {
        if (now - time > DEDUP_WINDOW * 2) {
          recentAlertsRef.current.delete(key);
        }
      });
    }, DEDUP_WINDOW * 2);

    return () => clearInterval(cleanup);
  }, []);

  const value: AlertContextValue = {
    alerts,
    addAlert,
    dismissAlert,
    dismissAllAlerts,
    getAlertsByCategory,
    getUndismissedCount,
    connectionHealth,
    lastConnectionCheck,
  };

  return <AlertContext.Provider value={value}>{children}</AlertContext.Provider>;
}

// Hook
export function useAlerts() {
  const context = useContext(AlertContext);
  if (!context) {
    throw new Error('useAlerts must be used within an AlertProvider');
  }
  return context;
}

// Helper hook for adding alerts easily
export function useAddAlert() {
  const { addAlert } = useAlerts();
  return addAlert;
}

export default AlertContext;
