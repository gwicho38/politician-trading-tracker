#!/usr/bin/env python3
"""
Inspect the raw QuiverQuant API response.

Downloads and shows the actual JSON structure.
"""

import sys
import os
import asyncio
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from supabase import create_client
from politician_trading.config import SupabaseConfig
from politician_trading.storage import StorageManager


async def main():
    """Inspect QuiverQuant response"""

    print("=" * 60)
    print("Inspecting QuiverQuant API Response")
    print("=" * 60)
    print()

    # Get database connection
    config = SupabaseConfig.from_env()
    db = create_client(config.url, config.service_role_key)
    storage = StorageManager(db)

    # Get most recent quiverquant file
    files = await storage.get_files_to_parse(bucket='api-responses', limit=10)

    quiver_files = [f for f in files if 'quiverquant/' in f['storage_path']]

    if not quiver_files:
        print("❌ No QuiverQuant files found")
        return 1

    # Get the most recent one
    latest = quiver_files[0]
    print(f"Latest file: {latest['storage_path']}")
    print(f"Downloaded: {latest['download_date']}")
    print()

    # Retrieve the response
    response = await storage.get_api_response(latest['storage_path'])

    print("Raw API Response:")
    print("-" * 60)
    print(json.dumps(response, indent=2))
    print()

    print("Response structure:")
    print("-" * 60)
    print(f"Type: {type(response)}")
    print(f"Keys: {list(response.keys()) if isinstance(response, dict) else 'N/A'}")

    if isinstance(response, dict):
        for key, value in response.items():
            if isinstance(value, list):
                print(f"  {key}: list with {len(value)} items")
                if value:
                    print(f"    First item type: {type(value[0])}")
                    if isinstance(value[0], dict):
                        print(f"    First item keys: {list(value[0].keys())}")
            else:
                print(f"  {key}: {type(value).__name__}")

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
