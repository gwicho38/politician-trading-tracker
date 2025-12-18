export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.1"
  }
  public: {
    Tables: {
      chart_data: {
        Row: {
          buys: number
          created_at: string
          id: string
          month: string
          sells: number
          volume: number
          year: number
        }
        Insert: {
          buys?: number
          created_at?: string
          id?: string
          month: string
          sells?: number
          volume?: number
          year: number
        }
        Update: {
          buys?: number
          created_at?: string
          id?: string
          month?: string
          sells?: number
          volume?: number
          year?: number
         }
         Relationships: []
       }
       positions: {
         Row: {
           asset_name: string
           avg_entry_price: number
           closed_at: string | null
           created_at: string
           current_price: number
           id: string
           is_open: boolean
           market_value: number
           metadata: Json | null
           opened_at: string
           order_ids: string[] | null
           portfolio_id: string | null
           quantity: number
           realized_pl: number | null
           realized_pl_pct: number | null
           side: string
           signal_ids: string[] | null
           stop_loss: number | null
           take_profit: number | null
           ticker: string
           total_cost: number
           unrealized_pl: number
           unrealized_pl_pct: number
           updated_at: string
         }
         Insert: {
           asset_name: string
           avg_entry_price?: number
           closed_at?: string | null
           created_at?: string
           current_price?: number
           id?: string
           is_open?: boolean
           market_value?: number
           metadata?: Json | null
           opened_at?: string
           order_ids?: string[] | null
           portfolio_id?: string | null
           quantity?: number
           realized_pl?: number | null
           realized_pl_pct?: number | null
           side: string
           signal_ids?: string[] | null
           stop_loss?: number | null
           take_profit?: number | null
           ticker: string
           total_cost?: number
           unrealized_pl?: number
           unrealized_pl_pct?: number
           updated_at?: string
         }
         Update: {
           asset_name?: string
           avg_entry_price?: number
           closed_at?: string | null
           created_at?: string
           current_price?: number
           id?: string
           is_open?: boolean
           market_value?: number
           metadata?: Json | null
           opened_at?: string
           order_ids?: string[] | null
           portfolio_id?: string | null
           quantity?: number
           realized_pl?: number | null
           realized_pl_pct?: number | null
           side?: string
           signal_ids?: string[] | null
           stop_loss?: number | null
           take_profit?: number | null
           ticker?: string
           total_cost?: number
           unrealized_pl?: number
           unrealized_pl_pct?: number
           updated_at?: string
         }
         Relationships: [
           {
             foreignKeyName: "positions_portfolio_id_fkey"
             columns: ["portfolio_id"]
             isOneToOne: false
             referencedRelation: "portfolios"
             referencedColumns: ["id"]
           },
         ]
       }
       wallet_nonces: {
         Row: {
           created_at: string
           expires_at: string
           id: string
           nonce: string
           wallet_address: string
         }
         Insert: {
           created_at?: string
           expires_at?: string
           id?: string
           nonce: string
           wallet_address: string
         }
         Update: {
           created_at?: string
           expires_at?: string
           id?: string
           nonce?: string
           wallet_address?: string
         }
         Relationships: []
       }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      get_user_role: {
        Args: { _user_id: string }
        Returns: Database["public"]["Enums"]["app_role"]
      }
      has_role: {
        Args: {
          _role: Database["public"]["Enums"]["app_role"]
          _user_id: string
        }
        Returns: boolean
      }
      search_documents: {
        Args: {
          match_count?: number
          match_threshold?: number
          p_user_id?: string
          query_embedding: string
        }
        Returns: {
          content: string
          document_id: string
          id: string
          similarity: number
        }[]
      }
    }
    Enums: {
      app_role: "admin" | "moderator" | "user"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      app_role: ["admin", "moderator", "user"],
    },
  },
} as const
