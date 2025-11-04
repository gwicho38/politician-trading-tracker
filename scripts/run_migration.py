"""
Run database migration for user_api_keys table
"""

import os
import sys
from pathlib import Path

# Get project directory
parent_dir = Path(__file__).parent.parent


def run_migration():
    """Display instructions for running the user_api_keys table migration"""

    # Read migration SQL
    migration_file = parent_dir / "supabase" / "migrations" / "004_create_user_api_keys_table.sql"

    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False

    print(f"📄 Reading migration from: {migration_file}")

    with open(migration_file, 'r') as f:
        migration_sql = f.read()

    print(f"📝 Migration SQL ({len(migration_sql)} characters)")

    # Get Supabase URL from environment
    supabase_url = os.getenv("SUPABASE_URL", "")

    if supabase_url:
        # Extract project ID from URL
        project_id = supabase_url.replace("https://", "").split(".")[0]
        dashboard_url = f"https://supabase.com/dashboard/project/{project_id}/sql/new"
    else:
        dashboard_url = "https://supabase.com/dashboard"

    print("\n" + "="*80)
    print("📋 MIGRATION INSTRUCTIONS")
    print("="*80)
    print("\nTo apply this migration:")
    print("\n1. Go to your Supabase SQL Editor:")
    print(f"   {dashboard_url}")
    print("\n2. Click 'New Query'")
    print("\n3. Copy and paste the migration SQL shown below")
    print("\n4. Click 'Run' to execute the migration")
    print("\n" + "="*80)
    print("\n📝 MIGRATION SQL:\n")
    print("="*80)
    print(migration_sql)
    print("="*80)

    return True


if __name__ == "__main__":
    print("🚀 Running user_api_keys table migration\n")
    success = run_migration()

    if success:
        print("\n✅ Migration prepared successfully")
        print("⚠️  Please run the migration in Supabase SQL Editor (see instructions above)")
        sys.exit(0)
    else:
        print("\n❌ Migration failed")
        sys.exit(1)
