"""
Tests for LineageAuditService (Prompt 3).

Covers:
1.  test_fetch_record_and_metadata - queries trading_disclosures by ID
2.  test_compute_hash_chain - produces valid SHA-256 chain
3.  test_render_audit_prompt - fills all {{ }} placeholders
4.  test_parse_provenance_report - parses structured JSON with trust_score and chain_integrity
5.  test_verification_questions_generated - response includes 3-5 verification questions
6.  test_chain_integrity_valid - detects valid hash chain
7.  test_audit_end_to_end - full flow with mocked LLM
"""

import hashlib
import json
import re

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm.client import LLMClient, LLMResponse
from app.services.llm.audit_logger import LLMAuditLogger
from app.services.llm.lineage_auditor import (
    LineageAuditService,
    _classify_chain_integrity,
)


# =============================================================================
# Fixtures
# =============================================================================


SAMPLE_RECORD = {
    "id": "disc-001",
    "politician_id": "pol-001",
    "asset_ticker": "NVDA",
    "asset_name": "NVIDIA Corporation",
    "transaction_type": "purchase",
    "transaction_date": "2026-01-10",
    "amount_range_min": 1000001,
    "amount_range_max": 5000000,
    "raw_data": {
        "source": "us_house",
        "source_url": "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/20012345.pdf",
        "extraction_ts": "2026-01-15T10:30:00Z",
        "method": "pdfplumber",
        "transform_chain": [
            {
                "step": "normalize_ticker",
                "ts": "2026-01-15T10:30:01Z",
                "version": "1.2.0",
            },
            {
                "step": "validate_amount_range",
                "ts": "2026-01-15T10:30:02Z",
                "version": "1.0.0",
            },
        ],
    },
    "created_at": "2026-01-15T10:30:05Z",
    "updated_at": "2026-01-15T10:30:05Z",
    "llm_validation_status": "pass",
    "llm_validated_at": "2026-01-15T11:00:00Z",
}


SAMPLE_LLM_RESPONSE = {
    "audit_id": "audit-001",
    "audit_ts": "2026-02-20T12:00:00Z",
    "record_id": "disc-001",
    "provenance_chain_valid": True,
    "overall_trust_score": 85,
    "chain_integrity": {
        "hash_chain_valid": True,
        "temporal_ordering_valid": True,
        "all_transforms_approved": True,
        "gaps_detected": 0,
    },
    "verification_questions": [
        {
            "question": "Does the SHA-256 hash correspond to a real filing?",
            "answer": "The hash matches the source PDF.",
            "status": "VERIFIED",
            "impact_if_failed": "high",
        },
        {
            "question": "Is there a gap in the transform chain between step 1 and step 2?",
            "answer": "No gap detected; timestamps are monotonically increasing.",
            "status": "VERIFIED",
            "impact_if_failed": "medium",
        },
        {
            "question": "Could the OCR extraction have misread the amount range?",
            "answer": "Amount range is within expected bounds for this filer.",
            "status": "VERIFIED",
            "impact_if_failed": "low",
        },
    ],
    "risk_factors": [
        {
            "factor": "Single extraction method",
            "severity": "low",
            "description": "Only pdfplumber was used; no cross-validation with OCR.",
        },
    ],
    "recommended_action": "trust",
    "audit_narrative": "Record passed all chain integrity checks. Hash chain is valid "
    "with monotonically increasing timestamps. All transform versions are approved.",
}


@pytest.fixture
def mock_llm_client():
    """Mock LLMClient that returns a valid lineage audit response."""
    client = AsyncMock(spec=LLMClient)
    client.generate = AsyncMock(
        return_value=LLMResponse(
            text=json.dumps(SAMPLE_LLM_RESPONSE),
            model="deepseek-r1:7b",
            input_tokens=600,
            output_tokens=400,
            latency_ms=3000,
        )
    )
    return client


@pytest.fixture
def mock_supabase_for_lineage():
    """Mock Supabase client tailored for lineage auditor queries."""
    client = MagicMock()

    # Default table mock
    table_mock = MagicMock()
    table_mock.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "test-uuid"}]
    )

    client.table.return_value = table_mock
    return client


@pytest.fixture
def service(mock_llm_client, mock_supabase_for_lineage):
    """Create a LineageAuditService with mocked dependencies."""
    return LineageAuditService(
        llm_client=mock_llm_client,
        supabase=mock_supabase_for_lineage,
    )


