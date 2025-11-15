# Alerting System Configuration Guide

## Overview

The politician-trading-tracker monitoring system includes automated alerting through multiple channels. Alerts are automatically sent when scrapers fail, produce errors, or show degraded performance.

## Supported Alert Channels

### 1. Email (SMTP)
### 2. Slack (Webhooks)
### 3. Discord (Webhooks)
### 4. Generic Webhooks

---

## Configuration

Alerts are configured via environment variables. Set these in your `.env` file or deployment environment.

### Email Configuration

**Required Environment Variables:**
```bash
# SMTP Server Configuration
SMTP_HOST=smtp.gmail.com          # SMTP server hostname
SMTP_PORT=587                      # SMTP port (587 for TLS, 465 for SSL)
SMTP_USER=your-email@gmail.com     # SMTP username (usually your email)
SMTP_PASSWORD=your-app-password    # SMTP password or app-specific password

# Alert Recipients
ALERT_FROM_EMAIL=alerts@yourdomain.com  # From address (optional, defaults to SMTP_USER)
ALERT_TO_EMAILS=admin@yourdomain.com,ops@yourdomain.com  # Comma-separated list of recipients
```

**Example: Gmail Configuration**

1. **Enable 2-Factor Authentication** in your Google Account
2. **Generate App Password**:
   - Go to Google Account → Security
   - Under "Signing in to Google", select "App passwords"
   - Generate password for "Mail"
3. **Set Environment Variables**:
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=generated-app-password
ALERT_TO_EMAILS=recipient1@example.com,recipient2@example.com
```

**Example: AWS SES Configuration**
```bash
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USER=your-ses-smtp-username
SMTP_PASSWORD=your-ses-smtp-password
ALERT_FROM_EMAIL=noreply@yourdomain.com
ALERT_TO_EMAILS=ops-team@yourdomain.com
```

---

### Slack Configuration

**Required Environment Variables:**
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_CHANNEL=#monitoring  # Optional, defaults to webhook's default channel
```

**Setup Instructions:**

1. **Create Slack Webhook**:
   - Go to https://api.slack.com/messaging/webhooks
   - Click "Create your Slack app"
   - Choose "From scratch"
   - Name your app (e.g., "Scraper Monitor")
   - Select your workspace
   - Navigate to "Incoming Webhooks"
   - Activate Incoming Webhooks
   - Click "Add New Webhook to Workspace"
   - Select channel and authorize

2. **Copy Webhook URL** and set environment variable:
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
```

**Message Format:**
- Color-coded based on severity (green=low, yellow=medium, orange=high, red=critical)
- Includes scraper name, severity, timestamp
- Formatted as Slack attachment for better visibility

---

### Discord Configuration

**Required Environment Variables:**
```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR/WEBHOOK/URL
```

**Setup Instructions:**

1. **Create Discord Webhook**:
   - Open Discord and go to your server
   - Click on channel settings (gear icon)
   - Go to "Integrations"
   - Click "Webhooks" → "New Webhook"
   - Name your webhook (e.g., "Scraper Monitor")
   - Select channel
   - Copy webhook URL

2. **Set Environment Variable**:
```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/abcdefghijklmnop
```

**Message Format:**
- Rich embeds with color-coding
- Includes scraper name, severity, timestamp
- Formatted for Discord's embed system

---

### Generic Webhook Configuration

For custom alerting systems or other services that accept webhooks.

**Required Environment Variables:**
```bash
ALERT_WEBHOOK_URL=https://your-custom-endpoint.com/alerts
```

**Optional Headers:**
```python
# Set via custom code, not environment variables
from politician_trading.monitoring import get_alert_manager, WebhookAlertChannel

# Create custom webhook with headers
webhook = WebhookAlertChannel(
    webhook_url="https://api.example.com/alerts",
    headers={
        "Authorization": "Bearer your-api-key",
        "Content-Type": "application/json"
    }
)

