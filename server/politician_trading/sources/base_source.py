"""
Base source class for all disclosure sources.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import aiohttp
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class SourceConfig:
    """Configuration for a data source"""

    name: str
    source_type: str
    base_url: str
    request_delay: float = 1.0  # Delay between requests (rate limiting)
    max_retries: int = 3
    timeout: int = 30
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)


class BaseSource(ABC):
    """
    Abstract base class for all disclosure sources.

    Each source implementation should:
    1. Implement fetch() to get raw data
    2. Implement _parse_response() to extract disclosures
    3. Handle rate limiting and errors
    """

    def __init__(self, config: Optional[SourceConfig] = None):
        self.config = config if config is not None else self._create_default_config()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.session: Optional[aiohttp.ClientSession] = None

    def configure(self, config_dict: Dict[str, Any]):
        """
        Configure source from dictionary.

        Args:
            config_dict: Configuration dictionary
        """
        if not self.config:
            self.config = self._create_default_config()

        # Update config from dict
        for key, value in config_dict.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

    @abstractmethod
    def _create_default_config(self) -> SourceConfig:
        """Create default configuration for this source"""
        pass

    @abstractmethod
    async def _parse_response(self, response_data: Any) -> List[Dict[str, Any]]:
        """
        Parse API/scraping response into disclosure dictionaries.

        Args:
            response_data: Raw response from API or web page

        Returns:
            List of disclosure dictionaries with standardized fields
        """
        pass

    async def fetch(self, lookback_days: int = 30, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch disclosures from this source.

        Args:
            lookback_days: How many days back to fetch
            **kwargs: Additional source-specific parameters

        Returns:
            List of raw disclosure dictionaries
        """
        self.logger.info(
            f"Fetching disclosures from {self.config.name} " f"(lookback: {lookback_days} days)"
        )

        start_time = datetime.utcnow()
        disclosures = []

        try:
            # Create session if needed
            if not self.session:
                self.session = aiohttp.ClientSession(
                    headers=self.config.headers,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                )

            # Fetch data (source-specific implementation)
            response_data = await self._fetch_data(lookback_days, **kwargs)

            # Parse response
            disclosures = await self._parse_response(response_data)

            duration = (datetime.utcnow() - start_time).total_seconds()
            self.logger.info(
                f"Fetched {len(disclosures)} disclosures from {self.config.name} "
                f"in {duration:.2f}s"
            )

        except Exception as e:
            self.logger.error(f"Error fetching from {self.config.name}: {e}", exc_info=True)
            raise

        return disclosures

    async def fetch_batch(
        self, offset: int, limit: int, lookback_days: int = 30, **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Fetch a batch of disclosures (for batch ingestion).

        Args:
            offset: Starting offset
            limit: Number of records to fetch
            lookback_days: How many days back to fetch
            **kwargs: Additional parameters

        Returns:
            List of disclosure dictionaries
        """
        # Default implementation - override in subclass if source supports pagination
        if offset > 0:
            return []  # No more data

        return await self.fetch(lookback_days, **kwargs)

    @abstractmethod
    async def _fetch_data(self, lookback_days: int, **kwargs) -> Any:
        """
        Fetch raw data from source.

        This is source-specific and should be implemented by subclasses.

        Args:
            lookback_days: How many days back to fetch
            **kwargs: Additional parameters

        Returns:
            Raw response data (JSON, HTML, etc.)
        """
        pass

    async def _make_request(self, url: str, method: str = "GET", **kwargs) -> Any:
        """
        Make HTTP request with retry logic.

        Args:
            url: URL to request
            method: HTTP method
            **kwargs: Additional request parameters

        Returns:
            Response data
        """
        for attempt in range(self.config.max_retries):
            try:
                self.logger.debug(
                    f"Request attempt {attempt + 1}/{self.config.max_retries}: {method} {url}"
                )

                async with self.session.request(method, url, **kwargs) as response:
                    response.raise_for_status()

                    # Rate limiting delay
                    if self.config.request_delay > 0:
                        await asyncio.sleep(self.config.request_delay)

                    # Return JSON if possible, otherwise text
                    try:
                        return await response.json()
                    except (ValueError, aiohttp.ContentTypeError):
                        return await response.text()

            except aiohttp.ClientError as e:
                self.logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.config.max_retries}): {e}"
                )
                if attempt == self.config.max_retries - 1:
                    raise
                await asyncio.sleep(2**attempt)  # Exponential backoff

    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def __aenter__(self):
        """Context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()
