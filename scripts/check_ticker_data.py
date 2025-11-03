#!/usr/bin/env python3
"""
Check ticker data quality in the database
"""
import os
import sys
from pathlib import Path

# Add src to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir / "src"))

from politician_trading.database.database import SupabaseClient
from politician_trading.config import SupabaseConfig
from politician_trading.utils.logger import create_logger

logger = create_logger("check_ticker_data")

def main():
    # Connect to database
    config = SupabaseConfig.from_env()
    db = SupabaseClient(config)

    # Get disclosures with tickers
    response = db.client.table("trading_disclosures")\
        .select("asset_ticker, asset_name")\
        .not_.is_("asset_ticker", "null")\
        .neq("asset_ticker", "")\
        .limit(100)\
        .execute()

    print(f"\n{'='*80}")
    print(f"Found {len(response.data)} disclosures with tickers")
    print(f"{'='*80}\n")

    # Analyze ticker patterns
    malformed = []
    valid = []

    for row in response.data:
        ticker = row.get("asset_ticker", "")
        asset_name = row.get("asset_name", "")

        # Check if ticker looks malformed (contains spaces, too long, etc.)
        if len(ticker) > 6 or " " in ticker:
            malformed.append((ticker, asset_name))
        else:
            valid.append((ticker, asset_name))

    print(f"\nValid tickers: {len(valid)}")
    print(f"Malformed tickers: {len(malformed)}")

    if malformed:
        print(f"\n{'='*80}")
        print("MALFORMED TICKERS (first 10):")
        print(f"{'='*80}\n")
        for ticker, asset_name in malformed[:10]:
            print(f"Ticker: '{ticker}'")
            print(f"Asset:  '{asset_name}'")
            print()

    if valid:
        print(f"\n{'='*80}")
        print("VALID TICKERS (first 10):")
        print(f"{'='*80}\n")
        for ticker, asset_name in valid[:10]:
            print(f"Ticker: '{ticker}'")
            print(f"Asset:  '{asset_name}'")
            print()

if __name__ == "__main__":
    main()
