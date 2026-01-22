# Function Review TODO

This document contains all functions across client, server, and etl-micro-service for manual review.

**Generated:** 2026-01-22

---

## Client (TypeScript/React)

### Components

#### ErrorBoundary.tsx
- [ ] `ErrorBoundary`
- [ ] `ErrorFallback`
- [ ] `MinimalErrorFallback`
- [ ] `withErrorBoundary`

#### NavLink.tsx
- [ ] `NavLink`

#### NotificationBell.tsx
- [ ] `NotificationBell`

#### PaginationControls.tsx
- [ ] `PaginationControls`

#### PoliticiansView.tsx
- [ ] `PoliticiansView`

#### RecentTrades.tsx
- [ ] `RecentTrades`

#### RootErrorBoundary.tsx
- [ ] `RootErrorBoundary`

#### StatsCard.tsx
- [ ] `StatsCard`

#### SyncStatus.tsx
- [ ] `useSyncStatus`
- [ ] `formatTimeAgo`
- [ ] `HeaderSyncStatus`
- [ ] `SidebarSyncStatus`

#### TopTickers.tsx
- [ ] `TopTickers`

#### TopTraders.tsx
- [ ] `TopTraders`

#### TradeCard.tsx
- [ ] `TradeCard`

#### TradeChart.tsx
- [ ] `CustomChartTooltip`
- [ ] `TradeChart`

#### TradesView.tsx
- [ ] `TradesView`

#### TradingSignals.tsx
- [ ] `TradingSignals`

#### VolumeChart.tsx
- [ ] `CustomVolumeTooltip`
- [ ] `VolumeChart`

### Admin Components

#### AdminAnalytics.tsx
- [ ] `AdminAnalytics`

#### AdminContentManagement.tsx
- [ ] `AdminContentManagement`

#### AdminNotifications.tsx
- [ ] `AdminNotifications`

#### AdminSyncStatus.tsx
- [ ] `AdminSyncStatus`

#### AdminUserManagement.tsx
- [ ] `AdminUserManagement`

#### PoliticianForm.tsx
- [ ] `PoliticianForm`

#### TradeForm.tsx
- [ ] `TradeForm`

### Cart Components

#### FloatingCart.tsx
- [ ] `getSignalIcon`
- [ ] `getSignalColor`
- [ ] `FloatingCart`

### Detail Modals

#### MonthDetailModal.tsx
- [ ] `MonthDetailModal`

#### PoliticianDetailModal.tsx
- [ ] `PoliticianDetailModal`

#### TickerDetailModal.tsx
- [ ] `TickerDetailModal`

### Trading Components

#### AccountDashboard.tsx
- [ ] `formatCurrency`
- [ ] `formatPercent`
- [ ] `AccountDashboard`

### Hooks

#### useDebounce.ts
- [ ] `useDebounce`

#### usePagination.ts
- [ ] `usePagination`

#### useAdmin.ts
- [ ] `useAdmin`

---

## Server (Elixir)

### Core Modules

#### Server (server.ex)
- [ ] `version/0`
- [ ] `health_check/0`

#### ServerWeb (server_web.ex)
- [ ] `static_paths/0`
- [ ] `router/0`
- [ ] `channel/0`
- [ ] `controller/0`
- [ ] `verified_routes/0`
- [ ] `__using__/1`

#### Server.Release (release.ex)
- [ ] `migrate/0`
- [ ] `rollback/2`
- [ ] `repos/0`
- [ ] `load_app/0`

#### Server.Application (application.ex)
- [ ] `start/2`
- [ ] `register_jobs/0`
- [ ] `config_change/3`

#### Server.SupabaseClient (supabase_client.ex)
- [ ] `invoke/2`
- [ ] `do_request/5`
- [ ] `parse_response/1`
- [ ] `get_service_key/0`

### Data Quality

#### Server.DataQuality.DigestStore (digest_store.ex)
- [ ] `start_link/1`
- [ ] `add_issue/1`
- [ ] `get_issues/0`
- [ ] `flush_issues/0`
- [ ] `get_counts/0`
- [ ] `clear/0`
- [ ] `init/1`
- [ ] `handle_cast/2`
- [ ] `handle_call/3`

