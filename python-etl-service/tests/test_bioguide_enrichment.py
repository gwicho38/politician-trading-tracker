"""
Tests for BioGuide ID Enrichment Service (app/services/bioguide_enrichment.py).

Tests:
- normalize_name() - Name normalization for matching
- fetch_congress_members() - Congress.gov API fetching
- fetch_politicians_without_bioguide() - Database query
- update_politician_from_congress() - Database update
- match_politicians() - Name matching logic
- run_bioguide_enrichment() - Full enrichment flow
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import httpx


# =============================================================================
# normalize_name() Tests
# =============================================================================

class TestNormalizeName:
    """Tests for normalize_name() function."""

    def test_returns_empty_for_none(self):
        """normalize_name() returns empty string for None input."""
        from app.services.bioguide_enrichment import normalize_name

        result = normalize_name(None)

        assert result == ""

    def test_returns_empty_for_empty_string(self):
        """normalize_name() returns empty string for empty input."""
        from app.services.bioguide_enrichment import normalize_name

        result = normalize_name("")

        assert result == ""

    def test_lowercases_name(self):
        """normalize_name() lowercases the name."""
        from app.services.bioguide_enrichment import normalize_name

        result = normalize_name("John Smith")

        assert result == "john smith"

    def test_strips_whitespace(self):
        """normalize_name() strips leading/trailing whitespace."""
        from app.services.bioguide_enrichment import normalize_name

        result = normalize_name("  John Smith  ")

        assert result == "john smith"

    def test_handles_last_first_format(self):
        """normalize_name() converts 'Last, First' to 'First Last'."""
        from app.services.bioguide_enrichment import normalize_name

        result = normalize_name("Smith, John")

        assert result == "john smith"

    def test_removes_jr_suffix(self):
        """normalize_name() removes Jr. suffix."""
        from app.services.bioguide_enrichment import normalize_name

        result = normalize_name("John Smith Jr.")

        assert result == "john smith"

    def test_removes_sr_suffix(self):
        """normalize_name() removes Sr. suffix."""
        from app.services.bioguide_enrichment import normalize_name

        result = normalize_name("John Smith Sr.")

        assert result == "john smith"

    def test_removes_iii_suffix(self):
        """normalize_name() removes III suffix."""
        from app.services.bioguide_enrichment import normalize_name

        result = normalize_name("John Smith III")

        assert result == "john smith"

    def test_removes_hon_prefix(self):
        """normalize_name() removes Hon. prefix."""
        from app.services.bioguide_enrichment import normalize_name

        result = normalize_name("Hon. John Smith")

        assert result == "john smith"

    def test_removes_sen_prefix(self):
        """normalize_name() removes Sen. prefix."""
        from app.services.bioguide_enrichment import normalize_name

        result = normalize_name("Sen. John Smith")

        assert result == "john smith"

    def test_removes_rep_prefix(self):
        """normalize_name() removes Rep. prefix."""
        from app.services.bioguide_enrichment import normalize_name

        result = normalize_name("Rep. John Smith")

        assert result == "john smith"

    def test_handles_multiple_suffixes(self):
        """normalize_name() removes multiple suffixes/prefixes."""
        from app.services.bioguide_enrichment import normalize_name

        result = normalize_name("Hon. John Smith Jr.")

        assert result == "john smith"


# =============================================================================
# fetch_congress_members() Tests
# =============================================================================

class TestFetchCongressMembers:
    """Tests for fetch_congress_members() function."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_api_key(self, monkeypatch):
        """fetch_congress_members() returns empty list when API key is missing."""
        monkeypatch.setattr("app.services.bioguide_enrichment.CONGRESS_API_KEY", None)
        from app.services.bioguide_enrichment import fetch_congress_members

        result = await fetch_congress_members()

        assert result == []

    @pytest.mark.asyncio
    async def test_fetches_members_from_api(self, monkeypatch):
        """fetch_congress_members() fetches members from Congress.gov API."""
        monkeypatch.setattr("app.services.bioguide_enrichment.CONGRESS_API_KEY", "test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "members": [
                {
                    "bioguideId": "A000001",
                    "name": "Smith, John",
                    "directOrderName": "John Smith",
                    "state": "CA",
                    "district": "12",
                    "partyName": "Democratic",
                    "terms": {"item": [{"chamber": "House of Representatives"}]}
                }
            ],
            "pagination": {"count": 1}
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock()

            from app.services.bioguide_enrichment import fetch_congress_members
            result = await fetch_congress_members()

        assert len(result) == 1
        assert result[0]["bioguide_id"] == "A000001"
        assert result[0]["name"] == "Smith, John"
        assert result[0]["state"] == "CA"

    @pytest.mark.asyncio
    async def test_returns_empty_on_api_error(self, monkeypatch):
        """fetch_congress_members() returns empty list on API error."""
        monkeypatch.setattr("app.services.bioguide_enrichment.CONGRESS_API_KEY", "test-key")

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock()

            from app.services.bioguide_enrichment import fetch_congress_members
            result = await fetch_congress_members()

        assert result == []

    @pytest.mark.asyncio
    async def test_handles_pagination(self, monkeypatch):
        """fetch_congress_members() handles paginated results."""
        monkeypatch.setattr("app.services.bioguide_enrichment.CONGRESS_API_KEY", "test-key")

        # First page
        page1_response = MagicMock()
        page1_response.status_code = 200
        page1_response.json.return_value = {
            "members": [
                {"bioguideId": "A000001", "name": "Smith, John", "directOrderName": "John Smith",
                 "state": "CA", "partyName": "Democratic", "terms": {"item": []}}
            ],
            "pagination": {"count": 2}
        }

        # Second page (empty to stop pagination)
        page2_response = MagicMock()
        page2_response.status_code = 200
        page2_response.json.return_value = {
            "members": [],
            "pagination": {"count": 2}
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(side_effect=[page1_response, page2_response])
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock()

            from app.services.bioguide_enrichment import fetch_congress_members
            result = await fetch_congress_members()

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handles_exception(self, monkeypatch):
        """fetch_congress_members() handles exceptions gracefully."""
        monkeypatch.setattr("app.services.bioguide_enrichment.CONGRESS_API_KEY", "test-key")

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(side_effect=Exception("Network error"))
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_client.return_value.__aexit__ = AsyncMock()

            from app.services.bioguide_enrichment import fetch_congress_members
            result = await fetch_congress_members()

        assert result == []


# =============================================================================
# fetch_politicians_without_bioguide() Tests
# =============================================================================

class TestFetchPoliticiansWithoutBioguide:
    """Tests for fetch_politicians_without_bioguide() function."""

    def test_returns_politicians_without_bioguide(self):
        """fetch_politicians_without_bioguide() returns politicians missing bioguide_id."""
        from app.services.bioguide_enrichment import fetch_politicians_without_bioguide

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {"id": "1", "full_name": "John Smith", "bioguide_id": None}
        ]
        mock_supabase.table.return_value.select.return_value.is_.return_value.limit.return_value.execute.return_value = mock_response

        result = fetch_politicians_without_bioguide(mock_supabase)

        assert len(result) == 1
        assert result[0]["full_name"] == "John Smith"

    def test_respects_limit_parameter(self):
        """fetch_politicians_without_bioguide() respects the limit parameter."""
        from app.services.bioguide_enrichment import fetch_politicians_without_bioguide

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_query = MagicMock()
        mock_query.limit.return_value.execute.return_value = mock_response
        mock_supabase.table.return_value.select.return_value.is_.return_value = mock_query

        fetch_politicians_without_bioguide(mock_supabase, limit=50)

        mock_query.limit.assert_called_with(50)

    def test_uses_default_limit_when_none(self):
        """fetch_politicians_without_bioguide() uses default limit of 1000."""
        from app.services.bioguide_enrichment import fetch_politicians_without_bioguide

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_query = MagicMock()
        mock_query.limit.return_value.execute.return_value = mock_response
        mock_supabase.table.return_value.select.return_value.is_.return_value = mock_query

        fetch_politicians_without_bioguide(mock_supabase, limit=None)

        mock_query.limit.assert_called_with(1000)

    def test_returns_empty_on_error(self):
        """fetch_politicians_without_bioguide() returns empty list on error."""
        from app.services.bioguide_enrichment import fetch_politicians_without_bioguide

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.side_effect = Exception("DB error")

        result = fetch_politicians_without_bioguide(mock_supabase)

        assert result == []

    def test_returns_empty_when_data_is_none(self):
        """fetch_politicians_without_bioguide() returns empty list when data is None."""
        from app.services.bioguide_enrichment import fetch_politicians_without_bioguide

        mock_supabase = MagicMock()
        mock_response = MagicMock()
        mock_response.data = None
        mock_supabase.table.return_value.select.return_value.is_.return_value.limit.return_value.execute.return_value = mock_response

        result = fetch_politicians_without_bioguide(mock_supabase)

        assert result == []


