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

#### 2. Type Safety: Playwright Page Type Annotation
**Category:** Type Safety
**Files Modified:**
- `python-etl-service/app/services/senate_etl.py` - Added proper Playwright Page type

**Details:**
The `parse_ptr_page_playwright` function used `page: Any` for the Playwright page parameter. This loses type information and IDE support for the Playwright API.

**Fix:**
- Added `TYPE_CHECKING` import and conditional import of `playwright.async_api.Page`
- Changed function signature from `page: Any` to `page: "Page"`
- Uses string annotation to avoid runtime import issues when Playwright isn't installed

**Verification:** All 1499 tests pass.

---

#### 3. Type Safety: Fix lowercase `any` type annotation
**Category:** Type Safety
**Files Modified:**
- `python-etl-service/app/services/error_report_processor.py` - Fixed type annotations

**Details:**
The `CorrectionProposal` dataclass used lowercase `any` for type annotations:
```python
old_value: any  # Wrong - 'any' is a builtin function
new_value: any  # Wrong - should be 'Any' from typing
```

This is incorrect because `any` is Python's builtin function, not a type. The correct type is `Any` from the `typing` module.

**Fix:**
- Added `Any` to typing imports
- Changed `old_value: any` to `old_value: Any`
- Changed `new_value: any` to `new_value: Any`

**Verification:** All 1499 tests pass.

---

#### 4. Traceability: Replace print() with proper logging
**Category:** Traceability
**Files Modified:**
- `python-etl-service/app/services/auto_correction.py` - Added logger, replaced 5 print statements
- `python-etl-service/app/services/politician_dedup.py` - Replaced 1 print statement
- `python-etl-service/app/services/error_report_processor.py` - Replaced 2 print statements

**Details:**
Multiple files were using `print()` for error logging instead of the standard Python logger. This is problematic because:
- No timestamps, log levels, or structured data
- Can't be filtered or configured
- Doesn't integrate with log aggregation systems
- Inconsistent with rest of codebase

**Fix:**
- Added `logging` import and `logger = logging.getLogger(__name__)` to auto_correction.py
- Replaced `print(f"Error...")` with `logger.error(f"...")`
- Replaced `print(f"Warning...")` with `logger.warning(f"...")`
- Replaced informational prints with `logger.info(f"...")`

**Verification:** All 1499 tests pass.

---

## Backlog - Discovered Issues for Future Loops

### High Priority

#### Type Safety Improvements
- [ ] Enable strict mypy mode for `python-etl-service` (currently disabled in pyproject.toml line 168)
- [ ] Add proper type annotations to functions lacking them
- [ ] Replace `Any` types with specific types (many remain - see grep for `Any` in codebase)
- [x] Replace `page: Any` with Playwright `Page` type in senate_etl.py
- [x] Fix lowercase `any` type annotations in error_report_processor.py

#### Error Handling
- [ ] Review exception handling in ETL services for proper error categorization
- [ ] Add structured error types for different failure modes

### Medium Priority

#### Testing
- [ ] Add test for market_momentum calculation with zero base price (line 351)
- [ ] Review test coverage for edge cases in price calculations

#### Logging
- [x] Replace print() statements with proper logger calls
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
**Recommended Task:** Add TypedDict for common return types like disclosure dictionaries. Many functions return `Dict[str, Any]` where a TypedDict would provide better type safety.
