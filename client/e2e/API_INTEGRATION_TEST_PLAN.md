# Playwright API Integration Test Plan

This document outlines the comprehensive plan for E2E tests that verify UI components correctly integrate with external APIs.

## Overview

Based on codebase analysis, the application has **8 major API integration categories** that need E2E test coverage:

| Priority | Category | Files to Create | Est. Tests |
|----------|----------|-----------------|------------|
| P0 | Alpaca Trading | `alpaca-integration.spec.ts` | 25 |
| P0 | Trading Signals | `trading-signals-integration.spec.ts` | 15 |
| P1 | Orders Management | `orders-integration.spec.ts` | 20 |
| P1 | Reference Portfolio | `reference-portfolio-integration.spec.ts` | 15 |
| P1 | Strategy Follow | `strategy-follow-integration.spec.ts` | 12 |
| P2 | Dashboard Data | `dashboard-data-integration.spec.ts` | 18 |
| P2 | Drops/Social | `drops-integration.spec.ts` | 10 |
| P2 | User Settings | `user-settings-integration.spec.ts` | 8 |

**Total: ~123 new E2E tests**

---

## P0: Critical Trading Integration Tests

### 1. Alpaca Account Integration (`alpaca-integration.spec.ts`)

**Edge Function**: `alpaca-account`

**Test Scenarios**:

```typescript
test.describe('Alpaca Account Integration', () => {
  // Connection Status Tests
  test('should display account balance when connected');
  test('should show buying power and equity');
  test('should display paper/live trading mode indicator');
  test('should handle connection failure gracefully');
  test('should show circuit breaker warning when degraded');

  // Position Display Tests
  test('should display current positions with P/L');
  test('should show position market values');
  test('should update positions on refresh');
  test('should handle empty positions gracefully');

  // Credential Management Tests
  test('should validate API credentials on test connection');
  test('should show error for invalid credentials');
  test('should save credentials successfully');
  test('should toggle between paper/live mode');

  // Error States
  test('should show trading blocked message when account restricted');
  test('should handle network timeout with retry');
  test('should display offline state appropriately');
});
```

**Mock Responses Required**:
- `alpaca-account?action=get-account` → Account data
- `alpaca-account?action=get-positions` → Positions array
- `alpaca-account?action=test-connection` → Connection result
- `alpaca-account?action=connection-status` → Health check

---

### 2. Trading Signals Integration (`trading-signals-integration.spec.ts`)

**Edge Function**: `trading-signals/preview-signals`

**Test Scenarios**:

```typescript
test.describe('Trading Signals Integration', () => {
  // Signal Generation Tests
  test('should generate signals with default weights');
  test('should update signals when weights change');
  test('should show ML-enhanced signals badge');
  test('should handle custom lambda functions');

  // Signal Display Tests
  test('should display signal strength indicators');
  test('should show buy/sell/hold recommendations');
  test('should display confidence scores');

  // Preset Management Tests
  test('should load system presets');
  test('should save custom preset');
  test('should apply preset weights');
  test('should delete user preset');

  // Error Handling
  test('should handle API timeout gracefully');
  test('should show lambda syntax errors');
  test('should fall back when ML unavailable');
});
```

**Mock Responses Required**:
- `trading-signals/preview-signals` → Signal array with stats
- `signal_weight_presets` table queries

---

## P1: Order & Portfolio Integration Tests

### 3. Orders Management (`orders-integration.spec.ts`)

**Edge Function**: `orders`

**Test Scenarios**:

```typescript
test.describe('Orders Integration', () => {
  // Order Placement Tests
  test('should place market buy order successfully');
  test('should place limit sell order');
  test('should validate order parameters');
  test('should show order confirmation');
  test('should reject invalid quantity');

  // Order History Tests
  test('should display order history with pagination');
  test('should filter by order status (open/closed/all)');
  test('should show order fill details');
  test('should sync orders from Alpaca');

  // Order Cancellation Tests
  test('should cancel open order');
  test('should show cancellation confirmation');
  test('should handle cancel failure');

  // Quick Trade Dialog Tests
  test('should open quick trade from signal');
  test('should pre-fill ticker from signal');
  test('should calculate estimated cost');
});
```

