"""
Authentication System Test Page
Tests enhanced authentication features including session tracking and management
"""

import streamlit as st
from auth_utils_enhanced import get_auth_manager, require_authentication, show_user_info

st.set_page_config(page_title="Auth Test", page_icon="🧪", layout="wide")

require_authentication()
show_user_info()

st.title("🧪 Authentication System Test")

st.markdown("""
This page tests the enhanced authentication system features:
- Session tracking and unique session IDs
- Concurrent session management
- Session timeout monitoring
- Action logging integration
""")

auth_manager = get_auth_manager()

# Show session stats
st.markdown("### 📊 Session Statistics")
stats = auth_manager.get_session_stats()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Active Sessions", stats['total_active_sessions'])
with col2:
    st.metric("Unique Users", stats['unique_users'])
with col3:
    st.metric("Max Sessions/User", stats['max_concurrent_sessions'])
with col4:
    timeout_mins = int(stats['session_timeout_minutes'])
    timeout_hours = timeout_mins // 60
    st.metric("Session Timeout", f"{timeout_hours}h")

# Show current session details
st.markdown("### 🔐 Current Session")
session_id = st.session_state.auth_current_session_id
if session_id and session_id in st.session_state.auth_sessions:
    session = st.session_state.auth_sessions[session_id]

    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Session ID:** `{session_id}`")
        st.info(f"**User:** {session.get('user_name')} ({session.get('user_email')})")
    with col2:
        login_time = session.get('login_time')
        last_activity = session.get('last_activity')
        st.info(f"**Login Time:** {login_time.strftime('%Y-%m-%d %H:%M:%S')}")
        st.info(f"**Last Activity:** {last_activity.strftime('%Y-%m-%d %H:%M:%S')}")
else:
    st.warning("No active session found")

# Show all sessions
st.markdown("### 📋 All Active Sessions")
if st.session_state.auth_sessions:
    st.caption(f"Total: {len(st.session_state.auth_sessions)} sessions")

    for sid, session in st.session_state.auth_sessions.items():
        is_current = (sid == session_id)
        badge = "🟢 CURRENT" if is_current else "⚪"

        with st.expander(f"{badge} Session: `{sid}`", expanded=is_current):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**User:** {session.get('user_name')}")
                st.markdown(f"**Email:** {session.get('user_email')}")
            with col2:
                login_time = session.get('login_time')
                last_activity = session.get('last_activity')
                st.markdown(f"**Login:** {login_time.strftime('%H:%M:%S')}")
                st.markdown(f"**Last Active:** {last_activity.strftime('%H:%M:%S')}")

            # Calculate session age
            from datetime import datetime
            age = datetime.now() - login_time
            minutes = int(age.total_seconds() / 60)
            hours = minutes // 60
            mins = minutes % 60
            st.caption(f"Session age: {hours}h {mins}m")
else:
    st.info("No active sessions")

# Show user-specific sessions
st.markdown("### 👤 My Sessions")
if st.user.is_logged_in:
    user_email = st.user.email
    user_sessions = [
        (sid, data) for sid, data in st.session_state.auth_sessions.items()
        if data.get('user_email') == user_email
    ]

    st.metric("My Active Sessions", len(user_sessions))

    if len(user_sessions) > 0:
        st.caption("These are all your active sessions across different browsers/tabs:")
        for sid, session_data in user_sessions:
            is_current = (sid == session_id)
            badge = "🟢" if is_current else "⚪"
            login_time = session_data.get('login_time')
            st.caption(f"{badge} `{sid}` - Logged in at {login_time.strftime('%H:%M:%S')}")

# Testing actions
st.markdown("### 🧪 Test Actions")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Test Session Update**")
    if st.button("🔄 Update Activity Timestamp", use_container_width=True):
        auth_manager._update_session_activity()
        st.success("Activity timestamp updated!")
        st.rerun()

with col2:
    st.markdown("**Test Session Cleanup**")
    if st.button("🧹 Clean Expired Sessions", use_container_width=True):
        before_count = len(st.session_state.auth_sessions)
        auth_manager._cleanup_expired_sessions()
        after_count = len(st.session_state.auth_sessions)
        removed = before_count - after_count
        if removed > 0:
            st.success(f"Removed {removed} expired session(s)")
        else:
            st.info("No expired sessions found")
        st.rerun()

# Logout test
st.markdown("### 🚪 Logout Test")
st.warning("This will log you out and clear your current session.")
if st.button("🧪 Test Logout", type="primary", use_container_width=True):
    st.info("Logging out...")
    auth_manager._handle_logout()
    st.rerun()

# Configuration info
st.markdown("### ⚙️ Configuration")
with st.expander("View Auth Manager Configuration"):
    st.json({
        "max_concurrent_sessions": auth_manager.max_concurrent_sessions,
        "session_timeout_minutes": int(auth_manager.session_timeout.total_seconds() / 60),
        "enable_action_logging": auth_manager.enable_action_logging,
        "action_logging_available": auth_manager.enable_action_logging and True
    })
