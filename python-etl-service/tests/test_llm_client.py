"""
Tests for LLMClient and LLMAuditLogger.

Covers:
1. LLMClient.generate() sends correct request body
2. LLMClient.generate() retries on httpx errors (3 attempts)
3. LLMClient.generate() parses Ollama response correctly
4. LLMClient.generate() raises after retries exhausted
5. LLMClient.test_connection() returns True/False
6. LLMAuditLogger.log() inserts correct row into llm_audit_trail
7. LLMAuditLogger.log() doesn't raise on Supabase failure
8. LLMAuditLogger.compute_prompt_hash() returns consistent SHA-256
9. LLMClient auto-logs via audit_logger when provided
10. LLMClient.generate() with system_prompt sets Ollama system field
"""

import hashlib
import time

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm.client import LLMClient, LLMResponse
from app.services.llm.audit_logger import LLMAuditLogger


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_ollama_response():
    """Standard successful Ollama response."""
    return {
        "model": "llama3.1:8b",
        "response": '{"result": "validated", "confidence": 0.95}',
        "done": True,
        "total_duration": 1500000000,
        "prompt_eval_count": 150,
        "eval_count": 42,
    }


@pytest.fixture
def mock_audit_logger():
    """Mock LLMAuditLogger with async log method."""
    logger = AsyncMock(spec=LLMAuditLogger)
    logger.log = AsyncMock()
    return logger


# =============================================================================
# Test 1: LLMClient.generate() sends correct request body
# =============================================================================


@pytest.mark.asyncio
async def test_generate_sends_correct_request_body(mock_ollama_response):
    """generate() should POST to /api/generate with the correct JSON body."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_ollama_response
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.llm.client.httpx.AsyncClient") as MockAsyncClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.aclose = AsyncMock()
        MockAsyncClient.return_value = mock_client_instance

        client = LLMClient()
        await client.generate(
            prompt="Validate this trade",
            model="llama3.1:8b",
            temperature=0.2,
            max_tokens=2048,
        )

        # Verify post was called with correct args
        mock_client_instance.post.assert_called_once()
        call_args = mock_client_instance.post.call_args
        assert call_args[0][0] == "/api/generate"
        body = call_args[1]["json"]
        assert body["model"] == "llama3.1:8b"
        assert body["prompt"] == "Validate this trade"
        assert body["stream"] is False
        assert body["format"] == "json"
        assert body["options"]["temperature"] == 0.2
        assert body["options"]["num_predict"] == 2048
        assert "system" not in body


# =============================================================================
# Test 2: LLMClient.generate() retries on httpx errors
# =============================================================================


@pytest.mark.asyncio
async def test_generate_retries_on_httpx_errors(mock_ollama_response):
    """generate() should retry up to 3 times on transient httpx errors."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_ollama_response
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.llm.client.httpx.AsyncClient") as MockAsyncClient:
        mock_client_instance = AsyncMock()
        # Fail twice, succeed on third attempt
        mock_client_instance.post = AsyncMock(
            side_effect=[
                httpx.ConnectError("Connection refused"),
                httpx.ReadTimeout("Read timed out"),
                mock_response,
            ]
        )
        mock_client_instance.aclose = AsyncMock()
        MockAsyncClient.return_value = mock_client_instance

        with patch("app.services.llm.client.asyncio.sleep", new_callable=AsyncMock):
            client = LLMClient()
            result = await client.generate(prompt="test", model="llama3.1:8b")

        assert result.text == '{"result": "validated", "confidence": 0.95}'
        assert mock_client_instance.post.call_count == 3


# =============================================================================
# Test 3: LLMClient.generate() parses Ollama response correctly
# =============================================================================


