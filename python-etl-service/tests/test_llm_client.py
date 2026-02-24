"""
Tests for LLMClient with OpenAI-format multi-provider failover.

Covers:
1.  generate() sends OpenAI chat completions format (POST /v1/chat/completions)
2.  generate() includes system_prompt as system message
3.  generate() omits system message when system_prompt is None
4.  generate() parses OpenAI response (choices[0].message.content, usage)
5.  generate() retries within a provider on transient errors
6.  generate() fails over to next provider after retries exhausted
7.  generate() skips immediately on 401/403
8.  generate() skips immediately on 429
9.  generate() raises AllProvidersExhaustedError when all fail
10. generate() sets LLMResponse.provider field correctly
11. generate() auto-logs via audit_logger
12. generate() succeeds even when audit logging fails
13. generate() handles missing usage field (defaults to 0)
14. test_connections() returns per-provider status dict
15. LLMResponse has provider field with default "unknown"
16. Audit logger tests (LLMResponse now has provider field)
"""

import hashlib

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm.client import LLMClient, LLMResponse, _ProviderExhausted
from app.services.llm.providers import (
    AllProvidersExhaustedError,
    LLMProvider,
    build_provider_chain,
)
from app.services.llm.audit_logger import LLMAuditLogger


# =============================================================================
# Helpers
# =============================================================================


def _make_provider(name: str = "test", base_url: str = "http://localhost:11434",
                   api_key: str = "sk-test", default_model: str = "test-model",
                   timeout: float = 120.0) -> LLMProvider:
    return LLMProvider(
        name=name,
        base_url=base_url,
        api_key=api_key,
        default_model=default_model,
        timeout=timeout,
    )


def _openai_response(content: str = '{"result": "ok"}',
                     model: str = "test-model",
                     prompt_tokens: int = 100,
                     completion_tokens: int = 50) -> dict:
    """Build a standard OpenAI chat completions response dict."""
    return {
        "id": "chatcmpl-abc123",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def _mock_httpx_response(status_code: int = 200, json_data: dict = None) -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    if status_code >= 400:
        resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                f"{status_code} Error",
                request=MagicMock(),
                response=resp,
            )
        )
    else:
        resp.raise_for_status = MagicMock()
    return resp


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def two_providers():
    """Return two mock providers for failover testing."""
    return [
        _make_provider(name="primary", base_url="http://primary:8080",
                       api_key="pk", default_model="model-a"),
        _make_provider(name="secondary", base_url="http://secondary:8080",
                       api_key="sk", default_model="model-b"),
    ]


@pytest.fixture
def mock_audit_logger():
    """Mock LLMAuditLogger with async log method."""
    logger = AsyncMock(spec=LLMAuditLogger)
    logger.log = AsyncMock()
    return logger


# =============================================================================
# Test 1: generate() sends OpenAI chat completions format
# =============================================================================


@pytest.mark.asyncio
async def test_generate_sends_openai_chat_completions_format():
    """generate() should POST to /v1/chat/completions with messages array."""
    provider = _make_provider()
    ok_resp = _mock_httpx_response(200, _openai_response())

    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=ok_resp)
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        client = LLMClient(providers=[provider])
        await client.generate(
            prompt="Validate this trade",
            model="test-model",
            temperature=0.2,
            max_tokens=2048,
        )

        mock_instance.post.assert_called_once()
        call_args = mock_instance.post.call_args
        assert call_args[0][0] == "/v1/chat/completions"
        body = call_args[1]["json"]
        assert body["model"] == "test-model"
        assert "messages" in body
        assert isinstance(body["messages"], list)
        # Should have user message only (no system)
        assert len(body["messages"]) == 1
        assert body["messages"][0]["role"] == "user"
        assert body["messages"][0]["content"] == "Validate this trade"
        assert body["temperature"] == 0.2
        assert body["max_tokens"] == 2048


# =============================================================================
# Test 2: generate() includes system_prompt as system message
# =============================================================================


@pytest.mark.asyncio
async def test_generate_includes_system_prompt():
    """generate() should prepend a system message when system_prompt is given."""
    provider = _make_provider()
    ok_resp = _mock_httpx_response(200, _openai_response())

    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=ok_resp)
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        client = LLMClient(providers=[provider])
        await client.generate(
            prompt="Validate this trade",
            system_prompt="You are a financial assistant.",
        )

        body = mock_instance.post.call_args[1]["json"]
        assert len(body["messages"]) == 2
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][0]["content"] == "You are a financial assistant."
        assert body["messages"][1]["role"] == "user"
        assert body["messages"][1]["content"] == "Validate this trade"


