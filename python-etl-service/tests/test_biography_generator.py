"""
Tests for Biography Generator Service (app/services/biography_generator.py).

Tests:
- generate_fallback_bio() - Template-based biography generation
- build_ollama_prompt() - Ollama prompt construction
- clean_llm_response() - LLM response cleaning/preamble stripping
- query_ollama_for_bio() - Ollama API calls
- BiographyJob - Background job class
- get_bio_job(), create_bio_job() - Job registry functions
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime


# =============================================================================
# generate_fallback_bio() Tests
# =============================================================================

class TestGenerateFallbackBio:
    """Tests for generate_fallback_bio() function."""

    def test_generates_bio_for_democrat_representative(self):
        """generate_fallback_bio() produces correct bio for Democrat Representative."""
        from app.services.biography_generator import generate_fallback_bio

        politician = {
            "full_name": "Nancy Pelosi",
            "party": "D",
            "role": "Representative",
            "state_or_country": "California",
        }
        stats = {
            "total_trades": 150,
            "total_volume": 5000000,
            "top_tickers": ["AAPL", "MSFT", "NVDA"],
        }

        bio = generate_fallback_bio(politician, stats)

        assert "Nancy Pelosi" in bio
        assert "Democratic" in bio
        assert "Representative" in bio
        assert "California" in bio
        assert "150 trades" in bio
        assert "$5,000,000" in bio
        assert "AAPL" in bio
        assert "MSFT" in bio
        assert "NVDA" in bio

    def test_generates_bio_for_republican_senator(self):
        """generate_fallback_bio() produces correct bio for Republican Senator."""
        from app.services.biography_generator import generate_fallback_bio

        politician = {
            "full_name": "Ted Cruz",
            "party": "R",
            "role": "Senator",
            "state_or_country": "Texas",
        }
        stats = {"total_trades": 20, "total_volume": 100000, "top_tickers": []}

        bio = generate_fallback_bio(politician, stats)

        assert "Ted Cruz" in bio
        assert "Republican" in bio
        assert "Senator" in bio
        assert "Texas" in bio
        assert "20 trades" in bio

    def test_generates_bio_for_independent(self):
        """generate_fallback_bio() handles Independent party."""
        from app.services.biography_generator import generate_fallback_bio

        politician = {
            "full_name": "Bernie Sanders",
            "party": "I",
            "role": "Senator",
            "state_or_country": "Vermont",
        }
        stats = {"total_trades": 5, "total_volume": 10000, "top_tickers": ["SPY"]}

        bio = generate_fallback_bio(politician, stats)

        assert "Independent" in bio
        assert "Senator" in bio

    def test_handles_missing_party(self):
        """generate_fallback_bio() handles None party."""
        from app.services.biography_generator import generate_fallback_bio

        politician = {
            "full_name": "John Doe",
            "party": None,
            "role": "Representative",
            "state_or_country": None,
        }
        stats = {"total_trades": 0, "total_volume": 0, "top_tickers": []}

        bio = generate_fallback_bio(politician, stats)

        assert "John Doe" in bio
        assert "0 trades" in bio

    def test_handles_mep_role(self):
        """generate_fallback_bio() recognizes MEP role."""
        from app.services.biography_generator import generate_fallback_bio

        politician = {
            "full_name": "EU Official",
            "party": None,
            "role": "MEP",
            "state_or_country": "France",
        }
        stats = {"total_trades": 3, "total_volume": 50000, "top_tickers": []}

        bio = generate_fallback_bio(politician, stats)

        assert "European Parliament" in bio

    def test_singular_trade_count(self):
        """generate_fallback_bio() uses singular 'trade' for count of 1."""
        from app.services.biography_generator import generate_fallback_bio

        politician = {
            "full_name": "Jane Doe",
            "party": "D",
            "role": "Representative",
            "state_or_country": "NY",
        }
        stats = {"total_trades": 1, "total_volume": 5000, "top_tickers": []}

        bio = generate_fallback_bio(politician, stats)

        assert "1 trade " in bio  # singular, not "1 trades"

    def test_limits_top_tickers_to_three(self):
        """generate_fallback_bio() only includes top 3 tickers."""
        from app.services.biography_generator import generate_fallback_bio

        politician = {
            "full_name": "Jane Doe",
            "party": "R",
            "role": "Senator",
        }
        stats = {
            "total_trades": 50,
            "total_volume": 100000,
            "top_tickers": ["AAPL", "MSFT", "GOOG", "TSLA", "AMZN"],
        }

        bio = generate_fallback_bio(politician, stats)

        assert "AAPL" in bio
        assert "MSFT" in bio
        assert "GOOG" in bio
        assert "TSLA" not in bio
        assert "AMZN" not in bio

    def test_uses_state_fallback(self):
        """generate_fallback_bio() uses 'state' when 'state_or_country' is missing."""
        from app.services.biography_generator import generate_fallback_bio

        politician = {
            "full_name": "Jane Doe",
            "party": "D",
            "role": "Representative",
            "state": "CA",
        }
        stats = {"total_trades": 10, "total_volume": 50000, "top_tickers": []}

        bio = generate_fallback_bio(politician, stats)

        assert "CA" in bio


# =============================================================================
# build_ollama_prompt() Tests
# =============================================================================

class TestBuildOllamaPrompt:
    """Tests for build_ollama_prompt() function."""

    def test_includes_politician_data(self):
        """build_ollama_prompt() includes all politician fields."""
        from app.services.biography_generator import build_ollama_prompt

        politician = {
            "full_name": "Nancy Pelosi",
            "party": "D",
            "role": "Representative",
            "state_or_country": "California",
        }
        stats = {
            "total_trades": 150,
            "total_volume": 5000000,
            "top_tickers": ["AAPL", "MSFT"],
        }

        prompt = build_ollama_prompt(politician, stats)

        assert "Nancy Pelosi" in prompt
        assert "D" in prompt
        assert "Representative" in prompt
        assert "California" in prompt
        assert "150" in prompt
        assert "5,000,000" in prompt
        assert "AAPL" in prompt

    def test_handles_no_tickers(self):
        """build_ollama_prompt() shows N/A when no tickers."""
        from app.services.biography_generator import build_ollama_prompt

        politician = {"full_name": "John Doe"}
        stats = {"total_trades": 0, "total_volume": 0, "top_tickers": []}

        prompt = build_ollama_prompt(politician, stats)

        assert "N/A" in prompt

    def test_includes_instructions(self):
        """build_ollama_prompt() includes writing instructions."""
        from app.services.biography_generator import build_ollama_prompt

        politician = {"full_name": "Test"}
        stats = {"total_trades": 0, "total_volume": 0, "top_tickers": []}

        prompt = build_ollama_prompt(politician, stats)

        assert "biography" in prompt.lower()
        assert "ONLY" in prompt


# =============================================================================
# clean_llm_response() Tests
# =============================================================================

class TestCleanLlmResponse:
    """Tests for clean_llm_response() function."""

    def test_strips_heres_preamble(self):
        """clean_llm_response() strips 'Here's a brief biography:' preamble."""
        from app.services.biography_generator import clean_llm_response

        text = "Here's a brief biography: Nancy Pelosi is a Democratic leader."
        result = clean_llm_response(text)

        assert result == "Nancy Pelosi is a Democratic leader."

    def test_strips_sure_preamble(self):
        """clean_llm_response() strips 'Sure, here is...' preamble."""
        from app.services.biography_generator import clean_llm_response

        text = "Sure, here's the bio: John Smith is a senator."
        result = clean_llm_response(text)

        assert result == "John Smith is a senator."

    def test_strips_based_on_preamble(self):
        """clean_llm_response() strips 'Based on the information:' preamble."""
        from app.services.biography_generator import clean_llm_response

        text = "Based on the provided information: Jane Doe serves in Congress."
        result = clean_llm_response(text)

        assert result == "Jane Doe serves in Congress."

    def test_removes_surrounding_quotes(self):
        """clean_llm_response() removes surrounding double quotes."""
        from app.services.biography_generator import clean_llm_response

        text = '"Nancy Pelosi is a Democratic leader."'
        result = clean_llm_response(text)

        assert result == "Nancy Pelosi is a Democratic leader."

    def test_preserves_clean_text(self):
        """clean_llm_response() preserves already-clean text."""
        from app.services.biography_generator import clean_llm_response

        text = "Nancy Pelosi is a Democratic leader."
        result = clean_llm_response(text)

        assert result == text

    def test_handles_empty_string(self):
        """clean_llm_response() handles empty string."""
        from app.services.biography_generator import clean_llm_response

        assert clean_llm_response("") == ""

    def test_handles_none(self):
        """clean_llm_response() handles None input."""
        from app.services.biography_generator import clean_llm_response

        assert clean_llm_response(None) is None


