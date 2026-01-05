import { useState, useEffect } from 'react';
import { supabase } from '@/integrations/supabase/client';

export const useAdmin = () => {
  const [isAdmin, setIsAdmin] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const checkAdmin = async () => {
      try {
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();

        if (sessionError) {
          console.error('[useAdmin] Session fetch error:', sessionError.message);
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
          console.error('[useAdmin] Error checking admin status:', error);
          setIsAdmin(false);
        } else {
          setIsAdmin(!!data);
        }
      } catch (error) {
        console.error('[useAdmin] Failed to check admin status:', error);
        // Clear potentially corrupted session
        try {
          await supabase.auth.signOut({ scope: 'local' });
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
