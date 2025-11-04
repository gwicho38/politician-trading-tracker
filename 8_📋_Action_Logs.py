"""
Action Logs Page - View and analyze system action logs
"""

import streamlit as st
import streamlit_antd_components as sac
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))
if str(parent_dir / "src") not in sys.path:
    sys.path.insert(0, str(parent_dir / "src"))

# Import logger
from politician_trading.utils.logger import create_logger
from politician_trading.utils.action_logger import get_action_logger

logger = create_logger("action_logs_page")

# Import utilities
try:
    from streamlit_utils import load_all_secrets
except (ImportError, KeyError):
    import importlib.util
    spec = importlib.util.spec_from_file_location("streamlit_utils", parent_dir / "streamlit_utils.py")
    streamlit_utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(streamlit_utils)
    load_all_secrets = streamlit_utils.load_all_secrets

st.set_page_config(page_title="Action Logs", page_icon="📋", layout="wide")

# Load secrets on page load
load_all_secrets()

# Require authentication
from auth_utils import require_authentication, show_user_info
require_authentication()
show_user_info()

logger.info("Action Logs page loaded")

st.title("📋 Action Logs")
st.markdown("Monitor and analyze all system actions and their results")

# Get action logger instance
action_logger = get_action_logger()

# Tabs for different views
tab = sac.tabs([
    sac.TabsItem(label='Recent Actions', icon='list-ul'),
    sac.TabsItem(label='Statistics', icon='bar-chart'),
    sac.TabsItem(label='Failed Actions', icon='exclamation-triangle'),
], align='center', return_index=False, size='large')

if tab == 'Recent Actions':
    sac.divider(label='Recent System Actions', align='center', color='blue')

    # Filters
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        action_type_filter = st.selectbox(
            "Action Type",
            ["All", "data_collection_start", "ticker_backfill", "job_execution",
             "job_pause", "job_resume", "job_manual_run", "job_remove"],
            index=0
        )

    with col2:
        status_filter = st.selectbox(
            "Status",
            ["All", "initiated", "in_progress", "completed", "failed", "cancelled"],
            index=0
        )

    with col3:
        source_filter = st.selectbox(
            "Source",
            ["All", "ui_button", "scheduled_job", "api", "recovery", "system"],
            index=0
        )

    with col4:
        limit = st.number_input("Limit", min_value=10, max_value=1000, value=100, step=10)

    # Fetch actions
    try:
        actions = action_logger.get_recent_actions(
            action_type=None if action_type_filter == "All" else action_type_filter,
            status=None if status_filter == "All" else status_filter,
            source=None if source_filter == "All" else source_filter,
            limit=limit
        )

        if actions:
            logger.info(f"Loaded {len(actions)} action logs")

            # Display summary metrics
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                total_actions = len(actions)
                st.metric("Total Actions", total_actions)

            with col2:
                completed = len([a for a in actions if a.get('status') == 'completed'])
                st.metric("Completed", completed, delta=f"{(completed/total_actions*100):.1f}%" if total_actions > 0 else "0%")

            with col3:
                failed = len([a for a in actions if a.get('status') == 'failed'])
                st.metric("Failed", failed, delta=f"-{(failed/total_actions*100):.1f}%" if failed > 0 and total_actions > 0 else "0%", delta_color="inverse")

            with col4:
                avg_duration = sum([a.get('duration_seconds', 0) or 0 for a in actions if a.get('duration_seconds')]) / len([a for a in actions if a.get('duration_seconds')])
                st.metric("Avg Duration", f"{avg_duration:.2f}s" if avg_duration > 0 else "N/A")

            st.markdown("---")

            # Convert to DataFrame for display
            df = pd.DataFrame(actions)

            # Format timestamp columns
            if 'action_timestamp' in df.columns:
                df['action_timestamp'] = pd.to_datetime(df['action_timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')

            # Select columns to display
            display_columns = [
                'action_timestamp', 'action_type', 'action_name', 'status',
                'source', 'user_id', 'duration_seconds', 'result_message', 'error_message'
            ]
            display_columns = [col for col in display_columns if col in df.columns]

            # Display actions in an expandable format
            st.markdown("### Action History")

            for idx, action in enumerate(actions):
                status_icon = {
                    'completed': '✅',
                    'failed': '❌',
                    'in_progress': '🔄',
                    'initiated': '🚀',
                    'cancelled': '⏹️'
                }.get(action.get('status', ''), '❓')

                timestamp = action.get('action_timestamp', 'Unknown')
                if isinstance(timestamp, str):
                    try:
                        timestamp = pd.to_datetime(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass

                action_name = action.get('action_name') or action.get('action_type', 'Unknown Action')
                duration = action.get('duration_seconds')
                duration_str = f" - {duration:.2f}s" if duration else ""

                with st.expander(f"{status_icon} {timestamp} - {action_name}{duration_str}", expanded=False):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown(f"**Action Type:** `{action.get('action_type', 'N/A')}`")
                        st.markdown(f"**Status:** `{action.get('status', 'N/A')}`")
                        st.markdown(f"**Source:** `{action.get('source', 'N/A')}`")
                        st.markdown(f"**User:** `{action.get('user_id', 'N/A')}`")

                    with col2:
                        if action.get('job_id'):
                            st.markdown(f"**Job ID:** `{action.get('job_id')}`")
                        if duration:
                            st.markdown(f"**Duration:** {duration:.3f}s")
                        st.markdown(f"**ID:** `{action.get('id', 'N/A')}`")

                    if action.get('result_message'):
                        st.success(f"**Result:** {action.get('result_message')}")

                    if action.get('error_message'):
                        st.error(f"**Error:** {action.get('error_message')}")

                    if action.get('action_details'):
                        st.markdown("**Details:**")
                        st.json(action.get('action_details'))

        else:
            st.info("No actions found matching the selected filters.")

    except Exception as e:
        logger.error(f"Failed to load action logs: {e}")
        st.error(f"Failed to load action logs: {str(e)}")

elif tab == 'Statistics':
    sac.divider(label='Action Statistics', align='center', color='green')

    try:
        # Get summary statistics
        summary_data = action_logger.get_action_summary(days=7)

        if summary_data and 'summary' in summary_data:
            summary = summary_data['summary']

            if summary:
                st.markdown("### Last 7 Days Summary")

                # Convert to DataFrame
                df = pd.DataFrame(summary)

                # Display key metrics
                col1, col2, col3 = st.columns(3)

                with col1:
                    total_actions = df['total_count'].sum() if 'total_count' in df.columns else 0
                    st.metric("Total Actions", int(total_actions))

                with col2:
                    completed_actions = df['completed_count'].sum() if 'completed_count' in df.columns else 0
                    success_rate = (completed_actions / total_actions * 100) if total_actions > 0 else 0
                    st.metric("Success Rate", f"{success_rate:.1f}%")

                with col3:
                    failed_actions = df['failed_count'].sum() if 'failed_count' in df.columns else 0
                    st.metric("Failed Actions", int(failed_actions))

                st.markdown("---")

                # Group by action type
                if 'action_type' in df.columns and 'total_count' in df.columns:
                    st.markdown("### Actions by Type")

                    type_summary = df.groupby('action_type').agg({
                        'total_count': 'sum',
                        'completed_count': 'sum',
                        'failed_count': 'sum',
                        'avg_duration_seconds': 'mean'
                    }).reset_index()

                    type_summary['success_rate'] = (
                        type_summary['completed_count'] / type_summary['total_count'] * 100
                    ).round(1)

                    st.dataframe(
                        type_summary,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "action_type": "Action Type",
                            "total_count": st.column_config.NumberColumn("Total", format="%d"),
                            "completed_count": st.column_config.NumberColumn("Completed", format="%d"),
                            "failed_count": st.column_config.NumberColumn("Failed", format="%d"),
                            "avg_duration_seconds": st.column_config.NumberColumn("Avg Duration (s)", format="%.2f"),
                            "success_rate": st.column_config.NumberColumn("Success Rate (%)", format="%.1f"),
                        }
                    )

                # Group by source
                if 'source' in df.columns:
                    st.markdown("### Actions by Source")

                    source_summary = df.groupby('source').agg({
                        'total_count': 'sum',
                        'completed_count': 'sum',
                        'failed_count': 'sum'
                    }).reset_index()

                    source_summary['success_rate'] = (
                        source_summary['completed_count'] / source_summary['total_count'] * 100
                    ).round(1)

                    st.dataframe(
                        source_summary,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "source": "Source",
                            "total_count": st.column_config.NumberColumn("Total", format="%d"),
                            "completed_count": st.column_config.NumberColumn("Completed", format="%d"),
                            "failed_count": st.column_config.NumberColumn("Failed", format="%d"),
                            "success_rate": st.column_config.NumberColumn("Success Rate (%)", format="%.1f"),
                        }
                    )

            else:
                st.info("No statistics available for the last 7 days.")
        else:
            st.info("No statistics available.")

    except Exception as e:
        logger.error(f"Failed to load statistics: {e}")
        st.error(f"Failed to load statistics: {str(e)}")

