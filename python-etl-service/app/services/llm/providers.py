"""
LLM provider configuration and failover chain.

Defines the provider registry (base URLs, default models, env-var keys)
and a builder that constructs an ordered list of ``LLMProvider`` instances
from the current environment.  Providers whose API keys are absent or
empty are silently skipped — except Ollama, which is always included
as the first-priority provider.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class LLMProvider:
    """Single LLM provider endpoint configuration."""

    name: str
    base_url: str
    api_key: str
    default_model: str
    timeout: float = field(default=120.0)


class AllProvidersExhaustedError(Exception):
    """Raised when every provider in the chain has failed.

    Parameters
    ----------
    provider_errors:
        Mapping of ``{provider_name: error_description}`` for every
        provider that was tried.
    """

    def __init__(self, provider_errors: dict[str, str]) -> None:
        self.provider_errors = provider_errors
        lines = [f"  {name}: {err}" for name, err in provider_errors.items()]
        detail = "\n".join(lines)
        message = (
            f"All LLM providers exhausted ({len(provider_errors)} tried):\n{detail}"
            if lines
            else "All LLM providers exhausted (0 tried)"
        )
        super().__init__(message)


# ---------------------------------------------------------------------------
# Provider registry — ordered by priority (lower index = higher priority)
# ---------------------------------------------------------------------------

_PROVIDER_SPECS: list[dict] = [
    {
        "name": "ollama",
        "base_url_env": "OLLAMA_BASE_URL",
        "base_url_default": "https://ollama.lefv.info",
        "api_key_env": "OLLAMA_API_KEY",
        "default_model": "llama3.1:8b",
        "always_include": True,
    },
    {
        "name": "xai",
        "base_url_default": "https://api.x.ai/v1",
        "api_key_env": "XAI_API_KEY",
        "default_model": "grok-3-mini-fast",
    },
    {
        "name": "groq",
        "base_url_default": "https://api.groq.com/openai",
        "api_key_env": "GROQ_API_KEY",
        "default_model": "llama-3.3-70b-versatile",
    },
    {
        "name": "cerebras",
        "base_url_default": "https://api.cerebras.ai",
        "api_key_env": "CEREBRAS_API_KEY",
        "default_model": "llama-3.3-70b",
    },
    {
        "name": "gemini",
        "base_url_default": "https://generativelanguage.googleapis.com/v1beta/openai",
        "api_key_env": "GEMINI_API_KEY",
        "default_model": "gemini-2.5-flash",
    },
    {
        "name": "mistral",
        "base_url_default": "https://api.mistral.ai",
        "api_key_env": "MISTRAL_API_KEY",
        "default_model": "mistral-small-latest",
    },
    {
        "name": "openrouter",
        "base_url_default": "https://openrouter.ai/api",
        "api_key_env": "OPENROUTER_API_KEY",
        "default_model": "meta-llama/llama-3.3-70b-instruct:free",
    },
]


def build_provider_chain() -> list[LLMProvider]:
    """Build an ordered list of LLM providers from environment variables.

    Providers whose API key is missing or empty are excluded — except
    Ollama which is **always** included regardless of key presence.

    Returns
    -------
    list[LLMProvider]
        Providers sorted by priority (Ollama first).
    """
    chain: list[LLMProvider] = []
    for spec in _PROVIDER_SPECS:
        api_key = os.environ.get(spec["api_key_env"], "")
        always_include = spec.get("always_include", False)

        if not api_key and not always_include:
            continue

        base_url_env = spec.get("base_url_env")
        if base_url_env:
            base_url = os.environ.get(base_url_env, spec["base_url_default"])
        else:
            base_url = spec["base_url_default"]

        chain.append(
            LLMProvider(
                name=spec["name"],
                base_url=base_url,
                api_key=api_key,
                default_model=spec["default_model"],
            )
        )
    return chain
