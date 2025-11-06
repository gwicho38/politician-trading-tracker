# End-to-End Trading Flow Test Documentation

## Overview

This directory contains a comprehensive end-to-end test that validates the complete user journey from politician trade discovery to stock purchase execution via Alpaca.

## Test File

**File:** `test_e2e_trading_flow.py`

**Test Method:** `TestE2ETradingFlow.test_complete_nancy_pelosi_aapl_trading_workflow`

## Test Scenario

The test simulates a real-world trading workflow based on politician trading activity:

### User Story
> As a Pro tier subscriber, I discover that Nancy Pelosi sold Apple (AAPL) stock. Based on this information, the system generates a SELL signal. I add this signal to my shopping cart, adjust the quantity, and execute the trade through Alpaca's paper trading platform. The position then appears in my portfolio with complete traceability back to the original politician trade.

## Test Flow (9 Steps)

### 1. **Data Seeding**
- Creates Nancy Pelosi politician record
- Creates AAPL stock sale disclosure
- Verifies data inserted correctly into database

**Assertions:**
- ✅ Politician record exists with correct name and party
- ✅ Disclosure record exists with correct ticker and transaction type
- ✅ Disclosure is linked to politician via `politician_id`

### 2. **Signal Generation**
- Generates trading signal from the politician disclosure
- Uses ML-based confidence scoring
- Sets price targets (target, stop loss, take profit)

