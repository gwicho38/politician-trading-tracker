import { useState, useEffect, useRef } from 'react';
import { User, Session } from '@supabase/supabase-js';
import { supabase } from '@/integrations/supabase/client';

// Get stored session from localStorage without triggering a refresh
function getStoredSession(): { user: User; session: Session } | null {
  try {
    const keys = Object.keys(localStorage).filter(k => k.startsWith('sb-') && k.endsWith('-auth-token'));
    if (keys.length === 0) return null;

    const sessionData = localStorage.getItem(keys[0]);
    if (!sessionData) return null;

    const parsed = JSON.parse(sessionData);

    // Check if session is expired
    const expiresAt = parsed?.expires_at;
    if (expiresAt && expiresAt * 1000 < Date.now()) {
      console.log('[useAuth] Stored session is expired');
      return null;
    }

    // Return user from stored session
    if (parsed?.user) {
      return { user: parsed.user, session: parsed };
    }
    return null;
  } catch (e) {
    console.error('[useAuth] Error reading stored session:', e);
    return null;
  }
}

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const initializedRef = useRef(false);

  useEffect(() => {
    // Prevent double initialization in React strict mode
    if (initializedRef.current) return;
    initializedRef.current = true;

    let mounted = true;

    // Step 1: Immediately check localStorage for existing session (non-blocking)
    const storedSession = getStoredSession();
    if (storedSession?.user) {
      console.log('[useAuth] Found valid stored session, setting user immediately');
      setUser(storedSession.user);
      setLoading(false);
    }

    // Step 2: Set up auth state change listener (primary mechanism)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        if (!mounted) return;
        console.log('[useAuth] Auth state changed:', event);
        setUser(session?.user ?? null);
        setLoading(false);
      }
    );

    // Step 3: Trigger Supabase to check/refresh session in background (don't await)
    // This will fire onAuthStateChange when complete
    supabase.auth.getSession()
      .then(({ data: { session }, error }) => {
        if (!mounted) return;
        if (error) {
          console.error('[useAuth] Background session check error:', error.message);
        }
        // Update user if different from stored (handles token refresh)
        if (session?.user?.id !== user?.id) {
          setUser(session?.user ?? null);
        }
        setLoading(false);
      })
      .catch((error) => {
        if (!mounted) return;
        console.error('[useAuth] Background session check failed:', error);
        // Don't clear user - keep using stored session if we have one
        setLoading(false);
      });

    // Step 4: Fallback timeout - ensure loading eventually stops
    const fallbackTimeout = setTimeout(() => {
      if (mounted && loading) {
        console.log('[useAuth] Fallback timeout - stopping loading state');
        setLoading(false);
      }
    }, 3000);

    return () => {
      mounted = false;
      subscription.unsubscribe();
      clearTimeout(fallbackTimeout);
    };
  }, []);

  return {
    user,
    loading,
    isAuthenticated: !!user,
  };
};
