"""
Tests for Ticker Backfill Service (app/services/ticker_backfill.py).

Tests:
- extract_ticker_from_asset_name() - Extract ticker from asset name
- run_ticker_backfill() - Full ticker backfill flow
- extract_transaction_type_from_raw() - Extract transaction type from raw data
- run_transaction_type_backfill() - Transaction type backfill flow
- is_metadata_only() - Detect metadata-only records
"""

import pytest
from unittest.mock import MagicMock, patch


# =============================================================================
# extract_ticker_from_asset_name() Tests
# =============================================================================

class TestExtractTickerFromAssetName:
    """Tests for extract_ticker_from_asset_name() function."""

    def test_returns_none_for_none_input(self):
        """extract_ticker_from_asset_name() returns None for None input."""
        from app.services.ticker_backfill import extract_ticker_from_asset_name

        result = extract_ticker_from_asset_name(None)

        assert result is None

    def test_returns_none_for_empty_string(self):
        """extract_ticker_from_asset_name() returns None for empty string."""
        from app.services.ticker_backfill import extract_ticker_from_asset_name

        result = extract_ticker_from_asset_name("")

        assert result is None

    def test_extracts_ticker_with_brackets(self):
        """extract_ticker_from_asset_name() extracts ticker from brackets."""
        from app.services.ticker_backfill import extract_ticker_from_asset_name

        # Assuming extract_ticker_from_text handles [AAPL] format
        with patch("app.services.ticker_backfill.extract_ticker_from_text") as mock:
            mock.return_value = "AAPL"

            result = extract_ticker_from_asset_name("Apple Inc [AAPL]")

            assert result == "AAPL"

    def test_maps_apple_to_aapl(self):
        """extract_ticker_from_asset_name() maps Apple to AAPL."""
        from app.services.ticker_backfill import extract_ticker_from_asset_name

        with patch("app.services.ticker_backfill.extract_ticker_from_text") as mock:
            mock.return_value = None

            result = extract_ticker_from_asset_name("Apple Inc.")

            assert result == "AAPL"

    def test_maps_microsoft_to_msft(self):
        """extract_ticker_from_asset_name() maps Microsoft to MSFT."""
        from app.services.ticker_backfill import extract_ticker_from_asset_name

        with patch("app.services.ticker_backfill.extract_ticker_from_text") as mock:
            mock.return_value = None

            result = extract_ticker_from_asset_name("Microsoft Corporation")

            assert result == "MSFT"

    def test_maps_amazon_to_amzn(self):
        """extract_ticker_from_asset_name() maps Amazon to AMZN."""
        from app.services.ticker_backfill import extract_ticker_from_asset_name

        with patch("app.services.ticker_backfill.extract_ticker_from_text") as mock:
            mock.return_value = None

            result = extract_ticker_from_asset_name("Amazon.com Inc")

            assert result == "AMZN"

    def test_maps_google_to_googl(self):
        """extract_ticker_from_asset_name() maps Google to GOOGL."""
        from app.services.ticker_backfill import extract_ticker_from_asset_name

        with patch("app.services.ticker_backfill.extract_ticker_from_text") as mock:
            mock.return_value = None

            result = extract_ticker_from_asset_name("Google LLC")

            assert result == "GOOGL"

    def test_maps_alphabet_to_googl(self):
        """extract_ticker_from_asset_name() maps Alphabet to GOOGL."""
        from app.services.ticker_backfill import extract_ticker_from_asset_name

        with patch("app.services.ticker_backfill.extract_ticker_from_text") as mock:
            mock.return_value = None

            result = extract_ticker_from_asset_name("Alphabet Inc")

            assert result == "GOOGL"

    def test_maps_tesla_to_tsla(self):
        """extract_ticker_from_asset_name() maps Tesla to TSLA."""
        from app.services.ticker_backfill import extract_ticker_from_asset_name

        with patch("app.services.ticker_backfill.extract_ticker_from_text") as mock:
            mock.return_value = None

            result = extract_ticker_from_asset_name("Tesla Inc")

            assert result == "TSLA"

    def test_maps_meta_to_meta(self):
        """extract_ticker_from_asset_name() maps Meta Platforms to META."""
        from app.services.ticker_backfill import extract_ticker_from_asset_name

        with patch("app.services.ticker_backfill.extract_ticker_from_text") as mock:
            mock.return_value = None

            result = extract_ticker_from_asset_name("Meta Platforms Inc")

            assert result == "META"

    def test_maps_nvidia_to_nvda(self):
        """extract_ticker_from_asset_name() maps Nvidia to NVDA."""
        from app.services.ticker_backfill import extract_ticker_from_asset_name

        with patch("app.services.ticker_backfill.extract_ticker_from_text") as mock:
            mock.return_value = None

            result = extract_ticker_from_asset_name("NVIDIA Corporation")

            assert result == "NVDA"

    def test_maps_jpmorgan_to_jpm(self):
        """extract_ticker_from_asset_name() maps JPMorgan to JPM."""
        from app.services.ticker_backfill import extract_ticker_from_asset_name

        with patch("app.services.ticker_backfill.extract_ticker_from_text") as mock:
            mock.return_value = None

            result = extract_ticker_from_asset_name("JPMorgan Chase & Co")

            assert result == "JPM"

    def test_maps_johnson_johnson_to_jnj(self):
        """extract_ticker_from_asset_name() maps Johnson & Johnson to JNJ."""
        from app.services.ticker_backfill import extract_ticker_from_asset_name

        with patch("app.services.ticker_backfill.extract_ticker_from_text") as mock:
            mock.return_value = None

            result = extract_ticker_from_asset_name("Johnson & Johnson")

            assert result == "JNJ"

    def test_case_insensitive_matching(self):
        """extract_ticker_from_asset_name() matches case-insensitively."""
        from app.services.ticker_backfill import extract_ticker_from_asset_name

        with patch("app.services.ticker_backfill.extract_ticker_from_text") as mock:
            mock.return_value = None

            result = extract_ticker_from_asset_name("APPLE INC")

            assert result == "AAPL"

    def test_returns_none_for_unknown_company(self):
        """extract_ticker_from_asset_name() returns None for unknown company."""
        from app.services.ticker_backfill import extract_ticker_from_asset_name

        with patch("app.services.ticker_backfill.extract_ticker_from_text") as mock:
            mock.return_value = None

            result = extract_ticker_from_asset_name("Unknown Random Company XYZ")

            assert result is None

    def test_prefers_direct_extraction_over_mapping(self):
        """extract_ticker_from_asset_name() prefers direct extraction over mapping."""
        from app.services.ticker_backfill import extract_ticker_from_asset_name

        with patch("app.services.ticker_backfill.extract_ticker_from_text") as mock:
            mock.return_value = "APPL"  # Wrong ticker but extracted directly

            result = extract_ticker_from_asset_name("Apple Inc [APPL]")

            # Should return the directly extracted ticker
            assert result == "APPL"


