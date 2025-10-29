"""
Data Collection Page - Collect politician trading disclosures
"""

import streamlit as st
import asyncio
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Data Collection", page_icon="📥", layout="wide")

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
    try:
        from politician_trading.workflow import PoliticianTradingWorkflow
        from politician_trading.config import SupabaseConfig, WorkflowConfig
        from politician_trading.database.database import SupabaseClient

        # Create config
        supabase_config = SupabaseConfig.from_env()
        workflow_config = WorkflowConfig(
            supabase=supabase_config,
            enable_us_congress=us_congress,
            enable_uk_parliament=uk_parliament,
            enable_eu_parliament=eu_parliament,
            enable_us_states=any([california, texas, new_york]),
            enable_california=california,
        )

        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Run workflow
        status_text.text("Initializing workflow...")
        workflow = PoliticianTradingWorkflow(workflow_config)

        # Create placeholder for results
        results_placeholder = st.empty()

        try:
            status_text.text("Running data collection...")
            progress_bar.progress(25)

            # Run collection (this is async in the actual implementation)
            results = asyncio.run(workflow.run())

            progress_bar.progress(100)
            status_text.text("✅ Collection complete!")

            # Store results
            st.session_state.collection_results = results
            st.session_state.collection_running = False

            # Display results
            st.success(f"✅ Successfully collected data!")

            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total Disclosures", results.get("total_processed", 0))
            with col2:
                st.metric("New Records", results.get("total_new", 0))
            with col3:
                st.metric("Updated Records", results.get("total_updated", 0))
            with col4:
                st.metric("Failed", results.get("total_failed", 0))

            # Detailed results by source
            st.markdown("### Results by Source")

            if "source_results" in results:
                source_df = pd.DataFrame([
                    {
                        "Source": source,
                        "Processed": data.get("processed", 0),
                        "New": data.get("new", 0),
                        "Updated": data.get("updated", 0),
                        "Failed": data.get("failed", 0),
                        "Status": "✅ Success" if data.get("status") == "completed" else "❌ Failed"
                    }
                    for source, data in results["source_results"].items()
                ])
                st.dataframe(source_df, use_container_width=True)

            st.rerun()

        except Exception as e:
            progress_bar.progress(100)
            status_text.text("❌ Collection failed")
            st.error(f"Error during collection: {str(e)}")
            st.session_state.collection_running = False
            st.rerun()

    except Exception as e:
        st.error(f"Failed to initialize collection: {str(e)}")
        st.session_state.collection_running = False
        st.rerun()

# Display recent disclosures
st.markdown("---")
st.markdown("### Recent Disclosures")

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

        # Rename columns for display
        display_df.columns = ["Date", "Ticker", "Asset", "Type", "Min Amount", "Max Amount"]

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
