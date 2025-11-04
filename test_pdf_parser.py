#!/usr/bin/env python3
"""
Test PDF parser with a sample Senate disclosure.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from politician_trading.transformers.pdf_parser import SenatePDFParser


async def test_pdf_parser():
    """Test parsing a Senate PTR PDF"""

    print("=" * 60)
    print("Testing Senate PDF Parser")
    print("=" * 60)
    print()

    # Use one of the PDF URLs from the database
    test_cases = [
        {
            'politician': 'Benjamin L Cardin',
            'url': 'https://efdsearch.senate.gov/search/view/paper/CDFDAF62-18EA-4298-B0C5-62085A6EC3CD/',
            'date': '2012-07-25'
        },
        {
            'politician': 'Thomas R Carper',
            'url': 'https://efdsearch.senate.gov/search/view/paper/CFDE3B80-E8BD-4F2D-9D64-E892C5EFB32A/',
            'date': '2012-08-02'
        }
    ]

    async with SenatePDFParser() as parser:
        for test_case in test_cases:
            print(f"\nTesting: {test_case['politician']} - {test_case['date']}")
            print("-" * 60)

            transactions = await parser.parse_pdf_url(
                test_case['url'],
                test_case['politician']
            )

            print(f"\n✅ Extracted {len(transactions)} transactions")

            if transactions:
                print("\nSample transaction:")
                print("-" * 60)
                import json
                print(json.dumps(transactions[0], indent=2, default=str))

            print("\n" + "=" * 60)

            # Just test one for now
            break

    print("\nTest complete!")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(test_pdf_parser())
    sys.exit(exit_code)
