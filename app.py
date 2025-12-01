"""
Politician Trading Tracker - Main Application
Uses st.Page navigation for cleaner sidebar experience
"""

import streamlit as st

# Enable analytics tracking
from src.analytics_wrapper import ANALYTICS_AVAILABLE, safe_track

# Initialize shopping cart
from src.shopping_cart import render_shopping_cart_sidebar
from src.sidebar_config import apply_sidebar_styling
from src.streamlit_hotkeys_integration import register_hotkeys

# Page configuration
st.set_page_config(
    page_title="Politician Trading Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",  # Start collapsed, especially important for mobile
    menu_items={
        "Get help": "https://github.com/gwicho38/politician-trading-tracker#readme",
        "Report a bug": "https://github.com/gwicho38/politician-trading-tracker/issues",
        "About": "Politician Trading Tracker\n\nA Streamlit app to track politician trading activity.",
    },
)

# Apply wider sidebar styling
apply_sidebar_styling()

# Register optional hotkeys
register_hotkeys()

# Define all pages with icons
pages = [
    st.Page(
        "src/1_📥_Data_Collection.py",
        title="Data Collection",
        icon="📥",
        default=True
    ),
    st.Page(
        "src/2_🎯_Trading_Signals.py",
        title="Trading Signals",
        icon="🎯"
    ),
    st.Page(
        "src/3_💼_Trading_Operations.py",
        title="Trading Operations",
        icon="💼"
    ),
    st.Page(
        "src/4_📈_Portfolio.py",
        title="Portfolio",
        icon="📈"
    ),
    st.Page(
        "src/4.5_📋_Orders.py",
        title="Orders",
        icon="📋"
    ),
    st.Page(
        "src/5_⏰_Scheduled_Jobs.py",
        title="Scheduled Jobs",
        icon="⏰"
    ),
    st.Page(
        "src/6_⚙️_Settings.py",
        title="Settings",
        icon="⚙️"
    ),
    st.Page(
        "src/9_🛒_Cart.py",
        title="Shopping Cart",
        icon="🛒"
    ),
    st.Page(
        "src/7_🔧_Database_Setup.py",
        title="Database Setup",
        icon="🔧"
    ),
    st.Page(
        "src/8_📋_Action_Logs.py",
        title="Action Logs",
        icon="📋"
    ),
    st.Page(
        "src/10_💳_Subscription.py",
        title="Subscription",
        icon="💳"
    ),
    st.Page(
        "src/11_🔐_Admin.py",
        title="Admin",
        icon="🔐"
    ),
    st.Page(
        "src/99_🧪_Auth_Test.py",
        title="Auth Test",
        icon="🧪"
    ),
]

# Render shopping cart indicator in sidebar
render_shopping_cart_sidebar()

# Show admin badge if user is admin
from src.admin_utils import show_admin_badge

show_admin_badge()

# Add trading mode toggle in sidebar
with st.sidebar:
    st.markdown("---")

    # Initialize trading mode in session state
    if "global_trading_mode" not in st.session_state:
        st.session_state.global_trading_mode = "paper"

    # Toggle between paper and live
    current_mode = st.session_state.global_trading_mode

    # Display current mode with prominent styling
    if current_mode == "live":
        st.markdown("""
        <div style="
            padding: 12px;
            border: 3px solid #ff4b4b;
            border-radius: 8px;
            background-color: #ffe6e6;
            text-align: center;
            margin-bottom: 10px;
        ">
            <h3 style="color: #ff4b4b; margin: 0;">🔴 LIVE TRADING</h3>
            <p style="margin: 5px 0 0 0; color: #ff4b4b; font-weight: bold;">Real Money Mode</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="
            padding: 12px;
            border: 2px solid #31d843;
            border-radius: 8px;
            background-color: #e6f7e9;
            text-align: center;
            margin-bottom: 10px;
        ">
            <h3 style="color: #31d843; margin: 0;">🟢 PAPER TRADING</h3>
            <p style="margin: 5px 0 0 0; color: #31d843; font-weight: bold;">Simulated Money Mode</p>
        </div>
        """, unsafe_allow_html=True)

    # Toggle button
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📝 Paper", use_container_width=True, type="primary" if current_mode == "paper" else "secondary"):
            st.session_state.global_trading_mode = "paper"
            st.rerun()

    with col2:
        if st.button("💰 Live", use_container_width=True, type="primary" if current_mode == "live" else "secondary"):
            # Check if user has live access
            try:
                from src.auth_utils import require_authentication
                from src.user_api_keys import get_user_api_keys_manager

                if st.user.is_logged_in and isinstance(st.user.email, str):
                    keys_manager = get_user_api_keys_manager()
                    user_keys = keys_manager.get_user_keys(st.user.email)

                    if user_keys and keys_manager.has_live_access(st.user.email) and user_keys.get("live_api_key"):
                        st.session_state.global_trading_mode = "live"
                        st.rerun()
                    else:
                        st.warning("⚠️ Live trading requires a paid subscription and configured live API keys. Go to Settings.")
                else:
                    st.warning("Please log in first")
            except:
                st.warning("⚠️ Configure your API keys in Settings first")

# Create navigation and run
page = st.navigation(pages)

# Handle hotkey navigation if target page is set
if st.session_state.get("_hotkeys_target_page"):
    target = st.session_state.pop("_hotkeys_target_page")
    # Map old path format to new page titles
    page_map = {
        "pages/1_📥_Data_Collection.py": "Data Collection",
        "pages/2_🎯_Trading_Signals.py": "Trading Signals",
        "pages/3_💼_Trading_Operations.py": "Trading Operations",
        "pages/4_📈_Portfolio.py": "Portfolio",
        "pages/5_⏰_Scheduled_Jobs.py": "Scheduled Jobs",
        "pages/6_⚙️_Settings.py": "Settings",
        "pages/7_🔧_Database_Setup.py": "Database Setup",
        "pages/8_📋_Action_Logs.py": "Action Logs",
    }
    if target in page_map:
        # Find the page and navigate to it
        for p in pages:
            if p.title == page_map[target]:
                st.switch_page(p)
                break

# Run the selected page with analytics tracking
if ANALYTICS_AVAILABLE:
    with safe_track(
        save_to_json="analytics.json",
        load_from_json="analytics.json"
    ):
        page.run()
else:
    page.run()
