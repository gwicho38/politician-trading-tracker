"""
Sidebar configuration for wider default width
"""
import streamlit as st


def apply_sidebar_styling():
    """Apply custom CSS to make sidebar 30% wider and adjust main content"""
    st.markdown("""
    <style>
    /* Wider sidebar - 30% increase from default 21rem to ~27rem */
    [data-testid="stSidebar"] {
        min-width: 27rem !important;
        max-width: 27rem !important;
    }

    /* Ensure sidebar content has proper padding */
    [data-testid="stSidebar"] > div:first-child {
        width: 27rem !important;
    }

    /* Adjust main content area to start after wider sidebar */
    .main .block-container {
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 100% !important;
    }

    /* When sidebar is expanded, adjust main content margin */
    [data-testid="stSidebar"][aria-expanded="true"] ~ .main .block-container {
        margin-left: 0 !important;
    }

    /* Adjust app view container to accommodate sidebar */
    .appview-container .main {
        margin-left: 27rem !important;
    }

    /* Mobile responsive - collapse to normal size on small screens */
    @media (max-width: 768px) {
        [data-testid="stSidebar"] {
            min-width: 21rem !important;
            max-width: 21rem !important;
        }

        .appview-container .main {
            margin-left: 0 !important;
        }

        .main .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
