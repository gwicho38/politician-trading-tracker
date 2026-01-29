import { useState, useEffect } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { logError } from '@/lib/logger';

export const useAdmin = () => {
  const [isAdmin, setIsAdmin] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const checkAdmin = async () => {
      try {
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();

        if (sessionError) {
          logError('Session fetch error', 'admin', undefined, { error: sessionError.message });
          setIsAdmin(false);
          return;
        }

        if (!session?.user) {
          setIsAdmin(false);
          return;
        }

        const { data, error } = await supabase.rpc('has_role', {
          _user_id: session.user.id,
          _role: 'admin'
        });

        if (error) {
          logError('Error checking admin status', 'admin', undefined, { error: error.message });
          setIsAdmin(false);
        } else {
          setIsAdmin(!!data);
        }
      } catch (error) {
        logError('Failed to check admin status', 'admin', error instanceof Error ? error : undefined);
        // Clear corrupted session directly from localStorage
        try {
          Object.keys(localStorage).filter(k => k.startsWith('sb-')).forEach(k => localStorage.removeItem(k));
        } catch {}
        setIsAdmin(false);
      } finally {
        setIsLoading(false);
      }
    };

    checkAdmin();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(() => {
      checkAdmin();
    });

    return () => subscription.unsubscribe();
  }, []);

  return { isAdmin, isLoading };
};
