"""
Data Collection Page - Collect politician trading disclosures
"""

import streamlit as st
import asyncio
from datetime import datetime, timedelta
import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))
if str(parent_dir / "src") not in sys.path:
    sys.path.insert(0, str(parent_dir / "src"))

# Import utilities
try:
    from streamlit_utils import load_all_secrets
except (ImportError, KeyError):
    # Fallback for different import contexts
    import importlib.util
    spec = importlib.util.spec_from_file_location("streamlit_utils", parent_dir / "streamlit_utils.py")
    streamlit_utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(streamlit_utils)
    load_all_secrets = streamlit_utils.load_all_secrets

st.set_page_config(page_title="Data Collection", page_icon="📥", layout="wide")

# Load secrets on page load
load_all_secrets()

st.title("📥 Data Collection")
st.markdown("Collect politician trading disclosures from multiple sources")

# Initialize session state
if "collection_running" not in st.session_state:
    st.session_state.collection_running = False
if "collection_results" not in st.session_state:
    st.session_state.collection_results = None

# Source selection
st.markdown("### Select Data Sources")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**🇺🇸 United States**")
    us_congress = st.checkbox("US Congress (House & Senate)", value=True)
    california = st.checkbox("California State", value=False)
    texas = st.checkbox("Texas State", value=False)
    new_york = st.checkbox("New York State", value=False)

with col2:
    st.markdown("**🇪🇺 European Union**")
    eu_parliament = st.checkbox("EU Parliament", value=False)
    germany = st.checkbox("Germany (Bundestag)", value=False)
    france = st.checkbox("France (National Assembly)", value=False)
    italy = st.checkbox("Italy (Parliament)", value=False)

with col3:
    st.markdown("**🇬🇧 United Kingdom**")
    uk_parliament = st.checkbox("UK Parliament", value=False)
    st.markdown("**📊 Third-Party**")
    quiver = st.checkbox("QuiverQuant", value=False)

# Collection parameters
st.markdown("---")
st.markdown("### Collection Parameters")

col1, col2 = st.columns(2)

with col1:
    lookback_days = st.number_input(
        "Look back period (days)",
        min_value=1,
        max_value=365,
        value=30,
        help="How many days of historical data to collect"
    )

with col2:
    max_retries = st.number_input(
        "Max retries per source",
        min_value=1,
        max_value=10,
        value=3,
        help="Number of retry attempts for failed scrapes"
    )

# Start collection
st.markdown("---")

col1, col2 = st.columns([1, 4])

with col1:
    if st.button("🚀 Start Collection", disabled=st.session_state.collection_running, use_container_width=True):
        st.session_state.collection_running = True
        st.rerun()

with col2:
    if st.session_state.collection_running:
        st.info("📊 Collection in progress... This may take several minutes.")