**Mock Responses Required**:
- `orders?action=get-orders` → Order history
- `orders?action=place-order` → Order result
- `orders?action=sync-orders` → Sync summary
- Direct Alpaca DELETE for cancellation

---

### 4. Reference Portfolio (`reference-portfolio-integration.spec.ts`)

**Edge Function**: `reference-portfolio` + Database tables

**Test Scenarios**:

```typescript
test.describe('Reference Portfolio Integration', () => {
  // Performance Display Tests
  test('should display portfolio value');
  test('should show returns percentage');
  test('should display risk metrics (Sharpe, drawdown)');
  test('should render performance chart');

  // Position Tracking Tests
  test('should list open positions');
  test('should show position P/L');
  test('should display closed positions history');

  // Transaction History Tests
  test('should display transaction log');
  test('should paginate transactions');
  test('should filter by transaction type');

  // Timeframe Selection Tests
  test('should switch performance timeframe');
  test('should update chart on timeframe change');
});
```

**Mock Responses Required**:
- `reference-portfolio?action=get-performance` → Snapshots
- `reference_portfolio_state` table
- `reference_portfolio_positions` table
- `reference_portfolio_transactions` table

---

### 5. Strategy Follow (`strategy-follow-integration.spec.ts`)

**Edge Function**: `strategy-follow`

**Test Scenarios**:

```typescript
test.describe('Strategy Follow Integration', () => {
  // Subscription Tests
  test('should display subscription status');
  test('should subscribe to reference strategy');
  test('should subscribe to custom strategy');
  test('should unsubscribe from strategy');

  // Trade Sync Tests
  test('should display strategy trades');
  test('should trigger manual sync');
  test('should show sync results');

  // Configuration Tests
  test('should set trading mode (paper/live)');
  test('should toggle sync existing positions');

  // Error States
  test('should handle subscribe failure');
  test('should show sync errors');
});
```

---

## P2: Dashboard & Social Integration Tests

### 6. Dashboard Data (`dashboard-data-integration.spec.ts`)

**Database Tables**: Multiple via `useSupabaseData.ts`

**Test Scenarios**:

```typescript
test.describe('Dashboard Data Integration', () => {
  // Stats Display Tests
  test('should display total trades count');
  test('should show total trading volume');
  test('should display active politicians count');
  test('should show average trade size');

  // Politicians List Tests
  test('should load politicians by jurisdiction');
  test('should filter by party');
  test('should sort by volume/trades');
  test('should open politician profile modal');

  // Trades List Tests
  test('should display recent trades');
  test('should filter by ticker');
  test('should filter by date range');
  test('should paginate results');

  // Chart Tests
  test('should render trade volume chart');
  test('should switch timeframe');
  test('should show chart tooltips');

  // Ticker Search Tests
  test('should search tickers with autocomplete');
  test('should navigate to ticker detail');
});
```

**Mock Responses Required**:
- `dashboard_stats` singleton
- `politicians` with filters
- `trading_disclosures` with joins
- `chart_data` time series
- `top_tickers` aggregations

---

### 7. Drops/Social Feed (`drops-integration.spec.ts`)

**Tables**: `drops`, `drop_likes` + Realtime

**Test Scenarios**:

```typescript
test.describe('Drops Social Integration', () => {
  // Feed Display Tests
  test('should load live drops feed');
  test('should load saved drops');
  test('should paginate feed');

  // Drop Creation Tests
  test('should create new drop');
  test('should validate drop content');
  test('should delete own drop');

  // Like Interaction Tests
  test('should like a drop');
  test('should unlike a drop');
  test('should show like count');

  // Realtime Tests
  test('should receive new drops in realtime');
  test('should update on drop deletion');
});
```

---

### 8. User Settings (`user-settings-integration.spec.ts`)

**Tables**: `user_api_keys`, `user_carts`

**Test Scenarios**:

