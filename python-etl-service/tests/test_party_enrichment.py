"""
Tests for Party Enrichment Service (app/services/party_enrichment.py).

Tests:
- query_ollama_for_party() - Query Ollama for party affiliation
- PartyEnrichmentJob - Background job class
- get_job(), create_job() - Job registry functions
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime


# =============================================================================
# query_ollama_for_party() Tests
# =============================================================================

class TestQueryOllamaForParty:
    """Tests for query_ollama_for_party() function."""

    @pytest.mark.asyncio
    async def test_returns_d_for_democrat(self):
        """query_ollama_for_party() returns 'D' for Democrat response."""
        from app.services.party_enrichment import query_ollama_for_party

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "D"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        result = await query_ollama_for_party(mock_client, "Nancy Pelosi", "CA", "House")

        assert result == "D"

    @pytest.mark.asyncio
    async def test_returns_r_for_republican(self):
        """query_ollama_for_party() returns 'R' for Republican response."""
        from app.services.party_enrichment import query_ollama_for_party

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "R"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        result = await query_ollama_for_party(mock_client, "Kevin McCarthy", "CA", "House")

        assert result == "R"

    @pytest.mark.asyncio
    async def test_returns_i_for_independent(self):
        """query_ollama_for_party() returns 'I' for Independent response."""
        from app.services.party_enrichment import query_ollama_for_party

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "I"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        result = await query_ollama_for_party(mock_client, "Bernie Sanders", "VT", "Senate")

        assert result == "I"

    @pytest.mark.asyncio
    async def test_parses_democrat_word(self):
        """query_ollama_for_party() parses 'DEMOCRAT' in response."""
        from app.services.party_enrichment import query_ollama_for_party

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Democrat"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        result = await query_ollama_for_party(mock_client, "Test Name")

        assert result == "D"

    @pytest.mark.asyncio
    async def test_parses_republican_word(self):
        """query_ollama_for_party() parses 'REPUBLICAN' in response."""
        from app.services.party_enrichment import query_ollama_for_party

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Republican"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        result = await query_ollama_for_party(mock_client, "Test Name")

        assert result == "R"

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown(self):
        """query_ollama_for_party() returns None for UNKNOWN response."""
        from app.services.party_enrichment import query_ollama_for_party

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "UNKNOWN"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        result = await query_ollama_for_party(mock_client, "Unknown Person")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self):
        """query_ollama_for_party() returns None on HTTP error."""
        from app.services.party_enrichment import query_ollama_for_party
        import httpx

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.HTTPError("Connection error")

        result = await query_ollama_for_party(mock_client, "Test Name")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self):
        """query_ollama_for_party() returns None on general exception."""
        from app.services.party_enrichment import query_ollama_for_party

        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Unexpected error")

        result = await query_ollama_for_party(mock_client, "Test Name")

        assert result is None

    @pytest.mark.asyncio
    async def test_includes_state_in_context(self):
        """query_ollama_for_party() includes state in query context."""
        from app.services.party_enrichment import query_ollama_for_party

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "D"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        await query_ollama_for_party(mock_client, "Test Name", state="CA")

        call_args = mock_client.post.call_args
        request_json = call_args.kwargs["json"]
        user_message = request_json["messages"][1]["content"]
        assert "from CA" in user_message

    @pytest.mark.asyncio
    async def test_includes_chamber_in_context(self):
        """query_ollama_for_party() includes chamber in query context."""
        from app.services.party_enrichment import query_ollama_for_party

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "D"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        await query_ollama_for_party(mock_client, "Test Name", chamber="House")

        call_args = mock_client.post.call_args
        request_json = call_args.kwargs["json"]
        user_message = request_json["messages"][1]["content"]
        assert "serving in the House" in user_message


# =============================================================================
# PartyEnrichmentJob Tests
# =============================================================================

class TestPartyEnrichmentJob:
    """Tests for PartyEnrichmentJob class."""

    def test_init_sets_job_id(self):
        """PartyEnrichmentJob.__init__() sets job ID."""
        from app.services.party_enrichment import PartyEnrichmentJob

        job = PartyEnrichmentJob("test-job-123")

        assert job.job_id == "test-job-123"

    def test_init_sets_limit(self):
        """PartyEnrichmentJob.__init__() sets limit."""
        from app.services.party_enrichment import PartyEnrichmentJob

        job = PartyEnrichmentJob("test-job", limit=50)

        assert job.limit == 50

    def test_init_sets_pending_status(self):
        """PartyEnrichmentJob.__init__() sets pending status."""
        from app.services.party_enrichment import PartyEnrichmentJob

        job = PartyEnrichmentJob("test-job")

        assert job.status == "pending"

    def test_init_sets_zero_counters(self):
        """PartyEnrichmentJob.__init__() sets zero counters."""
        from app.services.party_enrichment import PartyEnrichmentJob

        job = PartyEnrichmentJob("test-job")

        assert job.progress == 0
        assert job.total == 0
        assert job.updated == 0
        assert job.skipped == 0
        assert job.errors == 0

    def test_to_dict_returns_complete_state(self):
        """PartyEnrichmentJob.to_dict() returns complete state."""
        from app.services.party_enrichment import PartyEnrichmentJob

        job = PartyEnrichmentJob("test-job", limit=100)
        job.status = "running"
        job.progress = 10
        job.total = 50
        job.updated = 5
        job.skipped = 3
        job.errors = 2
        job.message = "Processing..."
        job.started_at = datetime(2024, 1, 1, 12, 0, 0)

        result = job.to_dict()

        assert result["job_id"] == "test-job"
        assert result["status"] == "running"
        assert result["progress"] == 10
        assert result["total"] == 50
        assert result["updated"] == 5
        assert result["skipped"] == 3
        assert result["errors"] == 2
        assert result["message"] == "Processing..."
        assert result["started_at"] == "2024-01-01T12:00:00"

    def test_to_dict_handles_none_dates(self):
        """PartyEnrichmentJob.to_dict() handles None dates."""
        from app.services.party_enrichment import PartyEnrichmentJob

        job = PartyEnrichmentJob("test-job")

        result = job.to_dict()

        assert result["started_at"] is None
        assert result["completed_at"] is None

    @pytest.mark.asyncio
    async def test_run_sets_running_status(self):
        """PartyEnrichmentJob.run() sets running status."""
        from app.services.party_enrichment import PartyEnrichmentJob

        with patch("app.services.party_enrichment.get_supabase") as mock_supabase:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = []  # No politicians to process
            mock_client.table.return_value.select.return_value.is_.return_value.range.return_value.execute.return_value = mock_response
            mock_supabase.return_value = mock_client

            job = PartyEnrichmentJob("test-job")
            await job.run()

            # Status should be completed (no politicians to process)
            assert job.status == "completed"
            assert job.started_at is not None

    @pytest.mark.asyncio
    async def test_run_completes_with_no_politicians(self):
        """PartyEnrichmentJob.run() completes when no politicians need enrichment."""
        from app.services.party_enrichment import PartyEnrichmentJob

        with patch("app.services.party_enrichment.get_supabase") as mock_supabase:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = []
            mock_client.table.return_value.select.return_value.is_.return_value.range.return_value.execute.return_value = mock_response
            mock_supabase.return_value = mock_client

            job = PartyEnrichmentJob("test-job")
            await job.run()

            assert job.status == "completed"
            assert job.message == "No politicians need party enrichment"
            assert job.completed_at is not None

    @pytest.mark.asyncio
    async def test_run_handles_exception(self):
        """PartyEnrichmentJob.run() handles exceptions gracefully."""
        from app.services.party_enrichment import PartyEnrichmentJob

        with patch("app.services.party_enrichment.get_supabase") as mock_supabase:
            mock_supabase.side_effect = Exception("Database error")

            job = PartyEnrichmentJob("test-job")
            await job.run()

            assert job.status == "failed"
            assert "Job failed" in job.message
            assert job.completed_at is not None


# =============================================================================
# Job Registry Tests
# =============================================================================

class TestJobRegistry:
    """Tests for job registry functions."""

    def test_create_job_returns_job(self):
        """create_job() returns a PartyEnrichmentJob."""
        from app.services.party_enrichment import create_job, PartyEnrichmentJob

        job = create_job()

        assert isinstance(job, PartyEnrichmentJob)

    def test_create_job_generates_unique_id(self):
        """create_job() generates unique job IDs."""
        from app.services.party_enrichment import create_job

        job1 = create_job()
        job2 = create_job()

        assert job1.job_id != job2.job_id

    def test_create_job_sets_limit(self):
        """create_job() sets limit on job."""
        from app.services.party_enrichment import create_job

        job = create_job(limit=100)

        assert job.limit == 100

    def test_get_job_returns_created_job(self):
        """get_job() returns previously created job."""
        from app.services.party_enrichment import create_job, get_job

        job = create_job()

        retrieved = get_job(job.job_id)

        assert retrieved is job

    def test_get_job_returns_none_for_unknown(self):
        """get_job() returns None for unknown job ID."""
        from app.services.party_enrichment import get_job

        result = get_job("nonexistent-job-id")

        assert result is None


# =============================================================================
# run_job_in_background() Tests
# =============================================================================

class TestRunJobInBackground:
    """Tests for run_job_in_background() function."""

    @pytest.mark.asyncio
    async def test_runs_job(self):
        """run_job_in_background() runs the job."""
        from app.services.party_enrichment import run_job_in_background, PartyEnrichmentJob

        with patch("app.services.party_enrichment.get_supabase") as mock_supabase:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = []
            mock_client.table.return_value.select.return_value.is_.return_value.range.return_value.execute.return_value = mock_response
            mock_supabase.return_value = mock_client

            job = PartyEnrichmentJob("test-job")
            await run_job_in_background(job)

            assert job.status == "completed"
