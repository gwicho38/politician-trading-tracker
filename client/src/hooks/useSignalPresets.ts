/**
 * useSignalPresets Hook
 * Manages CRUD operations for saved signal weight presets
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import { weightsToPresetFields } from '@/lib/signal-weights';
import type { SignalPreset, SignalWeights } from '@/types/signal-playground';

const PRESETS_QUERY_KEY = ['signalPresets'];

/**
 * Fetch all presets (user's own + public)
 */
async function fetchPresets(): Promise<SignalPreset[]> {
  const { data: userData } = await supabase.auth.getUser();
  const userId = userData?.user?.id;

  // Build query - get user's own presets and all public presets
  let query = supabase
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
 * Create a new preset
 */
async function createPreset(input: {
  name: string;
  description?: string;
  is_public?: boolean;
  weights: SignalWeights;
}): Promise<SignalPreset> {
  const { data: userData } = await supabase.auth.getUser();
  const userId = userData?.user?.id;

  if (!userId) {
    throw new Error('Must be logged in to save presets');
  }

  const presetFields = weightsToPresetFields(input.weights);

  const { data, error } = await supabase
    .from('signal_weight_presets')
    .insert({
      user_id: userId,
      name: input.name,
      description: input.description || null,
      is_public: input.is_public || false,
      ...presetFields,
    })
    .select()
    .single();

  if (error) {
    throw new Error(error.message || 'Failed to create preset');
  }

  return data as SignalPreset;
}

/**
 * Update an existing preset
 */
async function updatePreset(input: {
  id: string;
  name?: string;
  description?: string;
  is_public?: boolean;
  weights?: SignalWeights;
}): Promise<SignalPreset> {
  const updates: Record<string, unknown> = {};

  if (input.name !== undefined) updates.name = input.name;
  if (input.description !== undefined) updates.description = input.description;
  if (input.is_public !== undefined) updates.is_public = input.is_public;

  if (input.weights) {
    const presetFields = weightsToPresetFields(input.weights);
    Object.assign(updates, presetFields);
  }

  const { data, error } = await supabase
    .from('signal_weight_presets')
    .update(updates)
    .eq('id', input.id)
    .select()
    .single();

  if (error) {
    throw new Error(error.message || 'Failed to update preset');
  }

  return data as SignalPreset;
}

/**
 * Delete a preset
 */
async function deletePreset(id: string): Promise<void> {
  const { error } = await supabase
    .from('signal_weight_presets')
    .delete()
    .eq('id', id);

  if (error) {
    throw new Error(error.message || 'Failed to delete preset');
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
