"""
Capitol Trades - Streamlit Sync Page

Add this to your existing Streamlit app to sync data to the React frontend.

Usage:
    streamlit run streamlit_sync_page.py
    
Or import into your existing Streamlit app:
    from streamlit_sync_page import render_sync_page
    render_sync_page()
"""

import streamlit as st
from datetime import datetime, timedelta
from supabase_sync import CapitolTradesSync, get_sync_client

# Page config
st.set_page_config(
    page_title="Capitol Trades - Data Sync",
    page_icon="📊",
    layout="wide"
)


def render_sync_page():
    """Main sync page component - can be called from your existing Streamlit app."""
    
    st.title("📊 Capitol Trades Data Sync")
    st.markdown("Sync data to the React frontend dashboard")
    
    # Initialize sync client
    try:
        sync = get_sync_client()
        st.success("✅ Connected to Supabase")
    except Exception as e:
        st.error(f"❌ Failed to connect to Supabase: {e}")
        st.info("Make sure SUPABASE_SERVICE_ROLE_KEY is set in your environment")
        return
    
    # Tabs for different operations
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Dashboard", "👤 Politicians", "💹 Trades", "🔄 Sync"])
    
    # ==================== DASHBOARD TAB ====================
    with tab1:
        st.subheader("Current Database Status")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            politicians = sync.client.table("politicians").select("id", count="exact").execute()
            st.metric("Politicians", politicians.count or 0)
        
        with col2:
            trades = sync.client.table("trades").select("id", count="exact").execute()
            st.metric("Total Trades", trades.count or 0)
        
        with col3:
            jurisdictions = sync.client.table("jurisdictions").select("id", count="exact").execute()
            st.metric("Jurisdictions", jurisdictions.count or 0)
        
        with col4:
            week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
            recent = sync.client.table("trades").select("id", count="exact").gte("filing_date", week_ago).execute()
            st.metric("Recent Filings (7d)", recent.count or 0)
        
        st.divider()
        
        # Recent trades
        st.subheader("Recent Trades")
        recent_trades = sync.get_trades(limit=10)
        
        if recent_trades:
            for trade in recent_trades:
                pol_name = trade.get("politician", {}).get("name", "Unknown") if trade.get("politician") else "Unknown"
                trade_emoji = "🟢" if trade["trade_type"] == "buy" else "🔴"
                st.markdown(
                    f"{trade_emoji} **{pol_name}** - {trade['ticker']} ({trade['trade_type'].upper()}) - "
                    f"${trade['estimated_value']:,} - Filed: {trade['filing_date']}"
                )
        else:
            st.info("No trades in database yet")
    
    # ==================== POLITICIANS TAB ====================
    with tab2:
        st.subheader("Add/Update Politician")
        
        with st.form("politician_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Name", placeholder="Nancy Pelosi")
                party = st.selectbox("Party", ["D", "R", "I", "Other"])
                chamber = st.text_input("Chamber", placeholder="House")
            
            with col2:
                jurisdiction = st.selectbox(
                    "Jurisdiction",
                    ["us-house", "us-senate", "eu-parliament", "uk-parliament", "california", "texas"]
                )
                state = st.text_input("State (optional)", placeholder="CA")
            
            submitted = st.form_submit_button("Add/Update Politician")
            
            if submitted and name and chamber:
                result = sync.upsert_politician(
                    name=name,
                    party=party,
                    chamber=chamber,
                    jurisdiction_id=jurisdiction,
                    state=state if state else None
                )
                if result:
                    st.success(f"✅ Politician '{name}' saved!")
                else:
                    st.error("Failed to save politician")
        
        st.divider()
        
        # List politicians
        st.subheader("Current Politicians")
        politicians = sync.get_politicians()
        
        if politicians:
            for pol in politicians[:20]:  # Limit display
                st.markdown(
                    f"**{pol['name']}** ({pol['party']}) - {pol['chamber']} - "
                    f"${pol['total_volume']:,} in {pol['total_trades']} trades"
                )
        else:
            st.info("No politicians in database yet")
    
    # ==================== TRADES TAB ====================
    with tab3:
        st.subheader("Add Trade")
        
        # Get politicians for dropdown
        politicians = sync.get_politicians()
        politician_options = {p["name"]: p["id"] for p in politicians} if politicians else {}
        
        if not politician_options:
            st.warning("Add a politician first before adding trades")
        else:
            with st.form("trade_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    politician_name = st.selectbox("Politician", list(politician_options.keys()))
                    ticker = st.text_input("Ticker", placeholder="NVDA")
                    company = st.text_input("Company", placeholder="NVIDIA Corporation")
                    trade_type = st.selectbox("Type", ["buy", "sell"])
                
                with col2:
                    amount_range = st.selectbox("Amount Range", [
                        "$1,001 - $15,000",
                        "$15,001 - $50,000",
                        "$50,001 - $100,000",
                        "$100,001 - $250,000",
                        "$250,001 - $500,000",
                        "$500,001 - $1,000,000",
                        "$1,000,001 - $5,000,000",
                        "Over $5,000,000"
                    ])
                    estimated_value = st.number_input("Estimated Value ($)", min_value=0, value=50000)
                    transaction_date = st.date_input("Transaction Date")
                    filing_date = st.date_input("Filing Date")
                
                submitted = st.form_submit_button("Add Trade")
                
                if submitted and ticker and company:
                    result = sync.insert_trade(
                        politician_id=politician_options[politician_name],
                        ticker=ticker.upper(),
                        company=company,
                        trade_type=trade_type,
                        amount_range=amount_range,
                        estimated_value=estimated_value,
                        filing_date=str(filing_date),
                        transaction_date=str(transaction_date)
                    )
                    if result:
                        st.success(f"✅ Trade added for {politician_name}!")
                        # Update politician totals
                        sync.update_politician_totals(politician_options[politician_name])
                    else:
                        st.error("Failed to add trade")
    
    # ==================== SYNC TAB ====================
    with tab4:
        st.subheader("Data Sync Operations")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Recalculate Stats")
            st.markdown("Update all dashboard statistics from current data")
            
            if st.button("🔄 Recalculate Dashboard Stats", type="primary"):
                with st.spinner("Recalculating..."):
                    stats = sync.recalculate_dashboard_stats()
                    st.success("✅ Dashboard stats updated!")
                    st.json(stats)
        
        with col2:
            st.markdown("### Full Sync")
            st.markdown("Recalculate all politician totals and chart data")
            
            if st.button("🔄 Run Full Sync", type="secondary"):
                with st.spinner("Running full sync..."):
                    stats = sync.full_sync()
                    st.success("✅ Full sync complete!")
                    st.json(stats)
        
        st.divider()
        
        # Bulk import
        st.subheader("Bulk Import (JSON)")
        st.markdown("Paste JSON data to import multiple filings at once")
        
        json_input = st.text_area(
            "Filing Data (JSON)",
            placeholder='''[
    {
        "politician": {"name": "Nancy Pelosi", "party": "D", "chamber": "House", "state": "CA"},
        "trades": [
            {"ticker": "NVDA", "company": "NVIDIA", "type": "buy", "amount_range": "$100,001 - $250,000", "estimated_value": 175000, "filing_date": "2024-01-15", "transaction_date": "2024-01-10"}
        ]
    }
]''',
            height=200
        )
        
        if st.button("📥 Import JSON Data"):
            if json_input:
                try:
                    import json
                    filings = json.loads(json_input)
                    
                    progress = st.progress(0)
                    for i, filing in enumerate(filings):
                        sync.sync_filing(filing)
                        progress.progress((i + 1) / len(filings))
                    
                    st.success(f"✅ Imported {len(filings)} filings!")
                    sync.recalculate_dashboard_stats()
                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON: {e}")
                except Exception as e:
                    st.error(f"Import failed: {e}")
            else:
                st.warning("Please enter JSON data")
        
        st.divider()
        
        # Create notification
        st.subheader("Send Notification")
        
        with st.form("notification_form"):
            notif_title = st.text_input("Title", placeholder="New Data Available")
            notif_message = st.text_input("Message", placeholder="Fresh trading data has been synced")
            notif_type = st.selectbox("Type", ["info", "success", "warning", "error"])
            
            if st.form_submit_button("📢 Send Notification"):
                if notif_title and notif_message:
                    result = sync.create_notification(
                        title=notif_title,
                        message=notif_message,
                        notification_type=notif_type
                    )
                    if result:
                        st.success("✅ Notification sent!")
                    else:
                        st.error("Failed to send notification")


# Run directly
if __name__ == "__main__":
    render_sync_page()
