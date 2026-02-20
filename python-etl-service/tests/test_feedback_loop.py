"""
Tests for FeedbackLoopService (Prompt 4).

Covers:
1.  test_fetch_signals_with_outcomes - queries trading_signals with date range
2.  test_compute_scorecard - calculates hit_rate, alpha_rate, false_positive_rate correctly
3.  test_compute_scorecard_empty - handles empty signals list
4.  test_render_feedback_prompt - fills all {{ }} placeholders
5.  test_store_recommendations - inserts into llm_prompt_recommendations
6.  test_analyze_end_to_end - full flow with mocked LLM
7.  test_no_signals_in_window - handles periods with no signals
"""

import json
import re

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm.client import LLMClient, LLMResponse
from app.services.llm.audit_logger import LLMAuditLogger
from app.services.llm.feedback_loop import FeedbackLoopService


# =============================================================================
# Fixtures
# =============================================================================


SAMPLE_LLM_FEEDBACK_RESPONSE = {
    "feedback_id": "fb-001",
    "analysis_period": {"start": "2026-01-01", "end": "2026-01-31"},
    "scorecard": {
        "total_signals": 3,
        "hit_rate": 0.6667,
        "alpha_rate": 0.3333,
        "avg_confidence_winners": 8.0,
        "avg_confidence_losers": 6.0,
        "false_positive_rate": 0.5,
        "estimated_false_negatives": 1,
    },
    "failure_patterns": [
        {
            "pattern": "High confidence on energy sector signals during broad rally",
            "frequency": 1,
            "avg_loss_pct": -3.5,
            "root_cause": "market_context",
            "example_signal_ids": ["sig-003"],
        },
    ],
    "prompt_recommendations": [
        {
            "target_prompt": "anomaly_detection",
            "change_type": "modify_threshold",
            "description": "Raise z-score threshold from 2.0 to 2.5 for SECTOR_CLUSTER signals",
            "expected_impact": "Reduce false positives by ~20%",
            "priority": "high",
        },
        {
            "target_prompt": "validation",
            "change_type": "add_rule",
            "description": "Add market regime context check before flagging timing anomalies",
            "expected_impact": "Improve timing signal accuracy by ~15%",
            "priority": "medium",
        },
    ],
    "threshold_adjustments": [
        {
            "parameter": "z_score_threshold",
            "current_value": "2.0",
            "recommended_value": "2.5",
            "rationale": "Current threshold generates too many false positives in volatile markets",
        },
    ],
    "data_quality_feedback": {
        "issues_detected": 0,
        "categories": [],
        "recommended_pipeline_changes": [],
    },
    "next_review_date": "2026-02-28",
    "meta_confidence": 7,
}


SAMPLE_SIGNALS_WITH_OUTCOMES = [
    {
        "id": "sig-001",
        "ticker": "NVDA",
        "signal_type": "buy",
        "strength": 0.8,
        "confidence": 8,
        "source": "llm_anomaly_detection",
        "politician_name": "Nancy Pelosi",
        "created_at": "2026-01-10T00:00:00Z",
        "outcome": {
            "return_pct": 12.5,
            "benchmark_return_pct": 2.7,
            "alpha": 9.8,
            "max_drawdown_pct": -3.2,
            "holding_period_days": 14,
        },
    },
    {
        "id": "sig-002",
        "ticker": "AAPL",
        "signal_type": "buy",
        "strength": 0.7,
        "confidence": 7,
        "source": "llm_anomaly_detection",
        "politician_name": "Tommy Tuberville",
        "created_at": "2026-01-15T00:00:00Z",
        "outcome": {
            "return_pct": 3.1,
            "benchmark_return_pct": 2.0,
            "alpha": 1.1,
            "max_drawdown_pct": -1.5,
            "holding_period_days": 10,
        },
    },
    {
        "id": "sig-003",
        "ticker": "XOM",
        "signal_type": "buy",
        "strength": 0.6,
        "confidence": 8,
        "source": "llm_anomaly_detection",
        "politician_name": "Dan Crenshaw",
        "created_at": "2026-01-20T00:00:00Z",
        "outcome": {
            "return_pct": -3.5,
            "benchmark_return_pct": 1.5,
            "alpha": -5.0,
            "max_drawdown_pct": -7.2,
            "holding_period_days": 21,
        },
    },
]


@pytest.fixture
def mock_llm_client():
    """Mock LLMClient that returns a valid feedback loop response."""
    client = AsyncMock(spec=LLMClient)
    client.generate = AsyncMock(
        return_value=LLMResponse(
            text=json.dumps(SAMPLE_LLM_FEEDBACK_RESPONSE),
            model="gemma3:12b-it-qat",
            input_tokens=800,
            output_tokens=500,
            latency_ms=3000,
        )
    )
    return client


