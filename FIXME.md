# FIXME - Test Suite Issues

Last tested: 2026-01-21

## Test Results Summary

| Suite          | Passed | Failed | Status         |
|----------------|--------|--------|----------------|
| React (Vitest) | 106    | 0      | ✅             |
| Python ETL     | 729    | 20     | ⚠️             |
| Python Server  | -      | -      | ❌ Setup issue |
| Elixir         | -      | -      | ❌ DB required |
| Edge Functions | 363    | 3      | ⚠️             |

**Total working tests: 1,198 passing**

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

## Python Server Tests

**Status: ❌ Cannot run - module import errors**

```bash
make test-python-server
```

### Issue

The `tests/` directory at the project root contains tests that import from `politician_trading` module:

```python
from politician_trading.trading.alpaca_client import AlpacaTradingClient
from politician_trading.config import WorkflowConfig
```

However, this module is located in a deprecated location:
```
resources/deprecated/python-micro-service/politician_trading/
```

The `pyproject.toml` has:
```toml
[tool.setuptools]
packages = { find = { where = ["server"] } }
```

But `server/` is the Elixir Phoenix server, not a Python package.

### Fix Required

1. Either move/restore the `politician_trading` Python package to a proper location
2. Or update the tests to use the correct import paths
3. Or remove these legacy tests if they're no longer needed

---

## Elixir Tests

**Status: ❌ Cannot run - database required**

```bash
make test-elixir
```

### Issue

The Elixir tests require a PostgreSQL database connection with the proper schema. When running tests, the application tries to start and query the `scheduled_jobs` table:

```
** (Postgrex.Error) ERROR 42P01 (undefined_table) relation "scheduled_jobs" does not exist
```

### Prerequisites

1. PostgreSQL database running on `localhost:5432`
2. Database created with proper migrations applied
3. Environment variables configured in `server/.env`

### Fix Required

Either:
1. Set up a local test database with migrations
2. Or configure tests to use the production Supabase database (not recommended)
3. Or mock the database layer for unit tests

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

## How to Run All Tests

```bash
# Run all tests
make test

# Run individual test suites
make test-react        # React/Vitest
make test-python-etl   # Python ETL service
make test-python-server # Python server (currently broken)
make test-elixir       # Elixir (requires DB)
make test-edge         # Deno Edge Functions

# Get test summary
make test-summary
```

---

## Priority Fixes

1. **High:** Fix `parse_value_range()` in Python ETL (affects 20 tests)
2. **Medium:** Fix 3 Edge Function test assertions
3. **Low:** Resolve Python server module structure or remove legacy tests
4. **Low:** Set up Elixir test database or add mocking
