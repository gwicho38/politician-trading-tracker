"""
Auto-refresh configuration for live dashboard pages
Provides consistent refresh intervals across different page types
"""
import streamlit as st
from typing import Optional, Literal

# Try to import streamlit-autorefresh
try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except ImportError:
    AUTOREFRESH_AVAILABLE = False
    st_autorefresh = None


# Predefined refresh intervals (in milliseconds)
class RefreshInterval:
    """Standard refresh intervals for different page types"""
    REALTIME = 2000      # 2 seconds - Real-time monitoring
    FAST = 5000          # 5 seconds - Fast updates
    MEDIUM = 10000       # 10 seconds - Medium updates
    SLOW = 30000         # 30 seconds - Slow updates
    VERY_SLOW = 60000    # 1 minute - Very slow updates
    CUSTOM = None        # Custom interval


# Page-specific default intervals
PAGE_DEFAULTS = {
    "action_logs": RefreshInterval.FAST,         # 5 seconds
    "scheduled_jobs": RefreshInterval.MEDIUM,    # 10 seconds
    "portfolio": RefreshInterval.MEDIUM,         # 10 seconds
    "trading_operations": RefreshInterval.FAST,  # 5 seconds
    "data_collection": RefreshInterval.SLOW,     # 30 seconds
    "trading_signals": RefreshInterval.SLOW,     # 30 seconds
}


def setup_autorefresh(
    page_type: Optional[str] = None,
    interval: Optional[int] = None,
    limit: Optional[int] = None,
    debounce: bool = True,
    enabled: bool = True,
    key: Optional[str] = None
) -> int:
    """
    Setup auto-refresh for a page with consistent configuration

    Args:
        page_type: Page type for default interval (e.g., "action_logs")
        interval: Custom refresh interval in milliseconds (overrides page_type)
        limit: Maximum number of refreshes (None = unlimited)
        debounce: Delay refresh during user interactions
        enabled: Whether to enable auto-refresh
        key: Unique key for the autorefresh component

    Returns:
        int: Current refresh count (0 if disabled or unavailable)

    Usage:
        # Use page-specific default
        count = setup_autorefresh(page_type="action_logs", key="logs_refresh")

        # Use custom interval
        count = setup_autorefresh(interval=15000, key="custom_refresh")

        # Disable auto-refresh
        count = setup_autorefresh(enabled=False)
    """
    if not AUTOREFRESH_AVAILABLE:
        # Show info message only once per session
        if not st.session_state.get("autorefresh_warning_shown", False):
            st.sidebar.info(
                "📊 Auto-refresh is installing...\n\n"
                "Package is in requirements.txt.\n"
                "On Streamlit Cloud: Settings → Reboot app"
            )
            st.session_state.autorefresh_warning_shown = True
        return 0

    if not enabled:
        return 0

    # Determine interval
    if interval is None:
        if page_type and page_type in PAGE_DEFAULTS:
            interval = PAGE_DEFAULTS[page_type]
        else:
            interval = RefreshInterval.MEDIUM  # Default to 10 seconds

    # Generate key if not provided
    if key is None:
        key = f"autorefresh_{page_type or 'default'}"

    # Call st_autorefresh
    try:
        count = st_autorefresh(
            interval=interval,
            limit=limit,
            debounce=debounce,
            key=key
        )
        return count
    except Exception as e:
        st.error(f"Auto-refresh error: {e}")
        return 0