# Add to alert manager
alert_manager = get_alert_manager()
alert_manager.add_channel(webhook)
```

**Payload Format:**
```json
{
  "title": "Scraper Failing: US_Congress",
  "message": "3 consecutive failures. Last error: Connection timeout",
  "severity": "high",
  "scraper_name": "US_Congress",
  "timestamp": "2024-01-15T10:30:00",
  "metadata": {
    "alert_type": "consecutive_failures"
  }
}
```

---

## Alert Types

### 1. Consecutive Failures
**Trigger**: 3+ consecutive scraper failures
**Severity**: HIGH
**Example**: "Scraper Failing: US_Congress - 3 consecutive failures"

### 2. Low Success Rate
**Trigger**: Success rate < 50% (after at least 10 runs)
**Severity**: HIGH
**Example**: "Low Success Rate: California_NetFile - Success rate: 35.0%"

### 3. Stale Data
**Trigger**: No successful run in > 24 hours
**Severity**: MEDIUM
**Example**: "Stale Data: UK_Parliament - No successful run in 26.3 hours"

### 4. Circuit Breaker Open
**Trigger**: Circuit breaker opens due to repeated failures
**Severity**: HIGH
**Example**: "Circuit Breaker Open: Texas_Ethics - Circuit breaker opened after 5 failures"

---

## Testing Alerts

### Test Email Configuration

```python
import asyncio
from politician_trading.monitoring import send_alert, AlertSeverity

async def test_email_alert():
    """Test email alerting"""
    results = await send_alert(
        title="Test Alert",
        message="This is a test alert from the monitoring system.",
        severity=AlertSeverity.LOW,
        scraper_name="TestScraper"
    )
    print(f"Alert sent: {results}")

# Run test
asyncio.run(test_email_alert())
```

### Test Slack Configuration

```python
import asyncio
from politician_trading.monitoring import send_alert, AlertSeverity

async def test_slack_alert():
    """Test Slack alerting"""
    results = await send_alert(
        title="🧪 Test Alert",
        message="Testing Slack integration for scraper monitoring.",
        severity=AlertSeverity.MEDIUM,
        scraper_name="TestScraper"
    )
    print(f"Slack alert sent: {results}")

asyncio.run(test_slack_alert())
```

### Test All Channels

```python
import asyncio
from politician_trading.monitoring import get_alert_manager, AlertSeverity

async def test_all_channels():
    """Test all configured alert channels"""
    manager = get_alert_manager()

    # Send test alert
    results = await manager.send_alert(
        title="System Test",
        message="Testing all configured alert channels.",
        severity=AlertSeverity.LOW,
        scraper_name="System",
        metadata={"test": True}
    )

    # Print results
    for channel, success in results.items():
        status = "✓ Success" if success else "✗ Failed"
        print(f"{channel}: {status}")

asyncio.run(test_all_channels())
```

---

## Alert Suppression

Duplicate alerts are automatically suppressed:
- Same scraper + same alert type within 1 hour = suppressed
- This prevents alert spam during ongoing issues

---

## Monitoring Integration

Alerts are automatically integrated with the monitoring system:

```python
from politician_trading.monitoring import record_scraper_failure

# This will automatically trigger alerts if thresholds are exceeded
record_scraper_failure("MyScraper", "Connection timeout")
```

No additional code needed - alerts are sent automatically based on:
- Consecutive failure count
- Success rate
- Data staleness
- Circuit breaker state

---

## Security Best Practices

### 1. Protect Credentials
- **NEVER** commit credentials to git
- Use environment variables or secret managers
- Rotate credentials regularly

### 2. Use App-Specific Passwords
- For Gmail, use app passwords (not your main password)
- For AWS SES, use IAM credentials with minimal permissions

### 3. Limit Webhook Access
- Use webhook URLs with authentication if possible
- Rotate webhook URLs if compromised
- Monitor webhook usage for anomalies

### 4. Validate Recipients
- Only send alerts to authorized recipients
- Review recipient lists regularly
- Remove former team members promptly

---

## Troubleshooting

### Email Alerts Not Working

**Check 1: Credentials**
```bash
echo $SMTP_USER
echo $SMTP_PASSWORD  # Should not be empty
echo $ALERT_TO_EMAILS
```

**Check 2: Test SMTP Connection**
```python
import smtplib

