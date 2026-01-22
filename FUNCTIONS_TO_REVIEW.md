# Functions to Review

Generated: 2026-01-22

This document lists all functions across the client, server, and python-etl-service for manual review.

---

## Client (React/TypeScript)

### Hooks (`client/src/hooks/`)

| File | Hook | Status |
|------|------|--------|
| `useAccountStatus.ts` | `useAccountStatus()` | [ ] |
| `useAdmin.ts` | `useAdmin()` | [ ] |
| `useAdminStats.ts` | `useAdminStats()` | [ ] |
| `useAlerts.ts` | `useAlerts()` | [ ] |
| `useAlpacaAccount.ts` | `useAlpacaAccount()` | [ ] |
| `useAlpacaOrders.ts` | `useAlpacaOrders()` | [ ] |
| `useAlpacaPositions.ts` | `useAlpacaPositions()` | [ ] |
| `useAuth.ts` | `useAuth()` | [ ] |
| `useBulkOperations.ts` | `useBulkOperations()` | [ ] |
| `useCircuitBreaker.ts` | `useCircuitBreaker()` | [ ] |
| `useCommittees.ts` | `useCommittees()` | [ ] |
| `useConnectionStatus.ts` | `useConnectionStatus()` | [ ] |
| `useDarkMode.ts` | `useDarkMode()` | [ ] |
| `useDataSync.ts` | `useDataSync()` | [ ] |
| `useErrorReports.ts` | `useErrorReports()` | [ ] |
| `useFilings.ts` | `useFilings()` | [ ] |
| `useJobs.ts` | `useJobs()` | [ ] |
| `useMarketData.ts` | `useMarketData()` | [ ] |
| `useMLModels.ts` | `useMLModels()` | [ ] |
| `useNotifications.ts` | `useNotifications()` | [ ] |
| `useOrders.ts` | `useOrders()` | [ ] |
| `usePoliticianFilings.ts` | `usePoliticianFilings()` | [ ] |
| `usePoliticians.ts` | `usePoliticians()` | [ ] |
| `usePortfolio.ts` | `usePortfolio()` | [ ] |
| `usePortfolioHistory.ts` | `usePortfolioHistory()` | [ ] |
| `usePositions.ts` | `usePositions()` | [ ] |
| `useRealtimeFilings.ts` | `useRealtimeFilings()` | [ ] |
| `useRealtimeOrders.ts` | `useRealtimeOrders()` | [ ] |
| `useRealtimePositions.ts` | `useRealtimePositions()` | [ ] |
| `useRealtimeTrades.ts` | `useRealtimeTrades()` | [ ] |
| `useScheduler.ts` | `useScheduler()` | [ ] |
| `useSignalFeedback.ts` | `useSignalFeedback()` | [ ] |
| `useSignals.ts` | `useSignals()` | [ ] |
| `useStocks.ts` | `useStocks()` | [ ] |
| `useSyncStatus.ts` | `useSyncStatus()` | [ ] |
| `useSystemHealth.ts` | `useSystemHealth()` | [ ] |
| `useTrades.ts` | `useTrades()` | [ ] |
| `useTradingSignals.ts` | `useTradingSignals()` | [ ] |
| `useUserPreferences.ts` | `useUserPreferences()` | [ ] |
| `useUsers.ts` | `useUsers()` | [ ] |
| `useWatchlist.ts` | `useWatchlist()` | [ ] |

### Context Providers (`client/src/contexts/`)

| File | Provider | Status |
|------|----------|--------|
| `AuthContext.tsx` | `AuthProvider` | [ ] |
| `ThemeContext.tsx` | `ThemeProvider` | [ ] |

### Library Functions (`client/src/lib/`)

