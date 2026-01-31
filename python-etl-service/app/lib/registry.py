"""
ETL Service Registry

Provides service discovery for ETL data sources using a decorator-based
registration pattern.

Usage:
    from app.lib.registry import ETLRegistry
    from app.lib.base_etl import BaseETLService

    # Register a service
    @ETLRegistry.register
    class HouseETLService(BaseETLService):
        source_id = "house"
        source_name = "US House of Representatives"
        ...

    # Get a service by ID
    service_class = ETLRegistry.get("house")
    service = service_class()
    result = await service.run(job_id="...")

    # List all registered sources
    sources = ETLRegistry.list_sources()
    # ["house", "senate", ...]

    # Get metadata for all services
    info = ETLRegistry.get_all_info()
    # [{"source_id": "house", "source_name": "...", "class": "HouseETLService"}, ...]
"""

from typing import Dict, List, Optional, Type, Any
import logging

logger = logging.getLogger(__name__)


class ETLRegistry:
    """
    Registry for ETL service classes.

    Uses class-level storage to maintain registered services across
    module imports. Services register themselves using the @register
    decorator.
    """

    _services: Dict[str, Type["BaseETLService"]] = {}

    @classmethod
    def register(cls, service_class: Type["BaseETLService"]) -> Type["BaseETLService"]:
        """
        Decorator to register an ETL service class.

        Args:
            service_class: A class that extends BaseETLService

        Returns:
            The same class (allows use as decorator)

        Raises:
            ValueError: If source_id is missing or already registered

        Example:
            @ETLRegistry.register
            class MyETLService(BaseETLService):
                source_id = "my_source"
                source_name = "My Data Source"
        """
        # Validate the class has required attributes
        source_id = getattr(service_class, "source_id", None)
        if not source_id:
            raise ValueError(
                f"ETL service class {service_class.__name__} must define 'source_id'"
            )

        source_name = getattr(service_class, "source_name", None)
        if not source_name:
            raise ValueError(
                f"ETL service class {service_class.__name__} must define 'source_name'"
            )

        # Check for duplicates
        if source_id in cls._services:
            existing = cls._services[source_id]
            logger.warning(
                f"ETL source '{source_id}' already registered by {existing.__name__}, "
                f"overwriting with {service_class.__name__}"
            )

        # Register
        cls._services[source_id] = service_class
        logger.debug(f"Registered ETL service: {source_id} ({service_class.__name__})")

        return service_class

    @classmethod
    def get(cls, source_id: str) -> Optional[Type["BaseETLService"]]:
        """
        Get a registered ETL service class by source ID.

        Args:
            source_id: The unique identifier for the source

        Returns:
            The service class, or None if not found
        """
        return cls._services.get(source_id)

    @classmethod
    def get_or_raise(cls, source_id: str) -> Type["BaseETLService"]:
        """
        Get a registered ETL service class, raising if not found.

        Args:
            source_id: The unique identifier for the source

        Returns:
            The service class

        Raises:
            KeyError: If source_id is not registered
        """
        service = cls._services.get(source_id)
        if not service:
            available = ", ".join(cls._services.keys()) or "(none)"
            raise KeyError(
                f"Unknown ETL source: '{source_id}'. Available sources: {available}"
            )
        return service

    @classmethod
    def list_sources(cls) -> List[str]:
        """
        Get list of all registered source IDs.

        Returns:
            List of source ID strings
        """
        return list(cls._services.keys())

    @classmethod
    def get_all_info(cls) -> List[Dict[str, Any]]:
        """
        Get metadata for all registered services.

        Returns:
            List of dicts with source_id, source_name, and class name
        """
        return [
            {
                "source_id": source_id,
                "source_name": getattr(service_class, "source_name", "Unknown"),
                "class": service_class.__name__,
            }
            for source_id, service_class in cls._services.items()
        ]

    @classmethod
    def create_instance(cls, source_id: str) -> "BaseETLService":
        """
        Create an instance of a registered ETL service.

        Args:
            source_id: The unique identifier for the source

        Returns:
            An instance of the service class

        Raises:
            KeyError: If source_id is not registered
        """
        service_class = cls.get_or_raise(source_id)
        return service_class()

    @classmethod
    def clear(cls):
        """
        Clear all registered services.

        Primarily used for testing.
        """
        cls._services.clear()

    @classmethod
    def is_registered(cls, source_id: str) -> bool:
        """
        Check if a source ID is registered.

        Args:
            source_id: The unique identifier to check

        Returns:
            True if registered, False otherwise
        """
        return source_id in cls._services


# Import guard to avoid circular imports
# BaseETLService is imported at runtime when needed
def _get_base_class() -> Type[Any]:
    from app.lib.base_etl import BaseETLService
    return BaseETLService
