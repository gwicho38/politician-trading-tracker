import { useState, useEffect, createContext, useContext, ReactNode } from 'react';
import { User } from '@supabase/supabase-js';
import { supabase } from '@/integrations/supabase/client';
import { logDebug } from '@/lib/logger';

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

// Auth state interface
interface AuthState {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  authReady: boolean;
}

// Create context with default values
const AuthContext = createContext<AuthState>({
  user: null,
  loading: true,
  isAuthenticated: false,
  authReady: false,
});

// Provider component
export function AuthProvider({ children }: { children: ReactNode }) {
  // Initialize from localStorage immediately (sync, no loading)
  const storedUser = getStoredUser();
  const [user, setUser] = useState<User | null>(storedUser);
  const [loading, setLoading] = useState(!storedUser);
  // Track when auth listener has fired (auth client is ready for queries)
  const [authReady, setAuthReady] = useState(false);

  useEffect(() => {
    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        logDebug('Auth state changed', 'auth', { event, userId: session?.user?.id });
        setUser(session?.user ?? null);
        setLoading(false);
        setAuthReady(true);
      }
    );

    // Fallback: if auth listener doesn't fire within 2s, mark as ready anyway
    // Must also clear loading — otherwise ProtectedRoute spinner hangs forever
    const timeout = setTimeout(() => {
      setAuthReady(true);
      setLoading(false);
    }, 2000);

    return () => {
      subscription.unsubscribe();
      clearTimeout(timeout);
    };
  }, []);

  const value: AuthState = {
    user,
    loading,
    isAuthenticated: !!user,
    authReady,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// Hook to consume auth state
export const useAuth = () => {
  return useContext(AuthContext);
};

// Backwards compatibility export
export const useAuthReady = () => {
  const { authReady } = useAuth();
  return authReady;
};
