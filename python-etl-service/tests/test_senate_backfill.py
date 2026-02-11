"""
Tests for Senate PTR Historical Backfill service (app/services/senate_backfill.py).

Tests the year-by-year backfill orchestrator:
- Source URL dedup from database
- Completed year detection for resumability
- Per-year backfill logic (discovery, dedup, matching, processing)
- Full run orchestration (sequential years, skip completed, error handling)
- Concurrent run guard in the API endpoint
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
from datetime import datetime, timezone
from typing import Set


# =============================================================================
# TestGetExistingSenateSourceUrls
# =============================================================================

class TestGetExistingSenateSourceUrls:
    """Tests for get_existing_senate_source_urls."""

    def test_returns_set_of_urls(self):
        """get_existing_senate_source_urls returns a set of source URLs."""
        from app.services.senate_backfill import get_existing_senate_source_urls

        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        mock_table.select.return_value.like.return_value.range.return_value.execute.return_value = MagicMock(
            data=[
                {"source_url": "https://efdsearch.senate.gov/search/view/ptr/abc/"},
                {"source_url": "https://efdsearch.senate.gov/search/view/ptr/def/"},
            ]
        )

        urls = get_existing_senate_source_urls(mock_supabase)

        assert isinstance(urls, set)
        assert len(urls) == 2
        assert "https://efdsearch.senate.gov/search/view/ptr/abc/" in urls

    def test_handles_empty_database(self):
        """get_existing_senate_source_urls returns empty set when no records."""
        from app.services.senate_backfill import get_existing_senate_source_urls

        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        mock_table.select.return_value.like.return_value.range.return_value.execute.return_value = MagicMock(
            data=[]
        )

        urls = get_existing_senate_source_urls(mock_supabase)

        assert urls == set()

    def test_paginates_through_large_result_sets(self):
        """get_existing_senate_source_urls paginates when > 1000 records."""
        from app.services.senate_backfill import get_existing_senate_source_urls

        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # First page: 1000 records
        page1 = [{"source_url": f"https://efdsearch.senate.gov/ptr/{i}/"} for i in range(1000)]
        # Second page: 50 records (< batch_size, so pagination stops)
        page2 = [{"source_url": f"https://efdsearch.senate.gov/ptr/{i}/"} for i in range(1000, 1050)]

        mock_table.select.return_value.like.return_value.range.return_value.execute.side_effect = [
            MagicMock(data=page1),
            MagicMock(data=page2),
        ]

        urls = get_existing_senate_source_urls(mock_supabase)

        assert len(urls) == 1050


# =============================================================================
# TestGetCompletedBackfillYears
# =============================================================================

class TestGetCompletedBackfillYears:
    """Tests for get_completed_backfill_years."""

    def test_returns_completed_years(self):
        """get_completed_backfill_years returns set of completed years."""
        from app.services.senate_backfill import get_completed_backfill_years

        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {"metadata": {"year": 2020}},
                {"metadata": {"year": 2021}},
                {"metadata": {"year": 2022}},
            ]
        )

        years = get_completed_backfill_years(mock_supabase)

        assert years == {2020, 2021, 2022}

    def test_handles_empty_executions(self):
        """get_completed_backfill_years returns empty set when no executions."""
        from app.services.senate_backfill import get_completed_backfill_years

        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        years = get_completed_backfill_years(mock_supabase)

        assert years == set()

    def test_ignores_failed_executions(self):
        """get_completed_backfill_years only returns success status years."""
        from app.services.senate_backfill import get_completed_backfill_years, BACKFILL_JOB_ID

        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Only success records are queried (filter is in the query itself)
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"metadata": {"year": 2020}}]
        )

        years = get_completed_backfill_years(mock_supabase)

        # Verify the query filters by job_id and status
        select_chain = mock_table.select.return_value
        eq_calls = select_chain.eq.call_args_list
        assert any(c[0] == ("job_id", BACKFILL_JOB_ID) for c in eq_calls)


# =============================================================================
# TestBackfillYear
# =============================================================================

class TestBackfillYear:
    """Tests for backfill_year function."""

    @pytest.fixture
    def mock_job_status(self):
        """Set up JOB_STATUS for testing."""
        from app.services.house_etl import JOB_STATUS
        job_id = "test-backfill-year"
        JOB_STATUS[job_id] = {
            "status": "running",
            "progress": 0,
            "total": 1,
            "message": "",
        }
        return job_id

    @pytest.fixture
    def senators(self):
        return [
            {"first_name": "John", "last_name": "Smith", "full_name": "John Smith", "politician_id": "uuid-1"},
            {"first_name": "Jane", "last_name": "Doe", "full_name": "Jane Doe", "politician_id": "uuid-2"},
        ]

    @pytest.mark.asyncio
    async def test_skips_already_imported_disclosures(self, mock_job_status, senators):
        """backfill_year filters out disclosures already in existing_urls set."""
        from app.services.senate_backfill import backfill_year

        existing_urls = {"https://efdsearch.senate.gov/search/view/ptr/existing/"}

        raw = [
            {"source_url": "https://efdsearch.senate.gov/search/view/ptr/existing/",
             "first_name": "John", "last_name": "Smith", "politician_name": "John Smith"},
            {"source_url": "https://efdsearch.senate.gov/search/view/ptr/new/",
             "first_name": "Jane", "last_name": "Doe", "politician_name": "Jane Doe"},
        ]

        with patch("app.services.senate_backfill.search_all_ptr_disclosures_playwright",
                    new_callable=AsyncMock, return_value=raw):
            with patch("app.services.senate_backfill._match_disclosures_to_senators",
                        return_value=[{"source_url": "https://efdsearch.senate.gov/search/view/ptr/new/",
                                      "is_paper": False}]):
                with patch("app.services.senate_backfill.process_disclosures_playwright",
                            new_callable=AsyncMock, return_value=(2, 0)):
                    with patch("app.services.senate_backfill.log_job_execution"):
                        stats = await backfill_year(
                            year=2020,
                            senators=senators,
                            supabase=MagicMock(),
                            existing_urls=existing_urls,
                            job_id=mock_job_status,
                            idx=1,
                            total=1,
                        )

        assert stats["skipped_existing"] == 1
        assert stats["discovered"] == 2

    @pytest.mark.asyncio
    async def test_passes_correct_date_range(self, mock_job_status, senators):
        """backfill_year passes start_date=01/01/{year} and end_date=12/31/{year}."""
        from app.services.senate_backfill import backfill_year

        with patch("app.services.senate_backfill.search_all_ptr_disclosures_playwright",
                    new_callable=AsyncMock, return_value=[]) as mock_search:
            with patch("app.services.senate_backfill.log_job_execution"):
                await backfill_year(
                    year=2018,
                    senators=senators,
                    supabase=MagicMock(),
                    existing_urls=set(),
                    job_id=mock_job_status,
                    idx=1,
                    total=1,
                )

        mock_search.assert_awaited_once_with(
            start_date="01/01/2018",
            end_date="12/31/2018",
        )

    @pytest.mark.asyncio
    async def test_matches_disclosures_to_senators(self, mock_job_status, senators):
        """backfill_year calls _match_disclosures_to_senators with new disclosures."""
        from app.services.senate_backfill import backfill_year

        raw = [{"source_url": "https://efdsearch.senate.gov/ptr/new/",
                "first_name": "John", "last_name": "Smith", "politician_name": "John Smith"}]

        with patch("app.services.senate_backfill.search_all_ptr_disclosures_playwright",
                    new_callable=AsyncMock, return_value=raw):
            with patch("app.services.senate_backfill._match_disclosures_to_senators",
                        return_value=[]) as mock_match:
                with patch("app.services.senate_backfill.log_job_execution"):
                    await backfill_year(
                        year=2020,
                        senators=senators,
                        supabase=MagicMock(),
                        existing_urls=set(),
                        job_id=mock_job_status,
                        idx=1,
                        total=1,
                    )

        mock_match.assert_called_once_with(raw, senators)

    @pytest.mark.asyncio
    async def test_filters_paper_filings(self, mock_job_status, senators):
        """backfill_year filters out paper filings."""
        from app.services.senate_backfill import backfill_year

        raw = [
            {"source_url": "https://efdsearch.senate.gov/ptr/e1/",
             "first_name": "John", "last_name": "Smith", "politician_name": "John Smith"},
        ]

        matched = [
            {"source_url": "https://efdsearch.senate.gov/ptr/e1/", "is_paper": False},
            {"source_url": "https://efdsearch.senate.gov/ptr/p1/", "is_paper": True},
        ]

        with patch("app.services.senate_backfill.search_all_ptr_disclosures_playwright",
                    new_callable=AsyncMock, return_value=raw):
            with patch("app.services.senate_backfill._match_disclosures_to_senators",
                        return_value=matched):
                with patch("app.services.senate_backfill.process_disclosures_playwright",
                            new_callable=AsyncMock, return_value=(1, 0)) as mock_process:
                    with patch("app.services.senate_backfill.log_job_execution"):
                        stats = await backfill_year(
                            year=2020,
                            senators=senators,
                            supabase=MagicMock(),
                            existing_urls=set(),
                            job_id=mock_job_status,
                            idx=1,
                            total=1,
                        )

        assert stats["skipped_paper"] == 1
        # Only electronic disclosures passed to process
        electronic = mock_process.call_args[0][0]
        assert len(electronic) == 1
        assert not electronic[0]["is_paper"]

    @pytest.mark.asyncio
    async def test_returns_stats_dict(self, mock_job_status, senators):
        """backfill_year returns a stats dict with all expected keys."""
        from app.services.senate_backfill import backfill_year

        with patch("app.services.senate_backfill.search_all_ptr_disclosures_playwright",
                    new_callable=AsyncMock, return_value=[]):
            with patch("app.services.senate_backfill.log_job_execution"):
                stats = await backfill_year(
                    year=2015,
                    senators=senators,
                    supabase=MagicMock(),
                    existing_urls=set(),
                    job_id=mock_job_status,
                    idx=1,
                    total=1,
                )

        assert "year" in stats
        assert stats["year"] == 2015
        assert "discovered" in stats
        assert "skipped_existing" in stats
        assert "skipped_paper" in stats
        assert "processed" in stats
        assert "transactions" in stats
        assert "errors" in stats


# =============================================================================
# TestRunSenateBackfill
# =============================================================================

class TestRunSenateBackfill:
    """Tests for run_senate_backfill orchestrator."""

    @pytest.fixture
    def mock_job_status(self):
        """Set up JOB_STATUS for testing."""
        from app.services.house_etl import JOB_STATUS
        job_id = "test-run-backfill"
        JOB_STATUS[job_id] = {
            "status": "queued",
            "progress": 0,
            "total": None,
            "message": "Job queued",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
        }
        return job_id

    @pytest.mark.asyncio
    async def test_processes_years_sequentially(self, mock_job_status):
        """run_senate_backfill processes years in order."""
        from app.services.senate_backfill import run_senate_backfill
        from app.services.house_etl import JOB_STATUS

        senators = [{"first_name": "John", "last_name": "Smith", "full_name": "John Smith",
                     "bioguide_id": "S123"}]

        year_calls = []

        async def mock_backfill_year(year, **kwargs):
            year_calls.append(year)
            return {"year": year, "discovered": 0, "skipped_existing": 0,
                    "skipped_paper": 0, "processed": 0, "transactions": 0, "errors": 0}

        with patch("app.services.senate_backfill.get_supabase", return_value=MagicMock()):
            with patch("app.services.senate_backfill.fetch_senators_from_xml",
                        new_callable=AsyncMock, return_value=senators):
                with patch("app.services.senate_backfill.upsert_senator_to_db", return_value="uuid"):
                    with patch("app.services.senate_backfill.get_existing_senate_source_urls", return_value=set()):
                        with patch("app.services.senate_backfill.get_completed_backfill_years", return_value=set()):
                            with patch("app.services.senate_backfill.backfill_year",
                                        new_callable=AsyncMock, side_effect=mock_backfill_year):
                                with patch("app.services.senate_backfill.asyncio.sleep",
                                            new_callable=AsyncMock):
                                    await run_senate_backfill(
                                        job_id=mock_job_status,
                                        start_year=2020,
                                        end_year=2022,
                                    )

        assert year_calls == [2020, 2021, 2022]
        assert JOB_STATUS[mock_job_status]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_skips_completed_years(self, mock_job_status):
        """run_senate_backfill skips years already completed."""
        from app.services.senate_backfill import run_senate_backfill
        from app.services.house_etl import JOB_STATUS

        senators = [{"first_name": "John", "last_name": "Smith", "full_name": "John Smith",
                     "bioguide_id": "S123"}]

        year_calls = []

        async def mock_backfill_year(year, **kwargs):
            year_calls.append(year)
            return {"year": year, "discovered": 0, "skipped_existing": 0,
                    "skipped_paper": 0, "processed": 0, "transactions": 0, "errors": 0}

        with patch("app.services.senate_backfill.get_supabase", return_value=MagicMock()):
            with patch("app.services.senate_backfill.fetch_senators_from_xml",
                        new_callable=AsyncMock, return_value=senators):
                with patch("app.services.senate_backfill.upsert_senator_to_db", return_value="uuid"):
                    with patch("app.services.senate_backfill.get_existing_senate_source_urls", return_value=set()):
                        with patch("app.services.senate_backfill.get_completed_backfill_years",
                                    return_value={2020, 2022}):
                            with patch("app.services.senate_backfill.backfill_year",
                                        new_callable=AsyncMock, side_effect=mock_backfill_year):
                                with patch("app.services.senate_backfill.asyncio.sleep",
                                            new_callable=AsyncMock):
                                    await run_senate_backfill(
                                        job_id=mock_job_status,
                                        start_year=2020,
                                        end_year=2022,
                                    )

        # Only 2021 should be processed
        assert year_calls == [2021]

    @pytest.mark.asyncio
    async def test_continues_on_year_failure(self, mock_job_status):
        """run_senate_backfill continues to next year when one fails."""
        from app.services.senate_backfill import run_senate_backfill
        from app.services.house_etl import JOB_STATUS

        senators = [{"first_name": "John", "last_name": "Smith", "full_name": "John Smith",
                     "bioguide_id": "S123"}]

        call_count = 0

        async def mock_backfill_year(year, **kwargs):
            nonlocal call_count
            call_count += 1
            if year == 2021:
                raise Exception("Year 2021 failed")
            return {"year": year, "discovered": 0, "skipped_existing": 0,
                    "skipped_paper": 0, "processed": 0, "transactions": 0, "errors": 0}

        with patch("app.services.senate_backfill.get_supabase", return_value=MagicMock()):
            with patch("app.services.senate_backfill.fetch_senators_from_xml",
                        new_callable=AsyncMock, return_value=senators):
                with patch("app.services.senate_backfill.upsert_senator_to_db", return_value="uuid"):
                    with patch("app.services.senate_backfill.get_existing_senate_source_urls", return_value=set()):
                        with patch("app.services.senate_backfill.get_completed_backfill_years", return_value=set()):
                            with patch("app.services.senate_backfill.backfill_year",
                                        new_callable=AsyncMock, side_effect=mock_backfill_year):
                                with patch("app.services.senate_backfill.log_job_execution"):
                                    with patch("app.services.senate_backfill.asyncio.sleep",
                                                new_callable=AsyncMock):
                                        await run_senate_backfill(
                                            job_id=mock_job_status,
                                            start_year=2020,
                                            end_year=2022,
                                        )

        # All 3 years attempted despite 2021 failure
        assert call_count == 3
        assert JOB_STATUS[mock_job_status]["status"] == "completed"
        assert "1 failed" in JOB_STATUS[mock_job_status]["message"]

    @pytest.mark.asyncio
    async def test_updates_job_status_throughout(self, mock_job_status):
        """run_senate_backfill updates JOB_STATUS progress as years complete."""
        from app.services.senate_backfill import run_senate_backfill
        from app.services.house_etl import JOB_STATUS

        senators = [{"first_name": "John", "last_name": "Smith", "full_name": "John Smith",
                     "bioguide_id": "S123"}]

        async def mock_backfill_year(year, **kwargs):
            return {"year": year, "discovered": 10, "skipped_existing": 0,
                    "skipped_paper": 0, "processed": 8, "transactions": 5, "errors": 0}

        with patch("app.services.senate_backfill.get_supabase", return_value=MagicMock()):
            with patch("app.services.senate_backfill.fetch_senators_from_xml",
                        new_callable=AsyncMock, return_value=senators):
                with patch("app.services.senate_backfill.upsert_senator_to_db", return_value="uuid"):
                    with patch("app.services.senate_backfill.get_existing_senate_source_urls", return_value=set()):
                        with patch("app.services.senate_backfill.get_completed_backfill_years", return_value=set()):
                            with patch("app.services.senate_backfill.backfill_year",
                                        new_callable=AsyncMock, side_effect=mock_backfill_year):
                                with patch("app.services.senate_backfill.asyncio.sleep",
                                            new_callable=AsyncMock):
                                    await run_senate_backfill(
                                        job_id=mock_job_status,
                                        start_year=2024,
                                        end_year=2025,
                                    )

        assert JOB_STATUS[mock_job_status]["progress"] == 2
        assert JOB_STATUS[mock_job_status]["total"] == 2
        assert "10 transactions" in JOB_STATUS[mock_job_status]["message"]

    @pytest.mark.asyncio
    async def test_fails_when_senators_empty(self, mock_job_status):
        """run_senate_backfill reports error when no senators fetched."""
        from app.services.senate_backfill import run_senate_backfill
        from app.services.house_etl import JOB_STATUS

        with patch("app.services.senate_backfill.get_supabase", return_value=MagicMock()):
            with patch("app.services.senate_backfill.fetch_senators_from_xml",
                        new_callable=AsyncMock, return_value=[]):
                await run_senate_backfill(
                    job_id=mock_job_status,
                    start_year=2020,
                    end_year=2020,
                )

        assert JOB_STATUS[mock_job_status]["status"] == "error"
        assert "Failed to fetch senators" in JOB_STATUS[mock_job_status]["message"]


# =============================================================================
# TestConcurrencyGuard
# =============================================================================

class TestConcurrencyGuard:
    """Tests for concurrent run guard in the API endpoint."""

    @pytest.mark.asyncio
    async def test_blocks_concurrent_backfill(self):
        """POST /backfill-senate returns 409 when another backfill is running."""
        from fastapi.testclient import TestClient
        from app.services.house_etl import JOB_STATUS

        # Simulate a running backfill
        JOB_STATUS["existing-backfill"] = {
            "_type": "senate_backfill",
            "status": "running",
            "progress": 3,
            "total": 15,
            "message": "Year 2014...",
        }

        try:
            from app.main import app
            client = TestClient(app)
            response = client.post("/etl/backfill-senate", json={})

            assert response.status_code == 409
            assert "already running" in response.json()["detail"]
        finally:
            del JOB_STATUS["existing-backfill"]

    @pytest.mark.asyncio
    async def test_allows_after_completion(self):
        """POST /backfill-senate allows new backfill after previous completed."""
        from fastapi.testclient import TestClient
        from app.services.house_etl import JOB_STATUS

        # Simulate a completed backfill
        JOB_STATUS["old-backfill"] = {
            "_type": "senate_backfill",
            "status": "completed",
            "progress": 15,
            "total": 15,
            "message": "Done",
        }

        try:
            # Mock the backfill function so the background task doesn't hit Supabase
            with patch("app.routes.etl.run_senate_backfill", new_callable=AsyncMock):
                from app.main import app
                client = TestClient(app)
                response = client.post("/etl/backfill-senate", json={})

                assert response.status_code == 200
                assert response.json()["status"] == "started"
        finally:
            del JOB_STATUS["old-backfill"]
            # Clean up the newly created job
            for k in list(JOB_STATUS.keys()):
                if JOB_STATUS[k].get("_type") == "senate_backfill" and JOB_STATUS[k]["status"] == "queued":
                    del JOB_STATUS[k]


# =============================================================================
# TestBackfillConstants
# =============================================================================

class TestBackfillConstants:
    """Tests for module-level constants."""

    def test_backfill_year_range(self):
        """BACKFILL_START_YEAR and BACKFILL_END_YEAR are sensible."""
        from app.services.senate_backfill import BACKFILL_START_YEAR, BACKFILL_END_YEAR

        assert BACKFILL_START_YEAR == 2012  # STOCK Act
        assert BACKFILL_END_YEAR == 2026
        assert BACKFILL_END_YEAR > BACKFILL_START_YEAR

    def test_backfill_job_id_constant(self):
        """BACKFILL_JOB_ID is defined for job_executions tracking."""
        from app.services.senate_backfill import BACKFILL_JOB_ID

        assert BACKFILL_JOB_ID == "politician-trading-senate-backfill"

    def test_cooldown_is_reasonable(self):
        """YEAR_COOLDOWN_SECONDS is positive and reasonable."""
        from app.services.senate_backfill import YEAR_COOLDOWN_SECONDS

        assert 1 <= YEAR_COOLDOWN_SECONDS <= 30
