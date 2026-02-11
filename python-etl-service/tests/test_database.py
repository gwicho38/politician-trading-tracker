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


# =============================================================================
# prepare_transaction_for_batch() Tests
# =============================================================================

class TestPrepareTransactionForBatch:
    """Tests for prepare_transaction_for_batch() function."""

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

    def test_prepares_transaction_dict(self, sample_transaction, sample_disclosure):
        """prepare_transaction_for_batch() returns correct dict structure."""
        from app.lib.database import prepare_transaction_for_batch

        result = prepare_transaction_for_batch(
            "politician-uuid",
            sample_transaction,
            sample_disclosure,
        )

        assert result is not None
        assert result["politician_id"] == "politician-uuid"
        assert result["asset_name"] == "Apple Inc."
        assert result["asset_ticker"] == "AAPL"
        assert result["transaction_type"] == "purchase"
        assert result["status"] == "active"

    def test_returns_none_for_empty_asset_name(self, sample_disclosure):
        """prepare_transaction_for_batch() returns None for empty asset_name."""
        from app.lib.database import prepare_transaction_for_batch

        transaction = {"asset_name": ""}
        result = prepare_transaction_for_batch(
            "politician-uuid",
            transaction,
            sample_disclosure,
        )

        assert result is None

    def test_truncates_long_asset_name(self, sample_disclosure):
        """prepare_transaction_for_batch() truncates asset_name > 200 chars."""
        from app.lib.database import prepare_transaction_for_batch

        transaction = {"asset_name": "A" * 300}
        result = prepare_transaction_for_batch(
            "politician-uuid",
            transaction,
            sample_disclosure,
        )

        assert result is not None
        assert len(result["asset_name"]) == 200


# =============================================================================
# batch_upload_transactions() Tests
# =============================================================================