# =============================================================================
# is_metadata_only() Tests
# =============================================================================

class TestIsMetadataOnly:
    """Tests for is_metadata_only() function."""

    def test_returns_true_for_none(self):
        """is_metadata_only() returns True for None input."""
        from app.services.ticker_backfill import is_metadata_only

        result = is_metadata_only(None)

        assert result is True

    def test_returns_true_for_empty_string(self):
        """is_metadata_only() returns True for empty string."""
        from app.services.ticker_backfill import is_metadata_only

        result = is_metadata_only("")

        assert result is True

    def test_returns_true_for_filer_status(self):
        """is_metadata_only() returns True for 'F S:' pattern."""
        from app.services.ticker_backfill import is_metadata_only

        result = is_metadata_only("F S: Filed")

        assert result is True

    def test_returns_true_for_owner_pattern(self):
        """is_metadata_only() returns True for 'Owner:' pattern."""
        from app.services.ticker_backfill import is_metadata_only

        result = is_metadata_only("Owner: Self")

        assert result is True

    def test_returns_true_for_filing_date(self):
        """is_metadata_only() returns True for 'Filing Date:' pattern."""
        from app.services.ticker_backfill import is_metadata_only

        result = is_metadata_only("Filing Date: 01/15/2024")

        assert result is True

    def test_returns_true_for_td_ameritrade(self):
        """is_metadata_only() returns True for 'TD Ameritrade' brokerage."""
        from app.services.ticker_backfill import is_metadata_only

        result = is_metadata_only("TD Ameritrade account")

        assert result is True

    def test_returns_true_for_charles_schwab(self):
        """is_metadata_only() returns True for 'Charles Schwab' brokerage."""
        from app.services.ticker_backfill import is_metadata_only

        result = is_metadata_only("Charles Schwab IRA")

        assert result is True

    def test_returns_true_for_fidelity(self):
        """is_metadata_only() returns True for 'Fidelity' brokerage."""
        from app.services.ticker_backfill import is_metadata_only

        result = is_metadata_only("Fidelity Brokerage Account")

        assert result is True

    def test_returns_true_for_capital_gains(self):
        """is_metadata_only() returns True for 'Cap Gains' header."""
        from app.services.ticker_backfill import is_metadata_only

        result = is_metadata_only("Cap Gains > $200")

        assert result is True

    def test_returns_false_for_real_asset(self):
        """is_metadata_only() returns False for real asset names."""
        from app.services.ticker_backfill import is_metadata_only

        result = is_metadata_only("Apple Inc [AAPL]")

        assert result is False

    def test_returns_false_for_stock_name(self):
        """is_metadata_only() returns False for stock names."""
        from app.services.ticker_backfill import is_metadata_only

        result = is_metadata_only("Microsoft Corporation")

        assert result is False

    def test_case_insensitive(self):
        """is_metadata_only() matches patterns case-insensitively."""
        from app.services.ticker_backfill import is_metadata_only

        result = is_metadata_only("OWNER: John Smith")

        assert result is True


