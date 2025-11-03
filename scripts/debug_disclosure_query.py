#!/usr/bin/env python3
"""
Debug disclosure query to see what data is being returned
"""
import os
import sys
from pathlib import Path
import json

# Add src to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir / "src"))

from politician_trading.database.database import SupabaseClient
from politician_trading.config import SupabaseConfig
from politician_trading.utils.logger import create_logger

logger = create_logger("debug_disclosure_query")

def main():
    # Connect to database
    config = SupabaseConfig.from_env()
    db = SupabaseClient(config)

    # Fetch recent disclosures with politician information
    query = db.client.table("trading_disclosures").select(
        "*, politicians(first_name, last_name, full_name, role, party, state_or_country)"
    ).order("transaction_date", desc=True).limit(5)

    response = query.execute()

    print(f"\n{'='*80}")
    print(f"Query returned {len(response.data)} records")
    print(f"{'='*80}\n")

    for i, record in enumerate(response.data):
        print(f"\n--- Record {i+1} ---")
        print(f"Transaction Date: {record.get('transaction_date')}")
        print(f"Asset Ticker: {record.get('asset_ticker')}")
        print(f"Asset Name: {record.get('asset_name')}")
        print(f"Asset Type: {record.get('asset_type')}")
        print(f"Politician Data: {record.get('politicians')}")
        print(f"Politician Bioguide ID: {record.get('politician_bioguide_id')}")
        print(f"\nAll keys in record: {list(record.keys())}")
        print(f"\nFull record:")
        print(json.dumps(record, indent=2, default=str))

if __name__ == "__main__":
    main()