class TestBatchUploadTransactions:
    """Tests for batch_upload_transactions() function."""

    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client for batch upload tests."""
        client = MagicMock()
        table_mock = MagicMock()
        table_mock.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "id-1"}, {"id": "id-2"}, {"id": "id-3"}]
        )
        table_mock.upsert.return_value.execute.return_value = MagicMock(
            data=[{"id": "id-1"}, {"id": "id-2"}, {"id": "id-3"}]
        )
        client.table.return_value = table_mock
        return client

    @pytest.fixture
    def sample_transactions(self):
        """Sample prepared transaction data."""
        return [
            {
                "politician_id": "pol-1",
                "asset_name": "Apple Inc.",
                "asset_ticker": "AAPL",
                "transaction_type": "purchase",
                "transaction_date": "2024-01-15",
                "disclosure_date": "2024-01-25",
                "status": "active",
            },
            {
                "politician_id": "pol-1",
                "asset_name": "Microsoft Corp.",
                "asset_ticker": "MSFT",
                "transaction_type": "sale",
                "transaction_date": "2024-01-16",
                "disclosure_date": "2024-01-25",
                "status": "active",
            },
            {
                "politician_id": "pol-1",
                "asset_name": "Google LLC",
                "asset_ticker": "GOOGL",
                "transaction_type": "purchase",
                "transaction_date": "2024-01-17",
                "disclosure_date": "2024-01-25",
                "status": "active",
            },
        ]

    def test_batch_insert_succeeds(self, mock_supabase_client, sample_transactions):
        """batch_upload_transactions() inserts batch successfully."""
        from app.lib.database import batch_upload_transactions

        successful, failed = batch_upload_transactions(
            mock_supabase_client,
            sample_transactions,
            update_mode=False,
        )

        assert successful == 3
        assert failed == 0
        mock_supabase_client.table.assert_called_with("trading_disclosures")

    def test_batch_upsert_in_update_mode(self, mock_supabase_client, sample_transactions):
        """batch_upload_transactions() uses upsert when update_mode=True."""
        from app.lib.database import batch_upload_transactions

        successful, failed = batch_upload_transactions(
            mock_supabase_client,
            sample_transactions,
            update_mode=True,
        )

        assert successful == 3
        assert failed == 0
        table_mock = mock_supabase_client.table.return_value
        table_mock.upsert.assert_called_once()

    def test_returns_zeros_for_empty_list(self, mock_supabase_client):
        """batch_upload_transactions() returns (0, 0) for empty list."""
        from app.lib.database import batch_upload_transactions

        successful, failed = batch_upload_transactions(
            mock_supabase_client,
            [],
        )

        assert successful == 0
        assert failed == 0

    def test_handles_batch_with_custom_size(self, mock_supabase_client):
        """batch_upload_transactions() respects custom batch_size."""
        from app.lib.database import batch_upload_transactions

        # Create 5 transactions to test batch splitting
        transactions = [
            {"politician_id": f"pol-{i}", "asset_name": f"Asset {i}", "status": "active"}
            for i in range(5)
        ]

        # Set mock to return correct number of records
        table_mock = mock_supabase_client.table.return_value
        table_mock.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": f"id-{i}"} for i in range(2)]
        )

        batch_upload_transactions(
            mock_supabase_client,
            transactions,
            batch_size=2,
        )

        # Should be called 3 times: 2 + 2 + 1
        assert table_mock.insert.call_count == 3

    def test_handles_duplicate_key_with_fallback(self, mock_supabase_client, sample_transactions):
        """batch_upload_transactions() falls back to individual inserts on duplicate."""
        from app.lib.database import batch_upload_transactions

        table_mock = mock_supabase_client.table.return_value

        # First call fails with duplicate key, then individual inserts succeed
        call_count = [0]
        def side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("duplicate key value violates unique constraint")
            return MagicMock(data=[{"id": "id-1"}])

        table_mock.insert.return_value.execute.side_effect = side_effect

        successful, failed = batch_upload_transactions(
            mock_supabase_client,
            sample_transactions,
        )

        # All 3 should succeed via fallback individual inserts
        assert successful == 3
        assert failed == 0

    def test_counts_failures_correctly(self, mock_supabase_client, sample_transactions):
        """batch_upload_transactions() counts failures correctly."""
        from app.lib.database import batch_upload_transactions

        table_mock = mock_supabase_client.table.return_value
        table_mock.insert.return_value.execute.side_effect = Exception("Network error")

        successful, failed = batch_upload_transactions(
            mock_supabase_client,
            sample_transactions,
        )

        assert successful == 0
        assert failed == 3


# =============================================================================
# Trade Amount Validation Tests
# =============================================================================

class TestTradeAmountValidation:
    """Tests for trade amount validation (prevents corrupted data from PDF parsing)."""

    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client for validation tests."""
        client = MagicMock()
        table_mock = MagicMock()
        table_mock.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "new-uuid-123"}]
        )
        client.table.return_value = table_mock
        return client

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

    def test_rejects_amount_over_50_million(
        self, mock_supabase_client, sample_disclosure
    ):
        """upload_transaction_to_supabase() rejects amounts > $50M as corrupted."""
        from app.lib.database import upload_transaction_to_supabase

        # This represents corrupted data from PDF parsing (e.g., $4.5 trillion)
        transaction = {
            "asset_name": "Test Asset",
            "asset_ticker": "TEST",
            "value_low": 4_536_758_654_345,  # $4.5 trillion - clearly invalid
            "value_high": 4_536_758_654_345,
        }

        upload_transaction_to_supabase(
            mock_supabase_client,
            "politician-uuid",
            transaction,
            sample_disclosure,
        )

        # Verify insert was called with None amounts (rejected)
        table_mock = mock_supabase_client.table.return_value
        insert_call = table_mock.insert.call_args
        disclosure_data = insert_call[0][0]

        assert disclosure_data["amount_range_min"] is None
        assert disclosure_data["amount_range_max"] is None

    def test_rejects_amount_just_over_threshold(
        self, mock_supabase_client, sample_disclosure
    ):
        """upload_transaction_to_supabase() rejects amounts just over $50M."""
        from app.lib.database import upload_transaction_to_supabase

        transaction = {
            "asset_name": "Test Asset",
            "value_low": 50_000_001,  # Just over threshold
            "value_high": 60_000_000,
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

        assert disclosure_data["amount_range_min"] is None
        assert disclosure_data["amount_range_max"] is None

    def test_accepts_valid_amount_at_threshold(
        self, mock_supabase_client, sample_disclosure
    ):
        """upload_transaction_to_supabase() accepts amounts at exactly $50M."""
        from app.lib.database import upload_transaction_to_supabase

        transaction = {
            "asset_name": "Test Asset",
            "value_low": 5_000_001,  # "Over $5M" range low
            "value_high": 50_000_000,  # $50M - at threshold
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

        assert disclosure_data["amount_range_min"] == 5_000_001
        assert disclosure_data["amount_range_max"] == 50_000_000

    def test_accepts_normal_disclosure_range(
        self, mock_supabase_client, sample_disclosure
    ):
        """upload_transaction_to_supabase() accepts normal disclosure ranges."""
        from app.lib.database import upload_transaction_to_supabase

        transaction = {
            "asset_name": "Apple Inc.",
            "value_low": 1001,
            "value_high": 15000,
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

        assert disclosure_data["amount_range_min"] == 1001
        assert disclosure_data["amount_range_max"] == 15000

    def test_accepts_none_amounts(
        self, mock_supabase_client, sample_disclosure
    ):
        """upload_transaction_to_supabase() accepts None amounts."""
        from app.lib.database import upload_transaction_to_supabase

        transaction = {
            "asset_name": "Test Asset",
            "value_low": None,
            "value_high": None,
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

        assert disclosure_data["amount_range_min"] is None
        assert disclosure_data["amount_range_max"] is None

    def test_rejects_if_only_high_is_invalid(
        self, mock_supabase_client, sample_disclosure
    ):
        """upload_transaction_to_supabase() rejects both if high is invalid."""
        from app.lib.database import upload_transaction_to_supabase

        transaction = {
            "asset_name": "Test Asset",
            "value_low": 1001,  # Valid
            "value_high": 100_000_000,  # Invalid - $100M
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

        # Both should be None since high was invalid
        assert disclosure_data["amount_range_min"] is None
        assert disclosure_data["amount_range_max"] is None


class TestPrepareTransactionForBatchValidation:
    """Tests for trade amount validation in prepare_transaction_for_batch()."""

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

    def test_rejects_invalid_amount_in_batch_prep(self, sample_disclosure):
        """prepare_transaction_for_batch() rejects amounts > $50M."""
        from app.lib.database import prepare_transaction_for_batch

        transaction = {
            "asset_name": "Test Asset",
            "value_low": 896_756_453_421,  # ~$897B - clearly invalid
            "value_high": 896_756_453_421,
        }

        result = prepare_transaction_for_batch(
            "politician-uuid",
            transaction,
            sample_disclosure,
        )

        assert result is not None
        assert result["amount_range_min"] is None
        assert result["amount_range_max"] is None

    def test_accepts_valid_amount_in_batch_prep(self, sample_disclosure):
        """prepare_transaction_for_batch() accepts valid amounts."""
        from app.lib.database import prepare_transaction_for_batch

        transaction = {
            "asset_name": "Test Asset",
            "value_low": 15001,
            "value_high": 50000,
        }

        result = prepare_transaction_for_batch(
            "politician-uuid",
            transaction,
            sample_disclosure,
        )

        assert result is not None
        assert result["amount_range_min"] == 15001
        assert result["amount_range_max"] == 50000


# =============================================================================
# Parser Validation Function Tests
# =============================================================================

class TestValidateTradeAmount:
    """Tests for validate_trade_amount() function in parser module."""

    def test_none_is_valid(self):
        """validate_trade_amount() returns True for None."""
        from app.lib.parser import validate_trade_amount

        assert validate_trade_amount(None) is True

    def test_zero_is_valid(self):
        """validate_trade_amount() returns True for zero."""
        from app.lib.parser import validate_trade_amount

        assert validate_trade_amount(0) is True

    def test_normal_amount_is_valid(self):
        """validate_trade_amount() returns True for normal amounts."""
        from app.lib.parser import validate_trade_amount

        assert validate_trade_amount(1001) is True
        assert validate_trade_amount(15000) is True
        assert validate_trade_amount(1_000_000) is True
        assert validate_trade_amount(5_000_000) is True

    def test_max_threshold_is_valid(self):
        """validate_trade_amount() returns True for amount at threshold."""
        from app.lib.parser import validate_trade_amount, MAX_VALID_TRADE_AMOUNT

        assert validate_trade_amount(MAX_VALID_TRADE_AMOUNT) is True
        assert validate_trade_amount(50_000_000) is True

    def test_over_threshold_is_invalid(self):
        """validate_trade_amount() returns False for amounts over threshold."""
        from app.lib.parser import validate_trade_amount

        assert validate_trade_amount(50_000_001) is False
        assert validate_trade_amount(100_000_000) is False
        assert validate_trade_amount(1_000_000_000) is False
        assert validate_trade_amount(4_536_758_654_345) is False  # $4.5 trillion


class TestValidateAndSanitizeAmounts:
    """Tests for validate_and_sanitize_amounts() function."""

    def test_both_valid_returns_unchanged(self):
        """validate_and_sanitize_amounts() returns amounts unchanged when valid."""
        from app.lib.parser import validate_and_sanitize_amounts

        low, high = validate_and_sanitize_amounts(1001, 15000)
        assert low == 1001
        assert high == 15000

    def test_both_none_returns_none(self):
        """validate_and_sanitize_amounts() returns None, None for both None input."""
        from app.lib.parser import validate_and_sanitize_amounts

        low, high = validate_and_sanitize_amounts(None, None)
        assert low is None
        assert high is None

    def test_low_invalid_returns_both_none(self):
        """validate_and_sanitize_amounts() returns both None if low is invalid."""
        from app.lib.parser import validate_and_sanitize_amounts

        low, high = validate_and_sanitize_amounts(100_000_000, 15000)
        assert low is None
        assert high is None

    def test_high_invalid_returns_both_none(self):
        """validate_and_sanitize_amounts() returns both None if high is invalid."""
        from app.lib.parser import validate_and_sanitize_amounts

        low, high = validate_and_sanitize_amounts(1001, 100_000_000)
        assert low is None
        assert high is None

    def test_both_invalid_returns_both_none(self):
        """validate_and_sanitize_amounts() returns both None if both invalid."""
        from app.lib.parser import validate_and_sanitize_amounts

        low, high = validate_and_sanitize_amounts(
            4_536_758_654_345,  # $4.5 trillion
            896_756_453_421,    # $897 billion
        )
        assert low is None
        assert high is None

    def test_one_none_one_valid(self):
        """validate_and_sanitize_amounts() handles one None, one valid."""
        from app.lib.parser import validate_and_sanitize_amounts

        low, high = validate_and_sanitize_amounts(None, 15000)
        assert low is None
        assert high == 15000

        low, high = validate_and_sanitize_amounts(1001, None)
        assert low == 1001
        assert high is None


# =============================================================================
# Source Field Tests (database.py source + source_url fixes)
# =============================================================================

class TestSourceFieldHandling:
    """Tests for dynamic source field and source_url fallback."""

    @pytest.fixture
    def mock_supabase_client(self):
        """Create a mock Supabase client."""
        client = MagicMock()
        table_mock = MagicMock()
        table_mock.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "new-uuid"}]
        )
        client.table.return_value = table_mock
        return client

    def test_source_defaults_to_us_house(self, mock_supabase_client):
        """upload_transaction_to_supabase() defaults source to 'us_house'."""
        from app.lib.database import upload_transaction_to_supabase

        transaction = {"asset_name": "Test Asset"}
        disclosure = {"pdf_url": "https://example.com/doc.pdf", "filing_date": "2024-01-01"}

        upload_transaction_to_supabase(
            mock_supabase_client, "pol-uuid", transaction, disclosure
        )

        table_mock = mock_supabase_client.table.return_value
        insert_data = table_mock.insert.call_args[0][0]
        assert insert_data["raw_data"]["source"] == "us_house"

    def test_source_uses_disclosure_source(self, mock_supabase_client):
        """upload_transaction_to_supabase() uses disclosure source when provided."""
        from app.lib.database import upload_transaction_to_supabase

        transaction = {"asset_name": "Test Asset"}
        disclosure = {
            "source": "us_senate",
            "source_url": "https://efdsearch.senate.gov/view/ptr/abc/",
            "filing_date": "2024-01-01",
        }

        upload_transaction_to_supabase(
            mock_supabase_client, "pol-uuid", transaction, disclosure
        )

        table_mock = mock_supabase_client.table.return_value
        insert_data = table_mock.insert.call_args[0][0]
        assert insert_data["raw_data"]["source"] == "us_senate"

    def test_source_url_falls_back_to_source_url_key(self, mock_supabase_client):
        """upload_transaction_to_supabase() falls back to source_url key when pdf_url missing."""
        from app.lib.database import upload_transaction_to_supabase

        transaction = {"asset_name": "Test Asset"}
        disclosure = {
            "source_url": "https://efdsearch.senate.gov/view/ptr/abc/",
            "filing_date": "2024-01-01",
        }

        upload_transaction_to_supabase(
            mock_supabase_client, "pol-uuid", transaction, disclosure
        )

        table_mock = mock_supabase_client.table.return_value
        insert_data = table_mock.insert.call_args[0][0]
        assert insert_data["source_url"] == "https://efdsearch.senate.gov/view/ptr/abc/"

    def test_source_url_prefers_pdf_url(self, mock_supabase_client):
        """upload_transaction_to_supabase() prefers pdf_url over source_url."""
        from app.lib.database import upload_transaction_to_supabase

        transaction = {"asset_name": "Test Asset"}
        disclosure = {
            "pdf_url": "https://example.com/doc.pdf",
            "source_url": "https://example.com/other.html",
            "filing_date": "2024-01-01",
        }

        upload_transaction_to_supabase(
            mock_supabase_client, "pol-uuid", transaction, disclosure
        )

        table_mock = mock_supabase_client.table.return_value
        insert_data = table_mock.insert.call_args[0][0]
        assert insert_data["source_url"] == "https://example.com/doc.pdf"


class TestPrepareTransactionSourceField:
    """Tests for source field in prepare_transaction_for_batch()."""

    def test_batch_source_defaults_to_us_house(self):
        """prepare_transaction_for_batch() defaults source to 'us_house'."""
        from app.lib.database import prepare_transaction_for_batch

        transaction = {"asset_name": "Test Asset"}
        disclosure = {"pdf_url": "https://example.com/doc.pdf", "filing_date": "2024-01-01"}

        result = prepare_transaction_for_batch("pol-uuid", transaction, disclosure)

        assert result["raw_data"]["source"] == "us_house"

    def test_batch_source_uses_disclosure_source(self):
        """prepare_transaction_for_batch() uses disclosure source when provided."""
        from app.lib.database import prepare_transaction_for_batch

        transaction = {"asset_name": "Test Asset"}
        disclosure = {"source": "us_senate", "source_url": "https://test.url/", "filing_date": "2024-01-01"}

        result = prepare_transaction_for_batch("pol-uuid", transaction, disclosure)

        assert result["raw_data"]["source"] == "us_senate"

    def test_batch_source_url_falls_back(self):
        """prepare_transaction_for_batch() falls back to source_url key."""
        from app.lib.database import prepare_transaction_for_batch

        transaction = {"asset_name": "Test Asset"}
        disclosure = {"source_url": "https://test.url/ptr/abc/", "filing_date": "2024-01-01"}

        result = prepare_transaction_for_batch("pol-uuid", transaction, disclosure)

        assert result["source_url"] == "https://test.url/ptr/abc/"
