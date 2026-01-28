"""
Tests for Politician Deduplication Service (app/services/politician_dedup.py).

Tests:
- normalize_name() - Name normalization
- find_duplicates() - Find duplicate groups
- _pick_winner() - Pick best record to keep
- _count_disclosures() - Count disclosures for IDs
- merge_group() - Merge duplicate group
- process_all() - Process all duplicates
- preview() - Preview duplicates
"""

import pytest
from unittest.mock import MagicMock, patch


# =============================================================================
# normalize_name() Tests
# =============================================================================

class TestNormalizeName:
    """Tests for PoliticianDeduplicator.normalize_name() method."""

    def test_lowercases_name(self):
        """normalize_name() lowercases the name."""
        from app.services.politician_dedup import PoliticianDeduplicator

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        result = dedup.normalize_name("JOHN SMITH")

        assert result == "john smith"

    def test_removes_hon_prefix(self):
        """normalize_name() removes Hon. prefix."""
        from app.services.politician_dedup import PoliticianDeduplicator

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        result = dedup.normalize_name("Hon. John Smith")

        assert result == "john smith"

    def test_removes_honorable_prefix(self):
        """normalize_name() removes Honorable prefix."""
        from app.services.politician_dedup import PoliticianDeduplicator

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        result = dedup.normalize_name("Honorable John Smith")

        assert result == "john smith"

    def test_removes_representative_prefix(self):
        """normalize_name() removes Representative prefix."""
        from app.services.politician_dedup import PoliticianDeduplicator

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        result = dedup.normalize_name("Representative John Smith")

        assert result == "john smith"

    def test_removes_rep_prefix(self):
        """normalize_name() removes Rep. prefix."""
        from app.services.politician_dedup import PoliticianDeduplicator

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        result = dedup.normalize_name("Rep. John Smith")

        assert result == "john smith"

    def test_removes_senator_prefix(self):
        """normalize_name() removes Senator prefix."""
        from app.services.politician_dedup import PoliticianDeduplicator

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        result = dedup.normalize_name("Senator John Smith")

        assert result == "john smith"

    def test_removes_sen_prefix(self):
        """normalize_name() removes Sen. prefix."""
        from app.services.politician_dedup import PoliticianDeduplicator

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        result = dedup.normalize_name("Sen. John Smith")

        assert result == "john smith"

    def test_removes_dr_prefix(self):
        """normalize_name() removes Dr. prefix."""
        from app.services.politician_dedup import PoliticianDeduplicator

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        result = dedup.normalize_name("Dr. John Smith")

        assert result == "john smith"

    def test_removes_jr_suffix(self):
        """normalize_name() removes Jr. suffix."""
        from app.services.politician_dedup import PoliticianDeduplicator

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        result = dedup.normalize_name("John Smith Jr.")

        assert result == "john smith"

    def test_removes_sr_suffix(self):
        """normalize_name() removes Sr. suffix."""
        from app.services.politician_dedup import PoliticianDeduplicator

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        result = dedup.normalize_name("John Smith Sr.")

        assert result == "john smith"

    def test_removes_iii_suffix(self):
        """normalize_name() removes III suffix."""
        from app.services.politician_dedup import PoliticianDeduplicator

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        result = dedup.normalize_name("John Smith III")

        assert result == "john smith"

    def test_removes_punctuation(self):
        """normalize_name() removes punctuation."""
        from app.services.politician_dedup import PoliticianDeduplicator

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        result = dedup.normalize_name("John O'Brien-Smith")

        assert result == "john obriensmith"

    def test_collapses_multiple_spaces(self):
        """normalize_name() collapses multiple spaces."""
        from app.services.politician_dedup import PoliticianDeduplicator

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        result = dedup.normalize_name("John   Michael   Smith")

        assert result == "john michael smith"

    def test_returns_empty_for_none(self):
        """normalize_name() returns empty string for None."""
        from app.services.politician_dedup import PoliticianDeduplicator

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        result = dedup.normalize_name(None)

        assert result == ""

    def test_returns_empty_for_empty_string(self):
        """normalize_name() returns empty string for empty input."""
        from app.services.politician_dedup import PoliticianDeduplicator

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        result = dedup.normalize_name("")

        assert result == ""


# =============================================================================
# find_duplicates() Tests
# =============================================================================

