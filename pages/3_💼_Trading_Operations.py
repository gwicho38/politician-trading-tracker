"""
Trading Operations Page - Execute trades and manage orders
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from decimal import Decimal
import os
import sys
from pathlib import Path

# Add directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from streamlit_utils import load_all_secrets

st.set_page_config(page_title="Trading Operations", page_icon="💼", layout="wide")

# Load secrets on page load
load_all_secrets()

st.title("💼 Trading Operations")
st.markdown("Execute trades based on AI signals with comprehensive risk management")

# Check Alpaca configuration
alpaca_api_key = os.getenv("ALPACA_API_KEY")
alpaca_secret_key = os.getenv("ALPACA_SECRET_KEY")

if not alpaca_api_key or not alpaca_secret_key:
    st.error("""
    ⚠️ **Alpaca API not configured**

    To enable trading, please configure your Alpaca API keys:
    1. Sign up at [https://alpaca.markets/](https://alpaca.markets/)
    2. Get your API keys
    3. Add them to your .env file or Streamlit secrets:
        ```
        ALPACA_API_KEY=your_key_here
        ALPACA_SECRET_KEY=your_secret_here
        ```
    """)
    st.stop()

# Trading mode selection
st.markdown("### Trading Mode")

col1, col2 = st.columns([1, 3])

with col1:
    trading_mode = st.radio(
        "Select Mode",
        options=["Paper Trading", "Live Trading"],
        index=0,
        help="Paper trading uses simulated funds. Live trading uses real money!"
    )

with col2:
    if trading_mode == "Live Trading":
        st.error("""
        ⚠️ **WARNING: LIVE TRADING MODE**

        You are about to execute trades with REAL MONEY. Make sure you understand the risks involved.

        - All trades will use actual funds from your Alpaca account
        - Losses are real and cannot be undone
        - Always start with small position sizes
        - Monitor your positions closely
        """)
    else:
        st.info("""
        ℹ️ **Paper Trading Mode (Safe)**

        You're in paper trading mode, which uses simulated funds. This is perfect for:
        - Testing strategies without risk
        - Learning the platform
        - Evaluating signal performance
        """)

is_live = (trading_mode == "Live Trading")

# Initialize Alpaca client
try:
    from politician_trading.trading.alpaca_client import AlpacaTradingClient
    from politician_trading.trading.risk_manager import RiskManager
    from politician_trading.trading.strategy import TradingStrategy

    # Use paper=True by default unless explicitly set to Live
    use_paper = (trading_mode == "Paper Trading")

    alpaca_client = AlpacaTradingClient(
        api_key=alpaca_api_key,
        secret_key=alpaca_secret_key,
        paper=use_paper
    )

    # Get account info
    account_info = alpaca_client.get_account()

    # Display account info
    st.markdown("---")
    st.markdown("### 📊 Account Information")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Portfolio Value", f"${account_info['portfolio_value']:,.2f}")
    with col2:
        st.metric("Cash", f"${account_info['cash']:,.2f}")
    with col3:
        st.metric("Buying Power", f"${account_info['buying_power']:,.2f}")
    with col4:
        st.metric("Account Status", account_info['status'].upper())

except Exception as e:
    st.error(f"Failed to connect to Alpaca: {str(e)}")
    st.stop()

# Execute trades from signals
st.markdown("---")
st.markdown("### 🚀 Execute Trades from Signals")

# Fetch active signals
try:
    from politician_trading.database.database import SupabaseClient
    from politician_trading.config import SupabaseConfig

    config = SupabaseConfig.from_env()
    db = SupabaseClient(config)

    # Get signals
    query = db.client.table("trading_signals").select("*")
    query = query.eq("is_active", True)
    query = query.order("confidence_score", desc=True)

    response = query.execute()
    signals = response.data

    if signals:
        # Risk management settings
        st.markdown("#### Risk Management Settings")

        col1, col2, col3 = st.columns(3)

        with col1:
            max_position_pct = st.number_input(
                "Max Position Size (%)",
                min_value=1.0,
                max_value=100.0,
                value=10.0,
                step=1.0,
                help="Maximum % of portfolio per position"
            )

        with col2:
            max_risk_pct = st.number_input(
                "Max Risk Per Trade (%)",
                min_value=0.1,
                max_value=10.0,
                value=2.0,
                step=0.1,
                help="Maximum % of portfolio at risk per trade"
            )

        with col3:
            min_signal_confidence = st.slider(
                "Min Signal Confidence",
                min_value=0.0,
                max_value=1.0,
                value=0.7,
                step=0.05,
                help="Only trade signals above this confidence"
            )

        # Initialize risk manager and strategy
        risk_manager = RiskManager(
            max_position_size_pct=max_position_pct,
            max_portfolio_risk_pct=max_risk_pct,
            max_total_exposure_pct=80.0,
            max_positions=20,
            min_confidence=min_signal_confidence,
        )

        strategy = TradingStrategy(
            alpaca_client=alpaca_client,
            risk_manager=risk_manager,
            auto_execute=False,  # Manual execution via UI
        )

        # Filter signals by confidence
        tradeable_signals = [s for s in signals if s["confidence_score"] >= min_signal_confidence]

        if tradeable_signals:
            st.success(f"Found {len(tradeable_signals)} signals meeting confidence threshold")

            # Evaluate signals
            if st.button("🔍 Evaluate Signals", use_container_width=True):
                with st.spinner("Evaluating signals..."):
                    from src.models import TradingSignal, SignalType, SignalStrength

                    # Convert to TradingSignal objects
                    signal_objects = []
                    for data in tradeable_signals:
                        from uuid import UUID
                        signal_id = data["id"]
                        if isinstance(signal_id, str):
                            signal_id = UUID(signal_id)

                        signal = TradingSignal(
                            id=signal_id,
                            ticker=data["ticker"],
                            asset_name=data.get("asset_name", ""),
                            signal_type=SignalType(data["signal_type"]),
                            signal_strength=SignalStrength(data["signal_strength"]),
                            confidence_score=data["confidence_score"],
                            target_price=Decimal(str(data["target_price"])) if data.get("target_price") else None,
                            stop_loss=Decimal(str(data["stop_loss"])) if data.get("stop_loss") else None,
                            take_profit=Decimal(str(data["take_profit"])) if data.get("take_profit") else None,
                            politician_activity_count=data.get("politician_activity_count", 0),
                            buy_sell_ratio=data.get("buy_sell_ratio", 0.0),
                        )
                        signal_objects.append(signal)

                    # Evaluate
                    recommendations = strategy.evaluate_signals(signal_objects, dry_run=True)

                    if recommendations:
                        st.success(f"Generated {len(recommendations)} trade recommendations")

                        # Display recommendations
                        rec_df = pd.DataFrame(recommendations)

                        # Format for display
                        display_cols = ["ticker", "signal", "confidence", "shares", "estimated_cost", "can_trade", "reason"]
                        display_df = rec_df[[col for col in display_cols if col in rec_df.columns]].copy()

                        # Format
                        if "confidence" in display_df.columns:
                            display_df["confidence"] = display_df["confidence"].apply(lambda x: f"{x:.1%}")
                        if "estimated_cost" in display_df.columns:
                            display_df["estimated_cost"] = display_df["estimated_cost"].apply(lambda x: f"${x:,.2f}")

                        display_df.columns = ["Ticker", "Signal", "Confidence", "Shares", "Cost", "Can Trade", "Reason"]

                        st.dataframe(display_df, use_container_width=True)

                        # Execute trades
                        st.markdown("---")
                        st.markdown("#### Execute Selected Trades")

                        tradeable_recs = [r for r in recommendations if r.get("can_trade")]

                        if tradeable_recs:
                            selected_tickers = st.multiselect(
                                "Select trades to execute",
                                options=[r["ticker"] for r in tradeable_recs],
                                default=[],
                                help="Select which signals to trade"
                            )

                            if selected_tickers:
                                if is_live:
                                    st.warning(f"⚠️ You are about to execute {len(selected_tickers)} LIVE trades with REAL MONEY!")

                                confirm = st.checkbox("I confirm I want to execute these trades")

                                if st.button("🚀 Execute Trades", disabled=not confirm, use_container_width=True):
                                    for ticker in selected_tickers:
                                        # Find the signal
                                        signal_data = next((s for s in tradeable_signals if s["ticker"] == ticker), None)
                                        if signal_data:
                                            try:
                                                from uuid import UUID
                                                signal_id = signal_data["id"]
                                                if isinstance(signal_id, str):
                                                    signal_id = UUID(signal_id)

                                                signal = TradingSignal(
                                                    id=signal_id,
                                                    ticker=signal_data["ticker"],
                                                    asset_name=signal_data.get("asset_name", ""),
                                                    signal_type=SignalType(signal_data["signal_type"]),
                                                    signal_strength=SignalStrength(signal_data["signal_strength"]),
                                                    confidence_score=signal_data["confidence_score"],
                                                    target_price=Decimal(str(signal_data["target_price"])) if signal_data.get("target_price") else None,
                                                    stop_loss=Decimal(str(signal_data["stop_loss"])) if signal_data.get("stop_loss") else None,
                                                )

                                                order = strategy.execute_signal(signal, force=True)

                                                if order:
                                                    st.success(f"✅ Executed {signal_data['signal_type']} order for {ticker} (Order ID: {order.alpaca_order_id})")

                                                    # Save to database
                                                    order_data = {
                                                        "signal_id": str(signal_data["id"]) if signal_data.get("id") else None,
                                                        "ticker": order.ticker,
                                                        "order_type": order.order_type.value,
                                                        "side": order.side,
                                                        "quantity": order.quantity,
                                                        "limit_price": float(order.limit_price) if order.limit_price else None,
                                                        "status": order.status.value,
                                                        "trading_mode": "live" if is_live else "paper",
                                                        "alpaca_order_id": order.alpaca_order_id,
                                                        "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                                                    }

                                                    db.client.table("trading_orders").insert(order_data).execute()
                                                else:
                                                    st.error(f"❌ Failed to execute order for {ticker}")

                                            except Exception as e:
                                                st.error(f"❌ Error executing {ticker}: {str(e)}")

                                    st.success("Trade execution completed!")
                        else:
                            st.warning("No tradeable recommendations at this time. Adjust risk parameters or wait for better signals.")
                    else:
                        st.info("No trade recommendations generated. Try adjusting parameters.")
        else:
            st.info(f"No signals meet the minimum confidence threshold of {min_signal_confidence:.1%}")

    else:
        st.info("No active signals found. Generate signals first in the Trading Signals page.")

except Exception as e:
    st.error(f"Error loading signals: {str(e)}")

# Manual order placement
st.markdown("---")
st.markdown("### ✍️ Manual Order Placement")

with st.expander("Place Manual Order"):
    col1, col2 = st.columns(2)

    with col1:
        manual_ticker = st.text_input("Ticker Symbol", value="AAPL")
        manual_quantity = st.number_input("Quantity", min_value=1, value=10)
        manual_side = st.selectbox("Side", options=["buy", "sell"])

    with col2:
        manual_order_type = st.selectbox("Order Type", options=["market", "limit"])
        if manual_order_type == "limit":
            manual_limit_price = st.number_input("Limit Price", min_value=0.01, value=100.00, step=0.01)
        else:
            manual_limit_price = None

    if is_live:
        st.warning(f"⚠️ This will execute a LIVE {manual_side.upper()} order for {manual_quantity} shares of {manual_ticker}")

    confirm_manual = st.checkbox("Confirm manual order placement")

    if st.button("Place Order", disabled=not confirm_manual):
        try:
            if manual_order_type == "market":
                order = alpaca_client.place_market_order(manual_ticker, manual_quantity, manual_side)
            else:
                order = alpaca_client.place_limit_order(manual_ticker, manual_quantity, manual_side, Decimal(str(manual_limit_price)))

            st.success(f"✅ Order placed successfully! Order ID: {order.alpaca_order_id}")

            # Save to database
            order_data = {
                "ticker": order.ticker,
                "order_type": order.order_type.value,
                "side": order.side,
                "quantity": order.quantity,
                "limit_price": float(order.limit_price) if order.limit_price else None,
                "status": order.status.value,
                "trading_mode": "live" if is_live else "paper",
                "alpaca_order_id": order.alpaca_order_id,
                "submitted_at": datetime.utcnow().isoformat(),
            }

            db.client.table("trading_orders").insert(order_data).execute()

        except Exception as e:
            st.error(f"❌ Error placing order: {str(e)}")

# Recent orders
st.markdown("---")
st.markdown("### 📋 Recent Orders")

try:
    mode = "live" if is_live else "paper"

    query = db.client.table("trading_orders").select("*")
    query = query.eq("trading_mode", mode)
    query = query.order("created_at", desc=True)
    query = query.limit(50)

    response = query.execute()
    orders = response.data

    if orders:
        df = pd.DataFrame(orders)

        display_cols = ["ticker", "side", "quantity", "order_type", "status", "filled_quantity", "created_at"]
        display_df = df[[col for col in display_cols if col in df.columns]].copy()

        if "created_at" in display_df.columns:
            display_df["created_at"] = pd.to_datetime(display_df["created_at"]).dt.strftime("%Y-%m-%d %H:%M")

        display_df.columns = ["Ticker", "Side", "Qty", "Type", "Status", "Filled", "Time"]

        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No orders found for this trading mode")

except Exception as e:
    st.error(f"Error loading orders: {str(e)}")
