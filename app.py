"""
Politician Trading Tracker - Main Application
Uses st.Page navigation for cleaner sidebar experience
"""

import streamlit as st
from streamlit_hotkeys_integration import register_hotkeys
from sidebar_config import apply_sidebar_styling

# Enable analytics tracking
from analytics_wrapper import safe_track, ANALYTICS_AVAILABLE

# Page configuration
st.set_page_config(
    page_title="Politician Trading Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
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
        "1_📥_Data_Collection.py",
        title="Data Collection",
        icon="📥",
        default=True
    ),
    st.Page(
        "2_🎯_Trading_Signals.py",
        title="Trading Signals",
        icon="🎯"
    ),
    st.Page(
        "3_💼_Trading_Operations.py",
        title="Trading Operations",
        icon="💼"
    ),
    st.Page(
        "4_📈_Portfolio.py",
        title="Portfolio",
        icon="📈"
    ),
    st.Page(
        "5_⏰_Scheduled_Jobs.py",
        title="Scheduled Jobs",
        icon="⏰"
    ),
    st.Page(
        "6_⚙️_Settings.py",
        title="Settings",
        icon="⚙️"
    ),
    st.Page(
        "7_🔧_Database_Setup.py",
        title="Database Setup",
        icon="🔧"
    ),
    st.Page(
        "8_📋_Action_Logs.py",
        title="Action Logs",
        icon="📋"
    ),
    st.Page(
        "10_💳_Subscription.py",
        title="Subscription",
        icon="💳"
    ),
    st.Page(
        "11_🔐_Admin.py",
        title="Admin",
        icon="🔐"
    ),
    st.Page(
        "99_🧪_Auth_Test.py",
        title="Auth Test",
        icon="🧪"
    ),
]

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