#### Server.DataQuality.EmailAlerter (email_alerter.ex)
- [ ] `send_immediate/2`
- [ ] `queue_digest/1`
- [ ] `send_daily_digest/0`
- [ ] `send_weekly_summary/1`
- [ ] `render_critical_email/1`
- [ ] `render_critical_text/1`
- [ ] `render_digest_email/1`
- [ ] `render_severity_section/2`
- [ ] `render_digest_text/1`
- [ ] `render_weekly_email/1`
- [ ] `render_weekly_sections/1`
- [ ] `render_weekly_text/1`
- [ ] `render_weekly_text_sections/1`
- [ ] `email_enabled?/0`
- [ ] `from_email/0`
- [ ] `admin_email/0`
- [ ] `app_name/0`
- [ ] `normalize_severity/1`
- [ ] `severity_color/1`
- [ ] `severity_icon/1`
- [ ] `escape_html/1`
- [ ] `log_email_sent/2`
- [ ] `get_service_key/0`

### Scheduler

#### Server.Scheduler (scheduler.ex)
- [ ] `register_job/1`
- [ ] `register_jobs/1`
- [ ] `run_now/1`
- [ ] `enable_job/1`
- [ ] `disable_job/1`
- [ ] `list_jobs/0`
- [ ] `get_job_status/1`
- [ ] `get_executions/2`
- [ ] `child_spec/1`
- [ ] `quantum_jobs/0`

#### Server.Scheduler.Job (job.ex)
- [ ] `get_schedule_type/1`
- [ ] `enabled?/1`
- [ ] `get_metadata/1`

#### Server.Scheduler.API (api.ex)
- [ ] `register_job/1`
- [ ] `register_jobs/1`
- [ ] `run_now/1`
- [ ] `enable_job/1`
- [ ] `disable_job/1`
- [ ] `list_jobs/0`
- [ ] `get_job_status/1`
- [ ] `get_executions/2`
- [ ] `add_to_quantum/1`
- [ ] `execute_job_async/1`
- [ ] `execute_job/2`
- [ ] `update_job_enabled/2`

### Scheduler Jobs

#### SyncJob (sync_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `metadata/0`

#### SyncDataJob (sync_data_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `metadata/0`

#### PortfolioJob (portfolio_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `metadata/0`

#### PortfolioSnapshotJob (portfolio_snapshot_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `metadata/0`

#### OrdersJob (orders_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `metadata/0`

#### TradingSignalsJob (trading_signals_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `metadata/0`

#### SignalOutcomeJob (signal_outcome_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `metadata/0`

#### AlpacaAccountJob (alpaca_account_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `metadata/0`

#### ErrorReportsJob (error_reports_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `count_pending_reports/0`
- [ ] `process_reports/0`
- [ ] `get_service_key/0`
- [ ] `metadata/0`

#### EmailDigestJob (email_digest_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `schedule_type/0`
- [ ] `run/0`
- [ ] `metadata/0`

#### JobExecutionCleanupJob (job_execution_cleanup_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `trigger_cleanup/0`
- [ ] `metadata/0`

### Politician Trading Jobs

#### PoliticianTradingHouseJob (politician_trading_house_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `trigger_etl/0`
- [ ] `metadata/0`

#### PoliticianTradingSenateJob (politician_trading_senate_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `trigger_etl/0`
- [ ] `metadata/0`

#### PoliticianTradingQuiverJob (politician_trading_quiver_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `metadata/0`

#### PoliticianTradingCaliforniaJob (politician_trading_california_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `metadata/0`

#### PoliticianTradingEuJob (politician_trading_eu_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `metadata/0`

#### PoliticianTradingCollectJob (politician_trading_collect_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `metadata/0`

### Enrichment Jobs

#### BioguideEnrichmentJob (bioguide_enrichment_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `trigger_enrichment/0`
- [ ] `metadata/0`

#### PartyEnrichmentJob (party_enrichment_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `trigger_enrichment/0`
- [ ] `metadata/0`

#### TickerBackfillJob (ticker_backfill_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `trigger_backfill/0`
- [ ] `metadata/0`

#### PoliticianDedupJob (politician_dedup_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `trigger_dedup/0`
- [ ] `metadata/0`

### Data Quality Jobs

