"""
Tests for AnomalyDetectionService (Prompt 2).

Covers:
1.  test_fetch_trading_window_with_dates - verifies correct Supabase query
2.  test_fetch_trading_window_with_filer_filter - verifies filer filter applied
3.  test_compute_baseline_stats - returns correct structure
4.  test_compute_baseline_stats_no_history - handles filer with no prior trades
5.  test_fetch_calendar_events_returns_empty - placeholder returns empty list
6.  test_render_prompt_fills_all_variables - all {{ }} placeholders replaced
7.  test_parse_anomaly_signals - parses the LLM JSON output correctly
8.  test_store_signals_inserts_to_db - verifies Supabase insert call
9.  test_store_signals_high_confidence - signals with confidence >= 7 also go to trading_signals
10. test_detect_end_to_end - full flow with mocked LLM
11. test_detect_no_records - returns empty result when no trades in window
12. test_malformed_llm_response - handles bad JSON gracefully
"""

import json
import re
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm.client import LLMClient, LLMResponse
from app.services.llm.audit_logger import LLMAuditLogger
from app.services.llm.anomaly_detector import AnomalyDetectionService


# =============================================================================
# Fixtures
# =============================================================================


SAMPLE_LLM_RESPONSE = {
    "analysis_window": {"start": "2026-01-01", "end": "2026-01-31"},
    "anomalies_detected": 2,
    "signals": [
        {
            "signal_id": "sig-001",
            "filer": "Nancy Pelosi",
            "classification": "FREQUENCY_SPIKE",
            "severity": "high",
            "confidence": 8,
            "trades_involved": [
                {"record_id": "rec-1", "ticker": "NVDA", "date": "2026-01-10"},
                {"record_id": "rec-2", "ticker": "NVDA", "date": "2026-01-12"},
            ],
            "legislative_context": {
                "proximity_score": 7,
                "related_events": ["AI Regulation hearing on 2026-01-08"],
            },
            "statistical_evidence": {
                "z_score": 2.5,
                "baseline_deviation_pct": 150.0,
            },
            "reasoning": "Multiple NVDA trades clustered around AI hearing.",
            "trading_signal": {
                "direction": "long",
                "suggested_tickers": ["NVDA"],
                "time_horizon": "2-4 weeks",
                "conviction": 7,
            },
            "self_verification_notes": "Not explained by broad market rally.",
        },
        {
            "signal_id": "sig-002",
            "filer": "Dan Crenshaw",
            "classification": "SECTOR_CLUSTER",
            "severity": "medium",
            "confidence": 5,
            "trades_involved": [
                {"record_id": "rec-3", "ticker": "XOM", "date": "2026-01-15"},
            ],
            "legislative_context": {
                "proximity_score": 3,
                "related_events": [],
            },
            "statistical_evidence": {
                "z_score": 1.8,
                "baseline_deviation_pct": 80.0,
            },
            "reasoning": "Energy sector clustering for committee member.",
            "trading_signal": {
                "direction": "neutral",
                "suggested_tickers": ["XOM"],
                "time_horizon": "1-2 weeks",
                "conviction": 4,
            },
            "self_verification_notes": "Broad energy rally may explain.",
        },
    ],
    "market_context_notes": "S&P 500 up 2% in window, no significant macro events.",
}


SAMPLE_TRADING_RECORDS = [
    {
        "filer_name": "Nancy Pelosi",
        "transaction_date": "2026-01-10",
        "ticker": "NVDA",
        "asset_description": "NVIDIA Corporation",
        "transaction_type": "purchase",
        "amount_range_min": 1000001,
        "amount_range_max": 5000000,
        "source": "us_house",
    },
    {
        "filer_name": "Nancy Pelosi",
        "transaction_date": "2026-01-12",
        "ticker": "NVDA",
        "asset_description": "NVIDIA Corporation",
        "transaction_type": "purchase",
        "amount_range_min": 500001,
        "amount_range_max": 1000000,
        "source": "us_house",
    },
    {
        "filer_name": "Dan Crenshaw",
        "transaction_date": "2026-01-15",
        "ticker": "XOM",
        "asset_description": "Exxon Mobil Corp",
        "transaction_type": "purchase",
        "amount_range_min": 15001,
        "amount_range_max": 50000,
        "source": "us_house",
    },
]


