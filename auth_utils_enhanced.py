"""
Enhanced Authentication utilities for Streamlit app
Uses Google OAuth with additional security features:
- Session tracking and logging
- Login attempt monitoring
- Concurrent session management
- Action logging integration
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import hashlib

# Import action logger for auth event tracking
try:
    from politician_trading.utils.action_logger import log_action
    ACTION_LOGGING_AVAILABLE = True
except ImportError:
    ACTION_LOGGING_AVAILABLE = False


class AuthenticationManager:
    """
    Enhanced authentication manager with security features:
    - Session tracking
    - Login attempt monitoring
    - Action logging
    - Concurrent session management
    """

    def __init__(
        self,
        max_concurrent_sessions: int = 5,
        session_timeout_minutes: int = 480,  # 8 hours
        enable_action_logging: bool = True
    ):
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

        # Initialize session state for tracking
        if 'auth_sessions' not in st.session_state:
            st.session_state.auth_sessions = {}
        if 'auth_login_attempts' not in st.session_state:
            st.session_state.auth_login_attempts = {}
        if 'auth_current_session_id' not in st.session_state:
            st.session_state.auth_current_session_id = None

    def _generate_session_id(self, email: str) -> str:
        """Generate unique session ID for a user"""
        timestamp = datetime.now().isoformat()
        return hashlib.sha256(f"{email}:{timestamp}".encode()).hexdigest()[:16]

    def _log_auth_event(
        self,
        action_type: str,
        status: str,
        user_email: Optional[str] = None,
        error_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log authentication events to action_logs table"""
        if not self.enable_action_logging:
            return

        try:
            log_action(
                action_type=action_type,
                status=status,
                user_id=user_email or "unknown",
                source="authentication",
                error_message=error_message,
                result_message=f"User {'logged in' if status == 'completed' else 'failed login'}" if not error_message else None,
                action_details=details or {}
            )
        except Exception as e:
            # Don't fail auth if logging fails
            st.warning(f"Failed to log authentication event: {e}")

    def _cleanup_expired_sessions(self):
        """Remove expired sessions"""
        current_time = datetime.now()
        sessions = st.session_state.auth_sessions

        # Remove expired sessions
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

    def _manage_concurrent_sessions(self, user_email: str):
        """Enforce concurrent session limits"""
        sessions = st.session_state.auth_sessions
        user_sessions = [
            (sid, data) for sid, data in sessions.items()
            if data.get('user_email') == user_email
        ]

        # If too many sessions, remove oldest
        if len(user_sessions) >= self.max_concurrent_sessions:
            # Sort by last activity
            user_sessions.sort(key=lambda x: x[1]['last_activity'])

            # Remove oldest sessions
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

    def _update_session_activity(self):
        """Update last activity timestamp for current session"""
        if st.session_state.auth_current_session_id:
            session_id = st.session_state.auth_current_session_id
            if session_id in st.session_state.auth_sessions:
                st.session_state.auth_sessions[session_id]['last_activity'] = datetime.now()

    def require_authentication(self) -> Optional[str]:
        """
        Require authentication to access the page.
        Enhanced version with session management and logging.

        Returns:
            Optional[str]: User email if authenticated, None if stopped
        """
        # Clean up expired sessions
        self._cleanup_expired_sessions()

        # Check if user is logged in
        if not st.user.is_logged_in:
            st.title("🔐 Authentication Required")
            st.markdown("""
            This application requires authentication to access.

            Please log in with your Google account to continue.
            """)

            # Show login button
            if st.button("🔑 Log in with Google", on_click=st.login, use_container_width=True):
                # Log login attempt
                self._log_auth_event(
                    action_type="login_attempt",
                    status="initiated",
                    details={"method": "google_oauth"}
                )

            # Stop execution - don't show the rest of the page
            st.stop()

        # User is logged in - manage session
        user_email = st.user.email

        # Create or update session
        if not st.session_state.auth_current_session_id:
            # New session
            session_id = self._generate_session_id(user_email)
            st.session_state.auth_current_session_id = session_id

            # Manage concurrent sessions
            self._manage_concurrent_sessions(user_email)

            # Store session
            st.session_state.auth_sessions[session_id] = {
                'user_email': user_email,
                'user_name': st.user.name,
                'login_time': datetime.now(),
                'last_activity': datetime.now(),
            }

            # Log successful login
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

        # Update activity timestamp
        self._update_session_activity()

        # Return user email for convenience
        return user_email

    def show_user_info(self):
        """
        Show logged-in user information in the sidebar with session details.
        """
        if st.user.is_logged_in:
            with st.sidebar:
                st.success(f"Welcome, {st.user.name}!")
                st.caption(f"📧 {st.user.email}")

                # Show session info
                session_id = st.session_state.auth_current_session_id
                if session_id and session_id in st.session_state.auth_sessions:
                    session = st.session_state.auth_sessions[session_id]
                    login_time = session['login_time']
                    last_activity = session['last_activity']

                    with st.expander("📊 Session Info", expanded=False):
                        st.caption(f"**Login:** {login_time.strftime('%H:%M:%S')}")
                        st.caption(f"**Last Active:** {last_activity.strftime('%H:%M:%S')}")

                        # Show active session count
                        user_sessions = [
                            s for s in st.session_state.auth_sessions.values()
                            if s.get('user_email') == st.user.email
                        ]
                        st.caption(f"**Active Sessions:** {len(user_sessions)}")

                # Logout button
                if st.button("🚪 Log out", on_click=self._handle_logout, use_container_width=True):
                    pass  # Handled by callback

    def _handle_logout(self):
        """Handle logout with session cleanup and logging"""
        user_email = st.user.email if st.user.is_logged_in else "unknown"
        session_id = st.session_state.auth_current_session_id

        # Log logout
        self._log_auth_event(
            action_type="logout",
            status="completed",
            user_email=user_email,
            details={"session_id": session_id}
        )

        # Remove session
        if session_id and session_id in st.session_state.auth_sessions:
            del st.session_state.auth_sessions[session_id]

        # Clear session ID
        st.session_state.auth_current_session_id = None

        # Call Streamlit logout
        st.logout()

    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about current sessions"""
        sessions = st.session_state.auth_sessions

        # Count active sessions per user
        user_session_counts = {}
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


# Global instance
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


# Convenience functions compatible with existing code
def require_authentication() -> Optional[str]:
    """
    Require authentication to access the page.
    Drop-in replacement for the basic version.

    Returns:
        Optional[str]: User email if authenticated
    """
    auth_manager = get_auth_manager()
    return auth_manager.require_authentication()


def show_user_info():
    """
    Show logged-in user information in the sidebar.
    Drop-in replacement for the basic version.
    """
    auth_manager = get_auth_manager()
    auth_manager.show_user_info()