@pytest.mark.asyncio
async def test_generate_parses_ollama_response(mock_ollama_response):
    """generate() should extract text, model, and token counts from the response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_ollama_response
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.llm.client.httpx.AsyncClient") as MockAsyncClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.aclose = AsyncMock()
        MockAsyncClient.return_value = mock_client_instance

        client = LLMClient()
        result = await client.generate(prompt="test", model="llama3.1:8b")

    assert isinstance(result, LLMResponse)
    assert result.text == '{"result": "validated", "confidence": 0.95}'
    assert result.model == "llama3.1:8b"
    assert result.input_tokens == 150
    assert result.output_tokens == 42
    assert result.latency_ms >= 0


# =============================================================================
# Test 4: LLMClient.generate() raises after retries exhausted
# =============================================================================


@pytest.mark.asyncio
async def test_generate_raises_after_retries_exhausted():
    """generate() should raise after 3 failed attempts."""
    with patch("app.services.llm.client.httpx.AsyncClient") as MockAsyncClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        mock_client_instance.aclose = AsyncMock()
        MockAsyncClient.return_value = mock_client_instance

        with patch("app.services.llm.client.asyncio.sleep", new_callable=AsyncMock):
            client = LLMClient()
            with pytest.raises(httpx.ConnectError, match="Connection refused"):
                await client.generate(prompt="test", model="llama3.1:8b")

        # Should have attempted 3 times
        assert mock_client_instance.post.call_count == 3


# =============================================================================
# Test 5: LLMClient.test_connection() returns True/False
# =============================================================================


@pytest.mark.asyncio
async def test_connection_returns_true_on_success():
    """test_connection() should return True when Ollama responds with 200."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("app.services.llm.client.httpx.AsyncClient") as MockAsyncClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_instance.aclose = AsyncMock()
        MockAsyncClient.return_value = mock_client_instance

        client = LLMClient()
        result = await client.test_connection()

    assert result is True


@pytest.mark.asyncio
async def test_connection_returns_false_on_failure():
    """test_connection() should return False when connection fails."""
    with patch("app.services.llm.client.httpx.AsyncClient") as MockAsyncClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        mock_client_instance.aclose = AsyncMock()
        MockAsyncClient.return_value = mock_client_instance

        client = LLMClient()
        result = await client.test_connection()

    assert result is False


@pytest.mark.asyncio
async def test_connection_returns_false_on_non_200():
    """test_connection() should return False on non-200 status codes."""
    mock_response = MagicMock()
    mock_response.status_code = 503

    with patch("app.services.llm.client.httpx.AsyncClient") as MockAsyncClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_instance.aclose = AsyncMock()
        MockAsyncClient.return_value = mock_client_instance

        client = LLMClient()
        result = await client.test_connection()

    assert result is False


# =============================================================================
# Test 6: LLMAuditLogger.log() inserts correct row
# =============================================================================


@pytest.mark.asyncio
async def test_audit_logger_inserts_correct_row():
    """log() should insert a row into llm_audit_trail with all fields."""
    mock_supabase = MagicMock()
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "audit-1"}])
    mock_supabase.table.return_value = mock_table

    audit_logger = LLMAuditLogger()
    audit_logger._get_supabase = MagicMock(return_value=mock_supabase)

    response = LLMResponse(
        text='{"result": "ok"}',
        model="llama3.1:8b",
        input_tokens=100,
        output_tokens=50,
        latency_ms=1200,
    )

    await audit_logger.log(
        service_name="validation_gate",
        prompt_version="v1.0",
        prompt_hash="abc123",
        model_used="llama3.1:8b",
        response=response,
        request_context={"disclosure_id": "test-123"},
        parsed_output={"result": "ok"},
        parse_success=True,
    )

    # Verify insert was called
    mock_supabase.table.assert_called_once_with("llm_audit_trail")
    insert_call = mock_table.insert.call_args[0][0]
    assert insert_call["service_name"] == "validation_gate"
    assert insert_call["prompt_version"] == "v1.0"
    assert insert_call["prompt_hash"] == "abc123"
    assert insert_call["model_used"] == "llama3.1:8b"
    assert insert_call["input_tokens"] == 100
    assert insert_call["output_tokens"] == 50
    assert insert_call["latency_ms"] == 1200
    assert insert_call["raw_response"] == '{"result": "ok"}'
    assert insert_call["parsed_output"] == {"result": "ok"}
    assert insert_call["parse_success"] is True
    assert insert_call["error_message"] is None
    assert insert_call["request_context"] == {"disclosure_id": "test-123"}


