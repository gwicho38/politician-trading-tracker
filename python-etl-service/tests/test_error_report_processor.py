"""
Tests for Error Report Processor Service.

Tests cover:
- CorrectionProposal and ProcessingResult dataclasses
- ErrorReportProcessor class methods
- Party normalization
- Report processing logic
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.services.error_report_processor import (
    CorrectionProposal,
    ProcessingResult,
    ErrorReportProcessor,
    DEFAULT_MODEL,
)


class TestCorrectionProposal:
    """Tests for CorrectionProposal dataclass."""

    def test_creation(self):
        """Test basic creation of CorrectionProposal."""
        proposal = CorrectionProposal(
            field="asset_ticker",
            old_value="APPL",
            new_value="AAPL",
            confidence=0.95,
            reasoning="Typo correction"
        )

        assert proposal.field == "asset_ticker"
        assert proposal.old_value == "APPL"
        assert proposal.new_value == "AAPL"
        assert proposal.confidence == 0.95
        assert proposal.reasoning == "Typo correction"

    def test_numeric_values(self):
        """Test CorrectionProposal with numeric values."""
        proposal = CorrectionProposal(
            field="amount_range_min",
            old_value=1000,
            new_value=10000,
            confidence=0.85,
            reasoning="Missing zero"
        )

        assert proposal.old_value == 1000
        assert proposal.new_value == 10000


class TestProcessingResult:
    """Tests for ProcessingResult dataclass."""

    def test_creation(self):
        """Test basic creation of ProcessingResult."""
        result = ProcessingResult(
            report_id="report-123",
            status="fixed",
            corrections=[],
            admin_notes="No corrections needed"
        )

        assert result.report_id == "report-123"
        assert result.status == "fixed"
        assert result.corrections == []
        assert result.admin_notes == "No corrections needed"

    def test_with_corrections(self):
        """Test ProcessingResult with corrections list."""
        corrections = [
            CorrectionProposal(
                field="asset_ticker",
                old_value="APPL",
                new_value="AAPL",
                confidence=0.9,
                reasoning="Typo"
            )
        ]

        result = ProcessingResult(
            report_id="report-456",
            status="fixed",
            corrections=corrections,
            admin_notes="Applied 1 correction"
        )

        assert len(result.corrections) == 1
        assert result.corrections[0].field == "asset_ticker"


class TestErrorReportProcessorInit:
    """Tests for ErrorReportProcessor initialization."""

    def test_init_default_model(self):
        """Test initialization with default model."""
        with patch("app.services.error_report_processor.get_supabase") as mock_supabase:
            mock_supabase.return_value = MagicMock()

            processor = ErrorReportProcessor()

            assert processor.model == DEFAULT_MODEL

    def test_init_custom_model(self):
        """Test initialization with custom model."""
        with patch("app.services.error_report_processor.get_supabase") as mock_supabase:
            mock_supabase.return_value = MagicMock()

            processor = ErrorReportProcessor(model="custom-model")

            assert processor.model == "custom-model"


class TestErrorReportProcessorTestConnection:
    """Tests for ErrorReportProcessor.test_connection method."""

    @pytest.fixture
    def processor(self):
        """Create processor with mocked dependencies."""
        with patch("app.services.error_report_processor.get_supabase") as mock_supabase:
            mock_supabase.return_value = MagicMock()
            return ErrorReportProcessor()

    def test_connection_success(self, processor):
        """Test successful connection."""
        processor.ollama_client = MagicMock()
        processor.ollama_client.get.return_value = MagicMock(status_code=200)

        result = processor.test_connection()

        assert result is True

    def test_connection_failure_status(self, processor):
        """Test connection failure due to status code."""
        processor.ollama_client = MagicMock()
        processor.ollama_client.get.return_value = MagicMock(status_code=500)

        result = processor.test_connection()

        assert result is False

    def test_connection_exception(self, processor):
        """Test connection failure due to exception."""
        processor.ollama_client = MagicMock()
        processor.ollama_client.get.side_effect = Exception("Connection refused")

        result = processor.test_connection()

        assert result is False


class TestErrorReportProcessorGetPendingReports:
    """Tests for ErrorReportProcessor.get_pending_reports method."""

    @pytest.fixture
    def processor(self):
        """Create processor with mocked dependencies."""
        with patch("app.services.error_report_processor.get_supabase") as mock_supabase:
            mock_supabase.return_value = MagicMock()
            return ErrorReportProcessor()

    def test_get_pending_reports_success(self, processor):
        """Test successful fetch of pending reports."""
        mock_data = [
            {"id": "1", "description": "Wrong ticker"},
            {"id": "2", "description": "Wrong amount"},
        ]
        processor.supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_data
        )

        result = processor.get_pending_reports(limit=10)

        assert len(result) == 2
        assert result[0]["id"] == "1"

    def test_get_pending_reports_empty(self, processor):
        """Test when no pending reports."""
        processor.supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result = processor.get_pending_reports()

        assert result == []

    def test_get_pending_reports_no_supabase(self, processor):
        """Test when supabase is None."""
        processor.supabase = None

        result = processor.get_pending_reports()

        assert result == []

    def test_get_pending_reports_exception(self, processor):
        """Test exception handling."""
        processor.supabase.table.side_effect = Exception("Database error")

        result = processor.get_pending_reports()

        assert result == []


class TestErrorReportProcessorNormalizeParty:
    """Tests for ErrorReportProcessor._normalize_party method."""

    @pytest.fixture
    def processor(self):
        """Create processor with mocked dependencies."""
        with patch("app.services.error_report_processor.get_supabase") as mock_supabase:
            mock_supabase.return_value = MagicMock()
            return ErrorReportProcessor()

    def test_normalize_democrat_variations(self, processor):
        """Test normalizing Democrat variations."""
        assert processor._normalize_party("Democrat") == "D"
        assert processor._normalize_party("Democratic") == "D"
        assert processor._normalize_party("DEM") == "D"
        assert processor._normalize_party("d") == "D"
        assert processor._normalize_party("  democrat  ") == "D"

    def test_normalize_republican_variations(self, processor):
        """Test normalizing Republican variations."""
        assert processor._normalize_party("Republican") == "R"
        assert processor._normalize_party("GOP") == "R"
        assert processor._normalize_party("REP") == "R"
        assert processor._normalize_party("r") == "R"

    def test_normalize_independent_variations(self, processor):
        """Test normalizing Independent variations."""
        assert processor._normalize_party("Independent") == "I"
        assert processor._normalize_party("IND") == "I"
        assert processor._normalize_party("i") == "I"

    def test_normalize_unknown_party(self, processor):
        """Test unknown party returned as-is."""
        assert processor._normalize_party("Green") == "Green"
        assert processor._normalize_party("Libertarian") == "Libertarian"


class TestErrorReportProcessorBuildPrompt:
    """Tests for ErrorReportProcessor._build_prompt method."""

    @pytest.fixture
    def processor(self):
        """Create processor with mocked dependencies."""
        with patch("app.services.error_report_processor.get_supabase") as mock_supabase:
            mock_supabase.return_value = MagicMock()
            return ErrorReportProcessor()

    def test_build_prompt_includes_error_type(self, processor):
        """Test prompt includes error type."""
        report = {
            "error_type": "wrong_ticker",
            "description": "Should be AAPL not APPL",
            "disclosure_snapshot": {}
        }

        prompt = processor._build_prompt(report)

        assert "wrong_ticker" in prompt

    def test_build_prompt_includes_description(self, processor):
        """Test prompt includes user description."""
        report = {
            "error_type": "wrong_amount",
            "description": "Amount is $5,000,000 not $500,000",
            "disclosure_snapshot": {}
        }

        prompt = processor._build_prompt(report)

        assert "$5,000,000" in prompt

    def test_build_prompt_includes_snapshot(self, processor):
        """Test prompt includes disclosure snapshot."""
        report = {
            "error_type": "wrong_ticker",
            "description": "Fix ticker",
            "disclosure_snapshot": {
                "asset_ticker": "APPL",
                "amount_range_min": 1000
            }
        }

        prompt = processor._build_prompt(report)

        assert "APPL" in prompt


class TestErrorReportProcessorInterpretCorrections:
    """Tests for ErrorReportProcessor.interpret_corrections method."""

    @pytest.fixture
    def processor(self):
        """Create processor with mocked dependencies."""
        with patch("app.services.error_report_processor.get_supabase") as mock_supabase:
            mock_supabase.return_value = MagicMock()
            return ErrorReportProcessor()

    def test_interpret_success(self, processor):
        """Test successful correction interpretation."""
        llm_response = {
            "corrections": [
                {
                    "field": "asset_ticker",
                    "old_value": "APPL",
                    "new_value": "AAPL",
                    "confidence": 0.95,
                    "reasoning": "Common typo"
                }
            ]
        }

        processor.ollama_client = MagicMock()
        processor.ollama_client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"response": json.dumps(llm_response)}
        )

        report = {"error_type": "wrong_ticker", "description": "Typo", "disclosure_snapshot": {}}
        result = processor.interpret_corrections(report)

        assert len(result) == 1
        assert result[0].field == "asset_ticker"
        assert result[0].new_value == "AAPL"
        assert result[0].confidence == 0.95

    def test_interpret_empty_corrections(self, processor):
        """Test interpretation returns empty list for no corrections."""
        llm_response = {"corrections": []}

        processor.ollama_client = MagicMock()
        processor.ollama_client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"response": json.dumps(llm_response)}
        )

        report = {"error_type": "other", "description": "Unclear", "disclosure_snapshot": {}}
        result = processor.interpret_corrections(report)

        assert result == []

    def test_interpret_http_error(self, processor):
        """Test interpretation handles HTTP errors."""
        processor.ollama_client = MagicMock()
        processor.ollama_client.post.return_value = MagicMock(
            status_code=500,
            text="Internal Server Error"
        )

        report = {"error_type": "wrong_ticker", "description": "Fix", "disclosure_snapshot": {}}
        result = processor.interpret_corrections(report)

        assert result == []

    def test_interpret_json_error(self, processor):
        """Test interpretation handles JSON decode errors."""
        processor.ollama_client = MagicMock()
        processor.ollama_client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"response": "not valid json {"}
        )

        report = {"error_type": "wrong_ticker", "description": "Fix", "disclosure_snapshot": {}}
        result = processor.interpret_corrections(report)

        assert result == []

    def test_interpret_exception(self, processor):
        """Test interpretation handles general exceptions."""
        processor.ollama_client = MagicMock()
        processor.ollama_client.post.side_effect = Exception("Connection timeout")

        report = {"error_type": "wrong_ticker", "description": "Fix", "disclosure_snapshot": {}}
        result = processor.interpret_corrections(report)

        assert result == []


class TestErrorReportProcessorProcessReport:
    """Tests for ErrorReportProcessor.process_report method."""

    @pytest.fixture
    def processor(self):
        """Create processor with mocked dependencies."""
        with patch("app.services.error_report_processor.get_supabase") as mock_supabase:
            mock_supabase.return_value = MagicMock()
            processor = ErrorReportProcessor()
            processor.ollama_client = MagicMock()
            return processor

    def test_process_no_corrections(self, processor):
        """Test processing when no corrections can be determined."""
        processor.ollama_client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"response": json.dumps({"corrections": []})}
        )

        report = {"id": "report-1", "error_type": "other", "description": "Unclear", "disclosure_snapshot": {}}
        result = processor.process_report(report, dry_run=True)

        assert result.status == "needs_review"
        assert len(result.corrections) == 0

    def test_process_low_confidence(self, processor):
        """Test processing with low confidence corrections."""
        llm_response = {
            "corrections": [
                {"field": "asset_ticker", "old_value": "X", "new_value": "AAPL", "confidence": 0.5, "reasoning": "Guess"}
            ]
        }
        processor.ollama_client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"response": json.dumps(llm_response)}
        )

        report = {"id": "report-2", "error_type": "wrong_ticker", "description": "Maybe", "disclosure_snapshot": {}}
        result = processor.process_report(report, dry_run=True)

        assert result.status == "needs_review"
        assert len(result.corrections) == 1
        assert "low confidence" in result.admin_notes.lower()

    def test_process_high_confidence_dry_run(self, processor):
        """Test processing high confidence corrections in dry run mode."""
        llm_response = {
            "corrections": [
                {"field": "asset_ticker", "old_value": "APPL", "new_value": "AAPL", "confidence": 0.95, "reasoning": "Typo"}
            ]
        }
        processor.ollama_client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"response": json.dumps(llm_response)}
        )

        report = {"id": "report-3", "error_type": "wrong_ticker", "description": "AAPL not APPL", "disclosure_snapshot": {}}
        result = processor.process_report(report, dry_run=True)

        assert result.status == "fixed"
        assert len(result.corrections) == 1


class TestErrorReportProcessorApplyCorrections:
    """Tests for ErrorReportProcessor._apply_corrections method."""

    @pytest.fixture
    def processor(self):
        """Create processor with mocked dependencies."""
        with patch("app.services.error_report_processor.get_supabase") as mock_supabase:
            mock_supabase.return_value = MagicMock()
            return ErrorReportProcessor()

    def test_apply_no_supabase(self, processor):
        """Test apply returns False when no supabase."""
        processor.supabase = None

        result = processor._apply_corrections("disc-1", [])

        assert result is False

    def test_apply_no_disclosure_id(self, processor):
        """Test apply returns False with no disclosure_id."""
        result = processor._apply_corrections(None, [])

        assert result is False

    def test_apply_disclosure_updates(self, processor):
        """Test applying disclosure field updates."""
        corrections = [
            CorrectionProposal(
                field="asset_ticker",
                old_value="APPL",
                new_value="AAPL",
                confidence=0.9,
                reasoning="Typo"
            )
        ]

        processor.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        result = processor._apply_corrections("disc-123", corrections)

        assert result is True
        processor.supabase.table.assert_called()

    def test_apply_politician_updates(self, processor):
        """Test applying politician field updates."""
        corrections = [
            CorrectionProposal(
                field="politician_party",
                old_value="Democrat",
                new_value="Republican",
                confidence=0.9,
                reasoning="Wrong party"
            )
        ]

        # Mock disclosure query to get politician_id
        processor.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"politician_id": "pol-123"}
        )
        processor.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        result = processor._apply_corrections("disc-123", corrections)

        assert result is True

    def test_apply_politician_updates_no_politician_id(self, processor):
        """Test apply returns False when no politician_id found."""
        corrections = [
            CorrectionProposal(
                field="politician_party",
                old_value="D",
                new_value="R",
                confidence=0.9,
                reasoning="Wrong"
            )
        ]

        processor.supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={}
        )

        result = processor._apply_corrections("disc-123", corrections)

        assert result is False

    def test_apply_exception(self, processor):
        """Test apply handles exceptions."""
        corrections = [
            CorrectionProposal(
                field="asset_ticker",
                old_value="X",
                new_value="Y",
                confidence=0.9,
                reasoning="Fix"
            )
        ]

        processor.supabase.table.side_effect = Exception("DB error")

        result = processor._apply_corrections("disc-123", corrections)

        assert result is False


class TestErrorReportProcessorUpdateReportStatus:
    """Tests for ErrorReportProcessor._update_report_status method."""

    @pytest.fixture
    def processor(self):
        """Create processor with mocked dependencies."""
        with patch("app.services.error_report_processor.get_supabase") as mock_supabase:
            mock_supabase.return_value = MagicMock()
            return ErrorReportProcessor()

    def test_update_status_no_supabase(self, processor):
        """Test update does nothing when no supabase."""
        processor.supabase = None

        # Should not raise
        processor._update_report_status("report-1", "fixed", "Done")

    def test_update_status_success(self, processor):
        """Test successful status update."""
        processor.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        processor._update_report_status("report-1", "fixed", "Applied correction")

        processor.supabase.table.assert_called_with("user_error_reports")

    def test_update_status_exception(self, processor):
        """Test update handles exceptions gracefully."""
        processor.supabase.table.side_effect = Exception("DB error")

        # Should not raise
        processor._update_report_status("report-1", "fixed", "Done")


class TestErrorReportProcessorProcessAllPending:
    """Tests for ErrorReportProcessor.process_all_pending method."""

    @pytest.fixture
    def processor(self):
        """Create processor with mocked dependencies."""
        with patch("app.services.error_report_processor.get_supabase") as mock_supabase:
            mock_supabase.return_value = MagicMock()
            processor = ErrorReportProcessor()
            processor.ollama_client = MagicMock()
            return processor

    def test_process_all_no_reports(self, processor):
        """Test processing with no pending reports."""
        processor.supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result = processor.process_all_pending()

        assert result["processed"] == 0
        assert result["fixed"] == 0
        assert result["needs_review"] == 0
        assert result["errors"] == 0
        assert result["results"] == []

    def test_process_all_with_reports(self, processor):
        """Test processing multiple reports."""
        reports = [
            {"id": "1", "error_type": "wrong_ticker", "description": "Fix", "disclosure_snapshot": {}},
            {"id": "2", "error_type": "other", "description": "Unclear", "disclosure_snapshot": {}},
        ]

        processor.supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=reports
        )

        # First returns high confidence, second returns no corrections
        responses = [
            {"response": json.dumps({"corrections": [{"field": "asset_ticker", "old_value": "X", "new_value": "Y", "confidence": 0.95, "reasoning": "Fix"}]})},
            {"response": json.dumps({"corrections": []})},
        ]
        processor.ollama_client.post.return_value = MagicMock(
            status_code=200,
            json=lambda: responses.pop(0) if responses else {"response": "{}"}
        )

        result = processor.process_all_pending(dry_run=True)

        assert result["processed"] == 2

    def test_process_all_handles_exception(self, processor):
        """Test processing handles LLM errors gracefully."""
        reports = [
            {"id": "1", "error_type": "wrong_ticker", "description": "Fix", "disclosure_snapshot": {}},
        ]

        processor.supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=reports
        )
        # LLM exception is caught in interpret_corrections and returns empty list
        # This results in "needs_review" status, not "error"
        processor.ollama_client.post.side_effect = Exception("LLM crashed")

        result = processor.process_all_pending(dry_run=True)

        assert result["processed"] == 1
        # Empty corrections result in needs_review, not error
        assert result["needs_review"] == 1


class TestPoliticianFields:
    """Tests for POLITICIAN_FIELDS constant."""

    def test_politician_fields_defined(self):
        """Test POLITICIAN_FIELDS contains expected fields."""
        with patch("app.services.error_report_processor.get_supabase") as mock_supabase:
            mock_supabase.return_value = MagicMock()
            processor = ErrorReportProcessor()

            assert "politician_party" in processor.POLITICIAN_FIELDS
            assert "politician_name" in processor.POLITICIAN_FIELDS
            assert "state" in processor.POLITICIAN_FIELDS
            assert "chamber" in processor.POLITICIAN_FIELDS


class TestConfidenceThreshold:
    """Tests for CONFIDENCE_THRESHOLD constant."""

    def test_confidence_threshold_value(self):
        """Test CONFIDENCE_THRESHOLD is 0.8."""
        with patch("app.services.error_report_processor.get_supabase") as mock_supabase:
            mock_supabase.return_value = MagicMock()
            processor = ErrorReportProcessor()

            assert processor.CONFIDENCE_THRESHOLD == 0.8
