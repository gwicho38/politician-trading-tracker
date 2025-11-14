# Constants Usage Guide

## Overview

This project uses centralized constants to maintain consistency and prevent hardcoded strings throughout the codebase. All constants are defined in the `src/politician_trading/constants/` directory.

## Why Constants?

Centralizing constants provides several benefits:

1. **Single Source of Truth**: Change a value once, it updates everywhere
2. **Type Safety**: IDEs can autocomplete and catch typos
3. **Maintainability**: Easy to find all usages of a constant
4. **Consistency**: Prevents typos and variations (e.g., "pending" vs "Pending")
5. **Documentation**: Constants are self-documenting and easier to understand
6. **Refactoring**: Rename safely using IDE refactoring tools

## Available Constants

### Database (`database.py`)

#### Tables
Database table names:

```python
from politician_trading.constants import Tables

# Use constants instead of hardcoded strings
result = db.table(Tables.POLITICIANS).select("*")
result = db.table(Tables.TRADING_DISCLOSURES).insert(data)
result = db.table(Tables.SCHEDULED_JOBS).update({"status": "completed"})
```

**Available tables:**
- `Tables.POLITICIANS`
- `Tables.TRADING_DISCLOSURES`
- `Tables.TRADING_SIGNALS`
- `Tables.TRADING_ORDERS`
- `Tables.PORTFOLIOS`
- `Tables.POSITIONS`
- `Tables.DATA_PULL_JOBS`
- `Tables.SCHEDULED_JOBS`
- `Tables.JOB_EXECUTIONS`
- `Tables.ACTION_LOGS`
- `Tables.STORED_FILES`
- `Tables.USER_API_KEYS`
- `Tables.USER_SESSIONS`
- And more...

#### Columns
Database column names organized by table:

```python
from politician_trading.constants import Columns

# Common columns
.select(Columns.Common.ID, Columns.Common.CREATED_AT)

# Politician-specific columns
.eq(Columns.Politician.FIRST_NAME, "John")
.eq(Columns.Politician.LAST_NAME, "Doe")

# Disclosure-specific columns
.select(
    Columns.Disclosure.ASSET_TICKER,
    Columns.Disclosure.TRANSACTION_TYPE,
    Columns.Disclosure.TRANSACTION_DATE
)
```

**Available column classes:**
- `Columns.Common` - Shared columns (id, created_at, updated_at, status)
- `Columns.Politician` - Politician table columns
- `Columns.Disclosure` - Trading disclosure columns
- `Columns.Signal` - Trading signal columns
- `Columns.Order` - Order columns
- `Columns.Job` - Job-related columns
- `Columns.Storage` - Storage/file columns
- `Columns.ActionLog` - Action log columns
- `Columns.User` - User-related columns

### Status Values (`statuses.py`)

#### Job Status
Job execution statuses:

```python
from politician_trading.constants import JobStatus

job_data = {
    "status": JobStatus.RUNNING,
    "started_at": datetime.utcnow()
}

if job.status == JobStatus.COMPLETED:
    print("Job finished successfully")
```

**Available statuses:**
- `JobStatus.PENDING`
- `JobStatus.RUNNING`
- `JobStatus.COMPLETED`
- `JobStatus.FAILED`
- `JobStatus.SUCCESS`
- `JobStatus.ERROR`

#### Order Status
Trading order statuses (Alpaca-compatible):

```python
from politician_trading.constants import OrderStatus

if order.status == OrderStatus.FILLED:
    process_filled_order(order)
elif order.status in [OrderStatus.CANCELED, OrderStatus.REJECTED]:
    handle_failed_order(order)
```

**Available statuses:**
- `OrderStatus.PENDING_NEW`
- `OrderStatus.SUBMITTED`
- `OrderStatus.FILLED`
- `OrderStatus.PARTIALLY_FILLED`
- `OrderStatus.CANCELED`
- `OrderStatus.REJECTED`
- And more...

#### Transaction Types
Trading transaction types:

```python
from politician_trading.constants import TransactionType

if transaction.type == TransactionType.PURCHASE:
    signal_type = SignalType.BUY
elif transaction.type == TransactionType.SALE:
    signal_type = SignalType.SELL
```

**Available types:**
- `TransactionType.PURCHASE`
- `TransactionType.SALE`
- `TransactionType.BUY`
- `TransactionType.SELL`
- `TransactionType.EXCHANGE`

#### Signal Types
Trading signal types:

```python
from politician_trading.constants import SignalType

signal = {
    "type": SignalType.STRONG_BUY,
    "confidence": 0.85
}
```

**Available types:**
- `SignalType.STRONG_BUY`
- `SignalType.BUY`
- `SignalType.HOLD`
- `SignalType.SELL`
- `SignalType.STRONG_SELL`

