#!/usr/bin/env python3
"""
Test Phase 6: Database Integration

This script tests the complete flow:
1. Scrape House disclosures with enhanced parsing
2. Create TradingDisclosure objects with enhanced fields
3. Store to database via seed_database.py functions
4. Verify enhanced fields are persisted
"""
import asyncio
import sys
sys.path.insert(0, '/Users/lefv/repos/politician-trading-tracker/src')

from politician_trading.scrapers.scrapers import CongressTradingScraper
from politician_trading.config import ScrapingConfig
from politician_trading.scrapers.seed_database import (
    get_supabase_client,
    upsert_politicians,
    upsert_trading_disclosures
)
from models import Politician

async def test_phase6():
    print("=" * 80)
    print("PHASE 6 INTEGRATION TEST")
    print("=" * 80)
    print()

    # Step 1: Initialize scraper
    print("Step 1: Initialize scraper...")
    config = ScrapingConfig()
    scraper = CongressTradingScraper(config)

    # Step 2: Scrape a small sample with enhanced parsing
    print("Step 2: Scraping House disclosures (2025, parse_pdfs=True, limit=5)...")
    disclosures = await scraper.scrape_house_disclosures(
        year=2025,
        parse_pdfs=True,
        max_pdfs_per_run=5  # Only parse 5 PDFs for testing
    )

    print(f"  ✓ Scraped {len(disclosures)} disclosures")
    print()

    # Step 3: Show sample disclosure with enhanced fields
    if disclosures:
        sample = disclosures[0]
        print("Step 3: Sample disclosure with enhanced fields:")
        print(f"  Asset: {sample.asset_name}")
        print(f"  Ticker: {sample.asset_ticker}")
        print(f"  Transaction Type: {sample.transaction_type}")
        print(f"  Transaction Date: {sample.transaction_date}")
        print()
        print("  Enhanced Fields:")
        print(f"    filer_id: {sample.filer_id}")
        print(f"    filing_date: {sample.filing_date}")
        print(f"    ticker_confidence_score: {sample.ticker_confidence_score}")
        print(f"    asset_owner: {sample.asset_owner}")
        print(f"    specific_owner_text: {sample.specific_owner_text}")
        print(f"    asset_type_code: {sample.asset_type_code}")
        print(f"    notification_date: {sample.notification_date}")
        print(f"    filing_status: {sample.filing_status}")
        print(f"    quantity: {sample.quantity}")
        print()

    # Step 4: Get Supabase client
    print("Step 4: Connect to Supabase...")
    try:
        client = get_supabase_client()
        print("  ✓ Connected to Supabase")
    except Exception as e:
        print(f"  ✗ Error connecting to Supabase: {e}")
        print()
        print("Note: Database migration must be applied manually via Supabase dashboard.")
        print("SQL file: /Users/lefv/repos/politician-trading-tracker/migrations/001_enhanced_disclosure_fields.sql")
        return

    print()

    # Step 5: Create a test politician (or use existing)
    print("Step 5: Create test politician...")
    test_politician = Politician(
        first_name="Marjorie",
        last_name="Greene",
        full_name="Marjorie Taylor Greene",
        role="House",
        party="Republican",
        state_or_country="GA",
        district="14",
        bioguide_id="G000596"
    )

    politician_map = upsert_politicians(client, [test_politician])
    print(f"  ✓ Politician upserted: {politician_map}")
    print()

    # Step 6: Link disclosures to politician and upsert
    print("Step 6: Upserting disclosures with enhanced fields...")

    # Set politician_bioguide_id for lookup
    for disclosure in disclosures:
        disclosure.politician_bioguide_id = "G000596"

    stats = upsert_trading_disclosures(client, disclosures, politician_map)

    print(f"  ✓ Upsert complete:")
    print(f"    Records found: {stats['records_found']}")
    print(f"    Records new: {stats['records_new']}")
    print(f"    Records updated: {stats['records_updated']}")
    print(f"    Records failed: {stats['records_failed']}")
    print()

    # Step 7: Verify enhanced fields in database
    print("Step 7: Verifying enhanced fields in database...")

    pol_id = list(politician_map.values())[0]
    result = client.table("trading_disclosures").select("*").eq("politician_id", str(pol_id)).limit(1).execute()

    if result.data:
        record = result.data[0]
        print("  ✓ Sample database record:")
        print(f"    asset_name: {record.get('asset_name')}")
        print(f"    asset_ticker: {record.get('asset_ticker')}")
        print()
        print("  Enhanced fields in database:")
        print(f"    filer_id: {record.get('filer_id')}")
        print(f"    filing_date: {record.get('filing_date')}")
        print(f"    ticker_confidence_score: {record.get('ticker_confidence_score')}")
        print(f"    asset_owner: {record.get('asset_owner')}")
        print(f"    specific_owner_text: {record.get('specific_owner_text')}")
        print(f"    asset_type_code: {record.get('asset_type_code')}")
        print(f"    notification_date: {record.get('notification_date')}")
        print(f"    filing_status: {record.get('filing_status')}")
        print(f"    quantity: {record.get('quantity')}")
        print()
    else:
        print("  ✗ No records found in database")
        print()

    print("=" * 80)
    print("PHASE 6 INTEGRATION TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_phase6())
