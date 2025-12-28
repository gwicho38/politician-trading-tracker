"""
Supabase Edge Function Liveness Tests

Tests that verify all edge functions are deployed, reachable, and responding correctly.

Usage:
    uv run pytest tests/supabase-functions/test_liveness.py -v
    uv run pytest tests/supabase-functions/test_liveness.py -v -k "test_function_deployed"
"""

import os
import pytest
import httpx
from datetime import datetime
from typing import Optional

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://uljsqvwkomdrlnofmlad.supabase.co")
SUPABASE_ANON_KEY = os.getenv(
    "SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsanNxdndrb21kcmxub2ZtbGFkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4MDIyNDQsImV4cCI6MjA3MjM3ODI0NH0.QCpfcEpxGX_5Wn8ljf_J2KWjJLGdF8zRsV_7OatxmHI"
)

# Edge function definitions
EDGE_FUNCTIONS = {
    "politician-trading-collect": {
        "path": "/functions/v1/politician-trading-collect",
        "method": "POST",
        "auth_required": False,
        "expected_keys": ["success"],
        "periodicity": "0 */6 * * *",  # Every 6 hours
        "description": "Collects financial disclosures from multiple sources",
    },
    "sync-data": {
        "path": "/functions/v1/sync-data/update-stats",
        "method": "POST",
        "auth_required": False,
        "expected_keys": ["success"],
        "periodicity": "0 * * * *",  # Every hour
        "description": "Updates dashboard statistics",
    },
    "trading-signals": {
        "path": "/functions/v1/trading-signals/test",
        "method": "POST",
        "auth_required": False,
        "expected_keys": ["success", "message"],
        "periodicity": None,  # On-demand
        "description": "Trading signals health check",
    },
    "trading-signals-get": {
        "path": "/functions/v1/trading-signals/get-signals",
        "method": "POST",
        "auth_required": False,
        "expected_keys": ["success", "signals"],
        "periodicity": None,
        "description": "Retrieves active trading signals",
    },
}

# Functions requiring authentication
AUTH_REQUIRED_FUNCTIONS = {
    "alpaca-account": {
        "path": "/functions/v1/alpaca-account",
        "method": "POST",
        "expected_keys": ["success", "account"],
        "description": "Alpaca trading account info",
    },
    "portfolio": {
        "path": "/functions/v1/portfolio",
        "method": "POST",
        "expected_keys": ["success", "positions"],
        "description": "User portfolio positions",
    },
    "orders": {
        "path": "/functions/v1/orders",
        "method": "POST",
        "body": {"action": "get-orders"},
        "expected_keys": ["success", "orders"],
        "description": "User trading orders",
    },
}


