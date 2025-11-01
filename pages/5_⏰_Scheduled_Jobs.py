"""
Scheduled Jobs Management Page

Manage in-app scheduled jobs for automated data collection and maintenance.
"""

import streamlit as st
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add project root to path
app_dir = Path(__file__).parent.parent
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))
if str(app_dir / "src") not in sys.path:
    sys.path.insert(0, str(app_dir / "src"))

from politician_trading.utils.logger import create_logger
from politician_trading.scheduler import get_scheduler
from politician_trading.scheduler.jobs import data_collection_job, ticker_backfill_job

logger = create_logger("scheduled_jobs_page")

st.set_page_config(
    page_title="Scheduled Jobs",
    page_icon="⏰",
    layout="wide",
)

# Page header
st.title("⏰ Scheduled Jobs Management")
st.markdown("Manage automated data collection and maintenance jobs that run in the background.")

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
    if st.button("Restart Scheduler"):
        st.rerun()
else:
    st.success("✅ Scheduler is running")

st.markdown("---")

# Tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["📋 Active Jobs", "➕ Add New Job", "📊 Job History", "⚙️ Settings"])

# Tab 1: Active Jobs
with tab1:
    st.markdown("### Active Scheduled Jobs")

    jobs = scheduler.get_jobs()

    if not jobs:
        st.info("No scheduled jobs configured. Use the 'Add New Job' tab to create one.")
    else:
        for job in jobs:
            with st.expander(f"{'⏸️' if job['is_paused'] else '▶️'} {job['name']}", expanded=True):
                col1, col2, col3 = st.columns([2, 2, 1])

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
                        st.markdown("**Next Run:** Paused")

                    if job['last_execution']:
                        last_run = job['last_execution']['timestamp']
                        status = job['last_execution']['status']
                        status_emoji = "✅" if status == "success" else "❌"

                        last_run_str = last_run.strftime("%Y-%m-%d %H:%M:%S")
                        st.markdown(f"**Last Run:** {last_run_str} {status_emoji}")

                        if status == "error" and job['last_execution'].get('error'):
                            st.error(f"Error: {job['last_execution']['error']}")
                    else:
                        st.markdown("**Last Run:** Never")

                with col3:
                    # Control buttons
                    if job['is_paused']:
                        if st.button("▶️ Resume", key=f"resume_{job['id']}"):
                            if scheduler.resume_job(job['id']):
                                st.success(f"Resumed job: {job['name']}")
                                st.rerun()
                            else:
                                st.error("Failed to resume job")
                    else:
                        if st.button("⏸️ Pause", key=f"pause_{job['id']}"):
                            if scheduler.pause_job(job['id']):
                                st.success(f"Paused job: {job['name']}")
                                st.rerun()
                            else:
                                st.error("Failed to pause job")

                    if st.button("▶️ Run Now", key=f"run_{job['id']}"):
                        if scheduler.run_job_now(job['id']):
                            st.success(f"Triggered job: {job['name']}")
                            st.info("Job has been queued to run immediately. Check logs for execution status.")
                        else:
                            st.error("Failed to trigger job")

                    if st.button("🗑️ Remove", key=f"remove_{job['id']}"):
                        if scheduler.remove_job(job['id']):
                            st.success(f"Removed job: {job['name']}")
                            st.rerun()
                        else:
                            st.error("Failed to remove job")