class TestFindDuplicates:
    """Tests for PoliticianDeduplicator.find_duplicates() method."""

    def test_returns_empty_list_when_no_supabase(self):
        """find_duplicates() returns empty list when no Supabase client."""
        from app.services.politician_dedup import PoliticianDeduplicator

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        result = dedup.find_duplicates()

        assert result == []

    def test_returns_empty_list_when_no_politicians(self):
        """find_duplicates() returns empty list when no politicians."""
        from app.services.politician_dedup import PoliticianDeduplicator

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.range.return_value.execute.return_value = mock_response

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        result = dedup.find_duplicates()

        assert result == []

    def test_finds_duplicate_group(self):
        """find_duplicates() finds groups with duplicate names."""
        from app.services.politician_dedup import PoliticianDeduplicator

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {"id": "1", "full_name": "John Smith", "party": "D", "state": "CA", "chamber": "House", "created_at": "2024-01-01"},
            {"id": "2", "full_name": "Hon. John Smith", "party": None, "state": None, "chamber": None, "created_at": "2024-01-02"},
        ]
        mock_supabase.table.return_value.select.return_value.range.return_value.execute.return_value = mock_response

        # Mock count for disclosures
        mock_count_response = MagicMock()
        mock_count_response.count = 0
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_count_response

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        result = dedup.find_duplicates()

        assert len(result) == 1
        assert result[0].normalized_name == "john smith"
        assert len(result[0].records) == 2

    def test_respects_limit(self):
        """find_duplicates() respects the limit parameter."""
        from app.services.politician_dedup import PoliticianDeduplicator

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {"id": "1", "full_name": "John Smith", "party": "D", "state": "CA", "chamber": "House", "created_at": "2024-01-01"},
            {"id": "2", "full_name": "John Smith Jr.", "party": None, "state": None, "chamber": None, "created_at": "2024-01-02"},
            {"id": "3", "full_name": "Jane Doe", "party": "R", "state": "TX", "chamber": "Senate", "created_at": "2024-01-01"},
            {"id": "4", "full_name": "Jane Doe", "party": None, "state": None, "chamber": None, "created_at": "2024-01-02"},
        ]
        mock_supabase.table.return_value.select.return_value.range.return_value.execute.return_value = mock_response

        mock_count_response = MagicMock()
        mock_count_response.count = 0
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_count_response

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        result = dedup.find_duplicates(limit=1)

        assert len(result) == 1

    def test_handles_exception(self):
        """find_duplicates() handles exceptions gracefully."""
        from app.services.politician_dedup import PoliticianDeduplicator

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.side_effect = Exception("DB error")

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        result = dedup.find_duplicates()

        assert result == []


# =============================================================================
# _pick_winner() Tests
# =============================================================================

class TestPickWinner:
    """Tests for PoliticianDeduplicator._pick_winner() method."""

    def test_picks_record_with_party(self):
        """_pick_winner() picks record with party data."""
        from app.services.politician_dedup import PoliticianDeduplicator

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        records = [
            {"id": "1", "full_name": "John Smith", "party": None, "state": None, "chamber": None, "created_at": "2024-01-01"},
            {"id": "2", "full_name": "John Smith", "party": "D", "state": None, "chamber": None, "created_at": "2024-01-02"},
        ]

        winner = dedup._pick_winner(records)

        assert winner["id"] == "2"

    def test_picks_record_with_state(self):
        """_pick_winner() picks record with state data."""
        from app.services.politician_dedup import PoliticianDeduplicator

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        records = [
            {"id": "1", "full_name": "John Smith", "party": None, "state": None, "chamber": None, "created_at": "2024-01-01"},
            {"id": "2", "full_name": "John Smith", "party": None, "state": "CA", "chamber": None, "created_at": "2024-01-02"},
        ]

        winner = dedup._pick_winner(records)

        assert winner["id"] == "2"

    def test_picks_record_with_chamber(self):
        """_pick_winner() picks record with chamber data."""
        from app.services.politician_dedup import PoliticianDeduplicator

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        records = [
            {"id": "1", "full_name": "John Smith", "party": None, "state": None, "chamber": None, "created_at": "2024-01-01"},
            {"id": "2", "full_name": "John Smith", "party": None, "state": None, "chamber": "House", "created_at": "2024-01-02"},
        ]

        winner = dedup._pick_winner(records)

        assert winner["id"] == "2"

    def test_picks_longer_name_when_equal(self):
        """_pick_winner() picks longer name when other fields equal."""
        from app.services.politician_dedup import PoliticianDeduplicator

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        records = [
            {"id": "1", "full_name": "John Smith", "party": None, "state": None, "chamber": None, "created_at": "2024-01-02"},
            {"id": "2", "full_name": "John Michael Smith", "party": None, "state": None, "chamber": None, "created_at": "2024-01-02"},
        ]

        winner = dedup._pick_winner(records)

        assert winner["id"] == "2"