| File | Function | Status |
|------|----------|--------|
| `api.ts` | `apiClient` | [ ] |
| `api.ts` | `get()` | [ ] |
| `api.ts` | `post()` | [ ] |
| `api.ts` | `put()` | [ ] |
| `api.ts` | `delete()` | [ ] |
| `chartUtils.ts` | `formatChartData()` | [ ] |
| `chartUtils.ts` | `getChartColors()` | [ ] |
| `chartUtils.ts` | `calculateTrendLine()` | [ ] |
| `constants.ts` | `API_BASE_URL` | [ ] |
| `constants.ts` | `ROUTES` | [ ] |
| `dateUtils.ts` | `formatDate()` | [ ] |
| `dateUtils.ts` | `formatRelativeTime()` | [ ] |
| `dateUtils.ts` | `parseDate()` | [ ] |
| `dateUtils.ts` | `isToday()` | [ ] |
| `dateUtils.ts` | `isThisWeek()` | [ ] |
| `errorUtils.ts` | `parseError()` | [ ] |
| `errorUtils.ts` | `getErrorMessage()` | [ ] |
| `formatters.ts` | `formatCurrency()` | [ ] |
| `formatters.ts` | `formatPercent()` | [ ] |
| `formatters.ts` | `formatNumber()` | [ ] |
| `formatters.ts` | `formatCompact()` | [ ] |
| `queryClient.ts` | `queryClient` | [ ] |
| `supabase.ts` | `supabase` | [ ] |
| `supabase.ts` | `getSession()` | [ ] |
| `supabase.ts` | `signIn()` | [ ] |
| `supabase.ts` | `signOut()` | [ ] |
| `utils.ts` | `cn()` | [ ] |
| `utils.ts` | `debounce()` | [ ] |
| `utils.ts` | `throttle()` | [ ] |
| `validators.ts` | `validateEmail()` | [ ] |
| `validators.ts` | `validatePassword()` | [ ] |
| `validators.ts` | `validateTicker()` | [ ] |

### Components (`client/src/components/`)

| Category | Component | Status |
|----------|-----------|--------|
| **Admin** | `AdminDashboard` | [ ] |
| **Admin** | `UserManagement` | [ ] |
| **Admin** | `SystemSettings` | [ ] |
| **Admin** | `ErrorReports` | [ ] |
| **Admin** | `JobsManager` | [ ] |
| **Auth** | `LoginForm` | [ ] |
| **Auth** | `SignupForm` | [ ] |
| **Auth** | `ProtectedRoute` | [ ] |
| **Auth** | `ForgotPassword` | [ ] |
| **Charts** | `LineChart` | [ ] |
| **Charts** | `BarChart` | [ ] |
| **Charts** | `PieChart` | [ ] |
| **Charts** | `AreaChart` | [ ] |
| **Charts** | `CandlestickChart` | [ ] |
| **Common** | `Button` | [ ] |
| **Common** | `Card` | [ ] |
| **Common** | `Input` | [ ] |
| **Common** | `Modal` | [ ] |
| **Common** | `Table` | [ ] |
| **Common** | `Spinner` | [ ] |
| **Common** | `Toast` | [ ] |
| **Common** | `Tooltip` | [ ] |
| **Common** | `Badge` | [ ] |
| **Common** | `Dropdown` | [ ] |
| **Dashboard** | `DashboardLayout` | [ ] |
| **Dashboard** | `StatsCards` | [ ] |
| **Dashboard** | `RecentActivity` | [ ] |
| **Dashboard** | `PerformanceChart` | [ ] |
| **Filings** | `FilingsTable` | [ ] |
| **Filings** | `FilingCard` | [ ] |
| **Filings** | `FilingDetails` | [ ] |
| **Filings** | `FilingsFilter` | [ ] |
| **Layout** | `Header` | [ ] |
| **Layout** | `Sidebar` | [ ] |
| **Layout** | `Footer` | [ ] |
| **Layout** | `Navigation` | [ ] |
| **ML** | `MLDashboard` | [ ] |
| **ML** | `ModelMetrics` | [ ] |
| **ML** | `FeatureImportance` | [ ] |
| **ML** | `PredictionCard` | [ ] |
| **Orders** | `OrderForm` | [ ] |
| **Orders** | `OrdersTable` | [ ] |
| **Orders** | `OrderDetails` | [ ] |
| **Orders** | `OrderHistory` | [ ] |
| **Politicians** | `PoliticianCard` | [ ] |
| **Politicians** | `PoliticianList` | [ ] |
| **Politicians** | `PoliticianDetails` | [ ] |
| **Politicians** | `PoliticianFilings` | [ ] |
| **Portfolio** | `PortfolioSummary` | [ ] |
| **Portfolio** | `PositionsTable` | [ ] |
| **Portfolio** | `PerformanceMetrics` | [ ] |
| **Portfolio** | `AllocationChart` | [ ] |
| **Signals** | `SignalsTable` | [ ] |
| **Signals** | `SignalCard` | [ ] |
| **Signals** | `SignalDetails` | [ ] |
| **Signals** | `SignalFeedback` | [ ] |
| **Trading** | `TradingPanel` | [ ] |
| **Trading** | `QuickTrade` | [ ] |
| **Trading** | `TradeConfirmation` | [ ] |
| **Watchlist** | `WatchlistTable` | [ ] |
| **Watchlist** | `AddToWatchlist` | [ ] |

