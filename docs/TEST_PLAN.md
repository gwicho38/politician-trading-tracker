# Comprehensive Test Plan

This document tracks all tests needed for the Politician Trading Tracker application.

**Legend:**
- `[ ]` - Not started
- `[~]` - In progress
- `[x]` - Completed and passing
- `[!]` - Test revealed bug (fixed)

---

## 1. Client Tests (React/Vitest)

### 1.1 Authentication Hooks
| Status | Test File | Function | Description |
|--------|-----------|----------|-------------|
| [ ] | `useAuth.test.ts` | `useAuth()` | Auth context initialization |
| [ ] | `useAuth.test.ts` | `useAuth()` | Session state subscription |
| [ ] | `useAuth.test.ts` | `useAuthReady()` | Auth ready flag behavior |
| [ ] | `useAdmin.test.ts` | `useAdmin()` | Admin role RPC check |
| [ ] | `useAdmin.test.ts` | `useAdmin()` | Session validation |
| [ ] | `useWalletAuth.test.ts` | `useWalletAuth()` | Nonce retrieval |
| [ ] | `useWalletAuth.test.ts` | `useWalletAuth()` | Message signing flow |
| [ ] | `useWalletAuth.test.ts` | `useWalletAuth()` | Signature verification |

### 1.2 Data Fetching Hooks
| Status | Test File | Function | Description |
|--------|-----------|----------|-------------|
| [ ] | `useSupabaseData.test.ts` | `useJurisdictions()` | Fetch jurisdictions |
| [ ] | `useSupabaseData.test.ts` | `usePoliticians()` | Fetch politicians with filters |
| [ ] | `useSupabaseData.test.ts` | `useTrades()` | Fetch recent trades |
| [ ] | `useSupabaseData.test.ts` | `useTradingDisclosures()` | Advanced search/filter/sort |
| [ ] | `useSupabaseData.test.ts` | `useChartData()` | Time range filtering |
| [ ] | `useSupabaseData.test.ts` | `useTopTickers()` | Top tickers query |
| [ ] | `useSupabaseData.test.ts` | `useDashboardStats()` | Dashboard metrics |
| [ ] | `useSupabaseData.test.ts` | `usePoliticianDetail()` | Politician profile with stats |
| [ ] | `useSupabaseData.test.ts` | `useTickerDetail()` | Ticker detail aggregation |
| [ ] | `useSupabaseData.test.ts` | `useMonthDetail()` | Month detail aggregation |
| [ ] | `useTickerSearch.test.ts` | `useTickerSearch()` | Autocomplete search |
| [ ] | `useGlobalSearch.test.ts` | `useGlobalSearch()` | Combined search |

### 1.3 Trading/Order Hooks
| Status | Test File | Function | Description |
|--------|-----------|----------|-------------|
| [ ] | `useOrders.test.ts` | `useOrders()` | Fetch orders with filters |
| [ ] | `useOrders.test.ts` | `useSyncOrders()` | Sync orders mutation |
| [ ] | `useOrders.test.ts` | `usePlaceOrder()` | Place order mutation |
| [ ] | `useOrders.test.ts` | `useCancelOrder()` | Cancel order mutation |
| [ ] | `useOrders.test.ts` | `getOrderStatusColor()` | Status color helper |
| [ ] | `useAlpacaAccount.test.ts` | `useAlpacaAccount()` | Account info fetch |
| [ ] | `useAlpacaAccount.test.ts` | `calculateDailyPnL()` | P&L calculation |
| [ ] | `useAlpacaPositions.test.ts` | `useAlpacaPositions()` | Positions fetch |
| [ ] | `useAlpacaPositions.test.ts` | `calculatePositionMetrics()` | Position aggregation |
| [ ] | `useAlpacaCredentials.test.ts` | `useAlpacaCredentials()` | Credentials CRUD |
| [ ] | `useAlpacaCredentials.test.ts` | `testConnection()` | Connection test mutation |