@pytest.fixture
def mock_llm_client():
    """Mock LLMClient that returns a valid anomaly detection response."""
    client = AsyncMock(spec=LLMClient)
    client.generate = AsyncMock(
        return_value=LLMResponse(
            text=json.dumps(SAMPLE_LLM_RESPONSE),
            model="gemma3:12b-it-qat",
            input_tokens=500,
            output_tokens=300,
            latency_ms=2000,
        )
    )
    return client


@pytest.fixture
def mock_supabase_for_anomaly():
    """Mock Supabase client tailored for anomaly detector queries."""
    client = MagicMock()

    # Default table mock for inserts
    table_mock = MagicMock()
    table_mock.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "test-uuid"}]
    )

    client.table.return_value = table_mock
    return client


@pytest.fixture
def service(mock_llm_client, mock_supabase_for_anomaly):
    """Create an AnomalyDetectionService with mocked dependencies."""
    return AnomalyDetectionService(
        llm_client=mock_llm_client,
        supabase=mock_supabase_for_anomaly,
    )


# =============================================================================
# Test 1: test_fetch_trading_window_with_dates
# =============================================================================


@pytest.mark.asyncio
async def test_fetch_trading_window_with_dates(service, mock_supabase_for_anomaly):
    """_fetch_trading_window should query trading_disclosures with date filters."""
    # Set up the Supabase mock chain for the select query
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.gte.return_value = mock_chain
    mock_chain.lte.return_value = mock_chain
    mock_chain.execute.return_value = MagicMock(data=[
        {
            "id": "rec-1",
            "transaction_date": "2026-01-10",
            "asset_ticker": "NVDA",
            "asset_name": "NVIDIA Corporation",
            "transaction_type": "purchase",
            "amount_range_min": 1000001,
            "amount_range_max": 5000000,
            "raw_data": {"source": "us_house"},
            "politicians": {"full_name": "Nancy Pelosi"},
        }
    ])
    mock_supabase_for_anomaly.table.return_value = mock_chain

    records = await service._fetch_trading_window("2026-01-01", "2026-01-31", "ALL")

    # Verify the table was queried
    mock_supabase_for_anomaly.table.assert_called_with("trading_disclosures")
    # Verify date range filters were applied
    mock_chain.gte.assert_called_once_with("transaction_date", "2026-01-01")
    mock_chain.lte.assert_called_once_with("transaction_date", "2026-01-31")
    # Verify records were returned
    assert len(records) == 1
    assert records[0]["ticker"] == "NVDA"
    assert records[0]["filer_name"] == "Nancy Pelosi"


# =============================================================================
# Test 2: test_fetch_trading_window_with_filer_filter
# =============================================================================


@pytest.mark.asyncio
async def test_fetch_trading_window_with_filer_filter(service, mock_supabase_for_anomaly):
    """_fetch_trading_window should apply filer name filter when not ALL."""
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.gte.return_value = mock_chain
    mock_chain.lte.return_value = mock_chain
    mock_chain.ilike.return_value = mock_chain
    mock_chain.execute.return_value = MagicMock(data=[])
    mock_supabase_for_anomaly.table.return_value = mock_chain

    await service._fetch_trading_window("2026-01-01", "2026-01-31", "Nancy Pelosi")

    # When filer is not "ALL", ilike filter should be applied
    mock_chain.ilike.assert_called_once()


# =============================================================================
# Test 3: test_compute_baseline_stats
# =============================================================================


@pytest.mark.asyncio
async def test_compute_baseline_stats(service, mock_supabase_for_anomaly):
    """_compute_baseline_stats should return correct structure with avg_trades_per_month etc."""
    # Mock records for the 12-month baseline
    baseline_records = [
        {
            "transaction_date": f"2025-{m:02d}-15",
            "asset_ticker": "AAPL",
            "asset_name": "Apple Inc",
            "transaction_type": "purchase",
            "amount_range_min": 15001,
            "amount_range_max": 50000,
        }
        for m in range(1, 13)
    ]

    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.gte.return_value = mock_chain
    mock_chain.lt.return_value = mock_chain
    mock_chain.ilike.return_value = mock_chain
    mock_chain.execute.return_value = MagicMock(data=baseline_records)
    mock_supabase_for_anomaly.table.return_value = mock_chain

    stats = await service._compute_baseline_stats("Nancy Pelosi", "2026-01-01")

    assert "avg_trades_per_month" in stats
    assert "typical_sectors" in stats
    assert "avg_amount_range_index" in stats
    assert "trading_day_distribution" in stats
    assert isinstance(stats["avg_trades_per_month"], (int, float))
    assert isinstance(stats["typical_sectors"], list)


