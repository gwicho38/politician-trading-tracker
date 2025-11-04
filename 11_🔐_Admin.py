"""
Admin Dashboard - Restricted to administrator only
Shows Supabase connection status, analytics, and system diagnostics
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
import os
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import utilities
try:
    from streamlit_utils import load_all_secrets
except (ImportError, KeyError):
    import importlib.util
    spec = importlib.util.spec_from_file_location("streamlit_utils", Path(__file__).parent / "streamlit_utils.py")
    streamlit_utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(streamlit_utils)
    load_all_secrets = streamlit_utils.load_all_secrets

# Page configuration
st.set_page_config(
    page_title="Admin Dashboard",
    page_icon="🔐",
    layout="wide"
)

# Load secrets
load_all_secrets()

# Require authentication first
from auth_utils_enhanced import require_authentication

user_email = require_authentication()

# Admin email whitelist
ADMIN_EMAILS = ["luis.e.fernandezdelavara@gmail.com"]

# Check if user is admin
if user_email not in ADMIN_EMAILS:
    st.error("🚫 Access Denied")
    st.warning("This page is restricted to administrators only.")
    st.stop()

# Admin access granted
st.success(f"✅ Admin Access Granted: {user_email}")

# Add auto-refresh
from autorefresh_config import add_refresh_controls, setup_autorefresh

enabled, interval, _ = add_refresh_controls("admin", default_enabled=False)
if enabled:
    setup_autorefresh(interval=interval, key="admin_refresh")

# Page header
st.title("🔐 Admin Dashboard")
st.caption(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.divider()

# Tabs for different admin sections
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Analytics",
    "🗄️ Supabase",
    "⚙️ System Info",
    "👥 Users",
    "📝 Logs"
])

# Tab 1: Analytics
with tab1:
    st.subheader("📊 Application Analytics")

    try:
        import streamlit_analytics

        st.info("📈 Analytics tracking is available. Add `?analytics=on` to URL to view detailed analytics.")

        # Show analytics controls
        col1, col2 = st.columns(2)

        with col1:
            if st.button("📊 Start Tracking"):
                streamlit_analytics.start_tracking()
                st.success("Analytics tracking started")

        with col2:
            if st.button("🛑 Stop Tracking"):
                streamlit_analytics.stop_tracking()
                st.warning("Analytics tracking stopped")

        # Check for analytics JSON file
        analytics_file = Path("analytics.json")
        if analytics_file.exists():
            st.markdown("### Stored Analytics Data")
            try:
                with open(analytics_file, 'r') as f:
                    analytics_data = json.load(f)
                st.json(analytics_data)

                # Summary statistics
                if isinstance(analytics_data, dict):
                    st.markdown("### Summary")
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        total_views = analytics_data.get("pageviews", {}).get("total", 0)
                        st.metric("Total Pageviews", total_views)

                    with col2:
                        total_interactions = sum(analytics_data.get("widgets", {}).values()) if "widgets" in analytics_data else 0
                        st.metric("Total Interactions", total_interactions)

                    with col3:
                        unique_widgets = len(analytics_data.get("widgets", {}))
                        st.metric("Unique Widgets Used", unique_widgets)
            except Exception as e:
                st.error(f"Error reading analytics file: {e}")
        else:
            st.info("No analytics data stored yet. Use `streamlit_analytics.track(save_to_json='analytics.json')` in app.py")

    except ImportError:
        st.warning("⚠️ streamlit-analytics not installed. Install with: `uv pip install streamlit-analytics`")

        st.markdown("""
        ### Setup Instructions

        1. Install the package:
        ```bash
        uv pip install streamlit-analytics
        ```

        2. Add tracking to app.py:
        ```python
        import streamlit_analytics

        with streamlit_analytics.track(save_to_json="analytics.json"):
            # your app code
            page.run()
        ```

        3. View analytics by adding `?analytics=on` to URL
        """)

# Tab 2: Supabase Connection
with tab2:
    st.subheader("🗄️ Supabase Connection Status")

    try:
        from politician_trading.database.supabase_client import get_supabase_client

        with st.spinner("Connecting to Supabase..."):
            client = get_supabase_client()

        st.success("✅ Successfully connected to Supabase")

        # Supabase configuration
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Configuration")
            st.code(f"""
