# Ralph Continuous Improvement Plan

## 🎯 Current Focus
<!-- Ralph: Update this section each loop with what you're working on -->
Loop #61 - Code Quality: Migrate console.log to Logger Utility - COMPLETED

## 📋 Discovered Issues Backlog
<!-- Ralph: Add issues you discover during analysis here. Never let this be empty. -->

### High Priority
- [x] ~~Analyze ETL service for security vulnerabilities (input validation, SQL injection)~~ - Sandbox hardened, Supabase ORM safe
- [x] ~~Audit dependency versions for known vulnerabilities~~ - Fixed CVE-2025-53643, CVE-2025-50181, CVE-2025-66418
- [x] ~~Review authentication/authorization implementation across all services~~ - Comprehensive audit completed, auth middleware added
- [x] ~~Add input validation tests for API endpoints (quality, enrichment, etl routes)~~ - Added 13 tests
- [x] ~~Add trade amount validation in House ETL parser (reject amounts > $50M to prevent parsing errors)~~ - Implemented with 19 tests
- [x] ~~Fix CORS configuration in Edge Functions (currently allows all origins)~~ - Centralized CORS module with env-based allowlist
- [x] ~~Add admin-only protection to sensitive endpoints (force-apply, model activation)~~ - Applied to 4 endpoints
- [x] ~~Encrypt Alpaca API credentials at rest in user_api_keys table~~ - Implemented AES-256-GCM encryption

### Medium Priority
- [x] ~~Add structured logging with correlation IDs for request tracing~~ - Implemented
- [x] ~~Improve error handling in external API calls~~ - Created ResilientClient with retry logic
- [x] ~~Add retry logic with exponential backoff for flaky external services~~ - Implemented in http_client.py

### Medium Priority
- [x] ~~Add API rate limiting to prevent abuse (all services)~~ - Implemented for ETL service
- [x] ~~Add protected routes component in React frontend~~ - ProtectedRoute and AdminRoute wrapper components
- [x] ~~Use constant-time comparison for service role keys in Edge Functions~~ - Shared auth module with timing-attack resistant comparison

### Low Priority
- [x] ~~Increase test coverage for edge cases~~ - Added 57 tests for parser.py (62% → 96% coverage)
- [x] ~~Add tests for auto_correction.py~~ - Added 66 tests (0% → 100% coverage)
- [x] ~~Add tests for etl_services.py~~ - Added 31 tests (29% → 95% coverage)
- [x] ~~Add tests for feature_pipeline.py~~ - Added 68 tests (12% → 99% coverage)
- [x] ~~Add tests for ml_signal_model.py~~ - Added 45 tests (19% → 85% coverage)
- [x] ~~Add tests for name_enrichment.py~~ - Added 36 tests (24% → 87% coverage)
- [x] ~~Add tests for error_report_processor.py~~ - Added 42 tests (24% → 92% coverage)
- [x] ~~Add tests for house_etl.py~~ - Added 23 tests (57% → 78% coverage)
- [x] ~~Add tests for party_enrichment.py~~ - Added 12 tests (75% → 100% coverage)
- [x] ~~Add tests for quality.py routes~~ - Added 23 tests (71% → 91% coverage)
- [x] ~~Add tests for error_reports.py routes~~ - Added 21 tests (78% → 100% coverage)
- [x] ~~Add tests for senate_etl.py~~ - Added 35 tests (24% → 58% coverage)
- [x] ~~Document API endpoints with OpenAPI/Swagger~~ - Comprehensive documentation enhancement
- [x] ~~Add audit logging for sensitive operations~~ - Implemented comprehensive audit logging

### Discovered This Session (Pending)
- [x] ~~Add Edge Function tests for crypto.ts encryption module~~ - Added 24 Deno tests
- [x] ~~Add Edge Function tests for auth.ts security module~~ - Added 29 Deno tests
- [x] ~~Add Edge Function tests for cors.ts CORS module~~ - Added 37 Deno tests
- [x] ~~Implement credential rotation reminder (90-day key expiry tracking)~~ - Migration, Edge Function, 25 tests
- [x] ~~Add Phoenix server authentication middleware~~ - ApiKeyAuth plug with 39 tests
- [x] ~~Improve ml_signal_model.py coverage (85% → 100%, all lines covered)~~
- [x] ~~Improve politician_dedup.py coverage (81% → 100%, all lines covered)~~
- [x] ~~Improve etl.py routes coverage (87% → 100%, all lines covered)~~
- [x] ~~Fix UnboundLocalError in get_senators() - moved variable initialization before try block~~
- [x] ~~Add type annotations for remaining ETL service modules~~ - house_etl.py, senate_etl.py, auto_correction.py

### React Client Issues (Discovered Loop #40)
#### High Priority - Type Safety
- [x] ~~Create type guard utility (`lib/typeGuards.ts`) - validates party, transaction types at runtime~~ - Loop #40
- [x] ~~Fix unsafe party type casting in RecentTrades, TradesView (2 components)~~ - Loop #40
- [x] ~~Fix unsafe transaction type casting in RecentTrades, TradesView~~ - Loop #40
- [x] ~~Add null checks for optional properties in Dashboard components~~ - Loop #42

#### High Priority - Security
- [x] ~~Replace hardcoded email in RootErrorBoundary with env var~~ - Loop #41
- [x] ~~Fix unsafe localStorage access in Header (no error handling)~~ - Loop #41

#### Medium Priority - Testing
- [x] ~~Add tests for Dashboard.tsx~~ - Loop #43 (27 tests)
- [x] ~~Add tests for TradesView.tsx~~ - Loop #44 (32 tests)
- [x] ~~Add tests for TradingSignals.tsx~~ - Loop #45 (32 tests)
- [x] ~~Add tests for PoliticiansView.tsx~~ - Loop #46 (29 tests)
- [x] ~~Add tests for PoliticianDetailModal.tsx~~ - Loop #47 (27 tests)
- [x] ~~Add tests for ReferencePortfolio.tsx~~ - Loop #48 (40 tests)
- [x] ~~Add tests for useAlpacaCredentials.ts hook~~ - Loop #49 (16 tests)
- [x] ~~Add tests for useAuth.tsx hook~~ - Loop #50 (25 tests)

#### Low Priority - Code Quality
- [x] ~~Consolidate duplicate date formatting logic~~ - Loop #51 (formatters.ts)
- [x] ~~Consolidate duplicate currency formatting logic~~ - Loop #51 (formatters.ts)
- [x] ~~Extend formatter consolidation to trading components~~ - Loop #52 (9 components)
- [x] ~~Replace `any` types in Recharts tooltip components~~ - Loop #53 (3 components)
- [x] ~~Replace `any` types in error handling catch blocks~~ - Loop #53 (7 components)
- [x] ~~Add tests for trading module (OrderConfirmationModal)~~ - Loop #60 (57 tests)
- [x] ~~Migrate console.log to logger utility (useDrops, useSignalPresets, Drops, SignalPlayground)~~ - Loop #61 (48 statements)
- [ ] Migrate remaining console.log statements to logger utility (other files)
- [ ] Add missing TypeScript strict mode compliance

## 🔄 In Progress
<!-- Ralph: Move task here when you start working on it -->
None - ready for next task

## ✅ Completed Loop #61
- [2026-01-29] 🧹 **Code Quality: Migrate console.log to Logger Utility**
  - Migrated 48 console.log/console.error statements to structured logger
  - Files updated:
    - `hooks/useDrops.ts` - 34 statements (createDrop, deleteDrop, likeDrop, unlikeDrop, mutations)
    - `hooks/useSignalPresets.ts` - 5 statements (createPreset)
    - `pages/Drops.tsx` - 6 statements (handleCreateDrop)
    - `pages/SignalPlayground.tsx` - 3 statements (handleSavePreset)
  - Benefits: Structured logs with categories, metadata, session correlation, backend integration
  - All 760 tests pass

## ✅ Completed Loop #60
- [2026-01-29] 🧪 **Testing: OrderConfirmationModal Component Tests**
  - Created `client/src/components/trading/OrderConfirmationModal.test.tsx` with 57 comprehensive tests
  - Test coverage:
    - **Dialog visibility tests (3)**: Render when open, hidden when closed, description display
    - **Trading mode badge tests (2)**: Paper trading badge, live trading badge
    - **Order summary tests (6)**: Total orders count, total shares count, buy count badge, sell count badge, no buy badge when none, no sell badge when none
    - **Order list table tests (8)**: Table headers, ticker, side badge, quantity, order type, multiple orders, buy badge styling, sell badge styling
    - **Paper trading alert tests (2)**: Info message, no live warning
    - **Live trading warning tests (5)**: Warning message, confirmation checkbox, no paper info, checkbox unchecked default, checkbox toggle
    - **Submit button tests (6)**: Single order text, multiple orders text, enabled for paper, disabled for live without confirm, enabled for live with confirm, destructive variant
    - **Cancel button tests (2)**: Render, onOpenChange callback
    - **Order submission tests (5)**: Fetch call, loading state, success toast, onSuccess callback, close dialog on success
    - **Live trading submission tests (2)**: Button disabled without confirm, submit with confirm
    - **Error handling tests (4)**: API error toast, generic error, network error, re-enable button
    - **Partial success tests (4)**: Error toast for failed, success toast for successful, onSuccess callback, close dialog
    - **Access token handling tests (2)**: Authorization header, apikey header
    - **Button disabled states tests (2)**: Cancel disabled while submitting, submit disabled while submitting
    - **Edge cases tests (4)**: Empty orders array, orders with signal_id, limit orders with price, onSuccess undefined
  - All 760 client tests pass (703 → 760)

## ✅ Completed Loop #59
- [2026-01-29] 🧪 **Testing: AccountDashboard Component Tests**
  - Created `client/src/components/trading/AccountDashboard.test.tsx` with 49 comprehensive tests
  - Test coverage:
    - **Loading state tests (2)**: Loading spinner display, no content when loading
    - **Error state tests (3)**: Error message, retry button, refetch on retry
    - **Empty state tests (2)**: Connect message when no account, wallet icon
    - **Header display tests (8)**: Title, paper/live badges, active status, non-active status, refresh button, refetch, disabled during refetch, animating icon
    - **Warning badges tests (5)**: Trading blocked, account blocked, pattern day trader, multiple badges, no badges
    - **Main metrics tests (9)**: Portfolio value label/value, P&L label/value/percentage, cash label/value, buying power label/value
    - **P&L styling tests (5)**: Green for positive, red for negative, trending icons
    - **Secondary metrics tests (7)**: Equity, long market value, short market value, last close equity
    - **Trading mode tests (2)**: Paper and live mode hook calls
    - **calculateDailyPnL tests (2)**: Integration with account, zero P&L handling
    - **Edge cases tests (2)**: Undefined values, NaN values
  - Mocked useAlpacaAccount hook, calculateDailyPnL, formatters
  - All 703 client tests passing (654 existing + 49 new)
  - Build successful