### Pages (`client/src/pages/`)

| Page | Status |
|------|--------|
| `AdminPage` | [ ] |
| `DashboardPage` | [ ] |
| `FilingsPage` | [ ] |
| `LoginPage` | [ ] |
| `MLPage` | [ ] |
| `NotFoundPage` | [ ] |
| `OrdersPage` | [ ] |
| `PoliticianPage` | [ ] |
| `PoliticiansPage` | [ ] |
| `PortfolioPage` | [ ] |
| `SettingsPage` | [ ] |
| `SignalsPage` | [ ] |
| `SignupPage` | [ ] |
| `TradingPage` | [ ] |

---

## Server (Elixir/Phoenix)

### Controllers (`server/lib/server_web/controllers/`)

| Controller | Action | Route | Status |
|------------|--------|-------|--------|
| `HealthController` | `index/2` | `GET /` | [ ] |
| `HealthController` | `health/2` | `GET /health` | [ ] |
| `HealthController` | `ready/2` | `GET /ready` | [ ] |
| `JobController` | `index/2` | `GET /api/jobs` | [ ] |
| `JobController` | `show/2` | `GET /api/jobs/:id` | [ ] |
| `JobController` | `run/2` | `POST /api/jobs/:id/run` | [ ] |
| `JobController` | `sync_status/2` | `GET /api/jobs/sync-status` | [ ] |
| `JobController` | `run_all/2` | `POST /api/jobs/run-all` | [ ] |
| `MlController` | `predict/2` | `POST /api/ml/predict` | [ ] |
| `MlController` | `batch_predict/2` | `POST /api/ml/batch-predict` | [ ] |
| `MlController` | `list_models/2` | `GET /api/ml/models` | [ ] |
| `MlController` | `get_active_model/2` | `GET /api/ml/models/active` | [ ] |
| `MlController` | `get_model/2` | `GET /api/ml/models/:id` | [ ] |
| `MlController` | `feature_importance/2` | `GET /api/ml/models/:id/feature-importance` | [ ] |
| `MlController` | `train/2` | `POST /api/ml/train` | [ ] |
| `MlController` | `training_status/2` | `GET /api/ml/train/:job_id` | [ ] |
| `MlController` | `health/2` | `GET /api/ml/health` | [ ] |

### Scheduler Jobs (`server/lib/server/scheduler.ex`)

| Job ID | Function | Schedule | Status |
|--------|----------|----------|--------|
| `sync_house_disclosures` | House disclosure sync | Daily | [ ] |
| `sync_senate_disclosures` | Senate disclosure sync | Daily | [ ] |
| `sync_quiverquant` | QuiverQuant data sync | Every 6 hours | [ ] |
| `sync_capitol_trades` | Capitol Trades sync | Every 6 hours | [ ] |
| `sync_politician_profiles` | Politician profiles | Daily | [ ] |
| `sync_committee_assignments` | Committee assignments | Weekly | [ ] |
| `sync_stock_prices` | Stock price updates | Every 15 min | [ ] |
| `sync_market_data` | Market data sync | Every 5 min | [ ] |
| `generate_signals` | Trading signal generation | Every hour | [ ] |
| `evaluate_signals` | Signal performance eval | Daily | [ ] |
| `cleanup_old_data` | Data retention cleanup | Weekly | [ ] |
| `refresh_materialized_views` | MV refresh | Every 30 min | [ ] |
| `aggregate_daily_stats` | Daily statistics | Daily | [ ] |
| `aggregate_weekly_stats` | Weekly statistics | Weekly | [ ] |
| `aggregate_monthly_stats` | Monthly statistics | Monthly | [ ] |
| `check_filing_deadlines` | Filing deadline alerts | Daily | [ ] |
| `update_politician_rankings` | Rankings update | Daily | [ ] |
| `sync_alpaca_positions` | Alpaca position sync | Every 5 min | [ ] |
| `sync_alpaca_orders` | Alpaca order sync | Every 5 min | [ ] |
| `sync_alpaca_account` | Alpaca account sync | Every 15 min | [ ] |
| `execute_pending_orders` | Order execution | Every minute | [ ] |
| `check_circuit_breakers` | Circuit breaker check | Every minute | [ ] |
| `ml_model_training` | ML model training | Weekly | [ ] |
| `ml_prediction_batch` | Batch predictions | Daily | [ ] |
| `ml_feature_update` | Feature engineering | Daily | [ ] |
| `send_daily_digest` | Email digest | Daily | [ ] |
| `send_alert_notifications` | Alert notifications | Every 5 min | [ ] |
| `health_check_services` | Service health checks | Every minute | [ ] |
| `backup_database` | Database backup | Daily | [ ] |
| `rotate_logs` | Log rotation | Daily | [ ] |
| `update_cache` | Cache refresh | Every 10 min | [ ] |
| `sync_error_reports` | Error report sync | Every hour | [ ] |

