"""
Politician Trading Tracker - Streamlit App
Main application entry point for the web interface
"""

import streamlit as st
import os
import sys
from pathlib import Path

# Add directories to path
app_dir = Path(__file__).parent
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))
if str(app_dir / "src") not in sys.path:
    sys.path.insert(0, str(app_dir / "src"))

# Import logger first
from politician_trading.utils.logger import create_logger
logger = create_logger("app")

# Import utilities
try:
    from streamlit_utils import load_all_secrets
except (ImportError, KeyError):
    # Fallback for different import contexts
    import importlib.util
    spec = object
    try:
        spec = importlib.util.spec_from_file_location("streamlit_utils", app_dir / "streamlit_utils.py")
    except:
        logger.error("Failed to import spec from file")
    streamlit_utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(streamlit_utils)
    load_all_secrets = streamlit_utils.load_all_secrets

logger.info("Politician Trading Tracker starting")

# Page configuration
st.set_page_config(
    page_title="Politician Trading Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load secrets on startup
load_all_secrets()

# Initialize scheduler (singleton pattern ensures it only starts once)
# Temporarily disabled until deployment issues are resolved
# try:
#     from politician_trading.scheduler import get_scheduler
#     scheduler = get_scheduler()
#     logger.info("Scheduler initialized", metadata={
#         "running": scheduler.is_running()
#     })
# except Exception as e:
#     logger.error("Failed to initialize scheduler", error=e)
#     # Don't fail the app if scheduler fails to start

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #666;
        text-align: center;
        margin-bottom: 3rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        padding: 1rem;
        border-radius: 0.3rem;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        padding: 1rem;
        border-radius: 0.3rem;
        margin: 1rem 0;
    }
    .danger-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        padding: 1rem;
        border-radius: 0.3rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Check environment configuration
def check_environment():
    """Check if required environment variables are set"""
    logger.debug("Checking environment configuration")

    required_vars = {
        "SUPABASE_URL": os.getenv("SUPABASE_URL"),
        "SUPABASE_ANON_KEY": os.getenv("SUPABASE_ANON_KEY"),
    }

    optional_vars = {
        "ALPACA_API_KEY": os.getenv("ALPACA_API_KEY"),
        "ALPACA_SECRET_KEY": os.getenv("ALPACA_SECRET_KEY"),
    }

    missing_required = [k for k, v in required_vars.items() if not v]
    missing_optional = [k for k, v in optional_vars.items() if not v]

    if missing_required:
        logger.error("Missing required environment variables", metadata={
            "missing_vars": missing_required
        })
    else:
        logger.info("All required environment variables present")

    if missing_optional:
        logger.warn("Missing optional environment variables", metadata={
            "missing_vars": missing_optional
        })

    return missing_required, missing_optional

