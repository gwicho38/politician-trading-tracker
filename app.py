"""
Politician Trading Tracker - Main Entry Point
Redirects to Data Collection page
"""

import streamlit as st

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

# Redirect directly to Data Collection page
# st.switch_page("pages/1_📥_Data_Collection.py")
