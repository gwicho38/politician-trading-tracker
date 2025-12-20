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
        }
        Relationships: []
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
          limit_price: number | null
          metadata: Json | null
          notes: string | null
          order_type: string
          quantity: number
          reject_reason: string | null
          side: string
          signal_id: string | null
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
          limit_price?: number | null
          metadata?: Json | null
          notes?: string | null
          order_type: string
          quantity: number
          reject_reason?: string | null
          side: string
          signal_id?: string | null
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
          limit_price?: number | null
          metadata?: Json | null
          notes?: string | null
          order_type?: string
          quantity?: number
          reject_reason?: string | null
          side?: string
          signal_id?: string | null
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
          features: Json | null
          generated_at: string
          id: string
          is_active: boolean | null
          model_version: string
          notes: string | null
          politician_activity_count: number | null
          politician_id: string | null
          politician_name: string | null
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
          features?: Json | null
          generated_at?: string
          id?: string
          is_active?: boolean | null
          model_version?: string
          notes?: string | null
          politician_activity_count?: number | null
          politician_id?: string | null
          politician_name?: string | null
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
          features?: Json | null
          generated_at?: string
          id?: string
          is_active?: boolean | null
          model_version?: string
          notes?: string | null
          politician_activity_count?: number | null
          politician_id?: string | null
          politician_name?: string | null
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
        }
        Relationships: []
      }
      user_api_keys: {
        Row: {
          created_at: string | null
          id: string
          last_used_at: string | null
          live_api_key: string | null
          live_secret_key: string | null
          live_validated_at: string | null
          paper_api_key: string | null
          paper_secret_key: string | null
          paper_validated_at: string | null
          quiverquant_api_key: string | null
          quiverquant_validated_at: string | null
          stripe_customer_id: string | null
          stripe_subscription_id: string | null
          subscription_status: string | null
          subscription_tier: string | null
          supabase_anon_key: string | null
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
          live_secret_key?: string | null
          live_validated_at?: string | null
          paper_api_key?: string | null
          paper_secret_key?: string | null
          paper_validated_at?: string | null
          quiverquant_api_key?: string | null
          quiverquant_validated_at?: string | null
          stripe_customer_id?: string | null
          stripe_subscription_id?: string | null
          subscription_status?: string | null
          subscription_tier?: string | null
          supabase_anon_key?: string | null
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
          live_secret_key?: string | null
          live_validated_at?: string | null
          paper_api_key?: string | null
          paper_secret_key?: string | null
          paper_validated_at?: string | null
          quiverquant_api_key?: string | null
          quiverquant_validated_at?: string | null
          stripe_customer_id?: string | null
          stripe_subscription_id?: string | null
          subscription_status?: string | null
          subscription_tier?: string | null
          supabase_anon_key?: string | null
          supabase_service_role_key?: string | null
          supabase_url?: string | null
          supabase_validated_at?: string | null
          updated_at?: string | null
          user_email?: string
          user_name?: string | null
        }
        Relationships: []
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
    }
    Functions: {
      archive_expired_files: { Args: never; Returns: number }
      calculate_next_run: {
        Args: {
          p_last_run: string
          p_schedule_type: string
          p_schedule_value: string
        }
        Returns: string
      }
      cleanup_old_job_executions: { Args: never; Returns: undefined }
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
      has_role: { Args: { _role: string; _user_id: string }; Returns: boolean }
      invoke_edge_function: {
        Args: { body?: Json; function_path: string }
        Returns: undefined
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
      update_job_after_execution: {
        Args: { p_job_id: string; p_next_run?: string; p_success: boolean }
        Returns: undefined
      }
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
  public: {
    Enums: {},
  },
} as const
