# Advanced End-to-End Tests Documentation

## Overview

This document describes the advanced E2E test scenarios that extend beyond the basic trading flow. These tests validate edge cases, performance, and advanced features like limit orders and multiple signals.

---

## Test File

**File:** `test_e2e_advanced_scenarios.py`

---

## Test Scenarios

### 1. **Limit Orders Test** (`TestE2ELimitOrders`)

#### Test Method: `test_limit_order_with_price_targets`

**Scenario:**
Tests the complete workflow for placing a limit order with specific price targets.

**Flow:**
1. Nancy Pelosi sells Microsoft (MSFT) stock
2. System generates SELL signal with target price $380
3. User adds to cart with limit order parameters
4. System executes limit order at target price
5. Order stored with correct limit price

**Key Validations:**
- ✅ Limit order has correct price ($380)
- ✅ Order type is "limit" (not "market")
- ✅ Limit price stored in database
- ✅ Order can be tracked with price target

**Example Output:**
```
=== E2E Test: Limit Order with Price Targets ===

✅ Created MSFT SELL signal with target price: $380.00
✅ Added MSFT to cart with quantity: 20 shares
✅ Placed LIMIT order: SELL 20 shares of MSFT @ $380.00
   Order ID: ...
   Status: pending_new
✅ Limit order stored in database with limit_price=$380.00

✅ Limit Order Test Completed Successfully!
```

**Use Case:**
- User wants to sell at a specific price or better
- Protects against unfavorable price movements
- Allows strategic entry/exit points

---

### 2. **Multiple Signals Test** (`TestE2EMultipleSignals`)

#### Test Method: `test_multiple_signals_mixed_order_types`

**Scenario:**
Tests handling multiple signals in the shopping cart with mixed order types (market, limit).

**Flow:**
1. Create 3 different politician trades:
   - AAPL: Nancy Pelosi SELLS (signal: SELL)
   - MSFT: Nancy Pelosi BUYS (signal: BUY)
   - TSLA: Nancy Pelosi SELLS (signal: SELL)
2. Generate signals for each
3. Add all 3 to shopping cart (10, 20, 30 shares respectively)
4. Execute with mixed order types:
   - AAPL: Market order
   - MSFT: Limit order
   - TSLA: Limit order
5. Verify all 3 orders submitted correctly

**Key Validations:**
- ✅ Cart handles 3 different signals
- ✅ Quantities are distinct (10, 20, 30)
- ✅ Mixed order types executed correctly
- ✅ All orders have correct side (buy/sell)

**Example Output:**
```
=== E2E Test: Multiple Signals with Mixed Order Types ===

✅ Created SELL signal for AAPL
✅ Created BUY signal for MSFT
✅ Created SELL signal for TSLA
✅ Added 3 signals to cart
   • AAPL: 10 shares (SELL)
   • MSFT: 20 shares (BUY)
   • TSLA: 30 shares (SELL)
✅ Placed MARKET order: SELL 10 AAPL
✅ Placed LIMIT order: BUY 20 MSFT
✅ Placed LIMIT order: SELL 30 TSLA

✅ Successfully executed 3 orders with mixed types!
✅ Multiple Signals Test Completed Successfully!
```

**Use Case:**
- User follows multiple politicians simultaneously
- Diversified portfolio management
- Batch order execution
- Mixed trading strategies

---

### 3. **Performance Benchmarking** (`TestE2EPerformance`)

#### Test Method: `test_cart_performance_with_many_signals`

**Scenario:**
Tests shopping cart performance with high load (50 signals).

**Benchmarks:**
- **Add:** Time to add 50 signals to cart
- **Retrieve:** Time to fetch all cart items
- **Update:** Time to update 10 quantities
- **Clear:** Time to clear entire cart

**Performance Requirements:**
- ✅ Adding 50 items: < 1.0 second
- ✅ Retrieving items: < 0.1 second
- ✅ Updating 10 quantities: < 0.5 seconds
- ✅ Clearing cart: < 0.1 second

**Example Output:**
```
=== Performance Test: Shopping Cart with 50 Signals ===

✅ Added 50 signals in 0.1234 seconds (2.47ms per item)
✅ Retrieved 50 items in 0.0023 seconds
✅ Updated 10 quantities in 0.0456 seconds
✅ Cleared cart in 0.0012 seconds

📊 Performance Summary:
   Add 50 items: 123.40ms total, 2.47ms per item
   Retrieve: 2.30ms
   Update 10: 45.60ms
   Clear: 1.20ms

✅ Performance Test Passed!
```

**Use Case:**
- Ensure system scales with many signals
- Identify performance bottlenecks
- Validate user experience remains fast
- Regression testing for performance

**Markers:**
- `@pytest.mark.benchmark` - Identifies as performance test
- Run separately: `pytest -m benchmark`