# =============================================================================
# Test 7: LLMAuditLogger.log() doesn't raise on Supabase failure
# =============================================================================


@pytest.mark.asyncio
async def test_audit_logger_does_not_raise_on_supabase_failure():
    """log() should swallow exceptions from Supabase and not raise."""
    mock_supabase = MagicMock()
    mock_supabase.table.side_effect = Exception("Supabase connection failed")

    audit_logger = LLMAuditLogger()
    audit_logger._get_supabase = MagicMock(return_value=mock_supabase)

    response = LLMResponse(
        text="test",
        model="llama3.1:8b",
        input_tokens=10,
        output_tokens=5,
        latency_ms=100,
    )

    # Should not raise
    await audit_logger.log(
        service_name="validation_gate",
        prompt_version="v1.0",
        prompt_hash="abc123",
        model_used="llama3.1:8b",
        response=response,
    )


@pytest.mark.asyncio
async def test_audit_logger_does_not_raise_when_supabase_unavailable():
    """log() should not raise when Supabase client is None."""
    audit_logger = LLMAuditLogger()
    audit_logger._get_supabase = MagicMock(return_value=None)

    response = LLMResponse(
        text="test",
        model="llama3.1:8b",
        input_tokens=10,
        output_tokens=5,
        latency_ms=100,
    )

    # Should not raise
    await audit_logger.log(
        service_name="test_service",
        prompt_version="v1.0",
        prompt_hash="abc123",
        model_used="llama3.1:8b",
        response=response,
    )


# =============================================================================
# Test 8: LLMAuditLogger.compute_prompt_hash() returns consistent SHA-256
# =============================================================================


def test_compute_prompt_hash_returns_consistent_sha256():
    """compute_prompt_hash() should return a consistent SHA-256 hex digest."""
    template = "You are a validation assistant. Check: {disclosure}"

    hash1 = LLMAuditLogger.compute_prompt_hash(template)
    hash2 = LLMAuditLogger.compute_prompt_hash(template)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex digest length

    # Verify it matches manual computation
    expected = hashlib.sha256(template.encode("utf-8")).hexdigest()
    assert hash1 == expected


def test_compute_prompt_hash_different_for_different_inputs():
    """compute_prompt_hash() should produce different hashes for different inputs."""
    hash1 = LLMAuditLogger.compute_prompt_hash("template A")
    hash2 = LLMAuditLogger.compute_prompt_hash("template B")

    assert hash1 != hash2


# =============================================================================
# Test 9: LLMClient auto-logs via audit_logger when provided
# =============================================================================


@pytest.mark.asyncio
async def test_generate_auto_logs_when_audit_logger_provided(
    mock_ollama_response, mock_audit_logger
):
    """generate() should call audit_logger.log() when an audit_logger is provided."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_ollama_response
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.llm.client.httpx.AsyncClient") as MockAsyncClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.aclose = AsyncMock()
        MockAsyncClient.return_value = mock_client_instance

        client = LLMClient(audit_logger=mock_audit_logger)
        result = await client.generate(prompt="test prompt", model="llama3.1:8b")

    # audit_logger.log should have been called once
    mock_audit_logger.log.assert_awaited_once()
    log_kwargs = mock_audit_logger.log.call_args[1]
    assert log_kwargs["service_name"] == "llm_client"
    assert log_kwargs["model_used"] == "llama3.1:8b"
    assert isinstance(log_kwargs["response"], LLMResponse)


@pytest.mark.asyncio
async def test_generate_does_not_fail_when_audit_logging_fails(
    mock_ollama_response,
):
    """generate() should succeed even if audit logging raises an exception."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_ollama_response
    mock_response.raise_for_status = MagicMock()

    failing_logger = AsyncMock(spec=LLMAuditLogger)
    failing_logger.log = AsyncMock(side_effect=Exception("Logging failed"))

    with patch("app.services.llm.client.httpx.AsyncClient") as MockAsyncClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.aclose = AsyncMock()
        MockAsyncClient.return_value = mock_client_instance

        client = LLMClient(audit_logger=failing_logger)
        result = await client.generate(prompt="test prompt", model="llama3.1:8b")

    # Should still return a valid result despite logging failure
    assert result.text == '{"result": "validated", "confidence": 0.95}'


