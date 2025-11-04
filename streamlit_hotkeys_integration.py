"""
Integration helper for optional `streamlit-hotkeys` support.
This module registers a few global hotkeys and falls back gracefully
when the package is not installed.

Hotkeys implemented (examples):
- d : go to Data Collection page
- s : go to Settings page
- r : refresh (rerun)

This file purposely keeps the API usage tolerant because the
`streamlit-hotkeys` package may change. If it's not available,
we show an install message in the sidebar.
"""
from typing import Any
import streamlit as st

HOTKEYS_SESSION_KEY = "_hotkeys_target_page"


def register_hotkeys() -> None:
    """Attempt to register hotkeys using `streamlit-hotkeys` if present.

    If the library is missing, the function shows a brief sidebar
    instruction with install steps (so the app keeps working).
    """
    try:
        import streamlit_hotkeys  # type: ignore
    except Exception:
        # Friendly instruction for users/deployers to install the package
        st.sidebar.info(
            "Hotkeys not enabled — to enable keyboard shortcuts install:\n"
            "pip install git+https://github.com/viktor-shcherb/streamlit-hotkeys.git\n"
            "(or add the same line to requirements.txt and reinstall)."
        )
        return

    # If the package is present, try to use a generous API surface.
    # The real package may expose different helpers; we attempt a few
    # known patterns and fall back to a safe message when the API
    # doesn't match.
    try:
        # Preferred API (if available) — many small wrappers expose a
        # `use_hotkeys` or `HotKeys` style interface. Try `use_hotkeys` first.
        if hasattr(streamlit_hotkeys, "use_hotkeys"):
            # The callback updates `st.session_state[HOTKEYS_SESSION_KEY]` so
            # the main app can react (like switching pages) on next rerun.
            def go_to(path: str) -> None:
                st.session_state[HOTKEYS_SESSION_KEY] = path

            streamlit_hotkeys.use_hotkeys(
                {
                    "d": lambda: go_to("pages/1_📥_Data_Collection.py"),
                    "s": lambda: go_to("pages/6_⚙️_Settings.py"),
                    "r": lambda: st.experimental_rerun(),
                }
            )
            return

        # Alternative API: object-oriented HotKeys
        if hasattr(streamlit_hotkeys, "HotKeys"):
            HotKeys = getattr(streamlit_hotkeys, "HotKeys")

            def go_to(path: str) -> None:
                st.session_state[HOTKEYS_SESSION_KEY] = path

            hk = HotKeys(
                {
                    "d": lambda: go_to("pages/1_📥_Data_Collection.py"),
                    "s": lambda: go_to("pages/6_⚙️_Settings.py"),
                    "r": lambda: st.experimental_rerun(),
                }
            )
            # If the HotKeys object needs to be rendered/started, try to
            # call its `render()` or `mount()` methods if present.
            if hasattr(hk, "render"):
                try:
                    hk.render()
                except Exception:
                    pass
            elif hasattr(hk, "mount"):
                try:
                    hk.mount()
                except Exception:
                    pass
            return

        # Unknown API surface — notify the user in the sidebar with guidance.
        st.sidebar.warning(
            "`streamlit-hotkeys` installed but its API is unrecognized."
            " Please check the package README for integration details."
        )

    except Exception as e:  # pragma: no cover - runtime guard
        st.sidebar.error(f"Failed to initialize hotkeys: {e}")
