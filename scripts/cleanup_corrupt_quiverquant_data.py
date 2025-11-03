#!/usr/bin/env python3
"""
Clean up corrupt QuiverQuant data in the database

The QuiverQuant scraper had a bug where:
- asset_ticker = "STOCK" (should be the actual ticker like "FIG")
- asset_name = "STOCK" (should be company name like "Figma Inc")
- Politician name ended up in wrong table

This script deletes all corrupt QuiverQuant records so they can be re-scraped correctly.
"""
import os
import sys
from pathlib import Path

# Add src to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir / "src"))

from politician_trading.database.database import SupabaseClient
from politician_trading.config import SupabaseConfig
from politician_trading.utils.logger import create_logger

logger = create_logger("cleanup_corrupt_data")

def main():
    import sys

    # Check for --force flag
    force = "--force" in sys.argv

    # Connect to database
    config = SupabaseConfig.from_env()
    db = SupabaseClient(config)

    print("\n" + "="*80)
    print("Cleaning up corrupt QuiverQuant data")
    print("="*80 + "\n")

    # Find corrupt records (where asset_ticker = "STOCK" or asset_name = "STOCK")
    response = db.client.table("trading_disclosures")\
        .select("id, asset_ticker, asset_name, source_url")\
        .or_("asset_ticker.eq.STOCK,asset_name.eq.STOCK")\
        .execute()

    corrupt_records = response.data
    count = len(corrupt_records)

    print(f"Found {count} corrupt records\n")

    if count == 0:
        print("✅ No corrupt records found!")
        return

    # Show sample
    print("Sample corrupt records:")
    for i, record in enumerate(corrupt_records[:5]):
        print(f"{i+1}. ID: {record['id']}")
        print(f"   Ticker: {record['asset_ticker']}")
        print(f"   Asset: {record['asset_name']}")
        print(f"   Source: {record['source_url']}")
        print()

    # Confirm deletion
    if not force:
        try:
            response = input(f"\n❓ Delete these {count} corrupt records? (yes/no): ")
            if response.lower() != "yes":
                print("❌ Cancelled")
                return
        except EOFError:
            print("\n❌ Cannot prompt for confirmation (use --force flag to skip)")
            return

    # Delete records
    print(f"\n🗑️  Deleting {count} corrupt records...")

    deleted = 0
    for record in corrupt_records:
        try:
            db.client.table("trading_disclosures")\
                .delete()\
                .eq("id", record['id'])\
                .execute()
            deleted += 1

            if deleted % 10 == 0:
                print(f"   Deleted {deleted}/{count}...")

        except Exception as e:
            logger.error(f"Failed to delete record {record['id']}: {e}")

    print(f"\n✅ Deleted {deleted} corrupt records")
    print("\n💡 Run the data collection again to fetch clean data")

if __name__ == "__main__":
    main()