# =============================================================================
# _count_disclosures() Tests
# =============================================================================

class TestCountDisclosures:
    """Tests for PoliticianDeduplicator._count_disclosures() method."""

    def test_returns_zero_when_no_supabase(self):
        """_count_disclosures() returns 0 when no Supabase client."""
        from app.services.politician_dedup import PoliticianDeduplicator

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        result = dedup._count_disclosures(["id1", "id2"])

        assert result == 0

    def test_returns_zero_for_empty_ids(self):
        """_count_disclosures() returns 0 for empty ID list."""
        from app.services.politician_dedup import PoliticianDeduplicator

        mock_supabase = MagicMock()

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        result = dedup._count_disclosures([])

        assert result == 0

    def test_counts_disclosures_for_ids(self):
        """_count_disclosures() counts disclosures for given IDs."""
        from app.services.politician_dedup import PoliticianDeduplicator

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.count = 5
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        result = dedup._count_disclosures(["id1", "id2"])

        assert result == 10  # 5 for each ID

    def test_handles_exception(self):
        """_count_disclosures() handles exceptions gracefully."""
        from app.services.politician_dedup import PoliticianDeduplicator

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.side_effect = Exception("DB error")

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        result = dedup._count_disclosures(["id1"])

        assert result == 0


# =============================================================================
# merge_group() Tests
# =============================================================================

class TestMergeGroup:
    """Tests for PoliticianDeduplicator.merge_group() method."""

    def test_returns_error_when_no_supabase(self):
        """merge_group() returns error when no Supabase client."""
        from app.services.politician_dedup import PoliticianDeduplicator, DuplicateGroup

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        group = DuplicateGroup(
            normalized_name="john smith",
            records=[],
            winner_id="1",
            loser_ids=["2"],
            disclosures_to_update=0
        )

        result = dedup.merge_group(group)

        assert result["status"] == "error"
        assert "No database connection" in result["message"]

    def test_dry_run_returns_preview(self):
        """merge_group() with dry_run returns preview without changes."""
        from app.services.politician_dedup import PoliticianDeduplicator, DuplicateGroup

        mock_supabase = MagicMock()

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        group = DuplicateGroup(
            normalized_name="john smith",
            records=[],
            winner_id="1",
            loser_ids=["2", "3"],
            disclosures_to_update=5
        )

        result = dedup.merge_group(group, dry_run=True)

        assert result["status"] == "dry_run"
        assert result["winner_id"] == "1"
        assert result["losers_merged"] == 2
        assert result["disclosures_to_update"] == 5

    def test_handles_exception(self):
        """merge_group() handles exceptions gracefully."""
        from app.services.politician_dedup import PoliticianDeduplicator, DuplicateGroup

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.side_effect = Exception("DB error")

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        group = DuplicateGroup(
            normalized_name="john smith",
            records=[],
            winner_id="1",
            loser_ids=["2"],
            disclosures_to_update=0
        )

        result = dedup.merge_group(group)

        assert result["status"] == "error"


# =============================================================================
# process_all() Tests
# =============================================================================

class TestProcessAll:
    """Tests for PoliticianDeduplicator.process_all() method."""

    def test_returns_zero_when_no_duplicates(self):
        """process_all() returns zero counts when no duplicates."""
        from app.services.politician_dedup import PoliticianDeduplicator

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.range.return_value.execute.return_value = mock_response

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        result = dedup.process_all()

        assert result["processed"] == 0
        assert result["merged"] == 0
        assert result["disclosures_updated"] == 0
        assert result["errors"] == 0

    def test_processes_with_dry_run(self):
        """process_all() processes duplicates in dry_run mode."""
        from app.services.politician_dedup import PoliticianDeduplicator

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {"id": "1", "full_name": "John Smith", "party": "D", "state": "CA", "chamber": "House", "created_at": "2024-01-01"},
            {"id": "2", "full_name": "John Smith", "party": None, "state": None, "chamber": None, "created_at": "2024-01-02"},
        ]
        mock_supabase.table.return_value.select.return_value.range.return_value.execute.return_value = mock_response

        mock_count_response = MagicMock()
        mock_count_response.count = 0
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_count_response

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        result = dedup.process_all(dry_run=True)

        assert result["processed"] == 1
        assert result["dry_run"] is True


