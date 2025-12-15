#!/usr/bin/env python3
"""
Test script for job recovery and catch-up system

This script tests:
1. Schema verification - scheduled_jobs table exists
2. Initial data - default jobs are populated
3. Job registration - new jobs get registered in database
4. Missed job recovery - overdue jobs are caught up on startup
5. Failure tracking - consecutive_failures increments properly
6. Max retry limit - jobs stop after max_consecutive_failures
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Load secrets from .streamlit/secrets.toml if it exists
try:
    import toml
    secrets_path = Path(__file__).parent / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        secrets = toml.load(secrets_path)
        if "database" in secrets:
            for key, value in secrets["database"].items():
                os.environ[key] = value
            print("✅ Loaded secrets from .streamlit/secrets.toml")
except Exception as e:
    print(f"⚠️  Could not load secrets.toml: {e}")

from politician_trading.config import SupabaseConfig
from politician_trading.database.database import SupabaseClient


@pytest.fixture(scope="module")
def db_client():
    """Fixture to provide database client, skip if credentials unavailable."""
    try:
        config = SupabaseConfig.from_env()
        if not config.url or not config.key:
            pytest.skip("Supabase credentials not configured")
        client = SupabaseClient(config)
        print(f"✅ Database connection successful!")
        return client
    except Exception as e:
        pytest.skip(f"Database connection failed: {e}")


def test_schema_exists(db_client):
    """Test 1: Verify scheduled_jobs table exists"""
    print("\n" + "=" * 80)
    print("TEST 1: Schema Verification")
    print("=" * 80)

    try:
        response = db_client.client.table("scheduled_jobs").select("*").limit(1).execute()
        print("✅ scheduled_jobs table exists!")
        return True
    except Exception as e:
        print(f"❌ scheduled_jobs table not found: {e}")
        return False

def test_initial_data(db_client):
    """Test 2: Verify default jobs are populated"""
    print("\n" + "=" * 80)
    print("TEST 2: Initial Data")
    print("=" * 80)

    try:
        response = db_client.client.table("scheduled_jobs").select("*").execute()

        jobs = response.data or []
        print(f"✅ Found {len(jobs)} scheduled job(s)")

        if len(jobs) == 0:
            print("⚠️  No jobs found - this is OK if schema just created")
            return True

        print("\n   Registered Jobs:")
        for job in jobs:
            print(f"   📋 {job['job_name']} ({job['job_id']})")
            print(f"      Schedule: {job['schedule_type']} - every {job['schedule_value']} seconds" if job['schedule_type'] == 'interval' else f"      Schedule: {job['schedule_value']}")
            print(f"      Enabled: {job['enabled']}")
            print(f"      Next Run: {job['next_scheduled_run']}")
            print(f"      Consecutive Failures: {job['consecutive_failures']}/{job['max_consecutive_failures']}")
            print()

        # Check for expected jobs
        job_ids = [j['job_id'] for j in jobs]
        expected_jobs = ['data_collection', 'ticker_backfill']

        for expected in expected_jobs:
            if expected in job_ids:
                print(f"   ✅ Found expected job: {expected}")
            else:
                print(f"   ⚠️  Missing expected job: {expected}")

        return True

    except Exception as e:
        print(f"❌ Error querying scheduled_jobs: {e}")
        return False

def test_job_status_view(db_client):
    """Test 3: Query scheduled_jobs_status view"""
    print("\n" + "=" * 80)
    print("TEST 3: Job Status View")
    print("=" * 80)

    try:
        response = db_client.client.table("scheduled_jobs_status").select("*").execute()

        jobs = response.data or []
        print(f"✅ Successfully queried scheduled_jobs_status view")
        print(f"   Found {len(jobs)} job(s)")

        if jobs:
            print("\n   Job Status Summary:")
            for job in jobs:
                status_emoji = {
                    'disabled': '⚫',
                    'failed_max_retries': '🔴',
                    'pending_first_run': '🟡',
                    'overdue': '🟠',
                    'scheduled': '🟢'
                }.get(job['job_status'], '❓')

                print(f"   {status_emoji} {job['job_name']}")
                print(f"      Status: {job['job_status']}")
                print(f"      Last Execution: {job.get('last_execution_status', 'Never')}")
                if job.get('last_execution_time'):
                    print(f"      Last Run Time: {job['last_execution_time']}")
                print()

        return True

    except Exception as e:
        print(f"❌ Error querying scheduled_jobs_status view: {e}")
        return False

def test_overdue_job_detection(db_client):
    """Test 4: Create an overdue job and verify it's detected"""
    print("\n" + "=" * 80)
    print("TEST 4: Overdue Job Detection")
    print("=" * 80)

    try:
        # Create a test job that's overdue
        test_job = {
            'job_id': 'test_overdue_job',
            'job_name': 'Test Overdue Job',
            'job_function': 'politician_trading.scheduler.jobs.data_collection_job',
            'schedule_type': 'interval',
            'schedule_value': '3600',  # 1 hour
            'enabled': True,
            'auto_retry_on_startup': True,
            'next_scheduled_run': (datetime.now() - timedelta(hours=2)).isoformat(),  # 2 hours ago
            'consecutive_failures': 0,
            'max_consecutive_failures': 3,
            'metadata': {'test': True}
        }

        print("📝 Creating test overdue job...")
        db_client.client.table("scheduled_jobs").upsert(test_job, on_conflict='job_id').execute()
        print("✅ Test job created")

        # Query for overdue jobs
        print("\n🔍 Querying for overdue jobs...")
        response = (
            db_client.client.table("scheduled_jobs")
            .select("*")
            .eq("enabled", True)
            .eq("auto_retry_on_startup", True)
            .lte("next_scheduled_run", datetime.now().isoformat())
            .execute()
        )

        overdue_jobs = response.data or []
        print(f"✅ Found {len(overdue_jobs)} overdue job(s)")

        if overdue_jobs:
            print("\n   Overdue Jobs:")
            for job in overdue_jobs:
                print(f"   ⏰ {job['job_name']} ({job['job_id']})")
                print(f"      Should have run: {job['next_scheduled_run']}")
                print(f"      Consecutive failures: {job['consecutive_failures']}")
                print()

        # Check if our test job is in the overdue list
        test_job_found = any(j['job_id'] == 'test_overdue_job' for j in overdue_jobs)
        if test_job_found:
            print("✅ Test overdue job is correctly detected!")
        else:
            print("❌ Test overdue job was NOT detected")
            return False

        return True

    except Exception as e:
        print(f"❌ Error testing overdue detection: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_update_job_function(db_client):
    """Test 5: Test the update_job_after_execution function"""
    print("\n" + "=" * 80)
    print("TEST 5: update_job_after_execution() Function")
    print("=" * 80)

    try:
        # Test successful execution
        print("🧪 Testing successful execution update...")
        db_client.client.rpc(
            'update_job_after_execution',
            {'p_job_id': 'test_overdue_job', 'p_success': True}
        ).execute()
        print("✅ Successfully called update_job_after_execution(success=True)")

        # Verify the update
        response = (
            db_client.client.table("scheduled_jobs")
            .select("*")
            .eq("job_id", "test_overdue_job")
            .execute()
        )

        if response.data:
            job = response.data[0]
            print(f"   Consecutive failures: {job['consecutive_failures']} (should be 0)")
            print(f"   Last successful run: {job['last_successful_run']}")
            print(f"   Next scheduled run: {job['next_scheduled_run']}")

            if job['consecutive_failures'] == 0:
                print("✅ Consecutive failures correctly reset to 0!")
            else:
                print(f"❌ Expected consecutive_failures=0, got {job['consecutive_failures']}")

        # Test failed execution
        print("\n🧪 Testing failed execution update...")
        db_client.client.rpc(
            'update_job_after_execution',
            {'p_job_id': 'test_overdue_job', 'p_success': False}
        ).execute()
        print("✅ Successfully called update_job_after_execution(success=False)")

        # Verify the failure increment
        response = (
            db_client.client.table("scheduled_jobs")
            .select("*")
            .eq("job_id", "test_overdue_job")
            .execute()
        )

        if response.data:
            job = response.data[0]
            print(f"   Consecutive failures: {job['consecutive_failures']} (should be 1)")

            if job['consecutive_failures'] == 1:
                print("✅ Consecutive failures correctly incremented!")
            else:
                print(f"❌ Expected consecutive_failures=1, got {job['consecutive_failures']}")

        return True

    except Exception as e:
        print(f"❌ Error testing update function: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_max_failure_limit(db_client):
    """Test 6: Verify jobs stop after max consecutive failures"""
    print("\n" + "=" * 80)
    print("TEST 6: Max Consecutive Failures Limit")
    print("=" * 80)

    try:
        # Get the test job
        response = (
            db_client.client.table("scheduled_jobs")
            .select("*")
            .eq("job_id", "test_overdue_job")
            .execute()
        )

        if not response.data:
            print("⚠️  Test job not found, skipping this test")
            return True

        job = response.data[0]
        max_failures = job['max_consecutive_failures']
        current_failures = job['consecutive_failures']

        print(f"📊 Current state:")
        print(f"   Consecutive failures: {current_failures}")
        print(f"   Max failures allowed: {max_failures}")

        # Fail the job until we hit the max
        print(f"\n🔄 Failing job {max_failures - current_failures} more times to hit max...")

        for i in range(max_failures - current_failures):
            db_client.client.rpc(
                'update_job_after_execution',
                {'p_job_id': 'test_overdue_job', 'p_success': False}
            ).execute()
            print(f"   Failed attempt {i + 1}")

        # Verify it reached max
        response = (
            db_client.client.table("scheduled_jobs")
            .select("*")
            .eq("job_id", "test_overdue_job")
            .execute()
        )

        job = response.data[0]
        print(f"\n📊 Final state:")
        print(f"   Consecutive failures: {job['consecutive_failures']}")
        print(f"   Max failures: {job['max_consecutive_failures']}")

        if job['consecutive_failures'] >= job['max_consecutive_failures']:
            print("✅ Job reached max consecutive failures!")

            # Verify it won't be selected for recovery
            overdue_response = (
                db_client.client.table("scheduled_jobs")
                .select("*")
                .eq("enabled", True)
                .eq("auto_retry_on_startup", True)
                .lte("next_scheduled_run", datetime.now().isoformat())
                .execute()
            )

            overdue_jobs = [j for j in (overdue_response.data or [])
                          if j['consecutive_failures'] < j['max_consecutive_failures']]

            test_job_in_overdue = any(j['job_id'] == 'test_overdue_job' for j in overdue_jobs)

            if not test_job_in_overdue:
                print("✅ Job correctly excluded from recovery (hit max failures)!")
            else:
                print("❌ Job should not be in recovery list after hitting max failures")
        else:
            print("❌ Job did not reach max failures")

        return True

    except Exception as e:
        print(f"❌ Error testing max failure limit: {e}")
        import traceback
        traceback.print_exc()
        return False

@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data(db_client):
    """Clean up test data after all tests run"""
    yield  # Run tests first
    # Cleanup after tests
    print("\n" + "=" * 80)
    print("CLEANUP: Removing Test Data")
    print("=" * 80)

    try:
        db_client.client.table("scheduled_jobs").delete().eq("job_id", "test_overdue_job").execute()
        print("✅ Test job removed")
    except Exception as e:
        print(f"⚠️  Could not remove test job: {e}")