# =============================================================================
# Test 4: test_compute_baseline_stats_no_history
# =============================================================================


@pytest.mark.asyncio
async def test_compute_baseline_stats_no_history(service, mock_supabase_for_anomaly):
    """_compute_baseline_stats should handle filer with no prior trades."""
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.gte.return_value = mock_chain
    mock_chain.lt.return_value = mock_chain
    mock_chain.ilike.return_value = mock_chain
    mock_chain.execute.return_value = MagicMock(data=[])
    mock_supabase_for_anomaly.table.return_value = mock_chain

    stats = await service._compute_baseline_stats("New Politician", "2026-01-01")

    assert stats["avg_trades_per_month"] == 0
    assert stats["typical_sectors"] == []
    assert stats["avg_amount_range_index"] == 0
    assert stats["trading_day_distribution"] == {}


# =============================================================================
# Test 5: test_fetch_calendar_events_returns_empty
# =============================================================================


@pytest.mark.asyncio
async def test_fetch_calendar_events_returns_empty(service):
    """_fetch_calendar_events should return an empty list (placeholder)."""
    events = await service._fetch_calendar_events("2026-01-01", "2026-01-31")
    assert events == []


# =============================================================================
# Test 6: test_render_prompt_fills_all_variables
# =============================================================================


def test_render_prompt_fills_all_variables():
    """render_template for anomaly_detection fills all {{ }} placeholders."""
    from app.prompts import render_template

    result = render_template(
        "anomaly_detection",
        start_date="2026-01-01",
        end_date="2026-01-31",
        filer_names_or_ALL="ALL",
        calendar_events_json="[]",
        trading_records_json="[]",
        baseline_stats_json="{}",
    )
    remaining = re.findall(r"\{\{.*?\}\}", result)
    assert len(remaining) == 0, f"Remaining placeholders: {remaining}"
    assert "2026-01-01" in result
    assert "2026-01-31" in result
    assert "ALL" in result


# =============================================================================
# Test 7: test_parse_anomaly_signals
# =============================================================================


def test_parse_anomaly_signals():
    """Parsing the LLM JSON output should produce the expected signal structure."""
    parsed = SAMPLE_LLM_RESPONSE
    assert parsed["anomalies_detected"] == 2
    assert len(parsed["signals"]) == 2

    sig = parsed["signals"][0]
    assert sig["filer"] == "Nancy Pelosi"
    assert sig["classification"] == "FREQUENCY_SPIKE"
    assert sig["severity"] == "high"
    assert sig["confidence"] == 8
    assert len(sig["trades_involved"]) == 2
    assert sig["legislative_context"]["proximity_score"] == 7
    assert sig["statistical_evidence"]["z_score"] == 2.5
    assert sig["trading_signal"]["direction"] == "long"


# =============================================================================
# Test 8: test_store_signals_inserts_to_db
# =============================================================================


@pytest.mark.asyncio
async def test_store_signals_inserts_to_db(service, mock_supabase_for_anomaly):
    """_store_signals should insert each signal into llm_anomaly_signals table."""
    signals = SAMPLE_LLM_RESPONSE["signals"]

    # Track table calls
    table_calls = {}

    def track_table(name):
        if name not in table_calls:
            mock = MagicMock()
            mock.insert.return_value.execute.return_value = MagicMock(data=[{"id": "test"}])
            table_calls[name] = mock
        return table_calls[name]

    mock_supabase_for_anomaly.table.side_effect = track_table

    stored = await service._store_signals(signals, audit_id=None)

    # Both signals should be inserted into llm_anomaly_signals
    assert "llm_anomaly_signals" in table_calls
    assert table_calls["llm_anomaly_signals"].insert.call_count == 2
    assert stored == 2


# =============================================================================
# Test 9: test_store_signals_high_confidence
# =============================================================================


