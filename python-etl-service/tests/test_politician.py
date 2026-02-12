"""
Tests for politician utilities (app/lib/politician.py).

Tests:
- find_or_create_politician() - Find existing or create new politician
"""

import pytest
from unittest.mock import MagicMock, call


# =============================================================================
# find_or_create_politician() Tests
# =============================================================================

class TestFindOrCreatePolitician:
    """Tests for find_or_create_politician() function."""

    @pytest.fixture
    def mock_supabase_empty(self):
        """Mock Supabase client with no existing politicians."""
        client = MagicMock()
        table_mock = MagicMock()

        # No politician found
        table_mock.select.return_value.match.return_value.execute.return_value = MagicMock(
            data=[]
        )
        table_mock.select.return_value.ilike.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        # Insert succeeds
        table_mock.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "new-uuid-123"}]
        )

        client.table.return_value = table_mock
        return client

    @pytest.fixture
    def mock_supabase_existing(self):
        """Mock Supabase client with existing politician."""
        client = MagicMock()
        table_mock = MagicMock()

        # Politician found
        table_mock.select.return_value.match.return_value.execute.return_value = MagicMock(
            data=[{"id": "existing-uuid-456"}]
        )
        table_mock.select.return_value.ilike.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "existing-uuid-456"}]
        )

        client.table.return_value = table_mock
        return client

    # -------------------------------------------------------------------------
    # Basic Functionality Tests
    # -------------------------------------------------------------------------

    def test_finds_existing_house_politician(self, mock_supabase_existing):
        """find_or_create_politician() returns existing House politician."""
        from app.lib.politician import find_or_create_politician

        result = find_or_create_politician(
            mock_supabase_existing,
            first_name="Nancy",
            last_name="Pelosi",
            chamber="house",
        )

        assert result == "existing-uuid-456"

    def test_finds_existing_senate_politician(self, mock_supabase_existing):
        """find_or_create_politician() returns existing Senate politician."""
        from app.lib.politician import find_or_create_politician

        result = find_or_create_politician(
            mock_supabase_existing,
            name="John Smith",
            chamber="senate",
        )

        assert result == "existing-uuid-456"

    def test_creates_new_house_politician(self, mock_supabase_empty):
        """find_or_create_politician() creates new House politician."""
        from app.lib.politician import find_or_create_politician

        result = find_or_create_politician(
            mock_supabase_empty,
            first_name="Jane",
            last_name="Doe",
            chamber="house",
            state="CA",
            district="CA-12",
        )

        assert result == "new-uuid-123"
        table_mock = mock_supabase_empty.table.return_value
        table_mock.insert.assert_called_once()

    def test_creates_new_senate_politician(self, mock_supabase_empty):
        """find_or_create_politician() creates new Senate politician."""
        from app.lib.politician import find_or_create_politician

        result = find_or_create_politician(
            mock_supabase_empty,
            name="John Smith",
            chamber="senate",
            state="NY",
        )

        assert result == "new-uuid-123"
        table_mock = mock_supabase_empty.table.return_value
        table_mock.insert.assert_called_once()

    # -------------------------------------------------------------------------
    # Name Handling Tests
    # -------------------------------------------------------------------------

    def test_returns_none_for_empty_name(self, mock_supabase_empty):
        """find_or_create_politician() returns None for empty name."""
        from app.lib.politician import find_or_create_politician

        result = find_or_create_politician(
            mock_supabase_empty,
            name="",
            chamber="senate",
        )

        assert result is None

    def test_returns_none_for_unknown_name(self, mock_supabase_empty):
        """find_or_create_politician() returns None for 'Unknown' name."""
        from app.lib.politician import find_or_create_politician

        result = find_or_create_politician(
            mock_supabase_empty,
            name="Unknown",
            chamber="senate",
        )

        assert result is None

    def test_builds_name_from_first_and_last(self, mock_supabase_empty):
        """find_or_create_politician() builds name from first_name + last_name."""
        from app.lib.politician import find_or_create_politician

        result = find_or_create_politician(
            mock_supabase_empty,
            first_name="Jane",
            last_name="Doe",
            chamber="house",
        )

        assert result == "new-uuid-123"
        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]
        assert politician_data["name"] == "Jane Doe"

    def test_removes_sen_prefix(self, mock_supabase_empty):
        """find_or_create_politician() removes 'Sen.' prefix from name."""
        from app.lib.politician import find_or_create_politician

        result = find_or_create_politician(
            mock_supabase_empty,
            name="Sen. John Smith",
            chamber="senate",
        )

        assert result == "new-uuid-123"
        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]
        assert "Sen." not in politician_data["name"]

    def test_removes_senator_prefix(self, mock_supabase_empty):
        """find_or_create_politician() removes 'Senator' prefix."""
        from app.lib.politician import find_or_create_politician

        find_or_create_politician(
            mock_supabase_empty,
            name="Senator Jane Doe",
            chamber="senate",
        )

        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]
        assert "Senator" not in politician_data["name"]

    def test_removes_rep_prefix(self, mock_supabase_empty):
        """find_or_create_politician() removes 'Rep.' prefix."""
        from app.lib.politician import find_or_create_politician

        find_or_create_politician(
            mock_supabase_empty,
            name="Rep. John Doe",
            chamber="house",
        )

        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]
        assert "Rep." not in politician_data["name"]

    def test_removes_hon_prefix(self, mock_supabase_empty):
        """find_or_create_politician() removes 'Hon.' prefix."""
        from app.lib.politician import find_or_create_politician

        find_or_create_politician(
            mock_supabase_empty,
            name="Hon. Jane Smith",
            chamber="house",
        )

        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]
        assert "Hon." not in politician_data["name"]

    def test_strips_whitespace(self, mock_supabase_empty):
        """find_or_create_politician() strips whitespace from name."""
        from app.lib.politician import find_or_create_politician

        find_or_create_politician(
            mock_supabase_empty,
            name="  John Smith  ",
            chamber="senate",
        )

        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]
        assert politician_data["name"] == "John Smith"

    # -------------------------------------------------------------------------
    # Role/Chamber Tests
    # -------------------------------------------------------------------------

    def test_sets_representative_role_for_house(self, mock_supabase_empty):
        """find_or_create_politician() sets role='Representative' for house."""
        from app.lib.politician import find_or_create_politician

        find_or_create_politician(
            mock_supabase_empty,
            name="John Doe",
            chamber="house",
        )

        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]
        assert politician_data["role"] == "Representative"

    def test_sets_senator_role_for_senate(self, mock_supabase_empty):
        """find_or_create_politician() sets role='Senator' for senate."""
        from app.lib.politician import find_or_create_politician

        find_or_create_politician(
            mock_supabase_empty,
            name="Jane Smith",
            chamber="senate",
        )

        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]
        assert politician_data["role"] == "Senator"

    def test_sets_mep_role_for_eu_parliament(self, mock_supabase_empty):
        """find_or_create_politician() sets role='MEP' for eu_parliament."""
        from app.lib.politician import find_or_create_politician

        find_or_create_politician(
            mock_supabase_empty,
            name="Mika AALTOLA",
            chamber="eu_parliament",
            state="Finland",
        )

        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]
        assert politician_data["role"] == "MEP"
        assert politician_data["chamber"] == "eu_parliament"

    def test_sets_state_legislator_role_for_california(self, mock_supabase_empty):
        """find_or_create_politician() sets role='State Legislator' for california."""
        from app.lib.politician import find_or_create_politician

        find_or_create_politician(
            mock_supabase_empty,
            name="Jane Doe",
            chamber="california",
        )

        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]
        assert politician_data["role"] == "State Legislator"

    def test_unknown_chamber_defaults_to_representative(self, mock_supabase_empty):
        """find_or_create_politician() defaults to 'Representative' for unknown chambers."""
        from app.lib.politician import find_or_create_politician

        find_or_create_politician(
            mock_supabase_empty,
            name="Jane Doe",
            chamber="some_future_chamber",
        )

        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]
        assert politician_data["role"] == "Representative"

    def test_sets_chamber_field(self, mock_supabase_empty):
        """find_or_create_politician() sets chamber field."""
        from app.lib.politician import find_or_create_politician

        find_or_create_politician(
            mock_supabase_empty,
            name="John Smith",
            chamber="senate",
        )

        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]
        assert politician_data["chamber"] == "senate"

    # -------------------------------------------------------------------------
    # State/District Tests
    # -------------------------------------------------------------------------

    def test_sets_state_for_house(self, mock_supabase_empty):
        """find_or_create_politician() sets state for House politician."""
        from app.lib.politician import find_or_create_politician

        find_or_create_politician(
            mock_supabase_empty,
            name="John Doe",
            chamber="house",
            state="CA",
            district="CA-12",
        )

        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]
        assert politician_data["state"] == "CA"
        assert politician_data["district"] == "CA-12"

    def test_sets_state_for_senate(self, mock_supabase_empty):
        """find_or_create_politician() sets state for Senate politician."""
        from app.lib.politician import find_or_create_politician

        find_or_create_politician(
            mock_supabase_empty,
            name="Jane Smith",
            chamber="senate",
            state="NY",
        )

        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]
        assert politician_data["state"] == "NY"

    # -------------------------------------------------------------------------
    # Legacy Disclosure Format Tests
    # -------------------------------------------------------------------------

    def test_handles_disclosure_dict_format(self, mock_supabase_empty):
        """find_or_create_politician() handles legacy disclosure dict format."""
        from app.lib.politician import find_or_create_politician

        disclosure = {
            "first_name": "Jane",
            "last_name": "Smith",
            "politician_name": "Jane Smith",
            "state_district": "CA-15",
        }

        result = find_or_create_politician(
            mock_supabase_empty,
            disclosure=disclosure,
        )

        assert result == "new-uuid-123"

    def test_extracts_state_from_state_district(self, mock_supabase_empty):
        """find_or_create_politician() extracts state from state_district."""
        from app.lib.politician import find_or_create_politician

        disclosure = {
            "first_name": "John",
            "last_name": "Doe",
            "state_district": "NY-03",
        }

        find_or_create_politician(
            mock_supabase_empty,
            disclosure=disclosure,
        )

        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]
        assert politician_data["state"] == "NY"

    def test_disclosure_overrides_explicit_params(self, mock_supabase_empty):
        """find_or_create_politician() prioritizes disclosure dict."""
        from app.lib.politician import find_or_create_politician

        disclosure = {
            "first_name": "From",
            "last_name": "Disclosure",
            "state_district": "CA-01",
        }

        find_or_create_politician(
            mock_supabase_empty,
            name="Explicit Name",
            disclosure=disclosure,
        )

        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]
        assert politician_data["first_name"] == "From"
        assert politician_data["last_name"] == "Disclosure"

    # -------------------------------------------------------------------------
    # Name Splitting Tests
    # -------------------------------------------------------------------------

    def test_splits_name_for_first_and_last(self, mock_supabase_empty):
        """find_or_create_politician() splits name into first/last if not provided."""
        from app.lib.politician import find_or_create_politician

        find_or_create_politician(
            mock_supabase_empty,
            name="Jane Marie Doe",
            chamber="senate",
        )

        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]
        assert politician_data["first_name"] == "Jane"
        assert politician_data["last_name"] == "Marie Doe"

    def test_handles_single_name(self, mock_supabase_empty):
        """find_or_create_politician() handles single-word name."""
        from app.lib.politician import find_or_create_politician

        find_or_create_politician(
            mock_supabase_empty,
            name="Madonna",
            chamber="senate",
        )

        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]
        assert politician_data["first_name"] == "Madonna"
        assert politician_data["last_name"] == ""

    # -------------------------------------------------------------------------
    # Error Handling Tests
    # -------------------------------------------------------------------------

    def test_handles_find_exception(self, mock_supabase_empty):
        """find_or_create_politician() handles exception during find."""
        from app.lib.politician import find_or_create_politician

        table_mock = mock_supabase_empty.table.return_value
        table_mock.select.return_value.match.return_value.execute.side_effect = Exception(
            "DB error"
        )
        table_mock.select.return_value.ilike.return_value.limit.return_value.execute.side_effect = Exception(
            "DB error"
        )

        # Should still attempt to create
        result = find_or_create_politician(
            mock_supabase_empty,
            name="John Doe",
            chamber="senate",
        )

        assert result == "new-uuid-123"

    def test_handles_create_exception(self, mock_supabase_empty):
        """find_or_create_politician() returns None on create exception."""
        from app.lib.politician import find_or_create_politician

        table_mock = mock_supabase_empty.table.return_value
        table_mock.insert.return_value.execute.side_effect = Exception(
            "Insert failed"
        )

        result = find_or_create_politician(
            mock_supabase_empty,
            name="John Doe",
            chamber="senate",
        )

        assert result is None

    # -------------------------------------------------------------------------
    # Field Completeness Tests
    # -------------------------------------------------------------------------

    def test_sets_all_required_fields(self, mock_supabase_empty):
        """find_or_create_politician() sets all required fields."""
        from app.lib.politician import find_or_create_politician

        find_or_create_politician(
            mock_supabase_empty,
            name="John Smith",
            chamber="senate",
            state="CA",
        )

        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]

        # Check required fields
        assert "name" in politician_data
        assert "full_name" in politician_data
        assert "first_name" in politician_data
        assert "last_name" in politician_data
        assert "chamber" in politician_data
        assert "role" in politician_data
        assert "party" in politician_data
        assert "state" in politician_data

    def test_sets_party_to_none(self, mock_supabase_empty):
        """find_or_create_politician() sets party to None (to be enriched later)."""
        from app.lib.politician import find_or_create_politician

        find_or_create_politician(
            mock_supabase_empty,
            name="John Smith",
            chamber="senate",
        )

        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]
        assert politician_data["party"] is None

    # -------------------------------------------------------------------------
    # House-Specific Fields Tests
    # -------------------------------------------------------------------------

    def test_sets_house_specific_fields(self, mock_supabase_empty):
        """find_or_create_politician() sets House-specific fields."""
        from app.lib.politician import find_or_create_politician

        find_or_create_politician(
            mock_supabase_empty,
            name="John Doe",
            chamber="house",
            state="CA",
            district="CA-12",
        )

        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]

        assert politician_data["state_or_country"] == "CA"
        assert politician_data["district"] == "CA-12"

    def test_senate_does_not_have_district(self, mock_supabase_empty):
        """find_or_create_politician() does not set district for Senate."""
        from app.lib.politician import find_or_create_politician

        find_or_create_politician(
            mock_supabase_empty,
            name="Jane Smith",
            chamber="senate",
            state="NY",
        )

        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]

        assert "district" not in politician_data or politician_data.get("district") is None

    def test_eu_parliament_sets_state_or_country(self, mock_supabase_empty):
        """find_or_create_politician() sets state_or_country for EU MEPs."""
        from app.lib.politician import find_or_create_politician

        find_or_create_politician(
            mock_supabase_empty,
            name="Mika AALTOLA",
            first_name="Mika",
            last_name="AALTOLA",
            chamber="eu_parliament",
            state="Finland",
            party="EPP",
        )

        table_mock = mock_supabase_empty.table.return_value
        insert_call = table_mock.insert.call_args
        politician_data = insert_call[0][0]

        assert politician_data["state_or_country"] == "Finland"
        assert politician_data["role"] == "MEP"
        assert politician_data["party"] == "EPP"
