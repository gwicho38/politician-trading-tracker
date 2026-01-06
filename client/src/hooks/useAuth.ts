import { useState, useEffect } from 'react';
import { User } from '@supabase/supabase-js';
import { supabase } from '@/integrations/supabase/client';

// Check if stored session looks stale (older than 7 days since last activity)
function hasStaleSession(): boolean {
  try {
    const keys = Object.keys(localStorage).filter(k => k.startsWith('sb-') && k.endsWith('-auth-token'));
    if (keys.length === 0) return false;

    const sessionData = localStorage.getItem(keys[0]);
    if (!sessionData) return false;

    const parsed = JSON.parse(sessionData);
    const expiresAt = parsed?.expires_at;
    if (expiresAt && expiresAt * 1000 < Date.now()) {
      console.log('[useAuth] Found expired session, clearing...');
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

// Clear all Supabase session data from localStorage
function clearSupabaseSession(): void {
  try {
    const keys = Object.keys(localStorage).filter(k => k.startsWith('sb-'));
    keys.forEach(k => localStorage.removeItem(k));
    if (keys.length > 0) {
      console.log('[useAuth] Cleared Supabase session keys:', keys);
    }
  } catch (e) {
    console.error('[useAuth] Failed to clear localStorage:', e);
  }
}

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Get initial session with timeout to prevent infinite loading
    const getInitialSession = async () => {
      // Pre-check: if session is expired, clear it before getSession() tries to refresh
      if (hasStaleSession()) {
        clearSupabaseSession();
        setUser(null);
        setLoading(false);
        return;
      }

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
        clearSupabaseSession();
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