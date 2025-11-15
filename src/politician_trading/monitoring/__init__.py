"""
Monitoring and observability for politician trading tracker

This module provides monitoring, health checks, and alerting for scrapers.
"""

from .scraper_monitor import (
    ScraperMonitor,
    ScraperMetrics,
    HealthStatus,
    get_monitor,
    record_scraper_success,
    record_scraper_failure,
    get_scraper_health_summary,
)

__all__ = [
    "ScraperMonitor",
    "ScraperMetrics",
    "HealthStatus",
    "get_monitor",
    "record_scraper_success",
    "record_scraper_failure",
    "get_scraper_health_summary",
]
