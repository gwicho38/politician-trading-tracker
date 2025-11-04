# Auto-refresh Integration Guide

## Overview

The Politician Trading Tracker uses `streamlit-autorefresh` to provide real-time updates on live dashboard pages without requiring users to manually refresh. This creates a more dynamic, monitoring-focused experience.

## Architecture

### Components

1. **autorefresh_config.py** - Central configuration and utilities
2. **streamlit-autorefresh** - Frontend timer component
3. **Page integrations** - Individual pages with auto-refresh enabled

### How It Works

```
┌─────────────────────────────────────────────┐
│           Browser (Frontend)                │
│  ┌────────────────────────────────────┐    │
│  │  streamlit-autorefresh Component   │    │
│  │  Timer: Every N milliseconds       │    │
│  └──────────────┬─────────────────────┘    │
│                 │                           │
│                 │ Triggers rerun            │
│                 ▼                           │
│  ┌────────────────────────────────────┐    │
│  │   Streamlit App Reruns             │    │
│  │   Fresh data fetched from DB       │    │
│  └────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

## Installation

```bash
uv pip install streamlit-autorefresh
```

Already added to `requirements.txt`:
```
streamlit-autorefresh>=1.0.1
```

## Usage Patterns

### Pattern 1: Simple Auto-refresh (Basic)

Minimal integration with default settings:

```python
from autorefresh_config import setup_autorefresh

# Enable auto-refresh for this page
count = setup_autorefresh(
    page_type="action_logs",
    key="logs_refresh"
)

# Your page content
st.write(f"Page refreshed {count} times")
fetch_and_display_data()
```

### Pattern 2: With User Controls (Recommended)

Give users control over refresh behavior:

```python
from autorefresh_config import add_refresh_controls, setup_autorefresh, show_refresh_indicator

# Add controls in sidebar
enabled, interval, _ = add_refresh_controls(
    page_type="action_logs",
    default_enabled=True
)

# Setup auto-refresh based on user settings
refresh_count = 0
if enabled:
    refresh_count = setup_autorefresh(
        interval=interval,
        key="logs_refresh",
        debounce=True  # Pause during user interaction
    )
    if refresh_count > 0:
        show_refresh_indicator(refresh_count, "action_logs")

# Your page content
fetch_and_display_data()
```

### Pattern 3: Manual Refresh Only

For pages that shouldn't auto-refresh but need manual refresh:

```python
from autorefresh_config import create_manual_refresh_button

# Add manual refresh button in sidebar
if create_manual_refresh_button(use_sidebar=True):
    st.success("Data refreshed!")

# Your page content
fetch_and_display_data()
```

### Pattern 4: Conditional Auto-refresh

Only refresh for certain users or conditions:

```python
from autorefresh_config import setup_autorefresh, RefreshInterval
from paywall_config import check_feature_access

# Only enable auto-refresh for Pro users
if check_feature_access("portfolio_tracking"):
    count = setup_autorefresh(
        interval=RefreshInterval.FAST,
        key="premium_refresh"
    )
else:
    st.info("🔒 Real-time updates available with Pro subscription")
