#!/usr/bin/env python3
"""
Test US Senate source directly.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from politician_trading.sources import get_source

import pytest


@pytest.mark.asyncio
async def test_us_senate_source():
    """Test the US Senate source"""

    print("=" * 60)
    print("Testing US Senate Source")
    print("=" * 60)
    print()

    # Get the source
    source = get_source('us_senate')
    print(f"✓ Got source: {source}")
    print(f"  Config: {source.config}")
    print()

    # Fetch data
    print("Fetching data (30 day lookback)...")
    print("-" * 60)

    try:
        async with source:  # Use context manager to properly close session
            raw_data = await source.fetch(lookback_days=30)

            print()
            print("=" * 60)
            print(f"✅ Fetched {len(raw_data)} records")
            print("=" * 60)
            print()

            if raw_data:
                print("Sample record:")
                print("-" * 60)
                import json
                print(json.dumps(raw_data[0], indent=2, default=str))
                print()

            return len(raw_data)

    except Exception as e:
        print()
        print("=" * 60)
        print("❌ Fetch failed")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 0


if __name__ == "__main__":
    count = asyncio.run(test_us_senate_source())
    sys.exit(0 if count > 0 else 1)