### Scheduler API (`server/lib/server/scheduler.ex`)

| Function | Description | Status |
|----------|-------------|--------|
| `list_jobs/0` | List all registered jobs | [ ] |
| `get_job/1` | Get job by ID | [ ] |
| `run_job/1` | Trigger job execution | [ ] |
| `run_all_jobs/0` | Run all jobs | [ ] |
| `enable_job/1` | Enable a job | [ ] |
| `disable_job/1` | Disable a job | [ ] |
| `get_sync_status/0` | Get sync status | [ ] |
| `register_job/1` | Register new job | [ ] |

### SupabaseClient (`server/lib/server/supabase_client.ex`)

| Function | Description | Status |
|----------|-------------|--------|
| `invoke/1` | Invoke edge function by name | [ ] |
| `invoke/2` | Invoke with options | [ ] |
| `from/1` | Query table | [ ] |
| `select/2` | Select columns | [ ] |
| `insert/2` | Insert record | [ ] |
| `update/2` | Update record | [ ] |
| `delete/1` | Delete record | [ ] |
| `eq/3` | Equality filter | [ ] |
| `neq/3` | Not equal filter | [ ] |
| `gt/3` | Greater than filter | [ ] |
| `lt/3` | Less than filter | [ ] |
| `gte/3` | Greater or equal filter | [ ] |
| `lte/3` | Less or equal filter | [ ] |
| `like/3` | LIKE filter | [ ] |
| `ilike/3` | Case-insensitive LIKE | [ ] |
| `in/3` | IN filter | [ ] |
| `order/3` | Order by | [ ] |
| `limit/2` | Limit results | [ ] |
| `single/1` | Get single result | [ ] |
| `execute/1` | Execute query | [ ] |

---

## Python ETL Service

### Route Handlers (`python-etl-service/app/routes/`)

#### `health.py`

| Route | Method | Function | Status |
|-------|--------|----------|--------|
| `/health` | GET | `health_check()` | [ ] |
| `/health/ready` | GET | `readiness_check()` | [ ] |
| `/health/live` | GET | `liveness_check()` | [ ] |

#### `filings.py`

| Route | Method | Function | Status |
|-------|--------|----------|--------|
| `/filings` | GET | `get_filings()` | [ ] |
| `/filings/{filing_id}` | GET | `get_filing()` | [ ] |
| `/filings/sync` | POST | `sync_filings()` | [ ] |
| `/filings/house/sync` | POST | `sync_house_filings()` | [ ] |
| `/filings/senate/sync` | POST | `sync_senate_filings()` | [ ] |
| `/filings/parse` | POST | `parse_filing()` | [ ] |
| `/filings/recent` | GET | `get_recent_filings()` | [ ] |
| `/filings/by-politician/{politician_id}` | GET | `get_filings_by_politician()` | [ ] |
| `/filings/by-ticker/{ticker}` | GET | `get_filings_by_ticker()` | [ ] |
| `/filings/stats` | GET | `get_filing_stats()` | [ ] |

#### `politicians.py`

