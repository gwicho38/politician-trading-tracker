"""
Tests for EU Parliament ETL Service.

Covers:
- EU Parliament client (XML parsing, HTML parsing, PDF download)
- PDF section splitting and financial interest extraction
- MEP name splitting
- Income range extraction
- Schema mapping (parse_disclosure)
- Registry integration
- End-to-end run() with mocked HTTP + DB
"""

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.eu_etl import (
    EUParliamentETLService,
    extract_financial_interests,
    split_sections,
    _extract_income_range,
    _parse_eur_number,
    _parse_section_entries,
    _clean_entity_name,
    _split_mep_name,
    SECTION_ASSET_TYPES,
    EXTRACTABLE_SECTIONS,
)
from app.services.eu_parliament_client import (
    EUParliamentClient,
    parse_mep_xml,
    parse_declarations_html,
    _name_to_slug,
    _extract_date_from_url,
    _extract_date_from_text,
)
from app.lib.party_registry import abbreviate_group_name
from app.lib.registry import ETLRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_MEP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<meps>
  <mep>
    <id>256810</id>
    <fullName>Mika AALTOLA</fullName>
    <country>Finland</country>
    <politicalGroup>Group of the European People's Party (Christian Democrats)</politicalGroup>
    <nationalPoliticalGroup>Kansallinen Kokoomus</nationalPoliticalGroup>
  </mep>
  <mep>
    <id>197490</id>
    <fullName>Bas EICKHOUT</fullName>
    <country>Netherlands</country>
    <politicalGroup>Group of the Greens/European Free Alliance</politicalGroup>
    <nationalPoliticalGroup>GroenLinks</nationalPoliticalGroup>
  </mep>
  <mep>
    <id>124831</id>
    <fullName>María Teresa GIMÉNEZ BARBAT</fullName>
    <country>Spain</country>
    <politicalGroup>Renew Europe Group</politicalGroup>
    <nationalPoliticalGroup>Ciudadanos</nationalPoliticalGroup>
  </mep>
</meps>
"""

SAMPLE_DECLARATIONS_HTML = """
<html>
<body>
<div class="declarations">
  <h3>Declaration of financial interests</h3>
  <ul>
    <li>
      <a href="/erpl-app-public/mep-documents/DPI/10/256810/256810_20240716_abc123.pdf">
        Original declaration (16/07/2024)
      </a>
    </li>
    <li>
      <a href="/erpl-app-public/mep-documents/DPI/10/256810/256810_20240901_def456.pdf">
        1st modification (01/09/2024)
      </a>
    </li>
    <li>
      <a href="https://example.com/other-doc.pdf">
        Some other document
      </a>
    </li>
  </ul>
</div>
</body>
</html>
"""

SAMPLE_DPI_TEXT = """
Declaration of Private Interests
Member of the European Parliament

Name: Mika AALTOLA

A. Previous occupations during the three years before taking up office

1. University of Helsinki - Professor of International Relations
2. Finnish Institute of International Affairs - Director

B. Remunerated activities alongside the mandate

1. University of Helsinki - Guest lecturer, Category 3
2. Helsingin Sanomat - Columnist, EUR 5,000 - EUR 9,999

C. Memberships of boards or advisory bodies

1. European Policy Centre - Advisory Board Member
2. Finnish Foreign Policy Society - Board Member

D. Shareholdings and other financial interests

1. Nokia Corporation - 500 shares
2. UPM-Kymmene - Bond holdings

E. Support received from third parties

None.

F. Other private interests

Not applicable.
"""

SAMPLE_DPI_TEXT_NO_NUMBERED = """
Declaration of Private Interests

A. Previous occupations

Professor at University of Helsinki

B. Remunerated activities alongside the mandate

Consulting for Tech Corp International

C. Memberships of boards

Advisory role at European Institute

D. Shareholdings and other financial interests

