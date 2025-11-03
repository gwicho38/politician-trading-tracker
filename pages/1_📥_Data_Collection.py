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

# Import logger
from politician_trading.utils.logger import create_logger
logger = create_logger("data_collection_page")

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

# Require authentication
from auth_utils import require_authentication
require_authentication()

logger.info("Data Collection page loaded")

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
    if st.button("🚀 Start Collection", disabled=st.session_state.collection_running, width="stretch"):
        logger.info("Start Collection button clicked", metadata={
            "us_congress": us_congress,
            "uk_parliament": uk_parliament,
            "eu_parliament": eu_parliament,
            "california": california,
            "texas": texas,
            "new_york": new_york,
            "lookback_days": lookback_days,
            "max_retries": max_retries
        })
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
        logger.info("Initializing data collection workflow")

        # Create config
        supabase_config = SupabaseConfig.from_env()
        add_log(f"✅ Connected to Supabase: {supabase_config.url[:30]}...")
        logger.debug("Supabase connection configured", metadata={
            "url": supabase_config.url
        })

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
        logger.info("Data sources configured", metadata={
            "enabled_sources": enabled_sources,
            "source_count": len(enabled_sources)
        })

        if not enabled_sources:
            logger.warn("No data sources selected")
            st.warning("⚠️ No sources selected! Please select at least one data source.")
            st.session_state.collection_running = False
            st.stop()

        # Initialize workflow
        workflow = PoliticianTradingWorkflow(workflow_config)
        add_log("✅ Workflow initialized")
        logger.info("Workflow initialized successfully")
        progress_bar.progress(10)

        try:
            status_badge.warning("🔄 Running")
            progress_text.text("Collecting data...")
            add_log("🌐 Starting data collection from selected sources...")
            progress_bar.progress(20)

            # Run collection
            logger.info("Starting full data collection")
            results = asyncio.run(workflow.run_full_collection())

            # Log comprehensive results
            logger.info("Data collection completed", metadata={
                "results": results,
                "summary": results.get("summary", {}),
                "job_count": len(results.get("jobs", {}))
            })

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
                logger.info("Collection summary", metadata={
                    "new_disclosures": summary.get("total_new_disclosures", 0),
                    "updated_disclosures": summary.get("total_updated_disclosures", 0),
                    "duration_seconds": elapsed
                })

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
                    logger.debug(f"Processing {len(jobs)} job results")
                    for job_name, job_data in jobs.items():
                        logger.info(f"Job result: {job_name}", metadata={
                            "job_name": job_name,
                            "status": job_data.get("status"),
                            "new_disclosures": job_data.get("new_disclosures", 0),
                            "updated_disclosures": job_data.get("updated_disclosures", 0),
                            "error_count": len(job_data.get("errors", []))
                        })

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

            logger.error("Data collection failed", error=e, metadata={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": error_details
            })

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
        logger.info("Backfill Missing Tickers button clicked")
        with st.spinner("Backfilling tickers..."):
            try:
                from politician_trading.database.database import SupabaseClient
                from politician_trading.config import SupabaseConfig
                from politician_trading.utils.ticker_utils import extract_ticker_from_asset_name

                config = SupabaseConfig.from_env()
                db = SupabaseClient(config)
                logger.debug("Connected to database for ticker backfill")

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

                logger.info("Ticker backfill: found missing tickers", metadata={
                    "missing_count": len(all_missing)
                })

                if not all_missing:
                    logger.info("Ticker backfill: no missing tickers found")
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

                    logger.info("Ticker backfill completed", metadata={
                        "total_processed": len(all_missing),
                        "updated": updated,
                        "no_ticker_found": no_ticker
                    })

                    st.success(f"""
                    ✅ Backfill complete!
                    - Updated: {updated}
                    - No ticker found: {no_ticker}
                    """)
                    st.rerun()

            except Exception as e:
                logger.error("Ticker backfill failed", error=e)
                st.error(f"Backfill failed: {str(e)}")