def add_refresh_controls(
    page_type: str,
    default_enabled: bool = True,
    show_in_sidebar: bool = True
) -> tuple[bool, int, int]:
    """
    Add refresh control widgets to page (sidebar or main)

    Args:
        page_type: Page type for default settings
        default_enabled: Default enabled state
        show_in_sidebar: Show controls in sidebar

    Returns:
        tuple[bool, int, int]: (enabled, interval, refresh_count)

    Usage:
        enabled, interval, count = add_refresh_controls("action_logs")
        if enabled:
            count = setup_autorefresh(
                page_type="action_logs",
                interval=interval,
                key="logs_refresh"
            )
    """
    container = st.sidebar if show_in_sidebar else st

    with container:
        with st.expander("🔄 Auto-refresh Settings", expanded=False):
            # Enable/disable toggle
            enabled = st.toggle(
                "Enable auto-refresh",
                value=default_enabled,
                key=f"refresh_enabled_{page_type}",
                help="Automatically refresh page data at regular intervals"
            )

            # Interval selector
            interval_options = {
                "Real-time (2s)": RefreshInterval.REALTIME,
                "Fast (5s)": RefreshInterval.FAST,
                "Medium (10s)": RefreshInterval.MEDIUM,
                "Slow (30s)": RefreshInterval.SLOW,
                "Very slow (1m)": RefreshInterval.VERY_SLOW,
            }

            # Get default interval for this page type
            default_interval = PAGE_DEFAULTS.get(page_type, RefreshInterval.MEDIUM)

            # Find the label for the default interval
            default_label = next(
                (label for label, val in interval_options.items() if val == default_interval),
                "Medium (10s)"
            )

            selected_label = st.selectbox(
                "Refresh interval",
                options=list(interval_options.keys()),
                index=list(interval_options.keys()).index(default_label),
                key=f"refresh_interval_{page_type}",
                disabled=not enabled
            )

            interval = interval_options[selected_label]

            # Show refresh count if available
            if enabled and st.session_state.get(f"refresh_count_{page_type}"):
                count = st.session_state[f"refresh_count_{page_type}"]
                st.caption(f"Refreshed {count} times")
            else:
                count = 0

    return enabled, interval, count


def show_refresh_indicator(count: int, page_type: str):
    """
    Show a small refresh indicator in the corner

    Args:
        count: Current refresh count
        page_type: Page type for session state key
    """
    if count > 0:
        # Store count in session state
        st.session_state[f"refresh_count_{page_type}"] = count

        # Show indicator
        st.caption(f"🔄 Auto-refreshed {count} times")


def create_manual_refresh_button(
    label: str = "🔄 Refresh Now",
    key: Optional[str] = None,
    use_sidebar: bool = False
) -> bool:
    """
    Create a manual refresh button

    Args:
        label: Button label
        key: Unique button key
        use_sidebar: Show in sidebar

    Returns:
        bool: True if button was clicked
    """
    container = st.sidebar if use_sidebar else st

    if container.button(label, key=key, type="secondary"):
        st.rerun()
        return True

    return False


# Example usage documentation
if __name__ == "__main__":
    st.title("Auto-refresh Configuration Examples")

    st.markdown("""
    ## Method 1: Simple Auto-refresh

    ```python
    from autorefresh_config import setup_autorefresh

    # Auto-refresh every 5 seconds
    count = setup_autorefresh(page_type="action_logs", key="logs_refresh")
    st.write(f"Page refreshed {count} times")
    ```

    ## Method 2: With User Controls

    ```python
    from autorefresh_config import add_refresh_controls, setup_autorefresh

    # Add controls in sidebar
    enabled, interval, _ = add_refresh_controls("action_logs")

    # Setup refresh with user settings
    if enabled:
        count = setup_autorefresh(
            interval=interval,
            key="logs_refresh"
        )
    ```

    ## Method 3: Manual Refresh Only

    ```python
    from autorefresh_config import create_manual_refresh_button

    # Add manual refresh button
    if create_manual_refresh_button(use_sidebar=True):
        st.success("Page refreshed!")
    ```

    ## Method 4: Conditional Refresh

    ```python
    from autorefresh_config import setup_autorefresh, RefreshInterval

    # Only refresh if user is subscribed
    if st.session_state.get("user_subscribed"):
        count = setup_autorefresh(
            interval=RefreshInterval.FAST,
            key="premium_refresh"
        )
    ```
    """)
