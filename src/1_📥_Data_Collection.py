"""
Data Collection Page - Collect politician trading disclosures
"""

import streamlit as st
import asyncio
from datetime import datetime
import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))
if str(parent_dir / "src") not in sys.path:
    sys.path.insert(0, str(parent_dir / "src"))

# Import logger and action logger
from politician_trading.utils.logger import create_logger
from politician_trading.utils.action_logger import start_action, complete_action, fail_action
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

# Optional authentication - allow read-only browsing without login
from auth_utils import optional_authentication, is_authenticated
optional_authentication()

logger.info("Data Collection page loaded")

st.title("📥 Data Collection")
st.markdown("Collect and view politician trading disclosures")
# Force redeploy - single page layout with sections

# Initialize session state
if "collection_running" not in st.session_state:
    st.session_state.collection_running = False
if "collection_results" not in st.session_state:
    st.session_state.collection_results = None
if "collection_logs" not in st.session_state:
    st.session_state.collection_logs = []
if "collection_error" not in st.session_state:
    st.session_state.collection_error = None

# ============================================================================
# SECTION 1: DATABASE STATUS
# ============================================================================
st.markdown("## 📊 Database Status")

# Show status of data sources
st.success("""
✅ **8,485 actionable trades** with stock tickers from:
- **7,524 US Senate disclosures** (official Senate EFD)
- **961 congressional trades** (QuiverQuant aggregator)
- **126 politicians tracked** (Senators like Marjorie Taylor Greene, Sheldon Whitehouse, etc.)

💡 **Recent**: Marjorie Taylor Greene (PANW, BX, CVX, IBIT), Sheldon Whitehouse (PGR), David Taylor (T, AAPL)
""")

# ============================================================================
# SECTION 2: RUN NEW COLLECTION
# ============================================================================
st.markdown("---")
st.markdown("## 🚀 Run New Collection")

# Source selection
st.markdown("**🇺🇸 Data Sources**")
us_congress = st.checkbox("US Congress (Senate)", value=True, help="Collect new disclosures from Senate EFD + QuiverQuant")

# Commented out - not currently working
# california = st.checkbox("California State", value=False)
# texas = st.checkbox("Texas State", value=False)
# new_york = st.checkbox("New York State", value=False)
california = False
texas = False
new_york = False
eu_parliament = False
germany = False
france = False
italy = False
uk_parliament = False
quiver = False

# Collection parameters
st.markdown("**⚙️ Collection Parameters**")

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

# Start collection button - requires authentication
col1, col2 = st.columns([1, 4])

