"""
Orders Page - Track all trading orders and their status
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timezone
import os
import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent
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

st.set_page_config(page_title="Orders", page_icon="📋", layout="wide")

# Load secrets on page load
load_all_secrets()

# Require authentication
from auth_utils import require_authentication, show_user_info
require_authentication()
show_user_info()

st.title("📋 Order Tracking")
st.markdown("Monitor all your trading orders and their execution status")

# Check Alpaca configuration
alpaca_api_key = os.getenv("ALPACA_API_KEY")
alpaca_secret_key = os.getenv("ALPACA_SECRET_KEY")

if not alpaca_api_key or not alpaca_secret_key:
    st.error("🔑 Alpaca API not configured")
    st.markdown("""
    To track orders, you need to configure your Alpaca API credentials.
    See the Portfolio page for setup instructions.
    """)
    st.stop()

# Trading mode selection
col1, col2 = st.columns([1, 4])

with col1:
    trading_mode = st.radio(
        "Mode",
        options=["Paper", "Live"],
        index=0
    )

with col2:
    if trading_mode == "Live":
        st.info("📍 Viewing LIVE trading orders")
    else:
        st.info("📍 Viewing paper trading orders")

is_live = (trading_mode == "Live")
use_paper = (trading_mode == "Paper")

# Initialize Alpaca client
try:
    from politician_trading.trading.alpaca_client import AlpacaTradingClient

    alpaca_client = AlpacaTradingClient(
        api_key=alpaca_api_key,
        secret_key=alpaca_secret_key,
        paper=use_paper
    )

    # Link to Alpaca dashboard
    st.markdown("---")
    dashboard_url = "https://app.alpaca.markets/paper/dashboard/overview" if use_paper else "https://app.alpaca.markets/live/dashboard/overview"
    st.markdown(f"🔗 **[View in Alpaca Dashboard]({dashboard_url})** - See detailed order information")

    # Fetch orders
    st.markdown("---")
    st.markdown("### 📊 Order History")

    # Filter options
    col1, col2, col3 = st.columns(3)

    with col1:
        status_filter = st.selectbox(
            "Status",
            ["all", "open", "closed"],
            index=0,
            help="Filter orders by status"
        )

    with col2:
        limit = st.number_input(
            "Limit",
            min_value=10,
            max_value=500,
            value=100,
            step=10,
            help="Number of orders to fetch"
        )

    with col3:
        if st.button("🔄 Refresh Orders", use_container_width=True):
            st.rerun()

    # Fetch orders
    with st.spinner("Loading orders..."):
        orders = alpaca_client.get_orders(
            status=status_filter,
            limit=limit
        )

    if orders:
        st.success(f"Found {len(orders)} orders")

        # Convert to dataframe
        orders_data = []
        for order in orders:
            orders_data.append({
                "Order ID": order.alpaca_order_id[:8] + "...",
                "Full ID": order.alpaca_order_id,
                "Ticker": order.ticker,
                "Type": order.order_type.value,
                "Side": order.side.upper(),
                "Quantity": order.quantity,
                "Filled": order.filled_quantity,
                "Status": order.status.value,
                "Limit Price": f"${order.limit_price:.2f}" if order.limit_price else "N/A",
                "Stop Price": f"${order.stop_price:.2f}" if order.stop_price else "N/A",
                "Filled Price": f"${order.filled_avg_price:.2f}" if order.filled_avg_price else "N/A",
                "Submitted": order.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if order.submitted_at else "N/A",
                "Filled At": order.filled_at.strftime("%Y-%m-%d %H:%M:%S") if order.filled_at else "N/A",
            })

        df = pd.DataFrame(orders_data)

        # Display summary metrics
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            submitted = len([o for o in orders if o.status.value in ["new", "accepted", "pending_new"]])
            st.metric("⏳ Pending", submitted)

        with col2:
            filled = len([o for o in orders if o.status.value == "filled"])
            st.metric("✅ Filled", filled)

        with col3:
            partial = len([o for o in orders if o.status.value == "partially_filled"])
            st.metric("🔄 Partial", partial)

        with col4:
            canceled = len([o for o in orders if o.status.value == "canceled"])
            st.metric("❌ Canceled", canceled)

        with col5:
            rejected = len([o for o in orders if o.status.value == "rejected"])
            st.metric("🚫 Rejected", rejected)

        # Display orders table
        st.markdown("### Orders")

        # Style the dataframe based on status
        def style_status(row):
            status = row["Status"]
            if status == "filled":
                return ["background-color: #d4edda"] * len(row)
            elif status in ["new", "accepted", "pending_new"]:
                return ["background-color: #fff3cd"] * len(row)
            elif status == "partially_filled":
                return ["background-color: #cfe2ff"] * len(row)
            elif status == "canceled":
                return ["background-color: #f8d7da"] * len(row)
            elif status == "rejected":
                return ["background-color: #f1aeb5"] * len(row)
            else:
                return [""] * len(row)

        # Show simplified view
        display_df = df[["Order ID", "Ticker", "Type", "Side", "Quantity", "Filled", "Status", "Filled Price", "Submitted"]].copy()
        st.dataframe(display_df, use_container_width=True, height=400)

        # Order details expander
        st.markdown("### 🔍 Order Details")

        for idx, order in enumerate(orders[:20]):  # Show details for first 20 orders
            status_emoji = {
                "filled": "✅",
                "new": "⏳",
                "accepted": "⏳",
                "pending_new": "⏳",
                "partially_filled": "🔄",
                "canceled": "❌",
                "rejected": "🚫",
                "expired": "⏱️",
            }.get(order.status.value, "❓")

            with st.expander(f"{status_emoji} {order.ticker} - {order.side.upper()} {order.quantity} shares ({order.status.value})"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown("**Order Info**")
                    st.text(f"Order ID: {order.alpaca_order_id[:16]}...")
                    st.text(f"Type: {order.order_type.value}")
                    st.text(f"Side: {order.side.upper()}")
                    st.text(f"Quantity: {order.quantity}")
                    st.text(f"Filled: {order.filled_quantity}")

                with col2:
                    st.markdown("**Prices**")
                    if order.limit_price:
                        st.text(f"Limit: ${order.limit_price:.2f}")
                    if order.stop_price:
                        st.text(f"Stop: ${order.stop_price:.2f}")
                    if order.filled_avg_price:
                        st.text(f"Fill Avg: ${order.filled_avg_price:.2f}")
                    if order.trailing_percent:
                        st.text(f"Trail: {order.trailing_percent}%")

                with col3:
                    st.markdown("**Timestamps**")
                    if order.submitted_at:
                        st.text(f"Submitted: {order.submitted_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    if order.filled_at:
                        st.text(f"Filled: {order.filled_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    if order.canceled_at:
                        st.text(f"Canceled: {order.canceled_at.strftime('%Y-%m-%d %H:%M:%S')}")

                # Show order status explanation
                if order.status.value == "rejected":
                    st.error("⚠️ This order was rejected. Common reasons: insufficient funds, market closed, invalid symbol.")
                elif order.status.value in ["new", "accepted", "pending_new"]:
                    st.info("⏳ This order is pending execution. It will fill when market conditions are met.")
                elif order.status.value == "partially_filled":
                    st.warning(f"🔄 {order.filled_quantity}/{order.quantity} shares filled. Waiting for remaining shares.")

        # Export orders
        st.markdown("---")
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Orders as CSV",
            data=csv,
            file_name=f"orders_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

    else:
        st.info("No orders found. Place some trades to see them here!")

except Exception as e:
    st.error(f"Error loading orders: {str(e)}")
    import traceback
    with st.expander("📋 Error Details"):
        st.code(traceback.format_exc())

# Help section
st.markdown("---")
st.markdown("### 💡 Understanding Order Status")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **Order States:**
    - ⏳ **Pending** (new, accepted) - Order submitted, waiting to execute
    - 🔄 **Partially Filled** - Some shares filled, waiting for more
    - ✅ **Filled** - Order completely executed
    - ❌ **Canceled** - Order was canceled before execution
    - 🚫 **Rejected** - Order rejected (insufficient funds, invalid symbol, etc.)
    - ⏱️ **Expired** - Order expired (time in force reached)
    """)

with col2:
    st.markdown("""
    **Tips:**
    - Orders placed outside market hours (9:30 AM - 4:00 PM ET) will execute when market opens
    - Paper trading orders fill almost instantly during market hours
    - Check order status before assuming execution
    - Use limit orders for price control
    - Market orders execute immediately at current price
    """)
