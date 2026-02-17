# UK Parliament ETL Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a UK Parliament ETL service that fetches all 10 categories of MP financial interests from the official Register of Interests API and loads them into `trading_disclosures` with per-MP incremental upload.

**Architecture:** Members-first approach — fetch the MP list from the Members API, then for each MP fetch all their interests from the Interests API, parse into disclosure records, and upload immediately. Overrides `run()` like the EU ETL to survive Fly.io restarts.

**Tech Stack:** Python 3.11, httpx (async HTTP), BaseETLService, Supabase (trading_disclosures table), pytest

**Design Doc:** `docs/plans/2026-02-17-uk-parliament-etl-design.md`

---

## Task 1: Add chamber_role_map entry for UK Parliament

**Files:**
- Modify: `python-etl-service/app/lib/politician.py:84-89`

**Step 1: Write the failing test**

Create `python-etl-service/tests/test_uk_parliament_etl.py`:

```python
"""Tests for UK Parliament ETL Service."""

import pytest
from unittest.mock import MagicMock, patch


class TestPoliticianIntegration:
    """Test politician.py integration for UK Parliament."""

    def test_chamber_role_map_includes_uk_parliament(self):
        """uk_parliament chamber maps to Member of Parliament role."""
        from app.lib.politician import find_or_create_politician

        # The chamber_role_map is internal, but we can verify via a mock
        # that the correct role is used when chamber="uk_parliament"
        mock_supabase = MagicMock()
        # Make the lookup return a match so we don't create
        mock_supabase.table.return_value.select.return_value.ilike.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "test-uuid"}
        ]

        result = find_or_create_politician(
            mock_supabase,
            first_name="Keir",
            last_name="Starmer",
            chamber="uk_parliament",
        )
        assert result == "test-uuid"
```

**Step 2: Run test to verify it passes** (this one should already work since the map defaults to "Representative")

Run: `cd python-etl-service && uv run pytest tests/test_uk_parliament_etl.py::TestPoliticianIntegration::test_chamber_role_map_includes_uk_parliament -v`

**Step 3: Add uk_parliament to chamber_role_map**

In `python-etl-service/app/lib/politician.py`, add `"uk_parliament": "Member of Parliament"` to the `chamber_role_map` dict at line 84-89:

```python
    chamber_role_map = {
        "senate": "Senator",
        "house": "Representative",
        "eu_parliament": "MEP",
        "uk_parliament": "Member of Parliament",
        "california": "State Legislator",
    }
```

**Step 4: Run test to verify it passes**

Run: `cd python-etl-service && uv run pytest tests/test_uk_parliament_etl.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add python-etl-service/app/lib/politician.py python-etl-service/tests/test_uk_parliament_etl.py
git commit -m "feat: add uk_parliament chamber to politician role map"
```

---

## Task 2: Create UK Parliament ETL service skeleton with category mapping

**Files:**
- Create: `python-etl-service/app/services/uk_parliament_etl.py`
- Test: `python-etl-service/tests/test_uk_parliament_etl.py`

**Step 1: Write the failing tests**

Add to `test_uk_parliament_etl.py`:

```python
from app.services.uk_parliament_etl import (
    UKParliamentETLService,
    CATEGORY_MAP,
    MEMBERS_API_BASE,
    INTERESTS_API_BASE,
)
from app.lib.registry import ETLRegistry


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

    def test_all_ten_categories_covered(self):
        assert len(CATEGORY_MAP) == 12  # 10 main + 2 subcategories


class TestRegistration:
    """Test ETL registry integration."""

    def test_service_is_registered(self):
        assert ETLRegistry.is_registered("uk_parliament")

    def test_service_source_name(self):
        service = ETLRegistry.create_instance("uk_parliament")
        assert service.source_name == "UK Parliament"

    def test_service_is_base_etl_subclass(self):
        from app.lib.base_etl import BaseETLService
        service = ETLRegistry.create_instance("uk_parliament")
        assert isinstance(service, BaseETLService)
```

**Step 2: Run tests to verify they fail**

Run: `cd python-etl-service && uv run pytest tests/test_uk_parliament_etl.py::TestCategoryMapping -v`
Expected: FAIL (ImportError)

