"""
Tests for ETL registry (app/lib/registry.py).

Tests:
- ETLRegistry.register() - Service registration
- ETLRegistry.get() - Service lookup
- ETLRegistry.create_instance() - Instance creation
- ETLRegistry.list_sources() - Source listing
- ETLRegistry.get_all_info() - Metadata retrieval
"""

import pytest
from unittest.mock import MagicMock


# =============================================================================
# ETLRegistry Tests
# =============================================================================

class TestETLRegistry:
    """Tests for ETLRegistry class."""

    @pytest.fixture(autouse=True)
    def clear_registry(self):
        """Clear registry before and after each test."""
        from app.lib.registry import ETLRegistry
        ETLRegistry.clear()
        yield
        ETLRegistry.clear()

    @pytest.fixture
    def sample_service_class(self):
        """Create a sample ETL service class for testing."""
        from app.lib.base_etl import BaseETLService

        class SampleETLService(BaseETLService):
            source_id = "sample"
            source_name = "Sample Source"

            async def fetch_disclosures(self, **kwargs):
                return []

            async def parse_disclosure(self, raw):
                return raw

        return SampleETLService

    @pytest.fixture
    def another_service_class(self):
        """Create another ETL service class for testing."""
        from app.lib.base_etl import BaseETLService

        class AnotherETLService(BaseETLService):
            source_id = "another"
            source_name = "Another Source"

            async def fetch_disclosures(self, **kwargs):
                return []

            async def parse_disclosure(self, raw):
                return raw

        return AnotherETLService

    # -------------------------------------------------------------------------
    # register() Tests
    # -------------------------------------------------------------------------

    def test_register_adds_service(self, sample_service_class):
        """register() adds service class to registry."""
        from app.lib.registry import ETLRegistry

        ETLRegistry.register(sample_service_class)

        assert ETLRegistry.is_registered("sample")

    def test_register_returns_class(self, sample_service_class):
        """register() returns the registered class (for decorator use)."""
        from app.lib.registry import ETLRegistry

        result = ETLRegistry.register(sample_service_class)

        assert result is sample_service_class

    def test_register_can_be_used_as_decorator(self):
        """register() can be used as a class decorator."""
        from app.lib.registry import ETLRegistry
        from app.lib.base_etl import BaseETLService

        @ETLRegistry.register
        class DecoratedService(BaseETLService):
            source_id = "decorated"
            source_name = "Decorated Source"

            async def fetch_disclosures(self, **kwargs):
                return []

            async def parse_disclosure(self, raw):
                return raw

        assert ETLRegistry.is_registered("decorated")

    def test_register_raises_for_missing_source_id(self):
        """register() raises ValueError for missing source_id."""
        from app.lib.registry import ETLRegistry
        from app.lib.base_etl import BaseETLService

        class NoSourceId(BaseETLService):
            source_name = "Missing ID"

            async def fetch_disclosures(self, **kwargs):
                return []

            async def parse_disclosure(self, raw):
                return raw

        # Remove source_id attribute
        delattr(NoSourceId, "source_id") if hasattr(NoSourceId, "source_id") else None

        with pytest.raises(ValueError, match="must define 'source_id'"):
            ETLRegistry.register(NoSourceId)

    def test_register_raises_for_missing_source_name(self):
        """register() raises ValueError for missing source_name."""
        from app.lib.registry import ETLRegistry
        from app.lib.base_etl import BaseETLService

        class NoSourceName(BaseETLService):
            source_id = "no_name"

            async def fetch_disclosures(self, **kwargs):
                return []

            async def parse_disclosure(self, raw):
                return raw

        # Remove source_name attribute
        delattr(NoSourceName, "source_name") if hasattr(NoSourceName, "source_name") else None

        with pytest.raises(ValueError, match="must define 'source_name'"):
            ETLRegistry.register(NoSourceName)

    def test_register_overwrites_duplicate(self, sample_service_class):
        """register() overwrites duplicate source_id with warning."""
        from app.lib.registry import ETLRegistry
        from app.lib.base_etl import BaseETLService

        ETLRegistry.register(sample_service_class)

        class DuplicateService(BaseETLService):
            source_id = "sample"  # Same as sample_service_class
            source_name = "Duplicate Source"

            async def fetch_disclosures(self, **kwargs):
                return []

            async def parse_disclosure(self, raw):
                return raw

        ETLRegistry.register(DuplicateService)

        # Should be overwritten with new class
        service_class = ETLRegistry.get("sample")
        assert service_class is DuplicateService

    # -------------------------------------------------------------------------
    # get() Tests
    # -------------------------------------------------------------------------

    def test_get_returns_registered_service(self, sample_service_class):
        """get() returns the registered service class."""
        from app.lib.registry import ETLRegistry

        ETLRegistry.register(sample_service_class)

        result = ETLRegistry.get("sample")

        assert result is sample_service_class

    def test_get_returns_none_for_unknown(self):
        """get() returns None for unknown source_id."""
        from app.lib.registry import ETLRegistry

        result = ETLRegistry.get("unknown")

        assert result is None

    # -------------------------------------------------------------------------
    # get_or_raise() Tests
    # -------------------------------------------------------------------------

    def test_get_or_raise_returns_registered_service(self, sample_service_class):
        """get_or_raise() returns the registered service class."""
        from app.lib.registry import ETLRegistry

        ETLRegistry.register(sample_service_class)

        result = ETLRegistry.get_or_raise("sample")

        assert result is sample_service_class

    def test_get_or_raise_raises_for_unknown(self):
        """get_or_raise() raises KeyError for unknown source_id."""
        from app.lib.registry import ETLRegistry

        with pytest.raises(KeyError, match="Unknown ETL source: 'unknown'"):
            ETLRegistry.get_or_raise("unknown")

    def test_get_or_raise_includes_available_sources(
        self, sample_service_class, another_service_class
    ):
        """get_or_raise() includes available sources in error message."""
        from app.lib.registry import ETLRegistry

        ETLRegistry.register(sample_service_class)
        ETLRegistry.register(another_service_class)

        with pytest.raises(KeyError, match="sample") as exc_info:
            ETLRegistry.get_or_raise("unknown")

        assert "sample" in str(exc_info.value)
        assert "another" in str(exc_info.value)

    # -------------------------------------------------------------------------
    # list_sources() Tests
    # -------------------------------------------------------------------------

    def test_list_sources_returns_empty_initially(self):
        """list_sources() returns empty list when no services registered."""
        from app.lib.registry import ETLRegistry

        result = ETLRegistry.list_sources()

        assert result == []

    def test_list_sources_returns_all_source_ids(
        self, sample_service_class, another_service_class
    ):
        """list_sources() returns all registered source IDs."""
        from app.lib.registry import ETLRegistry

        ETLRegistry.register(sample_service_class)
        ETLRegistry.register(another_service_class)

        result = ETLRegistry.list_sources()

        assert "sample" in result
        assert "another" in result
        assert len(result) == 2

    # -------------------------------------------------------------------------
    # get_all_info() Tests
    # -------------------------------------------------------------------------

    def test_get_all_info_returns_empty_initially(self):
        """get_all_info() returns empty list when no services registered."""
        from app.lib.registry import ETLRegistry

        result = ETLRegistry.get_all_info()

        assert result == []

    def test_get_all_info_returns_service_metadata(self, sample_service_class):
        """get_all_info() returns service metadata."""
        from app.lib.registry import ETLRegistry

        ETLRegistry.register(sample_service_class)

        result = ETLRegistry.get_all_info()

        assert len(result) == 1
        assert result[0]["source_id"] == "sample"
        assert result[0]["source_name"] == "Sample Source"
        assert result[0]["class"] == "SampleETLService"

    def test_get_all_info_returns_all_services(
        self, sample_service_class, another_service_class
    ):
        """get_all_info() returns metadata for all services."""
        from app.lib.registry import ETLRegistry

        ETLRegistry.register(sample_service_class)
        ETLRegistry.register(another_service_class)

        result = ETLRegistry.get_all_info()

        assert len(result) == 2
        source_ids = [r["source_id"] for r in result]
        assert "sample" in source_ids
        assert "another" in source_ids

    # -------------------------------------------------------------------------
    # create_instance() Tests
    # -------------------------------------------------------------------------

    def test_create_instance_returns_new_instance(self, sample_service_class):
        """create_instance() returns a new instance of the service."""
        from app.lib.registry import ETLRegistry

        ETLRegistry.register(sample_service_class)

        instance = ETLRegistry.create_instance("sample")

        assert isinstance(instance, sample_service_class)
        assert instance.source_id == "sample"

    def test_create_instance_returns_different_instances(self, sample_service_class):
        """create_instance() returns new instance each call."""
        from app.lib.registry import ETLRegistry

        ETLRegistry.register(sample_service_class)

        instance1 = ETLRegistry.create_instance("sample")
        instance2 = ETLRegistry.create_instance("sample")

        assert instance1 is not instance2

    def test_create_instance_raises_for_unknown(self):
        """create_instance() raises KeyError for unknown source_id."""
        from app.lib.registry import ETLRegistry

        with pytest.raises(KeyError, match="Unknown ETL source"):
            ETLRegistry.create_instance("unknown")

    # -------------------------------------------------------------------------
    # is_registered() Tests
    # -------------------------------------------------------------------------

    def test_is_registered_returns_true_for_registered(self, sample_service_class):
        """is_registered() returns True for registered source."""
        from app.lib.registry import ETLRegistry

        ETLRegistry.register(sample_service_class)

        assert ETLRegistry.is_registered("sample") is True

    def test_is_registered_returns_false_for_unknown(self):
        """is_registered() returns False for unknown source."""
        from app.lib.registry import ETLRegistry

        assert ETLRegistry.is_registered("unknown") is False

    # -------------------------------------------------------------------------
    # clear() Tests
    # -------------------------------------------------------------------------

    def test_clear_removes_all_services(
        self, sample_service_class, another_service_class
    ):
        """clear() removes all registered services."""
        from app.lib.registry import ETLRegistry

        ETLRegistry.register(sample_service_class)
        ETLRegistry.register(another_service_class)
        assert len(ETLRegistry.list_sources()) == 2

        ETLRegistry.clear()

        assert len(ETLRegistry.list_sources()) == 0

    # -------------------------------------------------------------------------
    # Integration Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_registered_service_can_run(self, sample_service_class):
        """Registered service can be instantiated and run."""
        from app.lib.registry import ETLRegistry

        ETLRegistry.register(sample_service_class)

        instance = ETLRegistry.create_instance("sample")
        result = await instance.run("test-job")

        assert result.records_processed == 0  # Empty fetch returns no records

    def test_multiple_services_coexist(
        self, sample_service_class, another_service_class
    ):
        """Multiple services can be registered and retrieved."""
        from app.lib.registry import ETLRegistry

        ETLRegistry.register(sample_service_class)
        ETLRegistry.register(another_service_class)

        sample = ETLRegistry.get("sample")
        another = ETLRegistry.get("another")

        assert sample is sample_service_class
        assert another is another_service_class
        assert sample is not another
