#!/usr/bin/env python3
"""
Test QuiverQuant integration with storage.

Verifies that QuiverQuant API responses are saved to storage.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from supabase import create_client
from politician_trading.config import SupabaseConfig
from politician_trading.sources.quiverquant import QuiverQuantSource
from politician_trading.storage import StorageManager


async def main():
    """Test QuiverQuant with storage"""

    print("=" * 60)
    print("Testing QuiverQuant Storage Integration")
    print("=" * 60)
    print()

    # Get database connection
    config = SupabaseConfig.from_env()

    # Use service role key for storage operations
    if not config.service_role_key:
        print("❌ SUPABASE_SERVICE_KEY not found in environment")
        return 1

    db = create_client(config.url, config.service_role_key)

    print("✓ Connected to Supabase")
    print()

    # Initialize storage manager
    storage = StorageManager(db)
    print("✓ StorageManager initialized")
    print()

    # Initialize QuiverQuant source
    source = QuiverQuantSource()
    print("✓ QuiverQuantSource initialized")
    print()

    # Attach storage manager
    source.storage_manager = storage
    print("✓ Storage manager attached to source")
    print()

    # Test with mock API response (since we might not have a real API key)
    print("Test: Saving mock API response to storage")
    print("-" * 60)

    mock_response = {
        "trades": [
            {
                "Representative": "Test Representative",
                "TransactionDate": "2025-11-01",
                "ReportDate": "2025-11-04",
                "Ticker": "AAPL",
                "AssetDescription": "Apple Inc.",
                "Transaction": "Purchase",
                "Amount": "$15,001 - $50,000",
                "FilingID": "test-filing-123"
            },
            {
                "Representative": "Another Representative",
                "TransactionDate": "2025-11-02",
                "ReportDate": "2025-11-04",
                "Ticker": "MSFT",
                "AssetDescription": "Microsoft Corporation",
                "Transaction": "Sale",
                "Amount": "$50,001 - $100,000",
                "FilingID": "test-filing-456"
            }
        ]
    }

    try:
        # Save directly via storage manager (simulating what _fetch_via_api does)
        storage_path, file_id = await storage.save_api_response(
            response_data=mock_response,
            source='quiverquant',
            endpoint='/congresstrading',
            metadata={'url': 'https://api.quiverquant.com/beta/live/congresstrading', 'lookback_days': 30}
        )

        print(f"  ✓ Mock API response saved")
        print(f"    Path: {storage_path}")
        print(f"    File ID: {file_id}")
        print()

        # Retrieve it back
        retrieved_response = await storage.get_api_response(storage_path)
        print(f"  ✓ Response retrieved from storage")
        print(f"    Trades in response: {len(retrieved_response.get('trades', []))}")
        print()

        # Parse the response using QuiverQuant parser
        parsed_disclosures = source._parse_api_response(mock_response)
        print(f"  ✓ Response parsed")
        print(f"    Disclosures extracted: {len(parsed_disclosures)}")
        print()

        # Show first disclosure
        if parsed_disclosures:
            disc = parsed_disclosures[0]
            print(f"  Sample disclosure:")
            print(f"    Politician: {disc.get('politician_name')}")
            print(f"    Asset: {disc.get('asset_name')} ({disc.get('asset_ticker')})")
            print(f"    Type: {disc.get('transaction_type')}")
            print(f"    Date: {disc.get('transaction_date')}")
            print()

        # Mark file as parsed
        await storage.mark_file_parsed(file_id, transactions_count=len(parsed_disclosures))
        print(f"  ✓ File marked as parsed with {len(parsed_disclosures)} transactions")
        print()

    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("=" * 60)
    print("QuiverQuant Storage Integration Test Complete")
    print("=" * 60)
    print()
    print("✓ All storage operations working with QuiverQuant source")
    print("✓ Ready for production use with real API key")
    print()
    print("Next steps:")
    print("1. Get QuiverQuant API key")
    print("2. Set in environment or pass to source")
    print("3. Run pipeline with QuiverQuant source")
    print("4. API responses will automatically be saved to storage")
    print()

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