# =============================================================================
# Test 3: generate() omits system message when system_prompt is None
# =============================================================================


@pytest.mark.asyncio
async def test_generate_omits_system_message_when_none():
    """generate() should NOT include system message when system_prompt is None."""
    provider = _make_provider()
    ok_resp = _mock_httpx_response(200, _openai_response())

    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=ok_resp)
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        client = LLMClient(providers=[provider])
        await client.generate(prompt="test")

        body = mock_instance.post.call_args[1]["json"]
        assert len(body["messages"]) == 1
        assert body["messages"][0]["role"] == "user"


# =============================================================================
# Test 4: generate() parses OpenAI response correctly
# =============================================================================


@pytest.mark.asyncio
async def test_generate_parses_openai_response():
    """generate() should extract content, model, and token counts from OpenAI response."""
    provider = _make_provider(name="myp")
    resp_data = _openai_response(
        content='{"validated": true}',
        model="test-model",
        prompt_tokens=150,
        completion_tokens=42,
    )
    ok_resp = _mock_httpx_response(200, resp_data)

    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=ok_resp)
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        client = LLMClient(providers=[provider])
        result = await client.generate(prompt="test")

    assert isinstance(result, LLMResponse)
    assert result.text == '{"validated": true}'
    assert result.model == "test-model"
    assert result.input_tokens == 150
    assert result.output_tokens == 42
    assert result.latency_ms >= 0
    assert result.provider == "myp"


# =============================================================================
# Test 5: generate() retries within a provider on transient errors
# =============================================================================


@pytest.mark.asyncio
async def test_generate_retries_on_transient_errors():
    """generate() should retry up to 3 times within a provider on transient errors."""
    provider = _make_provider()
    ok_resp = _mock_httpx_response(200, _openai_response())

    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        # Fail twice, succeed on third attempt
        mock_instance.post = AsyncMock(
            side_effect=[
                httpx.ConnectError("Connection refused"),
                httpx.ReadTimeout("Read timed out"),
                ok_resp,
            ]
        )
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        with patch("app.services.llm.client.asyncio.sleep", new_callable=AsyncMock):
            client = LLMClient(providers=[provider])
            result = await client.generate(prompt="test")

    assert result.text == '{"result": "ok"}'
    assert mock_instance.post.call_count == 3


@pytest.mark.asyncio
async def test_generate_retries_on_5xx():
    """generate() should retry within a provider on 5xx HTTP errors."""
    provider = _make_provider()
    error_resp = _mock_httpx_response(500, {"error": "Internal Server Error"})
    ok_resp = _mock_httpx_response(200, _openai_response())

    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(side_effect=[error_resp, ok_resp])
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        with patch("app.services.llm.client.asyncio.sleep", new_callable=AsyncMock):
            client = LLMClient(providers=[provider])
            result = await client.generate(prompt="test")

    assert result.text == '{"result": "ok"}'
    assert mock_instance.post.call_count == 2


# =============================================================================
# Test 6: generate() fails over to next provider after retries exhausted
# =============================================================================


@pytest.mark.asyncio
async def test_generate_failover_to_next_provider(two_providers):
    """generate() should fail over to next provider after retries exhausted."""
    ok_resp = _mock_httpx_response(200, _openai_response(content="from secondary"))

    call_count = {"n": 0}

    async def mock_post(url, **kwargs):
        call_count["n"] += 1
        # First 3 calls (primary retries) fail, then secondary succeeds
        if call_count["n"] <= 3:
            raise httpx.ConnectError("Connection refused")
        return ok_resp

    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(side_effect=mock_post)
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        with patch("app.services.llm.client.asyncio.sleep", new_callable=AsyncMock):
            client = LLMClient(providers=two_providers)
            result = await client.generate(prompt="test")

    assert result.text == "from secondary"
    assert result.provider == "secondary"
    # 3 retries on primary + 1 success on secondary = 4 total calls
    assert call_count["n"] == 4


# =============================================================================
# Test 7: generate() skips immediately on 401/403
# =============================================================================


@pytest.mark.asyncio
async def test_generate_skips_on_401(two_providers):
    """generate() should skip immediately to next provider on 401."""
    auth_error_resp = _mock_httpx_response(401)
    ok_resp = _mock_httpx_response(200, _openai_response(content="ok from secondary"))

    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(side_effect=[auth_error_resp, ok_resp])
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        client = LLMClient(providers=two_providers)
        result = await client.generate(prompt="test")

    assert result.text == "ok from secondary"
    assert result.provider == "secondary"
    # 1 call to primary (skipped, no retry), 1 call to secondary = 2
    assert mock_instance.post.call_count == 2


