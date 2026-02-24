"""
LLM integration package with multi-provider failover.

Provides a shared async LLMClient that tries providers in priority order
(Ollama -> xAI -> Groq -> Cerebras -> Gemini -> Mistral -> OpenRouter) and
audit logging infrastructure used by all prompt pipeline services.
"""

from app.services.llm.client import LLMClient, LLMResponse  # noqa: F401
from app.services.llm.providers import (  # noqa: F401
    AllProvidersExhaustedError,
    LLMProvider,
    build_provider_chain,
)
