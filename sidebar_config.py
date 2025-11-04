"""
Sidebar configuration for wider default width
"""
import streamlit as st


def apply_sidebar_styling():
    """Apply custom CSS to make sidebar 30% wider"""
    st.markdown("""
    <style>
    /* Wider sidebar - 30% increase from default 21rem to ~27rem */
    [data-testid="stSidebar"] {
        min-width: 27rem !important;
        max-width: 27rem !important;
    }

    /* Adjust main content margin to accommodate wider sidebar */
    [data-testid="stSidebar"][aria-expanded="true"] + div [data-testid="stVerticalBlock"] {
        margin-left: 27rem !important;
    }

    /* Ensure sidebar content has proper padding */
    [data-testid="stSidebar"] > div:first-child {
        width: 27rem !important;
    }

    /* Mobile responsive - collapse to normal size on small screens */
    @media (max-width: 768px) {
        [data-testid="stSidebar"] {
            min-width: 21rem !important;
            max-width: 21rem !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
