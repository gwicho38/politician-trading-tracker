"""Tests for party_registry module."""
import hashlib
from unittest.mock import MagicMock, patch

import pytest

from app.lib.party_registry import (
    ensure_party_exists,
    generate_party_color,
    abbreviate_group_name,
    reset_cache,
)


class TestGeneratePartyColor:
    """Test hex color generation."""

    def test_returns_7_char_hex(self):
        color = generate_party_color("Test Party")
        assert len(color) == 7
        assert color.startswith("#")

    def test_deterministic_for_same_input(self):
        c1 = generate_party_color("Democrats")
        c2 = generate_party_color("Democrats")
        assert c1 == c2

    def test_different_for_different_input(self):
        c1 = generate_party_color("Democrats")
        c2 = generate_party_color("Republicans")
        assert c1 != c2

    def test_valid_hex_chars(self):
        color = generate_party_color("Any Party Name")
        assert all(c in "0123456789abcdefABCDEF#" for c in color)


class TestAbbreviateGroupName:
    """Test EU group name abbreviation."""

    def test_known_group_epp(self):
        assert abbreviate_group_name("Group of the European People's Party (Christian Democrats)") == "EPP"

    def test_known_group_sd(self):
        assert abbreviate_group_name("Group of the Progressive Alliance of Socialists and Democrats") == "S&D"

    def test_known_group_renew(self):
        assert abbreviate_group_name("Renew Europe Group") == "Renew"

    def test_known_group_greens(self):
        assert abbreviate_group_name("Group of the Greens/European Free Alliance") == "Greens/EFA"

    def test_known_group_ecr(self):
        assert abbreviate_group_name("European Conservatives and Reformists Group") == "ECR"

    def test_known_group_id(self):
        assert abbreviate_group_name("Identity and Democracy Group") == "ID"

    def test_known_group_left(self):
        assert abbreviate_group_name("The Left group in the European Parliament - GUE/NGL") == "GUE/NGL"

    def test_known_group_ni(self):
        assert abbreviate_group_name("Non-attached Members") == "NI"

    def test_patriots_for_europe(self):
        assert abbreviate_group_name("Patriots for Europe Group") == "PfE"

    def test_unknown_group_generates_initials(self):
        result = abbreviate_group_name("Some New Political Movement")
        assert isinstance(result, str)
        assert len(result) <= 20

    def test_empty_string(self):
        assert abbreviate_group_name("") == ""

    def test_none_input(self):
        assert abbreviate_group_name(None) == ""


class TestEnsurePartyExists:
    """Test party registration with Supabase."""

    def setup_method(self):
        """Reset cache before each test."""
        reset_cache()

    def test_returns_code_when_party_exists(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"code": "D"}
        ]
        result = ensure_party_exists(mock_sb, "D", "Democratic Party", "US")
        assert result == "D"

    def test_creates_party_when_not_exists(self):
        mock_sb = MagicMock()
        # First call: select returns empty (not found)
        mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        # Second call: insert succeeds
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{"code": "NEW"}]

        result = ensure_party_exists(mock_sb, "NEW", "New Party", "EU")
        assert result == "NEW"
        # Verify insert was called
        mock_sb.table.return_value.insert.assert_called_once()
        insert_arg = mock_sb.table.return_value.insert.call_args[0][0]
        assert insert_arg["code"] == "NEW"
        assert insert_arg["name"] == "New Party"
        assert insert_arg["jurisdiction"] == "EU"
        assert insert_arg["color"].startswith("#")

    def test_uses_code_as_name_when_name_not_provided(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = [{"code": "X"}]

        ensure_party_exists(mock_sb, "X")
        insert_arg = mock_sb.table.return_value.insert.call_args[0][0]
        assert insert_arg["name"] == "X"

    def test_handles_insert_error_gracefully(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        mock_sb.table.return_value.insert.return_value.execute.side_effect = Exception("DB error")

        # Should not raise, should return code anyway
        result = ensure_party_exists(mock_sb, "ERR", "Error Party")
        assert result == "ERR"

    def test_caches_known_parties(self):
        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"code": "D"}
        ]

        # Call twice with same code
        ensure_party_exists(mock_sb, "D")
        ensure_party_exists(mock_sb, "D")

        # Should only query DB once (second call hits cache)
        assert mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.call_count == 1

    def test_returns_empty_code_unchanged(self):
        mock_sb = MagicMock()
        result = ensure_party_exists(mock_sb, "")
        assert result == ""
        # Should not query DB at all
        mock_sb.table.assert_not_called()

    def test_returns_none_code_unchanged(self):
        mock_sb = MagicMock()
        result = ensure_party_exists(mock_sb, None)
        assert result is None
        mock_sb.table.assert_not_called()