@pytest.fixture
def mock_supabase_for_feedback():
    """Mock Supabase client tailored for feedback loop queries."""
    client = MagicMock()

    # Default table mock for inserts
    table_mock = MagicMock()
    table_mock.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "test-uuid"}]
    )

    client.table.return_value = table_mock
    return client


@pytest.fixture
def service(mock_llm_client, mock_supabase_for_feedback):
    """Create a FeedbackLoopService with mocked dependencies."""
    return FeedbackLoopService(
        llm_client=mock_llm_client,
        supabase=mock_supabase_for_feedback,
    )


# =============================================================================
# Test 1: test_fetch_signals_with_outcomes
# =============================================================================


@pytest.mark.asyncio
async def test_fetch_signals_with_outcomes(service, mock_supabase_for_feedback):
    """_fetch_signals_with_outcomes should query trading_signals with date range."""
    # Set up the Supabase mock chain for the signals select query
    signals_chain = MagicMock()
    signals_chain.select.return_value = signals_chain
    signals_chain.gte.return_value = signals_chain
    signals_chain.lte.return_value = signals_chain
    signals_chain.execute.return_value = MagicMock(data=[
        {
            "id": "sig-001",
            "ticker": "NVDA",
            "signal_type": "buy",
            "confidence": 8,
            "source": "llm_anomaly_detection",
            "created_at": "2026-01-10T00:00:00Z",
        },
    ])

    # Set up positions query chain
    positions_chain = MagicMock()
    positions_chain.select.return_value = positions_chain
    positions_chain.eq.return_value = positions_chain
    positions_chain.gte.return_value = positions_chain
    positions_chain.lte.return_value = positions_chain
    positions_chain.limit.return_value = positions_chain
    positions_chain.execute.return_value = MagicMock(data=[
        {
            "return_pct": 12.5,
            "benchmark_return_pct": 2.7,
            "alpha": 9.8,
            "max_drawdown_pct": -3.2,
            "holding_period_days": 14,
        },
    ])

    # Route table calls
    def route_table(name):
        if name == "trading_signals":
            return signals_chain
        elif name == "positions":
            return positions_chain
        return MagicMock()

    mock_supabase_for_feedback.table.side_effect = route_table

    records = await service._fetch_signals_with_outcomes("2026-01-01", "2026-01-31")

    # Verify signals table was queried
    mock_supabase_for_feedback.table.assert_any_call("trading_signals")
    # Verify date range filters were applied
    signals_chain.gte.assert_called_once_with("created_at", "2026-01-01")
    signals_chain.lte.assert_called_once_with("created_at", "2026-01-31")
    # Verify records were returned with outcomes
    assert len(records) == 1
    assert records[0]["ticker"] == "NVDA"
    assert records[0]["outcome"] is not None
    assert records[0]["outcome"]["return_pct"] == 12.5


# =============================================================================
# Test 2: test_compute_scorecard
# =============================================================================


def test_compute_scorecard(service):
    """_compute_scorecard should calculate hit_rate, alpha_rate, false_positive_rate correctly."""
    scorecard = service._compute_scorecard(SAMPLE_SIGNALS_WITH_OUTCOMES)

    assert scorecard["total_signals"] == 3
    # 2 out of 3 signals had positive return_pct
    assert scorecard["hit_rate"] == round(2 / 3, 4)
    # 2 out of 3 signals had positive alpha
    assert scorecard["alpha_rate"] == round(2 / 3, 4)
    # 1 false positive (sig-003: confidence=8, return_pct=-3.5) out of 3 high-confidence signals
    assert scorecard["false_positive_rate"] == round(1 / 3, 4)
    # avg confidence = (8 + 7 + 8) / 3 = 7.6667
    assert scorecard["avg_confidence"] == round((8 + 7 + 8) / 3, 4)


# =============================================================================
# Test 3: test_compute_scorecard_empty
# =============================================================================


def test_compute_scorecard_empty(service):
    """_compute_scorecard should handle empty signals list."""
    scorecard = service._compute_scorecard([])

    assert scorecard["total_signals"] == 0
    assert scorecard["hit_rate"] == 0
    assert scorecard["alpha_rate"] == 0
    assert scorecard["false_positive_rate"] == 0
    assert scorecard["avg_confidence"] == 0


# =============================================================================
# Test 4: test_render_feedback_prompt
# =============================================================================