@pytest.mark.asyncio
async def test_generate_skips_on_403(two_providers):
    """generate() should skip immediately to next provider on 403."""
    auth_error_resp = _mock_httpx_response(403)
    ok_resp = _mock_httpx_response(200, _openai_response(content="ok from secondary"))

    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(side_effect=[auth_error_resp, ok_resp])
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        client = LLMClient(providers=two_providers)
        result = await client.generate(prompt="test")

    assert result.text == "ok from secondary"
    assert result.provider == "secondary"
    assert mock_instance.post.call_count == 2


# =============================================================================
# Test 8: generate() skips immediately on 429
# =============================================================================


@pytest.mark.asyncio
async def test_generate_skips_on_429(two_providers):
    """generate() should skip immediately to next provider on 429 (rate limit)."""
    rate_limit_resp = _mock_httpx_response(429)
    ok_resp = _mock_httpx_response(200, _openai_response(content="ok from secondary"))

    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(side_effect=[rate_limit_resp, ok_resp])
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        client = LLMClient(providers=two_providers)
        result = await client.generate(prompt="test")

    assert result.text == "ok from secondary"
    assert result.provider == "secondary"
    assert mock_instance.post.call_count == 2


# =============================================================================
# Test 9: generate() raises AllProvidersExhaustedError when all fail
# =============================================================================


@pytest.mark.asyncio
async def test_generate_raises_all_providers_exhausted(two_providers):
    """generate() should raise AllProvidersExhaustedError when every provider fails."""
    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        with patch("app.services.llm.client.asyncio.sleep", new_callable=AsyncMock):
            client = LLMClient(providers=two_providers)
            with pytest.raises(AllProvidersExhaustedError) as exc_info:
                await client.generate(prompt="test")

    assert "primary" in exc_info.value.provider_errors
    assert "secondary" in exc_info.value.provider_errors
    # 3 retries * 2 providers = 6 total calls
    assert mock_instance.post.call_count == 6


@pytest.mark.asyncio
async def test_generate_all_providers_exhausted_skip_codes():
    """AllProvidersExhaustedError includes errors from all skipped providers."""
    providers = [
        _make_provider(name="p1"),
        _make_provider(name="p2"),
    ]
    resp_401 = _mock_httpx_response(401)
    resp_403 = _mock_httpx_response(403)

    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(side_effect=[resp_401, resp_403])
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        client = LLMClient(providers=providers)
        with pytest.raises(AllProvidersExhaustedError) as exc_info:
            await client.generate(prompt="test")

    assert "p1" in exc_info.value.provider_errors
    assert "p2" in exc_info.value.provider_errors


# =============================================================================
# Test 10: generate() sets LLMResponse.provider field correctly
# =============================================================================


@pytest.mark.asyncio
async def test_generate_sets_provider_field():
    """generate() should set LLMResponse.provider to the name of the provider that succeeded."""
    provider = _make_provider(name="my-ollama")
    ok_resp = _mock_httpx_response(200, _openai_response())

    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=ok_resp)
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        client = LLMClient(providers=[provider])
        result = await client.generate(prompt="test")

    assert result.provider == "my-ollama"


# =============================================================================
# Test 11: generate() auto-logs via audit_logger
# =============================================================================


@pytest.mark.asyncio
async def test_generate_auto_logs_when_audit_logger_provided(mock_audit_logger):
    """generate() should call audit_logger.log() when provided."""
    provider = _make_provider(name="testprov")
    ok_resp = _mock_httpx_response(200, _openai_response())

    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=ok_resp)
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        client = LLMClient(providers=[provider], audit_logger=mock_audit_logger)
        result = await client.generate(prompt="test prompt", model="test-model")

    mock_audit_logger.log.assert_awaited_once()
    log_kwargs = mock_audit_logger.log.call_args[1]
    assert log_kwargs["service_name"] == "llm_client"
    assert log_kwargs["model_used"] == "test-model"
    assert isinstance(log_kwargs["response"], LLMResponse)
    assert log_kwargs["response"].provider == "testprov"


# =============================================================================
# Test 12: generate() succeeds even when audit logging fails
# =============================================================================


