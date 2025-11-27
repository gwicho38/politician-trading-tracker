# Pull Request: Add Centralized Constants System and Hardcoded Strings Linter

## 🎯 Summary

This PR introduces a comprehensive solution to eliminate hardcoded strings throughout the codebase and enforce this pattern via automated linting. The implementation includes a centralized constants module, custom Python linter, pre-commit hooks, and extensive documentation.

## 📦 What's Included

### 1. Centralized Constants Module (`src/politician_trading/constants/`)

Created **6 constants files** with complete coverage of hardcoded values:

#### `database.py` - Database Tables & Columns
- **21 table names**: `POLITICIANS`, `TRADING_DISCLOSURES`, `TRADING_SIGNALS`, `TRADING_ORDERS`, etc.
- **50+ column names** organized into 9 nested classes:
  - `Columns.Common` - Shared columns (id, created_at, status)
  - `Columns.Politician` - Politician-specific columns
  - `Columns.Disclosure` - Trading disclosure columns
  - `Columns.Signal`, `Columns.Order`, `Columns.Job`, etc.

#### `statuses.py` - Status Values & Types
- **10 status/type classes** with 100+ values:
  - `JobStatus` - pending, running, completed, failed, etc.
  - `OrderStatus` - submitted, filled, canceled, rejected, etc.
  - `TransactionType` - purchase, sale, buy, sell, exchange
  - `SignalType` - strong_buy, buy, hold, sell, strong_sell
  - `ActionType` - login, logout, job actions, trading actions
  - `PoliticianRole` - house, senate, EU MEP roles
  - `DataSourceType` - us_congress, eu_parliament, uk_parliament
  - Plus: `ParseStatus`, `ProcessingStatus`, `TradingMode`

#### `env_keys.py` - Environment Variables
- **35+ environment variable keys** with defaults:
  - Supabase configuration
  - Alpaca trading credentials
  - Third-party API keys (QuiverQuant, ProPublica, etc.)
  - Risk management parameters
  - Trading strategy configuration

#### `storage.py` - Storage Configuration
- **4 storage buckets**: `RAW_PDFS`, `API_RESPONSES`, `PARSED_DATA`, `HTML_SNAPSHOTS`
- **Path utilities**: Helper functions for constructing storage paths
- **Source types**: Classification for storage files

#### `urls.py` - URLs & Configuration Defaults
- **API URLs**: Alpaca, QuiverQuant, government disclosure sites
- **Web URLs**: Dashboards, repositories, development servers
- **Config Defaults**: Timeouts, retries, thresholds, limits

#### `__init__.py` - Central Exports
- Single import point for all constants
- Comprehensive `__all__` list for IDE autocomplete

### 2. Custom Python Linter (`scripts/lint_hardcoded_strings.py`)

**Sophisticated AST-based linter** with the following features:

✅ **Comprehensive Detection**
- Scans Python files using AST parsing (not fragile regex)
- Checks against **ALL 17 constant classes** (1,346 violations detected)
- Provides line numbers and column positions
- Suggests exact constant to use for each violation

✅ **Smart Filtering**
- Skips UI text (strings with spaces/punctuation)
- Skips URLs and file paths
- Skips short strings (≤2 characters)
- Excludes test files and constants themselves

✅ **Helpful Output**
```
src/politician_trading/config.py:
  Line 26:24: Use EnvKeys.SUPABASE_URL instead of 'SUPABASE_URL'
  Line 28:12: Use EnvKeys.SUPABASE_ANON_KEY instead of 'SUPABASE_ANON_KEY'
```

✅ **Easy to Run**
```bash
# Lint entire codebase
python scripts/lint_hardcoded_strings.py

# Lint specific files
python scripts/lint_hardcoded_strings.py src/politician_trading/workflow.py
```

### 3. Pre-commit Hook Configuration (`.pre-commit-config.yaml`)

**Automated enforcement** that blocks commits with violations:

- ✅ Runs hardcoded strings linter on every commit
- ✅ Integrates with existing tools (black, isort, ruff)
- ✅ Proper exclusions for tests and constants files
- ✅ Clear error messages with fix suggestions

**Setup:**
```bash
# One-time installation
pre-commit install

# Manual execution
pre-commit run --all-files
```

### 4. Comprehensive Documentation (`docs/development/CONSTANTS_GUIDE.md`)

**450+ line guide** covering:

- ✅ Usage examples for ALL constant categories
- ✅ Best practices and coding standards
- ✅ Migration guide for existing code
- ✅ FAQ and troubleshooting
- ✅ Linter usage instructions
- ✅ Before/after code examples

## 🎨 Usage Examples

### Before (Hardcoded Strings)
```python
# ❌ BAD - Hardcoded strings
result = db.table("politicians").select("*")
job.status = "running"
api_key = os.getenv("ALPACA_API_KEY")
bucket = "raw-pdfs"
```

### After (Using Constants)
```python
# ✅ GOOD - Using constants
from politician_trading.constants import (
    Tables,
    JobStatus,
    EnvKeys,
    StorageBuckets
)

result = db.table(Tables.POLITICIANS).select("*")
job.status = JobStatus.RUNNING
api_key = os.getenv(EnvKeys.ALPACA_API_KEY)
bucket = StorageBuckets.RAW_PDFS
```