elif tab == 'Failed Actions':
    sac.divider(label='Failed Actions', align='center', color='red')

    try:
        # Fetch only failed actions
        failed_actions = action_logger.get_recent_actions(
            status="failed",
            limit=100
        )

        if failed_actions:
            st.markdown(f"### {len(failed_actions)} Failed Actions")

            # Group by action type
            df = pd.DataFrame(failed_actions)
            if 'action_type' in df.columns:
                type_counts = df['action_type'].value_counts()

                col1, col2, col3 = st.columns(3)
                for idx, (action_type, count) in enumerate(type_counts.head(3).items()):
                    with [col1, col2, col3][idx]:
                        st.metric(action_type.replace('_', ' ').title(), count)

            st.markdown("---")

            # Display failed actions
            for action in failed_actions:
                timestamp = action.get('action_timestamp', 'Unknown')
                if isinstance(timestamp, str):
                    try:
                        timestamp = pd.to_datetime(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass

                action_name = action.get('action_name') or action.get('action_type', 'Unknown Action')

                with st.expander(f"❌ {timestamp} - {action_name}", expanded=False):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown(f"**Action Type:** `{action.get('action_type', 'N/A')}`")
                        st.markdown(f"**Source:** `{action.get('source', 'N/A')}`")
                        st.markdown(f"**User:** `{action.get('user_id', 'N/A')}`")

                    with col2:
                        if action.get('job_id'):
                            st.markdown(f"**Job ID:** `{action.get('job_id')}`")
                        duration = action.get('duration_seconds')
                        if duration:
                            st.markdown(f"**Duration:** {duration:.3f}s")

                    st.error(f"**Error:** {action.get('error_message', 'No error message available')}")

                    if action.get('action_details'):
                        st.markdown("**Details:**")
                        st.json(action.get('action_details'))

        else:
            st.success("🎉 No failed actions found!")

    except Exception as e:
        logger.error(f"Failed to load failed actions: {e}")
        st.error(f"Failed to load failed actions: {str(e)}")
