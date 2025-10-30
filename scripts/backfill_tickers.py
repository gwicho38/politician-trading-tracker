#!/usr/bin/env python3
"""
Backfill missing tickers in existing trading_disclosures
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from politician_trading.config import SupabaseConfig
from politician_trading.database.database import SupabaseClient
from politician_trading.utils.ticker_utils import extract_ticker_from_asset_name
from dotenv import load_dotenv

load_dotenv()


def backfill_tickers():
    """Backfill missing tickers in trading_disclosures table"""

    print("🔧 Initializing Supabase client...")
    config = SupabaseConfig.from_env()
    db = SupabaseClient(config)

    print("📊 Fetching disclosures with missing tickers...")

    # Get all disclosures where ticker is null or empty
    response = db.client.table("trading_disclosures")\
        .select("id, asset_name, asset_ticker")\
        .is_("asset_ticker", "null")\
        .execute()

    disclosures_no_ticker = response.data or []

    # Also get disclosures where ticker is empty string
    response2 = db.client.table("trading_disclosures")\
        .select("id, asset_name, asset_ticker")\
        .eq("asset_ticker", "")\
        .execute()

    disclosures_empty_ticker = response2.data or []

    # Combine both lists
    all_disclosures = disclosures_no_ticker + disclosures_empty_ticker

    print(f"Found {len(all_disclosures)} disclosures with missing tickers")

    if not all_disclosures:
        print("✅ All disclosures already have tickers!")
        return

    updated = 0
    failed = 0
    no_ticker_found = 0

    for i, disclosure in enumerate(all_disclosures, 1):
        disclosure_id = disclosure['id']
        asset_name = disclosure['asset_name']

        if not asset_name:
            no_ticker_found += 1
            continue

        # Extract ticker
        ticker = extract_ticker_from_asset_name(asset_name)

        if ticker:
            try:
                # Update the record
                db.client.table("trading_disclosures")\
                    .update({"asset_ticker": ticker})\
                    .eq("id", disclosure_id)\
                    .execute()

                updated += 1
                print(f"[{i}/{len(all_disclosures)}] ✅ {asset_name[:50]:50} → {ticker}")
            except Exception as e:
                failed += 1
                print(f"[{i}/{len(all_disclosures)}] ❌ Failed to update {disclosure_id}: {e}")
        else:
            no_ticker_found += 1
            print(f"[{i}/{len(all_disclosures)}] ⚠️  No ticker found for: {asset_name[:60]}")

    print("\n" + "="*80)
    print(f"📊 Backfill Summary:")
    print(f"   Total disclosures: {len(all_disclosures)}")
    print(f"   ✅ Updated: {updated}")
    print(f"   ⚠️  No ticker found: {no_ticker_found}")
    print(f"   ❌ Failed: {failed}")
    print("="*80)

    if updated > 0:
        print(f"\n🎉 Successfully backfilled {updated} tickers!")

    if no_ticker_found > 0:
        print(f"\nℹ️  {no_ticker_found} assets couldn't be matched to tickers.")
        print("   These might be bonds, funds, or other non-stock assets.")


if __name__ == "__main__":
    try:
        backfill_tickers()
    except KeyboardInterrupt:
        print("\n\n⚠️  Backfill interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
