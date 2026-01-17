/**
 * useSignalPresets Hook
 * Manages CRUD operations for saved signal weight presets
 * Uses direct fetch for mutations to avoid Supabase client hanging issues
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabasePublic } from '@/integrations/supabase/client';
import { weightsToPresetFields } from '@/lib/signal-weights';
import type { SignalPreset, SignalWeights } from '@/types/signal-playground';

const PRESETS_QUERY_KEY = ['signalPresets'];

/**
 * Get access token from localStorage
 */
function getAccessToken(): string | null {
  try {
    const keys = Object.keys(localStorage).filter(k => k.startsWith('sb-') && k.endsWith('-auth-token'));
    if (keys.length === 0) return null;
    const sessionData = localStorage.getItem(keys[0]);
    if (!sessionData) return null;
    const parsed = JSON.parse(sessionData);
    return parsed?.access_token || null;
  } catch {
    return null;
  }
}

/**
 * Get current user ID from localStorage
 */
function getUserId(): string | null {
  try {
    const keys = Object.keys(localStorage).filter(k => k.startsWith('sb-') && k.endsWith('-auth-token'));
    if (keys.length === 0) return null;
    const sessionData = localStorage.getItem(keys[0]);
    if (!sessionData) return null;
    const parsed = JSON.parse(sessionData);
    return parsed?.user?.id || null;
  } catch {
    return null;
  }
}

/**
 * Fetch all presets (user's own + public)
 */
async function fetchPresets(): Promise<SignalPreset[]> {
  const userId = getUserId();

  // Build query - get user's own presets and all public presets
  let query = supabasePublic
    .from('signal_weight_presets')
    .select('*')
    .order('created_at', { ascending: false });

  // If user is logged in, get their presets + public
  // If not logged in, only get public presets
  if (userId) {
    query = query.or(`user_id.eq.${userId},is_public.eq.true`);
  } else {
    query = query.eq('is_public', true);
  }

  const { data, error } = await query;

  if (error) {
    throw new Error(error.message || 'Failed to fetch presets');
  }

  return (data || []) as SignalPreset[];
}

/**
 * Create a new preset using direct fetch to avoid Supabase client hanging
 */
async function createPreset(input: {
  name: string;
  description?: string;
  is_public?: boolean;
  weights: SignalWeights;
  user_lambda?: string;
}): Promise<SignalPreset> {
  console.log('[createPreset] Starting...');

  const userId = getUserId();
  const accessToken = getAccessToken();

  if (!userId || !accessToken) {
    throw new Error('Must be logged in to save presets');
  }

  const presetFields = weightsToPresetFields(input.weights);
  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
  const anonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

  const body = {
    user_id: userId,
    name: input.name,
    description: input.description || null,
    is_public: input.is_public || false,
    user_lambda: input.user_lambda || null,
    ...presetFields,
  };

  console.log('[createPreset] Making fetch request...');

  const response = await fetch(`${supabaseUrl}/rest/v1/signal_weight_presets`, {
    method: 'POST',
    headers: {
      'apikey': anonKey,
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
      'Prefer': 'return=representation',
    },
    body: JSON.stringify(body),
  });

  console.log('[createPreset] Response status:', response.status);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    console.error('[createPreset] Error:', errorData);
    throw new Error(errorData.message || `Failed to create preset (${response.status})`);
  }

  const data = await response.json();
  console.log('[createPreset] Success:', data);

  // Response is an array, get the first item
  return Array.isArray(data) ? data[0] : data;
}

/**
 * Update an existing preset using direct fetch
 */
async function updatePreset(input: {
  id: string;
  name?: string;
  description?: string;
  is_public?: boolean;
  weights?: SignalWeights;
  user_lambda?: string | null;
}): Promise<SignalPreset> {
  const accessToken = getAccessToken();
  if (!accessToken) {
    throw new Error('Must be logged in to update presets');
  }

  const updates: Record<string, unknown> = {};

  if (input.name !== undefined) updates.name = input.name;
  if (input.description !== undefined) updates.description = input.description;
  if (input.is_public !== undefined) updates.is_public = input.is_public;
  if (input.user_lambda !== undefined) updates.user_lambda = input.user_lambda;

  if (input.weights) {
    const presetFields = weightsToPresetFields(input.weights);
    Object.assign(updates, presetFields);
  }

  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
  const anonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

  const response = await fetch(
    `${supabaseUrl}/rest/v1/signal_weight_presets?id=eq.${input.id}`,
    {
      method: 'PATCH',
      headers: {
        'apikey': anonKey,
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
        'Prefer': 'return=representation',
      },
      body: JSON.stringify(updates),
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || 'Failed to update preset');
  }

  const data = await response.json();
  return Array.isArray(data) ? data[0] : data;
}

/**
 * Delete a preset using direct fetch
 */
async function deletePreset(id: string): Promise<void> {
  const accessToken = getAccessToken();
  if (!accessToken) {
    throw new Error('Must be logged in to delete presets');
  }

  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
  const anonKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

  const response = await fetch(
    `${supabaseUrl}/rest/v1/signal_weight_presets?id=eq.${id}`,
    {
      method: 'DELETE',
      headers: {
        'apikey': anonKey,
        'Authorization': `Bearer ${accessToken}`,
      },
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.message || 'Failed to delete preset');
  }
}

export function useSignalPresets() {
  const queryClient = useQueryClient();

  // Fetch presets query
  const {
    data: presets = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: PRESETS_QUERY_KEY,
    queryFn: fetchPresets,
    staleTime: 60 * 1000, // 1 minute
  });

  // Create preset mutation
  const createMutation = useMutation({
    mutationFn: createPreset,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PRESETS_QUERY_KEY });
    },
  });

  // Update preset mutation
  const updateMutation = useMutation({
    mutationFn: updatePreset,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PRESETS_QUERY_KEY });
    },
  });

  // Delete preset mutation
  const deleteMutation = useMutation({
    mutationFn: deletePreset,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PRESETS_QUERY_KEY });
    },
  });

  // Separate user presets from system/public presets
  const userPresets = presets.filter((p) => p.user_id !== null);
  const systemPresets = presets.filter((p) => p.user_id === null && p.is_public);

  return {
    // Data
    presets,
    userPresets,
    systemPresets,

    // Loading states
    isLoading,
    error,
    refetch,

    // Mutations
    createPreset: createMutation.mutate,
    createPresetAsync: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    createError: createMutation.error,

    updatePreset: updateMutation.mutate,
    updatePresetAsync: updateMutation.mutateAsync,
    isUpdating: updateMutation.isPending,
    updateError: updateMutation.error,

    deletePreset: deleteMutation.mutate,
    deletePresetAsync: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,
    deleteError: deleteMutation.error,
  };
}

export default useSignalPresets;
