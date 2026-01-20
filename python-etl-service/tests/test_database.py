"""
Tests for database utilities (app/lib/database.py).

Tests:
- get_supabase() - Client initialization
- upload_transaction_to_supabase() - Transaction upload
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


# =============================================================================
# get_supabase() Tests
# =============================================================================

class TestGetSupabase:
    """Tests for get_supabase() function."""

    def test_returns_client_when_env_vars_set(self, monkeypatch):
        """get_supabase() returns client when env vars are set."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-key")

        with patch("app.lib.database.create_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            from app.lib.database import get_supabase
            result = get_supabase()

            mock_create.assert_called_once_with(
                "https://test.supabase.co",
                "test-key"
            )
            assert result == mock_client

    def test_returns_none_when_key_empty(self, monkeypatch):
        """get_supabase() returns None when SUPABASE_SERVICE_KEY is empty."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "")

        from app.lib.database import get_supabase
        result = get_supabase()
        assert result is None

    def test_returns_none_when_key_missing(self, monkeypatch):
        """get_supabase() returns None when SUPABASE_SERVICE_KEY not set."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)

        from app.lib.database import get_supabase
        result = get_supabase()
        assert result is None

    def test_returns_none_when_both_empty(self, monkeypatch):
        """get_supabase() returns None when both env vars are empty."""
        monkeypatch.setenv("SUPABASE_URL", "")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "")

        from app.lib.database import get_supabase
        result = get_supabase()
        assert result is None


# =============================================================================
# upload_transaction_to_supabase() Tests
# =============================================================================

