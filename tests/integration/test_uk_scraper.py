#!/usr/bin/env python3
"""
Test script to verify enhanced UK Parliament scraper extracts real MP names
"""

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Check for bs4 dependency
try:
    import bs4

    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

if HAS_BS4:
    from mcli.workflow.politician_trading.config import WorkflowConfig
    from mcli.workflow.politician_trading.scrapers_uk import UKParliamentScraper


@pytest.mark.skipif(not HAS_BS4, reason="bs4 module not installed")
async def test_uk_name_extraction():
    """Test if the enhanced UK Parliament scraper extracts real MP names"""
    print("🧪 Testing Enhanced UK Parliament Scraper")
    print("=" * 50)

    config = WorkflowConfig.default().scraping

    try:
        async with UKParliamentScraper(config) as scraper:
            print("\n🏛️ Testing UK Parliament disclosure extraction...")
            disclosures = await scraper.fetch_members_interests()

            print(f"📊 Found {len(disclosures)} UK Parliament disclosures")

            # Show first few disclosures with names
            real_names = 0
            for i, disclosure in enumerate(disclosures[:5]):
                politician_name = disclosure.raw_data.get("politician_name", "No name")
                if politician_name and len(politician_name) > 3:
                    real_names += 1

                print(f"  {i+1}. {politician_name}")
                print(f"     Asset: {disclosure.asset_name}")
                print(f"     Category: {disclosure.raw_data.get('category_name', 'Unknown')}")
                print(f"     Amount: ${disclosure.amount_range_min}-{disclosure.amount_range_max}")
                print()

            # Summary
            total_with_names = sum(
                1
                for d in disclosures
                if d.raw_data.get("politician_name")
                and len(d.raw_data.get("politician_name", "")) > 3
            )

            print(f"📈 RESULTS:")
            print(f"Total disclosures found: {len(disclosures)}")
            print(f"Disclosures with real names: {total_with_names}")
            print(
                f"Success rate: {total_with_names/len(disclosures)*100:.1f}%"
                if len(disclosures) > 0
                else "No data"
            )

            if total_with_names > 0:
                print("✅ SUCCESS: Enhanced UK scraper is extracting real MP names!")
                return True
            else:
                print("⚠️  No MP names extracted - may need API endpoint adjustment")
                return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_uk_name_extraction())
    sys.exit(0 if success else 1)
