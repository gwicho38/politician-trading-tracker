"""
Tests for ETL Routes (app/routes/etl.py).

Tests:
- GET /etl/sources - List ETL sources
- POST /etl/trigger - Trigger ETL job
- GET /etl/status/{job_id} - Get job status
- POST /etl/backfill-tickers - Trigger ticker backfill
- POST /etl/backfill-transaction-types - Trigger transaction type backfill
- POST /etl/enrich-bioguide - Trigger bioguide enrichment
- POST /etl/ingest-url - Ingest single URL
- GET /etl/senators - Get senator list
- POST /etl/cleanup-executions - Cleanup old executions
- parse_pdf_url() - URL parsing helper
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient


# =============================================================================
# parse_pdf_url() Tests
# =============================================================================

class TestParsePdfUrl:
    """Tests for parse_pdf_url() helper function."""

    def test_parses_ptr_pdf_url(self):
        """parse_pdf_url() parses PTR PDF URL."""
        from app.routes.etl import parse_pdf_url

        year, doc_id, filing_type = parse_pdf_url(
            "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2025/20033576.pdf"
        )

        assert year == 2025
        assert doc_id == "20033576"
        assert filing_type == "P"

    def test_parses_financial_pdf_url(self):
        """parse_pdf_url() parses financial PDF URL."""
        from app.routes.etl import parse_pdf_url

        year, doc_id, filing_type = parse_pdf_url(
            "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/2024/12345678.pdf"
        )

        assert year == 2024
        assert doc_id == "12345678"
        assert filing_type == "F"

    def test_raises_for_invalid_url(self):
        """parse_pdf_url() raises ValueError for invalid URL."""
        from app.routes.etl import parse_pdf_url

        with pytest.raises(ValueError, match="Could not parse PDF URL"):
            parse_pdf_url("https://example.com/invalid.pdf")


# =============================================================================
# GET /etl/sources Tests
# =============================================================================

class TestListSources:
    """Tests for GET /etl/sources endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_list_sources_returns_200(self, client):
        """GET /etl/sources returns 200 status."""
        response = client.get("/etl/sources")

        assert response.status_code == 200

    def test_list_sources_returns_sources_list(self, client):
        """GET /etl/sources returns list of sources."""
        response = client.get("/etl/sources")
        data = response.json()

        assert "sources" in data
        assert isinstance(data["sources"], list)

    def test_list_sources_contains_house(self, client):
        """GET /etl/sources contains house source."""
        response = client.get("/etl/sources")
        data = response.json()

        source_ids = [s["source_id"] for s in data["sources"]]
        assert "house" in source_ids

    def test_list_sources_contains_senate(self, client):
        """GET /etl/sources contains senate source."""
        response = client.get("/etl/sources")
        data = response.json()

        source_ids = [s["source_id"] for s in data["sources"]]
        assert "senate" in source_ids


# =============================================================================
# POST /etl/trigger Tests
# =============================================================================

class TestTriggerEtl:
    """Tests for POST /etl/trigger endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client that doesn't wait for background tasks."""
        from app.main import app
        # Use raise_server_exceptions=False to avoid waiting for background tasks
        with patch("app.routes.etl.run_house_etl") as mock_house:
            with patch("app.routes.etl.run_senate_etl") as mock_senate:
                mock_house.return_value = None
                mock_senate.return_value = None
                yield TestClient(app, raise_server_exceptions=False)

    def test_trigger_house_returns_200(self, client):
        """POST /etl/trigger for house returns 200."""
        response = client.post(
            "/etl/trigger",
            json={"source": "house", "year": 2025}
        )

        assert response.status_code == 200

    def test_trigger_senate_returns_200(self, client):
        """POST /etl/trigger for senate returns 200."""
        response = client.post(
            "/etl/trigger",
            json={"source": "senate", "lookback_days": 30}
        )

        assert response.status_code == 200

    def test_trigger_returns_job_id(self, client):
        """POST /etl/trigger returns job ID."""
        response = client.post(
            "/etl/trigger",
            json={"source": "house", "year": 2025}
        )
        data = response.json()

        assert "job_id" in data
        assert len(data["job_id"]) == 36  # UUID format

    def test_trigger_returns_started_status(self, client):
        """POST /etl/trigger returns started status."""
        response = client.post(
            "/etl/trigger",
            json={"source": "house", "year": 2025}
        )
        data = response.json()

        assert data["status"] == "started"

    def test_trigger_invalid_source_returns_400(self):
        """POST /etl/trigger with invalid source returns 400."""
        from app.main import app
        client = TestClient(app)
        response = client.post(
            "/etl/trigger",
            json={"source": "invalid_source", "year": 2025}
        )

        assert response.status_code == 400
        assert "Unsupported source" in response.json()["detail"]

    def test_trigger_with_limit(self, client):
        """POST /etl/trigger with limit parameter."""
        response = client.post(
            "/etl/trigger",
            json={"source": "house", "year": 2025, "limit": 10}
        )

        assert response.status_code == 200
        assert "up to 10" in response.json()["message"]

    def test_trigger_with_update_mode(self, client):
        """POST /etl/trigger with update_mode parameter."""
        response = client.post(
            "/etl/trigger",
            json={"source": "house", "year": 2025, "update_mode": True}
        )

        assert response.status_code == 200
        assert "UPDATE MODE" in response.json()["message"]