@pytest.mark.asyncio
async def test_generate_succeeds_when_audit_logging_fails():
    """generate() should still return a result even if audit logging raises."""
    provider = _make_provider()
    ok_resp = _mock_httpx_response(200, _openai_response(content="good result"))

    failing_logger = AsyncMock(spec=LLMAuditLogger)
    failing_logger.log = AsyncMock(side_effect=Exception("Logging failed"))

    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=ok_resp)
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        client = LLMClient(providers=[provider], audit_logger=failing_logger)
        result = await client.generate(prompt="test")

    assert result.text == "good result"


# =============================================================================
# Test 13: generate() handles missing usage field (defaults to 0)
# =============================================================================


@pytest.mark.asyncio
async def test_generate_handles_missing_usage():
    """generate() should default token counts to 0 when usage is missing."""
    provider = _make_provider()
    resp_data = {
        "id": "chatcmpl-abc",
        "object": "chat.completion",
        "model": "test-model",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "hello"},
                "finish_reason": "stop",
            }
        ],
        # No "usage" field at all
    }
    ok_resp = _mock_httpx_response(200, resp_data)

    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=ok_resp)
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        client = LLMClient(providers=[provider])
        result = await client.generate(prompt="test")

    assert result.input_tokens == 0
    assert result.output_tokens == 0
    assert result.text == "hello"


# =============================================================================
# Test 14: test_connections() returns per-provider status dict
# =============================================================================


@pytest.mark.asyncio
async def test_connections_returns_per_provider_dict(two_providers):
    """test_connections() should return {provider_name: bool} for each provider."""
    ok_resp = MagicMock()
    ok_resp.status_code = 200

    error_resp = MagicMock()
    error_resp.status_code = 503

    call_count = {"n": 0}

    async def mock_get(url, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return ok_resp
        return error_resp

    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(side_effect=mock_get)
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        client = LLMClient(providers=two_providers)
        result = await client.test_connections()

    assert result == {"primary": True, "secondary": False}


@pytest.mark.asyncio
async def test_connections_handles_connection_error(two_providers):
    """test_connections() should return False for providers that raise exceptions."""
    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        client = LLMClient(providers=two_providers)
        result = await client.test_connections()

    assert result == {"primary": False, "secondary": False}


# =============================================================================
# Test 15: LLMResponse has provider field with default "unknown"
# =============================================================================


def test_llm_response_provider_field_default():
    """LLMResponse should have provider field with default 'unknown'."""
    resp = LLMResponse(
        text="hello",
        model="test",
        input_tokens=10,
        output_tokens=5,
        latency_ms=500,
    )
    assert resp.provider == "unknown"


def test_llm_response_provider_field_set():
    """LLMResponse should accept an explicit provider value."""
    resp = LLMResponse(
        text="hello",
        model="test",
        input_tokens=10,
        output_tokens=5,
        latency_ms=500,
        provider="ollama",
    )
    assert resp.provider == "ollama"


def test_llm_response_dataclass_all_fields():
    """LLMResponse dataclass should hold all expected fields."""
    resp = LLMResponse(
        text="hello",
        model="llama3.1:8b",
        input_tokens=10,
        output_tokens=5,
        latency_ms=500,
        provider="xai",
    )
    assert resp.text == "hello"
    assert resp.model == "llama3.1:8b"
    assert resp.input_tokens == 10
    assert resp.output_tokens == 5
    assert resp.latency_ms == 500
    assert resp.provider == "xai"


# =============================================================================
# Test 16: Audit logger tests (LLMResponse with provider field)
# =============================================================================


@pytest.mark.asyncio
async def test_audit_logger_receives_provider_in_response(mock_audit_logger):
    """Audit logger should receive LLMResponse with provider field populated."""
    provider = _make_provider(name="groq-provider")
    ok_resp = _mock_httpx_response(200, _openai_response())

    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=ok_resp)
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        client = LLMClient(providers=[provider], audit_logger=mock_audit_logger)
        await client.generate(prompt="test")

    log_kwargs = mock_audit_logger.log.call_args[1]
    assert log_kwargs["response"].provider == "groq-provider"


@pytest.mark.asyncio
async def test_audit_logger_inserts_correct_row():
    """LLMAuditLogger.log() should insert a row into llm_audit_trail with all fields."""
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
        provider="ollama",
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

    mock_supabase.table.assert_called_once_with("llm_audit_trail")
    insert_call = mock_table.insert.call_args[0][0]
    assert insert_call["service_name"] == "validation_gate"
    assert insert_call["input_tokens"] == 100
    assert insert_call["output_tokens"] == 50
    assert insert_call["latency_ms"] == 1200


