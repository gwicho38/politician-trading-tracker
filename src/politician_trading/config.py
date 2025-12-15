"""
Configuration for politician trading data workflow
"""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


class ConfigurationError(Exception):
    """Raised when required configuration is missing."""
    pass


@dataclass
class SupabaseConfig:
    """Supabase database configuration.

    Attributes:
        url: Supabase project URL (from SUPABASE_URL env var)
        key: Supabase anon/public key (from SUPABASE_ANON_KEY env var)
        service_role_key: Optional service role key for admin operations

    Required environment variables:
        - SUPABASE_URL: Your Supabase project URL
        - SUPABASE_ANON_KEY: Your Supabase anonymous/public key

    Optional environment variables:
        - SUPABASE_SERVICE_ROLE_KEY or SUPABASE_SERVICE_KEY: Service role key
    """

    url: str
    key: str
    service_role_key: Optional[str] = None

    @classmethod
    def from_env(cls, require_credentials: bool = True) -> "SupabaseConfig":
        """Load configuration from environment variables.

        Args:
            require_credentials: If True, raises ConfigurationError when
                required env vars are missing. If False, returns None values.

        Returns:
            SupabaseConfig instance

        Raises:
            ConfigurationError: When required env vars are missing and
                require_credentials is True
        """
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")

        if require_credentials:
            missing = []
            if not url:
                missing.append("SUPABASE_URL")
            if not key:
                missing.append("SUPABASE_ANON_KEY")

            if missing:
                raise ConfigurationError(
                    f"Missing required environment variables: {', '.join(missing)}. "
                    "Please set these in your .env file or environment."
                )

        # Check for service role key (supports both naming conventions)
        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv(
            "SUPABASE_SERVICE_KEY"
        )

        return cls(url=url or "", key=key or "", service_role_key=service_role_key)


@dataclass
class ScrapingConfig:
    """Web scraping configuration with comprehensive data sources"""

    # Rate limiting
    request_delay: float = 1.0  # seconds between requests
    max_retries: int = 3
    timeout: int = 30

    # User agent for requests
    user_agent: str = "Mozilla/5.0 (compatible; MCLI-PoliticianTracker/1.0)"

    # Enable/disable source categories
    enable_us_federal: bool = True
    enable_us_states: bool = True
    enable_eu_parliament: bool = True
    enable_eu_national: bool = True
    enable_third_party: bool = True

    # Legacy properties for backward compatibility
    us_congress_sources: list = None
    eu_sources: list = None

    def __post_init__(self):
        # Maintain backward compatibility
        if self.us_congress_sources is None:
            self.us_congress_sources = [
                "https://disclosures-clerk.house.gov/FinancialDisclosure",
                "https://efd.senate.gov",
                "https://api.quiverquant.com/beta/live/congresstrading",
            ]

        if self.eu_sources is None:
            self.eu_sources = [
                "https://www.europarl.europa.eu/meps/en/declarations",
            ]

    def get_active_sources(self):
        """Get all active data sources based on configuration"""
        from .data_sources import ALL_DATA_SOURCES

        active_sources = []

        if self.enable_us_federal:
            active_sources.extend(ALL_DATA_SOURCES["us_federal"])

        if self.enable_us_states:
            active_sources.extend(ALL_DATA_SOURCES["us_states"])

        if self.enable_eu_parliament:
            active_sources.extend(ALL_DATA_SOURCES["eu_parliament"])

        if self.enable_eu_national:
            active_sources.extend(ALL_DATA_SOURCES["eu_national"])

        if self.enable_third_party:
            active_sources.extend(ALL_DATA_SOURCES["third_party"])

        # Filter to only active status sources
        return [source for source in active_sources if source.status == "active"]


@dataclass
class WorkflowConfig:
    """Overall workflow configuration.

    Combines Supabase and scraping configuration into a single config object.

    Attributes:
        supabase: Database configuration
        scraping: Web scraping configuration
        cron_schedule: Cron expression for scheduled runs (reference only)
        retention_days: How long to keep data

    Example:
        # Standard usage - requires env vars
        config = WorkflowConfig.default()

        # For testing/development - doesn't require env vars
        config = WorkflowConfig.for_testing()
    """

    supabase: SupabaseConfig
    scraping: ScrapingConfig

    # Cron schedule (for reference, actual scheduling done in Supabase)
    cron_schedule: str = "0 */6 * * *"  # Every 6 hours

    # Data retention
    retention_days: int = 365  # Keep data for 1 year

    @classmethod
    def default(cls) -> "WorkflowConfig":
        """Create default configuration from environment.

        Raises:
            ConfigurationError: If required environment variables are missing
        """
        return cls(supabase=SupabaseConfig.from_env(), scraping=ScrapingConfig())

    @classmethod
    def for_testing(cls) -> "WorkflowConfig":
        """Create configuration for testing without requiring env vars."""
        return cls(
            supabase=SupabaseConfig.from_env(require_credentials=False),
            scraping=ScrapingConfig()
        )

    def to_serializable_dict(self) -> dict:
        """Convert to a JSON-serializable dictionary"""
        return {
            "supabase": {
                "url": self.supabase.url,
                "has_service_key": bool(self.supabase.service_role_key),
                # Don't include actual keys for security
            },
            "scraping": {
                "request_delay": self.scraping.request_delay,
                "max_retries": self.scraping.max_retries,
                "timeout": self.scraping.timeout,
                "user_agent": self.scraping.user_agent,
                "us_congress_sources": self.scraping.us_congress_sources,
                "eu_sources": self.scraping.eu_sources,
            },
            "cron_schedule": self.cron_schedule,
            "retention_days": self.retention_days,
        }