try:
    from politician_trading.database.database import SupabaseClient
    from politician_trading.config import SupabaseConfig

    logger.debug("Loading recent disclosures")
    config = SupabaseConfig.from_env()
    db = SupabaseClient(config)

    # Fetch recent disclosures with politician information
    # Using a join to get politician names
    query = db.client.table("trading_disclosures").select(
        "*, politicians(first_name, last_name, full_name, role, party, state_or_country)"
    ).order("transaction_date", desc=True).limit(100)
    response = query.execute()

    logger.info("Recent disclosures loaded", metadata={
        "count": len(response.data) if response.data else 0
    })

    if response.data:
        df = pd.DataFrame(response.data)

        # Extract politician information from nested object
        if "politicians" in df.columns:
            def extract_name(x):
                if not isinstance(x, dict) or not x:
                    return "Unknown"
                # Try full_name first, then construct from first/last name
                full_name = x.get("full_name")
                if full_name:
                    return full_name
                first = x.get("first_name", "")
                last = x.get("last_name", "")
                if first or last:
                    return f"{first} {last}".strip()
                return "Unknown"

            df["politician_name"] = df["politicians"].apply(extract_name)
            df["politician_party"] = df["politicians"].apply(
                lambda x: x.get("party", "N/A") if isinstance(x, dict) and x else "N/A"
            )
            df["politician_state"] = df["politicians"].apply(
                lambda x: x.get("state_or_country", "N/A") if isinstance(x, dict) and x else "N/A"
            )

            # Count how many have politician info
            has_politician = df["politician_name"].apply(lambda x: x != "Unknown").sum()

            # Log sample of politician data for debugging
            if len(df) > 0:
                sample_politician = df["politicians"].iloc[0] if isinstance(df["politicians"].iloc[0], dict) else None
                logger.debug("Sample politician data", metadata={
                    "sample": sample_politician,
                    "keys": list(sample_politician.keys()) if sample_politician else []
                })

            logger.info("Extracted politician information", metadata={
                "total_disclosures": len(df),
                "with_politician": int(has_politician),
                "without_politician": int(len(df) - has_politician)
            })
        else:
            df["politician_name"] = "Unknown"
            df["politician_party"] = "N/A"
            df["politician_state"] = "N/A"
            logger.warn("No politician information in query results")

        # Format for display - include more useful columns
        display_cols = [
            "transaction_date",
            "disclosure_date",
            "politician_name",
            "politician_party",
            "politician_state",
            "asset_ticker",
            "asset_name",
            "asset_type",
            "transaction_type",
            "amount_range_min",
            "amount_range_max",
            "status",
            "source_url"
        ]
        display_df = df[[col for col in display_cols if col in df.columns]].copy()

        # Format dates
        if "transaction_date" in display_df.columns:
            display_df["transaction_date"] = pd.to_datetime(display_df["transaction_date"]).dt.strftime("%Y-%m-%d")

        if "disclosure_date" in display_df.columns:
            display_df["disclosure_date"] = pd.to_datetime(display_df["disclosure_date"]).dt.strftime("%Y-%m-%d")

        # Replace None/empty tickers with "N/A"
        if "asset_ticker" in display_df.columns:
            display_df["asset_ticker"] = display_df["asset_ticker"].fillna("N/A").replace("", "N/A")

        # Format asset type
        if "asset_type" in display_df.columns:
            display_df["asset_type"] = display_df["asset_type"].fillna("Unknown").replace("", "Unknown")

        # Truncate source URL for display
        if "source_url" in display_df.columns:
            display_df["source_url"] = display_df["source_url"].apply(lambda x: (str(x)[:50] + "...") if x and len(str(x)) > 50 else (x if x else "N/A"))

        # Rename columns for display
        column_rename = {
            "transaction_date": "Trans. Date",
            "disclosure_date": "Disc. Date",
            "politician_name": "Politician",
            "politician_party": "Party",
            "politician_state": "State/Country",
            "asset_ticker": "Ticker",
            "asset_name": "Asset",
            "asset_type": "Asset Type",
            "transaction_type": "Type",
            "amount_range_min": "Min Amount",
            "amount_range_max": "Max Amount",
            "status": "Status",
            "source_url": "Source"
        }

        display_df.columns = [column_rename.get(col, col) for col in display_df.columns]

        logger.debug("Displaying disclosures table", metadata={
            "row_count": len(display_df),
            "columns": list(display_df.columns)
        })

        # Show count of missing tickers
        missing_tickers = len([t for t in df["asset_ticker"] if not t or t == ""])
        if missing_tickers > 0:
            st.warning(f"⚠️ {missing_tickers} disclosures are missing ticker symbols. Click 'Backfill Missing Tickers' to fix.")
            logger.info("Missing tickers detected", metadata={
                "missing_count": missing_tickers,
                "total_count": len(df)
            })

        st.dataframe(display_df, width="stretch")

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