### 1.4 Portfolio Hooks
| Status | Test File | Function | Description |
|--------|-----------|----------|-------------|
| [ ] | `useReferencePortfolio.test.ts` | `useReferencePortfolioState()` | Portfolio state |
| [ ] | `useReferencePortfolio.test.ts` | `useReferencePortfolioPositions()` | Positions query |
| [ ] | `useReferencePortfolio.test.ts` | `useReferencePortfolioTrades()` | Trade history |
| [ ] | `useReferencePortfolio.test.ts` | `useReferencePortfolioPerformance()` | Performance snapshots |
| [ ] | `useReferencePortfolio.test.ts` | `useMarketStatus()` | Market open/close check |
| [ ] | `useReferencePortfolio.test.ts` | `useReferencePortfolioSummary()` | Summary computation |

### 1.5 Strategy/Signal Hooks
| Status | Test File | Function | Description |
|--------|-----------|----------|-------------|
| [ ] | `useStrategyFollow.test.ts` | `useStrategyFollow()` | Strategy subscriptions |
| [ ] | `useSignalPlayground.test.ts` | `useSignalPlayground()` | Signal weight state |
| [ ] | `useSignalPlayground.test.ts` | `fetchPreviewSignals()` | Signal preview fetch |
| [ ] | `useSignalPresets.test.ts` | `useSignalPresets()` | Preset CRUD |
| [ ] | `useStrategyShowcase.test.ts` | `useStrategyShowcase()` | Public strategies |

### 1.6 Social/Community Hooks
| Status | Test File | Function | Description |
|--------|-----------|----------|-------------|
| [ ] | `useDrops.test.ts` | `useDrops()` | Drops CRUD |
| [ ] | `useDrops.test.ts` | `likeDropMutation` | Like/unlike drops |
| [ ] | `useDropsRealtime.test.ts` | `useDropsRealtime()` | Real-time subscription |

### 1.7 Utility Hooks
| Status | Test File | Function | Description |
|--------|-----------|----------|-------------|
| [ ] | `usePagination.test.ts` | `usePagination()` | Pagination state |
| [ ] | `useDebounce.test.ts` | `useDebounce()` | Debounce timing |

---

## 2. Server Tests (Elixir/ExUnit)

### 2.1 Controllers
| Status | Test File | Function | Description |
|--------|-----------|----------|-------------|
| [ ] | `health_controller_test.exs` | `GET /health` | Basic health check |
| [ ] | `health_controller_test.exs` | `GET /health/ready` | Readiness check |
| [ ] | `job_controller_test.exs` | `GET /api/jobs` | List all jobs |
| [ ] | `job_controller_test.exs` | `GET /api/jobs/:id` | Get job details |
| [ ] | `job_controller_test.exs` | `POST /api/jobs/:id/run` | Trigger job |
| [ ] | `job_controller_test.exs` | `GET /api/jobs/sync-status` | Sync status |
| [ ] | `job_controller_test.exs` | `POST /api/jobs/run-all` | Run all jobs |
| [ ] | `ml_controller_test.exs` | `POST /api/ml/predict` | Single prediction |
| [ ] | `ml_controller_test.exs` | `POST /api/ml/batch-predict` | Batch prediction |
| [ ] | `ml_controller_test.exs` | `GET /api/ml/models` | List models |
| [ ] | `ml_controller_test.exs` | `GET /api/ml/models/active` | Active model |
| [ ] | `ml_controller_test.exs` | `POST /api/ml/train` | Trigger training |
| [ ] | `ml_controller_test.exs` | `GET /api/ml/health` | ML service health |

### 2.2 Scheduler API
| Status | Test File | Function | Description |
|--------|-----------|----------|-------------|
| [ ] | `scheduler_api_test.exs` | `register_job/1` | Job registration |
| [ ] | `scheduler_api_test.exs` | `run_now/1` | Immediate job execution |
| [ ] | `scheduler_api_test.exs` | `enable_job/1` | Enable job |
| [ ] | `scheduler_api_test.exs` | `disable_job/1` | Disable job |
| [ ] | `scheduler_api_test.exs` | `list_jobs/0` | List all jobs |
| [ ] | `scheduler_api_test.exs` | `get_job_status/1` | Job status |
| [ ] | `scheduler_api_test.exs` | `get_executions/2` | Execution history |

