"""
Authentication utilities for Streamlit app.

Uses Google OAuth via Streamlit's built-in authentication.
Provides both simple and enhanced authentication options.

Simple usage (for most pages):
    from auth_utils import require_authentication, optional_authentication

    # At the top of your page:
    require_authentication()  # Blocks if not logged in
    # or
    optional_authentication()  # Shows login option but allows guest access

Enhanced usage (for admin/security-sensitive pages):
    from auth_utils import get_auth_manager

    auth = get_auth_manager()
    auth.require_authentication()  # With session tracking and logging
"""

import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import streamlit as st

# Import action logger for auth event tracking
try:
    from politician_trading.utils.action_logger import log_action
    ACTION_LOGGING_AVAILABLE = True
except ImportError:
    ACTION_LOGGING_AVAILABLE = False


# =============================================================================
# Simple Authentication Functions
# =============================================================================


def require_authentication() -> Optional[str]:
    """
    Require authentication to access the page.

    Uses Streamlit's built-in Google OAuth. Call this at the top of each page
    that needs authentication. Blocks page execution if not authenticated.

    Returns:
        User email if authenticated, None if execution was stopped.

    Example:
        require_authentication()
        # Rest of your page code here - only runs if authenticated
    """
    if not st.user.is_logged_in:
        st.title("Authentication Required")
        st.markdown("""
        This application requires authentication to access.

        Please log in with your Google account to continue.
        """)
        st.button("Log in with Google", on_click=st.login, use_container_width=True)
        st.stop()

    return st.user.email


def show_user_info() -> None:
    """
    Show logged-in user information in the sidebar.

    Displays user name, email, and logout button.
    """
    if st.user.is_logged_in:
        with st.sidebar:
            st.success(f"Welcome, {st.user.name}!")
            st.caption(f"{st.user.email}")
            st.button("Log out", on_click=st.logout, use_container_width=True)


def is_authenticated() -> bool:
    """
    Check if the user is currently authenticated.

    Returns:
        True if logged in, False otherwise.
    """
    return st.user.is_logged_in


def optional_authentication() -> None:
    """
    Show authentication UI but don't require it.

    Users can browse in read-only mode without logging in.
    Shows login option in sidebar for unauthenticated users.
    """
    if st.user.is_logged_in:
        show_user_info()
    else:
        with st.sidebar:
            st.info("Browsing as guest")
            st.caption("Log in to access all features")
            st.button("Log in with Google", on_click=st.login, use_container_width=True)


# =============================================================================
# Enhanced Authentication Manager
# =============================================================================


