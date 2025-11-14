"""
Manual test script for Supabase connection using st-supabase-connection
Run this with: uv run streamlit run tests/manual/test_supabase_connection.py
"""

import streamlit as st
from st_supabase_connection import SupabaseConnection

st.title("🗄️ Supabase Connection Test")

st.markdown(
    """
This test verifies that the Supabase connection is properly configured
using `st-supabase-connection`.
"""
)

try:
    # Test connection using secrets.toml [connections.supabase] section
    conn = st.connection(name="supabase", type=SupabaseConnection)

    st.success("✅ Successfully created Supabase connection!")

    # Display connection info
    st.markdown("### Connection Configuration")

    # Get config from secrets
    url = st.secrets.get("connections", {}).get("supabase", {}).get("url", "Not configured")
    key = st.secrets.get("connections", {}).get("supabase", {}).get("key", "Not configured")

    st.code(
        f"""
URL: {url}
Key: {key[:10]}...{key[-4:] if len(key) > 14 else 'masked'}
    """
    )

    # Test a simple query
    st.markdown("### Test Query")

    with st.spinner("Running test query..."):
        try:
            import pandas as pd

            # Try to list tables using information_schema
            # Note: st-supabase-connection returns a Supabase client, not a SQL query interface
            # We need to use RPC or query actual tables

            # Test by querying known tables
            test_tables = ["politician_trades", "action_logs", "scheduled_jobs", "user_sessions"]

            st.markdown("### Testing Table Access")

            for table in test_tables:
                try:
                    response = conn.table(table).select("*", count="exact").limit(0).execute()
                    count = response.count if hasattr(response, "count") else "Unknown"
                    st.success(f"✅ `{table}`: Accessible ({count} rows)")
                except Exception as table_err:
                    st.warning(f"⚠️ `{table}`: {str(table_err)[:100]}")

        except Exception as e:
            st.error(f"❌ Query failed: {str(e)}")
            st.exception(e)

except ImportError as e:
    st.error("❌ st-supabase-connection not installed")
    st.code("uv pip install st-supabase-connection")
    st.exception(e)

except Exception as e:
    st.error(f"❌ Connection failed: {str(e)}")
    st.markdown(
        """
    ### Troubleshooting

    1. Check that `.streamlit/secrets.toml` has:
    ```toml
    [connections.supabase]
    url = "your-supabase-url"
    key = "your-supabase-key"
    ```

    2. Verify the URL and key are correct

    3. Check that the Supabase project is active
    """
    )
    st.exception(e)

st.divider()
st.caption("Test completed. Check the results above.")