**Step 3: Create the service skeleton**

Create `python-etl-service/app/services/uk_parliament_etl.py`:

```python
"""
UK Parliament Register of Interests ETL Service.

Fetches MP financial interests (shareholdings, employment, gifts, property)
from the official Register of Interests API and loads them into
trading_disclosures with per-MP incremental upload.

Data sources:
- Members API: https://members-api.parliament.uk/api/v1/Members/Search
- Interests API: https://interests-api.parliament.uk/api/v1/Interests
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.lib.base_etl import BaseETLService, ETLResult, JobStatus
from app.lib.database import get_supabase
from app.lib.registry import ETLRegistry

logger = logging.getLogger(__name__)

MEMBERS_API_BASE = "https://members-api.parliament.uk/api"
INTERESTS_API_BASE = "https://interests-api.parliament.uk/api/v1"

# UK Parliament interest category ID -> transaction_type
CATEGORY_MAP: Dict[int, str] = {
    # Income categories
    1: "income",    # Ad hoc payments (subcategory of Employment)
    2: "income",    # Ongoing paid employment (subcategory of Employment)
    12: "income",   # Employment and earnings (parent)
    # Holding categories
    7: "holding",   # Land and property
    8: "holding",   # Shareholdings
    # Gift categories
    3: "gift",      # Donations and other support
    4: "gift",      # Gifts, benefits and hospitality from UK sources
    5: "gift",      # Visits outside the UK
    6: "gift",      # Gifts and benefits from sources outside the UK
    # Other categories
    9: "other",     # Miscellaneous
    10: "other",    # Family members employed
    11: "other",    # Family members engaged in lobbying
}


@ETLRegistry.register
class UKParliamentETLService(BaseETLService):
    """
    UK Parliament financial interests ETL service.

    Fetches MP interests from the Register of Interests API,
    parses all 10 categories of financial declarations, and uploads
    to trading_disclosures with per-MP incremental upload.
    """

    source_id = "uk_parliament"
    source_name = "UK Parliament"

    async def fetch_disclosures(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch all UK Parliament interests (buffered mode, for testing)."""
        return []

    async def parse_disclosure(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a single interest record into disclosure format."""
        return raw
```

**Step 4: Register the import in etl_services.py**

Add to the bottom of `python-etl-service/app/services/etl_services.py`:

```python
import app.services.uk_parliament_etl  # noqa: F401 - UK Parliament Interests
```

**Step 5: Run all tests to verify they pass**

Run: `cd python-etl-service && uv run pytest tests/test_uk_parliament_etl.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add python-etl-service/app/services/uk_parliament_etl.py python-etl-service/app/services/etl_services.py python-etl-service/tests/test_uk_parliament_etl.py
git commit -m "feat: add UK Parliament ETL service skeleton with category mapping"
```

---

## Task 3: Implement `_fetch_mp_list()` with pagination

**Files:**
- Modify: `python-etl-service/app/services/uk_parliament_etl.py`
- Test: `python-etl-service/tests/test_uk_parliament_etl.py`

**Step 1: Write the failing tests**

Add to `test_uk_parliament_etl.py`:

