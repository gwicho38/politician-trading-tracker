/**
 * useSignalPlayground Hook
 * Main state management for the signal generation playground
 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useDebounce } from './useDebounce';
import { supabase } from '@/integrations/supabase/client';
import {
  DEFAULT_WEIGHTS,
  presetToWeights,
} from '@/lib/signal-weights';
import type {
  SignalWeights,
  SignalPreset,
  PreviewResponse,
  PreviewSignal,
} from '@/types/signal-playground';

const DEBOUNCE_DELAY = 500; // ms

/**
 * Fetch preview signals from the edge function
 */
async function fetchPreviewSignals(
  weights: SignalWeights,
  lookbackDays: number = 90,
  useML: boolean = false
): Promise<PreviewResponse> {
  // Use path-based routing: trading-signals/preview-signals
  const { data, error } = await supabase.functions.invoke('trading-signals/preview-signals', {
    body: {
      weights,
      lookbackDays,
      useML,
    },
  });

  if (error) {
    throw new Error(error.message || 'Failed to fetch preview signals');
  }

  return data as PreviewResponse;
}

interface UseSignalPlaygroundOptions {
  initialWeights?: Partial<SignalWeights>;
  lookbackDays?: number;
}

export function useSignalPlayground(options: UseSignalPlaygroundOptions = {}) {
  const {
    initialWeights,
    lookbackDays: initialLookback = 90,
  } = options;

  // ML is always enabled - falls back to heuristic-only if no model available
  const mlEnabled = true;

  // Weight state - spread defaults with any initial overrides
  const [weights, setWeights] = useState<SignalWeights>({
    ...DEFAULT_WEIGHTS,
    ...initialWeights,
  });

  // Lookback period state
  const [lookbackDays, setLookbackDays] = useState(initialLookback);

  // Debounce weights for API calls
  const debouncedWeights = useDebounce(weights, DEBOUNCE_DELAY);
  const debouncedLookback = useDebounce(lookbackDays, DEBOUNCE_DELAY);

  // Track if we're in the debounce period (showing "Updating...")
  const [isDebouncing, setIsDebouncing] = useState(false);

  // When weights change, set debouncing to true
  useEffect(() => {
    setIsDebouncing(true);
    const timer = setTimeout(() => setIsDebouncing(false), DEBOUNCE_DELAY);
    return () => clearTimeout(timer);
  }, [weights, lookbackDays]);

  // Fetch preview signals with debounced weights (ML always enabled)
  const {
    data: previewData,
    isLoading,
    isFetching,
    error,
    refetch,
  } = useQuery({
    queryKey: ['signalPreview', debouncedWeights, debouncedLookback],
    queryFn: () => fetchPreviewSignals(debouncedWeights, debouncedLookback, mlEnabled),
    staleTime: 30 * 1000, // 30 seconds
    refetchOnWindowFocus: false,
  });

  // Update a single weight
  const updateWeight = useCallback(
    <K extends keyof SignalWeights>(key: K, value: SignalWeights[K]) => {
      setWeights((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  // Update multiple weights at once
  const updateWeights = useCallback((updates: Partial<SignalWeights>) => {
    setWeights((prev) => ({ ...prev, ...updates }));
  }, []);

  // Reset to default weights
  const resetToDefaults = useCallback(() => {
    setWeights(DEFAULT_WEIGHTS);
  }, []);

  // Load weights from a preset
  const loadPreset = useCallback((preset: SignalPreset) => {
    setWeights(presetToWeights(preset));
  }, []);

  // Check if current weights differ from defaults
  const hasChanges = useMemo(() => {
    return Object.keys(DEFAULT_WEIGHTS).some(
      (key) =>
        weights[key as keyof SignalWeights] !==
        DEFAULT_WEIGHTS[key as keyof SignalWeights]
    );
  }, [weights]);

  // Count modified fields
  const modifiedCount = useMemo(() => {
    return Object.keys(DEFAULT_WEIGHTS).filter(
      (key) =>
        weights[key as keyof SignalWeights] !==
        DEFAULT_WEIGHTS[key as keyof SignalWeights]
    ).length;
  }, [weights]);

  // Extract signals from response
  const signals: PreviewSignal[] = previewData?.signals || [];
  const stats = previewData?.stats;
  // mlEnhancedCount comes from stats in the edge function response
  const mlEnhancedCount = previewData?.stats?.mlEnhancedCount || 0;

  return {
    // Weight state
    weights,
    updateWeight,
    updateWeights,
    resetToDefaults,
    loadPreset,
    hasChanges,
    modifiedCount,

    // Lookback period
    lookbackDays,
    setLookbackDays,

    // ML enhancement (always enabled, falls back gracefully)
    mlEnabled,
    mlEnhancedCount,

    // Preview data
    signals,
    stats,
    previewData,

    // Loading states
    isLoading,
    isFetching,
    isDebouncing,
    isUpdating: isDebouncing || isFetching,

    // Error handling
    error,
    refetch,
  };
}

export default useSignalPlayground;