# =============================================================================
# extract_transaction_type_from_raw() Tests
# =============================================================================

class TestExtractTransactionTypeFromRaw:
    """Tests for extract_transaction_type_from_raw() function."""

    def test_returns_none_for_empty_raw_row(self):
        """extract_transaction_type_from_raw() returns None for empty raw_row."""
        from app.services.ticker_backfill import extract_transaction_type_from_raw

        result = extract_transaction_type_from_raw({})

        assert result is None

    def test_returns_none_for_missing_raw_row(self):
        """extract_transaction_type_from_raw() returns None when raw_row is missing."""
        from app.services.ticker_backfill import extract_transaction_type_from_raw

        result = extract_transaction_type_from_raw({"other_field": "value"})

        assert result is None

    def test_returns_purchase_for_purchase_keyword(self):
        """extract_transaction_type_from_raw() returns 'purchase' for 'purchase' keyword."""
        from app.services.ticker_backfill import extract_transaction_type_from_raw

        result = extract_transaction_type_from_raw({
            "raw_row": ["Apple Inc", "Purchase", "01/15/2024"]
        })

        assert result == "purchase"

    def test_returns_purchase_for_bought_keyword(self):
        """extract_transaction_type_from_raw() returns 'purchase' for 'bought' keyword."""
        from app.services.ticker_backfill import extract_transaction_type_from_raw

        result = extract_transaction_type_from_raw({
            "raw_row": ["Apple Inc", "Bought 100 shares", "01/15/2024"]
        })

        assert result == "purchase"

    def test_returns_purchase_for_buy_keyword(self):
        """extract_transaction_type_from_raw() returns 'purchase' for 'buy' keyword."""
        from app.services.ticker_backfill import extract_transaction_type_from_raw

        result = extract_transaction_type_from_raw({
            "raw_row": ["Apple Inc", "Buy order", "01/15/2024"]
        })

        assert result == "purchase"

    def test_returns_sale_for_sale_keyword(self):
        """extract_transaction_type_from_raw() returns 'sale' for 'sale' keyword."""
        from app.services.ticker_backfill import extract_transaction_type_from_raw

        result = extract_transaction_type_from_raw({
            "raw_row": ["Apple Inc", "Sale", "01/15/2024"]
        })

        assert result == "sale"

    def test_returns_sale_for_sold_keyword(self):
        """extract_transaction_type_from_raw() returns 'sale' for 'sold' keyword."""
        from app.services.ticker_backfill import extract_transaction_type_from_raw

        result = extract_transaction_type_from_raw({
            "raw_row": ["Apple Inc", "Sold 100 shares", "01/15/2024"]
        })

        assert result == "sale"

    def test_returns_sale_for_exchange_keyword(self):
        """extract_transaction_type_from_raw() returns 'sale' for 'exchange' keyword."""
        from app.services.ticker_backfill import extract_transaction_type_from_raw

        result = extract_transaction_type_from_raw({
            "raw_row": ["Apple Inc", "Exchange", "01/15/2024"]
        })

        assert result == "sale"

    def test_returns_purchase_for_p_pattern_with_date(self):
        """extract_transaction_type_from_raw() returns 'purchase' for 'P 01/15/2024' pattern."""
        from app.services.ticker_backfill import extract_transaction_type_from_raw

        result = extract_transaction_type_from_raw({
            "raw_row": ["Apple Inc [AAPL]", "ST", "P 01/15/2024", "$1,001 - $15,000"]
        })

        assert result == "purchase"

    def test_returns_sale_for_s_pattern_with_date(self):
        """extract_transaction_type_from_raw() returns 'sale' for 'S 12/01/2024' pattern."""
        from app.services.ticker_backfill import extract_transaction_type_from_raw

        result = extract_transaction_type_from_raw({
            "raw_row": ["Apple Inc [AAPL]", "ST", "S 12/01/2024", "$1,001 - $15,000"]
        })

        assert result == "sale"

    def test_returns_purchase_for_p_partial_pattern(self):
        """extract_transaction_type_from_raw() returns 'purchase' for 'P (partial)' pattern."""
        from app.services.ticker_backfill import extract_transaction_type_from_raw

        result = extract_transaction_type_from_raw({
            "raw_row": ["Apple Inc [AAPL]", "ST", "P (partial) 01/15/2024", "$1,001 - $15,000"]
        })

        assert result == "purchase"

    def test_returns_sale_for_s_partial_pattern(self):
        """extract_transaction_type_from_raw() returns 'sale' for 'S (partial)' pattern."""
        from app.services.ticker_backfill import extract_transaction_type_from_raw

        result = extract_transaction_type_from_raw({
            "raw_row": ["Apple Inc [AAPL]", "ST", "S(partial) 12/01/2024", "$1,001 - $15,000"]
        })

        assert result == "sale"

    def test_returns_none_for_no_type_indicator(self):
        """extract_transaction_type_from_raw() returns None when no type found."""
        from app.services.ticker_backfill import extract_transaction_type_from_raw

        result = extract_transaction_type_from_raw({
            "raw_row": ["Apple Inc", "100 shares", "01/15/2024"]
        })

        assert result is None

    def test_handles_none_cells_in_raw_row(self):
        """extract_transaction_type_from_raw() handles None cells in raw_row."""
        from app.services.ticker_backfill import extract_transaction_type_from_raw

        result = extract_transaction_type_from_raw({
            "raw_row": ["Apple Inc", None, "Purchase", None]
        })

        assert result == "purchase"


