"""
Integration helper for optional `streamlit-hotkeys` support.
This module registers global hotkeys for easy navigation.

Hotkeys implemented:
- d : go to Data Collection page
- t : go to Trading Signals page
- o : go to Trading Operations page
- p : go to Portfolio page
- j : go to Scheduled Jobs page
- s : go to Settings page
- l : go to Action Logs page
- a : go to Auth Test page

This file purposely keeps the API usage tolerant because the
`streamlit-hotkeys` package may change. If it's not available,
we show an install message in the sidebar.
"""
import streamlit as st

HOTKEYS_SESSION_KEY = "_hotkeys_target_page"


def register_hotkeys() -> None:
    """Attempt to register hotkeys using `streamlit-hotkeys` if present.

    If the library is missing, the function shows a brief sidebar
    instruction with install steps (so the app keeps working).
    """
    try:
        from streamlit_hotkeys import activate
    except Exception:
        # Friendly instruction for users/deployers to install the package
        st.sidebar.info(
            "⌨️ Hotkeys not enabled — to enable keyboard shortcuts install:\n"
            "`pip install git+https://github.com/viktor-shcherb/streamlit-hotkeys.git`\n"
            "(or add the same line to requirements.txt and reinstall)."
        )
        return

    # If the package is present, register hotkeys
    try:
        # Define hotkey callbacks
        def go_to_data_collection():
            st.switch_page("1_📥_Data_Collection.py")

        def go_to_trading_signals():
            st.switch_page("2_🎯_Trading_Signals.py")

        def go_to_trading_operations():
            st.switch_page("3_💼_Trading_Operations.py")

        def go_to_portfolio():
            st.switch_page("4_📈_Portfolio.py")

        def go_to_scheduled_jobs():
            st.switch_page("5_⏰_Scheduled_Jobs.py")

        def go_to_settings():
            st.switch_page("6_⚙️_Settings.py")

        def go_to_action_logs():
            st.switch_page("8_📋_Action_Logs.py")

        def go_to_auth_test():
            st.switch_page("99_🧪_Auth_Test.py")

        # Register hotkeys with the activate API
        activate(
            [
                ("d", "Go to Data Collection", go_to_data_collection),
                ("t", "Go to Trading Signals", go_to_trading_signals),
                ("o", "Go to Trading Operations", go_to_trading_operations),
                ("p", "Go to Portfolio", go_to_portfolio),
                ("j", "Go to Scheduled Jobs", go_to_scheduled_jobs),
                ("s", "Go to Settings", go_to_settings),
                ("l", "Go to Action Logs", go_to_action_logs),
                ("a", "Go to Auth Test", go_to_auth_test),
            ]
        )

        # Show hotkeys legend in sidebar
        with st.sidebar:
            with st.expander("⌨️ Keyboard Shortcuts", expanded=False):
                st.markdown("""
                - **D** - Data Collection
                - **T** - Trading Signals
                - **O** - Trading Operations
                - **P** - Portfolio
                - **J** - Scheduled Jobs
                - **S** - Settings
                - **L** - Action Logs
                - **A** - Auth Test
                """)

    except Exception as e:
        st.sidebar.error(f"Failed to initialize hotkeys: {e}")