```python
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

# Sample Members API response fixture
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


class TestFetchMPList:
    """Test _fetch_mp_list() MP fetching and pagination."""

    @pytest.mark.asyncio
    async def test_fetches_commons_members(self):
        service = UKParliamentETLService()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_MEMBERS_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.uk_parliament_etl.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            mps = await service._fetch_mp_list()

        assert len(mps) == 2
        assert mps[0]["id"] == 4514
        assert mps[0]["name"] == "Keir Starmer"
        assert mps[0]["party"] == "Labour"
        assert mps[0]["constituency"] == "Holborn and St Pancras"

    @pytest.mark.asyncio
    async def test_extracts_first_and_last_name(self):
        service = UKParliamentETLService()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_MEMBERS_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.uk_parliament_etl.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            mps = await service._fetch_mp_list()

        assert mps[0]["first_name"] == "Keir"
        assert mps[0]["last_name"] == "Starmer"

    @pytest.mark.asyncio
    async def test_paginates_when_more_results(self):
        service = UKParliamentETLService()
        page1 = {
            "items": [{"value": {"id": 1, "nameDisplayAs": "MP One", "nameListAs": "One, MP",
                        "latestParty": {"name": "Labour", "abbreviation": "Lab"},
                        "latestHouseMembership": {"membershipFrom": "Somewhere", "house": 1}}}],
            "totalResults": 2, "skip": 0, "take": 1,
        }
        page2 = {
            "items": [{"value": {"id": 2, "nameDisplayAs": "MP Two", "nameListAs": "Two, MP",
                        "latestParty": {"name": "Conservative", "abbreviation": "Con"},
                        "latestHouseMembership": {"membershipFrom": "Elsewhere", "house": 1}}}],
            "totalResults": 2, "skip": 1, "take": 1,
        }

        responses = [MagicMock(status_code=200, raise_for_status=MagicMock()),
                     MagicMock(status_code=200, raise_for_status=MagicMock())]
        responses[0].json.return_value = page1
        responses[1].json.return_value = page2

        with patch("app.services.uk_parliament_etl.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=responses)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            mps = await service._fetch_mp_list()

        assert len(mps) == 2
        assert mps[0]["id"] == 1
        assert mps[1]["id"] == 2

    @pytest.mark.asyncio
    async def test_respects_limit(self):
        service = UKParliamentETLService()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_MEMBERS_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.uk_parliament_etl.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            mps = await service._fetch_mp_list(limit=1)

        assert len(mps) == 1
```

**Step 2: Run tests to verify they fail**

Run: `cd python-etl-service && uv run pytest tests/test_uk_parliament_etl.py::TestFetchMPList -v`
Expected: FAIL (AttributeError: _fetch_mp_list not defined)

**Step 3: Implement `_fetch_mp_list()`**

Add to `UKParliamentETLService` in `uk_parliament_etl.py`:

```python
    async def _fetch_mp_list(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch current House of Commons MPs from the Members API.

        Args:
            limit: Max MPs to return (for testing).

        Returns:
            List of dicts with id, name, first_name, last_name, party, constituency.
        """
        mps: List[Dict[str, Any]] = []
        skip = 0
        take = 20

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                resp = await client.get(
                    f"{MEMBERS_API_BASE}/Members/Search",
                    params={
                        "House": 1,  # Commons
                        "IsCurrentMember": True,
                        "skip": skip,
                        "take": take,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("items", []):
                    member = item.get("value", {})
                    name = member.get("nameDisplayAs", "")
                    name_parts = member.get("nameListAs", "").split(", ", 1)
                    last_name = name_parts[0].strip() if name_parts else ""
                    first_name = name_parts[1].strip() if len(name_parts) > 1 else ""

                    party_info = member.get("latestParty", {})
                    house_info = member.get("latestHouseMembership", {})

                    mps.append({
                        "id": member.get("id"),
                        "name": name,
                        "first_name": first_name,
                        "last_name": last_name,
                        "party": party_info.get("name", ""),
                        "constituency": house_info.get("membershipFrom", ""),
                    })

                    if limit and len(mps) >= limit:
                        return mps

                total = data.get("totalResults", 0)
                skip += take
                if skip >= total:
                    break

        self.logger.info(f"Fetched {len(mps)} MPs from Members API")
        return mps
```

**Step 4: Run tests to verify they pass**

Run: `cd python-etl-service && uv run pytest tests/test_uk_parliament_etl.py::TestFetchMPList -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add python-etl-service/app/services/uk_parliament_etl.py python-etl-service/tests/test_uk_parliament_etl.py
git commit -m "feat: implement _fetch_mp_list with pagination for UK Parliament ETL"
```

---

## Task 4: Implement `_fetch_mp_interests()` with pagination

**Files:**
- Modify: `python-etl-service/app/services/uk_parliament_etl.py`
- Test: `python-etl-service/tests/test_uk_parliament_etl.py`

**Step 1: Write the failing tests**

Add fixture and tests to `test_uk_parliament_etl.py`:

```python
SAMPLE_INTERESTS_RESPONSE = {
    "items": [
        {
            "value": {
                "id": 14465,
                "summary": "Writing articles - Associated Newspapers Ltd",
                "registrationDate": "2026-02-02",
                "publishedDate": "2026-02-10",
                "updatedDates": [],
                "category": {"id": 12, "name": "Employment and earnings", "number": "1"},
                "member": {
                    "id": 4514,
                    "nameDisplayAs": "Keir Starmer",
                    "party": "Labour",
                    "memberFrom": "Holborn and St Pancras",
                },
                "fields": [
                    {"name": "JobTitle", "value": "Writing articles"},
                    {"name": "PayerName", "value": "Associated Newspapers Ltd"},
                ],
                "childInterests": [
                    {
                        "id": 14466,
                        "summary": "Payment of GBP 850",
                        "registrationDate": "2026-02-02",
                        "publishedDate": "2026-02-10",
                        "fields": [
                            {"name": "ReceivedDate", "value": "2026-01-29"},
                            {"name": "Value", "value": "850.00",
                             "typeInfo": {"currencyCode": "GBP"}},
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
                "category": {"id": 8, "name": "Shareholdings", "number": "7"},
                "member": {
                    "id": 4514,
                    "nameDisplayAs": "Keir Starmer",
                    "party": "Labour",
                    "memberFrom": "Holborn and St Pancras",
                },
                "fields": [
                    {"name": "OrganisationName", "value": "Acme Holdings Ltd"},
                    {"name": "OrganisationDescription", "value": "Software and Technology"},
                    {"name": "ShareholdingThreshold", "value": "(i) over 15% of issued share capital"},
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


class TestFetchMPInterests:
    """Test _fetch_mp_interests() interest fetching."""

    @pytest.mark.asyncio
    async def test_fetches_interests_for_mp(self):
        service = UKParliamentETLService()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_INTERESTS_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.uk_parliament_etl.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            interests = await service._fetch_mp_interests(4514)

        assert len(interests) == 2
        assert interests[0]["id"] == 14465
        assert interests[1]["id"] == 5000

    @pytest.mark.asyncio
    async def test_includes_child_interests(self):
        service = UKParliamentETLService()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_INTERESTS_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.uk_parliament_etl.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            interests = await service._fetch_mp_interests(4514)

        # First interest should have child interests
        assert len(interests[0].get("childInterests", [])) == 1
        child = interests[0]["childInterests"][0]
        assert child["id"] == 14466

    @pytest.mark.asyncio
    async def test_passes_expand_child_interests_param(self):
        service = UKParliamentETLService()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": [], "totalResults": 0, "skip": 0, "take": 20}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.uk_parliament_etl.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await service._fetch_mp_interests(4514)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params", {})
        assert params.get("ExpandChildInterests") is True
        assert params.get("MemberId") == 4514
```

**Step 2: Run tests to verify they fail**

Run: `cd python-etl-service && uv run pytest tests/test_uk_parliament_etl.py::TestFetchMPInterests -v`
Expected: FAIL

**Step 3: Implement `_fetch_mp_interests()`**

Add to `UKParliamentETLService`:

```python
    async def _fetch_mp_interests(
        self, mp_id: int
    ) -> List[Dict[str, Any]]:
        """Fetch all interests for a single MP from the Interests API.

        Args:
            mp_id: The Parliament Members API ID for the MP.

        Returns:
            List of raw interest dicts from the API, with child interests expanded.
        """
        interests: List[Dict[str, Any]] = []
        skip = 0
        take = 20

        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                resp = await client.get(
                    f"{INTERESTS_API_BASE}/Interests",
                    params={
                        "MemberId": mp_id,
                        "ExpandChildInterests": True,
                        "skip": skip,
                        "take": take,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("items", []):
                    interest = item.get("value", {})
                    interests.append(interest)

                total = data.get("totalResults", 0)
                skip += take
                if skip >= total:
                    break

        return interests
```

**Step 4: Run tests**

Run: `cd python-etl-service && uv run pytest tests/test_uk_parliament_etl.py::TestFetchMPInterests -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add python-etl-service/app/services/uk_parliament_etl.py python-etl-service/tests/test_uk_parliament_etl.py
git commit -m "feat: implement _fetch_mp_interests with pagination"
```

---