#### DataQualityTier1Job (data_quality_tier1_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `schedule_type/0`
- [ ] `run/0`
- [ ] `check_required_fields/0`
- [ ] `check_required_fields_via_rest/0`
- [ ] `check_etl_freshness/0`
- [ ] `stale_threshold/0`
- [ ] `check_orphaned_records/0`
- [ ] `check_orphaned_records_fallback/1`
- [ ] `check_constraints/0`
- [ ] `tomorrow/0`
- [ ] `count_records_with_filter/2`
- [ ] `call_supabase_rpc/2`
- [ ] `record_check_result/5`
- [ ] `send_critical_alert/1`
- [ ] `get_service_key/0`
- [ ] `metadata/0`

#### DataQualityTier2Job (data_quality_tier2_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `schedule_type/0`
- [ ] `run/0`
- [ ] `status_for_issues/1`
- [ ] `check_cross_source_reconciliation/0`
- [ ] `check_cross_source_fallback/1`
- [ ] `check_statistical_anomalies/0`
- [ ] `check_anomalies_simple/1`
- [ ] `check_ticker_validation/0`
- [ ] `days_ago/1`
- [ ] `record_check_result/5`
- [ ] `store_issues_for_digest/1`
- [ ] `get_service_key/0`
- [ ] `metadata/0`

#### DataQualityTier3Job (data_quality_tier3_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `schedule_type/0`
- [ ] `run/0`
- [ ] `status_for_issues/1`
- [ ] `audit_source_accuracy/0`
- [ ] `backtest_signal_accuracy/0`
- [ ] `backtest_signals_fallback/1`
- [ ] `triage_user_reports/0`
- [ ] `mark_reports_reviewed/2`
- [ ] `generate_weekly_summary/1`
- [ ] `get_weekly_metrics/0`
- [ ] `store_weekly_summary/1`
- [ ] `days_ago/1`
- [ ] `week_number/0`
- [ ] `record_check_result/5`
- [ ] `get_service_key/0`
- [ ] `metadata/0`

### ML Jobs

#### MlTrainingJob (ml_training_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `trigger_training/0`
- [ ] `trigger_manual/2`
- [ ] `check_status/1`
- [ ] `metadata/0`

#### BatchRetrainingJob (batch_retraining_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `schedule_type/0`
- [ ] `run/0`
- [ ] `get_retraining_stats/0`
- [ ] `parse_stats/1`
- [ ] `maybe_trigger_retrain/1`
- [ ] `trigger_training/0`
- [ ] `reset_stats_after_trigger/0`
- [ ] `get_service_key/0`
- [ ] `metadata/0`
- [ ] `check_status/0`
- [ ] `force_trigger/0`

#### ModelFeedbackRetrainJob (model_feedback_retrain_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `metadata/0`

#### FeatureAnalysisJob (feature_analysis_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `metadata/0`

### Reference Portfolio Jobs

#### ReferencePortfolioSyncJob (reference_portfolio_sync_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `sync_positions/0`
- [ ] `market_likely_open?/0`
- [ ] `metadata/0`

#### ReferencePortfolioExecuteJob (reference_portfolio_execute_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `execute_signals/0`
- [ ] `market_likely_open?/0`
- [ ] `metadata/0`

#### ReferencePortfolioDailyResetJob (reference_portfolio_daily_reset_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `metadata/0`

#### ReferencePortfolioExitCheckJob (reference_portfolio_exit_check_job.ex)
- [ ] `job_id/0`
- [ ] `job_name/0`
- [ ] `schedule/0`
- [ ] `run/0`
- [ ] `check_exits/0`
- [ ] `market_likely_open?/0`
- [ ] `metadata/0`

### Schemas

#### Server.Schemas.JobExecution (job_execution.ex)
- [ ] `changeset/2`
- [ ] `start_changeset/1`
- [ ] `complete_changeset/2`

#### Server.Schemas.ScheduledJob (scheduled_job.ex)
- [ ] `changeset/2`
- [ ] `update_execution_changeset/2`

### Controllers

#### ServerWeb.MlController (ml_controller.ex)
- [ ] `predict/2`
- [ ] `batch_predict/2`
- [ ] `list_models/2`
- [ ] `active_model/2`
- [ ] `show_model/2`
- [ ] `feature_importance/2`
- [ ] `trigger_training/2`
- [ ] `training_status/2`
- [ ] `health/2`
- [ ] `call_etl_predict/2`
- [ ] `call_etl_batch_predict/2`
- [ ] `call_etl_get/1`
- [ ] `call_etl_post/3`

