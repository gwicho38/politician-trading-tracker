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
