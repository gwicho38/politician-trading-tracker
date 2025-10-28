"""
Configuration for politician trading data workflow
"""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class SupabaseConfig:
    """Supabase database configuration"""

    url: str
    key: str
    service_role_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> "SupabaseConfig":
        """Load configuration from environment or use provided values"""
        # Your provided Supabase details
        url = os.getenv("SUPABASE_URL", "https://uljsqvwkomdrlnofmlad.supabase.co")
        key = os.getenv(
            "SUPABASE_ANON_KEY",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsanNxdndrb21kcmxub2ZtbGFkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4MDIyNDQsImV4cCI6MjA3MjM3ODI0NH0.QCpfcEpxGX_5Wn8ljf_J2KWjJLGdF8zRsV_7OatxmHI",
        )
        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        return cls(url=url, key=key, service_role_key=service_role_key)


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
    """Overall workflow configuration"""

    supabase: SupabaseConfig
    scraping: ScrapingConfig

    # Cron schedule (for reference, actual scheduling done in Supabase)
    cron_schedule: str = "0 */6 * * *"  # Every 6 hours

    # Data retention
    retention_days: int = 365  # Keep data for 1 year

    @classmethod
    def default(cls) -> "WorkflowConfig":
        """Create default configuration"""
        return cls(supabase=SupabaseConfig.from_env(), scraping=ScrapingConfig())

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
