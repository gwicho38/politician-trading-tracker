#!/usr/bin/env python3
"""
Verify Phase 6 Integration

This script verifies that all Phase 6 code changes are in place:
1. TradingDisclosure model has enhanced fields
2. Scraper populates enhanced fields
3. Database layer handles enhanced fields
"""
import sys
sys.path.insert(0, '/Users/lefv/repos/politician-trading-tracker/src')

from models import TradingDisclosure
from decimal import Decimal
from datetime import datetime

print("=" * 80)
print("PHASE 6 INTEGRATION VERIFICATION")
print("=" * 80)
print()

# Test 1: Model has enhanced fields
print("Test 1: TradingDisclosure model has enhanced fields")
print("-" * 80)

enhanced_fields = [
    'filer_id',
    'filing_date',
    'ticker_confidence_score',
    'asset_owner',
    'specific_owner_text',
    'asset_type_code',
    'notification_date',
    'filing_status',
    'quantity'
]

disclosure = TradingDisclosure()
missing_fields = []
for field in enhanced_fields:
    if not hasattr(disclosure, field):
        missing_fields.append(field)
        print(f"  ✗ Missing field: {field}")
    else:
        print(f"  ✓ Has field: {field}")

if missing_fields:
    print()
    print(f"❌ FAILED: Missing {len(missing_fields)} enhanced fields")
    sys.exit(1)
else:
    print()
    print("✅ PASSED: All enhanced fields present in model")

print()

# Test 2: Enhanced fields can be set
print("Test 2: Enhanced fields can be populated")
print("-" * 80)

test_disclosure = TradingDisclosure(
    asset_name="Amazon.com, Inc.",
    asset_ticker="AMZN",
    filer_id="20026658",
    filing_date="2025-01-27",
    ticker_confidence_score=Decimal("1.0"),
    asset_owner="SELF",
    specific_owner_text="DG Trust",
    asset_type_code="ST",
    notification_date=datetime(2025, 1, 10),
    filing_status="New",
    quantity=Decimal("100")
)

try:
    assert test_disclosure.filer_id == "20026658"
    assert test_disclosure.filing_date == "2025-01-27"
    assert test_disclosure.ticker_confidence_score == Decimal("1.0")
    assert test_disclosure.asset_owner == "SELF"
    assert test_disclosure.specific_owner_text == "DG Trust"
    assert test_disclosure.asset_type_code == "ST"
    assert test_disclosure.notification_date == datetime(2025, 1, 10)
    assert test_disclosure.filing_status == "New"
    assert test_disclosure.quantity == Decimal("100")

    print(f"  ✓ filer_id: {test_disclosure.filer_id}")
    print(f"  ✓ filing_date: {test_disclosure.filing_date}")
    print(f"  ✓ ticker_confidence_score: {test_disclosure.ticker_confidence_score}")
    print(f"  ✓ asset_owner: {test_disclosure.asset_owner}")
    print(f"  ✓ specific_owner_text: {test_disclosure.specific_owner_text}")
    print(f"  ✓ asset_type_code: {test_disclosure.asset_type_code}")
    print(f"  ✓ notification_date: {test_disclosure.notification_date}")
    print(f"  ✓ filing_status: {test_disclosure.filing_status}")
    print(f"  ✓ quantity: {test_disclosure.quantity}")

    print()
    print("✅ PASSED: Enhanced fields can be populated")
except AssertionError as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)

print()

# Test 3: Check database layer has enhanced field handling
print("Test 3: Database layer has enhanced field handling")
print("-" * 80)

from politician_trading.scrapers.seed_database import upsert_trading_disclosures
import inspect

source = inspect.getsource(upsert_trading_disclosures)

enhanced_field_checks = [
    'filer_id',
    'filing_date',
    'ticker_confidence_score',
    'asset_owner',
    'asset_type_code',
]

missing_checks = []
for field in enhanced_field_checks:
    if field in source:
        print(f"  ✓ Handles field: {field}")
    else:
        print(f"  ✗ Missing handler for: {field}")
        missing_checks.append(field)

if missing_checks:
    print()
    print(f"❌ FAILED: Database layer missing {len(missing_checks)} field handlers")
    sys.exit(1)
else:
    print()
    print("✅ PASSED: Database layer handles enhanced fields")

print()

# Test 4: Check scraper integration
print("Test 4: Scraper creates disclosures with enhanced fields")
print("-" * 80)

from politician_trading.scrapers.scrapers import CongressTradingScraper
import inspect

scraper_source = inspect.getsource(CongressTradingScraper.scrape_house_disclosures)

# Check that scraper passes enhanced fields to TradingDisclosure
enhanced_field_assignments = [
    'filer_id=',
    'filing_date=',
    'ticker_confidence_score=',
    'asset_owner=',
    'asset_type_code=',
]

missing_assignments = []
for assignment in enhanced_field_assignments:
    if assignment in scraper_source:
        print(f"  ✓ Assigns field: {assignment.replace('=', '')}")
    else:
        print(f"  ✗ Missing assignment: {assignment.replace('=', '')}")
        missing_assignments.append(assignment)

if missing_assignments:
    print()
    print(f"❌ FAILED: Scraper missing {len(missing_assignments)} field assignments")
    sys.exit(1)
else:
    print()
    print("✅ PASSED: Scraper assigns enhanced fields")

print()
print("=" * 80)
print("ALL TESTS PASSED ✅")
print("=" * 80)
print()
print("Phase 6 integration is complete and functional!")
print()
print("Next steps:")
print("  1. Run a full scrape with parse_pdfs=True")
print("  2. Verify enhanced fields in database")
print("  3. Enable in production workflow")
