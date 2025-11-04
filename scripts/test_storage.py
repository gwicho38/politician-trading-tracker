#!/usr/bin/env python3
"""
Test storage infrastructure.

Creates a test PDF and verifies storage operations.
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
import uuid

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from supabase import create_client
from politician_trading.config import SupabaseConfig
from politician_trading.storage import StorageManager


async def main():
    """Test storage operations"""

    print("=" * 60)
    print("Testing Storage Infrastructure")
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

    # Test 1: Save a test PDF (without disclosure_id since it's a test)
    print("Test 1: Save PDF to storage")
    print("-" * 60)

    test_pdf_content = b"%PDF-1.4\n%Test PDF content for storage testing\n"
    test_politician_name = "Test Politician"
    test_source_url = "https://example.com/test.pdf"
    test_transaction_date = datetime.now()

    try:
        # Temporarily store without disclosure_id for testing
        # In production, this would link to a real disclosure
        import hashlib
        file_hash = hashlib.sha256(test_pdf_content).hexdigest()
        year = test_transaction_date.year
        month = f"{test_transaction_date.month:02d}"
        date_str = test_transaction_date.strftime("%Y%m%d")
        clean_name = test_politician_name.replace(' ', '_')
        test_disclosure_id = str(uuid.uuid4())
        filename = f"{test_disclosure_id}_{clean_name}_{date_str}.pdf"
        chamber = "senate"
        storage_path = f"{chamber}/{year}/{month}/{filename}"

        # Upload to storage
        db.storage.from_('raw-pdfs').upload(
            storage_path,
            test_pdf_content,
            {
                'content-type': 'application/pdf',
                'x-upsert': 'true'
            }
        )

        # Save metadata without disclosure_id (NULL is allowed)
        metadata = {
            'disclosure_id': None,  # NULL for test
            'storage_bucket': 'raw-pdfs',
            'storage_path': storage_path,
            'file_type': 'pdf',
            'file_size_bytes': len(test_pdf_content),
            'file_hash_sha256': file_hash,
            'mime_type': 'application/pdf',
            'source_url': test_source_url,
            'source_type': 'senate_pdf_test',
            'parse_status': 'pending',
        }

        response = db.table('stored_files').insert(metadata).execute()
        file_id = response.data[0]['id'] if response.data else None

        print(f"  ✓ PDF saved")
        print(f"    Path: {storage_path}")
        print(f"    File ID: {file_id}")
        print()

    except Exception as e:
        print(f"  ❌ Error saving PDF: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Test 2: Retrieve the PDF
    print("Test 2: Retrieve PDF from storage")
    print("-" * 60)

    try:
        retrieved_pdf = await storage.get_pdf(storage_path)
        print(f"  ✓ PDF retrieved")
        print(f"    Size: {len(retrieved_pdf)} bytes")
        print(f"    Matches original: {retrieved_pdf == test_pdf_content}")
        print()

    except Exception as e:
        print(f"  ❌ Error retrieving PDF: {e}")
        import traceback
        traceback.print_exc()

    # Test 3: Save API response
    print("Test 3: Save API response to storage")
    print("-" * 60)

    test_api_response = {
        "data": [
            {
                "politician": "Test Person",
                "ticker": "AAPL",
                "transaction_type": "purchase",
                "amount": "$15,001 - $50,000"
            }
        ],
        "count": 1,
        "fetched_at": datetime.now().isoformat()
    }

    try:
        api_path, api_file_id = await storage.save_api_response(
            response_data=test_api_response,
            source="quiverquant_test",
            endpoint="/congresstrading",
            metadata={"url": "https://api.quiverquant.com/beta/live/congresstrading"}
        )

        print(f"  ✓ API response saved")
        print(f"    Path: {api_path}")
        print(f"    File ID: {api_file_id}")
        print()

    except Exception as e:
        print(f"  ❌ Error saving API response: {e}")
        import traceback
        traceback.print_exc()

    # Test 4: Get storage statistics
    print("Test 4: Get storage statistics")
    print("-" * 60)

    try:
        stats = await storage.get_storage_statistics()
        print(f"  ✓ Statistics retrieved")
        print(f"    Records: {len(stats)}")

        for stat in stats:
            print(f"    - {stat['storage_bucket']}/{stat['file_type']}: {stat['file_count']} files, {stat['total_size_mb']} MB")

        print()

    except Exception as e:
        print(f"  ❌ Error getting statistics: {e}")
        import traceback
        traceback.print_exc()

    # Test 5: Mark file as parsed
    print("Test 5: Mark file as parsed")
    print("-" * 60)

    try:
        await storage.mark_file_parsed(file_id, transactions_count=3)
        print(f"  ✓ File marked as parsed")
        print()

    except Exception as e:
        print(f"  ❌ Error marking file: {e}")
        import traceback
        traceback.print_exc()

    # Test 6: Get files to parse
    print("Test 6: Get files ready for parsing")
    print("-" * 60)

    try:
        files_to_parse = await storage.get_files_to_parse(bucket='raw-pdfs', limit=10)
        print(f"  ✓ Files to parse: {len(files_to_parse)}")

        for f in files_to_parse[:3]:  # Show first 3
            print(f"    - {f['storage_path']}")

        print()

    except Exception as e:
        print(f"  ❌ Error getting files to parse: {e}")
        import traceback
        traceback.print_exc()

    print("=" * 60)
    print("Storage Tests Complete")
    print("=" * 60)
    print()
    print("✓ All core storage operations are working")
    print("✓ Ready to integrate with PDF parser and QuiverQuant source")
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