```

## Configuration Reference

### Refresh Intervals

Predefined intervals from `RefreshInterval` class:

| Interval | Value | Use Case |
|----------|-------|----------|
| REALTIME | 2000ms (2s) | Critical monitoring |
| FAST | 5000ms (5s) | Active monitoring |
| MEDIUM | 10000ms (10s) | Regular updates |
| SLOW | 30000ms (30s) | Periodic checks |
| VERY_SLOW | 60000ms (60s) | Infrequent updates |

### Page-Specific Defaults

Default intervals for each page type (configurable in `autorefresh_config.py`):

```python
PAGE_DEFAULTS = {
    "action_logs": RefreshInterval.FAST,         # 5 seconds
    "scheduled_jobs": RefreshInterval.MEDIUM,    # 10 seconds
    "portfolio": RefreshInterval.MEDIUM,         # 10 seconds
    "trading_operations": RefreshInterval.FAST,  # 5 seconds
    "data_collection": RefreshInterval.SLOW,     # 30 seconds
    "trading_signals": RefreshInterval.SLOW,     # 30 seconds
}
```

## API Reference

### `setup_autorefresh()`

Main function to enable auto-refresh on a page.

```python
def setup_autorefresh(
    page_type: Optional[str] = None,
    interval: Optional[int] = None,
    limit: Optional[int] = None,
    debounce: bool = True,
    enabled: bool = True,
    key: Optional[str] = None
) -> int
```

**Parameters:**
- `page_type`: Page type for default interval (e.g., "action_logs")
- `interval`: Custom refresh interval in milliseconds (overrides page_type)
- `limit`: Maximum number of refreshes (None = unlimited)
- `debounce`: Delay refresh during user interactions (recommended: True)
- `enabled`: Whether to enable auto-refresh
- `key`: Unique key for the component (required for state persistence)

**Returns:**
- `int`: Current refresh count (0 if disabled)

### `add_refresh_controls()`

Add user-facing refresh controls to the page.

```python
def add_refresh_controls(
    page_type: str,
    default_enabled: bool = True,
    show_in_sidebar: bool = True
) -> tuple[bool, int, int]
```

**Parameters:**
- `page_type`: Page type for default settings
- `default_enabled`: Whether refresh is enabled by default
- `show_in_sidebar`: Show controls in sidebar (vs. main area)

**Returns:**
- `tuple[bool, int, int]`: (enabled, interval, refresh_count)

### `show_refresh_indicator()`

Display a small indicator showing refresh count.

```python
def show_refresh_indicator(count: int, page_type: str)
```

### `create_manual_refresh_button()`

Create a manual refresh button.

```python
def create_manual_refresh_button(
    label: str = "🔄 Refresh Now",
    key: Optional[str] = None,
    use_sidebar: bool = False
) -> bool
```

## Current Integrations

### 1. Action Logs (8_📋_Action_Logs.py)

**Default:** Enabled, 5-second refresh
**Why:** Real-time monitoring of system actions

```python
enabled, interval, _ = add_refresh_controls("action_logs", default_enabled=True)
if enabled:
    refresh_count = setup_autorefresh(interval=interval, key="action_logs_refresh")
```

### 2. Scheduled Jobs (5_⏰_Scheduled_Jobs.py)

**Default:** Enabled, 10-second refresh
**Why:** Monitor job execution status and next run times

```python
enabled, interval, _ = add_refresh_controls("scheduled_jobs", default_enabled=True)
if enabled:
    refresh_count = setup_autorefresh(interval=interval, key="scheduled_jobs_refresh")
```

### 3. Portfolio (4_📈_Portfolio.py)

**Default:** Disabled, 10-second refresh
**Why:** Real-time portfolio value updates (opt-in due to API costs)

```python
enabled, interval, _ = add_refresh_controls("portfolio", default_enabled=False)
if enabled:
    refresh_count = setup_autorefresh(interval=interval, key="portfolio_refresh")
```

## Best Practices

### ✅ Do

1. **Always use `debounce=True`** - Prevents refresh during form filling
2. **Provide user controls** - Let users enable/disable and adjust interval
3. **Use appropriate intervals** - Don't refresh too frequently
4. **Set unique keys** - Prevents state conflicts
5. **Monitor API costs** - Frequent refreshes = more API calls
6. **Show refresh indicators** - Users should know when data updates

### ❌ Don't

1. **Don't use on heavy pages** - Large data fetches = slow reruns
2. **Don't refresh user input pages** - Forms, settings, etc.
3. **Don't call st_autorefresh multiple times** - One per page only
4. **Don't use very short intervals** - Server load and API rate limits
5. **Don't forget to check if library is installed** - Handle ImportError gracefully

## Performance Considerations

### Server Load

Each refresh triggers a complete page rerun:
- Database queries re-executed
- API calls remade
- All computations rerun

**Mitigation:**
- Use `@st.cache_data` for expensive operations
- Set appropriate TTL on cached data
- Monitor server CPU/memory usage

### API Rate Limits

Auto-refresh can quickly hit API rate limits:

| Service | Rate Limit | Safe Refresh Interval |
|---------|------------|----------------------|
| Alpaca (Data) | 200/min | 10s (6/min) |
| Alpaca (Trading) | 200/min | 10s (6/min) |
| Capitol Trades | Varies | 30s+ |

### Database Load

Frequent queries can impact database performance:
- Use connection pooling
- Add appropriate indexes
- Cache frequently accessed data
- Monitor query performance

## Debugging

### Issue: Auto-refresh not working

**Possible causes:**
1. Library not installed
2. Multiple `st_autorefresh()` calls
3. Missing or duplicate `key` parameter
4. Page errors preventing rerun

**Debug steps:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Check if available
from autorefresh_config import AUTOREFRESH_AVAILABLE
st.write(f"Auto-refresh available: {AUTOREFRESH_AVAILABLE}")

# Check refresh count
count = setup_autorefresh(page_type="test", key="debug_refresh")
st.write(f"Refresh count: {count}")
```