#### ServerWeb.JobController (job_controller.ex)
- [ ] `index/2`
- [ ] `show/2`
- [ ] `run/2`
- [ ] `sync_status/2`
- [ ] `run_all/2`

#### ServerWeb.HealthController (health_controller.ex)
- [ ] `index/2`
- [ ] `ready/2`

#### ServerWeb.ErrorJSON (error_json.ex)
- [ ] `render/2`

### Web Infrastructure

#### ServerWeb.Telemetry (telemetry.ex)
- [ ] `start_link/1`
- [ ] `init/1`
- [ ] `metrics/0`
- [ ] `periodic_measurements/0`

#### ServerWeb.Endpoint (endpoint.ex)
- [ ] `cors_origin_allowed?/2`

---

## ETL Micro-Service (Python)

### Routes

#### quality.py
- [ ] `get_polygon_api_key`
- [ ] `validate_record_integrity`

#### etl.py
- [ ] `parse_pdf_url`

### Library Modules

#### pdf_utils.py
- [ ] `extract_text_from_pdf`
- [ ] `extract_tables_from_pdf`

#### registry.py
- [ ] `SourceRegistry.register`
- [ ] `SourceRegistry.get`
- [ ] `SourceRegistry.get_or_raise`
- [ ] `SourceRegistry.list_sources`
- [ ] `SourceRegistry.get_all_info`
- [ ] `SourceRegistry.create_instance`
- [ ] `SourceRegistry.clear`
- [ ] `SourceRegistry.is_registered`
- [ ] `_get_base_class`

#### database.py
- [ ] `get_supabase`
- [ ] `upload_transaction_to_supabase`

#### parser.py
- [ ] `extract_ticker_from_text`
- [ ] `sanitize_string`
- [ ] `parse_value_range`
- [ ] `parse_asset_type`
- [ ] `clean_asset_name`
- [ ] `is_header_row`
- [ ] `normalize_name`

#### base_etl.py
- [ ] `ETLResult.duration_seconds` (property)
- [ ] `ETLResult.success_rate` (property)
- [ ] `ETLResult.is_success` (property)
- [ ] `ETLResult.add_error`
- [ ] `ETLResult.add_warning`
- [ ] `ETLResult.to_dict`
- [ ] `BaseETL.__init__`
- [ ] `BaseETL.get_job_status`
- [ ] `BaseETL.update_job_status`
- [ ] `BaseETL.__repr__`

#### job_logger.py
- [ ] `log_job_execution`
- [ ] `cleanup_old_executions`
- [ ] `JobLogger.__init__`
- [ ] `JobLogger.add_metadata`
- [ ] `JobLogger.set_error`

#### politician.py
- [ ] `find_or_create_politician`

### Services

#### etl_services.py
- [ ] `init_services`

#### bioguide_enrichment.py
- [ ] `normalize_name`
- [ ] `fetch_politicians_without_bioguide`
- [ ] `update_politician_from_congress`
- [ ] `match_politicians`

#### ticker_backfill.py
- [ ] `extract_ticker_from_asset_name`
- [ ] `extract_transaction_type_from_raw`
- [ ] `is_metadata_only`

#### senate_etl.py
- [ ] `upsert_senator_to_db`
- [ ] `_upsert_senator_by_name`
- [ ] `parse_transaction_from_row`
- [ ] `parse_datatables_record`

#### error_report_processor.py
- [ ] `ErrorReportProcessor.__init__`
- [ ] `ErrorReportProcessor._get_supabase`
- [ ] `ErrorReportProcessor._get_ollama_client`
- [ ] `ErrorReportProcessor.test_connection`
- [ ] `ErrorReportProcessor.get_pending_reports`
- [ ] `ErrorReportProcessor.interpret_corrections`
- [ ] `ErrorReportProcessor._build_prompt`
- [ ] `ErrorReportProcessor.process_report`
- [ ] `ErrorReportProcessor._apply_corrections`
- [ ] `ErrorReportProcessor._normalize_party`
- [ ] `ErrorReportProcessor._update_report_status`
- [ ] `ErrorReportProcessor.process_all_pending`

#### party_enrichment.py
- [ ] `PartyEnrichmentJob.__init__`
- [ ] `PartyEnrichmentJob.to_dict`
- [ ] `get_job`
- [ ] `create_job`