#### Action Types
Action log types:

```python
from politician_trading.constants import ActionType

log_action(
    action_type=ActionType.LOGIN_SUCCESS,
    user_email=user.email
)
```

**Available types:**
- `ActionType.LOGIN_ATTEMPT`
- `ActionType.LOGIN_SUCCESS`
- `ActionType.DATA_COLLECTION_START`
- `ActionType.JOB_EXECUTION`
- And more...

### Environment Variables (`env_keys.py`)

Environment variable key names:

```python
from politician_trading.constants import EnvKeys, EnvDefaults
import os

# Use constants for env var keys
supabase_url = os.getenv(EnvKeys.SUPABASE_URL, EnvDefaults.SUPABASE_URL)
alpaca_key = os.getenv(EnvKeys.ALPACA_API_KEY)
log_level = os.getenv(EnvKeys.LOG_LEVEL, EnvDefaults.LOG_LEVEL)
```

**Available keys:**
- `EnvKeys.SUPABASE_URL`
- `EnvKeys.SUPABASE_ANON_KEY`
- `EnvKeys.ALPACA_API_KEY`
- `EnvKeys.ALPACA_SECRET_KEY`
- `EnvKeys.QUIVERQUANT_API_KEY`
- And many more...

**Default values:**
- `EnvDefaults.SUPABASE_URL`
- `EnvDefaults.LOG_LEVEL`
- `EnvDefaults.MAX_RETRIES`
- And more...

### Storage (`storage.py`)

Storage bucket names and path utilities:

```python
from politician_trading.constants import StorageBuckets, StoragePaths

# Upload to storage bucket
bucket = StorageBuckets.RAW_PDFS
path = StoragePaths.construct_pdf_path("senate", 2024, 3, "disclosure.pdf")
storage.from_(bucket).upload(path, pdf_content)

# Construct API response path
api_path = StoragePaths.construct_api_response_path(
    "quiverquant",
    "2024-03-15",
    "response.json"
)
```

**Available buckets:**
- `StorageBuckets.RAW_PDFS`
- `StorageBuckets.API_RESPONSES`
- `StorageBuckets.PARSED_DATA`
- `StorageBuckets.HTML_SNAPSHOTS`

**Path utilities:**
- `StoragePaths.get_chamber_path(source_type)`
- `StoragePaths.construct_pdf_path(chamber, year, month, filename)`
- `StoragePaths.construct_api_response_path(source, date, filename)`

### URLs and Configuration (`urls.py`)

#### API URLs
External API endpoints:

```python
from politician_trading.constants import ApiUrls

# Use constants for API endpoints
response = requests.get(ApiUrls.ALPACA_PAPER)
data = fetch_from(ApiUrls.QUIVERQUANT_API)
```

**Available API URLs:**
- `ApiUrls.ALPACA_PAPER` - Alpaca paper trading API
- `ApiUrls.ALPACA_LIVE` - Alpaca live trading API
- `ApiUrls.HOUSE_DISCLOSURES` - US House financial disclosures
- `ApiUrls.SENATE_EFD` - US Senate electronic filing system
- `ApiUrls.QUIVERQUANT_API` - QuiverQuant API endpoint
- And more...

#### Web URLs
Website URLs (non-API):

```python
from politician_trading.constants import WebUrls

# Use constants for web URLs
redirect_to(WebUrls.GITHUB_REPO)
dashboard_url = WebUrls.ALPACA_DASHBOARD
```

**Available web URLs:**
- `WebUrls.GITHUB_REPO` - This repository
- `WebUrls.ALPACA_DASHBOARD` - Alpaca web interface
- `WebUrls.LOCALHOST` - Local development
- And more...

#### Configuration Defaults
Default values for configuration:

```python
from politician_trading.constants import ConfigDefaults

# Use constants for config defaults
timeout = ConfigDefaults.DEFAULT_TIMEOUT
max_retries = ConfigDefaults.DEFAULT_MAX_RETRIES
confidence_threshold = ConfigDefaults.MIN_CONFIDENCE
```

**Available config defaults:**
- `ConfigDefaults.DEFAULT_TIMEOUT` - Default request timeout
- `ConfigDefaults.DEFAULT_MAX_RETRIES` - Default retry count
- `ConfigDefaults.MIN_CONFIDENCE` - Minimum trading confidence
- `ConfigDefaults.MAX_POSITIONS` - Maximum portfolio positions
- And more...

## Best Practices

### 1. Always Import Constants

```python
# ✅ Good
from politician_trading.constants import Tables, Columns, JobStatus

result = db.table(Tables.POLITICIANS).select(Columns.Politician.FULL_NAME)

# ❌ Bad
result = db.table("politicians").select("full_name")
```

