"""
Automated alerting system for scraper failures and issues

This module provides multi-channel alerting (email, Slack, Discord, webhooks)
for proactive notification of scraper failures and degraded performance.
"""

import asyncio
import logging
import os
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Any
from enum import Enum

import aiohttp

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert message structure"""
    title: str
    message: str
    severity: AlertSeverity
    scraper_name: str
    timestamp: datetime
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            "title": self.title,
            "message": self.message,
            "severity": self.severity.value,
            "scraper_name": self.scraper_name,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {},
        }


class AlertChannel(ABC):
    """Abstract base class for alert channels"""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    @abstractmethod
    async def send_alert(self, alert: Alert) -> bool:
        """
        Send alert through this channel

        Args:
            alert: Alert to send

        Returns:
            True if sent successfully, False otherwise
        """
        pass

    def should_send(self, alert: Alert) -> bool:
        """
        Determine if alert should be sent based on severity and settings

        Override this method to implement channel-specific filtering
        """
        if not self.enabled:
            return False
        return True


class EmailAlertChannel(AlertChannel):
    """Email alert channel using SMTP"""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: Optional[str] = None,
        to_emails: Optional[List[str]] = None,
        use_tls: bool = True,
        enabled: bool = True,
    ):
        super().__init__(enabled)
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.from_email = from_email or os.getenv("ALERT_FROM_EMAIL", self.smtp_user)
        self.to_emails = to_emails or (os.getenv("ALERT_TO_EMAILS", "").split(",") if os.getenv("ALERT_TO_EMAILS") else [])
        self.use_tls = use_tls

        # Disable if credentials not configured
        if not all([self.smtp_user, self.smtp_password, self.to_emails]):
            self.enabled = False
            logger.info("Email alerting disabled - missing credentials")

    async def send_alert(self, alert: Alert) -> bool:
        """Send alert via email"""
        if not self.should_send(alert):
            return False

        try:
            # Build email
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[{alert.severity.value.upper()}] {alert.title}"
            msg["From"] = self.from_email
            msg["To"] = ", ".join(self.to_emails)

            # Create text and HTML versions
            text_content = self._format_text_email(alert)
            html_content = self._format_html_email(alert)

            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            # Send email (in thread pool to avoid blocking)
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._send_smtp,
                msg
            )

            logger.info(f"Sent email alert for {alert.scraper_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False

    def _send_smtp(self, msg: MIMEMultipart):
        """Send email via SMTP (blocking call)"""
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.use_tls:
                server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)

    def _format_text_email(self, alert: Alert) -> str:
        """Format alert as plain text email"""
        return f"""
Politician Trading Tracker Alert

Severity: {alert.severity.value.upper()}
Scraper: {alert.scraper_name}
Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}

{alert.title}

{alert.message}

---
This is an automated alert from Politician Trading Tracker monitoring system.
"""

    def _format_html_email(self, alert: Alert) -> str:
        """Format alert as HTML email"""
        severity_colors = {
            AlertSeverity.LOW: "#28a745",
            AlertSeverity.MEDIUM: "#ffc107",
            AlertSeverity.HIGH: "#fd7e14",
            AlertSeverity.CRITICAL: "#dc3545",
        }
        color = severity_colors.get(alert.severity, "#6c757d")

        return f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
        .alert-box {{ border-left: 4px solid {color}; padding: 15px; background: #f8f9fa; }}
        .alert-header {{ color: {color}; font-weight: bold; font-size: 18px; }}
        .alert-meta {{ color: #6c757d; font-size: 14px; margin: 10px 0; }}
        .alert-message {{ margin: 15px 0; }}
    </style>
</head>
<body>
    <div class="alert-box">
        <div class="alert-header">{alert.title}</div>
        <div class="alert-meta">
            <strong>Severity:</strong> {alert.severity.value.upper()}<br>
            <strong>Scraper:</strong> {alert.scraper_name}<br>
            <strong>Time:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
        </div>
        <div class="alert-message">{alert.message}</div>
    </div>
    <p style="color: #6c757d; font-size: 12px;">
        This is an automated alert from Politician Trading Tracker monitoring system.
    </p>
</body>
</html>
"""


