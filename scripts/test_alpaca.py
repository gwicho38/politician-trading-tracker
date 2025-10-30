#!/usr/bin/env python3
"""
Test Alpaca API connection
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv()

# Test with alpaca-py library
try:
    from alpaca.trading.client import TradingClient

    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")

    print("="*80)
    print("🔧 Testing Alpaca API Connection")
    print("="*80)
    print(f"\nAPI Key: {api_key[:4]}...{api_key[-4:]}")
    print(f"Key Type: {'Paper Trading (PK)' if api_key.startswith('PK') else 'Live Trading (AK)'}")
    print(f"Paper Mode: True")
    print(f"\nAttempting connection...")

    # Initialize client
    client = TradingClient(
        api_key=api_key,
        secret_key=secret_key,
        paper=True
    )

    print("✅ Client initialized")

    # Try to get account info
    print("\nFetching account info...")
    account = client.get_account()

    print("\n" + "="*80)
    print("✅ SUCCESS! Account Info:")
    print("="*80)
    print(f"Account ID: {account.id}")
    print(f"Status: {account.status}")
    print(f"Cash: ${float(account.cash):,.2f}")
    print(f"Portfolio Value: ${float(account.portfolio_value):,.2f}")
    print(f"Buying Power: ${float(account.buying_power):,.2f}")
    print(f"Account Blocked: {account.account_blocked}")
    print(f"Trading Blocked: {account.trading_blocked}")
    print("="*80)

    if account.account_blocked or account.trading_blocked:
        print("\n⚠️ WARNING: Account has restrictions!")
        print(f"Account Blocked: {account.account_blocked}")
        print(f"Trading Blocked: {account.trading_blocked}")

except Exception as e:
    print("\n" + "="*80)
    print("❌ FAILED")
    print("="*80)
    print(f"Error: {str(e)}")
    print("\nPossible causes:")
    print("1. API keys are invalid or expired")
    print("2. Paper trading account not activated")
    print("3. Network/firewall blocking connection")
    print("4. Alpaca service is down")
    print("\nTo fix:")
    print("- Go to https://alpaca.markets/")
    print("- Login and verify your paper trading account is active")
    print("- Try regenerating your paper trading API keys")
    print("- Check https://status.alpaca.markets/ for service status")
    print("="*80)

    import traceback
    print("\nFull error details:")
    traceback.print_exc()
    sys.exit(1)