URL: {supabase_url}
Key: {supabase_key[:10]}...{supabase_key[-4:] if supabase_key else 'Not set'}
            """)

        with col2:
            st.markdown("### Connection Details")
            st.info("Connected via Supabase Python client")

        # Test database access
        st.markdown("### Database Tables")

        with st.expander("🔍 Test Table Access", expanded=True):
            # Try to query different tables
            tables_to_test = [
                "politician_trades",
                "action_logs",
                "scheduled_jobs",
                "user_sessions"
            ]

            for table in tables_to_test:
                try:
                    result = client.table(table).select("*", count="exact").limit(1).execute()
                    count = result.count if hasattr(result, 'count') else 'Unknown'
                    st.success(f"✅ `{table}`: Accessible ({count} total rows)")
                except Exception as e:
                    st.error(f"❌ `{table}`: {str(e)[:100]}")

        # Recent activity
        st.markdown("### Recent Database Activity")

        try:
            recent_logs = client.table("action_logs") \
                .select("*") \
                .order("created_at", desc=True) \
                .limit(5) \
                .execute()

            if recent_logs.data:
                import pandas as pd
                df = pd.DataFrame(recent_logs.data)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No recent action logs")
        except Exception as e:
            st.error(f"Error fetching recent logs: {e}")

    except Exception as e:
        st.error(f"❌ Failed to connect to Supabase: {e}")

        st.markdown("""
        ### Troubleshooting

        1. Check environment variables:
           - `SUPABASE_URL`
           - `SUPABASE_KEY`

        2. Verify .streamlit/secrets.toml configuration

        3. Test connection manually:
        ```python
        from supabase import create_client
        client = create_client(url, key)
        ```
        """)

# Tab 3: System Info
with tab3:
    st.subheader("⚙️ System Information")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Python Environment")
        import platform
        import sys

        st.code(f"""
Python Version: {sys.version}
Platform: {platform.platform()}
Processor: {platform.processor()}
        """)

        st.markdown("### Streamlit Info")
        st.code(f"""
Streamlit Version: {st.__version__}
        """)

    with col2:
        st.markdown("### Environment Variables")

        env_vars = [
            "SUPABASE_URL",
            "SUPABASE_KEY",
            "ALPACA_API_KEY",
            "ALPACA_SECRET_KEY",
            "GOOGLE_CLIENT_ID"
        ]

        for var in env_vars:
            value = os.getenv(var)
            if value:
                # Mask sensitive values
                masked = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
                st.success(f"✅ {var}: {masked}")
            else:
                st.error(f"❌ {var}: Not set")

    # Disk usage
    st.markdown("### Disk Usage")
    import shutil

    try:
        total, used, free = shutil.disk_usage("/")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total", f"{total // (2**30)} GB")
        with col2:
            st.metric("Used", f"{used // (2**30)} GB")
        with col3:
            st.metric("Free", f"{free // (2**30)} GB")
    except Exception as e:
        st.error(f"Error reading disk usage: {e}")

# Tab 4: Users
with tab4:
    st.subheader("👥 User Management")

    try:
        from politician_trading.database.supabase_client import get_supabase_client

        client = get_supabase_client()

        # Check if user_sessions table exists
        try:
            sessions = client.table("user_sessions") \
                .select("*") \
                .order("last_activity", desc=True) \
                .execute()

            if sessions.data:
                import pandas as pd
                df = pd.DataFrame(sessions.data)

                st.markdown("### Active Sessions")
                st.dataframe(df, use_container_width=True)

                # Summary stats
                col1, col2, col3 = st.columns(3)

                with col1:
                    unique_users = df['user_email'].nunique() if 'user_email' in df.columns else 0
                    st.metric("Unique Users", unique_users)

                with col2:
                    total_sessions = len(df)
                    st.metric("Total Sessions", total_sessions)

                with col3:
                    # Count active sessions (last activity < 1 hour ago)
                    if 'last_activity' in df.columns:
                        df['last_activity'] = pd.to_datetime(df['last_activity'])
                        active = df[df['last_activity'] > datetime.now() - pd.Timedelta(hours=1)]
                        st.metric("Active (1h)", len(active))
            else:
                st.info("No user sessions found")

        except Exception as e:
            st.warning(f"user_sessions table not accessible: {e}")

    except Exception as e:
        st.error(f"Error accessing user data: {e}")

# Tab 5: Logs
with tab5:
    st.subheader("📝 Application Logs")

    # Check for log files
    log_dir = Path("logs")
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))

        if log_files:
            selected_log = st.selectbox(
                "Select log file",
                options=log_files,
                format_func=lambda x: x.name
            )

            lines_to_show = st.slider("Lines to show", 10, 1000, 100)

            if selected_log:
                try:
                    with open(selected_log, 'r') as f:
                        lines = f.readlines()
                        # Show last N lines
                        recent_lines = lines[-lines_to_show:]
                        st.code(''.join(recent_lines), language="log")
                except Exception as e:
                    st.error(f"Error reading log file: {e}")
        else:
            st.info("No log files found in logs/ directory")
    else:
        st.info("logs/ directory does not exist")

    # Show Python logs if available
    st.markdown("### Recent Python Logs")

    try:
        import logging
        st.code("""
To enable logging, add to your page:

from politician_trading.utils.logger import create_logger
logger = create_logger(__name__)

logger.info("Your log message")
        """)
    except Exception as e:
        st.error(f"Error: {e}")

st.divider()

# Footer
st.caption(f"🔐 Admin Dashboard | Restricted Access | User: {user_email}")