### 2.3 Scheduler Jobs (32 jobs - testing key ones)
| Status | Test File | Function | Description |
|--------|-----------|----------|-------------|
| [ ] | `sync_job_test.exs` | `SyncJob.run/0` | Core sync job |
| [ ] | `sync_data_job_test.exs` | `SyncDataJob.run/0` | Data sync job |
| [ ] | `orders_job_test.exs` | `OrdersJob.run/0` | Orders sync |
| [ ] | `trading_signals_job_test.exs` | `TradingSignalsJob.run/0` | Signal generation |
| [ ] | `politician_trading_house_job_test.exs` | `PoliticianTradingHouseJob.run/0` | House ETL trigger |
| [ ] | `politician_trading_senate_job_test.exs` | `PoliticianTradingSenateJob.run/0` | Senate ETL trigger |
| [ ] | `politician_trading_quiver_job_test.exs` | `PoliticianTradingQuiverJob.run/0` | QuiverQuant ETL |
| [ ] | `ticker_backfill_job_test.exs` | `TickerBackfillJob.run/0` | Ticker backfill |
| [ ] | `bioguide_enrichment_job_test.exs` | `BioguideEnrichmentJob.run/0` | BioGuide enrichment |
| [ ] | `party_enrichment_job_test.exs` | `PartyEnrichmentJob.run/0` | Party enrichment |
| [ ] | `ml_training_job_test.exs` | `MlTrainingJob.run/0` | ML training trigger |
| [ ] | `email_digest_job_test.exs` | `EmailDigestJob.run/0` | Email digest |
| [ ] | `job_execution_cleanup_job_test.exs` | `JobExecutionCleanupJob.run/0` | Cleanup old executions |

### 2.4 Business Logic Modules
| Status | Test File | Function | Description |
|--------|-----------|----------|-------------|
| [ ] | `supabase_client_test.exs` | `invoke/3` | Edge function invocation |
| [ ] | `supabase_client_test.exs` | `invoke/3` | Error handling |
| [ ] | `email_alerter_test.exs` | `send_immediate/2` | Immediate alerts |
| [ ] | `email_alerter_test.exs` | `queue_digest/2` | Queue for digest |
| [ ] | `email_alerter_test.exs` | `send_daily_digest/0` | Daily digest |
| [ ] | `digest_store_test.exs` | `add_issue/1` | Add issue to store |
| [ ] | `digest_store_test.exs` | `get_issues/0` | Get accumulated issues |
| [ ] | `digest_store_test.exs` | `flush_issues/0` | Flush and return |

### 2.5 Schemas
| Status | Test File | Function | Description |
|--------|-----------|----------|-------------|
| [ ] | `scheduled_job_test.exs` | `changeset/2` | Valid changeset |
| [ ] | `scheduled_job_test.exs` | `changeset/2` | Invalid changeset |
| [ ] | `job_execution_test.exs` | `changeset/2` | Valid changeset |
| [ ] | `job_execution_test.exs` | `changeset/2` | Invalid changeset |

---

## 3. Python ETL Service Tests (pytest)

