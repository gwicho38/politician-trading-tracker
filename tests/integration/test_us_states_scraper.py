#!/usr/bin/env python3
"""
Test script to verify enhanced US states scrapers extract real politician names
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
    from mcli.workflow.politician_trading.scrapers_us_states import USStatesScraper


@pytest.mark.skipif(not HAS_BS4, reason="bs4 module not installed")
async def test_us_states_name_extraction():
    """Test if the enhanced US states scrapers extract real politician names"""
    print("🧪 Testing Enhanced US States Scrapers")
    print("=" * 50)

    config = WorkflowConfig.default().scraping

    try:
        scraper = USStatesScraper(config)
        async with scraper:
            print("\n🏛️ Testing US states disclosure extraction...")
            disclosures = await scraper.scrape_all_us_states()

            print(f"📊 Found {len(disclosures)} US states disclosures")

            # Show first few disclosures with names
            real_names = 0
            for i, disclosure in enumerate(disclosures[:8]):
                politician_name = disclosure.raw_data.get("politician_name", "No name")
                state = disclosure.raw_data.get("state", "Unknown")
                if politician_name and len(politician_name) > 3 and politician_name != "No name":
                    real_names += 1

                print(f"  {i+1}. {politician_name} ({state})")
                print(f"     Asset: {disclosure.asset_name}")
                print(f"     Source: {disclosure.raw_data.get('source', 'Unknown')}")
                print(f"     Amount: ${disclosure.amount_range_min}-{disclosure.amount_range_max}")
                print()

            # Summary by state
            state_counts = {}
            for disclosure in disclosures:
                state = disclosure.raw_data.get("state", "Unknown")
                if state not in state_counts:
                    state_counts[state] = 0
                state_counts[state] += 1

            print(f"📈 RESULTS:")
            print(f"Total disclosures found: {len(disclosures)}")
            print(f"Disclosures with real names: {real_names}")
            print(
                f"Success rate: {real_names/len(disclosures)*100:.1f}%"
                if len(disclosures) > 0
                else "No data"
            )

            print(f"\n📋 By State:")
            for state, count in state_counts.items():
                print(f"  {state}: {count} disclosures")

            if real_names > 0:
                print("\n✅ SUCCESS: Enhanced US states scrapers are extracting politician names!")
                return True
            else:
                print("\n⚠️  No politician names extracted - may need further enhancement")
                return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_us_states_name_extraction())
    sys.exit(0 if success else 1)
