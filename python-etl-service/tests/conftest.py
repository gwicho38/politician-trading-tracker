"""
Pytest fixtures for Python ETL service tests.

Provides mock Supabase clients, sample data, and common test utilities.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, date
from typing import Dict, Any, List
import io


# =============================================================================
# Mock Supabase Client Fixtures
# =============================================================================

@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    client = MagicMock()

    # Mock table operations
    table_mock = MagicMock()
    table_mock.insert.return_value.execute.return_value = MagicMock(data=[{"id": "test-uuid"}])
    table_mock.upsert.return_value.execute.return_value = MagicMock(data=[{"id": "test-uuid"}])
    table_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
    table_mock.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    client.table.return_value = table_mock
    return client


@pytest.fixture
def mock_supabase_with_politician():
    """Create a mock Supabase client with existing politician data."""
    client = MagicMock()

    table_mock = MagicMock()

    # Mock finding existing politician
    existing_politician = {
        "id": "pol-uuid-123",
        "full_name": "John Doe",
        "first_name": "John",
        "last_name": "Doe",
        "party": "D",
        "chamber": "House",
    }
    table_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[existing_politician]
    )

    client.table.return_value = table_mock
    return client


# =============================================================================
# Sample Data Fixtures - House Disclosures
# =============================================================================

@pytest.fixture
def sample_house_pdf_row():
    """Sample row data from a House disclosure PDF table."""
    return [
        "01/15/2024",  # Transaction date
        "01/25/2024",  # Notification date
        "Apple Inc.",  # Asset name
        "ST",  # Asset type (stock)
        "AAPL",  # Ticker
        "P",  # Transaction type (purchase)
        "$1,001 - $15,000",  # Amount range
        "SP",  # Owner (spouse)
        "",  # Comments
    ]


@pytest.fixture
def sample_house_disclosure_metadata():
    """Sample metadata from House disclosure index."""
    return {
        "doc_id": "20012345",
        "year": 2024,
        "filing_type": "P",  # PTR
        "pdf_url": "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2024/20012345.pdf",
        "politician_name": "Jane Smith",
        "first_name": "Jane",
        "last_name": "Smith",
        "state_district": "CA-12",
        "filing_date": "2024-01-25",
        "source": "us_house",
    }


@pytest.fixture
def sample_house_transactions():
    """Sample parsed transactions from House disclosure."""
    return [
        {
            "asset_name": "Apple Inc.",
            "asset_ticker": "AAPL",
            "asset_type": "stock",
            "transaction_type": "purchase",
            "transaction_date": "2024-01-15",
            "notification_date": "2024-01-25",
            "amount_range_min": 1001,
            "amount_range_max": 15000,
            "asset_owner": "spouse",
            "comments": None,
        },
        {
            "asset_name": "Microsoft Corporation",
            "asset_ticker": "MSFT",
            "asset_type": "stock",
            "transaction_type": "sale",
            "transaction_date": "2024-01-16",
            "notification_date": "2024-01-25",
            "amount_range_min": 15001,
            "amount_range_max": 50000,
            "asset_owner": "self",
            "comments": None,
        },
    ]


# =============================================================================
# Sample Data Fixtures - Senate Disclosures
# =============================================================================

@pytest.fixture
def sample_senate_xml_senator():
    """Sample senator data from Senate XML."""
    return {
        "first_name": "John",
        "last_name": "Smith",
        "full_name": "John Smith",
        "party": "D",
        "state": "CA",
        "bioguide_id": "S000123",
    }


@pytest.fixture
def sample_senate_disclosure_row():
    """Sample row from Senate EFD HTML table."""
    return {
        "transaction_date": "2024-01-10",
        "owner": "Self",
        "ticker": "GOOGL",
        "asset_name": "Alphabet Inc Class A",
        "asset_type": "Stock",
        "transaction_type": "Sale (Full)",
        "amount": "$50,001 - $100,000",
        "comment": "",
    }


@pytest.fixture
def sample_senate_transactions():
    """Sample parsed transactions from Senate disclosure."""
    return [
        {
            "asset_name": "Alphabet Inc Class A",
            "asset_ticker": "GOOGL",
            "asset_type": "stock",
            "transaction_type": "sale",
            "transaction_date": "2024-01-10",
            "disclosure_date": "2024-01-20",
            "amount_range_min": 50001,
            "amount_range_max": 100000,
            "asset_owner": "self",
            "comments": None,
        },
    ]


# =============================================================================
# Sample Data Fixtures - QuiverQuant
# =============================================================================

@pytest.fixture
def sample_quiverquant_response():
    """Sample QuiverQuant API response."""
    return [
        {
            "Representative": "Jonathan Jackson",
            "BioGuideID": "J000309",
            "ReportDate": "2024-01-08",
            "TransactionDate": "2023-12-22",
            "Ticker": "HOOD",
            "Transaction": "Sale",
            "Range": "$15,001 - $50,000",
            "House": "Representatives",
            "Amount": "15001.0",
            "Party": "D",
            "last_modified": "2024-01-09",
            "TickerType": "ST",
            "Description": None,
            "ExcessReturn": -6.39,
            "PriceChange": -5.70,
            "SPYChange": 0.69,
        },
        {
            "Representative": "Nancy Pelosi",
            "BioGuideID": "P000197",
            "ReportDate": "2024-01-05",
            "TransactionDate": "2023-12-15",
            "Ticker": "NVDA",
            "Transaction": "Purchase",
            "Range": "$1,000,001 - $5,000,000",
            "House": "Representatives",
            "Amount": "1000001.0",
            "Party": "D",
            "last_modified": "2024-01-06",
            "TickerType": "ST",
            "Description": "NVIDIA Corporation",
            "ExcessReturn": 12.5,
            "PriceChange": 15.2,
            "SPYChange": 2.7,
        },
    ]


# =============================================================================
# Sample Data Fixtures - Congress.gov
# =============================================================================

@pytest.fixture
def sample_congress_member():
    """Sample Congress.gov API member response."""
    return {
        "bioguideId": "P000197",
        "firstName": "Nancy",
        "lastName": "Pelosi",
        "partyName": "Democratic",
        "state": "CA",
        "district": 11,
        "terms": [
            {"startYear": 2023, "endYear": 2025, "chamber": "House"}
        ],
    }


# =============================================================================
# PDF Mock Fixtures
# =============================================================================

@pytest.fixture
def sample_pdf_bytes():
    """Sample PDF bytes for testing."""
    # Minimal valid PDF header
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


@pytest.fixture
def mock_pdf_tables():
    """Mock extracted tables from PDF."""
    return [
        [
            ["Transaction Date", "Notification Date", "Owner", "Asset", "Type", "Transaction", "Amount", "Comment"],
            ["01/15/2024", "01/25/2024", "SP", "Apple Inc. (AAPL)", "ST", "P", "$1,001 - $15,000", ""],
            ["01/16/2024", "01/25/2024", "JT", "Microsoft Corp (MSFT)", "ST", "S", "$15,001 - $50,000", ""],
        ]
    ]


# =============================================================================
# HTTP Response Fixtures
# =============================================================================

@pytest.fixture
def mock_httpx_response_success():
    """Mock successful HTTP response."""
    response = MagicMock()
    response.status_code = 200
    response.content = b"%PDF-1.4\ntest content"
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def mock_httpx_response_rate_limited():
    """Mock rate-limited HTTP response."""
    import httpx
    response = MagicMock()
    response.status_code = 429
    response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError(
        "Rate limited",
        request=MagicMock(),
        response=response
    ))
    return response


# =============================================================================
# Environment Variable Fixtures
# =============================================================================

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables for testing."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
    monkeypatch.setenv("CONGRESS_API_KEY", "test-congress-api-key")
    monkeypatch.setenv("QUIVERQUANT_API_KEY", "test-quiver-api-key")


# =============================================================================
# Job Status Fixtures
# =============================================================================

@pytest.fixture
def initial_job_status():
    """Initial job status structure."""
    return {
        "status": "running",
        "progress": 0,
        "total": None,
        "message": "Starting job",
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
    }


@pytest.fixture
def completed_job_status():
    """Completed job status structure."""
    return {
        "status": "completed",
        "progress": 100,
        "total": 100,
        "message": "Job completed successfully",
        "started_at": "2024-01-01T00:00:00",
        "completed_at": "2024-01-01T00:05:00",
    }
