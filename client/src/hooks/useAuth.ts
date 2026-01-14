import { useState, useEffect } from 'react';
import { User } from '@supabase/supabase-js';
import { supabase } from '@/integrations/supabase/client';

// Get user from localStorage synchronously (for instant hydration)
function getStoredUser(): User | null {
  try {
    const keys = Object.keys(localStorage).filter(k => k.startsWith('sb-') && k.endsWith('-auth-token'));
    if (keys.length === 0) return null;
    const sessionData = localStorage.getItem(keys[0]);
    if (!sessionData) return null;
    const parsed = JSON.parse(sessionData);
    // Check if not expired
    if (parsed?.user && parsed?.expires_at * 1000 > Date.now()) {
      return parsed.user;
    }
    return null;
  } catch {
    return null;
  }
}

export const useAuth = () => {
  // Initialize from localStorage immediately (sync, no loading)
  const storedUser = getStoredUser();
  const [user, setUser] = useState<User | null>(storedUser);
  const [loading, setLoading] = useState(!storedUser);

  useEffect(() => {
    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        console.log('[useAuth] Auth state changed:', event);
        setUser(session?.user ?? null);
        setLoading(false);
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  return {
    user,
    loading,
    isAuthenticated: !!user,
  };
};

// Backwards compatibility export
export const useAuthReady = () => true;
