"""
Tests for PoliticianNormalizer service.

Covers:
- Role mapping completeness and correctness
- Name prefix removal (all honorific variants)
- State extraction from district field
- Dry-run mode (no modifications)
- Placeholder name exclusion
- Audit trail logging
- Full normalize_all orchestration
"""

import uuid
from unittest.mock import MagicMock, patch, call

import pytest

from app.services.politician_normalizer import (
    CANONICAL_ROLES,
    HONORIFIC_PREFIXES,
    PLACEHOLDER_PATTERNS,
    ROLE_MAP,
    PoliticianNormalizer,
)
from app.services.auto_correction import CorrectionType


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    mock = MagicMock()

    # Default empty response
    empty_response = MagicMock()
    empty_response.data = []
    mock.table.return_value.select.return_value.limit.return_value.execute.return_value = (
        empty_response
    )

    return mock


@pytest.fixture
def normalizer(mock_supabase):
    """Create a PoliticianNormalizer with mock Supabase."""
    with patch("app.services.politician_normalizer.get_supabase", return_value=mock_supabase):
        n = PoliticianNormalizer()
    return n


def _make_response(data):
    """Create a mock Supabase response."""
    resp = MagicMock()
    resp.data = data
    return resp


# ============================================================================
# Role Mapping Tests
# ============================================================================


class TestRoleMapping:
    """Tests for role normalization logic."""

    def test_canonical_roles_unchanged(self, normalizer):
        """Canonical roles should not be modified."""
        for role in CANONICAL_ROLES:
            assert normalizer._map_role(role) is None or normalizer._map_role(role) == role

    def test_us_house_representative_maps_to_representative(self, normalizer):
        assert normalizer._map_role("us_house_representative") == "Representative"

    def test_senate_maps_to_senator(self, normalizer):
        assert normalizer._map_role("Senate") == "Senator"

    def test_house_maps_to_representative(self, normalizer):
        assert normalizer._map_role("House") == "Representative"

    def test_congress_maps_to_representative(self, normalizer):
        assert normalizer._map_role("Congress") == "Representative"

    def test_case_insensitive_mapping(self, normalizer):
        assert normalizer._map_role("SENATE") == "Senator"
        assert normalizer._map_role("senate") == "Senator"
        assert normalizer._map_role("HOUSE") == "Representative"

    def test_prefix_pattern_representative(self, normalizer):
        """Roles like 'Representative-CA' should map to 'Representative'."""
        assert normalizer._map_role("Representative-CA") == "Representative"
        assert normalizer._map_role("Representative-TX") == "Representative"

    def test_prefix_pattern_senator(self, normalizer):
        """Roles like 'Senator-NY' should map to 'Senator'."""
        assert normalizer._map_role("Senator-NY") == "Senator"

    def test_unknown_role_returns_none(self, normalizer):
        assert normalizer._map_role("SomeRandomRole") is None
        assert normalizer._map_role("") is None
        assert normalizer._map_role(None) is None

    def test_mep_variants(self, normalizer):
        assert normalizer._map_role("MEP") == "MEP"
        assert normalizer._map_role("EU Parliament") == "MEP"
        assert normalizer._map_role("Member of European Parliament") == "MEP"

    def test_all_role_map_entries_produce_canonical(self, normalizer):
        """Every entry in ROLE_MAP should map to a canonical role."""
        for key, value in ROLE_MAP.items():
            assert value in CANONICAL_ROLES, f"ROLE_MAP['{key}'] = '{value}' is not canonical"


