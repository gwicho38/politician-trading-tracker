"""Tests for source document backfill service."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

from app.services.source_document_backfill import (
    SourceDocumentBackfillService,
    backfill_year,
    backfill_all,
)


class TestSourceDocumentBackfillService:
    """Tests for SourceDocumentBackfillService."""

    def test_normalize_name_removes_honorifics(self):
        """Test that honorifics are removed from names."""
        service = SourceDocumentBackfillService()

        assert service._normalize_name("Hon. Nancy Pelosi") == "nancy pelosi"
        assert service._normalize_name("Rep. Kevin McCarthy") == "kevin mccarthy"
        assert service._normalize_name("Senator John Smith") == "john smith"

    def test_normalize_name_removes_suffixes(self):
        """Test that suffixes are removed from names."""
        service = SourceDocumentBackfillService()

        assert service._normalize_name("John Smith Jr.") == "john smith"
        assert service._normalize_name("James Brown III") == "james brown"
        assert service._normalize_name("Robert Davis Sr.") == "robert davis"

    def test_normalize_name_handles_empty(self):
        """Test that empty names are handled."""
        service = SourceDocumentBackfillService()

        assert service._normalize_name("") == ""
        assert service._normalize_name(None) == ""

    def test_normalize_name_removes_punctuation(self):
        """Test that punctuation is removed."""
        service = SourceDocumentBackfillService()

        assert service._normalize_name("John, Smith") == "john smith"
        assert service._normalize_name("Nancy Pelosi.") == "nancy pelosi"

    def test_name_similarity_exact_match(self):
        """Test similarity for exact matches."""
        service = SourceDocumentBackfillService()

        assert service._name_similarity("john smith", "john smith") == 1.0

    def test_name_similarity_similar_names(self):
        """Test similarity for similar names."""
        service = SourceDocumentBackfillService()

        similarity = service._name_similarity("john smith", "john smyth")
        assert 0.8 < similarity < 1.0

    def test_name_similarity_different_names(self):
        """Test similarity for different names."""
        service = SourceDocumentBackfillService()

        similarity = service._name_similarity("john smith", "jane doe")
        assert similarity < 0.5

    def test_name_similarity_empty_names(self):
        """Test similarity for empty names."""
        service = SourceDocumentBackfillService()

        assert service._name_similarity("", "john smith") == 0.0
        assert service._name_similarity("john smith", "") == 0.0
        assert service._name_similarity("", "") == 0.0

    def test_calculate_match_score_exact_name_recent_date(self):
        """Test match score for exact name and recent date."""
        service = SourceDocumentBackfillService()

        record = {"disclosure_date": "2025-01-15"}
        filing = {"filing_date": "2025-01-15"}

        score = service._calculate_match_score(record, filing, name_similarity=1.0)
        assert score == 1.0  # 0.6 (name) + 0.4 (date)

    def test_calculate_match_score_exact_name_old_date(self):
        """Test match score for exact name but older date."""
        service = SourceDocumentBackfillService()

        record = {"disclosure_date": "2025-01-15"}
        filing = {"filing_date": "2025-03-15"}  # 59 days later

        score = service._calculate_match_score(record, filing, name_similarity=1.0)
        # Name = 0.6, date score diminishes after 30 days
        assert 0.6 < score < 0.8

    def test_calculate_match_score_no_dates(self):
        """Test match score when dates are missing."""
        service = SourceDocumentBackfillService()

        record = {}
        filing = {}

        score = service._calculate_match_score(record, filing, name_similarity=1.0)
        assert score == 0.6  # Only name component

    def test_parse_house_index_valid_content(self):
        """Test parsing valid House index content."""
        service = SourceDocumentBackfillService()

        content = """Prefix\tLastName\tFirstName\tSuffix\tFilingType\tStateDistrict\tFileYear\tFilingDate\tDocID