### 3.1 Services
| Status | Test File | Function | Description |
|--------|-----------|----------|-------------|
| [ ] | `test_house_etl_service.py` | `run_house_etl()` | Full ETL run |
| [ ] | `test_house_etl_service.py` | `HouseDisclosureScraper` | Scraper class |
| [ ] | `test_house_etl_service.py` | `parse_transaction_from_row()` | Row parsing |
| [ ] | `test_senate_etl_service.py` | `run_senate_etl()` | Full ETL run |
| [ ] | `test_senate_etl_service.py` | `fetch_senators_from_xml()` | XML parsing |
| [ ] | `test_senate_etl_service.py` | `fetch_efd_disclosures()` | EFD scraping |
| [ ] | `test_etl_services.py` | `HouseETLService.run()` | Registry ETL wrapper |
| [ ] | `test_etl_services.py` | `SenateETLService.run()` | Registry ETL wrapper |
| [ ] | `test_bioguide_enrichment.py` | `run_bioguide_enrichment()` | Full enrichment |
| [ ] | `test_bioguide_enrichment.py` | `fetch_congress_members()` | Congress.gov API |
| [ ] | `test_ticker_backfill.py` | `run_ticker_backfill()` | Ticker backfill |
| [ ] | `test_ticker_backfill.py` | `run_transaction_type_backfill()` | Type backfill |
| [ ] | `test_party_enrichment.py` | `run_party_enrichment()` | Party enrichment |
| [ ] | `test_party_enrichment.py` | `query_ollama_for_party()` | Ollama integration |
| [ ] | `test_politician_dedup.py` | `PoliticianDeduplicator` | Dedup class |
| [ ] | `test_politician_dedup.py` | `find_duplicates()` | Duplicate detection |
| [ ] | `test_politician_dedup.py` | `merge_records()` | Record merging |
| [ ] | `test_auto_correction.py` | `AutoCorrector` | Auto-correction class |
| [ ] | `test_feature_pipeline.py` | `FeaturePipeline` | Feature extraction |
| [ ] | `test_ml_signal_model.py` | `CongressSignalModel` | ML model class |
| [ ] | `test_ml_signal_model.py` | `train()` | Model training |
| [ ] | `test_ml_signal_model.py` | `predict()` | Model prediction |

### 3.2 Routes
| Status | Test File | Function | Description |
|--------|-----------|----------|-------------|
| [ ] | `test_etl_routes.py` | `POST /etl/trigger` | Trigger ETL |
| [ ] | `test_etl_routes.py` | `GET /etl/status/{job_id}` | Job status |
| [ ] | `test_etl_routes.py` | `GET /etl/sources` | List sources |
| [ ] | `test_etl_routes.py` | `POST /etl/ingest-url` | Single URL ingest |
| [ ] | `test_etl_routes.py` | `POST /etl/backfill-tickers` | Ticker backfill |
| [ ] | `test_etl_routes.py` | `POST /etl/enrich-bioguide` | BioGuide enrichment |
| [ ] | `test_etl_routes.py` | `POST /etl/cleanup-executions` | Cleanup old records |
| [ ] | `test_ml_routes.py` | `POST /ml/predict` | Single prediction |
| [ ] | `test_ml_routes.py` | `POST /ml/batch-predict` | Batch prediction |
| [ ] | `test_ml_routes.py` | `GET /ml/models` | List models |
| [ ] | `test_ml_routes.py` | `GET /ml/models/active` | Active model |
| [ ] | `test_ml_routes.py` | `POST /ml/train` | Trigger training |
| [ ] | `test_signals_routes.py` | `POST /signals/apply-lambda` | Apply lambda |
| [ ] | `test_enrichment_routes.py` | `POST /enrichment/party` | Party enrichment |
| [ ] | `test_quality_routes.py` | `GET /quality/report` | Quality report |
| [ ] | `test_dedup_routes.py` | `GET /dedup/candidates` | Dedup candidates |
| [ ] | `test_dedup_routes.py` | `POST /dedup/merge` | Merge duplicates |
| [ ] | `test_health_routes.py` | `GET /health` | Health check |

### 3.3 Library Modules
| Status | Test File | Function | Description |
|--------|-----------|----------|-------------|
| [x] | `test_base_etl.py` | `BaseETLService` | Abstract base class (35 tests) |
| [x] | `test_base_etl.py` | `ETLResult` | Result tracking |
| [x] | `test_registry.py` | `ETLRegistry.register()` | Service registration (24 tests) |
| [x] | `test_registry.py` | `ETLRegistry.create_instance()` | Instance creation |
| [x] | `test_database.py` | `get_supabase()` | Client initialization (17 tests) |
| [x] | `test_database.py` | `upload_transaction_to_supabase()` | Transaction upload |
| [x] | `test_politician.py` | `find_or_create_politician()` | Politician lookup/create (28 tests) |
| [ ] | `test_job_logger.py` | `log_job_execution()` | Execution logging |
| [ ] | `test_job_logger.py` | `cleanup_old_executions()` | Cleanup old logs |
| [x] | `test_pdf_utils.py` | `extract_text_from_pdf()` | Text extraction (16 tests) |
| [x] | `test_pdf_utils.py` | `extract_tables_from_pdf()` | Table extraction |