# Run collection
if st.session_state.collection_running:
    st.markdown("---")
    st.markdown("### 🚀 Collection Progress")

    # Create detailed status containers
    status_container = st.container()
    progress_container = st.container()
    log_container = st.container()
    results_container = st.container()

    with status_container:
        col1, col2, col3 = st.columns(3)
        with col1:
            status_badge = st.empty()
        with col2:
            progress_text = st.empty()
        with col3:
            elapsed_time = st.empty()

    with progress_container:
        progress_bar = st.progress(0)

    with log_container:
        st.markdown("#### 📝 Collection Log")
        log_output = st.empty()

    try:
        import time
        from politician_trading.workflow import PoliticianTradingWorkflow
        from politician_trading.config import SupabaseConfig, WorkflowConfig
        from politician_trading.database.database import SupabaseClient

        start_time = time.time()
        logs = []

        def add_log(message):
            timestamp = time.strftime("%H:%M:%S")
            logs.append(f"[{timestamp}] {message}")
            log_output.code("\n".join(logs[-20:]))  # Show last 20 logs

        add_log("🔧 Initializing workflow...")
        status_badge.info("⏳ Initializing")

        # Create config
        supabase_config = SupabaseConfig.from_env()
        add_log(f"✅ Connected to Supabase: {supabase_config.url[:30]}...")

        workflow_config = WorkflowConfig(
            supabase=supabase_config,
            enable_us_congress=us_congress,
            enable_uk_parliament=uk_parliament,
            enable_eu_parliament=eu_parliament,
            enable_us_states=any([california, texas, new_york]),
            enable_california=california,
        )

        # Log enabled sources
        enabled_sources = []
        if us_congress:
            enabled_sources.append("US Congress")
        if uk_parliament:
            enabled_sources.append("UK Parliament")
        if eu_parliament:
            enabled_sources.append("EU Parliament")
        if california:
            enabled_sources.append("California")
        if texas:
            enabled_sources.append("Texas")
        if new_york:
            enabled_sources.append("New York")

        add_log(f"📊 Enabled sources: {', '.join(enabled_sources) if enabled_sources else 'None'}")

        if not enabled_sources:
            st.warning("⚠️ No sources selected! Please select at least one data source.")
            st.session_state.collection_running = False
            st.stop()

        # Initialize workflow
        workflow = PoliticianTradingWorkflow(workflow_config)
        add_log("✅ Workflow initialized")
        progress_bar.progress(10)

        try:
            status_badge.warning("🔄 Running")
            progress_text.text("Collecting data...")
            add_log("🌐 Starting data collection from selected sources...")
            progress_bar.progress(20)

            # Run collection
            results = asyncio.run(workflow.run_full_collection())

            progress_bar.progress(90)
            add_log("✅ Data collection completed!")
            add_log("📊 Processing results...")

            # Store results
            st.session_state.collection_results = results
            st.session_state.collection_running = False

            progress_bar.progress(100)
            status_badge.success("✅ Complete")
            elapsed = time.time() - start_time
            elapsed_time.text(f"⏱️ {elapsed:.1f}s")
            progress_text.text("Complete!")

            # Display detailed results
            with results_container:
                st.markdown("---")
                st.markdown("### 📊 Collection Results")

                # Summary metrics
                summary = results.get("summary", {})
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        "New Disclosures",
                        summary.get("total_new_disclosures", 0),
                        help="Newly discovered trading disclosures"
                    )
                with col2:
                    st.metric(
                        "Updated Records",
                        summary.get("total_updated_disclosures", 0),
                        help="Previously existing records that were updated"
                    )
                with col3:
                    jobs = results.get("jobs", {})
                    total_errors = sum(len(job.get("errors", [])) for job in jobs.values())
                    st.metric(
                        "Errors",
                        total_errors,
                        delta=f"-{total_errors}" if total_errors > 0 else None,
                        delta_color="inverse"
                    )
                with col4:
                    completed_jobs = sum(1 for job in jobs.values() if job.get("status") == "completed")
                    st.metric(
                        "Completed Jobs",
                        f"{completed_jobs}/{len(jobs)}",
                        help="Successfully completed collection jobs"
                    )

                # Detailed results by job
                st.markdown("#### 📋 Details by Source")

                jobs = results.get("jobs", {})
                if jobs:
                    for job_name, job_data in jobs.items():
                        with st.expander(f"{'✅' if job_data.get('status') == 'completed' else '❌'} {job_name.replace('_', ' ').title()}", expanded=False):
                            col1, col2, col3 = st.columns(3)

                            with col1:
                                st.metric("New", job_data.get("new_disclosures", 0))
                            with col2:
                                st.metric("Updated", job_data.get("updated_disclosures", 0))
                            with col3:
                                st.metric("Errors", len(job_data.get("errors", [])))

                            if job_data.get("errors"):
                                st.markdown("**Errors:**")
                                for error in job_data.get("errors", [])[:5]:  # Show first 5 errors
                                    st.code(error, language="text")
                else:
                    st.info("No job details available")

                add_log(f"🎉 Collection completed successfully in {elapsed:.1f}s")

            st.rerun()

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()

            progress_bar.progress(100)
            status_badge.error("❌ Failed")
            add_log(f"❌ Collection failed: {str(e)}")

            with results_container:
                st.error(f"""
                **Error during collection:**

                {str(e)}
                """)

                with st.expander("📋 Full Error Details"):
                    st.code(error_details, language="python")

            st.session_state.collection_running = False
            st.rerun()

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()

        st.error(f"""
        **Failed to initialize collection:**

        {str(e)}
        """)

        with st.expander("📋 Full Error Details"):
            st.code(error_details, language="python")

        st.session_state.collection_running = False
        st.rerun()