# =============================================================================
# preview() Tests
# =============================================================================

class TestPreview:
    """Tests for PoliticianDeduplicator.preview() method."""

    def test_returns_empty_when_no_duplicates(self):
        """preview() returns empty when no duplicates."""
        from app.services.politician_dedup import PoliticianDeduplicator

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.range.return_value.execute.return_value = mock_response

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        result = dedup.preview()

        assert result["duplicate_groups"] == 0
        assert result["total_duplicates"] == 0
        assert result["groups"] == []

    def test_returns_preview_with_duplicates(self):
        """preview() returns preview data with duplicates."""
        from app.services.politician_dedup import PoliticianDeduplicator

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {"id": "1", "full_name": "John Smith", "party": "D", "state": "CA", "chamber": "House", "created_at": "2024-01-01"},
            {"id": "2", "full_name": "John Smith Jr.", "party": None, "state": None, "chamber": None, "created_at": "2024-01-02"},
        ]
        mock_supabase.table.return_value.select.return_value.range.return_value.execute.return_value = mock_response

        mock_count_response = MagicMock()
        mock_count_response.count = 3
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_count_response

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        result = dedup.preview()

        assert result["duplicate_groups"] == 1
        assert result["total_duplicates"] == 1  # 1 loser in the group
        assert len(result["groups"]) == 1
        assert result["groups"][0]["normalized_name"] == "john smith"

    def test_respects_limit(self):
        """preview() respects the limit parameter."""
        from app.services.politician_dedup import PoliticianDeduplicator

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {"id": "1", "full_name": "John Smith", "party": "D", "state": "CA", "chamber": "House", "created_at": "2024-01-01"},
            {"id": "2", "full_name": "John Smith", "party": None, "state": None, "chamber": None, "created_at": "2024-01-02"},
            {"id": "3", "full_name": "Jane Doe", "party": "R", "state": "TX", "chamber": "Senate", "created_at": "2024-01-01"},
            {"id": "4", "full_name": "Jane Doe", "party": None, "state": None, "chamber": None, "created_at": "2024-01-02"},
        ]
        mock_supabase.table.return_value.select.return_value.range.return_value.execute.return_value = mock_response

        mock_count_response = MagicMock()
        mock_count_response.count = 0
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_count_response

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        result = dedup.preview(limit=1)

        assert len(result["groups"]) == 1


# =============================================================================
# merge_group() Actual Merge Tests (Lines 257-301)
# =============================================================================

