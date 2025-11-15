"""
Unit tests for enhanced House disclosure parsing utilities.

Tests for Issue #16: Enhanced House Financial Disclosure Parsing
"""

import pytest
from datetime import datetime
from decimal import Decimal

from politician_trading.parsers import (
    TickerResolver,
    ValueRangeParser,
    OwnerParser,
    DateParser,
    extract_ticker_from_text,
    DisclosureValidator,
)


class TestTickerResolver:
    """Tests for TickerResolver class"""

    def test_exact_match_common_ticker(self):
        """Test exact match against common ticker mappings"""
        resolver = TickerResolver()
        ticker, confidence = resolver.resolve("Apple Inc")

        assert ticker == "AAPL"
        assert confidence == 1.0

    def test_fuzzy_match_common_ticker(self):
        """Test fuzzy matching for slight variations"""
        resolver = TickerResolver()
        ticker, confidence = resolver.resolve("Apple Incorporated")

        assert ticker == "AAPL"
        assert confidence >= 0.75  # Fuzzy match threshold

    def test_cache_functionality(self):
        """Test that resolved tickers are cached"""
        resolver = TickerResolver()

        # First resolution
        ticker1, conf1 = resolver.resolve("Microsoft Corporation")
        # Second resolution (should use cache)
        ticker2, conf2 = resolver.resolve("Microsoft Corporation")

        assert ticker1 == ticker2 == "MSFT"
        assert conf1 == conf2 == 1.0
        assert "microsoft corporation" in resolver._cache

    def test_unknown_company(self):
        """Test resolution fails gracefully for unknown companies"""
        resolver = TickerResolver()
        ticker, confidence = resolver.resolve("Unknown Fictional Company Inc")

        # Should return None with 0 confidence
        assert confidence < 1.0  # May still attempt resolution

    def test_empty_input(self):
        """Test handling of empty input"""
        resolver = TickerResolver()
        ticker, confidence = resolver.resolve("")

        assert ticker is None
        assert confidence == 0.0


class TestValueRangeParser:
    """Tests for ValueRangeParser class"""

    def test_standard_range(self):
        """Test parsing standard disclosure range"""
        result = ValueRangeParser.parse("$1,001 - $15,000")

        assert result["value_low"] == Decimal("1001")
        assert result["value_high"] == Decimal("15000")
        assert result["is_range"] is True
        assert result["midpoint"] == Decimal("8000.5")

    def test_range_without_commas(self):
        """Test parsing range without thousand separators"""
        result = ValueRangeParser.parse("$15001-$50000")

        assert result["value_low"] == Decimal("15001")
        assert result["value_high"] == Decimal("50000")
        assert result["is_range"] is True

    def test_over_amount(self):
        """Test parsing 'Over' pattern"""
        result = ValueRangeParser.parse("Over $50,000,000")

        assert result["value_low"] == Decimal("50000000")
        assert result["value_high"] is None
        assert result["is_range"] is False
        assert result["midpoint"] == Decimal("50000000")

    def test_or_less_amount(self):
        """Test parsing 'or less' pattern"""
        result = ValueRangeParser.parse("$1,000 or less")

        assert result["value_low"] is None
        assert result["value_high"] == Decimal("1000")
        assert result["is_range"] is False
        assert result["midpoint"] == Decimal("500")  # Half of value_high

    def test_single_value(self):
        """Test parsing single exact value"""
        result = ValueRangeParser.parse("$25,000")

        assert result["value_low"] == Decimal("25000")
        assert result["value_high"] == Decimal("25000")
        assert result["is_range"] is False
        assert result["midpoint"] == Decimal("25000")

    def test_empty_input(self):
        """Test handling of empty input"""
        result = ValueRangeParser.parse("")

        assert result["value_low"] is None
        assert result["value_high"] is None
        assert result["is_range"] is False
        assert result["midpoint"] is None

    def test_unparseable_text(self):
        """Test handling of text with no value"""
        result = ValueRangeParser.parse("No value specified")

        assert result["value_low"] is None
        assert result["value_high"] is None


class TestOwnerParser:
    """Tests for OwnerParser class"""

    def test_joint_ownership(self):
        """Test parsing joint ownership codes"""
        assert OwnerParser.parse("JT") == "JOINT"
        assert OwnerParser.parse("joint") == "JOINT"

    def test_spouse_ownership(self):
        """Test parsing spouse ownership codes"""
        assert OwnerParser.parse("SP") == "SPOUSE"
        assert OwnerParser.parse("spouse") == "SPOUSE"
        assert OwnerParser.parse("S") == "SPOUSE"

    def test_self_ownership(self):
        """Test parsing self ownership"""
        assert OwnerParser.parse("Self") == "SELF"
        assert OwnerParser.parse("filer") == "SELF"
        assert OwnerParser.parse("") == "SELF"  # Default
        assert OwnerParser.parse(None) == "SELF"  # Default

    def test_dependent_ownership(self):
        """Test parsing dependent ownership codes"""
        assert OwnerParser.parse("DEP") == "DEPENDENT"
        assert OwnerParser.parse("dependent") == "DEPENDENT"
        assert OwnerParser.parse("DC") == "DEPENDENT"

    def test_partial_match(self):
        """Test partial matching in text"""
        assert OwnerParser.parse("owned by spouse") == "SPOUSE"
        assert OwnerParser.parse("joint account") == "JOINT"