**Assertions:**
- ✅ Signal type is SELL (following Pelosi's action)
- ✅ Confidence score >= 60%
- ✅ All price targets are set
- ✅ Signal is linked to disclosure via `disclosure_ids`

### 3. **Paywall Access Verification**
- Tests Pro tier user access (should have access)
- Tests Free tier user access (should be blocked)

**Assertions:**
- ✅ Pro tier user can access `trading_signals` feature
- ✅ Free tier user is blocked from `trading_signals`
- ✅ Subscription tier is correctly detected

### 4. **Shopping Cart Operations**
- Initializes empty cart
- Adds signal to cart with 10 shares
- Updates quantity to 15 shares
- Verifies cart state persistence

**Assertions:**
- ✅ Cart initializes empty
- ✅ Item added successfully
- ✅ Quantity update persists
- ✅ Cart maintains signal metadata (confidence, price targets)

### 5. **Trade Execution (Checkout)**
- Connects to Alpaca API (paper trading mode)
- Executes SELL order for 15 shares of AAPL
- Stores order in database
- Clears cart after successful execution

**Assertions:**
- ✅ Alpaca connection successful
- ✅ Account status is ACTIVE
- ✅ Order submitted with unique Alpaca order ID
- ✅ Order type is MARKET
- ✅ Order side is SELL
- ✅ Order stored in `trading_orders` table
- ✅ Cart cleared after execution

### 6. **Alpaca Integration Verification**
- Verifies order ID format (UUID as string, JSON serializable)
- Simulates order fill
- Updates order status in database

**Assertions:**
- ✅ Order IDs are strings (not UUID objects)
- ✅ Order can be JSON serialized
- ✅ Trading mode is PAPER

### 7. **Portfolio Tracking**
- Creates portfolio record
- Creates position record (SHORT 15 shares AAPL)
- Links position to signal and order

**Assertions:**
- ✅ Portfolio created with correct trading mode
- ✅ Position exists with correct ticker and quantity
- ✅ Position side is SHORT (because it's a sell order)
- ✅ Entry price recorded
- ✅ Position linked to signal via `signal_ids`
- ✅ Position linked to order via `order_ids`

### 8. **Complete Traceability Verification**
- Traces lineage: Politician → Disclosure → Signal → Order → Position
- Verifies all links in the chain are correct

**Assertions:**
- ✅ Position links to signal
- ✅ Signal links to disclosure
- ✅ Disclosure links to politician
- ✅ Complete audit trail established

### 9. **Cleanup**
- Deletes all test data in reverse dependency order
- Verifies clean slate for next test run

**Assertions:**
- ✅ All test records removed from database
- ✅ No orphaned data remains

## Running the Test

### Prerequisites

```bash
# Install dependencies
uv pip install pytest pytest-asyncio pytest-mock pytest-cov

# Set up environment (optional - test uses mocks)
export ALPACA_PAPER_API_KEY="your_paper_key"
export ALPACA_PAPER_SECRET_KEY="your_paper_secret"
```

### Run the Test

```bash
# Run E2E test
pytest tests/integration/test_e2e_trading_flow.py -v -s

# Run with coverage
pytest tests/integration/test_e2e_trading_flow.py --cov=src/politician_trading --cov-report=html

# Run specific test method
pytest tests/integration/test_e2e_trading_flow.py::TestE2ETradingFlow::test_complete_nancy_pelosi_aapl_trading_workflow -v
```

### Expected Output

```
=== STEP 1: Seeding Test Data ===
✅ Inserted Nancy Pelosi (ID: ...)
✅ Inserted AAPL sale disclosure (ID: ...)

=== STEP 2: Generating Trading Signal ===
✅ Generated signal: SELL AAPL
   Confidence: 75.0%
   Target: $145.50
   Stop Loss: $165.00
   Take Profit: $135.00

=== STEP 3: Verifying Paywall Access ===
✅ Pro tier user has access to trading_signals
✅ Free tier user correctly blocked from trading_signals

=== STEP 4: Shopping Cart Operations ===
✅ Cart initialized (empty)
✅ Added AAPL to cart (quantity: 10)
✅ Updated quantity to 15 shares

=== STEP 5: Executing Trade via Alpaca ===
✅ Connected to Alpaca (Paper Trading)
   Account ID: ...
   Buying Power: $100,000.00
✅ Placed order: SELL 15 shares of AAPL
   Order ID: ...
   Status: pending
✅ Cart cleared after successful execution

=== STEP 6: Verifying Alpaca Integration ===
✅ Order successfully submitted to Alpaca
   Alpaca Order ID: ...

=== STEP 7: Portfolio Tracking ===
✅ Portfolio created (ID: ...)
✅ Position created: SHORT 15 shares AAPL @ $150.25
✅ Position verified in portfolio
   Entry Price: $150.25
   Market Value: $2253.75
   Linked to Signal: ...
   Linked to Order: ...

=== STEP 8: Verifying Complete Traceability ===

📊 Complete Trade Lineage:
   1. Politician: Nancy Pelosi (Democrat)
   2. Disclosure: SALE AAPL on 2025-10-22
   3. Signal: SELL (Confidence: 75.0%)
   4. Order: SELL 15 shares @ MARKET
   5. Position: SHORT 15 shares @ $150.25

✅ Complete traceability verified!

=== STEP 9: Cleanup Test Data ===
✅ Deleted position
✅ Deleted portfolio
✅ Deleted order
✅ Deleted signal
✅ Deleted disclosure
✅ Deleted politician

======================================================================
🎉 END-TO-END TEST COMPLETED SUCCESSFULLY!
======================================================================

Test Summary:
✅ Politician trade data seeded
✅ Trading signal generated from politician activity
✅ Paywall correctly enforced feature access
✅ Shopping cart managed items correctly
✅ Order successfully submitted to Alpaca (paper mode)
✅ Portfolio position created and tracked
✅ Complete traceability maintained (politician → position)
✅ All test data cleaned up

======================================================================

======================== 1 passed in 2.72s ========================
```

## Test Architecture

### Mocking Strategy

The test uses mocks for:
- **Supabase Database**: `MockSupabaseClient` - In-memory database for fast tests
- **Alpaca API**: Mocked via `unittest.mock.patch` - No real API calls
- **Streamlit Session**: Mocked session state for paywall/cart testing

### Test Fixtures

**File:** `tests/fixtures/test_data.py`

The `TestDataFactory` provides:
- `create_nancy_pelosi()` - Politician record
- `create_aapl_sale_disclosure()` - Trading disclosure
- `create_test_signal()` - Trading signal with ML confidence
- `create_test_user_pro_tier()` - Pro subscription user
- `create_test_user_free_tier()` - Free tier user

### Database Schema Coverage

The test validates these tables:
- ✅ `politicians`
- ✅ `trading_disclosures`
- ✅ `trading_signals`
- ✅ `trading_orders`
- ✅ `portfolios`
- ✅ `positions`

## Key Learnings & Best Practices

### 1. **Enum Comparison**
When comparing enum values in assertions, use `.value` to compare the underlying value, not the enum identity:

```python
# ❌ BAD - compares enum identity
assert order.status == OrderStatus.PENDING

# ✅ GOOD - compares enum value
assert order.status.value == "pending"
```

### 2. **Complete Data Lineage**
Always maintain traceability through foreign keys:
- Disclosure → Signal via `disclosure_ids`
- Signal → Order via `signal_id`
- Order/Signal → Position via `order_ids` and `signal_ids`

### 3. **Test Data Cleanup**
Delete in reverse dependency order:
1. Positions (depend on portfolios, signals, orders)
2. Portfolios
3. Orders (depend on signals)
4. Signals (depend on disclosures)
5. Disclosures (depend on politicians)
6. Politicians

### 4. **Realistic Test Data**
Use realistic values for:
- Confidence scores (0.6-0.95)
- Stock prices (market-appropriate ranges)
- Transaction amounts ($50K-$100K for Congress disclosures)

### 5. **Paywall Testing**
Test both positive (Pro tier) and negative (Free tier) cases to ensure feature gating works correctly.

## Future Enhancements

Potential additions to the E2E test:

- [ ] Test multiple signals in cart simultaneously
- [ ] Test limit orders (not just market orders)
- [ ] Test order rejection scenarios
- [ ] Test portfolio performance calculations
- [ ] Test signal expiration handling
- [ ] Test rate limiting for Free tier users
- [ ] Integration with real Alpaca paper trading (optional)
- [ ] Test multi-politician aggregation (e.g., 3+ Congress members buying same stock)

## Troubleshooting

### Test Fails with Import Errors

```bash
# Ensure Python path includes src/
export PYTHONPATH="${PYTHONPATH}:/path/to/politician-trading-tracker/src"
```

### Streamlit Warnings

The warnings about `ScriptRunContext` are expected when running Streamlit code outside the Streamlit runtime. They can be safely ignored in tests.

### Mock Database Persistence

The `MockSupabaseClient` is in-memory only and resets between tests. This is intentional for test isolation.

## Contributing

When adding new features to the trading flow, ensure you:

1. Add corresponding steps to this E2E test
2. Update the test fixtures in `tests/fixtures/test_data.py`
3. Verify complete traceability through all data layers
4. Add cleanup for any new database tables

## Related Documentation

- [Paywall Integration](../../docs/PAYWALL_INTEGRATION.md)
- [Alpaca Trading Client](../../src/politician_trading/trading/alpaca_client.py)
- [Signal Generation](../../src/politician_trading/signals/signal_generator.py)
- [Shopping Cart](../../shopping_cart.py)

## Test Statistics

- **Total Assertions:** 50+
- **Test Duration:** ~2.7 seconds
- **Code Coverage:** 37% of Alpaca client, 12% of signal generator
- **Database Tables Tested:** 6
- **Test Isolation:** 100% (no shared state between runs)
