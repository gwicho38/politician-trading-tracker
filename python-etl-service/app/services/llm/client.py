"""
LLMClient — Async wrapper around Ollama's /api/generate endpoint.

Provides retry logic, token extraction, and optional audit logging
for all LLM calls in the prompt pipeline.

Usage:
    client = LLMClient(audit_logger=my_logger)
    response = await client.generate(
        prompt="Validate this trade...",
        model="llama3.1:8b",
        system_prompt="You are a financial validation assistant.",
    )
    print(response.text, response.input_tokens, response.output_tokens)
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "https://ollama.lefv.info")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
DEFAULT_MODEL = "llama3.1:8b"

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [2, 4, 8]  # seconds


@dataclass
class LLMResponse:
    """Response from an LLM generate call."""

    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


class LLMClient:
    """
    Async wrapper around Ollama's /api/generate endpoint.

    Features:
    - Retry logic: 3 attempts with [2, 4, 8] second delays
    - Token count extraction from Ollama response
    - Optional audit logging of every call
    - Auth via Bearer token header
    """

    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
        audit_logger: Optional[object] = None,
        timeout: float = 120.0,
    ):
        self.base_url = base_url or OLLAMA_BASE_URL
        self.api_key = api_key if api_key is not None else OLLAMA_API_KEY
        self.audit_logger = audit_logger
        self.timeout = timeout

    def _build_headers(self) -> dict:
        """Build HTTP headers including auth if configured."""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _create_client(self) -> httpx.AsyncClient:
        """Create a new async HTTP client."""
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=self._build_headers(),
        )

    async def generate(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        system_prompt: str = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        Send a generate request to Ollama with retry logic.

        Args:
            prompt: The prompt text to send.
            model: Ollama model name (default: llama3.1:8b).
            system_prompt: Optional system prompt for the model.
            temperature: Sampling temperature (default: 0.1 for deterministic).
            max_tokens: Maximum tokens to generate (default: 4096).

        Returns:
            LLMResponse with text, model, token counts, and latency.

        Raises:
            httpx.HTTPError: After all retry attempts are exhausted.
        """
        body = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        if system_prompt is not None:
            body["system"] = system_prompt

        last_exception = None
        client = self._create_client()

        try:
            for attempt in range(MAX_RETRIES):
                try:
                    start_time = time.monotonic()
                    response = await client.post("/api/generate", json=body)
                    response.raise_for_status()
                    elapsed_ms = int((time.monotonic() - start_time) * 1000)

                    result = response.json()
                    llm_response = LLMResponse(
                        text=result.get("response", ""),
                        model=result.get("model", model),
                        input_tokens=result.get("prompt_eval_count", 0),
                        output_tokens=result.get("eval_count", 0),
                        latency_ms=elapsed_ms,
                    )

                    # Auto-log if audit logger is provided
                    if self.audit_logger is not None:
                        try:
                            await self.audit_logger.log(
                                service_name="llm_client",
                                prompt_version="direct",
                                prompt_hash="",
                                model_used=model,
                                response=llm_response,
                            )
                        except Exception as log_err:
                            logger.warning(f"Audit logging failed: {log_err}")

                    return llm_response

                except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout,
                        httpx.PoolTimeout, httpx.ConnectTimeout) as e:
                    last_exception = e
                    if attempt < MAX_RETRIES - 1:
                        delay = RETRY_DELAYS[attempt]
                        logger.warning(
                            f"Ollama request failed (attempt {attempt + 1}/{MAX_RETRIES}), "
                            f"retrying in {delay}s: {e}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"Ollama request failed after {MAX_RETRIES} attempts: {e}"
                        )

                except httpx.HTTPStatusError as e:
                    last_exception = e
                    if attempt < MAX_RETRIES - 1:
                        delay = RETRY_DELAYS[attempt]
                        logger.warning(
                            f"Ollama returned {e.response.status_code} "
                            f"(attempt {attempt + 1}/{MAX_RETRIES}), "
                            f"retrying in {delay}s"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"Ollama request failed after {MAX_RETRIES} attempts: "
                            f"status {e.response.status_code}"
                        )

            # All retries exhausted
            raise last_exception

        finally:
            await client.aclose()

    async def test_connection(self) -> bool:
        """
        Test connectivity to the Ollama server.

        Returns:
            True if Ollama responds with 200 on GET /api/tags, False otherwise.
        """
        client = self._create_client()
        try:
            response = await client.get("/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama connection test failed: {e}")
            return False
        finally:
            await client.aclose()