def test_render_feedback_prompt():
    """render_template for feedback_loop fills all {{ }} placeholders."""
    from app.prompts import render_template

    result = render_template(
        "feedback_loop",
        start_date="2026-01-01",
        end_date="2026-01-31",
        signals_with_outcomes_json="[]",
        validation_version="v1.0",
        anomaly_version="v1.0",
        thresholds_json="{}",
    )
    remaining = re.findall(r"\{\{.*?\}\}", result)
    assert len(remaining) == 0, f"Remaining placeholders: {remaining}"
    assert "2026-01-01" in result
    assert "2026-01-31" in result


# =============================================================================
# Test 5: test_store_recommendations
# =============================================================================


@pytest.mark.asyncio
async def test_store_recommendations(service, mock_supabase_for_feedback):
    """_store_recommendations should insert into llm_prompt_recommendations."""
    recommendations = SAMPLE_LLM_FEEDBACK_RESPONSE["prompt_recommendations"]

    # Track table calls
    table_calls = {}

    def track_table(name):
        if name not in table_calls:
            mock = MagicMock()
            mock.insert.return_value.execute.return_value = MagicMock(data=[{"id": "test"}])
            table_calls[name] = mock
        return table_calls[name]

    mock_supabase_for_feedback.table.side_effect = track_table

    stored = await service._store_recommendations(recommendations, "fb-001")

    # Both recommendations should be inserted
    assert "llm_prompt_recommendations" in table_calls
    assert table_calls["llm_prompt_recommendations"].insert.call_count == 2
    assert stored == 2

    # Verify the inserted data structure
    first_call_args = table_calls["llm_prompt_recommendations"].insert.call_args_list[0][0][0]
    assert first_call_args["feedback_id"] == "fb-001"
    assert first_call_args["target_prompt"] == "anomaly_detection"
    assert first_call_args["change_type"] == "modify_threshold"
    assert first_call_args["priority"] == "high"


# =============================================================================
# Test 6: test_analyze_end_to_end
# =============================================================================


@pytest.mark.asyncio
async def test_analyze_end_to_end(service, mock_llm_client, mock_supabase_for_feedback):
    """Full analyze() flow with mocked LLM should return structured result."""
    # Mock _fetch_signals_with_outcomes to return sample data
    service._fetch_signals_with_outcomes = AsyncMock(return_value=SAMPLE_SIGNALS_WITH_OUTCOMES)

    # Track table calls for store verification
    table_calls = {}

    def track_table(name):
        if name not in table_calls:
            mock = MagicMock()
            mock.insert.return_value.execute.return_value = MagicMock(data=[{"id": "test"}])
            table_calls[name] = mock
        return table_calls[name]

    mock_supabase_for_feedback.table.side_effect = track_table

    result = await service.analyze("2026-01-01", "2026-01-31")

    # Verify return structure
    assert "scorecard" in result
    assert "recommendations" in result
    assert "threshold_adjustments" in result
    assert "feedback_id" in result

    # Verify scorecard was computed
    assert result["scorecard"]["total_signals"] == 3
    assert result["scorecard"]["hit_rate"] > 0

    # Verify recommendations from LLM response
    assert len(result["recommendations"]) == 2
    assert result["recommendations"][0]["target_prompt"] == "anomaly_detection"

    # Verify threshold adjustments from LLM response
    assert len(result["threshold_adjustments"]) == 1
    assert result["threshold_adjustments"][0]["parameter"] == "z_score_threshold"

    # Verify feedback_id
    assert result["feedback_id"] == "fb-001"

    # Verify LLM was called
    mock_llm_client.generate.assert_awaited_once()

    # Verify prompt was passed
    call_kwargs = mock_llm_client.generate.call_args
    prompt = call_kwargs.kwargs.get("prompt") or call_kwargs.args[0] if call_kwargs.args else ""
    assert isinstance(prompt, str)

    # Verify recommendations were stored
    assert "llm_prompt_recommendations" in table_calls
    assert table_calls["llm_prompt_recommendations"].insert.call_count == 2


# =============================================================================
# Test 7: test_no_signals_in_window
# =============================================================================


@pytest.mark.asyncio
async def test_no_signals_in_window(service, mock_llm_client):
    """analyze() should return empty result when no signals in window."""
    service._fetch_signals_with_outcomes = AsyncMock(return_value=[])

    result = await service.analyze("2026-01-01", "2026-01-31")

    assert result["scorecard"]["total_signals"] == 0
    assert result["scorecard"]["hit_rate"] == 0
    assert result["recommendations"] == []
    assert result["threshold_adjustments"] == []
    assert result["feedback_id"] is None

    # LLM should not be called when there are no signals
    mock_llm_client.generate.assert_not_awaited()
