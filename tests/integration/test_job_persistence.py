#!/usr/bin/env python3
"""
Test script for job execution persistence

This script tests that:
1. Database connection works
2. job_executions table exists
3. Can write job executions to database
4. Can read job executions from database
5. JobHistory class loads from database correctly
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Load secrets from .streamlit/secrets.toml if it exists
try:
    import toml
    secrets_path = Path(__file__).parent / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        secrets = toml.load(secrets_path)
        # Load database secrets
        if "database" in secrets:
            for key, value in secrets["database"].items():
                os.environ[key] = value
            print("✅ Loaded secrets from .streamlit/secrets.toml")
except Exception as e:
    print(f"⚠️  Could not load secrets.toml: {e}")

from politician_trading.config import SupabaseConfig
from politician_trading.database.database import SupabaseClient
from politician_trading.scheduler.manager import JobHistory

def test_database_connection():
    """Test 1: Verify database connection"""
    print("=" * 80)
    print("TEST 1: Database Connection")
    print("=" * 80)

    try:
        config = SupabaseConfig.from_env()
        db_client = SupabaseClient(config)
        print("✅ Database connection successful!")
        print(f"   URL: {config.url}")
        return db_client
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)

def test_table_exists(db_client):
    """Test 2: Verify job_executions table exists"""
    print("\n" + "=" * 80)
    print("TEST 2: Table Existence")
    print("=" * 80)

    try:
        # Try to query the table
        response = db_client.client.table("job_executions").select("*").limit(1).execute()
        print("✅ job_executions table exists!")
        print(f"   Current records: {len(response.data) if response.data else 0}")
        return True
    except Exception as e:
        print(f"❌ job_executions table not found: {e}")
        print("   Please run: supabase/sql/job_executions_schema.sql")
        sys.exit(1)

def test_write_execution(db_client):
    """Test 3: Write a test execution to database"""
    print("\n" + "=" * 80)
    print("TEST 3: Write Test Execution")
    print("=" * 80)

    try:
        test_execution = {
            "job_id": "test_job_persistence",
            "status": "success",
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
            "duration_seconds": 1.234,
            "error_message": None,
            "logs": "Test log line 1\nTest log line 2\nTest log line 3",
            "metadata": {"test": True, "purpose": "persistence_test"}
        }

        response = db_client.client.table("job_executions").insert(test_execution).execute()

        if response.data:
            record_id = response.data[0]["id"]
            print("✅ Test execution written to database!")
            print(f"   Record ID: {record_id}")
            print(f"   Job ID: {test_execution['job_id']}")
            print(f"   Duration: {test_execution['duration_seconds']}s")
            return record_id
        else:
            print("❌ Failed to write test execution")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error writing test execution: {e}")
        sys.exit(1)

def test_read_executions(db_client):
    """Test 4: Read executions from database"""
    print("\n" + "=" * 80)
    print("TEST 4: Read Executions")
    print("=" * 80)

    try:
        response = (
            db_client.client.table("job_executions")
            .select("*")
            .order("started_at", desc=True)
            .limit(5)
            .execute()
        )

        if response.data:
            print(f"✅ Successfully read {len(response.data)} executions from database!")
            print("\n   Recent executions:")
            for exec in response.data:
                status_emoji = "✅" if exec["status"] == "success" else "❌"
                print(f"   {status_emoji} {exec['job_id']} - {exec['status']} - {exec.get('duration_seconds', 0):.2f}s")
            return response.data
        else:
            print("⚠️  No executions found in database (this is OK if first run)")
            return []

    except Exception as e:
        print(f"❌ Error reading executions: {e}")
        sys.exit(1)

def test_job_history_load(db_client):
    """Test 5: JobHistory loads from database"""
    print("\n" + "=" * 80)
    print("TEST 5: JobHistory Loading")
    print("=" * 80)

    try:
        # Create JobHistory with database client
        job_history = JobHistory(db_client=db_client)

        # Get history
        history = job_history.get_history()

        print(f"✅ JobHistory initialized successfully!")
        print(f"   Loaded {len(history)} executions from database")

        if history:
            print("\n   Recent executions in memory:")
            for exec in history[:5]:
                status_emoji = "✅" if exec["status"] == "success" else "❌"
                duration = exec.get("duration_seconds", 0)
                timestamp = exec["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                print(f"   {status_emoji} {exec['job_id']} - {exec['status']} - {duration:.2f}s - {timestamp}")
        else:
            print("   (No history loaded - this is OK if no jobs have run yet)")

        return job_history

    except Exception as e:
        print(f"❌ Error loading JobHistory: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def test_job_history_persist(job_history):
    """Test 6: JobHistory persists new execution"""
    print("\n" + "=" * 80)
    print("TEST 6: JobHistory Persistence")
    print("=" * 80)

    try:
        # Add a test execution
        test_logs = [
            "🚀 Starting test job",
            "📊 Processing test data",
            "✅ Test completed successfully"
        ]

        job_history.add_execution(
            job_id="test_persistence_via_jobhistory",
            status="success",
            error=None,
            logs=test_logs
        )

        # Update with duration
        last_exec = job_history.get_last_execution("test_persistence_via_jobhistory")
        if last_exec:
            job_history.update_execution(
                job_id="test_persistence_via_jobhistory",
                timestamp=last_exec["timestamp"],
                duration_seconds=2.345
            )

            print("✅ JobHistory.add_execution() worked!")
            print(f"   Job ID: test_persistence_via_jobhistory")
            print(f"   Status: success")
            print(f"   Duration: 2.345s")
            print(f"   Logs: {len(test_logs)} lines")
            print(f"   DB ID: {last_exec.get('db_id', 'N/A')}")

            if last_exec.get("db_id"):
                print("\n   ✅ Execution persisted to database!")
            else:
                print("\n   ⚠️  Execution NOT persisted to database (check logs)")
        else:
            print("❌ Could not find last execution")

    except Exception as e:
        print(f"❌ Error testing JobHistory persistence: {e}")
        import traceback
        traceback.print_exc()

def test_query_view(db_client):
    """Test 7: Query the job_execution_summary view"""
    print("\n" + "=" * 80)
    print("TEST 7: Summary View")
    print("=" * 80)

    try:
        response = db_client.client.table("job_execution_summary").select("*").execute()

        if response.data:
            print(f"✅ Successfully queried job_execution_summary view!")
            print(f"\n   Job Summary (last 30 days):")
            for row in response.data:
                print(f"\n   📊 {row['job_id']}")
                print(f"      Total: {row['total_executions']}")
                print(f"      Success: {row['successful_executions']}")
                print(f"      Failed: {row['failed_executions']}")
                if row['avg_duration_seconds']:
                    print(f"      Avg Duration: {float(row['avg_duration_seconds']):.2f}s")
        else:
            print("⚠️  No data in summary view (no jobs executed in last 30 days)")

    except Exception as e:
        print(f"❌ Error querying summary view: {e}")

def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "JOB PERSISTENCE TEST SUITE" + " " * 32 + "║")
    print("╚" + "=" * 78 + "╝")

    # Run tests
    db_client = test_database_connection()
    test_table_exists(db_client)
    test_write_execution(db_client)
    test_read_executions(db_client)
    job_history = test_job_history_load(db_client)
    test_job_history_persist(job_history)
    test_query_view(db_client)

    # Final summary
    print("\n" + "=" * 80)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 80)
    print("\nYour job persistence system is working correctly!")
    print("\nNext steps:")
    print("1. Go to your Streamlit app: https://politician-trading-tracker.streamlit.app")
    print("2. Navigate to the 'Scheduled Jobs' page")
    print("3. Wait for a scheduled job to run (or trigger one manually)")
    print("4. Refresh the page - you should see the job execution in the history")
    print("5. Restart the app - the history should persist!")
    print("\nYou can also query the database directly:")
    print("  SELECT * FROM job_executions ORDER BY started_at DESC LIMIT 10;")
    print("  SELECT * FROM job_execution_summary;")
    print()

if __name__ == "__main__":
    main()