```typescript
test.describe('User Settings Integration', () => {
  // API Keys Tests
  test('should display saved credentials (masked)');
  test('should save paper trading keys');
  test('should save live trading keys');
  test('should clear credentials');

  // Cart Persistence Tests
  test('should save cart to database');
  test('should load cart on login');
  test('should clear cart on checkout');

  // Admin Checks
  test('should verify admin role');
  test('should hide admin features for non-admin');
});
```

---

## Test Infrastructure Requirements

### 1. Shared Mock Utilities

Create `e2e/utils/api-mocks.ts`:

```typescript
// Reusable mock factories
export const mockAlpacaAccount = (overrides?: Partial<AlpacaAccount>) => ({...});
export const mockPosition = (ticker: string, overrides?: Partial<Position>) => ({...});
export const mockOrder = (overrides?: Partial<Order>) => ({...});
export const mockSignal = (ticker: string, overrides?: Partial<Signal>) => ({...});
export const mockPolitician = (overrides?: Partial<Politician>) => ({...});
export const mockTrade = (overrides?: Partial<Trade>) => ({...});

// Route setup helpers
export async function setupAlpacaMocks(page: Page, options: MockOptions) {...}
export async function setupDashboardMocks(page: Page) {...}
export async function setupAuthenticatedUser(page: Page, user: MockUser) {...}
```

### 2. Test Data Fixtures

Create `e2e/fixtures/`:
- `alpaca-account.json` - Sample account data
- `positions.json` - Sample positions
- `orders.json` - Sample order history
- `signals.json` - Sample trading signals
- `politicians.json` - Sample politician data
- `trades.json` - Sample trade disclosures

### 3. Authentication Helpers

Create `e2e/utils/auth.ts`:

```typescript
export async function loginAsTestUser(page: Page) {...}
export async function loginAsAdmin(page: Page) {...}
export async function mockAuthSession(page: Page, user: MockUser) {...}
```

---

## Implementation Order

### Phase 1: Foundation (Week 1)
1. Create `e2e/utils/api-mocks.ts`
2. Create test data fixtures
3. Create `e2e/utils/auth.ts`
4. Implement `alpaca-integration.spec.ts` (P0)

### Phase 2: Trading Core (Week 2)
5. Implement `trading-signals-integration.spec.ts` (P0)
6. Implement `orders-integration.spec.ts` (P1)

### Phase 3: Portfolio & Strategy (Week 3)
7. Implement `reference-portfolio-integration.spec.ts` (P1)
8. Implement `strategy-follow-integration.spec.ts` (P1)

### Phase 4: Dashboard & Social (Week 4)
9. Implement `dashboard-data-integration.spec.ts` (P2)
10. Implement `drops-integration.spec.ts` (P2)
11. Implement `user-settings-integration.spec.ts` (P2)

---

## CI/CD Integration

Add to `.github/workflows/e2e.yml`:

```yaml
name: E2E API Integration Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: cd client && npm ci

      - name: Install Playwright browsers
        run: cd client && npx playwright install --with-deps chromium

      - name: Run E2E tests
        run: cd client && npm run test:e2e
        env:
          PLAYWRIGHT_BASE_URL: http://localhost:5173

      - name: Upload test report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: client/playwright-report/
```

---

## Existing Test Coverage Mapping

| Existing Test File | Coverage | Gaps |
|--------------------|----------|------|
| `admin.spec.ts` | Admin UI | Missing API mocks |
| `alpaca-trading.spec.ts` | Basic UI | Missing order placement |
| `dashboard.spec.ts` | Stats display | Missing chart interactions |
| `politicians-view.spec.ts` | List view | Missing modal tests |
| `portfolio.spec.ts` | Display | Missing performance API |
| `trading-signals.spec.ts` | UI | Missing preview API |
| **NEW: `politician-profile-modal.spec.ts`** | Ollama AI | Complete |

---

## Success Metrics

- [ ] 100% of Edge Functions have mock coverage
- [ ] All error states have dedicated tests
- [ ] Loading states verified for all async operations
- [ ] Authentication flows tested (logged in/out)
- [ ] Pagination tested for all list views
- [ ] Realtime subscriptions verified (drops)
- [ ] All tests pass in CI within 5 minutes
