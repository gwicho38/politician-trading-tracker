"""Tests for LLM provider configuration and failover chain."""

import os
from unittest.mock import patch

import pytest

from app.services.llm.providers import (
    AllProvidersExhaustedError,
    LLMProvider,
    build_provider_chain,
)


# ---------------------------------------------------------------------------
# LLMProvider dataclass tests
# ---------------------------------------------------------------------------


class TestLLMProviderDataclass:
    """Verify LLMProvider fields and defaults."""

    def test_fields_are_set(self):
        provider = LLMProvider(
            name="test",
            base_url="http://localhost",
            api_key="sk-test",
            default_model="model-v1",
        )
        assert provider.name == "test"
        assert provider.base_url == "http://localhost"
        assert provider.api_key == "sk-test"
        assert provider.default_model == "model-v1"

    def test_default_timeout(self):
        provider = LLMProvider(
            name="test",
            base_url="http://localhost",
            api_key="sk-test",
            default_model="model-v1",
        )
        assert provider.timeout == 120.0

    def test_custom_timeout(self):
        provider = LLMProvider(
            name="test",
            base_url="http://localhost",
            api_key="sk-test",
            default_model="model-v1",
            timeout=30.0,
        )
        assert provider.timeout == 30.0


# ---------------------------------------------------------------------------
# AllProvidersExhaustedError tests
# ---------------------------------------------------------------------------


class TestAllProvidersExhaustedError:
    """Verify custom exception behaviour."""

    def test_is_exception_subclass(self):
        assert issubclass(AllProvidersExhaustedError, Exception)

    def test_message_includes_all_providers(self):
        errors = {
            "ollama": "Connection refused",
            "xai": "401 Unauthorized",
            "groq": "Rate limited",
        }
        exc = AllProvidersExhaustedError(provider_errors=errors)
        msg = str(exc)
        for name, err in errors.items():
            assert name in msg, f"Expected provider '{name}' in message"
            assert err in msg, f"Expected error '{err}' in message"

    def test_provider_errors_attribute(self):
        errors = {"ollama": "timeout", "xai": "bad key"}
        exc = AllProvidersExhaustedError(provider_errors=errors)
        assert exc.provider_errors == errors

    def test_empty_provider_errors(self):
        exc = AllProvidersExhaustedError(provider_errors={})
        assert exc.provider_errors == {}
        # Should still be a valid string
        assert isinstance(str(exc), str)


# ---------------------------------------------------------------------------
# build_provider_chain() tests
# ---------------------------------------------------------------------------


class TestBuildProviderChain:
    """Verify provider chain construction from env vars."""

    @patch.dict(os.environ, {}, clear=True)
    def test_always_includes_ollama(self):
        """Ollama must appear even when no API keys are set."""
        chain = build_provider_chain()
        names = [p.name for p in chain]
        assert "ollama" in names

    @patch.dict(os.environ, {}, clear=True)
    def test_filters_empty_api_keys(self):
        """Providers with missing/empty API keys (except Ollama) are excluded."""
        chain = build_provider_chain()
        names = [p.name for p in chain]
        # Only ollama should remain when no keys are set
        assert names == ["ollama"]

    @patch.dict(
        os.environ,
        {
            "XAI_API_KEY": "xai-key",
            "GROQ_API_KEY": "groq-key",
            "CEREBRAS_API_KEY": "cerebras-key",
            "GEMINI_API_KEY": "gemini-key",
            "MISTRAL_API_KEY": "mistral-key",
            "OPENROUTER_API_KEY": "openrouter-key",
        },
        clear=True,
    )
    def test_preserves_priority_order(self):
        """All providers present must follow ollama > xai > groq > cerebras > gemini > mistral > openrouter."""
        chain = build_provider_chain()
        names = [p.name for p in chain]
        assert names == [
            "ollama",
            "xai",
            "groq",
            "cerebras",
            "gemini",
            "mistral",
            "openrouter",
        ]

    @patch.dict(
        os.environ,
        {"GROQ_API_KEY": "groq-key", "GEMINI_API_KEY": "gemini-key"},
        clear=True,
    )
    def test_partial_keys_preserves_order(self):
        """Only providers with keys (plus ollama) should appear, in priority order."""
        chain = build_provider_chain()
        names = [p.name for p in chain]
        assert names == ["ollama", "groq", "gemini"]

    @patch.dict(
        os.environ,
        {"OLLAMA_BASE_URL": "http://custom:11434"},
        clear=True,
    )
    def test_ollama_custom_base_url(self):
        """Ollama should respect a custom OLLAMA_BASE_URL env var."""
        chain = build_provider_chain()
        ollama = chain[0]
        assert ollama.base_url == "http://custom:11434"

    @patch.dict(os.environ, {}, clear=True)
    def test_ollama_default_base_url(self):
        """Ollama should fall back to the default base URL."""
        chain = build_provider_chain()
        ollama = chain[0]
        assert ollama.base_url == "https://ollama.lefv.info"

    @patch.dict(
        os.environ,
        {"XAI_API_KEY": "xai-key"},
        clear=True,
    )
    def test_provider_default_models(self):
        """Each provider should carry its correct default model."""
        chain = build_provider_chain()
        model_map = {p.name: p.default_model for p in chain}
        assert model_map["ollama"] == "llama3.1:8b"
        assert model_map["xai"] == "grok-3-mini-fast"

    @patch.dict(
        os.environ,
        {"OLLAMA_API_KEY": "ollama-secret"},
        clear=True,
    )
    def test_ollama_api_key_from_env(self):
        """Ollama should pick up its API key from env when set."""
        chain = build_provider_chain()
        ollama = chain[0]
        assert ollama.api_key == "ollama-secret"

    @patch.dict(os.environ, {}, clear=True)
    def test_ollama_api_key_empty_when_unset(self):
        """Ollama should have empty api_key when env var is not set."""
        chain = build_provider_chain()
        ollama = chain[0]
        assert ollama.api_key == ""

    @patch.dict(
        os.environ,
        {"XAI_API_KEY": ""},
        clear=True,
    )
    def test_empty_string_key_is_filtered(self):
        """An explicitly-set empty string key should still be filtered out."""
        chain = build_provider_chain()
        names = [p.name for p in chain]
        assert "xai" not in names
