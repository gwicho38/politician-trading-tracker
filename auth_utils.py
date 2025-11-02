"""
Authentication utilities for Streamlit app
Uses streamlit-authenticator for secure login
"""

import streamlit as st
from pathlib import Path

# Try to import streamlit_authenticator, gracefully handle if not installed
try:
    import streamlit_authenticator as stauth
    import bcrypt
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False


def load_auth_config():
    """
    Load authentication configuration from secrets.

    Returns:
        dict: Authentication configuration
    """
    # Try to load from Streamlit secrets first (for Cloud deployment)
    if hasattr(st, 'secrets') and 'auth' in st.secrets:
        # Convert to dict for easier handling
        config = {
            'enabled': st.secrets['auth'].get('enabled', True),
            'cookie': {
                'name': st.secrets['auth']['cookie']['name'],
                'key': st.secrets['auth']['cookie']['key'],
                'expiry_days': st.secrets['auth']['cookie']['expiry_days']
            },
            'credentials': {
                'usernames': dict(st.secrets['auth']['credentials']['usernames'])
            }
        }
        return config

    # Return default config if nothing found
    return {
        'enabled': False,  # Disabled by default if no config
        'cookie': {
            'name': 'politician_tracker_auth',
            'key': 'default_signature_key_change_in_production',
            'expiry_days': 30
        },
        'credentials': {
            'usernames': {}
        }
    }


def check_authentication():
    """
    Check if user is authenticated. If not, show login form.

    Returns:
        bool: True if authenticated, False otherwise
    """
    # If authentication module not available, allow access
    if not AUTH_AVAILABLE:
        return True

    # Load configuration
    config = load_auth_config()

    # Check if authentication is disabled (for development)
    if not config.get('enabled', True):
        return True

    # Initialize authenticator
    try:
        authenticator = stauth.Authenticate(
            config['credentials'],
            config['cookie']['name'],
            config['cookie']['key'],
            config['cookie']['expiry_days']
        )

        # Show login form
        name, authentication_status, username = authenticator.login()

        # Handle authentication states
        if authentication_status:
            # User is authenticated
            with st.sidebar:
                st.success(f'Welcome *{name}*')
                authenticator.logout('Logout')
            return True
        elif authentication_status == False:
            st.error('❌ Username/password is incorrect')
            return False
        elif authentication_status == None:
            st.info('👋 Please enter your username and password')
            return False

        return False
    except Exception as e:
        st.error(f"Authentication error: {e}")
        st.info("Running without authentication due to error.")
        return True  # Allow access on error to prevent lockout


def require_authentication():
    """
    Require authentication to access the page.
    Call this at the top of each page that needs authentication.
    """
    if not check_authentication():
        st.stop()
