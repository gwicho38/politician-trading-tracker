#!/usr/bin/env python3
"""
Test Signal Insertion

Quick script to test if we can successfully insert a signal into the database
with all the required fields we've identified.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

from politician_trading.database.database import SupabaseClient
from politician_trading.config import SupabaseConfig


def test_signal_insert():
    """Test inserting a minimal signal to verify schema compatibility."""
    print("\n" + "="*80)
    print("TESTING SIGNAL INSERTION")
    print("="*80 + "\n")

    try:
        # Initialize database
        config = SupabaseConfig.from_env()
        db = SupabaseClient(config)

        print(f"✅ Connected to Supabase: {config.url}\n")

        # Create test signal data with ALL the fields we've discovered
        now = datetime.now(timezone.utc)
        test_data = {
            # Core fields
            "ticker": "TEST",
            "symbol": "TEST",  # Redundant with ticker
            "asset_name": "Test Signal",

            # Signal classification
            "signal_type": "hold",
            "signal_strength": "moderate",
            "strength": 0.65,  # Numeric strength (0-1), NOT the same as signal_strength

            # Confidence
            "confidence_score": 0.65,
            "confidence": 0.65,  # Redundant with confidence_score

            # Price targets (optional)
            "target_price": None,
            "stop_loss": None,
            "take_profit": None,

            # Metadata
            "generated_at": now.isoformat(),
            "valid_until": (now + timedelta(days=7)).isoformat(),
            "model_version": "test-v1.0",

            # Supporting data
            "politician_activity_count": 0,
            "total_transaction_volume": None,
            "buy_sell_ratio": None,

            # Additional fields
            "features": {},
            "disclosure_ids": [],
            "is_active": True,
            "notes": "Test signal from schema compatibility check",

            # Portfolio (nullable)
            "portfolio_id": None,
        }

        print("Attempting to insert test signal with fields:")
        for key, value in test_data.items():
            value_str = str(value)
            if len(value_str) > 50:
                value_str = value_str[:47] + "..."
            print(f"  {key:30} = {value_str}")

        print("\nInserting...")

        # Try to insert
        response = db.client.table("trading_signals").insert(test_data).execute()

        if response.data:
            print("\n✅ SUCCESS! Signal inserted successfully!")
            print(f"   Inserted signal ID: {response.data[0].get('id')}")

            # Clean up - delete the test signal
            signal_id = response.data[0].get('id')
            if signal_id:
                print(f"\nCleaning up test signal...")
                db.client.table("trading_signals").delete().eq('id', signal_id).execute()
                print("✅ Test signal deleted")

            print("\n" + "="*80)
            print("RESULT: All required fields are present! ✅")
            print("="*80)
            print("\nYour signal generation should now work correctly.")
            print("The schema is compatible with the application code.")

        else:
            print("\n❌ Insert returned no data (unexpected)")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nThis error indicates missing required fields:")
        error_str = str(e)

        if "violates not-null constraint" in error_str:
            # Extract column name from error
            import re
            match = re.search(r'column "([^"]+)"', error_str)
            if match:
                missing_column = match.group(1)
                print(f"\n⚠️  Missing required column: {missing_column}")
                print(f"   This column needs to be added to the data dictionary")
                print(f"   in 2_🎯_Trading_Signals.py")

        print("\n" + "="*80)
        print("RESULT: Schema mismatch detected! ❌")
        print("="*80)
        return False

    return True


if __name__ == "__main__":
    success = test_signal_insert()
    sys.exit(0 if success else 1)