### 2. Use Type Hints

```python
from politician_trading.constants import JobStatus

def update_job_status(job_id: str, status: str) -> None:
    """
    Update job status.

    Args:
        job_id: Job identifier
        status: Job status (use JobStatus constants)
    """
    # Implementation
```

### 3. Group Related Imports

```python
# Group constants imports together
from politician_trading.constants import (
    Columns,
    EnvKeys,
    JobStatus,
    OrderStatus,
    Tables,
)

# Other imports
import os
from datetime import datetime
```

### 4. Don't Create New Hardcoded Strings

If you need a new constant:

1. Add it to the appropriate constants file
2. Update the linter if needed
3. Use it throughout your code

```python
# If you need a new status value:
# 1. Add to src/politician_trading/constants/statuses.py
class JobStatus:
    # ... existing statuses ...
    NEW_STATUS = "new_status"  # Add here

# 2. Use it in your code
from politician_trading.constants import JobStatus
job.status = JobStatus.NEW_STATUS
```

## Linter Enforcement

This project includes a custom linter that detects hardcoded strings that should use constants.

### Running the Linter

```bash
# Lint all files in src/
python scripts/lint_hardcoded_strings.py

# Lint specific files
python scripts/lint_hardcoded_strings.py src/politician_trading/workflow.py

# Strict mode (treat warnings as errors)
python scripts/lint_hardcoded_strings.py --strict
```

### Pre-commit Hook

The linter runs automatically on every commit via pre-commit hooks:

```bash
# Install pre-commit hooks (one-time setup)
pre-commit install

# Run hooks manually
pre-commit run --all-files

# Skip hooks (not recommended)
git commit --no-verify
```

### Fixing Violations

When the linter finds violations:

```
src/politician_trading/workflow.py:
  Line 45:12: Use Tables.POLITICIANS instead of 'politicians'
  Line 67:20: Use JobStatus.RUNNING instead of 'running'
```

Fix them by:

1. Importing the appropriate constant
2. Replacing the hardcoded string

```python
# Before
result = db.table("politicians").select("*")
job.status = "running"

# After
from politician_trading.constants import Tables, JobStatus

result = db.table(Tables.POLITICIANS).select("*")
job.status = JobStatus.RUNNING
```

## Migration Guide

### For Existing Code

If you're updating existing code to use constants:

1. **Identify hardcoded strings**: Run the linter to find violations
2. **Import constants**: Add imports at the top of the file
3. **Replace strings**: Update all hardcoded strings with constants
4. **Test**: Verify functionality hasn't changed
5. **Commit**: Commit changes with descriptive message

### Example Migration

```python
# Original code
def get_politician(db, politician_id):
    result = db.table("politicians").select("*").eq("id", politician_id).execute()
    if result.data and result.data[0]["is_active"]:
        return result.data[0]
    return None

# Migrated code
from politician_trading.constants import Tables, Columns

def get_politician(db, politician_id):
    result = (
        db.table(Tables.POLITICIANS)
        .select("*")
        .eq(Columns.Common.ID, politician_id)
        .execute()
    )
    if result.data and result.data[0][Columns.Common.IS_ACTIVE]:
        return result.data[0]
    return None
```

## FAQ

### Q: What if I need a constant that doesn't exist?

**A:** Add it to the appropriate constants file in `src/politician_trading/constants/`:
- Database-related → `database.py`
- Status values → `statuses.py`
- Environment vars → `env_keys.py`
- Storage paths → `storage.py`

### Q: Can I use hardcoded strings for UI text?

**A:** Yes, UI text like page titles, button labels, and user messages can be hardcoded. The linter skips strings with spaces or punctuation.

### Q: What about test files?

**A:** Test files are currently excluded from linting, but it's still good practice to use constants in tests for consistency.

### Q: How do I disable the linter for a specific file?

**A:** Add the file pattern to the `exclude` section in `.pre-commit-config.yaml`.

### Q: The linter is flagging a false positive. What do I do?

**A:** If the linter incorrectly flags a string:
1. Verify it's actually a false positive
2. Update the linter's skip conditions in `scripts/lint_hardcoded_strings.py`
3. Create an issue if it's a common case

## Contributing

When contributing to this project:

1. **Always use constants** for database tables, columns, and status values
2. **Run the linter** before committing: `python scripts/lint_hardcoded_strings.py`
3. **Add new constants** if you introduce new concepts or values
4. **Update this guide** if you add new constant categories

## Support

If you have questions about constants usage:

1. Check this guide first
2. Look at existing code for examples
3. Run the linter for suggestions
4. Open an issue for clarification

---

**Remember**: Constants make code more maintainable, consistent, and easier to refactor. Use them!
