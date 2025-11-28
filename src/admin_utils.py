"""
Admin Access Control Utilities

Centralized admin checking for bypassing subscription and feature restrictions.
"""

import streamlit as st
import os
from typing import Optional


# Admin emails - configured via environment variable for security
def get_admin_emails() -> list[str]:
    """
    Get list of admin emails from environment variable or default.

    Returns:
        List of admin email addresses
    """
    # Try to get from environment variable
    admin_emails_str = os.environ.get("ADMIN_EMAILS", "")

    if admin_emails_str:
        # Split by comma and strip whitespace
        return [email.strip() for email in admin_emails_str.split(",") if email.strip()]

    # Fallback to default admin email
    return ["luis.e.fernandezdelavara@gmail.com"]


def is_admin(user_email: Optional[str] = None) -> bool:
    """
    Check if the given user email is an admin.

    Args:
        user_email: Email to check. If None, checks current logged-in user.

    Returns:
        True if user is admin, False otherwise
    """
    if user_email is None:
        # Check current Streamlit user
        if hasattr(st, "user") and hasattr(st.user, "email"):
            user_email = st.user.email
        else:
            # Fallback to session state
            user_email = st.session_state.get("user_email", "")

    if not user_email:
        return False

    admin_emails = get_admin_emails()
    return user_email.lower() in [email.lower() for email in admin_emails]


def require_admin():
    """
    Require admin access for the current page.
    Stops execution and shows error if user is not admin.

    Usage:
        require_admin()  # Put at top of admin-only pages
    """
    if not is_admin():
        st.error("🔐 Access Denied")
        st.warning("This page is only accessible to administrators.")
        st.stop()


def show_admin_badge():
    """
    Display an admin badge in the sidebar for admin users.
    """
    if is_admin():
        st.sidebar.markdown("""
        <div style="
            background-color: #ff4b4b;
            color: white;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
            font-weight: bold;
            margin-bottom: 10px;
        ">
            🔐 ADMIN MODE
        </div>
        """, unsafe_allow_html=True)


def get_effective_tier(actual_tier: str) -> str:
    """
    Get the effective subscription tier, considering admin override.

    Args:
        actual_tier: The user's actual subscription tier

    Returns:
        "enterprise" if admin, otherwise the actual tier
    """
    if is_admin():
        return "enterprise"
    return actual_tier


def has_admin_override() -> bool:
    """
    Check if current user has admin override enabled.
    Alias for is_admin() for clarity in conditional logic.

    Returns:
        True if user is admin and has full feature access
    """
    return is_admin()
