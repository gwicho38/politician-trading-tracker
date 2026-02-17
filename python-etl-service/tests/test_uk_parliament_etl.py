"""Tests for UK Parliament ETL Service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.uk_parliament_etl import (
    UKParliamentETLService,
    CATEGORY_MAP,
)
from app.lib.registry import ETLRegistry


# =============================================================================
# Fixtures
# =============================================================================

SAMPLE_MEMBERS_RESPONSE = {
    "items": [
        {
            "value": {
                "id": 4514,
                "nameDisplayAs": "Keir Starmer",
                "nameListAs": "Starmer, Keir",
                "latestParty": {
                    "name": "Labour",
                    "abbreviation": "Lab",
                },
                "latestHouseMembership": {
                    "membershipFrom": "Holborn and St Pancras",
                    "house": 1,
                },
                "gender": "M",
                "thumbnailUrl": "https://example.com/photo.jpg",
            }
        },
        {
            "value": {
                "id": 4880,
                "nameDisplayAs": "Rishi Sunak",
                "nameListAs": "Sunak, Rishi",
                "latestParty": {
                    "name": "Conservative",
                    "abbreviation": "Con",
                },
                "latestHouseMembership": {
                    "membershipFrom": "Richmond and Northallerton",
                    "house": 1,
                },
                "gender": "M",
                "thumbnailUrl": "https://example.com/photo2.jpg",
            }
        },
    ],
    "totalResults": 2,
    "resultContext": "Members",
    "skip": 0,
    "take": 20,
}

SAMPLE_INTERESTS_RESPONSE = {
    "items": [
        {
            "value": {
                "id": 14465,
                "summary": "Writing articles - Associated Newspapers Ltd",
                "registrationDate": "2026-02-02",
                "publishedDate": "2026-02-10",
                "updatedDates": [],
                "category": {
                    "id": 12,
                    "name": "Employment and earnings",
                    "number": "1",
                },
                "member": {
                    "id": 4514,
                    "nameDisplayAs": "Keir Starmer",
                    "party": "Labour",
                    "memberFrom": "Holborn and St Pancras",
                },
                "fields": [
                    {"name": "JobTitle", "value": "Writing articles"},
                    {
                        "name": "PayerName",
                        "value": "Associated Newspapers Ltd",
                    },
                ],
                "childInterests": [
                    {
                        "id": 14466,
                        "summary": "Payment of GBP 850",
                        "registrationDate": "2026-02-02",
                        "publishedDate": "2026-02-10",
                        "fields": [
                            {"name": "ReceivedDate", "value": "2026-01-29"},
                            {
                                "name": "Value",
                                "value": "850.00",
                                "typeInfo": {"currencyCode": "GBP"},
                            },
                            {"name": "HoursWorked", "value": "4.00"},
                            {"name": "PaymentType", "value": "Monetary"},
                        ],
                        "rectified": False,
                    }
                ],
                "rectified": False,
            }
        },
        {
            "value": {
                "id": 5000,
                "summary": "Acme Holdings Ltd - Software and Technology",
                "registrationDate": "2025-08-01",
                "publishedDate": "2025-08-15",
                "updatedDates": [],
                "category": {
                    "id": 8,
                    "name": "Shareholdings",
                    "number": "7",
                },
                "member": {
                    "id": 4514,
                    "nameDisplayAs": "Keir Starmer",
                    "party": "Labour",
                    "memberFrom": "Holborn and St Pancras",
                },
                "fields": [
                    {
                        "name": "OrganisationName",
                        "value": "Acme Holdings Ltd",
                    },
                    {
                        "name": "OrganisationDescription",
                        "value": "Software and Technology",
                    },
                    {
                        "name": "ShareholdingThreshold",
                        "value": "(i) over 15% of issued share capital",
                    },
                ],
                "childInterests": [],
                "rectified": False,
            }
        },
    ],
    "totalResults": 2,
    "skip": 0,
    "take": 20,
}

SAMPLE_MP = {
    "id": 4514,
    "name": "Keir Starmer",
    "first_name": "Keir",
    "last_name": "Starmer",
    "party": "Labour",
    "constituency": "Holborn and St Pancras",
}


def _mock_httpx_client(responses):
    """Helper to create a mock httpx.AsyncClient with given responses."""
    if not isinstance(responses, list):
        responses = [responses]

    mock_responses = []
    for resp_data in responses:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = resp_data
        mock_resp.raise_for_status = MagicMock()
        mock_responses.append(mock_resp)

    mock_client = AsyncMock()
    if len(mock_responses) == 1:
        mock_client.get = AsyncMock(return_value=mock_responses[0])
    else:
        mock_client.get = AsyncMock(side_effect=mock_responses)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


# =============================================================================
# Test: Politician Integration
# =============================================================================


class TestPoliticianIntegration:
    """Test politician.py integration for UK Parliament."""

    def test_chamber_role_map_includes_uk_parliament(self):
        """uk_parliament chamber maps to Member of Parliament role."""
        from app.lib.politician import find_or_create_politician

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "test-uuid"}
        ]

        result = find_or_create_politician(
            mock_supabase,
            first_name="Keir",
            last_name="Starmer",
            chamber="uk_parliament",
            bioguide_id="4514",
        )
        assert result == "test-uuid"


# =============================================================================
# Test: Category Mapping
# =============================================================================


class TestCategoryMapping:
    """Test UK interest category to transaction_type mapping."""

    def test_employment_maps_to_income(self):
        assert CATEGORY_MAP[12] == "income"

    def test_ad_hoc_payments_maps_to_income(self):
        assert CATEGORY_MAP[1] == "income"

    def test_ongoing_employment_maps_to_income(self):
        assert CATEGORY_MAP[2] == "income"

    def test_shareholdings_maps_to_holding(self):
        assert CATEGORY_MAP[8] == "holding"

    def test_property_maps_to_holding(self):
        assert CATEGORY_MAP[7] == "holding"

    def test_donations_maps_to_gift(self):
        assert CATEGORY_MAP[3] == "gift"

    def test_gifts_uk_maps_to_gift(self):
        assert CATEGORY_MAP[4] == "gift"

    def test_overseas_visits_maps_to_gift(self):
        assert CATEGORY_MAP[5] == "gift"

    def test_gifts_foreign_maps_to_gift(self):
        assert CATEGORY_MAP[6] == "gift"

    def test_miscellaneous_maps_to_other(self):
        assert CATEGORY_MAP[9] == "other"

    def test_family_employed_maps_to_other(self):
        assert CATEGORY_MAP[10] == "other"

    def test_family_lobbying_maps_to_other(self):
        assert CATEGORY_MAP[11] == "other"

    def test_all_twelve_entries_covered(self):
        """10 main categories + 2 subcategories = 12 entries."""
        assert len(CATEGORY_MAP) == 12


# =============================================================================
# Test: Registration
# =============================================================================


class TestRegistration:
    """Test ETL registry integration."""

    def setup_method(self):
        # Re-register in case test_registry.py cleared the registry
        if not ETLRegistry.is_registered("uk_parliament"):
            ETLRegistry.register(UKParliamentETLService)

    def test_service_is_registered(self):
        assert ETLRegistry.is_registered("uk_parliament")

    def test_service_source_name(self):
        service = ETLRegistry.create_instance("uk_parliament")
        assert service.source_name == "UK Parliament"

    def test_service_is_base_etl_subclass(self):
        from app.lib.base_etl import BaseETLService

        service = ETLRegistry.create_instance("uk_parliament")
        assert isinstance(service, BaseETLService)


# =============================================================================
# Test: _fetch_mp_list()
# =============================================================================


class TestFetchMPList:
    """Test _fetch_mp_list() MP fetching and pagination."""

    @pytest.mark.asyncio
    async def test_fetches_commons_members(self):
        service = UKParliamentETLService()
        mock_client = _mock_httpx_client(SAMPLE_MEMBERS_RESPONSE)

        with patch(
            "app.services.uk_parliament_etl.httpx.AsyncClient",
            return_value=mock_client,
        ):
            mps = await service._fetch_mp_list()

        assert len(mps) == 2
        assert mps[0]["id"] == 4514
        assert mps[0]["name"] == "Keir Starmer"
        assert mps[0]["party"] == "Labour"
        assert mps[0]["constituency"] == "Holborn and St Pancras"

    @pytest.mark.asyncio
    async def test_extracts_first_and_last_name(self):
        service = UKParliamentETLService()
        mock_client = _mock_httpx_client(SAMPLE_MEMBERS_RESPONSE)

        with patch(
            "app.services.uk_parliament_etl.httpx.AsyncClient",
            return_value=mock_client,
        ):
            mps = await service._fetch_mp_list()

        assert mps[0]["first_name"] == "Keir"
        assert mps[0]["last_name"] == "Starmer"
        assert mps[1]["first_name"] == "Rishi"
        assert mps[1]["last_name"] == "Sunak"

    @pytest.mark.asyncio
    async def test_paginates_when_more_results(self):
        service = UKParliamentETLService()
        page1 = {
            "items": [
                {
                    "value": {
                        "id": 1,
                        "nameDisplayAs": "MP One",
                        "nameListAs": "One, MP",
                        "latestParty": {"name": "Labour"},
                        "latestHouseMembership": {
                            "membershipFrom": "Somewhere",
                        },
                    }
                }
            ],
            "totalResults": 2,
            "skip": 0,
            "take": 1,
        }
        page2 = {
            "items": [
                {
                    "value": {
                        "id": 2,
                        "nameDisplayAs": "MP Two",
                        "nameListAs": "Two, MP",
                        "latestParty": {"name": "Conservative"},
                        "latestHouseMembership": {
                            "membershipFrom": "Elsewhere",
                        },
                    }
                }
            ],
            "totalResults": 2,
            "skip": 1,
            "take": 1,
        }

        mock_client = _mock_httpx_client([page1, page2])

        with patch(
            "app.services.uk_parliament_etl.httpx.AsyncClient",
            return_value=mock_client,
        ):
            mps = await service._fetch_mp_list()

        assert len(mps) == 2
        assert mps[0]["id"] == 1
        assert mps[1]["id"] == 2

    @pytest.mark.asyncio
    async def test_respects_limit(self):
        service = UKParliamentETLService()
        mock_client = _mock_httpx_client(SAMPLE_MEMBERS_RESPONSE)

        with patch(
            "app.services.uk_parliament_etl.httpx.AsyncClient",
            return_value=mock_client,
        ):
            mps = await service._fetch_mp_list(limit=1)

        assert len(mps) == 1

    @pytest.mark.asyncio
    async def test_handles_empty_response(self):
        service = UKParliamentETLService()
        empty = {"items": [], "totalResults": 0, "skip": 0, "take": 20}
        mock_client = _mock_httpx_client(empty)

        with patch(
            "app.services.uk_parliament_etl.httpx.AsyncClient",
            return_value=mock_client,
        ):
            mps = await service._fetch_mp_list()

        assert len(mps) == 0


# =============================================================================
# Test: _fetch_mp_interests()
# =============================================================================


class TestFetchMPInterests:
    """Test _fetch_mp_interests() interest fetching."""

    @pytest.mark.asyncio
    async def test_fetches_interests_for_mp(self):
        service = UKParliamentETLService()
        mock_client = _mock_httpx_client(SAMPLE_INTERESTS_RESPONSE)

        with patch(
            "app.services.uk_parliament_etl.httpx.AsyncClient",
            return_value=mock_client,
        ):
            interests = await service._fetch_mp_interests(4514)

        assert len(interests) == 2
        assert interests[0]["id"] == 14465
        assert interests[1]["id"] == 5000

    @pytest.mark.asyncio
    async def test_includes_child_interests(self):
        service = UKParliamentETLService()
        mock_client = _mock_httpx_client(SAMPLE_INTERESTS_RESPONSE)

        with patch(
            "app.services.uk_parliament_etl.httpx.AsyncClient",
            return_value=mock_client,
        ):
            interests = await service._fetch_mp_interests(4514)

        assert len(interests[0].get("childInterests", [])) == 1
        child = interests[0]["childInterests"][0]
        assert child["id"] == 14466

    @pytest.mark.asyncio
    async def test_passes_expand_child_interests_param(self):
        service = UKParliamentETLService()
        empty = {"items": [], "totalResults": 0, "skip": 0, "take": 20}
        mock_client = _mock_httpx_client(empty)

        with patch(
            "app.services.uk_parliament_etl.httpx.AsyncClient",
            return_value=mock_client,
        ):
            await service._fetch_mp_interests(4514)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params", {})
        assert params.get("ExpandChildInterests") is True
        assert params.get("MemberId") == 4514

    @pytest.mark.asyncio
    async def test_handles_empty_interests(self):
        service = UKParliamentETLService()
        empty = {"items": [], "totalResults": 0, "skip": 0, "take": 20}
        mock_client = _mock_httpx_client(empty)

        with patch(
            "app.services.uk_parliament_etl.httpx.AsyncClient",
            return_value=mock_client,
        ):
            interests = await service._fetch_mp_interests(9999)

        assert len(interests) == 0


# =============================================================================
# Test: _parse_interest()
# =============================================================================


class TestParseInterest:
    """Test _parse_interest() disclosure mapping."""

    def setup_method(self):
        self.service = UKParliamentETLService()
        self.mp = SAMPLE_MP.copy()

    def test_parent_interest_without_children_produces_one_record(self):
        """Shareholding (no children) produces exactly one record."""
        interest = SAMPLE_INTERESTS_RESPONSE["items"][1]["value"]
        records = self.service._parse_interest(interest, self.mp)
        assert len(records) == 1

    def test_parent_with_children_produces_child_records(self):
        """Employment with 1 child payment produces 1 child record."""
        interest = SAMPLE_INTERESTS_RESPONSE["items"][0]["value"]
        records = self.service._parse_interest(interest, self.mp)
        assert len(records) == 1  # 1 child interest

    def test_shareholding_maps_to_holding(self):
        interest = SAMPLE_INTERESTS_RESPONSE["items"][1]["value"]
        records = self.service._parse_interest(interest, self.mp)
        assert records[0]["transaction_type"] == "holding"

    def test_employment_child_maps_to_income(self):
        interest = SAMPLE_INTERESTS_RESPONSE["items"][0]["value"]
        records = self.service._parse_interest(interest, self.mp)
        assert records[0]["transaction_type"] == "income"

    def test_extracts_asset_name_from_summary(self):
        interest = SAMPLE_INTERESTS_RESPONSE["items"][1]["value"]
        records = self.service._parse_interest(interest, self.mp)
        assert "Acme Holdings Ltd" in records[0]["asset_name"]

    def test_extracts_gbp_amount_from_child(self):
        interest = SAMPLE_INTERESTS_RESPONSE["items"][0]["value"]
        records = self.service._parse_interest(interest, self.mp)
        assert records[0]["value_low"] == 850.0
        assert records[0]["value_high"] == 850.0

    def test_sets_politician_fields(self):
        interest = SAMPLE_INTERESTS_RESPONSE["items"][1]["value"]
        records = self.service._parse_interest(interest, self.mp)
        r = records[0]
        assert r["politician_name"] == "Keir Starmer"
        assert r["first_name"] == "Keir"
        assert r["last_name"] == "Starmer"
        assert r["chamber"] == "uk_parliament"
        assert r["party"] == "Labour"
        assert r["state"] == "United Kingdom"
        assert r["district"] == "Holborn and St Pancras"

    def test_sets_source_fields(self):
        interest = SAMPLE_INTERESTS_RESPONSE["items"][1]["value"]
        records = self.service._parse_interest(interest, self.mp)
        r = records[0]
        assert r["source"] == "uk_parliament"
        assert r["doc_id"] == "5000"

    def test_sets_dates(self):
        interest = SAMPLE_INTERESTS_RESPONSE["items"][1]["value"]
        records = self.service._parse_interest(interest, self.mp)
        r = records[0]
        assert r["filing_date"] == "2025-08-01"
        assert r["transaction_date"] == "2025-08-01"

    def test_child_uses_received_date(self):
        interest = SAMPLE_INTERESTS_RESPONSE["items"][0]["value"]
        records = self.service._parse_interest(interest, self.mp)
        assert records[0]["transaction_date"] == "2026-01-29"

    def test_truncates_long_asset_name(self):
        interest = {
            "id": 999,
            "summary": "A" * 300,
            "registrationDate": "2025-01-01",
            "publishedDate": "2025-01-15",
            "category": {"id": 9, "name": "Miscellaneous"},
            "fields": [],
            "childInterests": [],
        }
        records = self.service._parse_interest(interest, self.mp)
        assert len(records[0]["asset_name"]) <= 200

    def test_stores_bioguide_id(self):
        interest = SAMPLE_INTERESTS_RESPONSE["items"][1]["value"]
        records = self.service._parse_interest(interest, self.mp)
        assert records[0]["bioguide_id"] == "4514"

    def test_unknown_category_defaults_to_other(self):
        interest = {
            "id": 888,
            "summary": "Something unknown",
            "registrationDate": "2025-01-01",
            "publishedDate": "2025-01-15",
            "category": {"id": 999, "name": "New Category"},
            "fields": [],
            "childInterests": [],
        }
        records = self.service._parse_interest(interest, self.mp)
        assert records[0]["transaction_type"] == "other"

    def test_child_doc_id_uses_child_id(self):
        interest = SAMPLE_INTERESTS_RESPONSE["items"][0]["value"]
        records = self.service._parse_interest(interest, self.mp)
        assert records[0]["doc_id"] == "14466"

    def test_child_raw_data_includes_parent_id(self):
        interest = SAMPLE_INTERESTS_RESPONSE["items"][0]["value"]
        records = self.service._parse_interest(interest, self.mp)
        assert records[0]["raw_data"]["parent_interest_id"] == 14465

    def test_no_amount_when_fields_have_no_value(self):
        interest = {
            "id": 777,
            "summary": "Some position",
            "registrationDate": "2025-01-01",
            "publishedDate": "2025-01-15",
            "category": {"id": 10, "name": "Family members employed"},
            "fields": [
                {"name": "SomethingElse", "value": "text"},
            ],
            "childInterests": [],
        }
        records = self.service._parse_interest(interest, self.mp)
        assert records[0]["value_low"] is None
        assert records[0]["value_high"] is None

    def test_multiple_children_produce_multiple_records(self):
        interest = {
            "id": 100,
            "summary": "Consulting - BigCorp",
            "registrationDate": "2025-03-01",
            "publishedDate": "2025-03-10",
            "category": {"id": 2, "name": "Ongoing paid employment"},
            "fields": [],
            "childInterests": [
                {
                    "id": 101,
                    "summary": "Payment 1",
                    "fields": [
                        {"name": "ReceivedDate", "value": "2025-01-15"},
                        {
                            "name": "Value",
                            "value": "1000.00",
                            "typeInfo": {"currencyCode": "GBP"},
                        },
                    ],
                },
                {
                    "id": 102,
                    "summary": "Payment 2",
                    "fields": [
                        {"name": "ReceivedDate", "value": "2025-02-15"},
                        {
                            "name": "Value",
                            "value": "2000.00",
                            "typeInfo": {"currencyCode": "GBP"},
                        },
                    ],
                },
            ],
        }
        records = self.service._parse_interest(interest, self.mp)
        assert len(records) == 2
        assert records[0]["value_low"] == 1000.0
        assert records[1]["value_low"] == 2000.0
        assert records[0]["transaction_date"] == "2025-01-15"
        assert records[1]["transaction_date"] == "2025-02-15"


# =============================================================================
# Test: _extract_amount() and _extract_field()
# =============================================================================


class TestFieldExtraction:
    """Test static helper methods."""

    def test_extract_amount_gbp(self):
        fields = [
            {
                "name": "Value",
                "value": "1500.50",
                "typeInfo": {"currencyCode": "GBP"},
            }
        ]
        assert UKParliamentETLService._extract_amount(fields) == 1500.50

    def test_extract_amount_by_name_fallback(self):
        fields = [{"name": "Value", "value": "250.00"}]
        assert UKParliamentETLService._extract_amount(fields) == 250.0

    def test_extract_amount_no_value(self):
        fields = [{"name": "SomethingElse", "value": "text"}]
        assert UKParliamentETLService._extract_amount(fields) is None

    def test_extract_amount_invalid_value(self):
        fields = [
            {
                "name": "Value",
                "value": "not-a-number",
                "typeInfo": {"currencyCode": "GBP"},
            }
        ]
        assert UKParliamentETLService._extract_amount(fields) is None

    def test_extract_amount_empty_fields(self):
        assert UKParliamentETLService._extract_amount([]) is None

    def test_extract_field_found(self):
        fields = [
            {"name": "ReceivedDate", "value": "2025-06-01"},
            {"name": "Value", "value": "100"},
        ]
        assert (
            UKParliamentETLService._extract_field(fields, "ReceivedDate")
            == "2025-06-01"
        )

    def test_extract_field_not_found(self):
        fields = [{"name": "Other", "value": "x"}]
        assert (
            UKParliamentETLService._extract_field(fields, "ReceivedDate")
            is None
        )

    def test_extract_field_empty(self):
        assert (
            UKParliamentETLService._extract_field([], "ReceivedDate") is None
        )


# =============================================================================
# Test: parse_disclosure()
# =============================================================================


class TestParseDisclosure:
    """Test parse_disclosure() validation."""

    @pytest.mark.asyncio
    async def test_passes_through_valid_record(self):
        service = UKParliamentETLService()
        raw = {
            "asset_name": "Acme Corp",
            "transaction_type": "holding",
            "politician_name": "Test MP",
        }
        result = await service.parse_disclosure(raw)
        assert result is not None
        assert result["asset_name"] == "Acme Corp"

    @pytest.mark.asyncio
    async def test_skips_empty_asset_name(self):
        service = UKParliamentETLService()
        raw = {"asset_name": "", "transaction_type": "other"}
        result = await service.parse_disclosure(raw)
        assert result is None

    @pytest.mark.asyncio
    async def test_skips_missing_asset_name(self):
        service = UKParliamentETLService()
        raw = {"transaction_type": "other"}
        result = await service.parse_disclosure(raw)
        assert result is None


# =============================================================================
# Test: run() with incremental per-MP upload
# =============================================================================


class TestRunIncremental:
    """Test run() with incremental per-MP upload."""

    @pytest.mark.asyncio
    async def test_uploads_per_mp(self):
        service = UKParliamentETLService()

        mp_list = [
            {
                "id": 1,
                "name": "MP One",
                "first_name": "MP",
                "last_name": "One",
                "party": "Lab",
                "constituency": "A",
            },
            {
                "id": 2,
                "name": "MP Two",
                "first_name": "MP",
                "last_name": "Two",
                "party": "Con",
                "constituency": "B",
            },
        ]

        interests_mp1 = [SAMPLE_INTERESTS_RESPONSE["items"][1]["value"]]
        interests_mp2 = [SAMPLE_INTERESTS_RESPONSE["items"][0]["value"]]

        with (
            patch.object(
                service,
                "_fetch_mp_list",
                new_callable=AsyncMock,
                return_value=mp_list,
            ),
            patch.object(
                service,
                "_fetch_mp_interests",
                new_callable=AsyncMock,
                side_effect=[interests_mp1, interests_mp2],
            ),
            patch.object(
                service,
                "upload_disclosure",
                new_callable=AsyncMock,
                return_value="disc-id",
            ),
            patch.object(service, "on_start", new_callable=AsyncMock),
            patch.object(service, "on_complete", new_callable=AsyncMock),
            patch(
                "app.services.uk_parliament_etl.get_supabase"
            ) as mock_sb,
            patch(
                "app.services.uk_parliament_etl.find_or_create_politician",
                return_value="pol-uuid",
            ),
        ):
            mock_sb.return_value = MagicMock()
            result = await service.run("test-job", update_mode=True)

        # 1 shareholding + 1 child payment = 2 records
        assert result.records_updated >= 2
        assert result.records_failed == 0

    @pytest.mark.asyncio
    async def test_handles_mp_fetch_error(self):
        service = UKParliamentETLService()

        mp_list = [
            {
                "id": 1,
                "name": "Bad MP",
                "first_name": "Bad",
                "last_name": "MP",
                "party": "Lab",
                "constituency": "X",
            },
        ]

        with (
            patch.object(
                service,
                "_fetch_mp_list",
                new_callable=AsyncMock,
                return_value=mp_list,
            ),
            patch.object(
                service,
                "_fetch_mp_interests",
                new_callable=AsyncMock,
                side_effect=Exception("API down"),
            ),
            patch.object(service, "on_start", new_callable=AsyncMock),
            patch.object(service, "on_complete", new_callable=AsyncMock),
            patch(
                "app.services.uk_parliament_etl.get_supabase"
            ) as mock_sb,
        ):
            mock_sb.return_value = MagicMock()
            result = await service.run("test-job")

        assert result.records_failed == 1
        assert "API down" in result.errors[0]

    @pytest.mark.asyncio
    async def test_updates_job_status_progress(self):
        service = UKParliamentETLService()

        mp_list = [
            {
                "id": 1,
                "name": "MP One",
                "first_name": "MP",
                "last_name": "One",
                "party": "Lab",
                "constituency": "A",
            },
        ]

        with (
            patch.object(
                service,
                "_fetch_mp_list",
                new_callable=AsyncMock,
                return_value=mp_list,
            ),
            patch.object(
                service,
                "_fetch_mp_interests",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch.object(service, "on_start", new_callable=AsyncMock),
            patch.object(service, "on_complete", new_callable=AsyncMock),
            patch(
                "app.services.uk_parliament_etl.get_supabase"
            ) as mock_sb,
            patch(
                "app.services.uk_parliament_etl.find_or_create_politician",
                return_value="pol-uuid",
            ),
        ):
            mock_sb.return_value = MagicMock()
            await service.run("test-job")

        status = service.get_job_status("test-job")
        assert status is not None
        assert status.progress == 1
        assert status.total == 1

    @pytest.mark.asyncio
    async def test_handles_no_mps(self):
        service = UKParliamentETLService()

        with (
            patch.object(
                service,
                "_fetch_mp_list",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch.object(service, "on_start", new_callable=AsyncMock),
            patch(
                "app.services.uk_parliament_etl.get_supabase"
            ) as mock_sb,
        ):
            mock_sb.return_value = MagicMock()
            result = await service.run("test-job")

        assert result.records_processed == 0
        assert len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_handles_supabase_unavailable(self):
        service = UKParliamentETLService()

        with (
            patch.object(service, "on_start", new_callable=AsyncMock),
            patch(
                "app.services.uk_parliament_etl.get_supabase",
                return_value=None,
            ),
        ):
            result = await service.run("test-job")

        assert len(result.errors) > 0
        assert "Supabase" in result.errors[0]

    @pytest.mark.asyncio
    async def test_handles_politician_creation_failure(self):
        service = UKParliamentETLService()

        mp_list = [
            {
                "id": 1,
                "name": "Bad MP",
                "first_name": "Bad",
                "last_name": "MP",
                "party": "Lab",
                "constituency": "X",
            },
        ]

        with (
            patch.object(
                service,
                "_fetch_mp_list",
                new_callable=AsyncMock,
                return_value=mp_list,
            ),
            patch.object(
                service,
                "_fetch_mp_interests",
                new_callable=AsyncMock,
                return_value=[SAMPLE_INTERESTS_RESPONSE["items"][1]["value"]],
            ),
            patch.object(service, "on_start", new_callable=AsyncMock),
            patch.object(service, "on_complete", new_callable=AsyncMock),
            patch(
                "app.services.uk_parliament_etl.get_supabase"
            ) as mock_sb,
            patch(
                "app.services.uk_parliament_etl.find_or_create_politician",
                return_value=None,
            ),
        ):
            mock_sb.return_value = MagicMock()
            result = await service.run("test-job")

        assert result.records_failed == 1
        assert "politician" in result.errors[0].lower()

    @pytest.mark.asyncio
    async def test_job_status_completed_on_success(self):
        service = UKParliamentETLService()

        with (
            patch.object(
                service,
                "_fetch_mp_list",
                new_callable=AsyncMock,
                return_value=[SAMPLE_MP],
            ),
            patch.object(
                service,
                "_fetch_mp_interests",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch.object(service, "on_start", new_callable=AsyncMock),
            patch.object(service, "on_complete", new_callable=AsyncMock),
            patch(
                "app.services.uk_parliament_etl.get_supabase"
            ) as mock_sb,
            patch(
                "app.services.uk_parliament_etl.find_or_create_politician",
                return_value="pol-uuid",
            ),
        ):
            mock_sb.return_value = MagicMock()
            await service.run("test-job")

        status = service.get_job_status("test-job")
        assert status.status == "completed"
        assert "Completed" in status.message
