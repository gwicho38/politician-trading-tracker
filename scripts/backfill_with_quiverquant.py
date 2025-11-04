#!/usr/bin/env python3
"""
Backfill Historical Records Using QuiverQuant

This script replaces PDF-only placeholder records with actual parsed data
from the QuiverQuant API, which has already processed Senate PTR PDFs.

Strategy:
1. Query records marked as 'needs_pdf_parsing' (447 records)
2. For each record, fetch politician's trading history from QuiverQuant
3. Find matching transactions by date range and politician name
4. Replace placeholder with real transaction data
5. Mark original record as 'replaced_by_quiverquant'

Usage:
    python scripts/backfill_with_quiverquant.py --limit 10     # Test with 10 records
    python scripts/backfill_with_quiverquant.py --yes          # Process all records
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import argparse

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

from politician_trading.database.database import SupabaseClient
from politician_trading.config import SupabaseConfig
from politician_trading.sources.quiverquant import QuiverQuantSource


class QuiverQuantBackfiller:
    """Backfill historical PDF records using QuiverQuant API."""

    def __init__(self, db: SupabaseClient, quiver_source: QuiverQuantSource):
        self.db = db
        self.quiver = quiver_source
        self.stats = {
            "total_records": 0,
            "processed": 0,
            "replaced": 0,
            "no_match": 0,
            "errors": 0,
        }

    def get_pdf_records(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get records that need backfilling from QuiverQuant."""
        query = self.db.client.table("trading_disclosures")\
            .select("*")\
            .eq("status", "needs_pdf_parsing")\
            .order("transaction_date", desc=True)

        if limit:
            query = query.limit(limit)

        response = query.execute()
        return response.data if response.data else []

    async def find_matching_transactions(
        self,
        politician_name: str,
        date_range_start: datetime,
        date_range_end: datetime
    ) -> List[Dict[str, Any]]:
        """
        Fetch transactions from QuiverQuant for a politician in a date range.

        Args:
            politician_name: Full name of politician
            date_range_start: Start of date range to search
            date_range_end: End of date range to search

        Returns:
            List of matching transactions from QuiverQuant
        """
        try:
            # QuiverQuant fetches recent transactions (usually last 90 days)
            # For historical data, we'd need the paid tier
            data = await self.quiver.fetch_data()

            if not data:
                return []

            # Filter by politician name and date range
            matches = []
            for transaction in data:
                trans_name = transaction.get("politician_name", "").lower()
                target_name = politician_name.lower()

                # Simple name matching (could be improved)
                if target_name in trans_name or trans_name in target_name:
                    # Check date range
                    trans_date_str = transaction.get("transaction_date")
                    if trans_date_str:
                        try:
                            trans_date = datetime.fromisoformat(
                                trans_date_str.replace("Z", "+00:00")
                            )
                            if date_range_start <= trans_date <= date_range_end:
                                matches.append(transaction)
                        except:
                            continue

            return matches

        except Exception as e:
            print(f"  Error fetching QuiverQuant data: {e}")
            return []

    async def backfill_record(self, record: Dict[str, Any]) -> bool:
        """
        Backfill a single PDF placeholder record.

        Args:
            record: The PDF placeholder record to replace

        Returns:
            True if successful, False otherwise
        """
        try:
            politician_name = record.get("politician_name", "")
            transaction_date_str = record.get("transaction_date")

            if not transaction_date_str:
                print(f"  ❌ No transaction date for record {record.get('id')}")
                return False

            # Parse transaction date
            transaction_date = datetime.fromisoformat(
                transaction_date_str.replace("Z", "+00:00")
            )

            # Search in a 30-day window around the transaction date
            date_range_start = transaction_date - timedelta(days=15)
            date_range_end = transaction_date + timedelta(days=15)

            print(f"\n  👤 {politician_name}")
            print(f"  📅 Date range: {date_range_start.date()} to {date_range_end.date()}")

            # Find matching transactions from QuiverQuant
            matches = await self.find_matching_transactions(
                politician_name,
                date_range_start,
                date_range_end
            )

            if not matches:
                print(f"  ⚠️  No matching transactions found in QuiverQuant")
                # Mark as no_match but keep the record
                self.db.client.table("trading_disclosures")\
                    .update({"status": "pdf_no_quiver_match"})\
                    .eq("id", record["id"])\
                    .execute()
                self.stats["no_match"] += 1
                return False

            print(f"  ✅ Found {len(matches)} matching transactions")

            # Insert new records from QuiverQuant
            new_records = []
            for match in matches:
                # Create normalized disclosure record
                new_record = {
                    "politician_name": match.get("politician_name", politician_name),
                    "politician_bioguide_id": record.get("politician_bioguide_id"),
                    "transaction_date": match.get("transaction_date"),
                    "disclosure_date": match.get("disclosure_date"),
                    "asset_name": match.get("asset_name", ""),
                    "asset_ticker": match.get("asset_ticker", ""),
                    "asset_type": match.get("asset_type", "Stock"),
                    "transaction_type": match.get("transaction_type", ""),
                    "amount": match.get("amount", ""),
                    "party": record.get("party"),
                    "role": record.get("role"),
                    "state": record.get("state"),
                    "source": "quiverquant",
                    "source_url": match.get("source_url", ""),
                    "raw_data": match,
                    "status": "active",
                }
                new_records.append(new_record)

            # Insert new records
            if new_records:
                self.db.client.table("trading_disclosures").insert(new_records).execute()
                print(f"  📝 Inserted {len(new_records)} new records")

            # Mark original placeholder as replaced
            self.db.client.table("trading_disclosures")\
                .update({
                    "status": "replaced_by_quiverquant",
                    "notes": f"Replaced with {len(new_records)} records from QuiverQuant"
                })\
                .eq("id", record["id"])\
                .execute()

            self.stats["replaced"] += 1
            return True

        except Exception as e:
            print(f"  ❌ Error processing record: {e}")
            self.stats["errors"] += 1
            return False

    async def run(self, limit: Optional[int] = None, batch_size: int = 10):
        """
        Run the backfill process.

        Args:
            limit: Maximum number of records to process (None = all)
            batch_size: Number of records to process before pausing
        """
        print("\n" + "="*80)
        print("QUIVERQUANT BACKFILL - Historical PDF Records")
        print("="*80)

        # Get records to process
        records = self.get_pdf_records(limit)
        self.stats["total_records"] = len(records)

        if not records:
            print("\n✅ No records need backfilling!")
            return

        print(f"\n📊 Found {len(records)} records to backfill")
        print(f"   Batch size: {batch_size}")
        print(f"   Rate limiting: 2s between records\n")

        # Process records in batches
        for i, record in enumerate(records, 1):
            print(f"\n[{i}/{len(records)}] Processing record {record.get('id')[:8]}...")

            success = await self.backfill_record(record)
            self.stats["processed"] += 1

            # Rate limiting
            if i < len(records):  # Don't wait after last record
                await asyncio.sleep(2)  # 2 seconds between requests

            # Pause between batches
            if i % batch_size == 0 and i < len(records):
                print(f"\n⏸  Batch complete. Pausing for 10 seconds...")
                await asyncio.sleep(10)

        # Print final statistics
        self.print_stats()

    def print_stats(self):
        """Print final statistics."""
        print("\n" + "="*80)
        print("BACKFILL STATISTICS")
        print("="*80)
        print(f"Total records:     {self.stats['total_records']}")
        print(f"Processed:         {self.stats['processed']}")
        print(f"Replaced:          {self.stats['replaced']} ✅")
        print(f"No match found:    {self.stats['no_match']} ⚠️")
        print(f"Errors:            {self.stats['errors']} ❌")

        if self.stats['processed'] > 0:
            success_rate = (self.stats['replaced'] / self.stats['processed']) * 100
            print(f"\nSuccess rate:      {success_rate:.1f}%")

        print("\n" + "="*80)


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Backfill PDF records with QuiverQuant data"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of records to process (for testing)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of records per batch (default: 10)"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt"
    )

    args = parser.parse_args()

    try:
        # Initialize clients
        config = SupabaseConfig.from_env()
        db = SupabaseClient(config)

        print("\n✅ Connected to Supabase")

        # Check QuiverQuant API key
        import os
        if not os.getenv("QUIVERQUANT_API_KEY"):
            print("\n❌ ERROR: QUIVERQUANT_API_KEY not found in environment")
            print("\nPlease set your QuiverQuant API key:")
            print("  export QUIVERQUANT_API_KEY='your-api-key'")
            print("\nGet an API key at: https://www.quiverquant.com/")
            sys.exit(1)

        quiver = QuiverQuantSource()
        print("✅ QuiverQuant API configured")

        # Confirm before proceeding
        if not args.yes:
            limit_text = f"first {args.limit}" if args.limit else "ALL"
            response = input(f"\nProcess {limit_text} PDF records? [y/N]: ")
            if response.lower() != 'y':
                print("Cancelled.")
                sys.exit(0)

        # Run backfill
        backfiller = QuiverQuantBackfiller(db, quiver)
        await backfiller.run(limit=args.limit, batch_size=args.batch_size)

        print("\n✅ Backfill complete!")

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