class TestNormalizeRoles:
    """Tests for the normalize_roles batch method."""

    def test_dry_run_no_writes(self, normalizer, mock_supabase):
        """Dry run should not make any database writes."""
        response = _make_response([
            {"id": "1", "first_name": "John", "last_name": "Doe", "role": "us_house_representative"},
        ])
        mock_supabase.table.return_value.select.return_value.limit.return_value.execute.return_value = response

        result = normalizer.normalize_roles(dry_run=True)

        assert result["corrections"] == 1
        assert result["errors"] == 0
        # Verify no update or insert calls were made
        mock_supabase.table.return_value.update.assert_not_called()

    def test_live_run_applies_corrections(self, normalizer, mock_supabase):
        """Live run should update the database and log corrections."""
        select_response = _make_response([
            {"id": "1", "first_name": "Jane", "last_name": "Smith", "role": "Senate"},
        ])
        mock_supabase.table.return_value.select.return_value.limit.return_value.execute.return_value = select_response

        # Mock the update chain
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = _make_response([])
        # Mock the insert for audit log
        mock_supabase.table.return_value.insert.return_value.execute.return_value = _make_response([])

        result = normalizer.normalize_roles(dry_run=False)

        assert result["corrections"] == 1
        assert result["errors"] == 0

    def test_skips_canonical_roles(self, normalizer, mock_supabase):
        """Politicians with canonical roles should be skipped."""
        response = _make_response([
            {"id": "1", "first_name": "A", "last_name": "B", "role": "Representative"},
            {"id": "2", "first_name": "C", "last_name": "D", "role": "Senator"},
            {"id": "3", "first_name": "E", "last_name": "F", "role": "MEP"},
        ])
        mock_supabase.table.return_value.select.return_value.limit.return_value.execute.return_value = response

        result = normalizer.normalize_roles(dry_run=True)
        assert result["corrections"] == 0

    def test_unknown_role_logged_as_skipped(self, normalizer, mock_supabase):
        """Unknown roles should be logged but not corrected."""
        response = _make_response([
            {"id": "1", "first_name": "A", "last_name": "B", "role": "WeirdRole"},
        ])
        mock_supabase.table.return_value.select.return_value.limit.return_value.execute.return_value = response

        result = normalizer.normalize_roles(dry_run=True)
        assert result["corrections"] == 0
        assert len(result["details"]) == 1
        assert result["details"][0]["action"] == "skipped_unknown"

    def test_respects_limit(self, normalizer, mock_supabase):
        """Should stop after processing 'limit' records."""
        records = [
            {"id": str(i), "first_name": f"P{i}", "last_name": "X", "role": "Senate"}
            for i in range(20)
        ]
        mock_supabase.table.return_value.select.return_value.limit.return_value.execute.return_value = _make_response(records)

        result = normalizer.normalize_roles(dry_run=True, limit=5)
        assert result["corrections"] == 5


# ============================================================================
# Name Standardization Tests
# ============================================================================


class TestNameCleaning:
    """Tests for name cleaning helpers."""

    def test_strip_hon_prefix(self, normalizer):
        assert normalizer._clean_name("Hon. John Smith") == "John Smith"

    def test_strip_the_honorable(self, normalizer):
        assert normalizer._clean_name("The Honorable Jane Doe") == "Jane Doe"

    def test_strip_mr_mrs_ms(self, normalizer):
        assert normalizer._clean_name("Mr. Bob Jones") == "Bob Jones"
        assert normalizer._clean_name("Mrs. Alice Green") == "Alice Green"
        assert normalizer._clean_name("Ms. Carol White") == "Carol White"

    def test_strip_sen_rep(self, normalizer):
        assert normalizer._clean_name("Sen. Mark Warner") == "Mark Warner"
        assert normalizer._clean_name("Rep. Nancy Pelosi") == "Nancy Pelosi"

    def test_strip_full_title(self, normalizer):
        assert normalizer._clean_name("Senator Patrick Leahy") == "Patrick Leahy"
        assert normalizer._clean_name("Representative Liz Cheney") == "Liz Cheney"

    def test_fix_multiple_spaces(self, normalizer):
        assert normalizer._clean_name("John   Smith") == "John Smith"

    def test_trim_whitespace(self, normalizer):
        assert normalizer._clean_name("  John Smith  ") == "John Smith"

    def test_name_without_prefix_unchanged(self, normalizer):
        assert normalizer._clean_name("John Smith") == "John Smith"

    def test_only_strips_first_prefix(self, normalizer):
        """Should only strip the first matching prefix."""
        result = normalizer._clean_name("Hon. Rep. Smith")
        # "Hon. " is stripped first, leaving "Rep. Smith"
        assert result == "Rep. Smith"


class TestPlaceholderDetection:
    """Tests for placeholder name detection."""

    def test_placeholder_detected(self, normalizer):
        assert normalizer._is_placeholder("Placeholder Senator")
        assert normalizer._is_placeholder("PLACEHOLDER")

    def test_unknown_detected(self, normalizer):
        assert normalizer._is_placeholder("Unknown Person")
        assert normalizer._is_placeholder("unknown")

    def test_pending_detected(self, normalizer):
        assert normalizer._is_placeholder("Pending")

    def test_tbd_detected(self, normalizer):
        assert normalizer._is_placeholder("TBD")

    def test_na_detected(self, normalizer):
        assert normalizer._is_placeholder("N/A")

    def test_real_name_not_placeholder(self, normalizer):
        assert not normalizer._is_placeholder("John Smith")
        assert not normalizer._is_placeholder("Nancy Pelosi")


