#!/usr/bin/env python3
"""
Test Phase 6 with MTG Filing

Tests the complete Phase 6 integration using Marjorie Taylor Greene's
filing which we know has 55 transactions with tickers and asset types.
"""
import asyncio
import sys
sys.path.insert(0, '/Users/lefv/repos/politician-trading-tracker/src')

from politician_trading.scrapers.scrapers import CongressTradingScraper
from politician_trading.config import ScrapingConfig

async def test_mtg_filing():
    print("=" * 80)
    print("PHASE 6 TEST: MTG Filing with Enhanced Parsing")
    print("=" * 80)
    print()

    # Initialize scraper
    print("Step 1: Initialize scraper")
    config = ScrapingConfig()
    scraper = CongressTradingScraper(config)
    print("  ✓ Scraper initialized")
    print()

    # Download and parse MTG's specific PDF
    print("Step 2: Download MTG PDF (Filing ID: 20026658)")
    pdf_url = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2025/20026658.pdf"

    filing_metadata = {
        "filer_id": "20026658",
        "filing_date": "2025-01-27",
        "doc_id": "20026658",
    }

    print(f"  URL: {pdf_url}")
    print(f"  Metadata: {filing_metadata}")
    print()

    # Parse the PDF
    print("Step 3: Parse PDF with enhanced parser")
    transactions = await scraper._parse_house_pdf(
        pdf_url=pdf_url,
        filing_metadata=filing_metadata
    )

    print(f"  ✓ Extracted {len(transactions)} transactions")
    print()

    if not transactions:
        print("❌ No transactions extracted - parser may have failed")
        return False

    # Analyze results
    print("Step 4: Analyze enhanced fields")
    print("-" * 80)

    with_ticker = sum(1 for t in transactions if t.get('ticker'))
    with_asset_type = sum(1 for t in transactions if t.get('asset_type_code'))
    with_owner = sum(1 for t in transactions if t.get('asset_owner'))
    with_confidence = sum(1 for t in transactions if t.get('ticker_confidence_score'))
    with_dates = sum(1 for t in transactions if t.get('transaction_date') and t.get('notification_date'))

    print(f"  Total transactions: {len(transactions)}")
    print(f"  With ticker: {with_ticker}/{len(transactions)} ({with_ticker/len(transactions)*100:.1f}%)")
    print(f"  With asset_type_code: {with_asset_type}/{len(transactions)} ({with_asset_type/len(transactions)*100:.1f}%)")
    print(f"  With asset_owner: {with_owner}/{len(transactions)} ({with_owner/len(transactions)*100:.1f}%)")
    print(f"  With confidence score: {with_confidence}/{len(transactions)} ({with_confidence/len(transactions)*100:.1f}%)")
    print(f"  With both dates: {with_dates}/{len(transactions)} ({with_dates/len(transactions)*100:.1f}%)")
    print()

    # Show sample transactions
    print("Step 5: Sample transactions with enhanced fields")
    print("-" * 80)

    samples = [t for t in transactions if t.get('ticker')][:5]

    for i, txn in enumerate(samples, 1):
        print(f"{i}. {txn.get('asset_name', 'Unknown')[:40]}")
        print(f"   Ticker: {txn.get('ticker')} (confidence: {txn.get('ticker_confidence_score', 0):.2f})")
        print(f"   Asset Type: [{txn.get('asset_type_code')}] {txn.get('asset_type', 'Unknown')}")
        print(f"   Owner: {txn.get('asset_owner', 'SELF')}")
        if txn.get('specific_owner_text'):
            print(f"   Specific Owner: {txn.get('specific_owner_text')}")
        print(f"   Transaction: {txn.get('transaction_type')} on {txn.get('transaction_date')}")
        print(f"   Notified: {txn.get('notification_date')}")
        print(f"   Value: ${txn.get('amount_min', 0):,} - ${txn.get('amount_max', 0):,}")
        print()

    print()

    # Test TradingDisclosure creation
    print("Step 6: Create TradingDisclosure objects with enhanced fields")
    print("-" * 80)

    from models import TradingDisclosure, TransactionType

    sample_txn = samples[0] if samples else transactions[0]

    disclosure = TradingDisclosure(
        politician_id="test-politician-id",
        asset_name=sample_txn.get("asset_name", "Unknown"),
        asset_ticker=sample_txn.get("ticker"),
        transaction_type=TransactionType[sample_txn.get("transaction_type", "PURCHASE")],
        transaction_date=sample_txn.get("transaction_date"),
        amount_range_min=sample_txn.get("amount_min"),
        amount_range_max=sample_txn.get("amount_max"),
        disclosure_date=sample_txn.get("notification_date"),
        # Enhanced fields
        filer_id=sample_txn.get("filer_id"),
        filing_date=sample_txn.get("filing_date"),
        ticker_confidence_score=sample_txn.get("ticker_confidence_score"),
        asset_owner=sample_txn.get("asset_owner"),
        specific_owner_text=sample_txn.get("specific_owner_text"),
        asset_type_code=sample_txn.get("asset_type_code"),
        notification_date=sample_txn.get("notification_date"),
        filing_status=sample_txn.get("filing_status"),
        quantity=sample_txn.get("quantity"),
    )

    print(f"  Asset: {disclosure.asset_name}")
    print(f"  Ticker: {disclosure.asset_ticker}")
    print()
    print("  Enhanced Fields:")
    print(f"    filer_id: {disclosure.filer_id}")
    print(f"    filing_date: {disclosure.filing_date}")
    print(f"    ticker_confidence_score: {disclosure.ticker_confidence_score}")
    print(f"    asset_owner: {disclosure.asset_owner}")
    print(f"    specific_owner_text: {disclosure.specific_owner_text}")
    print(f"    asset_type_code: {disclosure.asset_type_code}")
    print(f"    notification_date: {disclosure.notification_date}")
    print(f"    filing_status: {disclosure.filing_status}")
    print(f"    quantity: {disclosure.quantity}")
    print()

    # Success criteria
    print("Step 7: Verify success criteria")
    print("-" * 80)

    success = True

    # Should have extracted transactions
    if len(transactions) < 50:
        print(f"  ✗ Expected ~55 transactions, got {len(transactions)}")
        success = False
    else:
        print(f"  ✓ Extracted {len(transactions)} transactions")

    # Should have tickers
    if with_ticker < 30:
        print(f"  ✗ Expected ~35+ tickers, got {with_ticker}")
        success = False
    else:
        print(f"  ✓ Extracted {with_ticker} tickers")

    # Should have asset types
    if with_asset_type < 45:
        print(f"  ✗ Expected ~47+ asset types, got {with_asset_type}")
        success = False
    else:
        print(f"  ✓ Extracted {with_asset_type} asset types")

    # TradingDisclosure should have enhanced fields
    if not disclosure.filer_id or not disclosure.asset_type_code:
        print(f"  ✗ TradingDisclosure missing enhanced fields")
        success = False
    else:
        print(f"  ✓ TradingDisclosure has enhanced fields")

    print()

    if success:
        print("=" * 80)
        print("✅ ALL TESTS PASSED - PHASE 6 INTEGRATION WORKING!")
        print("=" * 80)
        print()
        print("The enhanced parser successfully:")
        print("  • Extracted transactions from PDF")
        print("  • Resolved tickers with confidence scores")
        print("  • Classified asset types using House codes")
        print("  • Identified asset owners")
        print("  • Parsed dates and value ranges")
        print("  • Populated TradingDisclosure objects with enhanced fields")
        print()
        print("Next steps:")
        print("  1. The data is ready to be stored in the database")
        print("  2. Enable parse_pdfs=True in production workflow")
        print("  3. Monitor enhanced field population rates")
        return True
    else:
        print("=" * 80)
        print("❌ SOME TESTS FAILED")
        print("=" * 80)
        return False

if __name__ == "__main__":
    result = asyncio.run(test_mtg_filing())
    sys.exit(0 if result else 1)
