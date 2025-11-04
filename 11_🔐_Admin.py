"""
Admin Dashboard - Restricted to administrator only
Shows Supabase connection status, analytics, and system diagnostics
"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
import os
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import utilities
try:
    from streamlit_utils import load_all_secrets
except (ImportError, KeyError):
    import importlib.util
    spec = importlib.util.spec_from_file_location("streamlit_utils", Path(__file__).parent / "streamlit_utils.py")
    streamlit_utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(streamlit_utils)
    load_all_secrets = streamlit_utils.load_all_secrets

# Page configuration
st.set_page_config(
    page_title="Admin Dashboard",
    page_icon="🔐",
    layout="wide"
)

# Load secrets
load_all_secrets()

# Require authentication first
from auth_utils_enhanced import require_authentication

user_email = require_authentication()

# Admin email whitelist
ADMIN_EMAILS = ["luis.e.fernandezdelavara@gmail.com"]

# Check if user is admin
if user_email not in ADMIN_EMAILS:
    st.error("🚫 Access Denied")
    st.warning("This page is restricted to administrators only.")
    st.stop()

# Admin access granted
st.success(f"✅ Admin Access Granted: {user_email}")

# Add auto-refresh
from autorefresh_config import add_refresh_controls, setup_autorefresh

enabled, interval, _ = add_refresh_controls("admin", default_enabled=False)
if enabled:
    setup_autorefresh(interval=interval, key="admin_refresh")

# Page header
st.title("🔐 Admin Dashboard")
st.caption(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.divider()

# Helper function for default insert templates (must be before tabs)
def get_default_insert_template(table_name):
    """Get default JSON template for inserting records"""
    templates = {
        "trading_disclosures": """{
  "politician_id": "uuid-of-politician",
  "transaction_date": "2025-11-04T00:00:00Z",
  "disclosure_date": "2025-11-04T00:00:00Z",
  "asset_name": "Apple Inc. - Common Stock",
  "asset_ticker": "AAPL",
  "asset_type": "stock",
  "transaction_type": "purchase",
  "amount_range_min": 15001,
  "amount_range_max": 50000,
  "status": "active",
  "source": "us_senate",
  "source_url": "https://efdsearch.senate.gov/..."
}""",
        "politicians": """{
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "role": "Senator",
  "party": "Democratic",
  "state_or_country": "California",
  "source": "us_senate"
}""",
        "action_logs": """{
  "action_type": "test_action",
  "status": "completed",
  "user_id": "test_user",
  "source": "manual_entry",
  "result_message": "Test action completed successfully"
}""",
        "scheduled_jobs": """{
  "job_name": "test_job",
  "job_type": "data_collection",
  "schedule": "0 0 * * *",
  "is_active": true,
  "description": "Test scheduled job"
}""",
        "user_sessions": """{
  "session_id": "test_session_123",
  "user_email": "test@example.com",
  "is_active": true
}"""
    }
    return templates.get(table_name, "{}")

# Tabs for different admin sections
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Analytics",
    "🗄️ Supabase",
    "🗂️ Database CRUD",
    "⚙️ System Info",
    "👥 Users",
    "📝 Logs"
])

# Tab 1: Analytics
with tab1:
    st.subheader("📊 Application Analytics")

    try:
        import streamlit_analytics

        st.info("📈 Analytics tracking is available. Add `?analytics=on` to URL to view detailed analytics.")

        # Show analytics controls
        col1, col2 = st.columns(2)

        with col1:
            if st.button("📊 Start Tracking"):
                streamlit_analytics.start_tracking()
                st.success("Analytics tracking started")

        with col2:
            if st.button("🛑 Stop Tracking"):
                streamlit_analytics.stop_tracking()
                st.warning("Analytics tracking stopped")

        # Check for analytics JSON file
        analytics_file = Path("analytics.json")
        if analytics_file.exists():
            st.markdown("### Stored Analytics Data")
            try:
                with open(analytics_file, 'r') as f:
                    analytics_data = json.load(f)
                st.json(analytics_data)

                # Summary statistics
                if isinstance(analytics_data, dict):
                    st.markdown("### Summary")
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        total_views = analytics_data.get("total_pageviews", 0)
                        st.metric("Total Pageviews", total_views)

                    with col2:
                        total_runs = analytics_data.get("total_script_runs", 0)
                        st.metric("Total Script Runs", total_runs)

                    with col3:
                        # Calculate total interactions from widgets (handle nested dicts)
                        total_interactions = 0
                        widgets = analytics_data.get("widgets", {})
                        for widget_name, widget_value in widgets.items():
                            if isinstance(widget_value, int):
                                total_interactions += widget_value
                            elif isinstance(widget_value, dict):
                                # Sum nested dictionary values
                                total_interactions += sum(v for v in widget_value.values() if isinstance(v, int))
                        st.metric("Total Interactions", total_interactions)

                    with col4:
                        unique_widgets = len(analytics_data.get("widgets", {}))
                        st.metric("Unique Widgets", unique_widgets)
            except json.JSONDecodeError as e:
                st.error(f"❌ Analytics file is corrupted or invalid JSON")
                st.code(f"Error: {e}")
                with st.expander("🔧 Fix corrupted analytics file"):
                    st.markdown("""
                    **Option 1: Reset analytics data**
                    ```bash
                    rm analytics.json
                    # Restart the app - new file will be created
                    ```

                    **Option 2: Fix JSON manually**
                    Open `analytics.json` and fix any JSON syntax errors.
                    """)
            except Exception as e:
                st.error(f"❌ Error reading analytics file")
                st.code(f"Error type: {type(e).__name__}\nError: {e}")
                with st.expander("🐛 Debug Information"):
                    st.markdown("""
                    This error occurred while parsing the analytics data.

                    **Common causes:**
                    - Corrupted analytics.json file
                    - Unexpected data structure
                    - Permission issues

                    **Solution:**
                    Check the analytics.json file or delete it to start fresh.
                    """)
        else:
            st.info("No analytics data stored yet. Use `streamlit_analytics.track(save_to_json='analytics.json')` in app.py")

    except ImportError:
        st.warning("⚠️ streamlit-analytics not installed. Install with: `uv pip install streamlit-analytics`")

        st.markdown("""
        ### Setup Instructions

        1. Install the package:
        ```bash
        uv pip install streamlit-analytics
        ```

        2. Add tracking to app.py:
        ```python
        import streamlit_analytics

        with streamlit_analytics.track(save_to_json="analytics.json"):
            # your app code
            page.run()
        ```

        3. View analytics by adding `?analytics=on` to URL
        """)

# Tab 2: Supabase Connection
with tab2:
    st.subheader("🗄️ Supabase Connection Status")

    try:
        # Use st-supabase-connection for connection management
        from st_supabase_connection import SupabaseConnection

        # Connection will use [connections.supabase] from secrets.toml automatically
        conn = st.connection(
            name="supabase",
            type=SupabaseConnection
        )

        st.success("✅ Successfully connected to Supabase via st.connection")

        # Supabase configuration
        supabase_url = st.secrets.get("connections", {}).get("supabase", {}).get("url", os.getenv("SUPABASE_URL"))
        supabase_key = st.secrets.get("connections", {}).get("supabase", {}).get("key", os.getenv("SUPABASE_KEY"))

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Configuration")
            st.code(f"""