---

## 4. Edge Function Tests (Deno)

### 4.1 Additional Edge Functions
| Status | Test File | Function | Description |
|--------|-----------|----------|-------------|
| [ ] | `alpaca-account/index.test.ts` | `handleGetAccount()` | Account fetch |
| [ ] | `alpaca-account/index.test.ts` | `handleGetPositions()` | Positions fetch |
| [ ] | `orders/index.test.ts` | `handleGetOrders()` | Orders fetch |
| [ ] | `orders/index.test.ts` | `handlePlaceOrder()` | Place order |
| [ ] | `orders/index.test.ts` | `handleCancelOrder()` | Cancel order |
| [ ] | `orders/index.test.ts` | `handleSyncOrders()` | Sync orders |
| [ ] | `reference-portfolio/index.test.ts` | Portfolio operations | Full coverage |
| [ ] | `strategy-follow/index.test.ts` | Strategy operations | Full coverage |
| [ ] | `wallet-auth/index.test.ts` | Auth operations | Full coverage |

---

## Test Totals

| Category | Total Tests | Completed | Remaining |
|----------|-------------|-----------|-----------|
| Client Hooks | 52 | 0 | 52 |
| Server Controllers | 13 | 0 | 13 |
| Server Scheduler | 20 | 0 | 20 |
| Server Business Logic | 8 | 0 | 8 |
| Server Schemas | 4 | 0 | 4 |
| Python Services | 22 | 0 | 22 |
| Python Routes | 18 | 0 | 18 |
| Python Library | 11 | 9 | 2 |
| Edge Functions | 9 | 0 | 9 |
| **TOTAL** | **157** | **9** | **148** |

### Phase 1 Complete: Python ETL Library Tests (120 test cases)
- `test_database.py`: 17 tests ✅
- `test_politician.py`: 28 tests ✅
- `test_pdf_utils.py`: 16 tests ✅
- `test_base_etl.py`: 35 tests ✅
- `test_registry.py`: 24 tests ✅

### Phase 2 Complete: Python ETL Services Tests (179 test cases)
- `test_house_etl_service.py`: 51 tests ✅
- `test_senate_etl_service.py`: 27 tests ✅
- `test_bioguide_enrichment.py`: 46 tests ✅
- `test_ticker_backfill.py`: 55 tests ✅

### Phase 3 Complete: Python ETL Routes Tests (57 test cases)
- `test_health_routes.py`: 3 tests ✅
- `test_etl_routes.py`: 31 tests ✅
- `test_ml_routes.py`: 23 tests ✅

---

## Execution Order

1. **Phase 1: Python ETL Library** (foundational)
   - `test_database.py`
   - `test_politician.py`
   - `test_pdf_utils.py`
   - `test_base_etl.py`
   - `test_registry.py`

2. **Phase 2: Python ETL Services**
   - `test_house_etl_service.py`
   - `test_senate_etl_service.py`
   - `test_bioguide_enrichment.py`
   - `test_ticker_backfill.py`

3. **Phase 3: Python ETL Routes**
   - `test_etl_routes.py`
   - `test_ml_routes.py`
   - `test_health_routes.py`

4. **Phase 4: Elixir Server**
   - `scheduler_api_test.exs`
   - `job_controller_test.exs`
   - `health_controller_test.exs`
   - Key job tests

5. **Phase 5: React Client**
   - `useAuth.test.ts`
   - `useOrders.test.ts`
   - `useAlpacaCredentials.test.ts`
   - Remaining hooks

---

*Last Updated: 2026-01-19*