class AuthenticationManager:
    """
    Enhanced authentication manager with security features.

    Features:
        - Session tracking
        - Login attempt monitoring
        - Action logging
        - Concurrent session management
        - Session timeout

    Usage:
        auth = get_auth_manager()
        user_email = auth.require_authentication()
        auth.show_user_info()
    """

    def __init__(
        self,
        max_concurrent_sessions: int = 5,
        session_timeout_minutes: int = 480,  # 8 hours
        enable_action_logging: bool = True
    ) -> None:
        """
        Initialize authentication manager.

        Args:
            max_concurrent_sessions: Maximum concurrent sessions per user
            session_timeout_minutes: Session timeout in minutes
            enable_action_logging: Whether to log auth events to action_logs
        """
        self.max_concurrent_sessions = max_concurrent_sessions
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.enable_action_logging = enable_action_logging and ACTION_LOGGING_AVAILABLE
        self._ensure_session_state_initialized()

    def _ensure_session_state_initialized(self) -> None:
        """Ensure session state variables are initialized."""
        if 'auth_sessions' not in st.session_state:
            st.session_state.auth_sessions = {}
        if 'auth_login_attempts' not in st.session_state:
            st.session_state.auth_login_attempts = {}
        if 'auth_current_session_id' not in st.session_state:
            st.session_state.auth_current_session_id = None

    def _generate_session_id(self, email: str) -> str:
        """Generate unique session ID for a user."""
        timestamp = datetime.now().isoformat()
        return hashlib.sha256(f"{email}:{timestamp}".encode()).hexdigest()[:16]

    def _log_auth_event(
        self,
        action_type: str,
        status: str,
        user_email: Optional[str] = None,
        error_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log authentication events to action_logs table."""
        if not self.enable_action_logging:
            return

        try:
            log_action(
                action_type=action_type,
                status=status,
                user_id=user_email or "unknown",
                source="authentication",
                error_message=error_message,
                result_message=(
                    f"User {'logged in' if status == 'completed' else 'failed login'}"
                    if not error_message else None
                ),
                action_details=details or {}
            )
        except Exception as e:
            # Don't fail auth if logging fails
            st.warning(f"Failed to log authentication event: {e}")

    def _cleanup_expired_sessions(self) -> None:
        """Remove expired sessions."""
        self._ensure_session_state_initialized()
        current_time = datetime.now()
        sessions = st.session_state.auth_sessions

        expired = []
        for session_id, session_data in sessions.items():
            if current_time - session_data['last_activity'] > self.session_timeout:
                expired.append(session_id)

        for session_id in expired:
            user_email = sessions[session_id].get('user_email')
            del sessions[session_id]
            self._log_auth_event(
                action_type="session_timeout",
                status="completed",
                user_email=user_email,
                details={"session_id": session_id, "reason": "timeout"}
            )

    def _manage_concurrent_sessions(self, user_email: str) -> None:
        """Enforce concurrent session limits."""
        self._ensure_session_state_initialized()
        sessions = st.session_state.auth_sessions
        user_sessions = [
            (sid, data) for sid, data in sessions.items()
            if data.get('user_email') == user_email
        ]

        if len(user_sessions) >= self.max_concurrent_sessions:
            user_sessions.sort(key=lambda x: x[1]['last_activity'])
            sessions_to_remove = len(user_sessions) - self.max_concurrent_sessions + 1

            for i in range(sessions_to_remove):
                session_id = user_sessions[i][0]
                del sessions[session_id]
                self._log_auth_event(
                    action_type="session_terminated",
                    status="completed",
                    user_email=user_email,
                    details={
                        "session_id": session_id,
                        "reason": "concurrent_session_limit"
                    }
                )

    def _update_session_activity(self) -> None:
        """Update last activity timestamp for current session."""
        self._ensure_session_state_initialized()
        session_id = st.session_state.auth_current_session_id
        if session_id and session_id in st.session_state.auth_sessions:
            st.session_state.auth_sessions[session_id]['last_activity'] = datetime.now()

    def require_authentication(self) -> Optional[str]:
        """
        Require authentication with session management and logging.

        Returns:
            User email if authenticated, None if stopped.
        """
        self._ensure_session_state_initialized()
        self._cleanup_expired_sessions()

        if not st.user.is_logged_in:
            st.title("Authentication Required")
            st.markdown("""
            This application requires authentication to access.

            Please log in with your Google account to continue.
            """)

            if st.button("Log in with Google", on_click=st.login, use_container_width=True):
                self._log_auth_event(
                    action_type="login_attempt",
                    status="initiated",
                    details={"method": "google_oauth"}
                )

            st.stop()

        user_email = st.user.email

        if not st.session_state.auth_current_session_id:
            session_id = self._generate_session_id(user_email)
            st.session_state.auth_current_session_id = session_id
            self._manage_concurrent_sessions(user_email)

            st.session_state.auth_sessions[session_id] = {
                'user_email': user_email,
                'user_name': st.user.name,
                'login_time': datetime.now(),
                'last_activity': datetime.now(),
            }

            self._log_auth_event(
                action_type="login_success",
                status="completed",
                user_email=user_email,
                details={
                    "session_id": session_id,
                    "user_name": st.user.name,
                    "method": "google_oauth"
                }
            )

        self._update_session_activity()
        return user_email

    def show_user_info(self) -> None:
        """Show user info with session details."""
        self._ensure_session_state_initialized()
        if st.user.is_logged_in:
            with st.sidebar:
                st.success(f"Welcome, {st.user.name}!")
                st.caption(f"{st.user.email}")

                session_id = st.session_state.auth_current_session_id
                if session_id and session_id in st.session_state.auth_sessions:
                    session = st.session_state.auth_sessions[session_id]
                    login_time = session['login_time']
                    last_activity = session['last_activity']

                    with st.expander("Session Info", expanded=False):
                        st.caption(f"**Login:** {login_time.strftime('%H:%M:%S')}")
                        st.caption(f"**Last Active:** {last_activity.strftime('%H:%M:%S')}")

                        user_sessions = [
                            s for s in st.session_state.auth_sessions.values()
                            if s.get('user_email') == st.user.email
                        ]
                        st.caption(f"**Active Sessions:** {len(user_sessions)}")

                if st.button("Log out", on_click=self._handle_logout, use_container_width=True):
                    pass

    def _handle_logout(self) -> None:
        """Handle logout with session cleanup and logging."""
        user_email = st.user.email if st.user.is_logged_in else "unknown"
        session_id = st.session_state.auth_current_session_id

        self._log_auth_event(
            action_type="logout",
            status="completed",
            user_email=user_email,
            details={"session_id": session_id}
        )

        if session_id and session_id in st.session_state.auth_sessions:
            del st.session_state.auth_sessions[session_id]

        st.session_state.auth_current_session_id = None
        st.logout()

    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about current sessions."""
        self._ensure_session_state_initialized()
        sessions = st.session_state.auth_sessions

        user_session_counts: Dict[str, int] = {}
        for session_data in sessions.values():
            email = session_data.get('user_email')
            user_session_counts[email] = user_session_counts.get(email, 0) + 1

        return {
            "total_active_sessions": len(sessions),
            "unique_users": len(user_session_counts),
            "users": user_session_counts,
            "max_concurrent_sessions": self.max_concurrent_sessions,
            "session_timeout_minutes": self.session_timeout.total_seconds() / 60
        }


# =============================================================================
# Global Instance
# =============================================================================

_auth_manager: Optional[AuthenticationManager] = None


def get_auth_manager(
    max_concurrent_sessions: int = 5,
    session_timeout_minutes: int = 480,
    enable_action_logging: bool = True
) -> AuthenticationManager:
    """
    Get or create the global authentication manager.

    Args:
        max_concurrent_sessions: Maximum concurrent sessions per user
        session_timeout_minutes: Session timeout in minutes
        enable_action_logging: Whether to log auth events

    Returns:
        AuthenticationManager instance
    """
    global _auth_manager

    if _auth_manager is None:
        _auth_manager = AuthenticationManager(
            max_concurrent_sessions=max_concurrent_sessions,
            session_timeout_minutes=session_timeout_minutes,
            enable_action_logging=enable_action_logging
        )

    return _auth_manager


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Simple functions
    "require_authentication",
    "show_user_info",
    "is_authenticated",
    "optional_authentication",
    # Enhanced authentication
    "AuthenticationManager",
    "get_auth_manager",
]