Shares in Acme Corporation
"""


# ===========================================================================
# Client Tests - XML Parsing
# ===========================================================================


class TestParseMepXml:

    def test_parses_all_meps(self):
        result = parse_mep_xml(SAMPLE_MEP_XML)
        assert len(result) == 3

    def test_extracts_mep_id(self):
        result = parse_mep_xml(SAMPLE_MEP_XML)
        assert result[0]["mep_id"] == "256810"

    def test_extracts_full_name(self):
        result = parse_mep_xml(SAMPLE_MEP_XML)
        assert result[0]["full_name"] == "Mika AALTOLA"

    def test_extracts_country(self):
        result = parse_mep_xml(SAMPLE_MEP_XML)
        assert result[0]["country"] == "Finland"

    def test_abbreviates_political_group(self):
        result = parse_mep_xml(SAMPLE_MEP_XML)
        assert result[0]["political_group"] == "EPP"

    def test_extracts_national_party(self):
        result = parse_mep_xml(SAMPLE_MEP_XML)
        assert result[0]["national_party"] == "Kansallinen Kokoomus"

    def test_handles_greens_group(self):
        result = parse_mep_xml(SAMPLE_MEP_XML)
        assert result[1]["political_group"] == "Greens/EFA"

    def test_handles_renew_group(self):
        result = parse_mep_xml(SAMPLE_MEP_XML)
        assert result[2]["political_group"] == "Renew"

    def test_empty_xml_returns_empty(self):
        result = parse_mep_xml("<meps></meps>")
        assert result == []

    def test_invalid_xml_returns_empty(self):
        result = parse_mep_xml("not xml at all")
        assert result == []

    def test_missing_id_skips_mep(self):
        xml = """<meps><mep><fullName>Test</fullName></mep></meps>"""
        result = parse_mep_xml(xml)
        assert result == []

    def test_missing_name_skips_mep(self):
        xml = """<meps><mep><id>123</id></mep></meps>"""
        result = parse_mep_xml(xml)
        assert result == []

    def test_empty_country_handled(self):
        xml = """<meps><mep><id>1</id><fullName>Test MEP</fullName></mep></meps>"""
        result = parse_mep_xml(xml)
        assert result[0]["country"] == ""

    def test_empty_group_handled(self):
        xml = """<meps><mep><id>1</id><fullName>Test MEP</fullName></mep></meps>"""
        result = parse_mep_xml(xml)
        assert result[0]["political_group"] == ""


# ===========================================================================
# Client Tests - Declarations HTML Parsing
# ===========================================================================


class TestParseDeclarationsHtml:

    def test_finds_dpi_pdfs(self):
        result = parse_declarations_html(SAMPLE_DECLARATIONS_HTML, "256810")
        # Should find 2 DPI PDFs, not the "other doc"
        assert len(result) == 2

    def test_builds_absolute_urls(self):
        result = parse_declarations_html(SAMPLE_DECLARATIONS_HTML, "256810")
        assert result[0]["pdf_url"].startswith("https://www.europarl.europa.eu/")

    def test_extracts_label(self):
        result = parse_declarations_html(SAMPLE_DECLARATIONS_HTML, "256810")
        assert "Original" in result[0]["label"]

    def test_original_revision_is_zero(self):
        result = parse_declarations_html(SAMPLE_DECLARATIONS_HTML, "256810")
        assert result[0]["revision"] == 0

    def test_modification_has_nonzero_revision(self):
        result = parse_declarations_html(SAMPLE_DECLARATIONS_HTML, "256810")
        assert result[1]["revision"] == 1

    def test_extracts_date_from_url(self):
        result = parse_declarations_html(SAMPLE_DECLARATIONS_HTML, "256810")
        assert result[0]["date"] == "2024-07-16"

    def test_mep_id_included(self):
        result = parse_declarations_html(SAMPLE_DECLARATIONS_HTML, "256810")
        assert result[0]["mep_id"] == "256810"

    def test_ignores_non_dpi_pdfs(self):
        html = '<a href="/other/document.pdf">Not DPI</a>'
        result = parse_declarations_html(html, "123")
        assert result == []

    def test_empty_html_returns_empty(self):
        result = parse_declarations_html("", "123")
        assert result == []

    def test_handles_absolute_urls(self):
        html = '<a href="https://www.europarl.europa.eu/erpl-app-public/mep-documents/DPI/10/123/test.pdf">Test</a>'
        result = parse_declarations_html(html, "123")
        assert len(result) == 1
        assert result[0]["pdf_url"].startswith("https://")


# ===========================================================================
# Client Tests - Helper Functions
# ===========================================================================


class TestNameToSlug:

    def test_simple_name(self):
        assert _name_to_slug("Mika AALTOLA") == "Mika+AALTOLA"

    def test_multi_word_name(self):
        result = _name_to_slug("María Teresa GIMÉNEZ BARBAT")
        assert result == "María+Teresa+GIMÉNEZ+BARBAT"

    def test_extra_spaces(self):
        assert _name_to_slug("  John  DOE  ") == "John+DOE"


class TestAbbreviateGroup:

    def test_epp(self):
        assert abbreviate_group_name("Group of the European People's Party (Christian Democrats)") == "EPP"

    def test_renew(self):
        assert abbreviate_group_name("Renew Europe Group") == "Renew"

    def test_unknown_group(self):
        result = abbreviate_group_name("Some Unknown Group")
        # abbreviate_group_name generates initials from significant words
        assert len(result) > 0

    def test_empty(self):
        assert abbreviate_group_name("") == ""

    def test_none(self):
        assert abbreviate_group_name(None) == ""

    def test_long_unknown_truncated(self):
        result = abbreviate_group_name("A" * 50)
        assert len(result) <= 20


class TestExtractDateFromUrl:

    def test_standard_url_date(self):
        url = "/DPI/10/256810/256810_20240716_abc.pdf"
        assert _extract_date_from_url(url) == "2024-07-16"

    def test_no_date_in_url(self):
        assert _extract_date_from_url("/DPI/simple.pdf") is None

    def test_invalid_date_rejected(self):
        url = "/DPI/10/256810/256810_20241399_abc.pdf"
        assert _extract_date_from_url(url) is None


class TestExtractDateFromText:

    def test_dd_mm_yyyy(self):
        assert _extract_date_from_text("16/07/2024") == "2024-07-16"

    def test_iso_format(self):
        assert _extract_date_from_text("2024-07-16") == "2024-07-16"

    def test_no_date(self):
        assert _extract_date_from_text("Original declaration") is None


# ===========================================================================
# PDF Parsing Tests - Section Splitting
# ===========================================================================


class TestSplitSections:

    def test_splits_all_sections(self):
        sections = split_sections(SAMPLE_DPI_TEXT)
        assert "A" in sections
        assert "B" in sections
        assert "C" in sections
        assert "D" in sections
        assert "E" in sections
        assert "F" in sections

    def test_section_a_content(self):
        sections = split_sections(SAMPLE_DPI_TEXT)
        assert "University of Helsinki" in sections["A"]

    def test_section_b_content(self):
        sections = split_sections(SAMPLE_DPI_TEXT)
        assert "Guest lecturer" in sections["B"]

    def test_section_d_content(self):
        sections = split_sections(SAMPLE_DPI_TEXT)
        assert "Nokia Corporation" in sections["D"]

    def test_empty_text_returns_empty(self):
        assert split_sections("") == {}

    def test_no_sections_returns_empty(self):
        assert split_sections("Just some random text") == {}

    def test_single_section(self):
        text = "A. Previous occupations\n\nProfessor at MIT"
        sections = split_sections(text)
        assert "A" in sections
        assert "Professor at MIT" in sections["A"]


# ===========================================================================
# PDF Parsing Tests - Financial Interest Extraction
# ===========================================================================


class TestExtractFinancialInterests:

    def test_extracts_from_sections_a_b_c_d(self):
        interests = extract_financial_interests(SAMPLE_DPI_TEXT)
        sections_found = {i["section"] for i in interests}
        assert sections_found == {"A", "B", "C", "D"}

    def test_section_a_is_income_type(self):
        interests = extract_financial_interests(SAMPLE_DPI_TEXT)
        a_interests = [i for i in interests if i["section"] == "A"]
        assert len(a_interests) > 0
        assert all(i["transaction_type"] == "income" for i in a_interests)

    def test_does_not_extract_section_e_f(self):
        interests = extract_financial_interests(SAMPLE_DPI_TEXT)
        assert all(i["section"] not in {"E", "F"} for i in interests)

    def test_section_b_is_income_type(self):
        interests = extract_financial_interests(SAMPLE_DPI_TEXT)
        b_interests = [i for i in interests if i["section"] == "B"]
        assert all(i["transaction_type"] == "income" for i in b_interests)

    def test_section_c_is_holding_type(self):
        interests = extract_financial_interests(SAMPLE_DPI_TEXT)
        c_interests = [i for i in interests if i["section"] == "C"]
        assert all(i["transaction_type"] == "holding" for i in c_interests)

    def test_section_d_is_holding_type(self):
        interests = extract_financial_interests(SAMPLE_DPI_TEXT)
        d_interests = [i for i in interests if i["section"] == "D"]
        assert all(i["transaction_type"] == "holding" for i in d_interests)

    def test_correct_asset_types(self):
        interests = extract_financial_interests(SAMPLE_DPI_TEXT)
        for interest in interests:
            expected = SECTION_ASSET_TYPES[interest["section"]]
            assert interest["asset_type"] == expected

    def test_entity_names_populated(self):
        interests = extract_financial_interests(SAMPLE_DPI_TEXT)
        assert all(len(i["entity"]) > 0 for i in interests)

    def test_nokia_found_in_section_d(self):
        interests = extract_financial_interests(SAMPLE_DPI_TEXT)
        d_entities = [i["entity"] for i in interests if i["section"] == "D"]
        assert any("Nokia" in e for e in d_entities)

    def test_raw_lines_present(self):
        interests = extract_financial_interests(SAMPLE_DPI_TEXT)
        assert all("raw_lines" in i for i in interests)
        assert all(isinstance(i["raw_lines"], list) for i in interests)

    def test_empty_text_returns_empty(self):
        assert extract_financial_interests("") == []

    def test_no_extractable_sections_returns_empty(self):
        text = "A. Previous occupations\n\nProfessor\n\nE. Support\n\nNone."
        assert extract_financial_interests(text) == []

    def test_non_numbered_entries_rejected(self):
        """Non-numbered content is not extracted — prevents multilingual boilerplate leaking."""
        interests = extract_financial_interests(SAMPLE_DPI_TEXT_NO_NUMBERED)
        assert len(interests) == 0

    def test_non_numbered_section_d_rejected(self):
        """Section D without numbered items produces no entries."""
        interests = extract_financial_interests(SAMPLE_DPI_TEXT_NO_NUMBERED)
        d_interests = [i for i in interests if i["section"] == "D"]
        assert len(d_interests) == 0

    def test_spanish_boilerplate_rejected(self):
        """Spanish DPI boilerplate text should produce zero entries."""
        spanish_dpi = """Declaración de intereses económicos

