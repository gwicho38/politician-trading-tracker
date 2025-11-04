"""
Authentication utilities for Streamlit app
Uses Google OAuth via Streamlit's built-in authentication
"""

import streamlit as st


def require_authentication():
    """
    Require authentication to access the page.
    Uses Streamlit's built-in Google OAuth.
    Call this at the top of each page that needs authentication.
    """
    # Check if user is logged in
    if not st.user.is_logged_in:
        st.title("🔐 Authentication Required")
        st.markdown("""
        This application requires authentication to access.

        Please log in with your Google account to continue.
        """)

        # Show login button
        st.button("🔑 Log in with Google", on_click=st.login, use_container_width=True)

        # Stop execution - don't show the rest of the page
        st.stop()


def show_user_info():
    """
    Show logged-in user information in the sidebar.
    """
    if st.user.is_logged_in:
        with st.sidebar:
            st.success(f"Welcome, {st.user.name}!")
            st.caption(f"📧 {st.user.email}")

            # Logout button
            st.button("🚪 Log out", on_click=st.logout, use_container_width=True)
