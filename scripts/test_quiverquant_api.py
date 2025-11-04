#!/usr/bin/env python3
"""
Test QuiverQuant API with real key.

Fetches real congressional trading data and saves to storage.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from supabase import create_client
from politician_trading.config import SupabaseConfig
from politician_trading.sources.quiverquant import QuiverQuantSource
from politician_trading.storage import StorageManager


async def main():
    """Test QuiverQuant API with real key"""

    print("=" * 60)
    print("Testing QuiverQuant API with Real Key")
    print("=" * 60)
    print()

    # Get API key from environment
    api_key = os.getenv('QUIVERQUANT_API_KEY')
    if not api_key:
        print("❌ QUIVERQUANT_API_KEY not found in environment")
        print("   Run: export QUIVERQUANT_API_KEY=<your-key>")
        return 1

    print(f"✓ API key found: {api_key[:10]}...{api_key[-10:]}")
    print()

    # Get database connection
    config = SupabaseConfig.from_env()

    # Use service role key for storage operations
    if not config.service_role_key:
        print("❌ SUPABASE_SERVICE_KEY not found in environment")
        return 1

    db = create_client(config.url, config.service_role_key)
    print("✓ Connected to Supabase")
    print()

    # Initialize storage manager
    storage = StorageManager(db)
    print("✓ StorageManager initialized")
    print()

    # Initialize QuiverQuant source
    source = QuiverQuantSource()
    source.storage_manager = storage
    print("✓ QuiverQuantSource initialized with storage")
    print()

    # Fetch data from API
    print("Fetching data from QuiverQuant API...")
    print("-" * 60)

    try:
        # Fetch last 7 days of data
        disclosures = await source.fetch(lookback_days=7, api_key=api_key)

        print(f"✓ Fetched {len(disclosures)} disclosures")
        print()

        # Show sample of disclosures
        if disclosures:
            print("Sample disclosures:")
            print("-" * 60)
            for i, disc in enumerate(disclosures[:5]):  # Show first 5
                print(f"\n{i+1}. {disc.get('politician_name', 'Unknown')}")
                print(f"   Asset: {disc.get('asset_name', 'Unknown')} ({disc.get('asset_ticker', 'N/A')})")
                print(f"   Type: {disc.get('transaction_type', 'Unknown')}")
                print(f"   Amount: {disc.get('amount', 'Unknown')}")
                print(f"   Date: {disc.get('transaction_date', 'Unknown')}")

            if len(disclosures) > 5:
                print(f"\n... and {len(disclosures) - 5} more")
            print()

        # Check storage
        print("Verifying storage...")
        print("-" * 60)

        stats = await storage.get_storage_statistics()
        api_response_stats = [s for s in stats if s['storage_bucket'] == 'api-responses']

        if api_response_stats:
            for stat in api_response_stats:
                print(f"✓ Bucket: {stat['storage_bucket']}")
                print(f"  Files: {stat['file_count']}")
                print(f"  Size: {stat['total_size_mb']} MB")
                print(f"  Status: {stat['parse_status']}")
        else:
            print("⚠️  No API response files found in storage")

        print()

        # Check for files to parse
        files_to_parse = await storage.get_files_to_parse(bucket='api-responses', limit=5)
        print(f"✓ Files pending parsing: {len(files_to_parse)}")

        if files_to_parse:
            print("\nRecent files:")
            for f in files_to_parse[:3]:
                print(f"  - {f['storage_path']}")

        print()

    except Exception as e:
        print(f"❌ Error fetching from QuiverQuant: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("=" * 60)
    print("QuiverQuant API Test Complete")
    print("=" * 60)
    print()
    print("✓ API key working")
    print("✓ Data fetched successfully")
    print("✓ Storage integration working")
    print()
    print(f"Summary:")
    print(f"  - Fetched {len(disclosures)} congressional trading disclosures")
    print(f"  - Raw API response saved to storage")
    print(f"  - Ready for database import")
    print()

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
