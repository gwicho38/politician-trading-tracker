Initialising login role...
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
    PostgrestVersion: "13.0.4"
  }
  graphql_public: {
    Tables: {
      [_ in never]: never
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      graphql: {
        Args: {
          extensions?: Json
          operationName?: string
          query?: string
          variables?: Json
        }
        Returns: Json
      }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
  public: {
    Tables: {
      action_logs: {
        Row: {
          action_details: Json | null
          action_name: string | null
          action_timestamp: string
          action_type: string
          completed_at: string | null
          created_at: string
          duration_seconds: number | null
          error_message: string | null
          id: string
          ip_address: string | null
          job_execution_id: string | null
          job_id: string | null
          result_message: string | null
          session_id: string | null
          source: string
          started_at: string | null
          status: string
          updated_at: string
          user_agent: string | null
          user_id: string | null
        }
        Insert: {
          action_details?: Json | null
          action_name?: string | null
          action_timestamp?: string
          action_type: string
          completed_at?: string | null
          created_at?: string
          duration_seconds?: number | null
          error_message?: string | null
          id?: string
          ip_address?: string | null
          job_execution_id?: string | null
          job_id?: string | null
          result_message?: string | null
          session_id?: string | null
          source: string
          started_at?: string | null
          status: string
          updated_at?: string
          user_agent?: string | null
          user_id?: string | null
        }
        Update: {
          action_details?: Json | null
          action_name?: string | null
          action_timestamp?: string
          action_type?: string
          completed_at?: string | null
          created_at?: string
          duration_seconds?: number | null
          error_message?: string | null
          id?: string
          ip_address?: string | null
          job_execution_id?: string | null
          job_id?: string | null
          result_message?: string | null
          session_id?: string | null
          source?: string
          started_at?: string | null
          status?: string
          updated_at?: string
          user_agent?: string | null
          user_id?: string | null
        }
        Relationships: []
      }
      asset_holdings: {
        Row: {
          asset_description: string | null
          asset_name: string
          asset_ticker: string | null
          asset_type: string | null
          comments: string | null
          created_at: string | null
          current_year_income: number | null
          filing_date: string
          filing_doc_id: string | null
          id: string
          income_type: string | null
          owner: string | null
          politician_id: string | null
          preceding_year_income: number | null
          raw_data: Json | null
          updated_at: string | null
          value_category: string | null
          value_high: number | null
          value_low: number | null
        }
        Insert: {
          asset_description?: string | null
          asset_name: string
          asset_ticker?: string | null
          asset_type?: string | null
          comments?: string | null
          created_at?: string | null
          current_year_income?: number | null
          filing_date: string
          filing_doc_id?: string | null
          id?: string
          income_type?: string | null
          owner?: string | null
          politician_id?: string | null
          preceding_year_income?: number | null
          raw_data?: Json | null
          updated_at?: string | null
          value_category?: string | null
          value_high?: number | null
          value_low?: number | null
        }
        Update: {
          asset_description?: string | null
          asset_name?: string
          asset_ticker?: string | null
          asset_type?: string | null
          comments?: string | null
          created_at?: string | null
          current_year_income?: number | null
          filing_date?: string
          filing_doc_id?: string | null
          id?: string
          income_type?: string | null
          owner?: string | null
          politician_id?: string | null
          preceding_year_income?: number | null
          raw_data?: Json | null
          updated_at?: string | null
          value_category?: string | null
          value_high?: number | null
          value_low?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "asset_holdings_politician_id_fkey"
            columns: ["politician_id"]
            isOneToOne: false
            referencedRelation: "politicians"
            referencedColumns: ["id"]
          },
        ]
      }
      capital_gains: {
        Row: {
          asset_name: string
          asset_owner: string | null
          asset_ticker: string | null
          comments: string | null
          created_at: string | null
          date_acquired: string | null
          date_sold: string
          disclosure_id: string | null
          gain_amount: number | null
          gain_type: string | null
          id: string
          politician_id: string | null
          raw_data: Json | null
          updated_at: string | null
        }
        Insert: {
          asset_name: string
          asset_owner?: string | null
          asset_ticker?: string | null
          comments?: string | null
          created_at?: string | null
          date_acquired?: string | null
          date_sold: string
          disclosure_id?: string | null
          gain_amount?: number | null
          gain_type?: string | null
          id?: string
          politician_id?: string | null
          raw_data?: Json | null
          updated_at?: string | null
        }
        Update: {
          asset_name?: string
          asset_owner?: string | null
          asset_ticker?: string | null
          comments?: string | null
          created_at?: string | null
          date_acquired?: string | null
          date_sold?: string
          disclosure_id?: string | null
          gain_amount?: number | null
          gain_type?: string | null
          id?: string
          politician_id?: string | null
          raw_data?: Json | null
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "capital_gains_disclosure_id_fkey"
            columns: ["disclosure_id"]
            isOneToOne: false
            referencedRelation: "trading_disclosures"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "capital_gains_politician_id_fkey"
            columns: ["politician_id"]
            isOneToOne: false
            referencedRelation: "politicians"
            referencedColumns: ["id"]
          },
        ]
      }
      chart_data: {
        Row: {
          buy_count: number | null
          buys: number | null
          created_at: string | null
          id: string
          month: number
          party_breakdown: Json | null
          sell_count: number | null
          sells: number | null
          top_tickers: Json | null
          total_trades: number | null
          total_volume: number | null
          unique_politicians: number | null
          updated_at: string | null
          volume: number | null
          year: number
        }
        Insert: {
          buy_count?: number | null
          buys?: number | null
          created_at?: string | null
          id?: string
          month: number
          party_breakdown?: Json | null
          sell_count?: number | null
          sells?: number | null
          top_tickers?: Json | null
          total_trades?: number | null
          total_volume?: number | null
          unique_politicians?: number | null
          updated_at?: string | null
          volume?: number | null
          year: number
        }
        Update: {
          buy_count?: number | null
          buys?: number | null
          created_at?: string | null
          id?: string
          month?: number
          party_breakdown?: Json | null
          sell_count?: number | null
          sells?: number | null
          top_tickers?: Json | null
          total_trades?: number | null
          total_volume?: number | null
          unique_politicians?: number | null
          updated_at?: string | null
          volume?: number | null
          year?: number
        }
        Relationships: []
      }
      connection_health_log: {
        Row: {
          checked_at: string
          checked_by: string | null
          connection_type: string
          diagnostics: Json | null
          endpoint_url: string | null
          error_message: string | null
          http_status_code: number | null
          id: string
          response_time_ms: number | null
          status: string
        }
        Insert: {
          checked_at?: string
          checked_by?: string | null
          connection_type: string
          diagnostics?: Json | null
          endpoint_url?: string | null
          error_message?: string | null
          http_status_code?: number | null
          id?: string
          response_time_ms?: number | null
          status: string
        }
        Update: {
          checked_at?: string
          checked_by?: string | null
          connection_type?: string
          diagnostics?: Json | null
          endpoint_url?: string | null
          error_message?: string | null
          http_status_code?: number | null
          id?: string
          response_time_ms?: number | null
          status?: string
        }
        Relationships: []
      }
      dashboard_stats: {
        Row: {
          active_politicians: number | null
          average_trade_size: number | null
          created_at: string | null
          id: string
          jurisdictions_tracked: number | null
          last_updated: string | null
          most_active_politician: string | null
          recent_filings: number | null
          stats_data: Json | null
          top_traded_stock: string | null
          total_politicians: number | null
          total_trades: number | null
          total_volume: number | null
          trades_this_month: number | null
          updated_at: string | null
        }
        Insert: {
          active_politicians?: number | null
          average_trade_size?: number | null
          created_at?: string | null
          id?: string
          jurisdictions_tracked?: number | null
          last_updated?: string | null
          most_active_politician?: string | null
          recent_filings?: number | null
          stats_data?: Json | null
          top_traded_stock?: string | null
          total_politicians?: number | null
          total_trades?: number | null
          total_volume?: number | null
          trades_this_month?: number | null
          updated_at?: string | null
        }
        Update: {
          active_politicians?: number | null
          average_trade_size?: number | null
          created_at?: string | null
          id?: string
          jurisdictions_tracked?: number | null
          last_updated?: string | null
          most_active_politician?: string | null
          recent_filings?: number | null
          stats_data?: Json | null
          top_traded_stock?: string | null
          total_politicians?: number | null
          total_trades?: number | null
          total_volume?: number | null
          trades_this_month?: number | null
          updated_at?: string | null
        }
        Relationships: []
      }
      data_pull_jobs: {
        Row: {
          completed_at: string | null
          config_snapshot: Json | null
          created_at: string | null
          error_details: Json | null
          error_message: string | null
          id: string
          job_type: string
          records_failed: number | null
          records_found: number | null
          records_new: number | null
          records_processed: number | null
          records_updated: number | null
          started_at: string | null
          status: string | null
        }
        Insert: {
          completed_at?: string | null
          config_snapshot?: Json | null
          created_at?: string | null
          error_details?: Json | null
          error_message?: string | null
          id?: string
          job_type: string
          records_failed?: number | null
          records_found?: number | null
          records_new?: number | null
          records_processed?: number | null
          records_updated?: number | null
          started_at?: string | null
          status?: string | null
        }
        Update: {
          completed_at?: string | null
          config_snapshot?: Json | null
          created_at?: string | null
          error_details?: Json | null
          error_message?: string | null
          id?: string
          job_type?: string
          records_failed?: number | null
          records_found?: number | null
          records_new?: number | null
          records_processed?: number | null
          records_updated?: number | null
          started_at?: string | null
          status?: string | null
        }
        Relationships: []
      }
      data_quality_checks: {
        Row: {
          check_category: string
          check_id: string
          check_name: string
          check_tier: number
          created_at: string | null
          description: string | null
          id: string
          is_active: boolean | null
          query_template: string | null
          threshold_config: Json | null
          updated_at: string | null
        }
        Insert: {
          check_category: string
          check_id: string
          check_name: string
          check_tier: number
          created_at?: string | null
          description?: string | null
          id?: string
          is_active?: boolean | null
          query_template?: string | null
          threshold_config?: Json | null
          updated_at?: string | null
        }
        Update: {
          check_category?: string
          check_id?: string
          check_name?: string
          check_tier?: number
          created_at?: string | null
          description?: string | null
          id?: string
          is_active?: boolean | null
          query_template?: string | null
          threshold_config?: Json | null
          updated_at?: string | null
        }
        Relationships: []
      }
      data_quality_corrections: {
        Row: {
          approved_at: string | null
          approved_by: string | null
          can_rollback: boolean | null
          confidence_score: number | null
          corrected_by: string
          correction_type: string
          created_at: string | null
          field_name: string
          id: string
          issue_id: string | null
          new_value: string | null
          old_value: string | null
          record_id: string
          rollback_reason: string | null
          rolled_back: boolean | null
          rolled_back_at: string | null
          table_name: string
        }
        Insert: {
          approved_at?: string | null
          approved_by?: string | null
          can_rollback?: boolean | null
          confidence_score?: number | null
          corrected_by?: string
          correction_type: string
          created_at?: string | null
          field_name: string
          id?: string
          issue_id?: string | null
          new_value?: string | null
          old_value?: string | null
          record_id: string
          rollback_reason?: string | null
          rolled_back?: boolean | null
          rolled_back_at?: string | null
          table_name: string
        }
        Update: {
          approved_at?: string | null
          approved_by?: string | null
          can_rollback?: boolean | null
          confidence_score?: number | null
          corrected_by?: string
          correction_type?: string
          created_at?: string | null
          field_name?: string
          id?: string
          issue_id?: string | null
          new_value?: string | null
          old_value?: string | null
          record_id?: string
          rollback_reason?: string | null
          rolled_back?: boolean | null
          rolled_back_at?: string | null
          table_name?: string
        }
        Relationships: [
          {
            foreignKeyName: "data_quality_corrections_issue_id_fkey"
            columns: ["issue_id"]
            isOneToOne: false
            referencedRelation: "data_quality_issues"
            referencedColumns: ["id"]
          },
        ]
      }
      data_quality_issues: {
        Row: {
          actual_value: string | null
          correction_id: string | null
          created_at: string | null
          description: string
          expected_value: string | null
          field_name: string | null
          id: string
          issue_type: string
          record_id: string | null
          resolution_notes: string | null
          resolved_at: string | null
          resolved_by: string | null
          result_id: string | null
          severity: string
          status: string | null
          table_name: string
          updated_at: string | null
        }
        Insert: {
          actual_value?: string | null
          correction_id?: string | null
          created_at?: string | null
          description: string
          expected_value?: string | null
          field_name?: string | null
          id?: string
          issue_type: string
          record_id?: string | null
          resolution_notes?: string | null
          resolved_at?: string | null
          resolved_by?: string | null
          result_id?: string | null
          severity: string
          status?: string | null
          table_name: string
          updated_at?: string | null
        }
        Update: {
          actual_value?: string | null
          correction_id?: string | null
          created_at?: string | null
          description?: string
          expected_value?: string | null
          field_name?: string | null
          id?: string
          issue_type?: string
          record_id?: string | null
          resolution_notes?: string | null
          resolved_at?: string | null
          resolved_by?: string | null
          result_id?: string | null
          severity?: string
          status?: string | null
          table_name?: string
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "data_quality_issues_result_id_fkey"
            columns: ["result_id"]
            isOneToOne: false
            referencedRelation: "data_quality_results"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "fk_dq_issues_correction"
            columns: ["correction_id"]
            isOneToOne: false
            referencedRelation: "data_quality_corrections"
            referencedColumns: ["id"]
          },
        ]
      }
      data_quality_quarantine: {
        Row: {
          created_at: string | null
          id: string
          issue_ids: string[] | null
          original_data: Json
          original_record_id: string | null
          quarantine_reason: string
          review_notes: string | null
          reviewed_at: string | null
          reviewed_by: string | null
          status: string | null
          suggested_corrections: Json | null
          table_name: string
          updated_at: string | null
        }
        Insert: {
          created_at?: string | null
          id?: string
          issue_ids?: string[] | null
          original_data: Json
          original_record_id?: string | null
          quarantine_reason: string
          review_notes?: string | null
          reviewed_at?: string | null
          reviewed_by?: string | null
          status?: string | null
          suggested_corrections?: Json | null
          table_name: string
          updated_at?: string | null
        }
        Update: {
          created_at?: string | null
          id?: string
          issue_ids?: string[] | null
          original_data?: Json
          original_record_id?: string | null
          quarantine_reason?: string
          review_notes?: string | null
          reviewed_at?: string | null
          reviewed_by?: string | null
          status?: string | null
          suggested_corrections?: Json | null
          table_name?: string
          updated_at?: string | null
        }
        Relationships: []
      }
      data_quality_results: {
        Row: {
          check_config: Json | null
          check_id: string
          completed_at: string | null
          created_at: string | null
          duration_ms: number | null
          execution_id: string | null
          id: string
          issue_summary: Json | null
          issues_found: number | null
          records_checked: number | null
          started_at: string
          status: string
          summary: string | null
        }
        Insert: {
          check_config?: Json | null
          check_id: string
          completed_at?: string | null
          created_at?: string | null
          duration_ms?: number | null
          execution_id?: string | null
          id?: string
          issue_summary?: Json | null
          issues_found?: number | null
          records_checked?: number | null
          started_at: string
          status: string
          summary?: string | null
        }
        Update: {
          check_config?: Json | null
          check_id?: string
          completed_at?: string | null
          created_at?: string | null
          duration_ms?: number | null
          execution_id?: string | null
          id?: string
          issue_summary?: Json | null
          issues_found?: number | null
          records_checked?: number | null
          started_at?: string
          status?: string
          summary?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "data_quality_results_check_id_fkey"
            columns: ["check_id"]
            isOneToOne: false
            referencedRelation: "data_quality_checks"
            referencedColumns: ["check_id"]
          },
        ]
      }
      data_sources: {
        Row: {
          consecutive_failures: number | null
          created_at: string | null
          id: string
          is_active: boolean | null
          last_attempt: string | null
          last_successful_pull: string | null
          name: string
          region: string
          request_config: Json | null
          source_type: string
          updated_at: string | null
          url: string
        }
        Insert: {
          consecutive_failures?: number | null
          created_at?: string | null
          id?: string
          is_active?: boolean | null
          last_attempt?: string | null
          last_successful_pull?: string | null
          name: string
          region: string
          request_config?: Json | null
          source_type: string
          updated_at?: string | null
          url: string
        }
        Update: {
          consecutive_failures?: number | null
          created_at?: string | null
          id?: string
          is_active?: boolean | null
          last_attempt?: string | null
          last_successful_pull?: string | null
          name?: string
          region?: string
          request_config?: Json | null
          source_type?: string
          updated_at?: string | null
          url?: string
        }
        Relationships: []
      }
      drop_likes: {
        Row: {
          created_at: string | null
          drop_id: string
          id: string
          user_id: string
        }
        Insert: {
          created_at?: string | null
          drop_id: string
          id?: string
          user_id: string
        }
        Update: {
          created_at?: string | null
          drop_id?: string
          id?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "drop_likes_drop_id_fkey"
            columns: ["drop_id"]
            isOneToOne: false
            referencedRelation: "drops"
            referencedColumns: ["id"]
          },
        ]
      }
      drops: {
        Row: {
          content: string
          created_at: string
          id: string
          is_public: boolean | null
          updated_at: string
          user_id: string
        }
        Insert: {
          content: string
          created_at?: string
          id?: string
          is_public?: boolean | null
          updated_at?: string
          user_id: string
        }
        Update: {
          content?: string
          created_at?: string
          id?: string
          is_public?: boolean | null
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      email_alert_config: {
        Row: {
          alert_level: string
          check_categories: string[] | null
          created_at: string | null
          delivery_mode: string
          digest_day: number | null
          digest_time: string | null
          id: string
          is_active: boolean | null
          min_issues: number | null
          recipients: string[]
          updated_at: string | null
        }
        Insert: {
          alert_level: string
          check_categories?: string[] | null
          created_at?: string | null
          delivery_mode: string
          digest_day?: number | null
          digest_time?: string | null
          id?: string
          is_active?: boolean | null
          min_issues?: number | null
          recipients: string[]
          updated_at?: string | null
        }
        Update: {
          alert_level?: string
          check_categories?: string[] | null
          created_at?: string | null
          delivery_mode?: string
          digest_day?: number | null
          digest_time?: string | null
          id?: string
          is_active?: boolean | null
          min_issues?: number | null
          recipients?: string[]
          updated_at?: string | null
        }
        Relationships: []
      }
      email_alert_log: {
        Row: {
          body_preview: string | null
          config_id: string | null
          created_at: string | null
          error_message: string | null
          id: string
          issue_count: number | null
          recipients: string[]
          result_ids: string[] | null
          sent_at: string | null
          status: string
          subject: string
        }
        Insert: {
          body_preview?: string | null
          config_id?: string | null
          created_at?: string | null
          error_message?: string | null
          id?: string
          issue_count?: number | null
          recipients: string[]
          result_ids?: string[] | null
          sent_at?: string | null
          status: string
          subject: string
        }
        Update: {
          body_preview?: string | null
          config_id?: string | null
          created_at?: string | null
          error_message?: string | null
          id?: string
          issue_count?: number | null
          recipients?: string[]
          result_ids?: string[] | null
          sent_at?: string | null
          status?: string
          subject?: string
        }
        Relationships: [
          {
            foreignKeyName: "email_alert_log_config_id_fkey"
            columns: ["config_id"]
            isOneToOne: false
            referencedRelation: "email_alert_config"
            referencedColumns: ["id"]
          },
        ]
      }
      feature_definitions: {
        Row: {
          activated_at: string | null
          computation_config: Json
          created_at: string | null
          created_by: string | null
          default_weights: Json | null
          deprecated_at: string | null
          deprecation_reason: string | null
          description: string | null
          feature_names: string[]
          feature_schema: Json
          id: string
          is_active: boolean | null
          updated_at: string | null
          version: string
        }
        Insert: {
          activated_at?: string | null
          computation_config?: Json
          created_at?: string | null
          created_by?: string | null
          default_weights?: Json | null
          deprecated_at?: string | null
          deprecation_reason?: string | null
          description?: string | null
          feature_names: string[]
          feature_schema: Json
          id?: string
          is_active?: boolean | null
          updated_at?: string | null
          version: string
        }
        Update: {
          activated_at?: string | null
          computation_config?: Json
          created_at?: string | null
          created_by?: string | null
          default_weights?: Json | null
          deprecated_at?: string | null
          deprecation_reason?: string | null
          description?: string | null
          feature_names?: string[]
          feature_schema?: Json
          id?: string
          is_active?: boolean | null
          updated_at?: string | null
          version?: string
        }
        Relationships: []
      }
      feature_importance_history: {
        Row: {
          analysis_date: string
          analysis_window_days: number | null
          avg_return_when_high: number | null
          avg_return_when_low: number | null
          correlation_p_value: number | null
          correlation_with_return: number | null
          created_at: string | null
          feature_name: string
          feature_useful: boolean | null
          id: string
          lift_pct: number | null
          median_value: number | null
          recommended_weight: number | null
          sample_size_high: number | null
          sample_size_low: number | null
          sample_size_total: number | null
          win_rate_when_high: number | null
          win_rate_when_low: number | null
        }
        Insert: {
          analysis_date: string
          analysis_window_days?: number | null
          avg_return_when_high?: number | null
          avg_return_when_low?: number | null
          correlation_p_value?: number | null
          correlation_with_return?: number | null
          created_at?: string | null
          feature_name: string
          feature_useful?: boolean | null
          id?: string
          lift_pct?: number | null
          median_value?: number | null
          recommended_weight?: number | null
          sample_size_high?: number | null
          sample_size_low?: number | null
          sample_size_total?: number | null
          win_rate_when_high?: number | null
          win_rate_when_low?: number | null
        }
        Update: {
          analysis_date?: string
          analysis_window_days?: number | null
          avg_return_when_high?: number | null
          avg_return_when_low?: number | null
          correlation_p_value?: number | null
          correlation_with_return?: number | null
          created_at?: string | null
          feature_name?: string
          feature_useful?: boolean | null
          id?: string
          lift_pct?: number | null
          median_value?: number | null
          recommended_weight?: number | null
          sample_size_high?: number | null
          sample_size_low?: number | null
          sample_size_total?: number | null
          win_rate_when_high?: number | null
          win_rate_when_low?: number | null
        }
        Relationships: []
      }
      job_executions: {
        Row: {
          completed_at: string
          created_at: string | null
          duration_seconds: number | null
          error_message: string | null
          id: string
          job_id: string
          logs: string | null
          metadata: Json | null
          started_at: string
          status: string
        }
        Insert: {
          completed_at: string
          created_at?: string | null
          duration_seconds?: number | null
          error_message?: string | null
          id?: string
          job_id: string
          logs?: string | null
          metadata?: Json | null
          started_at: string
          status: string
        }
        Update: {
          completed_at?: string
          created_at?: string | null
          duration_seconds?: number | null
          error_message?: string | null
          id?: string
          job_id?: string
          logs?: string | null
          metadata?: Json | null
          started_at?: string
          status?: string
        }
        Relationships: []
      }
      jurisdictions: {
        Row: {
          code: string | null
          country: string | null
          created_at: string | null
          flag: string | null
          id: string
          is_active: boolean | null
          name: string
          region: string | null
          updated_at: string | null
        }
        Insert: {
          code?: string | null
          country?: string | null
          created_at?: string | null
          flag?: string | null
          id?: string
          is_active?: boolean | null
          name: string
          region?: string | null
          updated_at?: string | null
        }
        Update: {
          code?: string | null
          country?: string | null
          created_at?: string | null
          flag?: string | null
          id?: string
          is_active?: boolean | null
          name?: string
          region?: string | null
          updated_at?: string | null
        }
        Relationships: []
      }
      lsh_job_executions: {
        Row: {
          avg_cpu_percent: number | null
          completed_at: string | null
          created_at: string | null
          disk_io_mb: number | null
          duration_ms: number | null
          environment: Json | null
          error_message: string | null
          error_type: string | null
          execution_id: string
          exit_code: number | null
          hostname: string | null
          id: string
          job_id: string
          log_file_path: string | null
          max_memory_mb: number | null
          metadata: Json | null
          output_size_bytes: number | null
          parent_execution_id: string | null
          pid: number | null
          ppid: number | null
          queued_at: string | null
          retry_count: number | null
          signal: string | null
          stack_trace: string | null
          started_at: string | null
          status: string | null
          stderr: string | null
          stdout: string | null
          tags: string[] | null
          triggered_by: string | null
          updated_at: string | null
          working_directory: string | null
        }
        Insert: {
          avg_cpu_percent?: number | null
          completed_at?: string | null
          created_at?: string | null
          disk_io_mb?: number | null
          duration_ms?: number | null
          environment?: Json | null
          error_message?: string | null
          error_type?: string | null
          execution_id: string
          exit_code?: number | null
          hostname?: string | null
          id?: string
          job_id: string
          log_file_path?: string | null
          max_memory_mb?: number | null
          metadata?: Json | null
          output_size_bytes?: number | null
          parent_execution_id?: string | null
          pid?: number | null
          ppid?: number | null
          queued_at?: string | null
          retry_count?: number | null
          signal?: string | null
          stack_trace?: string | null
          started_at?: string | null
          status?: string | null
          stderr?: string | null
          stdout?: string | null
          tags?: string[] | null
          triggered_by?: string | null
          updated_at?: string | null
          working_directory?: string | null
        }
        Update: {
          avg_cpu_percent?: number | null
          completed_at?: string | null
          created_at?: string | null
          disk_io_mb?: number | null
          duration_ms?: number | null
          environment?: Json | null
          error_message?: string | null
          error_type?: string | null
          execution_id?: string
          exit_code?: number | null
          hostname?: string | null
          id?: string
          job_id?: string
          log_file_path?: string | null
          max_memory_mb?: number | null
          metadata?: Json | null
          output_size_bytes?: number | null
          parent_execution_id?: string | null
          pid?: number | null
          ppid?: number | null
          queued_at?: string | null
          retry_count?: number | null
          signal?: string | null
          stack_trace?: string | null
          started_at?: string | null
          status?: string | null
          stderr?: string | null
          stdout?: string | null
          tags?: string[] | null
          triggered_by?: string | null
          updated_at?: string | null
          working_directory?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "lsh_job_executions_job_id_fkey"
            columns: ["job_id"]
            isOneToOne: false
            referencedRelation: "lsh_job_stats"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "lsh_job_executions_job_id_fkey"
            columns: ["job_id"]
            isOneToOne: false
            referencedRelation: "lsh_jobs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "lsh_job_executions_parent_execution_id_fkey"
            columns: ["parent_execution_id"]
            isOneToOne: false
            referencedRelation: "lsh_job_executions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "lsh_job_executions_parent_execution_id_fkey"
            columns: ["parent_execution_id"]
            isOneToOne: false
            referencedRelation: "lsh_recent_executions"
            referencedColumns: ["id"]
          },
        ]
      }
      lsh_jobs: {
        Row: {
          command: string
          created_at: string | null
          created_by: string | null
          cron_expression: string | null
          description: string | null
          environment: Json | null
          id: string
          interval_seconds: number | null
          job_name: string
          last_run: string | null
          max_cpu_percent: number | null
          max_memory_mb: number | null
          max_retries: number | null
          next_run: string | null
          priority: number | null
          retry_delay_seconds: number | null
          status: string | null
          tags: string[] | null
          timeout_seconds: number | null
          type: string | null
          updated_at: string | null
          working_directory: string | null
        }
        Insert: {
          command: string
          created_at?: string | null
          created_by?: string | null
          cron_expression?: string | null
          description?: string | null
          environment?: Json | null
          id?: string
          interval_seconds?: number | null
          job_name: string
          last_run?: string | null
          max_cpu_percent?: number | null
          max_memory_mb?: number | null
          max_retries?: number | null
          next_run?: string | null
          priority?: number | null
          retry_delay_seconds?: number | null
          status?: string | null
          tags?: string[] | null
          timeout_seconds?: number | null
          type?: string | null
          updated_at?: string | null
          working_directory?: string | null
        }
        Update: {
          command?: string
          created_at?: string | null
          created_by?: string | null
          cron_expression?: string | null
          description?: string | null
          environment?: Json | null
          id?: string
          interval_seconds?: number | null
          job_name?: string
          last_run?: string | null
          max_cpu_percent?: number | null
          max_memory_mb?: number | null
          max_retries?: number | null
          next_run?: string | null
          priority?: number | null
          retry_delay_seconds?: number | null
          status?: string | null
          tags?: string[] | null
          timeout_seconds?: number | null
          type?: string | null
          updated_at?: string | null
          working_directory?: string | null
        }
        Relationships: []
      }
      ml_models: {
        Row: {
          created_at: string | null
          error_message: string | null
          feature_importance: Json | null
          hyperparameters: Json | null
          id: string
          metrics: Json | null
          model_artifact_path: string | null
          model_name: string
          model_type: string
          model_version: string
          status: string | null
          training_completed_at: string | null
          training_samples: number | null
          training_started_at: string | null
          updated_at: string | null
          validation_samples: number | null
        }
        Insert: {
          created_at?: string | null
          error_message?: string | null
          feature_importance?: Json | null
          hyperparameters?: Json | null
          id?: string
          metrics?: Json | null
          model_artifact_path?: string | null
          model_name: string
          model_type: string
          model_version: string
          status?: string | null
          training_completed_at?: string | null
          training_samples?: number | null
          training_started_at?: string | null
          updated_at?: string | null
          validation_samples?: number | null
        }
        Update: {
          created_at?: string | null
          error_message?: string | null
          feature_importance?: Json | null
          hyperparameters?: Json | null
          id?: string
          metrics?: Json | null
          model_artifact_path?: string | null
          model_name?: string
          model_type?: string
          model_version?: string
          status?: string | null
          training_completed_at?: string | null
          training_samples?: number | null
          training_started_at?: string | null
          updated_at?: string | null
          validation_samples?: number | null
        }
        Relationships: []
      }
      ml_predictions_cache: {
        Row: {
          confidence: number | null
          created_at: string | null
          expires_at: string
          feature_hash: string
          id: string
          model_id: string | null
          prediction: number | null
          prediction_details: Json | null
          ticker: string
        }
        Insert: {
          confidence?: number | null
          created_at?: string | null
          expires_at: string
          feature_hash: string
          id?: string
          model_id?: string | null
          prediction?: number | null
          prediction_details?: Json | null
          ticker: string
        }
        Update: {
          confidence?: number | null
          created_at?: string | null
          expires_at?: string
          feature_hash?: string
          id?: string
          model_id?: string | null
          prediction?: number | null
          prediction_details?: Json | null
          ticker?: string
        }
        Relationships: [
          {
            foreignKeyName: "ml_predictions_cache_model_id_fkey"
            columns: ["model_id"]
            isOneToOne: false
            referencedRelation: "ml_models"
            referencedColumns: ["id"]
          },
        ]
      }
      ml_retraining_stats: {
        Row: {
          changes_since_training: number | null
          check_interval_minutes: number | null
          created_at: string | null
          id: string
          last_check_at: string | null
          last_training_at: string | null
          singleton_key: number | null
          threshold: number | null
          updated_at: string | null
        }
        Insert: {
          changes_since_training?: number | null
          check_interval_minutes?: number | null
          created_at?: string | null
          id?: string
          last_check_at?: string | null
          last_training_at?: string | null
          singleton_key?: number | null
          threshold?: number | null
          updated_at?: string | null
        }
        Update: {
          changes_since_training?: number | null
          check_interval_minutes?: number | null
          created_at?: string | null
          id?: string
          last_check_at?: string | null
          last_training_at?: string | null
          singleton_key?: number | null
          threshold?: number | null
          updated_at?: string | null
        }
        Relationships: []
      }
      ml_training_data: {
        Row: {
          actual_return_30d: number | null
          actual_return_7d: number | null
          created_at: string | null
          disclosure_date: string
          feature_vector: Json
          id: string
          label: number | null
          model_id: string | null
          price_30d_later: number | null
          price_7d_later: number | null
          price_at_disclosure: number | null
          ticker: string
        }
        Insert: {
          actual_return_30d?: number | null
          actual_return_7d?: number | null
          created_at?: string | null
          disclosure_date: string
          feature_vector: Json
          id?: string
          label?: number | null
          model_id?: string | null
          price_30d_later?: number | null
          price_7d_later?: number | null
          price_at_disclosure?: number | null
          ticker: string
        }
        Update: {
          actual_return_30d?: number | null
          actual_return_7d?: number | null
          created_at?: string | null
          disclosure_date?: string
          feature_vector?: Json
          id?: string
          label?: number | null
          model_id?: string | null
          price_30d_later?: number | null
          price_7d_later?: number | null
          price_at_disclosure?: number | null
          ticker?: string
        }
        Relationships: [
          {
            foreignKeyName: "ml_training_data_model_id_fkey"
            columns: ["model_id"]
            isOneToOne: false
            referencedRelation: "ml_models"
            referencedColumns: ["id"]
          },
        ]
      }
      ml_training_jobs: {
        Row: {
          completed_at: string | null
          config: Json | null
          created_at: string | null
          current_step: string | null
          error_message: string | null
          id: string
          job_type: string
          model_id: string | null
          progress_pct: number | null
          result_summary: Json | null
          started_at: string | null
          status: string | null
          triggered_by: string | null
        }
        Insert: {
          completed_at?: string | null
          config?: Json | null
          created_at?: string | null
          current_step?: string | null
          error_message?: string | null
          id?: string
          job_type: string
          model_id?: string | null
          progress_pct?: number | null
          result_summary?: Json | null
          started_at?: string | null
          status?: string | null
          triggered_by?: string | null
        }
        Update: {
          completed_at?: string | null
          config?: Json | null
          created_at?: string | null
          current_step?: string | null
          error_message?: string | null
          id?: string
          job_type?: string
          model_id?: string | null
          progress_pct?: number | null
          result_summary?: Json | null
          started_at?: string | null
          status?: string | null
          triggered_by?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "ml_training_jobs_model_id_fkey"
            columns: ["model_id"]
            isOneToOne: false
            referencedRelation: "ml_models"
            referencedColumns: ["id"]
          },
        ]
      }
      model_performance_history: {
        Row: {
          alpha: number | null
          avg_return_pct: number | null
          baseline_return_pct: number | null
          confidence_correlation: number | null
          created_at: string | null
          evaluation_date: string
          evaluation_window_days: number | null
          feature_weights: Json | null
          high_confidence_win_rate: number | null
          id: string
          low_confidence_win_rate: number | null
          max_drawdown_pct: number | null
          model_id: string | null
          model_version: string
          sharpe_ratio: number | null
          signals_skipped: number | null
          signals_traded: number | null
          sortino_ratio: number | null
          total_return_pct: number | null
          total_signals_generated: number | null
          win_rate: number | null
        }
        Insert: {
          alpha?: number | null
          avg_return_pct?: number | null
          baseline_return_pct?: number | null
          confidence_correlation?: number | null
          created_at?: string | null
          evaluation_date: string
          evaluation_window_days?: number | null
          feature_weights?: Json | null
          high_confidence_win_rate?: number | null
          id?: string
          low_confidence_win_rate?: number | null
          max_drawdown_pct?: number | null
          model_id?: string | null
          model_version: string
          sharpe_ratio?: number | null
          signals_skipped?: number | null
          signals_traded?: number | null
          sortino_ratio?: number | null
          total_return_pct?: number | null
          total_signals_generated?: number | null
          win_rate?: number | null
        }
        Update: {
          alpha?: number | null
          avg_return_pct?: number | null
          baseline_return_pct?: number | null
          confidence_correlation?: number | null
          created_at?: string | null
          evaluation_date?: string
          evaluation_window_days?: number | null
          feature_weights?: Json | null
          high_confidence_win_rate?: number | null
          id?: string
          low_confidence_win_rate?: number | null
          max_drawdown_pct?: number | null
          model_id?: string | null
          model_version?: string
          sharpe_ratio?: number | null
          signals_skipped?: number | null
          signals_traded?: number | null
          sortino_ratio?: number | null
          total_return_pct?: number | null
          total_signals_generated?: number | null
          win_rate?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "model_performance_history_model_id_fkey"
            columns: ["model_id"]
            isOneToOne: false
            referencedRelation: "ml_models"
            referencedColumns: ["id"]
          },
        ]
      }
      model_retraining_events: {
        Row: {
          created_at: string | null
          deployed: boolean | null
          deployment_reason: string | null
          id: string
          improvement_pct: number | null
          new_model_id: string | null
          new_model_metrics: Json | null
          old_model_id: string | null
          old_model_metrics: Json | null
          outcome_samples: number | null
          training_samples: number | null
          training_window_days: number | null
          trigger_reason: string | null
          trigger_type: string | null
          weight_changes: Json | null
        }
        Insert: {
          created_at?: string | null
          deployed?: boolean | null
          deployment_reason?: string | null
          id?: string
          improvement_pct?: number | null
          new_model_id?: string | null
          new_model_metrics?: Json | null
          old_model_id?: string | null
          old_model_metrics?: Json | null
          outcome_samples?: number | null
          training_samples?: number | null
          training_window_days?: number | null
          trigger_reason?: string | null
          trigger_type?: string | null
          weight_changes?: Json | null
        }
        Update: {
          created_at?: string | null
          deployed?: boolean | null
          deployment_reason?: string | null
          id?: string
          improvement_pct?: number | null
          new_model_id?: string | null
          new_model_metrics?: Json | null
          old_model_id?: string | null
          old_model_metrics?: Json | null
          outcome_samples?: number | null
          training_samples?: number | null
          training_window_days?: number | null
          trigger_reason?: string | null
          trigger_type?: string | null
          weight_changes?: Json | null
        }
        Relationships: [
          {
            foreignKeyName: "model_retraining_events_new_model_id_fkey"
            columns: ["new_model_id"]
            isOneToOne: false
            referencedRelation: "ml_models"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "model_retraining_events_old_model_id_fkey"
            columns: ["old_model_id"]
            isOneToOne: false
            referencedRelation: "ml_models"
            referencedColumns: ["id"]
          },
        ]
      }
      model_weights_snapshots: {
        Row: {
          created_at: string | null
          encoder_state: Json | null
          feature_definition_id: string | null
          id: string
          model_id: string
          sample_predictions: Json | null
          scaler_state: Json | null
          validation_metrics: Json | null
          weights_blob: string | null
          weights_hash: string
          weights_path: string | null
          weights_size_bytes: number | null
        }
        Insert: {
          created_at?: string | null
          encoder_state?: Json | null
          feature_definition_id?: string | null
          id?: string
          model_id: string
          sample_predictions?: Json | null
          scaler_state?: Json | null
          validation_metrics?: Json | null
          weights_blob?: string | null
          weights_hash: string
          weights_path?: string | null
          weights_size_bytes?: number | null
        }
        Update: {
          created_at?: string | null
          encoder_state?: Json | null
          feature_definition_id?: string | null
          id?: string
          model_id?: string
          sample_predictions?: Json | null
          scaler_state?: Json | null
          validation_metrics?: Json | null
          weights_blob?: string | null
          weights_hash?: string
          weights_path?: string | null
          weights_size_bytes?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "model_weights_snapshots_feature_definition_id_fkey"
            columns: ["feature_definition_id"]
            isOneToOne: false
            referencedRelation: "feature_definitions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "model_weights_snapshots_model_id_fkey"
            columns: ["model_id"]
            isOneToOne: false
            referencedRelation: "ml_models"
            referencedColumns: ["id"]
          },
        ]
      }
      notifications: {
        Row: {
          action_url: string | null
          created_at: string | null
          id: string
          is_read: boolean | null
          message: string | null
          metadata: Json | null
          title: string
          type: string | null
          user_id: string | null
        }
        Insert: {
          action_url?: string | null
          created_at?: string | null
          id?: string
          is_read?: boolean | null
          message?: string | null
          metadata?: Json | null
          title: string
          type?: string | null
          user_id?: string | null
        }
        Update: {
          action_url?: string | null
          created_at?: string | null
          id?: string
          is_read?: boolean | null
          message?: string | null
          metadata?: Json | null
          title?: string
          type?: string | null
          user_id?: string | null
        }
        Relationships: []
      }
      order_state_log: {
        Row: {
          alpaca_event_id: string | null
          alpaca_event_timestamp: string | null
          avg_price_at_state: number | null
          created_at: string
          error_code: string | null
          error_message: string | null
          filled_qty_at_state: number | null
          id: string
          new_status: string
          order_id: string
          previous_status: string | null
          raw_event: Json | null
          source: string | null
        }
        Insert: {
          alpaca_event_id?: string | null
          alpaca_event_timestamp?: string | null
          avg_price_at_state?: number | null
          created_at?: string
          error_code?: string | null
          error_message?: string | null
          filled_qty_at_state?: number | null
          id?: string
          new_status: string
          order_id: string
          previous_status?: string | null
          raw_event?: Json | null
          source?: string | null
        }
        Update: {
          alpaca_event_id?: string | null
          alpaca_event_timestamp?: string | null
          avg_price_at_state?: number | null
          created_at?: string
          error_code?: string | null
          error_message?: string | null
          filled_qty_at_state?: number | null
          id?: string
          new_status?: string
          order_id?: string
          previous_status?: string | null
          raw_event?: Json | null
          source?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "order_state_log_order_id_fkey"
            columns: ["order_id"]
            isOneToOne: false
            referencedRelation: "trading_orders"
            referencedColumns: ["id"]
          },
        ]
      }
      parties: {
        Row: {
          code: string
          color: string
          created_at: string | null
          id: string
          jurisdiction: string
          name: string
          short_name: string | null
        }
        Insert: {
          code: string
          color: string
          created_at?: string | null
          id?: string
          jurisdiction?: string
          name: string
          short_name?: string | null
        }
        Update: {
          code?: string
          color?: string
          created_at?: string | null
          id?: string
          jurisdiction?: string
          name?: string
          short_name?: string | null
        }
        Relationships: []
      }
      politician_trades: {
        Row: {
          amount: string | null
          amount_max: number | null
          amount_min: number | null
          asset_description: string | null
          asset_type: string | null
          created_at: string | null
          disclosure_date: string
          district: string | null
          id: string
          party: string | null
          politician_name: string
          position: string | null
          raw_data: Json | null
          source: string | null
          source_url: string | null
          state: string | null
          ticker: string | null
          transaction_date: string
          transaction_type: string
          updated_at: string | null
        }
        Insert: {
          amount?: string | null
          amount_max?: number | null
          amount_min?: number | null
          asset_description?: string | null
          asset_type?: string | null
          created_at?: string | null
          disclosure_date: string
          district?: string | null
          id?: string
          party?: string | null
          politician_name: string
          position?: string | null
          raw_data?: Json | null
          source?: string | null
          source_url?: string | null
          state?: string | null
          ticker?: string | null
          transaction_date: string
          transaction_type: string
          updated_at?: string | null
        }
        Update: {
          amount?: string | null
          amount_max?: number | null
          amount_min?: number | null
          asset_description?: string | null
          asset_type?: string | null
          created_at?: string | null
          disclosure_date?: string
          district?: string | null
          id?: string
          party?: string | null
          politician_name?: string
          position?: string | null
          raw_data?: Json | null
          source?: string | null
          source_url?: string | null
          state?: string | null
          ticker?: string | null
          transaction_date?: string
          transaction_type?: string
          updated_at?: string | null
        }
        Relationships: []
      }
      politicians: {
        Row: {
          avatar_url: string | null
          biography: string | null
          biography_updated_at: string | null
          bioguide_id: string | null
          chamber: string | null
          created_at: string | null
          district: string | null
          eu_id: string | null
          first_name: string
          full_name: string
          id: string
          image_url: string | null
          is_active: boolean | null
          last_name: string
          name: string | null
          party: string | null
          position: string | null
          role: string
          state: string | null
          state_or_country: string | null
          term_end: string | null
          term_start: string | null
          total_trades: number | null
          total_volume: number | null
          updated_at: string | null
        }
        Insert: {
          avatar_url?: string | null
          biography?: string | null
          biography_updated_at?: string | null
          bioguide_id?: string | null
          chamber?: string | null
          created_at?: string | null
          district?: string | null
          eu_id?: string | null
          first_name: string
          full_name: string
          id?: string
          image_url?: string | null
          is_active?: boolean | null
          last_name: string
          name?: string | null
          party?: string | null
          position?: string | null
          role: string
          state?: string | null
          state_or_country?: string | null
          term_end?: string | null
          term_start?: string | null
          total_trades?: number | null
          total_volume?: number | null
          updated_at?: string | null
        }
        Update: {
          avatar_url?: string | null
          biography?: string | null
          biography_updated_at?: string | null
          bioguide_id?: string | null
          chamber?: string | null
          created_at?: string | null
          district?: string | null
          eu_id?: string | null
          first_name?: string
          full_name?: string
          id?: string
          image_url?: string | null
          is_active?: boolean | null
          last_name?: string
          name?: string | null
          party?: string | null
          position?: string | null
          role?: string
          state?: string | null
          state_or_country?: string | null
          term_end?: string | null
          term_start?: string | null
          total_trades?: number | null
          total_volume?: number | null
          updated_at?: string | null
        }
        Relationships: []
      }
      portfolio_performance_snapshots: {
        Row: {
          cash_balance: number
          created_at: string | null
          daily_return: number
          daily_return_pct: number
          id: string
          max_drawdown: number
          portfolio_id: string
          portfolio_value: number
          positions_data: Json | null
          sharpe_ratio: number
          snapshot_date: string
          total_return: number
          total_return_pct: number
          volatility: number
        }
        Insert: {
          cash_balance: number
          created_at?: string | null
          daily_return?: number
          daily_return_pct?: number
          id?: string
          max_drawdown?: number
          portfolio_id: string
          portfolio_value: number
          positions_data?: Json | null
          sharpe_ratio?: number
          snapshot_date: string
          total_return?: number
          total_return_pct?: number
          volatility?: number
        }
        Update: {
          cash_balance?: number
          created_at?: string | null
          daily_return?: number
          daily_return_pct?: number
          id?: string
          max_drawdown?: number
          portfolio_id?: string
          portfolio_value?: number
          positions_data?: Json | null
          sharpe_ratio?: number
          snapshot_date?: string
          total_return?: number
          total_return_pct?: number
          volatility?: number
        }
        Relationships: [
          {
            foreignKeyName: "portfolio_performance_snapshots_portfolio_id_fkey"
            columns: ["portfolio_id"]
            isOneToOne: false
            referencedRelation: "portfolios"
            referencedColumns: ["id"]
          },
        ]
      }
      portfolios: {
        Row: {
          beta: number | null
          cash_balance: number
          created_at: string | null
          current_value: number
          cvar_95: number | null
          daily_return: number | null
          daily_return_pct: number | null
          description: string | null
          id: string
          initial_capital: number
          is_active: boolean | null
          max_drawdown: number | null
          max_drawdown_duration: number | null
          name: string
          sharpe_ratio: number | null
          sortino_ratio: number | null
          total_return: number | null
          total_return_pct: number | null
          trading_account_id: string
          updated_at: string | null
          var_95: number | null
          volatility: number | null
        }
        Insert: {
          beta?: number | null
          cash_balance?: number
          created_at?: string | null
          current_value?: number
          cvar_95?: number | null
          daily_return?: number | null
          daily_return_pct?: number | null
          description?: string | null
          id?: string
          initial_capital?: number
          is_active?: boolean | null
          max_drawdown?: number | null
          max_drawdown_duration?: number | null
          name: string
          sharpe_ratio?: number | null
          sortino_ratio?: number | null
          total_return?: number | null
          total_return_pct?: number | null
          trading_account_id: string
          updated_at?: string | null
          var_95?: number | null
          volatility?: number | null
        }
        Update: {
          beta?: number | null
          cash_balance?: number
          created_at?: string | null
          current_value?: number
          cvar_95?: number | null
          daily_return?: number | null
          daily_return_pct?: number | null
          description?: string | null
          id?: string
          initial_capital?: number
          is_active?: boolean | null
          max_drawdown?: number | null
          max_drawdown_duration?: number | null
          name?: string
          sharpe_ratio?: number | null
          sortino_ratio?: number | null
          total_return?: number | null
          total_return_pct?: number | null
          trading_account_id?: string
          updated_at?: string | null
          var_95?: number | null
          volatility?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "portfolios_trading_account_id_fkey"
            columns: ["trading_account_id"]
            isOneToOne: false
            referencedRelation: "trading_accounts"
            referencedColumns: ["id"]
          },
        ]
      }
      positions: {
        Row: {
          average_price: number
          cost_basis: number
          created_at: string | null
          current_price: number
          id: string
          market_value: number
          portfolio_id: string
          position_size_pct: number
          quantity: number
          realized_pnl: number
          side: string
          symbol: string
          unrealized_pnl: number
          unrealized_pnl_pct: number
          updated_at: string | null
          weight: number
        }
        Insert: {
          average_price: number
          cost_basis: number
          created_at?: string | null
          current_price: number
          id?: string
          market_value: number
          portfolio_id: string
          position_size_pct?: number
          quantity: number
          realized_pnl?: number
          side: string
          symbol: string
          unrealized_pnl?: number
          unrealized_pnl_pct?: number
          updated_at?: string | null
          weight?: number
        }
        Update: {
          average_price?: number
          cost_basis?: number
          created_at?: string | null
          current_price?: number
          id?: string
          market_value?: number
          portfolio_id?: string
          position_size_pct?: number
          quantity?: number
          realized_pnl?: number
          side?: string
          symbol?: string
          unrealized_pnl?: number
          unrealized_pnl_pct?: number
          updated_at?: string | null
          weight?: number
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
      profiles: {
        Row: {
          avatar_url: string | null
          created_at: string | null
          email: string | null
          full_name: string | null
          id: string
          preferences: Json | null
          subscription_tier: string | null
          updated_at: string | null
        }
        Insert: {
          avatar_url?: string | null
          created_at?: string | null
          email?: string | null
          full_name?: string | null
          id: string
          preferences?: Json | null
          subscription_tier?: string | null
          updated_at?: string | null
        }
        Update: {
          avatar_url?: string | null
          created_at?: string | null
          email?: string | null
          full_name?: string | null
          id?: string
          preferences?: Json | null
          subscription_tier?: string | null
          updated_at?: string | null
        }
        Relationships: []
      }
      reference_portfolio_config: {
        Row: {
          base_position_size_pct: number
          confidence_multiplier: number
          created_at: string | null
          default_stop_loss_pct: number | null
          default_take_profit_pct: number | null
          description: string | null
          id: string
          initial_capital: number
          is_active: boolean | null
          max_daily_trades: number
          max_hold_days: number | null
          max_portfolio_positions: number
          max_position_size_pct: number
          max_single_trade_pct: number
          min_confidence_threshold: number
          name: string
          trading_mode: string
          trailing_stop_pct: number | null
          updated_at: string | null
        }
        Insert: {
          base_position_size_pct?: number
          confidence_multiplier?: number
          created_at?: string | null
          default_stop_loss_pct?: number | null
          default_take_profit_pct?: number | null
          description?: string | null
          id?: string
          initial_capital?: number
          is_active?: boolean | null
          max_daily_trades?: number
          max_hold_days?: number | null
          max_portfolio_positions?: number
          max_position_size_pct?: number
          max_single_trade_pct?: number
          min_confidence_threshold?: number
          name?: string
          trading_mode?: string
          trailing_stop_pct?: number | null
          updated_at?: string | null
        }
        Update: {
          base_position_size_pct?: number
          confidence_multiplier?: number
          created_at?: string | null
          default_stop_loss_pct?: number | null
          default_take_profit_pct?: number | null
          description?: string | null
          id?: string
          initial_capital?: number
          is_active?: boolean | null
          max_daily_trades?: number
          max_hold_days?: number | null
          max_portfolio_positions?: number
          max_position_size_pct?: number
          max_single_trade_pct?: number
          min_confidence_threshold?: number
          name?: string
          trading_mode?: string
          trailing_stop_pct?: number | null
          updated_at?: string | null
        }
        Relationships: []
      }
      reference_portfolio_positions: {
        Row: {
          asset_name: string | null
          confidence_weight: number | null
          created_at: string | null
          current_price: number | null
          entry_confidence: number | null
          entry_date: string
          entry_order_id: string | null
          entry_price: number
          entry_signal_id: string | null
          exit_date: string | null
          exit_order_id: string | null
          exit_price: number | null
          exit_reason: string | null
          exit_signal_id: string | null
          highest_price: number | null
          id: string
          is_open: boolean | null
          market_value: number | null
          position_size_pct: number | null
          quantity: number
          realized_pl: number | null
          realized_pl_pct: number | null
          side: string
          stop_loss_price: number | null
          take_profit_price: number | null
          ticker: string
          trailing_stop_price: number | null
          unrealized_pl: number | null
          unrealized_pl_pct: number | null
          updated_at: string | null
        }
        Insert: {
          asset_name?: string | null
          confidence_weight?: number | null
          created_at?: string | null
          current_price?: number | null
          entry_confidence?: number | null
          entry_date?: string
          entry_order_id?: string | null
          entry_price: number
          entry_signal_id?: string | null
          exit_date?: string | null
          exit_order_id?: string | null
          exit_price?: number | null
          exit_reason?: string | null
          exit_signal_id?: string | null
          highest_price?: number | null
          id?: string
          is_open?: boolean | null
          market_value?: number | null
          position_size_pct?: number | null
          quantity: number
          realized_pl?: number | null
          realized_pl_pct?: number | null
          side?: string
          stop_loss_price?: number | null
          take_profit_price?: number | null
          ticker: string
          trailing_stop_price?: number | null
          unrealized_pl?: number | null
          unrealized_pl_pct?: number | null
          updated_at?: string | null
        }
        Update: {
          asset_name?: string | null
          confidence_weight?: number | null
          created_at?: string | null
          current_price?: number | null
          entry_confidence?: number | null
          entry_date?: string
          entry_order_id?: string | null
          entry_price?: number
          entry_signal_id?: string | null
          exit_date?: string | null
          exit_order_id?: string | null
          exit_price?: number | null
          exit_reason?: string | null
          exit_signal_id?: string | null
          highest_price?: number | null
          id?: string
          is_open?: boolean | null
          market_value?: number | null
          position_size_pct?: number | null
          quantity?: number
          realized_pl?: number | null
          realized_pl_pct?: number | null
          side?: string
          stop_loss_price?: number | null
          take_profit_price?: number | null
          ticker?: string
          trailing_stop_price?: number | null
          unrealized_pl?: number | null
          unrealized_pl_pct?: number | null
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "reference_portfolio_positions_entry_signal_id_fkey"
            columns: ["entry_signal_id"]
            isOneToOne: false
            referencedRelation: "trading_signals"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "reference_portfolio_positions_exit_signal_id_fkey"
            columns: ["exit_signal_id"]
            isOneToOne: false
            referencedRelation: "trading_signals"
            referencedColumns: ["id"]
          },
        ]
      }
      reference_portfolio_signal_queue: {
        Row: {
          created_at: string | null
          error_message: string | null
          id: string
          processed_at: string | null
          signal_id: string
          skip_reason: string | null
          status: string
          transaction_id: string | null
        }
        Insert: {
          created_at?: string | null
          error_message?: string | null
          id?: string
          processed_at?: string | null
          signal_id: string
          skip_reason?: string | null
          status?: string
          transaction_id?: string | null
        }
        Update: {
          created_at?: string | null
          error_message?: string | null
          id?: string
          processed_at?: string | null
          signal_id?: string
          skip_reason?: string | null
          status?: string
          transaction_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "reference_portfolio_signal_queue_signal_id_fkey"
            columns: ["signal_id"]
            isOneToOne: false
            referencedRelation: "trading_signals"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "reference_portfolio_signal_queue_transaction_id_fkey"
            columns: ["transaction_id"]
            isOneToOne: false
            referencedRelation: "reference_portfolio_transactions"
            referencedColumns: ["id"]
          },
        ]
      }
      reference_portfolio_snapshots: {
        Row: {
          alpha: number | null
          benchmark_return: number | null
          benchmark_return_pct: number | null
          benchmark_value: number | null
          cash: number
          created_at: string | null
          cumulative_return: number | null
          cumulative_return_pct: number | null
          current_drawdown: number | null
          day_return: number | null
          day_return_pct: number | null
          id: string
          max_drawdown: number | null
          open_positions: number | null
          portfolio_value: number
          positions_value: number
          sharpe_ratio: number | null
          snapshot_date: string
          snapshot_time: string
          total_trades: number | null
          win_rate: number | null
        }
        Insert: {
          alpha?: number | null
          benchmark_return?: number | null
          benchmark_return_pct?: number | null
          benchmark_value?: number | null
          cash: number
          created_at?: string | null
          cumulative_return?: number | null
          cumulative_return_pct?: number | null
          current_drawdown?: number | null
          day_return?: number | null
          day_return_pct?: number | null
          id?: string
          max_drawdown?: number | null
          open_positions?: number | null
          portfolio_value: number
          positions_value: number
          sharpe_ratio?: number | null
          snapshot_date: string
          snapshot_time?: string
          total_trades?: number | null
          win_rate?: number | null
        }
        Update: {
          alpha?: number | null
          benchmark_return?: number | null
          benchmark_return_pct?: number | null
          benchmark_value?: number | null
          cash?: number
          created_at?: string | null
          cumulative_return?: number | null
          cumulative_return_pct?: number | null
          current_drawdown?: number | null
          day_return?: number | null
          day_return_pct?: number | null
          id?: string
          max_drawdown?: number | null
          open_positions?: number | null
          portfolio_value?: number
          positions_value?: number
          sharpe_ratio?: number | null
          snapshot_date?: string
          snapshot_time?: string
          total_trades?: number | null
          win_rate?: number | null
        }
        Relationships: []
      }
      reference_portfolio_state: {
        Row: {
          alpha: number | null
          avg_loss: number | null
          avg_win: number | null
          benchmark_return_pct: number | null
          benchmark_value: number | null
          buying_power: number
          cash: number
          config_id: string | null
          created_at: string | null
          current_drawdown: number | null
          day_return: number | null
          day_return_pct: number | null
          id: string
          last_sync_at: string | null
          last_trade_at: string | null
          losing_trades: number | null
          max_drawdown: number | null
          open_positions: number | null
          peak_portfolio_value: number | null
          portfolio_value: number
          positions_value: number | null
          profit_factor: number | null
          sharpe_ratio: number | null
          sortino_ratio: number | null
          total_return: number | null
          total_return_pct: number | null
          total_trades: number | null
          trades_today: number | null
          updated_at: string | null
          volatility: number | null
          win_rate: number | null
          winning_trades: number | null
        }
        Insert: {
          alpha?: number | null
          avg_loss?: number | null
          avg_win?: number | null
          benchmark_return_pct?: number | null
          benchmark_value?: number | null
          buying_power?: number
          cash?: number
          config_id?: string | null
          created_at?: string | null
          current_drawdown?: number | null
          day_return?: number | null
          day_return_pct?: number | null
          id?: string
          last_sync_at?: string | null
          last_trade_at?: string | null
          losing_trades?: number | null
          max_drawdown?: number | null
          open_positions?: number | null
          peak_portfolio_value?: number | null
          portfolio_value?: number
          positions_value?: number | null
          profit_factor?: number | null
          sharpe_ratio?: number | null
          sortino_ratio?: number | null
          total_return?: number | null
          total_return_pct?: number | null
          total_trades?: number | null
          trades_today?: number | null
          updated_at?: string | null
          volatility?: number | null
          win_rate?: number | null
          winning_trades?: number | null
        }
        Update: {
          alpha?: number | null
          avg_loss?: number | null
          avg_win?: number | null
          benchmark_return_pct?: number | null
          benchmark_value?: number | null
          buying_power?: number
          cash?: number
          config_id?: string | null
          created_at?: string | null
          current_drawdown?: number | null
          day_return?: number | null
          day_return_pct?: number | null
          id?: string
          last_sync_at?: string | null
          last_trade_at?: string | null
          losing_trades?: number | null
          max_drawdown?: number | null
          open_positions?: number | null
          peak_portfolio_value?: number | null
          portfolio_value?: number
          positions_value?: number | null
          profit_factor?: number | null
          sharpe_ratio?: number | null
          sortino_ratio?: number | null
          total_return?: number | null
          total_return_pct?: number | null
          total_trades?: number | null
          trades_today?: number | null
          updated_at?: string | null
          volatility?: number | null
          win_rate?: number | null
          winning_trades?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "reference_portfolio_state_config_id_fkey"
            columns: ["config_id"]
            isOneToOne: false
            referencedRelation: "reference_portfolio_config"
            referencedColumns: ["id"]
          },
        ]
      }
      reference_portfolio_transactions: {
        Row: {
          alpaca_client_order_id: string | null
          alpaca_order_id: string | null
          confidence_weight: number | null
          created_at: string | null
          error_message: string | null
          executed_at: string
          exit_reason: string | null
          id: string
          portfolio_value_at_trade: number | null
          position_id: string | null
          position_size_pct: number | null
          price: number
          quantity: number
          realized_pl: number | null
          realized_pl_pct: number | null
          signal_confidence: number | null
          signal_id: string | null
          signal_type: string | null
          status: string
          ticker: string
          total_value: number
          transaction_type: string
        }
        Insert: {
          alpaca_client_order_id?: string | null
          alpaca_order_id?: string | null
          confidence_weight?: number | null
          created_at?: string | null
          error_message?: string | null
          executed_at?: string
          exit_reason?: string | null
          id?: string
          portfolio_value_at_trade?: number | null
          position_id?: string | null
          position_size_pct?: number | null
          price: number
          quantity: number
          realized_pl?: number | null
          realized_pl_pct?: number | null
          signal_confidence?: number | null
          signal_id?: string | null
          signal_type?: string | null
          status?: string
          ticker: string
          total_value: number
          transaction_type: string
        }
        Update: {
          alpaca_client_order_id?: string | null
          alpaca_order_id?: string | null
          confidence_weight?: number | null
          created_at?: string | null
          error_message?: string | null
          executed_at?: string
          exit_reason?: string | null
          id?: string
          portfolio_value_at_trade?: number | null
          position_id?: string | null
          position_size_pct?: number | null
          price?: number
          quantity?: number
          realized_pl?: number | null
          realized_pl_pct?: number | null
          signal_confidence?: number | null
          signal_id?: string | null
          signal_type?: string | null
          status?: string
          ticker?: string
          total_value?: number
          transaction_type?: string
        }
        Relationships: [
          {
            foreignKeyName: "reference_portfolio_transactions_position_id_fkey"
            columns: ["position_id"]
            isOneToOne: false
            referencedRelation: "reference_portfolio_positions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "reference_portfolio_transactions_signal_id_fkey"
            columns: ["signal_id"]
            isOneToOne: false
            referencedRelation: "trading_signals"
            referencedColumns: ["id"]
          },
        ]
      }
      scheduled_jobs: {
        Row: {
          auto_retry_on_startup: boolean | null
          consecutive_failures: number | null
          created_at: string | null
          enabled: boolean | null
          id: string
          job_function: string
          job_id: string
          job_name: string
          last_attempted_run: string | null
          last_run_at: string | null
          last_successful_run: string | null
          max_consecutive_failures: number | null
          metadata: Json | null
          next_scheduled_run: string | null
          schedule_type: string
          schedule_value: string
          updated_at: string | null
        }
        Insert: {
          auto_retry_on_startup?: boolean | null
          consecutive_failures?: number | null
          created_at?: string | null
          enabled?: boolean | null
          id?: string
          job_function: string
          job_id: string
          job_name: string
          last_attempted_run?: string | null
          last_run_at?: string | null
          last_successful_run?: string | null
          max_consecutive_failures?: number | null
          metadata?: Json | null
          next_scheduled_run?: string | null
          schedule_type: string
          schedule_value: string
          updated_at?: string | null
        }
        Update: {
          auto_retry_on_startup?: boolean | null
          consecutive_failures?: number | null
          created_at?: string | null
          enabled?: boolean | null
          id?: string
          job_function?: string
          job_id?: string
          job_name?: string
          last_attempted_run?: string | null
          last_run_at?: string | null
          last_successful_run?: string | null
          max_consecutive_failures?: number | null
          metadata?: Json | null
          next_scheduled_run?: string | null
          schedule_type?: string
          schedule_value?: string
          updated_at?: string | null
        }
        Relationships: []
      }
      schema_migrations: {
        Row: {
          inserted_at: string | null
          version: number
        }
        Insert: {
          inserted_at?: string | null
          version: number
        }
        Update: {
          inserted_at?: string | null
          version?: number
        }
        Relationships: []
      }
      shell_aliases: {
        Row: {
          alias_name: string
          alias_value: string
          created_at: string | null
          description: string | null
          id: string
          is_active: boolean | null
          updated_at: string | null
          user_id: string | null
        }
        Insert: {
          alias_name: string
          alias_value: string
          created_at?: string | null
          description?: string | null
          id?: string
          is_active?: boolean | null
          updated_at?: string | null
          user_id?: string | null
        }
        Update: {
          alias_name?: string
          alias_value?: string
          created_at?: string | null
          description?: string | null
          id?: string
          is_active?: boolean | null
          updated_at?: string | null
          user_id?: string | null
        }
        Relationships: []
      }
      shell_completions: {
        Row: {
          command: string
          completion_pattern: string
          completion_type: string
          created_at: string | null
          description: string | null
          id: string
          is_active: boolean | null
          updated_at: string | null
          user_id: string | null
        }
        Insert: {
          command: string
          completion_pattern: string
          completion_type: string
          created_at?: string | null
          description?: string | null
          id?: string
          is_active?: boolean | null
          updated_at?: string | null
          user_id?: string | null
        }
        Update: {
          command?: string
          completion_pattern?: string
          completion_type?: string
          created_at?: string | null
          description?: string | null
          id?: string
          is_active?: boolean | null
          updated_at?: string | null
          user_id?: string | null
        }
        Relationships: []
      }
      shell_configuration: {
        Row: {
          config_key: string
          config_type: string
          config_value: string
          created_at: string | null
          description: string | null
          id: string
          is_default: boolean | null
          updated_at: string | null
          user_id: string | null
        }
        Insert: {
          config_key: string
          config_type: string
          config_value: string
          created_at?: string | null
          description?: string | null
          id?: string
          is_default?: boolean | null
          updated_at?: string | null
          user_id?: string | null
        }
        Update: {
          config_key?: string
          config_type?: string
          config_value?: string
          created_at?: string | null
          description?: string | null
          id?: string
          is_default?: boolean | null
          updated_at?: string | null
          user_id?: string | null
        }
        Relationships: []
      }
      shell_functions: {
        Row: {
          created_at: string | null
          description: string | null
          function_body: string
          function_name: string
          id: string
          is_active: boolean | null
          updated_at: string | null
          user_id: string | null
        }
        Insert: {
          created_at?: string | null
          description?: string | null
          function_body: string
          function_name: string
          id?: string
          is_active?: boolean | null
          updated_at?: string | null
          user_id?: string | null
        }
        Update: {
          created_at?: string | null
          description?: string | null
          function_body?: string
          function_name?: string
          id?: string
          is_active?: boolean | null
          updated_at?: string | null
          user_id?: string | null
        }
        Relationships: []
      }
      shell_history: {
        Row: {
          command: string
          created_at: string | null
          duration_ms: number | null
          exit_code: number | null
          hostname: string
          id: string
          session_id: string
          timestamp: string
          updated_at: string | null
          user_id: string | null
          working_directory: string
        }
        Insert: {
          command: string
          created_at?: string | null
          duration_ms?: number | null
          exit_code?: number | null
          hostname: string
          id?: string
          session_id: string
          timestamp: string
          updated_at?: string | null
          user_id?: string | null
          working_directory: string
        }
        Update: {
          command?: string
          created_at?: string | null
          duration_ms?: number | null
          exit_code?: number | null
          hostname?: string
          id?: string
          session_id?: string
          timestamp?: string
          updated_at?: string | null
          user_id?: string | null
          working_directory?: string
        }
        Relationships: []
      }
      shell_jobs: {
        Row: {
          command: string
          completed_at: string | null
          created_at: string | null
          error: string | null
          exit_code: number | null
          id: string
          job_id: string
          output: string | null
          pid: number | null
          session_id: string
          started_at: string
          status: string
          updated_at: string | null
          user_id: string | null
          working_directory: string
        }
        Insert: {
          command: string
          completed_at?: string | null
          created_at?: string | null
          error?: string | null
          exit_code?: number | null
          id?: string
          job_id: string
          output?: string | null
          pid?: number | null
          session_id: string
          started_at: string
          status: string
          updated_at?: string | null
          user_id?: string | null
          working_directory: string
        }
        Update: {
          command?: string
          completed_at?: string | null
          created_at?: string | null
          error?: string | null
          exit_code?: number | null
          id?: string
          job_id?: string
          output?: string | null
          pid?: number | null
          session_id?: string
          started_at?: string
          status?: string
          updated_at?: string | null
          user_id?: string | null
          working_directory?: string
        }
        Relationships: []
      }
      shell_sessions: {
        Row: {
          created_at: string | null
          ended_at: string | null
          environment_variables: Json | null
          hostname: string
          id: string
          is_active: boolean | null
          session_id: string
          started_at: string
          updated_at: string | null
          user_id: string | null
          working_directory: string
        }
        Insert: {
          created_at?: string | null
          ended_at?: string | null
          environment_variables?: Json | null
          hostname: string
          id?: string
          is_active?: boolean | null
          session_id: string
          started_at: string
          updated_at?: string | null
          user_id?: string | null
          working_directory: string
        }
        Update: {
          created_at?: string | null
          ended_at?: string | null
          environment_variables?: Json | null
          hostname?: string
          id?: string
          is_active?: boolean | null
          session_id?: string
          started_at?: string
          updated_at?: string | null
          user_id?: string | null
          working_directory?: string
        }
        Relationships: []
      }
      signal_audit_trail: {
        Row: {
          created_at: string
          event_timestamp: string
          event_type: string
          feature_weights_hash: string | null
          id: string
          metadata: Json | null
          model_id: string | null
          model_version: string | null
          signal_id: string
          signal_snapshot: Json
          source_system: string
          triggered_by: string | null
        }
        Insert: {
          created_at?: string
          event_timestamp?: string
          event_type: string
          feature_weights_hash?: string | null
          id?: string
          metadata?: Json | null
          model_id?: string | null
          model_version?: string | null
          signal_id: string
          signal_snapshot: Json
          source_system?: string
          triggered_by?: string | null
        }
        Update: {
          created_at?: string
          event_timestamp?: string
          event_type?: string
          feature_weights_hash?: string | null
          id?: string
          metadata?: Json | null
          model_id?: string | null
          model_version?: string | null
          signal_id?: string
          signal_snapshot?: Json
          source_system?: string
          triggered_by?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "signal_audit_trail_model_id_fkey"
            columns: ["model_id"]
            isOneToOne: false
            referencedRelation: "ml_models"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "signal_audit_trail_signal_id_fkey"
            columns: ["signal_id"]
            isOneToOne: false
            referencedRelation: "trading_signals"
            referencedColumns: ["id"]
          },
        ]
      }
      signal_audit_trail_archive: {
        Row: {
          created_at: string
          event_timestamp: string
          event_type: string
          feature_weights_hash: string | null
          id: string
          metadata: Json | null
          model_id: string | null
          model_version: string | null
          signal_id: string
          signal_snapshot: Json
          source_system: string
          triggered_by: string | null
        }
        Insert: {
          created_at?: string
          event_timestamp?: string
          event_type: string
          feature_weights_hash?: string | null
          id?: string
          metadata?: Json | null
          model_id?: string | null
          model_version?: string | null
          signal_id: string
          signal_snapshot: Json
          source_system?: string
          triggered_by?: string | null
        }
        Update: {
          created_at?: string
          event_timestamp?: string
          event_type?: string
          feature_weights_hash?: string | null
          id?: string
          metadata?: Json | null
          model_id?: string | null
          model_version?: string | null
          signal_id?: string
          signal_snapshot?: Json
          source_system?: string
          triggered_by?: string | null
        }
        Relationships: []
      }
      signal_lifecycle: {
        Row: {
          created_at: string | null
          current_state: string
          id: string
          order_id: string | null
          position_id: string | null
          previous_state: string | null
          signal_id: string
          transition_metadata: Json | null
          transition_reason: string | null
          transitioned_at: string
          transitioned_by: string | null
        }
        Insert: {
          created_at?: string | null
          current_state: string
          id?: string
          order_id?: string | null
          position_id?: string | null
          previous_state?: string | null
          signal_id: string
          transition_metadata?: Json | null
          transition_reason?: string | null
          transitioned_at?: string
          transitioned_by?: string | null
        }
        Update: {
          created_at?: string | null
          current_state?: string
          id?: string
          order_id?: string | null
          position_id?: string | null
          previous_state?: string | null
          signal_id?: string
          transition_metadata?: Json | null
          transition_reason?: string | null
          transitioned_at?: string
          transitioned_by?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "signal_lifecycle_order_id_fkey"
            columns: ["order_id"]
            isOneToOne: false
            referencedRelation: "trading_orders"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "signal_lifecycle_position_id_fkey"
            columns: ["position_id"]
            isOneToOne: false
            referencedRelation: "positions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "signal_lifecycle_signal_id_fkey"
            columns: ["signal_id"]
            isOneToOne: false
            referencedRelation: "trading_signals"
            referencedColumns: ["id"]
          },
        ]
      }
      signal_outcomes: {
        Row: {
          created_at: string | null
          entry_date: string | null
          entry_price: number | null
          exit_date: string | null
          exit_price: number | null
          exit_reason: string | null
          features: Json
          holding_days: number | null
          id: string
          ml_enhanced: boolean | null
          model_id: string | null
          model_version: string | null
          outcome: string | null
          position_id: string | null
          return_dollars: number | null
          return_pct: number | null
          signal_confidence: number | null
          signal_date: string | null
          signal_id: string | null
          signal_type: string
          ticker: string
          updated_at: string | null
        }
        Insert: {
          created_at?: string | null
          entry_date?: string | null
          entry_price?: number | null
          exit_date?: string | null
          exit_price?: number | null
          exit_reason?: string | null
          features?: Json
          holding_days?: number | null
          id?: string
          ml_enhanced?: boolean | null
          model_id?: string | null
          model_version?: string | null
          outcome?: string | null
          position_id?: string | null
          return_dollars?: number | null
          return_pct?: number | null
          signal_confidence?: number | null
          signal_date?: string | null
          signal_id?: string | null
          signal_type: string
          ticker: string
          updated_at?: string | null
        }
        Update: {
          created_at?: string | null
          entry_date?: string | null
          entry_price?: number | null
          exit_date?: string | null
          exit_price?: number | null
          exit_reason?: string | null
          features?: Json
          holding_days?: number | null
          id?: string
          ml_enhanced?: boolean | null
          model_id?: string | null
          model_version?: string | null
          outcome?: string | null
          position_id?: string | null
          return_dollars?: number | null
          return_pct?: number | null
          signal_confidence?: number | null
          signal_date?: string | null
          signal_id?: string | null
          signal_type?: string
          ticker?: string
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "signal_outcomes_model_id_fkey"
            columns: ["model_id"]
            isOneToOne: false
            referencedRelation: "ml_models"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "signal_outcomes_position_id_fkey"
            columns: ["position_id"]
            isOneToOne: false
            referencedRelation: "reference_portfolio_positions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "signal_outcomes_signal_id_fkey"
            columns: ["signal_id"]
            isOneToOne: false
            referencedRelation: "trading_signals"
            referencedColumns: ["id"]
          },
        ]
      }
      signal_weight_presets: {
        Row: {
          author_name: string | null
          base_confidence: number
          bipartisan_bonus: number
          buy_threshold: number
          created_at: string
          description: string | null
          id: string
          is_public: boolean | null
          moderate_signal_bonus: number
          name: string
          politician_count_2: number
          politician_count_3_4: number
          politician_count_5_plus: number
          recent_activity_2_4: number
          recent_activity_5_plus: number
          sell_threshold: number
          strong_buy_threshold: number
          strong_sell_threshold: number
          strong_signal_bonus: number
          updated_at: string
          user_id: string | null
          user_lambda: string | null
          volume_100k_plus: number
          volume_1m_plus: number
        }
        Insert: {
          author_name?: string | null
          base_confidence?: number
          bipartisan_bonus?: number
          buy_threshold?: number
          created_at?: string
          description?: string | null
          id?: string
          is_public?: boolean | null
          moderate_signal_bonus?: number
          name: string
          politician_count_2?: number
          politician_count_3_4?: number
          politician_count_5_plus?: number
          recent_activity_2_4?: number
          recent_activity_5_plus?: number
          sell_threshold?: number
          strong_buy_threshold?: number
          strong_sell_threshold?: number
          strong_signal_bonus?: number
          updated_at?: string
          user_id?: string | null
          user_lambda?: string | null
          volume_100k_plus?: number
          volume_1m_plus?: number
        }
        Update: {
          author_name?: string | null
          base_confidence?: number
          bipartisan_bonus?: number
          buy_threshold?: number
          created_at?: string
          description?: string | null
          id?: string
          is_public?: boolean | null
          moderate_signal_bonus?: number
          name?: string
          politician_count_2?: number
          politician_count_3_4?: number
          politician_count_5_plus?: number
          recent_activity_2_4?: number
          recent_activity_5_plus?: number
          sell_threshold?: number
          strong_buy_threshold?: number
          strong_sell_threshold?: number
          strong_signal_bonus?: number
          updated_at?: string
          user_id?: string | null
          user_lambda?: string | null
          volume_100k_plus?: number
          volume_1m_plus?: number
        }
        Relationships: []
      }
      stored_files: {
        Row: {
          created_at: string | null
          disclosure_id: string | null
          download_date: string
          expires_at: string | null
          file_hash_sha256: string | null
          file_size_bytes: number | null
          file_type: string
          id: string
          is_archived: boolean | null
          mime_type: string | null
          parse_date: string | null
          parse_error: string | null
          parse_status: string | null
          source_type: string | null
          source_url: string | null
          storage_bucket: string
          storage_path: string
          transactions_found: number | null
          updated_at: string | null
        }
        Insert: {
          created_at?: string | null
          disclosure_id?: string | null
          download_date?: string
          expires_at?: string | null
          file_hash_sha256?: string | null
          file_size_bytes?: number | null
          file_type: string
          id?: string
          is_archived?: boolean | null
          mime_type?: string | null
          parse_date?: string | null
          parse_error?: string | null
          parse_status?: string | null
          source_type?: string | null
          source_url?: string | null
          storage_bucket: string
          storage_path: string
          transactions_found?: number | null
          updated_at?: string | null
        }
        Update: {
          created_at?: string | null
          disclosure_id?: string | null
          download_date?: string
          expires_at?: string | null
          file_hash_sha256?: string | null
          file_size_bytes?: number | null
          file_type?: string
          id?: string
          is_archived?: boolean | null
          mime_type?: string | null
          parse_date?: string | null
          parse_error?: string | null
          parse_status?: string | null
          source_type?: string | null
          source_url?: string | null
          storage_bucket?: string
          storage_path?: string
          transactions_found?: number | null
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "stored_files_disclosure_id_fkey"
            columns: ["disclosure_id"]
            isOneToOne: false
            referencedRelation: "trading_disclosures"
            referencedColumns: ["id"]
          },
        ]
      }
      strategy_likes: {
        Row: {
          created_at: string | null
          id: string
          preset_id: string
          user_id: string
        }
        Insert: {
          created_at?: string | null
          id?: string
          preset_id: string
          user_id: string
        }
        Update: {
          created_at?: string | null
          id?: string
          preset_id?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "strategy_likes_preset_id_fkey"
            columns: ["preset_id"]
            isOneToOne: false
            referencedRelation: "signal_weight_presets"
            referencedColumns: ["id"]
          },
        ]
      }
      sync_logs: {
        Row: {
          completed_at: string | null
          created_at: string | null
          details: Json | null
          error_message: string | null
          id: string
          records_failed: number | null
          records_found: number | null
          records_new: number | null
          records_processed: number | null
          records_updated: number | null
          source: string
          started_at: string | null
          status: string
          sync_type: string | null
        }
        Insert: {
          completed_at?: string | null
          created_at?: string | null
          details?: Json | null
          error_message?: string | null
          id?: string
          records_failed?: number | null
          records_found?: number | null
          records_new?: number | null
          records_processed?: number | null
          records_updated?: number | null
          source: string
          started_at?: string | null
          status: string
          sync_type?: string | null
        }
        Update: {
          completed_at?: string | null
          created_at?: string | null
          details?: Json | null
          error_message?: string | null
          id?: string
          records_failed?: number | null
          records_found?: number | null
          records_new?: number | null
          records_processed?: number | null
          records_updated?: number | null
          source?: string
          started_at?: string | null
          status?: string
          sync_type?: string | null
        }
        Relationships: []
      }
      trade_validation_results: {
        Row: {
          chamber: string | null
          created_at: string | null
          field_mismatches: Json | null
          id: string
          match_key: string | null
          politician_name: string | null
          quiver_record: Json | null
          resolution_notes: string | null
          resolved_at: string | null
          root_cause: string | null
          severity: string | null
          ticker: string | null
          trading_disclosure_id: string | null
          transaction_date: string | null
          transaction_type: string | null
          updated_at: string | null
          validated_at: string | null
          validation_status: string
        }
        Insert: {
          chamber?: string | null
          created_at?: string | null
          field_mismatches?: Json | null
          id?: string
          match_key?: string | null
          politician_name?: string | null
          quiver_record?: Json | null
          resolution_notes?: string | null
          resolved_at?: string | null
          root_cause?: string | null
          severity?: string | null
          ticker?: string | null
          trading_disclosure_id?: string | null
          transaction_date?: string | null
          transaction_type?: string | null
          updated_at?: string | null
          validated_at?: string | null
          validation_status: string
        }
        Update: {
          chamber?: string | null
          created_at?: string | null
          field_mismatches?: Json | null
          id?: string
          match_key?: string | null
          politician_name?: string | null
          quiver_record?: Json | null
          resolution_notes?: string | null
          resolved_at?: string | null
          root_cause?: string | null
          severity?: string | null
          ticker?: string | null
          trading_disclosure_id?: string | null
          transaction_date?: string | null
          transaction_type?: string | null
          updated_at?: string | null
          validated_at?: string | null
          validation_status?: string
        }
        Relationships: [
          {
            foreignKeyName: "trade_validation_results_trading_disclosure_id_fkey"
            columns: ["trading_disclosure_id"]
            isOneToOne: false
            referencedRelation: "trading_disclosures"
            referencedColumns: ["id"]
          },
        ]
      }
      trades: {
        Row: {
          amount: string | null
          amount_max: number | null
          amount_min: number | null
          amount_range: string | null
          asset_description: string | null
          asset_type: string | null
          chamber: string | null
          company: string | null
          created_at: string | null
          disclosure_date: string | null
          estimated_value: number | null
          filing_date: string | null
          id: string
          party: string | null
          politician_id: string | null
          politician_name: string | null
          price: number | null
          raw_data: Json | null
          source: string | null
          source_url: string | null
          state: string | null
          ticker: string | null
          trade_type: string | null
          transaction_date: string
          transaction_type: string
          updated_at: string | null
        }
        Insert: {
          amount?: string | null
          amount_max?: number | null
          amount_min?: number | null
          amount_range?: string | null
          asset_description?: string | null
          asset_type?: string | null
          chamber?: string | null
          company?: string | null
          created_at?: string | null
          disclosure_date?: string | null
          estimated_value?: number | null
          filing_date?: string | null
          id?: string
          party?: string | null
          politician_id?: string | null
          politician_name?: string | null
          price?: number | null
          raw_data?: Json | null
          source?: string | null
          source_url?: string | null
          state?: string | null
          ticker?: string | null
          trade_type?: string | null
          transaction_date: string
          transaction_type: string
          updated_at?: string | null
        }
        Update: {
          amount?: string | null
          amount_max?: number | null
          amount_min?: number | null
          amount_range?: string | null
          asset_description?: string | null
          asset_type?: string | null
          chamber?: string | null
          company?: string | null
          created_at?: string | null
          disclosure_date?: string | null
          estimated_value?: number | null
          filing_date?: string | null
          id?: string
          party?: string | null
          politician_id?: string | null
          politician_name?: string | null
          price?: number | null
          raw_data?: Json | null
          source?: string | null
          source_url?: string | null
          state?: string | null
          ticker?: string | null
          trade_type?: string | null
          transaction_date?: string
          transaction_type?: string
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "trades_politician_id_fkey"
            columns: ["politician_id"]
            isOneToOne: false
            referencedRelation: "politicians"
            referencedColumns: ["id"]
          },
        ]
      }
      trading_accounts: {
        Row: {
          account_name: string
          account_type: string
          alpaca_api_key: string | null
          alpaca_base_url: string | null
          alpaca_secret_key: string | null
          created_at: string | null
          id: string
          is_active: boolean | null
          max_portfolio_risk: number | null
          max_position_size: number | null
          paper_trading: boolean | null
          risk_level: string | null
          updated_at: string | null
          user_id: string | null
        }
        Insert: {
          account_name: string
          account_type?: string
          alpaca_api_key?: string | null
          alpaca_base_url?: string | null
          alpaca_secret_key?: string | null
          created_at?: string | null
          id?: string
          is_active?: boolean | null
          max_portfolio_risk?: number | null
          max_position_size?: number | null
          paper_trading?: boolean | null
          risk_level?: string | null
          updated_at?: string | null
          user_id?: string | null
        }
        Update: {
          account_name?: string
          account_type?: string
          alpaca_api_key?: string | null
          alpaca_base_url?: string | null
          alpaca_secret_key?: string | null
          created_at?: string | null
          id?: string
          is_active?: boolean | null
          max_portfolio_risk?: number | null
          max_position_size?: number | null
          paper_trading?: boolean | null
          risk_level?: string | null
          updated_at?: string | null
          user_id?: string | null
        }
        Relationships: []
      }
      trading_disclosures: {
        Row: {
          amount_exact: number | null
          amount_range_max: number | null
          amount_range_min: number | null
          asset_name: string
          asset_owner: string | null
          asset_ticker: string | null
          asset_type: string | null
          comments: string | null
          created_at: string | null
          deleted_at: string | null
          disclosure_date: string
          filer_id: string | null
          filing_date: string | null
          has_parsed_data: boolean | null
          has_raw_pdf: boolean | null
          id: string
          is_range: boolean | null
          period_end_date: string | null
          period_start_date: string | null
          politician_id: string
          price_per_unit: number | null
          processing_notes: string | null
          quantity: number | null
          quiver_validated_at: string | null
          quiver_validation_status: string | null
          raw_data: Json | null
          raw_pdf_text: string | null
          source_document_id: string | null
          source_file_id: string | null
          source_url: string | null
          status: string | null
          ticker_confidence_score: number | null
          transaction_date: string
          transaction_type: string
          updated_at: string | null
          validation_flags: Json | null
        }
        Insert: {
          amount_exact?: number | null
          amount_range_max?: number | null
          amount_range_min?: number | null
          asset_name: string
          asset_owner?: string | null
          asset_ticker?: string | null
          asset_type?: string | null
          comments?: string | null
          created_at?: string | null
          deleted_at?: string | null
          disclosure_date: string
          filer_id?: string | null
          filing_date?: string | null
          has_parsed_data?: boolean | null
          has_raw_pdf?: boolean | null
          id?: string
          is_range?: boolean | null
          period_end_date?: string | null
          period_start_date?: string | null
          politician_id: string
          price_per_unit?: number | null
          processing_notes?: string | null
          quantity?: number | null
          quiver_validated_at?: string | null
          quiver_validation_status?: string | null
          raw_data?: Json | null
          raw_pdf_text?: string | null
          source_document_id?: string | null
          source_file_id?: string | null
          source_url?: string | null
          status?: string | null
          ticker_confidence_score?: number | null
          transaction_date: string
          transaction_type: string
          updated_at?: string | null
          validation_flags?: Json | null
        }
        Update: {
          amount_exact?: number | null
          amount_range_max?: number | null
          amount_range_min?: number | null
          asset_name?: string
          asset_owner?: string | null
          asset_ticker?: string | null
          asset_type?: string | null
          comments?: string | null
          created_at?: string | null
          deleted_at?: string | null
          disclosure_date?: string
          filer_id?: string | null
          filing_date?: string | null
          has_parsed_data?: boolean | null
          has_raw_pdf?: boolean | null
          id?: string
          is_range?: boolean | null
          period_end_date?: string | null
          period_start_date?: string | null
          politician_id?: string
          price_per_unit?: number | null
          processing_notes?: string | null
          quantity?: number | null
          quiver_validated_at?: string | null
          quiver_validation_status?: string | null
          raw_data?: Json | null
          raw_pdf_text?: string | null
          source_document_id?: string | null
          source_file_id?: string | null
          source_url?: string | null
          status?: string | null
          ticker_confidence_score?: number | null
          transaction_date?: string
          transaction_type?: string
          updated_at?: string | null
          validation_flags?: Json | null
        }
        Relationships: [
          {
            foreignKeyName: "trading_disclosures_politician_id_fkey"
            columns: ["politician_id"]
            isOneToOne: false
            referencedRelation: "politicians"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "trading_disclosures_source_file_id_fkey"
            columns: ["source_file_id"]
            isOneToOne: false
            referencedRelation: "stored_files"
            referencedColumns: ["id"]
          },
        ]
      }
      trading_orders: {
        Row: {
          alpaca_client_order_id: string | null
          alpaca_order_id: string | null
          broker: string | null
          canceled_at: string | null
          commission: number | null
          created_at: string | null
          error_message: string | null
          expired_at: string | null
          external_order_id: string | null
          filled_at: string | null
          filled_avg_price: number | null
          filled_quantity: number | null
          id: string
          idempotency_key: string | null
          last_state_transition_at: string | null
          limit_price: number | null
          metadata: Json | null
          notes: string | null
          order_type: string
          quantity: number
          reject_reason: string | null
          side: string
          signal_id: string | null
          state_machine_version: number | null
          status: string | null
          stop_price: number | null
          submitted_at: string | null
          ticker: string
          trading_mode: string
          trailing_percent: number | null
          updated_at: string | null
          user_id: string | null
        }
        Insert: {
          alpaca_client_order_id?: string | null
          alpaca_order_id?: string | null
          broker?: string | null
          canceled_at?: string | null
          commission?: number | null
          created_at?: string | null
          error_message?: string | null
          expired_at?: string | null
          external_order_id?: string | null
          filled_at?: string | null
          filled_avg_price?: number | null
          filled_quantity?: number | null
          id?: string
          idempotency_key?: string | null
          last_state_transition_at?: string | null
          limit_price?: number | null
          metadata?: Json | null
          notes?: string | null
          order_type: string
          quantity: number
          reject_reason?: string | null
          side: string
          signal_id?: string | null
          state_machine_version?: number | null
          status?: string | null
          stop_price?: number | null
          submitted_at?: string | null
          ticker: string
          trading_mode?: string
          trailing_percent?: number | null
          updated_at?: string | null
          user_id?: string | null
        }
        Update: {
          alpaca_client_order_id?: string | null
          alpaca_order_id?: string | null
          broker?: string | null
          canceled_at?: string | null
          commission?: number | null
          created_at?: string | null
          error_message?: string | null
          expired_at?: string | null
          external_order_id?: string | null
          filled_at?: string | null
          filled_avg_price?: number | null
          filled_quantity?: number | null
          id?: string
          idempotency_key?: string | null
          last_state_transition_at?: string | null
          limit_price?: number | null
          metadata?: Json | null
          notes?: string | null
          order_type?: string
          quantity?: number
          reject_reason?: string | null
          side?: string
          signal_id?: string | null
          state_machine_version?: number | null
          status?: string | null
          stop_price?: number | null
          submitted_at?: string | null
          ticker?: string
          trading_mode?: string
          trailing_percent?: number | null
          updated_at?: string | null
          user_id?: string | null
        }
        Relationships: []
      }
      trading_signals: {
        Row: {
          analysis: Json | null
          asset_name: string
          avg_politician_return: number | null
          buy_sell_ratio: number | null
          confidence: number | null
          confidence_score: number
          created_at: string | null
          disclosure_ids: string[] | null
          expires_at: string | null
          feature_definition_id: string | null
          features: Json | null
          generated_at: string
          generation_context: Json | null
          id: string
          is_active: boolean | null
          ml_enhanced: boolean | null
          model_id: string | null
          model_version: string
          notes: string | null
          politician_activity_count: number | null
          politician_id: string | null
          politician_name: string | null
          reproducibility_hash: string | null
          signal_strength: string
          signal_type: string
          source: string | null
          stop_loss: number | null
          strength: number | null
          take_profit: number | null
          target_price: number | null
          ticker: string
          total_transaction_volume: number | null
          trade_id: string | null
          updated_at: string | null
          user_id: string | null
          valid_until: string | null
          weights_snapshot_id: string | null
        }
        Insert: {
          analysis?: Json | null
          asset_name?: string
          avg_politician_return?: number | null
          buy_sell_ratio?: number | null
          confidence?: number | null
          confidence_score?: number
          created_at?: string | null
          disclosure_ids?: string[] | null
          expires_at?: string | null
          feature_definition_id?: string | null
          features?: Json | null
          generated_at?: string
          generation_context?: Json | null
          id?: string
          is_active?: boolean | null
          ml_enhanced?: boolean | null
          model_id?: string | null
          model_version?: string
          notes?: string | null
          politician_activity_count?: number | null
          politician_id?: string | null
          politician_name?: string | null
          reproducibility_hash?: string | null
          signal_strength?: string
          signal_type: string
          source?: string | null
          stop_loss?: number | null
          strength?: number | null
          take_profit?: number | null
          target_price?: number | null
          ticker: string
          total_transaction_volume?: number | null
          trade_id?: string | null
          updated_at?: string | null
          user_id?: string | null
          valid_until?: string | null
          weights_snapshot_id?: string | null
        }
        Update: {
          analysis?: Json | null
          asset_name?: string
          avg_politician_return?: number | null
          buy_sell_ratio?: number | null
          confidence?: number | null
          confidence_score?: number
          created_at?: string | null
          disclosure_ids?: string[] | null
          expires_at?: string | null
          feature_definition_id?: string | null
          features?: Json | null
          generated_at?: string
          generation_context?: Json | null
          id?: string
          is_active?: boolean | null
          ml_enhanced?: boolean | null
          model_id?: string | null
          model_version?: string
          notes?: string | null
          politician_activity_count?: number | null
          politician_id?: string | null
          politician_name?: string | null
          reproducibility_hash?: string | null
          signal_strength?: string
          signal_type?: string
          source?: string | null
          stop_loss?: number | null
          strength?: number | null
          take_profit?: number | null
          target_price?: number | null
          ticker?: string
          total_transaction_volume?: number | null
          trade_id?: string | null
          updated_at?: string | null
          user_id?: string | null
          valid_until?: string | null
          weights_snapshot_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "trading_signals_feature_definition_id_fkey"
            columns: ["feature_definition_id"]
            isOneToOne: false
            referencedRelation: "feature_definitions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "trading_signals_model_id_fkey"
            columns: ["model_id"]
            isOneToOne: false
            referencedRelation: "ml_models"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "trading_signals_weights_snapshot_id_fkey"
            columns: ["weights_snapshot_id"]
            isOneToOne: false
            referencedRelation: "model_weights_snapshots"
            referencedColumns: ["id"]
          },
        ]
      }
      user_api_keys: {
        Row: {
          created_at: string | null
          id: string
          last_used_at: string | null
          live_api_key: string | null
          live_key_created_at: string | null
          live_secret_key: string | null
          live_validated_at: string | null
          paper_api_key: string | null
          paper_key_created_at: string | null
          paper_secret_key: string | null
          paper_validated_at: string | null
          quiverquant_api_key: string | null
          quiverquant_key_created_at: string | null
          quiverquant_validated_at: string | null
          rotation_reminder_sent_at: string | null
          stripe_customer_id: string | null
          stripe_subscription_id: string | null
          subscription_status: string | null
          subscription_tier: string | null
          supabase_anon_key: string | null
          supabase_key_created_at: string | null
          supabase_service_role_key: string | null
          supabase_url: string | null
          supabase_validated_at: string | null
          updated_at: string | null
          user_email: string
          user_name: string | null
        }
        Insert: {
          created_at?: string | null
          id?: string
          last_used_at?: string | null
          live_api_key?: string | null
          live_key_created_at?: string | null
          live_secret_key?: string | null
          live_validated_at?: string | null
          paper_api_key?: string | null
          paper_key_created_at?: string | null
          paper_secret_key?: string | null
          paper_validated_at?: string | null
          quiverquant_api_key?: string | null
          quiverquant_key_created_at?: string | null
          quiverquant_validated_at?: string | null
          rotation_reminder_sent_at?: string | null
          stripe_customer_id?: string | null
          stripe_subscription_id?: string | null
          subscription_status?: string | null
          subscription_tier?: string | null
          supabase_anon_key?: string | null
          supabase_key_created_at?: string | null
          supabase_service_role_key?: string | null
          supabase_url?: string | null
          supabase_validated_at?: string | null
          updated_at?: string | null
          user_email: string
          user_name?: string | null
        }
        Update: {
          created_at?: string | null
          id?: string
          last_used_at?: string | null
          live_api_key?: string | null
          live_key_created_at?: string | null
          live_secret_key?: string | null
          live_validated_at?: string | null
          paper_api_key?: string | null
          paper_key_created_at?: string | null
          paper_secret_key?: string | null
          paper_validated_at?: string | null
          quiverquant_api_key?: string | null
          quiverquant_key_created_at?: string | null
          quiverquant_validated_at?: string | null
          rotation_reminder_sent_at?: string | null
          stripe_customer_id?: string | null
          stripe_subscription_id?: string | null
          subscription_status?: string | null
          subscription_tier?: string | null
          supabase_anon_key?: string | null
          supabase_key_created_at?: string | null
          supabase_service_role_key?: string | null
          supabase_url?: string | null
          supabase_validated_at?: string | null
          updated_at?: string | null
          user_email?: string
          user_name?: string | null
        }
        Relationships: []
      }
      user_carts: {
        Row: {
          added_at: string
          asset_name: string | null
          bipartisan: boolean | null
          buy_sell_ratio: number | null
          confidence_score: number
          generated_at: string | null
          id: string
          politician_activity_count: number
          quantity: number
          signal_id: string
          signal_strength: string | null
          signal_type: string
          source: string
          target_price: number | null
          ticker: string
          total_transaction_volume: number | null
          updated_at: string
          user_id: string
        }
        Insert: {
          added_at?: string
          asset_name?: string | null
          bipartisan?: boolean | null
          buy_sell_ratio?: number | null
          confidence_score: number
          generated_at?: string | null
          id?: string
          politician_activity_count?: number
          quantity?: number
          signal_id: string
          signal_strength?: string | null
          signal_type: string
          source: string
          target_price?: number | null
          ticker: string
          total_transaction_volume?: number | null
          updated_at?: string
          user_id: string
        }
        Update: {
          added_at?: string
          asset_name?: string | null
          bipartisan?: boolean | null
          buy_sell_ratio?: number | null
          confidence_score?: number
          generated_at?: string | null
          id?: string
          politician_activity_count?: number
          quantity?: number
          signal_id?: string
          signal_strength?: string | null
          signal_type?: string
          source?: string
          target_price?: number | null
          ticker?: string
          total_transaction_volume?: number | null
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      user_error_reports: {
        Row: {
          admin_notes: string | null
          created_at: string | null
          description: string
          disclosure_id: string
          disclosure_snapshot: Json
          error_type: string
          id: string
          status: string | null
          updated_at: string | null
          user_id: string
        }
        Insert: {
          admin_notes?: string | null
          created_at?: string | null
          description: string
          disclosure_id: string
          disclosure_snapshot?: Json
          error_type: string
          id?: string
          status?: string | null
          updated_at?: string | null
          user_id: string
        }
        Update: {
          admin_notes?: string | null
          created_at?: string | null
          description?: string
          disclosure_id?: string
          disclosure_snapshot?: Json
          error_type?: string
          id?: string
          status?: string | null
          updated_at?: string | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "user_error_reports_disclosure_id_fkey"
            columns: ["disclosure_id"]
            isOneToOne: false
            referencedRelation: "trading_disclosures"
            referencedColumns: ["id"]
          },
        ]
      }
      user_roles: {
        Row: {
          created_at: string | null
          id: string
          role: string
          updated_at: string | null
          user_id: string
        }
        Insert: {
          created_at?: string | null
          id?: string
          role: string
          updated_at?: string | null
          user_id: string
        }
        Update: {
          created_at?: string | null
          id?: string
          role?: string
          updated_at?: string | null
          user_id?: string
        }
        Relationships: []
      }
      user_sessions: {
        Row: {
          created_at: string | null
          expires_at: string | null
          id: string
          ip_address: unknown
          is_active: boolean | null
          last_activity: string | null
          login_time: string | null
          logout_time: string | null
          session_data: Json | null
          session_id: string
          updated_at: string | null
          user_agent: string | null
          user_email: string
          user_name: string | null
        }
        Insert: {
          created_at?: string | null
          expires_at?: string | null
          id?: string
          ip_address?: unknown
          is_active?: boolean | null
          last_activity?: string | null
          login_time?: string | null
          logout_time?: string | null
          session_data?: Json | null
          session_id: string
          updated_at?: string | null
          user_agent?: string | null
          user_email: string
          user_name?: string | null
        }
        Update: {
          created_at?: string | null
          expires_at?: string | null
          id?: string
          ip_address?: unknown
          is_active?: boolean | null
          last_activity?: string | null
          login_time?: string | null
          logout_time?: string | null
          session_data?: Json | null
          session_id?: string
          updated_at?: string | null
          user_agent?: string | null
          user_email?: string
          user_name?: string | null
        }
        Relationships: []
      }
      user_strategy_subscriptions: {
        Row: {
          created_at: string | null
          custom_weights: Json | null
          id: string
          is_active: boolean | null
          last_synced_at: string | null
          preset_id: string | null
          strategy_type: string
          sync_existing_positions: boolean | null
          trading_mode: string
          updated_at: string | null
          user_email: string
        }
        Insert: {
          created_at?: string | null
          custom_weights?: Json | null
          id?: string
          is_active?: boolean | null
          last_synced_at?: string | null
          preset_id?: string | null
          strategy_type: string
          sync_existing_positions?: boolean | null
          trading_mode?: string
          updated_at?: string | null
          user_email: string
        }
        Update: {
          created_at?: string | null
          custom_weights?: Json | null
          id?: string
          is_active?: boolean | null
          last_synced_at?: string | null
          preset_id?: string | null
          strategy_type?: string
          sync_existing_positions?: boolean | null
          trading_mode?: string
          updated_at?: string | null
          user_email?: string
        }
        Relationships: [
          {
            foreignKeyName: "user_strategy_subscriptions_preset_id_fkey"
            columns: ["preset_id"]
            isOneToOne: false
            referencedRelation: "signal_weight_presets"
            referencedColumns: ["id"]
          },
        ]
      }
      user_strategy_trades: {
        Row: {
          alpaca_order_id: string | null
          confidence_score: number | null
          created_at: string | null
          error_message: string | null
          executed_at: string | null
          id: string
          quantity: number
          side: string
          signal_type: string | null
          source_preset_id: string | null
          source_signal_id: string | null
          status: string | null
          subscription_id: string
          ticker: string
          user_email: string
        }
        Insert: {
          alpaca_order_id?: string | null
          confidence_score?: number | null
          created_at?: string | null
          error_message?: string | null
          executed_at?: string | null
          id?: string
          quantity: number
          side: string
          signal_type?: string | null
          source_preset_id?: string | null
          source_signal_id?: string | null
          status?: string | null
          subscription_id: string
          ticker: string
          user_email: string
        }
        Update: {
          alpaca_order_id?: string | null
          confidence_score?: number | null
          created_at?: string | null
          error_message?: string | null
          executed_at?: string | null
          id?: string
          quantity?: number
          side?: string
          signal_type?: string | null
          source_preset_id?: string | null
          source_signal_id?: string | null
          status?: string | null
          subscription_id?: string
          ticker?: string
          user_email?: string
        }
        Relationships: [
          {
            foreignKeyName: "user_strategy_trades_subscription_id_fkey"
            columns: ["subscription_id"]
            isOneToOne: false
            referencedRelation: "user_strategy_subscriptions"
            referencedColumns: ["id"]
          },
        ]
      }
      validation_fix_log: {
        Row: {
          action_type: string
          field_changed: string | null
          id: string
          new_value: string | null
          notes: string | null
          old_value: string | null
          performed_at: string | null
          performed_by: string | null
          revalidated: boolean | null
          revalidation_status: string | null
          trading_disclosure_id: string | null
          validation_result_id: string | null
        }
        Insert: {
          action_type: string
          field_changed?: string | null
          id?: string
          new_value?: string | null
          notes?: string | null
          old_value?: string | null
          performed_at?: string | null
          performed_by?: string | null
          revalidated?: boolean | null
          revalidation_status?: string | null
          trading_disclosure_id?: string | null
          validation_result_id?: string | null
        }
        Update: {
          action_type?: string
          field_changed?: string | null
          id?: string
          new_value?: string | null
          notes?: string | null
          old_value?: string | null
          performed_at?: string | null
          performed_by?: string | null
          revalidated?: boolean | null
          revalidation_status?: string | null
          trading_disclosure_id?: string | null
          validation_result_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "validation_fix_log_trading_disclosure_id_fkey"
            columns: ["trading_disclosure_id"]
            isOneToOne: false
            referencedRelation: "trading_disclosures"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "validation_fix_log_validation_result_id_fkey"
            columns: ["validation_result_id"]
            isOneToOne: false
            referencedRelation: "trade_validation_results"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      action_logs_summary: {
        Row: {
          action_type: string | null
          avg_duration_seconds: number | null
          completed_count: number | null
          failed_count: number | null
          first_occurrence: string | null
          last_occurrence: string | null
          source: string | null
          status: string | null
          total_count: number | null
        }
        Relationships: []
      }
      data_quality_metrics: {
        Row: {
          avg_duration_ms: number | null
          check_category: string | null
          check_date: string | null
          check_tier: number | null
          failed_checks: number | null
          passed_checks: number | null
          total_checks: number | null
          total_issues: number | null
          warning_checks: number | null
        }
        Relationships: []
      }
      feature_importance_latest: {
        Row: {
          analysis_date: string | null
          correlation_with_return: number | null
          feature_name: string | null
          feature_useful: boolean | null
          lift_pct: number | null
          recommended_weight: number | null
          sample_size_total: number | null
          win_rate_when_high: number | null
          win_rate_when_low: number | null
        }
        Insert: {
          analysis_date?: string | null
          correlation_with_return?: number | null
          feature_name?: string | null
          feature_useful?: boolean | null
          lift_pct?: number | null
          recommended_weight?: number | null
          sample_size_total?: number | null
          win_rate_when_high?: number | null
          win_rate_when_low?: number | null
        }
        Update: {
          analysis_date?: string | null
          correlation_with_return?: number | null
          feature_name?: string | null
          feature_useful?: boolean | null
          lift_pct?: number | null
          recommended_weight?: number | null
          sample_size_total?: number | null
          win_rate_when_high?: number | null
          win_rate_when_low?: number | null
        }
        Relationships: []
      }
      job_action_history: {
        Row: {
          action_details: Json | null
          action_timestamp: string | null
          action_type: string | null
          duration_seconds: number | null
          error_message: string | null
          id: string | null
          job_execution_id: string | null
          job_id: string | null
          job_name: string | null
          schedule_type: string | null
          status: string | null
        }
        Relationships: []
      }
      job_execution_summary: {
        Row: {
          avg_duration_seconds: number | null
          cancelled_executions: number | null
          failed_executions: number | null
          job_id: string | null
          last_execution: string | null
          max_duration_seconds: number | null
          min_duration_seconds: number | null
          successful_executions: number | null
          total_executions: number | null
        }
        Relationships: []
      }
      job_status_summary: {
        Row: {
          completed_jobs: number | null
          failed_jobs: number | null
          job_type: string | null
          last_run: string | null
          running_jobs: number | null
          total_jobs: number | null
          total_new_records: number | null
          total_updated_records: number | null
        }
        Relationships: []
      }
      lsh_job_stats: {
        Row: {
          avg_duration_ms: number | null
          avg_memory_mb: number | null
          failed_executions: number | null
          id: string | null
          job_name: string | null
          last_execution_at: string | null
          max_duration_ms: number | null
          max_memory_mb: number | null
          min_duration_ms: number | null
          running_executions: number | null
          status: string | null
          success_rate_percent: number | null
          successful_executions: number | null
          total_executions: number | null
          type: string | null
        }
        Relationships: []
      }
      lsh_recent_executions: {
        Row: {
          completed_at: string | null
          duration_ms: number | null
          error_message: string | null
          execution_id: string | null
          exit_code: number | null
          id: string | null
          job_id: string | null
          job_name: string | null
          retry_count: number | null
          started_at: string | null
          status: string | null
          triggered_by: string | null
        }
        Relationships: [
          {
            foreignKeyName: "lsh_job_executions_job_id_fkey"
            columns: ["job_id"]
            isOneToOne: false
            referencedRelation: "lsh_job_stats"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "lsh_job_executions_job_id_fkey"
            columns: ["job_id"]
            isOneToOne: false
            referencedRelation: "lsh_jobs"
            referencedColumns: ["id"]
          },
        ]
      }
      model_performance_comparison: {
        Row: {
          alpha: number | null
          avg_return_pct: number | null
          evaluation_date: string | null
          high_confidence_win_rate: number | null
          model_name: string | null
          model_version: string | null
          sharpe_ratio: number | null
          signals_traded: number | null
          win_rate: number | null
        }
        Relationships: []
      }
      outcome_summary_by_model: {
        Row: {
          avg_holding_days: number | null
          avg_return_pct: number | null
          losses: number | null
          ml_enhanced: boolean | null
          model_version: string | null
          total_trades: number | null
          win_rate: number | null
          wins: number | null
        }
        Relationships: []
      }
      recent_fixes: {
        Row: {
          action_type: string | null
          field_changed: string | null
          id: string | null
          match_key: string | null
          new_value: string | null
          notes: string | null
          old_value: string | null
          performed_at: string | null
          revalidation_status: string | null
          validation_status: string | null
        }
        Relationships: []
      }
      recent_trading_activity: {
        Row: {
          amount_exact: number | null
          amount_range_max: number | null
          amount_range_min: number | null
          asset_name: string | null
          asset_ticker: string | null
          created_at: string | null
          disclosure_date: string | null
          full_name: string | null
          party: string | null
          role: string | null
          state_or_country: string | null
          transaction_date: string | null
          transaction_type: string | null
        }
        Relationships: []
      }
      scheduled_jobs_status: {
        Row: {
          auto_retry_on_startup: boolean | null
          consecutive_failures: number | null
          enabled: boolean | null
          id: string | null
          job_id: string | null
          job_name: string | null
          job_status: string | null
          last_attempted_run: string | null
          last_execution_duration: number | null
          last_execution_error: string | null
          last_execution_status: string | null
          last_execution_time: string | null
          last_successful_run: string | null
          max_consecutive_failures: number | null
          next_scheduled_run: string | null
          schedule_type: string | null
          schedule_value: string | null
        }
        Relationships: []
      }
      storage_statistics: {
        Row: {
          file_count: number | null
          file_type: string | null
          newest_file: string | null
          oldest_file: string | null
          parse_status: string | null
          storage_bucket: string | null
          total_size_bytes: number | null
          total_size_mb: number | null
          unique_disclosures: number | null
        }
        Relationships: []
      }
      top_tickers: {
        Row: {
          name: string | null
          ticker: string | null
          total_volume: number | null
          trade_count: number | null
        }
        Relationships: []
      }
      user_activity_summary: {
        Row: {
          failed_actions: number | null
          first_activity: string | null
          last_activity: string | null
          successful_actions: number | null
          total_actions: number | null
          unique_action_types: number | null
          user_id: string | null
        }
        Relationships: []
      }
      v_active_sessions: {
        Row: {
          expires_at: string | null
          ip_address: unknown
          last_activity: string | null
          login_time: string | null
          minutes_since_activity: number | null
          user_email: string | null
          user_name: string | null
        }
        Insert: {
          expires_at?: string | null
          ip_address?: unknown
          last_activity?: string | null
          login_time?: string | null
          minutes_since_activity?: never
          user_email?: string | null
          user_name?: string | null
        }
        Update: {
          expires_at?: string | null
          ip_address?: unknown
          last_activity?: string | null
          login_time?: string | null
          minutes_since_activity?: never
          user_email?: string | null
          user_name?: string | null
        }
        Relationships: []
      }
      v_recent_trades: {
        Row: {
          amount: string | null
          asset_description: string | null
          created_at: string | null
          disclosure_date: string | null
          party: string | null
          politician_name: string | null
          position: string | null
          source: string | null
          state: string | null
          ticker: string | null
          transaction_date: string | null
          transaction_type: string | null
        }
        Relationships: []
      }
      validation_summary: {
        Row: {
          count: number | null
          last_validated: string | null
          root_cause: string | null
          severity: string | null
          unresolved_count: number | null
          validation_status: string | null
        }
        Relationships: []
      }
    }
    Functions: {
      archive_expired_files: { Args: never; Returns: number }
      archive_old_audit_records: {
        Args: never
        Returns: {
          archived_count: number
          deleted_from_archive: number
        }[]
      }
      calculate_next_run: {
        Args: {
          p_last_run: string
          p_schedule_type: string
          p_schedule_value: string
        }
        Returns: string
      }
      calculate_reference_position_size: {
        Args: {
          p_confidence: number
          p_current_price: number
          p_portfolio_value: number
        }
        Returns: number
      }
      can_execute_reference_trade: { Args: never; Returns: boolean }
      cleanup_ml_predictions_cache: { Args: never; Returns: number }
      cleanup_old_job_executions: { Args: never; Returns: undefined }
      count_disclosure_changes_since: {
        Args: { since_ts: string }
        Returns: number
      }
      get_active_ml_model: {
        Args: { p_model_type?: string }
        Returns: {
          feature_importance: Json
          id: string
          metrics: Json
          model_artifact_path: string
          model_name: string
          model_version: string
        }[]
      }
      get_connection_health_summary: {
        Args: never
        Returns: {
          connection_type: string
          last_checked: string
          latest_response_time_ms: number
          latest_status: string
          unhealthy_count_24h: number
        }[]
      }
      get_credential_health: {
        Args: { p_user_email: string }
        Returns: {
          credential_type: string
          days_since_creation: number
          days_until_rotation: number
          health_status: string
          is_configured: boolean
          last_validated: string
        }[]
      }
      get_drops_feed: {
        Args: {
          feed_type?: string
          limit_count?: number
          offset_count?: number
          user_id_param?: string
        }
        Returns: {
          author_email: string
          content: string
          created_at: string
          id: string
          is_public: boolean
          likes_count: number
          updated_at: string
          user_has_liked: boolean
          user_id: string
        }[]
      }
      get_files_to_parse: {
        Args: { p_bucket?: string; p_limit?: number }
        Returns: {
          disclosure_id: string
          download_date: string
          file_id: string
          source_url: string
          storage_path: string
        }[]
      }
      get_open_issues_summary: {
        Args: never
        Returns: {
          count: number
          severity: string
        }[]
      }
      get_public_strategies: {
        Args: { sort_by?: string; user_id_param?: string }
        Returns: {
          author_email: string
          author_name: string
          base_confidence: number
          bipartisan_bonus: number
          buy_threshold: number
          created_at: string
          description: string
          id: string
          is_public: boolean
          likes_count: number
          moderate_signal_bonus: number
          name: string
          politician_count_2: number
          politician_count_3_4: number
          politician_count_5_plus: number
          recent_activity_2_4: number
          recent_activity_5_plus: number
          sell_threshold: number
          strong_buy_threshold: number
          strong_sell_threshold: number
          strong_signal_bonus: number
          updated_at: string
          user_has_liked: boolean
          user_id: string
          user_lambda: string
          volume_100k_plus: number
          volume_1m_plus: number
        }[]
      }
      get_recent_check_results: {
        Args: { p_limit?: number }
        Returns: {
          check_id: string
          check_name: string
          check_tier: number
          duration_ms: number
          id: string
          issues_found: number
          started_at: string
          status: string
          summary: string
        }[]
      }
      get_recent_strategy_trades: {
        Args: { limit_param?: number; user_email_param: string }
        Returns: {
          alpaca_order_id: string
          confidence_score: number
          created_at: string
          error_message: string
          executed_at: string
          id: string
          quantity: number
          side: string
          signal_type: string
          status: string
          ticker: string
        }[]
      }
      get_retraining_stats: {
        Args: never
        Returns: {
          current_change_count: number
          last_check_at: string
          last_training_at: string
          threshold: number
        }[]
      }
      get_signal_lineage: {
        Args: { p_signal_id: string }
        Returns: {
          audit_events: Json
          confidence_score: number
          feature_version: string
          model_metrics: Json
          model_name: string
          model_version: string
          signal_id: string
          signal_type: string
          ticker: string
          weights_hash: string
        }[]
      }
      get_user_subscription: {
        Args: { user_email_param: string }
        Returns: {
          created_at: string
          custom_weights: Json
          id: string
          is_active: boolean
          last_synced_at: string
          preset_id: string
          preset_name: string
          strategy_type: string
          sync_existing_positions: boolean
          trading_mode: string
          updated_at: string
          user_email: string
        }[]
      }
      get_users_needing_rotation_reminder: {
        Args: never
        Returns: {
          credentials_expiring: string[]
          earliest_expiry_days: number
          user_email: string
          user_name: string
        }[]
      }
      has_role: { Args: { _role: string; _user_id: string }; Returns: boolean }
      invoke_edge_function: {
        Args: { body?: Json; function_path: string }
        Returns: undefined
      }
      invoke_scheduled_function: {
        Args: {
          function_name: string
          function_path?: string
          request_body?: Json
        }
        Returns: number
      }
      log_job_execution: {
        Args: {
          p_error_message?: string
          p_job_id: string
          p_records_processed?: number
          p_status: string
        }
        Returns: string
      }
      mark_file_failed: {
        Args: { p_error_message: string; p_file_id: string }
        Returns: undefined
      }
      mark_file_parsed: {
        Args: { p_file_id: string; p_transactions_count?: number }
        Returns: undefined
      }
      recalculate_portfolio_state: { Args: never; Returns: undefined }
      record_correction: {
        Args: {
          p_confidence: number
          p_correction_type: string
          p_field_name: string
          p_issue_id: string
          p_new_value: string
          p_old_value: string
          p_record_id: string
          p_table_name: string
        }
        Returns: string
      }
      record_quality_check: {
        Args: {
          p_check_id: string
          p_duration_ms: number
          p_issues_found: number
          p_records_checked: number
          p_status: string
          p_summary: string
        }
        Returns: string
      }
      record_quality_issue: {
        Args: {
          p_actual: string
          p_description: string
          p_expected: string
          p_field_name: string
          p_issue_type: string
          p_record_id: string
          p_result_id: string
          p_severity: string
          p_table_name: string
        }
        Returns: string
      }
      record_signal_audit: {
        Args: {
          p_event_type: string
          p_metadata?: Json
          p_signal_id: string
          p_source_system?: string
          p_triggered_by?: string
        }
        Returns: string
      }
      refresh_top_tickers: { Args: never; Returns: undefined }
      reset_reference_daily_trades: { Args: never; Returns: undefined }
      reset_retraining_stats: {
        Args: { training_ts: string }
        Returns: undefined
      }
      update_job_after_execution: {
        Args: { p_job_id: string; p_next_run?: string; p_success: boolean }
        Returns: undefined
      }
      update_retraining_check: { Args: never; Returns: undefined }
    }
    Enums: {
      [_ in never]: never
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
  graphql_public: {
    Enums: {},
  },
  public: {
    Enums: {},
  },
} as const