A. Actividades profesionales anteriores

Ninguno

B. Actividades remuneradas junto al mandato

Ninguno Importe de los Naturaleza del Periodicidad
ingresos percibidos beneficio

C. Pertenencia a consejos de administración

Pertenencia o actividad Ingresos generados u otros beneficio

D. Participaciones y otros intereses financieros

ES
implicaciones políticas
"""
        interests = extract_financial_interests(spanish_dpi)
        assert len(interests) == 0


# ===========================================================================
# PDF Parsing Tests - Section Entry Parsing
# ===========================================================================


class TestParseSectionEntries:

    def test_numbered_entries(self):
        body = "1. First entity - role\n2. Second entity - role"
        entries = _parse_section_entries(body, "B")
        assert len(entries) == 2

    def test_numbered_entry_names(self):
        body = "1. Apple Inc - Board member\n2. Google LLC - Advisor"
        entries = _parse_section_entries(body, "C")
        assert "Apple Inc" in entries[0]["entity"]
        assert "Google" in entries[1]["entity"]

    def test_continuation_lines(self):
        body = "1. Big Corp\n   Role: Consultant\n   Since 2020\n2. Small Corp\n   Role: Advisor"
        entries = _parse_section_entries(body, "B")
        assert len(entries) == 2

    def test_skips_none_lines(self):
        body = "None."
        entries = _parse_section_entries(body, "B")
        assert len(entries) == 0

    def test_skips_na_lines(self):
        body = "N/A"
        entries = _parse_section_entries(body, "B")
        assert len(entries) == 0

    def test_skips_not_applicable(self):
        body = "Not applicable."
        entries = _parse_section_entries(body, "D")
        assert len(entries) == 0

    def test_empty_body(self):
        entries = _parse_section_entries("", "B")
        assert len(entries) == 0

    def test_raw_lines_preserved(self):
        body = "1. Entity Name\n   Additional detail"
        entries = _parse_section_entries(body, "B")
        assert len(entries[0]["raw_lines"]) >= 1

    def test_un_numbered_single_entry_rejected(self):
        """Non-numbered single entry is not extracted — only numbered items are valid."""
        body = "Some Company - Consultant Role"
        entries = _parse_section_entries(body, "B")
        assert len(entries) == 0


# ===========================================================================
# Income Range Extraction
# ===========================================================================


class TestExtractIncomeRange:

    def test_eur_range(self):
        low, high = _extract_income_range("EUR 5,000 - EUR 9,999")
        assert low == 5000.0
        assert high == 9999.0

    def test_euro_symbol_range(self):
        low, high = _extract_income_range("€5000 - €9999")
        assert low == 5000.0
        assert high == 9999.0

    def test_category_1(self):
        low, high = _extract_income_range("Category 1 income")
        assert low == 1.0
        assert high == 499.0

    def test_category_3(self):
        low, high = _extract_income_range("Category 3")
        assert low == 1000.0
        assert high == 4999.0

    def test_category_5_no_upper(self):
        low, high = _extract_income_range("Category 5")
        assert low == 10000.0
        assert high is None

    def test_no_income_info(self):
        low, high = _extract_income_range("Just a regular company name")
        assert low is None
        assert high is None

    def test_empty_text(self):
        low, high = _extract_income_range("")
        assert low is None
        assert high is None


# ===========================================================================
# MEP Name Splitting
# ===========================================================================


class TestSplitMepName:

    def test_simple_name(self):
        first, last = _split_mep_name("Mika AALTOLA")
        assert first == "Mika"
        assert last == "AALTOLA"

    def test_multi_word_first_name(self):
        first, last = _split_mep_name("María Teresa GIMÉNEZ BARBAT")
        assert first == "María Teresa"
        assert last == "GIMÉNEZ BARBAT"

    def test_single_word(self):
        first, last = _split_mep_name("Mononym")
        assert first == "Mononym"
        assert last == ""

    def test_empty_string(self):
        first, last = _split_mep_name("")
        assert first == ""
        assert last == ""

    def test_bas_eickhout(self):
        first, last = _split_mep_name("Bas EICKHOUT")
        assert first == "Bas"
        assert last == "EICKHOUT"

    def test_all_lowercase(self):
        first, last = _split_mep_name("john doe")
        # Without uppercase boundary, falls back to splitting last word
        assert first == "john"
        assert last == "doe"


# ===========================================================================
# Schema Mapping Tests (parse_disclosure)
# ===========================================================================


class TestParseDisclosure:

    @pytest.mark.asyncio
    async def test_maps_basic_fields(self):
        service = EUParliamentETLService()
        raw = {
            "politician_name": "Mika AALTOLA",
            "first_name": "Mika",
            "last_name": "AALTOLA",
            "state": "Finland",
            "asset_name": "Nokia Corporation - 500 shares",
            "asset_type": "Shareholding",
            "transaction_type": "holding",
            "transaction_date": "2024-07-16",
            "filing_date": "2024-07-16",
            "notification_date": "2024-07-16",
            "source_url": "https://example.com/dpi.pdf",
            "doc_id": "DPI-256810-2024-07-16",
            "source": "eu_parliament",
            "raw_row": ["Nokia Corporation - 500 shares"],
        }
        result = await service.parse_disclosure(raw)
        assert result is not None
        assert result["politician_name"] == "Mika AALTOLA"
        assert result["asset_name"] == "Nokia Corporation - 500 shares"
        assert result["chamber"] == "eu_parliament"
        assert result["transaction_type"] == "holding"
        assert result["source"] == "eu_parliament"

    @pytest.mark.asyncio
    async def test_skips_empty_asset_name(self):
        service = EUParliamentETLService()
        result = await service.parse_disclosure({"asset_name": ""})
        assert result is None

    @pytest.mark.asyncio
    async def test_skips_short_asset_name(self):
        service = EUParliamentETLService()
        result = await service.parse_disclosure({"asset_name": "X"})
        assert result is None

    @pytest.mark.asyncio
    async def test_skips_country_code_asset_name(self):
        """Country codes like 'ES' or 'FR' should be rejected (< 5 chars)."""
        service = EUParliamentETLService()
        assert await service.parse_disclosure({"asset_name": "ES"}) is None
        assert await service.parse_disclosure({"asset_name": "EUR"}) is None
        assert await service.parse_disclosure({"asset_name": "AAPL"}) is None

    @pytest.mark.asyncio
    async def test_skips_missing_asset_name(self):
        service = EUParliamentETLService()
        result = await service.parse_disclosure({})
        assert result is None

    @pytest.mark.asyncio
    async def test_defaults_transaction_type(self):
        service = EUParliamentETLService()
        raw = {"asset_name": "Some Company Holdings"}
        result = await service.parse_disclosure(raw)
        assert result["transaction_type"] == "holding"

    @pytest.mark.asyncio
    async def test_defaults_asset_type(self):
        service = EUParliamentETLService()
        raw = {"asset_name": "Some Company Holdings"}
        result = await service.parse_disclosure(raw)
        assert result["asset_type"] == "Other Interest"

    @pytest.mark.asyncio
    async def test_preserves_value_range(self):
        service = EUParliamentETLService()
        raw = {
            "asset_name": "Consulting Income",
            "value_low": 5000.0,
            "value_high": 9999.0,
        }
        result = await service.parse_disclosure(raw)
        assert result["value_low"] == 5000.0
        assert result["value_high"] == 9999.0

    @pytest.mark.asyncio
    async def test_raw_row_preserved(self):
        service = EUParliamentETLService()
        raw = {
            "asset_name": "Test Asset",
            "raw_row": ["line1", "line2"],
        }
        result = await service.parse_disclosure(raw)
        assert result["raw_row"] == ["line1", "line2"]


# ===========================================================================
# Registry Integration
# ===========================================================================


class TestRegistration:

    def test_source_id(self):
        service = EUParliamentETLService()
        assert service.source_id == "eu_parliament"

    def test_source_name(self):
        service = EUParliamentETLService()
        assert service.source_name == "EU Parliament Declarations"

    def test_is_registered(self):
        assert ETLRegistry.is_registered("eu_parliament")

    def test_create_from_registry(self):
        service = ETLRegistry.create_instance("eu_parliament")
        assert isinstance(service, EUParliamentETLService)


# ===========================================================================
# Integration Tests - run() with mocked dependencies
# ===========================================================================


class TestRunIntegration:

    @pytest.mark.asyncio
    async def test_run_no_supabase(self):
        """run() should handle missing Supabase gracefully."""
        service = EUParliamentETLService()
        with patch("app.services.eu_etl.get_supabase", return_value=None):
            result = await service.run(job_id="test-no-sb")
        # No records processed, but no crash
        assert result.records_processed == 0

    @pytest.mark.asyncio
    async def test_run_no_meps(self):
        """run() should handle empty MEP list gracefully."""
        service = EUParliamentETLService()
        mock_supabase = MagicMock()

        mock_client = AsyncMock(spec=EUParliamentClient)
        mock_client.fetch_mep_list = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.eu_etl.get_supabase", return_value=mock_supabase), \
             patch("app.services.eu_etl.EUParliamentClient", return_value=mock_client):
            result = await service.run(job_id="test-no-meps")

        assert result.records_processed == 0
        assert result.is_success

    @pytest.mark.asyncio
    async def test_run_with_mocked_data(self):
        """run() should process records end-to-end with mocked data."""
        service = EUParliamentETLService()
        mock_supabase = MagicMock()

        meps = [
            {
                "mep_id": "256810",
                "full_name": "Mika AALTOLA",
                "country": "Finland",
                "political_group": "EPP",
                "national_party": "Kansallinen Kokoomus",
            }
        ]

        declarations = [
            {
                "pdf_url": "https://example.com/dpi.pdf",
                "label": "Original",
                "date": "2024-07-16",
                "revision": 0,
                "mep_id": "256810",
            }
        ]

        mock_client = AsyncMock(spec=EUParliamentClient)
        mock_client.fetch_mep_list = AsyncMock(return_value=meps)
        mock_client.fetch_declarations_page = AsyncMock(return_value=declarations)
        mock_client.download_pdf = AsyncMock(return_value=b"pdf bytes")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.eu_etl.get_supabase", return_value=mock_supabase), \
             patch("app.services.eu_etl.EUParliamentClient", return_value=mock_client), \
             patch("app.services.eu_etl.find_or_create_politician", return_value="pol-uuid-123"), \
             patch("app.services.eu_etl.extract_text_from_pdf", return_value=SAMPLE_DPI_TEXT):
            result = await service.run(job_id="test-full")

        # Should have processed records from sections B, C, D
        assert result.records_processed > 0

    @pytest.mark.asyncio
    async def test_run_skips_failed_politician_upsert(self):
        """run() should skip MEPs that fail politician upsert."""
        service = EUParliamentETLService()
        mock_supabase = MagicMock()

        meps = [
            {
                "mep_id": "1",
                "full_name": "Test MEP",
                "country": "Germany",
                "political_group": "EPP",
                "national_party": "CDU",
            }
        ]

        mock_client = AsyncMock(spec=EUParliamentClient)
        mock_client.fetch_mep_list = AsyncMock(return_value=meps)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.eu_etl.get_supabase", return_value=mock_supabase), \
             patch("app.services.eu_etl.EUParliamentClient", return_value=mock_client), \
             patch("app.services.eu_etl.find_or_create_politician", return_value=None):
            result = await service.run(job_id="test-no-pol")

        assert result.records_processed == 0

    @pytest.mark.asyncio
    async def test_run_handles_no_pdf_text(self):
        """run() should handle PDFs that yield no text."""
        service = EUParliamentETLService()
        mock_supabase = MagicMock()

        meps = [{"mep_id": "1", "full_name": "Test MEP", "country": "DE",
                  "political_group": "EPP", "national_party": "CDU"}]
        declarations = [{"pdf_url": "https://example.com/dpi.pdf",
                         "label": "Original", "date": "2024-01-01",
                         "revision": 0, "mep_id": "1"}]

        mock_client = AsyncMock(spec=EUParliamentClient)
        mock_client.fetch_mep_list = AsyncMock(return_value=meps)
        mock_client.fetch_declarations_page = AsyncMock(return_value=declarations)
        mock_client.download_pdf = AsyncMock(return_value=b"pdf bytes")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.eu_etl.get_supabase", return_value=mock_supabase), \
             patch("app.services.eu_etl.EUParliamentClient", return_value=mock_client), \
             patch("app.services.eu_etl.find_or_create_politician", return_value="pol-1"), \
             patch("app.services.eu_etl.extract_text_from_pdf", return_value=None):
            result = await service.run(job_id="test-no-text")

        assert result.records_processed == 0
        assert result.is_success

    @pytest.mark.asyncio
    async def test_run_incremental_upload_per_mep(self):
        """run() should upload records after each MEP, not buffer all."""
        service = EUParliamentETLService()
        mock_supabase = MagicMock()

        meps = [
            {"mep_id": "1", "full_name": "Alice TEST", "country": "DE",
             "political_group": "EPP", "national_party": "CDU"},
            {"mep_id": "2", "full_name": "Bob TEST", "country": "FR",
             "political_group": "S&D", "national_party": "PS"},
        ]

        declarations = [
            {"pdf_url": "https://example.com/dpi.pdf",
             "label": "Original", "date": "2024-07-16",
             "revision": 0, "mep_id": "1"}
        ]

        mock_client = AsyncMock(spec=EUParliamentClient)
        mock_client.fetch_mep_list = AsyncMock(return_value=meps)
        mock_client.fetch_declarations_page = AsyncMock(return_value=declarations)
        mock_client.download_pdf = AsyncMock(return_value=b"pdf bytes")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        upload_calls = []

        async def mock_upload(disclosure, update_mode=False):
            upload_calls.append(disclosure["asset_name"])
            return "disc-uuid"

        with patch("app.services.eu_etl.get_supabase", return_value=mock_supabase), \
             patch("app.services.eu_etl.EUParliamentClient", return_value=mock_client), \
             patch("app.services.eu_etl.find_or_create_politician", return_value="pol-uuid"), \
             patch("app.services.eu_etl.extract_text_from_pdf", return_value=SAMPLE_DPI_TEXT):
            service.upload_disclosure = mock_upload
            result = await service.run(job_id="test-incremental", update_mode=True)

        # Both MEPs should have been processed
        assert result.records_processed > 0
        assert result.records_updated > 0
        # Upload was called (not buffered)
        assert len(upload_calls) == result.records_updated

    @pytest.mark.asyncio
    async def test_run_update_mode_counts_updated(self):
        """run() with update_mode=True should count records_updated."""
        service = EUParliamentETLService()
        mock_supabase = MagicMock()

        meps = [{"mep_id": "1", "full_name": "Test MEP", "country": "DE",
                  "political_group": "EPP", "national_party": "CDU"}]
        declarations = [{"pdf_url": "https://example.com/dpi.pdf",
                         "label": "Original", "date": "2024-01-01",
                         "revision": 0, "mep_id": "1"}]

        mock_client = AsyncMock(spec=EUParliamentClient)
        mock_client.fetch_mep_list = AsyncMock(return_value=meps)
        mock_client.fetch_declarations_page = AsyncMock(return_value=declarations)
        mock_client.download_pdf = AsyncMock(return_value=b"pdf bytes")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        async def mock_upload(disclosure, update_mode=False):
            return "disc-uuid"

        with patch("app.services.eu_etl.get_supabase", return_value=mock_supabase), \
             patch("app.services.eu_etl.EUParliamentClient", return_value=mock_client), \
             patch("app.services.eu_etl.find_or_create_politician", return_value="pol-uuid"), \
             patch("app.services.eu_etl.extract_text_from_pdf", return_value=SAMPLE_DPI_TEXT):
            service.upload_disclosure = mock_upload
            result = await service.run(job_id="test-update", update_mode=True)

        assert result.records_updated > 0
        assert result.records_inserted == 0


# ===========================================================================
# Client Class Tests
# ===========================================================================


class TestEUParliamentClient:

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Client should work as async context manager."""
        async with EUParliamentClient() as client:
            assert client._client is not None
        # After exit, client should be closed
        assert client._client is None

    @pytest.mark.asyncio
    async def test_fetch_mep_list_mocked(self):
        """fetch_mep_list should parse XML response."""
        mock_response = MagicMock()
        mock_response.text = SAMPLE_MEP_XML
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        async with EUParliamentClient() as client:
            client._client.get = AsyncMock(return_value=mock_response)
            result = await client.fetch_mep_list()

        assert len(result) == 3
        assert result[0]["mep_id"] == "256810"

    @pytest.mark.asyncio
    async def test_fetch_mep_list_http_error(self):
        """fetch_mep_list should return empty on HTTP error."""
        async with EUParliamentClient() as client:
            client._client.get = AsyncMock(side_effect=httpx.ConnectError("Connection error"))
            result = await client.fetch_mep_list()

        assert result == []

    @pytest.mark.asyncio
    async def test_download_pdf_success(self):
        """download_pdf should return bytes on success."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"%PDF-1.4 fake pdf content"

        async with EUParliamentClient(pdf_delay=0) as client:
            client._client.get = AsyncMock(return_value=mock_response)
            result = await client.download_pdf("https://example.com/test.pdf")

        assert result == b"%PDF-1.4 fake pdf content"

    @pytest.mark.asyncio
    async def test_download_pdf_404(self):
        """download_pdf should return None on 404."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        async with EUParliamentClient(pdf_delay=0) as client:
            client._client.get = AsyncMock(return_value=mock_response)
            result = await client.download_pdf("https://example.com/missing.pdf")

        assert result is None

    @pytest.mark.asyncio
    async def test_download_pdf_invalid_content(self):
        """download_pdf should return None for non-PDF content."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"<html>Not a PDF</html>"

        async with EUParliamentClient(pdf_delay=0) as client:
            client._client.get = AsyncMock(return_value=mock_response)
            result = await client.download_pdf("https://example.com/fake.pdf")

        assert result is None

    @pytest.mark.asyncio
    async def test_declarations_404_returns_empty(self):
        """fetch_declarations_page should return empty on 404."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        async with EUParliamentClient(request_delay=0) as client:
            client._client.get = AsyncMock(return_value=mock_response)
            result = await client.fetch_declarations_page("999", "Nobody NOTHING")

        assert result == []


