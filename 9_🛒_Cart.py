"""
Shopping Cart Page - View and manage trading cart
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))
if str(parent_dir / "src") not in sys.path:
    sys.path.insert(0, str(parent_dir / "src"))

# Import utilities
try:
    from streamlit_utils import load_all_secrets
except (ImportError, KeyError):
    # Fallback for different import contexts
    import importlib.util
    spec = importlib.util.spec_from_file_location("streamlit_utils", parent_dir / "streamlit_utils.py")
    streamlit_utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(streamlit_utils)
    load_all_secrets = streamlit_utils.load_all_secrets

st.set_page_config(page_title="Shopping Cart", page_icon="🛒", layout="wide")

# Load secrets on page load
load_all_secrets()

# Require authentication
from auth_utils import require_authentication, show_user_info
require_authentication()
show_user_info()

st.title("🛒 Trading Cart")
st.markdown("Review and manage your trading signals before execution")

# Render full shopping cart
from shopping_cart import render_shopping_cart
render_shopping_cart()

# Add helpful info
st.markdown("---")
st.markdown("### 💡 Tips")

col1, col2 = st.columns(2)

with col1:
    st.info("""
    **How to use the cart:**
    1. Browse signals on the Trading Signals page
    2. Add signals to cart with desired quantity
    3. Review and adjust quantities here
    4. Execute trades on the Trading Operations page
    """)

with col2:
    st.warning("""
    **Before executing:**
    - Verify you're in the correct trading mode (Paper/Live)
    - Check your buying power on Trading Operations
    - Review risk management settings
    - Confirm all quantities are correct
    """)
