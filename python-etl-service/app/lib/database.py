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
