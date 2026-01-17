/**
 * useSignalPlayground Hook
 * Main state management for the signal generation playground
 */

import { useState, useCallback, useMemo, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useDebounce } from './useDebounce';
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
 * Fetch preview signals from the edge function using direct fetch
 */
async function fetchPreviewSignals(
  weights: SignalWeights,
  lookbackDays: number = 90,
  useML: boolean = false,
  userLambda?: string
): Promise<PreviewResponse> {
  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
  const anonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

  const response = await fetch(`${supabaseUrl}/functions/v1/trading-signals/preview-signals`, {
    method: 'POST',
    headers: {
      'apikey': anonKey,
      'Authorization': `Bearer ${anonKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      weights,
      lookbackDays,
      useML,
      userLambda: userLambda?.trim() || undefined,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || 'Failed to fetch preview signals');
  }

  return response.json();
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

  // User lambda state
  const [userLambda, setUserLambda] = useState('');

  // Debounce weights for API calls
  const debouncedWeights = useDebounce(weights, DEBOUNCE_DELAY);
  const debouncedLookback = useDebounce(lookbackDays, DEBOUNCE_DELAY);
  const debouncedLambda = useDebounce(userLambda, DEBOUNCE_DELAY);

  // Track if we're in the debounce period (showing "Updating...")
  const [isDebouncing, setIsDebouncing] = useState(false);

  // When weights change, set debouncing to true
  useEffect(() => {
    setIsDebouncing(true);
    const timer = setTimeout(() => setIsDebouncing(false), DEBOUNCE_DELAY);
    return () => clearTimeout(timer);
  }, [weights, lookbackDays, userLambda]);

  // Check if we have a non-empty lambda to apply
  const hasActiveLambda = !!debouncedLambda?.trim();

  // Fetch base signals (without lambda) for comparison - only when lambda is active
  const {
    data: baseSignalsData,
    isLoading: isLoadingBase,
  } = useQuery({
    queryKey: ['signalPreviewBase', debouncedWeights, debouncedLookback],
    queryFn: () => fetchPreviewSignals(debouncedWeights, debouncedLookback, mlEnabled, undefined),
    staleTime: 60 * 1000, // 1 minute - base signals don't change often
    refetchOnWindowFocus: false,
    enabled: hasActiveLambda, // Only fetch when lambda is active
  });

  // Fetch preview signals with debounced weights (ML always enabled)
  const {
    data: previewData,
    isLoading,
    isFetching,
    error,
    refetch,
  } = useQuery({
    queryKey: ['signalPreview', debouncedWeights, debouncedLookback, debouncedLambda],
    queryFn: () => fetchPreviewSignals(debouncedWeights, debouncedLookback, mlEnabled, debouncedLambda),
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

  // Load weights (and optionally lambda) from a preset
  const loadPreset = useCallback((preset: SignalPreset) => {
    setWeights(presetToWeights(preset));
    // Also load user_lambda if the preset includes it
    if (preset.user_lambda) {
      setUserLambda(preset.user_lambda);
    }
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
  const baseSignals: PreviewSignal[] = baseSignalsData?.signals || [];
  const stats = previewData?.stats;
  // mlEnhancedCount comes from stats in the edge function response
  const mlEnhancedCount = previewData?.stats?.mlEnhancedCount || 0;

  // Lambda status from response
  const lambdaApplied = previewData?.lambdaApplied || false;
  const lambdaError = previewData?.lambdaError || null;
  const lambdaTrace = previewData?.lambdaTrace || null;

  // Compute comparison data when lambda is applied
  const comparisonData = useMemo(() => {
    if (!lambdaApplied || !baseSignals.length || !signals.length) {
      return null;
    }

    // Create lookup map for after signals
    const afterMap = new Map(signals.map((s) => [s.ticker, s]));

    const comparisons = baseSignals.map((before) => {
      const after = afterMap.get(before.ticker);
      if (!after) return null;

      const typeChanged = before.signal_type !== after.signal_type;
      const confidenceDelta = after.confidence_score - before.confidence_score;

      // Determine if the change is an improvement
      const signalTypeRank: Record<string, number> = {
        strong_sell: -2,
        sell: -1,
        hold: 0,
        buy: 1,
        strong_buy: 2,
      };

      const beforeRank = signalTypeRank[before.signal_type] || 0;
      const afterRank = signalTypeRank[after.signal_type] || 0;
      const typeImproved = afterRank > beforeRank;
      const typeDegraded = afterRank < beforeRank;

      return {
        ticker: before.ticker,
        before: {
          signal_type: before.signal_type,
          confidence_score: before.confidence_score,
        },
        after: {
          signal_type: after.signal_type,
          confidence_score: after.confidence_score,
        },
        changes: {
          typeChanged,
          confidenceDelta,
          typeImproved,
          typeDegraded,
        },
      };
    }).filter(Boolean);

    // Calculate summary stats
    const modified = comparisons.filter(
      (c) => c && (c.changes.typeChanged || Math.abs(c.changes.confidenceDelta) > 0.01)
    );
    const improved = comparisons.filter(
      (c) => c && (c.changes.typeImproved || c.changes.confidenceDelta > 0.01)
    );
    const degraded = comparisons.filter(
      (c) => c && (c.changes.typeDegraded || c.changes.confidenceDelta < -0.01)
    );
    const avgConfidenceDelta = modified.length > 0
      ? modified.reduce((sum, c) => sum + (c?.changes.confidenceDelta || 0), 0) / modified.length
      : 0;

    return {
      comparisons: comparisons as Array<{
        ticker: string;
        before: { signal_type: string; confidence_score: number };
        after: { signal_type: string; confidence_score: number };
        changes: { typeChanged: boolean; confidenceDelta: number; typeImproved: boolean; typeDegraded: boolean };
      }>,
      stats: {
        totalSignals: comparisons.length,
        modifiedCount: modified.length,
        improvedCount: improved.length,
        degradedCount: degraded.length,
        avgConfidenceDelta,
      },
    };
  }, [lambdaApplied, baseSignals, signals]);

  // Apply lambda manually (triggers refetch)
  const applyLambda = useCallback(() => {
    // Just trigger a refetch - the lambda is already in the query
    refetch();
  }, [refetch]);

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

    // User lambda
    userLambda,
    setUserLambda,
    lambdaApplied,
    lambdaError,
    lambdaTrace,
    applyLambda,
    comparisonData,
    isLoadingComparison: isLoadingBase,

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
