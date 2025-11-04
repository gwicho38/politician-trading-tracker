#!/usr/bin/env python3
"""
Mark PDF-only disclosure records for reprocessing.

This script identifies records in the database that are placeholders
for PDF disclosures and marks them with a special status.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from supabase import create_client
from politician_trading.config import SupabaseConfig


def main():
    """Mark PDF records for reprocessing"""

    print("=" * 60)
    print("Marking PDF-only Records for Reprocessing")
    print("=" * 60)
    print()

    # Get database connection
    config = SupabaseConfig.from_env()
    db = create_client(config.url, config.key)

    # Query for PDF-only records
    print("Querying for PDF-only records...")
    print("-" * 60)

    response = db.table("trading_disclosures").select("*").or_(
        "asset_type.eq.PDF Disclosed Filing,"
        "asset_ticker.eq.N/A,"
        "asset_name.ilike.%scanned PDF%"
    ).execute()

    pdf_records = response.data if response.data else []

    print(f"Found {len(pdf_records)} PDF-only records")
    print()

    if not pdf_records:
        print("No PDF records found to process")
        return 0

    # Show sample
    print("Sample records:")
    print("-" * 60)
    for record in pdf_records[:5]:
        print(f"ID: {record['id']}")
        print(f"  Politician: {record.get('politician_id')}")
        print(f"  Date: {record.get('transaction_date')}")
        print(f"  Asset: {record.get('asset_name', '')[:50]}...")
        print()

    # Ask for confirmation
    response = input(f"\nMark these {len(pdf_records)} records as 'needs_pdf_parsing'? (y/n): ")

    if response.lower() != 'y':
        print("Cancelled")
        return 0

    # Update records
    print("\nUpdating records...")
    print("-" * 60)

    updated_count = 0
    error_count = 0

    for record in pdf_records:
        try:
            # Update status
            db.table("trading_disclosures").update({
                "status": "needs_pdf_parsing"
            }).eq("id", record['id']).execute()

            updated_count += 1

            if updated_count % 100 == 0:
                print(f"Updated {updated_count}/{len(pdf_records)} records...")

        except Exception as e:
            print(f"Error updating record {record['id']}: {e}")
            error_count += 1

    print()
    print("=" * 60)
    print(f"✅ Updated {updated_count} records")
    if error_count > 0:
        print(f"⚠️  {error_count} errors")
    print("=" * 60)

    # Show statistics
    print("\nCurrent status distribution:")
    print("-" * 60)

    status_query = db.table("trading_disclosures").select("status").execute()
    statuses = {}
    for record in status_query.data:
        status = record.get('status', 'unknown')
        statuses[status] = statuses.get(status, 0) + 1

    for status, count in sorted(statuses.items()):
        print(f"  {status}: {count}")

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
