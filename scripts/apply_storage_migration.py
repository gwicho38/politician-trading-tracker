#!/usr/bin/env python3
"""
Apply storage infrastructure migration to Supabase.

This script executes the SQL migration to create storage buckets,
tables, and helper functions.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from supabase import create_client
from politician_trading.config import SupabaseConfig


async def main():
    """Apply migration"""

    print("=" * 60)
    print("Applying Storage Infrastructure Migration")
    print("=" * 60)
    print()

    # Get database connection
    config = SupabaseConfig.from_env()
    db = create_client(config.url, config.key)

    print("✓ Connected to Supabase")
    print()

    # Read migration file
    migration_file = Path(__file__).parent.parent / "supabase" / "migrations" / "003_create_storage_infrastructure.sql"

    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return 1

    print(f"Reading migration: {migration_file.name}")
    with open(migration_file, 'r') as f:
        sql = f.read()

    print(f"Migration size: {len(sql)} bytes")
    print()

    # Execute via RPC
    print("Executing migration...")
    print("-" * 60)

    try:
        # Use Supabase's SQL execution capability
        # Note: This requires the service role key
        response = db.rpc('exec', {'sql': sql}).execute()
        print("✓ Migration applied successfully")
        print()

    except Exception as e:
        error_msg = str(e)

        # Check if error is about buckets already existing
        if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
            print("⚠️  Some resources already exist - this is OK")
            print(f"   Details: {error_msg[:200]}")
            print()
        else:
            print(f"❌ Error applying migration: {e}")
            print()
            print("Please apply the migration manually via Supabase Dashboard:")
            print(f"1. Go to: https://app.supabase.com/project/uljsqvwkomdrlnofmlad/sql")
            print(f"2. Copy contents of: {migration_file}")
            print(f"3. Paste into SQL Editor and click 'Run'")
            print()
            return 1

    # Verify buckets were created
    print("Verifying storage buckets...")
    try:
        buckets = db.storage.list_buckets()
        bucket_names = [b.name for b in buckets]

        required_buckets = ['raw-pdfs', 'api-responses', 'parsed-data', 'html-snapshots']

        for bucket in required_buckets:
            if bucket in bucket_names:
                print(f"  ✓ {bucket}")
            else:
                print(f"  ❌ {bucket} (missing)")

        print()

    except Exception as e:
        print(f"⚠️  Could not verify buckets: {e}")
        print()

    # Verify stored_files table
    print("Verifying stored_files table...")
    try:
        result = db.table('stored_files').select('*').limit(1).execute()
        print("  ✓ stored_files table exists")
        print()
    except Exception as e:
        print(f"  ❌ stored_files table: {e}")
        print()

    print("=" * 60)
    print("Migration Complete")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
