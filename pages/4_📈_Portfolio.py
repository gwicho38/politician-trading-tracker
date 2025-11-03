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

st.set_page_config(page_title="Portfolio", page_icon="📈", layout="wide")

# Load secrets on page load
load_all_secrets()

# Require authentication
from auth_utils import require_authentication
require_authentication()

st.title("📈 Portfolio Management")
st.markdown("Monitor your positions, performance, and risk metrics")

# Check Alpaca configuration
alpaca_api_key = os.getenv("ALPACA_API_KEY")
alpaca_secret_key = os.getenv("ALPACA_SECRET_KEY")

if not alpaca_api_key or not alpaca_secret_key:
    st.warning("Alpaca API not configured. Please set up your API keys to view portfolio.")
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
        st.info("📍 Viewing LIVE trading account")
    else:
        st.info("📍 Viewing paper trading account")

is_live = (trading_mode == "Live")

# Initialize clients
try:
    from politician_trading.trading.alpaca_client import AlpacaTradingClient
    from politician_trading.trading.risk_manager import RiskManager

    # Use paper=True by default unless explicitly set to Live
    use_paper = (trading_mode == "Paper")

    # Show what we're trying to connect with
    with st.expander("🔍 Connection Details", expanded=False):
        st.code(f"""
API Key: {alpaca_api_key[:4]}...{alpaca_api_key[-4:]}
Key Type: {'Paper (PK)' if alpaca_api_key.startswith('PK') else 'Live (AK)'}
Paper Mode: {use_paper}
Expected Endpoint: {'https://paper-api.alpaca.markets' if use_paper else 'https://api.alpaca.markets'}
        """)

    with st.spinner("Connecting to Alpaca..."):
        alpaca_client = AlpacaTradingClient(
            api_key=alpaca_api_key,
            secret_key=alpaca_secret_key,
            paper=use_paper
        )

        risk_manager = RiskManager()

        # Get data
        st.write("Fetching account info...")
        account_info = alpaca_client.get_account()
        st.write("Fetching portfolio...")
        portfolio = alpaca_client.get_portfolio()
        st.write("Fetching positions...")
        positions = alpaca_client.get_positions()

    # Portfolio overview
    st.markdown("### 💼 Portfolio Overview")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Portfolio Value",
            f"${account_info['portfolio_value']:,.2f}",
            delta=f"${float(account_info['portfolio_value']) - float(account_info['last_equity']):,.2f}"
        )

    with col2:
        st.metric(
            "Cash",
            f"${account_info['cash']:,.2f}"
        )

    with col3:
        st.metric(
            "Buying Power",
            f"${account_info['buying_power']:,.2f}"
        )

    with col4:
        st.metric(
            "Long Value",
            f"${account_info['long_market_value']:,.2f}"
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