---

### 4. **Real Alpaca Integration** (`TestE2ERealAlpacaIntegration`)

#### Test Method: `test_real_alpaca_paper_trading_connection`

**Scenario:**
Optional test that connects to real Alpaca paper trading API (not mocked).

**Requirements:**
- Real Alpaca paper trading API keys
- Environment variables set:
  - `ALPACA_PAPER_API_KEY` (must start with "PK")
  - `ALPACA_PAPER_SECRET_KEY`

**Flow:**
1. Load real API keys from environment
2. Connect to Alpaca paper trading API
3. Retrieve account information
4. Verify connection successful
5. Display account status and balances

**Safety Features:**
- ⚠️ Skipped by default (must run explicitly)
- ⚠️ Only allows paper trading keys (PK prefix)
- ⚠️ Does NOT place real orders
- ⚠️ Only tests connection

**Example Output:**
```
=== Real Alpaca Integration Test ===

⚠️  WARNING: This test will use REAL Alpaca API
   API Key: PKxxxxxx...

✅ Connected to Alpaca Paper Trading
   Account ID: 12345678-1234-1234-1234-123456789012
   Status: ACTIVE
   Cash: $100,000.00
   Buying Power: $200,000.00

✅ Real Alpaca Connection Test Passed!
```

**How to Run:**
```bash
# Set real API keys
export ALPACA_PAPER_API_KEY="PK..."
export ALPACA_PAPER_SECRET_KEY="..."

# Run with special flag
pytest tests/integration/test_e2e_advanced_scenarios.py -m real_alpaca -v
```

**Markers:**
- `@pytest.mark.skip` - Skipped by default
- `@pytest.mark.real_alpaca` - Run with `-m real_alpaca`

---

## Running the Tests

### Run All Advanced Tests

```bash
pytest tests/integration/test_e2e_advanced_scenarios.py -v -s
```

### Run Specific Test Class

```bash
# Limit orders only
pytest tests/integration/test_e2e_advanced_scenarios.py::TestE2ELimitOrders -v -s

# Multiple signals only
pytest tests/integration/test_e2e_advanced_scenarios.py::TestE2EMultipleSignals -v -s

# Performance benchmarks only
pytest tests/integration/test_e2e_advanced_scenarios.py::TestE2EPerformance -v -s
```

### Run with Markers

```bash
# Run only performance benchmarks
pytest -m benchmark -v

# Skip real Alpaca tests (default)
pytest -m "not real_alpaca" -v

# Run ONLY real Alpaca tests (requires keys)
pytest -m real_alpaca -v
```

### Parallel Execution

```bash
# Run tests in parallel (4 workers)
pytest tests/integration/test_e2e_advanced_scenarios.py -n 4 -v
```

---

## Flaky Test Detection

The test suite uses `pytest-rerunfailures` to automatically detect and rerun flaky tests.

### Configuration

**File:** `pytest.ini`

```ini
[pytest]
addopts =
    --reruns 2        # Retry failed tests up to 2 times
    --reruns-delay 1  # Wait 1 second between retries
```

### Marking Flaky Tests

If a test is known to be flaky, mark it:

```python
@pytest.mark.flaky
async def test_potentially_flaky():
    # Test that might fail intermittently
    pass
```

### Viewing Flaky Test Reports

```bash
# Run with flaky test reporting
pytest --reruns 2 --reruns-delay 1 -v

# Example output:
# test_example.py::test_flaky RERUN                              [ 33%]
# test_example.py::test_flaky RERUN                              [ 66%]
# test_example.py::test_flaky PASSED                             [100%]
```

---

## Performance Benchmarking

### Using pytest-benchmark

The test suite includes performance benchmarking capabilities.

**Installation:**
```bash
uv pip install pytest-benchmark
```

**Example Test:**
```python
def test_cart_add_benchmark(benchmark):
    """Benchmark cart add operation"""
    cart_item = CartItem(...)
    result = benchmark(ShoppingCart.add_item, cart_item)
    assert result is True
```

**Run Benchmarks:**
```bash
# Run all benchmarks
pytest -m benchmark --benchmark-only

# Generate HTML report
pytest -m benchmark --benchmark-html=benchmark_report.html
```

**Benchmark Output:**
```
----------------------- benchmark: 1 tests ------------------------
Name (time in ms)                Min      Max     Mean  StdDev
-------------------------------------------------------------------
test_cart_add_benchmark      2.1234   2.5678   2.3456   0.1234
-------------------------------------------------------------------
```

---

## CI/CD Integration

The advanced E2E tests are integrated into GitHub Actions:

**Workflow:** `.github/workflows/ci.yml`