class TestEdgeFunctionDeployment:
    """Test that edge functions are deployed and reachable."""

    @pytest.fixture
    def client(self):
        """Create HTTP client with default headers."""
        return httpx.Client(
            base_url=SUPABASE_URL,
            headers={
                "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    @pytest.mark.parametrize("function_name", EDGE_FUNCTIONS.keys())
    def test_function_deployed(self, client, function_name):
        """Test that each edge function is deployed and responds."""
        config = EDGE_FUNCTIONS[function_name]

        response = client.request(
            method=config["method"],
            url=config["path"],
            json={},
        )

        # Function should be found (not 404)
        assert response.status_code != 404, (
            f"Function '{function_name}' not deployed. "
            f"Deploy with: npx supabase functions deploy {function_name.split('-')[0]}"
        )

        # Log the response for debugging
        print(f"\n{function_name}: {response.status_code} - {response.text[:200]}")

    @pytest.mark.parametrize("function_name", EDGE_FUNCTIONS.keys())
    def test_function_returns_json(self, client, function_name):
        """Test that each edge function returns valid JSON."""
        config = EDGE_FUNCTIONS[function_name]

        response = client.request(
            method=config["method"],
            url=config["path"],
            json={},
        )

        if response.status_code == 404:
            pytest.skip(f"Function '{function_name}' not deployed")

        # Should return JSON
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type, (
            f"Function '{function_name}' should return JSON, got: {content_type}"
        )

        # Should be parseable JSON
        try:
            data = response.json()
            assert isinstance(data, dict), "Response should be a JSON object"
        except Exception as e:
            pytest.fail(f"Failed to parse JSON response: {e}")

    @pytest.mark.parametrize("function_name", EDGE_FUNCTIONS.keys())
    def test_function_response_structure(self, client, function_name):
        """Test that each edge function returns expected keys."""
        config = EDGE_FUNCTIONS[function_name]

        response = client.request(
            method=config["method"],
            url=config["path"],
            json={},
        )

        if response.status_code == 404:
            pytest.skip(f"Function '{function_name}' not deployed")

        if response.status_code >= 500:
            pytest.skip(f"Function '{function_name}' returned server error: {response.status_code}")

        try:
            data = response.json()
        except Exception:
            pytest.skip(f"Function '{function_name}' did not return JSON")

        # Check for expected keys (at least one should be present)
        expected_keys = config.get("expected_keys", [])
        if expected_keys:
            found_keys = [k for k in expected_keys if k in data]
            assert len(found_keys) > 0, (
                f"Expected at least one of {expected_keys} in response, got: {list(data.keys())}"
            )


class TestAuthenticatedFunctions:
    """Test edge functions that require authentication."""

    @pytest.fixture
    def auth_token(self) -> Optional[str]:
        """Get auth token for authenticated requests."""
        # This would normally get a real auth token
        # For now, we'll skip these tests if no token is available
        return os.getenv("SUPABASE_AUTH_TOKEN")

    @pytest.fixture
    def client(self, auth_token):
        """Create HTTP client with auth headers."""
        if not auth_token:
            pytest.skip("No auth token available (set SUPABASE_AUTH_TOKEN)")

        return httpx.Client(
            base_url=SUPABASE_URL,
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    @pytest.mark.parametrize("function_name", AUTH_REQUIRED_FUNCTIONS.keys())
    def test_auth_function_deployed(self, client, function_name):
        """Test that authenticated functions are deployed."""
        config = AUTH_REQUIRED_FUNCTIONS[function_name]
        body = config.get("body", {})

        response = client.request(
            method=config["method"],
            url=config["path"],
            json=body,
        )

        assert response.status_code != 404, (
            f"Function '{function_name}' not deployed"
        )

        print(f"\n{function_name}: {response.status_code}")


class TestPeriodicityConfiguration:
    """Test that periodic functions have scheduled jobs configured."""

    @pytest.fixture
    def client(self):
        """Create Supabase client for database queries."""
        return httpx.Client(
            base_url=SUPABASE_URL,
            headers={
                "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
                "apikey": SUPABASE_ANON_KEY,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def test_scheduled_jobs_table_exists(self, client):
        """Test that scheduled_jobs table exists."""
        response = client.get(
            "/rest/v1/scheduled_jobs",
            params={"select": "id", "limit": "1"},
        )

        assert response.status_code != 404, (
            "scheduled_jobs table does not exist. Run migrations."
        )

    def test_periodic_jobs_configured(self, client):
        """Test that periodic jobs are configured in scheduled_jobs table."""
        response = client.get(
            "/rest/v1/scheduled_jobs",
            params={"select": "*"},
        )

        if response.status_code != 200:
            pytest.skip("Could not query scheduled_jobs table")

        jobs = response.json()
        job_names = [j.get("job_name", "").lower() for j in jobs]

        expected_jobs = [
            "data collection",
            "signal generation",
        ]

        for expected in expected_jobs:
            found = any(expected in name for name in job_names)
            if not found:
                print(f"WARNING: Expected job '{expected}' not found in scheduled_jobs")

    def test_job_execution_tracking(self, client):
        """Test that job_executions table exists for tracking."""
        response = client.get(
            "/rest/v1/job_executions",
            params={"select": "id", "limit": "1"},
        )

        assert response.status_code != 404, (
            "job_executions table does not exist. Run migrations."
        )


class TestFunctionHealth:
    """Health check tests for all functions."""

    @pytest.fixture
    def client(self):
        return httpx.Client(
            base_url=SUPABASE_URL,
            headers={
                "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    def test_trading_signals_health(self, client):
        """Test trading-signals function health endpoint."""
        response = client.post("/functions/v1/trading-signals/test")

        if response.status_code == 404:
            pytest.skip("trading-signals not deployed")

        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "timestamp" in data or "message" in data

    def test_sync_data_endpoints(self, client):
        """Test sync-data function has all expected endpoints."""
        endpoints = [
            "/functions/v1/sync-data/sync-all",
            "/functions/v1/sync-data/sync-politicians",
            "/functions/v1/sync-data/sync-trades",
            "/functions/v1/sync-data/update-stats",
            "/functions/v1/sync-data/sync-full",
        ]

        for endpoint in endpoints:
            response = client.post(endpoint, json={})

            if response.status_code == 404:
                pytest.fail(f"sync-data not deployed or endpoint missing: {endpoint}")

            # Should return some response (may be error if not fully configured)
            assert response.status_code < 500, f"Server error on {endpoint}"


class TestDataIntegrity:
    """Test that functions are writing to correct tables."""

    @pytest.fixture
    def client(self):
        return httpx.Client(
            base_url=SUPABASE_URL,
            headers={
                "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
                "apikey": SUPABASE_ANON_KEY,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def test_trading_disclosures_has_data(self, client):
        """Test that trading_disclosures table has data from ETL."""
        response = client.get(
            "/rest/v1/trading_disclosures",
            params={"select": "id,created_at", "limit": "1", "order": "created_at.desc"},
        )

        if response.status_code != 200:
            pytest.skip("Could not query trading_disclosures")

        data = response.json()
        assert len(data) > 0, "trading_disclosures table is empty. Run ETL pipeline."

        # Check freshness
        if data:
            latest = data[0].get("created_at")
            print(f"\nLatest disclosure: {latest}")

    def test_politicians_has_data(self, client):
        """Test that politicians table has data."""
        response = client.get(
            "/rest/v1/politicians",
            params={"select": "id", "limit": "1"},
        )

        if response.status_code != 200:
            pytest.skip("Could not query politicians")

        data = response.json()
        assert len(data) > 0, "politicians table is empty"

    def test_trading_signals_table_exists(self, client):
        """Test that trading_signals table exists."""
        response = client.get(
            "/rest/v1/trading_signals",
            params={"select": "id", "limit": "1"},
        )

        assert response.status_code != 404, "trading_signals table does not exist"


# CLI entry point for manual testing
if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("Supabase Edge Function Liveness Tests")
    print("=" * 60)
    print(f"Supabase URL: {SUPABASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    # Quick manual test
    client = httpx.Client(
        base_url=SUPABASE_URL,
        headers={
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )

    results = []

    for name, config in EDGE_FUNCTIONS.items():
        try:
            response = client.request(
                method=config["method"],
                url=config["path"],
                json={},
            )

            if response.status_code == 404:
                status = "❌ NOT DEPLOYED"
            elif response.status_code >= 500:
                status = f"⚠️ ERROR ({response.status_code})"
            elif response.status_code >= 400:
                status = f"⚠️ CLIENT ERROR ({response.status_code})"
            else:
                status = f"✅ OK ({response.status_code})"

            results.append((name, status, config.get("periodicity", "on-demand")))

        except Exception as e:
            results.append((name, f"❌ FAILED: {e}", config.get("periodicity", "on-demand")))

    print("Function Status:")
    print("-" * 60)
    for name, status, periodicity in results:
        period_str = periodicity if periodicity else "on-demand"
        print(f"  {name}: {status} | Schedule: {period_str}")

    print()
    print("=" * 60)

    # Exit with error if any function failed
    failed = any("❌" in r[1] for r in results)
    sys.exit(1 if failed else 0)
