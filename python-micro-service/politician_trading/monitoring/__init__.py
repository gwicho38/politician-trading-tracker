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

# Import alerting if available
try:
    from .alerting import (
        Alert,
        AlertSeverity,
        AlertChannel,
        EmailAlertChannel,
        SlackAlertChannel,
        DiscordAlertChannel,
        WebhookAlertChannel,
        AlertManager,
        get_alert_manager,
        send_alert,
    )

    __all__ = [
        "ScraperMonitor",
        "ScraperMetrics",
        "HealthStatus",
        "get_monitor",
        "record_scraper_success",
        "record_scraper_failure",
        "get_scraper_health_summary",
        # Alerting
        "Alert",
        "AlertSeverity",
        "AlertChannel",
        "EmailAlertChannel",
        "SlackAlertChannel",
        "DiscordAlertChannel",
        "WebhookAlertChannel",
        "AlertManager",
        "get_alert_manager",
        "send_alert",
    ]
except ImportError:
    __all__ = [
        "ScraperMonitor",
        "ScraperMetrics",
        "HealthStatus",
        "get_monitor",
        "record_scraper_success",
        "record_scraper_failure",
        "get_scraper_health_summary",
    ]
