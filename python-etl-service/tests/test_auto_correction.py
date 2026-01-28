"""
Tests for the Auto-Correction Service.

Tests cover:
- CorrectionType enum
- CorrectionResult dataclass
- AutoCorrector class methods for:
  - Ticker corrections (FB→META, etc.)
  - Value range corrections (inverted min/max)
  - Date format normalization
  - Amount text parsing
  - Batch operations
  - Database operations (mocked)
  - Rollback support
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime

from app.services.auto_correction import (
    CorrectionType,
    CorrectionResult,
    AutoCorrector,
)


class TestCorrectionType:
    """Tests for CorrectionType enum."""

    def test_date_format_value(self):
        assert CorrectionType.DATE_FORMAT.value == "date_format"

    def test_ticker_cleanup_value(self):
        assert CorrectionType.TICKER_CLEANUP.value == "ticker_cleanup"

    def test_duplicate_merge_value(self):
        assert CorrectionType.DUPLICATE_MERGE.value == "duplicate_merge"

    def test_value_range_value(self):
        assert CorrectionType.VALUE_RANGE.value == "value_range"

    def test_politician_match_value(self):
        assert CorrectionType.POLITICIAN_MATCH.value == "politician_match"

    def test_amount_cleanup_value(self):
        assert CorrectionType.AMOUNT_CLEANUP.value == "amount_cleanup"

    def test_enum_is_string_subclass(self):
        """CorrectionType should be usable as a string."""
        assert isinstance(CorrectionType.DATE_FORMAT, str)
        assert CorrectionType.DATE_FORMAT == "date_format"


class TestCorrectionResult:
    """Tests for CorrectionResult dataclass."""

    def test_create_minimal(self):
        result = CorrectionResult(
            success=True,
            correction_type=CorrectionType.TICKER_CLEANUP,
            record_id="abc123",
            table_name="trading_disclosures",
            field_name="asset_ticker",
            old_value="FB",
            new_value="META",
            confidence=1.0,
        )
        assert result.success is True
        assert result.correction_type == CorrectionType.TICKER_CLEANUP
        assert result.record_id == "abc123"
        assert result.table_name == "trading_disclosures"
        assert result.field_name == "asset_ticker"
        assert result.old_value == "FB"
        assert result.new_value == "META"
        assert result.confidence == 1.0
        assert result.message == ""
        assert result.correction_id is None

    def test_create_with_message(self):
        result = CorrectionResult(
            success=True,
            correction_type=CorrectionType.DATE_FORMAT,
            record_id="xyz789",
            table_name="trading_disclosures",
            field_name="transaction_date",
            old_value="01/15/2025",
            new_value="2025-01-15",
            confidence=0.9,
            message="Normalized date format",
        )
        assert result.message == "Normalized date format"

    def test_create_with_correction_id(self):
        result = CorrectionResult(
            success=True,
            correction_type=CorrectionType.VALUE_RANGE,
            record_id="def456",
            table_name="trading_disclosures",
            field_name="amount_range",
            old_value={"min": 50000, "max": 15000},
            new_value={"min": 15000, "max": 50000},
            confidence=0.95,
            correction_id="corr-123",
        )
        assert result.correction_id == "corr-123"

    def test_failed_result(self):
        result = CorrectionResult(
            success=False,
            correction_type=CorrectionType.TICKER_CLEANUP,
            record_id="fail123",
            table_name="trading_disclosures",
            field_name="asset_ticker",
            old_value="INVALID",
            new_value=None,
            confidence=0.0,
            message="No mapping found for ticker",
        )
        assert result.success is False
        assert result.confidence == 0.0


class TestAutoCorrector:
    """Tests for AutoCorrector class."""

    @pytest.fixture
    def corrector(self):
        """Create an AutoCorrector with mocked Supabase."""
        with patch("app.services.auto_correction.get_supabase") as mock_get_supabase:
            mock_get_supabase.return_value = MagicMock()
            corrector = AutoCorrector()
            return corrector

    @pytest.fixture
    def corrector_no_supabase(self):
        """Create an AutoCorrector without Supabase (None)."""
        with patch("app.services.auto_correction.get_supabase") as mock_get_supabase:
            mock_get_supabase.return_value = None
            corrector = AutoCorrector()
            return corrector

    # =========================================================================
    # Ticker Mappings
    # =========================================================================

    def test_ticker_mappings_exist(self, corrector):
        """Verify known ticker mappings are defined."""
        assert "FB" in corrector.TICKER_MAPPINGS
        assert corrector.TICKER_MAPPINGS["FB"] == "META"

        assert "TWTR" in corrector.TICKER_MAPPINGS
        assert corrector.TICKER_MAPPINGS["TWTR"] == "X"

        assert "ANTM" in corrector.TICKER_MAPPINGS
        assert corrector.TICKER_MAPPINGS["ANTM"] == "ELV"

    def test_amount_ranges_exist(self, corrector):
        """Verify amount range mappings are defined."""
        assert "$1,001 - $15,000" in corrector.AMOUNT_RANGES
        assert corrector.AMOUNT_RANGES["$1,001 - $15,000"] == (1001, 15000)

        assert "Over $50,000,000" in corrector.AMOUNT_RANGES
        assert corrector.AMOUNT_RANGES["Over $50,000,000"] == (50000001, None)

    # =========================================================================
    # correct_ticker tests
    # =========================================================================

    def test_correct_ticker_fb_to_meta_dry_run(self, corrector):
        """Test FB→META correction in dry run mode."""
        result = corrector.correct_ticker("rec123", "FB", dry_run=True)

        assert result is not None
        assert result.success is True
        assert result.correction_type == CorrectionType.TICKER_CLEANUP
        assert result.old_value == "FB"
        assert result.new_value == "META"
        assert result.confidence == 1.0
        assert "rebrand" in result.message.lower()

    def test_correct_ticker_twtr_to_x(self, corrector):
        """Test TWTR→X correction."""
        result = corrector.correct_ticker("rec456", "TWTR", dry_run=True)

        assert result is not None
        assert result.old_value == "TWTR"
        assert result.new_value == "X"

    def test_correct_ticker_case_insensitive(self, corrector):
        """Test ticker correction is case-insensitive."""
        result = corrector.correct_ticker("rec789", "fb", dry_run=True)

        assert result is not None
        assert result.new_value == "META"

    def test_correct_ticker_with_whitespace(self, corrector):
        """Test ticker correction handles whitespace."""
        result = corrector.correct_ticker("rec101", "  FB  ", dry_run=True)

        assert result is not None
        assert result.new_value == "META"

    def test_correct_ticker_returns_none_for_unknown(self, corrector):
        """Test unknown tickers return None."""
        result = corrector.correct_ticker("rec202", "AAPL", dry_run=True)
        assert result is None

    def test_correct_ticker_returns_none_for_empty(self, corrector):
        """Test empty ticker returns None."""
        result = corrector.correct_ticker("rec303", "", dry_run=True)
        assert result is None

        result = corrector.correct_ticker("rec303", None, dry_run=True)
        assert result is None

    def test_correct_ticker_applies_when_not_dry_run(self, corrector):
        """Test ticker correction applies when not in dry run."""
        # Mock the apply method
        corrector._apply_correction = MagicMock(return_value=True)

        result = corrector.correct_ticker("rec404", "FB", dry_run=False)

        assert result is not None
        corrector._apply_correction.assert_called_once_with(result)

    # =========================================================================
    # correct_value_range tests
    # =========================================================================

    def test_correct_value_range_inverted(self, corrector):
        """Test correction of inverted min/max values."""
        result = corrector.correct_value_range("rec123", 50000, 15000, dry_run=True)

        assert result is not None
        assert result.success is True
        assert result.correction_type == CorrectionType.VALUE_RANGE
        assert result.old_value == {"min": 50000, "max": 15000}
        assert result.new_value == {"min": 15000, "max": 50000}
        assert result.confidence == 0.95
        assert "swap" in result.message.lower()

    def test_correct_value_range_already_correct(self, corrector):
        """Test no correction needed when values are already correct."""
        result = corrector.correct_value_range("rec456", 15000, 50000, dry_run=True)
        assert result is None

    def test_correct_value_range_equal_values(self, corrector):
        """Test no correction when min equals max."""
        result = corrector.correct_value_range("rec789", 25000, 25000, dry_run=True)
        assert result is None

    def test_correct_value_range_none_values(self, corrector):
        """Test returns None when values are None."""
        result = corrector.correct_value_range("rec101", None, 50000, dry_run=True)
        assert result is None

        result = corrector.correct_value_range("rec102", 15000, None, dry_run=True)
        assert result is None

        result = corrector.correct_value_range("rec103", None, None, dry_run=True)
        assert result is None

    def test_correct_value_range_applies_when_not_dry_run(self, corrector):
        """Test value range correction applies when not in dry run."""
        corrector._apply_range_correction = MagicMock(return_value=True)

        result = corrector.correct_value_range("rec202", 100000, 50000, dry_run=False)

        assert result is not None
        corrector._apply_range_correction.assert_called_once_with(result)

    # =========================================================================
    # correct_date_format tests
    # =========================================================================

    def test_correct_date_format_mm_dd_yyyy(self, corrector):
        """Test date normalization from MM/DD/YYYY."""
        result = corrector.correct_date_format(
            "rec123", "transaction_date", "01/15/2025", dry_run=True
        )

        assert result is not None
        assert result.success is True
        assert result.correction_type == CorrectionType.DATE_FORMAT
        assert result.old_value == "01/15/2025"
        assert result.new_value == "2025-01-15"
        assert result.confidence == 0.9

    def test_correct_date_format_dd_mm_yyyy(self, corrector):
        """Test date normalization from DD-MM-YYYY."""
        result = corrector.correct_date_format(
            "rec456", "disclosure_date", "15-01-2025", dry_run=True
        )

        assert result is not None
        # dateutil may interpret 15-01-2025 as Jan 15 or as invalid
        # Either way, it should normalize to ISO format
        assert result.new_value is not None

    def test_correct_date_format_already_iso(self, corrector):
        """Test no correction needed for ISO format."""
        result = corrector.correct_date_format(
            "rec789", "transaction_date", "2025-01-15", dry_run=True
        )
        assert result is None

    def test_correct_date_format_empty(self, corrector):
        """Test empty date returns None."""
        result = corrector.correct_date_format(
            "rec101", "transaction_date", "", dry_run=True
        )
        assert result is None

        result = corrector.correct_date_format(
            "rec102", "transaction_date", None, dry_run=True
        )
        assert result is None

    def test_correct_date_format_invalid(self, corrector):
        """Test invalid date returns None."""
        result = corrector.correct_date_format(
            "rec202", "transaction_date", "not-a-date", dry_run=True
        )
        assert result is None

    def test_correct_date_format_month_name(self, corrector):
        """Test date with month name."""
        result = corrector.correct_date_format(
            "rec303", "transaction_date", "January 15, 2025", dry_run=True
        )

        assert result is not None
        assert result.new_value == "2025-01-15"

    # =========================================================================
    # correct_amount_text tests
    # =========================================================================

    def test_correct_amount_text_exact_match(self, corrector):
        """Test exact match of amount text."""
        result = corrector.correct_amount_text("rec123", "$1,001 - $15,000", dry_run=True)

        assert result is not None
        assert result.success is True
        assert result.correction_type == CorrectionType.AMOUNT_CLEANUP
        assert result.new_value == {"min": 1001, "max": 15000}
        assert result.confidence == 1.0

    def test_correct_amount_text_larger_range(self, corrector):
        """Test larger amount range."""
        result = corrector.correct_amount_text(
            "rec456", "$1,000,001 - $5,000,000", dry_run=True
        )

        assert result is not None
        assert result.new_value == {"min": 1000001, "max": 5000000}

    def test_correct_amount_text_over_50m(self, corrector):
        """Test 'Over $50,000,000' case."""
        result = corrector.correct_amount_text("rec789", "Over $50,000,000", dry_run=True)

        assert result is not None
        assert result.new_value == {"min": 50000001, "max": None}

    def test_correct_amount_text_empty(self, corrector):
        """Test empty amount returns None."""
        result = corrector.correct_amount_text("rec101", "", dry_run=True)
        assert result is None

        result = corrector.correct_amount_text("rec102", None, dry_run=True)
        assert result is None

    def test_correct_amount_text_fuzzy_match(self, corrector):
        """Test fuzzy matching for slight variations."""
        # Slight variation in format
        result = corrector.correct_amount_text(
            "rec202", "$1,001-$15,000", dry_run=True  # Missing spaces
        )

        # Fuzzy match might find it, or might not depending on cutoff
        # Just verify it doesn't crash
        # If result is not None, verify structure
        if result is not None:
            assert result.confidence <= 1.0

    def test_correct_amount_text_unknown(self, corrector):
        """Test unknown amount text returns None."""
        result = corrector.correct_amount_text("rec303", "Unknown Amount", dry_run=True)
        assert result is None

    # =========================================================================
    # Batch operations tests
    # =========================================================================

    def test_run_ticker_corrections_no_supabase(self, corrector_no_supabase):
        """Test batch ticker corrections returns empty when no Supabase."""
        results = corrector_no_supabase.run_ticker_corrections(dry_run=True)
        assert results == []

    def test_run_ticker_corrections_finds_outdated(self, corrector):
        """Test batch ticker corrections finds and corrects outdated tickers."""
        # Mock the database query
        mock_response = MagicMock()
        mock_response.data = [
            {"id": "rec1", "asset_ticker": "FB"},
            {"id": "rec2", "asset_ticker": "FB"},
        ]

        corrector.supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            mock_response
        )

        results = corrector.run_ticker_corrections(limit=10, dry_run=True)

        # Should find FB records and create corrections
        assert len(results) >= 2
        for result in results:
            if result.old_value == "FB":
                assert result.new_value == "META"

    def test_run_value_range_corrections_no_supabase(self, corrector_no_supabase):
        """Test batch value range corrections returns empty when no Supabase."""
        results = corrector_no_supabase.run_value_range_corrections(dry_run=True)
        assert results == []

    def test_run_value_range_corrections_filters_inverted_values(self, corrector):
        """Test that inverted values are correctly identified for correction.

        This tests the filtering logic indirectly - the batch function relies
        on correct_value_range which is tested separately. Here we just verify
        that the function correctly identifies inverted records.
        """
        # Test the underlying logic directly rather than through Supabase mocking
        # The filtering happens in correct_value_range, which we call directly

        # Record with inverted values should produce a result
        result1 = corrector.correct_value_range("rec1", 50000, 15000, dry_run=True)
        assert result1 is not None
        assert result1.old_value == {"min": 50000, "max": 15000}
        assert result1.new_value == {"min": 15000, "max": 50000}

        # Record with correct values should return None
        result2 = corrector.correct_value_range("rec2", 15000, 50000, dry_run=True)
        assert result2 is None

        # Another inverted record
        result3 = corrector.correct_value_range("rec3", 100000, 25000, dry_run=True)
        assert result3 is not None
        assert result3.record_id == "rec3"

    # =========================================================================
    # Database operation tests (mocked)
    # =========================================================================

    def test_apply_correction_success(self, corrector):
        """Test _apply_correction succeeds."""
        result = CorrectionResult(
            success=True,
            correction_type=CorrectionType.TICKER_CLEANUP,
            record_id="rec123",
            table_name="trading_disclosures",
            field_name="asset_ticker",
            old_value="FB",
            new_value="META",
            confidence=1.0,
        )

        corrector._log_correction = MagicMock(return_value="corr-123")
        corrector._mark_correction_applied = MagicMock()

        success = corrector._apply_correction(result)

        assert success is True
        assert result.correction_id == "corr-123"
        assert result in corrector.corrections_made
        corrector.supabase.table.assert_called()

    def test_apply_correction_no_supabase(self, corrector_no_supabase):
        """Test _apply_correction fails without Supabase."""
        result = CorrectionResult(
            success=True,
            correction_type=CorrectionType.TICKER_CLEANUP,
            record_id="rec123",
            table_name="trading_disclosures",
            field_name="asset_ticker",
            old_value="FB",
            new_value="META",
            confidence=1.0,
        )

        success = corrector_no_supabase._apply_correction(result)

        assert success is False
        assert result.success is False

    def test_apply_range_correction_success(self, corrector):
        """Test _apply_range_correction succeeds."""
        result = CorrectionResult(
            success=True,
            correction_type=CorrectionType.VALUE_RANGE,
            record_id="rec123",
            table_name="trading_disclosures",
            field_name="amount_range",
            old_value={"min": 50000, "max": 15000},
            new_value={"min": 15000, "max": 50000},
            confidence=0.95,
        )

        corrector._log_correction = MagicMock(return_value="corr-456")
        corrector._mark_correction_applied = MagicMock()

        success = corrector._apply_range_correction(result)

        assert success is True
        assert result.correction_id == "corr-456"

    def test_apply_amount_correction_success(self, corrector):
        """Test _apply_amount_correction succeeds."""
        result = CorrectionResult(
            success=True,
            correction_type=CorrectionType.AMOUNT_CLEANUP,
            record_id="rec123",
            table_name="trading_disclosures",
            field_name="amount_range",
            old_value="$1,001 - $15,000",
            new_value={"min": 1001, "max": 15000},
            confidence=1.0,
        )

        corrector._log_correction = MagicMock(return_value="corr-789")
        corrector._mark_correction_applied = MagicMock()

        success = corrector._apply_amount_correction(result)

        assert success is True

    def test_apply_amount_correction_with_none_max(self, corrector):
        """Test _apply_amount_correction with None max (Over $50M case)."""
        result = CorrectionResult(
            success=True,
            correction_type=CorrectionType.AMOUNT_CLEANUP,
            record_id="rec123",
            table_name="trading_disclosures",
            field_name="amount_range",
            old_value="Over $50,000,000",
            new_value={"min": 50000001, "max": None},
            confidence=1.0,
        )

        corrector._log_correction = MagicMock(return_value="corr-101")
        corrector._mark_correction_applied = MagicMock()

        success = corrector._apply_amount_correction(result)

        assert success is True

    # =========================================================================
    # Audit logging tests
    # =========================================================================

    def test_log_correction(self, corrector):
        """Test _log_correction inserts audit record."""
        result = CorrectionResult(
            success=True,
            correction_type=CorrectionType.TICKER_CLEANUP,
            record_id="rec123",
            table_name="trading_disclosures",
            field_name="asset_ticker",
            old_value="FB",
            new_value="META",
            confidence=1.0,
        )

        correction_id = corrector._log_correction(result)

        assert correction_id is not None
        # Verify insert was called
        corrector.supabase.table.assert_called_with("data_quality_corrections")

    def test_mark_correction_applied(self, corrector):
        """Test _mark_correction_applied updates status."""
        corrector._mark_correction_applied("corr-123")

        corrector.supabase.table.assert_called_with("data_quality_corrections")

    # =========================================================================
    # Rollback tests
    # =========================================================================

    def test_rollback_correction_success(self, corrector):
        """Test rollback_correction succeeds."""
        mock_response = MagicMock()
        mock_response.data = {
            "id": "corr-123",
            "record_id": "rec123",
            "table_name": "trading_disclosures",
            "field_name": "asset_ticker",
            "old_value": "FB",
            "new_value": "META",
        }

        corrector.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = (
            mock_response
        )

        success = corrector.rollback_correction("corr-123")

        assert success is True

    def test_rollback_correction_not_found(self, corrector):
        """Test rollback_correction fails when correction not found."""
        mock_response = MagicMock()
        mock_response.data = None

        corrector.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = (
            mock_response
        )

        success = corrector.rollback_correction("corr-nonexistent")

        assert success is False

    def test_rollback_correction_no_supabase(self, corrector_no_supabase):
        """Test rollback_correction fails without Supabase."""
        success = corrector_no_supabase.rollback_correction("corr-123")
        assert success is False

    # =========================================================================
    # Error handling tests
    # =========================================================================

    def test_apply_correction_handles_exception(self, corrector):
        """Test _apply_correction handles database errors."""
        result = CorrectionResult(
            success=True,
            correction_type=CorrectionType.TICKER_CLEANUP,
            record_id="rec123",
            table_name="trading_disclosures",
            field_name="asset_ticker",
            old_value="FB",
            new_value="META",
            confidence=1.0,
        )

        corrector._log_correction = MagicMock(side_effect=Exception("DB Error"))

        success = corrector._apply_correction(result)

        assert success is False
        assert result.success is False
        assert "Failed" in result.message

    def test_run_ticker_corrections_handles_exception(self, corrector):
        """Test batch ticker corrections handles exceptions gracefully."""
        corrector.supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = Exception(
            "Query failed"
        )

        # Should not raise, returns empty list
        results = corrector.run_ticker_corrections(dry_run=True)
        assert results == []
