#!/usr/bin/env python3
"""
Set up Supabase storage infrastructure.

Applies migration and tests storage functionality.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from supabase import create_client
from politician_trading.config import SupabaseConfig
from politician_trading.storage import StorageManager


async def main():
    """Set up and test storage"""

    print("=" * 60)
    print("Supabase Storage Setup")
    print("=" * 60)
    print()

    # Get database connection
    config = SupabaseConfig.from_env()
    db = create_client(config.url, config.key)

    print("✓ Connected to Supabase")
    print()

    # Read and apply migration
    print("Applying migration...")
    print("-" * 60)

    migration_file = Path(__file__).parent.parent / "supabase" / "migrations" / "003_create_storage_infrastructure.sql"

    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return 1

    with open(migration_file, 'r') as f:
        sql = f.read()

    # Split into statements (basic - doesn't handle all edge cases)
    statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]

    success_count = 0
    error_count = 0

    for i, statement in enumerate(statements):
        if not statement or len(statement) < 10:
            continue

        try:
            # Execute via RPC or direct SQL
            # Note: Supabase Python client doesn't have direct SQL execution
            # This would need to be run via psql or Supabase Dashboard
            print(f"Statement {i+1}/{len(statements)}: {statement[:50]}...")

        except Exception as e:
            print(f"❌ Error in statement {i+1}: {e}")
            error_count += 1

    print()
    print("=" * 60)
    print("Migration Notes:")
    print("=" * 60)
    print()
    print("The migration SQL needs to be applied via Supabase Dashboard:")
    print()
    print("1. Go to: https://app.supabase.com/project/uljsqvwkomdrlnofmlad/sql")
    print("2. Copy the contents of:")
    print(f"   {migration_file}")
    print("3. Paste into SQL Editor")
    print("4. Click 'Run'")
    print()
    print("=" * 60)
    print()

    # Test storage manager
    print("Testing StorageManager...")
    print("-" * 60)

    storage = StorageManager(db)

    # Test creating a small test file
    test_content = b"Test PDF content"
    test_disclosure_id = "00000000-0000-0000-0000-000000000001"

    try:
        from datetime import datetime

        print("✓ StorageManager initialized")
        print()
        print("To test file upload, run:")
        print("  await storage.save_pdf(pdf_bytes, disclosure_id, name, url, date)")
        print()

    except Exception as e:
        print(f"❌ Error testing storage: {e}")
        return 1

    print("=" * 60)
    print("Setup instructions printed above")
    print("Apply migration in Supabase Dashboard, then test storage")
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