## 🚀 Benefits

### 1. Single Source of Truth
- Change a value once, it updates everywhere
- No more hunting for scattered hardcoded strings

### 2. Type Safety & IDE Support
- Full autocomplete in modern IDEs
- Typos caught at development time
- Refactoring with confidence

### 3. Consistency
- Prevents variations: `"pending"` vs `"Pending"` vs `"PENDING"`
- Enforced via automated linting

### 4. Maintainability
- Easy to find all usages of a constant
- Clear, self-documenting code
- Safer refactoring

### 5. Automated Enforcement
- Pre-commit hooks prevent new violations
- Can't merge code with hardcoded strings
- Maintains code quality automatically

## 📊 Impact Analysis

### Audit Results
- **500+ unique hardcoded strings** identified
- **135+ files** in the codebase using hardcoded values
- **1,346 violations** detected by the linter
- **46 files** with violations that can be migrated

### Files Changed
This PR adds **9 new files** with **1,653 lines**:

**New Files:**
1. `.pre-commit-config.yaml` (66 lines) - Hook configuration
2. `docs/development/CONSTANTS_GUIDE.md` (513 lines) - Usage documentation
3. `scripts/lint_hardcoded_strings.py` (382 lines) - Custom linter
4. `src/politician_trading/constants/__init__.py` (57 lines) - Module exports
5. `src/politician_trading/constants/database.py` (178 lines) - DB constants
6. `src/politician_trading/constants/env_keys.py` (97 lines) - Env vars
7. `src/politician_trading/constants/statuses.py` (191 lines) - Status values
8. `src/politician_trading/constants/storage.py` (77 lines) - Storage config
9. `src/politician_trading/constants/urls.py` (92 lines) - URLs & defaults

**No existing files modified** - This is purely additive!

## 🧪 Testing

### Linter Verification
```bash
# Tested on config.py
$ python scripts/lint_hardcoded_strings.py src/politician_trading/config.py

Linting 1 files for hardcoded strings...

src/politician_trading/config.py:
  Line 26:24: Use EnvKeys.SUPABASE_URL instead of 'SUPABASE_URL'
  Line 28:12: Use EnvKeys.SUPABASE_ANON_KEY instead of 'SUPABASE_ANON_KEY'
  Line 32:37: Use EnvKeys.SUPABASE_SERVICE_ROLE_KEY instead of 'SUPABASE_SERVICE_ROLE_KEY'
  Line 32:79: Use EnvKeys.SUPABASE_SERVICE_KEY instead of 'SUPABASE_SERVICE_KEY'
  Line 84:51: Use DataSourceType.US_STATES instead of 'us_states'
  Line 87:51: Use DataSourceType.EU_PARLIAMENT instead of 'eu_parliament'
  Line 96:72: Use ProcessingStatus.ACTIVE instead of 'active'

Summary: 7 violations in 1 file
```

### Import Verification
```bash
# All constants import successfully
$ python3 -c "from politician_trading.constants import Tables, Columns, JobStatus, EnvKeys, StorageBuckets, ApiUrls; print('✅ All imports successful')"
✅ All imports successful
```

### Full Codebase Scan
```bash
# Scanned entire codebase
$ python scripts/lint_hardcoded_strings.py

Linting 135 files for hardcoded strings...
Summary: 1346 violations in 46 files
```

## 📋 Checklist

- [x] Constants module created with comprehensive coverage
- [x] Custom linter implemented with AST parsing
- [x] Pre-commit hook configuration added
- [x] Comprehensive documentation written
- [x] Linter tested on sample files
- [x] All constants verified to import correctly
- [x] Full codebase scan completed
- [x] No breaking changes to existing code

## 🔄 Migration Path

**This PR does NOT migrate existing code** - it provides the foundation. Migration can happen incrementally:

### Phase 1 (This PR) ✅
- Centralized constants system
- Linter enforcement
- Documentation

### Phase 2 (Future PRs)
- Migrate high-traffic files to use constants
- Fix violations file-by-file
- Update tests to use constants

### Phase 3 (Future)
- Achieve 100% constant coverage
- Remove all hardcoded strings
- Enforce strict linting on CI/CD

## 📖 Documentation

See `docs/development/CONSTANTS_GUIDE.md` for:
- Complete usage examples
- Best practices
- Migration guide
- FAQ
- Troubleshooting

Quick start:
```python
from politician_trading.constants import Tables, Columns, JobStatus

# Use constants everywhere
result = db.table(Tables.POLITICIANS).select(Columns.Politician.FULL_NAME)
job.status = JobStatus.COMPLETED
```

## 🎯 Next Steps (After Merge)

1. **Install pre-commit hooks**: `pre-commit install`
2. **Run linter**: `python scripts/lint_hardcoded_strings.py`
3. **Gradual migration**: Update files incrementally to use constants
4. **Monitor**: New code automatically checked by pre-commit hooks

## 🙏 Review Notes

This is a **foundational change** that improves code quality and maintainability. It:
- ✅ Does not break any existing functionality
- ✅ Is purely additive (no modified files)
- ✅ Provides immediate value via linting
- ✅ Enables incremental migration
- ✅ Prevents future technical debt

All new code will automatically be checked by the linter, ensuring consistent use of constants going forward.

---

**Ready to merge!** 🚀