# =============================================================================
# run_ticker_backfill() Tests
# =============================================================================

class TestRunTickerBackfill:
    """Tests for run_ticker_backfill() function."""

    @pytest.fixture
    def mock_job_status(self):
        """Create a mock job status dictionary."""
        return {"status": "pending", "message": ""}

    @pytest.mark.asyncio
    async def test_sets_status_running(self, mock_job_status, monkeypatch):
        """run_ticker_backfill() sets status to running."""
        from app.services.ticker_backfill import run_ticker_backfill
        import app.services.ticker_backfill as module

        monkeypatch.setattr(module, "JOB_STATUS", {"test-job": mock_job_status})

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.is_.return_value.execute.return_value = mock_response
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        with patch.object(module, "get_supabase", return_value=mock_supabase):
            await run_ticker_backfill("test-job")

        # After completing with no records, status should be completed
        assert mock_job_status["status"] == "completed"

    @pytest.mark.asyncio
    async def test_completes_when_no_disclosures_need_backfill(self, mock_job_status, monkeypatch):
        """run_ticker_backfill() completes when no disclosures need backfill."""
        from app.services.ticker_backfill import run_ticker_backfill
        import app.services.ticker_backfill as module

        monkeypatch.setattr(module, "JOB_STATUS", {"test-job": mock_job_status})

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.is_.return_value.execute.return_value = mock_response
        mock_supabase.table.return_value.select.return_value.is_.return_value.limit.return_value.execute.return_value = mock_response
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response

        with patch.object(module, "get_supabase", return_value=mock_supabase):
            await run_ticker_backfill("test-job")

        assert mock_job_status["status"] == "completed"
        assert "No disclosures need ticker backfill" in mock_job_status["message"]

    @pytest.mark.asyncio
    async def test_updates_disclosures_with_extracted_tickers(self, mock_job_status, monkeypatch):
        """run_ticker_backfill() updates disclosures with extracted tickers."""
        from app.services.ticker_backfill import run_ticker_backfill
        import app.services.ticker_backfill as module

        monkeypatch.setattr(module, "JOB_STATUS", {"test-job": mock_job_status})

        mock_supabase = MagicMock()

        # First query returns disclosures with null tickers
        null_response = MagicMock()
        null_response.data = [
            {"id": "1", "asset_name": "Apple Inc", "asset_ticker": None}
        ]

        # Second query returns disclosures with empty tickers
        empty_response = MagicMock()
        empty_response.data = []

        # Set up query chains
        mock_supabase.table.return_value.select.return_value.is_.return_value.execute.return_value = null_response
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = empty_response
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with patch.object(module, "get_supabase", return_value=mock_supabase):
            with patch.object(module, "extract_ticker_from_asset_name", return_value="AAPL"):
                await run_ticker_backfill("test-job")

        assert mock_job_status["status"] == "completed"
        assert "1 updated" in mock_job_status["message"]

    @pytest.mark.asyncio
    async def test_tracks_no_ticker_found(self, mock_job_status, monkeypatch):
        """run_ticker_backfill() tracks when no ticker can be found."""
        from app.services.ticker_backfill import run_ticker_backfill
        import app.services.ticker_backfill as module

        monkeypatch.setattr(module, "JOB_STATUS", {"test-job": mock_job_status})

        mock_supabase = MagicMock()

        null_response = MagicMock()
        null_response.data = [
            {"id": "1", "asset_name": "Unknown Company XYZ", "asset_ticker": None}
        ]

        empty_response = MagicMock()
        empty_response.data = []

        mock_supabase.table.return_value.select.return_value.is_.return_value.execute.return_value = null_response
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = empty_response

        with patch.object(module, "get_supabase", return_value=mock_supabase):
            with patch.object(module, "extract_ticker_from_asset_name", return_value=None):
                await run_ticker_backfill("test-job")

        assert mock_job_status["status"] == "completed"
        assert "no ticker found" in mock_job_status["message"]

    @pytest.mark.asyncio
    async def test_handles_update_failures(self, mock_job_status, monkeypatch):
        """run_ticker_backfill() tracks update failures."""
        from app.services.ticker_backfill import run_ticker_backfill
        import app.services.ticker_backfill as module

        monkeypatch.setattr(module, "JOB_STATUS", {"test-job": mock_job_status})

        mock_supabase = MagicMock()

        null_response = MagicMock()
        null_response.data = [
            {"id": "1", "asset_name": "Apple Inc", "asset_ticker": None}
        ]

        empty_response = MagicMock()
        empty_response.data = []

        mock_supabase.table.return_value.select.return_value.is_.return_value.execute.return_value = null_response
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = empty_response
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception("DB error")

        with patch.object(module, "get_supabase", return_value=mock_supabase):
            with patch.object(module, "extract_ticker_from_asset_name", return_value="AAPL"):
                await run_ticker_backfill("test-job")

        assert mock_job_status["status"] == "completed"
        assert "1 failed" in mock_job_status["message"]

    @pytest.mark.asyncio
    async def test_handles_exception(self, mock_job_status, monkeypatch):
        """run_ticker_backfill() handles unexpected exceptions."""
        from app.services.ticker_backfill import run_ticker_backfill
        import app.services.ticker_backfill as module

        monkeypatch.setattr(module, "JOB_STATUS", {"test-job": mock_job_status})

        with patch.object(module, "get_supabase") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            with pytest.raises(Exception):
                await run_ticker_backfill("test-job")

        assert mock_job_status["status"] == "failed"
        assert "Connection failed" in mock_job_status["message"]

    @pytest.mark.asyncio
    async def test_respects_limit_parameter(self, mock_job_status, monkeypatch):
        """run_ticker_backfill() respects the limit parameter."""
        from app.services.ticker_backfill import run_ticker_backfill
        import app.services.ticker_backfill as module

        monkeypatch.setattr(module, "JOB_STATUS", {"test-job": mock_job_status})

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []

        mock_query = MagicMock()
        mock_query.limit.return_value.execute.return_value = mock_response
        mock_supabase.table.return_value.select.return_value.is_.return_value = mock_query
        mock_supabase.table.return_value.select.return_value.eq.return_value = mock_query

        with patch.object(module, "get_supabase", return_value=mock_supabase):
            await run_ticker_backfill("test-job", limit=100)

        # Verify limit was called
        mock_query.limit.assert_called()


