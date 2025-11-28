"""
Scheduled Jobs Management Page

Manage in-app scheduled jobs for automated data collection and maintenance.
"""

import streamlit as st
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add project root to path
app_dir = Path(__file__).parent
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))
if str(app_dir / "src") not in sys.path:
    sys.path.insert(0, str(app_dir / "src"))

from politician_trading.utils.logger import create_logger
from politician_trading.utils.action_logger import log_action
from politician_trading.scheduler import get_scheduler
from politician_trading.scheduler.jobs import data_collection_job, ticker_backfill_job

# Import utilities
try:
    from streamlit_utils import load_all_secrets
except (ImportError, KeyError):
    import importlib.util
    spec = importlib.util.spec_from_file_location("streamlit_utils", app_dir / "streamlit_utils.py")
    streamlit_utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(streamlit_utils)
    load_all_secrets = streamlit_utils.load_all_secrets

logger = create_logger("scheduled_jobs_page")

st.set_page_config(
    page_title="Scheduled Jobs",
    page_icon="⏰",
    layout="wide",
)

# Load secrets
load_all_secrets()

# Require authentication
from auth_utils import require_authentication, show_user_info
require_authentication()
show_user_info()

# Page header
st.title("⏰ Scheduled Jobs Management")
st.markdown("Manage automated data collection and maintenance jobs that run in the background.")

# Add auto-refresh controls
from autorefresh_config import add_refresh_controls, setup_autorefresh, show_refresh_indicator

# Add refresh controls in sidebar
enabled, interval, _ = add_refresh_controls("scheduled_jobs", default_enabled=True)

# Setup auto-refresh if enabled
refresh_count = 0
if enabled:
    refresh_count = setup_autorefresh(
        interval=interval,
        key="scheduled_jobs_refresh",
        debounce=True
    )
    if refresh_count > 0:
        show_refresh_indicator(refresh_count, "scheduled_jobs")

# Get scheduler instance
try:
    scheduler = get_scheduler()
    logger.info("Scheduled Jobs page loaded", metadata={
        "scheduler_running": scheduler.is_running()
    })
except Exception as e:
    st.error(f"Failed to initialize scheduler: {e}")
    logger.error("Failed to initialize scheduler", error=e)
    st.stop()

# Check if scheduler is running
if not scheduler.is_running():
    st.error("⚠️ Scheduler is not running. Jobs will not execute.")
    if st.button("Restart Scheduler", key="restart_scheduler"):
        st.rerun()
else:
    st.success("✅ Scheduler is running")

st.markdown("---")

# Display all scheduled jobs from database
st.markdown("### 📋 Scheduled Jobs")
st.info("💡 **Note:** Jobs are defined in the database and managed programmatically. To modify jobs, update the database directly or use the initialization scripts.")

jobs = scheduler.get_jobs()

if not jobs:
    st.warning("No scheduled jobs found in database.")
else:
    for job in jobs:
        status_icon = "⏸️ DISABLED" if job['is_paused'] else "✅ ENABLED"
        with st.expander(f"{status_icon} | {job['name']}", expanded=True):
            col1, col2 = st.columns([1, 1])

            with col1:
                st.markdown(f"**Job ID:** `{job['id']}`")
                st.markdown(f"**Description:** {job['description'] or 'No description'}")
                st.markdown(f"**Type:** {job['type'].title()}")
                st.markdown(f"**Schedule:** {job['schedule']}")

            with col2:
                if job['next_run']:
                    next_run_str = job['next_run'].strftime("%Y-%m-%d %H:%M:%S UTC")
                    time_until = job['next_run'] - datetime.now(job['next_run'].tzinfo)
                    hours_until = time_until.total_seconds() / 3600

                    if hours_until < 0:
                        st.markdown(f"**Next Run:** Running now...")
                    elif hours_until < 1:
                        minutes = int(time_until.total_seconds() / 60)
                        st.markdown(f"**Next Run:** {next_run_str} (in {minutes} minutes)")
                    elif hours_until < 24:
                        st.markdown(f"**Next Run:** {next_run_str} (in {hours_until:.1f} hours)")
                    else:
                        days = int(hours_until / 24)
                        st.markdown(f"**Next Run:** {next_run_str} (in {days} days)")
                else:
                    st.markdown(f"**Next Run:** Not scheduled (job disabled)")

                if job['last_execution']:
                    last_run = job['last_execution']['timestamp']
                    status = job['last_execution']['status']
                    status_emoji = "✅" if status == "success" else "❌"
                    duration = job['last_execution'].get('duration_seconds')

                    last_run_str = last_run.strftime("%Y-%m-%d %H:%M:%S")
                    duration_str = f" ({duration:.2f}s)" if duration else ""
                    st.markdown(f"**Last Run:** {last_run_str} {status_emoji}{duration_str}")

                    if status == "error" and job['last_execution'].get('error'):
                        st.error(f"Error: {job['last_execution']['error']}")

                    # Show last few log lines
                    logs = job['last_execution'].get('logs', [])
                    if logs:
                        with st.expander("📋 View Last Execution Logs", expanded=False):
                            # Show last 20 lines
                            recent_logs = logs[-20:] if len(logs) > 20 else logs
                            st.code("\n".join(recent_logs), language="log")
                else:
                    st.markdown("**Last Run:** Never")

st.markdown("---")

# Job Execution History
st.markdown("### 📊 Recent Job Executions")

history = scheduler.job_history.get_history(limit=20)

if not history:
    st.info("No job executions found.")
else:
    # Display recent executions
    for idx, execution in enumerate(history):
        timestamp = execution["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        status = execution["status"]
        status_emoji = "✅" if status == "success" else "❌"
        duration = execution.get("duration_seconds")

        job_name = execution["job_id"]
        # Try to get friendly name
        for job in jobs:
            if job["id"] == execution["job_id"]:
                job_name = job["name"]
                break

        # Format title with duration
        title = f"{status_emoji} {job_name} - {timestamp}"
        if duration is not None:
            title += f" ({duration:.2f}s)"

        with st.expander(title, expanded=False):
            col1, col2 = st.columns([1, 3])

            with col1:
                st.markdown(f"**Status:** {status.upper()}")
                st.markdown(f"**Job ID:** `{execution['job_id']}`")
                if duration:
                    st.markdown(f"**Duration:** {duration:.2f}s")

            with col2:
                if execution.get("error"):
                    st.error(f"**Error:** {execution['error']}")

            # Show logs if available
            logs = execution.get("logs", [])
            if logs:
                st.markdown("---")
                st.markdown("### 📋 Execution Logs")

                # Add log viewer with syntax highlighting
                log_text = "\n".join(logs)
                st.code(log_text, language="log", line_numbers=True)

                # Option to download logs
                st.download_button(
                    label="📥 Download Logs",
                    data=log_text,
                    file_name=f"{execution['job_id']}_{timestamp.replace(' ', '_').replace(':', '-')}.log",
                    mime="text/plain",
                    key=f"download_logs_{idx}"
                )
            else:
                st.info("No logs captured for this execution")

st.markdown("---")

# Stats summary
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Jobs", len(jobs))
with col2:
    enabled_jobs = len([j for j in jobs if not j['is_paused']])
    st.metric("Enabled Jobs", enabled_jobs)
with col3:
    disabled_jobs = len([j for j in jobs if j['is_paused']])
    st.metric("Disabled Jobs", disabled_jobs)

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem 0;">
    Database-Managed Scheduled Jobs |
    <a href="/docs/scheduled-jobs.md" target="_blank">Documentation</a>
</div>
""", unsafe_allow_html=True)