# =============================================================================
# query_ollama_for_bio() Tests
# =============================================================================

class TestQueryOllamaForBio:
    """Tests for query_ollama_for_bio() function."""

    @pytest.mark.asyncio
    async def test_returns_bio_on_success(self):
        """query_ollama_for_bio() returns cleaned bio text on success."""
        from app.services.biography_generator import query_ollama_for_bio
        from app.services.llm.client import LLMResponse

        mock_client = AsyncMock()
        mock_client.generate.return_value = LLMResponse(
            text="Nancy Pelosi is a Democratic leader.",
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            latency_ms=200,
            provider="test",
        )

        politician = {"full_name": "Nancy Pelosi", "party": "D"}
        stats = {"total_trades": 100, "total_volume": 1000000, "top_tickers": ["AAPL"]}

        result = await query_ollama_for_bio(mock_client, politician, stats)

        assert result == "Nancy Pelosi is a Democratic leader."

    @pytest.mark.asyncio
    async def test_returns_none_on_all_providers_exhausted(self):
        """query_ollama_for_bio() returns None when all providers fail."""
        from app.services.biography_generator import query_ollama_for_bio
        from app.services.llm.providers import AllProvidersExhaustedError

        mock_client = AsyncMock()
        mock_client.generate.side_effect = AllProvidersExhaustedError(
            {"test": "Connection failed"}
        )

        politician = {"full_name": "Test"}
        stats = {"total_trades": 0, "total_volume": 0, "top_tickers": []}

        result = await query_ollama_for_bio(mock_client, politician, stats)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_empty_response(self):
        """query_ollama_for_bio() returns None when LLM returns empty content."""
        from app.services.biography_generator import query_ollama_for_bio
        from app.services.llm.client import LLMResponse

        mock_client = AsyncMock()
        mock_client.generate.return_value = LLMResponse(
            text="",
            model="test-model",
            input_tokens=100,
            output_tokens=0,
            latency_ms=200,
            provider="test",
        )

        politician = {"full_name": "Test"}
        stats = {"total_trades": 0, "total_volume": 0, "top_tickers": []}

        result = await query_ollama_for_bio(mock_client, politician, stats)

        assert result is None

    @pytest.mark.asyncio
    async def test_cleans_preamble_from_response(self):
        """query_ollama_for_bio() cleans preamble from LLM response."""
        from app.services.biography_generator import query_ollama_for_bio
        from app.services.llm.client import LLMResponse

        mock_client = AsyncMock()
        mock_client.generate.return_value = LLMResponse(
            text="Here's a brief biography: Ted Cruz is a Republican Senator.",
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            latency_ms=200,
            provider="test",
        )

        politician = {"full_name": "Ted Cruz", "party": "R"}
        stats = {"total_trades": 10, "total_volume": 50000, "top_tickers": []}

        result = await query_ollama_for_bio(mock_client, politician, stats)

        assert result == "Ted Cruz is a Republican Senator."

    @pytest.mark.asyncio
    async def test_returns_none_on_unexpected_error(self):
        """query_ollama_for_bio() returns None on unexpected exceptions."""
        from app.services.biography_generator import query_ollama_for_bio

        mock_client = AsyncMock()
        mock_client.generate.side_effect = ValueError("Unexpected")

        politician = {"full_name": "Test"}
        stats = {"total_trades": 0, "total_volume": 0, "top_tickers": []}

        result = await query_ollama_for_bio(mock_client, politician, stats)

        assert result is None


