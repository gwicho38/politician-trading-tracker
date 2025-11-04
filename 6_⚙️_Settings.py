"""
Settings Page - Configuration and system settings
"""

import streamlit as st
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

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")

# Load secrets on page load
load_all_secrets()

# Require authentication
from auth_utils import require_authentication, show_user_info
require_authentication()
show_user_info()

st.title("⚙️ Settings & Configuration")
st.markdown("Configure your trading system and manage settings")

# Environment configuration
st.markdown("### 🔧 Environment Configuration")

with st.expander("Database Configuration", expanded=False):
    st.markdown("**Supabase**")

    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_ANON_KEY", "")

    if supabase_url and supabase_key:
        st.success("✅ Supabase configured")
        st.markdown(f"- **URL**: `{supabase_url[:30]}...`")
        st.markdown(f"- **API Key**: `{'*' * 20}` (hidden)")
    else:
        st.warning("⚠️ Supabase not configured")
        st.markdown("Configure in Streamlit secrets or environment variables")

with st.expander("Trading API Configuration", expanded=False):
    st.markdown("**Alpaca Markets**")
    st.markdown("[Sign up for Alpaca](https://alpaca.markets/)")

    alpaca_key = os.getenv("ALPACA_API_KEY", "")
    alpaca_secret = os.getenv("ALPACA_SECRET_KEY", "")
    alpaca_paper = os.getenv("ALPACA_PAPER", "true") == "true"

    if alpaca_key and alpaca_secret:
        st.success(f"✅ Alpaca configured ({'Paper' if alpaca_paper else 'Live'} mode)")
        st.markdown(f"- **API Key**: `{'*' * 20}` (hidden)")
        st.markdown(f"- **Secret Key**: `{'*' * 20}` (hidden)")
        st.markdown(f"- **Mode**: {'📝 Paper Trading' if alpaca_paper else '💰 Live Trading'}")
    else:
        st.warning("⚠️ Alpaca not configured - trading features disabled")
        st.markdown("Configure in Streamlit secrets or environment variables")

with st.expander("Optional API Keys", expanded=False):
    st.markdown("**QuiverQuant** (for enhanced Congress trading data)")
    quiver_key = os.getenv("QUIVER_API_KEY", "")

    if quiver_key:
        st.success("✅ QuiverQuant configured")
        st.markdown(f"- **API Key**: `{'*' * 20}` (hidden)")
    else:
        st.info("ℹ️ QuiverQuant not configured (optional)")
        st.markdown("Sign up at [QuiverQuant](https://www.quiverquant.com/)")

# Trading configuration
st.markdown("---")
st.markdown("### 📊 Trading Configuration")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Signal Generation")

    signal_lookback = st.number_input(
        "Default lookback period (days)",
        min_value=7,
        max_value=365,
        value=int(os.getenv("SIGNAL_LOOKBACK_DAYS", "30")),
        help="Default period to analyze for signals"
    )

    signal_confidence = st.slider(
        "Minimum signal confidence",
        min_value=0.0,
        max_value=1.0,
        value=float(os.getenv("TRADING_MIN_CONFIDENCE", "0.65")),
        step=0.05,
        help="Minimum confidence threshold for signals"
    )

    fetch_market_data = st.checkbox(
        "Fetch market data by default",
        value=True,
        help="Include real-time market data in analysis"
    )

with col2:
    st.markdown("#### Risk Management")

    max_position_size = st.number_input(
        "Max position size (%)",
        min_value=1.0,
        max_value=100.0,
        value=float(os.getenv("RISK_MAX_POSITION_SIZE_PCT", "10.0")),
        step=1.0,
        help="Maximum % of portfolio per position"
    )

    max_risk_per_trade = st.number_input(
        "Max risk per trade (%)",
        min_value=0.1,
        max_value=10.0,
        value=float(os.getenv("RISK_MAX_PORTFOLIO_RISK_PCT", "2.0")),
        step=0.1,
        help="Maximum % of portfolio at risk per trade"
    )

    max_exposure = st.number_input(
        "Max total exposure (%)",
        min_value=10.0,
        max_value=100.0,
        value=float(os.getenv("RISK_MAX_TOTAL_EXPOSURE_PCT", "80.0")),
        step=5.0,
        help="Maximum % of portfolio invested"
    )

    max_positions = st.number_input(
        "Max open positions",
        min_value=1,
        max_value=100,
        value=int(os.getenv("RISK_MAX_POSITIONS", "20")),
        help="Maximum number of concurrent positions"
    )

# Data collection settings
st.markdown("---")
st.markdown("### 🔍 Data Collection Settings")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Sources")

    enable_us_congress = st.checkbox("US Congress", value=True)
    enable_uk_parliament = st.checkbox("UK Parliament", value=False)
    enable_eu_parliament = st.checkbox("EU Parliament", value=False)
    enable_us_states = st.checkbox("US State Legislatures", value=False)