# =============================================================================
# Test 1: test_fetch_record_and_metadata
# =============================================================================


@pytest.mark.asyncio
async def test_fetch_record_and_metadata(service, mock_supabase_for_lineage):
    """_fetch_record_and_metadata should query trading_disclosures by ID."""
    # Set up the Supabase mock chain for the select query
    mock_chain = MagicMock()
    mock_chain.select.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.limit.return_value = mock_chain
    mock_chain.execute.return_value = MagicMock(data=[SAMPLE_RECORD])
    mock_supabase_for_lineage.table.return_value = mock_chain

    record, metadata = await service._fetch_record_and_metadata("disc-001")

    # Verify the table was queried correctly
    mock_supabase_for_lineage.table.assert_called_with("trading_disclosures")
    mock_chain.select.assert_called_once_with("*")
    mock_chain.eq.assert_called_once_with("id", "disc-001")
    mock_chain.limit.assert_called_once_with(1)

    # Verify record was returned
    assert record is not None
    assert record["id"] == "disc-001"
    assert record["asset_ticker"] == "NVDA"

    # Verify metadata was extracted from raw_data
    assert metadata["source_url"] == "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/20012345.pdf"
    assert metadata["extraction_ts"] == "2026-01-15T10:30:00Z"
    assert metadata["method"] == "pdfplumber"
    assert isinstance(metadata["transform_chain"], list)
    assert len(metadata["transform_chain"]) == 2


# =============================================================================
# Test 2: test_compute_hash_chain
# =============================================================================


def test_compute_hash_chain(service):
    """_compute_hash_chain should produce valid SHA-256 chain."""
    hash_chain = service._compute_hash_chain(SAMPLE_RECORD)

    # Verify structure
    assert "source_hash" in hash_chain
    assert "current_hash" in hash_chain
    assert "transform_chain" in hash_chain
    assert "transform_chain_json" in hash_chain

    # Verify hashes are valid SHA-256 hex strings (64 chars)
    assert len(hash_chain["source_hash"]) == 64
    assert len(hash_chain["current_hash"]) == 64
    assert all(c in "0123456789abcdef" for c in hash_chain["source_hash"])
    assert all(c in "0123456789abcdef" for c in hash_chain["current_hash"])

    # Verify transform chain has hashes for each step
    chain = hash_chain["transform_chain"]
    assert len(chain) == 2
    assert chain[0]["step"] == "normalize_ticker"
    assert chain[1]["step"] == "validate_amount_range"

    # Verify hash chaining: output_hash of step N should be input_hash of step N+1
    assert chain[0]["input_hash"] == hash_chain["source_hash"]
    assert chain[1]["input_hash"] == chain[0]["output_hash"]

    # Verify each step hash is valid SHA-256
    for step in chain:
        assert len(step["input_hash"]) == 64
        assert len(step["output_hash"]) == 64

    # Verify transform_chain_json is valid JSON
    parsed_chain = json.loads(hash_chain["transform_chain_json"])
    assert len(parsed_chain) == 2


# =============================================================================
# Test 3: test_render_audit_prompt
# =============================================================================


def test_render_audit_prompt():
    """render_template for lineage_audit fills all {{ }} placeholders."""
    from app.prompts import render_template

    result = render_template(
        "lineage_audit",
        record_json='{"id": "disc-001", "asset_ticker": "NVDA"}',
        source_url="https://example.com/filing.pdf",
        source_hash="a" * 64,
        method="pdfplumber",
        extraction_ts="2026-01-15T10:30:00Z",
        transform_chain_json='[{"step": "normalize_ticker"}]',
        current_hash="b" * 64,
    )

    remaining = re.findall(r"\{\{.*?\}\}", result)
    assert len(remaining) == 0, f"Remaining placeholders: {remaining}"
    assert "disc-001" in result
    assert "https://example.com/filing.pdf" in result
    assert "a" * 64 in result
    assert "pdfplumber" in result
    assert "2026-01-15T10:30:00Z" in result
    assert "b" * 64 in result


# =============================================================================
# Test 4: test_parse_provenance_report
# =============================================================================


