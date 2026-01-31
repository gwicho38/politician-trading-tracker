# Ralph Autonomous Agent - Fix Plan

## Current Session: 2026-01-31

### Completed Improvements

#### 1. Division by Zero Fix in Feature Pipeline
**Category:** Robustness
**Files Modified:**
- `python-etl-service/app/services/feature_pipeline.py` - Added guard for zero-value start prices
- `python-etl-service/tests/test_feature_pipeline.py` - Updated test to explicitly verify null handling

**Details:**
The `_add_stock_returns` method in `FeaturePipeline` was performing divisions without checking if the denominator could be zero. This caused RuntimeWarnings during test execution:
- Line 333: `(price_7d - price_start) / price_start`
- Line 342: `(price_30d - price_start) / price_start`
- Line 351: `(prices_20d_back.iloc[-1] - prices_20d_back.iloc[0]) / prices_20d_back.iloc[0]`

**Fix:** Added explicit guard at line 326 to check if `price_start == 0` before any divisions, and added a similar guard for `momentum_base` at line 351.

**Verification:** All 1499 tests pass. RuntimeWarning for division by zero no longer appears.

---

## Backlog - Discovered Issues for Future Loops

### High Priority

#### Type Safety Improvements
- [ ] Enable strict mypy mode for `python-etl-service` (currently disabled in pyproject.toml line 168)
- [ ] Add proper type annotations to functions lacking them
- [ ] Replace `Any` types with specific types

#### Error Handling
- [ ] Review exception handling in ETL services for proper error categorization
- [ ] Add structured error types for different failure modes

### Medium Priority

#### Testing
- [ ] Add test for market_momentum calculation with zero base price (line 351)
- [ ] Review test coverage for edge cases in price calculations

#### Logging
- [ ] Review warning log messages for actionable information
- [ ] Consider structured logging improvements

#### Code Quality
- [ ] Review `placeholder` comments (lines 371-376) in feature_pipeline.py for unimplemented features

### Low Priority

#### Documentation
- [ ] Document the label threshold constants and their rationale
- [ ] Add inline documentation for complex calculation logic

---

## Notes

- Test suite: 1499 tests, all passing
- Warnings: 1 (unrelated RestrictedPython syntax warning)
- CI Status: ClawdBot Autonomous Agent workflow shows failures - needs investigation

---

## Next Priority

**Focus Area:** Type Safety
**Recommended Task:** Enable stricter mypy checks for python-etl-service module and fix type errors that arise.
