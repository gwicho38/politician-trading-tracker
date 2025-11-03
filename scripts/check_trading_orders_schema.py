"""Check the actual schema of trading_orders table in the database"""
import os
import sys
from pathlib import Path

# Add src to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir / "src"))

from politician_trading.database.database import SupabaseClient
from supabase import create_client

# Get credentials from environment
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")

if not supabase_url or not supabase_key:
    print("Error: SUPABASE_URL and SUPABASE_ANON_KEY must be set")
    sys.exit(1)

# Create client
client = create_client(supabase_url, supabase_key)

# Get one order to see its structure
print("Fetching a sample order...")
result = client.table("trading_orders").select("*").limit(1).execute()

if result.data:
    print("\nColumns in trading_orders table:")
    for key in sorted(result.data[0].keys()):
        print(f"  - {key}")
else:
    print("No orders found in table")

# Try to describe the table structure
print("\nAttempting to query information_schema...")
try:
    # Direct SQL query if RPC is available
    result = client.rpc('exec_sql', {
        'query': """
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'trading_orders'
ORDER BY ordinal_position;
"""
    }).execute()

    print("\nTable schema from information_schema:")
    for row in result.data:
        print(f"  {row['column_name']}: {row['data_type']} (nullable: {row['is_nullable']})")
except Exception as e:
    print(f"Could not query information_schema: {e}")