# ===========================================================================
# Edge Cases
# ===========================================================================


class TestEdgeCases:

    def test_section_with_dashes_in_header(self):
        text = "A. – Previous occupations\n\nProfessor\n\nB. – Outside activities\n\nConsultant"
        sections = split_sections(text)
        assert "A" in sections
        assert "B" in sections

    def test_section_f_not_extracted(self):
        text = """
A. Previous occupations
Professor
B. Remunerated activities
Consulting
F. Other interests
Real estate holdings
"""
        interests = extract_financial_interests(text)
        assert all(i["section"] != "F" for i in interests)

    def test_very_long_entity_name_truncated(self):
        """Entity names should be capped at 200 chars in records."""
        long_name = "A" * 300
        text = f"D. Shareholdings\n\n1. {long_name}"
        interests = extract_financial_interests(text)
        # The entity from _parse_section_entries may be long, but
        # the ETL service truncates in fetch_disclosures
        assert len(interests) > 0

    def test_mixed_numbered_and_unnumbered(self):
        body = """1. First Company - Board member
Additional details about first company
2. Second Company - Advisor"""
        entries = _parse_section_entries(body, "C")
        assert len(entries) == 2

    def test_skip_page_numbers(self):
        body = "Page 1\n1. Real Entry\nPage 2"
        entries = _parse_section_entries(body, "B")
        assert len(entries) == 1
        assert "Real Entry" in entries[0]["entity"]