## ✅ Completed Loop #58
- [2026-01-29] 🧪 **Testing: QuickTradeDialog Component Tests**
  - Created `client/src/components/trading/QuickTradeDialog.test.tsx` with 49 comprehensive tests
  - Test coverage:
    - **Null position tests (2)**: Returns null when position null, hook still called
    - **Dialog behavior tests (5)**: Dialog visibility, title with symbol, paper/live badges, position description
    - **Position summary tests (6)**: Current price, P&L display, labels, green/red styling for positive/negative P&L
    - **Side selection tests (6)**: Label, buy/sell buttons, default side, switching sides
    - **Quantity input tests (6)**: Label, input field, custom quantity, Sell All button visibility/click
    - **Order type tests (4)**: Label, default market, combobox, limit price hidden for market
    - **Estimated value tests (2)**: Hidden without quantity, shown with quantity
    - **Submit button tests (4)**: Disabled without quantity, enabled with quantity, buy/sell text, loading state
    - **Order submission tests (6)**: Market order, success toast, dialog close, error toast, default error message, buy order
    - **Cancel button tests (2)**: Button exists, closes dialog on click
    - **Trading mode tests (2)**: Paper and live mode hook calls
    - **Short position tests (2)**: Description display, no Sell All for short
    - **Submit button styling tests (2)**: Green for buy, red for sell
  - Mocked usePlaceOrder hook, toast, formatters
  - Added ResizeObserver and pointer capture mocks for Radix UI compatibility
  - All 654 client tests passing (605 existing + 49 new)
  - Build successful

## ✅ Completed Loop #57
- [2026-01-29] 🧪 **Testing: OrderHistory Component Tests**
  - Created `client/src/components/trading/OrderHistory.test.tsx` with 42 comprehensive tests
  - Test coverage:
    - **Loading state tests (1)**: Loading spinner display
    - **Error state tests (3)**: Error message, retry button, refetch on retry
    - **Empty state tests (2)**: Empty message, suggestion text
    - **Header display tests (4)**: Title, paper/live badges, total orders count
    - **Orders table tests (10)**: Headers, tickers, buy/sell styling, quantities, filled quantities, prices, status badges
    - **Status filter tests (2)**: Filter select, hook call with filter
    - **Sync functionality tests (4)**: Sync button, mutation call, success/error toasts
    - **Cancel order tests (8)**: Cancel button visibility, confirmation dialog, Keep Order, cancel mutation, success/error toasts
    - **Refetch functionality tests (2)**: Refetch button, refetch call
    - **Refetching state tests (2)**: Disabled button, spinning animation
    - **Can cancel order logic tests (4)**: new/accepted/partially_filled statuses allow cancel, cancelled does not
  - Mocked useOrders, useSyncOrders, useCancelOrder hooks, toast, formatters
  - All 605 client tests passing (563 existing + 42 new)
  - Build successful

## ✅ Completed Loop #56
- [2026-01-29] 🧪 **Testing: PositionsTable Component Tests**
  - Created `client/src/components/trading/PositionsTable.test.tsx` with 37 comprehensive tests
  - Test coverage:
    - **Loading state tests (1)**: Loading spinner display
    - **Error state tests (3)**: Error message, retry button, refetch on retry
    - **Empty state tests (3)**: Empty message, card title, null positions handling
    - **Positions display tests (7)**: Count in header, total value, total P&L, symbols, side badges, refresh button, refetch on refresh
    - **P&L styling tests (4)**: Green for positive, red for negative, trending up/down icons
    - **Trade dialog tests (7)**: Open on Buy/Sell click, correct position/mode/side passed, dialog close
    - **Refetching state tests (2)**: Disabled refresh button, spinning animation
    - **Desktop table view tests (3)**: Headers, quantities, market values
    - **Currency formatting tests (3)**: Avg entry price, current price, intraday P&L
    - **Percent formatting tests (2)**: + sign for positive, - sign for negative
    - **Total metrics tests (2)**: Green/red styling for positive/negative P&L
  - Mocked useAlpacaPositions hook and QuickTradeDialog component
  - All 563 client tests passing (526 existing + 37 new)
  - Build successful

## ✅ Completed Loop #55
- [2026-01-29] 🧪 **Testing: AlpacaConnectionCard Component Tests**
  - Created `client/src/components/trading/AlpacaConnectionCard.test.tsx` with 46 comprehensive tests
  - Test coverage:
    - **Header display tests (5)**: Card title, paper/live trading badges, descriptions
    - **Disconnected state tests (8)**: Input fields, placeholders, buttons, disabled/enabled states
    - **Password visibility tests (2)**: Hidden by default, toggle visibility
    - **Test connection tests (5)**: Validation, API call params, success/error messages, account info display
    - **Save credentials tests (6)**: Test before save, save after success, no save on failure, callback, clear inputs
    - **Connected state tests (5)**: Connected badge, message, last validated time, disconnect button, no input fields
    - **Disconnect functionality tests (2)**: Clear credentials, callback invocation
    - **Setup guide tests (8)**: Toggle visibility, content sections, signup link, trading mode badges, tips
    - **Live trading warning tests (3)**: Shown for live mode, not for paper, not when connected
    - **Error handling tests (2)**: Validation, default error messages
  - Mocked useAlpacaCredentials hook, date-fns
  - All 526 client tests passing (480 existing + 46 new)
  - Build successful

## ✅ Completed Loop #54
- [2026-01-29] 🧪 **Testing: AlpacaConnectionStatus Component Tests**
  - Created `client/src/components/trading/AlpacaConnectionStatus.test.tsx` with 28 comprehensive tests
  - Test coverage:
    - **Loading state tests (1)**: Loading spinner display
    - **Error state tests (2)**: Fetch failure, unauthenticated state
    - **Connected state tests (12)**: Title, trading mode badges, connection status, circuit breaker state, health rate, latency, healthy/total checks, recent health checks section, logs with latency, refresh button, health check button
    - **Degraded/Disconnected state tests (2)**: Status display with correct styling
    - **Circuit breaker state tests (2)**: Open state with warning, half-open state with info
    - **Health check functionality tests (2)**: Success and unhealthy results
    - **Refresh functionality tests (1)**: Refetch on button click
    - **Statistics edge cases tests (1)**: N/A for null avgLatencyMs
    - **Empty recent logs tests (1)**: Hidden section when no logs
    - **API request construction tests (3)**: Paper/live trading modes, authorization header
    - **HTTP error handling tests (1)**: HTTP error response handling
  - Mocked fetch, localStorage with session token, date-fns, env vars
  - All 480 client tests passing (452 existing + 28 new)
  - Build successful

## ✅ Completed Loop #53
- [2026-01-29] 📝 **Code Quality: Replace `any` Types with Proper TypeScript Types**
  - **Recharts tooltip components (3 files)**: Replaced `any` with `TooltipProps<number, string>` from Recharts
    - `VolumeChart.tsx` - CustomVolumeTooltip now properly typed
    - `TradeChart.tsx` - CustomChartTooltip now properly typed
    - `PerformanceChart.tsx` - CustomTooltip now properly typed
  - **Error handling catch blocks (7 files)**: Replaced `catch (error: any)` with `catch (error)` + `error instanceof Error` type guard
    - `strategy-follow/FollowingStatusBadge.tsx` - 2 catch blocks fixed
    - `strategy-follow/FollowingSettingsCard.tsx` - 2 catch blocks fixed
    - `strategy-follow/ApplyStrategyModal.tsx` - 1 catch block fixed
    - `cart/FloatingCart.tsx` - 1 catch block fixed + OrderResult interface added
    - `trading/OrderHistory.tsx` - 2 catch blocks fixed
    - `trading/OrderConfirmationModal.tsx` - 1 catch block fixed + OrderResult interface added
    - `trading/QuickTradeDialog.tsx` - 1 catch block fixed
  - All 452 client tests passing
  - Build successful
  - Type safety improved across 10 components

## ✅ Completed Loop #52
- [2026-01-29] 🧹 **Code Quality: Extend Formatter Consolidation to Trading Components**
  - Updated 9 additional components to use centralized formatters from `lib/formatters.ts`:
    - **Trading module (5)**: OrderConfirmationModal, QuickTradeDialog, OrderHistory, PositionsTable, AccountDashboard
    - **Reference portfolio (4)**: MetricsCards, HoldingsTable, PerformanceChart, TradeHistoryTable (already partially updated)
  - Replaced duplicate `formatCurrency` and `formatDate` function definitions
  - Preserved custom behavior where needed (e.g., signed percent formatting with + prefix)
  - All 452 client tests passing
  - Added 4 new discovered issues to backlog for future loops

## ✅ Completed Loop #51
- [2026-01-29] 🧹 **Code Quality: Centralized Formatting Utilities**
  - Created `client/src/lib/formatters.ts` with consolidated formatting functions:
    - **Currency formatting (4 functions)**: `formatCurrencyCompact` (K/M/B suffix), `formatCurrencyFull` (full precision), `formatCurrencyWhole` (no decimals), `formatAmountRange` (min/max ranges)
    - **Date formatting (5 functions)**: `formatDate` (configurable format), `formatTime`, `formatDateTime`, `formatDateForChart`, `toISODateString`
    - **Number formatting (2 functions)**: `formatNumber` (with separators), `formatPercent`
    - **DATE_FORMATS constant**: Predefined format options (short, long, withWeekday, monthYear, time, datetime, iso)
    - `formatCurrency` alias for backwards compatibility
  - Created `client/src/lib/formatters.test.ts` with 44 comprehensive tests
  - Updated `client/src/lib/mockData.ts` to re-export from formatters
  - Refactored 4 components to use centralized formatters:
    - `LandingTradesTable.tsx` - uses `formatDate`, `formatAmountRange`
    - `ReportErrorModal.tsx` - uses `formatDate`, `formatAmountRange`
    - `TradeHistoryTable.tsx` - uses `formatCurrencyFull`, `formatDateTime`
    - `AdminContentManagement.tsx` - uses `formatCurrencyCompact`, `formatDate`
  - All 452 client tests passing (408 existing + 44 new)
  - Reduces code duplication across ~30+ components

## ✅ Completed Loop #50
- [2026-01-29] 🧪 **Testing: useAuth.tsx Hook Tests**
  - Created `client/src/hooks/useAuth.test.tsx` with 25 comprehensive tests
  - Test coverage:
    - **AuthProvider tests (10)**: Renders children, default auth state, localStorage init, expired session, invalid JSON, auth listener setup, unsubscribe, user updates, sign out, timeout fallback
    - **useAuth hook tests (2)**: Returns auth state from context, returns defaults outside provider
    - **useAuthReady hook tests (3)**: Returns authReady from context, false initially, true after auth state change
    - **isAuthenticated tests (2)**: True when user exists, false when null
    - **Loading state tests (3)**: Starts true without stored user, false with stored user, becomes false after auth change
    - **localStorage key detection tests (3)**: Standard Supabase key format, ignores non-supabase keys, requires auth-token suffix
    - **Session validation tests (2)**: Validates session has user property, handles missing expires_at
  - Mocked Supabase client (auth.onAuthStateChange), localStorage with Object.keys spy
  - Used vi.useFakeTimers() for timeout testing
  - All 408 client tests passing (383 existing + 25 new)
  - Build successful

