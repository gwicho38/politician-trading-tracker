# FIXME - Test Suite Issues

Last tested: 2026-01-21

## Test Results Summary

| Suite              | Passed | Failed | Status         |
|--------------------|--------|--------|----------------|
| React (Vitest)     | 106    | 0      | ✅             |
| Python ETL         | 729    | 20     | ⚠️             |
| Elixir             | 28     | 0      | ✅ (36 excluded) |
| Edge Functions     | 387    | 3      | ⚠️             |
| Playwright E2E     | ~500   | ~50    | ⚠️ Some failures |
| tests/supabase     | 104    | 0      | ✅             |

**Total working tests: ~1,854 passing**

> **Note:** Python Server tests were removed (legacy tests for deprecated `politician_trading` module).
> Python tests now only run via `make test-python-etl` for the ETL service.

---

## React Client Tests (Vitest)

**Status: ✅ All passing**

```bash
make test-react
```

All 106 tests pass.

---

## Python ETL Tests

**Status: ⚠️ 729 passed, 20 failed**

```bash
cd python-etl-service && ./venv/bin/python -m pytest tests/ -v
```

### Failed Tests

#### `test_house_etl_metrics.py` (13 failures)

| Test | Error |
|------|-------|
| `test_empty_asset_name` | `assert None is not None` |
| `test_parse_stock_type` | `AttributeError: 'tuple' object has no attribute 'lower'` |
| `test_parse_amount_min_1001` | `assert 'value_low' == 1001` |
| `test_parse_amount_min_15001` | `assert 'value_low' == 15001` |
| `test_parse_amount_min_50001` | `assert 'value_low' == 50001` |
| `test_parse_amount_min_over_1m` | `assert 'value_low' == 1000001` |
| `test_parse_amount_max_15000` | `assert 'value_high' == 15000` |
| `test_parse_amount_max_50000` | `assert 'value_high' == 50000` |
| `test_parse_amount_max_100000` | `assert 'value_high' == 100000` |
| `test_amount_range_midpoint` | `TypeError: unsupported operand type(s) for /: 'str' and 'int'` |
| `test_detect_header_row` | `AttributeError: 'list' object has no attribute 'lower'` |
| `test_detect_data_row` | `AttributeError: 'list' object has no attribute 'lower'` |
| `test_parse_row_amount_range` | `assert 'value_low' == 1001` |

#### `test_quiverquant_metrics.py` (5 failures)

| Test | Error |
|------|-------|
| `test_parse_range_min` | `assert 'value_low' == 15001` |
| `test_parse_large_range_min` | `assert 'value_low' == 1000001` |
| `test_parse_range_max` | `assert 'value_high' == 50000` |
| `test_parse_large_range_max` | `assert 'value_high' == 5000000` |
| `test_amounts_can_be_parsed` | `assert 'value_high' >= 'value_low'` |

#### `test_senate_etl_metrics.py` (2 failures)

| Test | Error |
|------|-------|
| `test_amount_min_senate_format` | `assert 'value_low' == 50001` |
| `test_amount_max_senate_format` | `assert 'value_high' == 100000` |

### Root Cause

The `parse_value_range()` function in `app/lib/parser.py` returns dictionary keys (`'value_low'`, `'value_high'`) instead of the actual numeric values. The tests expect:

```python
result = parse_value_range("$1,001 - $15,000")
assert result['value_low'] == 1001  # Returns the key name, not the value
```

### Fix Required

Review `app/lib/parser.py` and ensure `parse_value_range()` returns proper numeric values in the dictionary, not the key names.

---

## Elixir Tests

**Status: ✅ Passing (28 tests, 36 excluded)**

```bash
make test-elixir
```

### What's Tested

- Health controller endpoints
- ML controller endpoints
- Job controller endpoints
- Supabase client functionality
- Scheduler delegation

### Excluded Tests

36 tests are excluded because they require a database connection:
- Tests tagged with `@moduletag :database`
- These test scheduler jobs, database aggregations, etc.

