#!/usr/bin/env python3
"""
Create storage buckets in Supabase.

Creates the four required buckets for raw data storage.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from supabase import create_client
from politician_trading.config import SupabaseConfig


def main():
    """Create storage buckets"""

    print("=" * 60)
    print("Creating Storage Buckets")
    print("=" * 60)
    print()

    # Get database connection with service role key
    config = SupabaseConfig.from_env()

    # Use service role key for admin operations
    if not config.service_role_key:
        print("❌ SUPABASE_SERVICE_KEY not found in environment")
        print("   This is required to create storage buckets")
        return 1

    db = create_client(config.url, config.service_role_key)

    print("✓ Connected to Supabase")
    print()

    # List of buckets to create
    buckets = [
        {'id': 'raw-pdfs', 'name': 'raw-pdfs', 'public': False},
        {'id': 'api-responses', 'name': 'api-responses', 'public': False},
        {'id': 'parsed-data', 'name': 'parsed-data', 'public': False},
        {'id': 'html-snapshots', 'name': 'html-snapshots', 'public': False},
    ]

    print("Creating buckets...")
    print("-" * 60)

    for bucket in buckets:
        try:
            db.storage.create_bucket(bucket['id'], options={'public': bucket['public']})
            print(f"  ✓ Created: {bucket['name']}")
        except Exception as e:
            error_msg = str(e)
            if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
                print(f"  ℹ️  Already exists: {bucket['name']}")
            else:
                print(f"  ❌ Error creating {bucket['name']}: {e}")

    print()

    # Verify buckets
    print("Verifying buckets...")
    print("-" * 60)

    try:
        existing_buckets = db.storage.list_buckets()
        bucket_names = [b.name for b in existing_buckets]

        for bucket in buckets:
            if bucket['id'] in bucket_names:
                print(f"  ✓ {bucket['name']}")
            else:
                print(f"  ❌ {bucket['name']} (missing)")

    except Exception as e:
        print(f"❌ Error listing buckets: {e}")

    print()
    print("=" * 60)
    print("Bucket Creation Complete")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Apply SQL migration to create stored_files table")
    print("2. Go to: https://app.supabase.com/project/uljsqvwkomdrlnofmlad/sql")
    print("3. Copy contents of:")
    print("   supabase/migrations/003_create_storage_infrastructure.sql")
    print("4. Paste into SQL Editor and click 'Run'")
    print()

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