class TestStandardizeNames:
    """Tests for the standardize_names batch method."""

    def test_dry_run_no_writes(self, normalizer, mock_supabase):
        """Dry run should find but not apply name changes."""
        response = _make_response([
            {"id": "1", "first_name": "Hon. John", "last_name": "Smith", "full_name": "Hon. John Smith"},
        ])
        mock_supabase.table.return_value.select.return_value.limit.return_value.execute.return_value = response

        result = normalizer.standardize_names(dry_run=True)
        assert result["corrections"] == 1
        mock_supabase.table.return_value.update.assert_not_called()

    def test_skips_placeholder_names(self, normalizer, mock_supabase):
        """Placeholder names should be skipped."""
        response = _make_response([
            {"id": "1", "first_name": "Placeholder", "last_name": "Senator", "full_name": "Placeholder Senator"},
        ])
        mock_supabase.table.return_value.select.return_value.limit.return_value.execute.return_value = response

        result = normalizer.standardize_names(dry_run=True)
        assert result["corrections"] == 0

    def test_clean_names_already_ok(self, normalizer, mock_supabase):
        """Names without prefixes should not be changed."""
        response = _make_response([
            {"id": "1", "first_name": "John", "last_name": "Smith", "full_name": "John Smith"},
        ])
        mock_supabase.table.return_value.select.return_value.limit.return_value.execute.return_value = response

        result = normalizer.standardize_names(dry_run=True)
        assert result["corrections"] == 0


# ============================================================================
# State Backfill Tests
# ============================================================================


class TestStateExtraction:
    """Tests for state extraction from district field."""

    def test_extract_state_from_district(self, normalizer):
        assert normalizer._extract_state("CA12") == "CA"
        assert normalizer._extract_state("TX07") == "TX"
        assert normalizer._extract_state("NY01") == "NY"

    def test_no_state_from_invalid_district(self, normalizer):
        assert normalizer._extract_state("") is None
        assert normalizer._extract_state(None) is None
        assert normalizer._extract_state("California") is None
        assert normalizer._extract_state("12") is None

    def test_at_large_district(self, normalizer):
        """At-large districts like 'AK0' should still extract state."""
        assert normalizer._extract_state("AK0") == "AK"


class TestBackfillStateCountry:
    """Tests for the backfill_state_country batch method."""

    def _setup_backfill_mock(self, mock_supabase, data):
        """Set up the chained mock for backfill queries."""
        response = _make_response(data)
        # The query chain is: .select().is_().not_.is_().limit().execute()
        # MagicMock auto-creates intermediates, but we need to ensure the
        # final .execute() returns our response regardless of chain order
        chain = mock_supabase.table.return_value.select.return_value
        chain.is_.return_value.not_.return_value.is_.return_value.limit.return_value.execute.return_value = response
        # Also handle if not_ comes from the chain directly
        chain.is_.return_value.not_.is_.return_value.limit.return_value.execute.return_value = response

    def test_dry_run_no_writes(self, normalizer, mock_supabase):
        """Dry run should find but not apply state changes."""
        self._setup_backfill_mock(mock_supabase, [
            {"id": "1", "first_name": "A", "last_name": "B", "district": "CA12", "state_or_country": None},
        ])

        result = normalizer.backfill_state_country(dry_run=True)
        assert result["corrections"] == 1
        mock_supabase.table.return_value.update.assert_not_called()

    def test_skips_records_without_district(self, normalizer, mock_supabase):
        """Records without district data should be skipped."""
        self._setup_backfill_mock(mock_supabase, [
            {"id": "1", "first_name": "A", "last_name": "B", "district": None, "state_or_country": None},
            {"id": "2", "first_name": "C", "last_name": "D", "district": "", "state_or_country": None},
        ])

        result = normalizer.backfill_state_country(dry_run=True)
        assert result["corrections"] == 0

    def test_skips_non_extractable_districts(self, normalizer, mock_supabase):
        """Districts without state abbreviation should be skipped."""
        self._setup_backfill_mock(mock_supabase, [
            {"id": "1", "first_name": "A", "last_name": "B", "district": "California", "state_or_country": None},
        ])

        result = normalizer.backfill_state_country(dry_run=True)
        assert result["corrections"] == 0


# ============================================================================
# Orchestration Tests
# ============================================================================