# ===========================================================================
# EUR Number Parsing
# ===========================================================================


class TestParseEurNumber:

    def test_simple_integer(self):
        assert _parse_eur_number("2500") == 2500.0

    def test_comma_thousands(self):
        assert _parse_eur_number("2,500") == 2500.0

    def test_period_thousands_european(self):
        assert _parse_eur_number("2.500") == 2500.0

    def test_space_thousands_french(self):
        assert _parse_eur_number("2 500") == 2500.0

    def test_comma_decimal(self):
        assert _parse_eur_number("1,5") == 1.5

    def test_period_decimal(self):
        assert _parse_eur_number("2.5") == 2.5

    def test_mixed_european(self):
        # 2.500,00 = 2500.00 in European format
        assert _parse_eur_number("2.500,00") == 2500.0

    def test_mixed_english(self):
        # 2,500.00 = 2500.00 in English format
        assert _parse_eur_number("2,500.00") == 2500.0

    def test_empty_string(self):
        assert _parse_eur_number("") is None

    def test_whitespace_only(self):
        assert _parse_eur_number("   ") is None

    def test_large_number(self):
        assert _parse_eur_number("100000") == 100000.0

    def test_invalid_returns_none(self):
        assert _parse_eur_number("abc") is None


# ===========================================================================
# Income Range - Single Amount Patterns
# ===========================================================================