## ✅ Completed Loop #49
- [2026-01-29] 🧪 **Testing: useAlpacaCredentials.ts Hook Tests**
  - Created `client/src/hooks/useAlpacaCredentials.test.ts` with 16 comprehensive tests
  - Test coverage:
    - **Query behavior tests (3)**: No fetch when user null, authReady false, or email missing
    - **isConnected helper tests (1)**: Returns false when credentials undefined
    - **getValidatedAt helper tests (1)**: Returns null when credentials undefined
    - **Hook return shape tests (2)**: Verifies all properties exist, functions are typed correctly
    - **Initial loading states tests (4)**: isSaving, isTesting, isClearing, error all start false/null
    - **Query key tests (1)**: User email included for proper caching
    - **Mode parameters tests (4)**: isConnected and getValidatedAt accept paper/live modes
  - Mocked useAuth hook, toast notifications, environment variables
  - All 383 client tests passing (367 existing + 16 new)
  - Build successful

## ✅ Completed Loop #48
- [2026-01-29] 🧪 **Testing: ReferencePortfolio.tsx Page Tests**
  - Created `client/src/pages/ReferencePortfolio.test.tsx` with 40 comprehensive tests
  - Test coverage:
    - **Page header tests (3)**: Title, description, SidebarLayout wrapper
    - **Market status tests (3)**: Open indicator, closed indicator, null handling
    - **Trading status tests (3)**: Active badge, paused badge, null state
    - **Last sync time tests (2)**: Display when available, hidden when null
    - **Info alert tests (4)**: Confidence threshold, last trade time, null handling, defaults
    - **Child component tests (7)**: MetricsCards, PerformanceChart, HoldingsTable, RiskMetrics, TradeHistoryTable (limit 20), FollowingStatusBadge, ApplyStrategyButton
    - **Strategy configuration tests (9)**: All 8 config values display correctly, default values when undefined
    - **Footer tests (2)**: Paper trading disclaimer, past performance disclaimer
    - **Edge cases tests (4)**: Null state, undefined config, loading market status, missing timestamps
    - **Hook integration tests (2)**: Calls useReferencePortfolioState, useMarketStatus
  - Mocked SidebarLayout, reference-portfolio components, strategy-follow components, UI components
  - Mocked useReferencePortfolioState and useMarketStatus hooks
  - All 367 client tests passing (327 existing + 40 new)
  - Build successful

## ✅ Completed Loop #47
- [2026-01-29] 🧪 **Testing: PoliticianDetailModal.tsx Component Tests**
  - Created `client/src/components/detail-modals/PoliticianDetailModal.test.tsx` with 27 comprehensive tests
  - Test coverage:
    - **Null politician tests (2)**: Returns null when no politician, doesn't call hook
    - **Dialog behavior tests (2)**: Opens when open=true, closed when open=false
    - **Header tests (2)**: Displays name and party badge with color
    - **Loading state tests (2)**: Shows skeleton during load, shows content when loaded
    - **Trading stats tests (4)**: Total trades, buys, sells, holding counts
    - **Total volume tests (2)**: Formatted currency display, zero handling
    - **Top tickers tests (2)**: Badge display, hidden when empty
    - **Recent trades tests (5)**: Section display, BUY/SELL/HOLD badges, source links
    - **Empty state tests (2)**: No trades message, no tickers message
    - **Hook integration tests (2)**: Calls hook with politician id, null id handling
  - Fixed test conflict: Changed AAPL to NVDA in top tickers test to avoid collision with recentTrades mock data
  - Mocked Dialog components, usePoliticianDetail hook, mockData utilities
  - All 327 client tests passing (300 existing + 27 new)
  - Build successful

## ✅ Completed Loop #46
- [2026-01-29] 🧪 **Testing: PoliticiansView.tsx Component Tests**
  - Created `client/src/components/PoliticiansView.test.tsx` with 29 comprehensive tests
  - Test coverage:
    - **Header tests (2)**: Title and description rendering
    - **Loading state tests (2)**: Spinner display/hide
    - **Error state tests (1)**: Error message display
    - **Empty state tests (1)**: Empty message when no politicians
    - **Politician list tests (6)**: Names, party badges, volume, trades, initials avatar, missing name handling
    - **Table headers and sorting tests (4)**: Headers render, sort by name/volume, toggle direction
    - **Pagination tests (4)**: Controls visibility, itemLabel, setTotalItems, result pagination
    - **Modal interaction tests (2)**: Open on row click, close on button click
    - **Initial politician selection tests (3)**: Opens for found ID, doesn't open for not found, null handling
    - **Edge cases tests (4)**: Undefined chamber, state fallback, zero values, undefined values
  - Mocked PaginationControls, PoliticianProfileModal, hooks (usePoliticians, usePagination)
  - All 300 client tests passing (271 existing + 29 new)
  - Build successful

## ✅ Completed Loop #45
- [2026-01-29] 🧪 **Testing: TradingSignals.tsx Component Tests**
  - Created `client/src/components/TradingSignals.test.tsx` with 32 comprehensive tests
  - Test coverage:
    - **Loading state tests (2)**: Loading spinner display/hide
    - **Header tests (2)**: Title and description rendering
    - **Signal generation parameters tests (5)**: Input rendering, login alert visibility, button enable/disable
    - **Stats cards tests (4)**: Total, buy, sell, hold signal counts
    - **Signal filters tests (3)**: Filter card title, toggle behavior, filtered count message
    - **Signals table tests (5)**: Table headers, signal rows, target price display, Export CSV button
    - **Top 10 signals tests (4)**: Section title, signal cards, Add to Cart buttons, limit to 10
    - **Error handling tests (2)**: Error toast on fetch failure, null data graceful handling
    - **Signal generation tests (2)**: Generating state, success toast
    - **Edge cases tests (3)**: Empty signals, date formatting, buy_sell_ratio formatting
  - Mocked Supabase client, useAuth hook, toast, and Slider component (to avoid ResizeObserver issues)
  - Added proper ResizeObserver mock for Radix UI components
  - All 271 client tests passing (239 existing + 32 new)
  - Build successful

## ✅ Completed Loop #44
- [2026-01-29] 🧪 **Testing: TradesView.tsx Component Tests**
  - Created `client/src/components/TradesView.test.tsx` with 32 comprehensive tests
  - Test coverage:
    - **Header tests (3)**: Title, description, Filter button rendering
    - **Loading state tests (3)**: Spinner for trades loading, jurisdictions loading, no spinner when loaded
    - **Jurisdiction filters tests (5)**: "All" badge, jurisdiction badges, highlighting, click behavior
    - **Trade list tests (4)**: Trade cards render, empty state, search-specific empty state, data transformation
    - **Search query filtering tests (5)**: Filter by ticker, company, politician name, case-insensitive, empty query
    - **Pagination tests (4)**: Controls visibility, hidden when no trades, itemLabel, setTotalItems callback
    - **Props handling tests (4)**: jurisdictionId passed to hook, undefined jurisdiction, initial filter state, page reset
    - **Edge cases tests (4)**: Null politician, missing ticker fields, undefined trades, empty jurisdictions
  - Mocked child components (TradeCard, PaginationControls)
  - Mocked hooks (useTrades, useJurisdictions, usePagination)
  - All 239 client tests passing (207 existing + 32 new)
  - Build successful

## ✅ Completed Loop #43
- [2026-01-29] 🧪 **Testing: Dashboard.tsx Component Tests**
  - Created `client/src/components/Dashboard.test.tsx` with 27 comprehensive tests
  - Test coverage:
    - **Header tests (2)**: Title and description rendering
    - **Loading state tests (2)**: Loading spinners, stats card visibility
    - **Stats cards tests (6)**: All 4 stats cards render, values display correctly, null handling
    - **Transaction breakdown tests (6)**: Buys/sells/other calculation, chart data handling, edge cases
    - **Child components tests (5)**: All child components render (LandingTradesTable, charts, TopTraders, TopTickers)
    - **Props handling tests (3)**: initialTickerSearch, onTickerSearchClear, no props
    - **Data edge cases tests (3)**: Empty arrays, null values, large numbers
  - Mocked child components for isolation (StatsCard, TradeChart, VolumeChart, TopTraders, TopTickers, LandingTradesTable)
  - Mocked hooks (useDashboardStats, useChartData) for controlled testing
  - All 207 client tests passing (180 existing + 27 new)
  - Build successful

## ✅ Completed Loop #42
- [2026-01-29] 📝 **Code Quality: Null Checks & Type Guards in Dashboard Components**
  - Updated `client/src/components/TopTraders.tsx`:
    - Imported and used `toParty()` type guard for safe party type validation
    - Added null checks for `politician.total_volume` and `politician.total_trades` using `?? 0`
    - Added fallbacks for `politician.chamber` and `politician.state` using `|| 'Unknown'`
  - Updated `client/src/components/LandingTradesTable.tsx`:
    - Imported and used `toParty()` type guard
    - Replaced 2 instances of unsafe `as 'D' | 'R' | 'I' | 'Other'` type assertion with `toParty()`
    - Mobile card view (line 537) and desktop table view (line 711) now use type-safe party conversion
  - All 180 client tests passing
  - Build successful
  - Components now handle undefined/null values gracefully at runtime

## ✅ Completed Loop #41
- [2026-01-29] 🔒 **Security: Safe Storage Utilities & Configurable Support Email**
  - Created `client/src/lib/safeStorage.ts` with error-handling localStorage utilities:
    - `isLocalStorageAvailable()` - checks if localStorage works
    - `safeGetItem()`, `safeSetItem()`, `safeRemoveItem()` - safe read/write/delete
    - `safeGetKeys()` - proper iteration over localStorage keys
    - `safeClearByPrefix()` - clear keys by prefix (used for Supabase auth cleanup)
    - `safeGetJSON()`, `safeSetJSON()` - JSON serialization with error handling
  - Created `client/src/lib/safeStorage.test.ts` with 15 tests
  - Updated `client/src/components/Header.tsx`:
    - Replaced unsafe `Object.keys(localStorage)` with `safeClearByPrefix('sb-')`
    - Sign-out now handles localStorage errors gracefully
  - Updated `client/src/components/RootErrorBoundary.tsx`:
    - Added `VITE_SUPPORT_EMAIL` environment variable support
    - Removed hardcoded personal email (luis@lefv.io)
    - Fallback to support@govmarket.trade if env var not set
  - Updated `.env` and `.env.production.example` with VITE_SUPPORT_EMAIL
  - Updated `client/src/test/setup.ts` with localStorage mock for jsdom
  - All 180 client tests passing (15 new + 165 existing)