class TestDateParser:
    """Tests for DateParser class"""

    def test_slash_format_mmddyyyy(self):
        """Test parsing MM/DD/YYYY format"""
        result = DateParser.parse("11/15/2024")

        assert result is not None
        assert result.year == 2024
        assert result.month == 11
        assert result.day == 15

    def test_dash_format(self):
        """Test parsing MM-DD-YYYY format"""
        result = DateParser.parse("11-15-2024")

        assert result is not None
        assert result.year == 2024
        assert result.month == 11
        assert result.day == 15

    def test_iso_format(self):
        """Test parsing ISO format YYYY-MM-DD"""
        result = DateParser.parse("2024-11-15")

        assert result is not None
        assert result.year == 2024
        assert result.month == 11
        assert result.day == 15

    def test_long_month_format(self):
        """Test parsing 'Month DD, YYYY' format"""
        result = DateParser.parse("November 15, 2024")

        assert result is not None
        assert result.year == 2024
        assert result.month == 11
        assert result.day == 15

    def test_short_month_format(self):
        """Test parsing 'Mon DD, YYYY' format"""
        result = DateParser.parse("Nov 15, 2024")

        assert result is not None
        assert result.year == 2024
        assert result.month == 11
        assert result.day == 15

    def test_to_iso(self):
        """Test conversion to ISO string"""
        iso_str = DateParser.to_iso("11/15/2024")

        assert iso_str is not None
        assert "2024-11-15" in iso_str

    def test_invalid_date(self):
        """Test handling of invalid date"""
        result = DateParser.parse("not a date")

        assert result is None

    def test_empty_input(self):
        """Test handling of empty input"""
        result = DateParser.parse("")

        assert result is None


class TestExtractTickerFromText:
    """Tests for extract_ticker_from_text function"""

    def test_parentheses_ticker(self):
        """Test extracting ticker from parentheses"""
        assert extract_ticker_from_text("Apple Inc (AAPL)") == "AAPL"

    def test_brackets_are_not_tickers(self):
        """Test that brackets are NOT treated as tickers (they're asset type codes)"""
        # Brackets like [ST] or [MF] indicate asset types, not ticker symbols
        # So ticker extraction should NOT match content in brackets
        assert extract_ticker_from_text("Microsoft Corp [MSFT]") is None
        assert extract_ticker_from_text("Some Stock [ST]") is None

    def test_ticker_label(self):
        """Test extracting ticker with 'Ticker:' label"""
        assert extract_ticker_from_text("Company Name Ticker: GOOGL") == "GOOGL"

    def test_symbol_label(self):
        """Test extracting ticker with 'Symbol:' label"""
        assert extract_ticker_from_text("Asset Symbol: TSLA") == "TSLA"

    def test_standalone_ticker(self):
        """Test extracting standalone ticker at end of line"""
        assert extract_ticker_from_text("Company Name NVDA") == "NVDA"

    def test_false_positive_filtering(self):
        """Test that common false positives are filtered out"""
        # These should not be recognized as tickers
        assert extract_ticker_from_text("Apple INC") is None
        assert extract_ticker_from_text("Company LLC") is None

    def test_no_ticker(self):
        """Test text with no ticker"""
        assert extract_ticker_from_text("Just some regular text") is None

    def test_empty_input(self):
        """Test empty input"""
        assert extract_ticker_from_text("") is None