try:
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login("your-email@gmail.com", "your-app-password")
    print("✓ SMTP connection successful")
    server.quit()
except Exception as e:
    print(f"✗ SMTP connection failed: {e}")
```

**Check 3: Firewall/Network**
- Ensure outbound port 587 (or 465) is open
- Check if your network blocks SMTP

**Check 4: Logs**
```bash
# Check application logs for error messages
tail -f logs/politician_trading.log | grep -i "email\|smtp\|alert"
```

### Slack Alerts Not Working

**Check 1: Webhook URL**
```bash
echo $SLACK_WEBHOOK_URL
# Should start with https://hooks.slack.com/services/
```

**Check 2: Test Webhook**
```bash
curl -X POST $SLACK_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{"text":"Test message from politician-trading-tracker"}'
```

**Check 3: Webhook Permissions**
- Ensure webhook is still active in Slack settings
- Check if app was removed from workspace

### Discord Alerts Not Working

Similar to Slack - verify webhook URL and test with curl:
```bash
curl -X POST $DISCORD_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{"content":"Test message from politician-trading-tracker"}'
```

### No Alerts Being Sent

**Check 1: Alert Thresholds**
```python
from politician_trading.monitoring import get_monitor

monitor = get_monitor()
print(f"Alert thresholds: {monitor.alert_thresholds}")
```

**Check 2: Alert Manager Initialization**
```python
from politician_trading.monitoring import get_alert_manager

manager = get_alert_manager()
print(f"Configured channels: {len(manager.channels)}")
for channel in manager.channels:
    print(f"- {channel.__class__.__name__}: {'enabled' if channel.enabled else 'disabled'}")
```

**Check 3: Enable Debug Logging**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Advanced Configuration

### Custom Alert Channel

Create your own alert channel by extending `AlertChannel`:

```python
from politician_trading.monitoring.alerting import AlertChannel, Alert

class CustomAlertChannel(AlertChannel):
    """Custom alert channel implementation"""

    async def send_alert(self, alert: Alert) -> bool:
        """Send alert through custom service"""
        if not self.should_send(alert):
            return False

        try:
            # Your custom alerting logic here
            # e.g., send to PagerDuty, Datadog, custom API, etc.
            print(f"Custom alert: {alert.title}")
            return True
        except Exception as e:
            logger.error(f"Custom alert failed: {e}")
            return False

# Add to alert manager
from politician_trading.monitoring import get_alert_manager

manager = get_alert_manager()
manager.add_channel(CustomAlertChannel(enabled=True))
```

### Conditional Alerting

Filter alerts based on custom criteria:

```python
class FilteredSlackChannel(SlackAlertChannel):
    """Slack channel that only sends high-severity alerts"""

    def should_send(self, alert: Alert) -> bool:
        """Only send high and critical severity alerts"""
        if not super().should_send(alert):
            return False

        return alert.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]
```

---

## Example .env File

```bash
# Email Alerts (Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=monitoring@example.com
SMTP_PASSWORD=your-gmail-app-password
ALERT_TO_EMAILS=ops@example.com,admin@example.com

# Slack Alerts
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
SLACK_CHANNEL=#monitoring

# Discord Alerts
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/abcdefghijklmnop

# Generic Webhook (Optional)
ALERT_WEBHOOK_URL=https://your-monitoring-system.com/webhook

# Application Settings
LOG_LEVEL=INFO
```

---

## Summary

**Quick Start:**
1. Set environment variables for desired channel(s)
2. Restart application
3. Test with provided test scripts
4. Alerts will be sent automatically when issues occur

**Best Practices:**
- Configure at least 2 channels for redundancy
- Test all channels after configuration
- Monitor alert volume to avoid fatigue
- Review and tune alert thresholds as needed

**Support:**
- Check logs for detailed error messages
- Review troubleshooting section
- Test individual channels in isolation
- Verify network connectivity and credentials
