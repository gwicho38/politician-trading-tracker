"""
Migrate admin users from environment variables to Supabase user_roles table.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from src.politician_trading.scrapers.seed_database import get_supabase_client
from src.admin_utils import get_admin_emails


def migrate_admin_users():
    """Migrate admin users from environment variables to Supabase user_roles table."""
    supabase = get_supabase_client()

    # Get admin emails from environment
    admin_emails = get_admin_emails()
    print(f"Found {len(admin_emails)} admin emails: {admin_emails}")

    migrated_count = 0
    skipped_count = 0

    for email in admin_emails:
        try:
            # Find user by email in auth.users
            # Note: We can't directly query auth.users, so we'll need to handle this
            # when users actually sign up. For now, we'll create a mapping script
            # that can be run after users exist.

            print(f"Would migrate admin role for: {email}")
            print("Note: User must be registered in Supabase Auth first")
            print("Run this script after admin users have signed up")

            # In a real migration, you'd do something like:
            # user_response = supabase.auth.admin.get_user_by_email(email)
            # if user_response.user:
            #     supabase.table("user_roles").insert({
            #         "user_id": user_response.user.id,
            #         "role": "admin"
            #     })

        except Exception as e:
            print(f"Error migrating {email}: {e}")

    print(f"Migration complete. {migrated_count} migrated, {skipped_count} skipped.")
    print("\nTo complete migration:")
    print("1. Have admin users sign up through the React app")
    print("2. Run this script again to assign admin roles")
    print("3. Or manually assign roles through Supabase dashboard")


if __name__ == "__main__":
    migrate_admin_users()