#### house_etl.py
- [ ] `HouseETLStats.__init__`
- [ ] `HouseETLStats.record_success`
- [ ] `HouseETLStats.record_error`
- [ ] `HouseETLStats.get_stats`
- [ ] `_validate_and_correct_year`
- [ ] `extract_dates_from_row`
- [ ] `is_metadata_row`
- [ ] `parse_transaction_from_row`
- [ ] `get_zip_url` (static)
- [ ] `get_pdf_url` (static)
- [ ] `extract_index_file` (static)
- [ ] `parse_filing_date` (static)
- [ ] `parse_disclosure_record` (static)
- [ ] `parse_disclosure_index` (static)

#### sandbox.py
- [ ] `SafeSandbox.__init__`
- [ ] `SafeSandbox.__call__`
- [ ] `SafeSandbox.get_output`
- [ ] `SafeSandbox.validate_code`
- [ ] `SafeSandbox.compile_lambda`
- [ ] `SafeSandbox._create_safe_math_module`
- [ ] `SafeSandbox.execute`
- [ ] `_signal_was_modified`
- [ ] `apply_lambda_to_signals`

#### politician_dedup.py
- [ ] `PoliticianDedup.__init__`
- [ ] `PoliticianDedup._get_supabase`
- [ ] `PoliticianDedup.normalize_name`
- [ ] `PoliticianDedup.find_duplicates`
- [ ] `PoliticianDedup._pick_winner`
- [ ] `PoliticianDedup._count_disclosures`
- [ ] `PoliticianDedup.merge_group`
- [ ] `PoliticianDedup.process_all`
- [ ] `PoliticianDedup.preview`

#### auto_correction.py
- [ ] `AutoCorrection.__init__`
- [ ] `AutoCorrection._get_supabase`
- [ ] `AutoCorrection.correct_ticker`
- [ ] `AutoCorrection.correct_value_range`
- [ ] `AutoCorrection.correct_date_format`
- [ ] `AutoCorrection.correct_amount_text`
- [ ] `AutoCorrection.run_ticker_corrections`
- [ ] `AutoCorrection.run_value_range_corrections`
- [ ] `AutoCorrection._apply_correction`
- [ ] `AutoCorrection._apply_range_correction`
- [ ] `AutoCorrection._apply_amount_correction`
- [ ] `AutoCorrection._log_correction`
- [ ] `AutoCorrection._mark_correction_applied`
- [ ] `AutoCorrection.rollback_correction`

#### name_enrichment.py
- [ ] `parse_ollama_name_response`
- [ ] `NameEnrichmentJob.__init__`
- [ ] `NameEnrichmentJob.to_dict`
- [ ] `get_name_job`
- [ ] `create_name_job`

#### ml_signal_model.py
- [ ] `ensure_storage_bucket_exists`
- [ ] `upload_model_to_storage`
- [ ] `download_model_from_storage`
- [ ] `compute_feature_hash`
- [ ] `SignalModel.__init__`
- [ ] `SignalModel.prepare_features`
- [ ] `SignalModel.train`
- [ ] `SignalModel.predict`
- [ ] `SignalModel.predict_batch`
- [ ] `SignalModel.save`
- [ ] `SignalModel.load`
- [ ] `SignalModel.get_feature_importance`
- [ ] `get_active_model`
- [ ] `load_active_model`
- [ ] `cache_prediction`
- [ ] `get_cached_prediction`

#### feature_pipeline.py
- [ ] `generate_label`
- [ ] `FeatureBuilder.__init__`
- [ ] `FeatureBuilder._aggregate_by_week`
- [ ] `FeatureBuilder._extract_features`
- [ ] `TrainingJob.__init__`
- [ ] `TrainingJob.to_dict`
- [ ] `get_training_job`
- [ ] `create_training_job`

---

## Summary

| Component | Files | Functions |
|-----------|-------|-----------|
| Client (TypeScript) | ~30 | ~50 |
| Server (Elixir) | ~40 | ~200 |
| ETL Service (Python) | ~20 | ~120 |
| **Total** | **~90** | **~370** |

---

## Review Notes

Use this section to document findings during review:

### Critical Issues Found
- [ ] _None yet_

### Improvements Suggested
- [ ] _None yet_

### Questions/Clarifications Needed
- [ ] _None yet_