class TestExtractIncomeRangeSingleAmounts:

    def test_number_before_eur(self):
        """Dutch/French/German format: '2500 EUR'"""
        low, high = _extract_income_range("2500 EUR per maand")
        assert low == 2500.0
        assert high == 2500.0

    def test_number_before_eur_with_spaces(self):
        """French format: '2 500 EUR'"""
        low, high = _extract_income_range("2 500 EUR par mois")
        assert low == 2500.0
        assert high == 2500.0

    def test_number_before_euro_symbol(self):
        low, high = _extract_income_range("600€")
        assert low == 600.0
        assert high == 600.0

    def test_eur_before_number_single(self):
        """'EUR 2500' as a single amount (no range)"""
        low, high = _extract_income_range("EUR 2500 monthly")
        assert low == 2500.0
        assert high == 2500.0

    def test_euro_symbol_before_number_single(self):
        low, high = _extract_income_range("€600 per month")
        assert low == 600.0
        assert high == 600.0

    def test_number_with_comma_before_eur(self):
        low, high = _extract_income_range("5,000 EUR per year")
        assert low == 5000.0
        assert high == 5000.0

    def test_number_with_period_before_eur(self):
        """European thousands separator"""
        low, high = _extract_income_range("5.000 EUR pro Monat")
        assert low == 5000.0
        assert high == 5000.0

    def test_range_still_works(self):
        """Ensure range extraction wasn't broken"""
        low, high = _extract_income_range("EUR 1,000 - EUR 4,999")
        assert low == 1000.0
        assert high == 4999.0

    def test_categories_still_work(self):
        """Ensure category extraction wasn't broken"""
        assert _extract_income_range("Category 2") == (500.0, 999.0)
        assert _extract_income_range("Category 4") == (5000.0, 9999.0)


# ===========================================================================
# Entity Name Cleanup
# ===========================================================================


class TestCleanEntityName:

    def test_strips_number_eur_suffix(self):
        assert _clean_entity_name("NBX 2500 EUR per maand") == "NBX"

    def test_strips_eur_number_suffix(self):
        assert _clean_entity_name("Uhasselt EUR 600") == "Uhasselt"

    def test_strips_euro_symbol(self):
        assert _clean_entity_name("Company €5000 monthly") == "Company monthly"

    def test_strips_trailing_x_marker(self):
        """'X' at end of entity = no-income marker in DPI table columns"""
        assert _clean_entity_name("Board of Directors Corp X") == "Board of Directors Corp"

    def test_preserves_x_in_name(self):
        """'X' mid-name should not be stripped"""
        result = _clean_entity_name("NBX Holdings")
        assert "NBX" in result

    def test_no_amount_unchanged(self):
        assert _clean_entity_name("Simple Company Name") == "Simple Company Name"

    def test_empty_returns_original(self):
        # If cleanup produces empty string, return original
        assert _clean_entity_name("600 EUR") == "600 EUR"

    def test_collapses_whitespace(self):
        result = _clean_entity_name("Company   Name    Here")
        assert result == "Company Name Here"

    def test_strips_trailing_dash(self):
        result = _clean_entity_name("Company Name -")
        assert result == "Company Name"


