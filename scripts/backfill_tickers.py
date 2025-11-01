#!/usr/bin/env python3
"""
Backfill missing tickers in existing trading_disclosures
Can be run manually or via cron for scheduled cleanup.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from politician_trading.config import SupabaseConfig
from politician_trading.database.database import SupabaseClient
from politician_trading.utils.ticker_utils import extract_ticker_from_asset_name
from politician_trading.utils.logger import create_logger
from dotenv import load_dotenv

load_dotenv()

logger = create_logger("scheduled_backfill")


def backfill_tickers():
    """Backfill missing tickers in trading_disclosures table"""

    start_time = datetime.now()
    logger.info("Starting ticker backfill job")

    print("🔧 Initializing Supabase client...")
    logger.info("Initializing database connection")
    config = SupabaseConfig.from_env()
    db = SupabaseClient(config)

    print("📊 Fetching disclosures with missing tickers...")
    logger.info("Querying disclosures with missing tickers")

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
    logger.info("Found disclosures with missing tickers", metadata={
        "count": len(all_disclosures)
    })

    if not all_disclosures:
        print("✅ All disclosures already have tickers!")
        logger.info("No disclosures need ticker backfill")
        return 0

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
                logger.debug("Updated disclosure with ticker", metadata={
                    "disclosure_id": disclosure_id,
                    "asset_name": asset_name,
                    "ticker": ticker
                })
            except Exception as e:
                failed += 1
                print(f"[{i}/{len(all_disclosures)}] ❌ Failed to update {disclosure_id}: {e}")
                logger.error("Failed to update disclosure", error=e, metadata={
                    "disclosure_id": disclosure_id,
                    "asset_name": asset_name,
                    "ticker": ticker
                })
        else:
            no_ticker_found += 1
            print(f"[{i}/{len(all_disclosures)}] ⚠️  No ticker found for: {asset_name[:60]}")
            logger.debug("No ticker found", metadata={
                "disclosure_id": disclosure_id,
                "asset_name": asset_name
            })

        # Log progress every 100 items
        if i % 100 == 0:
            logger.info("Backfill progress", metadata={
                "processed": i,
                "updated": updated,
                "no_ticker_found": no_ticker_found,
                "failed": failed
            })

    duration = (datetime.now() - start_time).total_seconds()

    print("\n" + "="*80)
    print(f"📊 Backfill Summary:")
    print(f"   Total disclosures: {len(all_disclosures)}")
    print(f"   ✅ Updated: {updated}")
    print(f"   ⚠️  No ticker found: {no_ticker_found}")
    print(f"   ❌ Failed: {failed}")
    print("="*80)

    logger.info("Ticker backfill completed", metadata={
        "total_processed": len(all_disclosures),
        "total_updated": updated,
        "total_no_ticker_found": no_ticker_found,
        "total_failed": failed,
        "duration_seconds": duration
    })

    if updated > 0:
        print(f"\n🎉 Successfully backfilled {updated} tickers!")

    if no_ticker_found > 0:
        print(f"\nℹ️  {no_ticker_found} assets couldn't be matched to tickers.")
        print("   These might be bonds, funds, or other non-stock assets.")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    try:
        exit_code = backfill_tickers()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Backfill interrupted by user")
        logger.warning("Backfill interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error("Backfill job failed", error=e)
        import traceback
        traceback.print_exc()
        sys.exit(1)