```yaml
- name: Run advanced E2E scenarios
  run: |
    pytest tests/integration/test_e2e_advanced_scenarios.py -v -s --tb=short -m "not real_alpaca"
  env:
    ALPACA_PAPER_API_KEY: PKTEST1234567890
    ALPACA_PAPER_SECRET_KEY: test_secret_key_12345
```

**Key Points:**
- ✅ Runs on every push/PR
- ✅ Excludes real Alpaca tests (`-m "not real_alpaca"`)
- ✅ Uses mock API keys
- ✅ Reports uploaded as artifacts

---

## Test Coverage

### What's Tested

**Order Types:**
- ✅ Market orders
- ✅ Limit orders
- ✅ Mixed order types

**Cart Functionality:**
- ✅ Multiple signals
- ✅ Different quantities
- ✅ High volume (50+ signals)
- ✅ Performance under load

**API Integration:**
- ✅ Mock Alpaca (default)
- ✅ Real Alpaca (optional)
- ✅ Connection testing
- ✅ Account validation

**Performance:**
- ✅ Cart operations
- ✅ Batch processing
- ✅ Scalability testing

---

## Best Practices

### 1. **Use Markers Appropriately**

```python
# Performance test
@pytest.mark.benchmark
async def test_performance():
    pass

# Real API test
@pytest.mark.real_alpaca
@pytest.mark.skip(reason="Requires real keys")
async def test_real_api():
    pass

# Flaky test
@pytest.mark.flaky
async def test_intermittent():
    pass
```

### 2. **Document Performance Expectations**

```python
# Bad - no documentation
def test_cart_add():
    assert add_duration < 1.0

# Good - clear expectations
def test_cart_add():
    """
    Performance requirement: Adding 50 items should take < 1.0 second
    Current average: ~0.12 seconds (6x faster than requirement)
    """
    assert add_duration < 1.0
```

### 3. **Use Fixtures for Common Setup**

```python
@pytest.fixture
def cart_with_signals():
    """Pre-populate cart with test signals"""
    ShoppingCart.initialize()
    for i in range(10):
        ShoppingCart.add_item(create_test_signal(i))
    yield
    ShoppingCart.clear()
```

### 4. **Clean Up After Tests**

```python
async def test_example():
    # ... test code ...

    # Always cleanup
    ShoppingCart.clear()
    mock_supabase_client.clear_all_data()
```

---

## Troubleshooting

### Issue: Performance Test Fails

```
AssertionError: Adding 50 items took too long: 1.5s
```

**Solution:**
- Check system load
- Run in isolation: `pytest -k test_cart_performance`
- Adjust threshold if running on slow CI

### Issue: Real Alpaca Test Skipped

```
SKIPPED [1] Real Alpaca API keys not found in environment
```

**Solution:**
```bash
export ALPACA_PAPER_API_KEY="PK..."
export ALPACA_PAPER_SECRET_KEY="..."
pytest -m real_alpaca
```

### Issue: Flaky Test Still Fails After Retries

```
test_flaky.py::test_example RERUN
test_flaky.py::test_example RERUN
test_flaky.py::test_example FAILED
```

**Solution:**
- Investigate root cause
- Add more logging
- Increase retry count: `--reruns 5`
- Add longer delay: `--reruns-delay 2`

---

## Future Enhancements

### Planned Features

- [ ] **Stop-limit orders** - Test stop-limit order execution
- [ ] **Trailing stop orders** - Test trailing stop functionality
- [ ] **Partial fills** - Test partial order fills
- [ ] **Order cancellation** - Test cancelling pending orders
- [ ] **Multi-leg strategies** - Test options strategies
- [ ] **Load testing** - Simulate 100+ concurrent users
- [ ] **Stress testing** - Test system under extreme load
- [ ] **Chaos engineering** - Test failure scenarios

### Performance Monitoring

- [ ] **Continuous benchmarking** - Track performance over time
- [ ] **Performance regression detection** - Alert on slowdowns
- [ ] **Resource usage monitoring** - CPU, memory, network
- [ ] **Database query profiling** - Identify slow queries

---

## Related Documentation

- [Basic E2E Tests](README_E2E_TEST.md)
- [Test Fixtures](../fixtures/test_data.py)
- [CI/CD Integration](../../docs/CI_CD_INTEGRATION.md)
- [GitHub Workflows](../../.github/workflows/README.md)

---

## Summary

The advanced E2E test suite extends the basic trading flow with:

✅ **Limit orders** - Strategic price targets
✅ **Multiple signals** - Batch processing
✅ **Performance benchmarks** - Scalability testing
✅ **Real API integration** - Production validation
✅ **Flaky test detection** - Automatic retries
✅ **Parallel execution** - Faster test runs

These tests ensure the system handles advanced use cases and maintains performance under load! 🚀