class TestMergeGroupActual:
    """Tests for PoliticianDeduplicator.merge_group() actual merge logic."""

    def test_merge_success_updates_winner_with_loser_data(self):
        """merge_group() merges data from losers into winner."""
        from app.services.politician_dedup import PoliticianDeduplicator, DuplicateGroup

        mock_supabase = MagicMock()

        # Winner query - missing some fields
        winner_data = {
            "id": "winner-1",
            "full_name": "John Smith",
            "party": None,  # Missing
            "state": "CA",
            "chamber": None,  # Missing
            "bioguide_id": None  # Missing
        }

        # Loser 1 query - has party and chamber
        loser1_data = {
            "id": "loser-1",
            "full_name": "John Smith",
            "party": "D",
            "state": None,
            "chamber": "House",
            "bioguide_id": None
        }

        # Loser 2 query - has bioguide_id
        loser2_data = {
            "id": "loser-2",
            "full_name": "John Smith",
            "party": None,
            "state": None,
            "chamber": None,
            "bioguide_id": "S001234"
        }

        # Create a simple mock that returns different data based on call sequence
        call_count = [0]
        data_sequence = [winner_data, loser1_data, loser2_data]

        def select_side_effect(*args):
            eq_mock = MagicMock()
            single_mock = MagicMock()
            response = MagicMock()

            idx = min(call_count[0], len(data_sequence) - 1)
            response.data = data_sequence[idx]
            call_count[0] += 1

            single_mock.execute.return_value = response
            eq_mock.eq.return_value.single.return_value = single_mock
            return eq_mock

        mock_supabase.table.return_value.select.side_effect = select_side_effect

        # Disclosure update response
        update_response = MagicMock()
        update_response.data = [{"id": "disc-1"}, {"id": "disc-2"}]
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = update_response
        mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock()

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        group = DuplicateGroup(
            normalized_name="john smith",
            records=[],
            winner_id="winner-1",
            loser_ids=["loser-1", "loser-2"],
            disclosures_to_update=2
        )

        result = dedup.merge_group(group, dry_run=False)

        assert result["status"] == "success"
        assert result["winner_id"] == "winner-1"
        assert result["losers_merged"] == 2

    def test_merge_success_no_update_needed(self):
        """merge_group() success when winner already has all data."""
        from app.services.politician_dedup import PoliticianDeduplicator, DuplicateGroup

        mock_supabase = MagicMock()

        # Winner already complete
        winner_response = MagicMock()
        winner_response.data = {
            "id": "winner-1",
            "full_name": "John Smith",
            "party": "D",
            "state": "CA",
            "chamber": "House",
            "bioguide_id": "S001234"
        }

        # Loser has nothing new
        loser_response = MagicMock()
        loser_response.data = {
            "id": "loser-1",
            "full_name": "John Smith",
            "party": None,
            "state": None,
            "chamber": None,
            "bioguide_id": None
        }

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        call_count = [0]
        def select_side_effect(*args):
            call_count[0] += 1
            eq_mock = MagicMock()
            single_mock = MagicMock()
            if call_count[0] == 1:
                single_mock.execute.return_value = winner_response
            else:
                single_mock.execute.return_value = loser_response
            eq_mock.eq.return_value.single.return_value = single_mock
            return eq_mock

        mock_table.select.side_effect = select_side_effect

        # Disclosure update
        update_response = MagicMock()
        update_response.data = []
        mock_table.update.return_value.eq.return_value.execute.return_value = update_response
        mock_table.delete.return_value.eq.return_value.execute.return_value = MagicMock()

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        group = DuplicateGroup(
            normalized_name="john smith",
            records=[],
            winner_id="winner-1",
            loser_ids=["loser-1"],
            disclosures_to_update=0
        )

        result = dedup.merge_group(group, dry_run=False)

        assert result["status"] == "success"
        # Update should NOT be called since no fields need updating
        # (The winner already has all data)

    def test_merge_counts_updated_disclosures(self):
        """merge_group() accurately counts updated disclosures."""
        from app.services.politician_dedup import PoliticianDeduplicator, DuplicateGroup

        mock_supabase = MagicMock()

        winner_response = MagicMock()
        winner_response.data = {"id": "winner-1", "full_name": "John", "party": "D", "state": "CA", "chamber": "House", "bioguide_id": None}

        loser_response = MagicMock()
        loser_response.data = {"id": "loser-1", "full_name": "John", "party": None, "state": None, "chamber": None, "bioguide_id": None}

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        call_count = [0]
        def select_side_effect(*args):
            call_count[0] += 1
            eq_mock = MagicMock()
            single_mock = MagicMock()
            if call_count[0] == 1:
                single_mock.execute.return_value = winner_response
            else:
                single_mock.execute.return_value = loser_response
            eq_mock.eq.return_value.single.return_value = single_mock
            return eq_mock

        mock_table.select.side_effect = select_side_effect

        # Disclosure update returns 3 records
        update_response = MagicMock()
        update_response.data = [{"id": "d1"}, {"id": "d2"}, {"id": "d3"}]
        mock_table.update.return_value.eq.return_value.execute.return_value = update_response
        mock_table.delete.return_value.eq.return_value.execute.return_value = MagicMock()

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        group = DuplicateGroup(
            normalized_name="john",
            records=[],
            winner_id="winner-1",
            loser_ids=["loser-1"],
            disclosures_to_update=3
        )

        result = dedup.merge_group(group, dry_run=False)

        assert result["status"] == "success"
        assert result["disclosures_updated"] == 3

    def test_merge_loser_data_none(self):
        """merge_group() handles loser with None data response."""
        from app.services.politician_dedup import PoliticianDeduplicator, DuplicateGroup

        mock_supabase = MagicMock()

        winner_response = MagicMock()
        winner_response.data = {"id": "winner-1", "full_name": "John", "party": "D", "state": "CA", "chamber": "House", "bioguide_id": None}

        loser_response = MagicMock()
        loser_response.data = None  # No data for loser

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        call_count = [0]
        def select_side_effect(*args):
            call_count[0] += 1
            eq_mock = MagicMock()
            single_mock = MagicMock()
            if call_count[0] == 1:
                single_mock.execute.return_value = winner_response
            else:
                single_mock.execute.return_value = loser_response
            eq_mock.eq.return_value.single.return_value = single_mock
            return eq_mock

        mock_table.select.side_effect = select_side_effect

        update_response = MagicMock()
        update_response.data = []
        mock_table.update.return_value.eq.return_value.execute.return_value = update_response
        mock_table.delete.return_value.eq.return_value.execute.return_value = MagicMock()

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        group = DuplicateGroup(
            normalized_name="john",
            records=[],
            winner_id="winner-1",
            loser_ids=["loser-1"],
            disclosures_to_update=0
        )

        result = dedup.merge_group(group, dry_run=False)

        assert result["status"] == "success"


