"""
Integration helper for optional `streamlit-hotkeys` support.
This module registers global hotkeys for easy navigation.

Hotkeys implemented:
- CMD+K / CTRL+K : Open command palette
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
from command_palette import get_command_palette, toggle_command_palette

HOTKEYS_SESSION_KEY = "_hotkeys_target_page"


def register_hotkeys() -> None:
    """Attempt to register hotkeys using `streamlit-hotkeys` if present.

    If the library is missing, the function shows a brief sidebar
    instruction with install steps (so the app keeps working).
    """
    try:
        from streamlit_hotkeys import activate, hk, pressed
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
        # Register hotkeys using hk() dicts
        activate(
            # Command palette
            hk("palette", "k", meta=True, help="Open command palette (Mac)"),
            hk("palette", "k", ctrl=True, help="Open command palette (Win/Linux)"),
            # Page navigation
            hk("data", "d", help="Go to Data Collection"),
            hk("signals", "t", help="Go to Trading Signals"),
            hk("operations", "o", help="Go to Trading Operations"),
            hk("portfolio", "p", help="Go to Portfolio"),
            hk("jobs", "j", help="Go to Scheduled Jobs"),
            hk("settings", "s", help="Go to Settings"),
            hk("logs", "l", help="Go to Action Logs"),
            hk("auth", "a", help="Go to Auth Test"),
            key="global"
        )

        # Check for pressed keys and navigate/act
        if pressed("palette"):
            # Toggle command palette
            toggle_command_palette()
            st.rerun()
        elif pressed("data"):
            st.switch_page("1_📥_Data_Collection.py")
        elif pressed("signals"):
            st.switch_page("2_🎯_Trading_Signals.py")
        elif pressed("operations"):
            st.switch_page("3_💼_Trading_Operations.py")
        elif pressed("portfolio"):
            st.switch_page("4_📈_Portfolio.py")
        elif pressed("jobs"):
            st.switch_page("5_⏰_Scheduled_Jobs.py")
        elif pressed("settings"):
            st.switch_page("6_⚙️_Settings.py")
        elif pressed("logs"):
            st.switch_page("8_📋_Action_Logs.py")
        elif pressed("auth"):
            st.switch_page("99_🧪_Auth_Test.py")

        # Render command palette if open
        palette = get_command_palette()
        palette.render()

        # Show hotkeys legend in sidebar
        with st.sidebar:
            with st.expander("⌨️ Keyboard Shortcuts", expanded=False):
                st.markdown("""
                - **CMD/CTRL + K** - Command Palette
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
