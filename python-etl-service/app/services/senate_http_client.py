"""
HTTP client for the Senate EFD (Electronic Financial Disclosure) system.

Implements a 3-step CSRF session flow to access the undocumented DataTables
JSON API at /search/report/data/. Falls back to Playwright when the Akamai
WAF blocks HTTP requests.

The CSRF flow:
1. GET /search/           -> obtain csrftoken cookie
2. POST /search/home/     -> accept agreement, get sessionid cookie
3. POST /search/report/data/ -> search PTRs via DataTables JSON API
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from app.services.senate_etl import (
    SENATE_BASE_URL,
    USER_AGENT,
    parse_datatables_record,
    parse_ptr_page_html,
)

logger = logging.getLogger(__name__)


class EFDSessionError(Exception):
    """Raised when the CSRF/session establishment flow fails."""
    pass


class EFDBlockedError(Exception):
    """Raised when Akamai WAF blocks the request (403, redirect, empty response)."""
    pass


class SenateEFDClient:
    """
    Async HTTP client for the Senate EFD search system.

    Usage::

        async with SenateEFDClient() as client:
            disclosures = await client.search_ptrs(lookback_days=30)
            for d in disclosures:
                txns = await client.fetch_ptr_page(d["source_url"])
    """

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None
        self._csrf_token: Optional[str] = None
        self._session_established: bool = False

    async def __aenter__(self) -> "SenateEFDClient":
        self._client = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=30.0,
        )
        await self.establish_session()
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def establish_session(self) -> None:
        """
        Perform the 3-step CSRF flow to get a valid session.

        Step 1: GET /search/ to obtain csrftoken cookie
        Step 2: POST /search/home/ with agreement checkbox to get sessionid
        Step 3: Validate that sessionid cookie is present
        """
        assert self._client is not None

        # Step 1: GET the search page to obtain CSRF cookie
        logger.info("[HTTP] Step 1: Fetching CSRF token from /search/")
        try:
            resp = await self._client.get(f"{SENATE_BASE_URL}/search/")
        except Exception as e:
            raise EFDSessionError(f"Failed to GET /search/: {e}") from e

        self._check_for_waf_block(resp, "GET /search/")

        # Extract CSRF token from cookies
        csrf_token = self._client.cookies.get("csrftoken")
        if not csrf_token:
            raise EFDSessionError("No csrftoken cookie returned from GET /search/")
        self._csrf_token = csrf_token

        # Step 2: POST the agreement acceptance
        logger.info("[HTTP] Step 2: Accepting agreement via POST /search/home/")
        try:
            resp = await self._client.post(
                f"{SENATE_BASE_URL}/search/home/",
                data={
                    "prohibition_agreement": "1",
                    "csrfmiddlewaretoken": self._csrf_token,
                },
                headers={
                    "Referer": f"{SENATE_BASE_URL}/search/home/",
                    "Origin": SENATE_BASE_URL,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
        except Exception as e:
            raise EFDSessionError(f"Failed to POST /search/home/: {e}") from e

        self._check_for_waf_block(resp, "POST /search/home/")

        # Step 3: Validate session cookie
        session_id = self._client.cookies.get("sessionid")
        if not session_id:
            raise EFDSessionError("No sessionid cookie after accepting agreement")

        # Refresh CSRF token (Django rotates it after login)
        new_csrf = self._client.cookies.get("csrftoken")
        if new_csrf:
            self._csrf_token = new_csrf

        self._session_established = True
        logger.info("[HTTP] Session established successfully")

    async def search_ptrs(
        self,
        lookback_days: int = 30,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for PTR disclosures via the DataTables JSON API.

        Paginates through all results, returning parsed disclosure dicts.
        """
        assert self._client is not None and self._session_established

        disclosures: List[Dict[str, Any]] = []
        start = 0
        page_length = 100

        while True:
            logger.info(f"[HTTP] Searching PTRs offset={start} length={page_length}")

            try:
                resp = await self._client.post(
                    f"{SENATE_BASE_URL}/search/report/data/",
                    data={
                        "start": str(start),
                        "length": str(page_length),
                        "report_type_id": "11",  # Periodic Transaction Reports
                        "filer_type_id": "1",    # Senator
                        "csrfmiddlewaretoken": self._csrf_token,
                    },
                    headers={
                        "Referer": f"{SENATE_BASE_URL}/search/",
                        "Origin": SENATE_BASE_URL,
                        "X-Requested-With": "XMLHttpRequest",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
            except Exception as e:
                raise EFDBlockedError(f"Request to /search/report/data/ failed: {e}") from e

            self._check_for_waf_block(resp, "POST /search/report/data/")

            # Parse JSON response
            try:
                data = resp.json()
            except Exception:
                raise EFDBlockedError(
                    f"Non-JSON response from /search/report/data/ "
                    f"(status={resp.status_code}, body={resp.text[:200]})"
                )

            if data.get("result") != "ok":
                raise EFDBlockedError(
                    f"Unexpected result from /search/report/data/: {data.get('result')}"
                )

            records = data.get("data", [])
            total_records = data.get("recordsTotal", 0)

            if not records:
                break

            for record in records:
                parsed = parse_datatables_record(record)
                if parsed:
                    disclosures.append(parsed)

            # Check limit
            if limit and len(disclosures) >= limit:
                disclosures = disclosures[:limit]
                logger.info(f"[HTTP] Reached limit of {limit} disclosures")
                break

            # Check if there are more pages
            start += page_length
            if start >= total_records:
                break

        logger.info(f"[HTTP] Found {len(disclosures)} PTR disclosures")
        return disclosures

    async def fetch_ptr_page(self, url: str) -> List[Dict[str, Any]]:
        """
        Fetch and parse a single PTR page using the established session.

        Returns parsed transactions via parse_ptr_page_html().
        """
        assert self._client is not None and self._session_established

        try:
            resp = await self._client.get(url)
        except Exception as e:
            raise EFDBlockedError(f"Failed to GET PTR page {url}: {e}") from e

        self._check_for_waf_block(resp, f"GET {url}")

        # Check for redirect to agreement page (session expired)
        if "/home/" in str(resp.url) and "/home/" not in url:
            raise EFDBlockedError(f"Redirected to agreement page when fetching {url}")

        return parse_ptr_page_html(resp.text, url)

    def _check_for_waf_block(self, response: httpx.Response, context: str = "") -> None:
        """
        Check for Akamai WAF blocks in the response.

        Raises EFDBlockedError on:
        - HTTP 403 Forbidden
        - Empty response body (Akamai drops connection)
        - Redirect to /home/ (session invalidated)
        """
        if response.status_code == 403:
            raise EFDBlockedError(f"HTTP 403 from {context}")

        if response.status_code == 200 and len(response.text.strip()) == 0:
            raise EFDBlockedError(f"Empty response body from {context}")