# =============================================================================
# process_all() Extended Tests (Lines 343-349)
# =============================================================================

class TestProcessAllExtended:
    """Extended tests for PoliticianDeduplicator.process_all() success/error paths."""

    def test_process_all_counts_successful_merges(self):
        """process_all() counts successful merges and disclosures."""
        from app.services.politician_dedup import PoliticianDeduplicator

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {"id": "1", "full_name": "John Smith", "party": "D", "state": "CA", "chamber": "House", "created_at": "2024-01-01"},
            {"id": "2", "full_name": "John Smith", "party": None, "state": None, "chamber": None, "created_at": "2024-01-02"},
        ]
        mock_supabase.table.return_value.select.return_value.range.return_value.execute.return_value = mock_response

        # For _count_disclosures
        mock_count_response = MagicMock()
        mock_count_response.count = 5
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_count_response

        # For the actual merge
        winner_response = MagicMock()
        winner_response.data = {"id": "1", "full_name": "John Smith", "party": "D", "state": "CA", "chamber": "House", "bioguide_id": None}

        loser_response = MagicMock()
        loser_response.data = {"id": "2", "full_name": "John Smith", "party": None, "state": None, "chamber": None, "bioguide_id": None}

        update_response = MagicMock()
        update_response.data = [{"id": "d1"}, {"id": "d2"}]

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        # Mock merge_group to return success
        with patch.object(dedup, 'merge_group') as mock_merge:
            mock_merge.return_value = {
                "status": "success",
                "normalized_name": "john smith",
                "winner_id": "1",
                "losers_merged": 1,
                "disclosures_updated": 2
            }

            result = dedup.process_all(dry_run=False)

        assert result["processed"] == 1
        assert result["merged"] == 1
        assert result["disclosures_updated"] == 2
        assert result["errors"] == 0

    def test_process_all_counts_errors(self):
        """process_all() counts error results."""
        from app.services.politician_dedup import PoliticianDeduplicator

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {"id": "1", "full_name": "John Smith", "party": "D", "state": "CA", "chamber": "House", "created_at": "2024-01-01"},
            {"id": "2", "full_name": "John Smith", "party": None, "state": None, "chamber": None, "created_at": "2024-01-02"},
        ]
        mock_supabase.table.return_value.select.return_value.range.return_value.execute.return_value = mock_response

        mock_count_response = MagicMock()
        mock_count_response.count = 0
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_count_response

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        # Mock merge_group to return error
        with patch.object(dedup, 'merge_group') as mock_merge:
            mock_merge.return_value = {
                "status": "error",
                "normalized_name": "john smith",
                "message": "DB connection failed"
            }

            result = dedup.process_all(dry_run=False)

        assert result["processed"] == 1
        assert result["merged"] == 0
        assert result["errors"] == 1

    def test_process_all_handles_mixed_results(self):
        """process_all() handles mix of success, dry_run, and errors."""
        from app.services.politician_dedup import PoliticianDeduplicator

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {"id": "1", "full_name": "John Smith", "party": "D", "state": "CA", "chamber": "House", "created_at": "2024-01-01"},
            {"id": "2", "full_name": "John Smith", "party": None, "state": None, "chamber": None, "created_at": "2024-01-02"},
            {"id": "3", "full_name": "Jane Doe", "party": "R", "state": "TX", "chamber": "Senate", "created_at": "2024-01-01"},
            {"id": "4", "full_name": "Jane Doe", "party": None, "state": None, "chamber": None, "created_at": "2024-01-02"},
        ]
        mock_supabase.table.return_value.select.return_value.range.return_value.execute.return_value = mock_response

        mock_count_response = MagicMock()
        mock_count_response.count = 0
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_count_response

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        call_count = [0]
        def merge_side_effect(group, dry_run=False):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"status": "success", "disclosures_updated": 5}
            else:
                return {"status": "error", "message": "Failed"}

        with patch.object(dedup, 'merge_group', side_effect=merge_side_effect):
            result = dedup.process_all(dry_run=False)

        assert result["processed"] == 2
        assert result["merged"] == 1
        assert result["errors"] == 1
        assert result["disclosures_updated"] == 5