## Task 5: Implement `_parse_interest()` — field extraction and disclosure mapping

**Files:**
- Modify: `python-etl-service/app/services/uk_parliament_etl.py`
- Test: `python-etl-service/tests/test_uk_parliament_etl.py`

**Step 1: Write the failing tests**

Add to `test_uk_parliament_etl.py`:

```python
class TestParseInterest:
    """Test _parse_interest() disclosure mapping."""

    def setup_method(self):
        self.service = UKParliamentETLService()
        self.mp = {
            "id": 4514,
            "name": "Keir Starmer",
            "first_name": "Keir",
            "last_name": "Starmer",
            "party": "Labour",
            "constituency": "Holborn and St Pancras",
        }

    def test_parent_interest_produces_one_disclosure(self):
        """Shareholding (no children) produces exactly one record."""
        interest = SAMPLE_INTERESTS_RESPONSE["items"][1]["value"]  # shareholding
        records = self.service._parse_interest(interest, self.mp)
        assert len(records) == 1

    def test_parent_with_children_produces_child_records(self):
        """Employment with 1 child payment produces 1 child record (not parent)."""
        interest = SAMPLE_INTERESTS_RESPONSE["items"][0]["value"]  # employment
        records = self.service._parse_interest(interest, self.mp)
        # Should produce child records when children exist
        assert len(records) >= 1

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
```

**Step 2: Run tests to verify they fail**

Run: `cd python-etl-service && uv run pytest tests/test_uk_parliament_etl.py::TestParseInterest -v`
Expected: FAIL

**Step 3: Implement `_parse_interest()`**

Add to `UKParliamentETLService`:

```python
    def _parse_interest(
        self, interest: Dict[str, Any], mp: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Parse a single interest (with children) into disclosure records.

        Parent interests without children produce one record.
        Parent interests with children produce one record per child
        (the child carries the payment details).

        Args:
            interest: Raw interest dict from the Interests API.
            mp: MP dict from _fetch_mp_list().

        Returns:
            List of disclosure dicts ready for parse_disclosure/upload.
        """
        category_id = interest.get("category", {}).get("id", 0)
        transaction_type = CATEGORY_MAP.get(category_id, "other")
        summary = (interest.get("summary") or "")[:200]
        reg_date = interest.get("registrationDate")
        pub_date = interest.get("publishedDate")

        base = {
            "politician_name": mp["name"],
            "first_name": mp["first_name"],
            "last_name": mp["last_name"],
            "bioguide_id": str(mp["id"]),
            "chamber": "uk_parliament",
            "party": mp["party"],
            "state": "United Kingdom",
            "district": mp["constituency"],
            "source": "uk_parliament",
            "filing_date": reg_date,
            "notification_date": pub_date,
        }

        children = interest.get("childInterests") or []

        if children:
            # Emit one record per child payment
            records = []
            for child in children:
                record = {**base}
                record["asset_name"] = summary
                record["transaction_type"] = transaction_type
                record["doc_id"] = str(child.get("id", interest.get("id", "")))

                # Extract GBP amount and date from child fields
                amount = self._extract_amount(child.get("fields", []))
                record["value_low"] = amount
                record["value_high"] = amount

                received_date = self._extract_field(child.get("fields", []), "ReceivedDate")
                record["transaction_date"] = received_date or reg_date

                record["raw_data"] = {
                    "parent_interest_id": interest.get("id"),
                    "child_interest_id": child.get("id"),
                    "category": interest.get("category", {}).get("name"),
                    "fields": child.get("fields", []),
                }

                records.append(record)
            return records
        else:
            # No children — emit the parent as a single record
            record = {**base}
            record["asset_name"] = summary
            record["transaction_type"] = transaction_type
            record["doc_id"] = str(interest.get("id", ""))
            record["transaction_date"] = reg_date

            # Try to extract amount from parent fields
            amount = self._extract_amount(interest.get("fields", []))
            record["value_low"] = amount
            record["value_high"] = amount

            record["raw_data"] = {
                "interest_id": interest.get("id"),
                "category": interest.get("category", {}).get("name"),
                "fields": interest.get("fields", []),
            }

            return [record]

    @staticmethod
    def _extract_amount(fields: List[Dict[str, Any]]) -> Optional[float]:
        """Extract GBP amount from interest fields.

        Looks for fields with typeInfo.currencyCode == 'GBP' and a numeric value.
        """
        for f in fields:
            type_info = f.get("typeInfo") or {}
            if type_info.get("currencyCode") == "GBP":
                try:
                    return float(f["value"])
                except (ValueError, KeyError, TypeError):
                    pass
            # Also check field name "Value" as fallback
            if f.get("name") == "Value" and f.get("value"):
                try:
                    return float(f["value"])
                except (ValueError, TypeError):
                    pass
        return None

    @staticmethod
    def _extract_field(fields: List[Dict[str, Any]], name: str) -> Optional[str]:
        """Extract a named field value from the fields list."""
        for f in fields:
            if f.get("name") == name:
                return f.get("value")
        return None
```

