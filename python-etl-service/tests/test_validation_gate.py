"""
Tests for ValidationGateService — post-ingestion LLM batch validation.

Covers:
1. test_fetch_pending_queries_correct_filters — verifies Supabase query filters
2. test_batch_records_splits_correctly — 60 records -> 3 batches (25, 25, 10)
3. test_batch_records_single_batch — 10 records -> 1 batch
4. test_validate_batch_renders_prompt — checks template is rendered with batch JSON
5. test_validate_batch_calls_llm — verifies LLMClient.generate() called with correct model
6. test_apply_results_pass — updates status to 'pass' and sets llm_validated_at
7. test_apply_results_flag — updates status to 'flag' and inserts data_quality_issues
8. test_apply_results_reject — updates status to 'reject' and inserts data_quality_quarantine
9. test_validate_recent_end_to_end — full flow with mocked LLM returning mixed results
10. test_validate_recent_no_pending — returns zeros when no pending records
11. test_malformed_llm_response — handles bad JSON from LLM gracefully
"""

import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from app.services.llm.client import LLMClient, LLMResponse
from app.services.llm.audit_logger import LLMAuditLogger
from app.services.llm.validation_gate import ValidationGateService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_llm_client():
    """Mock LLMClient with async generate method."""
    client = AsyncMock(spec=LLMClient)
    client.generate = AsyncMock()
    return client


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client with chainable table methods."""
    client = MagicMock()
    return client


@pytest.fixture
def sample_pending_records():
    """Sample pending disclosure records as returned from Supabase."""
    return [
        {
            "id": f"disc-{i:03d}",
            "politician_id": f"pol-{i:03d}",
            "asset_name": f"Asset {i}",
            "asset_ticker": f"TKR{i}",
            "transaction_type": "purchase" if i % 2 == 0 else "sale",
            "transaction_date": "2026-02-15",
            "disclosure_date": "2026-02-18",
            "amount_range_min": 1001,
            "amount_range_max": 15000,
            "source_url": f"https://example.com/filing-{i}",
            "raw_data": {"source": "us_house"},
            "llm_validation_status": "pending",
        }
        for i in range(60)
    ]


@pytest.fixture
def sample_llm_pass_response():
    """LLM response where all records pass."""
    return LLMResponse(
        text=json.dumps({
            "batch_id": "batch-0",
            "validation_ts": "2026-02-20T12:00:00Z",
            "total_records": 3,
            "passed": 3,
            "flagged": 0,
            "rejected": 0,
            "records": [
                {"record_index": 0, "status": "pass", "confidence": 9, "flags": []},
                {"record_index": 1, "status": "pass", "confidence": 8, "flags": []},
                {"record_index": 2, "status": "pass", "confidence": 9, "flags": []},
            ],
            "batch_summary": "All records validated successfully.",
        }),
        model="qwen3:8b",
        input_tokens=500,
        output_tokens=200,
        latency_ms=1500,
    )


@pytest.fixture
def sample_llm_mixed_response():
    """LLM response with mixed pass/flag/reject verdicts."""
    return LLMResponse(
        text=json.dumps({
            "batch_id": "batch-0",
            "validation_ts": "2026-02-20T12:00:00Z",
            "total_records": 3,
            "passed": 1,
            "flagged": 1,
            "rejected": 1,
            "records": [
                {"record_index": 0, "status": "pass", "confidence": 9, "flags": []},
                {
                    "record_index": 1,
                    "status": "flag",
                    "confidence": 5,
                    "flags": [
                        {
                            "step": "semantic",
                            "field": "asset_ticker",
                            "severity": "warning",
                            "description": "Ticker mismatch",
                            "reasoning": "AAPL does not match 'Microsoft Corp'",
                            "suggested_action": "review",
                        }
                    ],
                },
                {
                    "record_index": 2,
                    "status": "reject",
                    "confidence": 3,
                    "flags": [
                        {
                            "step": "schema",
                            "field": "transaction_date",
                            "severity": "critical",
                            "description": "Invalid date",
                            "reasoning": "Transaction date is in the future",
                            "suggested_action": "reject",
                        }
                    ],
                },
            ],
            "batch_summary": "1 pass, 1 flagged, 1 rejected.",
        }),
        model="qwen3:8b",
        input_tokens=500,
        output_tokens=300,
        latency_ms=2000,
    )


def _build_service(mock_llm_client, mock_supabase_client):
    """Helper to construct a ValidationGateService with mocked deps."""
    service = ValidationGateService(
        llm_client=mock_llm_client,
        supabase=mock_supabase_client,
    )
    # Mock the audit logger to avoid real DB calls
    service.audit_logger = AsyncMock(spec=LLMAuditLogger)
    service.audit_logger.log = AsyncMock()
    service.audit_logger.compute_prompt_hash = MagicMock(return_value="abc123hash")
    return service


# =============================================================================
# Test 1: _fetch_pending queries correct filters
# =============================================================================


@pytest.mark.asyncio
async def test_fetch_pending_queries_correct_filters(mock_llm_client, mock_supabase_client):
    """_fetch_pending should query trading_disclosures with status='pending' and time filter."""
    # Set up chainable mock
    table_mock = MagicMock()
    select_mock = MagicMock()
    eq_mock = MagicMock()
    gte_mock = MagicMock()
    order_mock = MagicMock()
    limit_mock = MagicMock()

    mock_supabase_client.table.return_value = table_mock
    table_mock.select.return_value = select_mock
    select_mock.eq.return_value = eq_mock
    eq_mock.gte.return_value = gte_mock
    gte_mock.order.return_value = order_mock
    order_mock.limit.return_value = limit_mock
    limit_mock.execute.return_value = MagicMock(data=[])

    service = _build_service(mock_llm_client, mock_supabase_client)
    result = await service._fetch_pending()

    # Verify table called with correct name
    mock_supabase_client.table.assert_called_once_with("trading_disclosures")
    # Verify select was called
    table_mock.select.assert_called_once_with("*")
    # Verify filter on llm_validation_status
    select_mock.eq.assert_called_once_with("llm_validation_status", "pending")
    # Verify gte filter on created_at (for lookback window)
    eq_mock.gte.assert_called_once()
    gte_call_args = eq_mock.gte.call_args
    assert gte_call_args[0][0] == "created_at"
    # The timestamp should be roughly LOOKBACK_HOURS ago
    assert result == []


# =============================================================================
# Test 2: _batch_records splits correctly (60 -> 3 batches)
# =============================================================================


def test_batch_records_splits_correctly(mock_llm_client, mock_supabase_client, sample_pending_records):
    """60 records should be split into 3 batches: 25, 25, 10."""
    service = _build_service(mock_llm_client, mock_supabase_client)

    batches = service._batch_records(sample_pending_records)

    assert len(batches) == 3
    assert len(batches[0]) == 25
    assert len(batches[1]) == 25
    assert len(batches[2]) == 10


# =============================================================================
# Test 3: _batch_records single batch
# =============================================================================


def test_batch_records_single_batch(mock_llm_client, mock_supabase_client, sample_pending_records):
    """10 records should produce a single batch."""
    service = _build_service(mock_llm_client, mock_supabase_client)

    records = sample_pending_records[:10]
    batches = service._batch_records(records)

    assert len(batches) == 1
    assert len(batches[0]) == 10


# =============================================================================
# Test 4: _validate_batch renders prompt template
# =============================================================================


@pytest.mark.asyncio
async def test_validate_batch_renders_prompt(
    mock_llm_client, mock_supabase_client, sample_pending_records, sample_llm_pass_response
):
    """_validate_batch should render the validation_gate template with batch JSON."""
    mock_llm_client.generate.return_value = sample_llm_pass_response

    service = _build_service(mock_llm_client, mock_supabase_client)
    batch = sample_pending_records[:3]

    with patch("app.services.llm.validation_gate.render_template") as mock_render:
        mock_render.return_value = "rendered prompt content"
        await service._validate_batch(batch, 0)

        # Verify render_template called with validation_gate template name
        mock_render.assert_called_once()
        call_args = mock_render.call_args
        assert call_args[0][0] == "validation_gate"
        # Verify batch_json kwarg contains the serialized batch
        assert "batch_json" in call_args[1]
        batch_json_str = call_args[1]["batch_json"]
        parsed = json.loads(batch_json_str)
        assert len(parsed) == 3


# =============================================================================
# Test 5: _validate_batch calls LLM with correct model
# =============================================================================


@pytest.mark.asyncio
async def test_validate_batch_calls_llm(
    mock_llm_client, mock_supabase_client, sample_pending_records, sample_llm_pass_response
):
    """_validate_batch should call LLMClient.generate() with correct model and prompt."""
    mock_llm_client.generate.return_value = sample_llm_pass_response

    service = _build_service(mock_llm_client, mock_supabase_client)
    batch = sample_pending_records[:3]

    with patch("app.services.llm.validation_gate.render_template", return_value="prompt text"):
        with patch("app.services.llm.validation_gate.load_template", return_value="raw template"):
            await service._validate_batch(batch, 0)

    # Verify generate was called
    mock_llm_client.generate.assert_awaited_once()
    call_kwargs = mock_llm_client.generate.call_args[1]
    assert call_kwargs["model"] == "qwen3:8b"
    assert "prompt" in call_kwargs


# =============================================================================
# Test 6: _apply_results with pass status
# =============================================================================


@pytest.mark.asyncio
async def test_apply_results_pass(mock_llm_client, mock_supabase_client, sample_pending_records):
    """Pass verdict should update status to 'pass' and set llm_validated_at."""
    # Set up chainable mock for update
    table_mock = MagicMock()
    update_mock = MagicMock()
    eq_mock = MagicMock()
    eq_mock.execute.return_value = MagicMock(data=[{"id": "disc-000"}])
    update_mock.eq.return_value = eq_mock
    table_mock.update.return_value = update_mock
    mock_supabase_client.table.return_value = table_mock

    service = _build_service(mock_llm_client, mock_supabase_client)
    batch = sample_pending_records[:1]

    results = {
        "records": [
            {"record_index": 0, "status": "pass", "confidence": 9, "flags": []}
        ]
    }

    await service._apply_results(results, batch)

    # Verify update was called with pass status
    mock_supabase_client.table.assert_called_with("trading_disclosures")
    update_call = table_mock.update.call_args[0][0]
    assert update_call["llm_validation_status"] == "pass"
    assert "llm_validated_at" in update_call
    # Verify it filters by the correct record ID
    update_mock.eq.assert_called_with("id", "disc-000")


# =============================================================================
# Test 7: _apply_results with flag status
# =============================================================================


@pytest.mark.asyncio
async def test_apply_results_flag(mock_llm_client, mock_supabase_client, sample_pending_records):
    """Flag verdict should update status and insert into data_quality_issues."""
    table_mock = MagicMock()
    update_mock = MagicMock()
    eq_mock = MagicMock()
    eq_mock.execute.return_value = MagicMock(data=[{"id": "disc-001"}])
    update_mock.eq.return_value = eq_mock
    table_mock.update.return_value = update_mock
    table_mock.insert.return_value.execute.return_value = MagicMock(data=[{"id": "issue-1"}])
    mock_supabase_client.table.return_value = table_mock

    service = _build_service(mock_llm_client, mock_supabase_client)
    batch = sample_pending_records[1:2]  # disc-001

    flags = [
        {
            "step": "semantic",
            "field": "asset_ticker",
            "severity": "warning",
            "description": "Ticker mismatch",
            "reasoning": "AAPL does not match 'Microsoft Corp'",
            "suggested_action": "review",
        }
    ]
    results = {
        "records": [
            {"record_index": 0, "status": "flag", "confidence": 5, "flags": flags}
        ]
    }

    await service._apply_results(results, batch)

    # Verify the table was called for both update and insert
    table_calls = mock_supabase_client.table.call_args_list
    table_names = [c[0][0] for c in table_calls]
    assert "trading_disclosures" in table_names
    assert "data_quality_issues" in table_names

    # Verify update set flag status
    update_call = table_mock.update.call_args[0][0]
    assert update_call["llm_validation_status"] == "flag"

    # Verify insert into data_quality_issues
    insert_call = table_mock.insert.call_args[0][0]
    assert insert_call["severity"] == "warning"
    assert insert_call["source"] == "llm_validation"


# =============================================================================
# Test 8: _apply_results with reject status
# =============================================================================


@pytest.mark.asyncio
async def test_apply_results_reject(mock_llm_client, mock_supabase_client, sample_pending_records):
    """Reject verdict should update status and insert into data_quality_quarantine."""
    table_mock = MagicMock()
    update_mock = MagicMock()
    eq_mock = MagicMock()
    eq_mock.execute.return_value = MagicMock(data=[{"id": "disc-002"}])
    update_mock.eq.return_value = eq_mock
    table_mock.update.return_value = update_mock
    table_mock.insert.return_value.execute.return_value = MagicMock(data=[{"id": "quarantine-1"}])
    mock_supabase_client.table.return_value = table_mock

    service = _build_service(mock_llm_client, mock_supabase_client)
    batch = sample_pending_records[2:3]  # disc-002

    flags = [
        {
            "step": "schema",
            "field": "transaction_date",
            "severity": "critical",
            "description": "Invalid date",
            "reasoning": "Transaction date is in the future",
            "suggested_action": "reject",
        }
    ]
    results = {
        "records": [
            {"record_index": 0, "status": "reject", "confidence": 3, "flags": flags}
        ]
    }

    await service._apply_results(results, batch)

    # Verify the table was called for both update and insert
    table_calls = mock_supabase_client.table.call_args_list
    table_names = [c[0][0] for c in table_calls]
    assert "trading_disclosures" in table_names
    assert "data_quality_quarantine" in table_names

    # Verify update set reject status
    update_call = table_mock.update.call_args[0][0]
    assert update_call["llm_validation_status"] == "reject"

    # Verify insert into data_quality_quarantine
    insert_call = table_mock.insert.call_args[0][0]
    assert "original_data" in insert_call
    assert "suggested_corrections" in insert_call


# =============================================================================
# Test 9: validate_recent end-to-end
# =============================================================================


@pytest.mark.asyncio
async def test_validate_recent_end_to_end(
    mock_llm_client, mock_supabase_client, sample_llm_mixed_response
):
    """Full validate_recent flow with mocked dependencies returning mixed results."""
    # Create 3 pending records
    records = [
        {
            "id": f"disc-{i:03d}",
            "politician_id": f"pol-{i:03d}",
            "asset_name": f"Asset {i}",
            "asset_ticker": f"TKR{i}",
            "transaction_type": "purchase",
            "transaction_date": "2026-02-15",
            "disclosure_date": "2026-02-18",
            "amount_range_min": 1001,
            "amount_range_max": 15000,
            "source_url": f"https://example.com/filing-{i}",
            "raw_data": {"source": "us_house"},
            "llm_validation_status": "pending",
        }
        for i in range(3)
    ]

    # Mock fetch_pending to return our records
    service = _build_service(mock_llm_client, mock_supabase_client)
    service._fetch_pending = AsyncMock(return_value=records)

    # Mock LLM to return mixed results
    mock_llm_client.generate.return_value = sample_llm_mixed_response

    # Mock _apply_results to avoid complex Supabase chain setup
    service._apply_results = AsyncMock()

    with patch("app.services.llm.validation_gate.render_template", return_value="prompt"):
        with patch("app.services.llm.validation_gate.load_template", return_value="raw"):
            result = await service.validate_recent()

    assert result["total_records"] == 3
    assert result["passed"] == 1
    assert result["flagged"] == 1
    assert result["rejected"] == 1
    assert result["batches_processed"] == 1

    # Verify _apply_results was called once (single batch for 3 records)
    service._apply_results.assert_awaited_once()


# =============================================================================
# Test 10: validate_recent with no pending records
# =============================================================================


@pytest.mark.asyncio
async def test_validate_recent_no_pending(mock_llm_client, mock_supabase_client):
    """validate_recent should return zeros when no pending records exist."""
    service = _build_service(mock_llm_client, mock_supabase_client)
    service._fetch_pending = AsyncMock(return_value=[])

    result = await service.validate_recent()

    assert result == {
        "total_records": 0,
        "passed": 0,
        "flagged": 0,
        "rejected": 0,
        "batches_processed": 0,
    }
    # LLM should never be called
    mock_llm_client.generate.assert_not_awaited()


# =============================================================================
# Test 11: malformed LLM response handled gracefully
# =============================================================================


@pytest.mark.asyncio
async def test_malformed_llm_response(
    mock_llm_client, mock_supabase_client, sample_pending_records
):
    """Service should handle malformed LLM JSON gracefully without crashing."""
    # Return garbage from LLM
    mock_llm_client.generate.return_value = LLMResponse(
        text="this is not valid json {{{",
        model="qwen3:8b",
        input_tokens=100,
        output_tokens=20,
        latency_ms=500,
    )

    service = _build_service(mock_llm_client, mock_supabase_client)
    batch = sample_pending_records[:3]

    with patch("app.services.llm.validation_gate.render_template", return_value="prompt"):
        with patch("app.services.llm.validation_gate.load_template", return_value="raw"):
            result = await service._validate_batch(batch, 0)

    # Should return empty/safe result, not crash
    assert result is not None
    assert result.get("passed", 0) == 0
    assert result.get("flagged", 0) == 0
    assert result.get("rejected", 0) == 0


# =============================================================================
# Test 12: malformed LLM response missing records key
# =============================================================================


@pytest.mark.asyncio
async def test_malformed_llm_response_missing_records(
    mock_llm_client, mock_supabase_client, sample_pending_records
):
    """Service should handle JSON that parses but lacks 'records' key."""
    mock_llm_client.generate.return_value = LLMResponse(
        text=json.dumps({"summary": "no records field here"}),
        model="qwen3:8b",
        input_tokens=100,
        output_tokens=20,
        latency_ms=500,
    )

    service = _build_service(mock_llm_client, mock_supabase_client)
    batch = sample_pending_records[:3]

    with patch("app.services.llm.validation_gate.render_template", return_value="prompt"):
        with patch("app.services.llm.validation_gate.load_template", return_value="raw"):
            result = await service._validate_batch(batch, 0)

    assert result is not None
    assert result.get("records", []) == []


# =============================================================================
# Test 13: LLM exception during generate is handled
# =============================================================================


@pytest.mark.asyncio
async def test_llm_exception_during_generate(
    mock_llm_client, mock_supabase_client, sample_pending_records
):
    """Service should handle LLM client exceptions without crashing."""
    mock_llm_client.generate.side_effect = Exception("Ollama is down")

    service = _build_service(mock_llm_client, mock_supabase_client)
    batch = sample_pending_records[:3]

    with patch("app.services.llm.validation_gate.render_template", return_value="prompt"):
        with patch("app.services.llm.validation_gate.load_template", return_value="raw"):
            result = await service._validate_batch(batch, 0)

    # Should return safe empty result
    assert result is not None
    assert result.get("passed", 0) == 0


# =============================================================================
# Test 14: batch_records with empty list
# =============================================================================


def test_batch_records_empty_list(mock_llm_client, mock_supabase_client):
    """Empty record list should produce no batches."""
    service = _build_service(mock_llm_client, mock_supabase_client)
    batches = service._batch_records([])
    assert batches == []


# =============================================================================
# Test 15: validate_batch extracts system prompt from template
# =============================================================================


@pytest.mark.asyncio
async def test_validate_batch_passes_system_prompt(
    mock_llm_client, mock_supabase_client, sample_pending_records, sample_llm_pass_response
):
    """_validate_batch should extract SYSTEM: section and pass it as system_prompt."""
    mock_llm_client.generate.return_value = sample_llm_pass_response

    service = _build_service(mock_llm_client, mock_supabase_client)
    batch = sample_pending_records[:3]

    # Use the real template to verify system prompt extraction
    template_text = "SYSTEM:\nYou are an expert.\n\nUSER:\nValidate {{ batch_json }}"
    with patch("app.services.llm.validation_gate.render_template", return_value="USER:\nValidate [...]"):
        with patch("app.services.llm.validation_gate.load_template", return_value=template_text):
            await service._validate_batch(batch, 0)

    # Verify system_prompt was passed to generate
    call_kwargs = mock_llm_client.generate.call_args[1]
    assert "system_prompt" in call_kwargs
    assert call_kwargs["system_prompt"] is not None