@pytest.mark.asyncio
async def test_audit_logger_does_not_raise_on_supabase_failure():
    """LLMAuditLogger.log() should swallow exceptions from Supabase."""
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
        provider="ollama",
    )

    # Should not raise
    await audit_logger.log(
        service_name="validation_gate",
        prompt_version="v1.0",
        prompt_hash="abc123",
        model_used="llama3.1:8b",
        response=response,
    )


def test_compute_prompt_hash_returns_consistent_sha256():
    """compute_prompt_hash() should return a consistent SHA-256 hex digest."""
    template = "You are a validation assistant. Check: {disclosure}"
    hash1 = LLMAuditLogger.compute_prompt_hash(template)
    hash2 = LLMAuditLogger.compute_prompt_hash(template)
    assert hash1 == hash2
    assert len(hash1) == 64
    expected = hashlib.sha256(template.encode("utf-8")).hexdigest()
    assert hash1 == expected


# =============================================================================
# Additional edge case tests
# =============================================================================


@pytest.mark.asyncio
async def test_generate_uses_provider_default_model():
    """generate() should use the provider's default_model when model is DEFAULT_MODEL."""
    provider = _make_provider(name="xai", default_model="grok-3-mini-fast")
    ok_resp = _mock_httpx_response(200, _openai_response(model="grok-3-mini-fast"))

    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=ok_resp)
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        client = LLMClient(providers=[provider])
        result = await client.generate(prompt="test")

    body = mock_instance.post.call_args[1]["json"]
    assert body["model"] == "grok-3-mini-fast"


@pytest.mark.asyncio
async def test_generate_explicit_model_overrides_default():
    """generate() should use the explicit model even when provider has a default."""
    provider = _make_provider(name="xai", default_model="grok-3-mini-fast")
    ok_resp = _mock_httpx_response(200, _openai_response(model="custom-model"))

    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=ok_resp)
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        client = LLMClient(providers=[provider])
        result = await client.generate(prompt="test", model="custom-model")

    body = mock_instance.post.call_args[1]["json"]
    assert body["model"] == "custom-model"


@pytest.mark.asyncio
async def test_backward_compat_test_connection():
    """test_connection() should return True if any provider is up (backward compat)."""
    providers = [
        _make_provider(name="down"),
        _make_provider(name="up"),
    ]

    call_count = {"n": 0}

    async def mock_get(url, **kwargs):
        call_count["n"] += 1
        resp = MagicMock()
        if call_count["n"] == 1:
            raise httpx.ConnectError("refused")
        resp.status_code = 200
        return resp

    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(side_effect=mock_get)
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        client = LLMClient(providers=providers)
        result = await client.test_connection()

    assert result is True


@pytest.mark.asyncio
async def test_backward_compat_test_connection_all_down():
    """test_connection() should return False when all providers are down."""
    providers = [_make_provider(name="down")]

    with patch("app.services.llm.client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_instance.aclose = AsyncMock()
        MockClient.return_value = mock_instance

        client = LLMClient(providers=providers)
        result = await client.test_connection()

    assert result is False


@pytest.mark.asyncio
async def test_constructor_defaults_to_build_provider_chain():
    """LLMClient() with no providers arg should call build_provider_chain()."""
    with patch("app.services.llm.client.build_provider_chain") as mock_build:
        mock_build.return_value = [_make_provider(name="auto")]
        client = LLMClient()
        assert len(client.providers) == 1
        assert client.providers[0].name == "auto"
        mock_build.assert_called_once()


def test_provider_exhausted_is_exception():
    """_ProviderExhausted should be a valid exception."""
    exc = _ProviderExhausted("test error")
    assert isinstance(exc, Exception)
    assert str(exc) == "test error"


@pytest.mark.asyncio
async def test_generate_creates_separate_client_per_provider(two_providers):
    """generate() should create a new httpx client for each provider it tries."""
    ok_resp = _mock_httpx_response(200, _openai_response())
    clients_created = []

    def make_client(**kwargs):
        instance = AsyncMock()
        clients_created.append(kwargs.get("base_url", "unknown"))
        if len(clients_created) == 1:
            # First provider fails
            instance.post = AsyncMock(side_effect=httpx.ConnectError("down"))
        else:
            # Second provider succeeds
            instance.post = AsyncMock(return_value=ok_resp)
        instance.aclose = AsyncMock()
        return instance

    with patch("app.services.llm.client.httpx.AsyncClient", side_effect=make_client):
        with patch("app.services.llm.client.asyncio.sleep", new_callable=AsyncMock):
            client = LLMClient(providers=two_providers)
            result = await client.generate(prompt="test")

    assert len(clients_created) == 2
    assert result.provider == "secondary"