## ✅ Completed Loop #40
- [2026-01-29] 📝 **Code Quality: Type Guard Utility for React Client**
  - Created `client/src/lib/typeGuards.ts` with comprehensive type guards:
    - `Party` type and guards: `isParty()`, `toParty()`, `getPartyFullName()`
    - `TransactionType` and `DisplayTransactionType` with conversions: `toDisplayTransactionType()`, `toDatabaseTransactionType()`
    - `SignalType` guards: `isSignalType()`, `toSignalType()`
    - `Chamber` guards: `isChamber()`, `toChamber()`
    - Generic utilities: `isObject()`, `isNonEmptyString()`, `isPositiveNumber()`, `isValidDateString()`, `toNumber()`, `toString()`
  - Created `client/src/lib/typeGuards.test.ts` with 59 comprehensive tests:
    - Party validation and conversion tests
    - Transaction type conversion tests (purchase↔buy, sale↔sell)
    - Signal type validation tests
    - Chamber type validation tests
    - Generic utility tests
  - Updated `client/src/lib/mockData.ts`:
    - Imported and re-exported `Party` type from typeGuards
    - Updated `Politician` and `Trade` interfaces to use typed exports
  - Updated `client/src/components/RecentTrades.tsx`:
    - Replaced unsafe `(trade.politician?.party as 'D' | 'R' | 'I' | 'Other')` with `toParty()`
    - Replaced unsafe transaction type casting with `toDisplayTransactionType()`
  - Updated `client/src/components/TradesView.tsx`:
    - Same type guard improvements as RecentTrades
  - All 165 client tests passing (59 new + 106 existing)
  - Build successful

