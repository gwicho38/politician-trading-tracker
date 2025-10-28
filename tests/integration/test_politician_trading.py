"""
Integration tests for politician trading workflow
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Check for postgrest dependency
try:
    import postgrest

    HAS_POSTGREST = True
except ImportError:
    HAS_POSTGREST = False

if HAS_POSTGREST:
    from mcli.workflow.politician_trading.config import (
        ScrapingConfig,
        SupabaseConfig,
        WorkflowConfig,
    )
    from mcli.workflow.politician_trading.models import (
        Politician,
        PoliticianRole,
        TradingDisclosure,
        TransactionType,
    )
    from mcli.workflow.politician_trading.monitoring import PoliticianTradingMonitor
    from mcli.workflow.politician_trading.workflow import PoliticianTradingWorkflow


@pytest.mark.skipif(not HAS_POSTGREST, reason="postgrest module not installed")
class TestPoliticianTradingIntegration:
    """Test the complete politician trading workflow"""

    def setup_method(self):
        """Setup test environment"""
        # Create test configuration
        self.config = WorkflowConfig(
            supabase=SupabaseConfig(url="https://test.supabase.co", key="test_key"),
            scraping=ScrapingConfig(
                request_delay=0.1, max_retries=2, timeout=10  # Faster for tests
            ),
        )

    @patch("mcli.workflow.politician_trading.database.create_client")
    def test_workflow_initialization(self, mock_create_client):
        """Test workflow initialization"""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        workflow = PoliticianTradingWorkflow(self.config)

        assert workflow.config == self.config
        assert workflow.db is not None
        assert workflow.politicians == []

    @pytest.mark.asyncio
    @patch("mcli.workflow.politician_trading.database.create_client")
    async def test_workflow_status_check(self, mock_create_client):
        """Test workflow status checking"""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        # Mock database responses
        mock_client.table.return_value.select.return_value.execute.return_value = Mock(
            data=[{"count": 5}]
        )

        workflow = PoliticianTradingWorkflow(self.config)

        # Mock database methods
        workflow.db.get_job_status = AsyncMock(
            return_value={
                "total_disclosures": 100,
                "recent_disclosures_today": 5,
                "recent_jobs": [],
            }
        )

        status = await workflow.run_quick_check()

        assert status is not None
        assert "database_connection" in status
        assert "config_loaded" in status
        assert "timestamp" in status

    @pytest.mark.asyncio
    @patch("mcli.workflow.politician_trading.database.create_client")
    async def test_monitoring_health_check(self, mock_create_client):
        """Test monitoring health check"""
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        # Mock successful database responses
        mock_client.table.return_value.select.return_value.execute.return_value = Mock(
            data=[{"created_at": datetime.utcnow().isoformat()}], count=10
        )

        monitor = PoliticianTradingMonitor(self.config)
        health = await monitor.get_system_health()

        assert health is not None
        assert "status" in health
        assert "timestamp" in health
        assert "database" in health
        assert "data_freshness" in health
        assert "recent_jobs" in health

    @pytest.mark.asyncio
    @patch("mcli.workflow.politician_trading.scrapers.CongressTradingScraper")
    @patch("mcli.workflow.politician_trading.scrapers.QuiverQuantScraper")
    @patch("mcli.workflow.politician_trading.scrapers.EUParliamentScraper")
    @patch("mcli.workflow.politician_trading.database.create_client")
    async def test_full_collection_workflow(
        self, mock_create_client, mock_eu_scraper, mock_quiver_scraper, mock_congress_scraper
    ):
        """Test complete data collection workflow"""
        # Setup mocks
        mock_client = Mock()
        mock_create_client.return_value = mock_client

        # Mock database operations
        mock_client.table.return_value.select.return_value.execute.return_value = Mock(data=[])
        mock_client.table.return_value.insert.return_value.execute.return_value = Mock(
            data=[{"id": "test_id"}]
        )

        workflow = PoliticianTradingWorkflow(self.config)

        # Mock database methods
        workflow.db.ensure_schema = AsyncMock(return_value=True)
        workflow.db.create_data_pull_job = AsyncMock(return_value="job_id")
        workflow.db.update_data_pull_job = AsyncMock(return_value=True)
        workflow.db.upsert_politician = AsyncMock(return_value="pol_id")
        workflow.db.insert_disclosure = AsyncMock(return_value="disc_id")
        workflow.db.find_disclosure_by_transaction = AsyncMock(return_value=None)

        # Mock scrapers
        sample_disclosure = TradingDisclosure(
            politician_id="",
            transaction_date=datetime.now(),
            disclosure_date=datetime.now(),
            transaction_type=TransactionType.PURCHASE,
            asset_name="Test Asset",
            asset_ticker="TEST",
            asset_type="stock",
            raw_data={"test": True},
        )

        mock_congress_instance = AsyncMock()
        mock_congress_instance.scrape_house_disclosures.return_value = [sample_disclosure]
        mock_congress_instance.scrape_senate_disclosures.return_value = [sample_disclosure]
        mock_congress_scraper.return_value = mock_congress_instance

        mock_quiver_instance = AsyncMock()
        mock_quiver_instance.scrape_congress_trades.return_value = []
        mock_quiver_scraper.return_value = mock_quiver_instance

        mock_eu_instance = AsyncMock()
        mock_eu_instance.scrape_mep_declarations.return_value = [sample_disclosure]
        mock_eu_scraper.return_value = mock_eu_instance

        # Run workflow
        result = await workflow.run_full_collection()

        # Verify results
        assert result is not None
        assert "status" in result
        assert "jobs" in result
        assert "summary" in result

        # Verify database operations were called
        workflow.db.ensure_schema.assert_called_once()
        workflow.db.create_data_pull_job.assert_called()
        workflow.db.upsert_politician.assert_called()

    def test_politician_role_enum(self):
        """Test politician role enumeration"""
        assert PoliticianRole.US_HOUSE_REP.value == "us_house_representative"
        assert PoliticianRole.US_SENATOR.value == "us_senator"
        assert PoliticianRole.EU_MEP.value == "eu_parliament_member"

    def test_transaction_type_enum(self):
        """Test transaction type enumeration"""
        assert TransactionType.PURCHASE.value == "purchase"
        assert TransactionType.SALE.value == "sale"
        assert TransactionType.EXCHANGE.value == "exchange"

    def test_politician_model_creation(self):
        """Test politician model creation"""
        politician = Politician(
            id="test_id",
            first_name="John",
            last_name="Doe",
            full_name="John Doe",
            role=PoliticianRole.US_HOUSE_REP,
            party="Democratic",
            state_or_country="CA",
        )

        assert politician.id == "test_id"
        assert politician.first_name == "John"
        assert politician.last_name == "Doe"
        assert politician.role == PoliticianRole.US_HOUSE_REP

    def test_trading_disclosure_model_creation(self):
        """Test trading disclosure model creation"""
        disclosure = TradingDisclosure(
            politician_id="pol_id",
            transaction_date=datetime(2024, 1, 15),
            disclosure_date=datetime(2024, 1, 20),
            transaction_type=TransactionType.PURCHASE,
            asset_name="Apple Inc.",
            asset_ticker="AAPL",
            asset_type="stock",
            raw_data={"source": "test"},
        )

        assert disclosure.politician_id == "pol_id"
        assert disclosure.asset_ticker == "AAPL"
        assert disclosure.transaction_type == TransactionType.PURCHASE
        assert disclosure.raw_data["source"] == "test"

    def test_config_validation(self):
        """Test configuration validation"""
        # Test default config creation
        default_config = WorkflowConfig.default()
        assert default_config.supabase is not None
        assert default_config.scraping is not None

        # Test custom config
        custom_config = WorkflowConfig(
            supabase=SupabaseConfig(url="https://custom.supabase.co", key="custom_key"),
            scraping=ScrapingConfig(request_delay=1.0, max_retries=5, timeout=30),
        )

        assert custom_config.supabase.url == "https://custom.supabase.co"
        assert custom_config.scraping.request_delay == 1.0
        assert custom_config.scraping.max_retries == 5


@pytest.mark.skipif(not HAS_POSTGREST, reason="postgrest module not installed")
class TestScrapingIntegration:
    """Test scraping functionality"""

    def setup_method(self):
        """Setup test environment"""
        self.config = ScrapingConfig(request_delay=0.1, max_retries=2, timeout=10)

    def test_amount_range_parsing(self):
        """Test amount range parsing functionality"""
        from mcli.workflow.politician_trading.scrapers import BaseScraper

        scraper = BaseScraper(self.config)

        # Test range parsing
        min_val, max_val, exact_val = scraper.parse_amount_range("$1,001 - $15,000")
        assert min_val == 1001
        assert max_val == 15000
        assert exact_val is None

        # Test exact amount parsing
        min_val, max_val, exact_val = scraper.parse_amount_range("$5,000")
        assert exact_val == 5000
        assert min_val is None
        assert max_val is None

        # Test empty string
        min_val, max_val, exact_val = scraper.parse_amount_range("")
        assert all(v is None for v in [min_val, max_val, exact_val])

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession")
    async def test_base_scraper_fetch(self, mock_session_class):
        """Test base scraper fetch functionality"""
        from mcli.workflow.politician_trading.scrapers import BaseScraper

        # Mock session and response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="<html>Test</html>")

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session

        scraper = BaseScraper(self.config)

        async with scraper:
            result = await scraper.fetch_page("https://test.com")

        assert result == "<html>Test</html>"
        mock_session.get.assert_called_once()

    def test_politician_matcher(self):
        """Test politician matching functionality"""
        from mcli.workflow.politician_trading.scrapers import PoliticianMatcher

        politicians = [
            Politician(
                id="pol_1",
                first_name="Nancy",
                last_name="Pelosi",
                full_name="Nancy Pelosi",
                role=PoliticianRole.US_HOUSE_REP,
                bioguide_id="P000197",
            ),
            Politician(
                id="pol_2",
                first_name="Ted",
                last_name="Cruz",
                full_name="Ted Cruz",
                role=PoliticianRole.US_SENATOR,
                bioguide_id="C001098",
            ),
        ]

        matcher = PoliticianMatcher(politicians)

        # Test exact name match
        found = matcher.find_politician("Nancy Pelosi")
        assert found is not None
        assert found.id == "pol_1"

        # Test bioguide match
        found = matcher.find_politician("", "C001098")
        assert found is not None
        assert found.id == "pol_2"

        # Test no match
        found = matcher.find_politician("Unknown Person")
        assert found is None


@pytest.mark.asyncio
async def test_standalone_functions():
    """Test standalone workflow functions"""
    from mcli.workflow.politician_trading.monitoring import run_health_check, run_stats_report
    from mcli.workflow.politician_trading.workflow import (
        check_politician_trading_status,
        run_politician_trading_collection,
    )

    # These functions should be importable and callable
    # In a real test environment with database access, they would return actual data
    assert callable(run_politician_trading_collection)
    assert callable(check_politician_trading_status)
    assert callable(run_health_check)
    assert callable(run_stats_report)


if __name__ == "__main__":
    pytest.main([__file__])