class TestNormalizeAll:
    """Tests for the normalize_all orchestrator."""

    def test_runs_all_steps_by_default(self, normalizer, mock_supabase):
        """normalize_all should run roles, names, and state_backfill."""
        # Set up empty responses for all queries
        empty = _make_response([])
        mock_supabase.table.return_value.select.return_value.limit.return_value.execute.return_value = empty
        (mock_supabase.table.return_value.select.return_value
         .is_.return_value.not_.return_value.is_.return_value
         .limit.return_value.execute.return_value) = empty

        result = normalizer.normalize_all(dry_run=True)

        assert "roles" in result["results"]
        assert "names" in result["results"]
        assert "state_backfill" in result["results"]
        assert result["dry_run"] is True
        assert "duration_ms" in result

    def test_returns_combined_totals(self, normalizer, mock_supabase):
        """normalize_all should sum corrections across steps."""
        # Roles: 2 corrections
        role_data = [
            {"id": "1", "first_name": "A", "last_name": "B", "role": "Senate"},
            {"id": "2", "first_name": "C", "last_name": "D", "role": "House"},
        ]
        # Names: 1 correction
        name_data = [
            {"id": "3", "first_name": "Hon. E", "last_name": "F", "full_name": "Hon. E F"},
        ]

        call_count = [0]

        def mock_execute():
            call_count[0] += 1
            # First call is for roles, second for names, third for state_backfill
            if call_count[0] == 1:
                return _make_response(role_data)
            elif call_count[0] == 2:
                return _make_response(name_data)
            else:
                return _make_response([])

        mock_supabase.table.return_value.select.return_value.limit.return_value.execute = mock_execute
        (mock_supabase.table.return_value.select.return_value
         .is_.return_value.not_.return_value.is_.return_value
         .limit.return_value.execute) = mock_execute

        result = normalizer.normalize_all(dry_run=True)

        assert result["total_corrections"] == 3
        assert result["total_errors"] == 0


# ============================================================================
# Audit Trail Tests
# ============================================================================


class TestAuditTrail:
    """Tests for audit trail logging."""

    def test_log_correction_inserts_record(self, normalizer, mock_supabase):
        """_log_correction should insert into data_quality_corrections."""
        mock_supabase.table.return_value.insert.return_value.execute.return_value = _make_response([])

        correction_id = normalizer._log_correction(
            record_id="test-123",
            table_name="politicians",
            field_name="role",
            old_value="Senate",
            new_value="Senator",
            correction_type=CorrectionType.ROLE_NORMALIZATION,
        )

        assert correction_id is not None
        mock_supabase.table.assert_any_call("data_quality_corrections")

    def test_log_correction_handles_none_old_value(self, normalizer, mock_supabase):
        """_log_correction should handle None old values (for backfill)."""
        mock_supabase.table.return_value.insert.return_value.execute.return_value = _make_response([])

        correction_id = normalizer._log_correction(
            record_id="test-456",
            table_name="politicians",
            field_name="state_or_country",
            old_value=None,
            new_value="CA",
            correction_type=CorrectionType.STATE_BACKFILL,
        )

        assert correction_id is not None

    def test_log_correction_handles_db_error(self, normalizer, mock_supabase):
        """_log_correction should return None on database error."""
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("DB error")

        correction_id = normalizer._log_correction(
            record_id="test-789",
            table_name="politicians",
            field_name="role",
            old_value="old",
            new_value="new",
            correction_type=CorrectionType.ROLE_NORMALIZATION,
        )

        assert correction_id is None


# ============================================================================
# CorrectionType Enum Tests
# ============================================================================


class TestCorrectionTypes:
    """Verify the new correction type enum values exist."""

    def test_role_normalization_exists(self):
        assert CorrectionType.ROLE_NORMALIZATION.value == "role_normalization"

    def test_name_standardization_exists(self):
        assert CorrectionType.NAME_STANDARDIZATION.value == "name_standardization"

    def test_state_backfill_exists(self):
        assert CorrectionType.STATE_BACKFILL.value == "state_backfill"


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Edge case tests."""

    def test_no_supabase_returns_error(self):
        """Normalizer without Supabase should return error results."""
        with patch("app.services.politician_normalizer.get_supabase", return_value=None):
            n = PoliticianNormalizer()

        result = n.normalize_roles(dry_run=True)
        assert result["errors"] == 1

        result = n.standardize_names(dry_run=True)
        assert result["errors"] == 1

        result = n.backfill_state_country(dry_run=True)
        assert result["errors"] == 1

    def test_empty_database(self, normalizer, mock_supabase):
        """Should handle empty results gracefully."""
        empty = _make_response([])
        mock_supabase.table.return_value.select.return_value.limit.return_value.execute.return_value = empty
        (mock_supabase.table.return_value.select.return_value
         .is_.return_value.not_.return_value.is_.return_value
         .limit.return_value.execute.return_value) = empty

        result = normalizer.normalize_all(dry_run=True)
        assert result["total_corrections"] == 0
        assert result["total_errors"] == 0