# =============================================================================
# find_duplicates() Extended Tests (Lines 136, 154)
# =============================================================================

class TestFindDuplicatesExtended:
    """Extended tests for find_duplicates pagination and filtering."""

    def test_pagination_increments_offset(self):
        """find_duplicates() increments offset for pagination."""
        from app.services.politician_dedup import PoliticianDeduplicator

        mock_supabase = MagicMock()

        # First page - full page size (triggers pagination)
        first_page = MagicMock()
        first_page.data = [{"id": str(i), "full_name": f"Person {i}", "party": "D", "state": "CA", "chamber": "House", "created_at": "2024-01-01"} for i in range(1000)]

        # Second page - partial (ends pagination)
        second_page = MagicMock()
        second_page.data = [{"id": "1001", "full_name": "Person 1001", "party": "D", "state": "CA", "chamber": "House", "created_at": "2024-01-01"}]

        call_count = [0]
        def range_side_effect(start, end):
            call_count[0] += 1
            exec_mock = MagicMock()
            if call_count[0] == 1:
                exec_mock.execute.return_value = first_page
            else:
                exec_mock.execute.return_value = second_page
            return exec_mock

        mock_supabase.table.return_value.select.return_value.range = range_side_effect

        # For _count_disclosures
        mock_count_response = MagicMock()
        mock_count_response.count = 0
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_count_response

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        result = dedup.find_duplicates()

        # Should have called range twice (pagination)
        assert call_count[0] == 2

    def test_skips_groups_with_single_record(self):
        """find_duplicates() skips groups with only 1 record (not duplicates)."""
        from app.services.politician_dedup import PoliticianDeduplicator

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            # John Smith appears twice - is a duplicate
            {"id": "1", "full_name": "John Smith", "party": "D", "state": "CA", "chamber": "House", "created_at": "2024-01-01"},
            {"id": "2", "full_name": "John Smith", "party": None, "state": None, "chamber": None, "created_at": "2024-01-02"},
            # Jane Doe appears once - NOT a duplicate (should be skipped)
            {"id": "3", "full_name": "Jane Doe", "party": "R", "state": "TX", "chamber": "Senate", "created_at": "2024-01-01"},
        ]
        mock_supabase.table.return_value.select.return_value.range.return_value.execute.return_value = mock_response

        mock_count_response = MagicMock()
        mock_count_response.count = 0
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_count_response

        with patch.object(PoliticianDeduplicator, '_get_supabase', return_value=mock_supabase):
            dedup = PoliticianDeduplicator()

        result = dedup.find_duplicates()

        # Only John Smith group should be returned (Jane Doe skipped)
        assert len(result) == 1
        assert result[0].normalized_name == "john smith"


# =============================================================================
# _get_supabase() Tests (Line 54)
# =============================================================================

class TestGetSupabase:
    """Tests for _get_supabase method."""

    def test_get_supabase_returns_client(self):
        """_get_supabase() returns client from get_supabase function."""
        from app.services.politician_dedup import PoliticianDeduplicator

        mock_client = MagicMock()

        with patch('app.services.politician_dedup.get_supabase', return_value=mock_client):
            dedup = PoliticianDeduplicator()

        assert dedup.supabase == mock_client

    def test_get_supabase_handles_none(self):
        """_get_supabase() handles None return."""
        from app.services.politician_dedup import PoliticianDeduplicator

        with patch('app.services.politician_dedup.get_supabase', return_value=None):
            dedup = PoliticianDeduplicator()

        assert dedup.supabase is None