**Step 4: Run tests**

Run: `cd python-etl-service && uv run pytest tests/test_uk_parliament_etl.py::TestParseInterest -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add python-etl-service/app/services/uk_parliament_etl.py python-etl-service/tests/test_uk_parliament_etl.py
git commit -m "feat: implement _parse_interest with field extraction and child handling"
```

---

## Task 6: Implement `parse_disclosure()` and `run()` with incremental upload

**Files:**
- Modify: `python-etl-service/app/services/uk_parliament_etl.py`
- Test: `python-etl-service/tests/test_uk_parliament_etl.py`

**Step 1: Write the failing tests**

Add to `test_uk_parliament_etl.py`:

```python
class TestParseDisclosure:
    """Test parse_disclosure() schema mapping."""

    @pytest.mark.asyncio
    async def test_maps_fields_for_upload(self):
        service = UKParliamentETLService()
        raw = {
            "politician_name": "Test MP",
            "first_name": "Test",
            "last_name": "MP",
            "bioguide_id": "123",
            "chamber": "uk_parliament",
            "party": "Labour",
            "state": "United Kingdom",
            "district": "Somewhere",
            "source": "uk_parliament",
            "asset_name": "Acme Corp",
            "transaction_type": "holding",
            "transaction_date": "2025-01-01",
            "filing_date": "2025-01-01",
            "notification_date": "2025-01-15",
            "doc_id": "5000",
            "value_low": None,
            "value_high": None,
            "raw_data": {"interest_id": 5000, "category": "Shareholdings"},
        }
        result = await service.parse_disclosure(raw)
        assert result is not None
        assert result["asset_name"] == "Acme Corp"
        assert result["transaction_type"] == "holding"

    @pytest.mark.asyncio
    async def test_skips_empty_asset_name(self):
        service = UKParliamentETLService()
        raw = {
            "asset_name": "",
            "transaction_type": "other",
        }
        result = await service.parse_disclosure(raw)
        assert result is None


class TestRunIncremental:
    """Test run() with incremental per-MP upload."""

    @pytest.mark.asyncio
    async def test_uploads_per_mp_not_buffered(self):
        service = UKParliamentETLService()

        mp_list = [
            {"id": 1, "name": "MP One", "first_name": "MP", "last_name": "One",
             "party": "Lab", "constituency": "A"},
            {"id": 2, "name": "MP Two", "first_name": "MP", "last_name": "Two",
             "party": "Con", "constituency": "B"},
        ]

        interests_mp1 = [SAMPLE_INTERESTS_RESPONSE["items"][1]["value"]]  # shareholding
        interests_mp2 = [SAMPLE_INTERESTS_RESPONSE["items"][0]["value"]]  # employment w/ child

        with patch.object(service, "_fetch_mp_list", new_callable=AsyncMock, return_value=mp_list), \
             patch.object(service, "_fetch_mp_interests", new_callable=AsyncMock, side_effect=[interests_mp1, interests_mp2]), \
             patch.object(service, "upload_disclosure", new_callable=AsyncMock, return_value="disc-id"), \
             patch.object(service, "on_start", new_callable=AsyncMock), \
             patch.object(service, "on_complete", new_callable=AsyncMock), \
             patch("app.services.uk_parliament_etl.get_supabase") as mock_sb:
            mock_sb.return_value = MagicMock()

            result = await service.run("test-job", update_mode=True)

        assert result.records_updated >= 2  # At least 1 shareholding + 1 child payment
        assert result.records_failed == 0

    @pytest.mark.asyncio
    async def test_run_handles_mp_fetch_error(self):
        service = UKParliamentETLService()

        mp_list = [
            {"id": 1, "name": "Bad MP", "first_name": "Bad", "last_name": "MP",
             "party": "Lab", "constituency": "X"},
        ]

        with patch.object(service, "_fetch_mp_list", new_callable=AsyncMock, return_value=mp_list), \
             patch.object(service, "_fetch_mp_interests", new_callable=AsyncMock, side_effect=Exception("API down")), \
             patch.object(service, "on_start", new_callable=AsyncMock), \
             patch.object(service, "on_complete", new_callable=AsyncMock), \
             patch("app.services.uk_parliament_etl.get_supabase") as mock_sb:
            mock_sb.return_value = MagicMock()

            result = await service.run("test-job")

        assert result.records_failed == 1
        assert "API down" in result.errors[0]

    @pytest.mark.asyncio
    async def test_run_updates_job_status_progress(self):
        service = UKParliamentETLService()

        mp_list = [
            {"id": 1, "name": "MP One", "first_name": "MP", "last_name": "One",
             "party": "Lab", "constituency": "A"},
        ]

        with patch.object(service, "_fetch_mp_list", new_callable=AsyncMock, return_value=mp_list), \
             patch.object(service, "_fetch_mp_interests", new_callable=AsyncMock, return_value=[]), \
             patch.object(service, "on_start", new_callable=AsyncMock), \
             patch.object(service, "on_complete", new_callable=AsyncMock), \
             patch("app.services.uk_parliament_etl.get_supabase") as mock_sb:
            mock_sb.return_value = MagicMock()

            await service.run("test-job")

        status = service.get_job_status("test-job")
        assert status is not None
        assert status.progress == 1
        assert status.total == 1
```