# Tab 2: Add New Job
with tab2:
    st.markdown("### Add New Scheduled Job")

    job_type = st.radio("Select job type:", ["Data Collection", "Ticker Backfill", "Custom"])

    if job_type in ["Data Collection", "Ticker Backfill"]:
        # Predefined jobs
        st.markdown("#### Configure Schedule")

        schedule_type = st.radio("Schedule type:", ["Interval", "Cron (Time-based)"])

        job_id = None
        job_name = None
        job_description = None
        job_func = None

        if job_type == "Data Collection":
            job_id = "data_collection"
            job_name = "Automated Data Collection"
            job_description = "Collect politician trading disclosures from configured sources"
            job_func = data_collection_job

            # Data source configuration
            st.markdown("#### Data Sources")
            col1, col2 = st.columns(2)
            with col1:
                us_congress = st.checkbox("US Congress", value=True, key="new_us_congress")
                uk_parliament = st.checkbox("UK Parliament", value=False, key="new_uk_parliament")
            with col2:
                eu_parliament = st.checkbox("EU Parliament", value=False, key="new_eu_parliament")
                california = st.checkbox("California", value=False, key="new_california")

            # Store in session state for job to access
            if "scheduled_us_congress" not in st.session_state:
                st.session_state.scheduled_us_congress = True
            if "scheduled_eu_parliament" not in st.session_state:
                st.session_state.scheduled_eu_parliament = False
            if "scheduled_uk_parliament" not in st.session_state:
                st.session_state.scheduled_uk_parliament = False
            if "scheduled_california" not in st.session_state:
                st.session_state.scheduled_california = False

        else:  # Ticker Backfill
            job_id = "ticker_backfill"
            job_name = "Ticker Backfill"
            job_description = "Find and update missing ticker symbols in disclosures"
            job_func = ticker_backfill_job

        if schedule_type == "Interval":
            st.markdown("#### Interval Settings")
            col1, col2, col3 = st.columns(3)
            with col1:
                hours = st.number_input("Hours", min_value=0, max_value=168, value=24 if job_type == "Data Collection" else 168)
            with col2:
                minutes = st.number_input("Minutes", min_value=0, max_value=59, value=0)
            with col3:
                seconds = st.number_input("Seconds", min_value=0, max_value=59, value=0)

            if hours == 0 and minutes == 0 and seconds == 0:
                st.warning("⚠️ Please specify a non-zero interval")
            else:
                if st.button("➕ Add Interval Job", type="primary"):
                    # Update session state if data collection
                    if job_type == "Data Collection":
                        st.session_state.scheduled_us_congress = us_congress
                        st.session_state.scheduled_eu_parliament = eu_parliament
                        st.session_state.scheduled_uk_parliament = uk_parliament
                        st.session_state.scheduled_california = california

                    success = scheduler.add_interval_job(
                        func=job_func,
                        job_id=job_id,
                        name=job_name,
                        hours=hours,
                        minutes=minutes,
                        seconds=seconds,
                        description=job_description,
                        replace_existing=True,
                    )
                    if success:
                        st.success(f"✅ Added job: {job_name}")
                        logger.info(f"Added interval job via UI: {job_name}", metadata={
                            "job_id": job_id,
                            "hours": hours,
                            "minutes": minutes,
                            "seconds": seconds
                        })
                        st.rerun()
                    else:
                        st.error("Failed to add job. Check logs for details.")

        else:  # Cron
            st.markdown("#### Cron Settings")

            col1, col2 = st.columns(2)
            with col1:
                hour = st.number_input("Hour (0-23)", min_value=0, max_value=23, value=2)
                minute = st.number_input("Minute (0-59)", min_value=0, max_value=59, value=0)
            with col2:
                day_of_week = st.selectbox(
                    "Day of Week (optional)",
                    ["Every day", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                )

            day_of_week_map = {
                "Monday": "mon",
                "Tuesday": "tue",
                "Wednesday": "wed",
                "Thursday": "thu",
                "Friday": "fri",
                "Saturday": "sat",
                "Sunday": "sun",
            }

            dow = day_of_week_map.get(day_of_week)

            schedule_preview = f"Daily at {hour:02d}:{minute:02d} UTC"
            if dow:
                schedule_preview = f"Every {day_of_week} at {hour:02d}:{minute:02d} UTC"

            st.info(f"📅 Schedule: {schedule_preview}")

            if st.button("➕ Add Cron Job", type="primary"):
                # Update session state if data collection
                if job_type == "Data Collection":
                    st.session_state.scheduled_us_congress = us_congress
                    st.session_state.scheduled_eu_parliament = eu_parliament
                    st.session_state.scheduled_uk_parliament = uk_parliament
                    st.session_state.scheduled_california = california

                success = scheduler.add_cron_job(
                    func=job_func,
                    job_id=job_id,
                    name=job_name,
                    hour=hour,
                    minute=minute,
                    day_of_week=dow,
                    description=job_description,
                    replace_existing=True,
                )
                if success:
                    st.success(f"✅ Added job: {job_name}")
                    logger.info(f"Added cron job via UI: {job_name}", metadata={
                        "job_id": job_id,
                        "schedule": schedule_preview
                    })
                    st.rerun()
                else:
                    st.error("Failed to add job. Check logs for details.")

    else:  # Custom job
        st.info("Custom job creation coming soon. For now, use the predefined Data Collection and Ticker Backfill jobs.")

# Tab 3: Job History
with tab3:
    st.markdown("### Job Execution History")

    history = scheduler.job_history.get_history()

    if not history:
        st.info("No job executions yet.")
    else:
        # Filter options
        col1, col2 = st.columns([1, 3])
        with col1:
            filter_job = st.selectbox("Filter by job:", ["All"] + [job["id"] for job in jobs])

        # Apply filter
        if filter_job != "All":
            history = [h for h in history if h["job_id"] == filter_job]

        # Display history
        for execution in history[:50]:  # Show last 50
            timestamp = execution["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            status = execution["status"]
            status_emoji = "✅" if status == "success" else "❌"

            job_name = execution["job_id"]
            # Try to get friendly name
            for job in jobs:
                if job["id"] == execution["job_id"]:
                    job_name = job["name"]
                    break

            col1, col2, col3 = st.columns([2, 1, 3])
            with col1:
                st.text(timestamp)
            with col2:
                st.text(f"{status_emoji} {status.upper()}")
            with col3:
                if execution.get("error"):
                    st.error(f"{job_name}: {execution['error']}")
                else:
                    st.text(job_name)

# Tab 4: Settings
with tab4:
    st.markdown("### Scheduler Settings")

    st.markdown("#### Scheduler Status")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Scheduler State", "Running ✅" if scheduler.is_running() else "Stopped ❌")
        st.metric("Active Jobs", len([j for j in jobs if not j['is_paused']]))
    with col2:
        st.metric("Paused Jobs", len([j for j in jobs if j['is_paused']]))
        st.metric("Total Jobs", len(jobs))

    st.markdown("---")

    st.markdown("#### Quick Actions")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔄 Refresh Page"):
            st.rerun()

    with col2:
        if st.button("📄 View Logs"):
            st.info("Check logs/latest.log for detailed execution logs")
            st.code("tail -f logs/latest.log | jq 'select(.logger | contains(\"scheduled\"))'", language="bash")

    with col3:
        if st.button("❌ Clear All Jobs"):
            if st.warning("This will remove ALL scheduled jobs. Are you sure?"):
                for job in jobs:
                    scheduler.remove_job(job['id'])
                st.success("All jobs removed")
                st.rerun()

    st.markdown("---")

    st.markdown("#### About In-App Scheduling")
    st.markdown("""
    **How it works:**
    - Jobs run in the background using APScheduler
    - The scheduler starts when the Streamlit app starts
    - Jobs continue running as long as the app is running
    - Job history is tracked and displayed above

    **Important notes:**
    - Jobs will NOT run if the Streamlit app is stopped
    - For production deployments, ensure the app stays running (e.g., on Streamlit Cloud, Render, etc.)
    - For critical jobs, consider also using system cron as a backup

    **For cloud deployments:**
    - This in-app scheduling works on Streamlit Cloud, Heroku, Render, and other platforms
    - No system access or cron needed
    - Jobs run in the same process as the Streamlit app
    """)

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem 0;">
    Scheduled Jobs powered by APScheduler |
    <a href="/docs/scheduled-jobs.md" target="_blank">Documentation</a>
</div>
""", unsafe_allow_html=True)