# =============================================================================
# BiographyJob Tests
# =============================================================================

class TestBiographyJob:
    """Tests for BiographyJob class."""

    def test_initial_state(self):
        """BiographyJob starts with correct initial state."""
        from app.services.biography_generator import BiographyJob

        job = BiographyJob("test-123", limit=50, force=False)

        assert job.job_id == "test-123"
        assert job.limit == 50
        assert job.force is False
        assert job.status == "pending"
        assert job.progress == 0
        assert job.total == 0
        assert job.updated == 0
        assert job.skipped == 0
        assert job.errors == 0

    def test_to_dict_returns_all_fields(self):
        """BiographyJob.to_dict() returns all expected fields."""
        from app.services.biography_generator import BiographyJob

        job = BiographyJob("test-456")
        result = job.to_dict()

        assert "job_id" in result
        assert "status" in result
        assert "progress" in result
        assert "total" in result
        assert "updated" in result
        assert "skipped" in result
        assert "errors" in result
        assert "message" in result
        assert "started_at" in result
        assert "completed_at" in result

    def test_force_flag(self):
        """BiographyJob respects force flag."""
        from app.services.biography_generator import BiographyJob

        job = BiographyJob("test-789", force=True)

        assert job.force is True


# =============================================================================
# Job Registry Tests
# =============================================================================

class TestJobRegistry:
    """Tests for job creation and retrieval functions."""

    def test_create_bio_job_returns_job(self):
        """create_bio_job() returns a BiographyJob with unique ID."""
        from app.services.biography_generator import create_bio_job

        job = create_bio_job(limit=25, force=True)

        assert job.job_id is not None
        assert len(job.job_id) == 8
        assert job.limit == 25
        assert job.force is True

    def test_get_bio_job_returns_created_job(self):
        """get_bio_job() returns the job created by create_bio_job()."""
        from app.services.biography_generator import create_bio_job, get_bio_job

        job = create_bio_job(limit=10)
        retrieved = get_bio_job(job.job_id)

        assert retrieved is not None
        assert retrieved.job_id == job.job_id

    def test_get_bio_job_returns_none_for_unknown(self):
        """get_bio_job() returns None for non-existent job ID."""
        from app.services.biography_generator import get_bio_job

        result = get_bio_job("nonexistent-id")

        assert result is None
