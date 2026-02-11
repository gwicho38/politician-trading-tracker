"""
Tests for Senate HTTP client (app/services/senate_http_client.py).

Tests the HTTP CSRF session flow, DataTables JSON search,
PTR page fetching, and WAF detection.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from typing import Any, Dict

import httpx


# =============================================================================
# Helper: Create mock httpx response
# =============================================================================

def _mock_response(
    status_code: int = 200,
    text: str = "",
    json_data: Any = None,
    url: str = "https://efdsearch.senate.gov/search/",
) -> MagicMock:
    """Create a mock httpx.Response."""
    import json as _json

    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.url = url
    if json_data is not None:
        resp.json.return_value = json_data
        # Ensure text is non-empty so WAF check passes
        resp.text = text or _json.dumps(json_data)
    else:
        resp.text = text
        resp.json.side_effect = ValueError("No JSON")
    return resp


# =============================================================================
# SenateEFDClient Session Tests
# =============================================================================

class TestSenateEFDClientSession:
    """Tests for CSRF session establishment flow."""

    @pytest.mark.asyncio
    async def test_session_establishes_successfully(self):
        """SenateEFDClient establishes session with valid CSRF + sessionid."""
        from app.services.senate_http_client import SenateEFDClient

        client = SenateEFDClient()
        mock_http = AsyncMock(spec=httpx.AsyncClient)

        # Mock cookies jar — returns csrftoken first, then sessionid after POST
        cookie_store = {}

        def mock_get_cookie(name):
            return cookie_store.get(name)

        mock_http.cookies = MagicMock()
        mock_http.cookies.get = mock_get_cookie

        # GET /search/ → set csrftoken
        async def mock_get(url, **kwargs):
            cookie_store["csrftoken"] = "fake-csrf-token"
            return _mock_response(200, "<html>search page</html>")

        # POST /search/home/ → set sessionid
        async def mock_post(url, **kwargs):
            cookie_store["sessionid"] = "fake-session-id"
            cookie_store["csrftoken"] = "rotated-csrf-token"
            return _mock_response(200, "<html>search form</html>")

        mock_http.get = mock_get
        mock_http.post = mock_post
        mock_http.aclose = AsyncMock()

        client._client = mock_http
        await client.establish_session()

        assert client._session_established is True
        assert client._csrf_token == "rotated-csrf-token"

    @pytest.mark.asyncio
    async def test_session_fails_without_csrf_token(self):
        """SenateEFDClient raises EFDSessionError when csrftoken missing."""
        from app.services.senate_http_client import SenateEFDClient, EFDSessionError

        client = SenateEFDClient()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.cookies = MagicMock()
        mock_http.cookies.get = MagicMock(return_value=None)

        mock_http.get = AsyncMock(return_value=_mock_response(200, "<html></html>"))

        client._client = mock_http

        with pytest.raises(EFDSessionError, match="No csrftoken"):
            await client.establish_session()

    @pytest.mark.asyncio
    async def test_session_fails_without_sessionid(self):
        """SenateEFDClient raises EFDSessionError when sessionid missing after POST."""
        from app.services.senate_http_client import SenateEFDClient, EFDSessionError

        client = SenateEFDClient()
        mock_http = AsyncMock(spec=httpx.AsyncClient)

        cookie_store = {}

        def mock_get_cookie(name):
            return cookie_store.get(name)

        mock_http.cookies = MagicMock()
        mock_http.cookies.get = mock_get_cookie

        async def mock_get(url, **kwargs):
            cookie_store["csrftoken"] = "fake-csrf"
            return _mock_response(200, "<html></html>")

        async def mock_post(url, **kwargs):
            # No sessionid set
            return _mock_response(200, "<html></html>")

        mock_http.get = mock_get
        mock_http.post = mock_post

        client._client = mock_http

        with pytest.raises(EFDSessionError, match="No sessionid"):
            await client.establish_session()

    @pytest.mark.asyncio
    async def test_session_fails_on_waf_block_get(self):
        """SenateEFDClient raises EFDBlockedError on 403 during GET /search/."""
        from app.services.senate_http_client import SenateEFDClient, EFDBlockedError

        client = SenateEFDClient()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.get = AsyncMock(return_value=_mock_response(403, "Forbidden"))

        client._client = mock_http

        with pytest.raises(EFDBlockedError, match="403"):
            await client.establish_session()

    @pytest.mark.asyncio
    async def test_session_fails_on_waf_block_post(self):
        """SenateEFDClient raises EFDBlockedError on 403 during POST /search/home/."""
        from app.services.senate_http_client import SenateEFDClient, EFDBlockedError

        client = SenateEFDClient()
        mock_http = AsyncMock(spec=httpx.AsyncClient)

        cookie_store = {}

        def mock_get_cookie(name):
            return cookie_store.get(name)

        mock_http.cookies = MagicMock()
        mock_http.cookies.get = mock_get_cookie

        async def mock_get(url, **kwargs):
            cookie_store["csrftoken"] = "fake-csrf"
            return _mock_response(200, "<html></html>")

        mock_http.get = mock_get
        mock_http.post = AsyncMock(return_value=_mock_response(403, "Forbidden"))

        client._client = mock_http

        with pytest.raises(EFDBlockedError, match="403"):
            await client.establish_session()

    @pytest.mark.asyncio
    async def test_session_fails_on_network_error(self):
        """SenateEFDClient raises EFDSessionError on network error."""
        from app.services.senate_http_client import SenateEFDClient, EFDSessionError

        client = SenateEFDClient()
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        client._client = mock_http

        with pytest.raises(EFDSessionError, match="Failed to GET"):
            await client.establish_session()


# =============================================================================
# SenateEFDClient Search Tests
# =============================================================================

class TestSenateEFDClientSearch:
    """Tests for PTR search via DataTables JSON API."""

    def _setup_client(self):
        """Create a pre-authenticated client for testing search."""
        from app.services.senate_http_client import SenateEFDClient

        client = SenateEFDClient()
        client._session_established = True
        client._csrf_token = "fake-csrf"
        client._client = AsyncMock(spec=httpx.AsyncClient)
        return client

    @pytest.mark.asyncio
    async def test_search_parses_json_results(self):
        """search_ptrs parses JSON response with 5-element records."""
        client = self._setup_client()

        json_data = {
            "result": "ok",
            "data": [
                [
                    "John",
                    "Smith",
                    "Senator",
                    '<a href="/search/view/ptr/abc-123-def/">Periodic Transaction Report</a>',
                    "01/15/2024",
                ],
            ],
            "recordsTotal": 1,
        }

        client._client.post = AsyncMock(
            return_value=_mock_response(200, json_data=json_data)
        )

        disclosures = await client.search_ptrs(lookback_days=30)

        assert len(disclosures) == 1
        assert disclosures[0]["politician_name"] == "John Smith"
        assert disclosures[0]["doc_id"] == "abc-123-def"
        assert disclosures[0]["source"] == "us_senate"

    @pytest.mark.asyncio
    async def test_search_handles_pagination(self):
        """search_ptrs paginates through multiple pages."""
        client = self._setup_client()

        page1 = {
            "result": "ok",
            "data": [
                [
                    "John", "Smith", "Senator",
                    '<a href="/search/view/ptr/abc-1/">Periodic Transaction Report</a>',
                    "01/15/2024",
                ],
            ] * 100,
            "recordsTotal": 150,
        }

        page2 = {
            "result": "ok",
            "data": [
                [
                    "Jane", "Doe", "Senator",
                    '<a href="/search/view/ptr/abc-2/">Periodic Transaction Report</a>',
                    "02/15/2024",
                ],
            ] * 50,
            "recordsTotal": 150,
        }

        client._client.post = AsyncMock(
            side_effect=[
                _mock_response(200, json_data=page1),
                _mock_response(200, json_data=page2),
            ]
        )

        disclosures = await client.search_ptrs(lookback_days=30)

        assert len(disclosures) == 150
        assert client._client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_search_respects_limit(self):
        """search_ptrs stops at the specified limit."""
        client = self._setup_client()

        json_data = {
            "result": "ok",
            "data": [
                [
                    "John", "Smith", "Senator",
                    '<a href="/search/view/ptr/abc-1/">Periodic Transaction Report</a>',
                    "01/15/2024",
                ],
            ] * 100,
            "recordsTotal": 500,
        }

        client._client.post = AsyncMock(
            return_value=_mock_response(200, json_data=json_data)
        )

        disclosures = await client.search_ptrs(lookback_days=30, limit=5)

        assert len(disclosures) == 5

    @pytest.mark.asyncio
    async def test_search_includes_date_params_when_provided(self):
        """search_ptrs includes submitted_start_date/end_date in POST when provided."""
        client = self._setup_client()

        json_data = {
            "result": "ok",
            "data": [],
            "recordsTotal": 0,
        }

        client._client.post = AsyncMock(
            return_value=_mock_response(200, json_data=json_data)
        )

        await client.search_ptrs(
            lookback_days=30,
            start_date="01/01/2020",
            end_date="12/31/2020",
        )

        # Verify POST data includes date params
        post_call = client._client.post.call_args
        post_data = post_call.kwargs.get("data", post_call[1].get("data", {}))
        assert post_data["submitted_start_date"] == "01/01/2020"
        assert post_data["submitted_end_date"] == "12/31/2020"

    @pytest.mark.asyncio
    async def test_search_omits_date_params_when_none(self):
        """search_ptrs omits date params from POST body when not provided."""
        client = self._setup_client()

        json_data = {
            "result": "ok",
            "data": [],
            "recordsTotal": 0,
        }

        client._client.post = AsyncMock(
            return_value=_mock_response(200, json_data=json_data)
        )

        await client.search_ptrs(lookback_days=30)

        # Verify POST data does NOT include date params
        post_call = client._client.post.call_args
        post_data = post_call.kwargs.get("data", post_call[1].get("data", {}))
        assert "submitted_start_date" not in post_data
        assert "submitted_end_date" not in post_data

    @pytest.mark.asyncio
    async def test_search_handles_empty_results(self):
        """search_ptrs returns empty list for no results."""
        client = self._setup_client()

        json_data = {
            "result": "ok",
            "data": [],
            "recordsTotal": 0,
        }

        client._client.post = AsyncMock(
            return_value=_mock_response(200, json_data=json_data)
        )

        disclosures = await client.search_ptrs(lookback_days=30)

        assert disclosures == []

    @pytest.mark.asyncio
    async def test_search_raises_on_non_json_response(self):
        """search_ptrs raises EFDBlockedError on non-JSON response."""
        from app.services.senate_http_client import EFDBlockedError

        client = self._setup_client()

        resp = _mock_response(200, text="<html>Not JSON</html>")
        resp.json.side_effect = ValueError("No JSON")
        client._client.post = AsyncMock(return_value=resp)

        with pytest.raises(EFDBlockedError, match="Non-JSON"):
            await client.search_ptrs(lookback_days=30)

    @pytest.mark.asyncio
    async def test_search_raises_on_result_not_ok(self):
        """search_ptrs raises EFDBlockedError when result != 'ok'."""
        from app.services.senate_http_client import EFDBlockedError

        client = self._setup_client()

        json_data = {"result": "error", "data": []}
        client._client.post = AsyncMock(
            return_value=_mock_response(200, json_data=json_data)
        )

        with pytest.raises(EFDBlockedError, match="Unexpected result"):
            await client.search_ptrs(lookback_days=30)

    @pytest.mark.asyncio
    async def test_search_raises_on_403(self):
        """search_ptrs raises EFDBlockedError on 403."""
        from app.services.senate_http_client import EFDBlockedError

        client = self._setup_client()
        client._client.post = AsyncMock(
            return_value=_mock_response(403, "Forbidden")
        )

        with pytest.raises(EFDBlockedError, match="403"):
            await client.search_ptrs(lookback_days=30)


# =============================================================================
# SenateEFDClient PTR Fetch Tests
# =============================================================================

class TestSenateEFDClientPTRFetch:
    """Tests for PTR page fetching."""

    def _setup_client(self):
        """Create a pre-authenticated client."""
        from app.services.senate_http_client import SenateEFDClient

        client = SenateEFDClient()
        client._session_established = True
        client._csrf_token = "fake-csrf"
        client._client = AsyncMock(spec=httpx.AsyncClient)
        return client

    @pytest.mark.asyncio
    async def test_fetch_ptr_page_parses_html(self):
        """fetch_ptr_page returns parsed transactions from HTML."""
        client = self._setup_client()

        html = """
        <html>
        <h1>Periodic Transaction Report for 01/15/2024</h1>
        <table class="table-striped">
            <thead>
                <tr><th>#</th><th>Transaction Date</th><th>Owner</th>
                <th>Ticker</th><th>Asset Name</th><th>Asset Type</th>
                <th>Type</th><th>Amount</th></tr>
            </thead>
            <tbody>
                <tr>
                    <td>1</td><td>01/10/2024</td><td>Self</td>
                    <td>AAPL</td><td>Apple Inc</td><td>Stock</td>
                    <td>Purchase</td><td>$1,001 - $15,000</td>
                </tr>
            </tbody>
        </table>
        </html>
        """

        resp = _mock_response(200, text=html, url="https://efdsearch.senate.gov/search/view/ptr/abc/")
        client._client.get = AsyncMock(return_value=resp)

        transactions = await client.fetch_ptr_page("https://efdsearch.senate.gov/search/view/ptr/abc/")

        assert len(transactions) == 1
        assert transactions[0]["asset_name"] == "Apple Inc"
        assert transactions[0]["transaction_type"] == "purchase"

    @pytest.mark.asyncio
    async def test_fetch_ptr_page_detects_redirect(self):
        """fetch_ptr_page raises EFDBlockedError on redirect to /home/."""
        from app.services.senate_http_client import EFDBlockedError

        client = self._setup_client()

        resp = _mock_response(
            200, text="<html>Agreement</html>",
            url="https://efdsearch.senate.gov/search/home/"
        )
        client._client.get = AsyncMock(return_value=resp)

        with pytest.raises(EFDBlockedError, match="Redirected to agreement"):
            await client.fetch_ptr_page("https://efdsearch.senate.gov/search/view/ptr/abc/")

    @pytest.mark.asyncio
    async def test_fetch_ptr_page_detects_403(self):
        """fetch_ptr_page raises EFDBlockedError on 403."""
        from app.services.senate_http_client import EFDBlockedError

        client = self._setup_client()
        client._client.get = AsyncMock(return_value=_mock_response(403, "Forbidden"))

        with pytest.raises(EFDBlockedError, match="403"):
            await client.fetch_ptr_page("https://efdsearch.senate.gov/search/view/ptr/abc/")


# =============================================================================
# WAF Detection Tests
# =============================================================================

class TestWAFDetection:
    """Tests for _check_for_waf_block."""

    def test_403_triggers_block(self):
        """_check_for_waf_block raises on 403."""
        from app.services.senate_http_client import SenateEFDClient, EFDBlockedError

        client = SenateEFDClient()
        resp = _mock_response(403, "Forbidden")

        with pytest.raises(EFDBlockedError, match="403"):
            client._check_for_waf_block(resp, "test")

    def test_empty_body_triggers_block(self):
        """_check_for_waf_block raises on empty 200 response."""
        from app.services.senate_http_client import SenateEFDClient, EFDBlockedError

        client = SenateEFDClient()
        resp = _mock_response(200, text="")

        with pytest.raises(EFDBlockedError, match="Empty response"):
            client._check_for_waf_block(resp, "test")

    def test_whitespace_only_triggers_block(self):
        """_check_for_waf_block raises on whitespace-only 200 response."""
        from app.services.senate_http_client import SenateEFDClient, EFDBlockedError

        client = SenateEFDClient()
        resp = _mock_response(200, text="   \n  ")

        with pytest.raises(EFDBlockedError, match="Empty response"):
            client._check_for_waf_block(resp, "test")

    def test_normal_200_passes(self):
        """_check_for_waf_block does not raise on normal 200."""
        from app.services.senate_http_client import SenateEFDClient

        client = SenateEFDClient()
        resp = _mock_response(200, text="<html>Normal content</html>")

        # Should not raise
        client._check_for_waf_block(resp, "test")


# =============================================================================
# Context Manager Tests
# =============================================================================

class TestContextManager:
    """Tests for async context manager behavior."""

    @pytest.mark.asyncio
    async def test_aenter_creates_client_and_establishes_session(self):
        """SenateEFDClient.__aenter__ creates httpx client and calls establish_session."""
        from app.services.senate_http_client import SenateEFDClient

        with patch.object(SenateEFDClient, "establish_session", new_callable=AsyncMock) as mock_establish:
            async with SenateEFDClient() as client:
                assert client._client is not None
                mock_establish.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_aexit_closes_client(self):
        """SenateEFDClient.__aexit__ closes the httpx client."""
        from app.services.senate_http_client import SenateEFDClient

        with patch.object(SenateEFDClient, "establish_session", new_callable=AsyncMock):
            async with SenateEFDClient() as client:
                assert client._client is not None

            assert client._client is None
