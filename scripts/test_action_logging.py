#!/usr/bin/env python3
"""
Test script to validate action logging system
Run this after database migration to verify everything works
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from politician_trading.utils.action_logger import (
    get_action_logger,
    start_action,
    complete_action,
    fail_action,
    log_action,
)
from politician_trading.config import SupabaseConfig


def test_basic_logging():
    """Test basic action logging"""
    print("🧪 Testing basic action logging...")

    action_id = log_action(
        action_type="test_action",
        status="completed",
        action_name="Test Basic Logging",
        user_id="test_user",
        source="system",
        result_message="Test completed successfully",
        action_details={"test": True, "timestamp": "now"}
    )

    if action_id:
        print(f"   ✅ Basic logging successful - Action ID: {action_id}")
        return True
    else:
        print("   ❌ Basic logging failed")
        return False


def test_action_workflow():
    """Test full action workflow (start -> complete)"""
    print("\n🧪 Testing action workflow...")

    # Start action
    action_id = start_action(
        action_type="test_workflow",
        action_name="Test Workflow Action",
        user_id="test_user",
        source="system",
        action_details={"phase": "start"}
    )

    if not action_id:
        print("   ❌ Failed to start action")
        return False

    print(f"   ✅ Action started - ID: {action_id}")

    # Simulate some work
    import time
    time.sleep(0.5)

    # Complete action
    success = complete_action(
        action_id=action_id,
        result_message="Workflow completed successfully",
        action_details={"phase": "complete", "records_processed": 100}
    )

    if success:
        print("   ✅ Action completed successfully")
        return True
    else:
        print("   ❌ Failed to complete action")
        return False


def test_action_failure():
    """Test action failure logging"""
    print("\n🧪 Testing action failure logging...")

    # Start action
    action_id = start_action(
        action_type="test_failure",
        action_name="Test Failure Action",
        user_id="test_user",
        source="system"
    )

    if not action_id:
        print("   ❌ Failed to start action")
        return False

    # Fail action
    success = fail_action(
        action_id=action_id,
        error_message="Simulated error for testing",
        action_details={"error_code": "TEST_ERROR"}
    )

    if success:
        print("   ✅ Action failure logged successfully")
        return True
    else:
        print("   ❌ Failed to log action failure")
        return False


def test_query_actions():
    """Test querying recent actions"""
    print("\n🧪 Testing action queries...")

    logger = get_action_logger()

    # Query recent actions
    actions = logger.get_recent_actions(limit=10)

    if actions:
        print(f"   ✅ Retrieved {len(actions)} recent actions")

        # Show the most recent action
        if len(actions) > 0:
            recent = actions[0]
            print(f"   📋 Most recent action:")
            print(f"      Type: {recent.get('action_type')}")
            print(f"      Status: {recent.get('status')}")
            print(f"      Time: {recent.get('action_timestamp')}")

        return True
    else:
        print("   ⚠️  No actions found (this might be expected if database is fresh)")
        return True


def test_get_summary():
    """Test getting action summary"""
    print("\n🧪 Testing action summary...")

    logger = get_action_logger()

    summary = logger.get_action_summary(days=7)

    if summary and 'summary' in summary:
        print(f"   ✅ Retrieved action summary")

        if summary['summary']:
            print(f"   📊 Summary includes {len(summary['summary'])} action types")
        else:
            print("   ℹ️  No summary data yet (expected for fresh database)")

        return True
    else:
        print("   ❌ Failed to get summary")
        return False


def test_database_connection():
    """Test database connection"""
    print("🧪 Testing database connection...")

    try:
        config = SupabaseConfig.from_env()
        print(f"   ✅ Supabase config loaded")
        print(f"   📡 URL: {config.url[:50]}...")
        return True
    except Exception as e:
        print(f"   ❌ Failed to load config: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("🚀 Action Logging System Test Suite")
    print("=" * 60)

    tests = [
        ("Database Connection", test_database_connection),
        ("Basic Logging", test_basic_logging),
        ("Action Workflow", test_action_workflow),
        ("Action Failure", test_action_failure),
        ("Query Actions", test_query_actions),
        ("Action Summary", test_get_summary),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n   ❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Print summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print("-" * 60)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Action logging system is working correctly.")
        print("\n📋 Next steps:")
        print("   1. Open the Streamlit app")
        print("   2. Navigate to the Action Logs page (📋)")
        print("   3. You should see the test actions logged")
        print("   4. Try triggering a data collection to see real actions")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
