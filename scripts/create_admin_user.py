#!/usr/bin/env python3
"""
Create admin user for politician trading tracker.
This script creates a user in Supabase Auth and assigns admin role.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def create_admin_user():
    """Create admin user with email and password"""
    
    email = "luis@lefv.io"
    password = "servicetoanothertoastATp3#Q79"
    
    print(f"Creating admin user: {email}")
    print("Note: This requires SUPABASE_SERVICE_ROLE_KEY to be set in environment")
    
    # Get Supabase URL and service role key
    supabase_url = os.getenv('SUPABASE_URL')
    service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not service_role_key:
        print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables")
        print("Please set these in your .env file or environment")
        return False
    
    try:
        # Import here to avoid issues if dependencies aren't available
        from supabase import create_client, Client
        
        supabase: Client = create_client(supabase_url, service_role_key)
        
        # Create user with admin privileges
        user_response = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,  # Auto-confirm email
            "user_metadata": {
                "role": "admin",
                "created_by": "setup_script"
            }
        })
        
        if user_response.user:
            user_id = user_response.user.id
            print(f"✅ User created with ID: {user_id}")
            
            # Assign admin role in user_roles table
            role_response = supabase.table("user_roles").insert({
                "user_id": user_id,
                "role": "admin"
            }).execute()
            
            if role_response.data:
                print("✅ Admin role assigned successfully")
                return True
            else:
                print("❌ Failed to assign admin role")
                return False
        else:
            print(f"❌ Failed to create user: {user_response}")
            return False
            
    except ImportError:
        print("❌ Supabase Python client not available")
        print("Install with: pip install supabase")
        return False
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        return False

if __name__ == "__main__":
    success = create_admin_user()
    if success:
        print("\n🎉 Admin user created successfully!")
        print("You can now log in with:")
        print(f"Email: luis@lefv.io")
        print(f"Password: servicetoanothertoastATp3#Q79")
    else:
        print("\n❌ Failed to create admin user")
        print("You may need to create the user manually in Supabase Dashboard")
