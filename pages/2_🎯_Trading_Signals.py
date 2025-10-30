"""
Trading Signals Page - Generate and view AI-powered trading signals
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal
import plotly.graph_objects as go
import plotly.express as px
import sys
from pathlib import Path

# Add directories to path for imports BEFORE importing
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Now import utilities
from streamlit_utils import load_all_secrets

st.set_page_config(page_title="Trading Signals", page_icon="🎯", layout="wide")

# Load secrets on page load
load_all_secrets()

st.title("🎯 AI-Powered Trading Signals")
st.markdown("Generate buy/sell/hold recommendations based on politician trading activity")

# Initialize session state
if "signals_generated" not in st.session_state:
    st.session_state.signals_generated = False
if "signals_data" not in st.session_state:
    st.session_state.signals_data = None

# Signal generation parameters
st.markdown("### Signal Generation Parameters")

col1, col2, col3 = st.columns(3)

with col1:
    lookback_days = st.number_input(
        "Look back period (days)",
        min_value=7,
        max_value=365,
        value=30,
        help="Analyze disclosures from the last N days"
    )

with col2:
    min_confidence = st.slider(
        "Minimum confidence",
        min_value=0.0,
        max_value=1.0,
        value=0.65,
        step=0.05,
        help="Only generate signals with confidence above this threshold"
    )

with col3:
    fetch_market_data = st.checkbox(
        "Fetch market data",
        value=True,
        help="Include real-time market data for better analysis"
    )

# Generate signals
if st.button("🎯 Generate Signals", use_container_width=True):
    with st.spinner("Generating AI-powered signals... This may take a minute."):
        try:
            from politician_trading.signals.signal_generator import SignalGenerator
            from politician_trading.database.database import SupabaseClient
            from politician_trading.config import SupabaseConfig

            # Initialize
            config = SupabaseConfig.from_env()
            db = SupabaseClient(config)

            # Fetch recent disclosures
            from datetime import timezone
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)

            query = db.client.table("trading_disclosures").select("*")
            query = query.gte("transaction_date", cutoff_date.isoformat())
            query = query.order("transaction_date", desc=True)

            response = query.execute()
            disclosures = response.data

            if not disclosures:
                st.warning("No disclosures found in the specified period")
                st.stop()

            # Group by ticker
            disclosures_by_ticker = {}
            for d in disclosures:
                ticker = d.get("asset_ticker")
                if ticker:
                    if ticker not in disclosures_by_ticker:
                        disclosures_by_ticker[ticker] = []
                    disclosures_by_ticker[ticker].append(d)

            st.info(f"Analyzing {len(disclosures_by_ticker)} unique tickers...")

            # Generate signals
            generator = SignalGenerator(
                model_version="v1.0",
                use_ml=False,  # Use heuristics for now
                confidence_threshold=min_confidence,
            )

            signals = generator.generate_signals(disclosures_by_ticker, fetch_market_data)

            # Save to database
            for signal in signals:
                try:
                    data = {
                        "ticker": signal.ticker,
                        "asset_name": signal.asset_name,
                        "signal_type": signal.signal_type.value,
                        "signal_strength": signal.signal_strength.value,
                        "confidence_score": signal.confidence_score,
                        "target_price": float(signal.target_price) if signal.target_price else None,
                        "stop_loss": float(signal.stop_loss) if signal.stop_loss else None,
                        "take_profit": float(signal.take_profit) if signal.take_profit else None,
                        "generated_at": signal.generated_at.isoformat(),
                        "valid_until": signal.valid_until.isoformat() if signal.valid_until else None,
                        "model_version": signal.model_version,
                        "politician_activity_count": signal.politician_activity_count,
                        "total_transaction_volume": float(signal.total_transaction_volume) if signal.total_transaction_volume else None,
                        "buy_sell_ratio": signal.buy_sell_ratio,
                        "features": signal.features,
                        "disclosure_ids": signal.disclosure_ids,
                        "is_active": signal.is_active,
                        "notes": signal.notes,
                    }

                    db.client.table("trading_signals").insert(data).execute()
                except Exception as e:
                    st.warning(f"Failed to save signal for {signal.ticker}: {e}")

            st.session_state.signals_data = signals
            st.session_state.signals_generated = True
            st.success(f"✅ Generated {len(signals)} signals meeting confidence threshold!")

        except Exception as e:
            st.error(f"Error generating signals: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

# Display active signals
st.markdown("---")
st.markdown("### Active Trading Signals")

try:
    from politician_trading.database.database import SupabaseClient
    from politician_trading.config import SupabaseConfig

    config = SupabaseConfig.from_env()
    db = SupabaseClient(config)

    # Fetch active signals
    query = db.client.table("trading_signals").select("*")
    query = query.eq("is_active", True)
    query = query.order("confidence_score", desc=True)
    query = query.limit(100)

    response = query.execute()
    signals = response.data

    # Convert all UUIDs to strings immediately
    for signal in signals:
        if signal.get("id"):
            signal["id"] = str(signal["id"])

    if signals:
        # Display count and filters
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Signals", len(signals))
        with col2:
            buy_signals = len([s for s in signals if s["signal_type"] in ["buy", "strong_buy"]])
            st.metric("Buy Signals", buy_signals)
        with col3:
            sell_signals = len([s for s in signals if s["signal_type"] in ["sell", "strong_sell"]])
            st.metric("Sell Signals", sell_signals)
        with col4:
            hold_signals = len([s for s in signals if s["signal_type"] == "hold"])
            st.metric("Hold Signals", hold_signals)

        # Filter options
        st.markdown("### Filter Signals")
        col1, col2 = st.columns(2)

        with col1:
            signal_type_filter = st.multiselect(
                "Signal Type",
                options=["buy", "strong_buy", "sell", "strong_sell", "hold"],
                default=["buy", "strong_buy", "sell", "strong_sell"]
            )

        with col2:
            min_confidence_display = st.slider(
                "Minimum Confidence (Display)",
                min_value=0.0,
                max_value=1.0,
                value=0.0,
                step=0.05
            )

        # Filter signals
        filtered_signals = [
            s for s in signals
            if s["signal_type"] in signal_type_filter
            and s["confidence_score"] >= min_confidence_display
        ]

        # Display signals table
        if filtered_signals:
            df = pd.DataFrame(filtered_signals)

            # Format for display
            display_df = df[[
                "ticker", "signal_type", "signal_strength", "confidence_score",
                "politician_activity_count", "buy_sell_ratio", "target_price", "generated_at"
            ]].copy()

            # Format columns
            display_df["confidence_score"] = display_df["confidence_score"].apply(lambda x: f"{x:.1%}")
            display_df["buy_sell_ratio"] = display_df["buy_sell_ratio"].apply(lambda x: f"{x:.2f}")
            display_df["target_price"] = display_df["target_price"].apply(lambda x: f"${x:.2f}" if x else "N/A")
            display_df["generated_at"] = pd.to_datetime(display_df["generated_at"]).dt.strftime("%Y-%m-%d %H:%M")

            # Rename columns
            display_df.columns = ["Ticker", "Signal", "Strength", "Confidence", "Politicians", "B/S Ratio", "Target", "Generated"]

            # Color-code signal types
            def color_signal(row):
                if row["Signal"] in ["buy", "strong_buy"]:
                    return ["background-color: #d4edda"] * len(row)
                elif row["Signal"] in ["sell", "strong_sell"]:
                    return ["background-color: #f8d7da"] * len(row)
                else:
                    return ["background-color: #fff3cd"] * len(row)

            st.dataframe(display_df, use_container_width=True)

            # Signal distribution chart
            st.markdown("### Signal Distribution")

            col1, col2 = st.columns(2)

            with col1:
                # Signal type distribution
                signal_counts = df["signal_type"].value_counts()
                fig = px.pie(
                    values=signal_counts.values,
                    names=signal_counts.index,
                    title="Signal Types",
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Confidence distribution
                fig = px.histogram(
                    df,
                    x="confidence_score",
                    nbins=20,
                    title="Confidence Distribution",
                    labels={"confidence_score": "Confidence Score"}
                )
                st.plotly_chart(fig, use_container_width=True)

            # Top signals
            st.markdown("### 🏆 Top 10 Signals by Confidence")

            top_signals = df.nlargest(10, "confidence_score")

            for idx, signal in top_signals.iterrows():
                with st.expander(f"**{signal['ticker']}** - {signal['signal_type'].upper()} ({signal['confidence_score']:.1%} confidence)"):
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Signal", signal['signal_type'].upper())
                    with col2:
                        st.metric("Confidence", f"{signal['confidence_score']:.1%}")
                    with col3:
                        st.metric("Politicians", signal['politician_activity_count'])
                    with col4:
                        st.metric("B/S Ratio", f"{signal['buy_sell_ratio']:.2f}")

                    if signal.get('target_price'):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Target Price", f"${signal['target_price']:.2f}")
                        with col2:
                            if signal.get('stop_loss'):
                                st.metric("Stop Loss", f"${signal['stop_loss']:.2f}")
                        with col3:
                            if signal.get('take_profit'):
                                st.metric("Take Profit", f"${signal['take_profit']:.2f}")

            # Export
            st.markdown("---")
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Signals as CSV",
                data=csv,
                file_name=f"trading_signals_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

        else:
            st.info("No signals match the selected filters")

    else:
        st.info("No active signals found. Generate signals to get started!")

except Exception as e:
    st.error(f"Error loading signals: {str(e)}")