# Main page
def main():
    # Header
    st.markdown('<div class="main-header">📊 Politician Trading Tracker</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Track, Analyze, and Trade Based on Politician Disclosures</div>', unsafe_allow_html=True)

    # Check environment
    missing_required, missing_optional = check_environment()

    if missing_required:
        st.markdown(f"""
        <div class="danger-box">
            <strong>⚠️ Configuration Error</strong><br>
            Missing required environment variables: {', '.join(missing_required)}<br>
            Please configure these in your .env file or Streamlit secrets.
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    if missing_optional:
        st.markdown(f"""
        <div class="warning-box">
            <strong>ℹ️ Optional Configuration</strong><br>
            Trading features disabled. To enable, set: {', '.join(missing_optional)}
        </div>
        """, unsafe_allow_html=True)

    # Welcome section
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        ### 🔍 Data Collection
        Automatically scrape and collect politician trading disclosures from:
        - US Congress (House & Senate)
        - EU Parliament
        - UK Parliament
        - US State legislatures
        """)
        if st.button("📥 Collect Data", key="collect", use_container_width=True):
            st.switch_page("pages/1_📥_Data_Collection.py")

    with col2:
        st.markdown("""
        ### 🤖 AI Signals
        Generate AI-powered trading signals using:
        - Machine Learning models
        - Heuristic analysis
        - Politician trading patterns
        - Market data integration
        """)
        if st.button("🎯 Generate Signals", key="signals", use_container_width=True):
            st.switch_page("pages/2_🎯_Trading_Signals.py")

    with col3:
        st.markdown("""
        ### 📈 Trading
        Execute trades with comprehensive features:
        - Paper & live trading
        - Risk management
        - Portfolio tracking
        - Performance analytics
        """)
        if st.button("💼 Trade Now", key="trade", use_container_width=True):
            st.switch_page("pages/3_💼_Trading_Operations.py")

    # Quick stats
    st.markdown("---")
    st.markdown("### 📊 Quick Stats")

    try:
        logger.debug("Loading database stats")
        from politician_trading.database.database import SupabaseClient
        from politician_trading.config import SupabaseConfig
        from datetime import datetime, timedelta

        config = SupabaseConfig.from_env()
        db = SupabaseClient(config)
        logger.info("Connected to database for stats")

        # Get counts
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            try:
                pols_response = db.client.table("politicians").select("id", count="exact").execute()
                count = pols_response.count if pols_response.count else 0
                st.metric("Total Politicians", count)
                logger.debug("Politicians count retrieved", metadata={"count": count})
            except Exception as e:
                st.metric("Total Politicians", "N/A")
                logger.error("Failed to get politicians count", error=e)

        with col2:
            try:
                disc_response = db.client.table("trading_disclosures").select("id", count="exact").execute()
                count = disc_response.count if disc_response.count else 0
                st.metric("Total Disclosures", count)
                logger.debug("Disclosures count retrieved", metadata={"count": count})
            except Exception as e:
                st.metric("Total Disclosures", "N/A")
                logger.error("Failed to get disclosures count", error=e)

        with col3:
            try:
                signals_response = db.client.table("trading_signals").select("id", count="exact").eq("is_active", True).execute()
                st.metric("Active Signals", signals_response.count if signals_response.count else 0)
            except:
                st.metric("Active Signals", "N/A")

        with col4:
            try:
                orders_response = db.client.table("trading_orders").select("id", count="exact").execute()
                st.metric("Total Orders", orders_response.count if orders_response.count else 0)
            except:
                st.metric("Total Orders", "N/A")

    except Exception as e:
        st.info("💡 Connect to database to see stats")

    # Features section
    st.markdown("---")
    st.markdown("### ✨ Key Features")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **Data Collection**
        - ✅ Automated scraping from multiple sources
        - ✅ Real-time disclosure tracking
        - ✅ Historical data analysis
        - ✅ Multi-jurisdiction support

        **AI-Powered Analysis**
        - ✅ Machine learning models
        - ✅ 40+ feature engineering
        - ✅ Confidence scoring
        - ✅ Price target calculation
        """)

    with col2:
        st.markdown("""
        **Trading Integration**
        - ✅ Alpaca API integration
        - ✅ Paper & live trading
        - ✅ Multiple order types
        - ✅ Real-time execution

        **Risk Management**
        - ✅ Automated position sizing
        - ✅ Stop loss placement
        - ✅ Portfolio monitoring
        - ✅ Performance tracking
        """)

    # Disclaimer
    st.markdown("---")
    st.markdown("""
    <div class="warning-box">
        <strong>⚠️ Disclaimer</strong><br>
        This software is for educational and research purposes only. Trading involves substantial
        risk of loss. Past performance of politicians' trades does not guarantee future results.
        You are solely responsible for your trading decisions.
    </div>
    """, unsafe_allow_html=True)

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 2rem 0;">
        Made with ❤️ using Streamlit |
        <a href="https://github.com/gwicho38/politician-trading-tracker" target="_blank">GitHub</a> |
        <a href="https://alpaca.markets" target="_blank">Powered by Alpaca</a>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