Hon.\tPelosi\tNancy\t\tP\tCA-11\t2025\t01/15/2025\t10020001
\tMcCarthy\tKevin\t\tP\tCA-20\t2025\t01/20/2025\t10020002"""

        filings = service._parse_house_index(content, 2025)

        assert len(filings) == 2
        assert filings[0]["doc_id"] == "10020001"
        assert filings[0]["politician_name"] == "Hon. Nancy Pelosi"
        assert filings[0]["filing_type"] == "P"
        assert filings[1]["doc_id"] == "10020002"
        assert filings[1]["politician_name"] == "Kevin McCarthy"

    def test_parse_house_index_skips_header(self):
        """Test that header row is skipped."""
        service = SourceDocumentBackfillService()

        content = """Prefix\tLastName\tFirstName\tSuffix\tFilingType\tStateDistrict\tFileYear\tFilingDate\tDocID"""

        filings = service._parse_house_index(content, 2025)
        assert len(filings) == 0

    def test_parse_house_index_skips_invalid_rows(self):
        """Test that invalid rows are skipped."""
        service = SourceDocumentBackfillService()

        content = """Prefix\tLastName\tFirstName
incomplete\trow"""

        filings = service._parse_house_index(content, 2025)
        assert len(filings) == 0


class TestFetchRecordsWithoutSourceId:
    """Tests for _fetch_records_without_source_id method."""

    @pytest.mark.asyncio
    async def test_fetches_and_enriches_records(self):
        """Test that records are fetched and enriched with politician names."""
        mock_supabase = MagicMock()

        # Mock trading_disclosures query
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.is_.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.lte.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.in_.return_value = mock_table

        # First call returns disclosures, second call returns politicians
        mock_table.execute.side_effect = [
            MagicMock(data=[
                {"id": "1", "politician_id": "pol-1", "disclosure_date": "2025-01-15"},
                {"id": "2", "politician_id": "pol-2", "disclosure_date": "2025-01-16"},
            ]),
            MagicMock(data=[
                {"id": "pol-1", "name": "Nancy Pelosi"},
                {"id": "pol-2", "name": "Kevin McCarthy"},
            ]),
        ]

        with patch.object(SourceDocumentBackfillService, '__init__', lambda x: None):
            service = SourceDocumentBackfillService()
            service.supabase = mock_supabase

            records = await service._fetch_records_without_source_id(2025)

        assert len(records) == 2
        assert records[0]["politician_name"] == "Nancy Pelosi"
        assert records[1]["politician_name"] == "Kevin McCarthy"

    @pytest.mark.asyncio
    async def test_handles_missing_politician_ids(self):
        """Test handling of records without politician_id."""
        mock_supabase = MagicMock()

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.is_.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.lte.return_value = mock_table
        mock_table.limit.return_value = mock_table

        mock_table.execute.return_value = MagicMock(data=[
            {"id": "1", "politician_id": None, "disclosure_date": "2025-01-15"},
        ])

        with patch.object(SourceDocumentBackfillService, '__init__', lambda x: None):
            service = SourceDocumentBackfillService()
            service.supabase = mock_supabase

            records = await service._fetch_records_without_source_id(2025)

        assert len(records) == 1
        assert records[0]["politician_name"] is None

    @pytest.mark.asyncio
    async def test_handles_no_records(self):
        """Test handling when no records need backfill."""
        mock_supabase = MagicMock()

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.is_.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.lte.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])

        with patch.object(SourceDocumentBackfillService, '__init__', lambda x: None):
            service = SourceDocumentBackfillService()
            service.supabase = mock_supabase

            records = await service._fetch_records_without_source_id(2025)

        assert len(records) == 0


class TestBackfillConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @pytest.mark.asyncio
    async def test_backfill_year_creates_service(self):
        """Test that backfill_year creates a service and calls backfill_year."""
        with patch.object(
            SourceDocumentBackfillService, 'backfill_year',
            new_callable=AsyncMock
        ) as mock_method:
            mock_method.return_value = {"matched": 10, "updated": 5}

            result = await backfill_year(2025, dry_run=True, threshold=0.85)

            mock_method.assert_called_once_with(2025, True, 0.85)
            assert result["matched"] == 10

    @pytest.mark.asyncio
    async def test_backfill_all_creates_service(self):
        """Test that backfill_all creates a service and calls backfill_all_years."""
        with patch.object(
            SourceDocumentBackfillService, 'backfill_all_years',
            new_callable=AsyncMock
        ) as mock_method:
            mock_method.return_value = {"total_matched": 100, "total_updated": 50}

            result = await backfill_all(
                from_year=2020, to_year=2025, dry_run=True, threshold=0.8
            )

            mock_method.assert_called_once_with(2020, 2025, True, 0.8)
            assert result["total_matched"] == 100