### Issue: Refresh happening too fast/slow

**Fix:** Adjust interval in user controls or page defaults

```python
# In autorefresh_config.py, modify PAGE_DEFAULTS
PAGE_DEFAULTS = {
    "your_page": 15000,  # 15 seconds
}
```

### Issue: Refresh during user interaction

**Fix:** Ensure `debounce=True`

```python
setup_autorefresh(
    interval=5000,
    debounce=True,  # Prevents refresh when user is typing/clicking
    key="refresh"
)
```

## Future Enhancements

### Potential Improvements

1. **Smart Refresh** - Only refresh if data actually changed
   ```python
   # Pseudo-code
   if data_hash_changed():
       st.rerun()
   ```

2. **Conditional Intervals** - Adjust based on activity
   ```python
   # Fast refresh during market hours, slow otherwise
   interval = 5000 if is_market_open() else 60000
   ```

3. **WebSocket Integration** - Replace polling with push updates
   - More efficient
   - True real-time
   - Requires server infrastructure

4. **Refresh Scheduling** - Refresh at specific times
   ```python
   # Refresh at :00, :15, :30, :45 of each hour
   setup_scheduled_refresh(cron="*/15 * * * *")
   ```

## Testing

### Manual Testing

1. Enable auto-refresh on a page
2. Watch for refresh indicator updates
3. Interact with widgets - should pause refresh
4. Disable auto-refresh - should stop

### Automated Testing

```python
def test_autorefresh_config():
    """Test auto-refresh configuration"""
    from autorefresh_config import RefreshInterval, PAGE_DEFAULTS

    # Test intervals
    assert RefreshInterval.FAST == 5000
    assert RefreshInterval.MEDIUM == 10000

    # Test page defaults
    assert "action_logs" in PAGE_DEFAULTS
    assert PAGE_DEFAULTS["action_logs"] == RefreshInterval.FAST
```

## Migration Guide

### Adding Auto-refresh to Existing Pages

1. **Import utilities at top of page:**
   ```python
   from autorefresh_config import add_refresh_controls, setup_autorefresh, show_refresh_indicator
   ```

2. **Add controls after authentication:**
   ```python
   require_authentication()
   show_user_info()

   # Add refresh controls
   enabled, interval, _ = add_refresh_controls("your_page", default_enabled=True)
   ```

3. **Setup auto-refresh:**
   ```python
   refresh_count = 0
   if enabled:
       refresh_count = setup_autorefresh(
           interval=interval,
           key="your_page_refresh",
           debounce=True
       )
       if refresh_count > 0:
           show_refresh_indicator(refresh_count, "your_page")
   ```

4. **Test thoroughly:**
   - Verify data updates
   - Check performance
   - Monitor API usage

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Library not found | Run `uv pip install streamlit-autorefresh` |
| Multiple timers | Only call `st_autorefresh()` once per page |
| Refresh too frequent | Increase interval or use debounce |
| High server load | Reduce refresh frequency or add caching |
| API rate limits | Increase interval or use cached data |
| State reset on refresh | Ensure proper `st.session_state` usage |

## Resources

- [streamlit-autorefresh GitHub](https://github.com/kmcgrady/streamlit-autorefresh)
- [Streamlit Caching Guide](https://docs.streamlit.io/develop/concepts/architecture/caching)
- [Streamlit Session State](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state)
