"""
LLMClient -- Async wrapper using the OpenAI /v1/chat/completions format
with multi-provider failover.

Iterates through an ordered list of ``LLMProvider`` instances (built by
``build_provider_chain()``).  For each provider it retries up to 3 times
on transient network / 5xx errors, then falls to the next provider.
Auth errors (401/403) and rate-limit (429) skip immediately.

Usage:
    client = LLMClient(audit_logger=my_logger)
    response = await client.generate(
        prompt="Validate this trade...",
        system_prompt="You are a financial validation assistant.",
    )
    print(response.text, response.input_tokens, response.output_tokens)
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field

import httpx

from app.services.llm.providers import (
    AllProvidersExhaustedError,
    LLMProvider,
    build_provider_chain,
)

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [2, 4, 8]  # seconds

# HTTP status codes that trigger an immediate skip to the next provider
SKIP_STATUS_CODES = {401, 403, 429}

# Transient network errors worth retrying within the same provider
_TRANSIENT_ERRORS = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.ConnectTimeout,
)


@dataclass
class LLMResponse:
    """Response from an LLM generate call."""

    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    provider: str = field(default="unknown")


class _ProviderExhausted(Exception):
    """Internal control-flow exception: all retries for one provider used up."""


class LLMClient:
    """
    Async wrapper around the OpenAI /v1/chat/completions endpoint with
    multi-provider failover.

    Features:
    - Multi-provider failover: iterates through providers on failure
    - Retry logic: 3 attempts per provider with [2, 4, 8] second delays
    - Immediate skip on 401/403 (auth) and 429 (rate limit)
    - OpenAI chat completions message format
    - Token count extraction from OpenAI usage object
    - Optional audit logging of every call
    - Auth via Bearer token header
    """

    def __init__(
        self,
        providers: list[LLMProvider] | None = None,
        audit_logger: object | None = None,
    ):
        self.providers = providers if providers is not None else build_provider_chain()
        self.audit_logger = audit_logger

    def _build_headers(self, provider: LLMProvider) -> dict:
        """Build HTTP headers including auth if configured."""
        headers = {"Content-Type": "application/json"}
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"
        return headers

    def _create_client(self, provider: LLMProvider) -> httpx.AsyncClient:
        """Create a new async HTTP client for a specific provider."""
        return httpx.AsyncClient(
            base_url=provider.base_url,
            timeout=provider.timeout,
            headers=self._build_headers(provider),
        )

    def _build_messages(
        self, prompt: str, system_prompt: str | None
    ) -> list[dict[str, str]]:
        """Convert prompt + optional system_prompt into an OpenAI messages array."""
        messages: list[dict[str, str]] = []
        if system_prompt is not None:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _resolve_model(self, model: str | None, provider: LLMProvider) -> str:
        """Return the model to use: explicit override or provider default."""
        if model is not None:
            return model
        return provider.default_model

    async def _try_provider(
        self,
        provider: LLMProvider,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """
        Attempt to generate a response from a single provider.

        Raises:
            _ProviderExhausted: All retries for this provider are used up.
        """
        resolved_model = self._resolve_model(model, provider)
        body = {
            "model": resolved_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        last_exception: Exception | None = None
        client = self._create_client(provider)

        try:
            for attempt in range(MAX_RETRIES):
                try:
                    start_time = time.monotonic()
                    response = await client.post("/v1/chat/completions", json=body)
                    response.raise_for_status()
                    elapsed_ms = int((time.monotonic() - start_time) * 1000)

                    result = response.json()
                    usage = result.get("usage", {})
                    content = ""
                    choices = result.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")

                    return LLMResponse(
                        text=content,
                        model=result.get("model", resolved_model),
                        input_tokens=usage.get("prompt_tokens", 0),
                        output_tokens=usage.get("completion_tokens", 0),
                        latency_ms=elapsed_ms,
                        provider=provider.name,
                    )

                except httpx.HTTPStatusError as e:
                    status = e.response.status_code
                    if status in SKIP_STATUS_CODES:
                        logger.warning(
                            f"Provider {provider.name} returned {status}, "
                            f"skipping to next provider"
                        )
                        raise _ProviderExhausted(
                            f"HTTP {status} from {provider.name}"
                        ) from e

                    # 5xx or other retryable status
                    last_exception = e
                    if attempt < MAX_RETRIES - 1:
                        delay = RETRY_DELAYS[attempt]
                        logger.warning(
                            f"Provider {provider.name} returned {status} "
                            f"(attempt {attempt + 1}/{MAX_RETRIES}), "
                            f"retrying in {delay}s"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"Provider {provider.name} failed after "
                            f"{MAX_RETRIES} attempts: status {status}"
                        )

                except _TRANSIENT_ERRORS as e:
                    last_exception = e
                    if attempt < MAX_RETRIES - 1:
                        delay = RETRY_DELAYS[attempt]
                        logger.warning(
                            f"Provider {provider.name} request failed "
                            f"(attempt {attempt + 1}/{MAX_RETRIES}), "
                            f"retrying in {delay}s: {e}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"Provider {provider.name} failed after "
                            f"{MAX_RETRIES} attempts: {e}"
                        )

            # All retries exhausted for this provider
            raise _ProviderExhausted(str(last_exception))

        finally:
            await client.aclose()

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        Send a generate request using the OpenAI chat completions format,
        iterating through providers on failure.

        Args:
            prompt: The prompt text to send.
            model: Model name override. When None (default), the provider's
                   own default_model is used.
            system_prompt: Optional system prompt for the model.
            temperature: Sampling temperature (default: 0.1).
            max_tokens: Maximum tokens to generate (default: 4096).

        Returns:
            LLMResponse with text, model, token counts, latency, and provider.

        Raises:
            AllProvidersExhaustedError: After all providers have failed.
        """
        messages = self._build_messages(prompt, system_prompt)
        provider_errors: dict[str, str] = {}

        for provider in self.providers:
            try:
                llm_response = await self._try_provider(
                    provider, messages, model, temperature, max_tokens
                )

                # Auto-log if audit logger is provided
                if self.audit_logger is not None:
                    try:
                        await self.audit_logger.log(
                            service_name="llm_client",
                            prompt_version="direct",
                            prompt_hash="",
                            model_used=f"{llm_response.provider}/{llm_response.model}",
                            response=llm_response,
                        )
                    except Exception as log_err:
                        logger.warning(f"Audit logging failed: {log_err}")

                return llm_response

            except _ProviderExhausted as e:
                provider_errors[provider.name] = str(e)
                logger.info(
                    f"Provider {provider.name} exhausted, "
                    f"trying next ({len(provider_errors)}/{len(self.providers)})"
                )
                continue

        raise AllProvidersExhaustedError(provider_errors)

    async def test_connections(self) -> dict[str, bool]:
        """
        Test connectivity to every provider in the chain.

        Returns:
            Dict mapping provider name to connectivity status (True/False).
        """
        results: dict[str, bool] = {}
        for provider in self.providers:
            client = self._create_client(provider)
            try:
                response = await client.get("/v1/models")
                results[provider.name] = response.status_code == 200
            except Exception as e:
                logger.warning(
                    f"Connection test failed for {provider.name}: {e}"
                )
                results[provider.name] = False
            finally:
                await client.aclose()
        return results

    async def test_connection(self) -> bool:
        """
        Test connectivity to any provider in the chain (backward compat).

        Returns:
            True if at least one provider responds with 200, False otherwise.
        """
        statuses = await self.test_connections()
        return any(statuses.values())