URL: {supabase_url}
Key: {supabase_key[:10]}...{supabase_key[-4:] if supabase_key else 'Not set'}
Connection Type: st-supabase-connection
            """)

        with col2:
            st.markdown("### Connection Details")
            st.info("Connected via Streamlit's st.connection API with st-supabase-connection")
            st.caption("Provides built-in caching and connection pooling")

        # Test database access
        st.markdown("### Database Tables")

        # Show setup instructions if tables are missing
        with st.expander("📋 Setup Instructions", expanded=False):
            st.markdown("""
            **If you see "Table not found" errors below:**

            1. Go to your [Supabase SQL Editor](https://app.supabase.com/project/uljsqvwkomdrlnofmlad/sql)
            2. Open the file: `supabase/sql/create_missing_tables.sql`
            3. Copy the SQL and paste it into the SQL Editor
            4. Click **Run** to create the missing tables
            5. Refresh this page to verify

            **Required Tables:**
            - `politician_trades` - Main trading data
            - `user_sessions` - Authentication sessions
            - `action_logs` - Application logs
            - `scheduled_jobs` - Job scheduling

            See `supabase/README.md` for detailed setup instructions.
            """)

        with st.expander("🔍 Test Table Access", expanded=True):
            # Try to query different tables
            tables_to_test = [
                "politician_trades",
                "action_logs",
                "scheduled_jobs",
                "user_sessions"
            ]

            for table in tables_to_test:
                try:
                    # Query using Supabase client API
                    # conn.table() returns a query builder
                    response = conn.table(table).select("*", count="exact").limit(0).execute()
                    count = response.count if hasattr(response, 'count') else 0
                    st.success(f"✅ `{table}`: Accessible ({count} total rows)")
                except Exception as e:
                    error_msg = str(e)
                    if "Could not find the table" in error_msg or "PGRST" in error_msg:
                        st.warning(f"⚠️ `{table}`: Table not found - needs to be created")
                    else:
                        st.error(f"❌ `{table}`: {error_msg[:100]}")

        # Recent activity
        st.markdown("### Recent Database Activity")

        try:
            # Query recent logs using Supabase client API
            import pandas as pd

            response = conn.table("action_logs").select("*").order("created_at", desc=True).limit(5).execute()

            if response.data:
                recent_logs_df = pd.DataFrame(response.data)
                st.dataframe(recent_logs_df, width="stretch")
            else:
                st.info("No recent action logs")
        except Exception as e:
            st.error(f"Error fetching recent logs: {e}")

        # Connection statistics
        st.markdown("### Connection Statistics")

        with st.expander("📊 Query Performance", expanded=False):
            st.markdown("""
            **st-supabase-connection Features:**
            - ✅ Uses official Supabase Python client
            - ✅ Streamlit's native st.connection API
            - ✅ Automatic connection management
            - ✅ Better error handling
            - ✅ Automatic cleanup on session end

            **API Methods:**
            - `conn.table(name).select(columns).execute()` - Query data
            - `conn.table(name).insert(data).execute()` - Insert data
            - `conn.table(name).update(data).eq(col, val).execute()` - Update
            - `conn.table(name).delete().eq(col, val).execute()` - Delete
            - Full postgrest-py API available
            """)

    except ImportError:
        st.error("❌ st-supabase-connection not installed")
        st.markdown("""
        ### Installation Required

        Install st-supabase-connection:
        ```bash
        uv pip install st-supabase-connection
        ```

        Already in requirements.txt: `st-supabase-connection>=2.1.3`
        """)

    except Exception as e:
        st.error(f"❌ Failed to connect to Supabase: {e}")

        st.markdown("""
        ### Troubleshooting

        1. Check environment variables:
           - `SUPABASE_URL`
           - `SUPABASE_KEY`

        2. Verify .streamlit/secrets.toml configuration:
        ```toml
        [connections.supabase]
        url = "your-supabase-url"
        key = "your-supabase-key"
        ```

        3. Test connection manually:
        ```python
        from st_supabase_connection import SupabaseConnection
        conn = st.connection("supabase", type=SupabaseConnection)
        df = conn.query("SELECT 1")
        ```

        4. Documentation: https://st-supabase-connection.streamlit.app/
        5. GitHub: https://github.com/SiddhantSadangi/st_supabase_connection
        """)

# Tab 3: Database CRUD
with tab3:
    st.subheader("🗂️ Database CRUD Operations")
    st.caption("Create, Read, Update, and Delete records from Supabase tables")

    try:
        from st_supabase_connection import SupabaseConnection
        import pandas as pd

        # Get connection
        conn = st.connection("supabase", type=SupabaseConnection)

        # List of known tables (from Supabase tab testing)
        KNOWN_TABLES = [
            "trading_disclosures",
            "politicians",
            "action_logs",
            "scheduled_jobs",
            "user_sessions"
        ]

        # Test which tables actually exist
        st.markdown("### Select Table")

        with st.expander("🔍 Table Status", expanded=False):
            st.caption("Checking which tables are accessible...")
            available_tables = []

            for table in KNOWN_TABLES:
                try:
                    # Quick test query
                    response = conn.table(table).select("*", count="exact").limit(0).execute()
                    count = response.count if hasattr(response, 'count') else 0
                    st.success(f"✅ `{table}`: {count} rows")
                    available_tables.append(table)
                except Exception as e:
                    error_msg = str(e)
                    if "Could not find the table" in error_msg or "PGRST" in error_msg:
                        st.warning(f"⚠️ `{table}`: Not found")
                    else:
                        st.error(f"❌ `{table}`: {str(e)[:50]}")

            if not available_tables:
                st.error("❌ No tables are accessible. Please create tables first.")
                st.info("See `SETUP_DATABASE.md` for instructions.")
                st.stop()

        # Table selection
        col1, col2 = st.columns([3, 1])

        with col1:
            selected_table = st.selectbox(
                "Choose a table to manage:",
                options=available_tables,
                format_func=lambda x: x.replace("_", " ").title(),
                key="crud_table_select"
            )

        with col2:
            use_custom = st.checkbox("Custom table", key="use_custom_table")

        if use_custom:
            custom_table = st.text_input(
                "Enter table name:",
                placeholder="e.g., my_custom_table",
                key="custom_table_name"
            )
            if custom_table:
                selected_table = custom_table
                st.info(f"Using custom table: `{custom_table}`")

        # Show selected table info
        st.info(f"📋 Current Table: **`{selected_table}`**")

        st.divider()

        # Create tabs for different operations
        crud_tab1, crud_tab2, crud_tab3, crud_tab4 = st.tabs([
            "📖 Read/View",
            "➕ Create/Insert",
            "✏️ Update/Edit",
            "🗑️ Delete"
        ])

        # READ/VIEW Tab
        with crud_tab1:
            st.markdown(f"### View Records from `{selected_table}`")

            try:
                # Query options
                col1, col2 = st.columns([3, 1])
                with col1:
                    limit = st.number_input("Number of records to display:", min_value=1, max_value=1000, value=50, key="read_limit")
                with col2:
                    order_desc = st.checkbox("Latest first", value=True, key="read_order")

                # Fetch data
                if st.button("🔄 Refresh Data", key="refresh_read"):
                    st.rerun()

                with st.spinner(f"Loading records from {selected_table}..."):
                    query = conn.table(selected_table).select("*")

                    # Add ordering if table has created_at or updated_at
                    if order_desc:
                        # Try common timestamp columns
                        for time_col in ["created_at", "updated_at", "timestamp", "date"]:
                            try:
                                query = query.order(time_col, desc=True)
                                break
                            except:
                                continue

                    query = query.limit(limit)
                    response = query.execute()

                if response.data:
                    df = pd.DataFrame(response.data)

                    # Show summary
                    st.info(f"📊 Showing {len(df)} of {response.count if hasattr(response, 'count') else 'unknown'} total records")

                    # Display as dataframe with selection
                    st.markdown("#### Records")
                    st.dataframe(
                        df,
                        width="stretch",
                        hide_index=False
                    )

                    # Export option
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv,
                        file_name=f"{selected_table}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        key="download_csv"
                    )
                else:
                    st.info(f"No records found in `{selected_table}`")

            except Exception as e:
                st.error(f"❌ Error loading data from `{selected_table}`")
                with st.expander("🐛 Error Details"):
                    import traceback
                    st.code(f"Error Type: {type(e).__name__}\nError: {str(e)}\n\nTraceback:\n{traceback.format_exc()}")

        # CREATE/INSERT Tab
        with crud_tab2:
            st.markdown(f"### Insert New Record into `{selected_table}`")

            try:
                # Get table schema by querying one row
                sample_response = conn.table(selected_table).select("*").limit(1).execute()

                if sample_response.data and len(sample_response.data) > 0:
                    sample_record = sample_response.data[0]
                    columns = list(sample_record.keys())

                    st.info(f"📋 Table has {len(columns)} columns")

                    with st.expander("📝 View Column Names"):
                        st.code(", ".join(columns))
                else:
                    # If no records, show common columns based on table name
                    st.warning(f"Table `{selected_table}` is empty. Showing estimated columns.")
                    columns = []

                st.markdown("#### Enter New Record Data")
                st.caption("Enter data as JSON. UUID fields will be auto-generated if omitted.")

                # Get default template based on table
                default_json = get_default_insert_template(selected_table)

                new_record_json = st.text_area(
                    "Record Data (JSON):",
                    value=default_json,
                    height=300,
                    key="insert_json"
                )

                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("➕ Insert Record", type="primary", key="insert_btn"):
                        try:
                            record_data = json.loads(new_record_json)

                            with st.spinner("Inserting record..."):
                                response = conn.table(selected_table).insert(record_data).execute()

                            if response.data:
                                st.success(f"✅ Successfully inserted record!")
                                st.json(response.data[0])
                                st.balloons()
                            else:
                                st.error("❌ Insert failed - no data returned")

                        except json.JSONDecodeError as e:
                            st.error(f"❌ Invalid JSON: {e}")
                        except Exception as e:
                            st.error(f"❌ Insert failed: {str(e)}")
                            with st.expander("🐛 Error Details"):
                                st.code(str(e))

                with col2:
                    with st.expander("💡 JSON Tips"):
                        st.markdown("""
                        - Use double quotes for strings: `"value"`
                        - Dates: `"2025-11-04T12:00:00Z"`
                        - UUID fields are usually auto-generated
                        - Check existing records for format examples
                        """)

            except Exception as e:
                st.error(f"❌ Error in Create/Insert for `{selected_table}`")
                with st.expander("🐛 Error Details"):
                    import traceback
                    st.code(f"Error Type: {type(e).__name__}\nError: {str(e)}\n\nTraceback:\n{traceback.format_exc()}")

        # UPDATE/EDIT Tab
        with crud_tab3:
            st.markdown(f"### Update Records in `{selected_table}`")

            try:
                # Step 1: Load and select record
                st.markdown("#### Step 1: Select Record to Update")

                with st.spinner("Loading records..."):
                    response = conn.table(selected_table).select("*").limit(100).execute()

                if response.data and len(response.data) > 0:
                    df = pd.DataFrame(response.data)

                    # Try to find ID column
                    id_column = None
                    for col in ['id', 'session_id', 'job_id']:
                        if col in df.columns:
                            id_column = col
                            break

                    if not id_column:
                        st.error("❌ Cannot find ID column in table")
                    else:
                        st.info(f"📊 Found {len(df)} records. Using `{id_column}` as identifier.")

                        # Show records
                        st.dataframe(df, width="stretch", height=300)

                        # Select record
                        record_id = st.selectbox(
                            f"Select record by {id_column}:",
                            options=df[id_column].tolist(),
                            format_func=lambda x: str(x)[:50],
                            key="update_record_select"
                        )

                        if record_id:
                            # Get the full record
                            selected_record = df[df[id_column] == record_id].iloc[0].to_dict()

                            st.markdown("#### Step 2: Edit Record Data")

                            # Show current data
                            with st.expander("📄 Current Record Data"):
                                st.json(selected_record)

                            # Edit form
                            st.caption("Edit the JSON below. Only changed fields will be updated.")

                            updated_json = st.text_area(
                                "Updated Record Data (JSON):",
                                value=json.dumps(selected_record, indent=2, default=str),
                                height=400,
                                key="update_json"
                            )

                            col1, col2 = st.columns([1, 3])
                            with col1:
                                if st.button("💾 Update Record", type="primary", key="update_btn"):
                                    try:
                                        updated_data = json.loads(updated_json)

                                        # Remove ID from update data
                                        update_payload = {k: v for k, v in updated_data.items() if k != id_column}

                                        with st.spinner("Updating record..."):
                                            response = conn.table(selected_table).update(update_payload).eq(id_column, record_id).execute()

                                        if response.data:
                                            st.success(f"✅ Successfully updated record!")
                                            st.json(response.data[0])
                                        else:
                                            st.warning("⚠️ Update completed but no data returned")

                                    except json.JSONDecodeError as e:
                                        st.error(f"❌ Invalid JSON: {e}")
                                    except Exception as e:
                                        st.error(f"❌ Update failed: {str(e)}")
                                        with st.expander("🐛 Error Details"):
                                            st.code(str(e))
                else:
                    st.info(f"No records found in `{selected_table}` to update")

            except Exception as e:
                st.error(f"❌ Error in Update/Edit for `{selected_table}`")
                with st.expander("🐛 Error Details"):
                    import traceback
                    st.code(f"Error Type: {type(e).__name__}\nError: {str(e)}\n\nTraceback:\n{traceback.format_exc()}")

        # DELETE Tab
        with crud_tab4:
            st.markdown(f"### Delete Records from `{selected_table}`")
            st.warning("⚠️ **Warning:** Deletion is permanent and cannot be undone!")

            try:
                # Load records
                st.markdown("#### Select Record to Delete")

                with st.spinner("Loading records..."):
                    response = conn.table(selected_table).select("*").limit(100).execute()

                if response.data and len(response.data) > 0:
                    df = pd.DataFrame(response.data)

                    # Find ID column
                    id_column = None
                    for col in ['id', 'session_id', 'job_id']:
                        if col in df.columns:
                            id_column = col
                            break

                    if not id_column:
                        st.error("❌ Cannot find ID column in table")
                    else:
                        st.info(f"📊 Found {len(df)} records")

                        # Show records
                        st.dataframe(df, width="stretch", height=300)

                        # Select record to delete
                        record_id = st.selectbox(
                            f"Select record to delete by {id_column}:",
                            options=df[id_column].tolist(),
                            format_func=lambda x: str(x)[:50],
                            key="delete_record_select"
                        )

                        if record_id:
                            # Show record details
                            selected_record = df[df[id_column] == record_id].iloc[0].to_dict()

                            with st.expander("📄 Record to Delete"):
                                st.json(selected_record)

                            # Confirmation
                            st.markdown("#### ⚠️ Confirm Deletion")
                            confirm_text = st.text_input(
                                f"Type DELETE to confirm deletion of record {id_column}='{record_id}':",
                                key="delete_confirm"
                            )

                            col1, col2 = st.columns([1, 3])
                            with col1:
                                if st.button("🗑️ Delete Record", type="secondary", key="delete_btn", disabled=(confirm_text != "DELETE")):
                                    try:
                                        with st.spinner("Deleting record..."):
                                            response = conn.table(selected_table).delete().eq(id_column, record_id).execute()

                                        st.success(f"✅ Successfully deleted record {id_column}='{record_id}'")
                                        st.rerun()

                                    except Exception as e:
                                        st.error(f"❌ Delete failed: {str(e)}")
                                        with st.expander("🐛 Error Details"):
                                            st.code(str(e))

                            with col2:
                                if confirm_text != "DELETE":
                                    st.caption("⚠️ Type DELETE in the box above to enable the delete button")
                else:
                    st.info(f"No records found in `{selected_table}` to delete")

            except Exception as e:
                st.error(f"❌ Error in Delete operation for `{selected_table}`")
                with st.expander("🐛 Error Details"):
                    import traceback
                    st.code(f"Error Type: {type(e).__name__}\nError: {str(e)}\n\nTraceback:\n{traceback.format_exc()}")

    except ImportError:
        st.error("❌ st-supabase-connection not installed")
        st.info("Install with: `uv pip install st-supabase-connection`")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

# Tab 4: System Info
with tab4:
    st.subheader("⚙️ System Information")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Python Environment")
        import platform
        import sys

        st.code(f"""
Python Version: {sys.version}
Platform: {platform.platform()}
Processor: {platform.processor()}
        """)

        st.markdown("### Streamlit Info")
        st.code(f"""
Streamlit Version: {st.__version__}
        """)

    with col2:
        st.markdown("### Environment Variables")

        # Check both environment variables and secrets
        config_checks = {
            "SUPABASE_URL": os.getenv("SUPABASE_URL") or st.secrets.get("connections", {}).get("supabase", {}).get("url"),
            "SUPABASE_KEY": os.getenv("SUPABASE_KEY") or st.secrets.get("connections", {}).get("supabase", {}).get("key"),
            "ALPACA_API_KEY": os.getenv("ALPACA_API_KEY") or st.secrets.get("alpaca", {}).get("ALPACA_API_KEY"),
            "ALPACA_SECRET_KEY": os.getenv("ALPACA_SECRET_KEY") or st.secrets.get("alpaca", {}).get("ALPACA_SECRET_KEY"),
            "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID") or st.secrets.get("auth", {}).get("client_id"),
        }

        for var, value in config_checks.items():
            if value:
                # Mask sensitive values
                masked = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
                st.success(f"✅ {var}: {masked}")
            else:
                st.error(f"❌ {var}: Not set")

    # Disk usage
    st.markdown("### Disk Usage")
    import shutil

    try:
        total, used, free = shutil.disk_usage("/")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total", f"{total // (2**30)} GB")
        with col2:
            st.metric("Used", f"{used // (2**30)} GB")
        with col3:
            st.metric("Free", f"{free // (2**30)} GB")
    except Exception as e:
        st.error(f"Error reading disk usage: {e}")

# Tab 5: Users
with tab5:
    st.subheader("👥 User Management")

    try:
        # Use st-supabase-connection
        from st_supabase_connection import SupabaseConnection
        import pandas as pd

        # Connection will use [connections.supabase] from secrets.toml automatically
        conn = st.connection(
            name="supabase",
            type=SupabaseConnection
        )

        # Check if user_sessions table exists
        try:
            # Query using Supabase client API
            response = conn.table("user_sessions").select("*").order("last_activity", desc=True).execute()

            if response.data:
                sessions_df = pd.DataFrame(response.data)
                st.markdown("### Active Sessions")
                st.dataframe(sessions_df, width="stretch")

                # Summary stats
                col1, col2, col3 = st.columns(3)

                with col1:
                    unique_users = sessions_df['user_email'].nunique() if 'user_email' in sessions_df.columns else 0
                    st.metric("Unique Users", unique_users)

                with col2:
                    total_sessions = len(sessions_df)
                    st.metric("Total Sessions", total_sessions)

                with col3:
                    # Count active sessions (last activity < 1 hour ago)
                    if 'last_activity' in sessions_df.columns:
                        sessions_df['last_activity'] = pd.to_datetime(sessions_df['last_activity'])
                        active = sessions_df[sessions_df['last_activity'] > datetime.now() - pd.Timedelta(hours=1)]
                        st.metric("Active (1h)", len(active))
            else:
                st.info("No user sessions found")

        except Exception as e:
            st.warning(f"user_sessions table not accessible: {e}")
            st.info("The user_sessions table may not exist yet. It will be created when users start logging in with enhanced authentication.")

    except ImportError:
        st.error("❌ st-supabase-connection not installed")
        st.info("Install with: `uv pip install st-supabase-connection`")
    except Exception as e:
        st.error(f"Error accessing user data: {e}")

# Tab 6: Logs
with tab6:
    st.subheader("📝 Application Logs")

    # Check for log files
    log_dir = Path("logs")
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))

        if log_files:
            selected_log = st.selectbox(
                "Select log file",
                options=log_files,
                format_func=lambda x: x.name
            )

            lines_to_show = st.slider("Lines to show", 10, 1000, 100)

            if selected_log:
                try:
                    with open(selected_log, 'r') as f:
                        lines = f.readlines()
                        # Show last N lines
                        recent_lines = lines[-lines_to_show:]
                        st.code(''.join(recent_lines), language="log")
                except Exception as e:
                    st.error(f"Error reading log file: {e}")
        else:
            st.info("No log files found in logs/ directory")
    else:
        st.info("logs/ directory does not exist")

    # Show Python logs if available
    st.markdown("### Recent Python Logs")

    try:
        import logging
        st.code("""
To enable logging, add to your page:

from politician_trading.utils.logger import create_logger
logger = create_logger(__name__)

logger.info("Your log message")
        """)
    except Exception as e:
        st.error(f"Error: {e}")

st.divider()

# Footer
st.caption(f"🔐 Admin Dashboard | Restricted Access | User: {user_email}")