# =============================================================================
# GET /etl/status/{job_id} Tests
# =============================================================================

class TestGetJobStatus:
    """Tests for GET /etl/status/{job_id} endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client that doesn't wait for background tasks."""
        from app.main import app
        with patch("app.routes.etl.run_house_etl") as mock_house:
            mock_house.return_value = None
            yield TestClient(app, raise_server_exceptions=False)

    def test_status_for_existing_job(self, client):
        """GET /etl/status/{job_id} returns status for existing job."""
        # First trigger a job
        trigger_response = client.post(
            "/etl/trigger",
            json={"source": "house", "year": 2025}
        )
        job_id = trigger_response.json()["job_id"]

        # Then check status
        response = client.get(f"/etl/status/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert "status" in data

    def test_status_for_nonexistent_job_returns_404(self):
        """GET /etl/status/{job_id} returns 404 for nonexistent job."""
        from app.main import app
        client = TestClient(app)
        response = client.get("/etl/status/nonexistent-job-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


# =============================================================================
# POST /etl/backfill-tickers Tests
# =============================================================================

class TestBackfillTickers:
    """Tests for POST /etl/backfill-tickers endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client that doesn't wait for background tasks."""
        from app.main import app
        with patch("app.routes.etl.run_ticker_backfill") as mock_backfill:
            mock_backfill.return_value = None
            yield TestClient(app, raise_server_exceptions=False)

    def test_backfill_tickers_returns_200(self, client):
        """POST /etl/backfill-tickers returns 200."""
        response = client.post("/etl/backfill-tickers", json={})

        assert response.status_code == 200

    def test_backfill_tickers_returns_job_id(self, client):
        """POST /etl/backfill-tickers returns job ID."""
        response = client.post("/etl/backfill-tickers", json={})
        data = response.json()

        assert "job_id" in data
        assert len(data["job_id"]) == 36

    def test_backfill_tickers_with_limit(self, client):
        """POST /etl/backfill-tickers with limit parameter."""
        response = client.post(
            "/etl/backfill-tickers",
            json={"limit": 50}
        )

        assert response.status_code == 200
        assert "up to 50" in response.json()["message"]


# =============================================================================
# POST /etl/backfill-transaction-types Tests
# =============================================================================

class TestBackfillTransactionTypes:
    """Tests for POST /etl/backfill-transaction-types endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client that doesn't wait for background tasks."""
        from app.main import app
        with patch("app.routes.etl.run_transaction_type_backfill") as mock_backfill:
            mock_backfill.return_value = None
            yield TestClient(app, raise_server_exceptions=False)

    def test_backfill_transaction_types_returns_200(self, client):
        """POST /etl/backfill-transaction-types returns 200."""
        response = client.post("/etl/backfill-transaction-types", json={})

        assert response.status_code == 200

    def test_backfill_transaction_types_returns_job_id(self, client):
        """POST /etl/backfill-transaction-types returns job ID."""
        response = client.post("/etl/backfill-transaction-types", json={})
        data = response.json()

        assert "job_id" in data


# =============================================================================
# POST /etl/enrich-bioguide Tests
# =============================================================================

class TestEnrichBioguide:
    """Tests for POST /etl/enrich-bioguide endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client that doesn't wait for background tasks."""
        from app.main import app
        with patch("app.routes.etl.run_bioguide_enrichment") as mock_enrich:
            mock_enrich.return_value = None
            yield TestClient(app, raise_server_exceptions=False)

    def test_enrich_bioguide_returns_200(self, client):
        """POST /etl/enrich-bioguide returns 200."""
        response = client.post("/etl/enrich-bioguide", json={})

        assert response.status_code == 200

    def test_enrich_bioguide_returns_job_id(self, client):
        """POST /etl/enrich-bioguide returns job ID."""
        response = client.post("/etl/enrich-bioguide", json={})
        data = response.json()

        assert "job_id" in data
        assert len(data["job_id"]) == 36

    def test_enrich_bioguide_with_limit(self, client):
        """POST /etl/enrich-bioguide with limit parameter."""
        response = client.post(
            "/etl/enrich-bioguide",
            json={"limit": 100}
        )

        assert response.status_code == 200
        assert "up to 100" in response.json()["message"]


# =============================================================================
# POST /etl/ingest-url Tests
# =============================================================================

class TestIngestUrl:
    """Tests for POST /etl/ingest-url endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_ingest_url_invalid_url_returns_400(self, client):
        """POST /etl/ingest-url with invalid URL returns 400."""
        response = client.post(
            "/etl/ingest-url",
            json={"url": "https://example.com/invalid.pdf"}
        )

        assert response.status_code == 400
        assert "Could not parse PDF URL" in response.json()["detail"]

    def test_ingest_url_dry_run_parses_url(self, client):
        """POST /etl/ingest-url with dry_run parses URL correctly."""
        # Mock the HTTP client to avoid actual network calls
        with patch("app.routes.etl.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.content = b"%PDF-1.4 fake pdf content"
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock()
            mock_client.return_value = mock_instance

            with patch("app.routes.etl.extract_tables_from_pdf", return_value=[]):
                response = client.post(
                    "/etl/ingest-url",
                    json={
                        "url": "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2025/20033576.pdf",
                        "dry_run": True
                    }
                )

        assert response.status_code == 200
        data = response.json()
        assert data["doc_id"] == "20033576"
        assert data["year"] == 2025
        assert data["dry_run"] is True


# =============================================================================
# GET /etl/senators Tests
# =============================================================================

class TestGetSenators:
    """Tests for GET /etl/senators endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_get_senators_returns_200(self, client):
        """GET /etl/senators returns 200."""
        with patch("app.routes.etl.fetch_senators_from_xml") as mock_fetch:
            mock_fetch.return_value = [
                {"name": "Test Senator", "bioguide_id": "T000001"}
            ]

            with patch("app.routes.etl.get_senate_supabase_client") as mock_supabase:
                mock_supabase.return_value = MagicMock()

                response = client.get("/etl/senators")

        assert response.status_code == 200

    def test_get_senators_returns_senators_list(self, client):
        """GET /etl/senators returns senators list."""
        with patch("app.routes.etl.fetch_senators_from_xml") as mock_fetch:
            mock_fetch.return_value = [
                {"name": "Test Senator", "bioguide_id": "T000001"}
            ]

            with patch("app.routes.etl.get_senate_supabase_client") as mock_supabase:
                mock_supabase.return_value = MagicMock()

                response = client.get("/etl/senators")

        data = response.json()
        assert "senators" in data
        assert isinstance(data["senators"], list)


# =============================================================================
# POST /etl/cleanup-executions Tests
# =============================================================================

class TestCleanupExecutions:
    """Tests for POST /etl/cleanup-executions endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from app.main import app
        return TestClient(app)

    def test_cleanup_executions_returns_200(self, client):
        """POST /etl/cleanup-executions returns 200."""
        with patch("app.routes.etl.get_supabase") as mock_supabase:
            mock_supabase.return_value = MagicMock()

            with patch("app.lib.job_logger.cleanup_old_executions") as mock_cleanup:
                mock_cleanup.return_value = 10

                response = client.post(
                    "/etl/cleanup-executions",
                    json={"days": 30}
                )

        assert response.status_code == 200

    def test_cleanup_executions_returns_deleted_count(self, client):
        """POST /etl/cleanup-executions returns deleted count."""
        with patch("app.routes.etl.get_supabase") as mock_supabase:
            mock_supabase.return_value = MagicMock()

            with patch("app.lib.job_logger.cleanup_old_executions") as mock_cleanup:
                mock_cleanup.return_value = 25

                response = client.post(
                    "/etl/cleanup-executions",
                    json={"days": 30}
                )

        data = response.json()
        assert data["deleted"] == 25
        assert "25" in data["message"]

    def test_cleanup_executions_default_days(self, client):
        """POST /etl/cleanup-executions uses default 30 days."""
        with patch("app.routes.etl.get_supabase") as mock_supabase:
            mock_supabase.return_value = MagicMock()

            with patch("app.lib.job_logger.cleanup_old_executions") as mock_cleanup:
                mock_cleanup.return_value = 0

                response = client.post(
                    "/etl/cleanup-executions",
                    json={}
                )

        assert response.status_code == 200
        # Default should be 30 days
        mock_cleanup.assert_called_once()
        call_args = mock_cleanup.call_args
        assert call_args[1]["days"] == 30
