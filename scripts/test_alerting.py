#!/usr/bin/env python3
"""
Test script for alert notification system

This script tests all configured alert channels and provides diagnostic information.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from politician_trading.monitoring import (
    get_alert_manager,
    send_alert,
    AlertSeverity
)


async def test_email_configuration():
    """Test email configuration"""
    print("\n" + "="*60)
    print("Testing Email Configuration")
    print("="*60)

    required_vars = ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "ALERT_TO_EMAILS"]
    configured = all(os.getenv(var) for var in required_vars)

    if configured:
        print("✓ Email environment variables configured")
        print(f"  SMTP_HOST: {os.getenv('SMTP_HOST')}")
        print(f"  SMTP_PORT: {os.getenv('SMTP_PORT', '587')}")
        print(f"  SMTP_USER: {os.getenv('SMTP_USER')}")
        print(f"  SMTP_PASSWORD: {'*' * len(os.getenv('SMTP_PASSWORD', ''))}")
        print(f"  ALERT_FROM_EMAIL: {os.getenv('ALERT_FROM_EMAIL', os.getenv('SMTP_USER'))}")
        print(f"  ALERT_TO_EMAILS: {os.getenv('ALERT_TO_EMAILS')}")

        # Send test email
        print("\nSending test email...")
        results = await send_alert(
            title="Test Email Alert",
            message="This is a test email from the politician-trading-tracker monitoring system.",
            severity=AlertSeverity.LOW,
            scraper_name="TestScript",
            metadata={"test": True, "channel": "email"}
        )

        if results.get("EmailAlertChannel"):
            print("✓ Test email sent successfully")
        else:
            print("✗ Test email failed")
            print("  Check logs for error details")
    else:
        print("✗ Email not configured")
        print("  Missing environment variables:")
        for var in required_vars:
            if not os.getenv(var):
                print(f"    - {var}")
        print("\n  Set these variables in your .env file or environment")


async def test_slack_configuration():
    """Test Slack configuration"""
    print("\n" + "="*60)
    print("Testing Slack Configuration")
    print("="*60)

    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    if webhook_url:
        print("✓ Slack webhook URL configured")
        print(f"  SLACK_WEBHOOK_URL: {webhook_url[:50]}...")
        if os.getenv("SLACK_CHANNEL"):
            print(f"  SLACK_CHANNEL: {os.getenv('SLACK_CHANNEL')}")

        # Send test message
        print("\nSending test Slack message...")
        results = await send_alert(
            title="🧪 Test Slack Alert",
            message="This is a test message from the politician-trading-tracker monitoring system.",
            severity=AlertSeverity.MEDIUM,
            scraper_name="TestScript",
            metadata={"test": True, "channel": "slack"}
        )

        if results.get("SlackAlertChannel"):
            print("✓ Test Slack message sent successfully")
            print("  Check your Slack channel for the message")
        else:
            print("✗ Test Slack message failed")
            print("  Check logs for error details")
    else:
        print("✗ Slack not configured")
        print("  Set SLACK_WEBHOOK_URL environment variable")


async def test_discord_configuration():
    """Test Discord configuration"""
    print("\n" + "="*60)
    print("Testing Discord Configuration")
    print("="*60)

    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    if webhook_url:
        print("✓ Discord webhook URL configured")
        print(f"  DISCORD_WEBHOOK_URL: {webhook_url[:50]}...")

        # Send test message
        print("\nSending test Discord message...")
        results = await send_alert(
            title="🧪 Test Discord Alert",
            message="This is a test message from the politician-trading-tracker monitoring system.",
            severity=AlertSeverity.HIGH,
            scraper_name="TestScript",
            metadata={"test": True, "channel": "discord"}
        )

        if results.get("DiscordAlertChannel"):
            print("✓ Test Discord message sent successfully")
            print("  Check your Discord channel for the message")
        else:
            print("✗ Test Discord message failed")
            print("  Check logs for error details")
    else:
        print("✗ Discord not configured")
        print("  Set DISCORD_WEBHOOK_URL environment variable")


async def test_webhook_configuration():
    """Test generic webhook configuration"""
    print("\n" + "="*60)
    print("Testing Generic Webhook Configuration")
    print("="*60)

    webhook_url = os.getenv("ALERT_WEBHOOK_URL")

    if webhook_url:
        print("✓ Generic webhook URL configured")
        print(f"  ALERT_WEBHOOK_URL: {webhook_url[:50]}...")

        # Send test message
        print("\nSending test webhook...")
        results = await send_alert(
            title="Test Webhook Alert",
            message="This is a test webhook from the politician-trading-tracker monitoring system.",
            severity=AlertSeverity.CRITICAL,
            scraper_name="TestScript",
            metadata={"test": True, "channel": "webhook"}
        )

        if results.get("WebhookAlertChannel"):
            print("✓ Test webhook sent successfully")
        else:
            print("✗ Test webhook failed")
            print("  Check logs for error details")
    else:
        print("✗ Generic webhook not configured")
        print("  Set ALERT_WEBHOOK_URL environment variable (optional)")


async def test_all_channels():
    """Test all configured alert channels"""
    print("\n" + "="*60)
    print("Alert System Test Summary")
    print("="*60)

    manager = get_alert_manager()

    print(f"\nConfigured alert channels: {len(manager.channels)}")
    for channel in manager.channels:
        status = "enabled" if channel.enabled else "disabled"
        print(f"  - {channel.__class__.__name__}: {status}")

    if not manager.channels:
        print("\n⚠️  WARNING: No alert channels configured!")
        print("   Set environment variables to enable alerting:")
        print("   - Email: SMTP_HOST, SMTP_USER, SMTP_PASSWORD, ALERT_TO_EMAILS")
        print("   - Slack: SLACK_WEBHOOK_URL")
        print("   - Discord: DISCORD_WEBHOOK_URL")
        print("   - Webhook: ALERT_WEBHOOK_URL")
        return

    print("\nSending test alert to all channels...")
    results = await send_alert(
        title="🎯 Multi-Channel Test Alert",
        message="This test alert is being sent to all configured channels simultaneously.",
        severity=AlertSeverity.MEDIUM,
        scraper_name="TestScript",
        metadata={
            "test": True,
            "timestamp": asyncio.get_event_loop().time(),
            "purpose": "multi-channel_test"
        }
    )

    print("\nResults:")
    for channel, success in results.items():
        status = "✓ Success" if success else "✗ Failed"
        print(f"  {channel}: {status}")

    success_count = sum(1 for s in results.values() if s)
    total_count = len(results)

    print(f"\nOverall: {success_count}/{total_count} channels successful")

    if success_count == 0:
        print("⚠️  All channels failed - check configuration and logs")
    elif success_count < total_count:
        print("⚠️  Some channels failed - check logs for details")
    else:
        print("✓ All channels working correctly")


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("Politician Trading Tracker - Alert System Test")
    print("="*60)

    # Load .env file if present
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            print(f"✓ Loaded environment from {env_path}")
        else:
            print(f"⚠️  No .env file found at {env_path}")
    except ImportError:
        print("⚠️  python-dotenv not installed - using system environment only")

    # Run tests
    await test_email_configuration()
    await test_slack_configuration()
    await test_discord_configuration()
    await test_webhook_configuration()
    await test_all_channels()

    print("\n" + "="*60)
    print("Test Complete")
    print("="*60)
    print("\nNext steps:")
    print("1. Review results above")
    print("2. Check your email/Slack/Discord for test messages")
    print("3. Fix any failed channels")
    print("4. Configure additional channels if needed")
    print("\nFor help, see: docs/ALERTING_CONFIGURATION.md")


if __name__ == "__main__":
    asyncio.run(main())
