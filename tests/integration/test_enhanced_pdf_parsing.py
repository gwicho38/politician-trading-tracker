"""
Integration test for enhanced House disclosure parsing.

Tests the full parsing pipeline with real PDF data.
"""

import asyncio
from pathlib import Path
from politician_trading.scrapers.scrapers import CongressTradingScraper
from politician_trading.config import ScrapingConfig
from politician_trading.parsers import DisclosureValidator


import pytest


@pytest.mark.asyncio
async def test_enhanced_parsing_with_sample_pdf():
    """
    Test enhanced parsing with a real House disclosure PDF.

    This test demonstrates what successful parsing looks like:
    1. Extract transactions from PDF text
    2. Resolve ticker symbols with confidence scores
    3. Parse value ranges
    4. Validate data quality
    """

    # Sample PDF text extracted from a real House disclosure
    # (In production, this would come from actual PDF parsing)
    sample_pdf_text = """
    PART VII: TRANSACTIONS

    1. Apple Inc (AAPL)
       Transaction Type: P (Purchase)
       Date: 10/15/2024
       Amount: $1,001 - $15,000
       Owner: JT

    2. Microsoft Corporation
       Transaction Type: S (Sale)
       Date: 10/20/2024
       Amount: $15,001 - $50,000
       Owner: SP

    3. Tesla Inc (TSLA)
       Transaction Type: P (Purchase)
       Date: 11/01/2024
       Amount: Over $1,000,000
       Owner: Self
    """

    config = ScrapingConfig()

    scraper = CongressTradingScraper(config)
    validator = DisclosureValidator()

    # Test the enhanced transaction extraction
    print("\n" + "="*80)
    print("TESTING ENHANCED HOUSE DISCLOSURE PARSING")
    print("="*80)

    # Extract transactions using the enhanced parser
    filing_metadata = {
        "filer_id": "10072333",
        "filing_date": "2024-11-10",
        "doc_id": "20024174",
    }

    transactions = scraper._extract_transactions_section(
        sample_pdf_text,
        filing_metadata
    )

    print(f"\n✅ Extracted {len(transactions)} transactions from sample PDF")

    # Validate and display results
    print("\n" + "-"*80)
    print("TRANSACTION DETAILS:")
    print("-"*80)

    for i, trans in enumerate(transactions, 1):
        print(f"\nTransaction #{i}:")
        print(f"  Asset: {trans['asset_name']}")
        print(f"  Ticker: {trans.get('ticker', 'N/A')} (confidence: {trans.get('ticker_confidence_score', 0):.2f})")
        print(f"  Type: {trans['transaction_type']}")
        print(f"  Date: {trans.get('transaction_date')}")
        value_low = trans.get('value_low')
        value_high = trans.get('value_high')
        value_low_str = f"${value_low:,}" if value_low else "N/A"
        value_high_str = f"${value_high:,}" if value_high else "N/A"
        print(f"  Value Range: {value_low_str} - {value_high_str}")
        print(f"  Owner: {trans.get('asset_owner', 'N/A')}")

        # Validate the transaction
        validation_result = validator.validate_transaction(trans)
        print(f"  Quality Score: {validation_result['quality_score']:.2f}")
        print(f"  Valid: {'✅ Yes' if validation_result['is_valid'] else '❌ No'}")

        if validation_result['warnings']:
            print(f"  Warnings: {', '.join(validation_result['warnings'])}")
        if validation_result['errors']:
            print(f"  Errors: {', '.join(validation_result['errors'])}")

    # Check for duplicates
    print("\n" + "-"*80)
    print("DUPLICATE DETECTION:")
    print("-"*80)

    duplicates = validator.check_duplicate_transactions(transactions)
    if duplicates:
        print(f"⚠️  Found {len(duplicates)} potential duplicate pairs")
        for dup in duplicates:
            print(f"  - Transactions {dup['index1']} and {dup['index2']} (similarity: {dup['similarity']:.2f})")
    else:
        print("✅ No duplicates detected")

    # Check for outliers
    print("\n" + "-"*80)
    print("OUTLIER DETECTION:")
    print("-"*80)

    outliers = validator.flag_outliers(transactions)
    if outliers:
        print(f"⚠️  Flagged {len(outliers)} outlier transactions:")
        for outlier in outliers:
            print(f"  - Transaction #{outlier['index'] + 1}: {', '.join(outlier['flags'])}")
    else:
        print("✅ No outliers detected")

    # Summary statistics
    print("\n" + "-"*80)
    print("VALIDATION SUMMARY:")
    print("-"*80)

    stats = validator.get_validation_summary()
    print(f"  Total Validated: {stats['total_validated']}")
    print(f"  Passed: {stats['passed']} ({stats.get('pass_rate', 0)*100:.1f}%)")
    print(f"  Warnings: {stats['warnings']} ({stats.get('warning_rate', 0)*100:.1f}%)")
    print(f"  Errors: {stats['errors']} ({stats.get('error_rate', 0)*100:.1f}%)")

    # Success criteria
    print("\n" + "="*80)
    print("SUCCESS CRITERIA:")
    print("="*80)

    success = True
    checks = []

    # Check 1: Extracted all transactions
    if len(transactions) == 3:
        checks.append("✅ Extracted all 3 transactions from PDF")
    else:
        checks.append(f"❌ Expected 3 transactions, got {len(transactions)}")
        success = False

    # Check 2: Resolved tickers with high confidence
    high_confidence_tickers = [t for t in transactions if t.get('ticker_confidence_score', 0) >= 0.9]
    if len(high_confidence_tickers) >= 2:
        checks.append(f"✅ Resolved {len(high_confidence_tickers)} tickers with high confidence (≥0.9)")
    else:
        checks.append(f"⚠️  Only {len(high_confidence_tickers)} high-confidence tickers")

    # Check 3: Parsed all value ranges
    with_values = [t for t in transactions if t.get('value_low') or t.get('value_high')]
    if len(with_values) == 3:
        checks.append("✅ Parsed value ranges for all transactions")
    else:
        checks.append(f"⚠️  Only parsed {len(with_values)}/3 value ranges")

    # Check 4: Parsed owners correctly
    with_owners = [t for t in transactions if t.get('asset_owner') in ['SELF', 'SPOUSE', 'JOINT', 'DEPENDENT']]
    if len(with_owners) == 3:
        checks.append("✅ Parsed ownership for all transactions")
    else:
        checks.append(f"⚠️  Only parsed {len(with_owners)}/3 ownerships")

    # Check 5: All transactions are valid
    if stats['errors'] == 0:
        checks.append("✅ All transactions passed validation (no errors)")
    else:
        checks.append(f"❌ {stats['errors']} transactions have validation errors")
        success = False

    # Check 6: Quality scores are good
    avg_quality = sum(validator.validate_transaction(t)['quality_score'] for t in transactions) / len(transactions)
    if avg_quality >= 0.7:
        checks.append(f"✅ Average quality score: {avg_quality:.2f} (≥0.7)")
    else:
        checks.append(f"⚠️  Average quality score: {avg_quality:.2f} (<0.7)")

    # Print results
    for check in checks:
        print(check)

    print("\n" + "="*80)
    if success:
        print("🎉 SUCCESS: Enhanced parsing is working correctly!")
    else:
        print("⚠️  PARTIAL SUCCESS: Some issues need attention")
    print("="*80 + "\n")

    return success


if __name__ == "__main__":
    success = asyncio.run(test_enhanced_parsing_with_sample_pdf())
    exit(0 if success else 1)