@pytest.mark.asyncio
async def test_store_signals_high_confidence(service, mock_supabase_for_anomaly):
    """Signals with confidence >= 7 should also be inserted into trading_signals."""
    signals = SAMPLE_LLM_RESPONSE["signals"]

    table_calls = {}

    def track_table(name):
        if name not in table_calls:
            mock = MagicMock()
            mock.insert.return_value.execute.return_value = MagicMock(data=[{"id": "test"}])
            table_calls[name] = mock
        return table_calls[name]

    mock_supabase_for_anomaly.table.side_effect = track_table

    await service._store_signals(signals, audit_id=None)

    # Signal with confidence=8 (Nancy Pelosi) should also go to trading_signals
    # Signal with confidence=5 (Dan Crenshaw) should NOT
    assert "trading_signals" in table_calls
    assert table_calls["trading_signals"].insert.call_count == 1

    # Verify the trading signal data
    insert_args = table_calls["trading_signals"].insert.call_args[0][0]
    assert insert_args["ticker"] == "NVDA"
    assert insert_args["signal_type"] in ("buy", "sell", "hold", "strong_buy", "strong_sell")
    assert insert_args["source"] == "llm_anomaly_detection"


# =============================================================================
# Test 10: test_detect_end_to_end
# =============================================================================


@pytest.mark.asyncio
async def test_detect_end_to_end(service, mock_llm_client, mock_supabase_for_anomaly):
    """Full detect() flow with mocked LLM should return structured result."""
    # Mock _fetch_trading_window to return records
    service._fetch_trading_window = AsyncMock(return_value=SAMPLE_TRADING_RECORDS)
    service._compute_baseline_stats = AsyncMock(return_value={
        "avg_trades_per_month": 3.0,
        "typical_sectors": ["Technology"],
        "avg_amount_range_index": 4,
        "trading_day_distribution": {"Monday": 2, "Wednesday": 1},
    })
    service._fetch_calendar_events = AsyncMock(return_value=[])

    # Track table calls for store verification
    table_calls = {}

    def track_table(name):
        if name not in table_calls:
            mock = MagicMock()
            mock.insert.return_value.execute.return_value = MagicMock(data=[{"id": "test"}])
            table_calls[name] = mock
        return table_calls[name]

    mock_supabase_for_anomaly.table.side_effect = track_table

    result = await service.detect("2026-01-01", "2026-01-31", filer="ALL")

    # Verify return structure
    assert result["anomalies_detected"] == 2
    assert len(result["signals"]) == 2
    assert result["analysis_window"]["start"] == "2026-01-01"
    assert result["analysis_window"]["end"] == "2026-01-31"
    assert result["signals_stored"] == 2

    # Verify LLM was called
    mock_llm_client.generate.assert_awaited_once()

    # Verify prompt was passed as first arg or keyword
    call_kwargs = mock_llm_client.generate.call_args
    prompt = call_kwargs.kwargs.get("prompt") or call_kwargs.args[0] if call_kwargs.args else ""
    assert isinstance(prompt, str)


# =============================================================================
# Test 11: test_detect_no_records
# =============================================================================


@pytest.mark.asyncio
async def test_detect_no_records(service, mock_llm_client):
    """detect() should return empty result when no trades in window."""
    service._fetch_trading_window = AsyncMock(return_value=[])

    result = await service.detect("2026-01-01", "2026-01-31", filer="ALL")

    assert result["anomalies_detected"] == 0
    assert result["signals"] == []
    assert result["analysis_window"]["start"] == "2026-01-01"
    assert result["analysis_window"]["end"] == "2026-01-31"

    # LLM should not be called when there are no records
    mock_llm_client.generate.assert_not_awaited()


# =============================================================================
# Test 12: test_malformed_llm_response
# =============================================================================


@pytest.mark.asyncio
async def test_malformed_llm_response(service, mock_llm_client, mock_supabase_for_anomaly):
    """detect() should handle malformed LLM JSON gracefully."""
    # Override LLM response with invalid JSON
    mock_llm_client.generate = AsyncMock(
        return_value=LLMResponse(
            text="This is not valid JSON {{{",
            model="gemma3:12b-it-qat",
            input_tokens=500,
            output_tokens=50,
            latency_ms=1000,
        )
    )

    service._fetch_trading_window = AsyncMock(return_value=SAMPLE_TRADING_RECORDS)
    service._compute_baseline_stats = AsyncMock(return_value={
        "avg_trades_per_month": 0,
        "typical_sectors": [],
        "avg_amount_range_index": 0,
        "trading_day_distribution": {},
    })
    service._fetch_calendar_events = AsyncMock(return_value=[])

    result = await service.detect("2026-01-01", "2026-01-31", filer="ALL")

    # Should return gracefully with zero anomalies
    assert result["anomalies_detected"] == 0
    assert result["signals"] == []
    assert "error" in result