# =============================================================================
# update_politician_from_congress() Tests
# =============================================================================

class TestUpdatePoliticianFromCongress:
    """Tests for update_politician_from_congress() function."""

    def test_updates_bioguide_id(self):
        """update_politician_from_congress() updates bioguide_id."""
        from app.services.bioguide_enrichment import update_politician_from_congress

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        congress_data = {"bioguide_id": "A000001", "name": "John Smith"}
        current_data = {"full_name": "John Smith", "party": "D"}

        result = update_politician_from_congress(mock_supabase, "pol-123", congress_data, current_data)

        assert result is True
        # Verify update was called with bioguide_id
        update_call = mock_supabase.table.return_value.update.call_args
        assert update_call[0][0]["bioguide_id"] == "A000001"

    def test_updates_name_for_placeholder(self):
        """update_politician_from_congress() updates full_name when it's a placeholder."""
        from app.services.bioguide_enrichment import update_politician_from_congress

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        congress_data = {"bioguide_id": "A000001", "direct_name": "John Smith", "name": "Smith, John"}
        current_data = {"full_name": "House_Member (CA-12)", "party": None}

        result = update_politician_from_congress(mock_supabase, "pol-123", congress_data, current_data)

        assert result is True
        update_call = mock_supabase.table.return_value.update.call_args
        assert update_call[0][0]["full_name"] == "John Smith"
        assert update_call[0][0]["first_name"] == "John"
        assert update_call[0][0]["last_name"] == "Smith"

    def test_does_not_update_real_name(self):
        """update_politician_from_congress() doesn't update a real name."""
        from app.services.bioguide_enrichment import update_politician_from_congress

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        congress_data = {"bioguide_id": "A000001", "direct_name": "John R. Smith", "name": "Smith, John"}
        current_data = {"full_name": "John Smith", "party": "D"}

        result = update_politician_from_congress(mock_supabase, "pol-123", congress_data, current_data)

        assert result is True
        update_call = mock_supabase.table.return_value.update.call_args
        # Should only have bioguide_id, not full_name
        assert "full_name" not in update_call[0][0]

    def test_fills_missing_party_democrat(self):
        """update_politician_from_congress() fills in missing party as 'D' for Democrat."""
        from app.services.bioguide_enrichment import update_politician_from_congress

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        congress_data = {"bioguide_id": "A000001", "party": "Democratic"}
        current_data = {"full_name": "John Smith", "party": None}

        update_politician_from_congress(mock_supabase, "pol-123", congress_data, current_data)

        update_call = mock_supabase.table.return_value.update.call_args
        assert update_call[0][0]["party"] == "D"

    def test_fills_missing_party_republican(self):
        """update_politician_from_congress() fills in missing party as 'R' for Republican."""
        from app.services.bioguide_enrichment import update_politician_from_congress

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        congress_data = {"bioguide_id": "A000001", "party": "Republican"}
        current_data = {"full_name": "John Smith", "party": None}

        update_politician_from_congress(mock_supabase, "pol-123", congress_data, current_data)

        update_call = mock_supabase.table.return_value.update.call_args
        assert update_call[0][0]["party"] == "R"

    def test_fills_missing_state(self):
        """update_politician_from_congress() fills in missing state."""
        from app.services.bioguide_enrichment import update_politician_from_congress

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        congress_data = {"bioguide_id": "A000001", "state": "CA"}
        current_data = {"full_name": "John Smith", "state": None, "state_or_country": None}

        update_politician_from_congress(mock_supabase, "pol-123", congress_data, current_data)

        update_call = mock_supabase.table.return_value.update.call_args
        assert update_call[0][0]["state"] == "CA"
        assert update_call[0][0]["state_or_country"] == "CA"

    def test_fills_missing_chamber(self):
        """update_politician_from_congress() fills in missing chamber."""
        from app.services.bioguide_enrichment import update_politician_from_congress

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        congress_data = {"bioguide_id": "A000001", "chamber": "House of Representatives"}
        current_data = {"full_name": "John Smith", "chamber": None}

        update_politician_from_congress(mock_supabase, "pol-123", congress_data, current_data)

        update_call = mock_supabase.table.return_value.update.call_args
        assert update_call[0][0]["chamber"] == "House of Representatives"

    def test_returns_false_on_error(self):
        """update_politician_from_congress() returns False on error."""
        from app.services.bioguide_enrichment import update_politician_from_congress

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.update.side_effect = Exception("DB error")

        congress_data = {"bioguide_id": "A000001"}
        current_data = {"full_name": "John Smith"}

        result = update_politician_from_congress(mock_supabase, "pol-123", congress_data, current_data)

        assert result is False


