#!/usr/bin/env python3
"""
Cleanup script for malformed politician records in the database
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from politician_trading.database.database import SupabaseClient
from politician_trading.config import SupabaseConfig


def find_malformed_politicians(db):
    """Find politicians that are clearly malformed"""
    print("🔍 Searching for malformed politician records...\n")

    malformed = []

    # 1. Check for asset names as politicians (like FIGMA)
    response = db.client.table('politicians').select('*').ilike('full_name', '%INC%').execute()
    if response.data:
        print(f"Found {len(response.data)} politicians with 'INC' in name (likely companies):")
        for p in response.data:
            print(f"  - {p['full_name']} (ID: {p['id']})")
            malformed.append(p['id'])

    # 2. Check for test/placeholder politicians
    test_names = [
        'California Politician Unknown',
        'Sample MEP',
        'Test Politician',
        'Unknown Politician'
    ]

    for name in test_names:
        response = db.client.table('politicians').select('*').eq('full_name', name).execute()
        if response.data:
            print(f"\nFound {len(response.data)} '{name}' records:")
            for p in response.data:
                print(f"  - ID: {p['id']}")
                malformed.append(p['id'])

    # 3. Check for politicians with asset ticker patterns in name
    response = db.client.table('politicians').select('*').ilike('full_name', '%CLASS A%').execute()
    if response.data:
        print(f"\nFound {len(response.data)} politicians with 'CLASS A' in name:")
        for p in response.data:
            print(f"  - {p['full_name']} (ID: {p['id']})")
            malformed.append(p['id'])

    response = db.client.table('politicians').select('*').ilike('full_name', '%CLASS B%').execute()
    if response.data:
        print(f"\nFound {len(response.data)} politicians with 'CLASS B' in name:")
        for p in response.data:
            print(f"  - {p['full_name']} (ID: {p['id']})")
            malformed.append(p['id'])

    return list(set(malformed))  # Remove duplicates


def check_disclosures(db, politician_ids):
    """Check which malformed politicians have associated disclosures"""
    print("\n📊 Checking for associated trading disclosures...\n")

    politicians_with_disclosures = []

    for pid in politician_ids:
        response = db.client.table('trading_disclosures').select('id').eq('politician_id', pid).execute()
        count = len(response.data) if response.data else 0

        if count > 0:
            # Get politician name
            pol_response = db.client.table('politicians').select('full_name').eq('id', pid).execute()
            name = pol_response.data[0]['full_name'] if pol_response.data else 'Unknown'

            print(f"  ⚠️  Politician '{name}' has {count} associated disclosures")
            politicians_with_disclosures.append((pid, name, count))

    return politicians_with_disclosures


def delete_politicians(db, politician_ids, dry_run=True):
    """Delete malformed politician records"""
    print(f"\n{'[DRY RUN] ' if dry_run else ''}🗑️  Deleting {len(politician_ids)} malformed politicians...\n")

    for pid in politician_ids:
        # Get politician name first
        response = db.client.table('politicians').select('full_name').eq('id', pid).execute()
        name = response.data[0]['full_name'] if response.data else 'Unknown'

        if not dry_run:
            # Delete the politician
            db.client.table('politicians').delete().eq('id', pid).execute()
            print(f"  ✅ Deleted: {name} ({pid})")
        else:
            print(f"  🔍 Would delete: {name} ({pid})")


def main():
    """Main cleanup function"""
    print("=" * 70)
    print("🧹 Malformed Politician Records Cleanup")
    print("=" * 70)

    # Connect to database
    config = SupabaseConfig.from_env()
    db = SupabaseClient(config)

    # Find malformed politicians
    malformed_ids = find_malformed_politicians(db)

    if not malformed_ids:
        print("\n✅ No malformed politician records found!")
        return 0

    print(f"\n📋 Total malformed politician records found: {len(malformed_ids)}")

    # Check for associated disclosures
    with_disclosures = check_disclosures(db, malformed_ids)

    # Separate into those with and without disclosures
    safe_to_delete = [pid for pid in malformed_ids if pid not in [x[0] for x in with_disclosures]]
    needs_review = [x for x in with_disclosures]

    print("\n" + "=" * 70)
    print("📊 Cleanup Summary")
    print("=" * 70)
    print(f"Safe to delete (no disclosures): {len(safe_to_delete)}")
    print(f"Needs review (has disclosures): {len(needs_review)}")

    if needs_review:
        print("\n⚠️  WARNING: The following politicians have associated disclosures:")
        for pid, name, count in needs_review:
            print(f"  - {name}: {count} disclosures (ID: {pid})")
        print("\nThese should be reviewed manually before deletion.")
        print("The disclosures might need to be reassigned to correct politicians.")

    # Perform dry run deletion
    if safe_to_delete:
        print("\n" + "=" * 70)
        print("🧪 DRY RUN - Showing what would be deleted")
        print("=" * 70)
        delete_politicians(db, safe_to_delete, dry_run=True)

        print("\n" + "=" * 70)
        print("To actually delete these records, run:")
        print("  python scripts/cleanup_malformed_politicians.py --confirm")
        print("=" * 70)

    return 0


if __name__ == "__main__":
    import sys

    # Check for --confirm flag
    if "--confirm" in sys.argv:
        print("⚠️  CONFIRMATION REQUIRED")
        print("This will DELETE malformed politician records from the database.")
        response = input("Are you sure? Type 'yes' to confirm: ")

        if response.lower() == 'yes':
            # Re-run with actual deletion
            config = SupabaseConfig.from_env()
            db = SupabaseClient(config)
            malformed_ids = find_malformed_politicians(db)
            with_disclosures = check_disclosures(db, malformed_ids)
            safe_to_delete = [pid for pid in malformed_ids if pid not in [x[0] for x in with_disclosures]]

            if safe_to_delete:
                delete_politicians(db, safe_to_delete, dry_run=False)
                print("\n✅ Cleanup complete!")
        else:
            print("❌ Deletion cancelled.")
    else:
        sys.exit(main())
