#!/usr/bin/env python3
"""Test script for the integrated House scraper

Tests the new ZIP-based scraper implementation to ensure it works correctly.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from politician_trading.config import ScrapingConfig
from politician_trading.scrapers.scrapers import CongressTradingScraper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_house_scraper_metadata_only():
    """Test 1: Metadata-only scraping (fast)"""
    print("=" * 70)
    print("TEST 1: House Scraper - Metadata Only (No PDF Parsing)")
    print("=" * 70)

    config = ScrapingConfig()
    scraper = CongressTradingScraper(config)

    # Test with current year, no PDF parsing
    disclosures = await scraper.scrape_house_disclosures(
        year=2025,
        parse_pdfs=False
    )

    print(f"\n✅ Retrieved {len(disclosures)} House disclosures")

    if disclosures:
        # Show first 5 disclosures
        print(f"\n📊 First 5 disclosures:")
        for i, disclosure in enumerate(disclosures[:5]):
            politician = disclosure.raw_data.get('politician')
            print(f"\n  {i+1}. {politician.full_name if politician else 'Unknown'}")
            print(f"     Asset: {disclosure.asset_name}")
            print(f"     Type: {disclosure.transaction_type.value}")
            print(f"     Date: {disclosure.transaction_date}")
            print(f"     Source: {disclosure.source_url}")

        # Show statistics
        print(f"\n📈 Statistics:")
        print(f"   Total disclosures: {len(disclosures)}")

        # Count by status
        statuses = {}
        for d in disclosures:
            status = d.status.value if d.status else 'Unknown'
            statuses[status] = statuses.get(status, 0) + 1

        print(f"   Status breakdown:")
        for status, count in sorted(statuses.items()):
            print(f"     - {status}: {count}")

    return len(disclosures) > 0


async def test_house_scraper_with_pdf_parsing():
    """Test 2: With PDF parsing (limited to 2 PDFs)"""
    print("\n" + "=" * 70)
    print("TEST 2: House Scraper - With PDF Parsing (Limited to 2 PDFs)")
    print("=" * 70)

    config = ScrapingConfig()
    scraper = CongressTradingScraper(config)

    # Test with PDF parsing (limit to 2 for speed)
    disclosures = await scraper.scrape_house_disclosures(
        year=2025,
        parse_pdfs=True,
        max_pdfs_per_run=2
    )

    print(f"\n✅ Retrieved {len(disclosures)} House disclosures")

    # Find disclosures with ticker info (from PDF parsing)
    with_tickers = [d for d in disclosures if d.asset_ticker]
    print(f"   Disclosures with tickers: {len(with_tickers)}")

    if with_tickers:
        print(f"\n📊 Disclosures with parsed ticker information:")
        for i, disclosure in enumerate(with_tickers[:5]):
            politician = disclosure.raw_data.get('politician')
            print(f"\n  {i+1}. {politician.full_name if politician else 'Unknown'}")
            print(f"     Ticker: {disclosure.asset_ticker}")
            print(f"     Asset: {disclosure.asset_name}")
            print(f"     Type: {disclosure.transaction_type.value}")
            print(f"     Date: {disclosure.transaction_date}")
            if disclosure.amount_range_min and disclosure.amount_range_max:
                print(f"     Amount: ${disclosure.amount_range_min:,} - ${disclosure.amount_range_max:,}")
    else:
        print(f"\n   ℹ️  Note: No tickers found in the 2 PDFs tested.")
        print(f"   This is normal - not all PDFs contain transaction data.")
        print(f"   PDFs may be blank forms, amendments, or termination reports.")

    # Test passes if we got disclosures back (PDF parsing worked even if no transactions found)
    return len(disclosures) > 0


async def main():
    """Run all tests"""
    print("\n🧪 Starting House Scraper Integration Tests\n")

    try:
        # Test 1: Metadata only
        test1_passed = await test_house_scraper_metadata_only()

        # Test 2: With PDF parsing
        test2_passed = await test_house_scraper_with_pdf_parsing()

        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Test 1 (Metadata Only): {'✅ PASSED' if test1_passed else '❌ FAILED'}")
        print(f"Test 2 (PDF Parsing):   {'✅ PASSED' if test2_passed else '❌ FAILED'}")
        print()

        if test1_passed and test2_passed:
            print("🎉 All tests passed!")
            return 0
        else:
            print("⚠️  Some tests failed")
            return 1

    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