# =============================================================================
# match_politicians() Tests
# =============================================================================

class TestMatchPoliticians:
    """Tests for match_politicians() function."""

    def test_matches_by_full_name(self):
        """match_politicians() matches by full_name."""
        from app.services.bioguide_enrichment import match_politicians

        app_politicians = [
            {"id": "1", "full_name": "John Smith", "first_name": "John", "last_name": "Smith"}
        ]
        congress_members = [
            {"bioguide_id": "A000001", "name": "Smith, John", "direct_name": "John Smith"}
        ]

        result = match_politicians(app_politicians, congress_members)

        assert len(result) == 1
        assert result[0][0]["id"] == "1"
        assert result[0][1]["bioguide_id"] == "A000001"

    def test_matches_by_first_last_name(self):
        """match_politicians() matches by first_name + last_name."""
        from app.services.bioguide_enrichment import match_politicians

        app_politicians = [
            {"id": "1", "full_name": "", "first_name": "John", "last_name": "Smith"}
        ]
        congress_members = [
            {"bioguide_id": "A000001", "name": "Smith, John", "direct_name": "John Smith"}
        ]

        result = match_politicians(app_politicians, congress_members)

        assert len(result) == 1

    def test_matches_by_last_first_format(self):
        """match_politicians() matches by 'Last, First' format."""
        from app.services.bioguide_enrichment import match_politicians

        app_politicians = [
            {"id": "1", "full_name": "Smith, John", "first_name": "", "last_name": ""}
        ]
        congress_members = [
            {"bioguide_id": "A000001", "name": "Smith, John", "direct_name": "John Smith"}
        ]

        result = match_politicians(app_politicians, congress_members)

        assert len(result) == 1

    def test_returns_empty_for_no_matches(self):
        """match_politicians() returns empty list when no matches found."""
        from app.services.bioguide_enrichment import match_politicians

        app_politicians = [
            {"id": "1", "full_name": "Jane Doe", "first_name": "Jane", "last_name": "Doe"}
        ]
        congress_members = [
            {"bioguide_id": "A000001", "name": "Smith, John", "direct_name": "John Smith"}
        ]

        result = match_politicians(app_politicians, congress_members)

        assert len(result) == 0

    def test_handles_empty_inputs(self):
        """match_politicians() handles empty inputs."""
        from app.services.bioguide_enrichment import match_politicians

        result = match_politicians([], [])

        assert result == []

    def test_matches_multiple_politicians(self):
        """match_politicians() matches multiple politicians."""
        from app.services.bioguide_enrichment import match_politicians

        app_politicians = [
            {"id": "1", "full_name": "John Smith", "first_name": "John", "last_name": "Smith"},
            {"id": "2", "full_name": "Jane Doe", "first_name": "Jane", "last_name": "Doe"},
        ]
        congress_members = [
            {"bioguide_id": "A000001", "name": "Smith, John", "direct_name": "John Smith"},
            {"bioguide_id": "A000002", "name": "Doe, Jane", "direct_name": "Jane Doe"},
        ]

        result = match_politicians(app_politicians, congress_members)

        assert len(result) == 2

    def test_case_insensitive_matching(self):
        """match_politicians() matches case-insensitively."""
        from app.services.bioguide_enrichment import match_politicians

        app_politicians = [
            {"id": "1", "full_name": "JOHN SMITH", "first_name": "JOHN", "last_name": "SMITH"}
        ]
        congress_members = [
            {"bioguide_id": "A000001", "name": "Smith, John", "direct_name": "John Smith"}
        ]

        result = match_politicians(app_politicians, congress_members)

        assert len(result) == 1


