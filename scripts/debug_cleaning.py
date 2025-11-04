#!/usr/bin/env python3
"""Debug why cleaning stage filters so many records."""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from politician_trading.sources.quiverquant import QuiverQuantSource
from politician_trading.storage import StorageManager
from supabase import create_client
from politician_trading.config import SupabaseConfig
import asyncio


async def main():
    api_key = os.getenv('QUIVERQUANT_API_KEY')
    config = SupabaseConfig.from_env()
    db = create_client(config.url, config.service_role_key)

    source = QuiverQuantSource()
    source.storage_manager = StorageManager(db)

    # Fetch data
    disclosures = await source.fetch(lookback_days=7, api_key=api_key)

    print(f"Total disclosures: {len(disclosures)}")
    print()

    # Check which records have empty/missing fields
    required_fields = {"politician_name", "transaction_date", "disclosure_date", "asset_name", "transaction_type"}

    valid_count = 0
    invalid_count = 0

    for i, disc in enumerate(disclosures[:50]):  # Check first 50
        missing = []
        for field in required_fields:
            value = disc.get(field)
            if value is None or value == "":
                missing.append(field)

        if missing:
            invalid_count += 1
            if invalid_count <= 5:  # Show first 5 invalid
                print(f"Record {i}: Missing/empty fields: {missing}")
                print(f"  Data: {disc}")
                print()
        else:
            valid_count += 1

    print(f"Valid: {valid_count}")
    print(f"Invalid: {invalid_count}")


if __name__ == "__main__":
    asyncio.run(main())