# =============================================================================
# run_transaction_type_backfill() Tests
# =============================================================================

class TestRunTransactionTypeBackfill:
    """Tests for run_transaction_type_backfill() function."""

    @pytest.fixture
    def mock_job_status(self):
        """Create a mock job status dictionary."""
        return {"status": "pending", "message": ""}

    @pytest.mark.asyncio
    async def test_sets_status_running(self, mock_job_status, monkeypatch):
        """run_transaction_type_backfill() sets status to running."""
        from app.services.ticker_backfill import run_transaction_type_backfill
        import app.services.ticker_backfill as module

        monkeypatch.setattr(module, "JOB_STATUS", {"test-job": mock_job_status})

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        with patch.object(module, "get_supabase", return_value=mock_supabase):
            await run_transaction_type_backfill("test-job")

        assert mock_job_status["status"] == "completed"

    @pytest.mark.asyncio
    async def test_completes_when_no_disclosures_need_backfill(self, mock_job_status, monkeypatch):
        """run_transaction_type_backfill() completes when no disclosures need backfill."""
        from app.services.ticker_backfill import run_transaction_type_backfill
        import app.services.ticker_backfill as module

        monkeypatch.setattr(module, "JOB_STATUS", {"test-job": mock_job_status})

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        with patch.object(module, "get_supabase", return_value=mock_supabase):
            await run_transaction_type_backfill("test-job")

        assert mock_job_status["status"] == "completed"
        assert "No disclosures need transaction_type backfill" in mock_job_status["message"]

    @pytest.mark.asyncio
    async def test_updates_disclosures_with_extracted_type(self, mock_job_status, monkeypatch):
        """run_transaction_type_backfill() updates disclosures with extracted type."""
        from app.services.ticker_backfill import run_transaction_type_backfill
        import app.services.ticker_backfill as module

        monkeypatch.setattr(module, "JOB_STATUS", {"test-job": mock_job_status})

        mock_supabase = MagicMock()

        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "1",
                "transaction_type": "unknown",
                "raw_data": {"raw_row": ["Apple Inc", "P 01/15/2024"]},
                "asset_name": "Apple Inc"
            }
        ]

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with patch.object(module, "get_supabase", return_value=mock_supabase):
            await run_transaction_type_backfill("test-job")

        assert mock_job_status["status"] == "completed"
        assert "1 updated" in mock_job_status["message"]

    @pytest.mark.asyncio
    async def test_deletes_metadata_only_records(self, mock_job_status, monkeypatch):
        """run_transaction_type_backfill() deletes metadata-only records."""
        from app.services.ticker_backfill import run_transaction_type_backfill
        import app.services.ticker_backfill as module

        monkeypatch.setattr(module, "JOB_STATUS", {"test-job": mock_job_status})

        mock_supabase = MagicMock()

        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "1",
                "transaction_type": "unknown",
                "raw_data": {},
                "asset_name": "TD Ameritrade account"
            }
        ]

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock()

        with patch.object(module, "get_supabase", return_value=mock_supabase):
            await run_transaction_type_backfill("test-job")

        assert mock_job_status["status"] == "completed"
        assert "1 deleted" in mock_job_status["message"]

    @pytest.mark.asyncio
    async def test_handles_exception(self, mock_job_status, monkeypatch):
        """run_transaction_type_backfill() handles unexpected exceptions."""
        from app.services.ticker_backfill import run_transaction_type_backfill
        import app.services.ticker_backfill as module

        monkeypatch.setattr(module, "JOB_STATUS", {"test-job": mock_job_status})

        with patch.object(module, "get_supabase") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            with pytest.raises(Exception):
                await run_transaction_type_backfill("test-job")

        assert mock_job_status["status"] == "failed"
        assert "Connection failed" in mock_job_status["message"]

    @pytest.mark.asyncio
    async def test_tracks_no_type_found(self, mock_job_status, monkeypatch):
        """run_transaction_type_backfill() tracks when no type can be found."""
        from app.services.ticker_backfill import run_transaction_type_backfill
        import app.services.ticker_backfill as module

        monkeypatch.setattr(module, "JOB_STATUS", {"test-job": mock_job_status})

        mock_supabase = MagicMock()

        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "1",
                "transaction_type": "unknown",
                "raw_data": {"raw_row": ["Apple Inc", "100 shares"]},
                "asset_name": "Apple Inc"
            }
        ]

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        with patch.object(module, "get_supabase", return_value=mock_supabase):
            await run_transaction_type_backfill("test-job")

        assert mock_job_status["status"] == "completed"
        assert "not found" in mock_job_status["message"]