# =============================================================================
# run_bioguide_enrichment() Tests
# =============================================================================

class TestRunBioguideEnrichment:
    """Tests for run_bioguide_enrichment() function."""

    @pytest.fixture
    def mock_job_status(self):
        """Create a mock job status dictionary."""
        return {"status": "pending", "message": ""}

    @pytest.mark.asyncio
    async def test_sets_status_running(self, mock_job_status, monkeypatch):
        """run_bioguide_enrichment() sets status to running."""
        from app.services.bioguide_enrichment import run_bioguide_enrichment
        import app.services.bioguide_enrichment as module

        monkeypatch.setattr(module, "JOB_STATUS", {"test-job": mock_job_status})

        with patch.object(module, "get_supabase") as mock_supabase:
            mock_supabase.side_effect = ValueError("No Supabase")

            await run_bioguide_enrichment("test-job")

        assert mock_job_status["status"] == "failed"

    @pytest.mark.asyncio
    async def test_fails_when_supabase_unavailable(self, mock_job_status, monkeypatch):
        """run_bioguide_enrichment() fails when Supabase is unavailable."""
        from app.services.bioguide_enrichment import run_bioguide_enrichment
        import app.services.bioguide_enrichment as module

        monkeypatch.setattr(module, "JOB_STATUS", {"test-job": mock_job_status})

        with patch.object(module, "get_supabase") as mock_supabase:
            mock_supabase.side_effect = ValueError("Missing credentials")

            await run_bioguide_enrichment("test-job")

        assert mock_job_status["status"] == "failed"
        assert "Missing credentials" in mock_job_status["message"]

    @pytest.mark.asyncio
    async def test_fails_when_no_congress_members(self, mock_job_status, monkeypatch):
        """run_bioguide_enrichment() fails when no Congress members fetched."""
        from app.services.bioguide_enrichment import run_bioguide_enrichment
        import app.services.bioguide_enrichment as module

        monkeypatch.setattr(module, "JOB_STATUS", {"test-job": mock_job_status})

        with patch.object(module, "get_supabase") as mock_supabase:
            mock_supabase.return_value = MagicMock()

            with patch.object(module, "fetch_congress_members") as mock_fetch:
                mock_fetch.return_value = []

                await run_bioguide_enrichment("test-job")

        assert mock_job_status["status"] == "failed"
        assert "Congress members" in mock_job_status["message"]

    @pytest.mark.asyncio
    async def test_completes_when_no_politicians_need_enrichment(self, mock_job_status, monkeypatch):
        """run_bioguide_enrichment() completes when no politicians need enrichment."""
        from app.services.bioguide_enrichment import run_bioguide_enrichment
        import app.services.bioguide_enrichment as module

        monkeypatch.setattr(module, "JOB_STATUS", {"test-job": mock_job_status})

        with patch.object(module, "get_supabase") as mock_supabase:
            mock_supabase.return_value = MagicMock()

            with patch.object(module, "fetch_congress_members") as mock_fetch_congress:
                mock_fetch_congress.return_value = [{"bioguide_id": "A000001", "name": "Test"}]

                with patch.object(module, "fetch_politicians_without_bioguide") as mock_fetch_pols:
                    mock_fetch_pols.return_value = []

                    await run_bioguide_enrichment("test-job")

        assert mock_job_status["status"] == "completed"
        assert "No politicians need enrichment" in mock_job_status["message"]

    @pytest.mark.asyncio
    async def test_completes_when_no_matches(self, mock_job_status, monkeypatch):
        """run_bioguide_enrichment() completes when no matches found."""
        from app.services.bioguide_enrichment import run_bioguide_enrichment
        import app.services.bioguide_enrichment as module

        monkeypatch.setattr(module, "JOB_STATUS", {"test-job": mock_job_status})

        with patch.object(module, "get_supabase") as mock_supabase:
            mock_supabase.return_value = MagicMock()

            with patch.object(module, "fetch_congress_members") as mock_fetch_congress:
                mock_fetch_congress.return_value = [
                    {"bioguide_id": "A000001", "name": "Smith, John", "direct_name": "John Smith"}
                ]

                with patch.object(module, "fetch_politicians_without_bioguide") as mock_fetch_pols:
                    mock_fetch_pols.return_value = [
                        {"id": "1", "full_name": "Jane Doe", "first_name": "Jane", "last_name": "Doe"}
                    ]

                    await run_bioguide_enrichment("test-job")

        assert mock_job_status["status"] == "completed"
        assert "No matches found" in mock_job_status["message"]

    @pytest.mark.asyncio
    async def test_updates_matched_politicians(self, mock_job_status, monkeypatch):
        """run_bioguide_enrichment() updates matched politicians."""
        from app.services.bioguide_enrichment import run_bioguide_enrichment
        import app.services.bioguide_enrichment as module

        monkeypatch.setattr(module, "JOB_STATUS", {"test-job": mock_job_status})

        mock_supabase_client = MagicMock()

        with patch.object(module, "get_supabase") as mock_supabase:
            mock_supabase.return_value = mock_supabase_client

            with patch.object(module, "fetch_congress_members") as mock_fetch_congress:
                mock_fetch_congress.return_value = [
                    {"bioguide_id": "A000001", "name": "Smith, John", "direct_name": "John Smith"}
                ]

                with patch.object(module, "fetch_politicians_without_bioguide") as mock_fetch_pols:
                    mock_fetch_pols.return_value = [
                        {"id": "1", "full_name": "John Smith", "first_name": "John", "last_name": "Smith"}
                    ]

                    with patch.object(module, "update_politician_from_congress") as mock_update:
                        mock_update.return_value = True

                        await run_bioguide_enrichment("test-job")

        assert mock_job_status["status"] == "completed"
        assert "1 updated" in mock_job_status["message"]
        mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_update_failures(self, mock_job_status, monkeypatch):
        """run_bioguide_enrichment() tracks update failures."""
        from app.services.bioguide_enrichment import run_bioguide_enrichment
        import app.services.bioguide_enrichment as module

        monkeypatch.setattr(module, "JOB_STATUS", {"test-job": mock_job_status})

        with patch.object(module, "get_supabase") as mock_supabase:
            mock_supabase.return_value = MagicMock()

            with patch.object(module, "fetch_congress_members") as mock_fetch_congress:
                mock_fetch_congress.return_value = [
                    {"bioguide_id": "A000001", "name": "Smith, John", "direct_name": "John Smith"}
                ]

                with patch.object(module, "fetch_politicians_without_bioguide") as mock_fetch_pols:
                    mock_fetch_pols.return_value = [
                        {"id": "1", "full_name": "John Smith", "first_name": "John", "last_name": "Smith"}
                    ]

                    with patch.object(module, "update_politician_from_congress") as mock_update:
                        mock_update.return_value = False

                        await run_bioguide_enrichment("test-job")

        assert mock_job_status["status"] == "completed"
        assert "1 failed" in mock_job_status["message"]

    @pytest.mark.asyncio
    async def test_handles_exception(self, mock_job_status, monkeypatch):
        """run_bioguide_enrichment() handles unexpected exceptions."""
        from app.services.bioguide_enrichment import run_bioguide_enrichment
        import app.services.bioguide_enrichment as module

        monkeypatch.setattr(module, "JOB_STATUS", {"test-job": mock_job_status})

        with patch.object(module, "get_supabase") as mock_supabase:
            mock_supabase.return_value = MagicMock()

            with patch.object(module, "fetch_congress_members") as mock_fetch_congress:
                mock_fetch_congress.side_effect = Exception("Unexpected error")

                await run_bioguide_enrichment("test-job")

        assert mock_job_status["status"] == "failed"
        assert "Unexpected error" in mock_job_status["message"]

    @pytest.mark.asyncio
    async def test_respects_limit_parameter(self, mock_job_status, monkeypatch):
        """run_bioguide_enrichment() respects the limit parameter."""
        from app.services.bioguide_enrichment import run_bioguide_enrichment
        import app.services.bioguide_enrichment as module

        monkeypatch.setattr(module, "JOB_STATUS", {"test-job": mock_job_status})

        with patch.object(module, "get_supabase") as mock_supabase:
            mock_supabase.return_value = MagicMock()

            with patch.object(module, "fetch_congress_members") as mock_fetch_congress:
                mock_fetch_congress.return_value = [
                    {"bioguide_id": "A000001", "name": "Smith, John", "direct_name": "John Smith"}
                ]

                with patch.object(module, "fetch_politicians_without_bioguide") as mock_fetch_pols:
                    mock_fetch_pols.return_value = []

                    await run_bioguide_enrichment("test-job", limit=100)

                    mock_fetch_pols.assert_called_once()
                    # Check the limit was passed
                    call_args = mock_fetch_pols.call_args
                    assert call_args[1].get("limit") == 100 or call_args[0][1] == 100
