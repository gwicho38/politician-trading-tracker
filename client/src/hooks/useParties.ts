import { useQuery } from '@tanstack/react-query';
import { supabasePublic as supabase } from '@/integrations/supabase/client';

export interface PartyRecord {
  id: string;
  code: string;
  name: string;
  short_name: string | null;
  jurisdiction: string;
  color: string;
}

export const useParties = () => {
  return useQuery<PartyRecord[]>({
    queryKey: ['parties'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('parties')
        .select('*')
        .order('jurisdiction')
        .order('name');
      if (error) throw error;
      return data || [];
    },
    staleTime: 30 * 60 * 1000, // 30 min cache
  });
};