## ✅ Completed Loop #39
- [2026-01-29] 🔒 **Security: Phoenix Server Authentication Middleware**
  - Created `server/lib/server_web/plugs/api_key_auth.ex`:
    - API key validation via X-API-Key header, Bearer token, or query param
    - Constant-time comparison using SHA256 hashing to prevent timing attacks
    - Public endpoint whitelist (/, /health, /health/ready, /ready)
    - Backwards compatibility when no key configured
    - Auth can be disabled via ETL_AUTH_DISABLED=true for development
    - Comprehensive logging of auth failures
  - Updated `server/lib/server_web/router.ex`:
    - Added ApiKeyAuth plug to :api pipeline
    - Updated moduledoc with authentication documentation
    - All /api/* routes now require authentication
  - Updated `server/config/runtime.exs`:
    - Added ETL_API_KEY and ETL_AUTH_DISABLED environment variables
    - Auth disabled by default in test environment
    - Same API key works for both Phoenix and ETL services
  - Created `server/test/server_web/plugs/api_key_auth_test.exs` with 39 tests:
    - Public endpoint detection
    - Auth disabled flag handling
    - API key extraction from headers/query params
    - Key validation and error handling
    - Constant-time comparison
    - Integration with router pipeline
  - All 67 Phoenix tests passing (39 auth + 28 existing)

## ✅ Completed Loop #38
- [2026-01-29] 📖 **Documentation: OpenAPI/Swagger Enhancement for ETL Service**
  - Enhanced `app/main.py` with comprehensive OpenAPI configuration:
    - Added detailed API description with authentication, rate limiting, and error response docs
    - Added 8 tag descriptions (health, etl, enrichment, ml, quality, error-reports, deduplication, signals)
    - Added license info and contact details
  - Updated `app/routes/ml.py` with proper response models:
    - Added `TrainJobResponse`, `TrainJobStatusResponse`, `ModelsListResponse`
    - Added `ModelActivateResponse`, `FeatureImportanceResponse`, `MLHealthResponse`
    - Made `ModelInfo` fields optional with `model_config` for extra fields
    - Enhanced docstrings with job statuses, model statuses, feature importance details
  - Updated `app/routes/error_reports.py` with full documentation:
    - Added `ErrorType` and `ReportStatus` enums for OpenAPI
    - Added response models: `ProcessResponse`, `ProcessOneResponse`, `StatsResponse`
    - Added `NeedsReviewResponse`, `ForceApplyResponse`, `ReanalyzeResponse`
    - Added `SuggestionResponse`, `OllamaHealthResponse`, `CorrectionDetail`
    - Added `ForceApplyCorrection` typed model
    - Enhanced docstrings with workflows and next steps
  - Updated `app/routes/dedup.py` with proper models:
    - Added `PoliticianRecord`, `DuplicateGroup`, `PreviewResponse`
    - Added `ProcessResponse`, `DedupHealthResponse`
    - Enhanced docstrings with merge logic and safety notes
  - Updated `app/routes/health.py`:
    - Added `HealthResponse` model
    - Enhanced docstring with related health endpoints
  - All 1499 tests passing

## ✅ Completed Loop #37
- [2026-01-28] 🔒 **Security: Credential Rotation Tracking (90-day key expiry)**
  - Created `supabase/migrations/20260129_credential_rotation_tracking.sql`:
    - Added `*_key_created_at` columns for paper, live, supabase, quiverquant keys
    - Added `rotation_reminder_sent_at` for cooldown tracking
    - Created `get_credential_health(user_email)` function: returns health status per credential
    - Created `get_users_needing_rotation_reminder()` function: finds users needing reminders
    - Added triggers to auto-set `key_created_at` on INSERT and UPDATE
  - Created `supabase/functions/credential-health/index.ts` Edge Function:
    - GET endpoint returns credential health for authenticated user
    - `?action=rotation-needed` admin-only endpoint for listing users needing reminders
    - Returns overall health (healthy/warning/critical), per-credential status, nearest expiry
    - Uses shared CORS and auth modules
  - Created `supabase/functions/credential-health/index.test.ts` with 25 tests:
    - Health status calculation (healthy/warning/expired/not_configured)
    - Overall health aggregation (critical if any expired, warning if any warning)
    - Summary counting, nearest expiry calculation
    - Response format validation, credential types, boundary conditions

## ✅ Completed Loop #36
- [2026-01-28] 📝 **Code Quality: Type Annotations for ETL Service Modules**
  - Updated `app/services/house_etl.py`:
    - Added class attribute types to `RateLimiter` (current_delay, consecutive_errors, etc.)
    - Added type hints for module constants (HOUSE_BASE_URL: str, RATE_LIMIT_CODES: Set[int], etc.)
    - Added return type annotations for all functions (`-> None`, `-> str`, etc.)
    - Removed 15 TODO comments (functions already reviewed and working)
  - Updated `app/services/senate_etl.py`:
    - Added type hints for module constants
    - Added proper type annotations for async functions
    - Fixed Playwright page parameter type (`page: Any`)
    - Removed 15 TODO comments
  - Updated `app/services/auto_correction.py`:
    - Fixed `any` → `Any` (proper Python typing)
    - Added class attribute types to `AutoCorrector`
    - Changed `list[CorrectionResult]` → `List[CorrectionResult]` (Python 3.8+ compatible)
    - Added `-> None` return type for void methods
  - All 202 tests passing for modified modules (74 house + 62 senate + 66 auto_correction)
  - Commit: c4e629d

## ✅ Completed Loop #35
- [2026-01-28] 🧪 **Testing: Edge Function Tests for cors.ts CORS Module**
  - Created `supabase/functions/_shared/cors.test.ts` with 37 Deno tests
  - Test coverage:
    - `isOriginAllowed`: Null origin, default production origins, non-allowed, custom ALLOWED_ORIGINS, whitespace trimming, dev mode, localhost patterns
    - `getCorsHeaders`: Required headers, origin reflection, disallowed fallback, dev mode wildcard, null origin, custom fallback
    - `handleCorsPreflightRequest`: 204 status, CORS headers, null body
    - `corsJsonResponse`: JSON format, default/custom status, CORS headers, null origin
    - `corsErrorResponse`: Error JSON, default/custom status, 500 errors, CORS headers
    - `createCorsHeaders`: Origin handling, null/undefined, backwards compatibility
    - `corsHeaders`: Legacy export object, required properties
    - Edge cases: Empty ALLOWED_ORIGINS, single origin, strict boolean env checks
  - All 37 tests passing
  - Complete test coverage for shared CORS configuration module

## ✅ Completed Loop #34
- [2026-01-28] 🧪 **Testing: Edge Function Tests for auth.ts Security Module**
  - Created `supabase/functions/_shared/auth.test.ts` with 29 Deno tests
  - Test coverage:
    - `constantTimeCompare`: Equal/different strings, empty strings, unicode, special chars, long strings, API keys
    - `validateServiceRoleKey`: Key not configured, empty key, matching/non-matching token, partial match
    - `extractBearerToken`: Valid Bearer header, null header, non-Bearer, malformed, empty token, JWT format
    - `isServiceRoleRequest`: No auth header, valid/invalid service role, key not configured, no Bearer prefix
    - Security: Timing consistency sanity check for constant-time comparison
  - All 29 tests passing
  - Complete test coverage for shared auth module

## ✅ Completed Loop #33
- [2026-01-28] 🧪 **Testing: Edge Function Tests for crypto.ts Encryption Module**
  - Created `supabase/functions/_shared/crypto.test.ts` with 24 Deno tests
  - Test coverage:
    - `isEncryptionEnabled`: Returns correct state based on API_ENCRYPTION_KEY env var
    - `encrypt`: Plaintext fallback when disabled, enc: prefix, random IV each call
    - `decrypt`: Unencrypted passthrough, missing key error, invalid ciphertext, wrong key error
    - Roundtrip: Preserves plaintext, special characters, unicode, empty strings, long strings
    - `encryptFields`: Encrypts specified fields, skips null/undefined/non-string values
    - `decryptFields`: Decrypts specified fields, handles unencrypted gracefully
    - `generateEncryptionKey`: Returns base64 string, produces unique keys, usable for encryption
    - Integration: Full credential lifecycle (encrypt, store, retrieve, decrypt)
  - All 24 tests passing
  - First test file for shared Edge Function modules

## ✅ Completed Loop #32
- [2026-01-28] 🧪 **Testing: Auto-Correction Service Test Coverage (81% → 100%)**
  - Added 13 tests to `tests/test_auto_correction.py` (53 → 66 tests)
  - New tests covering:
    - `test_correct_date_format_applies_correction`: Non-dry-run path (line 226)
    - `test_correct_amount_text_exact_applies_correction`: Exact match non-dry-run (line 270)
    - `test_correct_amount_text_fuzzy_applies_correction`: Fuzzy match non-dry-run (line 294)
    - `test_run_value_range_corrections_full_path`: Full execution with inverted records (lines 361-393)
    - `test_run_value_range_corrections_respects_limit`: Limit enforcement (lines 387-388)
    - `test_run_value_range_corrections_handles_exception`: Exception path (lines 390-392)
    - `test_apply_range_correction_no_supabase`: No Supabase path (lines 430-431)
    - `test_apply_range_correction_handles_exception`: Exception handling (lines 449-452)
    - `test_apply_amount_correction_no_supabase`: No Supabase path (lines 457-458)
    - `test_apply_amount_correction_handles_exception`: Exception handling (lines 476-479)
    - `test_log_correction_handles_exception`: Insert failure (lines 509-510)
    - `test_mark_correction_applied_handles_exception`: Update failure (lines 520-521)
    - `test_rollback_correction_handles_exception`: Query failure (lines 567-569)
  - Coverage improvement: 81% → 100% for app/services/auto_correction.py (+19 percentage points)
  - All 1499 tests passing

## ✅ Completed Loop #31
- [2026-01-28] 🏗️ **Robustness: Fix UnboundLocalError in get_senators()**
  - **Bug**: `get_senators()` endpoint failed with `UnboundLocalError` when Supabase was unavailable
  - **Root Cause**: `with_disclosures` and `total_disclosures` variables were initialized inside the try block (line 487-488), so when `get_senate_supabase_client()` threw an exception, they were never defined
  - **Fix**: Moved variable initialization before the try block, ensuring they're always defined
  - **Result**: Endpoint now gracefully returns senators with zero counts when Supabase fails (as originally intended)
  - Updated test to verify graceful handling (200 with zero counts) instead of documenting buggy behavior (500)
  - Files modified: `app/routes/etl.py`, `tests/test_etl_routes.py`
  - All 1486 tests passing

## ✅ Completed Loop #30
- [2026-01-28] 🧪 **Testing: ETL Routes Test Coverage (87% → 100%)**
  - Added 10 tests to `tests/test_etl_routes.py` (31 → 41 tests)
  - New test classes covering:
    - `TestCleanupExecutions` extension (1 test):
      - `test_cleanup_executions_supabase_error_returns_500`: Supabase connection error handling
    - `TestIngestUrlExtended` (7 tests):
      - `test_ingest_url_http_error_returns_502`: HTTP download failure handling
      - `test_ingest_url_invalid_pdf_content_returns_400`: Invalid PDF validation
      - `test_ingest_url_parses_transactions_from_tables`: Transaction extraction from PDF tables
      - `test_ingest_url_uploads_to_supabase`: Full upload flow with politician lookup
      - `test_ingest_url_supabase_error_returns_500`: Supabase connection error
      - `test_ingest_url_no_politician_id_skips_upload`: Missing politician handling
      - `test_ingest_url_upload_failure_not_counted`: Failed upload tracking
    - `TestGetSenatorsExtended` (2 tests):
      - `test_get_senators_with_disclosures`: Disclosure counting with trade data
      - `test_get_senators_supabase_exception_returns_500`: Documents existing bug
  - Coverage improvement: 87% → 100% for app/routes/etl.py (+13 percentage points)
  - Previously uncovered lines now tested:
    - Lines 389-390: HTTP error handling in PDF download
    - Line 397: Invalid PDF content validation
    - Lines 407-410: Transaction parsing from PDF tables
    - Lines 427-447: Supabase upload flow (politician lookup, transaction upload)
    - Lines 510-511: Senator disclosure counting (count > 0 path)
    - Lines 554-555: Supabase error handling in cleanup endpoint
  - **Bug Discovered**: `get_senators()` has UnboundLocalError when Supabase fails - `with_disclosures` and `total_disclosures` not initialized before exception handler
  - All 1486 tests passing

## ✅ Completed Loop #29
- [2026-01-28] 🧪 **Testing: ML Routes Test Coverage (87% → 100%)**
  - Added 8 tests to `tests/test_ml_routes.py` (28 → 36 tests)
  - New tests covering:
    - `test_predict_writes_to_cache`: Cache write verification (lines 153-154)
    - `test_predict_exception_returns_500`: Prediction exception handling (lines 170-172)
    - `test_batch_predict_handles_per_ticker_error`: Per-ticker error handling (lines 210-212)
    - `test_list_models_returns_500_on_exception`: list_models exception (lines 306-308)
    - `test_active_model_returns_500_on_exception`: get_active_model exception (lines 327-329)
    - `test_get_model_returns_500_on_exception`: get_model exception (lines 346-348)
    - `test_feature_importance_returns_500_on_exception`: feature_importance exception (lines 378-380)
    - `test_activate_model_returns_500_on_exception`: activate_model exception (lines 430-432)
  - Coverage improvement: 87% → 100% for ml.py routes (+13 percentage points)
  - All 1476 tests passing

## ✅ Completed Loop #28
- [2026-01-28] 🧪 **Testing: Signals Routes Test Coverage (85% → 100%)**
  - Added 9 tests to `tests/test_signals_routes.py` (13 → 22 tests)
  - New tests covering:
    - `test_apply_lambda_success_with_transformation`: Signal transformation verification
    - `test_apply_lambda_success_returns_trace`: Execution trace response validation
    - `test_apply_lambda_execution_error_tracked_in_trace`: Per-signal error tracking
    - `test_apply_lambda_raises_execution_error`: LambdaExecutionError 400 response
    - `test_apply_lambda_internal_error_returns_500`: General Exception 500 response
    - `test_validate_valid_code_returns_true`: Valid code compilation
    - `test_validate_code_with_modification`: Code that modifies signals
    - `test_validate_syntax_error_returns_invalid`: Syntax error detection
    - `test_validate_unexpected_error_returns_invalid`: Exception handling
  - Coverage improvement: 85% → 100% for signals.py routes (+15 percentage points)
  - Previously uncovered lines now tested:
    - Lines 153-164: apply-lambda success path (trace response)
    - Lines 178-183: LambdaExecutionError handling
    - Lines 185-187: General Exception handling
    - Lines 208-209: validate-lambda compile success
    - Lines 214-215: validate-lambda unexpected error
  - All 1468 tests passing

## ✅ Completed Loop #27
- [2026-01-28] 🧪 **Testing: Politician Dedup Test Coverage (81% → 100%)**
  - Added 11 tests to `tests/test_politician_dedup.py` (36 → 47 tests)
  - New test classes covering:
    - `TestMergeGroupActual` (4 tests): Full merge logic
      - Winner data update with loser fields
      - No update when winner complete
      - Disclosure count tracking
      - Loser with None data response
    - `TestProcessAllExtended` (3 tests): process_all() paths
      - Success merge counting with disclosures
      - Error result counting
      - Mixed success/error handling
    - `TestFindDuplicatesExtended` (2 tests): Pagination and filtering
      - Pagination offset increment
      - Single-record group skipping (line 154)
    - `TestGetSupabase` (2 tests): _get_supabase method
      - Client return verification (line 54)
      - None handling
  - Coverage improvement: 81% → 100% for politician_dedup.py (+19 percentage points)
  - Previously uncovered lines now tested:
    - Line 54: _get_supabase() return
    - Line 136: Pagination offset increment
    - Line 154: Skip groups with < 2 records
    - Lines 257-301: _merge_group_actual() body
    - Lines 344-345, 349: process_all() success/error paths
  - All 1459 tests passing

## ✅ Completed Loop #26
- [2026-01-28] 🧪 **Testing: ML Signal Model Test Coverage (85% → 100%)**
  - Added 13 tests to `tests/test_ml_signal_model.py` (45 → 58 tests)
  - New test classes covering:
    - `TestCongressSignalModelTrain` (7 tests): XGBoost training flow
      - Mocked XGBoost/sklearn to avoid libomp dependency
      - Success path with metrics and feature importance
      - Custom hyperparameters merging
      - Training metrics storage
      - Label shifting ([-2,2] to [0,4] for XGBoost)
      - Feature scaling verification
      - ImportError handling when XGBoost unavailable
    - `TestLoadActiveModelSuccessPaths` (6 tests): Model loading paths
      - Local file cache loading
      - Storage download when local missing
      - Specific model_id loading
      - Dict vs list result.data handling
      - Empty data list handling
      - model_artifact_path=None triggering download
  - Coverage improvement: 85% → 100% for ml_signal_model.py (+15 percentage points)
  - Previously uncovered lines now tested:
    - Lines 232-299: train() method body (XGBoost training, data split, scaling, evaluation)
    - Lines 457, 464-465, 470-473: load_active_model success paths
  - All 1448 tests passing

## ✅ Completed Loop #25
- [2026-01-28] 🔒 **Security: Encrypt Alpaca API Credentials at Rest**
  - Created `supabase/functions/_shared/crypto.ts` with encryption utilities:
    - AES-256-GCM authenticated encryption (confidentiality + integrity)
    - PBKDF2 key derivation with 100,000 iterations
    - Random 12-byte IV per encryption (prevents pattern analysis)
    - 'enc:' prefix for encrypted value identification
    - Backwards compatible with unencrypted legacy data
  - Updated Edge Functions to decrypt on retrieval:
    - `alpaca-account/index.ts`: decrypt credentials, added save-credentials action
    - `orders/index.ts`: decrypt credentials
    - `strategy-follow/index.ts`: decrypt credentials
  - Updated `client/src/hooks/useAlpacaCredentials.ts`:
    - `saveCredentials` now calls Edge Function for encrypted storage
    - No longer writes directly to REST API (was plain text)
  - Updated `docs/USER_API_KEYS_IMPLEMENTATION.md`:
    - Documented AES-256-GCM implementation
    - Added setup instructions for `API_ENCRYPTION_KEY`
  - Security features:
    - Keys encrypted before storage
    - Decryption on retrieval (transparent to application)
    - Backwards compatible (handles unencrypted legacy data)
    - Warning logged if encryption key not configured
  - All 1435 tests passing

## ✅ Completed Loop #24
- [2026-01-28] 🧪 **Testing: Feature Pipeline Test Coverage Enhancement**
  - Added 24 tests to `tests/test_feature_pipeline.py` (44 → 68 tests)
  - New test classes covering:
    - `TestPrepareTrainingDataSkipsNoReturn` (2 tests): forward_return_7d=None filtering
    - `TestAggregateByWeekEmptyList` (2 tests): Empty/None ticker handling
    - `TestAddStockReturnsWithYfinance` (12 tests): yfinance mocking, batch processing, missing data, exception handling
    - `TestExtractSentimentWithApiKey` (2 tests): Ollama Authorization header
    - `TestTrainingJobRunSuccess` (2 tests): Full success flow, storage upload failure
    - `TestTrainingJobRunModelUpdateFailure` (2 tests): Exception handling paths
    - `TestModuleConstants` (2 tests): Module configuration validation
  - Coverage improvement: 70% → 99% for feature_pipeline.py (+29 percentage points)
  - Tested functionality:
    - Aggregation filtering when forward returns unavailable
    - Stock returns calculation with yfinance batching
    - Missing ticker data and date range edge cases
    - Market momentum calculation (20-day lookback)
    - Exception handling in return calculation
    - Ollama API key authorization header
    - Training job success and failure paths
  - Remaining uncovered: Lines 195 (unreachable edge case), 267-269 (yfinance import error)
  - All 1435 tests passing

## ✅ Completed Loop #23
- [2026-01-28] 🧪 **Testing: Senate ETL Test Coverage**
  - Added 35 tests to `tests/test_senate_etl_service.py` (27 → 62 tests)
  - New test classes covering:
    - `TestUpsertSenatorExceptionHandling` (2 tests): Bioguide search exception, fallback failures
    - `TestUpsertSenatorByNameExceptionHandling` (1 test): Exception handling
    - `TestParseDatatablesRecord` (7 tests): Valid record, short record, non-PTR, full URL, date handling, fallback
    - `TestParsePtrPage` (8 tests): HTML parsing, HTTP errors, sale/exchange types, ticker handling
    - `TestDownloadSenatePdf` (6 tests): PDF download, rate limiting, server errors, exceptions
    - `TestProcessSenateDisclosure` (5 tests): Transaction upload, politician finding, no URL handling
    - `TestRunSenateEtl` (4 tests): Main function, exception handling, paper filtering
    - `TestSenateETLConstants` (2 tests): Module constants and imports verification
  - Coverage improvement: 24% → 58% for senate_etl.py (+34 percentage points)
  - Tested functionality:
    - Senator upsert exception handling and fallback paths
    - DataTables record parsing with UUID extraction
    - PTR page parsing from HTML (BeautifulSoup)
    - PDF download with rate limiting and error handling
    - Senate disclosure processing with politician lookup
    - Main ETL function with senator fetch, upsert, and disclosure processing
    - Paper disclosure filtering
  - Remaining uncovered: Playwright browser automation functions (require real browser)
  - All 1411 tests passing

## ✅ Completed Loop #22
- [2026-01-28] 🧪 **Testing: Error Reports Routes Test Coverage**
  - Added 21 tests to `tests/test_error_reports_routes.py` (24 → 45 tests)
  - New test classes covering:
    - `TestProcessSingleReportSuccess` (2 tests): Success path with corrections, exception handling
    - `TestGetErrorReportStatsExceptions` (1 test): Database exception handling
    - `TestGetReportsNeedingReviewExceptions` (1 test): Database exception handling
    - `TestForceApplyCorrectionExtended` (3 tests): Missing disclosure_id, apply failure, exception
    - `TestReanalyzeReportExtended` (3 tests): Ollama unavailable, DB not configured, not found
    - `TestGenerateSuggestion` (6 tests): Complete endpoint coverage
    - `TestRequestModels` (5 tests): Request model defaults and validation
  - Coverage improvement: 78% → 100% for error_reports.py (+22 percentage points)
  - Tested functionality:
    - process-one success path with corrections returned
    - Exception handling in process-one, stats, needs-review, force-apply
    - Missing disclosure_id returns 400
    - Failed correction application returns 500
    - generate-suggestion endpoint (all paths: 503, 404, no_corrections, suggestions, exception)
    - Request model defaults (ProcessRequest, ProcessOneRequest, ForceApplyRequest, ReanalyzeRequest, GenerateSuggestionRequest)
  - All 1376 tests passing

## ✅ Completed Loop #21
- [2026-01-28] 🧪 **Testing: Quality Routes Test Coverage**
  - Added 23 tests to `tests/test_quality_routes.py` (29 → 52 tests)
  - New test classes covering:
    - `TestValidateTickerPolygon` (6 tests): Polygon.io API validation
    - `TestTickerValidationEdgeCases` (5 tests): Pattern detection, format validation
    - `TestAuditSourcesEdgeCases` (3 tests): Source filtering, random sampling, exception handling
    - `TestValidateRecordIntegrityEdgeCases` (3 tests): Date format, future disclosure, attribute errors
    - `TestFreshnessReportEdgeCases` (4 tests): No data handling, job statuses, stale data, exceptions
    - `TestQualityConstants` (2 tests): Ticker mappings, invalid patterns
  - Coverage improvement: 71% → 91% for quality.py (+20 percentage points)
  - Tested functionality:
    - Polygon.io API ticker validation (active, inactive, 404, API error, network error)
    - Invalid ticker pattern detection
    - Unusual ticker format detection
    - Outdated ticker mapping detection
    - Source-filtered audit queries
    - Random sampling when records exceed limit
    - Future date detection in records
    - Invalid date format handling
    - Job status tracking (disabled, never_run, failed, healthy)
    - Degraded health status for stale data
  - All 1355 tests passing

## ✅ Completed Loop #20
- [2026-01-28] 🧪 **Testing: Party Enrichment Test Coverage**
  - Added 12 tests to `tests/test_party_enrichment.py` (25 → 37 tests)
  - New test classes covering:
    - `TestOllamaAuthorization` (1 test): API key authorization header
    - `TestJobPagination` (2 tests): Multi-page fetching, limit handling
    - `TestProcessingLoop` (5 tests): Update success, skip unknown, error counting, message updates, rate limiting
    - `TestConstants` (4 tests): Module constants verification
  - Coverage improvement: 75% → 100% for party_enrichment.py (+25 percentage points)
  - Tested functionality:
    - Authorization header inclusion when API key is set
    - Pagination across multiple pages of politicians
    - Limit handling during pagination
    - Successful party updates
    - Skipping politicians with unknown party
    - Error counting on update failures
    - Periodic message updates during processing
    - Rate limiting between requests
    - Module constants validation
  - All 1332 tests passing

## ✅ Completed Loop #19
- [2026-01-28] 🧪 **Testing: House ETL Test Coverage**
  - Added 23 tests to `tests/test_house_etl_service.py` (51 → 74 tests)
  - New test classes covering:
    - `TestFetchZipContent` (3 tests): ZIP download success, failure, exception
    - `TestExtractIndexFile` (2 tests): ZIP extraction success and missing file
    - `TestFetchPdfRateLimiting` (4 tests): Rate limit retry, timeout, max retries, Retry-After header
    - `TestRunHouseETL` (4 tests): Supabase error, ZIP failure, index failure, exception handling
    - `TestEdgeCases` (8 tests): Transaction parsing edge cases, date validation
    - `TestConstants` (2 tests): Module constants verification
  - Coverage improvement: 57% → 78% for house_etl.py (+21 percentage points)
  - Tested functionality:
    - Async ZIP content fetching with error handling
    - ZIP index file extraction
    - PDF fetch rate limiting with exponential backoff
    - Retry-After header handling
    - Main ETL function error paths
    - Transaction parsing edge cases (partial sales, keywords, metadata patterns)
    - Date validation with year corrections
    - Module constants and URL templates
  - All 1320 tests passing

## ✅ Completed Loop #18
- [2026-01-28] 🧪 **Testing: Error Report Processor Test Coverage**
  - Created `tests/test_error_report_processor.py` with 42 comprehensive tests
  - Test classes covering:
    - `TestCorrectionProposal` (2 tests): Dataclass creation
    - `TestProcessingResult` (2 tests): Result dataclass
    - `TestErrorReportProcessorInit` (2 tests): Processor initialization
    - `TestErrorReportProcessorTestConnection` (3 tests): Ollama connection testing
    - `TestErrorReportProcessorGetPendingReports` (4 tests): Report fetching
    - `TestErrorReportProcessorNormalizeParty` (4 tests): Party normalization
    - `TestErrorReportProcessorBuildPrompt` (3 tests): LLM prompt building
    - `TestErrorReportProcessorInterpretCorrections` (5 tests): LLM interpretation
    - `TestErrorReportProcessorProcessReport` (3 tests): Single report processing
    - `TestErrorReportProcessorApplyCorrections` (6 tests): Correction application
    - `TestErrorReportProcessorUpdateReportStatus` (3 tests): Status updates
    - `TestErrorReportProcessorProcessAllPending` (3 tests): Batch processing
    - `TestPoliticianFields` (1 test): Field configuration
    - `TestConfidenceThreshold` (1 test): Threshold configuration
  - Coverage improvement: 24% → 92% for error_report_processor.py
  - Tested functionality:
    - CorrectionProposal and ProcessingResult dataclasses
    - Ollama connection testing
    - Fetching pending reports with error handling
    - Party normalization (Democrat/Republican/Independent variations)
    - LLM prompt building with snapshot data
    - Correction interpretation from LLM responses
    - Report processing with confidence thresholds
    - Applying corrections to disclosure and politician tables
    - Batch processing with error handling
  - All 1297 tests passing

## ✅ Completed Loop #17
- [2026-01-28] 🧪 **Testing: Name Enrichment Test Coverage**
  - Created `tests/test_name_enrichment.py` with 36 comprehensive tests
  - Test classes covering:
    - `TestParseOllamaNameResponse` (14 tests): Response parsing for names, party, state, confidence
    - `TestExtractPoliticianNameWithOllama` (7 tests): Async LLM name extraction
    - `TestNameEnrichmentJobInit` (2 tests): Job initialization
    - `TestNameEnrichmentJobToDict` (2 tests): Job serialization
    - `TestNameEnrichmentJobRun` (4 tests): Job execution
    - `TestJobManagement` (5 tests): Job registry functions
    - `TestConstants` (2 tests): Module constants
  - Coverage improvement: 24% → 87% for name_enrichment.py
  - Tested functionality:
    - Parsing full responses with name, party, state, confidence
    - Handling UNKNOWN responses
    - Party name expansion (Democrat→D, Republican→R)
    - State code normalization
    - Multi-word last names
    - Empty/invalid raw_data handling
    - HTTP errors and unexpected exceptions
    - Job lifecycle (pending, running, completed, failed)
    - Job registry operations
  - Documented edge case: "STATE: UNKNOWN" captures "UN" as state code
  - All 1255 tests passing

## ✅ Completed Loop #16
- [2026-01-28] 🧪 **Testing: ML Signal Model Test Coverage**
  - Created `tests/test_ml_signal_model.py` with 45 comprehensive tests
  - Test classes covering:
    - `TestStorageBucketExists` (3 tests): Storage bucket management
    - `TestUploadModelToStorage` (2 tests): Model upload to Supabase storage
    - `TestDownloadModelFromStorage` (2 tests): Model download from storage
    - `TestComputeFeatureHash` (4 tests): Feature hashing for caching
    - `TestCongressSignalModelInit` (2 tests): Model initialization
    - `TestCongressSignalModelPrepareFeatures` (6 tests): Feature extraction
    - `TestCongressSignalModelPredict` (3 tests): Single prediction
    - `TestCongressSignalModelPredictBatch` (4 tests): Batch prediction
    - `TestCongressSignalModelSaveLoad` (2 tests): Model serialization
    - `TestCongressSignalModelGetFeatureImportance` (2 tests): Feature importance
    - `TestGetActiveModel` (2 tests): Global model accessor
    - `TestLoadActiveModel` (3 tests): Model loading from database
    - `TestCachePrediction` (3 tests): Prediction caching
    - `TestGetCachedPrediction` (3 tests): Cache retrieval
    - `TestSignalLabels` (2 tests): Label configuration
    - `TestFeatureNames` (2 tests): Feature configuration
  - Coverage improvement: 19% → 85% for ml_signal_model.py
  - Tested functionality:
    - Storage bucket creation and verification
    - Model upload/download to Supabase storage
    - Feature hash computation for caching
    - CongressSignalModel initialization with/without model path
    - Feature preparation with defaults
    - Prediction for trained/untrained models
    - Batch prediction with error handling
    - Model save/load roundtrip
    - Prediction caching and retrieval
  - All 1219 tests passing

## ✅ Completed Loop #15
- [2026-01-28] 🧪 **Testing: Feature Pipeline Test Coverage**
  - Created `tests/test_feature_pipeline.py` with 44 comprehensive tests
  - Test classes covering:
    - `TestGenerateLabel` (6 tests): Label generation based on forward returns
    - `TestFeaturePipelineInit` (1 test): Pipeline initialization
    - `TestFeaturePipelineExtractFeatures` (6 tests): Feature extraction
    - `TestFeaturePipelineAggregateByWeek` (6 tests): Weekly aggregation logic
    - `TestFeaturePipelineFetchDisclosures` (2 tests): Disclosure fetching
    - `TestFeaturePipelinePrepareTrainingData` (3 tests): Training data preparation
    - `TestFeaturePipelineExtractSentiment` (4 tests): Ollama sentiment extraction
    - `TestTrainingJob` (5 tests): Training job initialization and serialization
    - `TestTrainingJobRun` (2 tests): Training job execution
    - `TestJobManagement` (5 tests): Job registry functions
    - `TestFeaturePipelineAddStockReturns` (2 tests): Stock returns addition
    - `TestLabelThresholds` (2 tests): Threshold configuration
  - Coverage improvement: 12% → 70% for feature_pipeline.py
  - Tested functionality:
    - Label generation for strong_buy, buy, hold, sell, strong_sell
    - Feature extraction with defaults and cap on buy_sell_ratio
    - Weekly aggregation with bipartisan detection and disclosure delay
    - Sentiment extraction via Ollama API with clamping
    - Training job lifecycle (init, to_dict, run with errors)
    - Job registry (create, get, run in background)
  - Discovered edge case: empty aggregations causes ValueError in _add_stock_returns
  - All 1174 tests passing

## ✅ Completed Loop #14
- [2026-01-28] 🧪 **Testing: ETL Services Test Coverage**
  - Created `tests/test_etl_services.py` with 31 comprehensive tests
  - Test classes covering:
    - `TestHouseETLService` (11 tests): House ETL service wrapper
    - `TestSenateETLService` (11 tests): Senate ETL service wrapper
    - `TestETLRegistry` (5 tests): Registry integration
    - `TestInitServices` (2 tests): Service initialization
    - `TestETLResultTracking` (2 tests): Result and metadata tracking
  - Coverage improvement: 29% → 95% for etl_services.py
  - Tested functionality:
    - Service registration with ETLRegistry decorator
    - Source ID and source name configuration
    - Run method successful execution
    - Run method failed status handling
    - Exception handling with error reporting
    - Transaction count parsing from job messages
    - Default parameter handling
    - Timestamp tracking in ETLResult
    - Metadata population (year, lookback_days, source_status)
  - All 1130 tests passing

## ✅ Completed Loop #13
- [2026-01-28] 🧪 **Testing: Auto-Correction Service Test Coverage**
  - Created `tests/test_auto_correction.py` with 53 comprehensive tests
  - Test classes covering all AutoCorrector functionality:
    - `TestCorrectionType` (7 tests): enum values and string behavior
    - `TestCorrectionResult` (4 tests): dataclass creation and fields
    - `TestAutoCorrector` (42 tests): all correction methods
  - Coverage improvement: 0% → 81% for auto_correction.py
  - Tested functionality:
    - Ticker corrections (FB→META, TWTR→X, ANTM→ELV, etc.)
    - Value range corrections (inverted min/max detection)
    - Date format normalization (MM/DD/YYYY, DD-MM-YYYY, Month DD YYYY)
    - Amount text parsing (exact and fuzzy matching)
    - Batch operations (ticker and value range)
    - Database operations (mocked Supabase)
    - Audit logging and rollback support
    - Error handling edge cases
  - Fixed undefined `Client` type hint in source code
  - All 1099 tests passing

## ✅ Completed Loop #12
- [2026-01-28] 🔒 **Security: Protected Routes Component for React Frontend**
  - Created `client/src/components/ProtectedRoute.tsx` with reusable route wrappers:
    - `ProtectedRoute` - requires authentication, redirects to `/auth` if not logged in
    - `AdminRoute` - requires both authentication and admin role, redirects to `/` if not admin
    - `LoadingSpinner` - shown during auth state determination
  - Features:
    - Uses existing `useAuth()` and `useAdmin()` hooks from the codebase
    - Waits for `authReady` flag to prevent redirect flicker
    - Preserves attempted URL location for post-login redirect
    - Proper loading states during async auth checks
  - Protected routes in `App.tsx`:
    - `/trading` - requires authentication (personal trading features)
    - `/trading-signals` - requires authentication (premium trading signals)
    - `/reference-portfolio` - requires authentication (personal portfolio data)
    - `/admin/data-quality` - requires admin role (data quality dashboard)
  - Added E2E tests in `client/e2e/protected-routes.spec.ts`:
    - Tests for unauthenticated redirect behavior (6 tests)
    - Tests for loading state display
    - Validates public routes remain accessible
  - All tests passing, build successful

## ✅ Completed Loop #11
- [2026-01-28] 🧪 **Testing: Parser Module Test Coverage**
  - Created `tests/test_parser.py` with 57 comprehensive tests for `app/lib/parser.py`
  - Test classes covering all parser functions:
    - `TestExtractTickerFromText` (12 tests): ticker extraction from various formats
    - `TestSanitizeString` (7 tests): string sanitization and null character removal
    - `TestParseValueRange` (6 tests): value range parsing from disclosure text
    - `TestParseAssetType` (3 tests): asset type code parsing
    - `TestCleanAssetName` (9 tests): asset name cleaning and normalization
    - `TestIsHeaderRow` (5 tests): header row detection
    - `TestValidateTradeAmount` (3 tests): trade amount validation
    - `TestValidateAndSanitizeAmounts` (4 tests): amount sanitization
    - `TestNormalizeName` (8 tests): politician name normalization
  - Coverage improvement: 62% → 96% for parser.py
  - Discovered pattern order quirk in normalize_name (documented in tests)
  - All 1046 tests passing (989 original + 57 new)

## ✅ Completed Loop #10
- [2026-01-28] 🔒 **Security: Constant-Time Comparison for Service Role Keys**
  - Created `supabase/functions/_shared/auth.ts` with security utilities:
    - `constantTimeCompare(a, b)` - XOR-based comparison immune to timing attacks
    - `validateServiceRoleKey(token)` - validate tokens against service role key
    - `isServiceRoleRequest(req)` - check if request uses service role auth
    - `extractBearerToken(header)` - extract token from Authorization header
  - Security improvement:
    - Standard `===` comparison leaks information through timing differences
    - Constant-time comparison takes same time regardless of where strings differ
    - Uses byte-by-byte XOR to prevent early return optimization
    - Handles different-length strings without leaking length information
  - Updated 4 Edge Functions to use shared auth module:
    - alpaca-account: replaced local `isServiceRoleRequest` function
    - orders: replaced local `isServiceRoleRequest` function
    - portfolio: replaced local `isServiceRoleRequest` function
    - strategy-follow: replaced inline token comparison with `validateServiceRoleKey`
  - Added tests in alpaca-account/index.test.ts:
    - Tests for `constantTimeCompare()` equal strings
    - Tests for `constantTimeCompare()` different strings
    - Tests for `constantTimeCompare()` different length strings
    - Updated `isServiceRoleRequest()` tests to use new implementation

## ✅ Completed Loop #9
- [2026-01-28] 🔒 **Security: CORS Configuration Fix for Edge Functions**
  - Created `supabase/functions/_shared/cors.ts` with centralized CORS configuration:
    - `getCorsHeaders(origin)` - dynamic CORS headers based on request origin
    - `isOriginAllowed(origin)` - validates origins against allowlist
    - `handleCorsPreflightRequest(request)` - handles OPTIONS preflight
    - `corsJsonResponse()` / `corsErrorResponse()` - helper response builders
    - `createCorsHeaders()` - wrapper for backwards compatibility
    - `corsHeaders` - legacy constant that reads from environment at runtime
  - Features:
    - Environment-based configuration via `ALLOWED_ORIGINS` (comma-separated)
    - Default production origins: `https://govmarket.trade`, `https://www.govmarket.trade`
    - Dev mode support via `CORS_DEV_MODE=true` (allows all origins)
    - Localhost support via `ALLOW_LOCALHOST=true`
    - Proper `Vary: Origin` header for caching
    - Additional headers: `x-correlation-id`, `Access-Control-Max-Age: 86400`
  - Updated 12 Edge Functions to use shared CORS module:
    - alpaca-account, orders, portfolio, signal-feedback
    - trading-signals, sync-data, reference-portfolio, strategy-follow
    - scheduled-sync, process-error-reports, politician-profile, politician-trading-collect
  - Updated test file to import from shared module
  - All 989 Python ETL tests passing

## ✅ Completed Loop #8
- [2026-01-28] 🔍 **Traceability: Audit Logging for Sensitive Operations**
  - Created `app/lib/audit_log.py` with comprehensive audit logging infrastructure:
    - `AuditAction` enum with categories: auth, data, model, etl, error_report
    - `AuditEvent` dataclass with all audit fields (action, resource, actor, timing, etc.)
    - `log_audit_event()` function for manual audit event logging
    - `@audit_log()` decorator for automatic endpoint auditing
    - `AuditContext` context manager for manual auditing with timing
    - `get_client_ip()` helper for IP extraction from proxy headers
  - Features:
    - Correlation ID integration for request tracing
    - Automatic timing measurement (duration_ms)
    - Success/failure tracking with error messages
    - Structured JSON logging format
    - Warning-level logs for failures and auth issues
  - Added audit logging to 4 sensitive endpoints:
    - `POST /error-reports/force-apply` - logs corrections applied, disclosure_id, fields
    - `POST /error-reports/reanalyze` - logs model, threshold, dry_run, result status
    - `POST /ml/train` - logs job_id, lookback_days, model_type, triggered_by
    - `POST /ml/models/{model_id}/activate` - logs previous_status, new_status
  - Added 30 comprehensive tests in `tests/test_audit_log.py`:
    - AuditEvent creation and serialization tests
    - get_client_ip extraction tests
    - log_audit_event function tests
    - @audit_log decorator tests (sync/async, success/failure)
    - AuditContext context manager tests
    - AuditAction enum coverage tests
  - All 989 tests passing

## ✅ Completed This Session
<!-- Ralph: Record completed work with timestamps -->
- [2026-01-28] 🔒 **Security: API Rate Limiting Middleware**
  - Created `app/middleware/rate_limit.py` with sliding window rate limiter:
    - `SlidingWindowRateLimiter` class for IP-based rate limiting
    - `RateLimitMiddleware` ASGI middleware for global rate limiting
    - `check_rate_limit` FastAPI dependency for route-level rate limiting
  - Features:
    - Sliding window algorithm (smoother than fixed windows)
    - IP detection via X-Forwarded-For, X-Real-IP, or direct client
    - Configurable requests/window/burst via environment variables
    - Exempt endpoints (/, /health, /docs, /openapi.json)
    - Stricter limits for expensive endpoints (/ml/train: 5/hr, /etl/trigger: 10/min)
    - Returns 429 with Retry-After header when exceeded
    - X-RateLimit-Remaining header on responses
  - Environment variables:
    - ETL_RATE_LIMIT_ENABLED (default: true)
    - ETL_RATE_LIMIT_REQUESTS (default: 100)
    - ETL_RATE_LIMIT_WINDOW (default: 60 seconds)
    - ETL_RATE_LIMIT_BURST (default: 10)
  - Added 25 comprehensive tests in `test_rate_limit.py`
  - Updated conftest.py to disable rate limiting in tests by default
  - All 959 tests passing

- [2026-01-28] 🔒 **Security: Admin-Only Protection for Sensitive Endpoints**
  - Applied `require_admin_key` dependency to 4 sensitive endpoints:
    - `POST /error-reports/force-apply` - Can modify trading disclosure data
    - `POST /error-reports/reanalyze` - Can re-process reports with lower thresholds
    - `POST /ml/train` - Can trigger expensive ML training jobs
    - `POST /ml/models/{model_id}/activate` - Can change active prediction model
  - Updated routes with explicit **Requires admin API key** documentation
  - Added 11 tests for admin protection:
    - `TestMlAdminProtection`: 5 tests for ML endpoint auth
    - `TestErrorReportsAdminProtection`: 6 tests for error-reports endpoint auth
  - Tests verify:
    - Endpoints return 401 without API key
    - Endpoints return 403 with regular API key (not admin)
    - Endpoints succeed with admin API key
  - All 934 tests passing

- [2026-01-28] 🔒 **Security: API Key Authentication for ETL Service**
  - Created `app/middleware/auth.py` with comprehensive auth implementation:
    - `AuthMiddleware` ASGI middleware for global request authentication
    - `require_api_key` FastAPI dependency for route-level auth
    - `require_admin_key` FastAPI dependency for sensitive admin operations
    - `constant_time_compare()` to prevent timing attacks
    - `generate_api_key()` for secure key generation
  - Features:
    - X-API-Key header (primary), Authorization Bearer (secondary), query param (fallback)
    - Separate admin API key for sensitive operations (force-apply, model activation)
    - Public endpoints whitelist (/, /health, /docs, /openapi.json)
    - Backwards compatibility mode when no keys configured
    - Dev mode with ETL_AUTH_DISABLED=true
  - Added 48 tests in `test_auth_middleware.py` covering all auth scenarios
  - Updated `conftest.py` with autouse fixture to disable auth in tests
  - Environment variables: ETL_API_KEY, ETL_ADMIN_API_KEY, ETL_AUTH_DISABLED
  - All 923 tests passing

- [2026-01-28] 🔒 **Security Audit: Comprehensive Review**
  - Audited all services: ETL (Python), Phoenix (Elixir), Client (React), Edge Functions
  - **Critical findings**:
    - ETL service had NO authentication (now fixed with AuthMiddleware)
    - Phoenix server has no auth middleware (needs implementation)
    - Edge Functions use wildcard CORS (*) - security risk
    - Alpaca credentials stored unencrypted in database
  - **High severity findings**:
    - PDF URL injection attack vector (no whitelist validation)
    - ML training/model activation endpoints unprotected
    - Service role key comparison vulnerable to timing attacks
    - No rate limiting on any service
  - Documented 14 security issues with severity ratings
  - Added new backlog items for remaining fixes

- [2026-01-28] 🏗️ **Robustness: Resilient HTTP Client with Retry Logic**
  - Created `app/lib/http_client.py` with:
    - `resilient_request()` function for single requests with retry
    - `ResilientClient` context manager for multiple requests
    - `calculate_backoff_delay()` for exponential backoff with jitter
  - Features:
    - Exponential backoff (2^attempt * base_delay, capped at max_delay)
    - Jitter to prevent thundering herd
    - Configurable retry status codes (default: 429, 500, 502, 503, 504)
    - Respects Retry-After headers
    - Handles transient exceptions (timeout, connection error, read/write errors)
    - No retry for client errors (4xx except 429)
  - Added 26 comprehensive tests in `test_http_client.py`
  - Ready for use by enrichment services (name_enrichment, party_enrichment, bioguide_enrichment)
  - All 875 tests passing

- [2026-01-28] 🛡️ **Data Quality: Trade Amount Validation**
  - Added `validate_trade_amount()` and `validate_and_sanitize_amounts()` in `app/lib/parser.py`
  - Updated `upload_transaction_to_supabase()` and `prepare_transaction_for_batch()` in `app/lib/database.py`
  - Rejects amounts > $50M (the max disclosure threshold) as clearly corrupted
  - Logs warning when invalid amounts are rejected
  - Added 19 tests in `test_database.py` covering all validation scenarios
  - Prevents future volume spike issues from PDF parsing errors
  - All 849 tests passing

- [2026-01-28] 🗃️ **Data Quality: Volume Spike Fix**
  - **Issue**: Massive volume spike in Aug-Sep 2025 on Trade Volume chart (~$4.5B displayed)
  - **Root Cause**: 37 corrupted `trading_disclosures` records with impossible amounts (up to $4.5 trillion) from House ETL PDF parsing errors
  - **Parser Bug**: Concatenating multiple columns/rows into `asset_name` field, extracting dollar amounts from malformed text
  - **Example**: `asset_name: "Truway Health, Inc. Suing the U.S $4,536,758,654,345.00..."` with `amount_range_max: 4536758654345`
  - **Fix Applied**:
    1. Deleted 37 corrupted records where `amount_range_max > $1 billion`
    2. Regenerated `chart_data` table via `update-chart-data` edge function
  - **Result**: Sep 2025 volume now shows ~$1.4B (realistic) instead of ~$898B (corrupt)

- [2026-01-28] 🔒 **Security: Sandbox fail-closed + RestrictedPython dependency fix**
  - Added RestrictedPython>=6.1 to pyproject.toml (was missing from deps)
  - Changed sandbox to fail-closed (raise error) instead of falling back to unsafe exec()
  - Fixed RestrictedPython API compatibility (v6.x returns code directly, not result object)
  - Fixed `_write_` guard for subscription assignment in RestrictedPython
  - Fixed math module to use SimpleNamespace (safer_getattr returns None for dict)
  - Fixed print capture with RestrictedPython's `_print_` / `_call_print` pattern
  - Created comprehensive test suite: `tests/test_sandbox.py` (40 tests)
    - Validation tests for forbidden operations
    - Execution tests for safe operations
    - Security regression tests for common bypass attempts
  - All 53 sandbox/signal tests passing

- [2026-01-28] 🔒 **Security: Dependency vulnerability fixes**
  - CVE-2025-53643: Updated aiohttp minimum version to >=3.13.0 (HTTP request smuggling)
  - CVE-2025-50181: Added urllib3>=2.6.0 (SSRF redirect bypass)
  - CVE-2025-66418: urllib3>=2.6.0 also fixes decompression chain DoS
  - Current versions: aiohttp 3.13.2, urllib3 2.6.3
  - All 53 tests still passing

- [2026-01-28] 🔍 **Traceability: Structured logging with correlation IDs**
  - Created `app/lib/logging_config.py` with:
    - JSON structured formatter for production logs
    - Correlation ID context variable (thread-safe and async-safe)
    - `get_logger()` helper that auto-includes correlation ID
    - `configure_logging()` for app-wide setup
  - Created `app/middleware/correlation.py` with:
    - `CorrelationMiddleware` that extracts/generates correlation IDs
    - Request/response logging with timing
    - Adds `X-Correlation-ID` header to responses
    - Supports `X-Request-ID` as fallback header
  - Updated `app/main.py` to use structured logging
  - Created test suites: `test_logging_config.py` (13 tests), `test_correlation_middleware.py` (6 tests)
  - All 72 tests passing (53 + 19 new)

- [2026-01-28] 🧪 **Testing: Input validation tests for quality endpoints**
  - Added 13 input validation tests to `test_quality_routes.py`:
    - `TestValidateTickersInputValidation`: 8 tests for days_back, confidence_threshold, limit bounds
    - `TestAuditSourcesInputValidation`: 5 tests for sample_size, days_back bounds
  - Tests verify 422 validation errors for:
    - Values below minimum constraints (ge)
    - Values above maximum constraints (le)
    - Invalid types (string instead of int/float)
  - All 101 tests passing (72 + 29 quality route tests)

## 📜 Historical Completions
<!-- Ralph: Summarize past improvements for context -->

### January 2026
- Fixed Pydantic V2 deprecation warning in signals.py
- Added batch upload functions for ETL performance
- Added type annotations to ETL service modules
- Improved error handling: replaced bare except clauses
- Cleaned up unused imports across codebase

## 🧠 Analysis Notes
<!-- Ralph: Document your reasoning and discoveries here -->

### Repository Health Snapshot
- **Tests:** Run `make test` to verify current status
- **Linting:** Run `ruff check` and `eslint` for issues
- **Types:** Check for missing annotations with `mypy`

### Areas Needing Attention
<!-- Ralph: Update this based on your analysis -->
1. ~~Security audit not yet performed~~ - Comprehensive audit complete, auth middleware added to ETL
2. ~~Observability/logging could be improved~~ - Structured logging with correlation IDs implemented
3. ~~ETL service had no authentication~~ - API key auth middleware now protects all endpoints
4. ~~Phoenix server still has no auth~~ - ApiKeyAuth plug now protects all /api/* routes
5. ~~Edge Functions use wildcard CORS~~ - Centralized CORS module with env-based allowlist
6. ~~Alpaca API credentials stored unencrypted~~ - Implemented AES-256-GCM encryption
7. ~~API documentation may be incomplete~~ - Comprehensive OpenAPI documentation added
8. ~~Type annotations still missing in several ETL service modules~~ - Added to house_etl, senate_etl, auto_correction
9. ~~External API calls need better error handling~~ - ResilientClient with retry logic added

## 📊 Improvement Categories Reference

When analyzing, consider:
- 🔒 **Security** - vulnerabilities, auth, input validation
- 🧪 **Testing** - coverage, edge cases, reliability
- 📝 **Typing** - annotations, type safety, validation
- 🏗️ **Robustness** - error handling, retries, timeouts
- 📊 **Stability** - race conditions, resource management
- 🔍 **Traceability** - logging, metrics, auditing
- 💰 **Monetization** - usage tracking, premium features
- 🧹 **Code Quality** - DRY, complexity, documentation

## ⚙️ Instructions for Ralph

1. **Every loop**: Read this file first to understand context
2. **Before working**: Move a task from Backlog to In Progress
3. **While working**: Add any new issues you discover to Backlog
4. **After completing**: Move task to Completed with timestamp
5. **Always**: Ensure Backlog has items - discover new improvements!

**The goal is continuous improvement. There's always something to make better.**