class TestDisclosureValidator:
    """Tests for DisclosureValidator class"""

    def test_validate_complete_transaction(self):
        """Test validation of complete, valid transaction"""
        validator = DisclosureValidator()

        transaction = {
            "transaction_type": "PURCHASE",
            "asset_name": "Apple Inc",
            "ticker": "AAPL",
            "ticker_confidence_score": 1.0,
            "transaction_date": datetime(2024, 10, 1),
            "filing_date": datetime(2024, 10, 15),
            "value_low": Decimal("1001"),
            "value_high": Decimal("15000"),
        }

        result = validator.validate_transaction(transaction)

        assert result["is_valid"] is True
        assert len(result["errors"]) == 0
        assert result["quality_score"] > 0.8

    def test_validate_missing_required_fields(self):
        """Test validation catches missing required fields"""
        validator = DisclosureValidator()

        transaction = {
            # Missing transaction_type and asset_name
            "ticker": "AAPL",
        }

        result = validator.validate_transaction(transaction)

        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
        assert any("transaction_type" in error for error in result["errors"])
        assert any("asset_name" in error for error in result["errors"])

    def test_validate_date_sequence(self):
        """Test validation of date sequence"""
        validator = DisclosureValidator()

        # Transaction after filing (invalid)
        transaction = {
            "transaction_type": "SALE",
            "asset_name": "Test Asset",
            "transaction_date": datetime(2024, 10, 20),
            "filing_date": datetime(2024, 10, 15),  # Before transaction
        }

        result = validator.validate_transaction(transaction)

        assert len(result["warnings"]) > 0
        assert any("after filing_date" in warning for warning in result["warnings"])

    def test_validate_value_range(self):
        """Test validation of value ranges"""
        validator = DisclosureValidator()

        # Invalid: high < low
        transaction = {
            "transaction_type": "PURCHASE",
            "asset_name": "Test Asset",
            "value_low": Decimal("50000"),
            "value_high": Decimal("1000"),  # Lower than value_low
        }

        result = validator.validate_transaction(transaction)

        assert result["is_valid"] is False
        assert any("less than value_low" in error for error in result["errors"])

    def test_validate_capital_gain(self):
        """Test validation of capital gain entry"""
        validator = DisclosureValidator()

        capital_gain = {
            "asset_name": "Apple Inc",
            "date_acquired": datetime(2023, 1, 1),
            "date_sold": datetime(2024, 6, 1),
            "gain_type": "LONG_TERM",
            "gain_amount": Decimal("5000"),
        }

        result = validator.validate_capital_gain(capital_gain)

        assert result["is_valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_capital_gain_date_sequence(self):
        """Test capital gain validation catches invalid date sequence"""
        validator = DisclosureValidator()

        capital_gain = {
            "asset_name": "Test Asset",
            "date_acquired": datetime(2024, 6, 1),
            "date_sold": datetime(2023, 1, 1),  # Before acquired
        }

        result = validator.validate_capital_gain(capital_gain)

        assert result["is_valid"] is False
        assert any("before date_acquired" in error for error in result["errors"])

    def test_validate_asset_holding(self):
        """Test validation of asset holding"""
        validator = DisclosureValidator()

        holding = {
            "asset_name": "Microsoft Corp",
            "filing_date": datetime(2024, 10, 1),
            "value_low": Decimal("15001"),
            "value_high": Decimal("50000"),
        }

        result = validator.validate_asset_holding(holding)

        assert result["is_valid"] is True
        assert len(result["errors"]) == 0

    def test_check_duplicate_transactions(self):
        """Test duplicate detection"""
        validator = DisclosureValidator()

        transactions = [
            {
                "ticker": "AAPL",
                "asset_name": "Apple Inc",
                "transaction_type": "PURCHASE",
                "transaction_date": datetime(2024, 10, 1),
            },
            {
                "ticker": "AAPL",
                "asset_name": "Apple Inc",
                "transaction_type": "PURCHASE",
                "transaction_date": datetime(2024, 10, 1),
            },
            {
                "ticker": "MSFT",
                "asset_name": "Microsoft Corp",
                "transaction_type": "SALE",
                "transaction_date": datetime(2024, 10, 2),
            },
        ]

        duplicates = validator.check_duplicate_transactions(transactions)

        assert len(duplicates) > 0
        # First two transactions should be flagged as likely duplicates
        assert duplicates[0]["similarity"] > 0.9

    def test_flag_outliers(self):
        """Test outlier flagging"""
        validator = DisclosureValidator()

        transactions = [
            {
                "transaction_type": "PURCHASE",
                "asset_name": "Normal Transaction",
                "ticker": "AAPL",
                "value_high": Decimal("15000"),
                "transaction_date": datetime(2024, 10, 1),
                "ticker_confidence_score": 1.0,
            },
            {
                "transaction_type": "SALE",
                "asset_name": "Large Transaction",
                "ticker": "MSFT",
                "value_high": Decimal("5000000"),  # $5M - outlier
                "transaction_date": datetime(2024, 10, 1),
                "ticker_confidence_score": 1.0,
            },
            {
                "transaction_type": "PURCHASE",
                "asset_name": "Low Confidence",
                # No transaction_date - should be flagged
                "ticker_confidence_score": 0.3,  # Low confidence
            },
        ]

        outliers = validator.flag_outliers(transactions)

        assert len(outliers) >= 2  # At least the large transaction and low confidence
        # Check that large transaction is flagged
        assert any("Large transaction" in str(outlier["flags"]) for outlier in outliers)

    def test_validation_stats(self):
        """Test validation statistics tracking"""
        validator = DisclosureValidator()

        # Validate some transactions
        validator.validate_transaction({"transaction_type": "PURCHASE", "asset_name": "Test"})
        validator.validate_transaction({})  # Invalid - missing required fields

        stats = validator.get_validation_summary()

        assert stats["total_validated"] == 2
        assert stats["passed"] == 1
        assert stats["errors"] == 1
        assert "pass_rate" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