with col2:
    st.markdown("#### Scraping")

    scraping_delay = st.number_input(
        "Delay between requests (seconds)",
        min_value=0.1,
        max_value=10.0,
        value=float(os.getenv("SCRAPING_DELAY", "1.0")),
        step=0.1,
        help="Delay to avoid rate limiting"
    )

    max_retries = st.number_input(
        "Max retries",
        min_value=1,
        max_value=10,
        value=int(os.getenv("MAX_RETRIES", "3")),
        help="Number of retry attempts"
    )

    timeout = st.number_input(
        "Request timeout (seconds)",
        min_value=5,
        max_value=120,
        value=int(os.getenv("TIMEOUT", "30")),
        help="Timeout for HTTP requests"
    )

# Save settings (placeholder - in real implementation would save to .env or database)
st.markdown("---")

if st.button("💾 Save Settings", width="stretch"):
    st.info("""
    💡 **Settings saved to session**

    To persist these settings:
    1. Update your `.env` file with the new values
    2. Or configure via Streamlit secrets (`.streamlit/secrets.toml`)
    3. Restart the application

    Example `.env` format:
    ```
    SUPABASE_URL=your_url
    ALPACA_API_KEY=your_key
    TRADING_MIN_CONFIDENCE=0.65
    RISK_MAX_POSITION_SIZE_PCT=10.0
    ```
    """)

# System information
st.markdown("---")
st.markdown("### 📋 System Information")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Version**")
    st.code("1.0.0")

with col2:
    st.markdown("**Python**")
    import sys
    st.code(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

with col3:
    st.markdown("**Streamlit**")
    st.code(st.__version__)

# Database status
st.markdown("---")
st.markdown("### 💾 Database Status")

try:
    from politician_trading.database.database import SupabaseClient
    from politician_trading.config import SupabaseConfig

    config = SupabaseConfig.from_env()
    db = SupabaseClient(config)

    # Test connection
    response = db.client.table("politicians").select("id", count="exact").limit(1).execute()

    st.success("✅ Database connection successful")

    # Get table counts
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        pols = db.client.table("politicians").select("id", count="exact").execute()
        st.metric("Politicians", pols.count if pols.count else 0)

    with col2:
        disc = db.client.table("trading_disclosures").select("id", count="exact").execute()
        st.metric("Disclosures", disc.count if disc.count else 0)

    with col3:
        try:
            sig = db.client.table("trading_signals").select("id", count="exact").execute()
            st.metric("Signals", sig.count if sig.count else 0)
        except:
            st.metric("Signals", "N/A")

    with col4:
        try:
            ord = db.client.table("trading_orders").select("id", count="exact").execute()
            st.metric("Orders", ord.count if ord.count else 0)
        except:
            st.metric("Orders", "N/A")

except Exception as e:
    st.error(f"❌ Database connection failed: {str(e)}")

# API status
st.markdown("---")
st.markdown("### 🔌 API Status")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Alpaca API**")
    if os.getenv("ALPACA_API_KEY"):
        try:
            from politician_trading.trading.alpaca_client import AlpacaTradingClient

            client = AlpacaTradingClient(
                api_key=os.getenv("ALPACA_API_KEY"),
                secret_key=os.getenv("ALPACA_SECRET_KEY"),
                paper=True
            )

            account = client.get_account()
            st.success(f"✅ Connected (Status: {account['status']})")

        except Exception as e:
            st.error(f"❌ Connection failed: {str(e)}")
    else:
        st.warning("⚠️ Not configured")

with col2:
    st.markdown("**Market Data (Yahoo Finance)**")
    try:
        import yfinance as yf

        # Test fetch
        ticker = yf.Ticker("AAPL")
        info = ticker.info

        st.success("✅ Available")

    except Exception as e:
        st.error(f"❌ Not available: {str(e)}")

# Documentation links
st.markdown("---")
st.markdown("### 📚 Documentation & Resources")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    **Getting Started**
    - [Trading Guide](https://github.com/gwicho38/politician-trading-tracker/blob/main/docs/TRADING_GUIDE.md)
    - [Deployment Guide](https://github.com/gwicho38/politician-trading-tracker/blob/main/docs/DEPLOYMENT.md)
    """)

with col2:
    st.markdown("""
    **API Documentation**
    - [Alpaca API](https://alpaca.markets/docs/)
    - [Supabase](https://supabase.com/docs)
    """)

with col3:
    st.markdown("""
    **Support**
    - [GitHub Issues](https://github.com/gwicho38/politician-trading-tracker/issues)
    - [Report Bug](https://github.com/gwicho38/politician-trading-tracker/issues/new)
    """)

# Disclaimer
st.markdown("---")
st.warning("""
**⚠️ Important Disclaimer**

This software is for educational and research purposes only. Trading involves substantial risk of loss.
Past performance of politicians' trades does not guarantee future results. You are solely responsible
for your trading decisions and any losses incurred.
""")