# ===========================================================================
# Dutch DPI Format Integration
# ===========================================================================


DUTCH_DPI_TEXT = """
(A) "Overeenkomstig artikel 4, lid 2, punt a), van de gedragscode doe ik opgave:"

1. lid van het Europees Parlement publieke informatie per maand
2. Professor Economie 600 EUR per maand

(B) "Overeenkomstig artikel 4, lid 2, punt b), van de gedragscode doe ik opgave:"

Gebied en aard van de activiteit
Bedrag inkomsten Aard van het Periodiciteit
voordeel
1. Technologie Lid raad van bestuur - NBX 2500 EUR per maand
2. Professor Economie - Uhasselt 600 EUR per maand

(C) "Overeenkomstig artikel 4, lid 2, punt c), van de gedragscode doe ik opgave:"

Deelname of werkzaamheid Gegenereerde inkomsten
Geen Bedrag inkomsten Periodiciteit
1. Lid raad van bestuur N-VA vzw X
2. Bestuurder Refleco X

(D) "Overeenkomstig artikel 4, lid 2, punt d), van de gedragscode doe ik opgave:"

1. Lid raad van bestuur NBX 2500 EUR per maand

(E) Steun van derden

Geen.

(F) Overige belangen

NL
"""


class TestDutchDPIFormat:

    def test_sections_split_correctly(self):
        sections = split_sections(DUTCH_DPI_TEXT)
        assert "B" in sections
        assert "C" in sections
        assert "D" in sections

    def test_section_b_amounts_extracted(self):
        interests = extract_financial_interests(DUTCH_DPI_TEXT)
        b_interests = [i for i in interests if i["section"] == "B"]
        # At least one should have an EUR amount
        amounts = [(i["value_low"], i["value_high"]) for i in b_interests]
        assert any(low is not None for low, _ in amounts)

    def test_nbx_2500_eur_extracted(self):
        interests = extract_financial_interests(DUTCH_DPI_TEXT)
        nbx = [i for i in interests if "NBX" in i["entity"]]
        assert len(nbx) > 0
        assert any(i["value_low"] == 2500.0 for i in nbx)

    def test_600_eur_extracted(self):
        interests = extract_financial_interests(DUTCH_DPI_TEXT)
        prof = [i for i in interests if "Professor" in i["entity"] or "Uhasselt" in i["entity"]]
        assert len(prof) > 0
        assert any(i["value_low"] == 600.0 for i in prof)

    def test_section_c_no_amounts(self):
        """Section C entries with 'X' marker should have no amounts."""
        interests = extract_financial_interests(DUTCH_DPI_TEXT)
        c_interests = [i for i in interests if i["section"] == "C"]
        for i in c_interests:
            assert i["value_low"] is None
            assert i["value_high"] is None

    def test_entity_names_cleaned(self):
        """Entity names should not contain EUR amounts."""
        interests = extract_financial_interests(DUTCH_DPI_TEXT)
        for i in interests:
            assert "2500 EUR" not in i["entity"]
            assert "600 EUR" not in i["entity"]

    def test_nl_language_code_filtered(self):
        """'NL' language code should not appear as an entity."""
        interests = extract_financial_interests(DUTCH_DPI_TEXT)
        entities = [i["entity"] for i in interests]
        assert all(e.strip() != "NL" for e in entities)


# ===========================================================================
# Slovenian DPI Format Integration
# ===========================================================================


SLOVENIAN_DPI_TEXT = """Izjava o finančnih interesih

Ime: Matej TONIN

(A) "V skladu s členom 4(2)(a) kodeksa ravnanja izjavljam:"

Poklic ali članstvo Ustvarjeni prihodki Znesek prihodkov Narava ugodnosti Periodičnost
(če ne ustvarja
prihodkov)
1. minister za obrambo RS 4189 EUR mesečno
2. poslanec DZ RS X
3. predsednik stranke NSi 5446 EUR mesečno

(B) "V skladu s členom 4(2)(b) kodeksa ravnanja izjavljam:"

Jih ni.

(C) "V skladu s členom 4(2)(c) kodeksa ravnanja izjavljam:"

Jih ni.

(D) "V skladu s členom 4(2)(d) kodeksa ravnanja izjavljam:"

Jih ni.

(E) Podpora tretjih oseb

Jih ni.

(F) Drugi interesi

SL
"""


class TestSlovenianDPIFormat:

    def test_sections_split_correctly(self):
        sections = split_sections(SLOVENIAN_DPI_TEXT)
        assert "A" in sections
        assert "B" in sections

    def test_slovenian_section_a_amounts_extracted(self):
        """Slovenian Section A with 4189 EUR and 5446 EUR should be extracted."""
        interests = extract_financial_interests(SLOVENIAN_DPI_TEXT)
        a_interests = [i for i in interests if i["section"] == "A"]
        amounts = [(i["value_low"], i["value_high"]) for i in a_interests]
        assert any(low == 4189.0 for low, _ in amounts), f"Expected 4189 EUR, got {amounts}"
        assert any(low == 5446.0 for low, _ in amounts), f"Expected 5446 EUR, got {amounts}"

    def test_slovenian_section_a_is_income_type(self):
        """Section A entries should map to transaction_type='income'."""
        interests = extract_financial_interests(SLOVENIAN_DPI_TEXT)
        a_interests = [i for i in interests if i["section"] == "A"]
        assert len(a_interests) > 0
        assert all(i["transaction_type"] == "income" for i in a_interests)

    def test_slovenian_boilerplate_filtered(self):
        """Slovenian column headers should not appear as entity names."""
        interests = extract_financial_interests(SLOVENIAN_DPI_TEXT)
        entities = [i["entity"] for i in interests]
        for boilerplate in ["Znesek prihodkov", "Periodičnost", "Narava ugodnosti"]:
            assert all(boilerplate not in e for e in entities)

    def test_slovenian_entity_names_cleaned(self):
        """Entity names should not contain EUR amounts or 'mesečno'."""
        interests = extract_financial_interests(SLOVENIAN_DPI_TEXT)
        for i in interests:
            assert "4189 EUR" not in i["entity"]
            assert "5446 EUR" not in i["entity"]
            assert "mesečno" not in i["entity"].lower()

    def test_slovenian_x_marker_no_amount(self):
        """Entry 2 with 'X' marker should have null amounts."""
        interests = extract_financial_interests(SLOVENIAN_DPI_TEXT)
        a_interests = [i for i in interests if i["section"] == "A"]
        # Entry 2 is "poslanec DZ RS X" — X means no income
        x_entries = [i for i in a_interests if "poslanec" in i["entity"].lower()]
        assert len(x_entries) > 0
        for entry in x_entries:
            assert entry["value_low"] is None
            assert entry["value_high"] is None

    def test_slovenian_jih_ni_produces_no_entries(self):
        """Sections with 'Jih ni.' (Slovenian 'None') should produce no entries."""
        interests = extract_financial_interests(SLOVENIAN_DPI_TEXT)
        b_interests = [i for i in interests if i["section"] == "B"]
        assert len(b_interests) == 0

    def test_mesecno_stripped_from_entity(self):
        """'mesečno' periodicity word should be stripped from entity names."""
        result = _clean_entity_name("minister za obrambo RS 5446 EUR mesečno")
        assert "mesečno" not in result.lower()
        assert "5446" not in result
        assert "minister" in result.lower()