class SlackAlertChannel(AlertChannel):
    """Slack alert channel using webhooks"""

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        channel: Optional[str] = None,
        username: str = "Scraper Monitor",
        enabled: bool = True,
    ):
        super().__init__(enabled)
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.channel = channel or os.getenv("SLACK_CHANNEL")
        self.username = username

        if not self.webhook_url:
            self.enabled = False
            logger.info("Slack alerting disabled - no webhook URL configured")

    async def send_alert(self, alert: Alert) -> bool:
        """Send alert to Slack"""
        if not self.should_send(alert):
            return False

        try:
            payload = self._format_slack_message(alert)

            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Sent Slack alert for {alert.scraper_name}")
                        return True
                    else:
                        logger.error(f"Slack API returned {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False

    def _format_slack_message(self, alert: Alert) -> Dict[str, Any]:
        """Format alert as Slack message"""
        severity_colors = {
            AlertSeverity.LOW: "#28a745",
            AlertSeverity.MEDIUM: "#ffc107",
            AlertSeverity.HIGH: "#fd7e14",
            AlertSeverity.CRITICAL: "#dc3545",
        }
        color = severity_colors.get(alert.severity, "#6c757d")

        severity_emoji = {
            AlertSeverity.LOW: "ℹ️",
            AlertSeverity.MEDIUM: "⚠️",
            AlertSeverity.HIGH: "🔴",
            AlertSeverity.CRITICAL: "🚨",
        }
        emoji = severity_emoji.get(alert.severity, "📢")

        payload = {
            "username": self.username,
            "attachments": [
                {
                    "color": color,
                    "title": f"{emoji} {alert.title}",
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Scraper",
                            "value": alert.scraper_name,
                            "short": True
                        },
                        {
                            "title": "Severity",
                            "value": alert.severity.value.upper(),
                            "short": True
                        },
                        {
                            "title": "Time",
                            "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
                            "short": False
                        }
                    ],
                    "footer": "Politician Trading Tracker",
                    "ts": int(alert.timestamp.timestamp())
                }
            ]
        }

        if self.channel:
            payload["channel"] = self.channel

        return payload


