"""
Portfolio Page - Monitor positions, performance, and risk metrics
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
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

st.set_page_config(page_title="Portfolio", page_icon="📈", layout="wide")

# Load secrets on page load
load_all_secrets()

# Require authentication
from auth_utils import require_authentication, show_user_info
require_authentication()
show_user_info()

st.title("📈 Portfolio Management")
st.markdown("Monitor your positions, performance, and risk metrics")

# Add auto-refresh controls
from autorefresh_config import add_refresh_controls, setup_autorefresh, show_refresh_indicator

# Add refresh controls in sidebar
enabled, interval, _ = add_refresh_controls("portfolio", default_enabled=False)  # Default off for portfolio

# Setup auto-refresh if enabled
refresh_count = 0
if enabled:
    refresh_count = setup_autorefresh(
        interval=interval,
        key="portfolio_refresh",
        debounce=True
    )
    if refresh_count > 0:
        show_refresh_indicator(refresh_count, "portfolio")

# Get user-specific API keys
from user_api_keys import get_user_api_keys_manager

keys_manager = get_user_api_keys_manager()
user_email = st.user.email if st.user.is_logged_in else None

if not user_email:
    st.error("🔑 Authentication required")
    st.stop()

user_keys = keys_manager.get_user_keys(user_email)

if not user_keys or not user_keys.get("paper_api_key"):
    st.error("🔑 Alpaca API not configured")
    st.markdown("""
    ### Setup Instructions

    To use the Portfolio page, you need to configure your Alpaca API credentials:

    1. **Go to [Settings](/Settings)** page
    2. Navigate to the **Alpaca API Configuration** section
    3. Enter your paper trading API keys
    4. Test the connection to validate

    **Don't have an Alpaca account yet?**
    - Sign up for free at [alpaca.markets](https://alpaca.markets/)
    - Generate paper trading API keys in your dashboard
    - Return here and configure them in Settings
    """)
    st.stop()

# Trading mode selection
col1, col2 = st.columns([1, 4])

with col1:
    # Check if user has live trading access
    has_live_access = keys_manager.has_live_access(user_email)

    # Only show live option if user has both keys configured AND subscription
    if has_live_access and user_keys.get("live_api_key"):
        trading_mode = st.radio(
            "Mode",
            options=["Paper", "Live"],
            index=0
        )
    else:
        trading_mode = "Paper"
        st.radio(
            "Mode",
            options=["Paper"],
            index=0,
            disabled=True
        )

with col2:
    if trading_mode == "Live":
        st.info("📍 Viewing LIVE trading account")
    else:
        st.info("📍 Viewing paper trading account")
        if not has_live_access:
            st.caption("🔒 Upgrade to Basic/Pro for live trading")
        elif not user_keys.get("live_api_key"):
            st.caption("💡 Configure live API keys in Settings")

is_live = (trading_mode == "Live")

# Initialize clients
try:
    from politician_trading.trading.alpaca_client import AlpacaTradingClient
    from politician_trading.trading.risk_manager import RiskManager

    # Use paper=True by default unless explicitly set to Live
    use_paper = (trading_mode == "Paper")

    # Get appropriate API keys for the selected mode
    if use_paper:
        alpaca_api_key = user_keys.get("paper_api_key")
        alpaca_secret_key = user_keys.get("paper_secret_key")
    else:
        alpaca_api_key = user_keys.get("live_api_key")
        alpaca_secret_key = user_keys.get("live_secret_key")

    if not alpaca_api_key or not alpaca_secret_key:
        st.error(f"❌ {'Live' if not use_paper else 'Paper'} trading API keys not configured")
        st.info("Please configure your API keys in the [Settings](/Settings) page")
        st.stop()

    # Initialize Alpaca client
    alpaca_client = AlpacaTradingClient(
        api_key=alpaca_api_key,
        secret_key=alpaca_secret_key,
        paper=use_paper
    )

    # Test connection first
    with st.spinner("Testing connection to Alpaca..."):
        connection_test = alpaca_client.test_connection()

    if not connection_test["success"]:
        st.error(f"❌ {connection_test['message']}")

        if "error" in connection_test:
            st.markdown(f"**Error Details**: {connection_test['error']}")

        if "troubleshooting" in connection_test:
            st.markdown("### 🔧 Troubleshooting Steps:")
            for step in connection_test["troubleshooting"]:
                st.markdown(f"- {step}")

        # Show what we tried to connect with
        with st.expander("🔍 Debug Information"):
            st.code(f"""
API Key: {alpaca_api_key[:4]}...{alpaca_api_key[-4:]}
Key Type: {'Paper (PK)' if alpaca_api_key.startswith('PK') else 'Live (AK)' if alpaca_api_key.startswith('AK') else 'Unknown'}
Paper Mode: {use_paper}
Expected Endpoint: {alpaca_client.base_url}
            """)

        st.stop()

    # Connection successful
    st.success(f"✅ {connection_test['message']}")

    risk_manager = RiskManager()

    # Fetch portfolio data
    try:
        with st.spinner("Loading portfolio data..."):
            account_info = alpaca_client.get_account()
            portfolio = alpaca_client.get_portfolio()
            positions = alpaca_client.get_positions()
    except Exception as e:
        st.error(f"❌ Failed to fetch portfolio data: {str(e)}")

        with st.expander("📋 Error Details"):
            import traceback
            st.code(traceback.format_exc())

        st.info("💡 **Troubleshooting:**\n- Check if Alpaca service is operational\n- Verify your API keys are valid\n- Try refreshing the page")
        st.stop()

    # Check for pending orders
    st.markdown("---")
    st.markdown("### ⏳ Pending Orders")

    try:
        pending_orders = alpaca_client.get_orders(status="open", limit=50)

        if pending_orders:
            st.warning(f"You have {len(pending_orders)} pending order(s)")

            pending_data = []
            for order in pending_orders[:10]:  # Show first 10
                pending_data.append({
                    "Ticker": order.ticker,
                    "Side": order.side.upper(),
                    "Quantity": order.quantity,
                    "Type": order.order_type.value,
                    "Status": order.status.value,
                    "Submitted": order.submitted_at.strftime("%Y-%m-%d %H:%M") if order.submitted_at else "N/A",
                })

            pending_df = pd.DataFrame(pending_data)
            st.dataframe(pending_df, use_container_width=True)

            st.info("💡 These orders will execute when market conditions are met. View details on the **[Orders](/Orders)** page.")
        else:
            st.success("✅ No pending orders")
    except Exception as e:
        st.error(f"Could not fetch pending orders: {str(e)}")

    # Portfolio overview
    st.markdown("---")
    st.markdown("### 💼 Portfolio Overview")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        portfolio_val = float(account_info['portfolio_value'])
        last_eq = float(account_info['last_equity'])
        st.metric(
            "Portfolio Value",
            f"${portfolio_val:,.2f}",
            delta=f"${portfolio_val - last_eq:,.2f}"
        )

    with col2:
        cash_val = float(account_info['cash'])
        st.metric(
            "Cash",
            f"${cash_val:,.2f}"
        )

    with col3:
        buying_power_val = float(account_info['buying_power'])
        st.metric(
            "Buying Power",
            f"${buying_power_val:,.2f}"
        )

    with col4:
        long_val = float(account_info['long_market_value'])
        st.metric(
            "Long Value",
            f"${long_val:,.2f}"
        )

    with col5:
        st.metric(
            "Open Positions",
            len(positions)
        )

    # Risk metrics
    st.markdown("---")
    st.markdown("### ⚠️ Risk Metrics")

    risk_metrics = risk_manager.get_risk_metrics(portfolio, positions)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        exposure_pct = risk_metrics['exposure_pct']
        st.metric(
            "Total Exposure",
            f"{exposure_pct:.1f}%",
            delta=f"${risk_metrics['total_exposure']:,.2f}"
        )
        if exposure_pct > 80:
            st.error("⚠️ High exposure")
        elif exposure_pct > 60:
            st.warning("⚠️ Moderate exposure")

    with col2:
        unrealized_pl_pct = risk_metrics['unrealized_pl_pct']
        color = "normal"
        if unrealized_pl_pct > 5:
            color = "normal"
        elif unrealized_pl_pct < -5:
            color = "inverse"

        st.metric(
            "Unrealized P&L",
            f"{unrealized_pl_pct:.2f}%",
            delta=f"${risk_metrics['total_unrealized_pl']:,.2f}",
            delta_color=color
        )

    with col3:
        st.metric(
            "Largest Position",
            f"{risk_metrics['largest_position_pct']:.1f}%",
            delta=f"${risk_metrics['largest_position_value']:,.2f}"
        )
        if risk_metrics['largest_position_pct'] > 15:
            st.warning("⚠️ Position concentration")

    with col4:
        st.metric(
            "Win Rate",
            f"{risk_metrics['win_rate']:.1f}%",
            delta=f"{risk_metrics['winning_positions']}/{risk_metrics['total_positions']} positions"
        )

    # Positions
    st.markdown("---")
    st.markdown("### 📊 Open Positions")

    if positions:
        # Create positions dataframe
        positions_data = []
        for pos in positions:
            positions_data.append({
                "Ticker": pos.ticker,
                "Side": pos.side.upper(),
                "Quantity": pos.quantity,
                "Avg Entry": f"${pos.avg_entry_price:.2f}",
                "Current Price": f"${pos.current_price:.2f}",
                "Market Value": f"${pos.market_value:,.2f}",
                "P&L": f"${pos.unrealized_pl:,.2f}",
                "P&L %": f"{pos.unrealized_pl_pct:.2f}%",
                "Stop Loss": f"${pos.stop_loss:.2f}" if pos.stop_loss else "N/A",
                "Take Profit": f"${pos.take_profit:.2f}" if pos.take_profit else "N/A",
            })

        df = pd.DataFrame(positions_data)

        # Color-code P&L
        def color_pl(val):
            if "%" in val:
                try:
                    num = float(val.replace("%", ""))
                    color = 'green' if num > 0 else 'red' if num < 0 else 'black'
                    return f'color: {color}'
                except:
                    return ''
            elif "$" in val:
                try:
                    num = float(val.replace("$", "").replace(",", ""))
                    color = 'green' if num > 0 else 'red' if num < 0 else 'black'
                    return f'color: {color}'
                except:
                    return ''
            return ''

        styled_df = df.style.applymap(color_pl, subset=["P&L", "P&L %"])
        st.dataframe(styled_df, width="stretch")

        # Position distribution pie chart
        st.markdown("### Position Distribution")

        col1, col2 = st.columns(2)

        with col1:
            # By market value
            values = [abs(pos.market_value) for pos in positions]
            labels = [pos.ticker for pos in positions]

            fig = go.Figure(data=[go.Pie(labels=labels, values=values)])
            fig.update_layout(title="By Market Value")
            st.plotly_chart(fig, width="stretch")

        with col2:
            # P&L distribution
            pl_values = [pos.unrealized_pl for pos in positions]
            colors = ['green' if v > 0 else 'red' for v in pl_values]

            fig = go.Figure(data=[go.Bar(
                x=labels,
                y=pl_values,
                marker_color=colors
            )])
            fig.update_layout(title="P&L by Position", xaxis_title="Ticker", yaxis_title="P&L ($)")
            st.plotly_chart(fig, width="stretch")

        # Position details
        st.markdown("### Position Details")

        for pos in positions:
            with st.expander(f"**{pos.ticker}** - {pos.side.upper()} {pos.quantity} shares"):
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Avg Entry Price", f"${pos.avg_entry_price:.2f}")
                with col2:
                    st.metric("Current Price", f"${pos.current_price:.2f}")
                with col3:
                    st.metric("Market Value", f"${pos.market_value:,.2f}")
                with col4:
                    pl_color = "normal" if pos.unrealized_pl > 0 else "inverse"
                    st.metric(
                        "Unrealized P&L",
                        f"${pos.unrealized_pl:,.2f}",
                        delta=f"{pos.unrealized_pl_pct:.2f}%",
                        delta_color=pl_color
                    )

                # Close position button
                if st.button(f"Close Position", key=f"close_{pos.ticker}"):
                    if st.button(f"⚠️ Confirm close {pos.ticker}", key=f"confirm_close_{pos.ticker}"):
                        try:
                            success = alpaca_client.close_position(pos.ticker)
                            if success:
                                st.success(f"✅ Closed position in {pos.ticker}")
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to close position in {pos.ticker}")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

        # Export positions
        st.markdown("---")
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Positions as CSV",
            data=csv,
            file_name=f"positions_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

    else:
        st.info("No open positions")

    # Risk Report
    st.markdown("---")
    st.markdown("### 📋 Risk Report")

    risk_report = risk_manager.get_risk_report(portfolio, positions)

    st.code(risk_report)

    # Monitor positions
    st.markdown("---")
    st.markdown("### 🔍 Position Monitoring")

    if st.button("🔍 Check Risk Management", width="stretch"):
        from politician_trading.trading.strategy import TradingStrategy

        strategy = TradingStrategy(
            alpaca_client=alpaca_client,
            risk_manager=risk_manager,
            auto_execute=False
        )

        actions = strategy.monitor_positions()

        if actions:
            st.warning(f"⚠️ Found {len(actions)} positions requiring immediate action:")

            actions_df = pd.DataFrame(actions)
            st.dataframe(actions_df, width="stretch")

            if any(not a.get("executed") for a in actions):
                st.info("💡 Enable auto-execution to automatically manage risk")
        else:
            # Check if there are violations in the risk report
            has_violations = (
                risk_metrics['exposure_pct'] > risk_manager.max_total_exposure_pct or
                risk_metrics['largest_position_pct'] > risk_manager.max_position_size_pct or
                risk_metrics['open_positions'] >= risk_manager.max_positions
            )

            if has_violations:
                st.info("ℹ️ No positions need immediate closure, but risk violations exist (see Risk Report above)")
            else:
                st.success("✅ All positions within risk parameters")

except Exception as e:
    st.error(f"Error loading portfolio: {str(e)}")
    import traceback
    st.code(traceback.format_exc())

# Performance tracking (placeholder for future implementation)
st.markdown("---")
st.markdown("### 📊 Performance Tracking")

st.info("""
💡 **Coming Soon**: Historical performance tracking

- Daily/weekly/monthly returns
- Benchmark comparison
- Drawdown analysis
- Trade history
""")