# Display recent disclosures
st.markdown("---")
st.markdown("### Recent Disclosures")

# Add ticker backfill button
col1, col2 = st.columns([3, 1])
with col2:
    if st.button("🔄 Backfill Missing Tickers", help="Extract and populate missing ticker symbols from asset names"):
        with st.spinner("Backfilling tickers..."):
            try:
                from politician_trading.database.database import SupabaseClient
                from politician_trading.config import SupabaseConfig
                from politician_trading.utils.ticker_utils import extract_ticker_from_asset_name

                config = SupabaseConfig.from_env()
                db = SupabaseClient(config)

                # Get disclosures with missing tickers
                response_null = db.client.table("trading_disclosures")\
                    .select("id, asset_name, asset_ticker")\
                    .is_("asset_ticker", "null")\
                    .execute()

                response_empty = db.client.table("trading_disclosures")\
                    .select("id, asset_name, asset_ticker")\
                    .eq("asset_ticker", "")\
                    .execute()

                all_missing = (response_null.data or []) + (response_empty.data or [])

                if not all_missing:
                    st.success("✅ All disclosures already have tickers!")
                else:
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    updated = 0
                    no_ticker = 0

                    for i, disclosure in enumerate(all_missing):
                        progress_bar.progress((i + 1) / len(all_missing))
                        status_text.text(f"Processing {i+1}/{len(all_missing)}...")

                        asset_name = disclosure.get('asset_name', '')
                        if not asset_name:
                            no_ticker += 1
                            continue

                        ticker = extract_ticker_from_asset_name(asset_name)
                        if ticker:
                            db.client.table("trading_disclosures")\
                                .update({"asset_ticker": ticker})\
                                .eq("id", disclosure['id'])\
                                .execute()
                            updated += 1
                        else:
                            no_ticker += 1

                    progress_bar.progress(1.0)
                    status_text.empty()

                    st.success(f"""
                    ✅ Backfill complete!
                    - Updated: {updated}
                    - No ticker found: {no_ticker}
                    """)
                    st.rerun()

            except Exception as e:
                st.error(f"Backfill failed: {str(e)}")

try:
    from politician_trading.database.database import SupabaseClient
    from politician_trading.config import SupabaseConfig

    config = SupabaseConfig.from_env()
    db = SupabaseClient(config)

    # Fetch recent disclosures
    query = db.client.table("trading_disclosures").select("*").order("transaction_date", desc=True).limit(100)
    response = query.execute()

    if response.data:
        df = pd.DataFrame(response.data)

        # Format for display
        display_cols = ["transaction_date", "asset_ticker", "asset_name", "transaction_type", "amount_range_min", "amount_range_max"]
        display_df = df[[col for col in display_cols if col in df.columns]].copy()

        # Format dates
        if "transaction_date" in display_df.columns:
            display_df["transaction_date"] = pd.to_datetime(display_df["transaction_date"]).dt.strftime("%Y-%m-%d")

        # Replace None/empty tickers with "N/A"
        if "asset_ticker" in display_df.columns:
            display_df["asset_ticker"] = display_df["asset_ticker"].fillna("N/A").replace("", "N/A")

        # Rename columns for display
        display_df.columns = ["Date", "Ticker", "Asset", "Type", "Min Amount", "Max Amount"]

        # Show count of missing tickers
        missing_tickers = len([t for t in df["asset_ticker"] if not t or t == ""])
        if missing_tickers > 0:
            st.warning(f"⚠️ {missing_tickers} disclosures are missing ticker symbols. Click 'Backfill Missing Tickers' to fix.")

        st.dataframe(display_df, use_container_width=True)

        # Export option
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name=f"disclosures_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No disclosures found. Run collection to populate data.")

except Exception as e:
    st.warning("Connect to database to view recent disclosures")

# Scheduled collection
st.markdown("---")
st.markdown("### ⏰ Scheduled Collection")

st.info("""
💡 **Tip**: Set up a scheduled cron job to run collection automatically:
```bash
# Daily at 2 AM
0 2 * * * politician-trading collect
```
""")
