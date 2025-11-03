"""
Database Setup and Migration Page
"""

import streamlit as st
import os
import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
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

st.set_page_config(page_title="Database Setup", page_icon="🔧", layout="wide")

# Load secrets on page load
load_all_secrets()

# Require authentication
from auth_utils import require_authentication, show_user_info
require_authentication()
show_user_info()

st.title("🔧 Database Setup & Migration")
st.markdown("Set up your database schema and run migrations")

# Check database connection
try:
    from politician_trading.database.database import SupabaseClient
    from politician_trading.config import SupabaseConfig

    config = SupabaseConfig.from_env()
    db = SupabaseClient(config)

    st.success(f"✅ Connected to Supabase: {config.url}")

except Exception as e:
    st.error(f"❌ Failed to connect to database: {str(e)}")
    st.stop()

# Check schema status
st.markdown("---")
st.markdown("### 📋 Schema Status")

def check_table_exists(table_name):
    """Check if a table exists"""
    try:
        db.client.table(table_name).select("id").limit(1).execute()
        return True
    except:
        return False

def check_column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    try:
        db.client.table(table_name).select(column_name).limit(1).execute()
        return True
    except:
        return False

# Check tables
required_tables = {
    "politicians": "Base politician information",
    "trading_disclosures": "Trading disclosure records",
    "data_pull_jobs": "Data collection job tracking",
    "trading_signals": "AI-generated trading signals",
    "trading_orders": "Executed trading orders",
    "portfolios": "Portfolio tracking",
    "positions": "Open/closed positions"
}

st.markdown("#### Tables")
all_tables_ok = True

for table, description in required_tables.items():
    exists = check_table_exists(table)
    if exists:
        st.success(f"✅ {table} - {description}")
    else:
        st.error(f"❌ {table} - {description} (MISSING)")
        all_tables_ok = False

# Check critical columns
st.markdown("#### Critical Columns")
required_columns = {
    "trading_signals": ["confidence_score", "signal_type", "ticker"],
    "trading_orders": ["trading_mode", "status", "ticker"],
    "trading_disclosures": ["asset_ticker", "asset_name"],
}

all_columns_ok = True

for table, columns in required_columns.items():
    if check_table_exists(table):
        for col in columns:
            exists = check_column_exists(table, col)
            if exists:
                st.success(f"✅ {table}.{col}")
            else:
                st.error(f"❌ {table}.{col} (MISSING)")
                all_columns_ok = False

# Migration section
st.markdown("---")
st.markdown("### 🚀 Run Migrations")

if all_tables_ok and all_columns_ok:
    st.success("✅ All tables and columns exist! Your database is up to date.")
else:
    st.warning("⚠️ Some tables or columns are missing. Run the migrations below.")

    # Read SQL files
    sql_dir = Path(__file__).parent.parent / "supabase" / "sql"

    tab1, tab2 = st.tabs(["📊 Politician Trading Schema", "💼 Trading Schema"])

    with tab1:
        st.markdown("#### Step 1: Politician Trading Schema")
        st.markdown("Creates base tables: politicians, trading_disclosures, data_pull_jobs")

        politician_schema_file = sql_dir / "politician_trading_schema.sql"
        if politician_schema_file.exists():
            with open(politician_schema_file, 'r') as f:
                politician_sql = f.read()

            with st.expander("📄 View SQL"):
                st.code(politician_sql, language="sql")

            st.markdown("""
            **To run this migration:**
            1. Go to your [Supabase Dashboard](https://supabase.com/dashboard)
            2. Click **SQL Editor** in the sidebar
            3. Click **New query**
            4. Copy the SQL above
            5. Paste and click **Run**
            """)

            # Copy button
            st.code(politician_sql, language="sql")
        else:
            st.error("SQL file not found")

    with tab2:
        st.markdown("#### Step 2: Trading Schema")
        st.markdown("Creates trading tables: trading_signals, trading_orders, portfolios, positions")

        trading_schema_file = sql_dir / "trading_schema.sql"
        if trading_schema_file.exists():
            with open(trading_schema_file, 'r') as f:
                trading_sql = f.read()

            with st.expander("📄 View SQL"):
                st.code(trading_sql, language="sql")

            st.markdown("""
            **To run this migration:**
            1. Go to your [Supabase Dashboard](https://supabase.com/dashboard)
            2. Click **SQL Editor** in the sidebar
            3. Click **New query**
            4. Copy the SQL above
            5. Paste and click **Run**
            """)

            # Copy button
            st.code(trading_sql, language="sql")
        else:
            st.error("SQL file not found")

# Quick fixes
st.markdown("---")
st.markdown("### 🔧 Quick Fixes")

col1, col2 = st.columns(2)

with col1:
    if st.button("🔄 Refresh Schema Status"):
        st.rerun()

with col2:
    st.markdown(f"[📖 Full Setup Guide](https://github.com/gwicho38/politician-trading-tracker/blob/main/docs/DATABASE_SETUP.md)")

# Database info
st.markdown("---")
st.markdown("### ℹ️ Database Info")

try:
    # Get table counts
    col1, col2, col3 = st.columns(3)

    with col1:
        if check_table_exists("politicians"):
            pols = db.client.table("politicians").select("id", count="exact").execute()
            st.metric("Politicians", pols.count or 0)

    with col2:
        if check_table_exists("trading_disclosures"):
            disc = db.client.table("trading_disclosures").select("id", count="exact").execute()
            st.metric("Disclosures", disc.count or 0)

    with col3:
        if check_table_exists("trading_signals"):
            sig = db.client.table("trading_signals").select("id", count="exact").execute()
            st.metric("Trading Signals", sig.count or 0)

except Exception as e:
    st.warning(f"Could not fetch counts: {str(e)}")

# Warning
st.markdown("---")
st.warning("""
**⚠️ Important Notes:**

- Running migrations multiple times is safe (uses `IF NOT EXISTS`)
- Always backup your data before running migrations
- If you have custom modifications, they may be lost
- The migrations create tables, indexes, and Row Level Security policies
""")
