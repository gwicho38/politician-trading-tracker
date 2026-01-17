import os
from typing import Optional
from supabase import create_client, Client

def get_supabase() -> Optional[Client]:
    """Get Supabase client."""
    supabase_url = os.getenv("SUPABASE_URL", "https://uljsqvwkomdrlnofmlad.supabase.co")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not supabase_key or not supabase_url:
        return None
    return create_client(supabase_url, supabase_key)

# def get_supabase_client() -> Client:
#     # """Create Supabase client from environment variables."""
#     # url = os.environ.get("SUPABASE_URL")
#     # key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

#     # if not url or not key:
#     #     raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

#     # return create_client(url, key)