class DiscordAlertChannel(AlertChannel):
    """Discord alert channel using webhooks"""

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        username: str = "Scraper Monitor",
        enabled: bool = True,
    ):
        super().__init__(enabled)
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
        self.username = username

        if not self.webhook_url:
            self.enabled = False
            logger.info("Discord alerting disabled - no webhook URL configured")

    async def send_alert(self, alert: Alert) -> bool:
        """Send alert to Discord"""
        if not self.should_send(alert):
            return False

        try:
            payload = self._format_discord_message(alert)

            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status in [200, 204]:
                        logger.info(f"Sent Discord alert for {alert.scraper_name}")
                        return True
                    else:
                        logger.error(f"Discord API returned {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
            return False

    def _format_discord_message(self, alert: Alert) -> Dict[str, Any]:
        """Format alert as Discord message"""
        severity_colors = {
            AlertSeverity.LOW: 0x28a745,
            AlertSeverity.MEDIUM: 0xffc107,
            AlertSeverity.HIGH: 0xfd7e14,
            AlertSeverity.CRITICAL: 0xdc3545,
        }
        color = severity_colors.get(alert.severity, 0x6c757d)

        return {
            "username": self.username,
            "embeds": [
                {
                    "title": alert.title,
                    "description": alert.message,
                    "color": color,
                    "fields": [
                        {
                            "name": "Scraper",
                            "value": alert.scraper_name,
                            "inline": True
                        },
                        {
                            "name": "Severity",
                            "value": alert.severity.value.upper(),
                            "inline": True
                        },
                        {
                            "name": "Time",
                            "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
                            "inline": False
                        }
                    ],
                    "footer": {
                        "text": "Politician Trading Tracker"
                    },
                    "timestamp": alert.timestamp.isoformat()
                }
            ]
        }


class WebhookAlertChannel(AlertChannel):
    """Generic webhook alert channel"""

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        enabled: bool = True,
    ):
        super().__init__(enabled)
        self.webhook_url = webhook_url or os.getenv("ALERT_WEBHOOK_URL")
        self.headers = headers or {}

        if not self.webhook_url:
            self.enabled = False
            logger.info("Webhook alerting disabled - no webhook URL configured")

    async def send_alert(self, alert: Alert) -> bool:
        """Send alert to webhook"""
        if not self.should_send(alert):
            return False

        try:
            payload = alert.to_dict()

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers=self.headers
                ) as response:
                    if response.status in [200, 201, 202, 204]:
                        logger.info(f"Sent webhook alert for {alert.scraper_name}")
                        return True
                    else:
                        logger.error(f"Webhook returned {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False


class AlertManager:
    """
    Central alert management system

    Manages multiple alert channels and routes alerts based on configuration.
    """

    def __init__(self):
        self.channels: List[AlertChannel] = []
        self._initialize_channels()

    def _initialize_channels(self):
        """Initialize alert channels from environment configuration"""
        # Email channel
        email_channel = EmailAlertChannel()
        if email_channel.enabled:
            self.channels.append(email_channel)
            logger.info("Email alerting enabled")

        # Slack channel
        slack_channel = SlackAlertChannel()
        if slack_channel.enabled:
            self.channels.append(slack_channel)
            logger.info("Slack alerting enabled")

        # Discord channel
        discord_channel = DiscordAlertChannel()
        if discord_channel.enabled:
            self.channels.append(discord_channel)
            logger.info("Discord alerting enabled")

        # Generic webhook
        webhook_channel = WebhookAlertChannel()
        if webhook_channel.enabled:
            self.channels.append(webhook_channel)
            logger.info("Webhook alerting enabled")

        if not self.channels:
            logger.warning(
                "No alert channels configured. Set environment variables to enable:\n"
                "  Email: SMTP_HOST, SMTP_USER, SMTP_PASSWORD, ALERT_TO_EMAILS\n"
                "  Slack: SLACK_WEBHOOK_URL\n"
                "  Discord: DISCORD_WEBHOOK_URL\n"
                "  Webhook: ALERT_WEBHOOK_URL"
            )

    def add_channel(self, channel: AlertChannel):
        """Add a custom alert channel"""
        self.channels.append(channel)
        logger.info(f"Added alert channel: {channel.__class__.__name__}")

    async def send_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        scraper_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, bool]:
        """
        Send alert through all configured channels

        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity level
            scraper_name: Name of scraper that triggered alert
            metadata: Optional additional metadata

        Returns:
            Dict mapping channel name to success status
        """
        alert = Alert(
            title=title,
            message=message,
            severity=severity,
            scraper_name=scraper_name,
            timestamp=datetime.utcnow(),
            metadata=metadata
        )

        results = {}
        tasks = []
        channel_names = []

        for channel in self.channels:
            channel_name = channel.__class__.__name__
            channel_names.append(channel_name)
            tasks.append(channel.send_alert(alert))

        # Send to all channels concurrently
        if tasks:
            send_results = await asyncio.gather(*tasks, return_exceptions=True)

            for channel_name, result in zip(channel_names, send_results):
                if isinstance(result, Exception):
                    logger.error(f"Alert channel {channel_name} raised exception: {result}")
                    results[channel_name] = False
                else:
                    results[channel_name] = result

        return results


# Global alert manager instance
_alert_manager = AlertManager()


def get_alert_manager() -> AlertManager:
    """Get the global alert manager instance"""
    return _alert_manager


async def send_alert(
    title: str,
    message: str,
    severity: AlertSeverity = AlertSeverity.MEDIUM,
    scraper_name: str = "System",
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, bool]:
    """
    Send alert through all configured channels

    Args:
        title: Alert title
        message: Alert message
        severity: Alert severity level (default: MEDIUM)
        scraper_name: Name of scraper that triggered alert
        metadata: Optional additional metadata

    Returns:
        Dict mapping channel name to success status
    """
    return await _alert_manager.send_alert(
        title=title,
        message=message,
        severity=severity,
        scraper_name=scraper_name,
        metadata=metadata
    )
