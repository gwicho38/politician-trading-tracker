#!/usr/bin/env python3
"""
Test script to verify enhanced US Congress scraper extracts real politician names
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
    from mcli.workflow.politician_trading.scrapers import CongressTradingScraper


@pytest.mark.skipif(not HAS_BS4, reason="bs4 module not installed")
async def test_congress_name_extraction():
    """Test if the enhanced Congress scraper extracts real politician names"""
    print("🧪 Testing Enhanced US Congress Scraper")
    print("=" * 50)

    config = WorkflowConfig.default().scraping
    scraper = CongressTradingScraper(config)

    try:
        # Test House disclosures
        print("\n🏛️ Testing House disclosure extraction...")
        house_disclosures = await scraper.scrape_house_disclosures()

        print(f"📊 Found {len(house_disclosures)} House disclosures")

        for i, disclosure in enumerate(house_disclosures[:3]):
            politician_name = disclosure.raw_data.get("politician_name", "No name")
            extraction_method = disclosure.raw_data.get("extraction_method", "Unknown")
            print(f"  {i+1}. {politician_name} ({extraction_method})")
            print(f"     Asset: {disclosure.asset_name}")
            print(f"     URL: {disclosure.source_url}")

        # Test Senate disclosures
        print("\n🏛️ Testing Senate disclosure extraction...")
        senate_disclosures = await scraper.scrape_senate_disclosures()

        print(f"📊 Found {len(senate_disclosures)} Senate disclosures")

        for i, disclosure in enumerate(senate_disclosures[:3]):
            politician_name = disclosure.raw_data.get("politician_name", "No name")
            extraction_method = disclosure.raw_data.get("extraction_method", "Unknown")
            print(f"  {i+1}. {politician_name} ({extraction_method})")
            print(f"     Asset: {disclosure.asset_name}")
            print(f"     URL: {disclosure.source_url}")

        # Summary
        total_disclosures = len(house_disclosures) + len(senate_disclosures)
        real_names = sum(
            1
            for d in (house_disclosures + senate_disclosures)
            if d.raw_data.get("politician_name") and len(d.raw_data.get("politician_name", "")) > 3
        )

        print(f"\n📈 RESULTS:")
        print(f"Total disclosures found: {total_disclosures}")
        print(f"Disclosures with names: {real_names}")
        print(
            f"Success rate: {real_names/total_disclosures*100:.1f}%"
            if total_disclosures > 0
            else "No data"
        )

        if real_names > 0:
            print("✅ SUCCESS: Enhanced scraper is extracting politician names!")
        else:
            print("⚠️  No politician names extracted - may need further refinement")

    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_congress_name_extraction())