| Route | Method | Function | Status |
|-------|--------|----------|--------|
| `/politicians` | GET | `get_politicians()` | [ ] |
| `/politicians/{politician_id}` | GET | `get_politician()` | [ ] |
| `/politicians/sync` | POST | `sync_politicians()` | [ ] |
| `/politicians/search` | GET | `search_politicians()` | [ ] |
| `/politicians/{politician_id}/filings` | GET | `get_politician_filings()` | [ ] |
| `/politicians/{politician_id}/stats` | GET | `get_politician_stats()` | [ ] |
| `/politicians/rankings` | GET | `get_politician_rankings()` | [ ] |
| `/politicians/committees` | GET | `get_committees()` | [ ] |

#### `stocks.py`

| Route | Method | Function | Status |
|-------|--------|----------|--------|
| `/stocks` | GET | `get_stocks()` | [ ] |
| `/stocks/{ticker}` | GET | `get_stock()` | [ ] |
| `/stocks/sync` | POST | `sync_stocks()` | [ ] |
| `/stocks/{ticker}/price` | GET | `get_stock_price()` | [ ] |
| `/stocks/{ticker}/history` | GET | `get_stock_history()` | [ ] |
| `/stocks/{ticker}/filings` | GET | `get_stock_filings()` | [ ] |
| `/stocks/market-data` | GET | `get_market_data()` | [ ] |
| `/stocks/sectors` | GET | `get_sectors()` | [ ] |

#### `signals.py`

| Route | Method | Function | Status |
|-------|--------|----------|--------|
| `/signals` | GET | `get_signals()` | [ ] |
| `/signals/{signal_id}` | GET | `get_signal()` | [ ] |
| `/signals/generate` | POST | `generate_signals()` | [ ] |
| `/signals/active` | GET | `get_active_signals()` | [ ] |
| `/signals/{signal_id}/feedback` | POST | `submit_feedback()` | [ ] |
| `/signals/performance` | GET | `get_signal_performance()` | [ ] |
| `/signals/by-ticker/{ticker}` | GET | `get_signals_by_ticker()` | [ ] |

#### `ml.py`

| Route | Method | Function | Status |
|-------|--------|----------|--------|
| `/ml/predict` | POST | `predict()` | [ ] |
| `/ml/batch-predict` | POST | `batch_predict()` | [ ] |
| `/ml/train` | POST | `train_model()` | [ ] |
| `/ml/train/{job_id}` | GET | `get_training_status()` | [ ] |
| `/ml/models` | GET | `list_models()` | [ ] |
| `/ml/models/active` | GET | `get_active_model()` | [ ] |
| `/ml/models/{model_id}` | GET | `get_model()` | [ ] |
| `/ml/models/{model_id}/feature-importance` | GET | `get_feature_importance()` | [ ] |

### Services (`python-etl-service/app/services/`)

#### `house_etl.py`

| Function | Description | Status |
|----------|-------------|--------|
| `fetch_house_disclosures()` | Fetch from House API | [ ] |
| `parse_house_disclosure()` | Parse disclosure document | [ ] |
| `transform_house_filing()` | Transform to standard format | [ ] |
| `load_house_filings()` | Load into database | [ ] |
| `sync_house_data()` | Full sync orchestration | [ ] |

#### `senate_etl.py`

| Function | Description | Status |
|----------|-------------|--------|
| `fetch_senate_disclosures()` | Fetch from Senate API | [ ] |
| `parse_senate_disclosure()` | Parse disclosure document | [ ] |
| `transform_senate_filing()` | Transform to standard format | [ ] |
| `load_senate_filings()` | Load into database | [ ] |
| `sync_senate_data()` | Full sync orchestration | [ ] |

#### `quiverquant.py`

| Function | Description | Status |
|----------|-------------|--------|
| `fetch_quiverquant_data()` | Fetch from QuiverQuant | [ ] |
| `parse_quiverquant_trade()` | Parse trade record | [ ] |
| `transform_quiverquant()` | Transform to standard format | [ ] |
| `load_quiverquant_data()` | Load into database | [ ] |
| `sync_quiverquant()` | Full sync orchestration | [ ] |

#### `capitol_trades.py`

| Function | Description | Status |
|----------|-------------|--------|
| `fetch_capitol_trades()` | Fetch from Capitol Trades | [ ] |
| `parse_capitol_trade()` | Parse trade record | [ ] |
| `transform_capitol_trade()` | Transform to standard format | [ ] |
| `load_capitol_trades()` | Load into database | [ ] |
| `sync_capitol_trades()` | Full sync orchestration | [ ] |