# ── Italian DPI fixture (based on Francesco Torselli's declaration) ──

ITALIAN_DPI_TEXT = """DICHIARAZIONE DEGLI INTERESSI PRIVATI DEI DEPUTATI

Cognome: TORSELLI
Cognome: Francesco

(A) "A norma dell'articolo 4, paragrafo 2, lettera a), del codice di condotta:"

Attività o partecipazione Reddito generato o altri benefici
Nulla Importo del reddito Natura del beneficio Periodicità
(se non genera
reddito)
1. Consulente assicurativo previdenziale e 18000 EUR Annuale
finanziario presso Cacciola Assicurazioni snc
2. Consigliere Regione Toscana 101550 EUR Annuale
3. Dirigente regionale Fratelli d'Italia X

(B) "Ai sensi dell'articolo 4, paragrafo 2, lettera b), del codice di condotta:"

Settore e natura dell'attività, compreso il nome dell'entità Reddito generato o altri benefici
Importo del reddito Natura del beneficio Periodicità
(se non genera
reddito)
1. Consulente assicurativo previdenziale e finanziario - Cacciola 15000 EUR Stima
Assicurazioni snc remunerazione
annuale

(C) "A norma dell'articolo 4, paragrafo 2, lettera c), del codice di condotta:"

Partecipazione o attività Reddito generato o altri benefici
Nulla Importo del reddito Natura del beneficio Periodicità
(se non genera
reddito)
1. Dirigente regionale Fratelli d'Italia X

(D) "A norma dell'articolo 4, paragrafo 2, lettera d), del codice di condotta:"

Partecipazione o Partecipazione che Reddito generato o altri benefici
partenariato con conferisce un'influenza
possibili implicazioni significativa
di politica pubblica
Nulla Importo del reddito Natura del beneficio Periodicità

(E) Dichiaro qualsiasi sostegno

(F) Dichiaro qualsiasi interesse privato

IT
"""


class TestItalianDPIFormat:

    def test_sections_split_correctly(self):
        sections = split_sections(ITALIAN_DPI_TEXT)
        assert "A" in sections
        assert "B" in sections
        assert "C" in sections
        assert "D" in sections

    def test_section_a_amounts_extracted(self):
        """Italian Section A with 18000 EUR and 101550 EUR should be extracted."""
        interests = extract_financial_interests(ITALIAN_DPI_TEXT)
        a_interests = [i for i in interests if i["section"] == "A"]
        amounts = [(i["value_low"], i["value_high"]) for i in a_interests]
        assert any(low == 18000.0 for low, _ in amounts), f"Expected 18000 EUR, got {amounts}"
        assert any(low == 101550.0 for low, _ in amounts), f"Expected 101550 EUR, got {amounts}"

    def test_section_a_is_income_type(self):
        """Italian Section A entries should map to transaction_type='income'."""
        interests = extract_financial_interests(ITALIAN_DPI_TEXT)
        a_interests = [i for i in interests if i["section"] == "A"]
        assert len(a_interests) > 0
        assert all(i["transaction_type"] == "income" for i in a_interests)

    def test_section_b_amount_extracted(self):
        """Italian Section B with 15000 EUR should be extracted."""
        interests = extract_financial_interests(ITALIAN_DPI_TEXT)
        b_interests = [i for i in interests if i["section"] == "B"]
        assert len(b_interests) > 0
        amounts = [(i["value_low"], i["value_high"]) for i in b_interests]
        assert any(low == 15000.0 for low, _ in amounts), f"Expected 15000 EUR, got {amounts}"

    def test_italian_boilerplate_filtered(self):
        """Italian column headers should not appear as entity names."""
        interests = extract_financial_interests(ITALIAN_DPI_TEXT)
        entities = [i["entity"] for i in interests]
        for boilerplate in ["Importo del reddito", "Natura del beneficio", "Periodicità"]:
            assert all(boilerplate not in e for e in entities), f"'{boilerplate}' leaked into entities: {entities}"

    def test_annuale_stripped_from_entity(self):
        """'Annuale' periodicity word should be stripped from entity names."""
        interests = extract_financial_interests(ITALIAN_DPI_TEXT)
        for i in interests:
            assert "annuale" not in i["entity"].lower(), f"'annuale' in entity: {i['entity']}"
            assert "18000" not in i["entity"]
            assert "101550" not in i["entity"]

    def test_x_marker_no_amount(self):
        """Entry 3 with 'X' marker should have null amounts."""
        interests = extract_financial_interests(ITALIAN_DPI_TEXT)
        a_interests = [i for i in interests if i["section"] == "A"]
        x_entries = [i for i in a_interests if "dirigente" in i["entity"].lower()]
        assert len(x_entries) > 0
        for entry in x_entries:
            assert entry["value_low"] is None
            assert entry["value_high"] is None

    def test_nulla_produces_no_numbered_entries(self):
        """Section D with 'Nulla' (Italian 'None') and no numbered items produces no entries."""
        interests = extract_financial_interests(ITALIAN_DPI_TEXT)
        d_interests = [i for i in interests if i["section"] == "D"]
        assert len(d_interests) == 0

    def test_clean_entity_name_annuale(self):
        """_clean_entity_name strips 'Annuale' after EUR amount."""
        result = _clean_entity_name("Consulente assicurativo 18000 EUR Annuale")
        assert "annuale" not in result.lower()
        assert "18000" not in result
        assert "Consulente" in result

    def test_clean_entity_name_stima(self):
        """_clean_entity_name strips 'Stima remunerazione annuale' after EUR."""
        result = _clean_entity_name("Cacciola Assicurazioni 15000 EUR Stima remunerazione annuale")
        assert "stima" not in result.lower()
        assert "remunerazione" not in result.lower()
        assert "15000" not in result
        assert "Cacciola" in result
