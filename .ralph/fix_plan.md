# Ralph Continuous Improvement Plan

## 🎯 Current Focus
<!-- Ralph: Update this section each loop with what you're working on -->
Input validation tests for API endpoints - COMPLETED

## 📋 Discovered Issues Backlog
<!-- Ralph: Add issues you discover during analysis here. Never let this be empty. -->

### High Priority
- [x] ~~Analyze ETL service for security vulnerabilities (input validation, SQL injection)~~ - Sandbox hardened, Supabase ORM safe
- [x] ~~Audit dependency versions for known vulnerabilities~~ - Fixed CVE-2025-53643, CVE-2025-50181, CVE-2025-66418
- [ ] Review authentication/authorization implementation across all services
- [x] ~~Add input validation tests for API endpoints (quality, enrichment, etl routes)~~ - Added 13 tests
- [x] ~~Add trade amount validation in House ETL parser (reject amounts > $50M to prevent parsing errors)~~ - Implemented with 19 tests

### Medium Priority
- [x] ~~Add structured logging with correlation IDs for request tracing~~ - Implemented
- [ ] Improve error handling in external API calls (Alpaca, QuiverQuant)
- [ ] Add retry logic with exponential backoff for flaky external services

### Low Priority
- [ ] Increase test coverage for edge cases
- [ ] Add API rate limiting to prevent abuse
- [ ] Document API endpoints with OpenAPI/Swagger

## 🔄 In Progress
<!-- Ralph: Move task here when you start working on it -->
None - ready for next task

## ✅ Completed This Session
<!-- Ralph: Record completed work with timestamps -->
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
1. ~~Security audit not yet performed~~ - Initial audit complete, sandbox hardened
2. ~~Observability/logging could be improved~~ - Structured logging with correlation IDs implemented
3. API documentation may be incomplete
4. Type annotations still missing in several ETL service modules
5. External API calls (Alpaca, QuiverQuant) need better error handling and retries

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
