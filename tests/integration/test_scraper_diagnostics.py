#!/usr/bin/env python3
"""
Diagnostic test for scraper issues
Tests scrapers with detailed logging to identify why they're returning 0 results
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

import pytest

# Set up logging to see DEBUG messages
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

try:
    import bs4

    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

if HAS_BS4:
    from politician_trading.config import WorkflowConfig
    from politician_trading.scrapers import (
        CongressTradingScraper,
        QuiverQuantScraper,
    )


@pytest.mark.skipif(not HAS_BS4, reason="bs4 module not installed")
async def test_house_scraper_diagnostics():
    """Diagnostic test for House scraper with detailed logging"""
    print("\n" + "=" * 70)
    print("🏛️ HOUSE SCRAPER DIAGNOSTIC TEST")
    print("=" * 70)

    config = WorkflowConfig.default().scraping
    scraper = CongressTradingScraper(config)

    async with scraper:
        try:
            disclosures = await scraper.scrape_house_disclosures()

            print(f"\n📊 Results: Found {len(disclosures)} disclosures")

            if len(disclosures) == 0:
                print("⚠️  WARNING: No disclosures found")
                print(
                    "   Check the DEBUG logs above for HTML preview and form field details"
                )
            else:
                print("✅ SUCCESS: House scraper returned data")
                for i, d in enumerate(disclosures[:3]):
                    print(f"\n  Disclosure {i+1}:")
                    print(f"    Politician: {d.raw_data.get('politician_name', 'N/A')}")
                    print(f"    Asset: {d.asset_name}")
                    print(f"    Source: {d.source_url}")

        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback

            traceback.print_exc()


@pytest.mark.skipif(not HAS_BS4, reason="bs4 module not installed")
async def test_senate_scraper_diagnostics():
    """Diagnostic test for Senate scraper with detailed logging"""
    print("\n" + "=" * 70)
    print("🏛️ SENATE SCRAPER DIAGNOSTIC TEST")
    print("=" * 70)

    config = WorkflowConfig.default().scraping
    scraper = CongressTradingScraper(config)

    async with scraper:
        try:
            disclosures = await scraper.scrape_senate_disclosures()

            print(f"\n📊 Results: Found {len(disclosures)} disclosures")

            if len(disclosures) == 0:
                print("⚠️  WARNING: No disclosures found")
                print(
                    "   Check the DEBUG logs above for HTML preview and search URL details"
                )
            else:
                print("✅ SUCCESS: Senate scraper returned data")
                for i, d in enumerate(disclosures[:3]):
                    print(f"\n  Disclosure {i+1}:")
                    print(f"    Politician: {d.raw_data.get('politician_name', 'N/A')}")
                    print(f"    Asset: {d.asset_name}")
                    print(f"    Filing Date: {d.raw_data.get('filing_date', 'N/A')}")
                    print(f"    Source: {d.source_url}")

        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback

            traceback.print_exc()


@pytest.mark.skipif(not HAS_BS4, reason="bs4 module not installed")
async def test_quiverquant_scraper_diagnostics():
    """Diagnostic test for QuiverQuant scraper with detailed logging"""
    print("\n" + "=" * 70)
    print("📈 QUIVERQUANT SCRAPER DIAGNOSTIC TEST")
    print("=" * 70)

    config = WorkflowConfig.default().scraping
    scraper = QuiverQuantScraper(config)

    async with scraper:
        try:
            trades = await scraper.scrape_congress_trades()

            print(f"\n📊 Results: Found {len(trades)} trades")

            if len(trades) == 0:
                print("⚠️  WARNING: No trades found")
                print(
                    "   Check the DEBUG logs above for HTML length and JavaScript detection"
                )
            else:
                print("✅ SUCCESS: QuiverQuant scraper returned data")
                for i, trade in enumerate(trades[:3]):
                    print(f"\n  Trade {i+1}:")
                    print(f"    Politician: {trade.get('politician_name', 'N/A')}")
                    print(f"    Ticker: {trade.get('ticker', 'N/A')}")
                    print(f"    Asset: {trade.get('asset_name', 'N/A')}")
                    print(f"    Type: {trade.get('transaction_type', 'N/A')}")
                    print(f"    Date: {trade.get('transaction_date', 'N/A')}")

        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback

            traceback.print_exc()


@pytest.mark.skipif(not HAS_BS4, reason="bs4 module not installed")
async def test_all_scrapers():
    """Run all scraper diagnostics"""
    print("\n" + "=" * 70)
    print("🔍 RUNNING ALL SCRAPER DIAGNOSTICS")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")

    await test_house_scraper_diagnostics()
    await test_senate_scraper_diagnostics()
    await test_quiverquant_scraper_diagnostics()

    print("\n" + "=" * 70)
    print("✅ DIAGNOSTIC TESTS COMPLETE")
    print("=" * 70)
    print(
        "\nReview the DEBUG logs above to identify why scrapers are returning 0 results"
    )
    print("Common issues:")
    print("  1. Website structure changed (check HTML preview)")
    print("  2. Anti-scraping measures (check response headers)")
    print("  3. JavaScript-rendered content (check for JS requirements)")
    print("  4. Form field names changed (check input field names)")


if __name__ == "__main__":
    asyncio.run(test_all_scrapers())