**Step 2: Run tests to verify they fail**

Run: `cd python-etl-service && uv run pytest tests/test_uk_parliament_etl.py::TestRunIncremental -v`
Expected: FAIL

**Step 3: Implement `parse_disclosure()` and `run()`**

Update `parse_disclosure()` in `UKParliamentETLService`:

```python
    async def parse_disclosure(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a single interest record into disclosure format.

        The raw dict is already in the right shape from _parse_interest().
        This validates and passes it through.
        """
        if not raw.get("asset_name"):
            return None
        return raw
```

Add `run()` override:

```python
    async def run(
        self,
        job_id: str,
        limit: Optional[int] = None,
        update_mode: bool = False,
        **kwargs,
    ) -> ETLResult:
        """Execute UK Parliament ETL with incremental per-MP uploads."""
        result = ETLResult(started_at=datetime.now(timezone.utc))
        self._job_status[job_id] = JobStatus(
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
            message=f"Starting {self.source_name} ETL...",
        )

        try:
            await self.on_start(job_id, **kwargs)

            supabase = get_supabase()
            if not supabase:
                result.add_error("Supabase client not available")
                self._job_status[job_id].status = "failed"
                self._job_status[job_id].message = "Supabase unavailable"
                return result

            self.update_job_status(job_id, message="Fetching MP list...")
            mps = await self._fetch_mp_list(limit=limit)

            if not mps:
                result.add_warning("No MPs fetched from Members API")
                self.update_job_status(
                    job_id, status="completed", message="No MPs to process",
                )
                result.completed_at = datetime.now(timezone.utc)
                return result

            total_mps = len(mps)
            self.update_job_status(job_id, total=total_mps)
            self.logger.info(f"Processing {total_mps} MPs with incremental upload")

            for i, mp in enumerate(mps):
                mp_name = mp["name"]
                uploaded = result.records_inserted + result.records_updated
                self.update_job_status(
                    job_id, progress=i + 1,
                    message=f"MP {i + 1}/{total_mps}: {mp_name} ({uploaded} uploaded)",
                )

                try:
                    interests = await self._fetch_mp_interests(mp["id"])
                except Exception as e:
                    result.records_failed += 1
                    result.add_error(f"Failed to fetch interests for {mp_name}: {e}")
                    continue

                # Parse and upload each interest immediately
                for interest in interests:
                    records = self._parse_interest(interest, mp)
                    for record in records:
                        result.records_processed += 1
                        try:
                            parsed = await self.parse_disclosure(record)
                            if not parsed:
                                result.records_skipped += 1
                                continue

                            if not await self.validate_disclosure(parsed):
                                result.records_skipped += 1
                                continue

                            disclosure_id = await self.upload_disclosure(
                                parsed, update_mode=update_mode
                            )

                            if disclosure_id:
                                if update_mode:
                                    result.records_updated += 1
                                else:
                                    result.records_inserted += 1
                            else:
                                result.records_skipped += 1

                        except Exception as e:
                            result.records_failed += 1
                            result.add_error(f"Failed to upload: {e}")

                if interests:
                    uploaded = result.records_inserted + result.records_updated
                    self.logger.info(
                        f"MP {i + 1}/{total_mps} {mp_name}: "
                        f"uploaded {len(interests)} interests (total: {uploaded})"
                    )

            # Complete
            result.completed_at = datetime.now(timezone.utc)
            self._job_status[job_id].status = "completed"
            self._job_status[job_id].completed_at = (
                datetime.now(timezone.utc).isoformat()
            )
            self._job_status[job_id].result = result
            self._job_status[job_id].message = (
                f"Completed: {result.records_inserted} inserted, "
                f"{result.records_updated} updated, "
                f"{result.records_failed} failed"
            )
            await self.on_complete(job_id, result)

        except Exception as e:
            result.add_error(f"ETL job failed: {e}")
            result.completed_at = datetime.now(timezone.utc)
            self._job_status[job_id].status = "failed"
            self._job_status[job_id].completed_at = (
                datetime.now(timezone.utc).isoformat()
            )
            self._job_status[job_id].message = f"Failed: {e}"
            self.logger.exception(f"UK Parliament ETL failed: {e}")

        return result
```