with col1:
    # Check if user is authenticated before showing collection button
    if not is_authenticated():
        st.button("🚀 Start Collection", disabled=True, use_container_width=True, help="Login required to run collection")
        st.caption("🔒 Login to run collection")
    elif st.button("🚀 Start Collection", disabled=st.session_state.collection_running, use_container_width=True):
            # Clear previous logs and errors
            st.session_state.collection_logs = []
            st.session_state.collection_error = None
            st.session_state.collection_results = None

            # Log action start
            user_id = st.session_state.get("user_email", "unknown")
            action_id = start_action(
                action_type="data_collection_start",
                action_name="Manual Data Collection",
                source="ui_button",
                user_id=user_id,
                action_details={
                    "us_congress": us_congress,
                    "uk_parliament": uk_parliament,
                    "eu_parliament": eu_parliament,
                    "california": california,
                    "texas": texas,
                    "new_york": new_york,
                    "lookback_days": lookback_days,
                    "max_retries": max_retries
                }
            )
            st.session_state.action_id = action_id

            logger.info("Start Collection button clicked", metadata={
                "action_id": action_id,
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

# ============================================================================
# SECTION: DISPLAY PERSISTENT LOGS AND ERRORS
# ============================================================================
# Show logs from last collection (persists after rerun)
if st.session_state.collection_logs and not st.session_state.collection_running:
    st.markdown("---")
    st.markdown("### 📝 Last Collection Log")

    with st.expander("📋 View Full Log", expanded=st.session_state.collection_error is not None):
        st.code("\n".join(st.session_state.collection_logs), language="text")

        # Show download button for logs
        log_text = "\n".join(st.session_state.collection_logs)
        st.download_button(
            label="📥 Download Log",
            data=log_text,
            file_name=f"collection_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )

# Show error from last collection if it exists
if st.session_state.collection_error and not st.session_state.collection_running:
    error_info = st.session_state.collection_error

    st.error(f"""
    **❌ Last Collection Failed**

    **Error Type:** `{error_info['type']}`

    **Error Message:** {error_info['message']}
    """)

    with st.expander("📋 Full Error Traceback", expanded=True):
        st.code(error_info['traceback'], language="python")

    # Add link to action logs
    action_id = error_info.get('action_id')
    if action_id:
        st.info(f"""
        🔍 **View complete error logs:**

        Go to **[📋 Action Logs](/8_📋_Action_Logs)** page and filter by:
        - Action ID: `{action_id}`
        - Status: `failed`
        """)

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
            from politician_trading.config import SupabaseConfig, WorkflowConfig, ScrapingConfig
            from politician_trading.database.database import SupabaseClient

            start_time = time.time()

            def add_log(message):
                timestamp = time.strftime("%H:%M:%S")
                log_entry = f"[{timestamp}] {message}"
                st.session_state.collection_logs.append(log_entry)
                log_output.code("\n".join(st.session_state.collection_logs[-30:]))  # Show last 30 logs

            add_log("🔧 Initializing workflow...")
            status_badge.info("⏳ Initializing")
            logger.info("Initializing data collection workflow")

            # Create config
            supabase_config = SupabaseConfig.from_env()
            add_log(f"✅ Connected to Supabase: {supabase_config.url[:30]}...")
            logger.debug("Supabase connection configured", metadata={
                "url": supabase_config.url
            })

            # Create scraping config with enabled sources
            scraping_config = ScrapingConfig(
                enable_us_federal=us_congress,
                enable_eu_parliament=eu_parliament,
                enable_us_states=any([california, texas, new_york]),
            )

            workflow_config = WorkflowConfig(
                supabase=supabase_config,
                scraping=scraping_config
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
                logger.warning("No data sources selected")
                st.warning("⚠️ No sources selected! Please select at least one data source.")
                st.session_state.collection_running = False
                st.stop()

            # Set up a custom logging handler to capture workflow logs
            import logging
            class StreamlitLogHandler(logging.Handler):
                def __init__(self, log_callback):
                    super().__init__()
                    self.log_callback = log_callback

                def emit(self, record):
                    try:
                        # Format the message
                        msg = self.format(record)
                        # Add to Streamlit logs
                        self.log_callback(msg)
                    except Exception:
                        pass

            # Create handler and attach to workflow logger
            streamlit_handler = StreamlitLogHandler(add_log)
            streamlit_handler.setLevel(logging.INFO)
            workflow_logger = logging.getLogger("politician_trading.workflow")
            workflow_logger.addHandler(streamlit_handler)

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

                # Complete action logging
                action_id = st.session_state.get("action_id")
                if action_id:
                    summary = results.get("summary", {})
                    complete_action(
                        action_id=action_id,
                        result_message=f"Collected {summary.get('total_new_disclosures', 0)} new disclosures and updated {summary.get('total_updated_disclosures', 0)} records",
                        action_details={
                            "new_disclosures": summary.get("total_new_disclosures", 0),
                            "updated_disclosures": summary.get("total_updated_disclosures", 0),
                            "jobs_completed": len([j for j in results.get("jobs", {}).values() if j.get("status") == "completed"]),
                            "total_jobs": len(results.get("jobs", {}))
                        }
                    )

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

                    # Add link to action logs
                    st.markdown("---")
                    st.markdown("#### 📋 View Detailed Logs")

                    action_id = st.session_state.get("action_id")
                    if action_id:
                        st.info(f"""
                        💡 **View complete logs for this collection:**

                        Go to **[📋 Action Logs](/8_📋_Action_Logs)** page and filter by:
                        - Action ID: `{action_id}`
                        - Action Type: `data_collection_start`
                        - Time: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`
                        """)
                    else:
                        st.info("""
                        💡 **View complete logs for all collections:**

                        Go to **[📋 Action Logs](/8_📋_Action_Logs)** page to see detailed logs for all data collection runs.
                        """)

                # Clean up logging handler
                workflow_logger.removeHandler(streamlit_handler)

                st.rerun()

            except Exception as e:
                import traceback
                error_details = traceback.format_exc()

                logger.error("Data collection failed", error=e, metadata={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": error_details
                })

                # Store error in session state BEFORE rerun
                st.session_state.collection_error = {
                    "message": str(e),
                    "type": type(e).__name__,
                    "traceback": error_details,
                    "action_id": st.session_state.get("action_id")
                }

                # Fail action logging
                action_id = st.session_state.get("action_id")
                if action_id:
                    fail_action(
                        action_id=action_id,
                        error_message=str(e),
                        action_details={
                            "error_type": type(e).__name__,
                            "traceback_preview": error_details[:500]
                        }
                    )

                progress_bar.progress(100)
                status_badge.error("❌ Failed")
                add_log(f"❌ Collection failed: {str(e)}")
                add_log(f"📋 Error type: {type(e).__name__}")
                add_log("📋 Full traceback saved to logs")

                st.session_state.collection_running = False

                # Clean up logging handler
                workflow_logger.removeHandler(streamlit_handler)

                st.rerun()

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()

            logger.error("Failed to initialize collection", error=e, metadata={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": error_details
            })

            # Store error in session state BEFORE rerun
            st.session_state.collection_error = {
                "message": str(e),
                "type": type(e).__name__,
                "traceback": error_details,
                "action_id": st.session_state.get("action_id")
            }

            # Log the error
            timestamp = time.strftime("%H:%M:%S")
            st.session_state.collection_logs.append(f"[{timestamp}] ❌ Initialization failed: {str(e)}")
            st.session_state.collection_logs.append(f"[{timestamp}] 📋 Error type: {type(e).__name__}")

            st.session_state.collection_running = False
            st.rerun()

# ============================================================================
# SECTION 3: VIEW RECENT DISCLOSURES
# ============================================================================
st.markdown("---")
st.markdown("## 📊 Recent Disclosures")

# Add ticker backfill button - requires authentication
col1, col2 = st.columns([3, 1])
with col2:
    # Check if user is authenticated for backfill operation
    if not is_authenticated():
        st.button("🔄 Backfill Tickers", disabled=True, help="Login required")
    elif st.button("🔄 Backfill Missing Tickers", help="Extract and populate missing ticker symbols from asset names"):
        # Start action logging
        user_id = st.session_state.get("user_email", "unknown")
        backfill_action_id = start_action(
            action_type="ticker_backfill",
            action_name="Backfill Missing Tickers",
            source="ui_button",
            user_id=user_id
        )

        logger.info("Backfill Missing Tickers button clicked", metadata={"action_id": backfill_action_id})
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

                    # Complete action logging
                    if backfill_action_id:
                        complete_action(
                            action_id=backfill_action_id,
                            result_message=f"Backfilled {updated} tickers, {no_ticker} not found",
                            action_details={
                                "total_processed": len(all_missing),
                                "updated": updated,
                                "no_ticker_found": no_ticker
                            }
                        )

                    st.success(f"""
                    ✅ Backfill complete!
                    - Updated: {updated}
                    - No ticker found: {no_ticker}
                    """)
                    st.rerun()

            except Exception as e:
                logger.error("Ticker backfill failed", error=e)

                # Fail action logging
                if backfill_action_id:
                    fail_action(
                        action_id=backfill_action_id,
                        error_message=str(e)
                    )

                st.error(f"Backfill failed: {str(e)}")

try:
    from politician_trading.database.database import SupabaseClient
    from politician_trading.config import SupabaseConfig

    logger.debug("Loading recent disclosures")
    config = SupabaseConfig.from_env()
    db = SupabaseClient(config)

    # Filter options row
    st.markdown("#### Filter Options")
    filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 2])

    with filter_col1:
        # Filter by ticker - default to True to prioritize showing actionable disclosures
        show_ticker_only = st.checkbox(
            "🎯 Show only actionable stocks (with tickers)",
            value=True,
            help="Focus on the individual stocks that have ticker symbols - these generate trading signals."
        )

    with filter_col2:
        # Filing type filter - P = PTR (stock trades), A = Annual, etc.
        filing_type_options = {
            "All Types": None,
            "P - Periodic Transaction Report (PTR)": "P",
            "A - Annual Financial Disclosure": "A",
            "O - Original/Initial Report": "O",
            "T - Termination Report": "T",
            "N - New Member Report": "N",
        }
        selected_filing_type = st.selectbox(
            "📄 Filing Type",
            options=list(filing_type_options.keys()),
            index=0,
            help="Filter by disclosure filing type. PTR (P) contains stock trades reported within 45 days."
        )
        filing_type_filter = filing_type_options[selected_filing_type]

    with filter_col3:
        # Source filter
        source_options = ["All Sources", "us_house", "us_senate", "quiverquant"]
        selected_source = st.selectbox(
            "🏛️ Source",
            options=source_options,
            index=0,
            help="Filter by data source"
        )

    # Add pagination controls
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        page_size = st.selectbox(
            "Disclosures per page",
            options=[100, 500, 1000, 5000],
            index=0,
            help="Number of disclosures to display"
        )
    with col2:
        # Build count query with all filters applied
        def build_filtered_query(base_query):
            """Apply all filters to a query."""
            q = base_query
            if show_ticker_only:
                q = q.neq("asset_ticker", "").not_.is_("asset_ticker", "null")
            if filing_type_filter:
                # Filter by filing_type in raw_data JSONB
                q = q.eq("raw_data->>filing_type", filing_type_filter)
            if selected_source != "All Sources":
                # Filter by source in raw_data JSONB
                q = q.eq("raw_data->>source", selected_source)
            return q

        # Get total count for pagination with filters applied
        count_query = db.client.table("trading_disclosures").select("id", count="exact")
        count_query = build_filtered_query(count_query)
        count_response = count_query.execute()
        total_count = count_response.count if hasattr(count_response, 'count') else 0
        max_pages = (total_count // page_size) + (1 if total_count % page_size > 0 else 0)

        page_number = st.number_input(
            "Page number",
            min_value=1,
            max_value=max(1, max_pages),
            value=1,
            help=f"Total {total_count:,} disclosures across {max_pages:,} pages"
        )
    with col3:
        st.metric("Filtered", f"{total_count:,}")

    # Calculate offset
    offset = (page_number - 1) * page_size

    # Fetch recent disclosures with politician information
    # Using a join to get politician names
    query = db.client.table("trading_disclosures").select(
        "*, politicians(first_name, last_name, full_name, role, party, state_or_country)"
    )

    # Apply all filters at database level
    query = build_filtered_query(query)

    query = query.order("transaction_date", desc=True).limit(page_size).offset(offset)
    response = query.execute()

    logger.info("Recent disclosures loaded", metadata={
        "count": len(response.data) if response.data else 0
    })

    if response.data:
        df = pd.DataFrame(response.data)

        # Debug: Log raw column names and first row
        logger.debug("DataFrame created from response", metadata={
            "columns": list(df.columns),
            "row_count": len(df),
            "first_row_keys": list(response.data[0].keys()) if response.data else []
        })

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
            logger.warning("No politician information in query results")

        # Extract filing type and source from raw_data JSONB
        if "raw_data" in df.columns:
            def extract_filing_type(raw):
                if isinstance(raw, dict):
                    return raw.get("filing_type", "")
                return ""

            def extract_source(raw):
                if isinstance(raw, dict):
                    return raw.get("source", "")
                return ""

            df["filing_type"] = df["raw_data"].apply(extract_filing_type)
            df["source"] = df["raw_data"].apply(extract_source)
        else:
            df["filing_type"] = ""
            df["source"] = ""

        # Debug: Log sample of raw data
        if len(df) > 0:
            sample = df.iloc[0]
            logger.debug("Sample disclosure data", metadata={
                "asset_ticker": sample.get("asset_ticker"),
                "asset_name": sample.get("asset_name"),
                "asset_type": sample.get("asset_type"),
                "filing_type": sample.get("filing_type"),
                "source": sample.get("source"),
                "columns": list(df.columns)
            })

        # Format for display - include more useful columns
        display_cols = [
            "created_at",
            "transaction_date",
            "disclosure_date",
            "politician_name",
            "politician_party",
            "politician_state",
            "filing_type",
            "source",
            "asset_ticker",
            "asset_name",
            "asset_type",
            "transaction_type",
            "amount_range_min",
            "amount_range_max",
            "status",
            "source_url",
            "source_document_id"
        ]
        display_df = df[[col for col in display_cols if col in df.columns]].copy()

        # Create a clickable PDF link column if source_url exists
        if "source_url" in display_df.columns:
            def create_pdf_link(url):
                if url and isinstance(url, str) and url.strip():
                    # Return the full URL without truncation
                    if ".pdf" in url.lower():
                        return url
                return None
            display_df["pdf_link"] = display_df["source_url"].apply(create_pdf_link)

        # Format dates - use ISO8601 format for parsing Supabase timestamps
        if "created_at" in display_df.columns:
            display_df["created_at"] = pd.to_datetime(
                display_df["created_at"],
                format='ISO8601'
            ).dt.strftime("%Y-%m-%d %H:%M")

        if "transaction_date" in display_df.columns:
            display_df["transaction_date"] = pd.to_datetime(
                display_df["transaction_date"],
                format='ISO8601'
            ).dt.strftime("%Y-%m-%d")

        if "disclosure_date" in display_df.columns:
            display_df["disclosure_date"] = pd.to_datetime(
                display_df["disclosure_date"],
                format='ISO8601'
            ).dt.strftime("%Y-%m-%d")

        # Replace None/empty tickers with "N/A"
        if "asset_ticker" in display_df.columns:
            display_df["asset_ticker"] = display_df["asset_ticker"].fillna("N/A").replace("", "N/A")

        # Format asset type
        if "asset_type" in display_df.columns:
            display_df["asset_type"] = display_df["asset_type"].fillna("Unknown").replace("", "Unknown")

        # Drop the truncated source_url column since we now have pdf_link
        # Keep the document ID for reference
        if "source_url" in display_df.columns:
            display_df = display_df.drop(columns=["source_url"])

        # Rename columns for display
        column_rename = {
            "created_at": "Processed",
            "transaction_date": "Trans. Date",
            "disclosure_date": "Disc. Date",
            "politician_name": "Politician",
            "politician_party": "Party",
            "politician_state": "State/Country",
            "filing_type": "Filing",
            "source": "Source",
            "asset_ticker": "Ticker",
            "asset_name": "Asset",
            "asset_type": "Asset Type",
            "transaction_type": "Type",
            "amount_range_min": "Min $",
            "amount_range_max": "Max $",
            "status": "Status",
            "source_document_id": "Doc ID",
            "pdf_link": "PDF"
        }

        display_df.columns = [column_rename.get(col, col) for col in display_df.columns]

        logger.debug("Displaying disclosures table", metadata={
            "row_count": len(display_df),
            "columns": list(display_df.columns)
        })

        # Calculate GLOBAL ticker statistics (always unfiltered for context)
        # Query for total disclosures (unfiltered)
        total_all_response = db.client.table("trading_disclosures").select("id", count="exact").execute()
        total_all_disclosures = total_all_response.count if hasattr(total_all_response, 'count') else 0

        # Query for disclosures with tickers
        with_tickers_response = db.client.table("trading_disclosures").select("id", count="exact").neq("asset_ticker", "").not_.is_("asset_ticker", "null").execute()
        global_with_tickers = with_tickers_response.count if hasattr(with_tickers_response, 'count') else 0

        # Calculate missing from total (unfiltered)
        global_missing_tickers = total_all_disclosures - global_with_tickers
        global_ticker_percentage = (global_with_tickers / total_all_disclosures * 100) if total_all_disclosures > 0 else 0

        # Also calculate LOCAL (current page) ticker statistics for display messages
        missing_tickers = len([t for t in df["asset_ticker"] if not t or t == ""])
        with_tickers_on_page = len(df) - missing_tickers

        # Show ticker metrics (GLOBAL - always shows full database stats for context)
        st.markdown("#### 📊 Ticker Statistics (All Disclosures)")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "With Tickers (Actionable)",
                f"{global_with_tickers:,}",
                delta=f"{global_ticker_percentage:.1f}%",
                help="Individual stocks with ticker symbols - ready for trading signals"
            )

        with col2:
            st.metric(
                "Without Tickers",
                f"{global_missing_tickers:,}",
                delta=f"{(100-global_ticker_percentage):.1f}%",
                delta_color="inverse",
                help="Mutual funds, ETFs, bonds, and other assets without tickers"
            )

        with col3:
            st.metric(
                "Total Disclosures",
                f"{total_all_disclosures:,}",
                help="All trading disclosures in the database"
            )

        # Show filter status message
        if show_ticker_only:
            st.success(f"✅ Showing {len(display_df)} actionable stocks with tickers (filtered at database level)")
            logger.info("Filtered to ticker-only view", metadata={
                "filtered_count": len(display_df),
                "filter_enabled": True
            })
        else:
            # Show info about missing tickers on current page
            if missing_tickers > 0:
                st.info(f"""
                ℹ️ **{missing_tickers} disclosures on this page don't have tickers** (mostly mutual funds, ETFs, bonds)

                💡 **Tip**: Toggle "Show only actionable stocks" above to focus on the {global_with_tickers:,} individual stocks that can generate trading signals.
                """)
                logger.info("Missing tickers on page", metadata={
                    "missing_count": missing_tickers,
                    "page_count": len(df)
                })

        # Configure column display with clickable PDF links
        column_config = {}
        if "PDF" in display_df.columns:
            column_config["PDF"] = st.column_config.LinkColumn(
                "PDF",
                help="Click to open the source PDF disclosure document",
                display_text="View PDF",
                width="small"
            )

        st.dataframe(
            display_df,
            use_container_width=True,
            column_config=column_config
        )

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
    st.error(f"❌ Database connection error: {str(e)}")
    import traceback
    logger.error(f"Failed to load recent disclosures: {str(e)}", error=e, metadata={"traceback": traceback.format_exc()})

    # Show connection help
    with st.expander("🔍 Troubleshooting"):
        st.markdown("""
        **Common issues:**
        1. **Missing Supabase credentials** - Check `.streamlit/secrets.toml` has:
           ```toml
           [connections.supabase]
           url = "your-supabase-url"
           key = "your-supabase-key"
           ```

        2. **Database not initialized** - Run database setup first:
           ```bash
           python 7_🔧_Database_Setup.py
           ```

        3. **No data imported yet** - Import some data using the "Data Sources" tab above
        """)

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
