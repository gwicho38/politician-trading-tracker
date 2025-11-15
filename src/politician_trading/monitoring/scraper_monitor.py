"""
Scraper health monitoring and alerting system

This module provides comprehensive monitoring of scraper performance,
error tracking, and alerting for failures.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Scraper health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class ScraperMetrics:
    """Metrics for a single scraper"""
    scraper_name: str
    last_run_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None

    # Counters
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    records_scraped_total: int = 0

    # Recent performance
    last_run_duration_seconds: Optional[float] = None
    average_run_duration_seconds: float = 0.0
    last_error_message: Optional[str] = None
    consecutive_failures: int = 0

    # Circuit breaker state
    circuit_breaker_state: Optional[str] = None
    circuit_breaker_failures: int = 0

    def update_success(self, records_scraped: int, duration_seconds: float):
        """Update metrics after successful run"""
        self.last_run_time = datetime.now()
        self.last_success_time = datetime.now()
        self.total_runs += 1
        self.successful_runs += 1
        self.records_scraped_total += records_scraped
        self.last_run_duration_seconds = duration_seconds
        self.consecutive_failures = 0

        # Update rolling average
        if self.average_run_duration_seconds == 0:
            self.average_run_duration_seconds = duration_seconds
        else:
            # Exponential moving average
            alpha = 0.3
            self.average_run_duration_seconds = (
                alpha * duration_seconds +
                (1 - alpha) * self.average_run_duration_seconds
            )

    def update_failure(self, error_message: str, duration_seconds: Optional[float] = None):
        """Update metrics after failed run"""
        self.last_run_time = datetime.now()
        self.last_failure_time = datetime.now()
        self.total_runs += 1
        self.failed_runs += 1
        self.last_error_message = error_message
        self.consecutive_failures += 1

        if duration_seconds:
            self.last_run_duration_seconds = duration_seconds

    def get_success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_runs == 0:
            return 0.0
        return self.successful_runs / self.total_runs

    def get_health_status(self) -> HealthStatus:
        """Determine current health status"""
        # Never run
        if self.total_runs == 0:
            return HealthStatus.UNKNOWN

        # Multiple consecutive failures
        if self.consecutive_failures >= 5:
            return HealthStatus.DOWN
        elif self.consecutive_failures >= 3:
            return HealthStatus.FAILING

        # Check last success time
        if self.last_success_time:
            time_since_success = (datetime.now() - self.last_success_time).total_seconds()
            # No success in 24 hours
            if time_since_success > 86400:
                return HealthStatus.FAILING
            # No success in 6 hours
            elif time_since_success > 21600:
                return HealthStatus.DEGRADED

        # Check success rate
        success_rate = self.get_success_rate()
        if success_rate < 0.5:
            return HealthStatus.FAILING
        elif success_rate < 0.8:
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "scraper_name": self.scraper_name,
            "health_status": self.get_health_status().value,
            "last_run_time": self.last_run_time.isoformat() if self.last_run_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "success_rate": self.get_success_rate(),
            "records_scraped_total": self.records_scraped_total,
            "consecutive_failures": self.consecutive_failures,
            "last_run_duration_seconds": self.last_run_duration_seconds,
            "average_run_duration_seconds": self.average_run_duration_seconds,
            "last_error_message": self.last_error_message,
            "circuit_breaker_state": self.circuit_breaker_state,
            "circuit_breaker_failures": self.circuit_breaker_failures,
        }


class ScraperMonitor:
    """
    Central monitoring system for all scrapers

    Tracks performance metrics, health status, and triggers alerts
    for scraper failures and degraded performance.
    """

    def __init__(self, enable_external_alerts: bool = True):
        self.scrapers: Dict[str, ScraperMetrics] = {}
        self.alerts: List[Dict[str, Any]] = []
        self.alert_thresholds = {
            "consecutive_failures": 3,
            "max_failure_rate": 0.5,
            "max_age_hours": 24,
        }
        self.enable_external_alerts = enable_external_alerts

        # Import alerting here to avoid circular imports
        if enable_external_alerts:
            try:
                from .alerting import get_alert_manager, AlertSeverity
                self.alert_manager = get_alert_manager()
                self.AlertSeverity = AlertSeverity
                logger.info("External alerting enabled")
            except ImportError:
                logger.warning("Alerting module not available - external alerts disabled")
                self.enable_external_alerts = False

    def get_or_create_metrics(self, scraper_name: str) -> ScraperMetrics:
        """Get existing metrics or create new ones"""
        if scraper_name not in self.scrapers:
            self.scrapers[scraper_name] = ScraperMetrics(scraper_name=scraper_name)
        return self.scrapers[scraper_name]

    def record_success(self, scraper_name: str, records_scraped: int, duration_seconds: float):
        """Record successful scraper run"""
        metrics = self.get_or_create_metrics(scraper_name)
        metrics.update_success(records_scraped, duration_seconds)

        logger.info(
            f"Scraper '{scraper_name}' succeeded: "
            f"{records_scraped} records in {duration_seconds:.2f}s"
        )

        # Clear any existing alerts for this scraper
        self._clear_alerts(scraper_name)

    def record_failure(
        self,
        scraper_name: str,
        error_message: str,
        duration_seconds: Optional[float] = None
    ):
        """Record failed scraper run"""
        metrics = self.get_or_create_metrics(scraper_name)
        metrics.update_failure(error_message, duration_seconds)

        logger.error(
            f"Scraper '{scraper_name}' failed: {error_message} "
            f"(consecutive failures: {metrics.consecutive_failures})"
        )

        # Check if we should trigger an alert
        self._check_and_trigger_alert(scraper_name, metrics)

    def update_circuit_breaker_state(
        self,
        scraper_name: str,
        state: str,
        failure_count: int
    ):
        """Update circuit breaker state for a scraper"""
        metrics = self.get_or_create_metrics(scraper_name)
        metrics.circuit_breaker_state = state
        metrics.circuit_breaker_failures = failure_count

        if state == "open":
            logger.warning(
                f"Circuit breaker OPEN for '{scraper_name}' "
                f"after {failure_count} failures"
            )
            self._trigger_alert(
                scraper_name,
                "circuit_breaker_open",
                f"Circuit breaker opened after {failure_count} failures"
            )

    def get_scraper_health(self, scraper_name: str) -> Dict[str, Any]:
        """Get health status for a specific scraper"""
        if scraper_name not in self.scrapers:
            return {"scraper_name": scraper_name, "status": "unknown", "message": "No metrics available"}

        metrics = self.scrapers[scraper_name]
        return {
            "scraper_name": scraper_name,
            "status": metrics.get_health_status().value,
            "metrics": metrics.to_dict(),
        }

    def get_all_health(self) -> Dict[str, Any]:
        """Get health status for all scrapers"""
        overall_status = HealthStatus.HEALTHY
        scraper_health = {}

        for name, metrics in self.scrapers.items():
            health = metrics.get_health_status()
            scraper_health[name] = metrics.to_dict()

            # Determine overall status (worst status wins)
            if health == HealthStatus.DOWN:
                overall_status = HealthStatus.DOWN
            elif health == HealthStatus.FAILING and overall_status != HealthStatus.DOWN:
                overall_status = HealthStatus.FAILING
            elif health == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED

        # Calculate aggregate statistics
        total_runs = sum(m.total_runs for m in self.scrapers.values())
        total_successes = sum(m.successful_runs for m in self.scrapers.values())
        total_records = sum(m.records_scraped_total for m in self.scrapers.values())

        return {
            "overall_status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "scrapers": scraper_health,
            "summary": {
                "total_scrapers": len(self.scrapers),
                "healthy": sum(1 for m in self.scrapers.values() if m.get_health_status() == HealthStatus.HEALTHY),
                "degraded": sum(1 for m in self.scrapers.values() if m.get_health_status() == HealthStatus.DEGRADED),
                "failing": sum(1 for m in self.scrapers.values() if m.get_health_status() == HealthStatus.FAILING),
                "down": sum(1 for m in self.scrapers.values() if m.get_health_status() == HealthStatus.DOWN),
                "total_runs": total_runs,
                "total_successes": total_successes,
                "total_records_scraped": total_records,
                "overall_success_rate": total_successes / total_runs if total_runs > 0 else 0.0,
            },
            "active_alerts": len(self.alerts),
        }

    def get_alerts(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        alerts = sorted(self.alerts, key=lambda x: x["timestamp"], reverse=True)
        if limit:
            return alerts[:limit]
        return alerts

    def _check_and_trigger_alert(self, scraper_name: str, metrics: ScraperMetrics):
        """Check if alert should be triggered and trigger if needed"""
        # Alert on consecutive failures
        if metrics.consecutive_failures >= self.alert_thresholds["consecutive_failures"]:
            self._trigger_alert(
                scraper_name,
                "consecutive_failures",
                f"{metrics.consecutive_failures} consecutive failures. Last error: {metrics.last_error_message}"
            )

        # Alert on low success rate
        if metrics.total_runs >= 10:  # Only after enough runs
            success_rate = metrics.get_success_rate()
            if success_rate < self.alert_thresholds["max_failure_rate"]:
                self._trigger_alert(
                    scraper_name,
                    "low_success_rate",
                    f"Success rate: {success_rate:.1%} (threshold: {self.alert_thresholds['max_failure_rate']:.1%})"
                )

        # Alert on staleness
        if metrics.last_success_time:
            hours_since_success = (datetime.now() - metrics.last_success_time).total_seconds() / 3600
            if hours_since_success > self.alert_thresholds["max_age_hours"]:
                self._trigger_alert(
                    scraper_name,
                    "stale_data",
                    f"No successful run in {hours_since_success:.1f} hours"
                )

    def _trigger_alert(self, scraper_name: str, alert_type: str, message: str):
        """Trigger an alert and send via configured channels"""
        # Check if similar alert already exists
        for alert in self.alerts:
            if (alert["scraper_name"] == scraper_name and
                alert["alert_type"] == alert_type and
                (datetime.now() - alert["timestamp"]).total_seconds() < 3600):  # Within last hour
                # Don't create duplicate alert
                return

        severity = self._get_alert_severity(alert_type)

        alert = {
            "scraper_name": scraper_name,
            "alert_type": alert_type,
            "message": message,
            "timestamp": datetime.now(),
            "severity": severity,
        }

        self.alerts.append(alert)
        logger.warning(f"ALERT [{severity}] {scraper_name}: {message}")

        # Send external alerts if enabled
        if self.enable_external_alerts and hasattr(self, 'alert_manager'):
            try:
                # Map severity string to AlertSeverity enum
                severity_map = {
                    "low": self.AlertSeverity.LOW,
                    "medium": self.AlertSeverity.MEDIUM,
                    "high": self.AlertSeverity.HIGH,
                    "critical": self.AlertSeverity.CRITICAL,
                }
                alert_severity = severity_map.get(severity, self.AlertSeverity.MEDIUM)

                # Create title based on alert type
                title_map = {
                    "consecutive_failures": f"Scraper Failing: {scraper_name}",
                    "low_success_rate": f"Low Success Rate: {scraper_name}",
                    "stale_data": f"Stale Data: {scraper_name}",
                    "circuit_breaker_open": f"Circuit Breaker Open: {scraper_name}",
                }
                title = title_map.get(alert_type, f"Alert: {scraper_name}")

                # Send alert asynchronously (fire and forget)
                asyncio.create_task(
                    self.alert_manager.send_alert(
                        title=title,
                        message=message,
                        severity=alert_severity,
                        scraper_name=scraper_name,
                        metadata={"alert_type": alert_type}
                    )
                )
            except Exception as e:
                logger.error(f"Failed to send external alert: {e}")

    def _clear_alerts(self, scraper_name: str):
        """Clear alerts for a scraper after successful run"""
        self.alerts = [a for a in self.alerts if a["scraper_name"] != scraper_name]

    def _get_alert_severity(self, alert_type: str) -> str:
        """Determine alert severity level"""
        severity_map = {
            "consecutive_failures": "high",
            "low_success_rate": "high",
            "stale_data": "medium",
            "circuit_breaker_open": "high",
            "unexpected_error": "medium",
        }
        return severity_map.get(alert_type, "low")

    def export_metrics(self, format: str = "json") -> str:
        """Export metrics in specified format"""
        data = self.get_all_health()

        if format == "json":
            return json.dumps(data, indent=2, default=str)
        elif format == "prometheus":
            # Prometheus exposition format
            lines = []
            for name, metrics_dict in data["scrapers"].items():
                safe_name = name.replace("-", "_").replace(" ", "_")
                lines.append(f"scraper_total_runs{{scraper=\"{name}\"}} {metrics_dict['total_runs']}")
                lines.append(f"scraper_successful_runs{{scraper=\"{name}\"}} {metrics_dict['successful_runs']}")
                lines.append(f"scraper_failed_runs{{scraper=\"{name}\"}} {metrics_dict['failed_runs']}")
                lines.append(f"scraper_records_total{{scraper=\"{name}\"}} {metrics_dict['records_scraped_total']}")
                lines.append(f"scraper_success_rate{{scraper=\"{name}\"}} {metrics_dict['success_rate']}")
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Global monitor instance
_monitor = ScraperMonitor()


def get_monitor() -> ScraperMonitor:
    """Get the global scraper monitor instance"""
    return _monitor


def record_scraper_success(scraper_name: str, records_scraped: int, duration_seconds: float):
    """Record successful scraper run to global monitor"""
    _monitor.record_success(scraper_name, records_scraped, duration_seconds)


def record_scraper_failure(scraper_name: str, error_message: str, duration_seconds: Optional[float] = None):
    """Record failed scraper run to global monitor"""
    _monitor.record_failure(scraper_name, error_message, duration_seconds)


def get_scraper_health_summary() -> Dict[str, Any]:
    """Get health summary for all scrapers"""
    return _monitor.get_all_health()
