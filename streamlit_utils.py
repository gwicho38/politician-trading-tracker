"""
Streamlit utility functions for loading secrets and configuration
"""

import streamlit as st
import os


def load_secret(key, section=None, default=None):
    """
    Load secret from Streamlit secrets or environment variables.

    Args:
        key: The key name (e.g., "SUPABASE_URL")
        section: Optional section in st.secrets (e.g., "database")
        default: Default value if not found

    Returns:
        The secret value or default
    """
    # First try st.secrets (for Streamlit Cloud)
    if hasattr(st, 'secrets'):
        try:
            if section:
                return st.secrets.get(section, {}).get(key, os.getenv(key, default))
            else:
                return st.secrets.get(key, os.getenv(key, default))
        except:
            pass

    # Fall back to environment variable (for local development)
    return os.getenv(key, default)


def load_all_secrets():
    """Load all secrets from Streamlit secrets into environment variables"""
    if hasattr(st, 'secrets'):
        try:
            # Database secrets
            for key in ['SUPABASE_URL', 'SUPABASE_ANON_KEY', 'SUPABASE_SERVICE_KEY']:
                value = load_secret(key, 'database')
                if value:
                    os.environ[key] = value

            # Alpaca secrets
            for key in ['ALPACA_API_KEY', 'ALPACA_SECRET_KEY', 'ALPACA_PAPER', 'ALPACA_BASE_URL']:
                value = load_secret(key, 'alpaca')
                if value:
                    os.environ[key] = value

            # API secrets
            for key in ['QUIVER_API_KEY', 'UK_COMPANIES_HOUSE_API_KEY']:
                value = load_secret(key, 'apis')
                if value:
                    os.environ[key] = value

            # Trading config
            for key in ['TRADING_MIN_CONFIDENCE', 'TRADING_AUTO_EXECUTE']:
                value = load_secret(key, 'trading')
                if value:
                    os.environ[key] = value

            # Risk config
            for key in ['RISK_MAX_POSITION_SIZE_PCT', 'RISK_MAX_PORTFOLIO_RISK_PCT',
                       'RISK_MAX_TOTAL_EXPOSURE_PCT', 'RISK_MAX_POSITIONS']:
                value = load_secret(key, 'risk')
                if value:
                    os.environ[key] = value

            # Scraping config
            for key in ['SCRAPING_DELAY', 'MAX_RETRIES', 'TIMEOUT', 'USER_AGENT']:
                value = load_secret(key, 'scraping')
                if value:
                    os.environ[key] = value

            # Features config
            for key in ['ENABLE_US_CONGRESS', 'ENABLE_UK_PARLIAMENT', 'ENABLE_EU_PARLIAMENT',
                       'ENABLE_US_STATES', 'ENABLE_CALIFORNIA']:
                value = load_secret(key, 'features')
                if value:
                    os.environ[key] = value

            # Monitoring config
            for key in ['ENABLE_MONITORING', 'LOG_LEVEL']:
                value = load_secret(key, 'monitoring')
                if value:
                    os.environ[key] = value
        except Exception as e:
            # Silently fail if secrets not available
            pass