**Step 4: Run all tests**

Run: `cd python-etl-service && uv run pytest tests/test_uk_parliament_etl.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add python-etl-service/app/services/uk_parliament_etl.py python-etl-service/tests/test_uk_parliament_etl.py
git commit -m "feat: implement UK Parliament ETL run() with incremental per-MP upload"
```

---

## Task 7: Run full test suite, verify no regressions, final commit

**Step 1: Run UK Parliament ETL tests**

Run: `cd python-etl-service && uv run pytest tests/test_uk_parliament_etl.py -v --tb=short`
Expected: ALL PASS (40+ tests)

**Step 2: Run full ETL test suite to check for regressions**

Run: `cd python-etl-service && uv run pytest tests/ -v --tb=short -q`
Expected: ALL PASS, no regressions in existing ETL tests

**Step 3: Lint**

Run: `cd python-etl-service && uv run ruff check app/services/uk_parliament_etl.py`
Expected: No errors

**Step 4: Create feature branch, push, and open PR**

```bash
git checkout -b feat/uk-parliament-etl
git push -u origin HEAD
gh pr create --title "feat: add UK Parliament ETL service" --body "$(cat <<'EOF'
## Summary
- New ETL service for UK Parliament Register of Interests
- Fetches all 10 categories of MP financial interests via official API
- Members-first architecture with per-MP incremental upload
- Structured JSON API (no PDF parsing, no scraping)

## Changes
- `app/services/uk_parliament_etl.py` - New ETL service
- `app/services/etl_services.py` - Register import
- `app/lib/politician.py` - Add uk_parliament chamber role
- `tests/test_uk_parliament_etl.py` - ~40 tests

## Test plan
- [ ] All unit tests pass locally
- [ ] CI passes
- [ ] Trigger ETL with limit=5 to verify API integration
- [ ] Verify records appear in trading_disclosures

## Design doc
See `docs/plans/2026-02-17-uk-parliament-etl-design.md`
EOF
)"
```

**Step 5: Wait for CI, merge**

```bash
gh run watch
gh pr merge --squash --delete-branch
git checkout main && git pull origin main
```
