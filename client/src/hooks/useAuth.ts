import { useState, useEffect } from 'react';
import { User } from '@supabase/supabase-js';
import { supabase } from '@/integrations/supabase/client';

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Get initial session with timeout to prevent infinite loading
    const getInitialSession = async () => {
      try {
        // Add timeout to prevent hanging on slow/failed auth requests
        const timeoutPromise = new Promise<null>((_, reject) => {
          setTimeout(() => reject(new Error('Session fetch timeout')), 5000);
        });

        const sessionPromise = supabase.auth.getSession();
        const result = await Promise.race([sessionPromise, timeoutPromise]);

        if (result && 'data' in result) {
          const { data: { session }, error } = result;
          if (error) {
            console.error('[useAuth] Session fetch error:', error.message);
          }
          setUser(session?.user ?? null);
        } else {
          setUser(null);
        }
      } catch (error) {
        console.error('[useAuth] Failed to get session:', error);
        // Clear corrupted session directly from localStorage to prevent repeated timeouts
        // This is more reliable than signOut which may also hang
        try {
          const keys = Object.keys(localStorage).filter(k => k.startsWith('sb-'));
          keys.forEach(k => localStorage.removeItem(k));
          if (keys.length > 0) {
            console.log('[useAuth] Cleared stale Supabase session from localStorage:', keys);
          }
        } catch (clearError) {
          console.error('[useAuth] Failed to clear localStorage:', clearError);
        }
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    getInitialSession();

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
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