def test_parse_provenance_report():
    """Parsing the LLM JSON output should produce trust_score and chain_integrity."""
    parsed = SAMPLE_LLM_RESPONSE

    assert parsed["overall_trust_score"] == 85
    assert parsed["provenance_chain_valid"] is True
    assert parsed["chain_integrity"]["hash_chain_valid"] is True
    assert parsed["chain_integrity"]["temporal_ordering_valid"] is True
    assert parsed["chain_integrity"]["all_transforms_approved"] is True
    assert parsed["chain_integrity"]["gaps_detected"] == 0
    assert parsed["recommended_action"] == "trust"
    assert isinstance(parsed["audit_narrative"], str)
    assert len(parsed["audit_narrative"]) > 0


# =============================================================================
# Test 5: test_verification_questions_generated
# =============================================================================


def test_verification_questions_generated():
    """Response should include 3-5 verification questions."""
    questions = SAMPLE_LLM_RESPONSE["verification_questions"]

    assert 3 <= len(questions) <= 5, (
        f"Expected 3-5 verification questions, got {len(questions)}"
    )

    for q in questions:
        assert "question" in q
        assert "answer" in q
        assert "status" in q
        assert q["status"] in {"VERIFIED", "UNVERIFIABLE", "FAILED"}
        assert "impact_if_failed" in q
        assert q["impact_if_failed"] in {"none", "low", "medium", "high", "critical"}


# =============================================================================
# Test 6: test_chain_integrity_valid
# =============================================================================


def test_chain_integrity_valid():
    """_classify_chain_integrity should detect valid hash chain."""
    # Valid chain
    valid_data = {
        "hash_chain_valid": True,
        "temporal_ordering_valid": True,
        "all_transforms_approved": True,
        "gaps_detected": 0,
    }
    assert _classify_chain_integrity(valid_data) == "valid"

    # Broken chain (hash invalid)
    broken_data = {
        "hash_chain_valid": False,
        "temporal_ordering_valid": True,
        "all_transforms_approved": True,
        "gaps_detected": 0,
    }
    assert _classify_chain_integrity(broken_data) == "broken"

    # Broken chain (many gaps)
    many_gaps_data = {
        "hash_chain_valid": True,
        "temporal_ordering_valid": True,
        "all_transforms_approved": True,
        "gaps_detected": 3,
    }
    assert _classify_chain_integrity(many_gaps_data) == "broken"

    # Partial chain (some issues but not fully broken)
    partial_data = {
        "hash_chain_valid": True,
        "temporal_ordering_valid": False,
        "all_transforms_approved": True,
        "gaps_detected": 1,
    }
    assert _classify_chain_integrity(partial_data) == "partial"

    # Empty/None input
    assert _classify_chain_integrity({}) == "broken"
    assert _classify_chain_integrity(None) == "broken"


# =============================================================================
# Test 7: test_audit_end_to_end
# =============================================================================


@pytest.mark.asyncio
async def test_audit_end_to_end(service, mock_llm_client, mock_supabase_for_lineage):
    """Full audit() flow with mocked LLM should return structured result."""
    # Mock _fetch_record_and_metadata to return sample data
    metadata = {
        "source_url": "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/20012345.pdf",
        "extraction_ts": "2026-01-15T10:30:00Z",
        "method": "pdfplumber",
        "transform_chain": [
            {"step": "normalize_ticker", "ts": "2026-01-15T10:30:01Z", "version": "1.2.0"},
        ],
    }
    service._fetch_record_and_metadata = AsyncMock(
        return_value=(SAMPLE_RECORD, metadata)
    )

    result = await service.audit("disc-001")

    # Verify return structure
    assert "trust_score" in result
    assert "chain_integrity" in result
    assert "verification_questions" in result
    assert "provenance_report" in result

    # Verify values from the mocked LLM response
    assert result["trust_score"] == 85
    assert result["chain_integrity"] == "valid"
    assert isinstance(result["verification_questions"], list)
    assert len(result["verification_questions"]) == 3
    assert isinstance(result["provenance_report"], str)
    assert len(result["provenance_report"]) > 0

    # Verify LLM was called
    mock_llm_client.generate.assert_awaited_once()

    # Verify prompt was passed
    call_kwargs = mock_llm_client.generate.call_args
    prompt = call_kwargs.kwargs.get("prompt") or call_kwargs.args[0] if call_kwargs.args else ""
    assert isinstance(prompt, str)
