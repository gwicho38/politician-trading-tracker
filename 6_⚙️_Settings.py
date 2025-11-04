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

# Import user API keys manager
from user_api_keys import get_user_api_keys_manager

# Get current user info
user_email = st.user.email if st.user.is_logged_in else None
user_name = st.user.name if st.user.is_logged_in else None

# API Key Configuration Section (Most Important - Put First)
st.markdown("### 🔑 Alpaca API Configuration")
st.markdown("Connect your Alpaca trading account to execute trades")

# Get user's existing keys
keys_manager = get_user_api_keys_manager()
user_keys = keys_manager.get_user_keys(user_email) if user_email else None

tab1, tab2 = st.tabs(["📝 Paper Trading", "💰 Live Trading"])

with tab1:
    st.info("**Paper trading** uses simulated funds - perfect for testing strategies without risking real money")

    st.markdown("""
    **Getting Started:**
    1. Sign up for a free Alpaca account at [alpaca.markets](https://alpaca.markets/)
    2. Navigate to **Paper Trading** section in your dashboard
    3. Generate your Paper API keys
    4. Enter them below
    """)

    # Show existing validation status
    if user_keys and user_keys.get("paper_validated_at"):
        st.success(f"✅ Paper trading keys validated on {user_keys['paper_validated_at'][:10]}")

    # Input fields
    paper_api_key = st.text_input(
        "Paper API Key",
        type="password",
        placeholder="PK...",
        help="Your Alpaca paper trading API key (starts with 'PK')",
        value="" if not user_keys else "••••••••••••••••" if user_keys.get("paper_api_key") else ""
    )

    paper_secret_key = st.text_input(
        "Paper Secret Key",
        type="password",
        placeholder="Enter your paper secret key",
        help="Your Alpaca paper trading secret key",
        value="" if not user_keys else "••••••••••••••••" if user_keys.get("paper_secret_key") else ""
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🧪 Test Connection", key="test_paper", use_container_width=True):
            if not paper_api_key or paper_api_key.startswith("••"):
                st.warning("Please enter your API keys first")
            else:
                with st.spinner("Testing connection..."):
                    result = keys_manager.validate_and_save_keys(
                        user_email=user_email,
                        user_name=user_name,
                        api_key=paper_api_key,
                        secret_key=paper_secret_key,
                        is_paper=True
                    )

                    if result["valid"]:
                        st.success(result["message"])
                        account = result.get("account_info", {})
                        st.markdown(f"""
                        **Account Status:** {account.get('status', 'N/A')}
                        **Buying Power:** ${float(account.get('buying_power', 0)):,.2f}
                        **Portfolio Value:** ${float(account.get('portfolio_value', 0)):,.2f}
                        """)
                        st.rerun()
                    else:
                        st.error(result["message"])
                        if "error" in result:
                            with st.expander("Error Details"):
                                st.code(result["error"])

    with col2:
        if st.button("💾 Save Keys", key="save_paper", use_container_width=True):
            if not paper_api_key or not paper_secret_key or paper_api_key.startswith("••"):
                st.warning("Please enter both API key and secret key")
            else:
                success = keys_manager.save_user_keys(
                    user_email=user_email,
                    user_name=user_name,
                    paper_api_key=paper_api_key,
                    paper_secret_key=paper_secret_key,
                )

                if success:
                    st.success("✅ Paper trading keys saved!")
                    st.info("💡 Use 'Test Connection' to validate your keys")
                    st.rerun()
                else:
                    st.error("Failed to save keys")

with tab2:
    st.warning("⚠️ **Live Trading** - Real money will be used!")

    # Check subscription status
    has_access = keys_manager.has_live_access(user_email) if user_email else False

    if not has_access:
        st.error("🔒 Live trading requires a paid subscription (Basic or Pro tier)")
        st.markdown("""
        **To enable live trading:**
        1. Go to the **[Subscription](/Subscription)** page
        2. Upgrade to Basic ($9.99/month) or Pro ($29.99/month)
        3. Return here to configure your live API keys
        """)
        st.stop()

    st.markdown("""
    **Before you start:**
    1. Create an Alpaca account at [alpaca.markets](https://alpaca.markets/)
    2. **Complete identity verification** (required for live trading)
    3. **Fund your account** (minimum $500 for margin, or $0 for cash account)
    4. Generate **live** API keys (not paper keys!)
    5. Enter them below

    ⚠️ **Important:** Your money stays in your Alpaca account. This app only executes trades on your behalf.
    """)

    # Show existing validation status
    if user_keys and user_keys.get("live_validated_at"):
        st.success(f"✅ Live trading keys validated on {user_keys['live_validated_at'][:10]}")

    # Input fields
    live_api_key = st.text_input(
        "Live API Key",
        type="password",
        placeholder="AK...",
        help="Your Alpaca live trading API key (starts with 'AK')",
        value="" if not user_keys else "••••••••••••••••" if user_keys.get("live_api_key") else ""
    )

    live_secret_key = st.text_input(
        "Live Secret Key",
        type="password",
        placeholder="Enter your live secret key",
        help="Your Alpaca live trading secret key",
        value="" if not user_keys else "••••••••••••••••" if user_keys.get("live_secret_key") else ""
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🧪 Test Connection", key="test_live", use_container_width=True):
            if not live_api_key or live_api_key.startswith("••"):
                st.warning("Please enter your API keys first")
            else:
                with st.spinner("Testing connection to LIVE account..."):
                    result = keys_manager.validate_and_save_keys(
                        user_email=user_email,
                        user_name=user_name,
                        api_key=live_api_key,
                        secret_key=live_secret_key,
                        is_paper=False
                    )

                    if result["valid"]:
                        st.success(result["message"])
                        account = result.get("account_info", {})
                        st.markdown(f"""
                        **Account Status:** {account.get('status', 'N/A')}
                        **Buying Power:** ${float(account.get('buying_power', 0)):,.2f}
                        **Portfolio Value:** ${float(account.get('portfolio_value', 0)):,.2f}
                        """)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(result["message"])
                        if "error" in result:
                            with st.expander("Error Details"):
                                st.code(result["error"])

    with col2:
        if st.button("💾 Save Keys", key="save_live", use_container_width=True):
            if not live_api_key or not live_secret_key or live_api_key.startswith("••"):
                st.warning("Please enter both API key and secret key")
            else:
                success = keys_manager.save_user_keys(
                    user_email=user_email,
                    user_name=user_name,
                    live_api_key=live_api_key,
                    live_secret_key=live_secret_key,
                )

                if success:
                    st.success("✅ Live trading keys saved!")
                    st.info("💡 Use 'Test Connection' to validate your keys")
                    st.rerun()
                else:
                    st.error("Failed to save keys")

# Security best practices
with st.expander("🔒 Security Best Practices"):
    st.markdown("""
    **Protecting Your API Keys:**
    - ✅ Your keys are encrypted before being stored in the database
    - ✅ Keys are tied to your email address (only you can access them)
    - ✅ We never see or log your API keys
    - ✅ Rotate your keys regularly (generate new ones in Alpaca dashboard)

    **Recommended Security:**
    1. Enable 2FA on your Alpaca account
    2. Use read-only keys if you only want to monitor (not trade)
    3. Revoke old keys when generating new ones
    4. Never share your secret keys with anyone

    **If Your Keys are Compromised:**
    1. Go to [Alpaca Dashboard](https://app.alpaca.markets/)
    2. Revoke the compromised keys immediately
    3. Generate new API keys
    4. Update them here
    """)

st.markdown("---")

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