class TestUploadTransactionToSupabase:
    """Tests for upload_transaction_to_supabase() function."""

    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client for upload tests."""
        client = MagicMock()
        table_mock = MagicMock()
        table_mock.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "new-uuid-123"}]
        )
        table_mock.upsert.return_value.execute.return_value = MagicMock(
            data=[{"id": "upserted-uuid-456"}]
        )
        client.table.return_value = table_mock
        return client

    @pytest.fixture
    def sample_transaction(self):
        """Sample transaction data."""
        return {
            "asset_name": "Apple Inc.",
            "asset_ticker": "AAPL",
            "asset_type": "stock",
            "transaction_type": "purchase",
            "transaction_date": "2024-01-15",
            "notification_date": "2024-01-25",
            "value_low": 1001,
            "value_high": 15000,
            "raw_row": ["01/15/2024", "Apple Inc.", "AAPL", "P", "$1,001 - $15,000"],
        }

    @pytest.fixture
    def sample_disclosure(self):
        """Sample disclosure metadata."""
        return {
            "doc_id": "20012345",
            "year": 2024,
            "filing_type": "P",
            "pdf_url": "https://example.com/disclosure.pdf",
            "filing_date": "2024-01-25",
            "state_district": "CA-12",
        }

    def test_inserts_transaction_successfully(
        self, mock_supabase_client, sample_transaction, sample_disclosure
    ):
        """upload_transaction_to_supabase() inserts and returns ID."""
        from app.lib.database import upload_transaction_to_supabase

        result = upload_transaction_to_supabase(
            mock_supabase_client,
            "politician-uuid",
            sample_transaction,
            sample_disclosure,
            update_mode=False,
        )

        assert result == "new-uuid-123"
        mock_supabase_client.table.assert_called_with("trading_disclosures")

    def test_upserts_in_update_mode(
        self, mock_supabase_client, sample_transaction, sample_disclosure
    ):
        """upload_transaction_to_supabase() upserts when update_mode=True."""
        from app.lib.database import upload_transaction_to_supabase

        result = upload_transaction_to_supabase(
            mock_supabase_client,
            "politician-uuid",
            sample_transaction,
            sample_disclosure,
            update_mode=True,
        )

        assert result == "upserted-uuid-456"
        table_mock = mock_supabase_client.table.return_value
        table_mock.upsert.assert_called_once()

    def test_returns_none_for_empty_asset_name(
        self, mock_supabase_client, sample_disclosure
    ):
        """upload_transaction_to_supabase() returns None for empty asset_name."""
        from app.lib.database import upload_transaction_to_supabase

        transaction_no_name = {"asset_name": "", "asset_ticker": "AAPL"}
        result = upload_transaction_to_supabase(
            mock_supabase_client,
            "politician-uuid",
            transaction_no_name,
            sample_disclosure,
        )

        assert result is None

    def test_returns_none_for_missing_asset_name(
        self, mock_supabase_client, sample_disclosure
    ):
        """upload_transaction_to_supabase() returns None when asset_name missing."""
        from app.lib.database import upload_transaction_to_supabase

        transaction_missing_name = {"asset_ticker": "AAPL"}
        result = upload_transaction_to_supabase(
            mock_supabase_client,
            "politician-uuid",
            transaction_missing_name,
            sample_disclosure,
        )

        assert result is None

    def test_truncates_long_asset_name(
        self, mock_supabase_client, sample_disclosure
    ):
        """upload_transaction_to_supabase() truncates asset_name > 200 chars."""
        from app.lib.database import upload_transaction_to_supabase

        long_name = "A" * 300
        transaction = {"asset_name": long_name, "asset_ticker": "TEST"}

        upload_transaction_to_supabase(
            mock_supabase_client,
            "politician-uuid",
            transaction,
            sample_disclosure,
        )

        # Verify insert was called with truncated name
        table_mock = mock_supabase_client.table.return_value
        insert_call = table_mock.insert.call_args
        assert insert_call is not None
        disclosure_data = insert_call[0][0]
        assert len(disclosure_data["asset_name"]) == 200

    def test_handles_timestamp_with_t(
        self, mock_supabase_client, sample_disclosure
    ):
        """upload_transaction_to_supabase() normalizes timestamps with 'T'."""
        from app.lib.database import upload_transaction_to_supabase

        transaction = {
            "asset_name": "Test Asset",
            "filing_date": "2024-01-15T10:30:00",
            "transaction_date": "2024-01-10T09:00:00Z",
            "notification_date": "2024-01-20T14:00:00.000Z",
        }

        upload_transaction_to_supabase(
            mock_supabase_client,
            "politician-uuid",
            transaction,
            sample_disclosure,
        )

        table_mock = mock_supabase_client.table.return_value
        insert_call = table_mock.insert.call_args
        disclosure_data = insert_call[0][0]

        # Timestamps should be normalized (T replaced with space, truncated)
        assert "T" not in disclosure_data["transaction_date"]

    def test_handles_duplicate_key_error(
        self, mock_supabase_client, sample_transaction, sample_disclosure
    ):
        """upload_transaction_to_supabase() handles duplicate key gracefully."""
        from app.lib.database import upload_transaction_to_supabase

        table_mock = mock_supabase_client.table.return_value
        table_mock.insert.return_value.execute.side_effect = Exception(
            "duplicate key value violates unique constraint"
        )

        result = upload_transaction_to_supabase(
            mock_supabase_client,
            "politician-uuid",
            sample_transaction,
            sample_disclosure,
        )

        assert result is None

    def test_handles_23505_error_code(
        self, mock_supabase_client, sample_transaction, sample_disclosure
    ):
        """upload_transaction_to_supabase() handles PostgreSQL 23505 error."""
        from app.lib.database import upload_transaction_to_supabase

        table_mock = mock_supabase_client.table.return_value
        table_mock.insert.return_value.execute.side_effect = Exception(
            "23505: unique_violation"
        )

        result = upload_transaction_to_supabase(
            mock_supabase_client,
            "politician-uuid",
            sample_transaction,
            sample_disclosure,
        )

        assert result is None

    def test_handles_generic_exception(
        self, mock_supabase_client, sample_transaction, sample_disclosure
    ):
        """upload_transaction_to_supabase() returns None on generic error."""
        from app.lib.database import upload_transaction_to_supabase

        table_mock = mock_supabase_client.table.return_value
        table_mock.insert.return_value.execute.side_effect = Exception(
            "Network error"
        )

        result = upload_transaction_to_supabase(
            mock_supabase_client,
            "politician-uuid",
            sample_transaction,
            sample_disclosure,
        )

        assert result is None

    def test_sets_correct_disclosure_fields(
        self, mock_supabase_client, sample_transaction, sample_disclosure
    ):
        """upload_transaction_to_supabase() sets all expected fields."""
        from app.lib.database import upload_transaction_to_supabase

        upload_transaction_to_supabase(
            mock_supabase_client,
            "politician-uuid",
            sample_transaction,
            sample_disclosure,
        )

        table_mock = mock_supabase_client.table.return_value
        insert_call = table_mock.insert.call_args
        disclosure_data = insert_call[0][0]

        # Verify required fields
        assert disclosure_data["politician_id"] == "politician-uuid"
        assert disclosure_data["asset_name"] == "Apple Inc."
        assert disclosure_data["asset_ticker"] == "AAPL"
        assert disclosure_data["transaction_type"] == "purchase"
        assert disclosure_data["amount_range_min"] == 1001
        assert disclosure_data["amount_range_max"] == 15000
        assert disclosure_data["source_url"] == "https://example.com/disclosure.pdf"
        assert disclosure_data["source_document_id"] == "20012345"
        assert disclosure_data["status"] == "active"

    def test_sets_raw_data_metadata(
        self, mock_supabase_client, sample_transaction, sample_disclosure
    ):
        """upload_transaction_to_supabase() includes raw_data metadata."""
        from app.lib.database import upload_transaction_to_supabase

        upload_transaction_to_supabase(
            mock_supabase_client,
            "politician-uuid",
            sample_transaction,
            sample_disclosure,
        )

        table_mock = mock_supabase_client.table.return_value
        insert_call = table_mock.insert.call_args
        disclosure_data = insert_call[0][0]

        assert "raw_data" in disclosure_data
        raw_data = disclosure_data["raw_data"]
        assert raw_data["source"] == "us_house"
        assert raw_data["year"] == 2024
        assert raw_data["filing_type"] == "P"
        assert raw_data["state_district"] == "CA-12"
        assert "raw_row" in raw_data

    def test_defaults_transaction_type_to_unknown(
        self, mock_supabase_client, sample_disclosure
    ):
        """upload_transaction_to_supabase() defaults transaction_type to 'unknown'."""
        from app.lib.database import upload_transaction_to_supabase

        transaction = {"asset_name": "Test Asset"}  # No transaction_type

        upload_transaction_to_supabase(
            mock_supabase_client,
            "politician-uuid",
            transaction,
            sample_disclosure,
        )

        table_mock = mock_supabase_client.table.return_value
        insert_call = table_mock.insert.call_args
        disclosure_data = insert_call[0][0]

        assert disclosure_data["transaction_type"] == "unknown"

    def test_falls_back_to_filing_date(
        self, mock_supabase_client, sample_disclosure
    ):
        """upload_transaction_to_supabase() uses filing_date as fallback."""
        from app.lib.database import upload_transaction_to_supabase

        transaction = {"asset_name": "Test Asset"}  # No dates

        upload_transaction_to_supabase(
            mock_supabase_client,
            "politician-uuid",
            transaction,
            sample_disclosure,
        )

        table_mock = mock_supabase_client.table.return_value
        insert_call = table_mock.insert.call_args
        disclosure_data = insert_call[0][0]

        # Should fall back to disclosure's filing_date
        assert disclosure_data["transaction_date"] == "2024-01-25"
        assert disclosure_data["disclosure_date"] == "2024-01-25"