To run database tests, you would need:
1. PostgreSQL database running on `localhost:5432`
2. Database `server_test` created
3. Migrations applied: `cd server && mix ecto.migrate`

---

## Edge Function Tests (Deno)

**Status: ⚠️ 363 passed, 3 failed**

```bash
make test-edge
```

### Failed Tests

#### 1. `orders/index.test.ts:201` - validateOrderParams() - zero quantity

**Expected:**
```
"Quantity must be greater than 0"
```

**Actual:**
```
"Missing required fields: ticker, side, quantity"
```

**Issue:** The test expects the validation to catch zero quantity specifically, but the validation function fails earlier because zero is falsy and treated as missing.

**Fix:** Update `validateOrderParams()` to check for quantity > 0 separately:

```typescript
function validateOrderParams(params) {
  if (!params.ticker || params.quantity === undefined || !params.side) {
    return { valid: false, error: 'Missing required fields: ticker, side, quantity' };
  }
  if (params.quantity <= 0) {
    return { valid: false, error: 'Quantity must be greater than 0' };
  }
  return { valid: true };
}
```

#### 2. `process-error-reports/index.test.ts:143` - determineEndpoint() - handles trailing slash

**Expected:** `""` (empty string)
**Actual:** `"default"`

**Issue:** The function returns `"default"` for paths with trailing slashes instead of an empty string.

**Fix:** Update the test expectation or the function behavior based on desired behavior.

#### 3. `signal-feedback/index.test.ts:248` - calculateRecommendedWeight() - negative correlation

**Expected:** `0.05`
**Actual:** `0.05000000000000002`

**Issue:** Floating point precision error.

**Fix:** Use `assertAlmostEquals()` instead of `assertEquals()`:

```typescript
// Before
assertEquals(calculateRecommendedWeight(-0.5), 0.05);

// After
assertAlmostEquals(calculateRecommendedWeight(-0.5), 0.05, 0.0001);
```

---

## Playwright E2E Tests

**Status: ⚠️ Running with some failures**

```bash
cd client && npm run test:e2e
```

### Setup Required

Before running tests, install Playwright browsers:

```bash
cd client && npx playwright install
```

### Test Files

23+ E2E test files in `client/e2e/`:
- `admin.spec.ts`, `auth.spec.ts`, `dashboard.spec.ts`
- `alpaca-trading.spec.ts`, `orders.spec.ts`, `portfolio.spec.ts`
- `trading-signals.spec.ts`, `filings-view.spec.ts`, etc.

### Current Status

- Server auto-starts via `playwright.config.ts` webServer config
- ~500 tests passing, ~50 failing
- Failing tests are likely due to missing test data or API mocking issues

### Running Tests

```bash
# Run all E2E tests
cd client && npm run test:e2e

# Run specific test file
npm run test:e2e -- e2e/index.spec.ts

# Run with UI for debugging
npm run test:e2e:ui
```

---

## tests/supabase TypeScript Tests

**Status: ✅ All passing**

```bash
deno test tests/supabase/*.test.ts
```

### Test Files

4 test files in `tests/supabase/`:
- `alpaca-account.test.ts` (circuit breaker tests)
- `orders.test.ts` (order validation tests)
- `sync-data.test.ts` (data sync tests)
- `trading-signals.test.ts` (signal generation tests)

All 104 tests passing.

---

## How to Run All Tests

```bash
# Run all tests
make test

# Run individual test suites
make test-react        # React/Vitest
make test-python-etl   # Python ETL service
make test-elixir       # Elixir (requires DB)
make test-edge         # Deno Edge Functions

# Playwright E2E (install browsers first)
cd client && npx playwright install
cd client && npm run test:e2e

# tests/supabase
deno test tests/supabase/*.test.ts

# Get test summary
make test-summary
```

---

## Priority Fixes

1. **High:** Fix `parse_value_range()` in Python ETL (affects 20 tests)
2. **Medium:** Fix 3 Edge Function test assertions
3. **Medium:** Fix ~50 failing Playwright E2E tests (likely API mocking issues)
4. **Low:** Set up local PostgreSQL for Elixir database tests (36 excluded)