# =============================================================================
# Test 10: LLMClient.generate() with system_prompt sets Ollama system field
# =============================================================================


@pytest.mark.asyncio
async def test_generate_with_system_prompt(mock_ollama_response):
    """generate() should include 'system' field when system_prompt is provided."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_ollama_response
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.llm.client.httpx.AsyncClient") as MockAsyncClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.aclose = AsyncMock()
        MockAsyncClient.return_value = mock_client_instance

        client = LLMClient()
        await client.generate(
            prompt="Validate this trade",
            model="llama3.1:8b",
            system_prompt="You are a financial validation assistant.",
        )

        call_args = mock_client_instance.post.call_args
        body = call_args[1]["json"]
        assert body["system"] == "You are a financial validation assistant."


@pytest.mark.asyncio
async def test_generate_without_system_prompt_omits_system_field(mock_ollama_response):
    """generate() should NOT include 'system' field when system_prompt is None."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_ollama_response
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.llm.client.httpx.AsyncClient") as MockAsyncClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.aclose = AsyncMock()
        MockAsyncClient.return_value = mock_client_instance

        client = LLMClient()
        await client.generate(
            prompt="test",
            model="llama3.1:8b",
        )

        call_args = mock_client_instance.post.call_args
        body = call_args[1]["json"]
        assert "system" not in body


# =============================================================================
# Additional edge case tests
# =============================================================================


@pytest.mark.asyncio
async def test_generate_handles_non_200_status():
    """generate() should raise on non-200 response status from Ollama."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=MagicMock(),
            response=mock_response,
        )
    )

    with patch("app.services.llm.client.httpx.AsyncClient") as MockAsyncClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.aclose = AsyncMock()
        MockAsyncClient.return_value = mock_client_instance

        with patch("app.services.llm.client.asyncio.sleep", new_callable=AsyncMock):
            client = LLMClient()
            with pytest.raises(httpx.HTTPStatusError):
                await client.generate(prompt="test", model="llama3.1:8b")


@pytest.mark.asyncio
async def test_generate_handles_missing_token_counts():
    """generate() should default token counts to 0 when not in response."""
    ollama_response = {
        "model": "llama3.1:8b",
        "response": '{"ok": true}',
        "done": True,
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = ollama_response
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.llm.client.httpx.AsyncClient") as MockAsyncClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.aclose = AsyncMock()
        MockAsyncClient.return_value = mock_client_instance

        client = LLMClient()
        result = await client.generate(prompt="test", model="llama3.1:8b")

    assert result.input_tokens == 0
    assert result.output_tokens == 0


def test_llm_response_dataclass():
    """LLMResponse dataclass should hold all expected fields."""
    resp = LLMResponse(
        text="hello",
        model="llama3.1:8b",
        input_tokens=10,
        output_tokens=5,
        latency_ms=500,
    )
    assert resp.text == "hello"
    assert resp.model == "llama3.1:8b"
    assert resp.input_tokens == 10
    assert resp.output_tokens == 5
    assert resp.latency_ms == 500