#### `signal_generator.py`

| Function | Description | Status |
|----------|-------------|--------|
| `generate_signals()` | Generate trading signals | [ ] |
| `calculate_signal_strength()` | Calculate strength score | [ ] |
| `evaluate_signal()` | Evaluate signal quality | [ ] |
| `get_signal_factors()` | Get contributing factors | [ ] |
| `rank_signals()` | Rank signals by quality | [ ] |

#### `ml_service.py`

| Function | Description | Status |
|----------|-------------|--------|
| `train_model()` | Train ML model | [ ] |
| `predict()` | Make prediction | [ ] |
| `batch_predict()` | Batch predictions | [ ] |
| `get_feature_importance()` | Get feature importance | [ ] |
| `evaluate_model()` | Evaluate model performance | [ ] |
| `save_model()` | Save model to storage | [ ] |
| `load_model()` | Load model from storage | [ ] |

#### `stock_service.py`

| Function | Description | Status |
|----------|-------------|--------|
| `fetch_stock_price()` | Fetch current price | [ ] |
| `fetch_stock_history()` | Fetch price history | [ ] |
| `calculate_metrics()` | Calculate stock metrics | [ ] |
| `get_market_data()` | Get market-wide data | [ ] |
| `sync_stock_prices()` | Sync all prices | [ ] |

### Library Functions (`python-etl-service/app/lib/`)

#### `parser.py`

| Function | Description | Status |
|----------|-------------|--------|
| `parse_value_range()` | Parse dollar ranges | [ ] |
| `parse_date()` | Parse date formats | [ ] |
| `parse_ticker()` | Extract ticker symbol | [ ] |
| `parse_transaction_type()` | Parse buy/sell/exchange | [ ] |
| `parse_asset_type()` | Parse asset type | [ ] |
| `clean_text()` | Clean and normalize text | [ ] |
| `extract_amounts()` | Extract monetary amounts | [ ] |

#### `validators.py`

| Function | Description | Status |
|----------|-------------|--------|
| `validate_filing()` | Validate filing data | [ ] |
| `validate_politician()` | Validate politician data | [ ] |
| `validate_trade()` | Validate trade data | [ ] |
| `validate_ticker()` | Validate ticker symbol | [ ] |
| `validate_date_range()` | Validate date range | [ ] |

#### `transformers.py`

| Function | Description | Status |
|----------|-------------|--------|
| `normalize_filing()` | Normalize filing format | [ ] |
| `normalize_politician()` | Normalize politician data | [ ] |
| `normalize_trade()` | Normalize trade data | [ ] |
| `merge_duplicates()` | Merge duplicate records | [ ] |
| `deduplicate_filings()` | Remove duplicate filings | [ ] |

#### `db.py`

| Function | Description | Status |
|----------|-------------|--------|
| `get_supabase_client()` | Get Supabase client | [ ] |
| `insert_batch()` | Batch insert records | [ ] |
| `upsert_batch()` | Batch upsert records | [ ] |
| `query_table()` | Query table with filters | [ ] |
| `execute_rpc()` | Execute RPC function | [ ] |

#### `cache.py`

| Function | Description | Status |
|----------|-------------|--------|
| `get_cached()` | Get from cache | [ ] |
| `set_cached()` | Set in cache | [ ] |
| `invalidate()` | Invalidate cache key | [ ] |
| `clear_all()` | Clear entire cache | [ ] |

---

## Review Progress

| Service | Total | Reviewed | Remaining |
|---------|-------|----------|-----------|
| Client Hooks | 41 | 0 | 41 |
| Client Contexts | 2 | 0 | 2 |
| Client Lib | 30 | 0 | 30 |
| Client Components | ~65 | 0 | ~65 |
| Client Pages | 14 | 0 | 14 |
| Server Controllers | 17 | 0 | 17 |
| Server Scheduler Jobs | 32 | 0 | 32 |
| Server Scheduler API | 8 | 0 | 8 |
| Server SupabaseClient | 21 | 0 | 21 |
| Python Routes | 45 | 0 | 45 |
| Python Services | 42 | 0 | 42 |
| Python Lib | 28 | 0 | 28 |
| **Total** | **~345** | **0** | **~345** |

---

## Notes

- Mark items with `[x]` as you review them
- Add comments in this file for any issues found
- Update the progress table as you complete reviews
